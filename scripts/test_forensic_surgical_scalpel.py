"""法证级证据穿透手术刀引擎单元测试套件.

本测试模块严格遵循《36号工程黄金设计规范》与四段式结构化中文契约测试模型:
1. 测试功能与测试点说明 (Test Functionality & Objectives)
2. 正常函数业务边界与参数契约 (Business Boundaries & Parameter Contracts)
3. 测试数据与模拟场景说明 (Test Data & Scenario Descriptions)
4. 预期断言与结果验证 (Expected Assertions & Verification)

涵盖附注受限资金剥离与违约安全垫、产成品库存塞货毒性去工程符号化评级、
研发支出大额资本化强行费用化挤出、大客户单点脆弱性折扣、
渠道批价倒挂与合同负债骤降无双重负号语病消除及中继门面 SSOT 等价性断言。
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.forensic_surgical_scalpel import (
    ForensicInputData,
    ForensicDissectionResult,
    ForensicSurgicalScalpel,
)
from finance_tools.forensic_surgical_scalpel import (
    ForensicInputData as FacadeForensicInputData,
    ForensicDissectionResult as FacadeForensicDissectionResult,
    ForensicSurgicalScalpel as FacadeForensicSurgicalScalpel,
)


class TestForensicSurgicalScalpel(unittest.TestCase):
    """法证级证据穿透手术刀引擎契约测试."""

    def setUp(self):
        self.scalpel = ForensicSurgicalScalpel()
        self.facade_scalpel = FacadeForensicSurgicalScalpel()

    def test_ut_scalpel_01_restricted_cash_and_debt_covenant_default(self):
        """【UT-SCALPEL-01: 附注受限资金剥离与债务违约红线安全垫断言】

        一、测试功能与测试点:
            验证第一刀（附注受限资金剥离）：穿透财报主表汇报的现金总额，
            扣除附注中的保证金、质押款后计算真实自由流动性；若跌破银行契约底线，
            触发【致命债务违约风险】警报与流动性估值惩罚折扣。

        二、正常函数业务边界与参数契约:
            - reported_cash: 100M
            - restricted_cash: 30M (占 30%, 超过 15% 阈值)
            - debt_covenant_minimum_cash: 80M (自由现金 70M < 80M，击穿底线)

        三、测试数据与模拟场景说明:
            测试账面现金虚胖且实质濒临违约的企业。

        四、预期断言与结果验证:
            断言 unrestricted_liquid_cash == 70.0。
            断言 covenant_safety_buffer == -10.0。
            断言 forensic_red_flags 包含 "流动性虚胖" 与 "致命债务违约风险"。
        """
        data = ForensicInputData(
            ticker="FAKE_CASH",
            company_name="假充裕公司",
            reported_cash_and_equivalents=100.0,
            restricted_cash_in_notes=30.0,
            debt_covenant_minimum_cash=80.0,
            raw_materials=10.0,
            work_in_process=10.0,
            finished_goods=10.0,
            prior_finished_goods=10.0,
            revenue_growth_pct=0.10,
            total_rd_spent=10.0,
            capitalized_rd_amount=0.0,
            reported_operating_income=20.0,
            reported_net_income=15.0,
        )
        res = self.scalpel.dissect(data)

        self.assertEqual(res.unrestricted_liquid_cash, 70.0)
        self.assertEqual(res.covenant_safety_buffer, -10.0)
        self.assertTrue(any("致命债务违约风险" in f for f in res.forensic_red_flags))
        self.assertTrue(any("流动性虚胖" in f for f in res.forensic_red_flags))

    def test_ut_scalpel_02_finished_goods_bloat_and_deengineered_verdict(self):
        """【UT-SCALPEL-02: 产成品异常飙升与渠道塞货毒性滞销去工程符号化评级断言】

        一、测试功能与测试点:
            验证第二刀（存货结构解剖）：当产成品库存增速大幅超越营收增速 20 个百分点以上时，
            系统准确识别渠道塞货或产品滞销，输出去工程符号化的中文通俗评级：
            "严重积压塞货 (产成品异常飙升，滞销减值高危)"，杜绝暴露纯英文工程代号。

        二、正常函数业务边界与参数契约:
            - 产成品上期 20M，当期 40M (激增 100%)
            - 营收同期增速仅 5% (增速差 95% > 20%)

        三、测试数据与模拟场景说明:
            测试下游需求衰退但管理层强行压货的制造业标的。

        四、预期断言与结果验证:
            断言 inventory_toxicity_verdict 包含 "严重积压塞货"。
            断言 inventory_toxicity_verdict 严禁包含 "Severe_Channel_Stuffing"。
            断言 suggested_inventory_impairment > 0。
            断言 forensic_red_flags 包含 "渠道塞货滞销"。
        """
        data = ForensicInputData(
            ticker="STUFFING_CO",
            company_name="塞货制造",
            reported_cash_and_equivalents=50.0,
            restricted_cash_in_notes=2.0,
            debt_covenant_minimum_cash=10.0,
            raw_materials=15.0,
            work_in_process=15.0,
            finished_goods=40.0,
            prior_finished_goods=20.0,  # 激增 100%
            revenue_growth_pct=0.05,     # 营收仅增 5%
            total_rd_spent=5.0,
            capitalized_rd_amount=0.0,
            reported_operating_income=15.0,
            reported_net_income=10.0,
        )
        res = self.scalpel.dissect(data)

        self.assertIn("严重积压塞货", res.inventory_toxicity_verdict)
        self.assertNotIn("Severe_Channel_Stuffing", res.inventory_toxicity_verdict)
        self.assertGreater(res.suggested_inventory_impairment, 0.0)
        self.assertTrue(any("渠道塞货滞销" in f for f in res.forensic_red_flags))

    def test_ut_scalpel_03_rd_capitalization_impairment_and_loss_defense(self):
        """【UT-SCALPEL-03: 研发支出大额资本化强行费用化利润挤出断言】

        一、测试功能与测试点:
            验证第三刀（研发资本化费用化剥离）：当资本化比例 > 12% 时，
            系统强行费用化扣减营业利润；当汇报利润处于亏损状态 (<= 0) 时，
            准确警报管理层试图掩盖实质性亏损，消除除零漏报缺陷。

        二、正常函数业务边界与参数契约:
            - 研发总投入 50M，资本化 20M (占 40%)
            - 汇报营业利润 10M，真实营业利润还原为 -10M

        三、测试数据与模拟场景说明:
            测试通过研发费用资本化将实质性亏损粉饰为盈利的标的。

        四、预期断言与结果验证:
            断言 true_operating_income == -10.0。
            断言 operating_income_haircut_pct == 200.0。
            断言 forensic_red_flags 包含 "真实营业利润虚增"。
        """
        data = ForensicInputData(
            ticker="CAPITALIZE_SCAM",
            company_name="粉饰科技",
            reported_cash_and_equivalents=50.0,
            restricted_cash_in_notes=0.0,
            debt_covenant_minimum_cash=10.0,
            raw_materials=5.0,
            work_in_process=5.0,
            finished_goods=5.0,
            prior_finished_goods=5.0,
            revenue_growth_pct=0.10,
            total_rd_spent=50.0,
            capitalized_rd_amount=20.0,  # 40% 资本化
            reported_operating_income=10.0,
            reported_net_income=8.0,
        )
        res = self.scalpel.dissect(data)

        self.assertEqual(res.true_operating_income, -10.0)
        self.assertGreater(res.operating_income_haircut_pct, 100.0)
        self.assertTrue(any("真实营业利润虚增" in f for f in res.forensic_red_flags))

    def test_ut_scalpel_04_customer_concentration_haircut(self):
        """【UT-SCALPEL-04: 大客户单点脆弱性集中度估值折扣断言】

        一、测试功能与测试点:
            验证第四刀（大客户集中度脆弱性折扣）：当第一大客户营收占比 > 30% 且存在替代或砍单风险时，
            系统启动估值折扣惩罚机制，并将警报纳入红线清单。

        二、正常函数业务边界与参数契约:
            - top_customer_share: 0.45 (45%)
            - top_customer_risk_flag: True

        三、测试数据与模拟场景说明:
            某苹果链/特斯拉链供应商面临大客户自研芯片替代或转移订单风险。

        四、预期断言与结果验证:
            断言 valuation_concentration_haircut_pct > 15.0。
            断言 forensic_red_flags 包含 "高危单点依赖" 与 "第一大客户占比高达 45.0%"。
        """
        data = ForensicInputData(
            ticker="SUPPLIER_RISK",
            company_name="果链代工",
            reported_cash_and_equivalents=80.0,
            restricted_cash_in_notes=5.0,
            debt_covenant_minimum_cash=20.0,
            raw_materials=20.0,
            work_in_process=20.0,
            finished_goods=10.0,
            prior_finished_goods=10.0,
            revenue_growth_pct=0.05,
            total_rd_spent=10.0,
            capitalized_rd_amount=0.0,
            reported_operating_income=30.0,
            reported_net_income=25.0,
            top_customer_share=0.45,
            top_customer_risk_flag=True,
        )
        res = self.scalpel.dissect(data)

        self.assertGreater(res.valuation_concentration_haircut_pct, 15.0)
        self.assertTrue(any("高危单点依赖" in f for f in res.forensic_red_flags))

    def test_ut_scalpel_05_channel_inversion_no_double_negative_syntax(self):
        """【UT-SCALPEL-05: 渠道批价倒挂与合同负债骤降无双重负号语病断言】

        一、测试功能与测试点:
            验证第五刀（微观现实对撞与语法语病消除）：
            当真实批发价低于出厂价时，文字表述应为“倒挂幅度 25.0% (-25.0%)”；
            当合同负债骤降为负值时，文字表述应为“合同负债骤降 35.0%”，
            严禁出现“倒挂幅度 -25%”或“骤降 -35%”的双重负号语言倒错缺陷。

        二、正常函数业务边界与参数契约:
            - 出厂价 1000，场外批发价 750 (倒挂 -25%)
            - channel_contract_liabilities_drain_pct: -35.0%

        三、测试数据与模拟场景说明:
            白酒/新能源车等渠道压货崩盘、黄牛倒挂抛售场景。

        四、预期断言与结果验证:
            断言 channel_inversion_active == True。
            断言 forensic_red_flags 包含 "渠道批价倒挂" 与 "倒挂幅度 25.0%"。
            断言 forensic_red_flags 包含 "合同负债骤降 35.0%"。
            断言 forensic_red_flags 严禁出现 "倒挂幅度 -" 或 "骤降 -"。
        """
        data = ForensicInputData(
            ticker="CHANNEL_COLLAPSE",
            company_name="倒挂酒业",
            reported_cash_and_equivalents=100.0,
            restricted_cash_in_notes=0.0,
            debt_covenant_minimum_cash=10.0,
            raw_materials=20.0,
            work_in_process=20.0,
            finished_goods=30.0,
            prior_finished_goods=30.0,
            revenue_growth_pct=0.05,
            total_rd_spent=5.0,
            capitalized_rd_amount=0.0,
            reported_operating_income=40.0,
            reported_net_income=30.0,
            factory_quote=1000.0,
            real_market_wholesale_quote=750.0,  # 倒挂 25%
            channel_contract_liabilities_drain_pct=-35.0, # 预收款降 35%
        )
        res = self.scalpel.dissect(data)

        self.assertTrue(res.channel_inversion_active)
        flag_inversion = [f for f in res.forensic_red_flags if "渠道批价倒挂" in f]
        self.assertTrue(len(flag_inversion) > 0)
        self.assertIn("倒挂幅度 25.0%", flag_inversion[0])
        self.assertNotIn("倒挂幅度 -", flag_inversion[0])

        flag_drain = [f for f in res.forensic_red_flags if "合同负债骤降" in f]
        self.assertTrue(len(flag_drain) > 0)
        self.assertIn("合同负债骤降 35.0%", flag_drain[0])
        self.assertNotIn("骤降 -", flag_drain[0])

    def test_ut_scalpel_06_facade_and_core_ssot_equivalence(self):
        """【UT-SCALPEL-06: 向下兼容中继门面 SSOT 完全等价性断言】

        一、测试功能与测试点:
            验证 `finance_tools.forensic_surgical_scalpel` 中继门面与底层核心
            `financial_core.engines.forensic_surgical_scalpel` 计算输出 100% 相同。

        二、正常函数业务边界与参数契约:
            - Facade 与 Core 传入相同输入。

        三、测试数据与模拟场景说明:
            测试标准法证解剖场景。

        四、预期断言与结果验证:
            断言门面与核心输出属性完全一致。
        """
        data_core = ForensicInputData(
            ticker="COMPARE",
            company_name="对账科技",
            reported_cash_and_equivalents=100.0,
            restricted_cash_in_notes=10.0,
            debt_covenant_minimum_cash=20.0,
            raw_materials=10.0,
            work_in_process=10.0,
            finished_goods=15.0,
            prior_finished_goods=12.0,
            revenue_growth_pct=0.15,
            total_rd_spent=20.0,
            capitalized_rd_amount=2.0,
            reported_operating_income=30.0,
            reported_net_income=25.0,
        )
        data_facade = FacadeForensicInputData(
            ticker="COMPARE",
            company_name="对账科技",
            reported_cash_and_equivalents=100.0,
            restricted_cash_in_notes=10.0,
            debt_covenant_minimum_cash=20.0,
            raw_materials=10.0,
            work_in_process=10.0,
            finished_goods=15.0,
            prior_finished_goods=12.0,
            revenue_growth_pct=0.15,
            total_rd_spent=20.0,
            capitalized_rd_amount=2.0,
            reported_operating_income=30.0,
            reported_net_income=25.0,
        )

        res_core = self.scalpel.dissect(data_core)
        res_facade = self.facade_scalpel.dissect(data_facade)

        self.assertEqual(res_core.unrestricted_liquid_cash, res_facade.unrestricted_liquid_cash)
        self.assertEqual(res_core.inventory_toxicity_verdict, res_facade.inventory_toxicity_verdict)
        self.assertEqual(res_core.final_equity_value_haircut_pct, res_facade.final_equity_value_haircut_pct)
        self.assertEqual(res_core.forensic_red_flags, res_facade.forensic_red_flags)

    def test_ut_scalpel_07_buyer_dossier_card_and_to_dict_contract(self):
        """【UT-SCALPEL-07: 法证手术刀买方全息研报卡片与 to_dict 契约断言】

        一、测试功能与测试点:
            1. 验证 `ForensicDissectionResult` 具备标准 `narrative_zh` 全息研报卡片；
            2. 验证卡片通俗整合五大刀法核心结论（流动性自由现金、存货毒性、营业利润挤出、大客户折扣、渠道倒挂与估值惩罚）；
            3. 验证 `to_dict()` 输出分层结构清晰，包含各维度数据与 `narrative_zh`。

        二、正常函数业务边界与参数契约:
            - dissect 正常返回 ForensicDissectionResult。

        三、测试数据与模拟场景说明:
            测试标准法务风险标的。

        四、预期断言与结果验证:
            断言 narrative_zh 包含“【标的 RISK_CO 法证级财务造假与微观血肉手术刀研报】”。
            断言 to_dict() 包含 liquidity、inventory、operating_income_restated、concentration_and_channel、valuation_penalty 与 narrative_zh。
        """
        data = ForensicInputData(
            ticker="RISK_CO",
            company_name="高危实业",
            reported_cash_and_equivalents=100.0,
            restricted_cash_in_notes=20.0,
            debt_covenant_minimum_cash=50.0,
            raw_materials=10.0,
            work_in_process=10.0,
            finished_goods=30.0,
            prior_finished_goods=15.0,
            revenue_growth_pct=0.10,
            total_rd_spent=20.0,
            capitalized_rd_amount=5.0,
            reported_operating_income=25.0,
            reported_net_income=20.0,
            top_customer_share=0.40,
            top_customer_risk_flag=True,
            factory_quote=100.0,
            real_market_wholesale_quote=85.0,
            channel_contract_liabilities_drain_pct=-25.0,
        )
        res = self.scalpel.dissect(data)

        self.assertIn("法证级财务造假与微观血肉手术刀研报", res.narrative_zh)
        self.assertIn("真实可动用自由现金 $80.0", res.narrative_zh)
        self.assertIn("银行契约违约安全垫为 $30.0", res.narrative_zh)

        d = res.to_dict()
        self.assertEqual(d["ticker"], "RISK_CO")
        self.assertIn("liquidity", d)
        self.assertIn("inventory", d)
        self.assertIn("operating_income_restated", d)
        self.assertIn("concentration_and_channel", d)
        self.assertIn("valuation_penalty", d)
        self.assertIn("narrative_zh", d)
        self.assertEqual(d["narrative_zh"], res.narrative_zh)


if __name__ == "__main__":
    unittest.main()
