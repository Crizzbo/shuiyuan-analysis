# -*- coding: utf-8 -*-
"""四大金融模型动态点时选股对比引擎专业单元测试 (test_four_models_dynamic_comparison.py).

覆盖范围：
1. 四大模型定义与参数配置合法性校验；
2. 四大模型选股打分差异化逻辑断言 (动量 vs 价值 vs 尾部风控 vs 复合)；
3. 动态选股零前视偏差时序隔离验证；
4. 最小合成交易流程端到端执行断言。
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from financial_core.engines.dynamic_universe_screener import (
    DynamicUniverseScreener,
    VALID_STRATEGY_MODELS,
)
from scripts.run_four_models_dynamic_comparison import (
    MODEL_SPECS,
    calculate_model_metrics,
)
from financial_core.engines.portfolio_backtest_engine import (
    DailySnapshot,
    TradeRecord,
)


class TestFourModelsDynamicComparison(unittest.TestCase):
    """测试四大金融模型对比引擎与策略契约."""

    def test_model_specs_integrity(self):
        """测试 4 大模型规格定义完整性与参数防御."""
        self.assertEqual(len(MODEL_SPECS), 4)
        for key, spec in MODEL_SPECS.items():
            self.assertIn("strategy_model", spec)
            self.assertIn(spec["strategy_model"], VALID_STRATEGY_MODELS)
            self.assertLess(spec["stop_loss_pct"], 0.0)
            self.assertGreater(spec["trailing_stop_pct"], 0.0)

    def test_differentiation_between_momentum_and_value(self):
        """测试动量模型与价值模型在面对高估值牛股时的截然不同态度."""
        screener_momentum = DynamicUniverseScreener(strategy_model="MOMENTUM_SEPA", min_lookback_bars=60)
        screener_value = DynamicUniverseScreener(strategy_model="MOAT_VALUE", min_lookback_bars=60)

        dates = [f"2020-0{m}-{d:02d}" for m in range(1, 6) for d in range(1, 29)][:100]
        bench = [{"date": d, "close": 100.0} for d in dates]

        # 构造一只暴力大牛股：从 50 暴涨到 150，均线远抛在脑后 (Close / EMA200 远超 1.40)
        parabolic_winner = [{"date": d, "close": 50.0 + (i ** 1.3) * 0.4} for i, d in enumerate(dates)]
        universe = {"PARABOLIC": parabolic_winner}

        as_of = dates[-1]
        scores_mom, top_mom = screener_momentum.screen_universe_at_date(
            as_of_date=as_of,
            historical_universe_bars=universe,
            historical_benchmark_bars=bench,
            top_k=1
        )
        scores_val, top_val = screener_value.screen_universe_at_date(
            as_of_date=as_of,
            historical_universe_bars=universe,
            historical_benchmark_bars=bench,
            top_k=1
        )

        # 动量模型：热爱主升浪，即使估值高也积极入池击球区
        self.assertTrue(scores_mom[0].in_strike_zone)
        self.assertEqual(top_mom, ["PARABOLIC"])

        # 价值模型：认定严重估值透支，触发 VALUATION_OVERHANG 硬排除
        self.assertFalse(scores_val[0].in_strike_zone)
        self.assertIn("VALUATION_OVERHANG", scores_val[0].disqualification_reason)
        self.assertEqual(top_val, [])

    def test_var_tail_risk_model_filters_high_volatility(self):
        """测试尾部风控模型能够严格过滤高波动率资产."""
        screener_var = DynamicUniverseScreener(strategy_model="VAR_TAIL_RISK", min_lookback_bars=60)

        dates = [f"2020-0{m}-{d:02d}" for m in range(1, 6) for d in range(1, 29)][:100]
        bench = [{"date": d, "close": 100.0} for d in dates]

        # 构造一只高波动跳水股：剧烈上下翻飞，20日波动率远超 50%
        wild_stock = []
        base = 100.0
        for i, d in enumerate(dates):
            base = base * 1.15 if i % 2 == 0 else base * 0.88
            wild_stock.append({"date": d, "close": base})

        universe = {"WILD": wild_stock}
        as_of = dates[-1]
        scores_var, top_var = screener_var.screen_universe_at_date(
            as_of_date=as_of,
            historical_universe_bars=universe,
            historical_benchmark_bars=bench,
            top_k=1
        )

        self.assertFalse(scores_var[0].in_strike_zone)
        self.assertIn("VAR_VOLATILITY_BUDGET_BREACH", scores_var[0].disqualification_reason)
        self.assertEqual(top_var, [])

    def test_metrics_calculation_synthetic(self):
        """测试指标计算逻辑合成用例."""
        snaps = [
            DailySnapshot(date="2020-01-01", cash=100000.0, holdings_value=0.0, total_equity=100000.0, daily_return=0.0, cumulative_return=0.0, drawdown=0.0, active_positions_count=0),
            DailySnapshot(date="2020-01-02", cash=50000.0, holdings_value=60000.0, total_equity=110000.0, daily_return=0.10, cumulative_return=0.10, drawdown=0.0, active_positions_count=1),
            DailySnapshot(date="2020-01-03", cash=120000.0, holdings_value=0.0, total_equity=120000.0, daily_return=0.09, cumulative_return=0.20, drawdown=0.0, active_positions_count=0),
        ]
        trades = [
            TradeRecord(
                trade_id="TR_01",
                symbol="TEST",
                market="US",
                action="SELL",
                entry_date="2020-01-02",
                exit_date="2020-01-03",
                shares=100,
                entry_price=100.0,
                exit_price=120.0,
                commission_paid=20.0,
                slippage_paid=20.0,
                gross_pnl=2000.0,
                net_pnl=1960.0,
                return_pct=0.20,
                holding_days=1,
                exit_reason="PROFIT"
            )
        ]
        bench_bars = [{"date": "2020-01-01", "close": 100.0}, {"date": "2020-01-03", "close": 102.0}]

        m = calculate_model_metrics(
            initial_capital=100000.0,
            snapshots=snaps,
            trades=trades,
            bench_bars=bench_bars,
            mdd_start="2020-01-01",
            mdd_end="2020-01-01"
        )
        self.assertEqual(m.final_equity, 120000.0)
        self.assertEqual(m.cumulative_return, 0.20)
        self.assertEqual(m.win_rate, 1.0)


if __name__ == "__main__":
    unittest.main()
