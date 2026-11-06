"""三层行业映射桥梁、产业链价格传导与 41 行业因果策略回归测试.

覆盖规范:
1. 41 细分行业与 OECD 12 宏观投入产出部门 100% 双向全覆盖与守恒;
2. 个股标的及多源板块标签向 41 行业的精准归一自适应解析;
3. 列昂惕夫双对偶价格冲击向微观企业转嫁与有效毛利率的传导闭环;
4. 41 行业专属因果策略路由在量化因果推导网络中的无缝织入与自然语言商业大白话质量断言.
"""

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from financial_core.engines.industry_taxonomy_bridge import (
    IndustryTaxonomyBridge,
    IndustryMappingRecord,
)
from financial_core.engines.industry_price_shock_bridge import (
    IndustryPriceShockBridge,
    IndustryPriceShockResult,
)
from financial_core.engines.industry_causal_registry import (
    IndustryCausalStrategyRegistry,
    IndustryCausalFacts,
)
from financial_core.engines.causal_inference_engine import (
    QuantitativeCausalInferenceEngine,
    CausalInferenceResult,
)


class TestIndustryTaxonomyAndCausalBridge(unittest.TestCase):
    """三层行业映射与因果策略测试用例集."""

    def setUp(self):
        self.taxonomy = IndustryTaxonomyBridge()
        self.price_bridge = IndustryPriceShockBridge()
        self.causal_registry = IndustryCausalStrategyRegistry()
        self.causal_engine = QuantitativeCausalInferenceEngine()

    def test_41_industries_complete_coverage_and_macro_sectors(self):
        """【FT-INDTAX-01: 41细分行业与OECD12大宏观投入产出部门100%全息双向映射与守恒闭环】

        1. 测试功能与测试点:
           - 验证全系统 41 个标准细分行业全量覆盖度。
           - 验证全部 41 行业与 OECD 12 大宏观部门严格闭环映射无孤儿节点。
           - 验证典型销货成本率 (typical_cogs_ratio) 严格在 (0.0, 1.0) 之间。
           - 验证典型霍尔加价率 (typical_markup_ratio) 大于 0.90 底线。
           - 验证 12 个宏观部门均有微观行业承接。

        2. 正常函数业务边界与参数契约:
           - get_all_records() 返回 41 个 IndustryMappingRecord 对象。
           - macro_sector_id 属于合法集合：AGR, ENERGY_MIN, TECH_SEMI, CAP_GOODS, CONS_GOODS, INFRA_UTIL, CONST_RE, TRADE_LOG, FIN_INS, INFO_SOFT, HEALTH_BIO, PROF_SERV。

        3. 测试数据与模拟场景说明:
           - 系统内置全息三层映射词典。

        4. 预期断言与结果验证:
           - len(records) == 41。
           - covered_macro_sectors == valid_macro_sectors。
        """
        records = self.taxonomy.get_all_records()
        self.assertEqual(len(records), 41, f"细分行业数量必须严格为 41，实际为 {len(records)}")

        valid_macro_sectors = {
            "AGR", "ENERGY_MIN", "TECH_SEMI", "CAP_GOODS", "CONS_GOODS",
            "INFRA_UTIL", "CONST_RE", "TRADE_LOG", "FIN_INS", "INFO_SOFT",
            "HEALTH_BIO", "PROF_SERV",
        }

        covered_macro_sectors = set()
        for r in records:
            self.assertIn(r.macro_sector_id, valid_macro_sectors, f"行业 {r.industry_id} 对应的宏观部门非法: {r.macro_sector_id}")
            self.assertGreater(r.typical_cogs_ratio, 0.0)
            self.assertLess(r.typical_cogs_ratio, 1.0)
            self.assertGreater(r.typical_markup_ratio, 0.90)
            covered_macro_sectors.add(r.macro_sector_id)

        # 断言 12 大宏观部门均有微观行业承接覆盖
        self.assertEqual(covered_macro_sectors, valid_macro_sectors)

    def test_ticker_and_sector_resolution(self):
        """【UT-INDTAX-02: 跨市场多代码(US/JP/A股)及多语言别名向41标准行业归一自适应解析与安全降级】

        1. 测试功能与测试点:
           - 验证典型标的代码自适应解析：NVDA -> semiconductors, RXRX -> biotech, 000858 -> food_beverage, MSFT -> software, JPM -> banks, TSLA -> autos。
           - 验证中英文多准则别名容错解析：'chips'/'半导体' -> semiconductors, 'saas' -> software, '白酒' -> food_beverage。
           - 验证未知极端输入安全降级机制：回退到 'PROF_SERV' 综合服务。

        2. 正常函数业务边界与参数契约:
           - resolve_industry_from_ticker_or_sector(ticker, sector) 返回有效映射对象。
           - 异常或未知行业代码不抛异常，返回通用降级行业。

        3. 测试数据与模拟场景说明:
           - 美股高科技、A股白酒代码、中英文混合别名、不存在的越界行业名称。

        4. 预期断言与结果验证:
           - 目标行业精确匹配。降级行业归属 PROF_SERV 且包含“通用综合”。
        """
        # 典型标的代码自适应解析
        self.assertEqual(self.taxonomy.resolve_industry_from_ticker_or_sector("NVDA", "").industry_id, "semiconductors")
        self.assertEqual(self.taxonomy.resolve_industry_from_ticker_or_sector("RXRX", "").industry_id, "biotech")
        self.assertEqual(self.taxonomy.resolve_industry_from_ticker_or_sector("000858", "").industry_id, "food_beverage")
        self.assertEqual(self.taxonomy.resolve_industry_from_ticker_or_sector("MSFT", "").industry_id, "software")
        self.assertEqual(self.taxonomy.resolve_industry_from_ticker_or_sector("JPM", "").industry_id, "banks")
        self.assertEqual(self.taxonomy.resolve_industry_from_ticker_or_sector("TSLA", "").industry_id, "autos")

        # 别名与多准则输入容错解析
        self.assertEqual(self.taxonomy.get_record("chips").industry_id, "semiconductors")
        self.assertEqual(self.taxonomy.get_record("半导体").industry_id, "semiconductors")
        self.assertEqual(self.taxonomy.get_record("saas").industry_id, "software")
        self.assertEqual(self.taxonomy.get_record("白酒").industry_id, "food_beverage")

        # 未知输入安全降级
        fallback = self.taxonomy.get_record("unknown_space_tech_sector")
        self.assertEqual(fallback.macro_sector_id, "PROF_SERV")
        self.assertIn("通用综合", fallback.industry_name_zh)

    def test_industry_price_shock_bridge_with_pass_through(self):
        """【IT-INDTAX-03: 列昂惕夫对偶成本冲击与微观霍尔加价率(Hall Markup)顺价转嫁能力闭环传导】

        1. 测试功能与测试点:
           - 验证上游宏观能源原材料 (ENERGY_MIN) 价格暴涨 20% 时微观企业财务影响。
           - 弱势制造企业（霍尔加价率 0.90，成本转嫁率 0%）：毛利率受挫，营业利润率缩水，生成弱势诊断。
           - 强势品牌龙头（霍尔加价率 1.35，成本转嫁率 100%）：完全转嫁成本，营业利润率维持，生成高护城河顺价诊断。

        2. 正常函数业务边界与参数契约:
           - evaluate_supply_chain_shock(industry_id, macro_cost_shocks, company_markup, cogs_ratio, baseline_operating_margin)。
           - 返回 IndustryPriceShockResult 对象。

        3. 测试数据与模拟场景说明:
           - 模拟能源采掘上涨 20%，分别对比包装制造与食品饮料品牌。

        4. 预期断言与结果验证:
           - 弱势企业：cost_pass_through == 0.0，gross_margin_impact < 0。
           - 强势企业：cost_pass_through == 100.0，gross_margin_impact == 0。
        """
        # 模拟场景: 宏观能源与采掘 (ENERGY_MIN) 暴涨 20%
        macro_shocks = {"ENERGY_MIN": 0.20}

        # Case A: 弱势制造企业 (霍尔加价率仅 0.90，缺乏议价权)
        weak_res = self.price_bridge.evaluate_supply_chain_shock(
            industry_id="packaging",
            macro_cost_shocks=macro_shocks,
            company_markup=0.90,
            cogs_ratio=0.75,
            baseline_operating_margin=0.10,
        )
        self.assertGreater(weak_res.supply_chain_cost_inflation_pct, 0.0)
        self.assertEqual(weak_res.cost_pass_through_ratio_pct, 0.0)
        self.assertLess(weak_res.gross_margin_impact_pct, 0.0)
        self.assertLess(weak_res.shocked_operating_margin_pct, 10.0)
        self.assertIn("处于弱势", weak_res.commercial_diagnosis)

        # Case B: 强势定价权龙头 (霍尔加价率达 1.35，高护城河)
        strong_res = self.price_bridge.evaluate_supply_chain_shock(
            industry_id="food_beverage",
            macro_cost_shocks=macro_shocks,
            company_markup=1.35,
            cogs_ratio=0.45,
            baseline_operating_margin=0.35,
        )
        self.assertEqual(strong_res.cost_pass_through_ratio_pct, 100.0)
        self.assertAlmostEqual(strong_res.gross_margin_impact_pct, 0.0)
        self.assertAlmostEqual(strong_res.shocked_operating_margin_pct, 35.0)
        self.assertIn("能够将 100% 的成本涨幅平稳顺价至下游终端", strong_res.commercial_diagnosis)

    def test_industry_causal_registry_routing(self):
        """【UT-INDTAX-04: 关键细分行业(半导体/生物医药/食品饮料)专属买方因果事实与异质性风险催化路由】

        1. 测试功能与测试点:
           - 前沿半导体：先进制程技术前沿距离、大客户集中度脆弱性。
           - 研发型生物医药：在研管线 rNPV 估值折现、硬现金跑道 (runway_months)。
           - 食品饮料白酒：出厂价与批发价批价倒挂、经销商合同负债蓄水池干涸。

        2. 正常函数业务边界与参数契约:
           - evaluate_industry_causal_facts(industry_id, company_metrics, forensic_findings, macro_shock_data)。
           - 返回 IndustryCausalFacts 对象。

        3. 测试数据与模拟场景说明:
           - 半导体 DIO=85、前沿距离=0.08；创新药跑道=8.5个月；白酒出厂=1000、批发=850（倒挂）。

        4. 预期断言与结果验证:
           - 对应催化剂与风险文本精确包含专属业务术语。
        """
        # 1. 前沿半导体
        semi_facts = self.causal_registry.evaluate_industry_causal_facts(
            industry_id="semiconductors",
            company_metrics={
                "current_dio_days": 85.0,
                "micro_markup_ratio": 1.30,
                "distance_to_technology_frontier": 0.08,
                "top_customer_share": 32.0,
                "top_customer_risk_flag": True,
            },
            forensic_findings={},
            macro_shock_data={},
        )
        semi_text = " ".join(semi_facts.industry_catalysts + semi_facts.industry_risks)
        self.assertIn("先进制程壁垒", semi_text)
        self.assertIn("供应链禁运脆弱性", semi_text)

        # 2. 研发型创新药
        biotech_facts = self.causal_registry.evaluate_industry_causal_facts(
            industry_id="biotech",
            company_metrics={
                "pipeline_rnpv_value": 450000000.0,
                "hard_runway_months": 8.5,
                "revenue_growth_pct": -0.10,
            },
            forensic_findings={},
            macro_shock_data={},
        )
        bio_text = " ".join(biotech_facts.industry_catalysts + biotech_facts.industry_risks)
        self.assertIn("在研管线临床价值", bio_text)
        self.assertIn("现金跑道逼仄与临床失败归零风险", bio_text)

        # 3. 食品饮料白酒
        liquor_facts = self.causal_registry.evaluate_industry_causal_facts(
            industry_id="food_beverage",
            company_metrics={
                "factory_quote": 1000.0,
                "real_wholesale_quote": 850.0,  # 倒挂
                "contract_liabilities_drain_pct": -22.0,
                "micro_markup_ratio": 1.28,
            },
            forensic_findings={},
            macro_shock_data={},
        )
        liq_text = " ".join(liquor_facts.industry_catalysts + liquor_facts.industry_risks)
        self.assertIn("渠道批价倒挂", liq_text)
        self.assertIn("合同负债蓄水池急剧干涸", liq_text)

    def test_causal_inference_engine_end_to_end_integration(self):
        """【FT-INDTAX-05: 量化因果推导网络端到端综合输出与行业策略无缝织入全息验证】

        1. 测试功能与测试点:
           - 验证 QuantitativeCausalInferenceEngine 综合企业财报、法证排雷、宏观冲击、微观结构及行业策略。
           - 端到端推导核心催化剂 (primary_catalysts) 与主要风险 (key_risks)。
           - 断言半导体行业专属事实成功注入顶层因果推导结果。

        2. 正常函数业务边界与参数契约:
           - infer_catalysts_and_risks 接收 6 个维度结构化输入。
           - 返回 CausalInferenceResult 强类型结果。

        3. 测试数据与模拟场景说明:
           - 输入英伟达 (NVDA) 标的真实参数全集。

        4. 预期断言与结果验证:
           - 返回对象为 CausalInferenceResult。
           - 催化剂与风险项数大于 0。
           - 文本包含“先进制程壁垒”。
        """
        res = self.causal_engine.infer_catalysts_and_risks(
            company_info={
                "ticker": "NVDA",
                "sector": "information_technology",
                "industry": "semiconductors",
                "current_price": 130.0,
                "current_dio_days": 80.0,
                "top_customer_share": 12.0,
            },
            forensic_result={"inventory_verdict": "良性周转", "red_flags": []},
            macro_shock_result={"shocked_wacc_pct": 8.2, "valuation_haircut_pct": 5.0},
            valuation_result={"hard_runway_months": 999.0, "hard_runway_desc": "持续净流入", "margin_of_safety_pct": 22.0},
            microstructure_result={"squeeze_score": 20.0, "short_percent_of_float": 1.5},
            micro_founded_macro_result={
                "pricing_power_tier": "强定价权",
                "micro_markup_ratio": 1.32,
                "distance_to_technology_frontier": 0.05,
            },
        )
        self.assertIsInstance(res, CausalInferenceResult)
        self.assertGreater(len(res.primary_catalysts), 0)
        self.assertGreater(len(res.key_risks), 0)

        # 确认半导体行业特异性事实成功注入
        all_facts = " ".join(res.primary_catalysts)
        self.assertIn("先进制程壁垒", all_facts)


if __name__ == "__main__":
    unittest.main()
