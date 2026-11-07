"""突发事件微观事实与多业务分部 (SOTP) 穿透引擎.

本引擎专责实现用户核心投资哲学：
企业不是抽象单一行业，而是多个独立业务分部 (Business Segments) 的有机组合体。
突发事件 (地缘政治、各州法规、化工厂爆炸、断网封锁) 精准打击于特定业务分部。
引擎对标官方 10-K / 20-F 分部报告，执行分部暴露度测算、库存缓冲吸收、转嫁能力冲销
与企业级总体财务账本 (ΔEBIT / ΔEPS / DCF 折现估值) 刚性平账加总。

架构规则：
- 属于 financial_core 核心计算层；
- 零外层依赖，零外部逆向 import，纯相对导入；
- 具备平账自检与除零保护。
"""

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple

from .event_radar_engine import StructuredEventSummary


@dataclass
class BusinessSegment:
    """企业官方分部报告主营业务分部单元 (Segment Unit)."""
    segment_id: str
    name_zh: str
    name_en: str
    revenue: float  # 单位：百万美元 (USD Millions)
    revenue_weight: float  # 占总营收权重 (0.0 ~ 1.0)
    operating_margin: float  # 分部营运利润率 (如 0.42 代表 42%)
    operating_income: float  # 分部营运利润 (EBIT)
    cost_pass_through_power: float  # 成本转嫁与议价权 (0.0 无转嫁 ~ 1.0 完全转嫁)
    inventory_buffer_days: float  # 分部供应链库存缓冲周转天数 (DIO)
    relevant_keywords: List[str] = field(default_factory=list)  # 分部业务关联实体与特征词


@dataclass
class CompanySotpProfile:
    """企业级分部加总 (SOTP) 完整底账档案."""
    ticker: str
    company_name: str
    fiscal_year: str
    total_revenue: float  # 百万美元
    total_operating_income: float  # 百万美元
    effective_tax_rate: float  # 有效所得税率 (如 0.15)
    diluted_shares: float  # 稀释总股本 (百万股)
    current_share_price: float  # 当前股价 (USD)
    segments: List[BusinessSegment]
    unallocated_operating_income: float = 0.0
    source_refs: Dict[str, Any] = field(default_factory=dict)
    assumption_id: str = ""
    assumption_rationale: str = ""
    assumption_status: str = "uncalibrated_scenario"
    quote_timestamp: str = ""
    quote_session: str = ""
    data_origin: str = "synthetic"
    evidence_status: str = "unverified"

    def verify_balance_sheet_invariants(self) -> Tuple[bool, str]:
        """刚性平账自检：验证各分部营收之和与权重之和是否平账."""
        if not self.segments:
            return False, "分部列表为空，无法平账"
        numeric_fields = (
            self.total_revenue, self.total_operating_income, self.effective_tax_rate,
            self.diluted_shares, self.current_share_price, self.unallocated_operating_income,
        )
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not math.isfinite(value) for value in numeric_fields):
            return False, "企业数值必须为有限数"
        if self.total_revenue <= 0 or self.diluted_shares <= 0 or self.current_share_price <= 0:
            return False, "收入、稀释股数和报价必须为正数"
        if not 0 <= self.effective_tax_rate <= 1:
            return False, "有效税率必须处于 0 与 1 之间"
        if len({segment.segment_id for segment in self.segments}) != len(self.segments):
            return False, "分部标识不能重复"
        for segment in self.segments:
            values = (segment.revenue, segment.revenue_weight, segment.operating_margin,
                      segment.operating_income, segment.cost_pass_through_power,
                      segment.inventory_buffer_days)
            if any(isinstance(value, bool) or not isinstance(value, (int, float))
                   or not math.isfinite(value) for value in values):
                return False, "分部数值必须为有限数"
            if segment.revenue < 0 or not 0 <= segment.revenue_weight <= 1:
                return False, "分部收入或权重非法"
            if not 0 <= segment.cost_pass_through_power <= 1 or segment.inventory_buffer_days < 0:
                return False, "分部情景假设越界"

        sum_weights = sum(s.revenue_weight for s in self.segments)
        if abs(sum_weights - 1.0) > 0.005:
            return False, f"分部收入权重之和 ({sum_weights:.4f}) 未精确平账于 1.0"

        if any(abs(segment.revenue_weight - segment.revenue / self.total_revenue) > 0.005 for segment in self.segments):
            return False, "分部权重与披露收入不一致"

        sum_revenue = sum(s.revenue for s in self.segments)
        if self.total_revenue > 0:
            diff_ratio = abs(sum_revenue - self.total_revenue) / self.total_revenue
            if diff_ratio > 0.01:
                return False, f"分部营收加总 (${sum_revenue:.1f}M) 与总营收 (${self.total_revenue:.1f}M) 偏差超 1%"

        segment_income = sum(s.operating_income for s in self.segments)
        income_diff = abs(segment_income + self.unallocated_operating_income - self.total_operating_income)
        if income_diff > max(1e-9, abs(self.total_operating_income) * 0.01):
            return False, "分部利润及未分配项与合并利润不平账"
        return True, "平账自检 PASS"


@dataclass
class SegmentCausalImpact:
    """单一业务分部在突发事件中的受损/受益因果明细."""
    segment_id: str
    segment_name: str
    exposure_score: float  # 事件暴露度 (0.0 完全无关 ~ 1.0 正面全额承受)
    gross_cost_shock_pct: float  # 原始成本/收入冲击率 (如 +0.085 代表成本上涨 8.5%)
    inventory_absorption_factor: float  # 库存周期吸收因子 (0.0 无法吸收 ~ 1.0 完全被安全库存吸收)
    net_cost_shock_pct: float  # 扣除库存缓冲与转嫁权后的净成本冲击率
    operating_income_impact: float  # 分部营运利润变动额 ΔEBIT (百万美元)
    revenue_impact: float  # 分部营收变动额 ΔRevenue (百万美元)
    rationale: str  # 买方商业因果推演逻辑说明

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "segment_name": self.segment_name,
            "exposure_score": round(self.exposure_score, 4),
            "gross_cost_shock_pct": round(self.gross_cost_shock_pct, 4),
            "inventory_absorption_factor": round(self.inventory_absorption_factor, 4),
            "net_cost_shock_pct": round(self.net_cost_shock_pct, 4),
            "operating_income_impact": round(self.operating_income_impact, 2),
            "revenue_impact": round(self.revenue_impact, 2),
            "rationale": self.rationale,
        }


@dataclass
class EnterpriseEventImpactResult:
    """突发事件穿透至企业级总账的综合财务损益与决策卡."""
    ticker: str
    company_name: str
    event_id: str
    event_title: str
    severity_level: str
    total_operating_income_impact: float  # 全公司 ΔEBIT (百万美元)
    ebit_impact_percentage: float  # 对原有营业利润的百分比变动
    net_income_impact: float  # 全公司 ΔNet Income (百万美元)
    eps_impact: float  # 每股收益冲击 ΔEPS (美元/股)
    valuation_target_discount_pct: float  # 对 DCF 估值底价/靶心的敏感度折让幅度
    segment_impacts: List[SegmentCausalImpact]
    focal_summary: str  # 买方商业直觉总结
    recommended_action: str  # 买方决策建议 (如 "BUY_ON_OVERSOLD", "MONITOR_INVENTORY", "DOWNGRADE_MARGIN")
    source_refs: Dict[str, Any] = field(default_factory=dict)
    assumption_id: str = ""
    assumption_rationale: str = ""
    assumption_status: str = "uncalibrated_scenario"
    quote_timestamp: str = ""
    quote_session: str = ""
    data_origin: str = "synthetic"
    evidence_status: str = "unverified"
    is_actionable: bool = False
    scenario_signal: str = ""
    valuation_method: str = "uncalibrated_sensitivity"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "event_id": self.event_id,
            "event_title": self.event_title,
            "severity_level": self.severity_level,
            "total_operating_income_impact": round(self.total_operating_income_impact, 2),
            "ebit_impact_percentage": round(self.ebit_impact_percentage, 4),
            "net_income_impact": round(self.net_income_impact, 2),
            "eps_impact": round(self.eps_impact, 4),
            "valuation_target_discount_pct": round(self.valuation_target_discount_pct, 4),
            "segment_impacts": [s.to_dict() for s in self.segment_impacts],
            "focal_summary": self.focal_summary,
            "recommended_action": self.recommended_action,
            "source_refs": self.source_refs,
            "assumption_id": self.assumption_id,
            "assumption_rationale": self.assumption_rationale,
            "assumption_status": self.assumption_status,
            "quote_timestamp": self.quote_timestamp,
            "quote_session": self.quote_session,
            "data_origin": self.data_origin,
            "evidence_status": self.evidence_status,
            "is_actionable": self.is_actionable,
            "scenario_signal": self.scenario_signal,
            "valuation_method": self.valuation_method,
        }


class SotpEventPenetrationEngine:
    """突发微观事件与 SOTP 业务分部穿透引擎."""

    def __init__(self):
        pass

    def evaluate_segment_exposure(
        self,
        segment: BusinessSegment,
        event: StructuredEventSummary,
    ) -> Tuple[float, str]:
        """计算分部对特定突发事件的重叠暴露度 (Exposure Score).

        结合分部业务关键词、事件波及分部与微观物理事实进行语义交叉断言。
        """
        combined_event_context = (
            f"{' '.join(event.affected_business_segments)} "
            f"{event.micro_physical_impact} "
            f"{' '.join(event.involved_entities)} "
            f"{event.raw_title}"
        ).lower()

        # 1. 检查事件波及分部是否直接点名该分部 (双向包含与核心短语交叉判定)
        direct_match = False
        seg_zh_lower = segment.name_zh.lower()
        seg_en_lower = segment.name_en.lower()

        for target_seg in event.affected_business_segments:
            t_clean = target_seg.lower().strip()
            if t_clean in seg_zh_lower or seg_zh_lower in t_clean or t_clean in seg_en_lower:
                direct_match = True
                break
            # 检查高频核心产业短语重叠
            for core_phrase in [
                "先进制程", "晶圆代工", "晶圆制造", "半导体制造", "半导体代工",
                "算力中心", "数据中心", "云计算", "智能手机", "车规芯片", "动力电池"
            ]:
                if core_phrase in t_clean and (core_phrase in seg_zh_lower or core_phrase in seg_en_lower):
                    direct_match = True
                    break
            if direct_match:
                break

        # 2. 检查关键词词典命中数量
        hit_keywords = []
        for kw in segment.relevant_keywords:
            if kw.lower() in combined_event_context:
                hit_keywords.append(kw)

        if direct_match and hit_keywords:
            score = 1.0
            rationale = f"分部与事件直接锁定，命中核心业务关键词: {', '.join(hit_keywords[:3])}"
        elif direct_match:
            score = 0.85
            rationale = f"事件受波及分部明确包含 '{segment.name_zh}'"
        elif hit_keywords:
            # 根据关键词数量赋权
            score = min(0.75, 0.35 + 0.15 * len(hit_keywords))
            rationale = f"命中分部业务链路关键词: {', '.join(hit_keywords[:3])}"
        else:
            score = 0.0
            rationale = "该业务分部与当前突发事件无直接物理或供应链交集"

        return score, rationale

    def parse_event_duration_days(self, duration_str: str) -> float:
        """从自然语言持续期描述中解析出天数 (数值边界防御)."""
        d_lower = duration_str.lower()
        if "永久" in d_lower or "长期" in d_lower or "年" in d_lower:
            return 365.0
        if "16周" in d_lower:
            return 112.0
        if "周" in d_lower:
            # 尝试提取周数
            import re
            m = re.search(r"(\d+)\s*周", d_lower)
            if m:
                return float(m.group(1)) * 7.0
            return 45.0
        if "月" in d_lower:
            import re
            m = re.search(r"(\d+)\s*个?月", d_lower)
            if m:
                return float(m.group(1)) * 30.0
            return 90.0
        if "天" in d_lower or "日" in d_lower:
            import re
            m = re.search(r"(\d+)\s*[天日]", d_lower)
            if m:
                return float(m.group(1))
            return 14.0
        return 60.0  # 默认 60 天

    def parse_shock_intensity(self, event: StructuredEventSummary) -> float:
        """从微观物理事实中提取冲击强度基准 (基准变动率)."""
        text = event.micro_physical_impact.lower()
        import re
        # 匹配百分比，如 8.5%、35%、15%、40%
        match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        if match:
            val = float(match.group(1)) / 100.0
            return min(val, 0.60)  # 最大边界防护 60%

        # 若未显式写出百分比，按烈度默认基准
        if event.severity_level == "P0":
            return 0.15
        elif event.severity_level == "P1":
            return 0.08
        elif event.severity_level == "P2":
            return 0.03
        return 0.01

    def calculate_segment_impact(
        self,
        segment: BusinessSegment,
        event: StructuredEventSummary,
        exposure_score: float,
        exposure_rationale: str,
    ) -> SegmentCausalImpact:
        """执行单分部精准因果计算：结合库存缓冲吸收率、转嫁权与成本结构."""
        if exposure_score <= 0.001:
            return SegmentCausalImpact(
                segment_id=segment.segment_id,
                segment_name=segment.name_zh,
                exposure_score=0.0,
                gross_cost_shock_pct=0.0,
                inventory_absorption_factor=1.0,
                net_cost_shock_pct=0.0,
                operating_income_impact=0.0,
                revenue_impact=0.0,
                rationale=exposure_rationale,
            )

        # 1. 原始冲击率
        gross_shock = self.parse_shock_intensity(event)

        # 2. 持续期与库存周转天数 (DIO) 吸收抵御
        duration_days = self.parse_event_duration_days(event.estimated_duration)
        if segment.inventory_buffer_days > 0 and duration_days > 0:
            # 若库存天数能覆盖持续期的大部分，则吸收因子高
            buffer_ratio = min(1.0, segment.inventory_buffer_days / max(duration_days, 1.0))
            # 库存缓冲最多吸收 75% 冲击 (因为现存库存也会耗尽和存在重置成本)
            absorption_factor = min(0.75, buffer_ratio * 0.75)
        else:
            absorption_factor = 0.0

        effective_shock_after_buffer = gross_shock * (1.0 - absorption_factor)

        # 3. 成本转嫁能力冲销 (Pass-Through Power)
        # 如转嫁权 0.7，则公司能将 70% 额外成本向下游涨价转移，自身仅承受 30%
        net_shock = effective_shock_after_buffer * (1.0 - segment.cost_pass_through_power)

        # 4. 计算对营运利润 (EBIT) 的绝对金额冲击
        # 营业成本 = 营业收入 × (1 - 营业利润率)
        segment_cogs = segment.revenue * max(0.1, (1.0 - segment.operating_margin))

        # 判断事件是利好还是利空 (如德州补贴/便利化通关是利好降低成本，爆炸/加税是利空)
        is_favorable = any(w in event.raw_title or w in event.micro_physical_impact for w in ["补贴", "减免", "便利", "折抵", "资助"])
        sign = 1.0 if is_favorable else -1.0

        # 分部营业利润变动额 ΔEBIT (百万美元)
        delta_ebit = sign * (segment_cogs * net_shock * exposure_score)
        # 营收变动额 (若是涨价转嫁，会有少许名义营收增加)
        delta_revenue = (segment.revenue * effective_shock_after_buffer * segment.cost_pass_through_power * exposure_score) if not is_favorable else 0.0

        detailed_rationale = (
            f"{exposure_rationale}。原始冲击 {gross_shock*100:.1f}%，"
            f"DIO库存天数({segment.inventory_buffer_days:.0f}天)吸收 {absorption_factor*100:.1f}%，"
            f"下游转嫁权({segment.cost_pass_through_power*100:.0f}%)冲销后，净分部利润变动 ${delta_ebit:+.2f}M。"
        )

        return SegmentCausalImpact(
            segment_id=segment.segment_id,
            segment_name=segment.name_zh,
            exposure_score=exposure_score,
            gross_cost_shock_pct=gross_shock,
            inventory_absorption_factor=absorption_factor,
            net_cost_shock_pct=net_shock,
            operating_income_impact=delta_ebit,
            revenue_impact=delta_revenue,
            rationale=detailed_rationale,
        )

    def analyze_company_impact(
        self,
        company_sotp: CompanySotpProfile,
        event: StructuredEventSummary,
    ) -> EnterpriseEventImpactResult:
        """主入口：执行企业级全分部穿透与总账加总计算."""
        # 1. 前置刚性平账自检
        is_valid, msg = company_sotp.verify_balance_sheet_invariants()
        if not is_valid:
            raise ValueError(f"【SOTP 平账校验失败】：{company_sotp.ticker} - {msg}")

        segment_results: List[SegmentCausalImpact] = []
        total_delta_ebit = 0.0

        for segment in company_sotp.segments:
            exposure_score, exposure_rationale = self.evaluate_segment_exposure(segment, event)
            seg_impact = self.calculate_segment_impact(
                segment=segment,
                event=event,
                exposure_score=exposure_score,
                exposure_rationale=exposure_rationale,
            )
            segment_results.append(seg_impact)
            total_delta_ebit += seg_impact.operating_income_impact

        # 2. 全公司级加总与税后利润穿透
        tax_rate = company_sotp.effective_tax_rate
        delta_net_income = total_delta_ebit * (1.0 - tax_rate)

        # 3. 每股收益 (ΔEPS) 穿透 (防除零保护)
        shares = company_sotp.diluted_shares
        delta_eps = delta_net_income / shares

        # 4. 营业利润百分比冲击
        if company_sotp.total_operating_income == 0:
            raise ValueError("零营业利润无法用于 SOTP 相对冲击敏感度计算")
        base_ebit = abs(company_sotp.total_operating_income)
        ebit_pct_change = total_delta_ebit / base_ebit

        # 5. DCF 折现估值敏感度折让
        # 假设经营现金流永续折现系数，利润变化对估值靶心的弹性系数取约 1.2x (经营杠杆效应)
        valuation_discount = max(-0.35, min(0.35, ebit_pct_change * 1.2))

        # 未校准的启发式仅提供情景信号，正式操作需要另行研究审核。
        if total_delta_ebit == 0:
            rec_action = "NO_MEASURABLE_SEGMENT_IMPACT"
        elif total_delta_ebit > 0:
            rec_action = "EXPEDITE_EXPANSION_OVERWEIGHT"
        elif abs(ebit_pct_change) < 0.015:
            rec_action = "BUY_ON_OVERSOLD_NOISE"
        elif abs(ebit_pct_change) < 0.08:
            rec_action = "MONITOR_INVENTORY_BUFFER"
        else:
            rec_action = "DOWNGRADE_AND_HEDGE"
        focal_summary = (
            f"未校准情景估计，假设编号 {company_sotp.assumption_id or '未登记'}，"
            f"ΔEBIT {total_delta_ebit:+.2f} 百万美元，ΔEPS {delta_eps:+.4f} 美元/股。"
            "需复核冲击参数和原始事实后再做投资研判。"
        )

        return EnterpriseEventImpactResult(
            ticker=company_sotp.ticker,
            company_name=company_sotp.company_name,
            event_id=event.event_id,
            event_title=event.raw_title,
            severity_level=event.severity_level,
            total_operating_income_impact=total_delta_ebit,
            ebit_impact_percentage=ebit_pct_change,
            net_income_impact=delta_net_income,
            eps_impact=delta_eps,
            valuation_target_discount_pct=valuation_discount,
            segment_impacts=segment_results,
            focal_summary=focal_summary,
            recommended_action="SCENARIO_REVIEW_REQUIRED",
            scenario_signal=rec_action,
            source_refs=company_sotp.source_refs,
            assumption_id=company_sotp.assumption_id,
            assumption_rationale=company_sotp.assumption_rationale,
            assumption_status=company_sotp.assumption_status,
            quote_timestamp=company_sotp.quote_timestamp,
            quote_session=company_sotp.quote_session,
            data_origin=company_sotp.data_origin,
            evidence_status=company_sotp.evidence_status,
        )
