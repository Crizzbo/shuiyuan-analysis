"""假数据缺陷回归：调用方数字不能入报告；缺失、口径与事实血缘不能伪造。"""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from financial_reporting.evidence_dossiers import build_company_dossier,validate_dossier
from financial_reporting.deep_schema_generator import build_deep_dossier_data
from financial_reporting.generic_metrics import GenericFinancialMetrics

class Tests(unittest.TestCase):
    def test_unknown_company_missing_not_default(self):
        """【UT-EVIDENCE-01: 未建档公司证据缺失防御-严禁静默伪造默认财报事实】

        1. 测试功能与测试点:
           - 验证 build_company_dossier 对未核验/未建档公司的防御性逻辑。
           - 严禁调用方随意传入假数据填充入报告，缺失事实必须显式为空 (facts=[])。
           - 估值与投资立场必须严格为 None，杜绝未审研判外溢。

        2. 正常函数业务边界与参数契约:
           - 未收录标的统一返回空事实列表与空估值。

        3. 测试数据与模拟场景说明:
           - 传入无证据测试标的 'NO_REAL_EVIDENCE' 与假标的 'US:FAKE'。

        4. 预期断言与结果验证:
           - facts 为 []。
           - valuation 与 investment_stance 均为 None。
        """
        data=build_company_dossier('NO_REAL_EVIDENCE'.replace('_',''),'US','无证据测试')
        self.assertEqual(data['facts'],[])
        self.assertIsNone(data['valuation'])
        self.assertIsNone(data['investment_stance'])
        company={'ticker':'US:FAKE','market':'US','name':'测试','raw_financials':{'revenue':999999,'cash_and_equivalents':0},'valuation_params':{'shares':1}}
        self.assertEqual(build_deep_dossier_data(company)['facts'],[])

    def test_registered_stx_and_tamper_rejection(self):
        """【UT-EVIDENCE-02: 官方归档希捷(STX)财报底账读取与事实篡改物理阻断】

        1. 测试功能与测试点:
           - 验证希捷 (STX) 官方归档财报科目的准确读取 (营收 12195M, 自由现金流 3105M, 现金 1704M)。
           - 验证 validate_dossier 刚性校验防御: 任何手工篡改金额、货币单位、截止日期、合并范围或注入未核验估值均直接阻断抛出 ValueError。

        2. 正常函数业务边界与参数契约:
           - 档案各字段必须通过原件 SHA-256 证据链校验。

        3. 测试数据与模拟场景说明:
           - 读取希捷档案，分别篡改 value='8550', unit='JPY_million', period_end='2025-12-31', scope='subsidiary' 及非法注入 target=32.02。

        4. 预期断言与结果验证:
           - 原始字段读取数值准确。
           - 5 种篡改场景全部刚性抛出 ValueError。
        """
        data=build_company_dossier('STX','US','希捷')
        facts={r['component']:r for r in data['facts']}
        self.assertEqual(facts['Revenue']['value'],'12195')
        self.assertEqual(facts['Revenue']['unit'],'USD_million')
        self.assertEqual(facts['Free cash flow']['value'],'3105')
        self.assertEqual(facts['Cash and cash equivalents']['value'],'1704')
        self.assertEqual(facts['Cash and cash equivalents']['period_start'],None)
        for field,value in [('value','8550'),('unit','JPY_million'),('period_end','2025-12-31'),('scope','subsidiary')]:
            bad=copy.deepcopy(data);bad['facts'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError): validate_dossier(bad)
        bad=copy.deepcopy(data);bad['valuation']={'target':32.02,'verified':True}
        with self.assertRaises(ValueError): validate_dossier(bad)

    def test_total_liabilities_not_interest_debt(self):
        """【UT-EVIDENCE-03: 会计口径严谨区分-总负债绝不混淆为有息负债】

        1. 测试功能与测试点:
           - 验证 GenericFinancialMetrics.compute_health_profile 对负债口径的严谨区分。
           - 仅提供有息负债 (total_debt) 时，严禁冒充总资产负债率 (debt_to_assets)。
           - 必须显式提供总负债 (total_liabilities) 才能计算真实的资产负债率。

        2. 正常函数业务边界与参数契约:
           - 字段口径未对齐时拒绝静默估算。

        3. 测试数据与模拟场景说明:
           - 场景 1: 仅有 total_debt=10, total_assets=100；
           - 场景 2: 补充 total_liabilities=70。

        4. 预期断言与结果验证:
           - 场景 1: debt_to_assets 不在 profile['metrics'] 中；
           - 场景 2: debt_to_assets 计算为 70 / 100 = 0.7 (70%)。
        """
        profile=GenericFinancialMetrics.compute_health_profile({'total_debt':10,'total_assets':100})
        self.assertNotIn('debt_to_assets',profile['metrics'])
        profile=GenericFinancialMetrics.compute_health_profile({'total_debt':10,'total_liabilities':70,'total_assets':100})
        self.assertEqual(profile['metrics']['debt_to_assets']['value'],.7)

    def test_zero_reported_value_preserved(self):
        """【UT-EVIDENCE-04: 财报披露零值保真-严禁将官方0增长误判为空值】

        1. 测试功能与测试点:
           - 验证当官方财报披露数据为零时 (如销量增长率为 0.0)，系统忠实保留数值 0。
           - 严禁将 0 当做缺失值 (None/NaN) 抹杀或触发回退默认值。

        2. 正常函数业务边界与参数契约:
           - float(zero['value']) == 0.0。

        3. 测试数据与模拟场景说明:
           - 可口可乐 (KO) 官方科目 system_unit_case_volume_growth。

        4. 预期断言与结果验证:
           - 提取值为 0。
           - validate_dossier 验证通过。
        """
        data=build_company_dossier('KO','US','可口可乐')
        zero=next(f for f in data['facts'] if f['component']=='system_unit_case_volume_growth')
        self.assertEqual(float(zero['value']),0)
        validate_dossier(data)

    def test_roe_does_not_silently_use_closing_equity(self):
        """【UT-EVIDENCE-05: ROE/ROA杜邦口径杜绝偷换期末净资产-强制加权平均】

        1. 测试功能与测试点:
           - 验证杜邦分析中 ROE 与 ROA 的学术与买方机构标准: 必须采用当期加权平均资产/权益。
           - 严禁为了图省事偷换使用期末单一截面净资产 (closing equity) 计算，缺少平均值时严禁伪造。

        2. 正常函数业务边界与参数契约:
           - 缺少 average_equity 时拒绝计算 roe。

        3. 测试数据与模拟场景说明:
           - 净利润 10，期末权益 100，资产 200；随后注入平均权益 80，平均资产 160。

        4. 预期断言与结果验证:
           - 仅有期末值时，roe 与 roa 均不在 metrics 中。
           - 注入平均值后，roe = 10 / 80 = 0.125，roa = 10 / 160 = 0.0625。
        """
        data={'net_income':10,'equity':100,'total_assets':200}
        result=GenericFinancialMetrics.compute_health_profile(data)
        self.assertNotIn('roe',result['metrics'])
        self.assertNotIn('roa',result['metrics'])
        result=GenericFinancialMetrics.compute_health_profile(dict(data,average_equity=80,average_total_assets=160))
        self.assertEqual(result['metrics']['roe']['value'],.125)
        self.assertEqual(result['metrics']['roa']['value'],.0625)

    def test_builder_runs_in_isolated_workspace(self):
        """【IT-EVIDENCE-06: 归档生成器在独立隔离工作空间批处理与清单验签】

        1. 测试功能与测试点:
           - 验证 build_company_archives.py 命令行生成器在隔离临时工作目录下运行。
           - 输出指定数量 (limit=2) 的企业 JSON 证据档案并生成 manifest.json。
           - 遍历生成文件执行全息契约校验 validate_dossier。

        2. 正常函数业务边界与参数契约:
           - 子进程退出码为 0，清单包含对应文件列表。

        3. 测试数据与模拟场景说明:
           - 调度前 2 家标的批处理生成。

        4. 预期断言与结果验证:
           - result.returncode == 0。
           - manifest['count'] == 2。
           - 生成的每份档案全部通过 validate_dossier。
        """
        with tempfile.TemporaryDirectory(prefix='.evidence-build-',dir=ROOT,ignore_cleanup_errors=True) as temporary:
            relative=Path(temporary).relative_to(ROOT).as_posix()
            result=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/build_company_archives.py'),
                '--limit','2','--json-only','--output-dir',relative],cwd=ROOT,capture_output=True,text=True,encoding='utf8',timeout=60)
            self.assertEqual(result.returncode,0,result.stderr)
            manifest=json.loads((Path(temporary)/'manifest.json').read_text(encoding='utf8'))
            self.assertEqual(manifest['count'],2)
            self.assertFalse(manifest['complete_replacement_set'])
            for item in manifest['files']:
                validate_dossier(json.loads((ROOT/item['json_path']).read_text(encoding='utf8')))

    def test_legacy_generators_fail_closed(self):
        """【UT-EVIDENCE-07: 废弃旧版生成器暗门刚性阻断熔断(Fail-Closed)】

        1. 测试功能与测试点:
           - 验证历史旧版依赖假数据模板的生成器入口已物理熔断 (Fail-Closed)。
           - update_company_universe, compute_company_analysis, build_daily_briefing_data, main 严禁静默伪造，调用时刚性抛出 ValueError。

        2. 正常函数业务边界与参数契约:
           - 废弃接口统一拦截。

        3. 测试数据与模拟场景说明:
           - 调用 4 个历史旧版函数。

        4. 预期断言与结果验证:
           - 4 个旧接口无一例外抛出 ValueError。
        """
        from scripts.build_full_universe import update_company_universe
        from scripts.run_daily_analysis import compute_company_analysis
        from financial_reporting.deep_schema_generator import build_daily_briefing_data
        from scripts.sync_final_pdf_to_gdrive import main
        for fn in [update_company_universe,lambda:compute_company_analysis({},None),lambda:build_daily_briefing_data({},None),main]:
            with self.assertRaises(ValueError): fn()

    def test_live_company_index_has_only_evidence_outputs(self):
        """【FT-EVIDENCE-08: 在线公司全量索引Schema契约与底层事实血缘双向验签】

        1. 测试功能与测试点:
           - 验证 knowledge/companies/companies.json 在线主索引严格符合 company-archive.schema.json。
           - 验证索引中每一家公司的 investment_stance 均为 None (绝不硬编码投资立场)。
           - 验证其引用的真实底账 evidence_path 文件物理存在且通过 validate_dossier 证据血缘校验。

        2. 正常函数业务边界与参数契约:
           - companies.json 模式完全合规，底层引用文件全部可验。

        3. 测试数据与模拟场景说明:
           - 遍历主索引中的全量公司记录。

        4. 预期断言与结果验证:
           - jsonschema.validate 验证通过。
           - index['companies_count'] == len(index['companies'])。
           - 每份档案的 symbol 与 ticker 后缀对齐，证据校验通过。
        """
        from jsonschema import validate
        index=json.loads((ROOT/'knowledge/companies/companies.json').read_text(encoding='utf8'))
        schema=json.loads((ROOT/'schemas/company-archive.schema.json').read_text(encoding='utf8'))
        validate(index,schema)
        self.assertEqual(index['companies_count'],len(index['companies']))
        for company in index['companies']:
            self.assertIsNone(company['investment_stance'])
            data=json.loads((ROOT/company['evidence_path']).read_text(encoding='utf8'))
            validate_dossier(data)
            self.assertEqual(data['symbol'],company['ticker'].split(':')[-1])

if __name__=='__main__': unittest.main()
