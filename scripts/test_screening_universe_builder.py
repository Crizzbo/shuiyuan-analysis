#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""万家股票初筛资产池构建器单元测试 (Unit Tests for ScreeningUniverseBuilder)."""

import json
from pathlib import Path
import tempfile
import unittest

from finance_tools.screening_universe_builder import (
    ScreeningUniverseBuilder,
    StockScreeningRecord,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestScreeningUniverseBuilder(unittest.TestCase):
    """测试初筛资产池构建与四维指标计算引擎."""

    def setUp(self):
        self.builder = ScreeningUniverseBuilder()

    def test_compute_screening_metrics_golden_pass(self):
        """测试四维初筛指标计算：符合第二阶段主升浪与 VCP 就绪."""
        record = self.builder.compute_screening_metrics(
            ticker="NVDA",
            market="US",
            company_name="NVIDIA Corp",
            cik_or_code="0001045810",
            as_of_date="2026-11-07",
            latest_price=140.0,
            ma50=130.0,
            ma150=120.0,
            ma200=110.0,
            ma200_20d_ago=105.0,
            high_52w=145.0,
            low_52w=50.0,
            volume_today=40000000,
            volume_50d_avg=45000000,
            volume_min_consolidation=18000000,
            base_duration_weeks=8,
            contraction_sequence=[25.0, 12.0, 5.0, 2.0],
            pivot_price=142.0,
        )

        self.assertIsInstance(record, StockScreeningRecord)
        # ① 价格与均线系统
        self.assertTrue(record.price_and_moving_averages.is_price_above_all_mas)
        self.assertTrue(record.price_and_moving_averages.is_ma200_trending_up)
        # ② 周期位置与高低点
        self.assertTrue(record.cycle_and_high_low_positions.meets_cycle_thresholds)
        self.assertGreaterEqual(record.cycle_and_high_low_positions.gain_from_52w_low_pct, 30.0)
        self.assertLessEqual(record.cycle_and_high_low_positions.pullback_from_52w_high_pct, 25.0)
        # ③ 成交量与筹码抽干
        self.assertTrue(record.volume_and_supply_dryup.is_volume_dryup_confirmed)
        self.assertLessEqual(record.volume_and_supply_dryup.dryup_ratio, 0.50)
        # ④ 形态收敛足迹 VCP
        self.assertEqual(record.vcp_pattern_footprints.vcp_stage, "Tight_Pivot_Ready")
        self.assertEqual(record.vcp_pattern_footprints.vcp_code, "8W 25/2 4T")
        # 综合判定
        self.assertTrue(record.sepa_qualification.overall_preliminary_pass)
        self.assertEqual(record.sepa_qualification.decision_action, "Stage_2_Pivot_Ready")

    def test_compute_screening_metrics_disqualified(self):
        """测试趋势一票否决：均线下行与破位股拦截."""
        record = self.builder.compute_screening_metrics(
            ticker="INTC",
            market="US",
            company_name="Intel Corp",
            cik_or_code="0000050863",
            as_of_date="2026-11-07",
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
            base_duration_weeks=10,
            contraction_sequence=[40.0, 30.0],
            pivot_price=26.0,
        )

        self.assertFalse(record.price_and_moving_averages.is_price_above_all_mas)
        self.assertFalse(record.price_and_moving_averages.is_ma200_trending_up)
        self.assertFalse(record.sepa_qualification.overall_preliminary_pass)
        self.assertEqual(record.sepa_qualification.decision_action, "Trend_Disqualified")

    def test_generate_and_save_golden_samples(self):
        """测试重点标的黄金打样样本集生成与落盘."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_builder = ScreeningUniverseBuilder(data_root=Path(tmpdir))
            sample_file = temp_builder.build_and_save_samples()

            self.assertTrue(sample_file.exists())
            data = json.loads(sample_file.read_text(encoding="utf-8"))
            self.assertEqual(data["total_samples"], 5)
            tickers = [s["ticker"] for s in data["samples"]]
            self.assertIn("NVDA", tickers)
            self.assertIn("TSM", tickers)
            self.assertIn("8035", tickers)
            self.assertIn("6857", tickers)
            self.assertIn("INTC", tickers)

    def test_schema_conformance(self):
        """测试生成的初筛数据契约结构与字段完整性."""
        samples = self.builder.generate_golden_samples()
        schema_file = PROJECT_ROOT / "schemas/stock_screening_metrics.schema.json"
        self.assertTrue(schema_file.exists())

        sample_dict = samples[0].to_dict()
        required_keys = [
            "ticker",
            "market",
            "company_name",
            "cik_or_code",
            "as_of_date",
            "price_and_moving_averages",
            "cycle_and_high_low_positions",
            "volume_and_supply_dryup",
            "vcp_pattern_footprints",
            "sepa_qualification",
        ]
        for k in required_keys:
            self.assertIn(k, sample_dict)


if __name__ == "__main__":
    unittest.main()
