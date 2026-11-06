"""商业模式微观量价拆解与单体经济量化引擎单元测试套件.

本测试模块严格遵循《36号工程黄金设计规范》与四段式结构化中文契约测试模型:
1. 测试功能与测试点说明 (Test Functionality & Objectives)
2. 正常函数业务边界与参数契约 (Business Boundaries & Parameter Contracts)
3. 测试数据与模拟场景说明 (Test Data & Scenario Descriptions)
4. 预期断言与结果验证 (Expected Assertions & Verification)

涵盖创新药 rNPV 管线折现、资不抵债有限责任下界归零防御、SaaS 单体经济学
(ARR / ARPU / NRR / CAC Payback / LTV/CAC / Magic Number)、硬件 P × Q 量价模型与中继门面 SSOT 等价性断言。
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.unit_economics_engine import (
    PipelineAsset,
    BiotechRNPVResult,
    SaaSUnitEconomicsInput,
    SaaSUnitEconomicsResult,
    UnitEconomicsEngine,
)
from finance_tools.unit_economics_engine import (
    PipelineAsset as FacadePipelineAsset,
    BiotechRNPVResult as FacadeBiotechRNPVResult,
    SaaSUnitEconomicsInput as FacadeSaaSUnitEconomicsInput,
    SaaSUnitEconomicsResult as FacadeSaaSUnitEconomicsResult,
    UnitEconomicsEngine as FacadeUnitEconomicsEngine,
)


class TestUnitEconomicsEngine(unittest.TestCase):
    """商业模式微观量价拆解与单体经济量化引擎契约测试."""

    def test_ut_unit_01_biotech_rnpv_probability_weighted_valuation(self):
        """【UT-UNIT-01: 生物制药创新药管线 rNPV 概率加权贴现与每股公允价值断言】

        一、测试功能与测试点:
            验证 UnitEconomicsEngine.calculate_biotech_rnpv 能够针对在研临床管线资产，
            依据临床阶段 (Phase)、成功概率 (POS)、峰值销售额与分成比例，
            准确计算逐年贴现值 (rNPV)，并叠加手头净现金与专有平台清算溢价推导每股公允价值。

        二、正常函数业务边界与参数契约:
            - pipelines: 2 条管线 (Phase 2 POS=0.28, Phase 1 POS=0.10)
            - shares: 250M 股
            - net_cash: 100M
            - platform_base_value: 300M

        三、测试数据与模拟场景说明:
            测试典型 AI 驱动创新药研发企业。

        四、预期断言与结果验证:
            断言 total_pipeline_rnpv > 0。
            断言 rnpv_fair_value_per_share > 0。
            断言 deduction_notes_zh 包含 "概率加权模型" 与 "微观公允价值"。
        """
        p1 = PipelineAsset(
            asset_name="REC-994",
            phase="Phase 2",
            pos=0.28,
            peak_annual_sales=1000.0,
            royalty_take_rate=0.20,
            years_to_peak=6,
            commercial_life_years=10,
        )
        p2 = PipelineAsset(
            asset_name="REC-2282",
            phase="Phase 1",
            pos=0.10,
            peak_annual_sales=500.0,
            royalty_take_rate=0.15,
            years_to_peak=8,
            commercial_life_years=8,
        )

        res = UnitEconomicsEngine.calculate_biotech_rnpv(
            ticker="RXRX",
            shares=250.0,
            net_cash=100.0,
            wacc=0.10,
            pipelines=[p1, p2],
            platform_base_value=300.0,
        )

        self.assertGreater(res.total_pipeline_rnpv, 0.0)
        self.assertGreater(res.rnpv_fair_value_per_share, 1.0)
        self.assertEqual(len(res.asset_breakdowns), 2)
        self.assertIn("概率加权模型", res.deduction_notes_zh)

    def test_ut_unit_02_limited_liability_zero_floor_on_insolvency(self):
        """【UT-UNIT-02: 资不抵债极端场景有限责任公允价值下界归零防御断言】

        一、测试功能与测试点:
            验证金融有限责任防御：当企业巨额净负债大于在研管线折现总现值与技术平台资产之和时
            (即权益总价值为负)，系统不推导出荒谬的负数每股公允价值，
            而是根据有限责任原则刚性锁定股价下界为 $0.00，并在研报中明确揭示破产重组清盘风险。

        二、正常函数业务边界与参数契约:
            - net_cash: -800.0M (巨额负债)
            - total_pipe_val + platform_base_value < 800.0M

        三、测试数据与模拟场景说明:
            测试某濒临清盘的高负债生物制药标的。

        四、预期断言与结果验证:
            断言 rnpv_fair_value_per_share == 0.0 (严禁输出负数股价)。
            断言 deduction_notes_zh 包含 "有限责任约束" 与 "资不抵债与重组清盘风险"。
        """
        p_small = PipelineAsset(
            asset_name="FAILED_PIPELINE",
            phase="Phase 1",
            pos=0.05,
            peak_annual_sales=100.0,
            royalty_take_rate=0.10,
            years_to_peak=8,
        )

        res = UnitEconomicsEngine.calculate_biotech_rnpv(
            ticker="INSOLVENT_BIO",
            shares=50.0,
            net_cash=-800.0,  # 严重负现金净负债
            wacc=0.12,
            pipelines=[p_small],
            platform_base_value=50.0,
        )

        self.assertEqual(res.rnpv_fair_value_per_share, 0.0)
        self.assertIn("有限责任约束", res.deduction_notes_zh)
        self.assertIn("资不抵债与重组清盘风险", res.deduction_notes_zh)

    def test_ut_unit_03_saas_top_decile_growth_flywheel(self):
        """【UT-UNIT-03: SaaS 顶级现金牛飞轮单体经济学健康度与魔力数字断言】

        一、测试功能与测试点:
            验证 UnitEconomicsEngine.calculate_saas_unit_economics 针对高留存、高毛利的优质 SaaS 企业，
            能精确测算 ARPU、CAC、LTV/CAC 比例、CAC 回收期月数及 Magic Number，
            并准确判定为 "优秀现金牛飞轮 (Top Decile)"。

        二、正常函数业务边界与参数契约:
            - arr: 120M
            - ending_customers: 2400 (ARPU = $50,000)
            - nrr: 125.0%
            - gross_margin: 80.0%
            - cac_spend: 30M, new_customers: 600 (CAC = $50,000)
            - net_new_arr: 35M (Magic Number = 35 / 30 = 1.17)

        三、测试数据与模拟场景说明:
            顶级中大型 SaaS 软件标的。

        四、预期断言与结果验证:
            断言 ltv_cac_ratio >= 4.0。
            断言 cac_payback_months <= 15.0。
            断言 health_grade 包含 "优秀现金牛飞轮" 与 "Top Decile"。
            断言 verdict_zh 包含 "SaaS 增长飞轮标的"。
        """
        inp = SaaSUnitEconomicsInput(
            ticker="SAAS_STAR",
            arr_millions=120.0,
            ending_customers_count=2400,
            nrr_pct=125.0,
            gross_margin_pct=80.0,
            cac_spend_millions=30.0,
            new_customers_added=600,
            net_new_arr_millions=35.0,
        )
        res = UnitEconomicsEngine.calculate_saas_unit_economics(inp)

        self.assertEqual(res.arpu_dollars, 50000.0)
        self.assertEqual(res.cac_per_customer_dollars, 50000.0)
        self.assertGreaterEqual(res.ltv_cac_ratio, 4.0)
        self.assertLessEqual(res.cac_payback_months, 15.0)
        self.assertGreater(res.magic_number, 1.0)
        self.assertIn("优秀现金牛飞轮", res.health_grade)
        self.assertIn("SaaS 增长飞轮标的", res.verdict_zh)

    def test_ut_unit_04_saas_inefficient_burn_warning(self):
        """【UT-UNIT-04: SaaS 严重失血与高获客成本烧钱警报断言】

        一、测试功能与测试点:
            验证在客户流失严重 (NRR < 90%) 且获客成本极高 (CAC 回收期 > 24 个月) 时，
            系统发出 "烧钱失血警报 (Inefficient Burn)"，提示价值毁灭风险。

        二、正常函数业务边界与参数契约:
            - nrr_pct: 88.0%
            - cac_spend 庞大，新增客户少

        三、测试数据与模拟场景说明:
            测试失血型伪 SaaS 企业。

        四、预期断言与结果验证:
            断言 cac_payback_months > 24.0。
            断言 health_grade 包含 "烧钱失血警报"。
            断言 verdict_zh 包含 "价值毁灭风险"。
        """
        inp = SaaSUnitEconomicsInput(
            ticker="BLEEDING_SAAS",
            arr_millions=50.0,
            ending_customers_count=5000,  # ARPU = $10,000
            nrr_pct=88.0,
            gross_margin_pct=60.0,
            cac_spend_millions=40.0,
            new_customers_added=1000,     # CAC = $40,000
            net_new_arr_millions=5.0,
        )
        res = UnitEconomicsEngine.calculate_saas_unit_economics(inp)

        self.assertGreater(res.cac_payback_months, 24.0)
        self.assertIn("烧钱失血警报", res.health_grade)
        self.assertIn("价值毁灭风险", res.verdict_zh)

    def test_ut_unit_05_hardware_volume_price_breakdown(self):
        """【UT-UNIT-05: 硬件与消费电子 P × Q 量价拆解与综合毛利加权断言】

        一、测试功能与测试点:
            验证 UnitEconomicsEngine.calculate_hardware_volume_price 能按出货量 (Volume)
            与平均售价 (ASP) 拆解分部业务，并防御输入负数脏数据。

        二、正常函数业务边界与参数契约:
            - segments: [{"segment": "Phone", "volume_m": 200, "asp": 800, "bom_cost": 400}]

        三、测试数据与模拟场景说明:
            模拟消费电子巨头硬件业务线拆解。

        四、预期断言与结果验证:
            断言 total_revenue 包含 "$160,000.0M"。
            断言 blended_gross_margin 包含 "50.0%"。
        """
        segments = [
            {"segment": "Phone", "volume_m": 200.0, "asp": 800.0, "bom_cost": 400.0},
            {"segment": "Tablet", "volume_m": 50.0, "asp": 600.0, "bom_cost": 360.0},
        ]
        res = UnitEconomicsEngine.calculate_hardware_volume_price(segments, shares=1000.0)

        self.assertIn("190,000.0M", res["total_revenue"])
        self.assertIn("48.4%", res["blended_gross_margin"])
        self.assertEqual(len(res["segments_breakdown"]), 2)

    def test_ut_unit_06_facade_and_core_ssot_equivalence(self):
        """【UT-UNIT-06: 向下兼容中继门面 SSOT 完全等价性断言】

        一、测试功能与测试点:
            验证 `finance_tools.unit_economics_engine` 中继门面与底层核心
            `financial_core.engines.unit_economics_engine` 输出 100% 相同。

        二、正常函数业务边界与参数契约:
            - Facade 与 Core 传入相同输入。

        三、测试数据与模拟场景说明:
            测试标准 SaaS 输入。

        四、预期断言与结果验证:
            断言门面与核心输出属性完全一致。
        """
        inp_core = SaaSUnitEconomicsInput(
            ticker="COMPARE",
            arr_millions=80.0,
            ending_customers_count=1600,
            nrr_pct=118.0,
            gross_margin_pct=75.0,
            cac_spend_millions=20.0,
            new_customers_added=400,
            net_new_arr_millions=25.0,
        )
        inp_facade = FacadeSaaSUnitEconomicsInput(
            ticker="COMPARE",
            arr_millions=80.0,
            ending_customers_count=1600,
            nrr_pct=118.0,
            gross_margin_pct=75.0,
            cac_spend_millions=20.0,
            new_customers_added=400,
            net_new_arr_millions=25.0,
        )

        res_core = UnitEconomicsEngine.calculate_saas_unit_economics(inp_core)
        res_facade = FacadeUnitEconomicsEngine.calculate_saas_unit_economics(inp_facade)

        self.assertEqual(res_core.arpu_dollars, res_facade.arpu_dollars)
        self.assertEqual(res_core.ltv_cac_ratio, res_facade.ltv_cac_ratio)
        self.assertEqual(res_core.health_grade, res_facade.health_grade)
        self.assertEqual(res_core.verdict_zh, res_facade.verdict_zh)

    def test_ut_unit_07_buyer_dossier_card_and_to_dict_contract(self):
        """【UT-UNIT-07: 单位经济量化全息研报卡片与 to_dict 序列化契约断言】

        一、测试功能与测试点:
            1. 验证 BiotechRNPVResult 具备 narrative_zh 并在 to_dict() 中完整暴露；
            2. 验证 SaaSUnitEconomicsResult 具备 narrative_zh 并在 to_dict() 中完整暴露；
            3. 验证 calculate_hardware_volume_price 输出包含 narrative_zh 全息研报。

        二、正常函数业务边界与参数契约:
            - 各函数返回结果契约完备。

        三、测试数据与模拟场景说明:
            测试标准创新药、SaaS 与硬件输入。

        四、预期断言与结果验证:
            断言 narrative_zh 非空且符合中文买方直觉叙述规范。
        """
        # 1. 创新药 rNPV
        p = PipelineAsset("P1", "Phase 2", 0.30, 800.0, 0.15, 5)
        res_bio = UnitEconomicsEngine.calculate_biotech_rnpv("BIO", 100.0, 50.0, 0.10, [p], 100.0)
        self.assertIn("创新药管线 rNPV 估值全息研报", res_bio.narrative_zh)
        self.assertIn("narrative_zh", res_bio.to_dict())

        # 2. SaaS 单元经济学
        inp_saas = SaaSUnitEconomicsInput("SAAS", 100.0, 2000, 120.0, 80.0, 25.0, 500, 30.0)
        res_saas = UnitEconomicsEngine.calculate_saas_unit_economics(inp_saas)
        self.assertIn("SaaS 与云服务微观单体经济全息研报", res_saas.narrative_zh)
        self.assertNotIn("(Top Decile /", res_saas.narrative_zh)
        self.assertEqual(res_saas.health_grade_zh, "优秀现金牛飞轮 (极高客户忠诚度与获客杠杆)")
        self.assertIn("narrative_zh", res_saas.to_dict())
        self.assertIn("health_grade_zh", res_saas.to_dict())

        # 3. 硬件 P x Q
        segs = [{"segment": "Device", "volume_m": 10.0, "asp": 500.0, "bom_cost": 250.0}]
        res_hw = UnitEconomicsEngine.calculate_hardware_volume_price(segs, 100.0)
        self.assertIn("narrative_zh", res_hw)
        self.assertIn("P×Q 微观量价拆解研报", res_hw["narrative_zh"])


if __name__ == "__main__":
    unittest.main()
