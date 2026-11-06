"""单元测试：全盘分级资产池管理器 (test_tiered_universe_manager.py).

验证：
1. 全盘美股与日股公司资产池加载与统计;
2. 分级标记 (Tier 0, Tier 1, Tier 2, Tier 3);
3. 单标的代码检索 (美股与日股代码/名称);
4. 分批切片调度 (Batch Chunking);
5. S&P 500 优先收集队列生成.
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.tiered_universe_manager import (
    TieredUniverseManager,
    TieredUniverseStats,
    UniverseCompanyRecord,
)


class TestTieredUniverseManager(unittest.TestCase):
    """测试 TieredUniverseManager 全盘分级管理功能."""

    def setUp(self):
        self.manager = TieredUniverseManager()
        self.manager.load_universe()

    def test_01_load_stats(self):
        """【UT-UNIVERSE-01: 万家分级资产池规模统计与四级金字塔(Tier0~3)配比审计】

        1. 测试功能与测试点:
           - 验证 TieredUniverseManager.get_stats 统计美股 (SEC 10,000+) 与日股 (JPX 4,400+) 全盘资产池底账。
           - 验证分级资产池架构 (Tiered Universe Architecture) 数量分布:
             Tier 0 (核心旗舰), Tier 1 (主线成长), Tier 2/3 (全市场海量基础池)。

        2. 正常函数业务边界与参数契约:
           - manager.load_universe() 加载底账，返回 TieredUniverseStats 统计结构体。

        3. 测试数据与模拟场景说明:
           - 基于 data/universe/ 底账文件全量解析。

        4. 预期断言与结果验证:
           - 断言 total_companies > 14000。
           - 断言 us_sec_count > 10000 且 jp_jpx_count > 4000。
           - 断言 tier_1_count > 400 且 tier_3_count > 8000。
        """
        stats: TieredUniverseStats = self.manager.get_stats()
        self.assertGreater(stats.total_companies, 14000)
        self.assertGreater(stats.us_sec_count, 10000)
        self.assertGreater(stats.jp_jpx_count, 4000)
        self.assertGreater(stats.tier_1_count, 400)
        self.assertGreater(stats.tier_3_count, 8000)

    def test_02_lookup_companies(self):
        """【UT-UNIVERSE-02: 跨市场双向代码秒级检索(SEC CIK/东证四位码/企业全称)】

        1. 测试功能与测试点:
           - 验证 TieredUniverseManager.lookup 检索美股代码、SEC 官方 CIK 与日股东证代码能力。
           - 保证输入标的代码时能够在纳秒/微秒级准确定位到 UniverseCompanyRecord。

        2. 正常函数业务边界与参数契约:
           - 输入 ticker 字符串与可选 market ("US" / "JP")。
           - 存在时返回 UniverseCompanyRecord，不存在时返回 None。

        3. 测试数据与模拟场景说明:
           - 美股: NVDA (CIK 0001045810), AAPL (CIK 0000320193)。
           - 日股: 7203 (丰田汽车 Toyota Motor)。

        4. 预期断言与结果验证:
           - 断言 nvda 存在，market == 'US'，CIK 以 1045810 结尾。
           - 断言 aapl 存在，CIK 以 320193 结尾。
           - 断言 toyota 存在，market == 'JP'，名称包含 'トヨタ'。
        """
        # 检索美股 NVDA
        nvda = self.manager.lookup("NVDA")
        self.assertIsNotNone(nvda)
        self.assertEqual(nvda.ticker, "NVDA")
        self.assertEqual(nvda.market, "US")
        self.assertTrue(nvda.cik.endswith("1045810"))

        # 检索美股 AAPL
        aapl = self.manager.lookup("AAPL")
        self.assertIsNotNone(aapl)
        self.assertEqual(aapl.ticker, "AAPL")
        self.assertTrue(aapl.cik.endswith("320193"))

        # 检索日股 (7203 丰田汽车)
        toyota = self.manager.lookup("7203", market="JP")
        self.assertIsNotNone(toyota)
        self.assertEqual(toyota.market, "JP")
        self.assertIn("トヨタ", toyota.company_name)

    def test_03_batch_chunking(self):
        """【IT-UNIVERSE-03: 流式分批切片调度器(Batch Chunking)与批次间无重叠公理验证】

        1. 测试功能与测试点:
           - 验证 TieredUniverseManager.get_batch_chunk 分批切片管道。
           - 为早 07:00 (美股) 与 16:00 (日股) 批量分析提供稳定的流式吞吐。
           - 刚性无重叠公理: Batch 0 与 Batch 1 标的交集严格为空集。

        2. 正常函数业务边界与参数契约:
           - market in ("US", "JP"), batch_index >= 0, batch_size > 0。
           - 返回切片列表 List[UniverseCompanyRecord]。

        3. 测试数据与模拟场景说明:
           - 抽取美股第 0 批 (size=20) 与第 1 批 (size=20)。

        4. 预期断言与结果验证:
           - 断言 len(chunk_0) == 20 且 len(chunk_1) == 20。
           - 断言 c0_tickers 与 c1_tickers 交集长度严格等于 0。
        """
        chunk_0 = self.manager.get_batch_chunk(market="US", batch_index=0, batch_size=20)
        self.assertEqual(len(chunk_0), 20)

        chunk_1 = self.manager.get_batch_chunk(market="US", batch_index=1, batch_size=20)
        self.assertEqual(len(chunk_1), 20)

        # 两个批次无重叠
        c0_tickers = {c.ticker for c in chunk_0}
        c1_tickers = {c.ticker for c in chunk_1}
        self.assertEqual(len(c0_tickers.intersection(c1_tickers)), 0)

    def test_04_sp500_priority_list(self):
        """【IT-UNIVERSE-04: S&P 500核心权重资产池优先队列生成与标的穿透提取】

        1. 测试功能与测试点:
           - 验证 TieredUniverseManager.get_sp500_priority_collection_list 提取核心优先分析队列。
           - 确保高价值旗舰权重资产（S&P 500）优先进入 Tier 0/1 采集与档案更新主管道。

        2. 正常函数业务边界与参数契约:
           - unarchived_only: bool 控制是否过滤已归档。
           - 返回 List[UniverseCompanyRecord]。

        3. 测试数据与模拟场景说明:
           - 全量 S&P 500 成分股优先列表提取。

        4. 预期断言与结果验证:
           - 断言 priority_list 数量 > 450。
           - 提取集合必须包含 'AAPL'、'MSFT' 与 'GOOGL'。
        """
        priority_list = self.manager.get_sp500_priority_collection_list(unarchived_only=False)
        self.assertGreater(len(priority_list), 450)
        tickers = {c.ticker for c in priority_list}
        self.assertIn("AAPL", tickers)
        self.assertIn("MSFT", tickers)
        self.assertIn("GOOGL", tickers)


if __name__ == "__main__":
    unittest.main()
