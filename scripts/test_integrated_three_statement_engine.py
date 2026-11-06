"""动态三表强勾稽与现金跑道联动引擎单元测试套件.

本测试模块严格遵循《36号工程黄金设计规范》与四段式结构化中文契约测试模型:
1. 测试功能与测试点说明 (Test Functionality & Objectives)
2. 正常函数业务边界与参数契约 (Business Boundaries & Parameter Contracts)
3. 测试数据与模拟场景说明 (Test Data & Scenario Descriptions)
4. 预期断言与结果验证 (Expected Assertions & Verification)

涵盖三表动态勾稽联动、存货与应付款项动态营运资本占用 (Working Capital Delta)、
现金跑道安全月数测算、股权稀释风险分级与现金枯竭下界防御断言。
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.integrated_three_statement_engine import (
    BaselineFinancials,
    ProjectedYearResult,
    ThreeStatementSimulationResult,
    IntegratedThreeStatementEngine,
)
from finance_tools.integrated_three_statement_engine import (
    BaselineFinancials as FacadeBaselineFinancials,
    ProjectedYearResult as FacadeProjectedYearResult,
    ThreeStatementSimulationResult as FacadeThreeStatementSimulationResult,
    IntegratedThreeStatementEngine as FacadeIntegratedThreeStatementEngine,
)


class TestIntegratedThreeStatementEngine(unittest.TestCase):
    """动态三表强勾稽与现金跑道联动引擎契约测试."""

    def test_ut_three_01_dynamic_statement_linkage_and_wc_delta(self):
        """【UT-THREE-01: 动态三表多年度强勾稽与营收扩张营运资本动态占用断言】

        一、测试功能与测试点:
            验证 IntegratedThreeStatementEngine 能根据基期财务三表与未来多期营收增速，
            准确模拟利润表 (IS)、资产负债表营运资本 (BS Working Capital) 与现金流量表 (CF) 的联动闭环。
            断言营运资本占用 (delta_wc) 真实反映存货、应收与应付款项随营收扩张的动态变化，杜绝虚假抵消为零。

        二、正常函数业务边界与参数契约:
            - base: 基期财务数据 (营收 100M，毛利率 50%，DSO=45天，DIO=30天，DPO=40天)
            - revenue_growths: [0.20, 0.15] (未来两年分别增长 20%、15%)

        三、测试数据与模拟场景说明:
            测试正常成长型企业，营收扩张，营运资本被动态占用 (delta_wc > 0)。

        四、预期断言与结果验证:
            断言 projections 长度为 2。
            第一年营收 120.0M，毛利润 60.0M。
            第一年营运资本变动 delta_wc > 0，真实体现扩张带来的营运资金占用。
            断言期末现金 ending_cash = starting_cash + fcf。
        """
        base = BaselineFinancials(
            ticker="GROWTH_CO",
            cash_and_equivalents=50.0,
            total_debt=10.0,
            revenue=100.0,
            gross_margin_pct=50.0,
            opex_rnd=20.0,
            opex_sga=15.0,
            depr_amort=5.0,
            capex=8.0,
            tax_rate=0.21,
            dso_days=45.0,
            dio_days=30.0,
            dpo_days=40.0,
        )
        res = IntegratedThreeStatementEngine.simulate(base, revenue_growths=[0.20, 0.15])

        self.assertEqual(len(res.projections), 2)
        p1 = res.projections[0]
        self.assertAlmostEqual(p1.revenue, 120.0, places=1)
        self.assertAlmostEqual(p1.gross_profit, 60.0, places=1)
        # 营运资本因销售扩张而增加占用
        self.assertGreater(p1.working_capital_change, 0.0)
        # 现金勾稽验证
        self.assertAlmostEqual(p1.ending_cash, base.cash_and_equivalents + p1.free_cash_flow, places=2)

    def test_ut_three_02_burn_rate_and_dilution_warning_under_12m(self):
        """【UT-THREE-02: 研发失血期有限现金跑道 (<12个月) 极高稀释预警断言】

        一、测试功能与测试点:
            验证创新药/AI等高研发烧钱企业，在首年自由现金流为负且现金跑道 < 12 个月时，
            系统准确计算季度净消耗速率 (burn_rate_quarterly)，并触发“极高稀释风险 (<12个月)”的预警指令。

        二、正常函数业务边界与参数契约:
            - cash_and_equivalents: 20M
            - 首年预计净烧钱 (负 FCF): -30M
            - 跑道 = (20 / 30) * 12 = 8.0 个月

        三、测试数据与模拟场景说明:
            高强度研发管线推进期生物制药公司。

        四、预期断言与结果验证:
            断言 runway_months == 8.0。
            断言 dilution_risk_level 包含 "极高稀释风险" 与 "<12个月"。
            断言 verdict_zh 包含 "现金储备仅够维持 8.0 个月" 与 "ATM Offering"。
        """
        base = BaselineFinancials(
            ticker="BIOTECH_BURN",
            cash_and_equivalents=20.0,
            total_debt=0.0,
            revenue=10.0,
            gross_margin_pct=70.0,
            opex_rnd=35.0,  # 研发重度失血
            opex_sga=10.0,
            depr_amort=2.0,
            capex=3.0,
        )
        res = IntegratedThreeStatementEngine.simulate(base, revenue_growths=[0.10])

        self.assertLess(res.projections[0].free_cash_flow, 0.0)
        self.assertLess(res.runway_months, 12.0)
        self.assertIn("极高稀释风险", res.dilution_risk_level)
        self.assertIn("ATM Offering", res.verdict_zh)

    def test_ut_three_03_zero_or_negative_cash_emergency_defense(self):
        """【UT-THREE-03: 现金枯竭 (cash <= 0) 极端边界停摆倒计时断言】

        一、测试功能与测试点:
            验证金融数学除零除负与极端边界防御：当企业手头账面现金归零甚至为负（资不抵债严重透支）时，
            系统稳健运行，不崩溃抛错，且准确判定为“极度危急 (现金已枯竭，停摆倒计时)”，消除机械语病。

        二、正常函数业务边界与参数契约:
            - cash_and_equivalents <= 0.0

        三、测试数据与模拟场景说明:
            测试账面现金为 0.0 的濒临重组破产企业。

        四、预期断言与结果验证:
            断言 runway_months == 0.0。
            断言 dilution_risk_level 包含 "极度危急" 与 "现金已枯竭"。
            断言 verdict_zh 包含 "现金储备已彻底耗尽" 与 "清盘风险"。
        """
        base = BaselineFinancials(
            ticker="DYING_CO",
            cash_and_equivalents=0.0,  # 零现金
            total_debt=50.0,
            revenue=20.0,
            gross_margin_pct=30.0,
            opex_rnd=15.0,
            opex_sga=10.0,
            depr_amort=1.0,
            capex=2.0,
        )
        res = IntegratedThreeStatementEngine.simulate(base, revenue_growths=[0.05])

        self.assertEqual(res.runway_months, 0.0)
        self.assertIn("极度危急", res.dilution_risk_level)
        self.assertIn("现金储备已彻底耗尽", res.verdict_zh)
        self.assertIn("清盘风险", res.verdict_zh)

    def test_ut_three_04_positive_fcf_infinite_runway(self):
        """【UT-THREE-04: 正向自我造血企业无需融资与无稀释风险断言】

        一、测试功能与测试点:
            验证当企业首年自由现金流实现正向造血时 (FCF >= 0)，
            系统准确识别为盈利飞轮，判定为“无稀释风险 (已实现正向自我造血)”。

        二、正常函数业务边界与参数契约:
            - FCF > 0

        三、测试数据与模拟场景说明:
            稳健盈利现金牛企业。

        四、预期断言与结果验证:
            断言 runway_months >= 900.0 (无需融资)。
            断言 dilution_risk_level 包含 "无稀释风险"。
            断言 verdict_zh 包含 "自由现金流充沛" 与 "无任何断头台股权稀释风险"。
        """
        base = BaselineFinancials(
            ticker="CASH_COW",
            cash_and_equivalents=80.0,
            total_debt=20.0,
            revenue=200.0,
            gross_margin_pct=60.0,
            opex_rnd=20.0,
            opex_sga=30.0,
            depr_amort=10.0,
            capex=15.0,
        )
        res = IntegratedThreeStatementEngine.simulate(base, revenue_growths=[0.10])

        self.assertGreater(res.projections[0].free_cash_flow, 0.0)
        self.assertGreaterEqual(res.runway_months, 900.0)
        self.assertIn("无稀释风险", res.dilution_risk_level)
        self.assertIn("自由现金流充沛", res.verdict_zh)

    def test_ut_three_05_ample_runway_over_24m(self):
        """【UT-THREE-05: 充沛跑道 (>24个月) 安全直达远期断言】

        一、测试功能与测试点:
            验证即使处于研发投入期，但若账面现金极其充沛 (跑道 > 24 个月)，
            系统判定为流动性充沛，无需在估值低谷期贱卖股权。

        二、正常函数业务边界与参数契约:
            - runway_months > 24.0

        三、测试数据与模拟场景说明:
            手握 3 亿美元巨额融资现金的顶级生物科技独角兽。

        四、预期断言与结果验证:
            断言 runway_months > 24.0。
            断言 dilution_risk_level 包含 "流动性极其充沛"。
            断言 verdict_zh 包含 "直通远期数据读出期" 与 "无需在低估值时期贱卖股权"。
        """
        base = BaselineFinancials(
            ticker="WELL_FUNDED",
            cash_and_equivalents=300.0,  # 3亿现金
            total_debt=0.0,
            revenue=20.0,
            gross_margin_pct=60.0,
            opex_rnd=60.0,  # 每年净烧约 50M
            opex_sga=20.0,
            depr_amort=2.0,
            capex=5.0,
        )
        res = IntegratedThreeStatementEngine.simulate(base, revenue_growths=[0.15])

        self.assertGreater(res.runway_months, 24.0)
        self.assertIn("流动性极其充沛", res.dilution_risk_level)
        self.assertIn("无需在低估值时期贱卖股权", res.verdict_zh)

    def test_ut_three_06_facade_and_core_ssot_equivalence(self):
        """【UT-THREE-06: 向下兼容中继门面 SSOT 完全等价性断言】

        一、测试功能与测试点:
            验证 `finance_tools.integrated_three_statement_engine` 中继门面与底层核心
            `financial_core.engines.integrated_three_statement_engine` 计算输出 100% 相同。

        二、正常函数业务边界与参数契约:
            - Facade 与 Core 传入相同输入。

        三、测试数据与模拟场景说明:
            测试标准模拟场景。

        四、预期断言与结果验证:
            断言门面与核心输出属性完全一致。
        """
        base_core = BaselineFinancials(
            ticker="COMP_TEST",
            cash_and_equivalents=100.0,
            total_debt=20.0,
            revenue=150.0,
            gross_margin_pct=55.0,
            opex_rnd=30.0,
            opex_sga=25.0,
            depr_amort=8.0,
            capex=12.0,
        )
        base_facade = FacadeBaselineFinancials(
            ticker="COMP_TEST",
            cash_and_equivalents=100.0,
            total_debt=20.0,
            revenue=150.0,
            gross_margin_pct=55.0,
            opex_rnd=30.0,
            opex_sga=25.0,
            depr_amort=8.0,
            capex=12.0,
        )

        res_core = IntegratedThreeStatementEngine.simulate(base_core, [0.10, 0.08])
        res_facade = FacadeIntegratedThreeStatementEngine.simulate(base_facade, [0.10, 0.08])

        self.assertEqual(res_core.runway_months, res_facade.runway_months)
        self.assertEqual(res_core.dilution_risk_level, res_facade.dilution_risk_level)
        self.assertEqual(res_core.verdict_zh, res_facade.verdict_zh)

    def test_ut_three_07_buyer_dossier_card_and_to_dict_contract(self):
        """【UT-THREE-07: 动态三表联动买方全息研报卡片与 to_dict 序列化契约断言】

        一、测试功能与测试点:
            1. 验证 ThreeStatementSimulationResult 包含标准 narrative_zh 买方全息研报卡片；
            2. 验证 to_dict() 方法能够完整输出 narrative_zh，且与内部属性保持一致；
            3. 验证卡片通俗整合期初现金储备、现金跑道、季度净失血速率与买方破产融资压力研判。

        二、正常函数业务边界与参数契约:
            - simulate 返回合法 ThreeStatementSimulationResult

        三、测试数据与模拟场景说明:
            测试标准模拟场景。

        四、预期断言与结果验证:
            断言 narrative_zh 包含“【标的 COMP_TEST 动态三表联动与现金跑道全息研报】”；
            断言 to_dict() 字典包含 narrative_zh。
        """
        base = BaselineFinancials(
            ticker="COMP_TEST",
            cash_and_equivalents=100.0,
            total_debt=20.0,
            revenue=150.0,
            gross_margin_pct=55.0,
            opex_rnd=30.0,
            opex_sga=25.0,
            depr_amort=8.0,
            capex=12.0,
        )
        res = IntegratedThreeStatementEngine.simulate(base, [0.10])
        self.assertIn("动态三表联动与现金跑道全息研报", res.narrative_zh)
        self.assertIn("现金流与安全边界", res.narrative_zh)
        self.assertIn("买方破产与融资压力研判", res.narrative_zh)

        d = res.to_dict()
        self.assertIn("narrative_zh", d)
        self.assertEqual(d["narrative_zh"], res.narrative_zh)


if __name__ == "__main__":
    unittest.main()
