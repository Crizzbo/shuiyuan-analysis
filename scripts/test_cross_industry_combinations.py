# -*- coding: utf-8 -*-
"""跨行业多模型组合全息回测单元测试 (test_cross_industry_combinations.py).

覆盖范围：
1. 6 大行业与标的配置完整性验证 (无重复代码、双市场标的健全)；
2. 4 类量化买方策略契约定义完整性验证；
3. 微型合成矩阵回测流程与指标聚合断言；
4. 矩阵报告 Markdown 渲染逻辑与防除零断言。
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from scripts.run_cross_industry_model_combinations import (
    SECTOR_DEFINITIONS,
    STRATEGY_MODES,
    generate_cross_industry_report,
)
from financial_core.engines.portfolio_backtest_engine import (
    PortfolioBacktestEngine,
    BacktestMetrics,
)


class TestCrossIndustryCombinations(unittest.TestCase):
    """跨行业多策略回测调度器测试套件."""

    def test_sector_definitions_integrity(self):
        """断言 6 大支柱行业定义完整无遗漏."""
        self.assertEqual(len(SECTOR_DEFINITIONS), 6)
        all_symbols = set()
        expected_sectors = {
            "Technology_Semiconductor",
            "Healthcare_Biotech",
            "Consumer_Retail",
            "Industrial_Machinery",
            "Energy_Commodities",
            "Financial_Services"
        }
        actual_sectors = {sec["sector_id"] for sec in SECTOR_DEFINITIONS}
        self.assertEqual(actual_sectors, expected_sectors)

        for sec in SECTOR_DEFINITIONS:
            self.assertTrue(len(sec["us_symbols"]) >= 1, f"{sec['sector_id']} 缺少美股标的")
            self.assertTrue(len(sec["jp_symbols"]) >= 1, f"{sec['sector_id']} 缺少日股标的")
            self.assertTrue(sec["sector_name_zh"])
            self.assertTrue(sec["characteristic"])

            for s in sec["us_symbols"] + sec["jp_symbols"]:
                self.assertNotIn(s, all_symbols, f"标的 {s} 在多个行业中重复出现")
                all_symbols.add(s)

        self.assertEqual(len(all_symbols), 18)

    def test_strategy_modes_integrity(self):
        """断言 4 大买方策略模式完整."""
        self.assertEqual(len(STRATEGY_MODES), 4)
        modes = {strat["mode"] for strat in STRATEGY_MODES}
        expected_modes = {"MOMENTUM_SEPA", "MOAT_VALUE", "VAR_TAIL_RISK", "FULL_QUANTAMENTAL"}
        self.assertEqual(modes, expected_modes)

    def test_synthetic_cross_industry_backtest_flow(self):
        """通过微型合成数据验证跨策略回测与指标输出."""
        # 构造合成基准与单票 (需 >= 250 天以满足 EMA200 与指标计算窗口)
        dates = [f"2020-{m:02d}-{d:02d}" for m in range(1, 12) for d in range(1, 29)]
        dates = sorted(list(set(dates)))[:280]
        bench_bars = [{"date": d, "open": 100.0 + i * 0.1, "high": 102.0 + i * 0.1, "low": 99.0 + i * 0.1, "close": 100.5 + i * 0.1, "adj_close": 100.5 + i * 0.1, "volume": 10000} for i, d in enumerate(dates)]
        stock_bars = [{"date": d, "open": 50.0 + i * 0.2, "high": 52.0 + i * 0.2, "low": 49.0 + i * 0.2, "close": 51.0 + i * 0.2, "adj_close": 51.0 + i * 0.2, "volume": 5000} for i, d in enumerate(dates)]

        for strat_mode in ["MOMENTUM_SEPA", "MOAT_VALUE", "VAR_TAIL_RISK", "FULL_QUANTAMENTAL"]:
            engine = PortfolioBacktestEngine(
                market="US",
                currency="USD",
                strategy_mode=strat_mode,
                initial_capital=50_000.0,
                max_position_pct=0.5,
                commission_bps=10.0,
                slippage_bps=10.0
            )
            metrics, snaps, trades = engine.run_backtest(
                universe_bars={"TEST_STOCK": stock_bars},
                benchmark_bars=bench_bars,
                dividends_map={"TEST_STOCK": []},
                splits_map={"TEST_STOCK": []}
            )
            self.assertIsInstance(metrics, BacktestMetrics)
            self.assertGreater(metrics.final_equity, 0.0)
            self.assertIsNotNone(metrics.annualized_return_cagr)

    def test_matrix_report_generation(self):
        """测试研报 Markdown 渲染与格式防御."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir)
            fake_matrix_results = []
            for sec in SECTOR_DEFINITIONS:
                for strat in STRATEGY_MODES:
                    fake_matrix_results.append({
                        "sector_id": sec["sector_id"],
                        "sector_name_zh": sec["sector_name_zh"],
                        "sector_type": sec["sector_type"],
                        "strategy_mode": strat["mode"],
                        "strategy_name_zh": strat["name_zh"],
                        "composite": {
                            "avg_cagr": 0.155,
                            "avg_alpha": 0.082,
                            "worst_mdd": 0.125,
                            "avg_sharpe": 1.12,
                            "total_trades": 10,
                            "win_rate": 0.60
                        }
                    })

            stamp = "TEST_CAPTURE_STAMP"
            report_path = generate_cross_industry_report(fake_matrix_results, stamp, out_dir)
            self.assertTrue(report_path.exists())
            content = report_path.read_text(encoding="utf-8")
            self.assertIn("全球核心 6 大行业 × 4 类买方模型组合全息回测与收益验证报告", content)
            self.assertIn("科技与先进半导体行业", content)
            self.assertIn("医疗健康与生物制药行业", content)
            self.assertIn("CAGR: **+15.5%**", content)


if __name__ == "__main__":
    unittest.main()
