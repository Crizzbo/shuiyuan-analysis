"""验证依赖元数据缓存减少重复扫描，同时保留逐笔输入和文件哈希。"""
import hashlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from finance_tools import service


class MetadataCacheTests(unittest.TestCase):
    def tearDown(self):
        service._library_version.cache_clear()

    def test_cache_does_not_cache_calculations_or_hashes(self):
        """【UT-CACHE-01: 依赖元数据LRU缓存优化与源码实现哈希逐笔独立审计】

        1. 测试功能与测试点:
           - 验证 finance_tools.service 对第三方库版本元数据的 LRU 缓存生效，消除重复扫描开销。
           - 严格断言每次计算的输入哈希 (input_sha256) 与算法源码实现哈希 (implementation_sha256) 逐笔实时计算，绝不被缓存覆盖。

        2. 正常函数业务边界与参数契约:
           - calculate 接收模块与参数字典。
           - 返回结果中必须包含 input_sha256 与 implementation_sha256。

        3. 测试数据与模拟场景说明:
           - 计算两笔 NPV: [-100, 110] 与 [-100, 121]，贴现率 10.0%。
           - 模拟源码变更为 b'changed-code'。

        4. 预期断言与结果验证:
           - lookup 版本查询调用次数为 1 (缓存生效)。
           - a 与 b 的输入哈希和结果互不相等。
           - a 的源码哈希与 basic.py 文件哈希完全一致。
           - 模拟源码修改后 c 的哈希实时随之更新。
        """
        service._library_version.cache_clear()
        with patch.object(service,'version',return_value='test-version') as lookup:
            a=service.calculate('cashflow',dict(operation='npv',cashflows=[-100,110],interest_rate=.1))
            b=service.calculate('cashflow',dict(operation='npv',cashflows=[-100,121],interest_rate=.1))
            self.assertEqual(lookup.call_count,1)
            self.assertNotEqual(a['input_sha256'],b['input_sha256'])
            self.assertNotEqual(a['result'],b['result'])
            impl_file = ROOT / a.get('implementation_path', 'finance_tools/basic.py')
            self.assertEqual(a['implementation_sha256'], hashlib.sha256(impl_file.read_bytes()).hexdigest())
            # 模拟文件内容变化，不改真实源码，确认哈希仍逐笔读取。
            with patch.object(Path,'read_bytes',return_value=b'changed-code'):
                c=service.calculate('cashflow',dict(operation='npv',cashflows=[-100,110],interest_rate=.1))
            self.assertEqual(c['implementation_sha256'],hashlib.sha256(b'changed-code').hexdigest())


if __name__=='__main__':
    unittest.main()
