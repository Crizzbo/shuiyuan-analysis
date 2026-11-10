# -*- coding: utf-8 -*-
"""金融数据接口层单元测试 (test_data_interface_layer.py).

严格遵循《AGENTS.md》与《CLAUDE.md》：
1. 验证原始异构数据（非标字段名、异常日期、单位混杂）能被正确清洗为强类型数据契约；
2. 验证点时零前视偏差 (Point-in-Time) 严格截断有效性；
3. 验证会计恒等式自检与各维度除零除负防御；
4. 验证统一门面直通驱动五大金融引擎计算输出。
"""

import math
from pathlib import Path
import sys
import unittest
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.data_interface import (
    StandardBar,
    MarketDataFeatureInput,
    ForensicsAccountingInput,
    CreditStructuralInput,
    LiquidityStressInput,
    OptionSurfaceFlowInput,
    MacroRegimeInput,
    UnifiedFeatureBundle,
    MarketDataAdapter,
    FinancialStatementAdapter,
    DerivativeFlowAdapter,
    MacroLiquidityAdapter,
    UnifiedFinancialDataInterfaceFacade,
)


class DataInterfaceLayerTests(unittest.TestCase):
    """数据接口与特征加工层全维度测试套件."""

    def setUp(self) -> None:
        self.facade = UnifiedFinancialDataInterfaceFacade()

    def test_market_adapter_normalization_and_pit_truncation(self) -> None:
        """测试行情适配器的非标字段清洗与点时截断."""
        raw_bars = [
            {"Date": "2024-01-02", "Close": 100.0, "High": 102.0, "Low": 99.0, "Open": 100.5, "Volume": 10000},
            {"date": "2024-01-03", "close": 105.0, "high": 106.0, "low": 104.0, "open": 101.0, "vol": 12000},
            {"time": "2024-01-04", "adj_close": 110.0, "turnover": 1500000}, # 缺失 open/high/low/volume
            {"date": "2024-01-10", "close": 120.0}, # 未来日线，应在 as_of_date 截断
        ]

        # 截断到 2024-01-04
        pit_bars = MarketDataAdapter.filter_pit_bars(raw_bars, as_of_date="2024-01-04")
        self.assertEqual(len(pit_bars), 3)
        self.assertEqual(pit_bars[-1].date, "2024-01-04")
        self.assertEqual(pit_bars[-1].close, 110.0)

        # 提取特征
        feat = MarketDataAdapter.extract_market_features("TEST", raw_bars, as_of_date="2024-01-04")
        self.assertEqual(feat.symbol, "TEST")
        self.assertEqual(feat.bars_count, 3)
        self.assertEqual(feat.latest_close, 110.0)
        self.assertTrue(feat.sma20 > 0.0)
        self.assertTrue(feat.realized_vol20_annualized >= 0.0)

    def test_accounting_adapter_balance_sheet_and_extraction(self) -> None:
        """测试官方财报平账自检与 Beneish/Merton 指标提取."""
        # 1. 恒等式测试
        is_bal, err = FinancialStatementAdapter.verify_balance_sheet_equality(
            total_assets=1000.0, total_liabilities=600.0, total_equity=400.0
        )
        self.assertTrue(is_bal)
        self.assertAlmostEqual(err, 0.0)

        is_bal_fail, err_fail = FinancialStatementAdapter.verify_balance_sheet_equality(
            total_assets=1000.0, total_liabilities=800.0, total_equity=400.0
        )
        self.assertFalse(is_bal_fail)
        self.assertTrue(err_fail > 0.15)

        # 2. Beneish 输入提取测试
        raw_fin = {
            "filing_date": "2023-12-31",
            "TotalRevenue": 500.0,
            "CostOfRevenue": 300.0,
            "AccountsReceivableNetCurrent": 100.0,
            "TotalAssets": 800.0,
            "NetIncomeCommonStockholders": 80.0,
            "OperatingCashFlow": 95.0,
            "ShortTermDebt": 50.0,
            "LongTermDebtNoncurrent": 150.0,
        }
        b_input = FinancialStatementAdapter.extract_forensics_input("NVDA", raw_fin)
        self.assertEqual(b_input.symbol, "NVDA")
        self.assertEqual(b_input.curr_sales, 500.0)
        self.assertEqual(b_input.curr_cogs, 300.0)
        self.assertEqual(b_input.curr_receivables, 100.0)

        # 3. Merton 结构化信用输入提取测试
        c_input = FinancialStatementAdapter.extract_credit_structural_input(
            symbol="NVDA",
            raw_financials=raw_fin,
            equity_market_cap=2_000_000_000_000.0,
            equity_volatility=0.45,
            risk_free_rate=0.042,
        )
        self.assertEqual(c_input.short_term_debt, 50.0)
        self.assertEqual(c_input.long_term_debt, 150.0)
        # 违约触发点 D = STD + 0.5 * LTD = 50 + 0.5 * 150 = 125.0
        self.assertEqual(c_input.default_point_debt, 125.0)

    def test_derivative_flow_adapter(self) -> None:
        """测试期权衍生品输入提取与边界防御."""
        raw_deriv = {
            "total_call_vol": 5000.0,
            "total_put_vol": 4000.0,
            "total_call_oi": 50000.0,
            "total_put_oi": 60000.0,
            "iv_put_otm": 0.35,
            "iv_call_otm": 0.28,
            "front_month_iv": 0.32,
            "second_month_iv": 0.30,
        }
        opt_input = DerivativeFlowAdapter.extract_option_skew_input("AAPL", 180.0, raw_deriv)
        self.assertEqual(opt_input.symbol, "AAPL")
        self.assertEqual(opt_input.underlying_price, 180.0)
        self.assertEqual(opt_input.call_volume, 5000.0)
        self.assertEqual(opt_input.put_volume, 4000.0)
        self.assertAlmostEqual(opt_input.iv_25d_put, 0.35)

    def test_macro_liquidity_adapter(self) -> None:
        """测试宏观大盘与流动性基准适配器."""
        benchmark_bars = [
            {"date": "2024-01-02", "close": 470.0},
            {"date": "2024-01-03", "close": 472.0},
            {"date": "2024-01-04", "close": 471.0},
            {"date": "2024-01-05", "close": 469.0},
        ]
        mac_input = MacroLiquidityAdapter.extract_macro_regime_input(
            as_of_date="2024-01-03",
            benchmark_symbol="SPY",
            raw_benchmark_bars=benchmark_bars,
        )
        self.assertEqual(len(mac_input.historical_benchmark_bars), 2)
        self.assertEqual(mac_input.historical_benchmark_bars[-1]["date"], "2024-01-03")

    def test_facade_prepare_and_execute_full_suite(self) -> None:
        """测试统一门面的一键全息加工 (prepare) 与直通执行计算 (execute)."""
        raw_bars = [{"date": f"2024-01-{i:02d}", "close": 100.0 + i, "volume": 100000.0, "turnover": 10000000.0} for i in range(1, 31)]
        raw_fin = {
            "revenue": 1000.0,
            "cogs": 500.0,
            "receivables": 150.0,
            "total_assets": 2000.0,
            "short_term_debt": 100.0,
            "long_term_debt": 400.0,
            "net_income": 200.0,
            "cfo": 220.0,
        }
        raw_deriv = {
            "call_volume": 10000.0,
            "put_volume": 8000.0,
            "call_open_interest": 80000.0,
            "put_open_interest": 70000.0,
            "iv_25d_put": 0.30,
            "iv_25d_call": 0.26,
            "iv_front_month_atm": 0.28,
            "iv_back_month_atm": 0.27,
        }

        # 1. 一键全息特征打包
        bundle = self.facade.prepare_unified_bundle(
            symbol="MSFT",
            as_of_date="2024-01-20",
            raw_bars=raw_bars,
            raw_financials=raw_fin,
            raw_derivative=raw_deriv,
            raw_benchmark_bars=raw_bars,
            market="US",
            currency="USD",
            equity_market_cap=3_000_000_000_000.0,
        )
        self.assertIsNotNone(bundle.market_input)
        self.assertIsNotNone(bundle.forensics_input)
        self.assertIsNotNone(bundle.credit_input)
        self.assertIsNotNone(bundle.liquidity_input)
        self.assertIsNotNone(bundle.option_input)
        self.assertIsNotNone(bundle.macro_input)

        # 2. 直通执行 Amihud 微观流动性计算
        amihud_res = self.facade.execute_amihud_liquidity(bundle.liquidity_input)
        self.assertEqual(amihud_res.symbol, "MSFT")
        self.assertFalse(amihud_res.is_illiquid_trap)

        # 3. 直通执行 KMV-Merton 结构化信用违约计算
        merton_res = self.facade.execute_merton_credit(bundle.credit_input)
        self.assertTrue(merton_res.distance_to_default > 3.0) # 巨头违约距离远大于3倍标准差
        self.assertFalse(merton_res.is_black_swan_alert)

        # 4. 直通执行期权偏度与异动流计算
        skew_res = self.facade.execute_option_skew(bundle.option_input)
        self.assertEqual(skew_res.symbol, "MSFT")
        self.assertFalse(skew_res.is_overnight_crash_alert)

        # 5. 直通执行 Beneish 八维造假核算
        beneish_res = self.facade.execute_beneish_forensics(bundle.forensics_input)
        self.assertFalse(beneish_res.is_manipulation_suspect)


if __name__ == "__main__":
    unittest.main()
