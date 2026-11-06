"""微观筹码博弈、空头挤压与主力资金流向分析引擎 (Microstructure & Flow Engine).

功能设计：
量化分析二级市场真实的微观博弈与资金流动性环境：
1. 测算做空持仓占比 (Short Interest % of Float)；
2. 测算空头回补天数 (Days to Cover / Short Interest Ratio)；
3. 追踪借券年化利率成本 (Cost to Borrow, CTB) 与利用率 (Utilization %)；
4. 输出 0-100 空头轧空脆弱度指数 (Short Squeeze Vulnerability Score)；
5. 监控 Form 4 内部人高管净增持/减持态势；
6. 监控 13F 顶级买方机构季度调仓流向，提供非对称高赔率交易信号。
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class MicrostructureInput:
    """微观筹码与博弈输入数据。"""
    ticker: str
    current_price: float
    float_shares: float               # 真实自由流通股本 (百万股)
    short_interest_shares: float      # 空头持仓总股数 (百万股)
    average_daily_volume_30d: float   # 30日日均成交量 (百万股)
    cost_to_borrow_pct: float         # 借券年化费率 % (如 25.5 代表 25.5%)
    borrow_utilization_pct: float = 50.0 # 借券池利用率 % (0-100%)
    insider_buy_shares_90d: float = 0.0  # 董事高管近90天公开市场增持股数 (百万)
    insider_sell_shares_90d: float = 0.0 # 董事高管近90天公开市场减持股数 (百万)
    institutional_ownership_pct: float = 60.0 # 机构持仓占流通股比例 %
    top10_inst_net_flow_shares: float = 0.0   # 前十大机构近一季度净买入/净卖出股数 (百万)


@dataclass(frozen=True)
class MicrostructureResult:
    """微观筹码量化分析结果。"""
    ticker: str
    short_percent_of_float: float     # 做空比例 %
    days_to_cover: float              # 空头回补天数
    cost_to_borrow_pct: float
    squeeze_score: float              # [0, 100] 轧空潜能综合得分
    squeeze_risk_level: str           # "极高 (Extreme / 随时可能逼空爆发)", "显著 (High)", "中等 (Moderate)", "低 (Low / 筹码稳定)"
    insider_flow_status: str          # "内部人积极自购增持", "内部人集中减持抛售", "中性均衡"
    institutional_accumulation_desc: str # 机构建仓动向
    tactical_implication_zh: str      # 实盘博弈策略建议
    narrative_zh: str = ""           # 买方通俗全息研报卡片 (去工程符号化)
    squeeze_risk_level_zh: str = ""  # 纯自然中文轧空风险定性 (去工程符号化)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "short_metrics": {
                "short_percent_of_float": f"{self.short_percent_of_float:.2f}%",
                "days_to_cover": f"{self.days_to_cover:.1f} 天",
                "cost_to_borrow": f"{self.cost_to_borrow_pct:.2f}%",
                "squeeze_score": f"{self.squeeze_score:.1f} / 100",
                "squeeze_risk_level": self.squeeze_risk_level,
                "squeeze_risk_level_zh": self.squeeze_risk_level_zh or self.squeeze_risk_level,
            },
            "ownership_and_insiders": {
                "insider_status": self.insider_flow_status,
                "institutional_trend": self.institutional_accumulation_desc,
            },
            "tactical_implication": self.tactical_implication_zh,
            "narrative_zh": self.narrative_zh,
        }


class MicrostructureFlowEngine:
    """微观筹码量化分析器。"""

    @classmethod
    def evaluate(cls, inp: MicrostructureInput) -> MicrostructureResult:
        # 金融边界与除零除负防御
        fl = max(0.01, float(inp.float_shares))
        si_shares = max(0.0, float(inp.short_interest_shares))
        si_pct = min(150.0, (si_shares / fl) * 100.0)

        adv = max(0.001, float(inp.average_daily_volume_30d))
        raw_dtc = si_shares / adv
        # 离群值防御：日均成交量极小时将回补天数封顶至 100 天，防止数值爆炸
        dtc = min(100.0, raw_dtc)
        safe_ctb = max(0.0, float(inp.cost_to_borrow_pct))
        safe_util = max(0.0, min(100.0, float(inp.borrow_utilization_pct)))

        # 1. 轧空脆弱度综合评分 (0-100，刚性数值边界与除零除负防御)
        # 因子1: 做空比例 SI % (满分35分, SI >= 30% 即达满分)
        f_si = max(0.0, min(35.0, (si_pct / 30.0) * 35.0))
        # 因子2: 借券利率 CTB % (满分25分, CTB >= 50% 达满分)
        f_ctb = max(0.0, min(25.0, (safe_ctb / 50.0) * 25.0))
        # 因子3: 回补天数 DTC (满分25分, DTC >= 10天 达满分)
        f_dtc = max(0.0, min(25.0, (dtc / 10.0) * 25.0))
        # 因子4: 利用率 (满分15分, Util >= 90% 达满分)
        f_util = max(0.0, min(15.0, (safe_util / 90.0) * 15.0))

        squeeze_score = max(0.0, min(100.0, round(f_si + f_ctb + f_dtc + f_util, 1)))

        if squeeze_score >= 75.0:
            squeeze_level = "极高 (Extreme / 典型空头拥挤、强催化剂将引爆非线性逼空)"
            squeeze_level_zh = "极度拥挤 (强催化将引爆非线性逼空)"
        elif squeeze_score >= 50.0:
            squeeze_level = "显著 (High / 空头成本高企、具备高弹性反弹空间)"
            squeeze_level_zh = "显著承压 (空头成本高企/具备反弹弹性)"
        elif squeeze_score >= 25.0:
            squeeze_level = "中等 (Moderate / 正常空头头寸对冲)"
            squeeze_level_zh = "中等均衡 (正常套保与头寸对冲)"
        else:
            squeeze_level = "低 (Low / 筹码分散健康、无显著轧空潜能)"
            squeeze_level_zh = "低位平稳 (筹码分散健康/无轧空风险)"

        # 2. 内部人交易行为判定
        net_insider = inp.insider_buy_shares_90d - inp.insider_sell_shares_90d
        if inp.insider_buy_shares_90d > 0.05 and net_insider > 0:
            insider_status = f"内部人积极自购增持 (近90天净买入 {net_insider:.2f}M 股，彰显高管强烈信心)"
        elif inp.insider_sell_shares_90d > 0.50 and net_insider < -0.30:
            insider_status = f"内部人集中抛售减持 (近90天净卖出 {abs(net_insider):.2f}M 股，警惕估值偏高套现)"
        else:
            insider_status = "内部人中性均衡 (常规薪酬计划行权或零交易)"

        # 3. 顶级机构建仓动向
        if inp.top10_inst_net_flow_shares > 1.0:
            inst_trend = f"买方机构显著净增持 (+{inp.top10_inst_net_flow_shares:.1f}M 股)，主力长线资金筑底抱团"
        elif inp.top10_inst_net_flow_shares < -1.0:
            inst_trend = f"机构资金持续流出减持 ({abs(inp.top10_inst_net_flow_shares):.1f}M 股)，存量博弈缺乏增量接盘"
        else:
            inst_trend = f"机构持仓稳健 (总占比 {inp.institutional_ownership_pct:.1f}%)，多空分歧均衡"

        # 4. 实盘博弈交易战术指引 (结合 DTC 回补周期深度的差异化研判，对齐 75.0 阈值)
        if squeeze_score >= 75.0:
            dtc_clause = (
                f"回补需耗时 {dtc:.1f} 个交易日，回补周期漫长极易引发踩踏式断层拉升"
                if dtc >= 5.0
                else f"回补需耗时 {dtc:.1f} 个交易日，多呈现为短线急促高换手博弈"
            )
            tactical = (
                f"做空比例极高达 {si_pct:.1f}%，{dtc_clause}，借券成本高达 {safe_ctb:.1f}%。"
                f"若配合重大基本面催化剂读出，极易触发剧烈空头踩踏轧空 (Short Squeeze)。建议持有正股的同时，"
                f"可少量配置浅虚值看涨期权博弈非对称暴力拉升，但严禁追高追在逼空顶点。"
            )
        elif si_pct > 15.0 and net_insider < -0.5:
            tactical = (
                f"做空比例偏高达 {si_pct:.1f}%，但伴随高管抛售减持，表明基本面可能存在潜在隐患，"
                f"反弹常为诱多，切忌盲目押注逼空，需坚守严格资产底线再行考虑介入。"
            )
        else:
            tactical = (
                f"筹码结构健康均衡 (做空比例仅 {si_pct:.1f}%)，定价主要由基本面与业绩预期差主导，"
                f"按传统估值安全边际与凯利原则建仓即可。"
            )

        # 5. 生成通俗买方自然全息研报卡片 (去工程符号化)
        narrative_zh = (
            f"【标的 {inp.ticker} 微观筹码与博弈流动性全息研报】"
            f"空头轧空脆弱度评级【{squeeze_level_zh}】(轧空得分 {squeeze_score:.1f}/100)。"
            f"空头仓位现状: 做空占比流通盘 {si_pct:.1f}%，空头回补天数 {dtc:.1f} 天，借券年化费率 {safe_ctb:.1f}%。"
            f"关键筹码动向: {insider_status}；{inst_trend}。"
            f"买方博弈战术建议: {tactical}"
        )

        return MicrostructureResult(
            ticker=inp.ticker,
            short_percent_of_float=round(si_pct, 2),
            days_to_cover=round(dtc, 2),
            cost_to_borrow_pct=round(safe_ctb, 2),
            squeeze_score=squeeze_score,
            squeeze_risk_level=squeeze_level,
            insider_flow_status=insider_status,
            institutional_accumulation_desc=inst_trend,
            tactical_implication_zh=tactical,
            narrative_zh=narrative_zh,
            squeeze_risk_level_zh=squeeze_level_zh,
        )
