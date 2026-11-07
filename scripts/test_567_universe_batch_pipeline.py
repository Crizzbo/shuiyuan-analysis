"""单元测试: 567 资产池分批切片流水线与状态机测试 (567 Universe Batch Pipeline Tests).

测试覆盖:
1. 状态机原子落盘、加载与进度统计更新 (UniversePipelineStateManager)
2. 批次切片筛选与文件解析 (Chunk Discovery & Filtering)
3. 纯离线日结快照模式单标的端到端系统性估值
4. 断点续传机制验证: COMPLETED 标的自动跳过
5. 蒙特卡洛 10,000 次连续随机折现集成
"""

import unittest
from pathlib import Path
import sys
import json
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_567_universe_batch_pipeline import (
    UniversePipelineStateManager,
    BatchUniversePipelineRunner,
)
from scripts.test_support.fixtures import isolated_facade_ledger, project_temp, freeze_quote_clock
from financial_core.engines.prediction_ledger import PredictionLedger


class Test567UniverseBatchPipeline(unittest.TestCase):
    """567 资产池流水线单元测试套件."""

    def setUp(self):
        self.temp_dir = project_temp(self, "test-567-")
        isolated_facade_ledger(self, PredictionLedger(self.temp_dir / "predictions.sqlite3"))
        self.enter_test_paths()
        freeze_quote_clock(self)
        self.state_file = self.temp_dir / "test_progress.json"
        self.mock_chunks_dir = self.temp_dir / "chunks"
        self.mock_chunks_dir.mkdir(parents=True, exist_ok=True)

        # 构建模拟 chunk 数据
        self.mock_dossier_nvda = {
            "overview": {
                "ticker": "NVDA",
                "company_name": "NVIDIA Corporation",
                "market": "US",
                "industry_id": "semiconductors",
                "quote_timestamp": "2026-10-16T14:00:00Z",
            },
            "raw_financials_table": {
                "revenue": "$120,000M",
                "operating_income": "$75,000M",
                "net_income": "$62,000M",
                "free_cash_flow": "$65,000M",
                "total_assets": "$130,000M",
                "total_liabilities": "$35,000M",
                "capex": "$10,000M",
                "equity": "$95,000M",
                "cash_and_equivalents": "$35,000M",
                "total_debt": "$11,000M",
                "shares": "24,500M",
            },
            "long_term_outlook": {
                "dcf_valuation_matrix": {
                    "base_fair_value": "$145.0",
                    "margin_of_safety_buy_zone": "现价 $128.50 | 悲观底价 $95.0",
                }
            }
        }
        self.mock_dossier_aapl = {
            "overview": {
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "market": "US",
                "industry_id": "consumer_hardware",
                "quote_timestamp": "2026-10-16T14:00:00Z",
            },
            "raw_financials_table": {
                "revenue": "$383,000M",
                "operating_income": "$114,000M",
                "net_income": "$97,000M",
                "free_cash_flow": "$100,000M",
                "total_assets": "$350,000M",
                "total_liabilities": "$288,000M",
                "capex": "$11,000M",
                "equity": "$62,000M",
                "cash_and_equivalents": "$30,000M",
                "total_debt": "$105,000M",
                "shares": "15,500M",
            },
            "long_term_outlook": {
                "dcf_valuation_matrix": {
                    "base_fair_value": "$235.0",
                    "margin_of_safety_buy_zone": "现价 $225.00 | 悲观底价 $180.0",
                }
            }
        }

        # 写入 chunk_001.json 与 chunk_002.json
        chunk1_path = self.mock_chunks_dir / "chunk_001.json"
        chunk1_path.write_text(json.dumps([self.mock_dossier_nvda], ensure_ascii=False), encoding="utf-8")

        chunk2_path = self.mock_chunks_dir / "chunk_002.json"
        chunk2_path.write_text(json.dumps([self.mock_dossier_aapl], ensure_ascii=False), encoding="utf-8")

    def enter_test_paths(self):
        # 批次仍从项目内读取，合成档案、账本及补数只落在本次临时目录。
        for binding in (
            patch("scripts.run_567_universe_batch_pipeline.ROOT", self.temp_dir),
            patch("scripts.run_567_universe_batch_pipeline.RECONCILIATION_STATE_PATH", self.temp_dir / "reconciliation.json"),
            patch("financial_reporting.data_collection_gateway.UnifiedDataCollectionGateway.DEFAULT_GAP_MANIFEST_PATH",
                  self.temp_dir / "replenishment.json"),
        ):
            binding.start()
            self.addCleanup(binding.stop)

    def test_state_manager_persistence(self):
        """【UT-567-01: 567资产池流水线状态机原子落盘、重载与统计计数自愈】

        1. 测试功能与测试点:
           - 验证 UniversePipelineStateManager 状态机管理器的原子写入、多轮持久化与重载自洽性。
           - 记录已完成标的及其公允价值，验证统计计数 completed_count 正确累加。

        2. 正常函数业务边界与参数契约:
           - state_file 必须为合法 Path。
           - record_ticker_completed 接收 chunk_id、ticker 及估值结果字典。

        3. 测试数据与模拟场景说明:
           - 模拟记录 NVDA (中性公允价 145.0，现价 128.5) 于 chunk_001。

        4. 预期断言与结果验证:
           - 写入后 is_ticker_completed("NVDA") 为 True。
           - 断言 completed_count 精确为 1。
           - 重新初始化加载后，数据无损读取且中性公允价为 145.0。
        """
        mgr = UniversePipelineStateManager(self.state_file)
        self.assertFalse(mgr.is_ticker_completed("NVDA"))

        # 记录完成
        mgr.record_ticker_completed("chunk_001", "NVDA", {"neutral_fair_value": 145.0, "current_price": 128.5})
        self.assertTrue(mgr.is_ticker_completed("NVDA"))
        self.assertEqual(mgr.data["summary"]["completed_count"], 1)

        # 重新初始化载入，验证持久化无损
        mgr_reloaded = UniversePipelineStateManager(self.state_file)
        self.assertTrue(mgr_reloaded.is_ticker_completed("NVDA"))
        self.assertEqual(mgr_reloaded.data["tickers"]["NVDA"]["neutral_fair_value"], 145.0)

    def test_chunk_filtering(self):
        """【UT-567-02: 批次切片筛选器按单批与范围提取】

        1. 测试功能与测试点:
           - 验证 BatchUniversePipelineRunner.get_chunk_files 切片发现与范围过滤能力。
           - 支持单批次检索 (chunk_id=1) 与闭区间批次检索 (chunk_range=(1, 2))。

        2. 正常函数业务边界与参数契约:
           - chunk_id 为正整数，chunk_range 为二元元组 (start, end)。

        3. 测试数据与模拟场景说明:
           - 模拟目录下包含 chunk_001.json 与 chunk_002.json。

        4. 预期断言与结果验证:
           - 单批过滤结果长度为 1，文件名匹配 'chunk_001.json'。
           - 范围过滤结果长度为 2。
        """
        runner = BatchUniversePipelineRunner(
            chunks_dir=self.mock_chunks_dir,
            state_file=self.state_file,
        )

        # 单批测试
        c1 = runner.get_chunk_files(chunk_id=1)
        self.assertEqual(len(c1), 1)
        self.assertEqual(c1[0].name, "chunk_001.json")

        # 范围测试
        cr = runner.get_chunk_files(chunk_range=(1, 2))
        self.assertEqual(len(cr), 2)

    def test_offline_execution_and_resumption(self):
        """【IT-567-03: 纯离线日结快照模式端到端计算与断点续传】

        1. 测试功能与测试点:
           - 验证 BatchUniversePipelineRunner 在 offline_mode=True 模式下跑通单标的估值。
           - 集成 1,000 次蒙特卡洛随机折现模拟，断言 P50 中值公允价与 CVaR_10% 悲观底价落盘。
           - 验证断点续传 (resume=True): 二次执行同一切片时自动跳过已完成标的。

        2. 正常函数业务边界与参数契约:
           - resume=True, offline_mode=True。

        3. 测试数据与模拟场景说明:
           - 运行包含 NVDA 的 chunk 1。

        4. 预期断言与结果验证:
           - 第一次执行 processed_count == 1, skipped_count == 0。
           - 状态机记录包含 monte_carlo 字段且 median_fair_value > 0, cvar_10_floor > 0。
           - 第二次执行 processed_count == 0, skipped_count == 1 (断点成功跳过)。
        """
        runner = BatchUniversePipelineRunner(
            chunks_dir=self.mock_chunks_dir,
            state_file=self.state_file,
            include_monte_carlo=True,
            mc_iterations=1000,
            offline_mode=True,
        )

        # 第一次执行 chunk 1
        res1 = runner.run_pipeline(chunk_id=1, resume=True)
        self.assertEqual(res1["processed_count"], 1)
        self.assertEqual(res1["skipped_count"], 0)
        self.assertTrue(runner.state_mgr.is_ticker_completed("NVDA"))

        # 验证 Monte Carlo 数据写入状态机
        nvda_record = runner.state_mgr.data["tickers"]["NVDA"]
        self.assertIn("monte_carlo", nvda_record)
        self.assertGreater(nvda_record["monte_carlo"]["median_fair_value"], 0.0)
        self.assertGreater(nvda_record["monte_carlo"]["cvar_10_floor"], 0.0)

        # 第二次断点执行 (resume=True)，应跳过已完成的 NVDA
        res2 = runner.run_pipeline(chunk_id=1, resume=True)
        self.assertEqual(res2["processed_count"], 0)
        self.assertEqual(res2["skipped_count"], 1)

    def test_failed_core_analysis_cannot_generate_dossier(self):
        """核心明确失败时拒绝生成估值走廊、JSON 或 Excel。"""
        from types import SimpleNamespace
        runner = BatchUniversePipelineRunner(chunks_dir=self.mock_chunks_dir, state_file=self.state_file)
        failure = SimpleNamespace(execution_success=False, decision_card=None, block_reason="合成阻断原因")
        with patch.object(runner.fin_system, "analyze_equity", return_value=failure):
            with self.assertRaisesRegex(ValueError, "核心分析未通过"):
                runner.process_single_company(self.mock_dossier_nvda, "chunk_001")
        self.assertFalse(list((self.temp_dir / "reports").rglob("*.json")))

    def test_dry_run_mode(self):
        """FT-03 试运行可预览，恢复时仍须执行正式任务。"""
        runner = BatchUniversePipelineRunner(
            chunks_dir=self.mock_chunks_dir,
            state_file=self.state_file,
        )
        res = runner.run_pipeline(chunk_id=2, dry_run=True)
        self.assertEqual(res["processed_count"], 1)
        self.assertFalse(UniversePipelineStateManager(self.state_file).is_ticker_completed("AAPL"))
        self.assertFalse(list(self.temp_dir.glob("reports/**/*_deep_dossier.json")))

    def test_verified_batches_discovery(self):
        """【IT-567-05: 78个已核验官方批次真实切片索引提取】

        1. 测试功能与测试点:
           - 验证流水线默认接入 78 个已核验官方批次数据源。
           - 提取 batch_001 中的标的列表并验证包含核心旗舰公司。

        2. 正常函数业务边界与参数契约:
           - batch_id=1，返回 List[Tuple[batch_name, dossiers]]。

        3. 测试数据与模拟场景说明:
           - 检索 batch_001 真实档案。

        4. 预期断言与结果验证:
           - 检索批次数量为 1，名称为 'batch_001'。
           - b_dossiers 长度 > 0 且包含标的 'AAPL'。
        """
        runner = BatchUniversePipelineRunner(
            state_file=self.state_file,
        )
        batches_1 = runner.get_batches(batch_id=1)
        self.assertEqual(len(batches_1), 1)
        b_name, b_dossiers = batches_1[0]
        self.assertEqual(b_name, "batch_001")
        self.assertGreater(len(b_dossiers), 0)
        tickers = [d.get("overview", {}).get("ticker") for d in b_dossiers]
        self.assertIn("AAPL", tickers)

    def test_verified_batch_end_to_end_with_excel(self):
        """完整合成三表、明确行情与估值输入生成可回读的五页工作簿。"""
        excel_tmp_dir = self.temp_dir / "excel_reports"
        excel_tmp_dir.mkdir(parents=True, exist_ok=True)

        runner = BatchUniversePipelineRunner(
            state_file=self.state_file,
            output_excel=True,
            excel_output_root=excel_tmp_dir,
        )
        # 成功交付使用明示完整的合成样本；存量缺证据拒绝由独立回归覆盖。
        with patch.object(runner, "get_batches", return_value=[("batch_001", [self.mock_dossier_aapl])]):
            res = runner.run_pipeline(batch_id=1, limit=1, resume=False)
        self.assertEqual(res["processed_count"], 1)
        self.assertEqual(res["failed_count"], 0)
        aapl_rec = runner.state_mgr.data["tickers"]["AAPL"]
        self.assertEqual(aapl_rec["status"], "COMPLETED")
        excel_file = self.temp_dir / aapl_rec["excel_path"]
        self.assertTrue(excel_file.is_file())
        self.assertGreater(excel_file.stat().st_size, 3000)

    def test_reconciliation_enrichment_for_deficient_companies(self):
        """平账修复保留原始字段，仍缺现金、债务或股数时拒绝发布。"""
        from financial_core.engines.normalized_reconciliation_engine import (
            NormalizedReconciliationStateManager,
            ReconciliationRecord,
        )

        rec_state_file = self.temp_dir / "temp_rec_state.json"
        rec_mgr = NormalizedReconciliationStateManager(rec_state_file, sync_legacy=False)

        # 写入一个完美平账的官方事实记录 (TMO)
        rec_mgr.record_success(ReconciliationRecord(
            ticker="TMO",
            market="US",
            company_name="Thermo Fisher Scientific",
            tier="TIER_0",
            cik="0000097745",
            status="COMPLETED",
            fiscal_year=2024,
            form="10-K",
            accounting_standard="US-GAAP",
            currency="USD",
            total_assets=110343000000.0,
            total_liabilities=56806000000.0,
            stockholders_equity=53537000000.0,
            revenue=44556000000.0,
            gross_profit=18000000000.0,
            operating_income=7500000000.0,
            net_income=6000000000.0,
            operating_cash_flow=8500000000.0,
            capex=1500000000.0,
            free_cash_flow=7000000000.0,
            is_balanced=True,
            balance_sheet_diff=0.0,
            balance_sheet_rel_ratio=0.0,
            source_filing="SEC EDGAR 10-K",
        ))
        rec_mgr.save()

        # 构造一个有严重平账破损的历史 dossier
        broken_dossier = {
            "overview": {
                "ticker": "TMO",
                "company_name": "Thermo Fisher Scientific",
                "market": "US",
                "industry_id": "medical_devices",
            },
            "raw_financials_table": {
                "revenue": "$40,000M",
                "total_assets": "$100,000M",
                "total_liabilities": "$90,000M",
                "equity": "$90,000M",  # 严重不平账 (100 != 90 + 90)
            },
        }

        excel_tmp_dir = self.temp_dir / "excel_enrich_reports"
        excel_tmp_dir.mkdir(parents=True, exist_ok=True)

        runner = BatchUniversePipelineRunner(
            state_file=self.state_file,
            reconciliation_state_path=rec_state_file,
            output_excel=True,
            excel_output_root=excel_tmp_dir,
        )

        # 平账修复不等于三表及行情齐备，缺少现金、债务和股数时保持阻断。
        from financial_core.engines.filing_mapper import IncompleteFilingFactError
        with self.assertRaises(IncompleteFilingFactError):
            runner.process_single_company(broken_dossier, "chunk_broken")
        self.assertEqual(broken_dossier["raw_financials_table"]["total_assets"], 110343000000.0)
        self.assertEqual(broken_dossier["raw_financials_table"]["total_liabilities"], 56806000000.0)
        self.assertFalse(list(excel_tmp_dir.glob("*.xlsx")))



if __name__ == "__main__":
    unittest.main()
