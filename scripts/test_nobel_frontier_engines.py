"""诺贝尔经济学奖微观前沿引擎单元测试套件 (Test Nobel Frontier Engines).

本测试模块严格遵循《36号工程黄金设计规范》与四段式结构化中文契约测试模型:
1. 测试功能与测试点说明 (Test Functionality & Objectives)
2. 正常函数业务边界与参数契约 (Business Boundaries & Parameter Contracts)
3. 测试数据与模拟场景说明 (Test Data & Scenario Descriptions)
4. 预期断言与结果验证 (Expected Assertions & Verification)

涵盖阿西莫格鲁制度风险与主权治理溢价引擎 (Acemoglu Institutional Risk)、
霍尔微观成本摩擦与加成率引擎 (Hall Discount Friction)、
阿吉翁创造性破坏与技术前沿引擎 (Aghion Creative Destruction)
之金融动力学核算、去工程符号化、纯自然中文买方研报卡片与中继门面 SSOT 完全等价性断言。
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.acemoglu_institutional_risk_engine import (
    AcemogluInstitutionalInput,
    AcemogluInstitutionalResult,
    AcemogluInstitutionalRiskEngine,
)
from financial_core.engines.hall_discount_friction_engine import (
    HallFrictionInput,
    HallFrictionResult,
    HallDiscountFrictionEngine,
)
from financial_core.engines.aghion_creative_destruction_engine import (
    AghionDestructionInput,
    AghionDestructionResult,
    AghionCreativeDestructionEngine,
)

from finance_tools.acemoglu_institutional_risk_engine import (
    AcemogluInstitutionalInput as FacadeAcemogluInput,
    AcemogluInstitutionalRiskEngine as FacadeAcemogluEngine,
)
from finance_tools.hall_discount_friction_engine import (
    HallFrictionInput as FacadeHallInput,
    HallDiscountFrictionEngine as FacadeHallEngine,
)
from finance_tools.aghion_creative_destruction_engine import (
    AghionDestructionInput as FacadeAghionInput,
    AghionCreativeDestructionEngine as FacadeAghionEngine,
)


class TestNobelFrontierEngines(unittest.TestCase):
    """诺奖前沿宏微观经济学引擎契约测试."""

    def test_ut_acemoglu_01_inclusive_rule_of_law_strong(self):
        """【UT-ACE-01: 强包容性制度体系法治溢价与零终值折价断言】

        一、测试功能与测试点:
            验证在成熟法治、司法独立与产权保护完善的环境中 (如法治分 90，产权安全 90):
            1. 制度质量评级判定为"高度包容法治安全型"；
            2. 制度与产权风险补偿利差处于超低安全区间 (<60 bps)；
            3. 超长远期终值产权不确定性折价率为 0.0% (顶级法治无终值折价)；
            4. narrative_zh 包含纯自然中文研报，无工程代号暴露与机械括号。

        二、正常函数业务边界与参数契约:
            - 各评分介于 0.0 与 100.0 之间；
            - cross_border_sanction_exposure 为 False。

        三、测试数据与模拟场景说明:
            测试成熟发达法治国家科技巨头。

        四、预期断言与结果验证:
            断言 institution_type_zh 为 "高度包容法治安全型"。
            断言 terminal_value_governance_haircut_pct == 0.0。
            断言 narrative_zh 包含"主权制度质量评级【高度包容法治安全型】"。
            断言 to_dict() 完整暴露 narrative_zh。
        """
        inp = AcemogluInstitutionalInput(
            country_domicile="US",
            rule_of_law_score=90.0,
            property_rights_security=90.0,
            regulatory_predictability=85.0,
            corruption_control_score=90.0,
            cross_border_sanction_exposure=False,
            offshore_revenue_share_pct=30.0,
            sensitive_technology_sector=False,
            geopolitical_tension_index=30.0,
        )
        engine = AcemogluInstitutionalRiskEngine()
        res = engine.evaluate(inp)

        self.assertEqual(res.institution_type_zh, "高度包容法治安全型")
        self.assertEqual(res.terminal_value_governance_haircut_pct, 0.0)
        self.assertLess(res.institutional_risk_spread_bps, 100.0)
        self.assertIn("主权治理与制度法治风险全息研判", res.narrative_zh)
        self.assertIn("主权制度质量评级【高度包容法治安全型】", res.narrative_zh)
        self.assertNotIn("(", res.narrative_zh.split("基础法治架构:")[1].split("。")[0])

        d = res.to_dict()
        self.assertIn("narrative_zh", d)
        self.assertEqual(d["institution_type_zh"], "高度包容法治安全型")

    def test_ut_acemoglu_02_extractive_sanction_vulnerability(self):
        """【UT-ACE-02: 掠夺型制度脆弱性与跨国实体清单制裁地缘利差惩罚断言】

        一、测试功能与测试点:
            验证当标的处于制度摩擦高危地带，且面临跨国长臂管辖与实体清单制裁时:
            1. 制度质量评级判定为"制度掠夺与政策突变高危型"；
            2. 制度与地缘风险利差显著惩罚性上升 (>200 bps)；
            3. 终值资本折价率触发上限下折 (>15%)。

        二、正常函数业务边界与参数契约:
            - cross_border_sanction_exposure = True。

        三、测试数据与模拟场景说明:
            测试面临技术断供与跨国制裁风险的敏感标的。

        四、预期断言与结果验证:
            断言 institution_type_zh 为 "制度掠夺与政策突变高危型"。
            断言 institutional_risk_spread_bps > 200.0。
            断言 terminal_value_governance_haircut_pct > 15.0。
        """
        inp = AcemogluInstitutionalInput(
            country_domicile="EM",
            rule_of_law_score=35.0,
            property_rights_security=30.0,
            regulatory_predictability=30.0,
            corruption_control_score=25.0,
            cross_border_sanction_exposure=True,
            offshore_revenue_share_pct=50.0,
            sensitive_technology_sector=True,
            geopolitical_tension_index=80.0,
        )
        engine = AcemogluInstitutionalRiskEngine()
        res = engine.evaluate(inp)

        self.assertEqual(res.institution_type_zh, "制度掠夺与政策突变高危型")
        self.assertGreater(res.institutional_risk_spread_bps, 200.0)
        self.assertGreater(res.terminal_value_governance_haircut_pct, 15.0)
        self.assertIn("制度掠夺与政策突变高危型", res.narrative_zh)

    def test_ut_hall_01_strong_defense_pricing_power(self):
        """【UT-HALL-01: 霍尔特许定价权龙头成本转嫁抗性与消除双重正号断言】

        一、测试功能与测试点:
            验证霍尔微观成本摩擦模型:
            1. 高价格转嫁弹性 (elasticity >= 0.85) 准确评定为"强防御特许定价权"；
            2. 面对投入品通胀，毛利率抗性极强，受挤压幅度平缓；
            3. 验证 narrative_zh 买方研报彻底消除冗余正号拼贴 (+{...}%)。

        二、正常函数业务边界与参数契约:
            - pricing_pass_through_elasticity = 0.90。

        三、测试数据与模拟场景说明:
            测试高端奢侈品/晶圆代工巨头。

        四、预期断言与结果验证:
            断言 pricing_power_tier_zh 为 "强防御特许定价权"。
            断言 narrative_zh 包含 "面对上游要素复合通胀 +"，且严禁出现 "(+" 冗余符号拼贴。
        """
        inp = HallFrictionInput(
            reported_revenue=1000.0,
            reported_cogs=400.0,
            reported_gross_margin_pct=60.0,
            reported_capex=100.0,
            cash_and_equivalents=500.0,
            total_debt=100.0,
            annual_fcf=250.0,
            macro_vix_volatility=25.0,
            commodity_input_inflation_pct=4.0,
            unit_labor_cost_inflation_pct=6.0,
            labor_share_in_cogs_pct=30.0,
            pricing_pass_through_elasticity=0.90,
            variable_cost_ratio=0.70,
        )
        engine = HallDiscountFrictionEngine()
        res = engine.evaluate(inp)

        self.assertEqual(res.pricing_power_tier_zh, "强防御特许定价权")
        self.assertIn("成本摩擦加成率与流动性防御全息研判", res.narrative_zh)
        self.assertIn("面对上游要素复合通胀 +", res.narrative_zh)
        self.assertNotIn("(+", res.narrative_zh)
        self.assertNotIn("(%", res.narrative_zh)

        d = res.to_dict()
        self.assertIn("narrative_zh", d)
        self.assertEqual(d["pricing_power_tier_zh"], "强防御特许定价权")

    def test_ut_aghion_01_frontier_leader_survivor_premium(self):
        """【UT-AGHION-01: 阿吉翁技术前沿领跑者熊彼特幸存者溢价断言】

        一、测试功能与测试点:
            验证阿吉翁创造性破坏模型:
            1. 研发投入强度与专利质量双高的颠覆式创新标的，评定为"行业技术前沿领跑者"；
            2. 熊彼特逆周期市场整合乘数 > 1.0 (危机后吞噬落后对手份额)；
            3. 长周期终值永续增长率调整值为正 (+50~100 bps 幸存者溢价)；
            4. 验证 narrative_zh 研报无机械多余括号。

        二、正常函数业务边界与参数契约:
            - is_disruptive_innovator = True，dtf >= 0.80。

        三、测试数据与模拟场景说明:
            测试颠覆性 AI 芯片领军企业。

        四、预期断言与结果验证:
            断言 schumpeterian_survival_status_zh 为 "行业技术前沿领跑者"。
            断言 market_share_consolidation_multiplier > 1.0。
            断言 terminal_growth_adjustment_bps > 0.0。
            断言 narrative_zh 包含纯自然中文研报，且不含 "评分 ("。
        """
        inp = AghionDestructionInput(
            rd_expenses=12000.0,
            reported_revenue=60000.0,
            industry_max_rd_intensity_pct=20.0,
            patent_portfolio_quality_score=95.0,
            total_debt_to_ebitda=1.2,
            operating_cash_flow=30000.0,
            capital_expenditures=4000.0,
            is_disruptive_innovator=True,
        )
        engine = AghionCreativeDestructionEngine()
        res = engine.evaluate(inp)

        self.assertEqual(res.schumpeterian_survival_status_zh, "行业技术前沿领跑者")
        self.assertGreater(res.market_share_consolidation_multiplier, 1.0)
        self.assertGreater(res.terminal_growth_adjustment_bps, 0.0)
        self.assertIn("熊彼特创造性破坏与技术前沿全息研判", res.narrative_zh)
        self.assertIn("行业技术前沿领跑者", res.narrative_zh)
        self.assertNotIn("评分 (", res.narrative_zh)
        self.assertNotIn("概率 (", res.narrative_zh)

        d = res.to_dict()
        self.assertIn("narrative_zh", d)
        self.assertEqual(d["schumpeterian_survival_status_zh"], "行业技术前沿领跑者")

    def test_ut_aghion_02_zombie_vulnerability_creative_destruction(self):
        """【UT-AGHION-02: 僵尸产能技术替代出清与终值增长率惩罚性下折断言】

        一、测试功能与测试点:
            验证阿吉翁创造性破坏对落后僵尸产能的识别:
            1. 负债杠杆沉重 (Debt/EBITDA > 4.0)、缺乏研发且自由现金流失血的标的，
               评定为"技术替代与负债出清高危型"；
            2. 创造性破坏淘汰风险 zombie_creative_destruction_risk_pct >= 50%；
            3. 熊彼特长周期终值增长率惩罚性下调 (terminal_growth_adjustment_bps < 0)。

        二、正常函数业务边界与参数契约:
            - total_debt_to_ebitda = 5.0，fcf < 0。

        三、测试数据与模拟场景说明:
            测试传统高负债被替代的燃油车代工厂。

        四、预期断言与结果验证:
            断言 schumpeterian_survival_status_zh 为 "技术替代与负债出清高危型"。
            断言 zombie_creative_destruction_risk_pct >= 50.0。
            断言 terminal_growth_adjustment_bps < 0.0。
        """
        inp = AghionDestructionInput(
            rd_expenses=50.0,
            reported_revenue=5000.0,
            industry_max_rd_intensity_pct=15.0,
            patent_portfolio_quality_score=20.0,
            total_debt_to_ebitda=5.5,
            operating_cash_flow=100.0,
            capital_expenditures=300.0, # FCF = -200
            is_disruptive_innovator=False,
        )
        engine = AghionCreativeDestructionEngine()
        res = engine.evaluate(inp)

        self.assertEqual(res.schumpeterian_survival_status_zh, "技术替代与负债出清高危型")
        self.assertGreaterEqual(res.zombie_creative_destruction_risk_pct, 50.0)
        self.assertLess(res.terminal_growth_adjustment_bps, 0.0)
        self.assertIn("技术替代与负债出清高危型", res.narrative_zh)

    def test_ut_nobel_03_facade_and_core_ssot_equivalence(self):
        """【UT-NOBEL-03: 诺奖前沿引擎向下兼容门面与底层核心 SSOT 完全等价性断言】

        一、测试功能与测试点:
            验证 `finance_tools` 门面与 `financial_core` 底层核心计算结果 100% 等价。

        二、预期断言与结果验证:
            断言 Acemoglu、Hall、Aghion 门面与核心输出属性完全一致。
        """
        # 1. Acemoglu 门面对比
        ace_inp = AcemogluInstitutionalInput("US", 88.0, 88.0, 85.0, 85.0)
        res_ace_core = AcemogluInstitutionalRiskEngine().evaluate(ace_inp)
        res_ace_facade = FacadeAcemogluEngine().evaluate(ace_inp)
        self.assertEqual(res_ace_core.to_dict(), res_ace_facade.to_dict())

        # 2. Hall 门面对比
        hall_inp = HallFrictionInput(1000.0, 500.0, 50.0, 100.0, 400.0, 100.0, 20.0, 5.0, 5.0, 50.0, 0.7, 0.6)
        res_hall_core = HallDiscountFrictionEngine().evaluate(hall_inp)
        res_hall_facade = FacadeHallEngine().evaluate(hall_inp)
        self.assertEqual(res_hall_core.to_dict(), res_hall_facade.to_dict())

        # 3. Aghion 门面对比
        aghion_inp = AghionDestructionInput(1000.0, 10000.0, 15.0, 80.0, 2.0, 2000.0, 500.0)
        res_aghion_core = AghionCreativeDestructionEngine().evaluate(aghion_inp)
        res_aghion_facade = FacadeAghionEngine().evaluate(aghion_inp)
        self.assertEqual(res_aghion_core.to_dict(), res_aghion_facade.to_dict())


if __name__ == "__main__":
    unittest.main()
