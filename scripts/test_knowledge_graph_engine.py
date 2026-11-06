#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/test_knowledge_graph_engine.py

全盘买方投研知识图谱遍历与知识边界核验引擎 (KnowledgeGraphEngine) 契约与功能测试用例集
- 验证知识图谱底账 (knowledge_graph.json) 拓扑节点与关系边的完整性
- 验证行业知识边界一键 O(1) 检索
- 验证非法与违规估值操作的硬拦截防御
- 验证产业链有向图拓扑追踪
"""

import unittest
from pathlib import Path
from financial_core.engines.knowledge_graph_engine import KnowledgeGraphEngine

ROOT_DIR = Path(__file__).resolve().parent.parent

class KnowledgeGraphEngineTests(unittest.TestCase):
    """知识图谱引擎与边界核验契约测试"""

    @classmethod
    def setUpClass(cls):
        cls.engine = KnowledgeGraphEngine()

    def test_graph_data_integrity(self):
        """【KG-01: 图谱底账数据完整性断言】全量板块、行业、模式与指标覆盖"""
        stats = self.engine.get_graph_stats()
        self.assertGreaterEqual(stats["total_nodes"], 320, "节点总数应覆盖 11 板块+41 行业+16 模式+指标与衍生节点")
        self.assertGreaterEqual(stats["total_edges"], 350, "关系边总数应覆盖拓扑关联与产业链供求")

        type_dist = stats["node_type_distribution"]
        self.assertEqual(type_dist.get("Sector"), 11, "必须包含 11 个标准经济板块")
        self.assertEqual(type_dist.get("Industry"), 41, "必须全息覆盖全量 41 个行业正式档案")
        self.assertEqual(type_dist.get("BusinessModel"), 16, "必须覆盖 16 个标准商业模式")
        self.assertEqual(type_dist.get("ValuationRoute"), 41, "每个行业必须拥有法定估值路由节点")
        self.assertEqual(type_dist.get("FalsificationRule"), 41, "每个行业必须拥有买方核心反证逻辑节点")
        self.assertEqual(type_dist.get("DesignSpec"), 41, "每个行业必须映射至设计书与计算引擎代码")

    def test_get_industry_boundary_mining(self):
        """【KG-02: 金属采矿 (mining) 行业边界 O(1) 提取测试】"""
        boundary = self.engine.get_industry_boundary("mining")
        self.assertTrue(boundary["success"])
        self.assertEqual(boundary["code"], "mining")
        self.assertEqual(boundary["name_cn"], "金属与采矿")
        self.assertEqual(boundary["sector"]["code"], "materials")

        # 校验商业模式与专属驱动指标
        bm_codes = [bm["code"] for bm in boundary["business_models"]]
        self.assertIn("product_sales", bm_codes)

        metric_codes = [m["code"] for m in boundary["driver_metrics"]]
        self.assertIn("mining_driver_1", metric_codes)
        self.assertIn("mining_driver_2", metric_codes)
        self.assertIn("mining_driver_3", metric_codes)

        # 校验反证逻辑与设计书映射
        falsify = boundary["falsification_rule"]["core_falsification_logic"]
        self.assertTrue(len(falsify) > 20, "反证逻辑必须包含完整的业务证伪推导")
        self.assertIn("矿石品位", falsify)

        spec = boundary["design_spec"]
        self.assertIn("docs/", spec["spec_doc"])
        self.assertIn("MiningStrategy", spec["engine_module"])

    def test_get_industry_boundary_banks(self):
        """【KG-03: 商业银行 (banks) 行业边界提取与三项量化驱动指标】"""
        boundary = self.engine.get_industry_boundary("banks")
        self.assertTrue(boundary["success"])
        self.assertEqual(boundary["sector"]["code"], "financials")

        metric_codes = [m["code"] for m in boundary["driver_metrics"]]
        self.assertIn("banks_driver_1", metric_codes)
        self.assertIn("banks_driver_2", metric_codes)
        self.assertIn("banks_driver_3", metric_codes)

    def test_validate_action_boundary_rejections(self):
        """【KG-04: 自动越界防御拦截测试】拦截违规估值模型与非法调用"""
        # 1. 银行严禁使用 EV/EBITDA
        ok, msg = self.engine.validate_action_boundary("banks", proposed_valuation_model="EV/EBITDA")
        self.assertFalse(ok)
        self.assertIn("严禁使用企业价值倍数", msg)
        self.assertIn("必须使用市净率 PB-ROE 或股息折现 DDM", msg)

        # 2. 研发期生物科技严禁直接使用静态 PE
        ok, msg = self.engine.validate_action_boundary("biotech", proposed_valuation_model="P/E")
        self.assertFalse(ok)
        self.assertIn("严禁直接使用静态市盈率", msg)
        self.assertIn("必须使用研发管线风险调整净现值 rNPV", msg)

        # 3. 权益型 REITs 严禁使用 GAAP PE
        ok, msg = self.engine.validate_action_boundary("equity_reit", proposed_valuation_model="P/E")
        self.assertFalse(ok)
        self.assertIn("严禁使用 GAAP 市盈率", msg)
        self.assertIn("必须采用经调整运营资金 P/AFFO 或每股资产净值 NAV", msg)

        # 4. 未知非法行业代码拦截
        ok, msg = self.engine.validate_action_boundary("unknown_crypto_token")
        self.assertFalse(ok)
        self.assertIn("非法行业代码", msg)

    def test_validate_action_boundary_pass(self):
        """【KG-05: 合规操作验证通过测试】"""
        ok, msg = self.engine.validate_action_boundary("mining", proposed_valuation_model="DCF_Normalized_Commodity")
        self.assertTrue(ok)
        self.assertIn("知识边界验证通过", msg)

    def test_trace_supply_chain(self):
        """【KG-06: 产业链供求关系拓扑追踪断言】"""
        # 追踪半导体 (semiconductors) 的上下游
        sc = self.engine.trace_supply_chain("semiconductors")
        self.assertEqual(sc["target_code"], "semiconductors")

        # 验证半导体的上游包含半导体设备 (semi_equipment)
        upstream_suppliers = [s["supplier_industry_id"] for s in sc["direct_upstream_suppliers"]]
        self.assertIn("ind_semi_equipment", upstream_suppliers)

        # 验证半导体的下游包含硬件终端 (hardware) 与智能汽车 (autos)
        downstream_customers = [c["customer_industry_id"] for c in sc["direct_downstream_customers"]]
        self.assertIn("ind_hardware", downstream_customers)
        self.assertIn("ind_autos", downstream_customers)

    def test_search_nodes(self):
        """【KG-07: 全息图谱节点模糊检索与类型过滤】"""
        results = self.engine.search_nodes("半导体", node_type="Industry")
        self.assertGreaterEqual(len(results), 2, "应检索出半导体制造与半导体设备")
        codes = [r["code"] for r in results]
        self.assertIn("semiconductors", codes)
        self.assertIn("semi_equipment", codes)

    def test_system_design_spec_coverage(self):
        """【KG-08: 全系统核心主设计书覆盖与图拓扑规模断言】"""
        stats = self.engine.get_graph_stats()
        type_dist = stats["node_type_distribution"]
        self.assertGreaterEqual(type_dist.get("SystemDesignSpec", 0), 35, "必须覆盖全系统 35 篇以上核心主设计书")
        self.assertGreaterEqual(type_dist.get("CodeModule", 0), 30, "必须关联 30 个以上物理实现代码模块")
        self.assertGreaterEqual(type_dist.get("TestFile", 0), 25, "必须关联 25 个以上自动化验证测试套件")
        self.assertGreaterEqual(stats["total_nodes"], 400, "节点总数应大幅扩充至 400+")
        self.assertGreaterEqual(stats["total_edges"], 500, "拓扑关系边应达到 500+")

    def test_find_design_content_multidimensional(self):
        """【KG-09: 设计内容多维秒级查找测试】解决功能定位与代码寻找难题"""
        # 1. 按核心功能/算法关键词查找平账
        results_balance = self.engine.find_design_content("平账")
        self.assertTrue(len(results_balance) >= 1)
        spec_nums = [r["spec_number"] for r in results_balance]
        self.assertIn("14", spec_nums, "应精准定位至 docs/14 财报解析与平账自检设计书")

        # 2. 按买入信号/VCP关键词查找 SEPA
        results_sepa = self.engine.find_design_content("SEPA")
        self.assertTrue(len(results_sepa) >= 1)
        sepa_hit = results_sepa[0]
        self.assertEqual(sepa_hit["spec_number"], "33")
        self.assertIn("趋势模板Stage 2研判", sepa_hit["core_features"][0])
        self.assertTrue(any("sepa_buy_signal_engine" in cb["file"] for cb in sepa_hit["code_bindings"]))

        # 3. 按宏观前瞻/泰勒规则查找宏观传导
        results_macro = self.engine.find_design_content("前瞻指引")
        self.assertTrue(len(results_macro) >= 1)
        self.assertEqual(results_macro[0]["spec_number"], "23")

    def test_get_design_spec_boundary(self):
        """【KG-10: 单篇设计书边界与上下游 DAG 提取测试】"""
        boundary = self.engine.get_design_spec_boundary("14")
        self.assertTrue(boundary["success"])
        self.assertEqual(boundary["spec_number"], "14")
        self.assertIn("平账自检", boundary["title"])
        self.assertEqual(boundary["doc_path"], "docs/14-财报解析标准化与计算功能设计.md")

        # 验证绑定的代码与测试
        code_files = [cb["file_path"] for cb in boundary["code_bindings"]]
        self.assertTrue(any("filing_mapper.py" in cf for cf in code_files))

        test_files = [tb["file_path"] for tb in boundary["test_bindings"]]
        self.assertTrue(any("test_filing_mapper_balance.py" in tf for tf in test_files))

        # 验证直接上游与下游影响
        upstream_nums = [u["spec_number"] for u in boundary["upstream_dependencies"]]
        self.assertIn("04", upstream_nums, "财报平账依赖上游 docs/04 数据与证据管理")

        downstream_nums = [d["spec_number"] for d in boundary["direct_downstream_impacts"]]
        self.assertIn("21", downstream_nums, "深度档案 docs/21 直接依赖财报平账 docs/14")
        self.assertIn("26", downstream_nums, "千家资产池 docs/26 直接依赖财报平账 docs/14")

    def test_analyze_upgrade_impact_downstream(self):
        """【KG-11: 设计升级影响面分析与波及半径推演测试】"""
        impact = self.engine.analyze_upgrade_impact("14")
        self.assertTrue(impact["success"])

        # 核心数据基石升级风险等级断言为 Critical
        self.assertEqual(impact["risk_assessment"]["risk_level"], "Critical")

        # 验证直接波及下游与传递波及下游
        radius = impact["impact_radius"]
        direct_nums = [d["spec_number"] for d in radius["direct_downstream_specs"]]
        self.assertIn("21", direct_nums)
        self.assertIn("26", direct_nums)

        transitive_nums = [t["spec_number"] for t in radius["transitive_downstream_specs"]]
        # docs/27, docs/31, docs/32 是间接波及
        self.assertTrue(len(transitive_nums) >= 2)

        # 验证收集到的必跑测试清单
        test_paths = [t["file"] for t in impact["mandatory_regression_tests"]]
        self.assertTrue(any("test_filing_mapper_balance.py" in tp for tp in test_paths))
        self.assertTrue(any("test_normalized_universe_reconciliation.py" in tp for tp in test_paths))

    def test_generate_upgrade_checklist(self):
        """【KG-12: 自动生成五步升级实施闭环清单测试】"""
        checklist_res = self.engine.generate_upgrade_checklist("33", upgrade_summary="升级SEPA形态收敛判定算法")
        self.assertTrue(checklist_res["success"])
        self.assertEqual(checklist_res["target_spec_number"], "33")
        self.assertEqual(checklist_res["risk_level"], "High")

        steps = checklist_res["checklist_steps"]
        self.assertEqual(len(steps), 5, "必须严格包含 docs/36 标准五大闭环步骤")
        self.assertIn("设计文档修订", steps[0]["name"])
        self.assertIn("底层代码改造", steps[1]["name"])
        self.assertIn("测试用例增补", steps[2]["name"])
        self.assertIn("全链路回归", steps[3]["name"])
        self.assertIn("四道硬门禁验收", steps[4]["name"])

    def test_verify_graph_disk_integrity(self):
        """【KG-13: 图谱物理磁盘真实性与零死链硬断言】"""
        disk_check = self.engine.verify_graph_disk_integrity()
        if not disk_check["all_valid"]:
            print(f"缺失项清单: {disk_check['missing_items']}")
        self.assertTrue(disk_check["all_valid"], "图谱中登记的所有设计书、代码和测试文件必须在物理磁盘真实存在")
        self.assertGreaterEqual(disk_check["docs_checked"], 35)
        self.assertGreaterEqual(disk_check["code_files_checked"], 30)
        self.assertGreaterEqual(disk_check["test_files_checked"], 25)
        self.assertEqual(disk_check["missing_count"], 0)

if __name__ == "__main__":
    unittest.main()

