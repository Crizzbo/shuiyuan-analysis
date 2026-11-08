"""产业链上下游涟漪效应传导引擎 (Supply Chain Ripple Effect Engine).

遵循 Google Python 编程风格指南与系统架构防劣变准则:
1. 纯净核心层: 属于 financial_core 底层独立金融计算引擎，严禁逆向依赖外层脚本或工具;
2. 产业链拓扑因果建模: 建立 "上游供应商 ➔ 核心中枢企业 ➔ 下游大客户" 纵横向因果传导数学体系;
3. 动态防御数学机制: 结合存货周转天数 (DIO) 吸收周期、传导弹性 (Beta) 与定价转嫁权 (PT);
4. 有限责任与边界防御: 严格执行除零除负防御、下界有限责任截断与极值平滑收敛;
5. 去工程符号化: 全量输出买方自然中文商业语义与投资决策战术直觉。
"""

from dataclasses import asdict, dataclass
import math
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class RippleNodeImpact:
    """产业链单个实体节点的突发事件涟漪冲击测算契约."""

    node_id: str
    name_zh: str
    ticker: Optional[str]
    node_role: str  # "upstream", "core_hub", "downstream"
    effective_shock_pct: float
    buffer_dio_days: float
    uncovered_exposure_days: float
    transmission_elasticity: float
    pricing_power_pt: float
    ebit_impact_pct: float
    vulnerability_level: str
    buyer_verdict_zh: str
    rationale_zh: str

    def to_dict(self) -> Dict[str, Any]:
        """将节点影响序列化为字典."""
        return asdict(self)


@dataclass
class SupplyChainRippleReport:
    """产业链全息涟漪效应推演评估报告."""

    topology_id: str
    topology_name_zh: str
    event_id: str
    event_title: str
    disruption_duration_days: float
    core_hub_impact: RippleNodeImpact
    upstream_impacts: List[RippleNodeImpact]
    downstream_impacts: List[RippleNodeImpact]
    chain_vulnerability_level: str
    chain_summary_zh: str
    transmission_matrix: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """序列化为标准输出字典."""
        return {
            "topology_id": self.topology_id,
            "topology_name_zh": self.topology_name_zh,
            "event_id": self.event_id,
            "event_title": self.event_title,
            "disruption_duration_days": self.disruption_duration_days,
            "chain_vulnerability_level": self.chain_vulnerability_level,
            "chain_summary_zh": self.chain_summary_zh,
            "core_hub_impact": self.core_hub_impact.to_dict(),
            "upstream_impacts": [u.to_dict() for u in self.upstream_impacts],
            "downstream_impacts": [d.to_dict() for d in self.downstream_impacts],
            "transmission_matrix": self.transmission_matrix,
        }


class SupplyChainRippleEngine:
    """产业链上下游涟漪效应传导计算核心引擎."""

    def __init__(self, default_disruption_days: float = 60.0) -> None:
        """初始化产业链涟漪传导引擎.

        Args:
            default_disruption_days: 默认断供/物理冲击持续天数 (天).
        """
        self.default_disruption_days = max(1.0, float(default_disruption_days))

    @staticmethod
    def _clamp(val: float, low: float, high: float) -> float:
        """数值安全上下界钳位函数 (私有辅助方法)."""
        if math.isnan(val) or math.isinf(val):
            return low
        return max(low, min(high, val))

    def _derive_buyer_verdict(self, ebit_impact_pct: float, pt: float, dio: float) -> Tuple[str, str]:
        """根据利润受损幅度、转嫁权与库存天数推导买方战术决策直觉 (私有方法).

        Args:
            ebit_impact_pct: 预估营业利润受损百分比 (如 -6.5).
            pt: 定价转嫁权系数 (0 ~ 1.0).
            dio: 存货周转天数安全垫.

        Returns:
            (vulnerability_level, verdict_zh) 元组.
        """
        if ebit_impact_pct >= 0.0:
            return "正向受益", "利好受益 (产业链协同增厚业绩，战术增配)"

        abs_loss = abs(ebit_impact_pct)
        if abs_loss < 1.5:
            return "稳健防御", "防御极强 (存货缓冲与议价权充分对冲，维持持仓底仓)"
        elif abs_loss < 5.0:
            if pt >= 0.70:
                return "中度承压", "韧性消化 (受损可控且转嫁能力高，等待情绪超跌布局)"
            else:
                return "中度承压", "利润承压 (缺乏定价转嫁权，短期面临毛利率收缩压制)"
        else:
            if dio < 30.0:
                return "极高脆弱", "高危脆弱 (存货告急且断供暴露敞口巨大，建议坚决回避或认沽对冲)"
            else:
                return "高度承压", "严重承压 (产业链交付断崖式受阻，建议战术性减仓控制下行风险)"

    def evaluate_ripple_transmission(
        self,
        topology: Dict[str, Any],
        event: Dict[str, Any],
        disruption_days: Optional[float] = None,
    ) -> SupplyChainRippleReport:
        """计算给定突发事件在特定产业链中的全息涟漪传导影响.

        Args:
            topology: 产业链拓扑定义字典 (符合 supply_chain_topologies.schema.json).
            event: 事件雷达记录字典.
            disruption_days: 预估断供/事故影响总天数 (若留空则采用默认或事件自推导).

        Returns:
            SupplyChainRippleReport 评估报告对象.

        Raises:
            ValueError: 拓扑结构缺失必需字段.
        """
        if not topology or "core_hub" not in topology:
            raise ValueError("产业链拓扑缺失核心中枢 (core_hub) 定义")

        topology_id = topology.get("topology_id", "UNKNOWN_CHAIN")
        topology_name_zh = topology.get("name_zh", "未命名产业链")
        event_id = event.get("event_id", "EVT_UNKNOWN")
        event_title = event.get("title", "未命名突发事件")

        # 1. 确定物理断供与冲击基准天数 (严格防止 0.0 被 or 语法旁路并确保安全下界)
        raw_days = disruption_days if disruption_days is not None else self.default_disruption_days
        t_days = max(1.0, float(raw_days))

        # 2. 测算核心中枢企业 (Core Hub)
        hub_cfg = topology["core_hub"]
        hub_dio = max(0.0, float(hub_cfg.get("base_raw_material_dio_days", 45.0)))
        hub_pt = self._clamp(float(hub_cfg.get("pricing_power_pt", 0.70)), 0.0, 1.0)

        # 存货耗尽后的未覆盖暴露天数
        hub_uncovered = max(0.0, t_days - hub_dio)
        hub_exposure_ratio = self._clamp(hub_uncovered / t_days, 0.0, 1.0)
        # 核心代工厂/中枢产能受损比例 (基准假定断供敞口下满负荷损失)
        hub_base_shock_pct = -100.0 * hub_exposure_ratio * 0.25  # 季度度量归一
        hub_ebit_impact = hub_base_shock_pct * (1.0 - hub_pt * 0.5)  # 中枢可转嫁部分成本
        hub_ebit_impact = self._clamp(hub_ebit_impact, -100.0, 50.0)

        hub_vuln, hub_verdict = self._derive_buyer_verdict(hub_ebit_impact, hub_pt, hub_dio)
        hub_rationale = (
            f"中枢标的具备 {hub_dio:.0f} 天原材料存货缓冲，事件导致有效断供 {t_days:.0f} 天，"
            f"存货消耗后暴露敞口天数为 {hub_uncovered:.0f} 天 (敞口比 {hub_exposure_ratio*100:.1f}%)。"
            f"依托 {hub_pt*100:.0f}% 定价转嫁权冲销后，预估对营业利润冲击为 {hub_ebit_impact:.2f}%。"
        )

        hub_node = RippleNodeImpact(
            node_id=f"HUB_{hub_cfg.get('ticker', 'CORE')}",
            name_zh=hub_cfg.get("name_zh", "核心中枢企业"),
            ticker=hub_cfg.get("ticker"),
            node_role="core_hub",
            effective_shock_pct=hub_base_shock_pct,
            buffer_dio_days=hub_dio,
            uncovered_exposure_days=hub_uncovered,
            transmission_elasticity=1.0,
            pricing_power_pt=hub_pt,
            ebit_impact_pct=round(hub_ebit_impact, 2),
            vulnerability_level=hub_vuln,
            buyer_verdict_zh=hub_verdict,
            rationale_zh=hub_rationale,
        )

        # 3. 测算上游节点 (Upstream Nodes)
        upstream_impacts: List[RippleNodeImpact] = []
        for up in topology.get("upstream_nodes", []):
            up_dio = max(0.0, float(up.get("buffer_dio_days", 15.0)))
            up_elasticity = self._clamp(float(up.get("transmission_elasticity", 1.0)), 0.0, 2.0)
            up_uncovered = max(0.0, t_days - up_dio)
            up_exposure_ratio = self._clamp(up_uncovered / t_days, 0.0, 1.0)

            # 上游作为供应方或直接物理受害者
            up_shock_pct = -100.0 * up_exposure_ratio * up_elasticity * 0.35
            up_ebit_impact = self._clamp(up_shock_pct, -100.0, 50.0)
            up_vuln, up_verdict = self._derive_buyer_verdict(up_ebit_impact, 0.20, up_dio)

            up_rationale = (
                f"上游供应节点储备缓冲 {up_dio:.0f} 天，传导弹性系数为 {up_elasticity:.2f}。"
                f"断供造成敞口 {up_uncovered:.0f} 天，预估营业利润受损约为 {up_ebit_impact:.2f}%。"
            )

            upstream_impacts.append(
                RippleNodeImpact(
                    node_id=up.get("node_id", "UPSTREAM_UNKNOWN"),
                    name_zh=up.get("name_zh", "上游供应商"),
                    ticker=up.get("ticker"),
                    node_role="upstream",
                    effective_shock_pct=round(up_shock_pct, 2),
                    buffer_dio_days=up_dio,
                    uncovered_exposure_days=up_uncovered,
                    transmission_elasticity=up_elasticity,
                    pricing_power_pt=0.20,
                    ebit_impact_pct=round(up_ebit_impact, 2),
                    vulnerability_level=up_vuln,
                    buyer_verdict_zh=up_verdict,
                    rationale_zh=up_rationale,
                )
            )

        # 4. 测算下游节点 (Downstream Nodes)
        downstream_impacts: List[RippleNodeImpact] = []
        for down in topology.get("downstream_nodes", []):
            down_dio = max(0.0, float(down.get("buffer_dio_days", 45.0)))
            down_elasticity = self._clamp(float(down.get("transmission_elasticity", 0.70)), 0.0, 2.0)
            down_pt = self._clamp(float(down.get("pricing_power_pt", 0.80)), 0.0, 1.0)

            # 下游承受来自核心中枢产能缺口的传导
            down_uncovered = max(0.0, t_days - down_dio)
            down_exposure_ratio = self._clamp(down_uncovered / t_days, 0.0, 1.0)

            # 下游损益 = 中枢受损 * 传导弹性 * 下游自身暴露敞口 * (1 - 转嫁权)
            down_effective_shock = hub_base_shock_pct * down_elasticity * down_exposure_ratio
            down_ebit_impact = down_effective_shock * (1.0 - down_pt)
            down_ebit_impact = self._clamp(down_ebit_impact, -100.0, 50.0)

            down_vuln, down_verdict = self._derive_buyer_verdict(down_ebit_impact, down_pt, down_dio)
            down_rationale = (
                f"下游终端储备 {down_dio:.0f} 天存货缓冲，承接中枢代工缺口传导 (弹性 {down_elasticity:.2f})。"
                f"自身未覆盖暴露天数 {down_uncovered:.0f} 天，凭借 {down_pt*100:.0f}% 强定价权对冲后，"
                f"预估营业利润损益为 {down_ebit_impact:.2f}%。"
            )

            downstream_impacts.append(
                RippleNodeImpact(
                    node_id=down.get("node_id", "DOWNSTREAM_UNKNOWN"),
                    name_zh=down.get("name_zh", "下游大客户"),
                    ticker=down.get("ticker"),
                    node_role="downstream",
                    effective_shock_pct=round(down_effective_shock, 2),
                    buffer_dio_days=down_dio,
                    uncovered_exposure_days=down_uncovered,
                    transmission_elasticity=down_elasticity,
                    pricing_power_pt=down_pt,
                    ebit_impact_pct=round(down_ebit_impact, 2),
                    vulnerability_level=down_vuln,
                    buyer_verdict_zh=down_verdict,
                    rationale_zh=down_rationale,
                )
            )

        # 5. 综合全链脆弱度定级
        all_ebit_impacts = [hub_ebit_impact] + [u.ebit_impact_pct for u in upstream_impacts] + [d.ebit_impact_pct for d in downstream_impacts]
        avg_ebit_loss = abs(sum(all_ebit_impacts) / max(1, len(all_ebit_impacts)))

        if avg_ebit_loss > 8.0:
            chain_vuln = "全链系统性高危"
        elif avg_ebit_loss > 3.0:
            chain_vuln = "局部中度受损"
        else:
            chain_vuln = "整体稳健受控"

        chain_summary = (
            f"【{topology_name_zh} 突发事件全息涟漪研判】\n"
            f"物理冲击源引发持续约 {t_days:.0f} 天断供危机。全链综合脆弱度定级为【{chain_vuln}】(产业链平均受损 -{avg_ebit_loss:.2f}%)。\n"
            f"核心中枢 {hub_node.name_zh} ({hub_node.ticker}) 凭借 {hub_dio:.0f} 天存货与 {hub_pt*100:.0f}% 议价权，预估利润冲击 {hub_ebit_impact:.2f}%；\n"
            f"下游大客户群受各自存货缓冲与定价权分化影响，整体受损呈阶梯式衰减。"
        )

        # 6. 构建供前端大屏消费的拓扑关系矩阵
        transmission_matrix: List[Dict[str, Any]] = [hub_node.to_dict()] + [u.to_dict() for u in upstream_impacts] + [d.to_dict() for d in downstream_impacts]

        return SupplyChainRippleReport(
            topology_id=topology_id,
            topology_name_zh=topology_name_zh,
            event_id=event_id,
            event_title=event_title,
            disruption_duration_days=t_days,
            core_hub_impact=hub_node,
            upstream_impacts=upstream_impacts,
            downstream_impacts=downstream_impacts,
            chain_vulnerability_level=chain_vuln,
            chain_summary_zh=chain_summary,
            transmission_matrix=transmission_matrix,
        )
