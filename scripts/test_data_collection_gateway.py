"""测试专业数据收集与前置校验网关 (UnifiedDataCollectionGateway)."""

import json
from pathlib import Path
import tempfile
import unittest

from financial_reporting.data_collection_gateway import (
    UnifiedDataCollectionGateway,
    BalanceSheetIdentityError,
    IncompleteFilingFactError,
)

ROOT = Path(__file__).resolve().parents[1]


class TestDataCollectionGateway(unittest.TestCase):
    """测试数据收集网关各项核心功能."""

    def test_collect_macro_snapshot(self):
        """【UT-GATEWAY-01: 免配置官方宏观快照提取(美债收益率曲线/期限利差/美元指数/美日汇率)】

        1. 测试功能与测试点:
           - 验证 UnifiedDataCollectionGateway.collect_macro_snapshot 免配置提取官方宏观快照。
           - 覆盖 10Y/2Y 美债收益率、期限利差 (bps)、美元指数 (DXY) 与美日汇率 (USD/JPY)。

        2. 正常函数业务边界与参数契约:
           - 无需外部私密密钥，完全依赖项目内合法公开宏观底账。
           - 返回标准字典包含 5 大核心宏观字段。

        3. 测试数据与模拟场景说明:
           - 本地公开基准宏观数据加载。

        4. 预期断言与结果验证:
           - 包含 us_10y_yield_pct, us_2y_yield_pct, us_term_spread_bps, dxy_index, usdjpy_rate。
           - us_10y_yield_pct > 0.0，dxy_index > 50.0。
        """
        snap = UnifiedDataCollectionGateway.collect_macro_snapshot()
        self.assertIn("us_10y_yield_pct", snap)
        self.assertIn("us_2y_yield_pct", snap)
        self.assertIn("us_term_spread_bps", snap)
        self.assertIn("dxy_index", snap)
        self.assertIn("usdjpy_rate", snap)
        self.assertGreater(snap["us_10y_yield_pct"], 0.0)
        self.assertGreater(snap["dxy_index"], 50.0)

    def test_verify_and_prepare_quote_fresh(self):
        """【UT-GATEWAY-02: 当日新鲜行情核验与时效标签格式化(盘中实时时段判定)】

        1. 测试功能与测试点:
           - 验证 verify_and_prepare_quote 对当日新鲜行情的有效性核验与标签格式化。
           - 采样延迟在 2 小时之内，判定为有效并生成包含币种符号的显示标签。

        2. 正常函数业务边界与参数契约:
           - 传入合法 ISO 8601 时区字符串。

        3. 测试数据与模拟场景说明:
           - 现价 235.50，行情时间 11:30，当前时间 12:00 (延迟 30 分钟)。

        4. 预期断言与结果验证:
           - is_valid 为 True。
           - age_hours < 2.0。
           - formatted_label 包含 'USD235.50'。
        """
        # 模拟当日正常行情 (假定当前时点后 1 小时之内)
        now_iso = "2026-10-17T12:00:00+00:00"
        quote_ts = "2026-10-17T11:30:00+00:00"
        res = UnifiedDataCollectionGateway.verify_and_prepare_quote(
            ticker="AAPL",
            market="US",
            price=235.50,
            quote_timestamp=quote_ts,
            currency="USD",
            current_time_iso=now_iso,
        )
        self.assertTrue(res["is_valid"])
        self.assertLess(res["age_hours"], 2.0)
        self.assertIn("USD235.50", res["formatted_label"])

    def test_verify_and_prepare_quote_stale_blocked(self):
        """【UT-GATEWAY-03: 严重滞后超期(>24h)行情刚性拦截阻断(stale_blocked)】

        1. 测试功能与测试点:
           - 验证当行情时间戳滞后超过 24 小时（如 48 小时历史旧数据）时，网关实施刚性阻断。
           - 严禁将严重陈旧缓存当做盘中现价提供给下游估值模型。

        2. 正常函数业务边界与参数契约:
           - 滞后 > 24h 刚性将 is_valid 置为 False。

        3. 测试数据与模拟场景说明:
           - 行情时间 10 月 15 日，当前时间 10 月 17 日 (滞后 48+ 小时)。

        4. 预期断言与结果验证:
           - is_valid 为 False。
           - session_status == 'stale_blocked'。
           - formatted_label 包含 '阻断'。
        """
        now_iso = "2026-10-17T12:00:00+00:00"
        stale_ts = "2026-10-15T10:00:00+00:00"  # 滞后 48+ 小时
        res = UnifiedDataCollectionGateway.verify_and_prepare_quote(
            ticker="AAPL",
            market="US",
            price=230.00,
            quote_timestamp=stale_ts,
            currency="USD",
            current_time_iso=now_iso,
        )
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["session_status"], "stale_blocked")
        self.assertIn("阻断", res["formatted_label"])

    def test_ingest_company_financials_balanced(self):
        """【UT-GATEWAY-04: 企业官方财报录入与资产负债表刚性平账自检(PERFECTLY_BALANCED)】

        1. 测试功能与测试点:
           - 验证 ingest_company_financials 接收财报事实并执行会计恒等式刚性平账。
           - 资产 == 负债 + 股东权益 时，评定为 PERFECTLY_BALANCED。

        2. 正常函数业务边界与参数契约:
           - total_assets == total_liabilities + stockholders_equity。

        3. 测试数据与模拟场景说明:
           - 营收 10 万，资产 50 万，负债 30 万，权益 20 万 (30 + 20 = 50)。

        4. 预期断言与结果验证:
           - balance_sheet_status == 'PERFECTLY_BALANCED'。
           - total_assets == 500000.0，stockholders_equity == 200000.0。
        """
        facts = {
            "revenue": 100000.0,
            "net_income": 25000.0,
            "operating_cash_flow": 30000.0,
            "total_assets": 500000.0,
            "total_liabilities": 300000.0,
            "stockholders_equity": 200000.0,  # 300000 + 200000 = 500000 严格平账
        }
        res = UnifiedDataCollectionGateway.ingest_company_financials("TEST", "US", facts)
        self.assertEqual(res["balance_sheet_status"], "PERFECTLY_BALANCED")
        self.assertEqual(res["total_assets"], 500000.0)
        self.assertEqual(res["stockholders_equity"], 200000.0)

    def test_ingest_company_financials_unbalanced_error(self):
        """【UT-GATEWAY-05: 资产负债表失衡刚性异常阻断抛出(BalanceSheetIdentityError)】

        1. 测试功能与测试点:
           - 验证当输入的资产负债表不平账时，网关立即刚性抛出 BalanceSheetIdentityError。
           - 杜绝会计逻辑错漏的垃圾数据流入任何估值或评级管道。

        2. 正常函数业务边界与参数契约:
           - 相对误差超界抛出强类型异常。

        3. 测试数据与模拟场景说明:
           - 资产 50 万，负债 30 万，权益 10 万 (30 + 10 = 40 != 50，差异 10 万)。

        4. 预期断言与结果验证:
           - 必须抛出 BalanceSheetIdentityError 异常。
        """
        facts = {
            "revenue": 100000.0,
            "net_income": 25000.0,
            "operating_cash_flow": 30000.0,
            "total_assets": 500000.0,
            "total_liabilities": 300000.0,
            "stockholders_equity": 100000.0,  # 300000 + 100000 = 400000 != 500000
        }
        with self.assertRaises(BalanceSheetIdentityError):
            UnifiedDataCollectionGateway.ingest_company_financials("TEST", "US", facts)

    def test_ingest_company_financials_missing_facts_error(self):
        """【UT-GATEWAY-06: 关键三表事实科目残缺刚性阻断抛出(IncompleteFilingFactError)】

        1. 测试功能与测试点:
           - 验证当关键科目（如未提供 revenue）缺失时，网关拒绝放行并抛出 IncompleteFilingFactError。

        2. 正常函数业务边界与参数契约:
           - revenue 必须有明确披露，真实零值仍是有效披露。

        3. 测试数据与模拟场景说明:
           - 省略 revenue 字段。

        4. 预期断言与结果验证:
           - 必须抛出 IncompleteFilingFactError 异常。
        """
        facts = {
            "total_assets": 500000.0,
            "total_liabilities": 300000.0,
            "stockholders_equity": 200000.0,
        }
        with self.assertRaises(IncompleteFilingFactError):
            UnifiedDataCollectionGateway.ingest_company_financials("TEST", "US", facts)

    def test_load_verified_batch_dossier(self):
        """【IT-GATEWAY-07: 已核验归档官方三表底账(AAPL)即时按需穿透加载】

        1. 测试功能与测试点:
           - 验证 load_verified_batch_dossier 穿透已核验批次数据，精准提取目标公司档案。

        2. 正常函数业务边界与参数契约:
           - 标的代码合法且已收录。

        3. 测试数据与模拟场景说明:
           - 检索苹果公司 (AAPL)。

        4. 预期断言与结果验证:
           - dossier 非空。
           - ticker == 'AAPL'。
           - company_name 包含 'Apple'。
        """
        dossier = UnifiedDataCollectionGateway.load_verified_batch_dossier("AAPL")
        self.assertIsNotNone(dossier)
        self.assertEqual(dossier["overview"]["ticker"], "AAPL")
        self.assertIn("Apple", dossier["overview"]["company_name"])

    def test_indexed_batch_slices(self):
        """【IT-GATEWAY-08: 78批次全息内存索引构建/按批切片与批号探查】

        1. 测试功能与测试点:
           - 验证 load_all_verified_dossiers_indexed 全局内存索引构建。
           - 验证 get_verified_batch_slice 按批次号切片提取能力。
           - 验证 get_all_verified_batch_numbers 批次覆盖完整性 (包含批次 1 与 78)。

        2. 正常函数业务边界与参数契约:
           - 批次范围在 1~78 之间。

        3. 测试数据与模拟场景说明:
           - 全量加载批次索引，提取第 1 批切片。

        4. 预期断言与结果验证:
           - 索引公司总数 > 100，包含 AAPL 与 NVDA。
           - 第 1 批切片长度 > 0，包含 AAPL。
           - 批号列表包含 1 与 78。
        """
        all_dossiers = UnifiedDataCollectionGateway.load_all_verified_dossiers_indexed()
        self.assertGreater(len(all_dossiers), 100)
        self.assertIn("AAPL", all_dossiers)
        self.assertIn("NVDA", all_dossiers)

        # 测试获取第 1 批切片
        slice_1 = UnifiedDataCollectionGateway.get_verified_batch_slice(1)
        self.assertGreater(len(slice_1), 0)
        tickers_slice_1 = [d.get("overview", {}).get("ticker") for d in slice_1]
        self.assertIn("AAPL", tickers_slice_1)

        # 测试获取全部有效批次列表
        batch_nums = UnifiedDataCollectionGateway.get_all_verified_batch_numbers()
        self.assertIn(1, batch_nums)
        self.assertIn(78, batch_nums)

    def test_generate_replenishment_gap_manifest(self):
        """【IT-GATEWAY-09: 跨市场(美股EDGAR/日股TDnet)缺失财报AI补数清单自动生成】

        1. 测试功能与测试点:
           - 验证 generate_replenishment_gap_manifest 为缺失财报公司生成标准补数任务清单。
           - 跨市场路由: 美股标的导向 SEC EDGAR，日股标的导向 TDnet/EDINET。

        2. 正常函数业务边界与参数契约:
           - 输入包含缺失标的列表与输出路径。

        3. 测试数据与模拟场景说明:
           - 美股标的 XYZ (CIK 0001234567)，日股标的 9999 (东证代码 9999)。

        4. 预期断言与结果验证:
           - total_pending_companies == 2。
           - 美股任务 target_filing 包含 'SEC EDGAR'。
           - 日股任务 target_filing 包含 'TDnet'。
           - 临时清单文件物理存在。
        """
        missing = [
            {"ticker": "XYZ", "market": "US", "company_name": "XYZ Corp", "cik": "0001234567"},
            {"ticker": "9999", "market": "JP", "company_name": "Test JP", "jpx_code": "9999"},
        ]
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            manifest = UnifiedDataCollectionGateway.generate_replenishment_gap_manifest(missing, tmp_path)
            self.assertEqual(manifest["total_pending_companies"], 2)
            self.assertEqual(len(manifest["tasks"]), 2)
            self.assertIn("SEC EDGAR", manifest["tasks"][0]["target_filing"])
            self.assertIn("TDnet", manifest["tasks"][1]["target_filing"])
            self.assertTrue(tmp_path.exists())
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


if __name__ == "__main__":
    unittest.main()
