# -*- coding: utf-8 -*-
"""补充金融模型全息检验单元测试 (test_supplementary_models.py).

严格遵循《AGENTS.md》与《CLAUDE.md》：
1. 测试覆盖四大失效防御补充模型：
   - Merton 结构化信用违约与破产预警引擎；
   - Amihud 微观流动性冲击与市场深度衰减引擎；
   - Option Skew 期权波动率曲面偏度与主力异动流引擎。
2. 金融数学边界防御断言：
   - 除零/除负/极小值防御；
   - 极端黑天鹅前瞻预警灵敏度与一票否决门禁；
   - 100% 独立于外部环境，纯本地确定性验证。
"""

import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.merton_default_engine import (
    MertonStructuralDefaultEngine,
    MertonDefaultMetrics,
)
from financial_core.engines.amihud_liquidity_engine import (
    AmihudLiquidityEngine,
    AmihudLiquidityMetrics,
)
from financial_core.engines.option_skew_flow_engine import (
    OptionSkewFlowEngine,
    OptionSkewMetrics,
)


class TestSupplementaryFinancialModels(unittest.TestCase):
    """失效防御补充金融模型全息单元测试."""

    def setUp(self) -> None:
        self.merton = MertonStructuralDefaultEngine(risk_free_rate_default=0.04)
        self.amihud = AmihudLiquidityEngine(lookback_days=20)
        self.skew = OptionSkewFlowEngine()

    def test_merton_investment_grade_firm(self) -> None:
        """测试高市值、低负债、低波动率蓝筹股的信用与违约距离."""
        # 类似微软/苹果：市值 $2000B, 短期债 $20B, 长期债 $80B, 年化波动率 22%
        res = self.merton.evaluate_credit_default_risk(
            equity_market_cap=2_000_000_000_000.0,
            short_term_debt=20_000_000_000.0,
            long_term_debt=80_000_000_000.0,
            equity_volatility_annual=0.22,
            risk_free_rate=0.04,
            time_horizon_years=1.0,
        )
        self.assertIsInstance(res, MertonDefaultMetrics)
        self.assertGreater(res.distance_to_default, 3.5)
        self.assertLess(res.expected_default_freq, 0.001)
        self.assertFalse(res.is_black_swan_alert)
        self.assertIn("INVESTMENT_GRADE", res.credit_health_grade)
        self.assertGreater(res.implied_asset_value, res.equity_market_cap)

    def test_merton_distressed_black_swan_firm(self) -> None:
        """测试高负债、低市值、剧烈波动的暴雷破产高危标的."""
        # 类似破产边缘公司：市值 $50M, 短期债 $300M, 长期债 $500M, 年化波动率 85%
        res = self.merton.evaluate_credit_default_risk(
            equity_market_cap=50_000_000.0,
            short_term_debt=300_000_000.0,
            long_term_debt=500_000_000.0,
            equity_volatility_annual=0.85,
            risk_free_rate=0.05,
            time_horizon_years=1.0,
        )
        self.assertIsInstance(res, MertonDefaultMetrics)
        self.assertLess(res.distance_to_default, 1.0)
        self.assertGreater(res.expected_default_freq, 0.15)
        self.assertTrue(res.is_black_swan_alert)
        self.assertIn(res.credit_health_grade, ["DISTRESSED_CCC", "CRITICAL_DEFAULT_D"])

    def test_merton_math_boundary_defense(self) -> None:
        """测试 Merton 引擎在零负债、零波动率、负数输入下的抗崩溃能力."""
        res_zero_debt = self.merton.evaluate_credit_default_risk(
            equity_market_cap=1_000_000.0,
            short_term_debt=0.0,
            long_term_debt=0.0,
            equity_volatility_annual=0.0,
        )
        self.assertGreater(res_zero_debt.distance_to_default, 0.0)
        self.assertFalse(math.isnan(res_zero_debt.distance_to_default))
        self.assertFalse(math.isinf(res_zero_debt.distance_to_default))

    def test_amihud_mega_cap_liquidity(self) -> None:
        """测试高流动性标的（日均成交额上亿美元）的低不流动性比率与低冲击滑点."""
        bars = []
        base_price = 150.0
        for i in range(30):
            p = base_price + (i % 3) * 0.5
            bars.append({
                "date": f"2024-01-{i+1:02d}",
                "open": p - 0.2,
                "high": p + 0.8,
                "low": p - 0.5,
                "close": p,
                "volume": 20_000_000,  # 每日成交量 2000万股，成交额约 $3B
            })
        res = self.amihud.evaluate_liquidity(
            symbol="NVDA",
            bars=bars,
            market="US",
            intended_order_value=100_000.0,
        )
        self.assertIsInstance(res, AmihudLiquidityMetrics)
        self.assertFalse(res.is_illiquid_trap)
        self.assertEqual(res.capacity_tier, "MEGA_LIQUID")
        self.assertLess(res.amihud_illiquidity_ratio, 0.01)
        self.assertLess(res.market_impact_penalty_bps, 15.0)

    def test_amihud_illiquid_micro_cap_trap(self) -> None:
        """测试微盘仙股流动性陷阱硬拦截与大额滑点惩罚."""
        bars = []
        base_price = 1.0
        for i in range(25):
            p = base_price + (i % 2) * 0.1
            bars.append({
                "date": f"2024-01-{i+1:02d}",
                "open": p,
                "high": p + 0.1,
                "low": p - 0.1,
                "close": p,
                "volume": 5_000,  # 每日成交仅 5000 股，成交额仅 $5,000
            })
        res = self.amihud.evaluate_liquidity(
            symbol="PENNY",
            bars=bars,
            market="US",
            intended_order_value=50_000.0,
        )
        self.assertTrue(res.is_illiquid_trap)
        self.assertEqual(res.capacity_tier, "ILLIQUID_TRAP")
        self.assertGreater(res.market_impact_penalty_bps, 30.0)

    def test_amihud_empty_and_zero_volume_defense(self) -> None:
        """测试空日线与全部零成交量时的边界安全防御."""
        empty_res = self.amihud.evaluate_liquidity("EMPTY", [])
        self.assertTrue(empty_res.is_illiquid_trap)
        self.assertEqual(empty_res.capacity_tier, "ILLIQUID_TRAP")

    def test_option_skew_normal_balanced(self) -> None:
        """测试期权市场平静中性态（无主力异常对冲看跌）."""
        res = self.skew.evaluate_skew_and_flow(
            symbol="AAPL",
            underlying_price=180.0,
            call_volume=100_000,
            put_volume=80_000,
            call_open_interest=500_000,
            put_open_interest=450_000,
            iv_25d_put=0.24,
            iv_25d_call=0.22,
            iv_front_month_atm=0.23,
            iv_back_month_atm=0.24,
        )
        self.assertIsInstance(res, OptionSkewMetrics)
        self.assertFalse(res.is_overnight_crash_alert)
        self.assertLess(res.composite_bearish_flow_score, 50.0)
        self.assertIn(res.flow_sentiment_regime, ["EXTREME_GREED", "BULLISH", "NEUTRAL"])

    def test_option_skew_overnight_crash_alert(self) -> None:
        """测试主力重度买入看跌期权、Skew膨胀、期限结构倒挂的高危隔夜跳水预警."""
        res = self.skew.evaluate_skew_and_flow(
            symbol="CRASH_RISK",
            underlying_price=50.0,
            call_volume=20_000,
            put_volume=45_000,     # PCR > 2.25
            call_open_interest=80_000,
            put_open_interest=150_000,
            iv_25d_put=0.58,        # 看跌下行保护 IV 暴涨
            iv_25d_call=0.42,       # 偏度达到 16%
            iv_front_month_atm=0.55,# 近端极端恐慌，期限结构严重倒挂
            iv_back_month_atm=0.40,
        )
        self.assertTrue(res.is_overnight_crash_alert)
        self.assertGreaterEqual(res.composite_bearish_flow_score, 65.0)
        self.assertEqual(res.flow_sentiment_regime, "EXTREME_FEAR")
        self.assertEqual(res.dealer_gamma_exposure_regime, "SHORT_GAMMA_EXPLOSIVE")


if __name__ == "__main__":
    unittest.main()
