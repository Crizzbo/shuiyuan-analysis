"""AI 投研日记与定性归纳协议 (AI Research Journal Protocol).

响应用户核心投研哲学：
“程序只是负责数据输入和结构化显示数据，ai需要参与去归纳整理日记”

本模块定义 AI 投研日记的标准架构、提示词协议与合成辅助方法：
1. 商业血肉与护城河质感 (穿透财务数字，审视生意实质与客户粘性);
2. 法证体检与微观现实对撞 (解读受限资金、存货周转、渠道倒挂背后的经营意图);
3. 第二层次思维与共识预期差 (识别市场非理性恐慌或亢奋背后的共识盲点);
4. 极端风险推演与下行防线 (推演跌破悲观底价的实际触发路径与应对预案);
5. 核心跟踪日记与拐点指标 (确立后续定期复盘的 2-3 个微观高频验证指标)。
"""

from typing import Dict, Any, Optional
from datetime import datetime


class AIJournalProtocol:
    """AI 投研日记规范与合成模板中枢."""

    JOURNAL_TEMPLATE = """#### 📖 【AI 投研日记与定性归纳】
**记录时间**: {record_date} | **分析标的**: {company_name} (`{ticker}`)

##### 1. 商业血肉与护城河质感
{business_essence}

##### 2. 法证体检与微观现实对撞
{forensic_reflection}

##### 3. 第二层次思维与共识预期差
{second_level_thinking}

##### 4. 极端情景推演与下行防线
{downside_defense_plan}

##### 5. 持续跟踪日记与验证锚点
{tracking_calendar_notes}
"""

    @classmethod
    def generate_journal_prompt(cls, result_data: Dict[str, Any]) -> str:
        """根据底层量化引擎输出的客观数据包，生成供 AI 归纳日记的结构化提示指南."""
        card = result_data.get("decision_card", {})
        ticker = card.get("ticker", "UNKNOWN")
        name = card.get("company_name", ticker)
        price = card.get("current_price", 0.0)
        sym = card.get("currency_symbol", "$")
        fair_val = card.get("neutral_fair_value", 0.0)
        pess_floor = card.get("pessimistic_floor", 0.0)
        opt_target = card.get("optimistic_target", 0.0)
        runway = card.get("hard_runway_desc", "N/A")
        red_flags = card.get("forensic_red_flags_count", 0)

        prompt = f"""[AI 投研日记撰写指引]
程序已完成标的 {name} ({ticker}) 的数据输入、时效门禁与数学模型运算：
- 现价: {sym}{price:.2f} | 内在公允锚点: {sym}{fair_val:.2f}
- 悲观清算防线: {sym}{pess_floor:.2f} | 乐观目标: {sym}{opt_target:.2f}
- 现金跑道: {runway} | 法证红牌: {red_flags} 项

请 AI 投资研究员基于上述客观数据，撰写一段富有商业洞察力与批判性思维的【投研日记】：
1. 深入剖析其商业模式与护城河真实度（非套话，结合产品与客户集中度）；
2. 结合法证体检结果（红牌/黄牌/存货/现金）解读管理层的真实处境；
3. 指出当前市场定价的共识偏见（第二层次思维）；
4. 明确写出若跌破悲观底价的具体防范措施；
5. 锁定 2-3 个核心验证指标作为后续跟踪日记重点。
"""
        return prompt

    @classmethod
    def format_journal_entry(
        cls,
        ticker: str,
        company_name: str,
        business_essence: str,
        forensic_reflection: str,
        second_level_thinking: str,
        downside_defense_plan: str,
        tracking_calendar_notes: str,
        record_date: Optional[str] = None,
    ) -> str:
        """合成结构化 AI 投研日记 Markdown 文本."""
        now_str = record_date or datetime.now().strftime("%Y-%m-%d %H:%M")
        return cls.JOURNAL_TEMPLATE.format(
            record_date=now_str,
            company_name=company_name,
            ticker=ticker,
            business_essence=business_essence.strip(),
            forensic_reflection=forensic_reflection.strip(),
            second_level_thinking=second_level_thinking.strip(),
            downside_defense_plan=downside_defense_plan.strip(),
            tracking_calendar_notes=tracking_calendar_notes.strip(),
        )
