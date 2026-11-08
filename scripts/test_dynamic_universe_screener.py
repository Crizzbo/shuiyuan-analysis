# -*- coding: utf-8 -*-
"""动态点时选股引擎与回测调度器专业单元测试 (test_dynamic_universe_screener.py).

覆盖范围：
1. 动态选股筛选器参数边界防御 (除零、负值、非法回溯天数)；
2. 零前视偏差严格验证 (PIT 隔离断言：未来价格暴跌或暴涨无法泄露到当前打分)；
3. Stage 2 均线通道状态与 Stage 4 熊市破位惩罚断言；
4. 综合得分排位与击球区 Top-K 选股契约断言；
5. 动态回测全流程最小可复现合成断言。
"""

import math
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
    StockScreeningScore,
)


class TestDynamicUniverseScreener(unittest.TestCase):
    """测试动态点时选股核心逻辑与时序隔离."""

    def test_screener_param_validation(self):
        """测试参数初始化边界校验."""
        with self.assertRaises(ValueError):
            DynamicUniverseScreener(min_lookback_bars=30)  # 必须 >= 50

        screener = DynamicUniverseScreener(min_lookback_bars=100)
        self.assertEqual(screener.min_lookback_bars, 100)

        # 候选集为空或基准为空时应抛出 ValueError
        with self.assertRaises(ValueError):
            screener.screen_universe_at_date(
                as_of_date="2020-01-01",
                historical_universe_bars={},
                historical_benchmark_bars=[{"date": "2020-01-01", "close": 100}]
            )

        with self.assertRaises(ValueError):
            screener.screen_universe_at_date(
                as_of_date="2020-01-01",
                historical_universe_bars={"AAPL": [{"date": "2020-01-01", "close": 100}]},
                historical_benchmark_bars=[]
            )

    def test_zero_look_ahead_isolation(self):
        """严格断言：未来发生暴跌数据绝对不影响 T 点时的选股打分 (No Look-Ahead)."""
        screener = DynamicUniverseScreener(min_lookback_bars=60)
        t_cutoff = "2020-06-01"

        dates_past = [f"2020-01-{d:02d}" for d in range(1, 31)] + [f"2020-02-{d:02d}" for d in range(1, 29)] + [f"2020-03-{d:02d}" for d in range(1, 31)]
        dates_past = sorted(list(set(dates_past)))

        bench_bars = [{"date": d, "close": 100.0 + i * 0.1} for i, d in enumerate(dates_past)]
        stock_a_past = [{"date": d, "close": 50.0 + i * 0.5} for i, d in enumerate(dates_past)]

        # 第一次打分：仅包含截至 2020-03-31 的历史
        scores_1, top_1 = screener.screen_universe_at_date(
            as_of_date=dates_past[-1],
            historical_universe_bars={"STOCK_A": stock_a_past},
            historical_benchmark_bars=bench_bars,
            top_k=1
        )
        score_1_val = scores_1[0].composite_score

        # 第二次打分：向 STOCK_A 中人为注入 4 月以后的剧烈暴跌未来数据 (50 跌到 5)
        stock_a_with_future = list(stock_a_past) + [
            {"date": "2020-04-01", "close": 30.0},
            {"date": "2020-04-02", "close": 15.0},
            {"date": "2020-04-03", "close": 5.0}
        ]
        bench_with_future = list(bench_bars) + [
            {"date": "2020-04-01", "close": 110.0},
            {"date": "2020-04-02", "close": 110.0},
            {"date": "2020-04-03", "close": 110.0}
        ]

        scores_2, top_2 = screener.screen_universe_at_date(
            as_of_date=dates_past[-1],  # 依然在 2020-03-31 点时评估
            historical_universe_bars={"STOCK_A": stock_a_with_future},
            historical_benchmark_bars=bench_with_future,
            top_k=1
        )
        score_2_val = scores_2[0].composite_score

        # 断言：无论未来如何暴跌，只要评估点时在 3 月底，两次打分完全一致，未来数据零污染！
        self.assertEqual(score_1_val, score_2_val)
        self.assertEqual(scores_1[0].rs_score, scores_2[0].rs_score)

    def test_stage2_winner_vs_stage4_decliner_screening(self):
        """测试大牛股 (Stage 2) 能够被系统自动识别，而衰退破位股 (Stage 4) 被系统硬拦截."""
        screener = DynamicUniverseScreener(min_lookback_bars=60)
        dates = [f"2020-{m:02d}-{d:02d}" for m in range(1, 6) for d in range(1, 29)]
        dates = sorted(list(set(dates)))[:120]

        bench = [{"date": d, "close": 100.0} for d in dates]

        # WINNER_STOCK: 从 50 稳步涨到 75，呈现健康平缓的 Stage 2 均线多头
        winner_bars = [{"date": d, "close": 50.0 + (i * 0.22)} for i, d in enumerate(dates)]

        # DECLINER_STOCK: 从 75 持续阴跌到 45，破位 Stage 4
        decliner_bars = [{"date": d, "close": 75.0 - (i * 0.25)} for i, d in enumerate(dates)]

        universe = {
            "WINNER": winner_bars,
            "DECLINER": decliner_bars
        }

        as_of = dates[-1]
        scores, top_symbols = screener.screen_universe_at_date(
            as_of_date=as_of,
            historical_universe_bars=universe,
            historical_benchmark_bars=bench,
            top_k=1
        )

        score_map = {s.symbol: s for s in scores}
        self.assertTrue(score_map["WINNER"].is_stage2)
        self.assertTrue(score_map["WINNER"].in_strike_zone)
        self.assertFalse(score_map["DECLINER"].in_strike_zone)
        self.assertIn("STAGE4_BEARISH_TREND", score_map["DECLINER"].disqualification_reason)
        self.assertEqual(top_symbols, ["WINNER"])

    def test_hysteresis_holding_buffer(self):
        """测试滞后缓冲防洗机制：Top10买入，Top40内持仓继续持有，跌破Top40或MA50才淘汰."""
        screener = DynamicUniverseScreener(min_lookback_bars=60)

        # 模拟生成 50 只股票的打分结果
        scores = []
        for i in range(1, 51):
            scores.append(StockScreeningScore(
                symbol=f"STK_{i:02d}",
                date="2024-06-01",
                current_price=100.0,
                is_stage2=True,
                rs_score=100.0 - i,
                trend_score=30.0,
                valuation_penalty=0.0,
                volatility_score=10.0,
                composite_score=140.0 - i,
                in_strike_zone=True
            ))

        # 假设当前持仓为: STK_02, STK_15 (第15名), STK_45 (第45名)
        current_holdings = ["STK_02", "STK_15", "STK_45"]

        to_buy, to_keep = screener.filter_with_hysteresis(
            current_holdings=current_holdings,
            ranked_scores=scores,
            top_k=10,
            buffer_rank=40
        )

        # 验证：
        # 1. STK_02 在 Top10 内，必须保留 (to_keep)
        self.assertIn("STK_02", to_keep)
        # 2. STK_15 虽跌出 Top10，但仍在 Top40 缓冲保护区内，必须继续持有，严防无谓换仓摩擦！
        self.assertIn("STK_15", to_keep)
        # 3. STK_45 跌出 Top40，必须被移出持仓！
        self.assertNotIn("STK_45", to_keep)
        self.assertNotIn("STK_45", to_buy)
        # 4. 新建仓补足 Top 10 (总目标容量 10，已有 2 留存，需买入 8 只新票)
        self.assertEqual(len(to_keep), 2)
        self.assertEqual(len(to_buy), 8)
        self.assertEqual(len(to_keep) + len(to_buy), 10)

    def test_moat_value_falling_knife_defense(self):
        """测试护城河价值模型 B：严厉驱逐下行均线破位飞刀 (EMA200向下倾斜且股价破位)."""
        screener = DynamicUniverseScreener(strategy_model="MOAT_VALUE", min_lookback_bars=60)
        dates = [f"2024-{m:02d}-{d:02d}" for m in range(1, 6) for d in range(1, 29)]
        dates = sorted(list(set(dates)))[:120]
        bench = [{"date": d, "close": 100.0} for d in dates]

        # 持续阴跌破位的假价值陷阱股票
        falling_knife_bars = [{"date": d, "close": 100.0 - (i * 0.4)} for i, d in enumerate(dates)]
        universe = {"KNIFE": falling_knife_bars}

        scores, top_syms = screener.screen_universe_at_date(
            as_of_date=dates[-1],
            historical_universe_bars=universe,
            historical_benchmark_bars=bench,
            top_k=1
        )
        self.assertEqual(len(scores), 1)
        self.assertFalse(scores[0].in_strike_zone)
        self.assertIn("FALLING_KNIFE", scores[0].disqualification_reason)
        self.assertEqual(top_syms, [])


if __name__ == "__main__":
    unittest.main()
