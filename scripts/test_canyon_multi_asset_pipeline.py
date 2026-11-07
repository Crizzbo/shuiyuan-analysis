"""Canyon 多资产多态插槽单元测试套件 (Canyon Multi-Asset Polymorphic Pipeline Tests).

覆盖核心指数/行业 ETF、黄金大宗商品与普通股多态工位流动的单向线性执行、
刚性合规门禁阻断、多情景估值走廊约束与密码学时间链条验证。
"""

import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from financial_core.pipeline.canyon_linear_pipeline import (
    CanyonStationInput,
    CanyonDecisionCard,
    CanyonLinearPipeline,
    QuoteFreshnessError,
    BalanceSheetInvariantError,
)
from financial_core.engines.prediction_ledger import PredictionLedger
from financial_core import FinancialAnalysisSystem
from scripts.test_support.fixtures import isolated_facade_ledger, project_temp, freeze_quote_clock


class TestCanyonMultiAssetPipeline(unittest.TestCase):
    """Canyon 多资产多态插槽全链路验证。"""

    def setUp(self):
        self.temp_dir = project_temp(self, "test-canyon-assets-")
        self.ledger_db_path = Path(self.temp_dir) / "test_multi_asset_ledger.db"
        self.ledger = PredictionLedger(db_path=str(self.ledger_db_path))
        isolated_facade_ledger(self, self.ledger)
        self.pipeline = CanyonLinearPipeline(ledger=self.ledger)

        edt_tz = timezone(timedelta(hours=-4))
        self.now_fresh_ts = (freeze_quote_clock(self).astimezone(edt_tz) - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S EDT")
        now_fresh_ts = self.now_fresh_ts

        # 1. 标普 500 ETF (SPY) 标准合规输入样本
        self.valid_etf_input = CanyonStationInput(
            ticker="SPY",
            company_name="SPDR S&P 500 ETF Trust",
            market="US",
            sector="BroadMarketETF",
            asset_type="ETF",
            current_price=570.0,
            quote_timestamp=now_fresh_ts,
            market_session="regular_trading",
            etf_expense_ratio=0.000945,  # 0.0945% 费率
            etf_aum_billion=550.0,
            etf_top10_weight_pct=34.2,
            etf_underlying_nav=571.20,
            etf_tracking_error_pct=0.0012,
            company_beta=1.00,
            vix_index=18.5,
            us_10y_yield=0.042,
            fed_liquidity_drain_billion=40.0,
        )

        # 2. 实物黄金信托 (GLD) 标准合规输入样本
        self.valid_gold_input = CanyonStationInput(
            ticker="GLD",
            company_name="SPDR Gold Shares",
            market="US",
            sector="PreciousMetals",
            asset_type="COMMODITY_GOLD",
            current_price=245.50,
            quote_timestamp=now_fresh_ts,
            market_session="regular_trading",
            gold_tips_10y_real_yield=0.0185,  # 1.85% TIPS 实际利率
            gold_breakeven_inflation=0.0235,
            gold_central_bank_net_tonnes=1050.0,  # 主权央行年净购金 1050 吨
            gold_physical_premium_pct=0.025,      # 现货实物溢价 2.5%
            gold_traditional_anchor_price=240.0,
            company_beta=0.15,
            vix_index=18.5,
            us_10y_yield=0.042,
            fed_liquidity_drain_billion=40.0,
        )

    def test_etf_end_to_end_linear_flow_success(self):
        """【IT-CANYON-MA-01: ETF多态插槽全链路单向执行与费率折减估值走廊】

        1. 测试功能与测试点:
           - 验证 CanyonLinearPipeline 针对宽基/行业主题 ETF 资产的单向流水线穿透执行。
           - 估值三态走廊单调性: 悲观底价 <= 基准中性公允价 <= 乐观靶心。
           - 弹性安全边际 (Elastic MoS): ETF 分散化资产基准安全边际 >= 10.0%。
           - 击球买入底线: strike_price < neutral_fair_value。
           - 密码学账本存证: 产出 64 位 SHA-256 哈希存证，账本完整性验签通过。

        2. 正常函数业务边界与参数契约:
           - CanyonStationInput 中 asset_type="ETF"。
           - etf_expense_ratio 在 [0.0, 0.10] 之间，etf_top10_weight_pct 在 [0.0, 100.0] 之间。
           - 产出 CanyonDecisionCard 决策卡片。

        3. 测试数据与模拟场景说明:
           - 标的: SPDR 标普500 ETF (SPY)，现价 570.0 美元，费率 0.0945%，AUM 5500 亿美元，前十大权重 34.2%，NAV 571.20。

        4. 预期断言与结果验证:
           - 断言 card.asset_type == 'ETF' 且 label 包含 '核心指数与主题 ETF'。
           - 断言 card.pessimistic_floor <= card.neutral_fair_value <= card.optimistic_target。
           - 断言 card.strike_price < card.neutral_fair_value。
           - 断言 card.elastic_mos_pct >= 10.0。
           - 断言 len(card.ledger_hash) == 64 且 ledger.verify_integrity().is_valid 为 True。
        """
        card = self.pipeline.run(self.valid_etf_input)

        self.assertIsInstance(card, CanyonDecisionCard)
        self.assertEqual(card.ticker, "SPY")
        self.assertEqual(card.asset_type, "ETF")
        self.assertIn("核心指数与主题 ETF", card.asset_class_label)
        self.assertEqual(card.current_price, 570.0)

        # 估值单调走廊断言
        self.assertLessEqual(card.pessimistic_floor, card.neutral_fair_value)
        self.assertLessEqual(card.neutral_fair_value, card.optimistic_target)

        # 黄金击球买入底线断言
        self.assertLess(card.strike_price, card.neutral_fair_value)
        # ETF 基准安全边际为 10%
        self.assertGreaterEqual(card.elastic_mos_pct, 10.0)

        # 区位断言与存证
        self.assertIn(card.zone_status, ["GOLDEN_STRIKE_ZONE", "NEUTRAL_HOLD", "PREMIUM_OVERVALUED"])
        self.assertEqual(len(card.ledger_hash), 64)

        integrity = self.ledger.verify_integrity()
        self.assertTrue(integrity.is_valid)

    def test_gold_end_to_end_linear_flow_success(self):
        """【IT-CANYON-MA-02: 黄金大宗商品多态插槽全链路执行与逆周期避险弹性走廊】

        1. 测试功能与测试点:
           - 验证实物黄金信托 (GLD) 在 Canyon 工位管线中的宏观定价与多情景推演。
           - 实际利率与央行去美元化储备溢价动态走廊: 涵盖 10Y TIPS 真实利率锚与主权央行净购金增量。
           - 逆周期避险弹性安全边际: 大宗商品避险资产基准安全边际要求 >= 12.0%。
           - 区块链式时间链条上链与哈希确定性。

        2. 正常函数业务边界与参数契约:
           - asset_type="COMMODITY_GOLD"。
           - gold_tips_10y_real_yield 与 gold_physical_premium_pct 位于合规区间。

        3. 测试数据与模拟场景说明:
           - 标的: SPDR Gold Shares (GLD)，现价 245.50 美元，10Y TIPS 实际利率 1.85%，央行购金 1050 吨，实物溢价 2.5%。

        4. 预期断言与结果验证:
           - 断言 card.asset_type == 'COMMODITY_GOLD' 且 label 包含 '黄金与宏观贵金属'。
           - 断言 pessimistic_floor <= neutral_fair_value <= optimistic_target。
           - 断言 card.elastic_mos_pct >= 12.0。
           - 断言 len(card.ledger_hash) == 64 且 ledger.verify_integrity().is_valid 为 True。
        """
        card = self.pipeline.run(self.valid_gold_input)

        self.assertIsInstance(card, CanyonDecisionCard)
        self.assertEqual(card.ticker, "GLD")
        self.assertEqual(card.asset_type, "COMMODITY_GOLD")
        self.assertIn("黄金与宏观贵金属", card.asset_class_label)
        self.assertEqual(card.current_price, 245.50)

        # 估值单调走廊断言
        self.assertLessEqual(card.pessimistic_floor, card.neutral_fair_value)
        self.assertLessEqual(card.neutral_fair_value, card.optimistic_target)

        # 黄金逆周期避险基准安全边际为 12%
        self.assertGreaterEqual(card.elastic_mos_pct, 12.0)
        self.assertLess(card.strike_price, card.neutral_fair_value)

        # 密码学存证
        self.assertEqual(len(card.ledger_hash), 64)
        integrity = self.ledger.verify_integrity()
        self.assertTrue(integrity.is_valid)

    def test_etf_invalid_expense_ratio_blocked(self):
        """【UT-CANYON-MA-03: 工位2-ETF管理费率异常硬阻断与金融边界防御】

        1. 测试功能与测试点:
           - 验证 CanyonLinearPipeline 工位 2 对非法 ETF 费率的刚性阻断。
           - 当 ETF 管理费率极端离谱 (> 10%) 时，触发 BalanceSheetInvariantError 刚性阻断，保护下游估值模型免受异常数据污染。

        2. 正常函数业务边界与参数契约:
           - 0.0 <= etf_expense_ratio <= 0.10。超出该上限视作非标或伪造输入。

        3. 测试数据与模拟场景说明:
           - 模拟构造费率高达 15% (0.15) 的极端恶性 ETF 样本。

        4. 预期断言与结果验证:
           - 刚性抛出 BalanceSheetInvariantError 异常。
           - 异常描述信息明确包含“管理费率异常”。
        """
        bad_etf = CanyonStationInput(
            ticker="BAD_ETF",
            company_name="Overpriced ETF",
            asset_type="ETF",
            current_price=100.0,
            quote_timestamp=self.now_fresh_ts,
            etf_expense_ratio=0.15,  # 15% 极端离谱费率
        )
        with self.assertRaises(BalanceSheetInvariantError) as ctx:
            self.pipeline.run(bad_etf)
        self.assertIn("管理费率异常", str(ctx.exception))

    def test_etf_invalid_concentration_blocked(self):
        """【UT-CANYON-MA-04: 工位2-ETF前十大持仓集中度超界硬阻断】

        1. 测试功能与测试点:
           - 验证公理守恒: ETF 前十大持仓权重之和必然严格 <= 100%。
           - 当传入 > 100% 的集中度时，工位 2 立即阻断。

        2. 正常函数业务边界与参数契约:
           - 0.0 <= etf_top10_weight_pct <= 100.0。

        3. 测试数据与模拟场景说明:
           - 模拟构造前十大权重和为 105.0% 的非法 ETF 样本。

        4. 预期断言与结果验证:
           - 刚性抛出 BalanceSheetInvariantError。
           - 异常说明包含“前十大持仓集中度权重”。
        """
        bad_etf = CanyonStationInput(
            ticker="BAD_ETF",
            company_name="Impossible ETF",
            asset_type="ETF",
            current_price=100.0,
            quote_timestamp=self.now_fresh_ts,
            etf_expense_ratio=0.002,
            etf_top10_weight_pct=105.0,  # 超过 100%
        )
        with self.assertRaises(BalanceSheetInvariantError) as ctx:
            self.pipeline.run(bad_etf)
        self.assertIn("前十大持仓集中度权重", str(ctx.exception))

    def test_gold_extreme_physical_premium_blocked(self):
        """【UT-CANYON-MA-05: 工位2-黄金实物溢价率脱轨反常硬阻断】

        1. 测试功能与测试点:
           - 验证大宗商品无套利边界: 现货黄金实物溢价通常在小幅正负区间，反常极端溢价预示流动性黑天鹅或假账。
           - 溢价率超过阈值 (如 85%) 触发硬阻断。

        2. 正常函数业务边界与参数契约:
           - gold_physical_premium_pct 处于合理物理无套利约束走廊。

        3. 测试数据与模拟场景说明:
           - 溢价高达 85% (0.85) 的虚假实物黄金信托样本。

        4. 预期断言与结果验证:
           - 刚性抛出 BalanceSheetInvariantError。
           - 异常说明包含“实物溢价率”。
        """
        bad_gold = CanyonStationInput(
            ticker="FAKE_GOLD",
            company_name="Suspicious Gold Trust",
            asset_type="COMMODITY_GOLD",
            current_price=240.0,
            quote_timestamp=self.now_fresh_ts,
            gold_physical_premium_pct=0.85,  # 溢价达 85% 极其反常
        )
        with self.assertRaises(BalanceSheetInvariantError) as ctx:
            self.pipeline.run(bad_gold)
        self.assertIn("实物溢价率", str(ctx.exception))

    def test_multi_asset_cryptographic_chain_continuity(self):
        """【IT-CANYON-MA-06: 跨资产类别(股票/ETF/黄金)连续执行密码学哈希时间链条防篡改断言】

        1. 测试功能与测试点:
           - 验证股票、ETF、大宗商品等不同多态资产混合连续入库时，PredictionLedger 时间链条的连贯性与密码学自洽性。
           - 前后区块链式哈希指针校验 (previous_hash -> current_hash)。
           - 防篡改验收 (verify_integrity)。

        2. 正常函数业务边界与参数契约:
           - 连续执行不同类型的 CanyonStationInput。
           - ledger.verify_integrity().is_valid == True。

        3. 测试数据与模拟场景说明:
           - 顺序执行: 1. 普通股票 (MSFT); 2. 宽基 ETF (SPY); 3. 实物黄金 (GLD)。

        4. 预期断言与结果验证:
           - 断言 ledger.verify_integrity().is_valid 为 True。
           - 断言 ledger.verify_integrity().error 为 None。
        """
        # 1. 股票
        stock_input = CanyonStationInput(
            ticker="MSFT",
            company_name="Microsoft Corp",
            asset_type="EQUITY",
            current_price=420.0,
            quote_timestamp=self.now_fresh_ts,
            total_assets=400000.0,
            total_liabilities=220000.0,
            stockholders_equity=180000.0,
            reported_operating_cash_flow=110000.0,
            reported_capex=25000.0,
            shares_outstanding=7400.0,
        )
        self.pipeline.run(stock_input)

        # 2. ETF
        self.pipeline.run(self.valid_etf_input)

        # 3. 黄金
        self.pipeline.run(self.valid_gold_input)

        integrity = self.ledger.verify_integrity()
        self.assertTrue(integrity.is_valid)
        self.assertIsNone(integrity.error)

    def test_facade_analyze_linear_multi_asset_integration(self):
        """【IT-CANYON-MA-07: 统一顶层门面FinancialAnalysisSystem多资产线性决策透明支持】

        1. 测试功能与测试点:
           - 验证金融分析系统总门面 FinancialAnalysisSystem.analyze_linear_equity 对多态资产的透明路由能力。
           - 确保外部调用方无需感知底层复杂工位，仅通过同一门面接口即可完成多资产多态估值。

        2. 正常函数业务边界与参数契约:
           - 输入合法 CanyonStationInput，返回决策卡片 CanyonDecisionCard。

        3. 测试数据与模拟场景说明:
           - 分别注入 SPY 与 GLD 输入样本。

        4. 预期断言与结果验证:
           - 断言 card_etf.ticker == 'SPY' 且 asset_type == 'ETF'。
           - 断言 card_gold.ticker == 'GLD' 且 asset_type == 'COMMODITY_GOLD'。
        """
        system = FinancialAnalysisSystem()
        card_etf = system.analyze_linear_equity(self.valid_etf_input)
        self.assertEqual(card_etf.ticker, "SPY")
        self.assertEqual(card_etf.asset_type, "ETF")

        card_gold = system.analyze_linear_equity(self.valid_gold_input)
        self.assertEqual(card_gold.ticker, "GLD")
        self.assertEqual(card_gold.asset_type, "COMMODITY_GOLD")


if __name__ == "__main__":
    unittest.main()
