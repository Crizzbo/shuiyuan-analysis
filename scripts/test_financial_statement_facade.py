#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/test_financial_statement_facade.py

企业财报与时效数据防腐中继门面 (FinancialStatementFacade) 契约与功能测试用例集
- 验证官方财报刚性平账自检 (Assets = Liabilities + Equity)
- 验证平账失衡与缺失核心科目的硬拦截
- 验证通用关键比率与存货周转天数 DIO 安全计算
- 验证行情数据时效性与交易时段状态门禁集成
"""

from datetime import datetime, timezone
import unittest
from financial_core.engines.financial_statement_facade import (
    FinancialStatementFacade,
    NormalizedFinancialProfile,
    BalanceSheetIdentityError,
    IncompleteFilingFactError,
)


class TestFinancialStatementFacade(unittest.TestCase):
    """财报防腐中继门面契约与鲁棒性测试"""

    def setUp(self):
        self.facade = FinancialStatementFacade()

    def test_fsf_01_valid_filing_ingestion_and_metrics(self):
        """【FSF-01: 正常平账财报摄入与全息指标计算】"""
        raw_facts = {
            "ticker": "AAPL",
            "company_name": "Apple Inc.",
            "currency": "USD",
            "fiscal_period": "FY2026",
            "total_assets": 1000.0,
            "total_liabilities": 600.0,
            "total_equity": 400.0,
            "cash_and_equivalents": 150.0,
            "total_debt": 250.0,
            "revenue": 800.0,
            "gross_profit": 320.0,
            "operating_income": 240.0,
            "net_income": 200.0,
            "free_cash_flow": 210.0,
            "inventory": 60.0,
            "cogs": 480.0,
            "interest_expense": 20.0,
            "shares_outstanding": 10.0,
        }
        raw_quote = {
            "price": 220.0,
            "timestamp": "2026-11-05 10:30:00 EST",
            "session": "Regular Trading",
            "current_time_iso": "2026-11-05T10:35:00-05:00",
        }

        profile = self.facade.process_company_filing(raw_facts, raw_quote_data=raw_quote)

        self.assertIsInstance(profile, NormalizedFinancialProfile)
        self.assertEqual(profile.ticker, "AAPL")
        self.assertTrue(profile.is_balanced)
        self.assertAlmostEqual(profile.balance_discrepancy, 0.0)

        # 校验指标计算
        self.assertAlmostEqual(profile.gross_margin, 320.0 / 800.0)  # 40%
        self.assertAlmostEqual(profile.operating_margin, 240.0 / 800.0)  # 30%
        self.assertAlmostEqual(profile.net_margin, 200.0 / 800.0)  # 25%
        self.assertAlmostEqual(profile.roe, 200.0 / 400.0)  # 50%
        self.assertAlmostEqual(profile.net_cash, -100.0)  # 150 - 250 = -100

        # 存货周转天数 DIO: (60 * 365) / 480 = 45.625 天
        self.assertAlmostEqual(profile.inventory_turnover_days, 45.625)
        self.assertAlmostEqual(profile.interest_coverage_ratio, 240.0 / 20.0)  # 12x

        # 校验行情时效集成
        self.assertEqual(profile.quote_price, 220.0)
        self.assertEqual(profile.market_session, "regular_trading")

    def test_fsf_02_balance_sheet_imbalance_rejection(self):
        """【FSF-02: 资产负债不平硬拦截】偏差超出 0.1% 容差严禁通过"""
        imbalanced_facts = {
            "ticker": "FAKE",
            "total_assets": 1000.0,
            "total_liabilities": 500.0,
            "total_equity": 400.0,  # 资产 1000 != 负债 500 + 权益 400 (差 100, 10% 偏差)
            "revenue": 500.0,
        }
        with self.assertRaises(BalanceSheetIdentityError) as ctx:
            self.facade.process_company_filing(imbalanced_facts)
        self.assertIn("资产负债恒等式严重破损", str(ctx.exception))

    def test_fsf_03_missing_core_asset_rejection(self):
        """【FSF-03: 缺失总资产核心科目硬拦截】"""
        missing_facts = {
            "ticker": "NO_ASSETS",
            "total_assets": 0.0,
            "total_liabilities": 0.0,
            "total_equity": 0.0,
        }
        with self.assertRaises(IncompleteFilingFactError) as ctx:
            self.facade.process_company_filing(missing_facts)
        self.assertIn("缺失总资产核心科目", str(ctx.exception))

    def test_fsf_04_zero_division_safety(self):
        """【FSF-04: 金融数学边界防御与除零保护】"""
        zero_facts = {
            "ticker": "ZERO_BIZ",
            "total_assets": 100.0,
            "total_liabilities": 50.0,
            "total_equity": 50.0,
            "revenue": 0.0,  # 零营收
            "gross_profit": 0.0,
            "operating_income": 0.0,
            "net_income": 0.0,
            "inventory": 0.0,
            "cogs": 0.0,  # 零成本
            "interest_expense": 0.0,
        }
        # 不应抛出 ZeroDivisionError
        profile = self.facade.process_company_filing(zero_facts)
        self.assertEqual(profile.gross_margin, 0.0)
        self.assertEqual(profile.operating_margin, 0.0)
        self.assertEqual(profile.inventory_turnover_days, 0.0)
        self.assertEqual(profile.interest_coverage_ratio, 0.0)


if __name__ == "__main__":
    unittest.main()
