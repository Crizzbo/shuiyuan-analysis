"""阿吉翁创造性破坏与技术前沿引擎 (Aghion Creative Destruction & Technology Frontier Engine).

理论来源与微观基础：
菲利普·阿吉翁 (Philippe Aghion)、彼得·豪伊特 (Peter Howitt)、乔尔·莫基尔 (Joel Mokyr, 2025年诺贝尔经济学奖得主) 经典理论：
1. 创造性破坏与内生增长模型 (Creative Destruction & Schumpeterian Growth):
   技术前沿进步驱动长波繁荣，而陈旧生产力在宏观紧缩中被不可逆地替代出清。
2. 距离技术前沿距离 (Distance to Technology Frontier, DTF):
   处于技术前沿 (DTF 近 1.0) 的企业在危机中享受“熊彼特幸存者溢价 (Survivor Premium)”，
   通过吞噬破产落后对手的市场份额实现逆周期扩张；
   而远离前沿且负债沉重的僵尸产能 (Zombie Firms) 则面临被创造性破坏淘汰的高危风险。
"""

from dataclasses import dataclass
import math
from typing import Dict, Any, Optional


@dataclass
class AghionDestructionInput:
    """阿吉翁创造性破坏输入."""
    rd_expenses: float                      # 研发费用 R&D Expenses
    reported_revenue: float                 # 营业收入
    industry_max_rd_intensity_pct: float    # 行业最高研发强度 % (如半导体行业 20.0%)
    patent_portfolio_quality_score: float   # 专利技术护城河评分 [0.0, 100.0]
    total_debt_to_ebitda: float             # 债务杠杆倍数 Debt / EBITDA
    operating_cash_flow: float              # 经营活动现金流
    capital_expenditures: float             # 资本开支 Capex
    is_disruptive_innovator: bool = False   # 是否具备颠覆式底层技术创新架构 (如 GPU算力/mRNA/EUV)


@dataclass
class AghionDestructionResult:
    """阿吉翁创造性破坏评估输出."""
    distance_to_technology_frontier: float  # 距离行业技术前沿得分 DTF [0.0, 1.0] (1.0=世界前沿领跑者)
    schumpeterian_survival_status: str      # "FRONTIER_LEADER" / "ADAPTIVE_FOLLOWER" / "CREATIVE_DESTRUCTION_VULNERABLE"
    terminal_growth_adjustment_bps: float   # 熊彼特长周期终值增长率调整基点 (-100 ~ +100 bps)
    market_share_consolidation_multiplier: float # 逆周期市场份额集中乘数 (如 1.15 表示危机后市占率提升 15%)
    zombie_creative_destruction_risk_pct: float # 被创造性破坏加速淘汰的概率 %
    schumpeterian_verdict: str              # 熊彼特创造性破坏深度研判结论
    schumpeterian_survival_status_zh: str = "" # 熊彼特生存状态自然中文命名
    narrative_zh: str = ""                  # 买方通俗全息研报卡片 (去工程符号化)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "distance_to_technology_frontier": self.distance_to_technology_frontier,
            "schumpeterian_survival_status": self.schumpeterian_survival_status,
            "schumpeterian_survival_status_zh": self.schumpeterian_survival_status_zh or self.schumpeterian_survival_status,
            "terminal_growth_adjustment_bps": f"{self.terminal_growth_adjustment_bps:+.0f} bps",
            "market_share_consolidation_multiplier": f"{self.market_share_consolidation_multiplier:.2f}x",
            "zombie_creative_destruction_risk_pct": f"{self.zombie_creative_destruction_risk_pct:.1f}%",
            "verdict": self.schumpeterian_verdict,
            "narrative_zh": self.narrative_zh or self.schumpeterian_verdict,
        }


class AghionCreativeDestructionEngine:
    """阿吉翁创造性破坏与技术前沿引擎."""

    def __init__(self):
        self.version = "1.0.0"

    def evaluate(self, inp: AghionDestructionInput) -> AghionDestructionResult:
        """评估企业技术前沿距离、出清淘汰风险与熊彼特幸存者估值调整."""
        # 1. 研发强度与技术前沿距离 (Distance to Technology Frontier, DTF)
        rev_safe = max(1.0, inp.reported_revenue)
        company_rd_intensity = (max(0.0, inp.rd_expenses) / rev_safe) * 100.0
        max_rd_safe = max(1.0, inp.industry_max_rd_intensity_pct)

        # 研发投入相对比重 [0.0, 1.0]
        rd_frontier_ratio = min(1.0, company_rd_intensity / max_rd_safe)

        # 专利质量权重 [0.0, 1.0]
        patent_quality_ratio = max(0.0, min(100.0, inp.patent_portfolio_quality_score)) / 100.0

        # 综合 DTF 计算: 60% 专利质量 + 40% 研发投入比重 (若为颠覆式创新者有加成)
        dtf_raw = 0.60 * patent_quality_ratio + 0.40 * rd_frontier_ratio
        if inp.is_disruptive_innovator:
            dtf_raw = min(1.0, dtf_raw * 1.25)

        dtf = round(max(0.05, min(1.0, dtf_raw)), 3)

        # 2. 僵尸产能与被破坏淘汰风险 (Zombie Vulnerability)
        # 债务高企 (Debt/EBITDA > 4.5) 且远离技术前沿 (DTF < 0.40) 的企业在宏观加息出清周期极度脆弱
        fcf = inp.operating_cash_flow - inp.capital_expenditures
        leverage = max(0.0, inp.total_debt_to_ebitda)

        zombie_score = 0.0
        if dtf < 0.40:
            zombie_score += (0.40 - dtf) * 100.0 # 前沿距离落后计分
        if leverage > 3.5:
            zombie_score += min(50.0, (leverage - 3.5) * 15.0) # 杠杆压力计分
        if fcf < 0:
            zombie_score += 20.0 # 烧钱不能自给计分

        zombie_risk_pct = round(max(0.0, min(95.0, zombie_score)), 1)

        # 3. 幸存者状态与长周期终值增长率调整 (Terminal Growth Adjustment)
        if dtf >= 0.80 and fcf > 0:
            status = "FRONTIER_LEADER"
            status_zh = "行业技术前沿领跑者"
            # 前沿领跑者: 危机带来更强的行业整合与定价权，终值增长率上调 50~100 bps
            terminal_adj_bps = round(min(100.0, (dtf - 0.70) * 300.0), 1)
            consolidation_multiplier = round(1.0 + (dtf - 0.70) * 0.50, 2)
        elif zombie_risk_pct >= 50.0:
            status = "CREATIVE_DESTRUCTION_VULNERABLE"
            status_zh = "技术替代与负债出清高危型"
            # 淘汰高危型: 面临技术替代与债务违约出清，终值增长率惩罚性下调
            terminal_adj_bps = round(-min(200.0, zombie_risk_pct * 2.0), 1)
            consolidation_multiplier = 0.75 # 市场份额预期被蚕食
        else:
            status = "ADAPTIVE_FOLLOWER"
            status_zh = "中坚梯队技术跟随者"
            terminal_adj_bps = 0.0
            consolidation_multiplier = 1.00

        # 4. 研判定性总结 (纯自然中文语义，消除英文代号暴露)
        verdict = (
            f"技术前沿距离为 {dtf:.2f} ({status_zh})；"
            f"研发强度 {company_rd_intensity:.1f}% (行业标杆 {max_rd_safe:.1f}%)，专利质量分 {inp.patent_portfolio_quality_score:.0f}；"
            f"创造性破坏淘汰风险 {zombie_risk_pct:.1f}%；"
            f"熊彼特市场整合乘数 {consolidation_multiplier:.2f} 倍，"
            f"长期终值增长率调整 {terminal_adj_bps:+.0f} 基点。"
        )

        # 5. 买方通俗全息研报卡片 (去工程符号化)
        narrative_zh = (
            f"【熊彼特创造性破坏与技术前沿全息研判】"
            f"行业技术竞争位势【{status_zh}】(距离技术前沿度 {dtf:.2f}/1.00)。"
            f"研发与专利护城河: 企业研发强度 {company_rd_intensity:.1f}% (行业顶尖标杆 {max_rd_safe:.1f}%)，"
            f"底层专利质量评分 {inp.patent_portfolio_quality_score:.0f}/100。"
            f"产业出清淘汰风险: 创造性破坏加速淘汰概率 {zombie_risk_pct:.1f}%。"
            f"买方终值折现修正: 逆周期行业份额整合乘数 {consolidation_multiplier:.2f}倍，"
            f"长期永续增长率调整 {terminal_adj_bps:+.0f} 基点。"
        )

        return AghionDestructionResult(
            distance_to_technology_frontier=dtf,
            schumpeterian_survival_status=status,
            terminal_growth_adjustment_bps=terminal_adj_bps,
            market_share_consolidation_multiplier=consolidation_multiplier,
            zombie_creative_destruction_risk_pct=zombie_risk_pct,
            schumpeterian_verdict=verdict,
            schumpeterian_survival_status_zh=status_zh,
            narrative_zh=narrative_zh,
        )
