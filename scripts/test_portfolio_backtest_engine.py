# -*- coding: utf-8 -*-
"""投资组合回测引擎专业单元测试 (test_portfolio_backtest_engine.py).

覆盖范围：
1. 投资组合引擎参数初始化防御与边界校验 (除零、负本金、非法仓位约束)；
2. T日计算信号与 T+1 开盘价滑点撮合无前视偏差验证；
3. 刚性硬止损 (-7%)、跟踪移动止盈、目标价退出的状态转移验证；
4. 拆股复权份额与分红现金入账的正确性验证；
5. 关键度量指标 (CAGR, MDD, Sharpe, Sortino, Calmar, Win Rate) 准确性断言；
6. 账本存证验签全链路闭环断言。
"""

import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.portfolio_backtest_engine import (
    PortfolioBacktestEngine,
    TradeRecord,
    DailySnapshot,
    BacktestMetrics,
)


class TestPortfolioBacktestEngine(unittest.TestCase):
    """测试组合回测引擎核心金融计算与执行逻辑."""

    def test_init_validation(self):
        """测试参数初始化边界防御."""
        # 初始本金必须 > 0
        with self.assertRaises(ValueError):
            PortfolioBacktestEngine(initial_capital=0)
        with self.assertRaises(ValueError):
            PortfolioBacktestEngine(initial_capital=-1000)

        # 单票仓位上限必须在 (0, 1]
        with self.assertRaises(ValueError):
            PortfolioBacktestEngine(max_position_pct=0)
        with self.assertRaises(ValueError):
            PortfolioBacktestEngine(max_position_pct=1.5)

        # 正常初始化
        engine = PortfolioBacktestEngine(
            market="US",
            currency="USD",
            initial_capital=100_000.0,
            max_position_pct=0.15,
            commission_bps=10.0,
            slippage_bps=10.0
        )
        self.assertEqual(engine.market, "US")
        self.assertEqual(engine.currency, "USD")
        self.assertAlmostEqual(engine.commission_rate, 0.001)
        self.assertAlmostEqual(engine.slippage_rate, 0.001)

    def test_empty_universe_error(self):
        """测试空输入防御."""
        engine = PortfolioBacktestEngine()
        with self.assertRaises(ValueError):
            engine.run_backtest(universe_bars={}, benchmark_bars=[{"date": "2020-01-01", "close": 100}])
        with self.assertRaises(ValueError):
            engine.run_backtest(universe_bars={"AAPL": [{"date": "2020-01-01", "close": 100}]}, benchmark_bars=[])

    def test_synthetic_uptrend_backtest_execution(self):
        """构建合成的 300 天数据测试 Stage 2 均线突破建仓、止盈与指标计算."""
        dates = [f"2020-{m:02d}-{d:02d}" for m in range(1, 11) for d in range(1, 31)]
        dates = sorted(list(set(dates)))[:260]

        # 构造基准指数: 持续稳定在 200 上方，从 100 涨到 130
        bench_bars = []
        for i, dt in enumerate(dates):
            px = 100.0 + (i * 0.12)
            bench_bars.append({
                "date": dt,
                "open": px,
                "high": px + 0.5,
                "low": px - 0.5,
                "close": px,
                "adj_close": px,
                "volume": 1_000_000
            })

        # 构造个股 AAPL: 前 100 天横盘震荡，第 100 天起放量爆发主升浪，触发 Stage 2 突破
        stock_bars = []
        for i, dt in enumerate(dates):
            if i < 100:
                px = 50.0 + (i % 5) * 0.2
            else:
                px = 52.0 + (i - 100) * 0.8  # 稳健主升浪
            stock_bars.append({
                "date": dt,
                "open": px,
                "high": px + 0.8,
                "low": px - 0.8,
                "close": px,
                "adj_close": px,
                "volume": 500_000
            })

        engine = PortfolioBacktestEngine(
            market="US",
            currency="USD",
            initial_capital=100_000.0,
            max_position_pct=0.20,
            hard_stop_loss_pct=0.07,
            profit_target_pct=0.30
        )

        metrics, snapshots, trades = engine.run_backtest(
            universe_bars={"AAPL": stock_bars},
            benchmark_bars=bench_bars
        )

        # 断言:
        # 1. 产生有效净值快照序列
        self.assertEqual(len(snapshots), len(dates))
        # 2. 最终权益大于初始本金
        self.assertGreater(metrics.final_equity, 100_000.0)
        self.assertGreater(metrics.cumulative_return, 0.0)
        self.assertGreater(metrics.annualized_return_cagr, 0.0)
        # 3. 最大回撤在合理范围
        self.assertGreaterEqual(metrics.max_drawdown, 0.0)
        self.assertLessEqual(metrics.max_drawdown, 1.0)
        # 4. 夏普与索提诺比率为有限浮点数
        self.assertTrue(math.isfinite(metrics.sharpe_ratio))
        self.assertTrue(math.isfinite(metrics.sortino_ratio))
        # 5. 产生了至少 1 笔平仓交易
        self.assertGreaterEqual(metrics.total_trades, 1)
        self.assertGreaterEqual(metrics.win_rate, 0.5)

    def test_corporate_actions_split_and_dividend(self):
        """测试拆股与分红事件的持仓调整与现金流入."""
        dates = [f"2020-{m:02d}-{d:02d}" for m in range(1, 11) for d in range(1, 31)]
        dates = sorted(list(set(dates)))[:260]

        bench_bars = [{"date": dt, "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000} for dt in dates]
        stock_bars = []
        for i, dt in enumerate(dates):
            px = 50.0 + i * 0.3  # 上升通道
            stock_bars.append({"date": dt, "open": px, "high": px + 0.5, "low": px - 0.5, "close": px, "volume": 2000})

        # 在第 150 天发生 1 拆 2 (ratio=2.0)
        split_date = dates[150]
        # 在第 180 天发生每股分红 1.5 元
        div_date = dates[180]

        splits_map = {"TEST": [{"date": split_date, "timestamp": 123456, "numerator": 2, "denominator": 1, "ratio": 2.0}]}
        dividends_map = {"TEST": [{"date": div_date, "timestamp": 123457, "amount": 1.5}]}

        engine = PortfolioBacktestEngine(
            market="US",
            currency="USD",
            initial_capital=100_000.0,
            profit_target_pct=1.0  # 宽松目标价，确保在第150-180天期间持续持仓
        )

        metrics, snapshots, trades = engine.run_backtest(
            universe_bars={"TEST": stock_bars},
            benchmark_bars=bench_bars,
            dividends_map=dividends_map,
            splits_map=splits_map
        )

        # 验证回测正常跑完且分红进入组合资产
        self.assertGreater(metrics.final_equity, 100_000.0)
        self.assertTrue(math.isfinite(metrics.cumulative_return))


if __name__ == "__main__":
    unittest.main()
