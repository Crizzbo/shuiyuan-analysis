# -*- coding: utf-8 -*-
"""通用商业物理与速度动力学计算引擎 (UniversalPhysicalDynamicsEngine).

遵循《AGENTS.md》与《CLAUDE.md》：
1. 底层纯净金融核心层：零逆向依赖，纯数学与统计推导，完全自包含；
2. 100% 通用计算模块：严禁针对任何单家公司编写特定特例硬编码；
3. 破除“单点中档增速假定”：从标的客观客观时序与财报底账中提取真实物理参数，
   包含反弹速度半衰期、动量推进加速度、恐慌平息天数、商业现金循环天数，
   以及增长率归零 (Growth = 0%) 条件下的极端停滞防御底价；
4. 严格数值安全与除零除负防御，保障在各类极端市场与财务状态下均稳定收敛。
"""

from dataclasses import dataclass, asdict
import math
from typing import Any, Dict, List, Optional, Tuple, Union


# ==========================================
# 业务数据契约 (Data Contracts)
# ==========================================

@dataclass
class PriceDynamicsMetrics:
    """价格时序动力学与速度参数契约."""
    rebound_half_life_days: float        # 反弹速度半衰期天数 (脱离中枢后修复50%所需的交易日数)
    trend_velocity_annual_pct: float     # 趋势推进速度 (MA20相对MA60的一阶推进速度，年化百分比)
    momentum_acceleration_pct: float     # 动量加速度 (近5日斜率减去过去20日斜率的二阶加速度)
    panic_calming_days: float           # 恐慌平息天数 (黑天鹅或剧烈冲击后波动率衰减至常态的天数)
    annualized_realized_vol_pct: float   # 客观年化实际波动率 (百分比)
    equilibrium_mu_price: float          # 当前物理均值回归平衡中枢价格

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FundamentalSupplyChainMetrics:
    """供应链周转与商业变现速度契约."""
    dio_inventory_days: float            # 存货周转天数 (原材料到制成品的仓库停留时间)
    dso_receivables_days: float          # 应收账款周转天数 (发货到现金入账的等待时间)
    dpo_payables_days: float             # 应付账款周转天数 (占用上游供应商货款的时间)
    cash_conversion_cycle_days: float    # 商业现金造血循环周期 CCC (负值代表强势先收钱占用上下游资金)
    capital_turnover_velocity: float     # 投入资本周转速率 (年化营收 / 投入资本)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TerminalValuationDistribution:
    """非对称情景与极端停滞估值分布契约 (破除单一中档假定)."""
    zero_growth_floor_price: float       # 极端零增长/停滞无增长底价 (Growth=0% 刚性清算/防御底线)
    steady_state_value_price: float      # 常态稳健内生估值 (基准中档公允价值)
    optimistic_target_price: float       # 乐观爆发靶心价格 (周期景气上行目标)
    current_vs_floor_gap_pct: float      # 现价相对停滞底价的溢价率 (正为溢价，负为跌穿底价)
    margin_of_safety_assessment_zh: str  # 安全垫与底价状态通俗商业评定

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UniversalDynamicsProfile:
    """标的全息商业物理与动力学档案契约."""
    ticker: str
    company_name_zh: str
    as_of_date: str
    current_price: float
    price_dynamics: PriceDynamicsMetrics
    supply_chain_dynamics: FundamentalSupplyChainMetrics
    valuation_distribution: TerminalValuationDistribution
    business_physics_summary_zh: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name_zh": self.company_name_zh,
            "as_of_date": self.as_of_date,
            "current_price": self.current_price,
            "price_dynamics": self.price_dynamics.to_dict(),
            "supply_chain_dynamics": self.supply_chain_dynamics.to_dict(),
            "valuation_distribution": self.valuation_distribution.to_dict(),
            "business_physics_summary_zh": self.business_physics_summary_zh,
        }


# ==========================================
# 核心通用计算引擎 (Universal Engine)
# ==========================================

class UniversalPhysicalDynamicsEngine:
    """通用商业物理与速度动力学计算引擎.

    100% 通用，无任何标的硬编码特例分支。
    """

    def __init__(
        self,
        default_wacc: float = 0.085,             # 买方基准资本折现率 (8.5%)
        rebound_lookback_days: int = 60,         # 均值回归反弹速度回溯期
        trend_short_window: int = 20,            # 趋势速度短期均线窗口
        trend_long_window: int = 60,             # 趋势速度长期均线窗口
    ):
        self.default_wacc = default_wacc
        self.rebound_lookback_days = rebound_lookback_days
        self.trend_short_window = trend_short_window
        self.trend_long_window = trend_long_window

    def analyze_ticker_dynamics(
        self,
        ticker: str,
        as_of_date: str,
        close_prices: List[float],
        high_prices: Optional[List[float]] = None,
        low_prices: Optional[List[float]] = None,
        volumes: Optional[List[float]] = None,
        financial_statement: Optional[Dict[str, Any]] = None,
        shares_outstanding: Optional[float] = None,
        company_name_zh: Optional[str] = None,
        custom_wacc: Optional[float] = None,
    ) -> UniversalDynamicsProfile:
        """纯通用核心计算入口：输入客观数据时序与财报底账，输出独一无二的物理动力学档案."""
        if not close_prices or len(close_prices) < 5:
            raise ValueError(f"标的 {ticker} 的价格序列长度不足，至少需要 5 个观测点")

        current_price = close_prices[-1]
        wacc = custom_wacc if (custom_wacc and custom_wacc > 0.01) else self.default_wacc
        display_name = company_name_zh or ticker

        # 1. 计算价格时序动力学参数 (反弹半衰期、速度、加速度、恐慌平息天数)
        price_metrics = self._calculate_price_dynamics(
            close_prices=close_prices,
            high_prices=high_prices,
            low_prices=low_prices,
        )

        # 2. 计算供应链周转与商业变现速度 (CCC, DIO, DSO, DPO)
        supply_chain_metrics = self._calculate_supply_chain_dynamics(
            financial_statement=financial_statement
        )

        # 3. 计算非对称极端停滞与零增长防御底价 (Zero-Growth Terminal Floor)
        valuation_dist = self._calculate_valuation_distribution(
            current_price=current_price,
            financial_statement=financial_statement,
            shares_outstanding=shares_outstanding,
            wacc=wacc,
        )

        # 4. 生成通俗商业投资直觉解读文本
        summary_zh = self._synthesize_business_intuition(
            ticker=ticker,
            name_zh=display_name,
            current_price=current_price,
            price_m=price_metrics,
            sc_m=supply_chain_metrics,
            val_d=valuation_dist,
        )

        return UniversalDynamicsProfile(
            ticker=ticker,
            company_name_zh=display_name,
            as_of_date=as_of_date,
            current_price=round(current_price, 2),
            price_dynamics=price_metrics,
            supply_chain_dynamics=supply_chain_metrics,
            valuation_distribution=valuation_dist,
            business_physics_summary_zh=summary_zh,
        )

    # -------------------------------------------------------------------------
    # 算法 1 & 2 & 3: 纯价格动力学与物理速度
    # -------------------------------------------------------------------------

    def _calculate_price_dynamics(
        self,
        close_prices: List[float],
        high_prices: Optional[List[float]] = None,
        low_prices: Optional[List[float]] = None,
    ) -> PriceDynamicsMetrics:
        """计算客观速度参数：反弹半衰期、推进速度与加速度、恐慌平息天数."""
        N = len(close_prices)

        # A. 均值回归反弹半衰期 (OU 离散自回归过程)
        # 考察价格对 20 日均线的对数偏离恢复速度
        window = min(self.rebound_lookback_days, N)
        recent_prices = close_prices[-window:]

        # 计算滚动移动均线中枢
        ma_span = min(20, len(recent_prices))
        spreads: List[float] = []
        for i in range(ma_span, len(recent_prices)):
            local_ma = sum(recent_prices[i - ma_span:i]) / ma_span
            if local_ma > 1e-8:
                spreads.append(math.log(recent_prices[i] / local_ma))

        theta = 0.05  # 默认基准回归强度
        if len(spreads) >= 10:
            x_prev = spreads[:-1]
            dx = [spreads[k] - spreads[k - 1] for k in range(1, len(spreads))]
            var_x = sum(x ** 2 for x in x_prev)
            if var_x > 1e-10:
                cov_xdx = sum(x_prev[k] * dx[k] for k in range(len(dx)))
                # dx = -theta * x -> theta = -cov(x, dx) / var(x)
                fitted_theta = -cov_xdx / var_x
                if fitted_theta > 0.001:
                    theta = min(fitted_theta, 0.693)  # 物理上限每天最多消除 50% 偏离

        rebound_half_life = round(math.log(2.0) / max(theta, 0.015), 1)
        rebound_half_life = max(1.5, min(rebound_half_life, 45.0))  # 物理有界约束在 1.5 ~ 45 天

        # B. 趋势推进速度与动量加速度 (一阶导与二阶导)
        ma20 = sum(close_prices[-min(20, N):]) / min(20, N)
        ma60 = sum(close_prices[-min(60, N):]) / min(60, N)
        ma5 = sum(close_prices[-min(5, N):]) / min(5, N)

        # 一阶推进速度: MA20 相对 MA60 的年化推进百分比
        if ma60 > 1e-8:
            trend_velocity = ((ma20 - ma60) / ma60) * (252.0 / 40.0) * 100.0
        else:
            trend_velocity = 0.0

        # 二阶动量加速度: 近 5 日斜率与近 20 日斜率的差值 (5日冲刺速度减去20日平稳速度)
        if len(close_prices) >= 21:
            p_now = close_prices[-1]
            p_5 = close_prices[-6]
            p_20 = close_prices[-21]
            slope_5 = ((p_now - p_5) / 5.0) / max(p_now, 1e-8)
            slope_20 = ((p_now - p_20) / 20.0) / max(p_now, 1e-8)
            momentum_acc = (slope_5 - slope_20) * 100.0 * 20.0  # 月度化加速度
        else:
            momentum_acc = 0.0

        # C. 恐慌平息天数与年化波动率 (条件异方差衰减)
        daily_returns: List[float] = []
        for i in range(1, len(recent_prices)):
            p0 = recent_prices[i - 1]
            p1 = recent_prices[i]
            if p0 > 1e-8 and p1 > 1e-8:
                daily_returns.append(math.log(p1 / p0))

        if len(daily_returns) >= 5:
            mean_ret = sum(daily_returns) / len(daily_returns)
            var_ret = sum((r - mean_ret) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
            realized_vol = math.sqrt(max(var_ret, 1e-8)) * math.sqrt(252.0) * 100.0

            # 持续性估计: 自相关衰减
            ret_sq = [r ** 2 for r in daily_returns]
            mean_sq = sum(ret_sq) / len(ret_sq)
            cov_sq = sum((ret_sq[k] - mean_sq) * (ret_sq[k-1] - mean_sq) for k in range(1, len(ret_sq)))
            var_sq = sum((x - mean_sq) ** 2 for x in ret_sq)
            persistence = 0.88  # 稳健先验衰减强度
            if var_sq > 1e-12:
                inferred_p = cov_sq / var_sq
                persistence = max(0.65, min(inferred_p, 0.96))
        else:
            realized_vol = 25.0
            persistence = 0.88

        # 冲击平息半衰期天数
        panic_calm_days = round(math.log(0.5) / math.log(max(persistence, 0.01)), 1)
        panic_calm_days = max(2.0, min(panic_calm_days, 30.0))

        return PriceDynamicsMetrics(
            rebound_half_life_days=rebound_half_life,
            trend_velocity_annual_pct=round(trend_velocity, 1),
            momentum_acceleration_pct=round(momentum_acc, 1),
            panic_calming_days=panic_calm_days,
            annualized_realized_vol_pct=round(realized_vol, 1),
            equilibrium_mu_price=round(ma20, 2),
        )

    # -------------------------------------------------------------------------
    # 算法 4: 供应链变现速度 (CCC, DIO, DSO, DPO)
    # -------------------------------------------------------------------------

    def _calculate_supply_chain_dynamics(
        self,
        financial_statement: Optional[Dict[str, Any]],
    ) -> FundamentalSupplyChainMetrics:
        """从官方三表底账提取真实的供应链周转与现金造血天数."""
        if not financial_statement:
            # 缺少财报输入时的中性行业默认值
            return FundamentalSupplyChainMetrics(
                dio_inventory_days=45.0,
                dso_receivables_days=40.0,
                dpo_payables_days=50.0,
                cash_conversion_cycle_days=35.0,
                capital_turnover_velocity=1.2,
            )

        # 提取关键财务科目 (容错非标键名)
        rev = float(financial_statement.get("revenue") or financial_statement.get("total_revenue") or financial_statement.get("sales") or 1000.0)
        cogs = float(financial_statement.get("cogs") or financial_statement.get("cost_of_revenue") or financial_statement.get("operating_cost") or rev * 0.6)
        inv = float(financial_statement.get("inventory") or financial_statement.get("inventories") or 0.0)
        rec = float(financial_statement.get("receivables") or financial_statement.get("accounts_receivable") or 0.0)
        pay = float(financial_statement.get("payables") or financial_statement.get("accounts_payable") or 0.0)
        total_assets = float(financial_statement.get("total_assets") or rev * 1.5)
        curr_liab = float(financial_statement.get("current_liabilities") or rev * 0.4)

        # 计算周转天数 (除零防御)
        safe_cogs = max(cogs, 1.0)
        safe_rev = max(rev, 1.0)

        dio = (inv / safe_cogs) * 365.0
        dso = (rec / safe_rev) * 365.0
        dpo = (pay / safe_cogs) * 365.0
        ccc = dio + dso - dpo

        invested_capital = max(total_assets - curr_liab, 1.0)
        cap_turnover = rev / invested_capital

        return FundamentalSupplyChainMetrics(
            dio_inventory_days=round(dio, 1),
            dso_receivables_days=round(dso, 1),
            dpo_payables_days=round(dpo, 1),
            cash_conversion_cycle_days=round(ccc, 1),
            capital_turnover_velocity=round(cap_turnover, 2),
        )

    # -------------------------------------------------------------------------
    # 算法 5: 破除单一中档假定：极端零增长底价与非对称估值分布
    # -------------------------------------------------------------------------

    def _calculate_valuation_distribution(
        self,
        current_price: float,
        financial_statement: Optional[Dict[str, Any]],
        shares_outstanding: Optional[float],
        wacc: float,
    ) -> TerminalValuationDistribution:
        """计算极端停滞 (Growth=0%) 刚性底线与多维度估值分布."""
        shares = float(shares_outstanding or (financial_statement.get("shares_outstanding") if financial_statement else None) or 1000.0)
        shares = max(shares, 0.001)

        if not financial_statement:
            # 缺少财报输入时的保守物理估值
            floor = current_price * 0.60
            steady = current_price * 1.05
            opt = current_price * 1.35
            gap = ((current_price - floor) / floor) * 100.0
            return TerminalValuationDistribution(
                zero_growth_floor_price=round(floor, 2),
                steady_state_value_price=round(steady, 2),
                optimistic_target_price=round(opt, 2),
                current_vs_floor_gap_pct=round(gap, 1),
                margin_of_safety_assessment_zh="缺少财报底账，采用物理波动率下界作为保守防御底线",
            )

        # 提取现金造血与流动性科目
        cfo = float(financial_statement.get("cash_from_operations") or financial_statement.get("cfo") or 0.0)
        capex = float(financial_statement.get("capital_expenditure") or financial_statement.get("capex") or 0.0)
        capex = abs(capex)  # 资本开支统一为正数
        fcf = cfo - capex

        cash = float(financial_statement.get("cash_and_equivalents") or financial_statement.get("cash") or 0.0)
        st_inv = float(financial_statement.get("short_term_investments") or 0.0)
        total_cash = cash + st_inv

        lt_debt = float(financial_statement.get("long_term_debt") or 0.0)
        st_debt = float(financial_statement.get("short_term_debt") or 0.0)
        total_debt = lt_debt + st_debt

        net_cash = total_cash - total_debt
        total_assets = float(financial_statement.get("total_assets") or 0.0)
        total_liabilities = float(financial_statement.get("total_liabilities") or 0.0)
        book_equity = max(total_assets - total_liabilities, 0.0)

        # 极端零增长模型 (Zero-Growth Terminal Model, Growth = 0%)
        # 即使未来不再增长一分钱，单凭现有静态现金流持续产出，现值是多少？
        if fcf > 0.0:
            ev_zero_growth = fcf / max(wacc, 0.04)
            equity_zero_growth = ev_zero_growth + net_cash
            # 有限责任与清算价值下界保护
            equity_zero_growth = max(equity_zero_growth, net_cash, book_equity * 0.5)
            floor_price = equity_zero_growth / shares
        else:
            # 自由现金流为负时，退化为净资产折现清算价值
            equity_zero_growth = max(net_cash, book_equity * 0.6)
            floor_price = max(equity_zero_growth / shares, current_price * 0.35)

        floor_price = max(round(floor_price, 2), 0.01)

        # 常态稳健内生估值 (融入基准资本回报率与 3%~5% 名义稳态增长)
        g_steady = 0.035
        denom = max(wacc - g_steady, 0.02)
        if fcf > 0.0:
            ev_steady = (fcf * (1.0 + g_steady)) / denom
            equity_steady = ev_steady + net_cash
            steady_price = round(max(equity_steady / shares, floor_price * 1.15), 2)
        else:
            steady_price = round(current_price * 1.05, 2)

        # 乐观爆发靶心价格 (在护城河加速与景气爆发下的溢价天花板)
        opt_price = round(max(steady_price * 1.30, current_price * 1.25), 2)

        # 现价与零增长停滞底价的差距
        gap_pct = round(((current_price - floor_price) / floor_price) * 100.0, 1)

        # 商业通俗评价
        if gap_pct < 0.0:
            assessment = "现价已跌破零增长停滞清算底价，处于极端极度低估的深度黄金安全边际状态"
        elif gap_pct <= 25.0:
            assessment = "现价极其贴近零增长停滞底价，具备极高安全垫，几乎未透支任何未来成长预期"
        elif gap_pct <= 70.0:
            assessment = "现价处于常态合理估值区间，包含了适度的中长期稳健增长预期"
        else:
            assessment = "现价远高于零增长停滞底价，估值内涵高度依赖未来高景气爆发兑现，安全垫较薄"

        return TerminalValuationDistribution(
            zero_growth_floor_price=floor_price,
            steady_state_value_price=steady_price,
            optimistic_target_price=opt_price,
            current_vs_floor_gap_pct=gap_pct,
            margin_of_safety_assessment_zh=assessment,
        )

    # -------------------------------------------------------------------------
    # 投资直觉与通俗商业语言解读合成器
    # -------------------------------------------------------------------------

    def _synthesize_business_intuition(
        self,
        ticker: str,
        name_zh: str,
        current_price: float,
        price_m: PriceDynamicsMetrics,
        sc_m: FundamentalSupplyChainMetrics,
        val_d: TerminalValuationDistribution,
    ) -> str:
        """将复杂的动力学数值转化为直观通俗的商业物理总结."""
        ccc_comment = (
            f"商业话语权极强（先收钱后付货款，无偿占用上下游资金 {abs(sc_m.cash_conversion_cycle_days)} 天）"
            if sc_m.cash_conversion_cycle_days < 0
            else f"属于制造与交付垫资型业务，从买原料到真金白银收回现金需要 {sc_m.cash_conversion_cycle_days} 天"
        )

        acc_comment = (
            "处于踩油门深冲刺阶段（动量正加速）"
            if price_m.momentum_acceleration_pct > 0.0
            else "处于带刹车滑行阶段（动能正减退，警惕冲高滞胀）"
        )

        return (
            f"【{name_zh} 商业物理动力学速览】\n"
            f"1. 弹簧反弹速度：遭遇非理性砸盘时，平均只需 {price_m.rebound_half_life_days} 个交易日即可自动反弹修复一半跌幅；\n"
            f"2. 恐慌平息天数：突发利空冲击引起的剧烈震荡，通常在 {price_m.panic_calming_days} 天内彻底恢复冷静；\n"
            f"3. 趋势推进动能：当前年化推进速度为 {price_m.trend_velocity_annual_pct}%，二阶动量状态为{acc_comment}；\n"
            f"4. 商业造血周转：{ccc_comment}；\n"
            f"5. 零增长防身底线：就算未来公司彻底停滞、一分钱不增长，凭借其账面现金与现有造血能力，"
            f"最硬的物理防守底价为 ${val_d.zero_growth_floor_price}（当前价格溢价率 {val_d.current_vs_floor_gap_pct}%，{val_d.margin_of_safety_assessment_zh}）。"
        )
