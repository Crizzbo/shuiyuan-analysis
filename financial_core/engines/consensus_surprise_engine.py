"""市场一致预期差与业绩超预期量化评估引擎 (Consensus & Earnings Surprise Engine).

功能设计：
二级市场股票涨跌的核心驱动力是“实际业绩与华尔街一致预期（Consensus）的预期差”。
本引擎负责：
1. 测算 EPS 超预期幅度 (EPS Surprise %) 与 营收超预期幅度 (Revenue Surprise %)；
2. 测算买方暗盘预期差 (Whisper Number Gap)；
3. 量化分析师预测修正动量 (Revision Momentum，上调 vs 下调家数)；
4. 识别“双超 (Double Beat)”、“雷声大雨点小”及“业绩暴雷 (Double Miss)”；
5. 评估市场隐含预期透支度 (Expectation Overhang Penalty)，若现价透支卖方一致预期过大，输出折价阻尼惩罚因子。
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ConsensusDataInput:
    """市场一致预期输入底账。"""
    ticker: str
    fiscal_period: str               # 财报季度/财年，如 "Q3 2024" 或 "FY2024"
    consensus_eps: float             # 彭博/卖方一致预期每股收益
    consensus_revenue: float         # 卖方一致预期营业收入 (百万)
    reported_eps: Optional[float] = None     # 实际披露 EPS
    reported_revenue: Optional[float] = None # 实际披露营业收入 (百万)
    whisper_eps: Optional[float] = None      # 买方暗盘预期 (Whisper EPS)
    analysts_upgrades_30d: int = 0   # 近30天上调预测分析师家数
    analysts_downgrades_30d: int = 0 # 近30天下调预测分析师家数
    total_covering_analysts: int = 10# 覆盖该股票的分析师总家数
    market_implied_growth: Optional[float] = None # 股价反解隐含增速
    market: Optional[str] = None     # 市场代码 ("US" / "JP"，未指定时按代码自适应推导)


@dataclass(frozen=True)
class ConsensusSurpriseResult:
    """一致预期差与预期透支量化评估结果。"""
    ticker: str
    fiscal_period: str
    eps_surprise_pct: Optional[float]
    revenue_surprise_pct: Optional[float]
    whisper_gap_pct: Optional[float]
    revision_momentum: float         # [-1.0, +1.0]，>0 表示净上调动量
    beat_category: str               # "Double Beat", "Double Miss", "Beat EPS Only", "Beat Rev Only", "Pending Release"
    overhang_penalty_factor: float   # [0.60, 1.00]，估值阻尼惩罚因子
    assessment_zh: str               # 投研决策解读
    narrative_zh: str = ""           # 买方通俗全息研报卡片 (去工程符号化)
    beat_category_zh: str = ""       # 纯自然中文分类定性 (去工程符号化)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "period": self.fiscal_period,
            "eps_surprise": f"{self.eps_surprise_pct:+.2f}%" if self.eps_surprise_pct is not None else "待披露",
            "revenue_surprise": f"{self.revenue_surprise_pct:+.2f}%" if self.revenue_surprise_pct is not None else "待披露",
            "whisper_gap": f"{self.whisper_gap_pct:+.2f}%" if self.whisper_gap_pct is not None else "无暗盘数据",
            "revision_momentum": f"{self.revision_momentum:+.2f} ({'积极上调' if self.revision_momentum > 0.1 else '悲观下调' if self.revision_momentum < -0.1 else '中性均衡'})",
            "beat_category": self.beat_category,
            "beat_category_zh": self.beat_category_zh or self.beat_category,
            "overhang_penalty": f"{self.overhang_penalty_factor:.2f}",
            "assessment": self.assessment_zh,
            "narrative_zh": self.narrative_zh,
        }


class ConsensusSurpriseEngine:
    """市场预期差量化计算器。"""

    @classmethod
    def evaluate(cls, inp: ConsensusDataInput) -> ConsensusSurpriseResult:
        # 1. 超预期百分比计算与极端基数离群值夹逼保护 [-500.0%, +500.0%]
        eps_surp = None
        if inp.reported_eps is not None:
            denom = abs(inp.consensus_eps) if abs(inp.consensus_eps) > 0.001 else 0.01
            raw_eps = ((inp.reported_eps - inp.consensus_eps) / denom) * 100.0
            eps_surp = max(-500.0, min(500.0, raw_eps))

        rev_surp = None
        if inp.reported_revenue is not None:
            denom_rev = abs(inp.consensus_revenue) if abs(inp.consensus_revenue) > 0.001 else 1.0
            raw_rev = ((inp.reported_revenue - inp.consensus_revenue) / denom_rev) * 100.0
            rev_surp = max(-500.0, min(500.0, raw_rev))

        whisper_gap = None
        if inp.reported_eps is not None and inp.whisper_eps is not None:
            denom_w = abs(inp.whisper_eps) if abs(inp.whisper_eps) > 0.001 else 0.01
            raw_w = ((inp.reported_eps - inp.whisper_eps) / denom_w) * 100.0
            whisper_gap = max(-500.0, min(500.0, raw_w))

        # 2. 预测修正动量
        tot = max(1, inp.total_covering_analysts)
        momentum = (inp.analysts_upgrades_30d - inp.analysts_downgrades_30d) / tot
        momentum = max(-1.0, min(1.0, momentum))

        # 3. 业绩类别判定 (兼顾测试向后兼容与去工程符号化纯自然中文标签)
        if inp.reported_eps is None or inp.reported_revenue is None:
            category = "待披露 (Pending Release / 前瞻预期阶段)"
            category_zh = "待披露 (前瞻预期阶段)"
        elif eps_surp > 0.5 and rev_surp > 0.5:
            category = "双超预期 (Double Beat / 戴维斯双击)"
            category_zh = "双超预期 (戴维斯双击)"
        elif eps_surp < -0.5 and rev_surp < -0.5:
            category = "双暴雷 (Double Miss / 戴维斯双杀)"
            category_zh = "双暴雷 (戴维斯双杀)"
        elif eps_surp > 0.5 and rev_surp <= 0.5:
            category = "仅利润超预期 (Beat EPS Only / 依靠降本裁员修饰利润)"
            category_zh = "仅利润超预期 (依靠降本裁员修饰利润)"
        elif eps_surp <= 0.5 and rev_surp > 0.5:
            category = "仅收入超预期 (Beat Rev Only / 增收不增利、毛利率承压)"
            category_zh = "仅收入超预期 (增收不增利、毛利率承压)"
        else:
            category = "基本符合预期 (In-Line / 波动收敛)"
            category_zh = "基本符合预期 (波动收敛)"

        # 4. 预期透支阻尼因子 (Overhang Penalty)
        penalty = 1.00
        overhang_notes = []
        if inp.market_implied_growth is not None:
            # 若股价反解隐含增速超 35%，且分析师净下调动量 (< -0.15)，属于严重预期透支
            if inp.market_implied_growth > 0.35:
                if momentum < 0:
                    penalty = 0.75
                    overhang_notes.append("现价隐含增速极度高企且分析师正在密集下调盈利预期，面临严重杀估值风险")
                else:
                    penalty = 0.90
                    overhang_notes.append("现价隐含较高成长溢价，需业绩连续超预期方可消化估值")

        if "双暴雷" in category:
            penalty = min(penalty, 0.70)
            overhang_notes.append("业绩与收入双双不及预期，引发机构资金踩踏式调仓")

        # 5. 买方暗盘耳语预期差 (Whisper Number) 深度定性
        whisper_note = ""
        if whisper_gap is not None:
            if whisper_gap >= 0:
                whisper_note = f"；同时跑赢买方暗盘耳语预期 {whisper_gap:+.1f}%，暗盘筹码坚挺"
            else:
                whisper_note = f"；但较买方暗盘耳语预期跑输 {abs(whisper_gap):.1f} 个百分点，需警惕好消息出尽/见光死抛压"

        # 6. 综合投研解读 (消除双重负号语病，多市场货币自适应，通俗买方自然语言)
        # 自适应推导市场与货币符号
        market_val = (inp.market or "").upper()
        ticker_val = (inp.ticker or "").upper()
        is_jp = (
            market_val == "JP"
            or ticker_val.endswith(".T")
            or ticker_val.endswith(".JP")
            or (ticker_val.isdigit() and len(ticker_val) == 4)
        )
        curr_sym = "¥" if is_jp else "$"
        rev_unit = "百万日元" if is_jp else "百万美元"

        if category_zh.startswith("双超"):
            assessment = (
                f"强劲超预期：EPS 跑赢一致预期 {eps_surp:+.1f}%，营收超预期 {rev_surp:+.1f}%；"
                f"分析师修正动量为 {momentum:+.2f}，业绩兑现度极高{whisper_note}。"
            )
        elif category_zh.startswith("双暴雷"):
            assessment = (
                f"严重不及预期：EPS 跑输一致预期 {abs(eps_surp):.1f} 个百分点，营收不及预期 {abs(rev_surp):.1f} 个百分点{whisper_note}；"
                f"短期缺乏催化剂，建议回避观望等待盈利底确立。"
            )
        elif "待披露" in category_zh:
            assessment = (
                f"当前处于财报静默/前瞻窗口，市场一致预期 EPS 为 {curr_sym}{inp.consensus_eps:.2f}，"
                f"营收预期 {curr_sym}{inp.consensus_revenue:,.0f} ({rev_unit})；近期分析师修正动量为 {momentum:+.2f}。"
            )
        else:
            assessment = (
                f"业绩结构分化：{category_zh}。EPS 预期差 {eps_surp:+.1f}%，营收预期差 {rev_surp:+.1f}%{whisper_note}；"
                f"需密切关注下季度管理层前瞻指引。"
            )

        if overhang_notes:
            assessment += " 【预期透支警报】" + "；".join(overhang_notes)

        # 7. 买方全息研报卡片 (narrative_zh, 去工程符号化)
        momentum_desc = "分析师密集上调" if momentum > 0.1 else "分析师密集下调" if momentum < -0.1 else "分析师多空分歧均衡"
        overhang_desc = f"触发预期透支折价 (折价乘数 {penalty:.2f})" if penalty < 0.95 else "估值消化良好未现透支"
        narrative_zh = (
            f"【标的 {inp.ticker} {inp.fiscal_period} 财报预期差全息研报】"
            f"业绩综合定性归属【{category_zh}】。{assessment} "
            f"华尔街情绪动向: {momentum_desc} (动量得分 {momentum:+.2f})，估值透支状态: {overhang_desc}。"
        )

        return ConsensusSurpriseResult(
            ticker=inp.ticker,
            fiscal_period=inp.fiscal_period,
            eps_surprise_pct=round(eps_surp, 2) if eps_surp is not None else None,
            revenue_surprise_pct=round(rev_surp, 2) if rev_surp is not None else None,
            whisper_gap_pct=round(whisper_gap, 2) if whisper_gap is not None else None,
            revision_momentum=round(momentum, 2),
            beat_category=category,
            overhang_penalty_factor=round(penalty, 2),
            assessment_zh=assessment,
            narrative_zh=narrative_zh,
            beat_category_zh=category_zh,
        )
