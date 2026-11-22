#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""全盘流式分批并发采集管线测试 (Chunk-and-Stream Unit Tests).

验证:
1. 分块标的读取与 DCF/基准价格规范化 (load_chunk_universe);
2. 单个分块多表并发采集与验真入账 (collect_chunk);
3. 多个连续分块流式分批并发采集与断点续传 (stream_collect_chunks);
4. 检查点状态一致性 (get_stream_chunk_status / checkpoint persistence).
"""

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.concurrent_sheets_quote_collector import (
    BatchCollectionResult,
    ConcurrentSheetsQuoteCollector,
)


class TestChunkStreamQuoteCollector(unittest.TestCase):
    """Chunk-and-Stream 流水线单元测试用例."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_chunk_stream_"))
        self.collector = ConcurrentSheetsQuoteCollector(
            data_root=self.test_dir,
            max_workers=2,
            delay_range=(0.001, 0.005),
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_load_chunk_universe(self):
        """测试加载指定分块的标的资产池."""
        u1 = self.collector.load_chunk_universe(1)
        self.assertIsInstance(u1, dict)
        self.assertGreater(len(u1), 0)
        # 验证首个标的规范
        first_key = next(iter(u1))
        item = u1[first_key]
        self.assertIn("ticker", item)
        self.assertIn("price", item)
        self.assertIn("currency", item)
        self.assertIn("market", item)
        self.assertGreater(item["price"], 0)

    def test_get_stream_chunk_status_initial(self):
        """测试初始状态下流式检查点默认值."""
        status = self.collector.get_stream_chunk_status()
        self.assertEqual(status["completed_chunks_count"], 0)
        self.assertEqual(status["total_tickers_archived"], 0)
        self.assertEqual(status["next_chunk_to_process"], 1)

    def test_collect_single_chunk_dry_run(self):
        """测试单个分块的本地仿真并发采集与落盘."""
        res = self.collector.collect_chunk(chunk_num=1, dry_run=True, max_workers=2)
        self.assertIsInstance(res, BatchCollectionResult)
        self.assertGreater(res.successful_tickers, 0)
        self.assertEqual(res.failed_tickers, 0)

        # 检查检查点更新
        status = self.collector.get_stream_chunk_status()
        self.assertIn(1, status["completed_chunks"])
        self.assertEqual(status["completed_chunks_count"], 1)
        self.assertEqual(status["total_tickers_archived"], res.successful_tickers)
        self.assertEqual(status["next_chunk_to_process"], 2)

    def test_stream_collect_chunks_resumable(self):
        """测试多批次流式并发推进与断点续传."""
        stream_res = self.collector.stream_collect_chunks(
            start_chunk=1,
            end_chunk=2,
            dry_run=True,
            max_workers=2,
            chunk_delay=0.01,
        )
        self.assertEqual(stream_res["total_chunks_processed"], 2)
        self.assertGreater(stream_res["total_tickers_collected"], 0)
        self.assertEqual(stream_res["total_tickers_failed"], 0)

        # 检查点应记录 Chunk 1 和 2 完成
        cp = self.collector.get_stream_chunk_status()
        self.assertEqual(cp["completed_chunks"], [1, 2])
        self.assertEqual(cp["completed_chunks_count"], 2)
        self.assertEqual(cp["next_chunk_to_process"], 3)


if __name__ == "__main__":
    unittest.main()
