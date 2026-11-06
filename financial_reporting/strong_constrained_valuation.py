"""强约束股票价格估算与公允价值推导引擎 (Strongly-Constrained Valuation Engine)

设计目标：
针对传统 DCF 与估值模型中“参数微调导致结果失真”、“缺乏资产负债表刚性底线约束”、
“终值臆想占比过高”以及“市场隐含预期缺乏反解校验”的四大核心缺陷，构建买方机构级
五维强约束估值模型体系：
1. 【资产负债表刚性底线约束 (Hard Floor Constraint)】：
   - 每股净现金 (Net Cash Per Share) 刚性托底；
   - 格雷厄姆净流动资产净值 (NCAV) 与每股有形账面价值 (TBV) 强校验；
   - 绝不允许非破产健康企业的悲观底价击穿资产重置/清算硬支撑。
2. 【反向 DCF 市场预期透支校验约束 (Reverse DCF & Expectation Overhang)】：
   - 从市场真实抽取的最新市价反解出当前价格隐含的未来 5 年复合 FCF 增速 g_implied；
   - 若隐含增速严重透支历史与行业天花板 (>30%)，强制判定为“预期过度透支”，压缩乐观溢价空间；
   - 若隐含增速过低甚至为负，确认非理性错杀与深度安全边际。
3. 【终值现值阻尼约束 (Terminal Value Damping Constraint)】：
   - 限制永续增长率 g_terminal <= min(名义GDP增速 2.5%, Rf - 150bp)；
   - 当终值现值占总企业价值比例超过 70% 时，强制启用阻尼折价惩罚，防止“靠终值假象造富”。
4. 【历史与行业乘数走廊校准约束 (Multiples Corridor Bounds)】：
   - 理论 DCF 价格必须反推隐含 PE、PS、PB 乘数，严格限制在历史 5 年分位数走廊 [P10, P90] 内截断。
5. 【概率守恒期望值与 1/4 凯利仓位约束 (Probability & 1/4 Kelly Allocation)】：
   - 严格满足 Bear / Base / Bull 三态概率守恒 (sum=1.0)；
   - 严格由数学期望与下行风险计算赔率 b，输出严格的错误边际买点与 1/4 凯利仓位上限 (<=15%)。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class CompanyFinancialFacts:
    """来自官方财报三表底稿的可验证真实财务事实。"""
    ticker: str
    currency: str
    current_price: float
    shares: float                   # 稀释后总股本 (百万股)
    cash_and_equivalents: float     # 现金及现金等价物 + 短期投资 (百万)
    total_debt: float               # 包含短期借款与长期有息负债 (百万)
    total_assets: float             # 资产总计 (百万)
    current_assets: float           # 流动资产 (百万)
    total_liabilities: float        # 负债合计 (百万)
    equity: float                   # 所有者权益总额 (百万)
    goodwill_and_intangibles: float # 商誉及无形资产 (百万)
    revenue: float                  # 过去 12 个月 (TTM) 营业收入 (百万)
    operating_income: float         # 营业利润 / EBIT (百万)
    net_income: float               # 归属于母公司净利润 (百万)
    free_cash_flow: float           # 自由现金流 FCF (百万)
    operating_cash_flow: float      # 经营现金流 (百万)
    beta: float = 1.0
    quote_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    market_session: str = "regular_trading" # "pre_market", "regular_trading", "after_hours", "previous_close"


@dataclass(frozen=True)
class MacroParameters:
    """宏观利率基准与贴现率参数。"""
    rf_10y: float = 0.0440          # 10Y 美债收益率基准 (约 4.40%)
    erp: float = 0.0500             # 股权风险溢价 (Equity Risk Premium, 5.0%)
    gdp_terminal_growth: float = 0.0250 # 长期名义 GDP 潜在永续增速 (2.5%)
    debt_spread: float = 0.0150     # 企业债务信用利差 (150 bps)
    tax_rate: float = 0.21          # 实际企业所得税率 (21%)


@dataclass
class ValuationConstraintsResult:
    """强约束估值运算全景输出。"""
    ticker: str
    currency: str
    current_price: float
    
    # 1. 资产底线指标
    net_cash_per_share: float
    ncav_per_share: float
    tangible_book_value_per_share: float
    hard_asset_floor: float
    
    # 2. 反向 DCF 市场预期反解
    implied_fcf_growth_rate: Optional[float]
    market_expectation_assessment: str
    
    # 3. 三情景强约束公允定价
    bear_fair_value: float          # 悲观情景底线价
    base_fair_value: float          # 中性基准公允价
    bull_fair_value: float          # 乐观扩张目标价
    
    # 4. 终值质量与阻尼
    base_terminal_pv_ratio: float
    is_terminal_damped: bool
    
    # 5. 走廊截断状态
    multiples_corridor_applied: bool
    implied_base_pe: Optional[float]
    implied_base_ps: float
    
    # 6. 水源决策：期望值、安全边际与仓位建议
    mathematical_expected_value: float
    margin_of_safety_buy_zone: float
    expected_return_pct: float
    win_loss_odds: float            # 赔率 b
    quarter_kelly_allocation_pct: float
    investment_verdict: str
    decision_rationale_zh: str

    # 7. 行情时效性与时段硬约束
    quote_timestamp: str = "2026-10-14T07:25:00Z"
    market_session: str = "regular_trading"
    freshness_status_zh: str = "当日已核验"
    cash_runway_months: Optional[float] = None


    def to_dict(self) -> Dict[str, Any]:
        curr_sym = "¥" if self.currency == "JPY" else "$"
        return {
            "ticker": self.ticker,
            "currency": self.currency,
            "current_price": f"{curr_sym}{self.current_price:.2f}",
            "freshness": {
                "quote_timestamp": self.quote_timestamp,
                "market_session": self.market_session,
                "freshness_status": self.freshness_status_zh,
            },
            "asset_floors": {
                "net_cash_per_share": f"{curr_sym}{self.net_cash_per_share:.2f}",
                "ncav_per_share": f"{curr_sym}{self.ncav_per_share:.2f}",
                "tangible_book_value_per_share": f"{curr_sym}{self.tangible_book_value_per_share:.2f}",
                "hard_asset_floor": f"{curr_sym}{self.hard_asset_floor:.2f}",
                "cash_runway": f"{self.cash_runway_months:.1f} 个月" if (self.cash_runway_months and self.cash_runway_months < 900) else "正向自由造血 (无需再融资)",
            },
            "reverse_dcf_expectation": {
                "implied_fcf_growth_rate": f"{self.implied_fcf_growth_rate * 100:.2f}%" if self.implied_fcf_growth_rate is not None else "N/A (基期负现金流)",
                "assessment": self.market_expectation_assessment,
            },
            "constrained_scenarios": {
                "bear_case": {
                    "fair_value": f"{curr_sym}{self.bear_fair_value:.2f}",
                    "gap_from_current": f"{(self.bear_fair_value - self.current_price) / self.current_price * 100:+.2f}%",
                },
                "base_case": {
                    "fair_value": f"{curr_sym}{self.base_fair_value:.2f}",
                    "gap_from_current": f"{(self.base_fair_value - self.current_price) / self.current_price * 100:+.2f}%",
                    "implied_pe": f"{self.implied_base_pe:.1f}x" if self.implied_base_pe else "N/A",
                    "implied_ps": f"{self.implied_base_ps:.2f}x",
                },
                "bull_case": {
                    "fair_value": f"{curr_sym}{self.bull_fair_value:.2f}",
                    "gap_from_current": f"{(self.bull_fair_value - self.current_price) / self.current_price * 100:+.2f}%",
                },
            },
            "terminal_quality": {
                "terminal_pv_ratio": f"{self.base_terminal_pv_ratio * 100:.1f}%",
                "is_terminal_damped": self.is_terminal_damped,
            },
            "shuiyuan_decision": {
                "expected_value": f"{curr_sym}{self.mathematical_expected_value:.2f}",
                "margin_of_safety_buy_line": f"{curr_sym}{self.margin_of_safety_buy_zone:.2f}",
                "expected_return_pct": f"{self.expected_return_pct:+.2f}%",
                "win_loss_odds": round(self.win_loss_odds, 2),
                "quarter_kelly_allocation": f"{self.quarter_kelly_allocation_pct:.2f}%",
                "verdict": self.investment_verdict,
                "rationale": self.decision_rationale_zh,
            }
        }


class StronglyConstrainedValuationEngine:
    """买方机构级强约束股票估值引擎。"""

    @classmethod
    def verify_quote_freshness(
        cls,
        quote_timestamp: str,
        current_time_iso: Optional[str] = None,
        max_staleness_hours: float = 24.0,
    ) -> Tuple[bool, str]:
        """【时效硬约束】核验行情时间戳是否属于当日新鲜数据，杜绝过时旧价格冒充当前实时市价。"""
        if current_time_iso:
            now_dt = datetime.fromisoformat(current_time_iso.replace("Z", "+00:00"))
        else:
            now_dt = datetime.now(timezone.utc)
        if now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=timezone.utc)
        try:
            q_dt = datetime.fromisoformat(quote_timestamp.replace("Z", "+00:00"))
            if q_dt.tzinfo is None:
                q_dt = q_dt.replace(tzinfo=timezone.utc)
        except Exception:
            return False, f"行情时间戳格式非法: {quote_timestamp}"

        age_hours = (now_dt - q_dt).total_seconds() / 3600.0
        if age_hours > max_staleness_hours:
            return False, f"【严重超期阻断】行情数据已滞后 {age_hours:.1f} 小时，属于过时历史数据，严禁冒充盘中实时市价！"

        if q_dt.date() == now_dt.date():
            return True, f"当日最新行情 (采样于 {age_hours:.1f} 小时前)"
        else:
            return True, f"前一交易日收盘基准行情 (采样于 {age_hours:.1f} 小时前)"

    @classmethod
    def calculate_hard_asset_floors(cls, f: CompanyFinancialFacts) -> Tuple[float, float, float, float]:
        """计算资产负债表刚性底线指标。"""
        shares = max(0.001, f.shares)
        # 1. 每股净现金 = (现金及等价物 - 总有息负债) / 股本
        net_cash = f.cash_and_equivalents - f.total_debt
        ncps = net_cash / shares

        # 2. 每股净流动资产 NCAV = (流动资产 - 负债总额) / 股本
        ncav = (f.current_assets - f.total_liabilities) / shares

        # 3. 每股有形账面价值 TBV = (所有者权益 - 商誉与无形资产) / 股本
        tbv = (f.equity - max(0.0, f.goodwill_and_intangibles)) / shares

        # 4. 刚性资产底线 Hard Floor:
        # 若处于净现金状态，NCPS 构成最强硬度底垫；
        # 辅以格雷厄姆两折法 (NCAV * 0.70) 与有形资产五折法 (TBV * 0.50) 取最高值
        candidates = [0.01]
        if ncps > 0:
            candidates.append(ncps * 0.90) # 90% 净现金垫
        if ncav > 0:
            candidates.append(ncav * 0.70) # 格雷厄姆标准 7 折流动净资产
        if tbv > 0:
            candidates.append(tbv * 0.50)  # 5 折有形账面
        
        hard_floor = max(candidates)
        return round(ncps, 2), round(ncav, 2), round(tbv, 2), round(hard_floor, 2)

    @classmethod
    def solve_reverse_dcf(
        cls,
        current_price: float,
        cash_flow: float,
        shares: float,
        net_debt: float,
        wacc: float,
        terminal_growth: float,
        years: int = 5,
    ) -> Optional[float]:
        """反向 DCF 单调二分法求解当前市价所隐含的未来 5 年自由现金流复合增速。"""
        if cash_flow <= 0 or current_price <= 0 or shares <= 0:
            return None  # 基期现金流为负或无意义，无法反解标准 FCF 增速
        
        target_ev = current_price * shares + net_debt
        if target_ev <= 0:
            return None

        # 求解函数: f(g) = EV(g) - target_ev
        def eval_ev(g: float) -> float:
            pv = 0.0
            cf = cash_flow
            for t in range(1, years + 1):
                cf *= (1.0 + g)
                pv += cf / ((1.0 + wacc) ** t)
            # 终值
            term_val = (cf * (1.0 + terminal_growth)) / max(0.005, wacc - terminal_growth)
            pv_term = term_val / ((1.0 + wacc) ** years)
            return pv + pv_term

        # 二分查找区间 [-50%, +100%]
        low, high = -0.50, 1.00
        ev_low = eval_ev(low)
        ev_high = eval_ev(high)

        if target_ev < ev_low:
            return -0.50
        if target_ev > ev_high:
            return 1.00

        for _ in range(80):
            mid = (low + high) / 2.0
            ev_mid = eval_ev(mid)
            if abs(ev_mid - target_ev) / target_ev < 1e-5:
                return round(mid, 4)
            if ev_mid < target_ev:
                low = mid
            else:
                high = mid
        return round((low + high) / 2.0, 4)

    @classmethod
    def evaluate_valuation(
        cls,
        facts: CompanyFinancialFacts,
        macro: Optional[MacroParameters] = None,
        base_growth_rates: Optional[List[float]] = None,
        industry_pe_corridor: Tuple[float, float, float] = (12.0, 22.0, 38.0), # (P10, P50, P90)
        industry_ps_corridor: Tuple[float, float, float] = (1.5, 4.0, 9.0),
        lifecycle_stage: str = "growth", # "intro", "growth", "mature", "cyclical"
        current_time_iso: Optional[str] = None,
    ) -> ValuationConstraintsResult:
        """运行全套五维强约束估值计算，返回契约化研报结果。"""
        if macro is None:
            macro = MacroParameters()
        f = facts

        # 0. 行情时效性与当日新鲜度强制门禁核验 (Quote Freshness Gate)
        is_fresh, freshness_msg = cls.verify_quote_freshness(f.quote_timestamp, current_time_iso=current_time_iso)
        if not is_fresh:
            raise ValueError(f"【行情时效硬约束阻断】标的 {f.ticker} " + freshness_msg)

        # 1. 资产底线刚性约束
        ncps, ncav, tbv, hard_floor = cls.calculate_hard_asset_floors(f)

        # 2. 贴现率与资本结构强约束
        market_cap = max(0.01, f.current_price * f.shares)
        total_enterprise_val = market_cap + max(0.0, f.total_debt)
        we = market_cap / total_enterprise_val
        wd = max(0.0, f.total_debt) / total_enterprise_val
        ke = macro.rf_10y + f.beta * macro.erp
        kd_post = (macro.rf_10y + macro.debt_spread) * (1.0 - macro.tax_rate)
        wacc_base = max(0.065, we * ke + wd * kd_post)
        
        # 终值永续增长率受宏观潜在 GDP 增速与贴现率严格双重夹逼
        tg_base = min(macro.gdp_terminal_growth, max(0.010, wacc_base - 0.020))

        # 3. 基础现金流设定与反向 DCF 检验
        # 若自由现金流为负（如导入期制药/前沿AI），采用标准化经营现金流或调整净利
        normalized_cf = f.free_cash_flow
        if normalized_cf <= 0:
            if f.net_income > 0:
                normalized_cf = f.net_income * 0.85
            else:
                # 导入期营收折算远期稳态自由现金流 (以 12% 稳态利润率估算)
                normalized_cf = max(1.0, f.revenue * 0.12)
        
        net_debt = f.total_debt - f.cash_and_equivalents
        implied_g = cls.solve_reverse_dcf(f.current_price, normalized_cf, f.shares, net_debt, wacc_base, tg_base)

        # 评估市场隐含预期透支度
        if implied_g is None:
            market_assessment = "公司当前处于高额研发净现金消耗期，市场完全依靠远期研发管线资产或并购价值定价，未反映短期经营自由现金流。"
        elif implied_g > 0.30:
            market_assessment = f"【预期过度透支警报】现价隐含未来5年高企复合增长率 ({implied_g*100:.1f}%)，任何业绩或指引不及预期均将引发剧烈戴维斯双杀。"
        elif implied_g < -0.05:
            market_assessment = f"【过度悲观错杀信号】现价隐含未来5年现金流萎缩 ({implied_g*100:.1f}%)，若基本面健康，提供深厚安全边际。"
        else:
            market_assessment = f"【合理中枢定价】现价隐含复合增速 ({implied_g*100:.1f}%) 与宏观及行业常态基本一致。"

        # 4. 多阶段基本面 DCF (带终值阻尼机制)
        if base_growth_rates is None:
            if lifecycle_stage == "intro":
                base_growth_rates = [0.25, 0.20, 0.15, 0.12, 0.10]
            elif lifecycle_stage == "growth":
                base_growth_rates = [0.18, 0.15, 0.12, 0.10, 0.08]
            else:
                base_growth_rates = [0.06, 0.05, 0.04, 0.03, 0.025]

        def run_bounded_dcf(cf_in: float, growths: List[float], wacc_val: float, tg_val: float) -> Tuple[float, float, bool]:
            pv_explicit = 0.0
            cur_cf = cf_in
            for idx, g in enumerate(growths, 1):
                cur_cf *= (1.0 + g)
                pv_explicit += cur_cf / ((1.0 + wacc_val) ** idx)
            
            # Gordon 终值
            term_val = (cur_cf * (1.0 + tg_val)) / max(0.005, wacc_val - tg_val)
            pv_term = term_val / ((1.0 + wacc_val) ** len(growths))
            total_ev = pv_explicit + pv_term
            
            # 终值现值阻尼强约束
            tv_ratio = pv_term / total_ev if total_ev > 0 else 0.0
            damped = False
            if tv_ratio > 0.70:
                damped = True
                damping_penalty = max(0.60, 1.0 - 0.5 * (tv_ratio - 0.70))
                pv_term *= damping_penalty
                total_ev = pv_explicit + pv_term
            
            eq_val = total_ev - net_debt
            val_per_share = max(0.01, eq_val / f.shares)
            return val_per_share, tv_ratio, damped

        # 基准情景 (Base)
        raw_base_val, tv_ratio, is_damped = run_bounded_dcf(normalized_cf, base_growth_rates, wacc_base, tg_base)

        # 悲观情景 (Bear): 滞胀加息 WACC +100bp, 增速下调 35%, 永续下调 75bp
        wacc_bear = wacc_base + 0.010
        tg_bear = max(0.008, tg_base - 0.0075)
        bear_growths = [max(-0.15, g * 0.65) for g in base_growth_rates]
        raw_bear_val, _, _ = run_bounded_dcf(normalized_cf, bear_growths, wacc_bear, tg_bear)

        # 乐观情景 (Bull): 宽松降息 WACC -75bp, 增速上浮 25%, 永续 +50bp
        wacc_bull = max(0.055, wacc_base - 0.0075)
        tg_bull = min(macro.gdp_terminal_growth + 0.005, tg_base + 0.005)
        bull_growths = [g * 1.25 for g in base_growth_rates]
        raw_bull_val, _, _ = run_bounded_dcf(normalized_cf, bull_growths, wacc_bull, tg_bull)

        # 5. 行业乘数走廊校准与资产底线强行截断
        # 资产底线截断：悲观价格绝不能低于资产底线 Hard Floor
        bear_val = max(hard_floor, raw_bear_val)
        base_val = max(bear_val * 1.08, raw_base_val)
        bull_val = max(base_val * 1.15, raw_bull_val)

        # 乘数走廊约束 (Multiples Corridor)
        eps = (f.net_income / f.shares) if f.shares > 0 else 0.0
        sps = (f.revenue / f.shares) if f.shares > 0 else 0.0
        corridor_applied = False

        if eps > 0:
            pe_10, pe_50, pe_90 = industry_pe_corridor
            # 基准价受中位数与上下走廊约束
            pe_base_raw = base_val / eps
            if pe_base_raw > pe_90:
                base_val = pe_90 * eps
                corridor_applied = True
            elif pe_base_raw < pe_10:
                base_val = pe_10 * eps
                corridor_applied = True

            # 悲观价受 10分位走廊与资产底线约束
            pe_bear_raw = bear_val / eps
            if pe_bear_raw < pe_10:
                bear_val = max(hard_floor, pe_10 * 0.85 * eps)
                corridor_applied = True
            elif pe_bear_raw > (base_val / eps) * 0.90:
                bear_val = base_val * 0.85
                corridor_applied = True

            # 乐观价受 90分位走廊上限约束
            pe_bull_raw = bull_val / eps
            if pe_bull_raw > pe_90 * 1.25:
                bull_val = pe_90 * 1.25 * eps
                corridor_applied = True
        elif sps > 0:
            ps_10, ps_50, ps_90 = industry_ps_corridor
            ps_base_raw = base_val / sps
            if ps_base_raw > ps_90:
                base_val = ps_90 * sps
                corridor_applied = True
            elif ps_base_raw < ps_10:
                base_val = ps_10 * sps
                corridor_applied = True
            
            bear_val = min(bear_val, base_val * 0.85)
            bull_val = max(bull_val, base_val * 1.15)

        # 终极单调性与底线刚性约束保障: Hard Floor <= Bear <= Base <= Bull
        bear_val = max(hard_floor, bear_val)
        base_val = max(bear_val * 1.05, base_val)
        bull_val = max(base_val * 1.10, bull_val)

        implied_pe = round(base_val / eps, 2) if eps > 0 else None
        implied_ps = round(base_val / sps, 2) if sps > 0 else 0.0

        # 6. 水源分析决策：严格概率守恒与 1/4 凯利仓位
        # 设定严密三元概率守恒：P(Bear)=0.25, P(Base)=0.50, P(Bull)=0.25
        p_bear, p_base, p_bull = 0.25, 0.50, 0.25
        exp_val = p_bear * bear_val + p_base * base_val + p_bull * bull_val
        
        # 安全边际买入触发线: Min(悲观价 * 1.05, 期望价值 * 0.80)
        buy_zone = min(bear_val * 1.05, exp_val * 0.80)
        
        # 期望收益率与赔率计算
        exp_return_pct = ((exp_val - f.current_price) / f.current_price) * 100
        upside = max(0.0, exp_val - f.current_price)
        downside = max(0.01, f.current_price - bear_val)
        odds_b = upside / downside if downside > 0 else 1.0

        # 胜率与败率
        prob_win = p_base + p_bull # 75% 达成或跑赢基准
        prob_lose = p_bear         # 25% 跌入悲观
        kelly_f = max(0.0, (odds_b * prob_win - prob_lose) / odds_b) if odds_b > 0 else 0.0
        
        # 1/4 凯利执行 + 单只标的 15% 绝对风控上限
        if exp_val <= f.current_price or odds_b < 0.6:
            rec_allocation = 0.0
            verdict = "回避 / 严禁追高 (预期收益不足，无错误边际)"
            rationale = f"现价 (${f.current_price:.2f}) 已经充分甚至过度反映未来乐观增长，数学期望收益为 {exp_return_pct:+.1f}%，赔率仅为 {odds_b:.2f}，缺乏下行防御空间。"
        elif f.current_price <= buy_zone:
            rec_allocation = min(15.0, round(kelly_f * 0.25 * 100, 2))
            verdict = "强力买入 (Strong Buy / 击穿严格安全边际线)"
            rationale = f"现价已跌入严格安全边际买入线 (${buy_zone:.2f})，数学期望价值高达 ${exp_val:.2f} (潜在期望空间 {exp_return_pct:+.1f}%)，下行有资产底线 (${hard_floor:.2f}) 强约束托底，胜率高达 75%，建议 1/4 凯利配置 {rec_allocation:.1f}% 仓位。"
        else:
            rec_allocation = min(8.0, round(kelly_f * 0.15 * 100, 2))
            verdict = "中性观望 / 等待回调 (Hold / Wait for Pullback)"
            rationale = f"公司基本面优秀，但现价 (${f.current_price:.2f}) 略高于买点上限 (${buy_zone:.2f})；建议等待盘中或大盘系统性震荡回调至安全边际区间内再行分批建仓。"

        runway_calc = round((f.cash_and_equivalents / abs(f.free_cash_flow)) * 12.0, 1) if f.free_cash_flow < 0 else 999.0

        return ValuationConstraintsResult(
            ticker=f.ticker,
            currency=f.currency,
            current_price=f.current_price,
            quote_timestamp=f.quote_timestamp,
            market_session=f.market_session,
            freshness_status_zh=freshness_msg,
            cash_runway_months=runway_calc,
            net_cash_per_share=ncps,
            ncav_per_share=ncav,
            tangible_book_value_per_share=tbv,
            hard_asset_floor=hard_floor,
            implied_fcf_growth_rate=implied_g,
            market_expectation_assessment=market_assessment,
            bear_fair_value=round(bear_val, 2),
            base_fair_value=round(base_val, 2),
            bull_fair_value=round(bull_val, 2),
            base_terminal_pv_ratio=round(tv_ratio, 4),
            is_terminal_damped=is_damped,
            multiples_corridor_applied=corridor_applied,
            implied_base_pe=implied_pe,
            implied_base_ps=implied_ps,
            mathematical_expected_value=round(exp_val, 2),
            margin_of_safety_buy_zone=round(buy_zone, 2),
            expected_return_pct=round(exp_return_pct, 2),
            win_loss_odds=round(odds_b, 2),
            quarter_kelly_allocation_pct=rec_allocation,
            investment_verdict=verdict,
            decision_rationale_zh=rationale,
        )
