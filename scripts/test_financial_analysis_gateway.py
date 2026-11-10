# -*- coding: utf-8 -*-
"""金融计算与行业因果分析统一网关测试套件 (test_financial_analysis_gateway.py).

严格遵循《AGENTS.md》与《CLAUDE.md》：
1. 验证 8 种模式 (industry, physics, forensics, credit, liquidity, options, regime, all) 纯净执行；
2. 验证行业解析与因果敏感性输出；
3. 验证无网络状态下全流程闭环及边界保护。
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finance_tools.governance_and_pipeline.financial_analysis_gateway import (
    FinancialAnalysisGateway,
    IndustryAnalysisReport,
    ComprehensiveAnalysisReport,
)


class FinancialAnalysisGatewayTests(unittest.TestCase):
    """金融计算与行业分析网关全维度单元测试."""

    def setUp(self) -> None:
        self.gateway = FinancialAnalysisGateway.get_instance()
        self.sample_bars = [
            {
                "date": f"2024-01-{i:02d}",
                "open": 100.0 + i * 0.5,
                "high": 102.0 + i * 0.5,
                "low": 99.0 + i * 0.5,
                "close": 101.0 + i * 0.5,
                "volume": 50000.0,
                "turnover": 5000000.0,
            }
            for i in range(1, 31)
        ]

    def test_industry_analysis(self) -> None:
        """测试行业知识画像与敏感性分析."""
        # 1. 股票代码映射行业 (NVDA -> semiconductors)
        rep = self.gateway.analyze_industry("NVDA")
        self.assertIsInstance(rep, IndustryAnalysisReport)
        self.assertEqual(rep.industry_id, "semiconductors")
        self.assertTrue(len(rep.key_drivers) > 0)
        self.assertTrue(len(rep.accounting_focus) > 0)

        # 2. 行业ID直接查询
        rep_soft = self.gateway.analyze_industry("software")
        self.assertEqual(rep_soft.industry_id, "software")
        self.assertIn("软件", rep_soft.industry_name_zh)

    def test_physics_dynamics_analysis(self) -> None:
        """测试通用商业物理动力学分析."""
        res = self.gateway.analyze_physics("NVDA", self.sample_bars)
        self.assertEqual(res["symbol"], "NVDA")
        self.assertEqual(res["status"], "COMPLETED")
        self.assertTrue("trend_velocity_annual_pct" in res)
        self.assertTrue("zero_growth_floor_price" in res)
        self.assertTrue("kinetic_to_potential_ratio" in res)
        self.assertIn("breakout_power_verdict", res)

    def test_forensics_analysis(self) -> None:
        """测试法务会计 Beneish M-Score 防舞弊核算."""
        raw_fin = {
            "TotalRevenue": 1000.0,
            "CostOfRevenue": 500.0,
            "AccountsReceivableNetCurrent": 150.0,
            "TotalAssets": 2000.0,
            "NetIncomeCommonStockholders": 200.0,
            "OperatingCashFlow": 220.0,
        }
        res = self.gateway.analyze_forensics("NVDA", raw_fin)
        self.assertEqual(res["symbol"], "NVDA")
        self.assertFalse(res["is_manipulation_suspect"])
        self.assertEqual(res["risk_rating"], "CLEAN")

    def test_credit_risk_analysis(self) -> None:
        """测试 KMV-Merton 结构化信用违约测算."""
        raw_fin = {"ShortTermDebt": 100.0, "LongTermDebtNoncurrent": 400.0}
        res = self.gateway.analyze_credit(
            symbol="NVDA",
            raw_financials=raw_fin,
            equity_market_cap=2_000_000_000_000.0,
            equity_volatility=0.45,
        )
        self.assertEqual(res["symbol"], "NVDA")
        self.assertTrue(res["distance_to_default_DD"] > 3.0)
        self.assertFalse(res["is_black_swan_alert"])

    def test_liquidity_analysis(self) -> None:
        """测试 Amihud 微观流动性冲击与非线性滑点测算."""
        res = self.gateway.analyze_liquidity(
            symbol="NVDA",
            raw_bars=self.sample_bars,
            intended_order_value=50000.0,
            market="US",
        )
        self.assertEqual(res["symbol"], "NVDA")
        self.assertFalse(res["is_illiquid_trap"])
        self.assertTrue(res["total_effective_slippage_bps"] >= 10.0)

    def test_options_skew_analysis(self) -> None:
        """测试期权偏度与异动分析."""
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
        res = self.gateway.analyze_options("NVDA", 120.0, raw_deriv)
        self.assertEqual(res["symbol"], "NVDA")
        self.assertFalse(res["is_overnight_crash_alert"])

    def test_macro_regime_analysis(self) -> None:
        """测试宏观 3 状态 HMM 识别."""
        res = self.gateway.analyze_macro_regime("SPY")
        self.assertIn("regime_state", res)
        self.assertIn(res["regime_state"], ["BULL_MOMENTUM", "RANGE_BOUND_VALUE", "CRISIS_DEFENSE"])
        self.assertTrue(0.0 <= res["recommended_gross_exposure"] <= 1.0)

    def test_comprehensive_analysis(self) -> None:
        """测试一键全景融合买方综合诊断."""
        comp = self.gateway.analyze_comprehensive("NVDA", self.sample_bars)
        self.assertIsInstance(comp, ComprehensiveAnalysisReport)
        self.assertEqual(comp.symbol, "NVDA")
        self.assertIn(comp.actionable_verdict, [
            "HARD_REJECT_DISQUALIFIED", "DEFENSIVE_HOLD", "STRONG_ACCUMULATE_ROCKET", "SELECTIVE_ACCUMULATE", "NEUTRAL"
        ])
        self.assertTrue(len(comp.executive_summary_zh) > 50)
        self.assertIsNotNone(comp.industry_report)
        self.assertIsNotNone(comp.physics_report)
        self.assertIsNotNone(comp.forensics_report)


if __name__ == "__main__":
    unittest.main()
