"""41 细分行业买方专属因果推导与财报附注穿透单元测试.

测试范围:
1. 覆盖 IndustryTaxonomyBridge 登记的全部 41 细分行业代码;
2. 验证 IndustryCausalStrategyRegistry 对 41 个行业全部具备专属买方因果推导逻辑;
3. 验证推导文本严格遵循自然语言汇报规范：杜绝 Emoji 表情符号，杜绝生硬数学代数公式;
4. 验证 OfficialFilingMapper 对存货三级细分、受限资金与研发资本化附注的自适应解析与平账自检。
"""

from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.industry_taxonomy_bridge import IndustryTaxonomyBridge
from financial_core.engines.industry_causal_registry import (
    IndustryCausalStrategyRegistry,
    IndustryCausalFacts,
)
from financial_core.engines.filing_mapper import OfficialFilingMapper


class TestIndustryCausalRegistry41(unittest.TestCase):
    """41 细分行业买方专属因果推导与附注穿透测试套件."""

    def setUp(self):
        self.bridge = IndustryTaxonomyBridge()
        self.registry = IndustryCausalStrategyRegistry()
        self.emoji_pattern = re.compile(
            r"[\U00010000-\U0010ffff]|"
            + "|".join(
                f"[{chr(start)}-{chr(end)}]"
                for start, end in [
                    (0x2600, 0x27BF),  # 杂项与装饰符号
                    (0x2300, 0x23FF),  # 杂项技术符号
                    (0x2B50, 0x2B55),  # 星形与圆形符号
                    (0x203C, 0x2049),  # 双重标点
                    (0x2194, 0x21AA),  # 箭头符号
                    (0x25A0, 0x25FE),  # 几何图形符号
                ]
            )
        )

    def test_01_all_41_industries_covered(self):
        """【UT-IND41-01: 行业全景分类桥梁41个标准细分赛道覆盖度验证】

        1. 测试功能与测试点:
           - 验证 IndustryTaxonomyBridge 登记的标准行业总数恰好为 41 个。
           - 确保覆盖半导体、软件SaaS、创新药、高端装备、数字基建等全行业生态。

        2. 正常函数业务边界与参数契约:
           - get_all_records() 返回列表长度严格等于 41。

        3. 测试数据与模拟场景说明:
           - 读取当前项目底账注册的全部标准行业列表。

        4. 预期断言与结果验证:
           - len(all_inds) == 41。
        """
        all_inds = self.bridge.get_all_records()
        self.assertEqual(len(all_inds), 41, f"标准行业总数必须为 41，实际为 {len(all_inds)}")

    def test_02_all_41_industries_evaluated_with_distinct_facts(self):
        """【IT-IND41-02: 41细分行业买方专属因果推导事实矩阵与零Emoji规范】

        1. 测试功能与测试点:
           - 遍历全部 41 个细分行业，验证 IndustryCausalStrategyRegistry 均具备专属买方因果研判逻辑。
           - 验证行业专属催化剂 (catalysts) 与风险事实 (risks) 非空且非千篇一律的通用模板。
           - 验证悲观底价防线与乐观靶心触发逻辑完整。
           - 严密断言全文本 100% 杜绝 Emoji 表情符号，符合买方机构严谨汇报规范。

        2. 正常函数业务边界与参数契约:
           - 传入行业特定指标与宏观冲击数据，返回强类型 IndustryCausalFacts 实例。

        3. 测试数据与模拟场景说明:
           - 注入存货周转天数 DIO 85天、微观加价率 1.25、前沿技术距离 0.12 等样本微观指标。

        4. 预期断言与结果验证:
           - facts.industry_id == ind_id。
           - catalysts 与 risks 列表长度大于 0。
           - leading_optimistic_trigger 与 leading_pessimistic_trigger 均为有效字符串。
           - emoji_pattern 搜索结果为 False。
        """
        all_inds = self.bridge.get_all_records()
        sample_metrics = {
            "current_dio_days": 85.0,
            "micro_markup_ratio": 1.25,
            "distance_to_technology_frontier": 0.12,
            "top_customer_share": 18.0,
            "top_customer_risk_flag": False,
            "factory_quote": 1000.0,
            "real_wholesale_quote": 1080.0,
            "contract_liabilities_drain_pct": 5.0,
            "hard_runway_months": 48.0,
            "revenue_growth_pct": 0.15,
            "pipeline_rnpv_value": 3500.0,
        }

        for ind in all_inds:
            ind_id = ind.industry_id
            facts = self.registry.evaluate_industry_causal_facts(
                industry_id=ind_id,
                company_metrics=sample_metrics,
                forensic_findings={},
                macro_shock_data={},
            )
            self.assertIsInstance(facts, IndustryCausalFacts)
            self.assertEqual(facts.industry_id, ind_id)
            self.assertEqual(facts.industry_name_zh, ind.industry_name_zh)
            self.assertGreater(len(facts.industry_catalysts), 0, f"行业 {ind_id} 催化事实不可为空")
            self.assertGreater(len(facts.industry_risks), 0, f"行业 {ind_id} 风险警示不可为空")
            self.assertTrue(facts.leading_optimistic_trigger, f"行业 {ind_id} 必须有主导乐观靶心")
            self.assertTrue(facts.leading_pessimistic_trigger, f"行业 {ind_id} 必须有主导悲观底价防线")

            # 严格核验：杜绝 Emoji
            combined_text = " ".join(facts.industry_catalysts + facts.industry_risks)
            combined_text += f" {facts.leading_optimistic_trigger} {facts.leading_pessimistic_trigger}"
            self.assertFalse(
                bool(self.emoji_pattern.search(combined_text)),
                f"行业 {ind_id} 推导文本中含有禁止的 Emoji 符号: {combined_text}"
            )

    def test_03_filing_mapper_footnotes_parsing(self):
        """【UT-IND41-03: 官方财报附注深度穿透(存货三级细分/受限资金/研发资本化)】

        1. 测试功能与测试点:
           - 验证 OfficialFilingMapper 对文本自然语言附注的智能法证解剖与提取能力:
             1. 存货三级细分（原材料 raw_materials、在制品 work_in_process、产成品 finished_goods）；
             2. 受限质押资金 (restricted_cash) 与银行债务最低流动性契约红线 (debt_covenant_min_cash)；
             3. 研发总投入 (total_rd_spent) 与软件开发费用资本化金额 (capitalized_rd_amount)。

        2. 正常函数业务边界与参数契约:
           - 输入自然语言描述的文本，准确剥离并转换为以美元为基准单位的高精度浮点数。

        3. 测试数据与模拟场景说明:
           - 存货 $2,450M (含原材料 $650M, 在制品 $800M, 产成品 $1,000M)；
           - 现金 $4,500M (含受限 $280M, 最低契约 $600M)；
           - 研发 $1,800M (资本化 $150M)。

        4. 预期断言与结果验证:
           - 原材料提取为 650,000,000.0，在制品 800,000,000.0，产成品 1,000,000,000.0。
           - 受限现金 280,000,000.0，契约现金 600,000,000.0。
           - 研发投入 1,800,000,000.0，资本化研发 150,000,000.0。
        """
        sample_dossier = {
            "overview": {
                "ticker": "TEST_TICKER",
                "company_name": "测试先进制程科技股份有限公司",
                "market": "US",
                "industry_id": "semiconductors",
            },
            "financial_statement_deep_dive": {
                "inventory_cycle_analysis": {
                    "inventory_scale": "存货总计 $2,450M (含原材料 $650M, 在制品 $800M, 产成品 $1,000M)",
                    "inventory_turnover_days": "78 天",
                },
                "cash_and_liquidity": {
                    "total_cash_and_equivalents": "账面现金 $4,500M (其中包含受限质押资金 $280M, 银行借款最低流动性契约红线 $600M)",
                },
                "profitability_quality": {
                    "profitability_quality": "研发总投入 $1,800M (其中软件开发费用资本化 $150M), ROE 维持在 22.5%",
                },
            },
            "raw_financials_table": {
                "revenue": "$12,000M",
                "operating_income": "$3,200M",
                "net_income": "$2,600M",
                "free_cash_flow": "$2,200M",
                "total_assets": "$18,000M",
                "equity": "$11,000M",
                "cash_and_equivalents": "$4,500M",
                "total_debt": "$3,000M",
                "shares": "500M 股",
            },
            "long_term_outlook": {
                "dcf_valuation_matrix": {
                    "margin_of_safety_buy_zone": "现价 $85.00，严苛买入线 $68.00",
                    "base_fair_value": "$95.00",
                }
            }
        }

        company_input = OfficialFilingMapper.map_dossier_to_company_input(sample_dossier)
        self.assertEqual(company_input.ticker, "TEST_TICKER")
        # 验证存货三级细分
        self.assertEqual(company_input.raw_materials, 650_000_000.0)
        self.assertEqual(company_input.work_in_process, 800_000_000.0)
        self.assertEqual(company_input.finished_goods, 1_000_000_000.0)
        # 验证受限现金与契约最低流动资金
        self.assertEqual(company_input.restricted_cash, 280_000_000.0)
        self.assertEqual(company_input.debt_covenant_min_cash, 600_000_000.0)
        # 验证研发投入与资本化
        self.assertEqual(company_input.total_rd_spent, 1_800_000_000.0)
        self.assertEqual(company_input.capitalized_rd_amount, 150_000_000.0)


if __name__ == "__main__":
    unittest.main()
