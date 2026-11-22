#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""多资产自适应选股路由引擎单元测试 (Unit Tests for MultiAssetScreeningEngine).

测试重点：
1. 资产分类与白名单/关键词启发式识别 (AssetClassClassifier);
2. 根治逻辑缺陷 2：GLD, SPY, SCHD, NEM 等优质防守与宏观资产不再被纯高成长 SEPA 30% 底部反弹或 4T VCP 规则一票误杀;
3. 验证四条量化路由通道（Growth, ETF, Gold, Dividend）各自的判定准则与打分逻辑;
4. 验证初筛构建器与排序器对多资产分类和分级榜单的完整承接与向后兼容性。
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from financial_core.engines.multi_asset_screening_engine import (
    AssetCategory,
    AssetClassClassifier,
    MultiAssetScreeningDecision,
    MultiAssetScreeningEngine,
    MultiAssetScreeningInput,
)
from finance_tools.screening.screening_candidate_ranker import (
    QualifiedCandidate,
    ScreeningCandidateRanker,
)
from finance_tools.screening.screening_universe_builder import (
    ScreeningUniverseBuilder,
    StockScreeningRecord,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestMultiAssetScreeningEngine(unittest.TestCase):
    """测试多资产自适应选股路由引擎与各资产专属漏斗."""

    def setUp(self):
        self.engine = MultiAssetScreeningEngine()
        self.classifier = AssetClassClassifier()

    def test_asset_class_classifier_static_and_heuristic(self):
        """测试代码白名单匹配与公司名称/行业启发式分类推导."""
        # 白名单精准命中
        self.assertEqual(self.classifier.classify("GLD"), AssetCategory.GOLD_AND_COMMODITY)
        self.assertEqual(self.classifier.classify("IAU"), AssetCategory.GOLD_AND_COMMODITY)
        self.assertEqual(self.classifier.classify("NEM"), AssetCategory.GOLD_AND_COMMODITY)
        self.assertEqual(self.classifier.classify("1326.T"), AssetCategory.GOLD_AND_COMMODITY)

        self.assertEqual(self.classifier.classify("SPY"), AssetCategory.BROAD_OR_SECTOR_ETF)
        self.assertEqual(self.classifier.classify("QQQ"), AssetCategory.BROAD_OR_SECTOR_ETF)
        self.assertEqual(self.classifier.classify("TLT"), AssetCategory.BROAD_OR_SECTOR_ETF)
        self.assertEqual(self.classifier.classify("1306.T"), AssetCategory.BROAD_OR_SECTOR_ETF)

        self.assertEqual(self.classifier.classify("SCHD"), AssetCategory.DIVIDEND_AND_DEFENSIVE)
        self.assertEqual(self.classifier.classify("XLU"), AssetCategory.DIVIDEND_AND_DEFENSIVE)
        self.assertEqual(self.classifier.classify("JNJ"), AssetCategory.DIVIDEND_AND_DEFENSIVE)
        self.assertEqual(self.classifier.classify("9432.T"), AssetCategory.DIVIDEND_AND_DEFENSIVE)

        self.assertEqual(self.classifier.classify("NVDA"), AssetCategory.GROWTH_EQUITY)
        self.assertEqual(self.classifier.classify("AAPL"), AssetCategory.GROWTH_EQUITY)
        self.assertEqual(self.classifier.classify("8035"), AssetCategory.GROWTH_EQUITY)

        # 启发式名称推导
        self.assertEqual(
            self.classifier.classify("XYZ", company_name="Global Physical Gold Trust"),
            AssetCategory.GOLD_AND_COMMODITY,
        )
        self.assertEqual(
            self.classifier.classify("ABC", company_name="Vanguard Total Market Index ETF"),
            AssetCategory.BROAD_OR_SECTOR_ETF,
        )
        self.assertEqual(
            self.classifier.classify("UTIL", company_name="Pacific Gas and Electric Power Co"),
            AssetCategory.DIVIDEND_AND_DEFENSIVE,
        )

        # 显式覆盖
        self.assertEqual(
            self.classifier.classify("NVDA", explicit_category=AssetCategory.BROAD_OR_SECTOR_ETF),
            AssetCategory.BROAD_OR_SECTOR_ETF,
        )

    def test_growth_equity_sepa_and_vcp(self):
        """测试成长股 SEPA 8 大指标与 VCP 4T 极窄收敛流程."""
        # 1. 黄金通过样例 (NVDA)
        nvda_inp = MultiAssetScreeningInput(
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            latest_price=145.0,
            ma50=132.0,
            ma150=120.0,
            ma200=110.0,
            ma200_20d_ago=106.0,
            high_52w=150.0,
            low_52w=48.0,
            volume_today=40000000,
            volume_50d_avg=45000000,
            volume_min_consolidation=18000000,
            base_duration_weeks=8,
            contraction_sequence=[25.0, 12.0, 5.0, 2.0],
            pivot_price=148.0,
        )
        res = self.engine.screen(nvda_inp)
        self.assertEqual(res.asset_category, AssetCategory.GROWTH_EQUITY.value)
        self.assertTrue(res.is_qualified)
        self.assertEqual(res.decision_action, "Stage_2_Pivot_Ready")
        self.assertGreaterEqual(res.composite_score, 75.0)

        # 2. 负面破位股 (INTC)
        intc_inp = MultiAssetScreeningInput(
            ticker="INTC",
            company_name="Intel Corporation",
            latest_price=22.0,
            ma50=24.0,
            ma150=28.0,
            ma200=34.0,
            ma200_20d_ago=35.0,
            high_52w=50.0,
            low_52w=18.0,
            volume_today=30000000,
            volume_50d_avg=32000000,
            volume_min_consolidation=25000000,
        )
        res_intc = self.engine.screen(intc_inp)
        self.assertFalse(res_intc.is_qualified)
        self.assertEqual(res_intc.decision_action, "Trend_Disqualified")

    def test_gold_and_commodity_rescued_from_false_kill(self):
        """核心验证：黄金 ETF (GLD) 在底部反弹不足 30% 时不再被机械误杀，成功准入 Gold_Macro_Ready."""
        # GLD 场景：最新价 242，52周低点 195 (涨幅 24.1% < 30%)，距高点 252 仅回撤 3.96%
        # 在老 SEPA 规则下因 24.1% < 30% 必然被一票误杀！
        gld_inp = MultiAssetScreeningInput(
            ticker="GLD",
            company_name="SPDR Gold Trust",
            latest_price=242.0,
            ma50=238.0,
            ma150=226.0,
            ma200=218.0,
            ma200_20d_ago=215.0,
            high_52w=252.0,
            low_52w=195.0,
            volume_today=8500000,
            volume_50d_avg=8200000,
            volume_min_consolidation=4100000,
            real_rate_10y_tips=1.85,
        )
        res = self.engine.screen(gld_inp)
        self.assertEqual(res.asset_category, AssetCategory.GOLD_AND_COMMODITY.value)
        self.assertTrue(res.is_qualified)
        self.assertEqual(res.decision_action, "Gold_Macro_Ready")
        self.assertTrue(res.trend_alignment_pass)
        self.assertTrue(res.channel_or_cycle_pass)
        self.assertIn("黄金/贵金属宏观中枢就绪", res.business_rationale_zh)

    def test_broad_or_sector_etf_rescued_from_false_kill(self):
        """核心验证：指数 ETF (SPY) 在底部反弹 26.5% (<30%) 时成功自适应准入 ETF_Trend_Ready."""
        spy_inp = MultiAssetScreeningInput(
            ticker="SPY",
            company_name="SPDR S&P 500 ETF Trust",
            latest_price=592.0,
            ma20=588.0,
            ma50=578.0,
            ma150=555.0,
            ma200=532.0,
            ma200_20d_ago=528.0,
            high_52w=602.0,
            low_52w=468.0,
            volume_today=45000000,
            volume_50d_avg=48000000,
            volume_min_consolidation=22000000,
        )
        res = self.engine.screen(spy_inp)
        self.assertEqual(res.asset_category, AssetCategory.BROAD_OR_SECTOR_ETF.value)
        self.assertTrue(res.is_qualified)
        self.assertEqual(res.decision_action, "ETF_Trend_Ready")
        self.assertTrue(res.risk_or_volatility_pass)
        self.assertIn("核心指数/行业 ETF 顺势通道就绪", res.business_rationale_zh)

    def test_dividend_and_defensive_moat_ready(self):
        """核心验证：高股息防御 ETF (SCHD) 稳健低 Beta 运行，成功准入 Dividend_Moat_Ready."""
        schd_inp = MultiAssetScreeningInput(
            ticker="SCHD",
            company_name="Schwab U.S. Dividend Equity ETF",
            latest_price=84.20,
            ma50=82.50,
            ma150=80.80,
            ma200=79.20,
            ma200_20d_ago=78.90,
            high_52w=85.50,
            low_52w=71.0,
            volume_today=3200000,
            volume_50d_avg=3500000,
            volume_min_consolidation=1800000,
            dividend_yield_pct=3.45,
        )
        res = self.engine.screen(schd_inp)
        self.assertEqual(res.asset_category, AssetCategory.DIVIDEND_AND_DEFENSIVE.value)
        self.assertTrue(res.is_qualified)
        self.assertEqual(res.decision_action, "Dividend_Moat_Ready")
        self.assertIn("高股息防御护城河就绪", res.business_rationale_zh)

    def test_screening_universe_builder_multi_asset_integration(self):
        """测试初筛资产池构建器全盘四维指标计算与多资产契约兼容性."""
        builder = ScreeningUniverseBuilder()

        # 1. 验证 GLD 计算与落盘结构
        rec_gld = builder.compute_screening_metrics(
            ticker="GLD",
            market="US",
            company_name="SPDR Gold Trust",
            cik_or_code="0001222333",
            as_of_date="2026-11-07",
            latest_price=242.0,
            ma50=238.0,
            ma150=226.0,
            ma200=218.0,
            ma200_20d_ago=215.0,
            high_52w=252.0,
            low_52w=195.0,
            volume_today=8500000,
            volume_50d_avg=8200000,
            volume_min_consolidation=4100000,
            real_rate_10y_tips=1.85,
        )
        self.assertIsInstance(rec_gld, StockScreeningRecord)
        self.assertEqual(rec_gld.asset_category, "Gold_And_Commodity")
        self.assertEqual(rec_gld.multi_asset_action, "Gold_Macro_Ready")
        self.assertTrue(rec_gld.sepa_qualification.overall_preliminary_pass)
        self.assertEqual(rec_gld.sepa_qualification.decision_action, "Stage_2_Pivot_Ready")
        d = rec_gld.to_dict()
        self.assertEqual(d["asset_category"], "Gold_And_Commodity")
        self.assertEqual(d["multi_asset_action"], "Gold_Macro_Ready")

        # 2. 验证 SPY 计算与落盘结构
        rec_spy = builder.compute_screening_metrics(
            ticker="SPY",
            market="US",
            company_name="SPDR S&P 500 ETF Trust",
            cik_or_code="0000884394",
            as_of_date="2026-11-07",
            latest_price=592.0,
            ma50=578.0,
            ma150=555.0,
            ma200=532.0,
            ma200_20d_ago=528.0,
            high_52w=602.0,
            low_52w=468.0,
            volume_today=45000000,
            volume_50d_avg=48000000,
            volume_min_consolidation=22000000,
        )
        self.assertEqual(rec_spy.asset_category, "Broad_Or_Sector_ETF")
        self.assertEqual(rec_spy.multi_asset_action, "ETF_Trend_Ready")
        self.assertTrue(rec_spy.sepa_qualification.overall_preliminary_pass)

        # 3. 验证 SCHD 计算与落盘结构
        rec_schd = builder.compute_screening_metrics(
            ticker="SCHD",
            market="US",
            company_name="Schwab U.S. Dividend Equity ETF",
            cik_or_code="0001509378",
            as_of_date="2026-11-07",
            latest_price=84.20,
            ma50=82.50,
            ma150=80.80,
            ma200=79.20,
            ma200_20d_ago=78.90,
            high_52w=85.50,
            low_52w=71.0,
            volume_today=3200000,
            volume_50d_avg=3500000,
            volume_min_consolidation=1800000,
            dividend_yield_pct=3.45,
        )
        self.assertEqual(rec_schd.asset_category, "Dividend_And_Defensive")
        self.assertEqual(rec_schd.multi_asset_action, "Dividend_Moat_Ready")
        self.assertTrue(rec_schd.sepa_qualification.overall_preliminary_pass)

        # 4. 验证黄金打样全集构建 (包含 9 大样本)
        samples = builder.generate_golden_samples()
        self.assertEqual(len(samples), 9)
        tickers = [s.ticker for s in samples]
        self.assertIn("NVDA", tickers)
        self.assertIn("GLD", tickers)
        self.assertIn("SPY", tickers)
        self.assertIn("SCHD", tickers)
        self.assertIn("NEM", tickers)
        self.assertIn("INTC", tickers)

        # 验证合格率：前 4 只成长 + 4 只多资产宏观合格，仅 INTC 否决
        passes = [s for s in samples if s.sepa_qualification.overall_preliminary_pass]
        self.assertEqual(len(passes), 8)

    def test_candidate_ranker_multi_asset_aggregation(self):
        """测试候选池聚合排序器正确按资产类别分类并输出."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            results_dir = tmp_root / "screening" / "results"
            results_dir.mkdir(parents=True, exist_ok=True)

            mock_results = {
                "chunk_name": "screened_mock.json",
                "market": "US",
                "records": [
                    {
                        "ticker": "NVDA",
                        "market": "US",
                        "company_name": "NVIDIA",
                        "asset_category": "Growth_Equity",
                        "multi_asset_action": "Stage_2_Pivot_Ready",
                        "price_and_moving_averages": {"latest_price": 145.0},
                        "cycle_and_high_low_positions": {"gain_from_52w_low_pct": 200.0, "pullback_from_52w_high_pct": 3.0},
                        "volume_and_supply_dryup": {"dryup_ratio": 0.40},
                        "vcp_pattern_footprints": {"pivot_price": 148.0, "contraction_sequence": [20.0, 10.0, 3.0]},
                        "sepa_qualification": {"decision_action": "Stage_2_Pivot_Ready", "business_rationale_zh": "成长主升"},
                    },
                    {
                        "ticker": "GLD",
                        "market": "US",
                        "company_name": "SPDR Gold Trust",
                        "asset_category": "Gold_And_Commodity",
                        "multi_asset_action": "Gold_Macro_Ready",
                        "price_and_moving_averages": {"latest_price": 242.0},
                        "cycle_and_high_low_positions": {"gain_from_52w_low_pct": 24.0, "pullback_from_52w_high_pct": 4.0},
                        "volume_and_supply_dryup": {"dryup_ratio": 0.50},
                        "vcp_pattern_footprints": {"pivot_price": 245.0, "contraction_sequence": [10.0, 5.0, 2.5]},
                        "sepa_qualification": {"decision_action": "Stage_2_Pivot_Ready", "business_rationale_zh": "黄金宏观"},
                    },
                    {
                        "ticker": "SPY",
                        "market": "US",
                        "company_name": "SPDR S&P 500",
                        "asset_category": "Broad_Or_Sector_ETF",
                        "multi_asset_action": "ETF_Trend_Ready",
                        "price_and_moving_averages": {"latest_price": 592.0},
                        "cycle_and_high_low_positions": {"gain_from_52w_low_pct": 26.0, "pullback_from_52w_high_pct": 2.0},
                        "volume_and_supply_dryup": {"dryup_ratio": 0.45},
                        "vcp_pattern_footprints": {"pivot_price": 596.0, "contraction_sequence": [8.0, 4.0, 1.8]},
                        "sepa_qualification": {"decision_action": "Stage_2_Pivot_Ready", "business_rationale_zh": "指数顺势"},
                    },
                    {
                        "ticker": "SCHD",
                        "market": "US",
                        "company_name": "Schwab Dividend",
                        "asset_category": "Dividend_And_Defensive",
                        "multi_asset_action": "Dividend_Moat_Ready",
                        "price_and_moving_averages": {"latest_price": 84.0},
                        "cycle_and_high_low_positions": {"gain_from_52w_low_pct": 18.0, "pullback_from_52w_high_pct": 1.5},
                        "volume_and_supply_dryup": {"dryup_ratio": 0.50},
                        "vcp_pattern_footprints": {"pivot_price": 85.0, "contraction_sequence": [6.0, 3.0, 1.2]},
                        "sepa_qualification": {"decision_action": "Stage_2_Pivot_Ready", "business_rationale_zh": "高股息防御"},
                    },
                ],
            }
            res_file = results_dir / "screened_chunk_001.json"
            res_file.write_text(json.dumps(mock_results), encoding="utf-8")

            ranker = ScreeningCandidateRanker(data_root=tmp_root)
            aggregated = ranker.aggregate_and_rank_candidates()

            # 断言总账与分类指标
            self.assertEqual(aggregated["tier0_pivot_ready_count"], 4)
            cat_breakdown = aggregated["asset_category_breakdown"]
            self.assertEqual(cat_breakdown["Growth_Equity"], 1)
            self.assertEqual(cat_breakdown["Gold_And_Commodity"], 1)
            self.assertEqual(cat_breakdown["Broad_Or_Sector_ETF"], 1)
            self.assertEqual(cat_breakdown["Dividend_And_Defensive"], 1)

            categorized = aggregated["categorized_candidates"]
            self.assertEqual(len(categorized["growth_equity"]), 1)
            self.assertEqual(categorized["growth_equity"][0]["ticker"], "NVDA")
            self.assertEqual(len(categorized["gold_and_commodity"]), 1)
            self.assertEqual(categorized["gold_and_commodity"][0]["ticker"], "GLD")
            self.assertEqual(len(categorized["broad_or_sector_etf"]), 1)
            self.assertEqual(categorized["broad_or_sector_etf"][0]["ticker"], "SPY")
            self.assertEqual(len(categorized["dividend_and_defensive"]), 1)
            self.assertEqual(categorized["dividend_and_defensive"][0]["ticker"], "SCHD")


if __name__ == "__main__":
    unittest.main()
