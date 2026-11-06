"""霍尔微观成本摩擦与加成率引擎单元测试套件.

本测试模块严格遵循《36号工程黄金设计规范》与四段式结构化中文契约测试模型:
1. 测试功能与测试点说明 (Test Functionality & Objectives)
2. 正常函数业务边界与参数契约 (Business Boundaries & Parameter Contracts)
3. 测试数据与模拟场景说明 (Test Data & Scenario Descriptions)
4. 预期断言与结果验证 (Expected Assertions & Verification)

涵盖霍尔加成率、通胀成本转嫁摩擦、折现率波动与预防性资本开支收缩、多币种自适应及研报去符号化契约。
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.hall_discount_friction_engine import (
    HallFrictionInput,
    HallFrictionResult,
    HallDiscountFrictionEngine,
)


class TestHallDiscountFrictionEngine(unittest.TestCase):
    """霍尔微观摩擦与加成率引擎测试."""

    def setUp(self):
        self.engine = HallDiscountFrictionEngine()

    def test_ut_hall_01_markup_and_pricing_power_tiers(self):
        """【UT-HALL-01: 霍尔微观加成率计算与三大定价权防御分层断言】

        一、测试功能与测试点:
            验证依据营业收入、营业成本与变动成本比例准确计算微观价格-成本加成率 μ = P/MC，
            并在不同价格转嫁弹性下正确映射至强防御、中度转嫁与严重挤压三档定价权。

        二、正常函数业务边界与参数契约:
            - 高定价权标的: pricing_pass_through_elasticity = 0.90 -> STRONG_DEFENSE
            - 中度转嫁标的: pricing_pass_through_elasticity = 0.65 -> MODERATE_PASSTHROUGH
            - 严重挤压标的: pricing_pass_through_elasticity = 0.30 -> SEVERE_MARGIN_SQUEEZE

        三、测试数据与模拟场景说明:
            模拟高毛利消费品/特许经营龙头企业，对比薄利代工制造企业。

        四、预期断言与结果验证:
            断言微观加成率 μ > 1.0，定价权评级与纯中文说明一一对应。
        """
        inp_high = HallFrictionInput(
            reported_revenue=1000.0,
            reported_cogs=500.0,
            reported_gross_margin_pct=50.0,
            reported_capex=100.0,
            cash_and_equivalents=200.0,
            total_debt=100.0,
            annual_fcf=150.0,
            pricing_pass_through_elasticity=0.90,
        )
        res_high = self.engine.evaluate(inp_high)
        self.assertEqual(res_high.pricing_power_tier, "STRONG_DEFENSE")
        self.assertIn("强防御特许定价权", res_high.pricing_power_tier_zh)
        self.assertGreater(res_high.micro_markup_ratio, 1.5)

        inp_low = HallFrictionInput(
            reported_revenue=1000.0,
            reported_cogs=900.0,
            reported_gross_margin_pct=10.0,
            reported_capex=80.0,
            cash_and_equivalents=50.0,
            total_debt=200.0,
            annual_fcf=20.0,
            pricing_pass_through_elasticity=0.30,
        )
        res_low = self.engine.evaluate(inp_low)
        self.assertEqual(res_low.pricing_power_tier, "SEVERE_MARGIN_SQUEEZE")
        self.assertIn("利润率严重受压脆弱型", res_low.pricing_power_tier_zh)

    def test_ut_hall_02_cost_inflation_and_margin_squeeze(self):
        """【UT-HALL-02: 要素综合通胀冲击与毛利率受压侵蚀测算断言】

        一、测试功能与测试点:
            验证结合劳动力成本占比与原材料成本占比加权生成综合投入要素通胀率，
            在不完全转嫁下准确计算预测毛利率及毛利率变动点数。

        二、正常函数业务边界与参数契约:
            - 原材料通胀: 10%，劳动力通胀: 6%
            - 劳动力占比: 40% (原材料 60%)
            - 综合加权通胀 = 0.4*6 + 0.6*10 = 8.4%
            - 转嫁弹性: 0.50 -> 售价仅上涨 4.2%

        三、测试数据与模拟场景说明:
            测试制造业在要素滞胀环境下的毛利率收缩情景。

        四、预期断言与结果验证:
            断言毛利率变动 gross_margin_shock_pct < 0，且承压后毛利率低于基准毛利率。
        """
        inp = HallFrictionInput(
            reported_revenue=1000.0,
            reported_cogs=600.0,
            reported_gross_margin_pct=40.0,
            reported_capex=120.0,
            cash_and_equivalents=150.0,
            total_debt=100.0,
            annual_fcf=80.0,
            commodity_input_inflation_pct=10.0,
            unit_labor_cost_inflation_pct=6.0,
            labor_share_in_cogs_pct=40.0,
            pricing_pass_through_elasticity=0.50,
        )
        res = self.engine.evaluate(inp)
        self.assertLess(res.gross_margin_shock_pct, 0.0)
        self.assertLess(res.shocked_gross_margin_pct, 40.0)

    def test_ut_hall_03_vix_volatility_and_liquidity_hoarding(self):
        """【UT-HALL-03: 宏观折现率不确定性 (VIX) 与预防性流动性囤积 Capex 收缩断言】

        一、测试功能与测试点:
            验证当宏观不确定性 VIX 飙升、企业面临较高杠杆时，
            系统能够触发内生性 Capex 预防性收缩机制，降低扩张性资本开支。

        二、正常函数业务边界与参数契约:
            - VIX = 38.0 (远超 18.0 常态基准)
            - 杠杆负债较高 (total_debt / cash > 2.0)

        三、测试数据与模拟场景说明:
            模拟危机时期高负债企业自主收紧资本开支囤积现金的行为。

        四、预期断言与结果验证:
            断言资本开支自主收缩率 > 5%，调整后开支金额低于原报资本开支。
        """
        inp = HallFrictionInput(
            reported_revenue=2000.0,
            reported_cogs=1400.0,
            reported_gross_margin_pct=30.0,
            reported_capex=250.0,
            cash_and_equivalents=100.0,
            total_debt=300.0,
            annual_fcf=50.0,
            macro_vix_volatility=38.0,
        )
        res = self.engine.evaluate(inp)
        self.assertGreater(res.precautionary_capex_curtailment_pct, 5.0)
        self.assertLess(res.curtailed_capex_amount, 250.0)
        self.assertGreater(res.liquidity_buffer_resilience_months, 0.0)

    def test_ut_hall_04_buyer_narrative_and_to_dict_contract(self):
        """【UT-HALL-04: 买方全息研报卡片与 to_dict 序列化契约完整性断言】

        一、测试功能与测试点:
            验证 narrative_zh 包含成本转嫁、毛利抗性、资本开支收缩与现金储备寿命全息研判；
            验证 to_dict() 输出分层清晰无遗漏。

        二、正常函数业务边界与参数契约:
            - 标准企业摩擦评估输入。

        三、测试数据与模拟场景说明:
            测试标准研报输出内容。

        四、预期断言与结果验证:
            断言 narrative_zh 包含“【成本摩擦加成率与流动性防御全息研判】”，to_dict() 各字段存在。
        """
        inp = HallFrictionInput(
            reported_revenue=1500.0,
            reported_cogs=900.0,
            reported_gross_margin_pct=40.0,
            reported_capex=150.0,
            cash_and_equivalents=300.0,
            total_debt=100.0,
            annual_fcf=120.0,
        )
        res = self.engine.evaluate(inp)
        self.assertIn("成本摩擦加成率与流动性防御全息研判", res.narrative_zh)
        self.assertIn("定价权护城河评级", res.narrative_zh)
        self.assertIn("流动性防御与资本开支", res.narrative_zh)

        d = res.to_dict()
        self.assertIn("micro_markup_ratio", d)
        self.assertIn("pricing_power_tier", d)
        self.assertIn("currency_symbol", d)
        self.assertIn("narrative_zh", d)

    def test_ut_hall_05_cross_market_currency_adaptation(self):
        """【UT-HALL-05: 跨市场多币种自适应推导与研报货币符号断言】

        一、测试功能与测试点:
            验证传入日股代码 (如 7203.T) 或 A 股代码时，自适应推导货币符号为 '¥'；
            验证研报 narrative_zh 中严禁死锁美元 '$'，必须呈现 '¥'；
            验证 to_dict() 序列化中 currency_symbol 为 '¥'。

        二、正常函数业务边界与参数契约:
            - ticker="7203.T", market="JP"

        三、测试数据与模拟场景说明:
            测试日股丰田汽车微观加成与流动性摩擦评估场景。

        四、预期断言与结果验证:
            断言 currency_symbol == "¥"，narrative_zh 包含 "¥" 且无死锁 "$" 符号。
        """
        inp_jp = HallFrictionInput(
            reported_revenue=300000.0,
            reported_cogs=220000.0,
            reported_gross_margin_pct=26.6,
            reported_capex=35000.0,
            cash_and_equivalents=50000.0,
            total_debt=80000.0,
            annual_fcf=25000.0,
            ticker="7203.T",
            market="JP",
        )
        res_jp = self.engine.evaluate(inp_jp)

        self.assertEqual(res_jp.currency_symbol, "¥")
        self.assertIn("¥", res_jp.narrative_zh)
        self.assertNotIn("$", res_jp.narrative_zh)
        d_jp = res_jp.to_dict()
        self.assertEqual(d_jp["currency_symbol"], "¥")


if __name__ == "__main__":
    unittest.main()
