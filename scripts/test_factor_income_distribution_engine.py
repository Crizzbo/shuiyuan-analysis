"""要素收入分配与居民个人部门传导引擎单元测试套件.

本测试模块严格遵循《36号工程黄金设计规范》与四段式结构化中文契约测试模型:
1. 测试功能与测试点说明 (Test Functionality & Objectives)
2. 正常函数业务边界与参数契约 (Business Boundaries & Parameter Contracts)
3. 测试数据与模拟场景说明 (Test Data & Scenario Descriptions)
4. 预期断言与结果验证 (Expected Assertions & Verification)

涵盖要素穿透分配、居民消费与储蓄决策、宏观行星闭环吸收 (C+I+G==Y) 及跨市场多币种自适应断言。
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.factor_income_distribution_engine import (
    FactorIncomeDistributionEngine,
)


class TestFactorIncomeDistributionEngine(unittest.TestCase):
    """要素收入分配与居民传导引擎测试."""

    def setUp(self):
        self.engine = FactorIncomeDistributionEngine()

    def test_ut_factor_01_household_income_and_absorption(self):
        """【UT-FACTOR-01: 宏观增加值向居民部门穿透与可支配收入测算断言】

        一、测试功能与测试点:
            验证将宏观 GDP 增加值穿透分解为劳动者报酬、资本回报分配 (分红、回购与利息)
            以及个人所得税扣除，准确得出居民净可支配收入与人均年薪。

        二、正常函数业务边界与参数契约:
            - world_gdp_trillion: 105.0 (万亿美元)
            - labor_compensation_trillion: 55.0
            - capital_operating_surplus_trillion: 35.0
            - net_taxes_trillion: 15.0
            - labor_force_billion: 3.5 (十亿人)

        三、测试数据与模拟场景说明:
            测试标准全球宏观要素收入分配基准场景。

        四、预期断言与结果验证:
            断言可支配收入 > 0，人均年薪落在正常经济区间 ($10,000 ~ $25,000)。
        """
        res = self.engine.compute_household_distribution(
            world_gdp_trillion=105.0,
            labor_compensation_trillion=55.0,
            capital_operating_surplus_trillion=35.0,
            net_taxes_trillion=15.0,
            labor_force_billion=3.5,
            mpc=0.75,
            capital_payout_ratio=0.55,
        )

        income = res["household_income_breakdown"]
        self.assertGreater(income["net_disposable_income_trillion"], 50.0)
        self.assertGreater(res["per_capita_metrics"]["average_annual_wage_usd"], 10000.0)
        self.assertLess(res["per_capita_metrics"]["average_annual_wage_usd"], 25000.0)

    def test_ut_factor_02_mpc_savings_and_investment_closure(self):
        """【UT-FACTOR-02: 边际消费倾向与储蓄转化为固定资产投资 (S->I) 断言】

        一、测试功能与测试点:
            验证依据边际消费倾向 MPC 测算最终消费支出与储蓄，
            并经由金融中介转化率准确推导实体资本形成 I。

        二、正常函数业务边界与参数契约:
            - mpc: 0.70 -> 储蓄率: 30%

        三、测试数据与模拟场景说明:
            测试居民部门高储蓄倾向下资本积累传导。

        四、预期断言与结果验证:
            断言储蓄率等于 30.0%，资本形成总额大于 0。
        """
        res = self.engine.compute_household_distribution(
            world_gdp_trillion=100.0,
            labor_compensation_trillion=50.0,
            capital_operating_surplus_trillion=35.0,
            net_taxes_trillion=15.0,
            mpc=0.70,
        )

        abs_data = res["household_absorption_behavior"]
        self.assertEqual(abs_data["savings_rate_pct"], 30.0)
        self.assertGreater(res["financial_intermediation_and_investment"]["gross_capital_formation_i_trillion"], 10.0)

    def test_ut_factor_03_strict_planetary_absorption_closure(self):
        """【UT-FACTOR-03: 行星尺度内生宏观吸收 (C + I + G == Y) 严格平账闭环断言】

        一、测试功能与测试点:
            验证在行星封闭体系中，最终消费 C + 严格资本形成 I + 政府支出 G 与全球 GDP 严格恒等平账。

        二、正常函数业务边界与参数契约:
            - strict_total_absorption_c_plus_i_plus_g_trillion == world_gdp_trillion

        三、预期断言与结果验证:
            断言 is_strict_planetary_absorption_balanced 为 True，平账误差小于 1e-3。
        """
        res = self.engine.compute_household_distribution(
            world_gdp_trillion=110.0,
            labor_compensation_trillion=58.0,
            capital_operating_surplus_trillion=36.0,
            net_taxes_trillion=16.0,
        )

        strict = res["financial_intermediation_and_investment"]["strict_macro_closure"]
        self.assertTrue(strict["is_strict_planetary_absorption_balanced"])
        self.assertAlmostEqual(strict["strict_total_absorption_c_plus_i_plus_g_trillion"], 110.0, places=2)

    def test_ut_factor_04_buyer_narrative_and_contract(self):
        """【UT-FACTOR-04: 买方全息研报卡片与去工程符号化契约断言】

        一、测试功能与测试点:
            验证 narrative_zh 包含宏观总产出、要素分配穿透、居民消费与行星闭环等核心研判；
            验证消除工程代码暴露。

        二、预期断言与结果验证:
            断言 narrative_zh 包含“【全球要素收入分配与居民消费循环流转全息研报】”。
        """
        res = self.engine.compute_household_distribution(
            world_gdp_trillion=100.0,
            labor_compensation_trillion=50.0,
            capital_operating_surplus_trillion=35.0,
            net_taxes_trillion=15.0,
        )
        self.assertIn("全球要素收入分配与居民消费循环流转全息研报", res["narrative_zh"])
        self.assertIn("要素分配穿透", res["narrative_zh"])
        self.assertIn("实体投资与吸收平账", res["narrative_zh"])

    def test_ut_factor_05_cross_market_currency_adaptation(self):
        """【UT-FACTOR-05: 跨市场多币种自适应推导与研报货币符号断言】

        一、测试功能与测试点:
            验证当传入 market='JP' 或显式指定 currency_symbol='¥' 时：
            1. currency_symbol 输出为 '¥'；
            2. 研报 narrative_zh 中人均薪酬使用 '¥' 呈现，无死锁 '$'。

        二、预期断言与结果验证:
            断言 currency_symbol == '¥'，narrative_zh 包含 '¥' 且无 '$'。
        """
        res_jp = self.engine.compute_household_distribution(
            world_gdp_trillion=100.0,
            labor_compensation_trillion=50.0,
            capital_operating_surplus_trillion=35.0,
            net_taxes_trillion=15.0,
            market="JP",
        )
        self.assertEqual(res_jp["currency_symbol"], "¥")
        self.assertIn("¥", res_jp["narrative_zh"])
        self.assertNotIn("$", res_jp["narrative_zh"])


if __name__ == "__main__":
    unittest.main()
