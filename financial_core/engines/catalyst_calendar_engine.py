"""催化剂日历时间轴与二元事件定价引擎 (Catalyst Calendar & Binary Event Engine).

功能设计：
二级市场科技股与创新药的核心逻辑是“事件驱动 (Event-Driven)”：
1. 建立结构化硬性时间轴日历（包含精准交易日与事件类别）；
2. 量化二元事件概率分布 (Binary Event Expected Value)，计算成功与失败的数学期望；
3. 将事件驱动股价潜在爆发幅度与期权平值跨式 (Straddle) 隐含波动率进行横向比对，
   识别期权波动率是否被市场严重低估（买入波动率套利）或过度透支（警惕财报后 IV Crush）。
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class CorporateEvent:
    """结构化催化剂事件对象。"""
    event_id: str
    target_date: str                 # "YYYY-MM-DD"
    category: str                    # "clinical_readout", "fda_pdufa", "earnings_release", "product_launch", "partnership_milestone"
    title_zh: str
    description_zh: str
    upside_potential_pct: float      # 成功预期涨幅 % (如 +60.0 代表 +60%)
    downside_risk_pct: float         # 失败预期跌幅 % (如 -40.0 代表 -40%)
    probability_of_success: float    # 成功胜率 POS (如 0.60 代表 60%)
    options_implied_move_pct: Optional[float] = None # 期权市场平值跨式隐含的预期涨跌幅 % (如 25.0)


@dataclass(frozen=True)
class EventEvaluationResult:
    """事件定价与期权波动率比对结果。"""
    event_id: str
    target_date: str
    category: str
    title_zh: str
    days_until_event: int
    urgency_status: str              # "即将来临 (<14天)", "近期 (14-60天)", "中长期 (>60天)", "已发生"
    binary_expected_move_pct: float  # 二元数学期望涨幅 %
    odds_ratio: float                # 上行弹性与下行风险比值
    volatility_arbitrage_verdict: str# 期权 IV 定价合理性判定
    actionable_tactics_zh: str       # 实盘交易战术
    narrative_zh: str = ""           # 买方通俗全息研报卡片 (去工程符号化)
    category_zh: str = ""            # 纯自然中文事件分类 (去工程符号化)
    urgency_status_zh: str = ""      # 纯自然中文时效阶段 (去工程符号化)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "date": self.target_date,
            "category": self.category,
            "category_zh": self.category_zh or self.category,
            "title": self.title_zh,
            "days_until": f"{self.days_until_event} 天 ({self.urgency_status})",
            "urgency_status": self.urgency_status,
            "urgency_status_zh": self.urgency_status_zh or self.urgency_status,
            "binary_expected_move": f"{self.binary_expected_move_pct:+.2f}%",
            "odds_ratio": round(self.odds_ratio, 2),
            "volatility_arbitrage": self.volatility_arbitrage_verdict,
            "tactics": self.actionable_tactics_zh,
            "narrative_zh": self.narrative_zh,
        }


# 催化剂自然中文分类映射 (SSOT - 去工程符号化)
EVENT_CATEGORY_NAMES_ZH: Dict[str, str] = {
    "clinical_readout": "临床试验数据读出",
    "fda_pdufa": "FDA审评审批裁决",
    "earnings_release": "官方季度业绩发布",
    "product_launch": "重磅核心新品发布",
    "partnership_milestone": "战略合作与商业化里程碑",
}


class CatalystCalendarEngine:
    """催化剂日历量化评估器。"""

    @classmethod
    def evaluate_event(
        cls,
        event: CorporateEvent,
        as_of_date: Optional[str] = None,
    ) -> EventEvaluationResult:
        as_of = date.fromisoformat(as_of_date) if as_of_date else date.today()
        evt_d = date.fromisoformat(event.target_date)
        days = (evt_d - as_of).days
        category_zh = EVENT_CATEGORY_NAMES_ZH.get(event.category, "核心催化事件")

        if days < 0:
            urgency = "已过去 (历史事件)"
            urgency_zh = "已过去 (历史事件)"
        elif days == 0:
            urgency = "极度临近 (<14天，即将决战)"
            urgency_zh = "决战窗口即在今日"
        elif days <= 14:
            urgency = "极度临近 (<14天，即将决战)"
            urgency_zh = f"极度临近 (不足{days}天，即将决战)"
        elif days <= 60:
            urgency = "中期窗口 (14-60天，进入布局期)"
            urgency_zh = "中期窗口 (14-60天，进入布局期)"
        else:
            urgency = "远期储备 (>60天)"
            urgency_zh = "远期储备 (60天以上)"

        # 1. 金融边界防御：跌幅强制规范为负数，涨幅规范为正数，防止正负号混淆颠倒数学期望
        safe_upside = abs(float(event.upside_potential_pct))
        safe_downside = -abs(float(event.downside_risk_pct))

        # 胜率合法区间规范化 [0.01, 0.99]
        p_up = max(0.01, min(0.99, float(event.probability_of_success)))
        p_down = 1.0 - p_up
        exp_move = (p_up * safe_upside) + (p_down * safe_downside)

        # 2. 赔率计算 (上行空间 / 下行损失绝对值)
        downside_abs = max(1.0, abs(safe_downside))
        odds = safe_upside / downside_abs

        # 3. 期权市场隐含预期与基本面偏差比对 (Volatility Arbitrage)
        if event.options_implied_move_pct is not None and event.options_implied_move_pct > 0:
            mkt_move = float(event.options_implied_move_pct)
            # 衡量基本面真实二元无方向理论波动振幅
            fund_abs_move = p_up * safe_upside + p_down * abs(safe_downside)
            if fund_abs_move > mkt_move * 1.4:
                vol_verdict = f"期权波动率被低估 (期权仅计入 {mkt_move:.1f}% 波动，而基本面二元摆动高达 {fund_abs_move:.1f}%)：存在买入跨式/双买波动率套利空间。"
            elif fund_abs_move < mkt_move * 0.7:
                vol_verdict = f"期权波动率严重泡沫 (期权隐含暴涨暴跌 {mkt_move:.1f}%，引伸波幅极高)：警惕事件落地后剧烈 IV Crush 导致买方期权双杀。"
            else:
                vol_verdict = f"期权波动率合理定价 (期权隐含 {mkt_move:.1f}% 与基本面二元摆幅基本吻合)。"
        else:
            vol_verdict = "无公开期权引伸波幅数据，按纯正股基本面博弈定价。"

        # 4. 战术建议 (彻底消除二元负期望/高危利空事件在中期窗口被误导为"分批埋伏"的严重逻辑漏洞与0日语病)
        days_desc = "决战即在今日" if days == 0 else f"仅剩 {days} 天"
        if days < 0:
            tactics = "事件已落地，应关注实际结果与指引更新，移除日前博弈仓位。"
        elif days <= 14:
            if exp_move > 15.0 and odds > 1.8:
                tactics = (
                    f"临近决战窗口（{days_desc}），数学期望为正 ({exp_move:+.1f}%) 且赔率极高 ({odds:.2f})。"
                    f"建议正股锁定底仓，若参与衍生品切忌单腿裸买重仓，可采用牛市价差 (Bull Call Spread) 锁定成本规避暴跌风险。"
                )
            elif exp_move < 0.0 or odds < 1.0:
                tactics = (
                    f"【二元事件高危警报】临近决战（{days_desc}），二元数学期望为负 ({exp_move:+.1f}%) 或风险收益比倒挂 ({odds:.2f})！"
                    f"严禁日前单腿赌博博弈，建议及时规避二元归零踩踏风险或收紧绝对止损线防守。"
                )
            else:
                tactics = (
                    f"临近决战窗口（{days_desc}），预期收益平淡 ({exp_move:+.1f}%)、赔率适中 ({odds:.2f})。"
                    f"保持观望或仅维持极轻仓位跟踪，切勿在不确定性极高前夕盲目重仓追高。"
                )
        elif days <= 60:
            if exp_move > 10.0 and odds > 1.5:
                tactics = (
                    f"处于积极催化剂中期发酵窗口（距事件 {days} 天），二元数学期望良好 ({exp_move:+.1f}%)、盈亏赔率比达 {odds:.2f} 倍，"
                    f"当前股价尚未完全计入事件溢价，适合在震荡回调时分批建仓埋伏。"
                )
            elif exp_move < 0.0 or odds < 0.8:
                tactics = (
                    f"【中期利空/风险提示窗口】距事件尚有 {days} 天，但二元期望为负 ({exp_move:+.1f}%) 或下行风险不对称 (赔率仅 {odds:.2f})，"
                    f"切忌盲目抄底或逢低埋伏，应以逢高减持控仓或构建下行对冲保护为主。"
                )
            else:
                tactics = (
                    f"处于中期催化观察期（距事件 {days} 天），二元期望 ({exp_move:+.1f}%) 与赔率 ({odds:.2f}) 处于均衡状态，"
                    f"维持正常跟踪，等待进一步关键指引或数据读出。"
                )
        else:
            tactics = f"远期储备催化剂（距事件 {days} 天），重点跟踪管线推进进展与行业会议摘要更新。"

        # 5. 生成通俗买方自然全息研报卡片 (去工程符号化)
        narrative_zh = (
            f"【二元催化剂事件全息研判: {event.title_zh} ({category_zh})】"
            f"事件所处时效阶段【{urgency_zh}】(距离落地还剩 {days} 天)。"
            f"二元收益与风险推演: 预估成功率 {p_up * 100:.0f}%，成功上涨空间 +{safe_upside:.1f}%，"
            f"失败下跌风险 {safe_downside:.1f}%，数学综合期望回报 {exp_move:+.1f}%，盈亏赔率比 {odds:.2f} 倍。"
            f"期权波动率定价分析: {vol_verdict} "
            f"买方操作战术建议: {tactics}"
        )

        return EventEvaluationResult(
            event_id=event.event_id,
            target_date=event.target_date,
            category=event.category,
            title_zh=event.title_zh,
            days_until_event=days,
            urgency_status=urgency,
            binary_expected_move_pct=round(exp_move, 2),
            odds_ratio=round(odds, 2),
            volatility_arbitrage_verdict=vol_verdict,
            actionable_tactics_zh=tactics,
            narrative_zh=narrative_zh,
            category_zh=category_zh,
            urgency_status_zh=urgency_zh,
        )
