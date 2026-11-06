"""动态三表强勾稽与现金跑道联动引擎 (Integrated Three-Statement & Runway Engine).

遵循 Google Python 编程风格指南与《SPEC-04 六步研究法与官方财报三表契约规范》:
1. 【利润表 (IS)】：从营业收入推导毛利、扣减研发与管理营运费用 (OpEx)、税金，推导净利润；
2. 【资产负债表 (BS) 营运资本动态占用】：
   - 应收账款 (DSO 驱动)、存货 (DIO 驱动) 与应付账款 (DPO 驱动) 的变动自动形成营运资本变动 (Change in Working Capital)；
3. 【现金流量表 (CF) 闭环回流】：
   - 经营现金流 OCF = 净利润 + 折旧摊销 - 营运资本占用；
   - 自由现金流 FCF = OCF - 资本开支 CapEx；
4. 【期末现金动态平衡与跑道压力测试 (Cash Runway Stress Test)】：
   - 期末现金 = 期初现金 + 自由现金流；
   - 动态测算现金烧光 (Cash Exhaustion) 的精确剩余月数；
   - 当剩余月数 < 18 个月时，强制触发股权稀释风险预警。
"""

# 1. Python 标准库
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class BaselineFinancials:
    """基期财务三表输入底稿 (百万单位).

    Attributes:
        ticker: 证券代码 (如 'NVDA', '7203.T').
        cash_and_equivalents: 期初现金及短期投资储备 (百万单位).
        total_debt: 期初总有息负债 (百万单位).
        revenue: 基期年度营业收入 (百万单位).
        gross_margin_pct: 基期毛利率 % (例如 50.0 代表 50%).
        opex_rnd: 研发费用 R&D (百万单位).
        opex_sga: 销售与行政费用 SG&A (百万单位).
        depr_amort: 折旧与摊销 (百万单位).
        capex: 资本性开支 (百万单位).
        tax_rate: 有效企业所得税率 (默认 0.21 即 21%).
        dso_days: 应收账款周转天数 (默认 45.0 天).
        dio_days: 存货周转天数 (默认 30.0 天).
        dpo_days: 应付账款周转天数 (默认 40.0 天).
        market: 交易市场代码 ('US', 'JP', 'CN'，未指定时自适应推导).
        currency_symbol: 显式货币符号 ('$', '¥'，未指定时自适应推导).
    """

    ticker: str
    cash_and_equivalents: float
    total_debt: float
    revenue: float
    gross_margin_pct: float
    opex_rnd: float
    opex_sga: float
    depr_amort: float
    capex: float
    tax_rate: float = 0.21
    dso_days: float = 45.0
    dio_days: float = 30.0
    dpo_days: float = 40.0
    market: Optional[str] = None
    currency_symbol: Optional[str] = None


@dataclass(frozen=True)
class ProjectedYearResult:
    """预测年度三表动态勾稽结果.

    Attributes:
        year_index: 预测年份索引 (1, 2, 3...).
        revenue: 当年营业收入预测 (百万单位).
        gross_profit: 当年毛利润 (百万单位).
        operating_income: 息税前营业利润 EBIT (百万单位).
        net_income: 净利润 (百万单位).
        working_capital_change: 营运资本变动占用 (百万单位，正值表示占用现金).
        operating_cash_flow: 经营活动现金流量净额 OCF (百万单位).
        capex: 当年资本开支 (百万单位).
        free_cash_flow: 当年自由现金流 FCF (百万单位).
        ending_cash: 期末累计现金及等价物 (百万单位).
        ending_net_cash: 期末净现金 (现金 - 总有息负债).
    """

    year_index: int
    revenue: float
    gross_profit: float
    operating_income: float
    net_income: float
    working_capital_change: float
    operating_cash_flow: float
    capex: float
    free_cash_flow: float
    ending_cash: float
    ending_net_cash: float


@dataclass(frozen=True)
class ThreeStatementSimulationResult:
    """全周期动态三表模拟与跑道诊断结果.

    Attributes:
        ticker: 标的代码.
        starting_cash: 期初现金储备 (百万单位).
        runway_months: 现金跑道安全续航月数 (若为正现金流则为 999.0 表示无限续航).
        dilution_risk_level: 股权稀释风险评级中文描述.
        projections: 分年度详细三表预测列表.
        burn_rate_quarterly: 季度净现金消耗速率 (百万单位 / 季).
        verdict_zh: 财务跑道与破产压力测试解读.
        narrative_zh: 买方通俗全息研报卡片.
        currency_symbol: 货币符号 ('$', '¥').
    """

    ticker: str
    starting_cash: float
    runway_months: float
    dilution_risk_level: str
    projections: List[ProjectedYearResult]
    burn_rate_quarterly: float
    verdict_zh: str
    narrative_zh: str = ""
    currency_symbol: str = "$"

    def to_dict(self) -> Dict[str, Any]:
        """序列化为买方可视化卡片字典."""
        curr = self.currency_symbol or "$"
        return {
            "ticker": self.ticker,
            "starting_cash": f"{curr}{self.starting_cash:,.1f}M",
            "runway_months": (
                f"{self.runway_months:.1f} 个月"
                if self.runway_months < 900
                else "无需融资 (正造血飞轮)"
            ),
            "quarterly_burn": f"{curr}{self.burn_rate_quarterly:,.1f}M / 季",
            "dilution_risk": self.dilution_risk_level,
            "verdict": self.verdict_zh,
            "narrative_zh": self.narrative_zh or self.verdict_zh,
            "yearly_forecast": [
                {
                    "year": f"Y+{p.year_index}",
                    "revenue": f"{curr}{p.revenue:,.1f}M",
                    "operating_income": f"{curr}{p.operating_income:,.1f}M",
                    "fcf": f"{curr}{p.free_cash_flow:,.1f}M",
                    "ending_cash": f"{curr}{p.ending_cash:,.1f}M",
                }
                for p in self.projections
            ],
        }


class IntegratedThreeStatementEngine:
    """动态三表勾稽与现金跑道模拟器 (Google Python Style Guide 架构设计)."""

    @classmethod
    def simulate(
        cls,
        base: BaselineFinancials,
        revenue_growths: List[float],
        opex_escalation_pct: float = 5.0,
    ) -> ThreeStatementSimulationResult:
        """执行全生命周期动态三表多年度压力模拟.

        Args:
            base: 基期财务三表事实底稿.
            revenue_growths: 未来若干年复合营业收入增速列表 (例如 [0.20, 0.15, 0.10]).
            opex_escalation_pct: 营运费用年化通胀扩张增幅 % (默认 5.0 代表 5%).

        Returns:
            ThreeStatementSimulationResult 结构化三表勾稽与现金跑道模拟结果.

        Raises:
            ValueError: 当基期营业收入 < 0 或所得税率非法时抛出 (金融数学防御).
        """
        if base.revenue < 0.0:
            raise ValueError(
                f"【金融数学防御】基期营业收入不可为负，收到非法值: {base.revenue}"
            )
        if not (0.0 <= base.tax_rate <= 1.0):
            raise ValueError(
                f"【参数边界防御】所得税率必须在 [0.0, 1.0] 区间内，收到非法值: {base.tax_rate}"
            )

        cur_cash = base.cash_and_equivalents
        cur_debt = base.total_debt
        cur_rev = base.revenue
        cur_rnd = max(0.0, base.opex_rnd)
        cur_sga = max(0.0, base.opex_sga)
        cur_capex = max(0.0, base.capex)
        cur_da = max(0.0, base.depr_amort)

        projections: List[ProjectedYearResult] = []
        for idx, g in enumerate(revenue_growths, 1):
            next_rev = cur_rev * (1.0 + g)
            cogs = next_rev * (1.0 - (base.gross_margin_pct / 100.0))
            gp = next_rev - cogs

            # OpEx 年化通胀膨胀
            cur_rnd *= 1.0 + (opex_escalation_pct / 100.0)
            cur_sga *= 1.0 + (opex_escalation_pct / 100.0)
            ebit = gp - (cur_rnd + cur_sga)

            # 净利润 (所得税保护)
            taxes = max(0.0, ebit * base.tax_rate)
            net_income = ebit - taxes

            # 营运资本变动测算 (严格三表真实动态占用：存货与应付款项随营收与成本同步扩张)
            prev_cogs = cur_rev * (1.0 - (base.gross_margin_pct / 100.0))
            prev_wc = cls._compute_working_capital(
                rev=cur_rev,
                cogs=prev_cogs,
                dso=base.dso_days,
                dio=base.dio_days,
                dpo=base.dpo_days,
            )
            next_wc = cls._compute_working_capital(
                rev=next_rev,
                cogs=cogs,
                dso=base.dso_days,
                dio=base.dio_days,
                dpo=base.dpo_days,
            )
            delta_wc = next_wc - prev_wc

            # 现金流勾稽
            ocf = net_income + cur_da - delta_wc
            fcf = ocf - cur_capex

            # 期末现金闭环更新
            cur_cash += fcf
            cur_net_cash = cur_cash - cur_debt

            projections.append(
                ProjectedYearResult(
                    year_index=idx,
                    revenue=round(next_rev, 2),
                    gross_profit=round(gp, 2),
                    operating_income=round(ebit, 2),
                    net_income=round(net_income, 2),
                    working_capital_change=round(delta_wc, 2),
                    operating_cash_flow=round(ocf, 2),
                    capex=round(cur_capex, 2),
                    free_cash_flow=round(fcf, 2),
                    ending_cash=round(cur_cash, 2),
                    ending_net_cash=round(cur_net_cash, 2),
                )
            )
            cur_rev = next_rev

        curr_sym = cls._resolve_currency_symbol(base)
        runway, burn_q, dilution_level, verdict = cls._evaluate_cash_runway(
            base=base,
            projections=projections,
            curr_sym=curr_sym,
        )

        narrative_zh = cls._render_narrative(
            base=base,
            runway=runway,
            burn_q=burn_q,
            dilution_level=dilution_level,
            verdict=verdict,
            curr_sym=curr_sym,
        )

        return ThreeStatementSimulationResult(
            ticker=base.ticker,
            starting_cash=base.cash_and_equivalents,
            runway_months=round(runway, 1),
            dilution_risk_level=dilution_level,
            projections=projections,
            burn_rate_quarterly=round(burn_q, 2),
            verdict_zh=verdict,
            narrative_zh=narrative_zh,
            currency_symbol=curr_sym,
        )

    # --------------------------------------------------------------------------
    # 私有辅助方法 (Private Helpers, Google Style Guide)
    # --------------------------------------------------------------------------

    @staticmethod
    def _compute_working_capital(
        rev: float, cogs: float, dso: float, dio: float, dpo: float
    ) -> float:
        """根据周转天数测算当期营运资本总额 (私有辅助方法)."""
        ar = (rev * dso) / 365.0
        inv = (cogs * dio) / 365.0
        ap = (cogs * dpo) / 365.0
        return ar + inv - ap

    @staticmethod
    def _resolve_currency_symbol(base: BaselineFinancials) -> str:
        """根据证券代码和市场推导货币符号 (私有辅助方法)."""
        t_up = (base.ticker or "").upper()
        m_up = (base.market or "").upper()
        is_jp = (
            m_up == "JP"
            or t_up.endswith(".T")
            or t_up.endswith(".JP")
            or (t_up.isdigit() and len(t_up) == 4)
        )
        is_cn = (
            m_up == "CN"
            or t_up.endswith(".SS")
            or t_up.endswith(".SZ")
            or (t_up.isdigit() and len(t_up) == 6)
        )
        if base.currency_symbol:
            return base.currency_symbol
        if is_jp or is_cn:
            return "¥"
        return "$"

    @staticmethod
    def _evaluate_cash_runway(
        base: BaselineFinancials,
        projections: List[ProjectedYearResult],
        curr_sym: str,
    ) -> Tuple[float, float, str, str]:
        """测算现金安全跑道月数与股权稀释风险级别 (私有辅助方法)."""
        first_year_fcf = projections[0].free_cash_flow if projections else 0.0
        if first_year_fcf >= 0:
            runway = 999.0
            burn_q = 0.0
            dilution_level = "无稀释风险 (已实现正向自我造血)"
            verdict = (
                "企业已跨越盈亏平衡点，自由现金流充沛，无需依赖外部股权融资，"
                "无任何断头台股权稀释风险。"
            )
            return runway, burn_q, dilution_level, verdict

        annual_burn = abs(first_year_fcf)
        burn_q = annual_burn / 4.0
        safe_cash = max(0.0, base.cash_and_equivalents)
        runway = (safe_cash / max(0.01, annual_burn)) * 12.0

        if safe_cash <= 0.0:
            dilution_level = "极度危急 (现金已枯竭，停摆倒计时)"
            verdict = (
                f"现金储备已彻底耗尽！企业正处于极度危险的断流失血状态（季度净烧钱 {curr_sym}{burn_q:.1f}M），"
                "面临迫在眉睫的紧急配股、债务违约或重组清盘风险。"
            )
        elif runway < 12.0:
            dilution_level = "极高稀释风险 (<12个月，濒临现金枯竭)"
            verdict = (
                f"现金储备仅够维持 {runway:.1f} 个月（季度净烧钱 {curr_sym}{burn_q:.1f}M）。"
                "未来1年内必然启动大规模股权增发配股 (ATM Offering)，面临沉重的每股价值稀释惩罚。"
            )
        elif runway < 24.0:
            dilution_level = "严重警惕 (12-24个月，进入融资倒计时)"
            verdict = (
                f"现金储备可支撑 {runway:.1f} 个月。若管线催化剂未能在18个月内兑现，"
                "管理层将被迫低位增发，建议密切跟踪再融资动向。"
            )
        else:
            dilution_level = "流动性极其充沛 (跑道 >24个月，安全直达远期)"
            verdict = (
                f"现金储备可支撑超 {runway:.1f} 个月（直通远期数据读出期）。"
                "资产负债表极度坚固，管理层无需在低估值时期贱卖股权，为管线商业化留足安全冗余。"
            )

        return runway, burn_q, dilution_level, verdict

    @staticmethod
    def _render_narrative(
        base: BaselineFinancials,
        runway: float,
        burn_q: float,
        dilution_level: str,
        verdict: str,
        curr_sym: str,
    ) -> str:
        """生成买方通俗自然语言研报卡片 (私有辅助方法)."""
        runway_desc = f"{runway:.1f}个月" if runway < 900 else "无限续航 (正造血飞轮)"
        burn_desc = f"{curr_sym}{burn_q:.1f}M / 季" if burn_q > 0 else "无失血 (盈利净回流)"
        return (
            f"【标的 {base.ticker} 动态三表联动与现金跑道全息研报】"
            f"股权稀释风险评级【{dilution_level}】。"
            f"现金流与安全边界: 期初现金及等价物 {curr_sym}{base.cash_and_equivalents:,.1f}M，"
            f"安全现金跑道折合【{runway_desc}】，季度净现金消耗速率 ({burn_desc})。"
            f"买方破产与融资压力研判: {verdict}"
        )
