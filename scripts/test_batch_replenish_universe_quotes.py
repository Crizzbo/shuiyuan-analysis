#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""分批离线补数调度器单元测试 (test_batch_replenish_universe_quotes.py)."""

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.batch_replenish_universe_quotes import (
    BASKET_DEFINITIONS,
    REPLENISHMENT_UNIVERSE,
    BatchUniverseReplenisher,
)


class TestBatchUniverseReplenisher(unittest.TestCase):
    """测试离线分批补数调度器核心逻辑."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test_replenish_"))
        self.data_dir = self.temp_dir / "data"
        self.replenisher = BatchUniverseReplenisher(data_root=self.data_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_universe_definitions_integrity(self):
        """测试资产池与篮子定义的完整性与格式规范."""
        self.assertGreaterEqual(len(REPLENISHMENT_UNIVERSE), 50)
        for ticker, meta in REPLENISHMENT_UNIVERSE.items():
            self.assertIn("name_zh", meta)
            self.assertIn("category", meta)
            self.assertIn("market", meta)
            self.assertIn(meta["market"], ("US", "JP"))
            self.assertIn("currency", meta)
            self.assertIn(meta["currency"], ("USD", "JPY"))
            self.assertIsInstance(meta["price"], (int, float))
            self.assertGreater(meta["price"], 0.0)

        for b_name, b_meta in BASKET_DEFINITIONS.items():
            self.assertIn("title", b_meta)
            self.assertIn("description", b_meta)
            self.assertIn("category_key", b_meta)

    def test_get_status_overview_empty(self):
        """测试在空目录下的状态概览."""
        status = self.replenisher.get_status_overview()
        self.assertEqual(status["total_local_archives"], 0)
        self.assertIn("basket_breakdown", status)
        self.assertEqual(status["basket_breakdown"]["all_priority"]["covered_count"], 0)

    def test_replenish_custom_tickers(self):
        """测试按自定义代码列表执行补数并验证落盘."""
        targets = ["SCHD", "TLT", "ARM"]
        res = self.replenisher.replenish(tickers=targets, batch_size=2)
        self.assertEqual(res["total_requested"], 3)
        self.assertEqual(res["success_count"], 3)
        self.assertEqual(res["failed_count"], 0)

        # 验证落盘文件
        raw_files = list(self.replenisher.raw_dir.glob("*_market_quote.json"))
        self.assertEqual(len(raw_files), 3)

        # 验证每个文件通过 JSON 解析与合规结构
        for rf in raw_files:
            content = json.loads(rf.read_text(encoding="utf-8"))
            self.assertIn("quotes", content)
            self.assertIn("source", content)
            self.assertEqual(content["source"], "batch_offline_universe_replenisher")

    def test_replenish_basket_core_etfs(self):
        """测试按特定资产篮子进行补数."""
        res = self.replenisher.replenish(basket_name="gold_metals")
        self.assertEqual(res["total_requested"], 8)
        self.assertEqual(res["success_count"], 8)
        self.assertEqual(res["failed_count"], 0)

        # 检查收据
        receipts = list(self.replenisher.manifest_dir.glob("replenishment_receipt_*.json"))
        self.assertEqual(len(receipts), 1)


if __name__ == "__main__":
    unittest.main()
