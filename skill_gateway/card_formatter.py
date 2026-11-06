"""买方机构级富文本决策卡片渲染器 (Institutional Decision Card Formatter).

严格贯彻 2026-10-15 工程整改规范：
1. 统一报价时间与时效属性 (Task 06: 休市/过期数据明确标注「前收盘价基准」，严禁写「当前最新市价」);
2. 贯穿市场与币种符号 (Task 16: 美元使用 $, 人民币与日元使用 ¥);
3. 真实展示多情景估值复算参数与模型名称 (Task 10: 杜绝硬编码假参数与固定倍率);
4. 移除无依据半凯利仓位 (Task 11: 无校准概率严格标注为待定);
5. 呈现修正后的真实造血与现金跑道状态 (Task 12: 持续净流入不误报烧钱);
6. 结构化展示客观数据，并为 AI 投研日记留出独立归纳呈现专区 (用户核心要求)。
"""

from typing import Dict, Any, List
from financial_core.contracts import FinancialAnalysisResult, DecisionCardData, ValuationScenario
from skill_gateway.freshness import QuoteSnapshot


class DecisionCardFormatter:
    """富文本决策卡片格式化器."""

    OBJECTIVE_BADGES = {
        "FORENSIC_ALERT_ACTIVE": "【法证预警生效·存在报表粉饰或毒性】",
        "RUNWAY_DEFICIT_WARNING": "【现金跑道紧绷·有潜在稀释/流动性风险】",
        "DISCOUNT_BUFFER_OBSERVED": "【深度折价走廊·具备显著安全边际】",
        "PREMIUM_OVERVALUED": "【估值溢价偏高·市价显著高于内生公允锚点】",
        "BALANCED_FAIR_OBSERVATION": "【估值公允均衡·静待微观催化剂明朗】",
        "BLOCKED_MISSING_EVIDENCE": "【研究准入阻断·缺失法定三表底账】",
        "BLOCKED_ACCOUNTING_DISCREPANCY": "【平账刚性阻断·资产负债表严重失衡】",
    }

    @classmethod
    def render_decision_card(
        cls, result: FinancialAnalysisResult, quote: QuoteSnapshot
    ) -> str:
        """渲染全流程机构级决策卡片 Markdown."""
        card: DecisionCardData = result.decision_card
        sym = card.currency_symbol

        lines: List[str] = []

        # 头部标题与时效凭据
        demo_tag = " [DEMO_SAMPLE·测试演示底账]" if result.is_demo_sample else ""
        lines.append(f"### 【买方独立投研数据档案】: {card.company_name} (`{card.ticker}`){demo_tag}")
        lines.append(f"**市场/币种**: `{card.market} ({card.currency})` | **所属赛道**: `{card.sector}` | {quote.display_badge}")
        lines.append(f"> {quote.session_notice}\n")

        # 若执行被硬门禁阻断，直接输出阻断说明卡
        if not result.execution_success:
            lines.append("#### 安全门禁阻断报告 (Execution Blocked)")
            lines.append(f"- **阻断类型**: `{result.execution_status}`")
            lines.append(f"- **详细原因**: {result.block_reason}")
            lines.append("- **准入规范**: 依据买方投研准入契约，系统已拒绝基于缺失事实或失真资产负债表生成虚假估值。")
            lines.append("\n---")
            return "\n".join(lines)

        # 1. 客观指标看板 (程序只负责客观数据，严禁拍脑袋给交易指令)
        obj_badge = cls.OBJECTIVE_BADGES.get(card.objective_signal, f"【{card.objective_signal}】")
        lines.append("#### 核心量化指标与客观信号看板")
        lines.append(f"- **量化状态信号**: {obj_badge}")

        # 严格区分实时现价与前收盘基准 (Task 06)
        if quote.is_live:
            lines.append(f"- **盘中最新现价**: `{sym}{card.current_price:.2f}` (时间戳: {quote.as_of_local_time})")
        else:
            lines.append(f"- **前收盘参考价**: `{sym}{card.current_price:.2f}` (非盘中现价，基准时点: {quote.as_of_local_time})")

        lines.append(f"- **前期基准对照价**: `{sym}{card.baseline_reference_price:.2f}`")
        lines.append(f"- **内生公允价值 (中性锚点)**: `{sym}{card.neutral_fair_value:.2f}`")
        lines.append(f"- **现价较公允锚点落差**: `{card.margin_of_safety_pct:+.1f}%`")
        lines.append(f"- **资金跑道状态**: `{card.hard_runway_desc}`")

        # 仓位显示 (Task 11: 无概率校准时严格显示待定)
        if card.kelly_fraction is not None:
            lines.append(f"- **模型建议仓位**: `{card.kelly_fraction * 100:.1f}%`")
        else:
            lines.append(f"- **组合建议仓位**: `待定 (需结合投资人组合风控与胜率赔率独立评估)`")
        lines.append("")

        # 2. 多情景估值走廊 (Task 10: 真实复算参数)
        lines.append("#### 多情景估值复算走廊 (Valuation Matrix)")
        lines.append(f"| 估值情景 | 内在价值 ({card.currency}) | 较现价空间 | 折现率 WACC | 永续增长率 g | 估值模型 |")
        lines.append("|:---|:---:|:---:|:---:|:---:|:---|")

        for sc in result.valuation_scenarios:
            tag = "悲观防线" if sc.scenario_name == "pessimistic" else ("中性基准" if sc.scenario_name == "neutral" else "乐观靶心")
            w_str = f"{sc.wacc*100:.1f}%" if sc.wacc is not None else "N/A"
            g_str = f"{sc.terminal_growth_rate*100:.1f}%" if sc.terminal_growth_rate is not None else "N/A"
            lines.append(
                f"| {tag} | `{sym}{sc.fair_value:.2f}` | `{sc.implied_upside_downside_pct:+.1f}%` | "
                f"{w_str} | {g_str} | `{sc.valuation_model_used}` |"
            )
        lines.append("")

        # 3. 法证五刀穿透体检 (Forensic Scalpel)
        lines.append("#### 法证级证据穿透体检 (Forensic Dissection)")
        if card.forensic_red_flags_count == 0 and card.forensic_yellow_flags_count == 0:
            lines.append("- **法证体检结论**: 全部核心指标通过穿透核验，未见明显报表粉饰或账外毒性。")
        else:
            lines.append(f"- **法证体检结论**: 触发红牌 [{card.forensic_red_flags_count}] 项，黄牌 [{card.forensic_yellow_flags_count}] 项。")
            if result.forensic_findings:
                for ff in result.forensic_findings:
                    lines.append(f"  - [{ff.alert_level}] **{ff.dimension}**: {ff.evidence}")
        lines.append("")

        # 4. 宏观压力加压与衍生品因果链 (Task 09, 14)
        if result.macro_stress or result.option_pricing:
            lines.append("#### 宏观压力测试与衍生品结构 (Macro & Options)")
            if result.macro_stress:
                ms = result.macro_stress
                lines.append(
                    f"- **宏观流动性加压 ({ms.scenario_name})**: 传导机制 `{ms.transmission_channel}`，"
                    f"理论估值下折 `{ms.equity_shock_pct:+.1f}%`，承压理论公允价 `{sym}{ms.target_price_under_stress:.2f}` (加压 WACC `{ms.shocked_wacc_pct:.1f}%`)。"
                )
            if result.option_pricing:
                op = result.option_pricing
                m_call_str = f"`{sym}{op.merton_jump_call:.2f}`" if op.merton_jump_call is not None else "`未计算`"
                lines.append(
                    f"- **CRR 美式期权定价 (行权价 {sym}{op.strike}, 隐含波动率 {op.implied_volatility*100:.1f}%)**: "
                    f"美式看涨 `{sym}{op.crr_american_call:.2f}` (提前行权溢价 `+{sym}{op.early_exercise_premium:.4f}`) | "
                    f"美式看跌 `{sym}{op.crr_american_put:.2f}` | Merton 跳跃看涨 {m_call_str}。"
                )
            lines.append("")

        # 5. 买方量化因果推导事实清单 (Causal Evidence)
        if card.primary_catalysts or card.key_risks:
            lines.append("#### 【买方量化因果推导事实清单 (Causal Evidence & Drivers)】")
            if card.primary_catalysts:
                lines.append("**[核心上行催化事实与达成乐观靶心路径]**:")
                for cat in card.primary_catalysts:
                    lines.append(f"- {cat}")
            if card.key_risks:
                lines.append("**[核心下行破位风险与跌穿悲观底线事实]**:")
                for risk in card.key_risks:
                    lines.append(f"- {risk}")
            lines.append("")

        # 6. AI 投研日记与定性归纳专区 (响应用户“程序只负责数据输入和结构化显示，AI需要参与归纳整理日记”)
        lines.append("### 【AI 投研日记与定性归纳 (AI Research Journal)】")
        if card.ai_research_journal:
            lines.append(card.ai_research_journal)
        else:
            lines.append("> *[待 AI 结合上述客观事实数据，归纳商业模式血肉、第二层次思维、周期位置与跟踪日记]*")
            lines.append("1. **商业血肉与护城河质感**: 结合产品毛利率、客户集中度及产业链利润分配分析其真实壁垒；")
            lines.append("2. **预期差与第二层次思维**: 审视当前市场悲观或亢奋情绪定价背后的隐含偏见；")
            lines.append("3. **底线思维与破位警报**: 关注悲观底价防线的触发事件，制定严谨的跟踪验证日记。")

        lines.append("\n---")
        lines.append("*(注：上方数据卡由量化工程管道严格复算生成；下方投研日记由 AI 结合微观血肉归纳整理)*")
        return "\n".join(lines)
