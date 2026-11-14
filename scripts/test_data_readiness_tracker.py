#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""数据拉取就绪追踪器单元测试 (Unit Tests for DataReadinessTracker)."""

import json
import tempfile
import unittest
from pathlib import Path

from finance_tools.data_readiness_tracker import (
    DataReadinessSnapshot,
    DataReadinessTracker,
    get_data_readiness_banner,
)


class TestDataReadinessTracker(unittest.TestCase):
    """测试数据拉取完备度与时效追踪器."""

    def test_inspect_real_data_readiness(self):
        """独立验证批次排序与资产分类，避免随生产归档滚动失效。"""
        tickers = ("SPY", "QQQ", "^VIX", "NVDA", "TSM", "AAPL")
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmpdir:
            path = Path(tmpdir)
            for ticker in tickers:
                (path / f"20261107T124149_123Z_{ticker}_market_quote.json").write_text(
                    json.dumps({"quotes": {ticker: {"ticker": ticker}}}), encoding="utf-8"
                )
            snapshot = DataReadinessTracker(path).inspect_latest_readiness()

        self.assertIsInstance(snapshot, DataReadinessSnapshot)
        self.assertEqual(snapshot.latest_date_str, "2026-11-07")
        self.assertIn("2026-11-07", snapshot.latest_timestamp_utc)
        self.assertEqual(snapshot.total_completed_count, len(tickers))

        # 验证宏观资产分类
        self.assertIn("SPY", snapshot.macro_indices_completed)
        self.assertIn("QQQ", snapshot.macro_indices_completed)
        self.assertIn("^VIX", snapshot.macro_indices_completed)

        # 验证核心个股分类
        self.assertIn("NVDA", snapshot.equities_completed)
        self.assertIn("TSM", snapshot.equities_completed)
        self.assertIn("AAPL", snapshot.equities_completed)

        # 验证横幅文本生成
        self.assertIn("最新数据拉取完成度与时效底账前置提醒", snapshot.banner_text)
        self.assertIn("2026-11-07", snapshot.banner_text)

    def test_snapshot_to_dict(self):
        """测试快照结构序列化为字典契约."""
        tracker = DataReadinessTracker()
        snapshot = tracker.inspect_latest_readiness()
        data = snapshot.to_dict()

        self.assertIsInstance(data, dict)
        self.assertEqual(data["latest_date"], snapshot.latest_date_str)
        self.assertIn("macro_indices", data)
        self.assertIn("equities", data)
        self.assertIn("total_completed", data)
        self.assertIn("banner_text", data)

    def test_empty_directory_handling(self):
        """测试空目录或不存在目录时的安全降级处理."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_tracker = DataReadinessTracker(raw_dir=Path(tmpdir))
            snapshot = empty_tracker.inspect_latest_readiness()
            self.assertEqual(snapshot.total_completed_count, 0)
            self.assertIn("暂无行情数据", snapshot.banner_text)

    def test_get_data_readiness_banner_helper(self):
        """测试全局便捷调用函数."""
        banner = get_data_readiness_banner()
        self.assertIsInstance(banner, str)
        self.assertTrue(banner)


if __name__ == "__main__":
    unittest.main()
