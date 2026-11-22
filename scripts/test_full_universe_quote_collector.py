#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""美日全量标的固化抽取流水线测试 (Full Universe Solidified Collector Tests).

严格验证:
1. 全盘 14,897 家上市公司全息底账加载 (US: 10,450 + JP: 4,447);
2. 50 只/表安全公式分片矩阵创建契约;
3. 固化流式分批并发采集 (stream_collect_full_universe);
4. 调度器任务注册契约 (FULL_UNIVERSE_COLLECT).
"""

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.concurrent_sheets_quote_collector import (
    ConcurrentSheetsQuoteCollector,
    SheetShard,
)
from scripts.terminal_scheduler import COLLECTION_TASKS, TASKS


class TestFullUniverseQuoteCollector(unittest.TestCase):
    """美日万家标的固化抽取单元测试."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_full_universe_"))
        self.collector = ConcurrentSheetsQuoteCollector(
            data_root=self.test_dir,
            max_workers=2,
            delay_range=(0.001, 0.005),
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_get_full_universe_records_counts(self):
        """测试全盘美日底账规模: 全量 14,897 家 (US: 10,450, JP: 4,447)."""
        all_recs = self.collector.get_full_universe_records(market="ALL")
        self.assertGreaterEqual(len(all_recs), 14890)

        us_recs = self.collector.get_full_universe_records(market="US")
        self.assertGreaterEqual(len(us_recs), 10440)

        jp_recs = self.collector.get_full_universe_records(market="JP")
        self.assertGreaterEqual(len(jp_recs), 4440)

        # 验证总数等于分市场之和
        self.assertEqual(len(all_recs), len(us_recs) + len(jp_recs))

    def test_create_full_universe_shards(self):
        """测试全盘分片矩阵切分: 每分片 <= 50 只标的以满足 Google Sheets 安全配额."""
        shards = self.collector.create_full_universe_shards(chunk_size=50, market="ALL")
        self.assertGreater(len(shards), 290)
        for s in shards:
            self.assertIsInstance(s, SheetShard)
            self.assertLessEqual(len(s.tickers), 50)
            self.assertTrue(s.shard_id.startswith("shard_"))

    def test_stream_collect_full_universe_dry_run(self):
        """测试固化全量流式分批抽取 (抽样 2 个分片验证落盘与收据)."""
        res = self.collector.stream_collect_full_universe(
            market="ALL",
            chunk_size=40,
            max_workers=2,
            dry_run=True,
            limit_chunks=2,
        )
        self.assertEqual(res["total_shards"], 2)
        self.assertEqual(res["successful_shards"], 2)
        self.assertEqual(res["total_tickers_collected"], 80)
        self.assertEqual(res["total_tickers_failed"], 0)

        # 验证收据文件生成
        receipt_file = self.test_dir / "google-finance" / "manifests" / "full_universe_solidified_receipt_all.json"
        self.assertTrue(receipt_file.exists())
        data = json.loads(receipt_file.read_text(encoding="utf-8"))
        self.assertEqual(data["pipeline"], "full_universe_solidified_collector")
        self.assertEqual(data["successful_shards"], 2)

    def test_terminal_scheduler_task_registration(self):
        """测试终端调度器是否固化注册了 FULL_UNIVERSE_COLLECT 任务."""
        self.assertIn("FULL_UNIVERSE_COLLECT", TASKS)
        self.assertIn("FULL_UNIVERSE_COLLECT", COLLECTION_TASKS)
        title, schedule = TASKS["FULL_UNIVERSE_COLLECT"]
        self.assertIn("万家", title)


if __name__ == "__main__":
    unittest.main()
