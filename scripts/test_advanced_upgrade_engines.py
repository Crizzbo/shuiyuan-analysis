"""美式期权二叉树与宏观传导引擎单元测试套件 (Advanced Upgrade Engines Tests).

验证针对系统弱项 3 (跨市场宏观冲击) 与弱项 4 (美式期权提前行权与跳跃扩散) 的量化升级能力.
"""

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from finance_tools.american_option_tree_engine import (
    AmericanOptionTreeInput,
    AmericanOptionTreeEngine,
)
from finance_tools.macro_shock_transmission_engine import (
    MacroShockInput,
    MacroShockTransmissionEngine,
)


class TestAdvancedUpgradeEngines(unittest.TestCase):
    """测试二叉树与宏观冲击高级引擎."""

    def setUp(self):
        self.tree_engine = AmericanOptionTreeEngine()
        self.macro_engine = MacroShockTransmissionEngine()

    def test_american_put_early_exercise(self):
        """【UT-UPGRADE-01: 深度实值美式看跌期权提前行权溢价(CRR二叉树对决欧式BSM)】

        1. 测试功能与测试点:
           - 验证 AmericanOptionTreeEngine.price_crr_tree 针对深度实值美式看跌期权 (Deep In-the-Money American Put) 的提前行权判定。
           - 严格断言美式期权价格必然高于欧式 BSM 解析解价格，提前行权溢价 (early_exercise_premium) > 0。

        2. 正常函数业务边界与参数契约:
           - spot_price, strike_price, time_to_expiry_years, risk_free_rate, implied_vol > 0。
           - is_call=False, steps >= 50。

        3. 测试数据与模拟场景说明:
           - 现价 $30，行权价 $50 (内在价值 $20)，无风险利率 5%，隐含波动率 30%，期限 1.0 年，二叉树 150 步。

        4. 预期断言与结果验证:
           - early_exercise_occurred 为 True。
           - american_price > european_price。
           - early_exercise_premium > 0.0。
        """
        # 深度实值 Put: 现价 $30, 行权价 $50, 利率 5%, 波动率 30%, 1年到期
        params = AmericanOptionTreeInput(
            spot_price=30.0,
            strike_price=50.0,
            time_to_expiry_years=1.0,
            risk_free_rate=0.05,
            implied_vol=0.30,
            dividend_yield=0.0,
            is_call=False,
            steps=150,
        )
        res = self.tree_engine.price_crr_tree(params)
        self.assertTrue(res["early_exercise_occurred"])
        self.assertGreater(res["american_price"], res["european_price"])
        self.assertGreater(res["early_exercise_premium"], 0.0)

    def test_merton_jump_diffusion_call(self):
        """【UT-UPGRADE-02: Merton跳跃扩散模型极端负向跳跃厚尾非线性调整】

        1. 测试功能与测试点:
           - 验证 AmericanOptionTreeEngine.price_crr_tree 针对 Merton 跳跃扩散 (Jump-Diffusion) 的非线性厚尾校准。
           - 引入泊松跳跃强度 (jump_intensity)、负向跳跃均值 (mean_jump_size) 与跳跃波动率 (jump_vol)，防止低估尾部风险。

        2. 正常函数业务边界与参数契约:
           - jump_intensity > 0, jump_vol > 0。
           - 返回包含 jump_adjusted_price 强类型字段。

        3. 测试数据与模拟场景说明:
           - 平值看涨期权: 现价 $100，行权价 $100，期限 0.5 年，利率 4%，波动率 25%，年化跳跃强度 1.5 次，跳跃均值 -15%，跳跃波动率 20%。

        4. 预期断言与结果验证:
           - jump_adjusted_price > 0.0。
        """
        params = AmericanOptionTreeInput(
            spot_price=100.0,
            strike_price=100.0,
            time_to_expiry_years=0.5,
            risk_free_rate=0.04,
            implied_vol=0.25,
            is_call=True,
            steps=100,
            jump_intensity=1.5,
            mean_jump_size=-0.15,
            jump_vol=0.20,
        )
        res = self.tree_engine.price_crr_tree(params)
        self.assertGreater(res["jump_adjusted_price"], 0.0)

    def test_macro_carry_trade_unwind_trigger(self):
        """【UT-UPGRADE-03: 日元暴力套息平仓与VIX飙升流动性收缩宏观冲击传导】

        1. 测试功能与测试点:
           - 验证 MacroShockTransmissionEngine.evaluate_macro_shock 对跨市场宏观挤兑冲击的量化传导。
           - 日元单日大涨 (-2.5%) 叠加恐慌指数 VIX 冲高至 28，触发套息交易平仓去杠杆警报 (carry_trade_unwind_active)。
           - 验证流动性挤兑下资产相关性非线性趋同 (>0.70) 与企业 WACC 风险溢价惩罚。

        2. 正常函数业务边界与参数契约:
           - 输入包含美债收益率、美日汇率变动、VIX 及企业 Beta 与资产负债率。
           - 输出 shocked_wacc_pct, valuation_haircut_pct 等。

        3. 测试数据与模拟场景说明:
           - 美债 10Y 收益率 4.5%，USDJPY 149.5，VIX 28.0，日元单日变动 -2.5% (升值)，美联储流动性抽离 600 亿，企业 Beta 1.4，杠杆率 1.6，基准 WACC 9.0%。

        4. 预期断言与结果验证:
           - carry_trade_unwind_active 为 True。
           - carry_trade_stress_score > 60.0。
           - converged_market_correlation > 0.70。
           - shocked_wacc_pct > base_wacc_pct。
           - valuation_haircut_pct > 10.0%。
        """
        params = MacroShockInput(
            us_10y_yield=0.045,
            usdjpy_rate=149.5,
            vix_index=28.0,
            usdjpy_daily_change_pct=-0.025,
            fed_liquidity_drain_billion=60.0,
            company_beta=1.4,
            company_debt_to_equity=1.6,
            base_wacc=0.09,
        )
        res = self.macro_engine.evaluate_macro_shock(params)
        self.assertTrue(res["carry_trade_unwind_active"])
        self.assertGreater(res["carry_trade_stress_score"], 60.0)
        # 危机时刻跨资产相关性应收敛到 0.70 以上
        self.assertGreater(res["converged_market_correlation"], 0.70)
        # WACC 应该受到明显的利差加压
        self.assertGreater(res["shocked_wacc_pct"], res["base_wacc_pct"])
        self.assertGreater(res["valuation_haircut_pct"], 10.0)

    def test_merton_jump_extreme_negative_defense_and_arbitrage_bound(self):
        """【UT-UPGRADE-04: 极端跌幅(mean_jump <= -1.0)数学域防御与美式行权溢价无套利保留】

        1. 测试功能与测试点:
           - 验证当跳跃幅度 mean_jump_size <= -1.0 时，引擎不触发 ValueError: math domain error。
           - 验证 safe_jump = max(-0.99, min(5.0, mean_jump)) 金融工程下界防御生效。
           - 验证深度实值美式看跌期权在开启跳跃扩散后，调整价格不得低于其行权内在价值 (Intrinsic Value)，坚守无套利铁律。

        2. 正常函数业务边界与参数契约:
           - mean_jump_size 处于真实物理世界下界保护区间 [-0.99, +5.0]。
           - jump_adjusted_price >= max(0.0, K - S)。

        3. 测试数据与模拟场景说明:
           - 模拟黑天鹅暴跌 100% 破产场景 (mean_jump_size = -1.20)，现价 $20，行权价 $50 (内在价值 $30)。

        4. 预期断言与结果验证:
           - 过程不抛出异常。
           - jump_adjusted_price 严格大于等于内在价值 $30.0。
        """
        params = AmericanOptionTreeInput(
            spot_price=20.0,
            strike_price=50.0,
            time_to_expiry_years=1.0,
            risk_free_rate=0.04,
            implied_vol=0.35,
            dividend_yield=0.0,
            is_call=False,
            steps=100,
            jump_intensity=2.0,
            mean_jump_size=-1.20,  # 极端破产穿透测试
            jump_vol=0.30,
        )
        res = self.tree_engine.price_crr_tree(params)
        self.assertGreaterEqual(res["jump_adjusted_price"], 30.0)

    def test_ut_upgrade_05_option_tree_nonpositive_inputs_defense(self):
        """【UT-UPGRADE-05: 美式期权现价与行权价非正数物理拦截与异常防御断言】

        一、测试功能与测试点:
            验证 AmericanOptionTreeEngine.price_crr_tree 金融数学边界防御:
            标的现价 (spot_price) 或行权价 (strike_price) 小于等于 0 时，
            引擎坚决抛出结构化 ValueError 拦截，杜绝 math.log(S/K) 在零或负数域发生程序崩溃。

        二、正常函数业务边界与参数契约:
            - spot_price <= 0 或 strike_price <= 0

        三、测试数据与模拟场景说明:
            测试现价为 0.0 与行权价为 -10.0 的非法脏数据输入场景。

        四、预期断言与结果验证:
            断言抛出 ValueError 且包含 "【金融数学防御】"。
        """
        bad_spot = AmericanOptionTreeInput(
            spot_price=0.0,
            strike_price=100.0,
            time_to_expiry_years=0.5,
            risk_free_rate=0.04,
            implied_vol=0.20,
        )
        with self.assertRaises(ValueError) as ctx:
            self.tree_engine.price_crr_tree(bad_spot)
        self.assertIn("【金融数学防御】", str(ctx.exception))

        bad_strike = AmericanOptionTreeInput(
            spot_price=100.0,
            strike_price=-10.0,
            time_to_expiry_years=0.5,
            risk_free_rate=0.04,
            implied_vol=0.20,
        )
        with self.assertRaises(ValueError) as ctx2:
            self.tree_engine.price_crr_tree(bad_strike)
        self.assertIn("【金融数学防御】", str(ctx2.exception))

    def test_ut_upgrade_06_option_tree_narrative_zh_deengineered(self):
        """【UT-UPGRADE-06: 美式期权去工程符号化与买方直觉通俗研报 narrative_zh 断言】

        一、测试功能与测试点:
            验证面向买方投资人的通俗商业自然语言研报卡片 (narrative_zh) 输出:
            美式期权二叉树引擎必须输出去工程符号化的高可读性研报卡片，
            清晰阐释二叉树公允理论价、纯欧式基准对比、提前行权溢价及理性行权决策建议。

        二、正常函数业务边界与参数契约:
            - 正常美式期权输入参数。

        三、测试数据与模拟场景说明:
            测试实值看涨期权场景。

        四、预期断言与结果验证:
            断言 narrative_zh 字段存在且非空。
            断言包含 "美式看涨期权" 与 "二叉树公允理论价"。
            断言严禁包含原始工程代码变量名 (如 "american_price" 或 "spot_price")。
        """
        params = AmericanOptionTreeInput(
            spot_price=110.0,
            strike_price=100.0,
            time_to_expiry_years=0.5,
            risk_free_rate=0.05,
            implied_vol=0.25,
            is_call=True,
            steps=80,
        )
        res = self.tree_engine.price_crr_tree(params)
        narrative = res["narrative_zh"]
        self.assertIn("美式看涨期权", narrative)
        self.assertIn("二叉树公允理论价", narrative)
        self.assertIn("提前行权", narrative)
        self.assertNotIn("spot_price", narrative)
        self.assertNotIn("american_price", narrative)

    def test_ut_upgrade_07_macro_shock_wacc_floor_and_negative_beta_defense(self):
        """【UT-UPGRADE-07: 宏观传导无风险利率底线与负Beta异常防御断言】

        一、测试功能与测试点:
            验证 MacroShockTransmissionEngine.evaluate_macro_shock 的资本资产定价公理:
            在宏观紧缩与日元套息平仓踩踏背景下，即便是特殊行业或误传入负 Beta (如 -0.5)，
            微观权益资本成本 (shocked_wacc) 也绝不能跌破美债无风险利率基准 (us_10y_yield)。
            同时有效 Beta 取绝对值并施加 0.10 下界，防止折现率逆向塌陷。

        二、正常函数业务边界与参数契约:
            - company_beta = -0.5 (异常负 Beta 输入)
            - base_wacc = 0.03 (极低初始 WACC)
            - us_10y_yield = 0.045 (4.5% 美债利率)

        三、测试数据与模拟场景说明:
            测试宏观压力下企业折现率下界兜底场景。

        四、预期断言与结果验证:
            断言 shocked_wacc_pct 必须严格大于等于 us_10y_yield (4.50%)。
            断言过程平稳计算，无除零或负数异常。
        """
        params = MacroShockInput(
            us_10y_yield=0.045,
            usdjpy_rate=150.0,
            vix_index=25.0,
            usdjpy_daily_change_pct=-0.02,
            fed_liquidity_drain_billion=50.0,
            company_beta=-0.5,
            company_debt_to_equity=0.5,
            base_wacc=0.03,
        )
        res = self.macro_engine.evaluate_macro_shock(params)
        self.assertGreaterEqual(res["shocked_wacc_pct"], 4.50)

    def test_ut_upgrade_08_macro_shock_narrative_zh_deengineered(self):
        """【UT-UPGRADE-08: 宏观传导去工程符号化与买方全息研报 narrative_zh 断言】

        一、测试功能与测试点:
            验证宏观冲击传导引擎输出去工程符号化的全息买方研报卡片 (narrative_zh):
            将宏观流动性周期、日元套息平仓、资产相关性趋同、微观折现率加压与估值下折、
            微观资产画像和买方战术策略通俗融汇，杜绝向投资人呈现技术代码下划线。

        二、正常函数业务边界与参数契约:
            - 正常宏观冲击参数。

        三、测试数据与模拟场景说明:
            测试物理垄断资产在黑天鹅流动性错杀中的承压研报生成场景。

        四、预期断言与结果验证:
            断言 narrative_zh 非空且包含 "宏观流动性与微观承压全息研判"。
            断言包含 "物理垄断" 与 "流动性错杀提款机抛盘"。
            断言严禁包含 "carry_trade_stress_score" 等工程代码字段名。
        """
        params = MacroShockInput(
            us_10y_yield=0.044,
            usdjpy_rate=145.0,
            vix_index=32.0,
            usdjpy_daily_change_pct=-0.03,
            fed_liquidity_drain_billion=80.0,
            company_beta=1.2,
            company_debt_to_equity=1.0,
            base_wacc=0.08,
            has_monopoly_moat=True,
        )
        res = self.macro_engine.evaluate_macro_shock(params)
        narrative = res["narrative_zh"]
        self.assertIn("宏观流动性与微观承压全息研判", narrative)
        self.assertIn("物理垄断", narrative)
        self.assertIn("流动性错杀提款机抛盘", narrative)
        self.assertNotIn("carry_trade_stress_score", narrative)
        self.assertNotIn("converged_market_correlation", narrative)

    def test_ut_upgrade_09_facade_and_core_ssot_equivalence(self):
        """【UT-UPGRADE-09: 向下兼容中继门面 SSOT 完全等价性断言】

        一、测试功能与测试点:
            验证 `finance_tools.american_option_tree_engine` 与
            `finance_tools.macro_shock_transmission_engine` 门面与底层核心
            `financial_core.engines` 模块的一致性与单一事实来源 (SSOT) 完全等价。

        二、正常函数业务边界与参数契约:
            - Core 与 Facade 运行相同输入用例。

        三、测试数据与模拟场景说明:
            测试标准期权定价与宏观冲击评测场景。

        四、预期断言与结果验证:
            断言门面与核心输出的核心指标与全息研报卡片完全一致。
        """
        from financial_core.engines.american_option_tree_engine import (
            AmericanOptionTreeEngine as CoreTreeEngine,
            AmericanOptionTreeInput as CoreTreeInput,
        )
        from financial_core.engines.macro_shock_transmission_engine import (
            MacroShockTransmissionEngine as CoreMacroEngine,
            MacroShockInput as CoreMacroInput,
        )

        core_tree = CoreTreeEngine()
        p_tree = CoreTreeInput(50.0, 50.0, 0.5, 0.04, 0.25, is_call=True, steps=60)
        res_tree_core = core_tree.price_crr_tree(p_tree)
        res_tree_facade = self.tree_engine.price_crr_tree(p_tree)
        self.assertEqual(res_tree_core["american_price"], res_tree_facade["american_price"])
        self.assertEqual(res_tree_core["narrative_zh"], res_tree_facade["narrative_zh"])

        core_macro = CoreMacroEngine()
        p_macro = CoreMacroInput(0.04, 150.0, 20.0, -0.01, 30.0, 1.1, 0.8, 0.08)
        res_macro_core = core_macro.evaluate_macro_shock(p_macro)
        res_macro_facade = self.macro_engine.evaluate_macro_shock(p_macro)
        self.assertEqual(res_macro_core["shocked_wacc_pct"], res_macro_facade["shocked_wacc_pct"])
        self.assertEqual(res_macro_core["narrative_zh"], res_macro_facade["narrative_zh"])


if __name__ == "__main__":
    unittest.main()
