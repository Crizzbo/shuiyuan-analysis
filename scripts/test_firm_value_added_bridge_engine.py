"""中观行业至微观企业增加值映射桥梁引擎单元测试套件.

本测试模块严格遵循《36号工程黄金设计规范》与四段式结构化中文契约测试模型:
1. 测试功能与测试点说明 (Test Functionality & Objectives)
2. 正常函数业务边界与参数契约 (Business Boundaries & Parameter Contracts)
3. 测试数据与模拟场景说明 (Test Data & Scenario Descriptions)
4. 预期断言与结果验证 (Expected Assertions & Verification)

涵盖企业微观增加值生产法与分配法平账恒等式验证、宏观行业冲击与动态经营杠杆传导、
多情景两阶段内生收敛 DCF 估值走廊、默顿有限责任下界与清算残值防御、
纯中文自然语言研报卡片 (去工程符号化) 及向下兼容门面 SSOT 等价性断言。
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.firm_value_added_bridge_engine import (
    FirmFinancialFact,
    FirmValueAddedBridgeEngine,
)
from finance_tools.firm_value_added_bridge_engine import (
    FirmFinancialFact as FacadeFirmFinancialFact,
    FirmValueAddedBridgeEngine as FacadeFirmValueAddedBridgeEngine,
)


class TestFirmValueAddedBridgeEngine(unittest.TestCase):
    """企业增加值映射桥梁引擎契约与数值测试."""

    def setUp(self):
        self.engine = FirmValueAddedBridgeEngine()

    def test_ut_firm_va_01_corporate_value_added_production_and_distribution_identity(self):
        """【UT-FIRM-VA-01: 企业微观增加值分配法与生产法刚性平账恒等式断言】

        一、测试功能与测试点:
            验证 compute_firm_value_added 严格依据国民核算体系 (SNA 2008):
            1. 分配法核算增加值: VA = EBITDA + 劳动薪酬 + 税收；
            2. 生产法反推外购中间消耗: Intermediate = Revenue - VA；
            3. 要素切片收益总和为 100%；
            4. 买方全息研报卡片 narrative_zh 包含纯自然中文要素分配解读。

        二、正常函数业务边界与参数契约:
            - 输入财务底账营收、EBITDA、薪酬、税费均为非负实数；
            - 增加值率 value_added_ratio_pct 介于 0% 与 100% 之间。

        三、测试数据与模拟场景说明:
            测试典型先进制造与半导体标的 (以台积电为蓝本)。
            营收 $70,000M，营业成本 $32,000M，营运费用 $8,000M，
            EBITDA $42,000M，薪酬 $9,000M，税费 $5,000M，FCF $25,000M，市值 $550B。

        四、预期断言与结果验证:
            断言 VA = 42,000 + 9,000 + 5,000 = 56,000M。
            断言 外购中间消耗 = 70,000 - 56,000 = 14,000M。
            断言 要素切片分配恒等式成立。
            断言 narrative_zh 包含"企业增加值核算与要素分配全息研报"。
        """
        fact = FirmFinancialFact(
            ticker="TSM",
            company_name="台积电",
            market="US",
            sector_id="TECH_SEMI",
            revenue_million=70000.0,
            cogs_million=32000.0,
            operating_expenses_million=8000.0,
            ebitda_million=42000.0,
            wages_and_salaries_million=9000.0,
            taxes_paid_million=5000.0,
            capex_million=15000.0,
            annual_fcf_million=25000.0,
            market_cap_billion=550.0,
            country_id="US",
            foreign_revenue_ratio=0.85,
            fx_sensitivity_elasticity=0.40,
            inventory_turnover_days_dio=75.0,
        )

        res = self.engine.compute_firm_value_added(fact)

        expected_va = 42000.0 + 9000.0 + 5000.0
        self.assertEqual(res["corporate_value_added_million"], expected_va)
        self.assertEqual(res["intermediate_purchases_million"], 70000.0 - expected_va)
        self.assertTrue(res["factor_distribution"]["is_distribution_identity_held"])
        self.assertAlmostEqual(
            res["factor_distribution"]["labor_share_pct"]
            + res["factor_distribution"]["capital_share_pct"]
            + res["factor_distribution"]["tax_share_pct"],
            100.0,
            places=1,
        )
        self.assertIn("企业增加值核算与要素分配全息研报", res["narrative_zh"])
        self.assertIn("真实企业创造增加值", res["narrative_zh"])

    def test_ut_firm_va_02_macro_sector_shock_and_dol_transmission(self):
        """【UT-FIRM-VA-02: 宏观行业冲击向企业微观业绩传导与动态经营杠杆断言】

        一、测试功能与测试点:
            验证 map_sector_shock_to_firm 能够模拟行业内需增加值扩张、海外出口外需拉动、
            汇率贬值计价收益对企业综合增速的加权放大，并驱动动态经营杠杆 (DOL)。
            验证微观分配法平账恒等式在冲击后刚性闭环成立 (is_distribution_identity_held == True)。

        二、正常函数业务边界与参数契约:
            - sector_va_growth_pct 传入行业增加值增速 (如 +8.0%)；
            - firm_pricing_power_mu 传入加价率乘数 (如 1.25 代表超额定价权)。

        三、测试数据与模拟场景说明:
            测试半导体繁荣周期上行冲击。

        四、预期断言与结果验证:
            断言 effective_firm_growth_pct > 8.0%。
            断言 operating_leverage_dol > 1.0。
            断言 is_distribution_identity_held 为 True。
            断言 narrative_zh 包含"宏观行业冲击与企业微观业绩映射全息研报"。
        """
        fact = FirmFinancialFact(
            ticker="NVDA",
            company_name="英伟达",
            market="US",
            sector_id="TECH_SEMI",
            revenue_million=60000.0,
            cogs_million=15000.0,
            operating_expenses_million=10000.0,
            ebitda_million=38000.0,
            wages_and_salaries_million=6000.0,
            taxes_paid_million=4000.0,
            capex_million=3000.0,
            annual_fcf_million=32000.0,
            market_cap_billion=2500.0,
            country_id="US",
            foreign_revenue_ratio=0.60,
            fx_sensitivity_elasticity=0.20,
            inventory_turnover_days_dio=50.0,
        )

        shock_res = self.engine.map_sector_shock_to_firm(
            firm=fact,
            sector_va_growth_pct=10.0,
            firm_pricing_power_mu=1.20,
            export_demand_growth_pct=15.0,
            fx_shock_multiplier=1.05,
        )

        self.assertGreater(shock_res["effective_firm_growth_pct"], 10.0)
        self.assertGreater(shock_res["operating_leverage_dol"], 1.0)
        self.assertTrue(shock_res["is_distribution_identity_held"])
        self.assertLessEqual(shock_res["identity_discrepancy_million"], 0.05)
        self.assertIn("宏观行业冲击与企业微观业绩映射全息研报", shock_res["narrative_zh"])
        self.assertIn("经营杠杆 DOL=", shock_res["narrative_zh"])

    def test_ut_firm_va_03_intrinsic_valuation_two_stage_dcf_and_buyer_narrative(self):
        """【UT-FIRM-VA-03: 两阶段收敛DCF公允内在价值与买方研报纯中文定性断言】

        一、测试功能与测试点:
            验证 compute_firm_intrinsic_valuation 计算微观企业内生公允价值：
            1. 覆盖单阶段戈登基准与两阶段有限生命收敛 DCF；
            2. 输出悲观防御底价、公允中枢与乐观弹性靶心价值走廊；
            3. 达摩达兰资本内生增长检验 (implied_roic_pct 与 capital_status)；
            4. 验证 institutional_verdict 与 recommended_action 彻底消除纯英文代号；
            5. 验证 narrative_zh 买方研报卡片完整组装且通俗自然。

        二、正常函数业务边界与参数契约:
            - 针对造血强劲标的 (FCF > 0)，折现公允价值为正，估值缺口计算精确。

        三、测试数据与模拟场景说明:
            测试深度低估成长标的。

        四、预期断言与结果验证:
            断言 two_stage_fair_value_billion > 0。
            断言 capital_status 属于纯自然中文 ("内生资本增长良性可行")。
            断言 institutional_verdict 与 recommended_action 不含任何英文括号代号。
            断言 narrative_zh 包含"微观内在价值与多情景折现全息研报"。
        """
        fact = FirmFinancialFact(
            ticker="VALUE_GROWTH",
            company_name="价值成长标的",
            market="US",
            sector_id="TECH_SOFTWARE",
            revenue_million=10000.0,
            cogs_million=2500.0,
            operating_expenses_million=3500.0,
            ebitda_million=4000.0,
            wages_and_salaries_million=2000.0,
            taxes_paid_million=500.0,
            capex_million=500.0,
            annual_fcf_million=3000.0,
            market_cap_billion=30.0,
            country_id="US",
            foreign_revenue_ratio=0.30,
            cash_and_equivalents_million=5000.0,
            total_debt_million=1000.0,
            interest_expense_million=50.0,
            tangible_book_value_million=8000.0,
        )

        val = self.engine.compute_firm_intrinsic_valuation(
            firm=fact,
            sector_wacc=0.08,
            terminal_growth_rate=0.03,
            stage1_years=5,
        )

        self.assertGreater(val["two_stage_valuation"]["two_stage_fair_value_billion"], 0.0)
        self.assertGreater(val["optimistic_target_value_billion"], val["fair_intrinsic_value_billion"])
        self.assertGreater(val["fair_intrinsic_value_billion"], val["pessimistic_floor_value_billion"])

        # 检查去工程符号化与消除英文代号
        cap_status = val["endogenous_capital_consistency"]["capital_status"]
        self.assertIn("内生资本增长良性可行", cap_status)
        self.assertNotIn("Economically Feasible", cap_status)

        verdict = val["institutional_verdict"]
        action = val["recommended_action"]
        self.assertNotIn("Buy / Accumulate", action)
        self.assertNotIn("Batting Zone", verdict)
        self.assertIn("深度低估最佳击球区", verdict)

        # 检查买方全息研报卡片
        self.assertIn("narrative_zh", val)
        self.assertIn("微观内在价值与多情景折现全息研报", val["narrative_zh"])
        self.assertIn("买方机构终局研判", val["narrative_zh"])
        self.assertNotIn("(", val["narrative_zh"].split("买方机构终局研判")[1])

    def test_ut_firm_va_04_distressed_zombie_and_merton_liquidation_floor_defense(self):
        """【UT-FIRM-VA-04: 严重失血困境标的有限责任下界与僵尸企业预警断言】

        一、测试功能与测试点:
            验证当标的自由现金流持续失血 (FCF < 0)、利息支出无法覆盖 (ICR < 1.0) 时：
            1. 触发默顿有限责任下界防御 (Merton Limited Liability Floor)，权益折现不出现荒谬负值；
            2. 正确测算现金失血跑道月数 (cash_burn_runway_months)；
            3. 正确发出纯自然中文高危财务警报，剔除出投资池。

        二、正常函数业务边界与参数契约:
            - annual_fcf_million < 0；
            - interest_coverage_ratio < 1.0。

        三、测试数据与模拟场景说明:
            测试失血型严重负债僵尸企业。

        四、预期断言与结果验证:
            断言 fair_intrinsic_value_billion >= 0 (有限责任下界非负)。
            断言 is_zombie_firm 为 True。
            断言 institutional_verdict 包含纯中文"破产重组风险"或"高危财务预警"。
            断言 narrative_zh 包含失血跑道描述。
        """
        fact = FirmFinancialFact(
            ticker="BLEEDING_ZOMBIE",
            company_name="失血僵尸标的",
            market="US",
            sector_id="CONSUMER_RETAIL",
            revenue_million=2000.0,
            cogs_million=1800.0,
            operating_expenses_million=500.0,
            ebitda_million=-300.0,
            wages_and_salaries_million=300.0,
            taxes_paid_million=0.0,
            capex_million=100.0,
            annual_fcf_million=-400.0,
            market_cap_billion=0.5,
            country_id="US",
            cash_and_equivalents_million=100.0,
            total_debt_million=800.0,
            interest_expense_million=60.0,
            tangible_book_value_million=-200.0,
        )

        val = self.engine.compute_firm_intrinsic_valuation(firm=fact)

        self.assertGreaterEqual(val["fair_intrinsic_value_billion"], 0.0)
        self.assertGreaterEqual(val["two_stage_valuation"]["two_stage_fair_value_billion"], 0.0)
        self.assertTrue(val["financial_distress_diagnostics"]["is_zombie_firm"])
        self.assertIsNotNone(val["financial_distress_diagnostics"]["cash_burn_runway_months"])
        self.assertLess(val["financial_distress_diagnostics"]["cash_burn_runway_months"], 12.0)

        verdict = val["institutional_verdict"]
        self.assertNotIn("Insolvency Crisis", verdict)
        self.assertNotIn("Zombie Debt Wall", verdict)
        self.assertIn("风险", verdict)
        self.assertIn("失血跑道仅剩", val["narrative_zh"])

    def test_ut_firm_va_05_facade_and_core_ssot_equivalence(self):
        """【UT-FIRM-VA-05: 增加值映射桥梁门面与底层核心 SSOT 完全等价性断言】

        一、测试功能与测试点:
            验证 `finance_tools.firm_value_added_bridge_engine` 门面与
            `financial_core.engines.firm_value_added_bridge_engine` 核心计算结果完全一致。

        二、预期断言与结果验证:
            断言增加值核算与多情景估值输出字典 100% 相同。
        """
        fact_core = FirmFinancialFact(
            ticker="EQUIV",
            company_name="等价标的",
            market="US",
            sector_id="TECH_SEMI",
            revenue_million=50000.0,
            cogs_million=20000.0,
            operating_expenses_million=5000.0,
            ebitda_million=25000.0,
            wages_and_salaries_million=5000.0,
            taxes_paid_million=3000.0,
            capex_million=7000.0,
            annual_fcf_million=15000.0,
            market_cap_billion=400.0,
        )
        fact_facade = FacadeFirmFinancialFact(
            ticker="EQUIV",
            company_name="等价标的",
            market="US",
            sector_id="TECH_SEMI",
            revenue_million=50000.0,
            cogs_million=20000.0,
            operating_expenses_million=5000.0,
            ebitda_million=25000.0,
            wages_and_salaries_million=5000.0,
            taxes_paid_million=3000.0,
            capex_million=7000.0,
            annual_fcf_million=15000.0,
            market_cap_billion=400.0,
        )

        core_engine = FirmValueAddedBridgeEngine()
        facade_engine = FacadeFirmValueAddedBridgeEngine()

        va_core = core_engine.compute_firm_value_added(fact_core)
        va_facade = facade_engine.compute_firm_value_added(fact_facade)
        self.assertEqual(va_core, va_facade)

        val_core = core_engine.compute_firm_intrinsic_valuation(fact_core)
        val_facade = facade_engine.compute_firm_intrinsic_valuation(fact_facade)
        self.assertEqual(val_core, val_facade)

    def test_ut_firm_va_06_cross_market_currency_adaptation(self):
        """【UT-FIRM-VA-06: 跨市场多币种自适应推导与日股/A股研报货币符号断言】

        一、测试功能与测试点:
            1. 验证传入日股标的 (如 6758.T, market="JP") 时，自动推导货币符号为 '¥'；
            2. 验证 compute_firm_value_added、simulate_macro_to_firm_value_added 与
               compute_firm_intrinsic_valuation 的研报卡片 narrative_zh 中均使用 '¥'，严禁死锁 '$'；
            3. 验证返回字典中包含 "currency_symbol": "¥"。

        二、正常函数业务边界与参数契约:
            - ticker: "6758.T"
            - market: "JP"

        三、测试数据与模拟场景说明:
            测试日股索尼公司增加值核算与估值场景。

        四、预期断言与结果验证:
            断言 currency_symbol == "¥"，narrative_zh 中包含 "¥" 且无 "$" 符号。
        """
        fact_jp = FirmFinancialFact(
            ticker="6758.T",
            company_name="索尼集团",
            market="JP",
            sector_id="TECH_HARDWARE",
            revenue_million=13000000.0,
            cogs_million=9000000.0,
            operating_expenses_million=2500000.0,
            ebitda_million=1800000.0,
            wages_and_salaries_million=1200000.0,
            taxes_paid_million=300000.0,
            capex_million=600000.0,
            annual_fcf_million=900000.0,
            market_cap_billion=18000.0,
            country_id="JP",
            cash_and_equivalents_million=1500000.0,
            total_debt_million=1200000.0,
            interest_expense_million=20000.0,
            tangible_book_value_million=6000000.0,
        )

        # 1. 增加值核算
        va_res = self.engine.compute_firm_value_added(fact_jp)
        self.assertEqual(va_res["currency_symbol"], "¥")
        self.assertIn("¥", va_res["narrative_zh"])
        self.assertNotIn("$", va_res["narrative_zh"])

        # 2. 宏观冲击模拟
        sim_res = self.engine.map_sector_shock_to_firm(
            firm=fact_jp,
            sector_va_growth_pct=5.0,
            firm_pricing_power_mu=1.20,
            export_demand_growth_pct=3.0,
        )
        self.assertEqual(sim_res["currency_symbol"], "¥")
        self.assertIn("¥", sim_res["narrative_zh"])
        self.assertNotIn("$", sim_res["narrative_zh"])

        # 3. 估值研报
        val_res = self.engine.compute_firm_intrinsic_valuation(fact_jp)
        self.assertEqual(val_res["currency_symbol"], "¥")
        self.assertIn("¥", val_res["narrative_zh"])
        self.assertNotIn("$", val_res["narrative_zh"])


if __name__ == "__main__":
    unittest.main()
