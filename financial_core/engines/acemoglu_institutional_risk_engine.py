"""阿西莫格鲁制度风险与主权治理溢价引擎 (Acemoglu Institutional Risk & Governance Engine).

理论来源与微观基础：
达隆·阿西莫格鲁 (Daron Acemoglu)、西蒙·约翰逊 (Simon Johnson)、詹姆斯·罗宾逊 (James A. Robinson, 2024年诺贝尔经济学奖得主) 经典理论：
1. 包容性制度 vs 掠夺性制度 (Inclusive vs Extractive Institutions):
   产权界定、法治约束与契约执行效率决定了长期经济繁荣与资本投资回报率的下界。
2. 制度持久性与逆转风险 (Institutional Persistence & Risk Premium):
   处于制度摩擦、产权保护薄弱或监管干预频发环境中的企业，其股权估值必须内生扣减
   “制度与主权法治风险利差 (Institutional Risk Spread)”。
3. 跨国长臂管辖与实体清单脱钩暴露 (Cross-Border Jurisdictional Sanctions):
   涉足跨国技术封锁、实体清单及资本管制的企业，承担不可忽视的尾部资产剥离与流动性折价。
"""

from dataclasses import dataclass
import math
from typing import Dict, Any, Optional, List


@dataclass
class AcemogluInstitutionalInput:
    """阿西莫格鲁制度风险输入."""
    country_domicile: str                   # 注册地/运营主权体 (例如 "US", "JP", "CN", "SG", "EM")
    rule_of_law_score: float                # 法治与司法独立评分 [0.0, 100.0] (如 US/JP 约 85~90, EM 约 40~60)
    property_rights_security: float         # 产权私有保护指数 [0.0, 100.0]
    regulatory_predictability: float        # 监管可预期性评分 [0.0, 100.0] (排斥突发突变式干预)
    corruption_control_score: float         # 廉洁度与反寻租评分 [0.0, 100.0]

    # 地缘与跨国管辖风险
    cross_border_sanction_exposure: bool = False # 是否存在跨国制裁、实体清单或长臂技术封锁风险
    offshore_revenue_share_pct: float = 30.0     # 跨国海外收入占比 % (如 30%)
    sensitive_technology_sector: bool = False    # 是否属于地缘敏感核心科技/国防安全领域 (半导体/AI/稀缺资源)
    geopolitical_tension_index: float = 40.0     # 全球地缘政治紧张指数 [0, 100] (0=和平, 100=极端地缘摩擦)


@dataclass
class AcemogluInstitutionalResult:
    """阿西莫格鲁制度风险评估输出."""
    institutional_quality_index: float       # 综合制度质量指数 (0~100)
    institution_type: str                    # INCLUSIVE_STRONG (强包容性) / MODERATE_TRANSITIONAL (过渡型) / EXTRACTIVE_RISK (掠夺脆弱型)
    institutional_risk_spread_bps: float     # 制度与产权风险附加利差 (基点，叠加至 WACC/折现率)
    terminal_value_governance_haircut_pct: float # 终值制度风险折价率 % (用于防御长期产权不确定性)
    cross_border_vulnerability_score: float  # 跨国地缘管辖脆弱性得分 (0~100)
    institutional_verdict: str               # 制度经济学深度分析结论
    institution_type_zh: str = ""            # 制度类型通俗中文语义命名
    narrative_zh: str = ""                   # 买方通俗全息研报卡片 (去工程符号化)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "institutional_quality_index": self.institutional_quality_index,
            "institution_type": self.institution_type,
            "institution_type_zh": self.institution_type_zh or self.institution_type,
            "institutional_risk_spread_bps": self.institutional_risk_spread_bps,
            "terminal_value_governance_haircut_pct": f"{self.terminal_value_governance_haircut_pct:.1f}%",
            "cross_border_vulnerability_score": self.cross_border_vulnerability_score,
            "verdict": self.institutional_verdict,
            "narrative_zh": self.narrative_zh or self.institutional_verdict,
        }


class AcemogluInstitutionalRiskEngine:
    """阿西莫格鲁制度与主权法治风险引擎."""

    def __init__(self):
        self.version = "1.0.0"

    def evaluate(self, inp: AcemogluInstitutionalInput) -> AcemogluInstitutionalResult:
        """评估产权保护、法治完备度、长臂管辖暴露及内生制度风险利差."""
        # 1. 综合制度质量指数 (Institutional Quality Index, IQI)
        # 加权合成: 产权 35%, 法治 30%, 监管预期 20%, 廉洁 15%
        p_rights = max(0.0, min(100.0, inp.property_rights_security))
        rol = max(0.0, min(100.0, inp.rule_of_law_score))
        reg = max(0.0, min(100.0, inp.regulatory_predictability))
        corr = max(0.0, min(100.0, inp.corruption_control_score))

        iqi = round(0.35 * p_rights + 0.30 * rol + 0.20 * reg + 0.15 * corr, 2)

        # 制度类型定性判定
        if iqi >= 80.0:
            inst_type = "INCLUSIVE_STRONG" # 强包容性法治制度
            inst_type_zh = "高度包容法治安全型"
        elif iqi >= 55.0:
            inst_type = "MODERATE_TRANSITIONAL" # 中度法治与监管过渡体系
            inst_type_zh = "中度法治监管过渡型"
        else:
            inst_type = "EXTRACTIVE_RISK" # 制度掠夺性与政策突变风险较高
            inst_type_zh = "制度掠夺与政策突变高危型"

        # 2. 跨国地缘长臂管辖脆弱性得分 (Cross-Border Vulnerability)
        base_geo = max(0.0, min(100.0, inp.geopolitical_tension_index))
        offshore_share = max(0.0, min(100.0, inp.offshore_revenue_share_pct)) / 100.0

        geo_multiplier = 1.0
        if inp.sensitive_technology_sector:
            geo_multiplier += 0.50 # 敏感科技提升 50% 脆弱性
        if inp.cross_border_sanction_exposure:
            geo_multiplier += 1.00 # 实体清单直接提升 100% 脆弱性

        cross_border_score = round(min(100.0, (base_geo * 0.50 + offshore_share * 50.0) * geo_multiplier), 1)

        # 3. 制度与法治风险利差 (Institutional Risk Spread, bps)
        # 基准: 制度缺口 = (100 - IQI)
        # 每落后 10 分制度质量，内生要求 35 bps 风险利差，叠加跨国地缘敞口
        base_inst_spread = (100.0 - iqi) * 3.5
        geo_spread = (cross_border_score / 100.0) * 120.0
        total_inst_spread_bps = round(max(0.0, base_inst_spread + geo_spread), 1)

        # 4. 终值制度折价率 (Terminal Value Governance Haircut %)
        # 产权薄弱环境下，超长远期 (10年以后) 的现金流面临潜在政策重构风险
        if iqi >= 85.0 and not inp.cross_border_sanction_exposure:
            tv_haircut_pct = 0.0 # 顶级法治体系无终值折价
        else:
            tv_haircut_pct = round(min(30.0, ((100.0 - iqi) * 0.25 + (cross_border_score * 0.15))), 1)

        # 5. 制度研判总结 (纯自然中文语义，消除英文代号暴露)
        verdict = (
            f"制度质量指数 IQI={iqi:.1f} ({inst_type_zh})；"
            f"主权法治得分 {rol:.1f}，产权安全度 {p_rights:.1f}；"
            f"跨国管辖脆弱度 {cross_border_score:.1f} (地缘利差 +{geo_spread:.0f} bps)；"
            f"合计要求制度风险补偿利差 +{total_inst_spread_bps:.0f} bps，"
            f"长周期终值资本折价率 {tv_haircut_pct:.1f}%。"
        )

        # 6. 生成买方通俗全息研报卡片 (去工程符号化)
        narrative_zh = (
            f"【主权治理与制度法治风险全息研判】"
            f"主权制度质量评级【{inst_type_zh}】(制度综合评分 {iqi:.1f}/100)。"
            f"基础法治架构: 司法独立与法治得分 {rol:.1f}，私人产权安全度 {p_rights:.1f}，监管政策透明度 {reg:.1f}。"
            f"跨国地缘敞口: 长臂管辖脆弱度 {cross_border_score:.1f}/100，内生要求附加地缘利差 +{geo_spread:.0f} 基点。"
            f"买方折现率要求: 制度与主权法治合计要求额外贴现补偿 +{total_inst_spread_bps:.0f} 基点；"
            f"远期终值产权不确定性折价 {tv_haircut_pct:.1f}%。"
        )

        return AcemogluInstitutionalResult(
            institutional_quality_index=iqi,
            institution_type=inst_type,
            institutional_risk_spread_bps=total_inst_spread_bps,
            terminal_value_governance_haircut_pct=tv_haircut_pct,
            cross_border_vulnerability_score=cross_border_score,
            institutional_verdict=verdict,
            institution_type_zh=inst_type_zh,
            narrative_zh=narrative_zh,
        )
