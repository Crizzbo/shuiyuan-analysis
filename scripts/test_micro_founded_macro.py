"""诺贝尔经济学奖微观基础宏观传导与制度风险架构单元测试套件.

涵盖理论：
1. 迈克尔·伍德福德 (Michael Woodford, 2026年诺贝尔经济学奖) 维克塞尔自然利率缺口与前瞻指引动态期限 WACC 向量；
2. 罗伯特·霍尔 (Robert E. Hall, 2026年诺贝尔经济学奖) 微观加成率 (Markup)、成本转嫁摩擦与预防性流动性囤积；
3. 达龙·阿西莫格鲁、西蒙·约翰逊、詹姆斯·鲁滨逊 (Acemoglu, Johnson, Robinson, 2024年诺贝尔经济学奖) 制度质量指数与地缘治理折价；
4. 菲利普·阿吉翁、彼得·豪伊特、乔尔·莫基尔 (Aghion, Howitt, Mokyr, 2025年诺贝尔经济学奖) 技术前沿距离与熊彼特创造性破坏；
5. 系统性主管道 (SystemicAnalysisPipeline) 与统一 API (FinancialAnalysisSystem) 宏观-微观内生估值全息闭环。
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from financial_core.contracts import (
    AnalysisMode,
    FinancialAnalysisResult,
    DecisionCardData,
    MicroFoundedMacroContractResult,
)
from financial_core.engines import (
    WoodfordForwardGuidanceEngine,
    WoodfordGuidanceInput,
    WoodfordGuidanceResult,
    HallDiscountFrictionEngine,
    HallFrictionInput,
    HallFrictionResult,
    AcemogluInstitutionalRiskEngine,
    AcemogluInstitutionalInput,
    AcemogluInstitutionalResult,
    AghionCreativeDestructionEngine,
    AghionDestructionInput,
    AghionDestructionResult,
    MicroFoundedMacroEngine,
    MicroFoundedMacroInput,
    MicroFoundedMacroCompositeResult,
)
from financial_core.pipeline import (
    SystemicCompanyInput,
    SystemicAnalysisPipeline,
)
from financial_core.api import FinancialAnalysisSystem


class TestMicroFoundedMacroArchitecture(unittest.TestCase):
    """诺奖微观基础宏观传导架构核心测试套件."""

    def setUp(self):
        self.api = FinancialAnalysisSystem()
        self.pipeline = SystemicAnalysisPipeline()
        self.woodford_engine = WoodfordForwardGuidanceEngine()
        self.hall_engine = HallDiscountFrictionEngine()
        self.acemoglu_engine = AcemogluInstitutionalRiskEngine()
        self.aghion_engine = AghionCreativeDestructionEngine()
        self.composite_engine = MicroFoundedMacroEngine()

    def test_woodford_wicksellian_gap_and_dynamic_wacc(self):
        """【UT-MFMACRO-01: 伍德福德维克塞尔自然利率缺口(Wicksellian Gap)与逐年动态折现向量(Dynamic WACC)及下界防御断言】

        1. 测试功能与测试点:
           - 验证 WoodfordForwardGuidanceEngine 计算维克塞尔自然利率缺口：政策利率 5.25% - 预期通胀 2.5% - 自然利率 1.25% = +150 bps（紧缩立场）。
           - 验证点阵图逐年降息路径推进下的动态期限 WACC 向量平滑下行收敛。
           - 验证金融数学硬边界约束：任何时点 WACC 均不得低于 3.5% 下界，极低/负利率输入触发有限责任防御。

        2. 正常函数业务边界与参数契约:
           - WoodfordGuidanceInput 接收通胀预期、点阵图路径与股权风险溢价。
           - evaluate(inp) 输出 WoodfordGuidanceResult 强类型结果。

        3. 测试数据与模拟场景说明:
           - 美联储紧缩周期基准参数与负利率极端测试输入。

        4. 预期断言与结果验证:
           - wicksellian_rate_gap_bps == 150.0。
           - is_monetary_restrictive 为 True。
           - dynamic_wacc_vector[0] > dynamic_wacc_vector[-1] 且所有元素 >= 0.035。
        """
        # 紧缩情景: 政策利率 5.25%, 通胀预期 2.5%, 自然利率 1.25%
        # 真实政策利率 = 5.25% - 2.5% = 2.75%, 缺口 = 2.75% - 1.25% = 1.50% = +150 bps (紧缩)
        inp = WoodfordGuidanceInput(
            policy_rate=0.0525,
            expected_inflation_1y=0.025,
            natural_rate_r_star=0.0125,
            equity_beta=1.2,
            equity_risk_premium=0.055,
            debt_to_equity=0.4,
            credit_spread=0.0180,
            tax_rate=0.21,
            forecast_years=5,
            dot_plot_rate_path=[0.050, 0.0425, 0.0350, 0.030, 0.0275],
        )
        res = self.woodford_engine.evaluate(inp)

        self.assertIsInstance(res, WoodfordGuidanceResult)
        self.assertAlmostEqual(res.wicksellian_rate_gap_bps, 150.0, places=1)
        self.assertTrue(res.is_monetary_restrictive)
        self.assertIn("紧缩", res.monetary_stance_summary)

        # 检查动态 WACC 向量长度与数值合理性
        self.assertEqual(len(res.dynamic_wacc_vector), 5)
        # 首期政策利率高，WACC 较高；随着降息路径推进，远期 WACC 应呈下行平滑收敛趋势
        self.assertGreaterEqual(res.dynamic_wacc_vector[0], 0.07)
        self.assertGreater(res.dynamic_wacc_vector[0], res.dynamic_wacc_vector[-1])
        # 硬边界约束: 任何时期 WACC 均不得低于 3.5%
        for w in res.dynamic_wacc_vector:
            self.assertGreaterEqual(w, 0.035)

        # 边界防御: 极低/负利率输入下的下界收敛
        neg_inp = WoodfordGuidanceInput(
            policy_rate=-0.01,
            expected_inflation_1y=0.05,
            natural_rate_r_star=0.02,
            equity_beta=0.2,
            credit_spread=-0.05,
        )
        neg_res = self.woodford_engine.evaluate(neg_inp)
        self.assertFalse(neg_res.is_monetary_restrictive)
        for w in neg_res.dynamic_wacc_vector:
            self.assertGreaterEqual(w, 0.035)

    def test_hall_markup_friction_and_precautionary_curtailment(self):
        """【UT-MFMACRO-02: 霍尔微观加成率(Hall Markup)/转嫁弹性摩擦与预防性流动性囤积(Capex Curtailment)核验】

        1. 测试功能与测试点:
           - 验证 HallDiscountFrictionEngine 评估企业微观加成率 (Markup) 与定价权防线。
           - 强定价权标的（转嫁弹性 0.90）：加成率 > 1.4，归类 "STRONG_DEFENSE"，毛利率受挫轻微，Capex 削减温和 (< 20%)。
           - 弱定价权高负债标的（转嫁弹性 0.20，FCF < 0）：归类 "SEVERE_MARGIN_SQUEEZE"，毛利严重挤压，Capex 遭大幅削减 (>= 15%)。

        2. 正常函数业务边界与参数契约:
           - HallFrictionInput 包含企业财务事实与宏观通胀、VIX 输入。
           - evaluate(inp) 输出 HallFrictionResult。

        3. 测试数据与模拟场景说明:
           - 对比高毛利半导体巨头与薄利高负债代工企业在原材料暴涨与 VIX 飙升下的分化。

        4. 预期断言与结果验证:
           - 强定价权：micro_markup_ratio > 1.4，pricing_power_tier == 'STRONG_DEFENSE'。
           - 弱定价权：pricing_power_tier == 'SEVERE_MARGIN_SQUEEZE'，precautionary_capex_curtailment_pct >= 15.0。
        """
        # 强定价权消费/半导体企业: 转嫁弹性 0.90, 加成率高
        inp_strong = HallFrictionInput(
            reported_revenue=1000.0,
            reported_cogs=500.0,
            reported_gross_margin_pct=50.0,
            reported_capex=80.0,
            cash_and_equivalents=300.0,
            total_debt=100.0,
            annual_fcf=120.0,
            commodity_input_inflation_pct=6.0,
            unit_labor_cost_inflation_pct=4.0,
            macro_vix_volatility=25.0,
            pricing_pass_through_elasticity=0.90,
        )
        res_strong = self.hall_engine.evaluate(inp_strong)

        self.assertIsInstance(res_strong, HallFrictionResult)
        # 营业毛利率 50% 对应加成率约 1.5 ~ 2.0
        self.assertGreater(res_strong.micro_markup_ratio, 1.4)
        self.assertEqual(res_strong.pricing_power_tier, "STRONG_DEFENSE")
        # 强转嫁权下毛利率侵蚀较轻 (侵蚀幅度 < 2.0%)
        self.assertGreaterEqual(res_strong.shocked_gross_margin_pct, 48.0)
        # 流动性充足且现金流为正，Capex 削减幅度温和
        self.assertLess(res_strong.precautionary_capex_curtailment_pct, 20.0)

        # 弱定价权低毛利高负债制造企业: 转嫁弹性 0.20, 现金流负
        inp_weak = HallFrictionInput(
            reported_revenue=1000.0,
            reported_cogs=880.0,
            reported_gross_margin_pct=12.0,
            reported_capex=60.0,
            cash_and_equivalents=20.0,
            total_debt=400.0,
            annual_fcf=-50.0,
            commodity_input_inflation_pct=8.0,
            unit_labor_cost_inflation_pct=5.0,
            macro_vix_volatility=38.0,
            pricing_pass_through_elasticity=0.20,
        )
        res_weak = self.hall_engine.evaluate(inp_weak)
        self.assertEqual(res_weak.pricing_power_tier, "SEVERE_MARGIN_SQUEEZE")
        # 成本冲击大幅侵蚀微薄毛利
        self.assertLess(res_weak.shocked_gross_margin_pct, inp_weak.reported_gross_margin_pct)
        self.assertLess(res_weak.gross_margin_shock_pct, 0.0)
        # 危机中预防性流动性囤积，Capex 遭到显著削减 (>= 15%)
        self.assertGreaterEqual(res_weak.precautionary_capex_curtailment_pct, 15.0)
        self.assertIn("利润率严重受压脆弱型", res_weak.friction_verdict)
        self.assertNotIn("SEVERE_MARGIN_SQUEEZE", res_weak.friction_verdict)
        self.assertIn("成本摩擦加成率与流动性防御全息研判", res_weak.narrative_zh)

    def test_acemoglu_institutional_risk_and_governance_haircut(self):
        """【UT-MFMACRO-03: 阿西莫格鲁制度质量指数(Institutional Quality)与终值地缘治理折价(Governance Haircut)断言】

        1. 测试功能与测试点:
           - 验证 AcemogluInstitutionalRiskEngine 计算法治保护、产权安全性与地缘政治脆弱性。
           - 包容性强制度样本（美日成熟市场）：制度质量得分 >= 80，制度风险溢价 <= 100 bps，终值折价 <= 5%。
           - 掠夺性高风险样本（前沿市场高地缘制裁暴露）：制度利差大幅走阔 >= 200 bps，终值治理折价 >= 25%。

        2. 正常函数业务边界与参数契约:
           - AcemogluInstitutionalInput 接收产权、腐败控制及制裁暴露标志。
           - evaluate(inp) 输出 AcemogluInstitutionalResult。

        3. 测试数据与模拟场景说明:
           - 对比成熟合规本土蓝筹与地缘高危边陲市场标的。

        4. 预期断言与结果验证:
           - 包容性：institution_type == 'INCLUSIVE_STRONG'，terminal_value_governance_haircut_pct <= 5.0。
           - 掠夺性：institution_type == 'EXTRACTIVE_RISK'，institutional_risk_spread_bps >= 200.0。
        """
        # 成熟包容性制度样本 (如美股/日股本土合规蓝筹)
        inp_inclusive = AcemogluInstitutionalInput(
            country_domicile="US",
            rule_of_law_score=88.0,
            property_rights_security=90.0,
            regulatory_predictability=85.0,
            corruption_control_score=85.0,
            cross_border_sanction_exposure=False,
            offshore_revenue_share_pct=25.0,
            sensitive_technology_sector=False,
            geopolitical_tension_index=30.0,
        )
        res_inclusive = self.acemoglu_engine.evaluate(inp_inclusive)

        self.assertIsInstance(res_inclusive, AcemogluInstitutionalResult)
        self.assertGreaterEqual(res_inclusive.institutional_quality_index, 80.0)
        self.assertEqual(res_inclusive.institution_type, "INCLUSIVE_STRONG")
        self.assertLessEqual(res_inclusive.institutional_risk_spread_bps, 100.0)
        self.assertLessEqual(res_inclusive.terminal_value_governance_haircut_pct, 5.0)

        # 存在地缘摩擦与制裁暴露的高危标的
        inp_extractive = AcemogluInstitutionalInput(
            country_domicile="FRONTIER",
            rule_of_law_score=45.0,
            property_rights_security=40.0,
            regulatory_predictability=35.0,
            corruption_control_score=30.0,
            cross_border_sanction_exposure=True,
            offshore_revenue_share_pct=70.0,
            sensitive_technology_sector=True,
            geopolitical_tension_index=85.0,
        )
        res_extractive = self.acemoglu_engine.evaluate(inp_extractive)
        self.assertEqual(res_extractive.institution_type, "EXTRACTIVE_RISK")
        # 制度利差大幅飙升 (> 200 bps)
        self.assertGreaterEqual(res_extractive.institutional_risk_spread_bps, 200.0)
        # 远期终值治理折价显著 (> 25%)
        self.assertGreaterEqual(res_extractive.terminal_value_governance_haircut_pct, 25.0)

    def test_aghion_creative_destruction_and_frontier_distance(self):
        """【UT-MFMACRO-04: 阿吉翁熊彼特创造性破坏/技术前沿距离(DTF)与终值增长率调整核验】

        1. 测试功能与测试点:
           - 验证 AghionCreativeDestructionEngine 计算技术前沿距离 (DTF) 与熊彼特淘汰风险。
           - 行业前沿领跑者（高研发、高质量专利壁垒、现金充沛）：DTF >= 0.85，终值增长率享受正向奖励 (>= 50 bps)，出清风险 < 10%。
           - 僵尸出清型标的（零研发、重债务、现金持续流血）：DTF < 0.35，终值增长率惩罚性下调 (< -50 bps)，淘汰风险 >= 50%。

        2. 正常函数业务边界与参数契约:
           - AghionDestructionInput 包含研发强度、专利质量得分与债务偿付倍数。
           - evaluate(inp) 输出 AghionDestructionResult。

        3. 测试数据与模拟场景说明:
           - 对比高科技领跑者与出清边缘僵尸企业。

        4. 预期断言与结果验证:
           - 领跑者：schumpeterian_survival_status == 'FRONTIER_LEADER'，terminal_growth_adjustment_bps >= 50.0。
           - 僵尸型：schumpeterian_survival_status == 'CREATIVE_DESTRUCTION_VULNERABLE'，zombie_risk >= 50.0。
        """
        # 行业顶级前沿领跑者 (高研发、高专利护城河、充沛自由现金流)
        inp_leader = AghionDestructionInput(
            rd_expenses=180.0,
            reported_revenue=1000.0,
            industry_max_rd_intensity_pct=18.0,
            patent_portfolio_quality_score=92.0,
            total_debt_to_ebitda=1.2,
            operating_cash_flow=350.0,
            capital_expenditures=100.0,
            is_disruptive_innovator=True,
        )
        res_leader = self.aghion_engine.evaluate(inp_leader)

        self.assertIsInstance(res_leader, AghionDestructionResult)
        self.assertGreaterEqual(res_leader.distance_to_technology_frontier, 0.85)
        self.assertEqual(res_leader.schumpeterian_survival_status, "FRONTIER_LEADER")
        # 领跑者逆周期市占率提升，终值增长率享受正向奖励 (+50 ~ +100 bps)
        self.assertGreaterEqual(res_leader.terminal_growth_adjustment_bps, 50.0)
        self.assertGreater(res_leader.market_share_consolidation_multiplier, 1.0)
        self.assertLess(res_leader.zombie_creative_destruction_risk_pct, 10.0)

        # 僵尸出清高危型企业 (零研发、沉重债务、现金流持续流血)
        inp_zombie = AghionDestructionInput(
            rd_expenses=5.0,
            reported_revenue=1000.0,
            industry_max_rd_intensity_pct=18.0,
            patent_portfolio_quality_score=20.0,
            total_debt_to_ebitda=6.5,
            operating_cash_flow=-50.0,
            capital_expenditures=30.0,
            is_disruptive_innovator=False,
        )
        res_zombie = self.aghion_engine.evaluate(inp_zombie)
        self.assertEqual(res_zombie.schumpeterian_survival_status, "CREATIVE_DESTRUCTION_VULNERABLE")
        self.assertLess(res_zombie.distance_to_technology_frontier, 0.35)
        # 终值增长率惩罚性下调
        self.assertLess(res_zombie.terminal_growth_adjustment_bps, -50.0)
        self.assertGreaterEqual(res_zombie.zombie_creative_destruction_risk_pct, 50.0)
        self.assertLess(res_zombie.market_share_consolidation_multiplier, 1.0)

    def test_composite_micro_founded_macro_engine(self):
        """【IT-MFMACRO-05: 微观基础宏观综合总装引擎四引擎熔铸与全景评级验证】

        1. 测试功能与测试点:
           - 验证 MicroFoundedMacroEngine 将伍德福德、霍尔、阿西莫格鲁与阿吉翁四大诺奖模型熔铸总装。
           - 综合推导英伟达 (NVDA) 真实企业环境下的初始有效 WACC (> 7.0%)、10 年动态 WACC 向量与终值增长奖励。
           - 输出“微观基础宏观全景”统领性买方评级结论。

        2. 正常函数业务边界与参数契约:
           - MicroFoundedMacroInput 接收企业微观三表与宏观基准全量参数。
           - evaluate(comp_inp) 返回 MicroFoundedMacroCompositeResult。

        3. 测试数据与模拟场景说明:
           - NVDA 真实财报参数。

        4. 预期断言与结果验证:
           - effective_initial_wacc_pct > 7.0。
           - len(dynamic_wacc_vector) == 10。
           - terminal_growth_rate_adj_bps > 0.0。
           - integrated_macro_verdict 包含“微观基础宏观全景”。
        """
        comp_inp = MicroFoundedMacroInput(
            ticker="NVDA",
            country_domicile="US",
            sector="TechHardware",
            policy_rate=0.0475,
            expected_inflation_1y=0.024,
            natural_rate_r_star=0.0120,
            equity_beta=1.35,
            equity_risk_premium=0.055,
            credit_spread=0.0120,
            reported_revenue=26000.0,
            reported_cogs=7000.0,
            reported_gross_margin_pct=73.0,
            reported_capex=2500.0,
            cash_and_equivalents=20000.0,
            total_debt=9000.0,
            annual_fcf=18000.0,
            macro_vix=21.0,
            pricing_pass_through_elasticity=0.92,
            rule_of_law_score=88.0,
            rd_expenses=3000.0,
            patent_portfolio_quality_score=95.0,
            operating_cash_flow=20500.0,
            is_disruptive_innovator=True,
        )
        res = self.composite_engine.evaluate(comp_inp)

        self.assertIsInstance(res, MicroFoundedMacroCompositeResult)
        self.assertEqual(res.ticker, "NVDA")
        self.assertGreater(res.effective_initial_wacc_pct, 7.0)
        self.assertEqual(len(res.dynamic_wacc_vector), 10)
        self.assertGreater(res.terminal_growth_rate_adj_bps, 0.0)
        self.assertIn("微观基础宏观全景", res.integrated_macro_verdict)
        # 买方自然全息研报卡片契约断言
        self.assertIn("【标的 NVDA 宏观传导与制度护城河全息研报】", res.narrative_zh)
        self.assertIn("定价权定性为【强防御特许定价权】", res.narrative_zh)
        self.assertIn("行业技术竞争地位属于【行业技术前沿领跑者】", res.narrative_zh)
        res_dict = res.to_dict()
        self.assertIn("narrative_zh", res_dict)
        self.assertIn("woodford", res_dict)
        self.assertIn("hall", res_dict)
        self.assertIn("acemoglu", res_dict)
        self.assertIn("aghion", res_dict)

    def test_systemic_pipeline_stage3_and_stage4_linkage(self):
        """【FT-MFMACRO-06: 系统性主管道Stage3宏观压力与Stage4估值走廊单调性内生闭环联动断言】

        1. 测试功能与测试点:
           - 验证 SystemicAnalysisPipeline 在三阶段宏观压力中内嵌微观基础宏观推导字典。
           - 验证四阶段长短期差异化情景 DCF 估值走廊刚性单调性契约：
             悲观底价 <= 0.90 * 公允锚点 < 公允锚点 < 1.10 * 公允锚点 <= 乐观靶心。
           - 验证顶层机构决策卡片成功挂载维克塞尔缺口、首期动态 WACC、定价权等级与前沿距离。

        2. 正常函数业务边界与参数契约:
           - run_systemic_analysis 输出完整报告字典，pipeline_status == 'SUCCESS'。

        3. 测试数据与模拟场景说明:
           - RXRX 样本企业完整参数运行。

        4. 预期断言与结果验证:
           - stage_3 包含 micro_founded_macro 字典。
           - 估值走廊单调性满足：pess_floor <= fair_price * 0.90 且 opt_target >= fair_price * 1.10。
           - card 关键宏观字段健全非空。
        """
        comp_input = self.api.get_preset_sample_input("RXRX")
        self.assertIsNotNone(comp_input)

        out = self.pipeline.run_systemic_analysis(comp_input)
        self.assertEqual(out["pipeline_status"], "SUCCESS")

        # 检查 Stage 3 宏观输出中内嵌微观基础宏观字典
        stage_3 = out["stage_3_macro_stress"]
        self.assertIn("micro_founded_macro", stage_3)
        mf_macro = stage_3["micro_founded_macro"]
        self.assertIn("wicksellian_rate_gap_bps", mf_macro)
        self.assertIn("dynamic_wacc_vector", mf_macro)
        self.assertIn("schumpeterian_survival_status", mf_macro)
        self.assertIn("pricing_power_tier", mf_macro)

        # 检查 Stage 4 估值体系
        stage_4 = out["stage_4_valuation"]
        pess_floor = stage_4["pessimistic_floor"]
        fair_price = stage_4["forensic_adjusted_fair_price"]
        opt_target = stage_4["optimistic_target"]

        # 验证单调估值走廊: 悲观底 <= 0.90 * 公允锚点 < 公允锚点 < 1.10 * 公允锚点 <= 乐观靶心
        self.assertLessEqual(pess_floor, fair_price * 0.90 + 1e-4)
        self.assertGreaterEqual(opt_target, fair_price * 1.10 - 1e-4)

        # 检查顶层机构决策卡片中的微观基础宏观字段
        card = out["final_institutional_decision_card"]
        self.assertIsNotNone(card.get("wicksellian_gap_bps"))
        self.assertIsNotNone(card.get("dynamic_wacc_t1"))
        self.assertIsNotNone(card.get("pricing_power_tier"))
        self.assertIsNotNone(card.get("distance_to_frontier"))
        self.assertIsNotNone(card.get("institutional_quality_score"))
        self.assertTrue(len(card.get("micro_founded_macro_verdict", "")) > 0)

    def test_financial_analysis_system_api_modes(self):
        """【IT-MFMACRO-07: FinancialAnalysisSystem统一API多模式执行与全息决策卡片契约核验】

        1. 测试功能与测试点:
           - 验证 FinancialAnalysisSystem.analyze_equity 在 MICRO_FOUNDED_MACRO 与 FULL_SYSTEMIC 双模式下的执行契约。
           - 模式 1: 单独执行宏观微观微基传导分析模式，断言强类型返回对象与卡片字段。
           - 模式 2: 执行全流程系统性分析模式，断言顶层决策卡片包含定价权等级与前沿距离。
           - 验证 to_dict() 序列化健全无 TypeError 且关键宏观参数保真。

        2. 正常函数业务边界与参数契约:
           - 支持枚举 AnalysisMode，返回 FinancialAnalysisResult 对象。

        3. 测试数据与模拟场景说明:
           - RXRX 样本企业输入。

        4. 预期断言与结果验证:
           - execution_success 为 True。
           - res_macro_mode.analysis_mode == 'MICRO_FOUNDED_MACRO'。
           - res_dict 字典健全且数值一致。
        """
        comp_input = self.api.get_preset_sample_input("RXRX")

        # 1. 独立执行 MICRO_FOUNDED_MACRO 模式
        res_macro_mode = self.api.analyze_equity(
            ticker="RXRX",
            company_input=comp_input,
            mode=AnalysisMode.MICRO_FOUNDED_MACRO,
        )
        self.assertTrue(res_macro_mode.execution_success)
        self.assertEqual(res_macro_mode.analysis_mode, AnalysisMode.MICRO_FOUNDED_MACRO.value)
        self.assertIsInstance(res_macro_mode.micro_founded_macro, MicroFoundedMacroContractResult)
        self.assertGreater(len(res_macro_mode.micro_founded_macro.dynamic_wacc_vector), 0)
        self.assertIsNotNone(res_macro_mode.decision_card.wicksellian_gap_bps)
        self.assertIsNotNone(res_macro_mode.decision_card.dynamic_wacc_t1)

        # 2. 完整执行 FULL_SYSTEMIC 模式
        res_full = self.api.analyze_equity(
            ticker="RXRX",
            company_input=comp_input,
            mode=AnalysisMode.FULL_SYSTEMIC,
        )
        self.assertTrue(res_full.execution_success)
        self.assertIsInstance(res_full.micro_founded_macro, MicroFoundedMacroContractResult)
        self.assertIsNotNone(res_full.decision_card.wicksellian_gap_bps)
        self.assertIsNotNone(res_full.decision_card.pricing_power_tier)
        self.assertIsNotNone(res_full.decision_card.distance_to_frontier)

        # 验证序列化为字典时不出现 TypeError 且字段健全
        res_dict = res_full.to_dict()
        self.assertIn("micro_founded_macro", res_dict)
        self.assertIsNotNone(res_dict["micro_founded_macro"])
        self.assertEqual(
            res_dict["micro_founded_macro"]["wicksellian_rate_gap_bps"],
            res_full.micro_founded_macro.wicksellian_rate_gap_bps,
        )


    def test_ut_mfmacro_08_narrative_zh_and_buyer_dossier_contract(self):
        """【UT-MFMACRO-08: 诺奖微观基础宏观四大引擎买方全息研报卡片与去工程符号化契约断言】

        一、测试功能与测试点:
            1. 验证伍德福德前瞻指引引擎、霍尔微观加成率引擎、阿西莫格鲁制度风险引擎与阿吉翁创造性破坏引擎输出中，
               均已彻底根除纯英文技术代号直接暴露，全面对齐自然中文买方全息研报卡片 `narrative_zh` 契约。
            2. 验证各个引擎输出的 `to_dict()` 方法均健全包含 `narrative_zh` 与对应中文语义定性字段。

        二、正常函数业务边界与参数契约:
            - 伍德福德: `monetary_stance_zh` 与 `narrative_zh` 包含自然中文货币立场与期限折现研判。
            - 霍尔: `pricing_power_tier_zh` 与 `narrative_zh` 包含加成率与流动性防御研判。
            - 阿西莫格鲁: `institution_type_zh` 与 `narrative_zh` 包含主权法治与地缘管辖脆弱度研判。
            - 阿吉翁: `schumpeterian_survival_status_zh` 与 `narrative_zh` 包含熊彼特技术竞争位势研判。

        三、测试数据与模拟场景说明:
            - 使用典型输入运行四大独立引擎。

        四、预期断言与结果验证:
            - 断言每个引擎返回的 `narrative_zh` 均非空且包含中文研判标题前缀。
            - 断言 `to_dict()` 正常序列化且字段健全。
        """
        # 1. 伍德福德前瞻指引
        woodford_res = self.woodford_engine.evaluate(WoodfordGuidanceInput(
            policy_rate=0.0525, expected_inflation_1y=0.025, natural_rate_r_star=0.0125,
        ))
        self.assertIn("深度货币紧缩走廊", woodford_res.monetary_stance_zh)
        self.assertIn("【央行前瞻指引与自然利率期限折现全息研判】", woodford_res.narrative_zh)
        self.assertIn("narrative_zh", woodford_res.to_dict())

        # 2. 霍尔成本摩擦与加成率
        hall_res = self.hall_engine.evaluate(HallFrictionInput(
            reported_revenue=1000.0, reported_cogs=500.0, reported_gross_margin_pct=50.0,
            reported_capex=80.0, cash_and_equivalents=300.0, total_debt=100.0, annual_fcf=120.0,
            pricing_pass_through_elasticity=0.90,
        ))
        self.assertEqual(hall_res.pricing_power_tier_zh, "强防御特许定价权")
        self.assertIn("【成本摩擦加成率与流动性防御全息研判】", hall_res.narrative_zh)
        self.assertIn("narrative_zh", hall_res.to_dict())

        # 3. 阿西莫格鲁制度风险
        acemoglu_res = self.acemoglu_engine.evaluate(AcemogluInstitutionalInput(
            country_domicile="US", rule_of_law_score=88.0, property_rights_security=90.0,
            regulatory_predictability=85.0, corruption_control_score=85.0,
        ))
        self.assertEqual(acemoglu_res.institution_type_zh, "高度包容法治安全型")
        self.assertIn("【主权治理与制度法治风险全息研判】", acemoglu_res.narrative_zh)
        self.assertIn("narrative_zh", acemoglu_res.to_dict())

        # 4. 阿吉翁创造性破坏
        aghion_res = self.aghion_engine.evaluate(AghionDestructionInput(
            rd_expenses=180.0, reported_revenue=1000.0, industry_max_rd_intensity_pct=18.0,
            patent_portfolio_quality_score=92.0, total_debt_to_ebitda=1.2,
            operating_cash_flow=350.0, capital_expenditures=100.0, is_disruptive_innovator=True,
        ))
        self.assertEqual(aghion_res.schumpeterian_survival_status_zh, "行业技术前沿领跑者")
        self.assertIn("【熊彼特创造性破坏与技术前沿全息研判】", aghion_res.narrative_zh)
        self.assertIn("narrative_zh", aghion_res.to_dict())


if __name__ == "__main__":
    unittest.main()
