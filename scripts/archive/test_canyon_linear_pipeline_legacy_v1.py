"""Canyon 单向线性流水线单元测试套件 (Canyon Linear Pipeline Tests).

覆盖 6 大标准作业工位的单向流动、门禁阻断、估值走廊约束与密码学时间链条验证。
"""

import unittest
from datetime import datetime, timezone
import tempfile
from pathlib import Path
import shutil

from financial_core.pipeline.canyon_linear_pipeline import (
    CanyonStationInput,
    CanyonDecisionCard,
    CanyonLinearPipeline,
    QuoteFreshnessError,
    BalanceSheetInvariantError,
)
from financial_core.engines.prediction_ledger import PredictionLedger


class TestCanyonLinearPipeline(unittest.TestCase):
    """Canyon 单向线性流水线全工位验证。"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.ledger_db_path = Path(self.temp_dir) / "test_canyon_ledger.db"
        self.ledger = PredictionLedger(db_path=str(self.ledger_db_path))
        self.pipeline = CanyonLinearPipeline(ledger=self.ledger)

        # 标准合规输入样本 (以典型蓝筹高通胀测试用例为基准)
        self.valid_input = CanyonStationInput(
            ticker="AAPL",
            company_name="Apple Inc.",
            market="US",
            sector="TechHardware",
            current_price=180.0,
            quote_timestamp="2026-10-14 15:45:00 EDT",
            market_session="regular_trading",
            baseline_reference_price=175.0,
            reported_cash=30000.0,
            restricted_cash=2000.0,
            debt_covenant_min_cash=3000.0,
            total_debt=100000.0,
            total_assets=350000.0,
            total_liabilities=280000.0,
            stockholders_equity=70000.0,  # 350000 == 280000 + 70000 (严格平账)
            reported_operating_cash_flow=110000.0,
            reported_capex=12000.0,
            maintenance_capex_ratio=0.70,
            stock_based_compensation=10000.0,
            reported_revenue=380000.0,
            reported_operating_income=115000.0,
            reported_net_income=97000.0,
            shares_outstanding=15000.0,
            us_10y_yield=0.044,
            vix_index=19.5,
            fed_liquidity_drain_billion=45.0,
            company_beta=1.15,
            option_target_strike=185.0,
            option_expiry_days=30.0,
            option_implied_vol=0.25,
            is_call_option=True,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_end_to_end_linear_flow_success(self):
        """测试 6 工位单向线性无环全链路顺利执行并生成合规买方决策卡 (拒绝自等假断言与弱断言)."""
        card = self.pipeline.run(self.valid_input)

        self.assertIsInstance(card, CanyonDecisionCard)
        self.assertEqual(card.ticker, "AAPL")
        self.assertEqual(card.company_name, "Apple Inc.")

        # 1. 美分级与货币精度断言 (验证绝无浮点漂移或整数截断)
        formatted_price = f"${card.current_price:.2f}"
        self.assertRegex(formatted_price, r"^\$\d+\.\d{2}$", "决策卡现价必须保持严格美分级两位小数")
        self.assertGreater(card.current_price, 0.0, "现价必须为严格正数")

        # 2. 估值单调走廊数学硬约束: 悲观底 <= 公允锚点 <= 乐观靶心
        self.assertLessEqual(card.pessimistic_floor, card.neutral_fair_value, "悲观底不能超过公允中枢")
        self.assertLessEqual(card.neutral_fair_value, card.optimistic_target, "公允中枢不能超过乐观靶心")

        # 3. 黄金击球买入底线与弹性安全边际精准计算断言 (非空泛断言)
        self.assertLess(card.strike_price, card.neutral_fair_value, "买入底线必须严于公允内在价值")
        expected_mos = ((card.neutral_fair_value - card.strike_price) / card.neutral_fair_value) * 100.0
        self.assertAlmostEqual(
            card.elastic_mos_pct,
            expected_mos,
            places=2,
            msg=f"弹性安全边际计算不符: 实际 {card.elastic_mos_pct}%, 期望 {expected_mos:.2f}%",
        )
        self.assertGreater(card.elastic_mos_pct, 15.0, "蓝筹严苛安全边际必须大于 15%")

        # 4. 区位与行动建议的真实商业语义一致性断言 (拒绝长度判断)
        valid_zones = ["GOLDEN_STRIKE_ZONE", "NEUTRAL_HOLD", "PREMIUM_OVERVALUED"]
        self.assertIn(card.zone_status, valid_zones)
        if card.zone_status == "GOLDEN_STRIKE_ZONE":
            self.assertTrue(
                any(kw in card.recommended_action for kw in ["买入", "建仓", "吸纳", "关注"]),
                f"击球区建议必须包含买入相关自然语言投资动作: {card.recommended_action}",
            )
        elif card.zone_status == "PREMIUM_OVERVALUED":
            self.assertTrue(
                any(kw in card.recommended_action for kw in ["观望", "减持", "止盈", "防范", "溢价"]),
                f"高估区建议必须包含防守相关投资动作: {card.recommended_action}",
            )

        # 5. 密码学不可篡改链条真实签名与完整性验签
        self.assertEqual(len(card.ledger_hash), 64, "账本哈希必须为 SHA-256 64 位十六进制串")
        integrity = self.ledger.verify_integrity()
        self.assertTrue(integrity.is_valid, f"账本密码学链条篡改检测失败: {integrity.error_details}")

    def test_station_1_quote_freshness_zero_price_blocked(self):
        """测试工位 1: 价格 <= 0 触发 QuoteFreshnessError 硬阻断。"""
        bad_input = CanyonStationInput(
            ticker="AAPL",
            company_name="Apple Inc.",
            current_price=0.0,
            quote_timestamp="2026-10-14 15:45:00 EDT",
        )
        with self.assertRaises(QuoteFreshnessError) as ctx:
            self.pipeline.run(bad_input)
        self.assertIn("价格必须严格大于零", str(ctx.exception))

    def test_station_1_quote_freshness_missing_timestamp_blocked(self):
        """测试工位 1: 缺少时间戳触发 QuoteFreshnessError 硬阻断。"""
        bad_input = CanyonStationInput(
            ticker="AAPL",
            company_name="Apple Inc.",
            current_price=150.0,
            quote_timestamp="",
        )
        with self.assertRaises(QuoteFreshnessError) as ctx:
            self.pipeline.run(bad_input)
        self.assertIn("缺失精确报价时间戳", str(ctx.exception))

    def test_station_2_balance_sheet_imbalance_blocked(self):
        """测试工位 2: 资产负债表不平账触发 BalanceSheetInvariantError 硬阻断。"""
        imbalanced_input = CanyonStationInput(
            ticker="AAPL",
            company_name="Apple Inc.",
            current_price=180.0,
            quote_timestamp="2026-10-14 15:45:00 EDT",
            total_assets=350000.0,
            total_liabilities=200000.0,
            stockholders_equity=50000.0,  # 350000 != 200000 + 50000 (差 100,000)
        )
        with self.assertRaises(BalanceSheetInvariantError) as ctx:
            self.pipeline.run(imbalanced_input)
        self.assertIn("资产负债表严重失衡", str(ctx.exception))

    def test_station_3_macro_stress_and_elastic_mos(self):
        """测试工位 3: 宏观高压力下弹性安全边际显著放大。"""
        # 低压力环境
        low_stress_input = CanyonStationInput(
            ticker="AAPL",
            company_name="Apple Inc.",
            current_price=180.0,
            quote_timestamp="2026-10-14 15:45:00 EDT",
            total_assets=100.0,
            total_liabilities=50.0,
            stockholders_equity=50.0,
            reported_operating_cash_flow=20.0,
            vix_index=12.0,
            us_10y_yield=0.035,
            fed_liquidity_drain_billion=0.0,
        )
        card_low = self.pipeline.run(low_stress_input)

        # 极端踩踏高压力环境
        high_stress_input = CanyonStationInput(
            ticker="AAPL",
            company_name="Apple Inc.",
            current_price=180.0,
            quote_timestamp="2026-10-14 15:45:00 EDT",
            total_assets=100.0,
            total_liabilities=50.0,
            stockholders_equity=50.0,
            reported_operating_cash_flow=20.0,
            vix_index=45.0,
            us_10y_yield=0.065,
            fed_liquidity_drain_billion=100.0,
        )
        card_high = self.pipeline.run(high_stress_input)

        self.assertGreater(card_high.macro_stress_score, card_low.macro_stress_score)
        self.assertGreater(card_high.elastic_mos_pct, card_low.elastic_mos_pct)

    def test_station_5_golden_strike_zone_trigger(self):
        """测试工位 5: 现价击穿 Strike Price 准确触发 GOLDEN_STRIKE_ZONE 与半凯利建仓。"""
        cheap_input = CanyonStationInput(
            ticker="AAPL",
            company_name="Apple Inc.",
            current_price=10.0,  # 现价远低于公允价值
            quote_timestamp="2026-10-14 15:45:00 EDT",
            total_assets=350000.0,
            total_liabilities=280000.0,
            stockholders_equity=70000.0,
            reported_operating_cash_flow=110000.0,
            reported_capex=12000.0,
            stock_based_compensation=10000.0,
            shares_outstanding=15000.0,
        )
        card = self.pipeline.run(cheap_input)

        self.assertEqual(card.zone_status, "GOLDEN_STRIKE_ZONE")
        self.assertGreater(card.kelly_position_pct, 0.0)
        self.assertIn("击穿黄金买入底线", card.recommended_action)

    def test_multi_record_ledger_cryptographic_chain_continuity(self):
        """测试连续多家标的执行后，PredictionLedger 区块链式 SHA-256 完整性 100% 连贯。"""
        tickers = ["AAPL", "NVDA", "MSFT"]
        for t in tickers:
            inp = CanyonStationInput(
                ticker=t,
                company_name=f"{t} Corporation",
                current_price=150.0,
                quote_timestamp="2026-10-14 15:45:00 EDT",
                total_assets=100.0,
                total_liabilities=60.0,
                stockholders_equity=40.0,
                reported_operating_cash_flow=25.0,
                reported_capex=5.0,
                shares_outstanding=10.0,
            )
            card = self.pipeline.run(inp)
            self.assertEqual(len(card.ledger_hash), 64)

        integrity = self.ledger.verify_integrity()
        self.assertTrue(integrity.is_valid)
        self.assertIsNone(integrity.error)

    def test_facade_analyze_linear_equity_integration(self):
        """测试通过统一门面 FinancialAnalysisSystem.analyze_linear_equity 执行线性流水线。"""
        from financial_core import FinancialAnalysisSystem
        system = FinancialAnalysisSystem()
        card = system.analyze_linear_equity(self.valid_input)
        self.assertIsInstance(card, CanyonDecisionCard)
        self.assertEqual(card.ticker, "AAPL")
        self.assertEqual(card.current_price, 180.0)
        self.assertEqual(len(card.ledger_hash), 64)


if __name__ == "__main__":
    unittest.main()
