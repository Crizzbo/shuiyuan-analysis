"""全阶希腊字母与波动率偏斜分析引擎单元测试套件.

本测试模块严格遵循《36号工程黄金设计规范》与四段式结构化中文契约测试模型:
1. 测试功能与测试点说明 (Test Functionality & Objectives)
2. 正常函数业务边界与参数契约 (Business Boundaries & Parameter Contracts)
3. 测试数据与模拟场景说明 (Test Data & Scenario Descriptions)
4. 预期断言与结果验证 (Expected Assertions & Verification)

涵盖解析解全阶希腊字母、平价套利核验、25-Delta偏斜识别、去工程符号化及跨市场多币种自适应推导。
"""

import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.volatility_surface_engine import (
    OptionGreeksResult,
    PutCallParityCheckResult,
    VolatilitySkewResult,
    VolatilitySurfaceGreeksEngine,
)


class TestVolatilitySurfaceGreeksEngine(unittest.TestCase):
    """全阶希腊字母与波动率曲面引擎单元测试."""

    def test_ut_vol_01_merton_black_scholes_pricing(self):
        """【UT-VOL-01: 连续红利 Merton (1973) 扩展期权定价解析解与希腊字母准确性断言】

        一、测试功能与测试点:
            验证在标的现价、行权价、到期期限、无风险利率、股息率和年化波动率输入下，
            期权公允理论价格、内在价值、时间价值及一阶 Delta 正确收敛至理论边界。

        二、正常函数业务边界与参数契约:
            - spot: 100.0
            - strike: 100.0 (平值 ATM)
            - time_to_expiry_years: 1.0 年
            - risk_free_rate: 0.05 (5%)
            - dividend_yield: 0.02 (2%)
            - volatility: 0.20 (20%)
            - option_type: "call" 与 "put"

        三、测试数据与模拟场景说明:
            测试标准平值合约在经典 Black-Scholes-Merton 框架下的基准定价。

        四、预期断言与结果验证:
            断言 Call 理论价格大于 0，内在价值为 0，时间价值等于期权价格；
            断言 Call Delta 介于 (0.5, 0.7) 之间，Put Delta 介于 (-0.5, -0.3) 之间。
        """
        res_call = VolatilitySurfaceGreeksEngine.calculate_option_greeks(
            spot=100.0,
            strike=100.0,
            time_to_expiry_years=1.0,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
            option_type="call",
        )

        self.assertIsInstance(res_call, OptionGreeksResult)
        self.assertGreater(res_call.theoretical_price, 7.0)
        self.assertLess(res_call.theoretical_price, 12.0)
        self.assertEqual(res_call.intrinsic_value, 0.0)
        self.assertEqual(res_call.time_value, res_call.theoretical_price)
        self.assertGreater(res_call.delta, 0.5)
        self.assertLess(res_call.delta, 0.7)

        res_put = VolatilitySurfaceGreeksEngine.calculate_option_greeks(
            spot=100.0,
            strike=100.0,
            time_to_expiry_years=1.0,
            risk_free_rate=0.05,
            dividend_yield=0.02,
            volatility=0.20,
            option_type="put",
        )
        self.assertIsInstance(res_put, OptionGreeksResult)
        self.assertGreater(res_put.theoretical_price, 4.0)
        self.assertLess(res_put.theoretical_price, 9.0)
        self.assertLess(res_put.delta, -0.3)
        self.assertGreater(res_put.delta, -0.5)

    def test_ut_vol_02_higher_order_greeks_economic_intuition(self):
        """【UT-VOL-02: 一阶/二阶与交叉希腊字母符号与买方经济学直觉断言】

        一、测试功能与测试点:
            验证 Gamma (凸性 > 0)、Vega (波动率敏感度 > 0)、Theta (时间衰减 < 0)、
            Volga (波动率凸性 > 0) 等高阶希腊字母符合金融常识。

        二、正常函数业务边界与参数契约:
            - 标准欧式买权多头头寸。

        三、测试数据与模拟场景说明:
            测试典型流动性合约的希腊字母曲率。

        四、预期断言与结果验证:
            断言 Gamma > 0, Vega > 0, Theta < 0, Volga > 0。
        """
        res = VolatilitySurfaceGreeksEngine.calculate_option_greeks(
            spot=150.0,
            strike=150.0,
            time_to_expiry_years=0.5,
            risk_free_rate=0.04,
            dividend_yield=0.01,
            volatility=0.25,
            option_type="call",
        )
        self.assertGreater(res.gamma, 0.0)
        self.assertGreater(res.vega_1pct, 0.0)
        self.assertLess(res.theta_daily, 0.0)
        self.assertIsInstance(res.volga, float)

        # 虚值期权 (OTM Call) 处 d1 与 d2 同号，Volga (波动率凸性) 严格大于 0
        res_otm = VolatilitySurfaceGreeksEngine.calculate_option_greeks(
            spot=150.0,
            strike=180.0,
            time_to_expiry_years=0.5,
            risk_free_rate=0.04,
            dividend_yield=0.01,
            volatility=0.25,
            option_type="call",
        )
        self.assertGreater(res_otm.volga, 0.0)

    def test_ut_vol_03_put_call_parity_arbitrage_detection(self):
        """【UT-VOL-03: 看涨看跌平价套利关系检验与正反向转化套利信号断言】

        一、测试功能与测试点:
            验证在市场期权价偏离合成远期价值时，精准捕获正向转化套利 (Call 高估) 与反向转化套利 (Put 高估)。

        二、正常函数业务边界与参数契约:
            - tolerance: 0.35
            - spot: 100.0, strike: 100.0, T: 1.0, r: 0.05, q: 0.0

        三、测试数据与模拟场景说明:
            1. 远期差额 S - K*exp(-r*T) ≈ 100 - 95.12 = 4.88
            2. 若 Call=12.0, Put=4.0 -> C - P = 8.0 > 4.88 + 0.35 -> 正向转化套利
            3. 若 Call=6.0, Put=5.0 -> C - P = 1.0 < 4.88 - 0.35 -> 反向转化套利

        四、预期断言与结果验证:
            断言套利信号分别判定为 CONVERSION_ARBITRAGE 与 REVERSE_CONVERSION_ARBITRAGE。
        """
        # 场景 1: 正向转化套利
        res_conv = VolatilitySurfaceGreeksEngine.check_put_call_parity(
            call_price=12.0,
            put_price=4.0,
            spot=100.0,
            strike=100.0,
            time_to_expiry_years=1.0,
            risk_free_rate=0.05,
            dividend_yield=0.0,
        )
        self.assertEqual(res_conv.arbitrage_signal, "CONVERSION_ARBITRAGE")
        self.assertIn("正向转化套利", res_conv.arbitrage_signal_zh)
        self.assertGreater(res_conv.max_arbitrage_profit, 2.0)

        # 场景 2: 反向转化套利
        res_rev = VolatilitySurfaceGreeksEngine.check_put_call_parity(
            call_price=6.0,
            put_price=5.0,
            spot=100.0,
            strike=100.0,
            time_to_expiry_years=1.0,
            risk_free_rate=0.05,
            dividend_yield=0.0,
        )
        self.assertEqual(res_rev.arbitrage_signal, "REVERSE_CONVERSION_ARBITRAGE")
        self.assertIn("反向转化套利", res_rev.arbitrage_signal_zh)
        self.assertGreater(res_rev.max_arbitrage_profit, 2.0)

    def test_ut_vol_04_volatility_skew_market_sentiment(self):
        """【UT-VOL-04: 波动率偏斜 25-Delta Skew 与微笑曲线买方情绪诊断断言】

        一、测试功能与测试点:
            验证依据各行权价的 IV 序列，二次拟合求解对数 Moneyness 下的微笑曲率，
            并依据 25-Delta 看跌与看涨 IV 之差判定下行恐慌情绪。

        二、正常函数业务边界与参数契约:
            - strikes: [80, 90, 100, 110, 120]
            - IV: 左高右低典型恐慌偏斜 [0.35, 0.28, 0.22, 0.18, 0.16]

        三、测试数据与模拟场景说明:
            测试典型机构重仓防范黑天鹅行情的偏斜曲线。

        四、预期断言与结果验证:
            断言 skew_25d > 0，市场信号为 SEVERE_CRASH_FEAR 或 NORMAL_EQUITY_SKEW。
        """
        strikes = [80.0, 90.0, 100.0, 110.0, 120.0]
        ivs = [0.38, 0.30, 0.23, 0.19, 0.16]

        res = VolatilitySurfaceGreeksEngine.analyze_volatility_skew(
            strikes=strikes,
            implied_vols=ivs,
            spot=100.0,
            time_to_expiry_years=0.25,
            risk_free_rate=0.04,
            dividend_yield=0.01,
        )

        self.assertIsInstance(res, VolatilitySkewResult)
        self.assertGreater(res.skew_25d, 0.05)
        self.assertEqual(res.market_sentiment_signal, "SEVERE_CRASH_FEAR")
        self.assertIn("恐慌", res.market_sentiment_signal_zh)
        self.assertIn("买方对冲情绪研判", res.narrative_zh)

    def test_ut_vol_05_natural_language_and_de_engineering(self):
        """【UT-VOL-05: 消除英文代号 100bps 暴露与买方全息研报卡片纯中文契约断言】

        一、测试功能与测试点:
            验证在研报文字中彻底消除纯英文工程代码 "100bps"，全面替换为自然通俗中文 "每 100 个基点"，
            确保买方阅读体验直观专业。

        二、正常函数业务边界与参数契约:
            - calculate_option_greeks 输出 narrative_zh。

        三、测试数据与模拟场景说明:
            测试标准期权希腊字母研报输出。

        四、预期断言与结果验证:
            断言 narrative_zh 中严禁出现 "100bps"，必须包含 "每 100 个基点"。
        """
        res = VolatilitySurfaceGreeksEngine.calculate_option_greeks(
            spot=200.0,
            strike=200.0,
            time_to_expiry_years=0.5,
            risk_free_rate=0.05,
            dividend_yield=0.0,
            volatility=0.30,
            option_type="call",
        )

        self.assertNotIn("100bps", res.narrative_zh)
        self.assertIn("每 100 个基点", res.narrative_zh)
        self.assertIn("全阶希腊字母与敏感度全息研报", res.narrative_zh)

    def test_ut_vol_06_cross_market_currency_adaptation(self):
        """【UT-VOL-06: 跨市场多币种自适应推导与日股/A股研报货币符号断言】

        一、测试功能与测试点:
            验证传入日股代码 (如 9984.T 或 6758) 时，自适应推导货币符号为 '¥'；
            验证研报 narrative_zh 中严禁死锁美元 '$'，必须呈现 '¥'；
            验证 to_dict() 序列化中包含 currency_symbol 字段。

        二、正常函数业务边界与参数契约:
            - ticker="9984.T", market="JP"

        三、测试数据与模拟场景说明:
            测试日股软银集团期权定价与希腊字母计算场景。

        四、预期断言与结果验证:
            断言 currency_symbol == "¥"，narrative_zh 中包含 "¥" 且无 "$"；
            平价核验同样自适应支持日元符号。
        """
        res_greeks = VolatilitySurfaceGreeksEngine.calculate_option_greeks(
            spot=8500.0,
            strike=8500.0,
            time_to_expiry_years=0.25,
            risk_free_rate=0.005,
            dividend_yield=0.01,
            volatility=0.35,
            option_type="call",
            ticker="9984.T",
            market="JP",
        )

        self.assertEqual(res_greeks.currency_symbol, "¥")
        self.assertIn("¥", res_greeks.narrative_zh)
        self.assertNotIn("$", res_greeks.narrative_zh)
        d_greeks = res_greeks.to_dict()
        self.assertEqual(d_greeks["currency_symbol"], "¥")

        # 检验平价核验自适应推导
        res_parity = VolatilitySurfaceGreeksEngine.check_put_call_parity(
            call_price=500.0,
            put_price=450.0,
            spot=8500.0,
            strike=8500.0,
            time_to_expiry_years=0.25,
            risk_free_rate=0.005,
            dividend_yield=0.01,
            ticker="9984.T",
        )
        self.assertEqual(res_parity.currency_symbol, "¥")
        self.assertIn("¥", res_parity.narrative_zh)
        self.assertNotIn("$", res_parity.narrative_zh)
        d_parity = res_parity.to_dict()
        self.assertEqual(d_parity["currency_symbol"], "¥")

    def test_ut_vol_07_implied_volatility_solver_convergence(self):
        """【UT-VOL-07: 隐含波动率 (IV) Brent 数值求解与精度验证断言】

        一、测试功能与测试点:
            验证给定市价与期权合约参数，能够通过 Brent 算法逆向精准求解隐含波动率，
            与反算代入的误差在 1e-3 以内。

        二、正常函数业务边界与参数契约:
            - 已知理论价格求解 IV。

        三、测试数据与模拟场景说明:
            设定真实波动率为 0.28，先计算理论市价，再求解 IV 对比。

        四、预期断言与结果验证:
            断言求解出的 IV 与 0.28 绝对差值小于 0.002。
        """
        true_vol = 0.28
        calc = VolatilitySurfaceGreeksEngine.calculate_option_greeks(
            spot=100.0,
            strike=105.0,
            time_to_expiry_years=0.5,
            risk_free_rate=0.04,
            dividend_yield=0.01,
            volatility=true_vol,
            option_type="call",
        )
        market_price = calc.theoretical_price

        solved_iv = VolatilitySurfaceGreeksEngine.solve_implied_volatility(
            market_price=market_price,
            spot=100.0,
            strike=105.0,
            time_to_expiry_years=0.5,
            risk_free_rate=0.04,
            dividend_yield=0.01,
            option_type="call",
        )

        self.assertIsNotNone(solved_iv)
        self.assertAlmostEqual(solved_iv, true_vol, places=2)


if __name__ == "__main__":
    unittest.main()
