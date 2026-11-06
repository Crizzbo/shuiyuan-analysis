"""测试批次全息档案数据向 SystemicCompanyInput 的结构化转换与端到端计算 (Test Batch Dossier Ingestion).

验证 78 个 Batch 档案能够无缝转换、平账并喂入 FinancialAnalysisSystem 计算。
"""

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.filing_mapper import OfficialFilingMapper
from financial_core.api import FinancialAnalysisSystem
from data_sources.batch78_verified_dossiers_data import BATCH78_DOSSIERS


class TestBatchDossierIngestion(unittest.TestCase):
    """测试批次全息档案数据转换与端到端计算."""

    def setUp(self):
        self.fin_system = FinancialAnalysisSystem()

    def test_parse_financial_number_edge_cases(self):
        """测试复杂财务字符串解析 (符号、逗号、各种乘数)."""
        mapper = OfficialFilingMapper
        self.assertEqual(mapper.parse_financial_number("$750.0M (现金及国债)"), 750_000_000.0)
        self.assertEqual(mapper.parse_financial_number("-$380.0M"), -380_000_000.0)
        self.assertEqual(mapper.parse_financial_number("($345.0M)"), -345_000_000.0)
        self.assertEqual(mapper.parse_financial_number("$1.2B"), 1_200_000_000.0)
        self.assertEqual(mapper.parse_financial_number("380.0M 股"), 380_000_000.0)
        self.assertEqual(mapper.parse_financial_number("5,600億円"), 560_000_000_000.0)
        self.assertEqual(mapper.parse_financial_number("890円"), 890.0)
        # 日股 TDnet / EDINET 决算短信常见负数符号 (△, ▲, 全角括号)
        self.assertEqual(mapper.parse_financial_number("△5,200百万円"), -5_200_000_000.0)
        self.assertEqual(mapper.parse_financial_number("▲12.5%"), -12.5)
        self.assertEqual(mapper.parse_financial_number("（△340億円）"), -34_000_000_000.0)
        self.assertEqual(mapper.parse_financial_number("▲¥1,250.5M"), -1_250_500_000.0)
        self.assertEqual(mapper.parse_financial_number(None), 0.0)
        self.assertEqual(mapper.parse_financial_number("N/A"), 0.0)

    def test_map_and_execute_us_batch_company(self):
        """测试美股 ACHR 档案映射并运行系统性估值."""
        achr = BATCH78_DOSSIERS[0]
        inp = OfficialFilingMapper.map_dossier_to_company_input(achr)
        self.assertEqual(inp.ticker, "ACHR")
        self.assertEqual(inp.total_assets, 750_000_000.0)
        self.assertEqual(inp.stockholders_equity, 590_000_000.0)
        self.assertEqual(inp.total_liabilities, 160_000_000.0)
        self.assertAlmostEqual(inp.total_assets, inp.total_liabilities + inp.stockholders_equity, delta=1.0)

        res = self.fin_system.analyze_equity(inp.ticker, company_input=inp)
        self.assertTrue(res.execution_success)
        self.assertEqual(res.ticker, "ACHR")
        self.assertGreater(res.decision_card.neutral_fair_value, 0.0)

    def test_map_and_execute_jp_batch_company(self):
        """测试日股 1332 (Nissui) 档案映射并运行系统性估值."""
        nissui = BATCH78_DOSSIERS[5]
        inp = OfficialFilingMapper.map_dossier_to_company_input(nissui)
        self.assertEqual(inp.ticker, "1332")
        self.assertEqual(inp.total_assets, 560_000_000_000.0)
        self.assertEqual(inp.stockholders_equity, 245_000_000_000.0)
        self.assertEqual(inp.total_liabilities, 315_000_000_000.0)
        self.assertAlmostEqual(inp.total_assets, inp.total_liabilities + inp.stockholders_equity, delta=1.0)

        res = self.fin_system.analyze_equity(inp.ticker, company_input=inp)
        self.assertTrue(res.execution_success)
        self.assertEqual(res.ticker, "1332")
        self.assertEqual(res.currency, "JPY")
        self.assertGreater(res.decision_card.neutral_fair_value, 0.0)


if __name__ == "__main__":
    unittest.main()
