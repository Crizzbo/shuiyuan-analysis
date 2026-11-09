# -*- coding: utf-8 -*-
"""全天候实战闭环公式群单元测试与回归套件 (test_all_weather_formulas.py).

覆盖 5 大买方机构级核心公式引擎：
1. 牛熊状态总阀门 (MacroRegimeHMMValveEngine)
2. 震荡市高抛低吸副武器 (MeanReversionKalmanEngine)
3. 动态波动率引擎 (GARCHVolatilityEngine)
4. 基本面与动量权重转化器 (BlackLittermanShrinkageEngine)
5. 攻防护航工具 (ForensicsAndTrailingExitEngine: Beneish M-Score + Chandelier Exit 棘轮)
6. 虚拟门面与向下兼容透明重定向验证
"""

import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.macro_regime_hmm_valve_engine import (
    MacroRegimeHMMValveEngine,
    MarketRegimeState,
    HMMModelResult,
    TrendFilterResult,
    MacroValveDecision,
)
from financial_core.engines.mean_reversion_kalman_engine import (
    MeanReversionKalmanEngine,
    OUProcessResult,
    KalmanFilterResult,
    MeanReversionVerdict,
)
from financial_core.engines.garch_volatility_engine import (
    GARCHVolatilityEngine,
    GARCHModelResult,
    VolatilityForecastResult,
    GARCHVolatilityVerdict,
)
from financial_core.engines.black_litterman_shrinkage_engine import (
    BlackLittermanShrinkageEngine,
    ShrinkageResult,
    BlackLittermanResult,
)
from financial_core.engines.forensics_and_trailing_exit_engine import (
    ForensicsAndTrailingExitEngine,
    BeneishMetrics,
    BeneishScoreResult,
    ChandelierExitResult,
)
from financial_core.api import FinancialAnalysisSystem


class TestAllWeatherFormulasSuite(unittest.TestCase):
    """全天候实战闭环公式群全息单元测试."""

    def setUp(self):
        self.fin_system = FinancialAnalysisSystem()

    # ==========================================
    # 1. 牛熊状态总阀门测试
    # ==========================================

    def test_hmm_valve_gaussian_pdf_safety(self):
        """【UT-VALVE-01: 高斯 PDF 数值边界防下溢与除零防御】"""
        engine = MacroRegimeHMMValveEngine()
        # 极小标准差防御
        val1 = engine._gaussian_pdf(0.0, 0.0, 1e-12)
        self.assertGreater(val1, 0.0)
        # 极端偏差不崩溃且不下溢
        val2 = engine._gaussian_pdf(100.0, 0.0, 0.01)
        self.assertGreaterEqual(val2, 1e-300)

    def test_hmm_valve_fit_and_trend_filter(self):
        """【UT-VALVE-02: 三状态 HMM 拟合与 200 日大盘生命线开关】"""
        engine = MacroRegimeHMMValveEngine()

        # 构造模拟收益率 (60 天低波动牛市样本)
        bull_returns = [0.0015 + 0.004 * math.sin(i * 0.2) for i in range(80)]
        hmm_res = engine.fit_and_predict_hmm(bull_returns)

        self.assertIsInstance(hmm_res.current_state, MarketRegimeState)
        self.assertEqual(len(hmm_res.state_probabilities), 3)
        self.assertAlmostEqual(sum(hmm_res.state_probabilities.values()), 1.0, places=2)
        self.assertGreater(hmm_res.confidence_score, 0.0)

        # 构造大盘收盘价序列 (220 天，稳步上行)
        base_price = 100.0
        prices = [base_price * (1.0 + 0.001 * t) for t in range(220)]
        trend_res = engine.compute_trend_filter(prices)

        self.assertTrue(trend_res.is_above_ma200)
        self.assertTrue(trend_res.is_golden_cross)
        self.assertEqual(trend_res.trend_verdict, "STRONG_BULL_TREND")

        # 评估总阀门决策 (放开进攻)
        decision = engine.evaluate_valve("2026-11-09", prices)
        self.assertIn(decision.valve_status, ["OPEN", "CAUTION"])
        self.assertGreaterEqual(decision.total_position_ceiling_pct, 0.60)
        self.assertIn("MA200", decision.rationale_zh)

    def test_hmm_valve_bear_defense_ceiling(self):
        """【UT-VALVE-03: 大盘失守 MA200 触发刚性仓位降温与防守】"""
        engine = MacroRegimeHMMValveEngine()
        # 构造跌破均线时序 (前 150 天在 200 点，后 70 天暴跌至 80 点)
        prices = [200.0] * 150 + [200.0 - (120.0 * (t / 70.0)) for t in range(1, 71)]
        trend_res = engine.compute_trend_filter(prices)
        self.assertFalse(trend_res.is_above_ma200)

        decision = engine.evaluate_valve("2026-11-09", prices)
        self.assertIn(decision.valve_status, ["DEFENSE", "CLOSED"])
        self.assertLessEqual(decision.total_position_ceiling_pct, 0.30)

    # ==========================================
    # 2. 震荡市高抛低吸副武器测试
    # ==========================================

    def test_ou_process_and_kalman_filter(self):
        """【UT-SWING-01: OU 均值回归过程半衰期与卡尔曼动态通道】"""
        engine = MeanReversionKalmanEngine()

        # 构造强均值回归正弦平稳序列 (围绕 50 震荡)
        prices = [50.0 + 5.0 * math.sin(i * 0.4) for i in range(40)]
        ou_res = engine.fit_ou_process(prices)

        self.assertTrue(ou_res.is_mean_reverting)
        self.assertGreater(ou_res.theta, 0.0)
        self.assertAlmostEqual(ou_res.equilibrium_mu, 50.0, delta=2.0)
        self.assertLess(ou_res.half_life_days, 30.0)

        # 运行卡尔曼滤波
        kalman_res = engine.apply_kalman_filter(prices)
        self.assertGreater(kalman_res.kalman_upper_band, kalman_res.kalman_lower_band)
        self.assertAlmostEqual(kalman_res.filtered_price, 50.0, delta=6.0)
        self.assertGreaterEqual(kalman_res.channel_position_pct, 0.0)
        self.assertLessEqual(kalman_res.channel_position_pct, 1.0)

    def test_swing_oversold_buy_signal(self):
        """【UT-SWING-02: 严重超跌触及卡尔曼下轨触发左侧低吸】"""
        engine = MeanReversionKalmanEngine(zscore_entry_threshold=1.5)
        # 构造标准 AR(1) 均值回归样本序列 (中枢 100, 回归系数 0.6)
        prices = [100.0]
        for i in range(1, 45):
            p = 100.0 + 0.6 * (prices[-1] - 100.0) + 1.5 * math.sin(i * 0.8)
            prices.append(p)
        # 突发短暂超跌触及下轨
        prices.append(88.0)
        verdict = engine.evaluate_swing_opportunity("TEST_STOCK", "2026-11-09", prices)

        self.assertEqual(verdict.swing_action, "STRONG_BUY_DIP")
        self.assertGreater(verdict.expected_profit_pct, 5.0)
        self.assertIn("左侧低吸", verdict.rationale_zh)

    # ==========================================
    # 3. 动态波动率引擎测试
    # ==========================================

    def test_garch_volatility_fit_and_forecast(self):
        """【UT-GARCH-01: GARCH(1,1) 平稳性、波动率半衰期与多期限前瞻】"""
        engine = GARCHVolatilityEngine()

        # 构造带有波动率聚类的日收益率时序
        rets = [0.005 * math.cos(i * 0.1) * (1.5 if i > 30 else 0.8) for i in range(60)]
        garch_res = engine.fit_garch(rets)

        self.assertLess(garch_res.persistence, 1.0)
        self.assertGreater(garch_res.unconditional_vol_annual, 0.0)
        self.assertGreater(garch_res.vol_half_life_days, 0.0)

        # 多期限前瞻预测
        forecast = engine.forecast_volatility(garch_res, last_residual=rets[-1])
        self.assertGreater(forecast.forecast_1d_annual, 0.0)
        self.assertGreater(forecast.forecast_5d_annual, 0.0)
        self.assertGreater(forecast.forecast_22d_annual, 0.0)
        self.assertIn(forecast.vol_risk_level, ["LOW_VOL", "MODERATE_VOL", "ELEVATED_VOL", "CRITICAL_SPIKE"])

    # ==========================================
    # 4. 基本面与动量权重转化器测试
    # ==========================================

    def test_ledoit_wolf_shrinkage_and_black_litterman(self):
        """【UT-BL-01: Ledoit-Wolf 协方差收缩与 Black-Litterman 贝叶斯后验权重】"""
        engine = BlackLittermanShrinkageEngine(max_single_weight=0.40)

        tickers = ["NVDA", "AAPL", "MSFT", "GOOGL"]
        # 构造 30 天 4 标的高相关收益率矩阵
        returns_mat = [
            [0.01 * math.sin(t * 0.2 + i * 0.1) for i in range(4)]
            for t in range(40)
        ]

        # 协方差收缩
        shrinkage = engine.compute_ledoit_wolf_shrinkage(returns_mat)
        self.assertGreaterEqual(shrinkage.optimal_shrinkage_intensity, 0.0)
        self.assertLessEqual(shrinkage.optimal_shrinkage_intensity, 1.0)
        self.assertEqual(len(shrinkage.shrunk_covariance), 4)

        # Black-Litterman 贝叶斯优化配置 (主观超预期看多 NVDA，看平 AAPL)
        mkt_weights = [0.25, 0.25, 0.25, 0.25]
        views = {"NVDA": 0.20, "AAPL": -0.05}
        bl_res = engine.optimize_black_litterman(
            tickers=tickers,
            covariance_matrix=shrinkage.shrunk_covariance,
            market_benchmark_weights=mkt_weights,
            views_dict=views,
            views_confidence={"NVDA": 0.8, "AAPL": 0.6},
        )

        self.assertAlmostEqual(sum(bl_res.optimized_weights.values()), 1.0, places=2)
        # NVDA 获得正向倾斜 (Active Tilt > 0)
        self.assertGreaterEqual(bl_res.active_tilts["NVDA"], 0.0)
        # 单票上限不超过 0.40
        self.assertLessEqual(bl_res.optimized_weights["NVDA"], 0.4001)

    # ==========================================
    # 5. 攻防护航工具测试 (Beneish + Chandelier)
    # ==========================================

    def test_beneish_m_score_forensics(self):
        """【UT-FORENSIC-01: Beneish M-Score 八维财务操纵指纹排雷】"""
        engine = ForensicsAndTrailingExitEngine()

        # 正常稳健企业财报底账
        clean_res = engine.compute_beneish_m_score(
            curr_sales=1000.0, curr_cogs=600.0, curr_receivables=100.0,
            curr_current_assets=500.0, curr_ppe_net=400.0, curr_securities=50.0,
            curr_total_assets=1200.0, curr_depreciation=50.0, curr_sga=150.0,
            curr_long_term_debt=200.0, curr_current_liabilities=150.0,
            curr_net_income=120.0, curr_cfo=140.0,
            prev_sales=900.0, prev_cogs=540.0, prev_receivables=90.0,
            prev_current_assets=450.0, prev_ppe_net=380.0, prev_securities=40.0,
            prev_total_assets=1100.0, prev_depreciation=45.0, prev_sga=140.0,
            prev_long_term_debt=200.0, prev_current_liabilities=140.0,
        )
        self.assertFalse(clean_res.is_manipulation_suspect)
        self.assertEqual(clean_res.risk_rating, "CLEAN")
        self.assertLess(clean_res.m_score, -2.0)

        # 财务造假严重企业 (应收账款翻倍、毛利率暴跌但虚报利润、应计利润奇高)
        fraud_res = engine.compute_beneish_m_score(
            curr_sales=1000.0, curr_cogs=750.0, curr_receivables=450.0, # 应收暴增
            curr_current_assets=700.0, curr_ppe_net=200.0, curr_securities=10.0,
            curr_total_assets=1500.0, curr_depreciation=10.0, curr_sga=250.0,
            curr_long_term_debt=600.0, curr_current_liabilities=400.0,
            curr_net_income=250.0, curr_cfo=-80.0, # 净利润与现金流严重背离
            prev_sales=900.0, prev_cogs=500.0, prev_receivables=100.0,
            prev_current_assets=400.0, prev_ppe_net=300.0, prev_securities=50.0,
            prev_total_assets=1000.0, prev_depreciation=40.0, prev_sga=100.0,
            prev_long_term_debt=200.0, prev_current_liabilities=150.0,
        )
        self.assertTrue(fraud_res.is_manipulation_suspect)
        self.assertEqual(fraud_res.risk_rating, "MANIPULATOR_ALERT")
        self.assertGreater(fraud_res.m_score, -1.78)
        self.assertGreater(len(fraud_res.flagged_dimensions), 0)

    def test_chandelier_exit_one_way_ratchet(self):
        """【UT-TRAILING-02: 吊灯移动止盈与单向棘轮锁定机制】"""
        engine = ForensicsAndTrailingExitEngine(chandelier_period=22, chandelier_atr_mult=3.0)

        highs = [100.0 + i * 2.0 for i in range(25)] # 持续创新高
        lows = [95.0 + i * 2.0 for i in range(25)]
        closes = [98.0 + i * 2.0 for i in range(25)]

        # 处于上涨途中，持仓守利
        res1 = engine.compute_chandelier_exit("NVDA", "2026-11-09", highs, lows, closes)
        self.assertFalse(res1.is_triggered)
        self.assertEqual(res1.action_verdict, "HOLD_RIDE_TREND")
        ratchet_1 = res1.ratchet_stop_price

        # 下一交易日出现剧烈破位下杀 (价格跌穿先前锁定的棘轮止盈位)
        highs_crash = highs + [highs[-1] + 1.0]
        lows_crash = lows + [ratchet_1 - 10.0]
        closes_crash = closes + [ratchet_1 - 5.0]

        res2 = engine.compute_chandelier_exit(
            "NVDA", "2026-11-10", highs_crash, lows_crash, closes_crash,
            prior_ratchet_stop=ratchet_1,
        )
        # 单向棘轮保证止盈线绝不因为当天波动向下退化
        self.assertGreaterEqual(res2.ratchet_stop_price, ratchet_1)
        self.assertTrue(res2.is_triggered)
        self.assertEqual(res2.action_verdict, "TAKE_PROFIT_EXIT")

    # ==========================================
    # 6. 门面集成与向下兼容透明重定向验证
    # ==========================================

    def test_virtual_facade_transparent_redirection(self):
        """【UT-FACADE-03: PEP 451 虚拟门面向下兼容导入透明重定向】"""
        import finance_tools.macro_regime_hmm_valve_engine as m1
        import finance_tools.mean_reversion_kalman_engine as m2
        import finance_tools.garch_volatility_engine as m3
        import finance_tools.black_litterman_shrinkage_engine as m4
        import finance_tools.forensics_and_trailing_exit_engine as m5

        self.assertTrue(hasattr(m1, "MacroRegimeHMMValveEngine"))
        self.assertTrue(hasattr(m2, "MeanReversionKalmanEngine"))
        self.assertTrue(hasattr(m3, "GARCHVolatilityEngine"))
        self.assertTrue(hasattr(m4, "BlackLittermanShrinkageEngine"))
        self.assertTrue(hasattr(m5, "ForensicsAndTrailingExitEngine"))

    def test_financial_analysis_system_api_mount(self):
        """【UT-API-04: FinancialAnalysisSystem 统一门面实例挂载就绪】"""
        self.assertTrue(hasattr(self.fin_system, "macro_hmm_valve_engine"))
        self.assertTrue(hasattr(self.fin_system, "mean_reversion_kalman_engine"))
        self.assertTrue(hasattr(self.fin_system, "garch_volatility_engine"))
        self.assertTrue(hasattr(self.fin_system, "black_litterman_engine"))
        self.assertTrue(hasattr(self.fin_system, "forensics_trailing_engine"))


if __name__ == "__main__":
    unittest.main()
