#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""万家企业初筛批处理流水线与候选池排序单元测试 (Unit Tests for Batch Pipeline & Ranker)."""

import json
from pathlib import Path
import tempfile
import unittest

from finance_tools.screening_candidate_ranker import ScreeningCandidateRanker
from scripts.run_screening_universe_batch import ScreeningUniverseBatchPipeline

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestScreeningUniverseBatchPipeline(unittest.TestCase):
    """测试初筛批处理管道与断点续传检查点逻辑."""

    def test_pipeline_execution_and_checkpointing(self):
        """测试在临时目录下分块批处理执行、检查点更新与总账落盘."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            us_chunk_dir = tmp_root / "screening" / "us_10k"
            us_chunk_dir.mkdir(parents=True, exist_ok=True)

            # 构造模拟分块文件
            sample_chunk = {
                "market": "US",
                "chunk_index": 1,
                "total_items": 3,
                "items": [
                    {"ticker": "NVDA", "title": "NVIDIA Corp", "cik_str": 1045810},
                    {"ticker": "INTC", "title": "Intel Corp", "cik_str": 50863},
                    {"ticker": "TSM", "title": "TSMC", "cik_str": 1046179},
                ],
            }
            chunk_file = us_chunk_dir / "us_screening_chunk_001.json"
            chunk_file.write_text(json.dumps(sample_chunk), encoding="utf-8")

            pipeline = ScreeningUniverseBatchPipeline(data_root=tmp_root)
            summary = pipeline.run_pipeline(market_filter="US", max_chunks=1, verbose=False)

            self.assertEqual(summary["total_completed_chunks"], 1)
            self.assertEqual(summary["total_processed_companies"], 3)
            self.assertTrue(pipeline.checkpoint_file.exists())
            self.assertTrue(pipeline.summary_file.exists())

            # 验证断点续传跳过已完成批次
            checkpoint = pipeline.load_checkpoint()
            self.assertIn("us_screening_chunk_001.json", checkpoint["completed_chunks"])

            # 再次运行应跳过已完成批次
            summary2 = pipeline.run_pipeline(market_filter="US", max_chunks=1, verbose=False)
            self.assertEqual(summary2["performance_metrics"]["processed_this_run_chunks"], 0)

    def test_candidate_ranker(self):
        """测试候选池排序聚合器正确汇总与地量抽干度排序."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            results_dir = tmp_root / "screening" / "results"
            results_dir.mkdir(parents=True, exist_ok=True)

            mock_results = {
                "chunk_name": "mock_chunk_001.json",
                "market": "US",
                "records": [
                    {
                        "ticker": "WIN1",
                        "market": "US",
                        "company_name": "Winner 1 Corp",
                        "cik_or_code": "001",
                        "price_and_moving_averages": {"latest_price": 100.0},
                        "cycle_and_high_low_positions": {
                            "gain_from_52w_low_pct": 50.0,
                            "pullback_from_52w_high_pct": 5.0,
                        },
                        "volume_and_supply_dryup": {"dryup_ratio": 0.30},
                        "vcp_pattern_footprints": {
                            "pivot_price": 102.0,
                            "vcp_code": "8W 24/2 4T",
                            "contraction_sequence": [24.0, 12.0, 5.0, 2.0],
                        },
                        "sepa_qualification": {
                            "decision_action": "Stage_2_Pivot_Ready",
                            "business_rationale_zh": "测试买点",
                        },
                    },
                    {
                        "ticker": "WATCH1",
                        "market": "US",
                        "company_name": "Watchlist 1 Corp",
                        "cik_or_code": "002",
                        "price_and_moving_averages": {"latest_price": 80.0},
                        "cycle_and_high_low_positions": {
                            "gain_from_52w_low_pct": 40.0,
                            "pullback_from_52w_high_pct": 10.0,
                        },
                        "volume_and_supply_dryup": {"dryup_ratio": 0.65},
                        "vcp_pattern_footprints": {
                            "pivot_price": 85.0,
                            "vcp_code": "8W 28/15 2T",
                            "contraction_sequence": [28.0, 15.0],
                        },
                        "sepa_qualification": {
                            "decision_action": "Watchlist_Forming",
                            "business_rationale_zh": "测试观察池",
                        },
                    },
                    {
                        "ticker": "FAIL1",
                        "market": "US",
                        "company_name": "Failed 1 Corp",
                        "cik_or_code": "003",
                        "sepa_qualification": {
                            "decision_action": "Trend_Disqualified",
                            "business_rationale_zh": "测试淘汰",
                        },
                    },
                ],
            }
            res_file = results_dir / "screened_mock_chunk_001.json"
            res_file.write_text(json.dumps(mock_results), encoding="utf-8")

            ranker = ScreeningCandidateRanker(data_root=tmp_root)
            ranked_data = ranker.aggregate_and_rank_candidates()

            self.assertEqual(ranked_data["source_result_chunks_count"], 1)
            self.assertEqual(ranked_data["tier0_pivot_ready_count"], 1)
            self.assertEqual(ranked_data["tier1_watchlist_count"], 1)
            self.assertEqual(ranked_data["pivot_ready_candidates"][0]["ticker"], "WIN1")
            self.assertEqual(ranked_data["watchlist_candidates"][0]["ticker"], "WATCH1")
            self.assertTrue(ranker.qualified_file.exists())


if __name__ == "__main__":
    unittest.main()
