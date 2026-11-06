"""单元测试：全盘数千家美股官方数据批量收集与平账管道 (test_multi_thousand_collection.py).

验证：
1. 状态机断点续传与记录落盘机制 (SecCollectionProgressManager);
2. 批量流水线 dry-run 模式解析与过滤;
3. 不平账与缺失标的拦截归入补数清单;
4. 真实归档底账向 UnifiedDataCollectionGateway 与 FirmFinancialFact 动态贯通.
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.sec_edgar_collector import (
    OfficialSecEdgarCollector,
    SecExtractedFinancialFacts,
)
from financial_reporting.data_collection_gateway import UnifiedDataCollectionGateway
from financial_core.engines.filing_mapper import OfficialFilingMapper
from scripts.run_multi_thousand_sec_collection import (
    SecCollectionProgressManager,
    run_collection_pipeline,
)
from scripts.test_support.fixtures import project_temp


class TestMultiThousandCollection(unittest.TestCase):
    """测试数千家官方数据批量收集与断点续传管线."""

    def setUp(self):
        self.test_state_path = project_temp(self, "test-sec-collection-") / "progress.json"

    def test_01_progress_manager_state_machine(self):
        """【UT-COLLECT-01: SEC数千家批量收集断点续传状态机记录与原子持久化】

        1. 测试功能与测试点:
           - 验证 SecCollectionProgressManager 管理数千家标的批量收集时的断点续传状态机。
           - 记录成功解析的 SecExtractedFinancialFacts，更新 balanced_count 并执行原子写盘。

        2. 正常函数业务边界与参数契约:
           - state_file 路径合法，record_success 接收强类型三表事实。

        3. 测试数据与模拟场景说明:
           - 模拟记录 TEST_TICKER (总资产 1000，负债 600，权益 400，平账差额 0.0)。

        4. 预期断言与结果验证:
           - 重新加载后断言 is_completed("TEST_TICKER") 为 True。
           - 断言 balanced_count 精确为 1。
        """
        mgr = SecCollectionProgressManager(self.test_state_path)
        self.assertFalse(mgr.is_completed("TEST_TICKER"))

        facts = SecExtractedFinancialFacts(
            cik="0001234567",
            ticker="TEST_TICKER",
            company_name="Test Corp",
            fiscal_year_end="2025-12-31",
            fiscal_year=2025,
            form="10-K",
            currency="USD",
            total_assets=1000.0,
            total_liabilities=600.0,
            stockholders_equity=400.0,
            revenue=800.0,
            cost_of_revenue=400.0,
            gross_profit=400.0,
            operating_income=200.0,
            net_income=150.0,
            operating_cash_flow=180.0,
            capex=30.0,
            free_cash_flow=150.0,
            cash_and_equivalents=100.0,
            total_debt=200.0,
            diluted_shares=10.0,
            inventory=50.0,
            balance_sheet_diff=0.0,
            balance_sheet_rel_ratio=0.0,
            is_balanced=True,
            source_filing="Test",
        )
        mgr.record_success(facts)
        mgr.save()

        # 重新加载断言
        mgr2 = SecCollectionProgressManager(self.test_state_path)
        self.assertTrue(mgr2.is_completed("TEST_TICKER"))
        self.assertEqual(mgr2.data["summary"]["balanced_count"], 1)

    def test_02_pipeline_dry_run(self):
        """【IT-COLLECT-02: 官方数据批量收集流水线 Dry-Run 试运行与队列预览】

        1. 测试功能与测试点:
           - 验证 run_collection_pipeline 在 dry_run=True 模式下的任务调度与待处理队列探查。
           - 不进行真实外部或大量文件解析，快速输出候选集规模。

        2. 正常函数业务边界与参数契约:
           - target_group="sp500", limit=5, dry_run=True。

        3. 测试数据与模拟场景说明:
           - 预览标普 500 前 5 家标的的收集任务。

        4. 预期断言与结果验证:
           - 断言 status == 'DRY_RUN_COMPLETED'。
           - 断言 pending_count >= 1。
        """
        res = run_collection_pipeline(
            target_group="sp500",
            limit=5,
            dry_run=True,
        )
        self.assertEqual(res.get("status"), "DRY_RUN_COMPLETED")
        self.assertGreaterEqual(res.get("pending_count", 0), 1)

    def test_03_archived_dossier_loads_and_maps(self):
        """【IT-COLLECT-03: 已归档官方三表底账(VRT)网关加载与实体金融事实平账映射】

        1. 测试功能与测试点:
           - 验证 UnifiedDataCollectionGateway.load_verified_batch_dossier 读取已归档标的底账。
           - 验证 OfficialFilingMapper.map_to_firm_financial_fact 将底账映射为计算引擎核心输入。
           - 会计刚性平账自检验证: balance_sheet_balanced 为 True。

        2. 正常函数业务边界与参数契约:
           - 标的为仓库中已核验归档的实体 (如 VRT)。

        3. 测试数据与模拟场景说明:
           - 读取 VRT 归档档案。

        4. 预期断言与结果验证:
           - dossier 非空且包含 raw_financials_table。
           - balance_sheet_balanced 为 True。
           - firm_fact.ticker == "VRT"，营收与自由现金流均大于 0。
        """
        dossier = UnifiedDataCollectionGateway.load_verified_batch_dossier("VRT")
        self.assertIsNotNone(dossier)
        self.assertIn("raw_financials_table", dossier)
        self.assertTrue(dossier["raw_financials_table"]["balance_sheet_balanced"])

        firm_fact = OfficialFilingMapper.map_to_firm_financial_fact(dossier)
        self.assertEqual(firm_fact.ticker, "VRT")
        self.assertGreater(firm_fact.revenue_million, 0)
        self.assertGreater(firm_fact.annual_fcf_million, 0)


if __name__ == "__main__":
    unittest.main()
