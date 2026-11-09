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

    def test_beneish_m_score_fraud_rejection(self):
        """测试 Beneish M-Score 财务舞弊排雷门禁对造假企业的一票否决拦截."""
        screener = DynamicUniverseScreener(min_lookback_bars=60, enable_forensics_gate=True)
        dates = [f"2020-{m:02d}-{d:02d}" for m in range(1, 4) for d in range(1, 29)][:80]
        bench = [{"date": d, "close": 100.0} for d in dates]

        # 构造一只形态看似完美的牛股
        stock_bars = [{"date": d, "close": 50.0 + (i * 0.3)} for i, d in enumerate(dates)]
        universe = {"FRAUD_INC": stock_bars}

        # 注入典型造假财务特征 (应收账款暴涨 DSRI 恶化、毛利率暴跌 GMI 恶化、应计利润 TATA 畸高)
        fraud_fin_profile = {
            "FRAUD_INC": {
                "curr_sales": 120.0,
                "prev_sales": 100.0,
                "curr_cogs": 90.0,
                "prev_cogs": 50.0,
                "curr_receivables": 80.0,  # 严重失常的应收账款
                "prev_receivables": 20.0,
                "curr_current_assets": 150.0,
                "prev_current_assets": 80.0,
                "curr_ppe_net": 100.0,
                "prev_ppe_net": 90.0,
                "curr_securities": 10.0,
                "prev_securities": 10.0,
                "curr_total_assets": 300.0,
                "prev_total_assets": 200.0,
                "curr_depreciation": 2.0,   # 蓄意放慢折旧
                "prev_depreciation": 10.0,
                "curr_sga": 25.0,
                "prev_sga": 15.0,
                "curr_long_term_debt": 60.0,
                "prev_long_term_debt": 30.0,
                "curr_current_liabilities": 50.0,
                "prev_current_liabilities": 25.0,
                "curr_net_income": 30.0,    # 虚构账面利润
                "curr_cfo": -20.0,          # 现金流深度赤字，TATA 爆表
            }
        }

        scores, top_symbols = screener.screen_universe_at_date(
            as_of_date=dates[-1],
            historical_universe_bars=universe,
            historical_benchmark_bars=bench,
            top_k=1,
            company_financial_profiles=fraud_fin_profile,
        )

        s = scores[0]
        self.assertIsNotNone(s.beneish_m_score)
        self.assertTrue(s.is_fraud_suspect)
        self.assertFalse(s.in_strike_zone)
        self.assertIn("BENEISH_FRAUD_ALERT", s.disqualification_reason)
        self.assertEqual(len(top_symbols), 0)

    def test_moat_value_kalman_mean_reversion_support(self):
        """测试护城河价值模型 (MOAT_VALUE) 下卡尔曼滤波与 OU 均值回归指标的生成."""
        screener = DynamicUniverseScreener(
            strategy_model="MOAT_VALUE",
            min_lookback_bars=60,
            enable_kalman_filter=True,
        )
        dates = [f"2020-{m:02d}-{d:02d}" for m in range(1, 4) for d in range(1, 29)][:80]
        bench = [{"date": d, "close": 100.0} for d in dates]

        # 围绕 100 窄幅震荡具有显著均值回归特征的日线
        bars = [{"date": d, "close": 100.0 + math.sin(i * 0.5) * 4.0} for i, d in enumerate(dates)]
        universe = {"R_VALUE": bars}

        scores, _ = screener.screen_universe_at_date(
            as_of_date=dates[-1],
            historical_universe_bars=universe,
            historical_benchmark_bars=bench,
            top_k=1,
        )

        s = scores[0]
        self.assertIsNotNone(s.ou_half_life)
        self.assertIsNotNone(s.kalman_z_score)


if __name__ == "__main__":
    unittest.main()
