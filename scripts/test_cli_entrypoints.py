"""离线CLI真实进程测试：参数解析、派发、退出码与追加写入约束。"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class Tests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='.cli-test-',dir=ROOT,ignore_cleanup_errors=True)
        self.area=Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        self.relative=self.area.relative_to(ROOT).as_posix()

    def cli(self,script,*args):
        return subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts'/script),*args],cwd=ROOT,
            capture_output=True,text=True,encoding='utf8',timeout=60)

    def test_help_and_required_arguments(self):
        """【UT-CLI-01: 核心脚本命令行参数解析/帮助提示(--help)与未知命令拦截(退出码2)】

        1. 测试功能与测试点:
           - 验证 data_catalog.py, import_market_snapshot.py, build_company_archives.py 命令行参数解析。
           - 验证 --help 命令输出标准使用说明 (usage:) 并返回退出码 0。
           - 验证参数缺失或未知子命令时由 argparse 返回标准退出码 2。

        2. 正常函数业务边界与参数契约:
           - 参数合规返回 0，参数缺失返回 2。

        3. 测试数据与模拟场景说明:
           - 传入 --help；无参数调用；传入未知子命令 'unknown-command'。

        4. 预期断言与结果验证:
           - --help 返回码为 0，stdout 包含 'usage:'。
           - 无参数或非法命令返回码为 2。
        """
        for name in ('data_catalog.py','import_market_snapshot.py','build_company_archives.py'):
            with self.subTest(script=name):
                result=self.cli(name,'--help')
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn('usage:',result.stdout)
        self.assertEqual(self.cli('data_catalog.py').returncode,2)
        self.assertEqual(self.cli('data_catalog.py','unknown-command').returncode,2)
        self.assertEqual(self.cli('import_market_snapshot.py').returncode,2)

    def test_catalog_register_query_audit_and_failures(self):
        """【IT-CLI-02: 数据底账CLI服务注册/幂等去重/时点追溯/完整性审计与越界拦截】

        1. 测试功能与测试点:
           - 验证 data_catalog.py 核心生命周期命令: register-source, source-as-of, audit。
           - 验证初次注册成功，重复注册具备幂等性 (idempotent=True)。
           - 验证时点追溯查询 revision 递增，审计命令 ok 为 True。
           - 验证越界相对路径 ('../outside.json') 与非法时间戳刚性拦截 (返回码 1)。

        2. 正常函数业务边界与参数契约:
           - 合法数据清单注册成功，非法路径拦截。

        3. 测试数据与模拟场景说明:
           - 写入临时 source.txt 与 manifest.json。

        4. 预期断言与结果验证:
           - 首次注册 idempotent 为 False，二次注册为 True。
           - audit ok 为 True。
           - 非法路径与时间戳命令返回码为 1。
        """
        source=self.area/'source.txt'
        source.write_text('CLI synthetic test only',encoding='utf8')
        manifest=json.loads((ROOT/'examples/source.synthetic.manifest.json').read_text(encoding='utf8'))
        manifest['source_path']=source.relative_to(ROOT).as_posix()
        path=self.area/'manifest.json'
        path.write_text(json.dumps(manifest),encoding='utf8')
        args=('--store',self.relative+'/store')
        registered=self.cli('data_catalog.py',*args,'register-source',path.relative_to(ROOT).as_posix())
        self.assertEqual(registered.returncode,0,registered.stderr)
        self.assertFalse(json.loads(registered.stdout)['idempotent'])
        again=self.cli('data_catalog.py',*args,'register-source',path.relative_to(ROOT).as_posix())
        self.assertEqual(again.returncode,0,again.stderr)
        self.assertTrue(json.loads(again.stdout)['idempotent'])
        found=self.cli('data_catalog.py',*args,'source-as-of',manifest['source_id'],manifest['available_at'])
        self.assertEqual(found.returncode,0,found.stderr)
        self.assertEqual(json.loads(found.stdout)['manifest']['revision'],1)
        audit=self.cli('data_catalog.py',*args,'audit')
        self.assertEqual(audit.returncode,0,audit.stderr)
        self.assertTrue(json.loads(audit.stdout)['ok'])
        failed=self.cli('data_catalog.py',*args,'register-source','../outside.json')
        self.assertEqual(failed.returncode,1)
        self.assertIn('FAIL:',failed.stderr)
        invalid=self.cli('data_catalog.py',*args,'source-as-of',manifest['source_id'],'invalid-time')
        self.assertEqual(invalid.returncode,1)

    def import_args(self):
        raw='data/google-finance/raw/20261011T094549Z.json'
        acquired=json.loads((ROOT/raw).read_text(encoding='utf8'))['acquired_at']
        return [raw,'config/google-finance-smoke-plan.json','--output',self.relative+'/snapshot.json','--as-of',acquired]

    def test_market_import_and_no_overwrite(self):
        """【IT-CLI-03: 行情快照导入生成与同名文件物理防覆盖写入锁】

        1. 测试功能与测试点:
           - 验证 import_market_snapshot.py 解析原始行情快照并生成标准化输入。
           - 严格执行防静默覆盖约束: 目标文件已存在时二次导入必须拒绝 (返回非零退出码)，原文件内容保持不变。

        2. 正常函数业务边界与参数契约:
           - 首次写入成功，二次写入抛出覆盖冲突。

        3. 测试数据与模拟场景说明:
           - 导入 Google Finance 冒烟计划生成的 3 支标的快照。

        4. 预期断言与结果验证:
           - 首次导入成功，price 为 336.64，未核验前状态为 action_gate=='blocked'。
           - 二次导入返回非零码，原文件字节内容未受破坏。
        """
        args=self.import_args()
        imported=self.cli('import_market_snapshot.py',*args)
        self.assertEqual(imported.returncode,0,imported.stderr)
        path=self.area/'snapshot.json'
        original=path.read_bytes()
        data=json.loads(original)
        self.assertEqual(data['snapshot']['quotes'][0]['fields']['price']['value'],336.64)
        self.assertEqual(len(data['calculation_inputs']['inputs']),3)
        self.assertTrue(all(r['action_gate']=='blocked' for r in data['calculation_inputs']['inputs']))
        denied=self.cli('import_market_snapshot.py',*args)
        self.assertNotEqual(denied.returncode,0)
        self.assertEqual(path.read_bytes(),original)

    def test_market_failures_leave_no_output(self):
        """【UT-CLI-04: 导入异常时原子回滚与脏临时文件物理零残留(未来时间/越界/破损JSON)】

        1. 测试功能与测试点:
           - 验证 import_market_snapshot.py 在遭遇未来时间戳穿越、越界路径或破损 JSON 时执行原子回滚。
           - 严禁在目标输出路径残留半写入状态的脏数据文件。

        2. 正常函数业务边界与参数契约:
           - 异常退出时目标文件不存在。

        3. 测试数据与模拟场景说明:
           - 场景 1: 未来时间戳；场景 2: 越界路径；场景 3: 语法破损 JSON。

        4. 预期断言与结果验证:
           - 命令均返回非零退出码。
           - snapshot.json 物理文件不存在。
        """
        for mode in ('future','outside','invalid-json'):
            args=self.import_args()
            if mode=='future': args[-1]='2026-10-10T00:00:00Z'
            elif mode=='outside': args[0]='../outside.json'
            else:
                invalid=self.area/'bad.json';invalid.write_text('{broken',encoding='utf8')
                args[0]=invalid.relative_to(ROOT).as_posix()
            with self.subTest(mode=mode):
                result=self.cli('import_market_snapshot.py',*args)
                self.assertNotEqual(result.returncode,0)
                self.assertFalse((self.area/'snapshot.json').exists())

    def test_archive_output_path_rejection(self):
        """【UT-CLI-05: 归档导出路径非法跨界(上级/绝对盘符/根路径)刚性拦截】

        1. 测试功能与测试点:
           - 验证 build_company_archives.py 对输出目录的安全校验。
           - 拦截上级目录跨界 ('../outside')、跨盘符绝对路径 ('C:/outside') 及项目根目录写入。

        2. 正常函数业务边界与参数契约:
           - 参数解析拦截退出码为 2。

        3. 测试数据与模拟场景说明:
           - 目标路径包含 '../outside', 'C:/outside', '/outside', '.'。

        4. 预期断言与结果验证:
           - 所有非法输出路径均返回退出码 2。
        """
        for target in ('../outside','C:/outside','/outside','.'):
            with self.subTest(target=target):
                self.assertEqual(self.cli('build_company_archives.py','--output-dir',target).returncode,2)

if __name__=='__main__': unittest.main()
