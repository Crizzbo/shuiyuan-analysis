# -*- coding: utf-8 -*-
"""买方宏观市场状态机与自适应策略切换引擎单元测试 (test_market_regime_switching.py).

覆盖范围：
1. 引擎初始化参数合法性与边界防御断言；
2. 牛市主升浪形态判别 (BULL_MOMENTUM -> MOMENTUM_SEPA)；
3. 危机暴跌与波动率飙升防守判别 (CRISIS_DEFENSE -> VAR_TAIL_RISK)；
4. 震荡筑底中性区间判别 (RANGE_BOUND_VALUE -> MOAT_VALUE)；
5. 点时零前视偏差截断机制断言。
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.market_regime_switching_engine import (
    MarketRegimeSwitchingEngine,
    MarketRegime,
    MarketRegimeVerdict,
)


class TestMarketRegimeSwitching(unittest.TestCase):
    """测试宏观状态机与自适应策略切换机制."""

    def setUp(self):
        self.engine = MarketRegimeSwitchingEngine(
            vol_crisis_threshold=0.28,
            vol_calm_threshold=0.22,
            min_benchmark_bars=60
        )

    def test_parameter_validation(self):
        """测试参数非法值防御断言."""
        with self.assertRaises(ValueError):
            MarketRegimeSwitchingEngine(vol_crisis_threshold=0.20, vol_calm_threshold=0.25)
        with self.assertRaises(ValueError):
            MarketRegimeSwitchingEngine(min_benchmark_bars=10)

    def test_bull_momentum_detection(self):
        """测试牛市主升浪状态判定与切换到模型 A."""
        # 构造一条持续温和上涨、均线多头排列且低波动的 SPY 序列
        dates = [f"2020-0{m}-{d:02d}" for m in range(1, 6) for d in range(1, 29)][:100]
        # 价格从 100 平稳上涨到 140
        bench_bars = [{"date": d, "close": 100.0 + i * 0.4} for i, d in enumerate(dates)]

        verdict = self.engine.detect_regime(
            as_of_date=dates[-1],
            historical_benchmark_bars=bench_bars
        )
        self.assertEqual(verdict.regime, MarketRegime.BULL_MOMENTUM)
        self.assertEqual(verdict.selected_strategy_model, "MOMENTUM_SEPA")
        self.assertEqual(verdict.stop_loss_pct, -0.07)
        self.assertEqual(verdict.trailing_stop_pct, 0.15)
        self.assertIn("牛市主升", verdict.rationale_zh)

    def test_crisis_defense_detection_on_breakdown(self):
        """测试大盘破位暴跌时切换到模型 C (尾部风控)."""
        dates = [f"2020-0{m}-{d:02d}" for m in range(1, 6) for d in range(1, 29)][:100]
        # 前 80 天在 150，最后 20 天闪崩断崖式下跌到 80
        bench_bars = []
        for i, d in enumerate(dates):
            p = 150.0 if i < 80 else (150.0 - (i - 79) * 3.5)
            bench_bars.append({"date": d, "close": p})

        verdict = self.engine.detect_regime(
            as_of_date=dates[-1],
            historical_benchmark_bars=bench_bars
        )
        self.assertEqual(verdict.regime, MarketRegime.CRISIS_DEFENSE)
        self.assertEqual(verdict.selected_strategy_model, "VAR_TAIL_RISK")
        self.assertEqual(verdict.stop_loss_pct, -0.05)
        self.assertEqual(verdict.trailing_stop_pct, 0.10)
        self.assertIn("危机避险", verdict.rationale_zh)

    def test_range_bound_value_detection(self):
        """测试大盘宽幅震荡消化期切换到模型 B (护城河价值)."""
        import math
        dates = [f"2020-0{m}-{d:02d}" for m in range(1, 6) for d in range(1, 29)][:100]
        # 构造一条先温和上涨到 115，随后在 105 附近横盘整理、回踩至 EMA50 下方的温和震荡日线
        bench_bars = []
        for i, d in enumerate(dates):
            if i < 60:
                p = 100.0 + i * 0.25  # 缓慢攀升到 115
            else:
                # 在 106 附近温和窄幅拉锯 (EMA200 还在 102 附近，EMA50 在 110 附近，价格在 106 处于二者之间)
                p = 106.0 + math.sin(i) * 0.8
            bench_bars.append({"date": d, "close": p})

        verdict = self.engine.detect_regime(
            as_of_date=dates[-1],
            historical_benchmark_bars=bench_bars
        )
        self.assertEqual(verdict.regime, MarketRegime.RANGE_BOUND_VALUE)
        self.assertEqual(verdict.selected_strategy_model, "MOAT_VALUE")
        self.assertEqual(verdict.stop_loss_pct, -0.10)
        self.assertEqual(verdict.trailing_stop_pct, 0.20)
        self.assertIn("震荡中性", verdict.rationale_zh)

    def test_point_in_time_truncation_no_lookahead(self):
        """测试零前视偏差时序隔离截断."""
        dates = [f"2020-0{m}-{d:02d}" for m in range(1, 6) for d in range(1, 29)][:100]
        bench_bars = [{"date": d, "close": 100.0 + i * 0.4} for i, d in enumerate(dates)]
        # 在截面后注入未来大暴跌数据
        bench_bars_with_future = list(bench_bars)
        bench_bars_with_future.append({"date": "2020-07-01", "close": 10.0})
        bench_bars_with_future.append({"date": "2020-07-02", "close": 5.0})

        # 在 2020-04-15 截面上判别
        verdict = self.engine.detect_regime(
            as_of_date="2020-04-15",
            historical_benchmark_bars=bench_bars_with_future
        )
        # 截面上大盘仍在牛市上涨，绝不受未来7月崩盘的影响
        self.assertEqual(verdict.regime, MarketRegime.BULL_MOMENTUM)
        self.assertEqual(verdict.selected_strategy_model, "MOMENTUM_SEPA")


if __name__ == "__main__":
    unittest.main()
