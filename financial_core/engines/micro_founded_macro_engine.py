"""微观基础宏观综合评估引擎 (Micro-Founded Macro Composite Engine).

将伍德福德前瞻指引 (Woodford)、霍尔加成率成本摩擦 (Hall)、阿西莫格鲁制度风险 (Acemoglu)
与阿吉翁创造性破坏 (Aghion) 四大诺奖级微观基础理论有机熔铸为一体，
为系统性分析管道 Stage 3 提供买方机构级内生宏观加压与动态折现结构。
"""

from dataclasses import dataclass, field
import math
from typing import Dict, Any, List, Optional

from .woodford_forward_guidance_engine import (
    WoodfordForwardGuidanceEngine,
    WoodfordGuidanceInput,
    WoodfordGuidanceResult,
)
from .hall_discount_friction_engine import (
    HallDiscountFrictionEngine,
    HallFrictionInput,
    HallFrictionResult,
)
from .acemoglu_institutional_risk_engine import (
    AcemogluInstitutionalRiskEngine,
    AcemogluInstitutionalInput,
    AcemogluInstitutionalResult,
)
from .aghion_creative_destruction_engine import (
    AghionCreativeDestructionEngine,
    AghionDestructionInput,
    AghionDestructionResult,
)


@dataclass
class MicroFoundedMacroInput:
    """微观基础宏观综合输入数据模型."""
    ticker: str
    country_domicile: str = "US"            # 标的主体注册地
    sector: str = "General"

    # 1. 宏观货币与利率参数 (Woodford)
    policy_rate: float = 0.050              # 当期政策利率 (如 5.0%)
    expected_inflation_1y: float = 0.025    # 1年期通胀预期 (如 2.5%)
    natural_rate_r_star: float = 0.0125      # 维克塞尔自然利率 r* (如 1.25%)
    equity_beta: float = 1.0                # 股权 Beta
    equity_risk_premium: float = 0.055       # 股权风险溢价 ERP
    credit_spread: float = 0.0180           # 信用违约利差 (如 180 bps)
    tax_rate: float = 0.21                  # 企业税率
    dot_plot_rate_path: Optional[List[float]] = None

    # 2. 微观财务与成本摩擦参数 (Hall)
    reported_revenue: float = 1000.0        # 营业收入
    reported_cogs: float = 550.0            # 营业成本
    reported_gross_margin_pct: float = 45.0 # 毛利率 %
    reported_capex: float = 80.0            # 资本开支
    cash_and_equivalents: float = 200.0     # 现金储备
    total_debt: float = 150.0               # 有息负债
    annual_fcf: float = 100.0               # 自由现金流
    commodity_input_inflation_pct: float = 4.0 # 原材料/外购通胀 %
    unit_labor_cost_inflation_pct: float = 3.5 # 单位劳动力成本 ULC 通胀 %
    macro_vix: float = 20.0                 # VIX 不确定性
    pricing_pass_through_elasticity: float = 0.70 # 价格转嫁弹性 [0, 1]

    # 3. 制度与主权法治参数 (Acemoglu)
    rule_of_law_score: float = 85.0         # 法治评分 [0, 100]
    property_rights_security: float = 85.0  # 产权安全指数 [0, 100]
    regulatory_predictability: float = 80.0 # 监管可预期性 [0, 100]
    corruption_control_score: float = 80.0  # 廉洁指数 [0, 100]
    cross_border_sanction_exposure: bool = False # 实体清单/技术管制
    offshore_revenue_share_pct: float = 30.0# 海外跨国收入占比 %
    sensitive_technology_sector: bool = False # 敏感科技领域
    geopolitical_tension_index: float = 35.0# 地缘政治摩擦指数 [0, 100]

    # 4. 创造性破坏与技术前沿 (Aghion)
    rd_expenses: float = 60.0               # 研发投入
    industry_max_rd_intensity_pct: float = 15.0 # 行业顶级研发强度 %
    patent_portfolio_quality_score: float = 75.0 # 专利质量评分 [0, 100]
    total_debt_to_ebitda: float = 1.5       # 债务杠杆倍数
    operating_cash_flow: float = 180.0      # 经营现金流
    is_disruptive_innovator: bool = False   # 是否颠覆式底层技术先锋


@dataclass
class MicroFoundedMacroCompositeResult:
    """微观基础宏观综合评估输出."""
    ticker: str
    woodford_result: WoodfordGuidanceResult
    hall_result: HallFrictionResult
    acemoglu_result: AcemogluInstitutionalResult
    aghion_result: AghionDestructionResult

    # 贯穿至 Stage 4 估值体系的核心综合参数
    effective_initial_wacc_pct: float       # 首期经制度利差校准的真实有效 WACC %
    dynamic_wacc_vector: List[float]        # 包含制度利差的逐年递进折现率向量 [WACC_1, ..., WACC_N]
    shocked_gross_margin_pct: float         # 经成本转嫁摩擦后的承压毛利率 %
    terminal_growth_rate_adj_bps: float     # 经创造性破坏 (Aghion) 调整后的终值增长率基点
    governance_terminal_haircut_pct: float  # 经制度风险 (Acemoglu) 调整后的超长远期折价率 %
    integrated_macro_verdict: str           # 微观基础宏观全景评级总结
    narrative_zh: str = ""                  # 买方通俗全息研报卡片 (彻底去工程符号化)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "effective_initial_wacc_pct": f"{self.effective_initial_wacc_pct:.2f}%",
            "dynamic_wacc_vector": [f"{w * 100:.2f}%" for w in self.dynamic_wacc_vector],
            "shocked_gross_margin_pct": f"{self.shocked_gross_margin_pct:.1f}%",
            "terminal_growth_rate_adj_bps": f"{self.terminal_growth_rate_adj_bps:+.0f} bps",
            "governance_terminal_haircut_pct": f"{self.governance_terminal_haircut_pct:.1f}%",
            "verdict": self.integrated_macro_verdict,
            "narrative_zh": self.narrative_zh or self.integrated_macro_verdict,
            "woodford": self.woodford_result.to_dict(),
            "hall": self.hall_result.to_dict(),
            "acemoglu": self.acemoglu_result.to_dict(),
            "aghion": self.aghion_result.to_dict(),
        }


class MicroFoundedMacroEngine:
    """微观基础宏观综合总装引擎."""

    def __init__(self):
        self.version = "1.0.0"
        self.woodford = WoodfordForwardGuidanceEngine()
        self.hall = HallDiscountFrictionEngine()
        self.acemoglu = AcemogluInstitutionalRiskEngine()
        self.aghion = AghionCreativeDestructionEngine()

    def evaluate(self, inp: MicroFoundedMacroInput) -> MicroFoundedMacroCompositeResult:
        """多维度微观宏观融合评估与折现向量校准."""
        # 1. 运行阿西莫格鲁制度风险引擎，获取内生制度利差
        acemoglu_res = self.acemoglu.evaluate(
            AcemogluInstitutionalInput(
                country_domicile=inp.country_domicile,
                rule_of_law_score=inp.rule_of_law_score,
                property_rights_security=inp.property_rights_security,
                regulatory_predictability=inp.regulatory_predictability,
                corruption_control_score=inp.corruption_control_score,
                cross_border_sanction_exposure=inp.cross_border_sanction_exposure,
                offshore_revenue_share_pct=inp.offshore_revenue_share_pct,
                sensitive_technology_sector=inp.sensitive_technology_sector,
                geopolitical_tension_index=inp.geopolitical_tension_index,
            )
        )
        inst_spread_decimal = acemoglu_res.institutional_risk_spread_bps / 10000.0

        # 2. 运行伍德福德前瞻指引引擎，信用利差融合制度利差
        total_credit_spread = max(0.005, inp.credit_spread + inst_spread_decimal * 0.50)
        debt_to_equity = inp.total_debt / max(1.0, inp.cash_and_equivalents * 2.0)

        woodford_res = self.woodford.evaluate(
            WoodfordGuidanceInput(
                policy_rate=inp.policy_rate,
                expected_inflation_1y=inp.expected_inflation_1y,
                natural_rate_r_star=inp.natural_rate_r_star,
                equity_beta=inp.equity_beta,
                equity_risk_premium=inp.equity_risk_premium,
                debt_to_equity=debt_to_equity,
                credit_spread=total_credit_spread,
                tax_rate=inp.tax_rate,
                dot_plot_rate_path=inp.dot_plot_rate_path,
            )
        )

        # 将制度利差全额注入逐年动态 WACC 向量
        effective_wacc_vector = [
            round(max(0.035, w + inst_spread_decimal * 0.60), 5)
            for w in woodford_res.dynamic_wacc_vector
        ]
        effective_initial_wacc = round(effective_wacc_vector[0] * 100.0, 2)

        # 3. 运行霍尔成本摩擦与加成率引擎
        hall_res = self.hall.evaluate(
            HallFrictionInput(
                reported_revenue=inp.reported_revenue,
                reported_cogs=inp.reported_cogs,
                reported_gross_margin_pct=inp.reported_gross_margin_pct,
                reported_capex=inp.reported_capex,
                cash_and_equivalents=inp.cash_and_equivalents,
                total_debt=inp.total_debt,
                annual_fcf=inp.annual_fcf,
                commodity_input_inflation_pct=inp.commodity_input_inflation_pct,
                unit_labor_cost_inflation_pct=inp.unit_labor_cost_inflation_pct,
                macro_vix_volatility=inp.macro_vix,
                pricing_pass_through_elasticity=inp.pricing_pass_through_elasticity,
            )
        )

        # 4. 运行阿吉翁创造性破坏与技术前沿引擎
        aghion_res = self.aghion.evaluate(
            AghionDestructionInput(
                rd_expenses=inp.rd_expenses,
                reported_revenue=inp.reported_revenue,
                industry_max_rd_intensity_pct=inp.industry_max_rd_intensity_pct,
                patent_portfolio_quality_score=inp.patent_portfolio_quality_score,
                total_debt_to_ebitda=inp.total_debt_to_ebitda,
                operating_cash_flow=inp.operating_cash_flow,
                capital_expenditures=inp.reported_capex,
                is_disruptive_innovator=inp.is_disruptive_innovator,
            )
        )

        # 5. 综合微观宏观顶层研判 (双轨兼容: 技术代号保持向前兼容，同时补充自然语义)
        integrated_verdict = (
            f"【微观基础宏观全景】"
            f"1. 货币政策立场: {woodford_res.monetary_stance_summary} "
            f"首期折现率 WACC(t1)={effective_initial_wacc:.2f}% (含制度利差 +{acemoglu_res.institutional_risk_spread_bps:.0f} bps)；"
            f"2. 微观成本转嫁: 加成率 μ={hall_res.micro_markup_ratio:.2f} ({hall_res.pricing_power_tier} / {hall_res.pricing_power_tier_zh})，"
            f"毛利率受摩擦调整为 {hall_res.shocked_gross_margin_pct:.1f}%；"
            f"3. 制度与法治环境: {acemoglu_res.institution_type} / {acemoglu_res.institution_type_zh} (IQI={acemoglu_res.institutional_quality_index:.1f})，"
            f"终值制度折价率 {acemoglu_res.terminal_value_governance_haircut_pct:.1f}%；"
            f"4. 创造性破坏地位: {aghion_res.schumpeterian_survival_status} / {aghion_res.schumpeterian_survival_status_zh} (DTF={aghion_res.distance_to_technology_frontier:.2f})，"
            f"终值增长率调整 {aghion_res.terminal_growth_adjustment_bps:+.0f} bps。"
        )

        # 6. 买方通俗全息研报卡片 (彻底去工程符号化)
        narrative_zh = (
            f"【标的 {inp.ticker} 宏观传导与制度护城河全息研报】"
            f"货币与折现中枢: 货币政策定性属于【{woodford_res.monetary_stance_zh}】(维克塞尔利率缺口 {woodford_res.wicksellian_rate_gap_bps:+.0f} 基点)，"
            f"第1年有效折现率 WACC 为 {effective_initial_wacc:.2f}% (已内生吸收制度风险利差 +{acemoglu_res.institutional_risk_spread_bps:.0f} 基点)。"
            f"微观成本摩擦防御: 定价权定性为【{hall_res.pricing_power_tier_zh}】(价格-成本加成率 μ={hall_res.micro_markup_ratio:.2f}倍)，"
            f"承压后毛利率预测为 {hall_res.shocked_gross_margin_pct:.1f}%。"
            f"主权法治与地缘治理: 主权制度环境属于【{acemoglu_res.institution_type_zh}】(制度综合质量评分 {acemoglu_res.institutional_quality_index:.1f}/100)，"
            f"远期终值产权治理折价 {acemoglu_res.terminal_value_governance_haircut_pct:.1f}%。"
            f"技术创新与熊彼特出清: 行业技术竞争地位属于【{aghion_res.schumpeterian_survival_status_zh}】(距离技术前沿度 {aghion_res.distance_to_technology_frontier:.2f}/1.00)，"
            f"长期永续增长率调整 {aghion_res.terminal_growth_adjustment_bps:+.0f} 基点。"
        )

        return MicroFoundedMacroCompositeResult(
            ticker=inp.ticker,
            woodford_result=woodford_res,
            hall_result=hall_res,
            acemoglu_result=acemoglu_res,
            aghion_result=aghion_res,
            effective_initial_wacc_pct=effective_initial_wacc,
            dynamic_wacc_vector=effective_wacc_vector,
            shocked_gross_margin_pct=hall_res.shocked_gross_margin_pct,
            terminal_growth_rate_adj_bps=aghion_res.terminal_growth_adjustment_bps,
            governance_terminal_haircut_pct=acemoglu_res.terminal_value_governance_haircut_pct,
            integrated_macro_verdict=integrated_verdict,
            narrative_zh=narrative_zh,
        )
