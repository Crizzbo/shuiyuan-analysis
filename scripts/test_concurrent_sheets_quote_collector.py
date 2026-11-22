#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Google Sheets 多表并发收集器单元测试 (test_concurrent_sheets_quote_collector.py)."""

import csv
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.concurrent_sheets_quote_collector import (
    BatchCollectionResult,
    ConcurrentSheetsQuoteCollector,
    SheetShard,
    get_full_symbol,
)
from scripts.batch_replenish_universe_quotes import REPLENISHMENT_UNIVERSE


class TestConcurrentSheetsQuoteCollector(unittest.TestCase):
    """测试多表并发行情数据收集引擎."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="test_concurrent_sheets_"))
        self.data_dir = self.temp_dir / "data"
        self.collector = ConcurrentSheetsQuoteCollector(
            data_root=self.data_dir,
            max_workers=4,
            delay_range=(0.01, 0.02),
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_symbol_mapping(self):
        """测试交易所前缀映射准确性 (美股/日股/ETF)."""
        self.assertEqual(get_full_symbol("NVDA", "US"), "NASDAQ:NVDA")
        self.assertEqual(get_full_symbol("LLY", "US"), "NYSE:LLY")
        self.assertEqual(get_full_symbol("SPY", "US"), "NYSEARCA:SPY")
        self.assertEqual(get_full_symbol("7203", "JP"), "TYO:7203")
        self.assertEqual(get_full_symbol("1306", "JP"), "TYO:1306")

    def test_sharding_integrity_by_category(self):
        """测试基于业务分类的智能分片逻辑."""
        shards = self.collector.create_shards(chunk_size=10, by_category=True)
        self.assertGreater(len(shards), 5)

        total_sharded_tickers = sum(s.item_count for s in shards)
        self.assertEqual(total_sharded_tickers, len(REPLENISHMENT_UNIVERSE))

        for s in shards:
            self.assertLessEqual(s.item_count, 10)
            self.assertTrue(s.range_a1.startswith(f"'{s.sheet_name}'!A1:M"))
            for item in s.tickers:
                self.assertIn("ticker", item)
                self.assertIn("full_symbol", item)

    def test_sharding_linear_chunking(self):
        """测试纯线性切分分片."""
        shards = self.collector.create_shards(chunk_size=20, by_category=False)
        total_tickers = len(REPLENISHMENT_UNIVERSE)
        expected_shard_count = (total_tickers + 19) // 20
        self.assertEqual(len(shards), expected_shard_count)

        total_sharded_tickers = sum(s.item_count for s in shards)
        self.assertEqual(total_sharded_tickers, total_tickers)

    def test_formula_matrix_generation(self):
        """测试标准 GOOGLEFINANCE 矩阵与表头生成."""
        sample_tickers = [
            {"ticker": "NVDA", "full_symbol": "NASDAQ:NVDA", "name_zh": "英伟达", "market": "US", "price": 186.64},
            {"ticker": "7203", "full_symbol": "TYO:7203", "name_zh": "丰田汽车", "market": "JP", "price": 2910.50},
        ]
        shard = SheetShard(
            shard_id="test_shard",
            shard_title="测试分片",
            sheet_name="TestSheet",
            tickers=sample_tickers,
        )

        matrix = self.collector.generate_formula_matrix(shard)
        # 第一行为表头，后两行为数据
        self.assertEqual(len(matrix), 3)

        # 检查表头
        headers = matrix[0]
        self.assertEqual(headers[0], "Ticker")
        self.assertEqual(headers[2], "Price")
        self.assertEqual(headers[3], "Change")
        self.assertEqual(headers[4], "Change %")
        self.assertEqual(headers[5], "Volume")

        # 检查数据行 1 (NVDA)
        row1 = matrix[1]
        self.assertEqual(row1[0], "NASDAQ:NVDA")
        self.assertEqual(row1[1], "英伟达")
        self.assertEqual(row1[2], '=GOOGLEFINANCE($A2, "price")')
        self.assertEqual(row1[3], '=GOOGLEFINANCE($A2, "change")')
        self.assertEqual(row1[4], '=GOOGLEFINANCE($A2, "changepct")')
        self.assertEqual(row1[5], '=GOOGLEFINANCE($A2, "volume")')
        self.assertEqual(row1[6], '=GOOGLEFINANCE($A2, "pe")')
        self.assertEqual(row1[7], '=GOOGLEFINANCE($A2, "eps")')
        self.assertEqual(row1[8], '=GOOGLEFINANCE($A2, "high52")')
        self.assertEqual(row1[9], '=GOOGLEFINANCE($A2, "low52")')
        self.assertEqual(row1[10], '=GOOGLEFINANCE($A2, "currency")')

        # 检查数据行 2 (7203)
        row2 = matrix[2]
        self.assertEqual(row2[0], "TYO:7203")
        self.assertEqual(row2[2], '=GOOGLEFINANCE($A3, "price")')

    def test_export_templates(self):
        """测试批量导出 CSV 模板与 Manifest 清单."""
        res = self.collector.export_templates()
        self.assertGreater(res["total_shards"], 0)
        self.assertTrue(Path(res["manifest_file"]).exists())

        manifest = json.loads(Path(res["manifest_file"]).read_text(encoding="utf-8"))
        self.assertIn("shards", manifest)
        self.assertIn("exported_files", manifest)
        self.assertEqual(len(manifest["exported_files"]), res["total_shards"])

        # 验证导出的 CSV 可正确由 csv.reader 读取
        first_csv = self.collector.templates_dir / manifest["exported_files"][0]
        self.assertTrue(first_csv.exists())
        with open(first_csv, "r", encoding="utf-8-sig") as f:
            reader = list(csv.reader(f))
            self.assertGreater(len(reader), 1)
            self.assertEqual(reader[0][0], "Ticker")

    def test_concurrent_collection_dry_run(self):
        """测试 4 线程并发采集、时效验真与不可篡改落盘."""
        shards = self.collector.create_shards(chunk_size=15, by_category=True)
        # 限制取前 3 个分片进行高频并发压测
        test_shards = shards[:3]
        expected_total_tickers = sum(s.item_count for s in test_shards)

        result = self.collector.collect_all(
            shards=test_shards,
            dry_run=True,
            max_workers=4,
        )

        self.assertEqual(result.total_shards, 3)
        self.assertEqual(result.successful_shards, 3)
        self.assertEqual(result.failed_shards, 0)
        self.assertEqual(result.successful_tickers, expected_total_tickers)
        self.assertEqual(result.failed_tickers, 0)
        self.assertGreater(result.elapsed_seconds, 0.0)
        self.assertTrue(result.receipt_file.endswith(".json"))

        # 验证 raw 目录落盘的实际文件
        raw_files = list(self.collector.raw_dir.glob("*_market_quote.json"))
        self.assertEqual(len(raw_files), expected_total_tickers)

        # 验证单条记录格式
        sample_file = raw_files[0]
        content = json.loads(sample_file.read_text(encoding="utf-8"))
        self.assertIn("quotes", content)
        self.assertEqual(content["source"], "google_sheets_concurrent_collector")

        # 验证 manifest 目录中的收据文件
        receipt_file = self.collector.manifest_dir / result.receipt_file
        self.assertTrue(receipt_file.exists())
        receipt_data = json.loads(receipt_file.read_text(encoding="utf-8"))
        self.assertEqual(receipt_data["total_tickers"], expected_total_tickers)

    def test_retry_on_transient_failure(self):
        """测试网络偶发故障时的指数退避与重试机制."""
        shard = SheetShard(
            shard_id="retry_test",
            shard_title="重试测试",
            sheet_name="RetrySheet",
            tickers=[{"ticker": "NVDA", "market": "US", "price": 186.64}],
        )

        call_count = 0

        def flaky_simulate(s, prices):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionResetError("429 Too Many Requests (Simulated)")
            return {
                "shard_id": s.shard_id,
                "status": "success",
                "items": [{
                    "ticker": "NVDA",
                    "company_name": "英伟达",
                    "price": 186.64,
                    "currency": "USD",
                    "market": "US",
                }],
            }

        with patch.object(self.collector, "_simulate_shard_fetch", side_effect=flaky_simulate):
            res = self.collector.fetch_shard_with_retry(shard, dry_run=True, max_retries=3)
            self.assertEqual(res["status"], "success")
            self.assertEqual(call_count, 2)  # 第 1 次失败，第 2 次重试成功

    def test_import_csv_export(self):
        """测试从外部导出的 Google Sheet CSV 中极速解析与落盘."""
        csv_path = self.temp_dir / "external_export.csv"
        rows = [
            ["Ticker", "Company Name", "Price", "Change", "Change %", "Volume", "PE", "EPS", "52W High", "52W Low", "Currency", "Trade Time", "Data Delay"],
            ["NASDAQ:NVDA", "英伟达", "186.64", "2.20", "1.19%", "25000000", "45.2", "4.12", "200.00", "95.00", "USD", "2026-11-20 16:00:00", "0"],
            ["TYO:7203", "丰田汽车", "2,910.50", "15.00", "0.52%", "15000000", "9.5", "306.00", "3600.00", "2500.00", "JPY", "2026-11-20 15:00:00", "0"],
        ]
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        import_res = self.collector.import_csv_export(csv_path)
        self.assertEqual(import_res["imported_count"], 2)
        self.assertEqual(len(import_res["errors"]), 0)

        # 检查是否成功生成归档文件
        raw_files = list(self.collector.raw_dir.glob("*_market_quote.json"))
        tickers_saved = set()
        for rf in raw_files:
            c = json.loads(rf.read_text(encoding="utf-8"))
            tickers_saved.update(c.get("quotes", {}).keys())
        self.assertIn("NVDA", tickers_saved)
        self.assertIn("7203", tickers_saved)


if __name__ == "__main__":
    unittest.main()
