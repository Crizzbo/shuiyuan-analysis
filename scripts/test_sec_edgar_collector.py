"""单元测试：官方 SEC EDGAR 财报收集与三表对齐提取引擎 (test_sec_edgar_collector.py).

验证：
1. 离线 CompanyFacts 结构化提取与三表对齐;
2. 资产负债表平衡律自检 ($Assets = Liabilities + Equity$);
3. 不平衡财报的阻断与异常捕获;
4. 深度档案补丁字典转换格式与量纲合规性。
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
from financial_core.engines.filing_mapper import (
    OfficialFilingMapper,
    BalanceSheetIdentityError,
    IncompleteFilingFactError,
)


class TestSecEdgarCollector(unittest.TestCase):
    """测试 SEC EDGAR 官方财报提取器."""

    def setUp(self):
        # 构造模拟的真实官方 SEC CompanyFacts JSON 结构
        self.mock_facts = {
            "cik": 1674101,
            "entityName": "Vertiv Holdings Co",
            "facts": {
                "dei": {
                    "EntityCommonStockSharesOutstanding": {
                        "units": {
                            "shares": [
                                {"end": "2025-12-31", "val": 385000000, "form": "10-K", "fp": "FY"}
                            ]
                        }
                    }
                },
                "us-gaap": {
                    "Assets": {
                        "units": {
                            "USD": [
                                {"end": "2025-12-31", "val": 12212400000.0, "form": "10-K", "fy": 2025, "fp": "FY", "accn": "0001674101-26-000008"}
                            ]
                        }
                    },
                    "Liabilities": {
                        "units": {
                            "USD": [
                                {"end": "2025-12-31", "val": 8271100000.0, "form": "10-K", "fy": 2025, "fp": "FY", "accn": "0001674101-26-000008"}
                            ]
                        }
                    },
                    "StockholdersEquity": {
                        "units": {
                            "USD": [
                                {"end": "2025-12-31", "val": 3941300000.0, "form": "10-K", "fy": 2025, "fp": "FY", "accn": "0001674101-26-000008"}
                            ]
                        }
                    },
                    "Revenues": {
                        "units": {
                            "USD": [
                                {"end": "2025-12-31", "val": 10229900000.0, "form": "10-K", "fy": 2025, "fp": "FY"}
                            ]
                        }
                    },
                    "OperatingIncomeLoss": {
                        "units": {
                            "USD": [
                                {"end": "2025-12-31", "val": 1829700000.0, "form": "10-K", "fy": 2025, "fp": "FY"}
                            ]
                        }
                    },
                    "NetIncomeLoss": {
                        "units": {
                            "USD": [
                                {"end": "2025-12-31", "val": 1332800000.0, "form": "10-K", "fy": 2025, "fp": "FY"}
                            ]
                        }
                    },
                    "NetCashProvidedByUsedInOperatingActivities": {
                        "units": {
                            "USD": [
                                {"end": "2025-12-31", "val": 2113800000.0, "form": "10-K", "fy": 2025, "fp": "FY"}
                            ]
                        }
                    },
                    "PaymentsToAcquirePropertyPlantAndEquipment": {
                        "units": {
                            "USD": [
                                {"end": "2025-12-31", "val": 220000000.0, "form": "10-K", "fy": 2025, "fp": "FY"}
                            ]
                        }
                    },
                    "CashAndCashEquivalentsAtCarryingValue": {
                        "units": {
                            "USD": [
                                {"end": "2025-12-31", "val": 850000000.0, "form": "10-K", "fy": 2025, "fp": "FY"}
                            ]
                        }
                    },
                    "InventoryNet": {
                        "units": {
                            "USD": [
                                {"end": "2025-12-31", "val": 980000000.0, "form": "10-K", "fy": 2025, "fp": "FY"}
                            ]
                        }
                    }
                }
            }
        }

    def test_01_extract_balanced_three_statements(self):
        """【UT-SEC-01: US-GAAP官方CompanyFacts财报三表对齐与资产负债刚性平账自检】

        1. 测试功能与测试点:
           - 验证 OfficialSecEdgarCollector.extract_aligned_financial_facts 解析 SEC 官方 US-GAAP taxonomy。
           - 自动化三表对齐: 资产负债表、利润表、现金流量表核心指标对齐同财年 (FY)。
           - 会计刚性平账自检: Assets == Liabilities + Equity，计算 balance_sheet_diff。

        2. 正常函数业务边界与参数契约:
           - companyfacts 包含 dei 与 us-gaap 数据字典。
           - 返回 SecExtractedFinancialFacts 强类型结构体。

        3. 测试数据与模拟场景说明:
           - 模拟 Vertiv Holdings (VRT，AI 数据中心液冷龙头)。
           - 资产 122.124 亿，负债 82.711 亿，权益 39.413 亿 (12.2124B == 8.2711B + 3.9413B)。
           - 营收 102.299 亿，自由现金流 = 经营现金流 21.138 亿 - 资本开支 2.20 亿 = 18.938 亿。

        4. 预期断言与结果验证:
           - 断言 facts.is_balanced 为 True，balance_sheet_diff 精确等于 0.0。
           - 断言 total_assets, total_liabilities, stockholders_equity, revenue 等各科目数值完全吻合。
        """
        facts = OfficialSecEdgarCollector.extract_aligned_financial_facts(
            companyfacts=self.mock_facts,
            ticker="VRT",
        )
        self.assertEqual(facts.ticker, "VRT")
        self.assertEqual(facts.fiscal_year_end, "2025-12-31")
        self.assertEqual(facts.total_assets, 12212400000.0)
        self.assertEqual(facts.total_liabilities, 8271100000.0)
        self.assertEqual(facts.stockholders_equity, 3941300000.0)
        self.assertTrue(facts.is_balanced)
        self.assertEqual(facts.balance_sheet_diff, 0.0)
        self.assertEqual(facts.revenue, 10229900000.0)
        self.assertEqual(facts.operating_income, 1829700000.0)
        self.assertEqual(facts.net_income, 1332800000.0)
        self.assertEqual(facts.operating_cash_flow, 2113800000.0)
        self.assertEqual(facts.capex, 220000000.0)
        self.assertEqual(facts.free_cash_flow, 2113800000.0 - 220000000.0)

    def test_02_convert_to_dossier_patch_and_map_fact(self):
        """【IT-SEC-02: 深度档案补丁转换与OfficialFilingMapper实体映射集成验证】

        1. 测试功能与测试点:
           - 验证 OfficialSecEdgarCollector.convert_to_dossier_patch 生成档案增量补丁。
           - 验证 OfficialFilingMapper.map_to_firm_financial_fact 承接补丁并完成百万美元 (Million) 单位换算。

        2. 正常函数业务边界与参数契约:
           - 档案补丁符合 schemas/deep_dossier.schema.json。

        3. 测试数据与模拟场景说明:
           - VRT 提取事实合并至 overview 形成微观档案输入。

        4. 预期断言与结果验证:
           - 断言 firm_fact.ticker == "VRT"。
           - 断言 revenue_million == 10229.9。
           - 断言 annual_fcf_million 约为 1893.8 (2113.8 - 220.0)。
           - 断言 raw_financials_table['total_assets'] == 12212400000.0。
        """
        facts = OfficialSecEdgarCollector.extract_aligned_financial_facts(
            companyfacts=self.mock_facts,
            ticker="VRT",
        )
        patch = OfficialSecEdgarCollector.convert_to_dossier_patch(facts)
        self.assertIn("facts", patch)
        self.assertIn("raw_financials_table", patch)

        # 结合基础 overview 形成微观档案
        dossier = {
            "overview": {
                "ticker": "VRT",
                "company_name": "Vertiv Holdings Co",
                "market": "US",
                "industry_id": "ai_data_center_liquid_cooling",
            },
            "financial_unit": "usd",
            **patch,
        }

        firm_fact = OfficialFilingMapper.map_to_firm_financial_fact(dossier)
        self.assertEqual(firm_fact.ticker, "VRT")
        self.assertEqual(firm_fact.revenue_million, 10229.9)
        self.assertAlmostEqual(firm_fact.annual_fcf_million, (2113.8 - 220.0), places=3)
        self.assertEqual(dossier["raw_financials_table"]["total_assets"], 12212400000.0)

    def test_03_missing_assets_raises_error(self):
        """【UT-SEC-03: 缺失核心资产科目残缺财报刚性阻断(IncompleteFilingFactError)】

        1. 测试功能与测试点:
           - 验证缺失总资产 (Assets) 等基础科目时，引擎拒绝容忍假定，刚性抛出 IncompleteFilingFactError。

        2. 正常函数业务边界与参数契约:
           - 缺失关键 GAAP 科目抛出 IncompleteFilingFactError。

        3. 测试数据与模拟场景说明:
           - us-gaap 数据为空字典。

        4. 预期断言与结果验证:
           - 断言抛出 IncompleteFilingFactError。
        """
        bad_facts = {
            "cik": 12345,
            "entityName": "Bad Company",
            "facts": {"us-gaap": {}}
        }
        with self.assertRaises(IncompleteFilingFactError):
            OfficialSecEdgarCollector.extract_aligned_financial_facts(bad_facts, ticker="BAD")

    def test_04_unbalanced_balance_sheet_raises_error(self):
        """【UT-SEC-04: 会计恒等式失衡财报刚性阻断(BalanceSheetIdentityError)】

        1. 测试功能与测试点:
           - 验证当负债与权益合计与总资产严重不平 (|Assets - (Liab + Equity)| / Assets > 0.1%) 时，引擎拒绝将坏数据注入主管道。

        2. 正常函数业务边界与参数契约:
           - 会计方程失衡抛出 BalanceSheetIdentityError。

        3. 测试数据与模拟场景说明:
           - 总资产 122.124 亿，负债 10 亿，权益 10 亿 (差 102 亿)。

        4. 预期断言与结果验证:
           - 断言抛出 BalanceSheetIdentityError。
        """
        unbalanced = dict(self.mock_facts)
        unbalanced["facts"] = dict(self.mock_facts["facts"])
        unbalanced["facts"]["us-gaap"] = dict(self.mock_facts["facts"]["us-gaap"])
        unbalanced["facts"]["us-gaap"]["Liabilities"] = {
            "units": {
                "USD": [{"end": "2025-12-31", "val": 1000000000.0, "form": "10-K"}] # 故意破损
            }
        }
        unbalanced["facts"]["us-gaap"]["StockholdersEquity"] = {
            "units": {
                "USD": [{"end": "2025-12-31", "val": 1000000000.0, "form": "10-K"}] # 故意破损
            }
        }
        with self.assertRaises(BalanceSheetIdentityError):
            OfficialSecEdgarCollector.extract_aligned_financial_facts(unbalanced, ticker="UNBAL")

    def test_05_ifrs_full_taxonomy_extraction(self):
        """【UT-SEC-05: IFRS-Full国际会计准则(Form 20-F)多币种三表事实对齐与平账验证】

        1. 测试功能与测试点:
           - 验证 OfficialSecEdgarCollector 对 ifrs-full (国际财务报告准则，外国发行人 Form 20-F) 标签体系的提取支持。
           - 支持非美元本位币 (如新台币 TWD) 事实抽取与平账校验。

        2. 正常函数业务边界与参数契约:
           - 支持 ifrs-full: Assets, Liabilities, Equity, Revenue, ProfitLossFromOperatingActivities。

        3. 测试数据与模拟场景说明:
           - 标的: 台积电 (TSMC, TSM)。
           - 总资产 6.69176 万亿新台币，负债 2.41249 万亿，股东权益 4.27927 万亿 (6.69176 == 2.41249 + 4.27927)。
           - 营收 2.8943 万亿，自由现金流 = 经营现金流 1.69017 万亿 - 资本开支 8200 亿 = 8701.7 亿。

        4. 预期断言与结果验证:
           - 断言 ticker == 'TSM'，currency == 'TWD'，fiscal_year == 2024。
           - 断言 is_balanced 为 True，balance_sheet_diff == 0.0。
           - 断言各财务数字精确吻合。
        """
        ifrs_mock = {
            "cik": 1046179,
            "entityName": "TAIWAN SEMICONDUCTOR MANUFACTURING CO LTD",
            "facts": {
                "ifrs-full": {
                    "Assets": {
                        "units": {
                            "TWD": [
                                {"end": "2024-12-31", "val": 6691764700000.0, "form": "20-F", "fy": 2024, "fp": "FY", "accn": "0001046179-25-000005"}
                            ]
                        }
                    },
                    "Liabilities": {
                        "units": {
                            "TWD": [
                                {"end": "2024-12-31", "val": 2412493100000.0, "form": "20-F", "fy": 2024, "fp": "FY", "accn": "0001046179-25-000005"}
                            ]
                        }
                    },
                    "Equity": {
                        "units": {
                            "TWD": [
                                {"end": "2024-12-31", "val": 4279271600000.0, "form": "20-F", "fy": 2024, "fp": "FY", "accn": "0001046179-25-000005"}
                            ]
                        }
                    },
                    "Revenue": {
                        "units": {
                            "TWD": [
                                {"end": "2024-12-31", "val": 2894307700000.0, "form": "20-F", "fy": 2024, "fp": "FY"}
                            ]
                        }
                    },
                    "ProfitLossFromOperatingActivities": {
                        "units": {
                            "TWD": [
                                {"end": "2024-12-31", "val": 1251322000000.0, "form": "20-F", "fy": 2024, "fp": "FY"}
                            ]
                        }
                    },
                    "ProfitLoss": {
                        "units": {
                            "TWD": [
                                {"end": "2024-12-31", "val": 1169871000000.0, "form": "20-F", "fy": 2024, "fp": "FY"}
                            ]
                        }
                    },
                    "CashFlowsFromUsedInOperatingActivities": {
                        "units": {
                            "TWD": [
                                {"end": "2024-12-31", "val": 1690170000000.0, "form": "20-F", "fy": 2024, "fp": "FY"}
                            ]
                        }
                    },
                    "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities": {
                        "units": {
                            "TWD": [
                                {"end": "2024-12-31", "val": 820000000000.0, "form": "20-F", "fy": 2024, "fp": "FY"}
                            ]
                        }
                    }
                }
            }
        }

        facts = OfficialSecEdgarCollector.extract_aligned_financial_facts(ifrs_mock, ticker="TSM")
        self.assertEqual(facts.ticker, "TSM")
        self.assertEqual(facts.currency, "TWD")
        self.assertEqual(facts.fiscal_year, 2024)
        self.assertTrue(facts.is_balanced)
        self.assertEqual(facts.balance_sheet_diff, 0.0)
        self.assertEqual(facts.total_assets, 6691764700000.0)
        self.assertEqual(facts.total_liabilities, 2412493100000.0)
        self.assertEqual(facts.stockholders_equity, 4279271600000.0)
        self.assertEqual(facts.revenue, 2894307700000.0)
        self.assertEqual(facts.free_cash_flow, 1690170000000.0 - 820000000000.0)


if __name__ == "__main__":
    unittest.main()
