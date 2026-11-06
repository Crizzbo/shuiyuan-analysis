"""真实财报答案及失败路径回归；网络访问在整个测试进程中被禁止。"""
import copy
import json
from pathlib import Path
import socket
import sys
import unittest
from lxml import etree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
def deny(*args,**kwargs):
    raise AssertionError('本地解析禁止网络')
socket.socket.connect=deny
socket.create_connection=deny
from financial_reporting.pipeline import run, numeric, period_of, pdf_row, reconcile, validate, local, metric_batch
from finance_tools.metric_pipeline import run_batch

class ReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plans=[json.loads((ROOT/f'examples/financial/{name}-2026.json').read_text(encoding='utf-8')) for name in ['intu','sony']]
        cls.reports=[run(p) for p in cls.plans]
        cls.nintendo=run(json.loads((ROOT/'examples/financial/nintendo-2026.json').read_text(encoding='utf-8')))
    def test_jgaap_answers_and_cash_definition(self):
        """【UT-FINREP-01: 日本会计准则(J-GAAP)财报事实抽取与现金存款会计口径严密区分】

        1. 测试功能与测试点:
           - 验证针对任天堂 (Nintendo) J-GAAP 财报的 30 项科目抽取与 6 项平账校验。
           - 严格断言 J-GAAP 口径下的 cash_end (现金及现金等价物) 与 cash_deposits (现存款) 的本质区分。
           - 严禁在 J-GAAP 体系下混用通用的 'cash' 字段。

        2. 正常函数业务边界与参数契约:
           - 货币单位 JPY，会计准则 J-GAAP，四舍五入容差 1,000,000 JPY。

        3. 测试数据与模拟场景说明:
           - 任天堂 2026-03-31 财年报表：营收 2.313万亿日元，净利润 4240.92亿日元，期末现金 1.316万亿日元。

        4. 预期断言与结果验证:
           - facts 数量为 30，checks 6 项全部 passed，issues 为空。
           - cash_end 与 cash_deposits 数值完全吻合，'cash' 字段不在 rows 中。
        """
        r=self.nintendo
        self.assertFalse(r['issues'])
        self.assertEqual(len(r['facts']),30)
        self.assertEqual(sum(c['status']=='passed' for c in r['checks']),6)
        self.assertFalse([c for c in r['checks'] if c['status']!='passed'])
        rows={f['field']:f for f in r['facts'] if f['period']['end']=='2026-03-31'}
        self.assertEqual(rows['revenue']['value'],'2313051000000')
        self.assertEqual(rows['net_income']['value'],'424092000000')
        self.assertEqual(rows['cash_end']['value'],'1316680000000')
        self.assertEqual(rows['cash_deposits']['value'],'1791802000000')
        self.assertNotIn('cash',rows)
        self.assertTrue(all(f['currency']=='JPY' and f['accounting_basis']=='J-GAAP' and f['rounding_tolerance']=='1000000' for f in r['facts']))

    def test_jgaap_convenience_column_and_notes_block(self):
        """【UT-FINREP-02: J-GAAP注记栏标记(*1)与便利货币换算列对齐与列漂移拦截】

        1. 测试功能与测试点:
           - 验证 pdf_reviewed_columns 准确识别日式财报注记标记 (*1) 与列 Token。
           - 提取指定选择列的金额，保留上下文摘录。
           - 遇到未知或错配标记 (*2) 时刚性拦截并抛出 ValueError。

        2. 正常函数业务边界与参数契约:
           - 输入文本与 column_tokens 规范结构。

        3. 测试数据与模拟场景说明:
           - 场景 1: 合法注记标记 '*1'；场景 2: 漂移注记 '*2'。

        4. 预期断言与结果验证:
           - 场景 1 提取值为 ['100000000', '200000000']。
           - 场景 2 抛出 ValueError。
        """
        from financial_reporting.pipeline import pdf_reviewed_columns
        row={'label':'Cash','column_tokens':['*1','amount','*1','amount','amount'],'selected_columns':[0,1]}
        values,excerpt=pdf_reviewed_columns('Cash\n\n*1\n100\n*1\n200\n1\nNext',row)
        self.assertEqual(values,['100000000','200000000'])
        self.assertIn('\n\n*1\n',excerpt)
        with self.assertRaises(ValueError):pdf_reviewed_columns('Cash\n*2\n100\n*1\n200\n1',row)

    def test_us_answers(self):
        """【UT-FINREP-03: 美股GAAP三表财务事实精准换算与营业利润率批处理指标对齐】

        1. 测试功能与测试点:
           - 验证 Intuit (INTU) 美股 US-GAAP 财报数据抽取。
           - 验证年度营收 214.48 亿美元，营业利润 58.84 亿美元。
           - 验证批处理下游计算指标 operating_margin 精确对齐 5884 / 21448。

        2. 正常函数业务边界与参数契约:
           - 事实无报错且指标计算状态正常。

        3. 测试数据与模拟场景说明:
           - 2026-07-31 财年报表输入。

        4. 预期断言与结果验证:
           - revenue == 21448000000。
           - operating_income == 5884000000。
           - operating_margin 近似等于 5884/21448，issues 为空。
        """
        r=self.reports[0]
        rows={f['field']:f for f in r['facts'] if f['period']['end']=='2026-07-31' and f['period']['basis']=='annual'}
        self.assertEqual(int(rows['revenue']['value']),21448000000)
        self.assertEqual(int(rows['operating_income']['value']),5884000000)
        calc=[c for c in r['calculations'] if c['metric_id']=='operating_margin' and c['period']['end']=='2026-07-31'][0]
        self.assertAlmostEqual(calc['value'],5884/21448)
        self.assertFalse(r['issues'])

    def test_japan_scope_and_negative(self):
        """【UT-FINREP-04: 日股IFRS合并持续经营口径与负净利润指标计算安全熔断】

        1. 测试功能与测试点:
           - 验证索尼 (SONY) IFRS 口径下合并持续经营口径 (consolidated_continuing) 识别。
           - 验证负净利润 (-3024.92 亿日元) 忠实保留负号。
           - 验证衍生指标 net_margin 在面对严重亏损或异常时安全熔断为 'blocked'。

        2. 正常函数业务边界与参数契约:
           - accounting_basis == 'IFRS'。

        3. 测试数据与模拟场景说明:
           - 索尼 2026-03-31 财年净利润亏损场景。

        4. 预期断言与结果验证:
           - scope_id == 'consolidated_continuing'。
           - net_income == -302492000000。
           - net_margin 计算状态全部为 'blocked'。
        """
        r=self.reports[1]
        rows={f['field']:f for f in r['facts'] if f['period']['end']=='2026-03-31' and f['period']['basis']=='annual'}
        self.assertEqual(rows['revenue']['scope_id'],'consolidated_continuing')
        self.assertEqual(int(rows['net_income']['value']),-302492000000)
        self.assertEqual(rows['net_income']['accounting_basis'],'IFRS')
        self.assertTrue(all(c['status']=='blocked' for c in r['calculations'] if c['metric_id']=='net_margin'))
        self.assertFalse(r['issues'])

    def test_reconciliation_answers(self):
        """【UT-FINREP-05: 资产负债平衡表与现金流量调节表自动对账刚性校验】

        1. 测试功能与测试点:
           - 验证多份样本财报的对账结果 (balance_sheet 平账与 cash_flow_bridge 勾稽)。
           - 确保没有产生任何 'failed' 状态的核验条目。

        2. 正常函数业务边界与参数契约:
           - 所有核验规则必须全部为 'passed'。

        3. 测试数据与模拟场景说明:
           - 遍历已生成的样本报表。

        4. 预期断言与结果验证:
           - 无 failed 状态。
           - balance_sheet passed 次数符合契约 (2 次)。
           - cash_flow_bridge passed 次数符合契约 (3 次)。
        """
        for r in self.reports:
            self.assertFalse([c for c in r['checks'] if c['status']=='failed'])
            self.assertEqual(sum(c['check']=='balance_sheet' and c['status']=='passed' for c in r['checks']),2)
            self.assertEqual(sum(c['check']=='cash_flow_bridge' and c['status']=='passed' for c in r['checks']),3)

    def test_rounding_failure_blocks(self):
        """【UT-FINREP-06: 资产负债不平账舍入误差超限(>容差)阻断与失败打标】

        1. 测试功能与测试点:
           - 验证 validate 函数对资产负债表平衡性的刚性约束。
           - 人为篡改资产金额 (+10,000,000 JPY)，超过允许的舍入容差。
           - 验证核验结果立即出现 'failed' 且目标科目状态被标记为 'check_failed'。

        2. 正常函数业务边界与参数契约:
           - 差额 > tolerance 时触发平账阻断。

        3. 测试数据与模拟场景说明:
           - 篡改索尼财报资产字段 assets。

        4. 预期断言与结果验证:
           - 'failed' 出现在 checks 状态中。
           - target['status'] == 'check_failed'。
        """
        facts=copy.deepcopy(self.reports[1]['facts'])
        target=next(f for f in facts if f['field']=='assets')
        target['value']=str(int(target['value'])+10000000)
        self.assertIn('failed',[c['status'] for c in validate(facts)])
        self.assertEqual(target['status'],'check_failed')

    def test_duplicate_conflict(self):
        """【UT-FINREP-07: 同一科目数值冲突排他对账标记(conflict状态拦截)】

        1. 测试功能与测试点:
           - 验证 reconcile 函数对同一期间、同一科目但不同数值的排斥性对账逻辑。
           - 严禁静默覆盖或随机选择，必须将两条冲突事实全部打标为 'conflict'。

        2. 正常函数业务边界与参数契约:
           - 相同键值但 value 不同触发冲突。

        3. 测试数据与模拟场景说明:
           - 复制一份事实，将数值 +1。

        4. 预期断言与结果验证:
           - 产生的结果中所有记录 status 均为 'conflict'。
        """
        f=copy.deepcopy(self.reports[0]['facts'][0]); other=copy.deepcopy(f)
        other['value']=str(int(f['value'])+1)
        self.assertTrue(all(x['status']=='conflict' for x in reconcile([f,other])))

    def test_equal_duplicates_keep_evidence(self):
        """【UT-FINREP-08: 重复等值事实去重保留多源证据引用链条(duplicate_refs)】

        1. 测试功能与测试点:
           - 验证相同数值的重复事实在对账合并时，只保留 1 条主事实。
           - 副本事实被合并至 duplicate_refs 列表中，完整保留多源审计证据。

        2. 正常函数业务边界与参数契约:
           - 合并后长度为 1，duplicate_refs 长度为 1。

        3. 测试数据与模拟场景说明:
           - 传入两条完全相同的财报事实。

        4. 预期断言与结果验证:
           - len(result) == 1。
           - len(result[0]['duplicate_refs']) == 1。
        """
        f=copy.deepcopy(self.reports[0]['facts'][0]); result=reconcile([f,copy.deepcopy(f)])
        self.assertEqual(len(result),1)
        self.assertEqual(len(result[0]['duplicate_refs']),1)

    def test_hash_lock(self):
        """【UT-FINREP-09: 原始输入文件SHA-256内容哈希强锁定与防篡改熔断】

        1. 测试功能与测试点:
           - 验证 run 执行前对输入计划预期哈希 expected_sha256 的强一致校验。
           - 预期哈希不匹配时，刚性抛出包含 '内容锁' 的 ValueError。

        2. 正常函数业务边界与参数契约:
           - 篡改哈希立即熔断。

        3. 测试数据与模拟场景说明:
           - 设置 expected_sha256 为 64 个 '0'。

        4. 预期断言与结果验证:
           - 抛出 ValueError，正则匹配 '内容锁'。
        """
        p=copy.deepcopy(self.plans[0]); p['expected_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'内容锁'):
            run(p)

    def test_company_identity(self):
        """【UT-FINREP-10: 实体身份代码(entity_id)一致性核验与跨实体污染拦截】

        1. 测试功能与测试点:
           - 验证 run 对计划内声明实体与源文件实体的交叉核验。
           - 实体代码篡改时（如篡改为 'US:OTHER'），阻断执行并报错。

        2. 正常函数业务边界与参数契约:
           - 身份不符抛出 ValueError。

        3. 测试数据与模拟场景说明:
           - entity_id 修改为 'US:OTHER'。

        4. 预期断言与结果验证:
           - 抛出 ValueError，正则匹配 '身份'。
        """
        p=copy.deepcopy(self.plans[0]); p['entity_id']='US:OTHER'
        with self.assertRaisesRegex(ValueError,'身份'):
            run(p)

    def test_paths(self):
        """【UT-FINREP-11: 财报解析本地引用路径安全边界与外网/越界URL刚性阻断】

        1. 测试功能与测试点:
           - 验证 local 函数对项目外文件、跨盘符绝对路径及网络 URL 的绝对拦截。
           - 拦截 '../outside', 'C:/outside', 'https://example.com', '/outside'。

        2. 正常函数业务边界与参数契约:
           - 越界输入必须抛出 ValueError。

        3. 测试数据与模拟场景说明:
           - 4 种典型越界与外网路径输入。

        4. 预期断言与结果验证:
           - 4 种场景全部引发 ValueError。
        """
        for p in ['../outside','C:/outside','https://example.com','/outside']:
            with self.assertRaises(ValueError):
                local(p)

    def test_transform_sign_scale_and_nil(self):
        """【UT-FINREP-12: iXBRL数字符号(sign)、量纲(scale)转换与nil空值拦截】

        1. 测试功能与测试点:
           - 验证 numeric 函数正确解析 iXBRL 的 sign 负号与 scale 量纲放大。
           - 验证标有 xsi:nil="true" 的空值元素时抛出 ValueError。

        2. 正常函数业务边界与参数契约:
           - '1,234' with sign='-' and scale='6' -> '-1234000000'。

        3. 测试数据与模拟场景说明:
           - 解析 XML 片段；随后追加 nil='true'。

        4. 预期断言与结果验证:
           - 数值转换为 '-1234000000'。
           - nil 为 true 时抛出 ValueError。
        """
        node=etree.fromstring(b'<ix:nonFraction xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:ixt="http://www.xbrl.org/inlineXBRL/transformation/2020-02-12" format="ixt:num-dot-decimal" sign="-" scale="6">1,234</ix:nonFraction>')
        self.assertEqual(numeric(node),'-1234000000')
        node.set('{http://www.w3.org/2001/XMLSchema-instance}nil','true')
        with self.assertRaises(ValueError):
            numeric(node)

    def test_cumulative_not_quarter(self):
        """【UT-FINREP-13: XBRL期间上下文周期属性判定(累计数与单季度区分)】

        1. 测试功能与测试点:
           - 验证 period_of 识别 6 个月跨度周期为累计期 (ytd_or_other)。
           - 严禁将半年度累计数误判为单季度数值。

        2. 正常函数业务边界与参数契约:
           - 半年期返回 basis == 'ytd_or_other'。

        3. 测试数据与模拟场景说明:
           - 2026-01-01 至 2026-06-30 的 period 节点。

        4. 预期断言与结果验证:
           - basis 为 'ytd_or_other'。
        """
        c=etree.fromstring(b'<context xmlns="http://www.xbrl.org/2003/instance"><period><startDate>2026-01-01</startDate><endDate>2026-06-30</endDate></period></context>')
        self.assertEqual(period_of(c)['basis'],'ytd_or_other')

    def test_pdf_column_change(self):
        """【UT-FINREP-14: PDF表格列结构漂移/破损数据行缺失刚性拦截】

        1. 测试功能与测试点:
           - 验证 pdf_row 在检测到表格列定义变动或缺失破折号占位时抛出异常。
           - 拦截格式未对齐的 PDF 脏数据。

        2. 正常函数业务边界与参数契约:
           - 格式不合规抛出 ValueError。

        3. 测试数据与模拟场景说明:
           - 列数不匹配行与包含无效占位符的行。

        4. 预期断言与结果验证:
           - 两种场景均引发 ValueError。
        """
        with self.assertRaises(ValueError):
            pdf_row('Sales\n22\n100\n200\n300\n400','Sales','22',3)
        with self.assertRaises(ValueError):
            pdf_row('Sales\n22\n100\n-\n300','Sales','22',3)

    def test_real_metric_bridge_without_fabricated_publication(self):
        """【IT-FINREP-15: 真实财报事实跨模块桥接计算(保留证据未公布状态)】

        1. 测试功能与测试点:
           - 验证 metric_batch 将解析后的财报事实无损桥接至指标计算引擎 run_batch。
           - 保留 published_at 为 None (未人工伪造公布时间)。
           - 计算结果准确输出 operating_margin == 5884/21448。

        2. 正常函数业务边界与参数契约:
           - 指标批量执行返回 status == 'computed'。

        3. 测试数据与模拟场景说明:
           - Intuit 财报事实批量输入。

        4. 预期断言与结果验证:
           - published_at 为 None。
           - status == 'computed'，数值吻合。
        """
        r=self.reports[0]
        b=metric_batch(r,'2026-07-31',r['artifact']['available_at'])
        self.assertIsNone(b['facts'][0]['source']['published_at'])
        result=run_batch(b)
        self.assertEqual(result['results'][0]['status'],'computed')
        self.assertAlmostEqual(result['results'][0]['value'],5884/21448)

    def test_asof_blocks_lookahead(self):
        """【UT-FINREP-16: 未来时点穿越(Lookahead)与早于可用时间计算刚性阻断】

        1. 测试功能与测试点:
           - 验证 metric_batch 严禁前视未来时点。
           - 传入早于财报可用时间 (available_at) 的 as_of 时间戳时直接抛出 ValueError。

        2. 正常函数业务边界与参数契约:
           - as_of < available_at 抛出异常。

        3. 测试数据与模拟场景说明:
           - 传入 2026-09-10 时点（早于报表可用时间）。

        4. 预期断言与结果验证:
           - 抛出 ValueError。
        """
        with self.assertRaises(ValueError):
            metric_batch(self.reports[0],'2026-07-31','2026-09-10T00:00:00+00:00')

    def test_machine_contract_and_dictionary(self):
        """【FT-FINREP-17: 财报Schema元模型验证与财务数据字典Markdown对齐】

        1. 测试功能与测试点:
           - 验证 financial-report.schema.json 符合 Draft202012Validator 规范。
           - 验证所有生成的真实报表 100% 满足该 Schema。
           - 破坏性测试: 将数值篡改为 None 确保能准确侦测出校验错误。
           - 验证 docs/financial-dictionary/*.md 文档与 Schema 字段定义 100% 互相对齐。

        2. 正常函数业务边界与参数契约:
           - 模式合规且文档无缺漏。

        3. 测试数据与模拟场景说明:
           - 校验全量报表与字典 markdown 文件。

        4. 预期断言与结果验证:
           - 语法检验通过，iter_errors 探测出非法 None，字典包含全部属性 title/key。
        """
        from jsonschema import Draft202012Validator,FormatChecker
        schema=json.loads((ROOT/'schemas/financial-report.schema.json').read_text(encoding='utf-8'))
        Draft202012Validator.check_schema(schema)
        validator=Draft202012Validator(schema,format_checker=FormatChecker())
        for r in self.reports:
            validator.validate(r)
        changed=copy.deepcopy(self.reports[0]);changed['calculations'][0]['value']=None
        self.assertTrue(list(validator.iter_errors(changed)))
        for name,table in [('report',schema),*schema['$defs'].items()]:
            text=(ROOT/f'docs/financial-dictionary/{name}.md').read_text(encoding='utf-8')
            for key,v in table['properties'].items():
                self.assertIn(v.get('title',key),text)

if __name__=='__main__':
    unittest.main()
