"""股价异动与公司信息披露因果归因引擎 (Price Shock & Disclosure Attribution Engine).

本引擎针对企业信息披露 (财报、指引修定、增发、研发黑天鹅、诉讼) 或股价异常波动进行微观底层物理量化解构。
回答核心问题:
1. 为什么会有这种异常波动? (Causal Mechanism)
2. 价格差距 (Price Gap) 是如何产生的? 各因子在每股价格落差中具体贡献了多少美元? (Quantitative Attribution)

六大微观底层驱动力分解方程:
    Delta_P = Delta_GuidanceTerminal + Delta_OperatingLeverage + Delta_DilutionOverhang
              + Delta_TrueFCF_SBC + Delta_RiskPremiumWACC + Delta_DealerGamma
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import math


@dataclass
class GuidanceTerminalImpact:
    """前瞻指引修改对终值现值的传导冲击."""
    previous_guidance_growth: float  # 原预期年化增长率 (例如 0.20)
    revised_guidance_growth: float   # 修订后年化增长率 (例如 0.14)
    wacc: float                      # 加权平均资本成本 (例如 0.10)
    terminal_growth: float           # 永续增长率 (例如 0.025)
    base_share_price: float          # 冲击前每股价格 (例如 40.0)
    terminal_value_weight: float     # 终值占总企业价值权重 (通常 0.65 ~ 0.85)

    def compute(self) -> Dict[str, float]:
        growth_drop = self.revised_guidance_growth - self.previous_guidance_growth
        # 终值折现乘数杠杆 = 1 / (wacc - terminal_growth)
        spread = max(0.015, self.wacc - self.terminal_growth)
        terminal_revision_pct = (growth_drop / max(0.05, self.previous_guidance_growth)) * self.terminal_value_weight
        raw_delta_p = self.base_share_price * terminal_revision_pct
        # 有限责任下界防御：公允价值绝不为负
        delta_p = max(-self.base_share_price, raw_delta_p)
        return {
            "growth_revision_delta": round(growth_drop, 4),
            "terminal_revision_pct": round(terminal_revision_pct * 100, 2),
            "dollar_impact_per_share": round(delta_p, 4),
        }


@dataclass
class OperatingLeverageImpact:
    """经营杠杆 (DOL) 对营业利润与市盈率分母的非线性坍塌冲击."""
    revenue_change_pct: float     # 营收变动比例 (例如 -0.05 代表下滑 5%)
    fixed_cost_ratio: float       # 固定成本占总成本费用比例 (例如 0.70)
    baseline_operating_margin: float # 原基准营业利润率 (例如 0.15)
    current_pe: float             # 现行市盈率
    base_share_price: float       # 冲击前股价

    def compute(self) -> Dict[str, float]:
        # 经营杠杆系数 DOL = (1 + Fixed Costs / Operating Income)
        # = [1 + (1 - Margin) * FixedRatio / Margin]
        margin = max(0.01, self.baseline_operating_margin)
        dol = 1.0 + ((1.0 - margin) * self.fixed_cost_ratio) / margin
        operating_income_change_pct = self.revenue_change_pct * dol
        # 利润变动对每股内生价值的传导，有限责任下界防御：最大损失为基准股价，绝无负数下界
        raw_delta_p = self.base_share_price * operating_income_change_pct
        delta_p = max(-self.base_share_price, raw_delta_p)
        return {
            "degree_of_operating_leverage": round(dol, 2),
            "operating_income_shock_pct": round(operating_income_change_pct * 100, 2),
            "dollar_impact_per_share": round(delta_p, 4),
        }


@dataclass
class DilutionOverhangImpact:
    """增发 (Secondary Offering / ATM / S-3) 与承销商折价套利冲击."""
    new_shares_issued: float      # 新增发股数
    current_shares_outstanding: float # 原发行在外总股数
    offering_price: float         # 增发价格
    current_market_price: float   # 宣布前市场价
    atm_shelf_remaining: float    # 货架剩余在售筹码额 (USD)

    def compute(self) -> Dict[str, float]:
        total_shares = max(1.0, self.current_shares_outstanding + self.new_shares_issued)
        dilution_ratio = self.new_shares_issued / total_shares

        # 折价率 Haircut
        discount_pct = (self.offering_price - self.current_market_price) / max(0.01, self.current_market_price)

        # 内生价值摊薄: 新内生每股价格 = (原市值 + 募集现金) / 新总股数
        raised_cash = max(0.0, self.new_shares_issued * self.offering_price)
        old_market_cap = max(0.0, self.current_shares_outstanding * self.current_market_price)
        new_fair_price = max(0.0, (old_market_cap + raised_cash) / total_shares)

        # 叠加货架压制系数 (Shelf Overhang Drag): 货架额占市值比重 * 5% 压制
        shelf_drag_pct = min(0.15, (max(0.0, self.atm_shelf_remaining) / max(1.0, old_market_cap)) * 0.05)

        raw_delta_p = (new_fair_price - self.current_market_price) - (self.current_market_price * shelf_drag_pct)
        # 有限责任下界防御
        delta_p = max(-self.current_market_price, raw_delta_p)
        return {
            "dilution_ratio_pct": round(dilution_ratio * 100, 2),
            "offering_discount_pct": round(discount_pct * 100, 2),
            "new_diluted_fair_price": round(new_fair_price, 4),
            "shelf_overhang_drag_pct": round(shelf_drag_pct * 100, 2),
            "dollar_impact_per_share": round(delta_p, 4),
        }


@dataclass
class SBCFreeCashFlowImpact:
    """员工股权激励 (Stock-Based Compensation, SBC) 伪造现金流与真实造血价值还原."""
    reported_operating_cash_flow: float  # 财报汇报的经营现金流
    reported_capex: float                # 资本开支
    annual_sbc: float                    # 财报计提的年度股权激励费用 (SBC)
    shares_outstanding: float            # 总股本
    market_cap: float                    # 市值
    base_share_price: float              # 当前股价

    def compute(self) -> Dict[str, float]:
        # 汇报的自由现金流 (表面)
        apparent_fcf = self.reported_operating_cash_flow - self.reported_capex
        # 真实自由现金流 (扣除股东实际被稀释发放的薪水)
        true_fcf = apparent_fcf - self.annual_sbc

        safe_shares = max(1.0, self.shares_outstanding)
        apparent_fcf_per_share = apparent_fcf / safe_shares
        true_fcf_per_share = true_fcf / safe_shares

        # SBC 隐形稀释率
        sbc_dilution_pct = self.annual_sbc / max(1.0, self.market_cap)
        # 估值重定价差距 (若市场按照真实 FCF 重新计价，扣除虚增的折现值，假设 10x FCF 估值乘数)
        raw_gap = (true_fcf_per_share - apparent_fcf_per_share) * 10.0
        # 有限责任下界防御：每股折价扣减不可跌破股价基准
        delta_p = max(-self.base_share_price, raw_gap)

        return {
            "apparent_fcf": round(apparent_fcf, 2),
            "true_fcf": round(true_fcf, 2),
            "sbc_dilution_pct_annual": round(sbc_dilution_pct * 100, 2),
            "dollar_impact_per_share": round(delta_p, 4),
        }


@dataclass
class RiskPremiumWACCImpact:
    """重大事件 (FDA/诉讼/监管) 消除或加剧不确定性引发的风险溢价 (ERP) 与折现率重定价."""
    previous_wacc: float         # 之前折现率 (例如 0.09)
    revised_wacc: float          # 风险落地后折现率 (例如 0.12 表示风险加剧，或 0.08 表示靴子落地)
    terminal_growth: float       # 永续增长率 (例如 0.02)
    base_share_price: float      # 基准股价

    def compute(self) -> Dict[str, float]:
        # 戈登永续折现因子反比关系: Price ~ 1 / (WACC - g)
        prev_spread = max(0.015, self.previous_wacc - self.terminal_growth)
        new_spread = max(0.015, self.revised_wacc - self.terminal_growth)

        rerating_factor = prev_spread / new_spread
        re_rated_price = max(0.0, self.base_share_price * rerating_factor)
        raw_delta_p = re_rated_price - self.base_share_price
        delta_p = max(-self.base_share_price, raw_delta_p)

        return {
            "wacc_spread_change_bps": round((self.revised_wacc - self.previous_wacc) * 10000, 1),
            "rerating_factor": round(rerating_factor, 4),
            "re_rated_price": round(re_rated_price, 4),
            "dollar_impact_per_share": round(delta_p, 4),
        }


@dataclass
class DealerGammaDragImpact:
    """做市商负 Gamma 对冲盘对破位行情的顺周期加速砸盘引力."""
    current_price: float         # 当前股价
    critical_strike: float       # 大单聚集的关键破位行权价 (例如 4.0)
    net_gamma_exposure_shares: float # 每变动 1 美元，做市商需顺势卖出的股票数
    average_daily_volume: float  # 日均成交量

    def compute(self) -> Dict[str, float]:
        # 若价格跌破关键行权价，做市商 Delta 迅速转负，产生被迫抛盘
        is_breakdown = self.current_price < self.critical_strike
        if not is_breakdown:
            return {
                "gamma_drag_active": False,
                "forced_selling_shares": 0.0,
                "dollar_impact_per_share": 0.0,
            }

        distance_below = max(0.0, self.critical_strike - self.current_price)
        forced_selling = max(0.0, self.net_gamma_exposure_shares * distance_below)
        adv_ratio = max(0.0, forced_selling / max(1.0, self.average_daily_volume))

        # 流动性冲击价格下挫模型: 冲击幅度 = 0.5 * (Forced Selling / ADV)^0.6 * Price
        # 严格防御 math.pow 负数域异常，adv_ratio 已由 max(0.0) 保证非负
        gamma_impact_pct = min(0.20, 0.5 * math.pow(adv_ratio, 0.6))
        raw_delta_p = -self.current_price * gamma_impact_pct
        delta_p = max(-self.current_price, raw_delta_p)

        return {
            "gamma_drag_active": True,
            "forced_selling_shares": round(forced_selling, 0),
            "adv_absorption_ratio": round(adv_ratio, 4),
            "dollar_impact_per_share": round(delta_p, 4),
        }


# 驱动力自然中文语义映射表 (SSOT - 去工程符号化)
FACTOR_CHINESE_NAMES: Dict[str, str] = {
    "guidance_terminal_shock": "官方前瞻指引下修 (终值折现下折)",
    "operating_leverage_shock": "高固定成本经营杠杆反噬 (利润塌陷)",
    "dilution_and_shelf_shock": "定增折价摊薄与货架筹码压制",
    "sbc_true_fcf_shock": "员工股权激励真实造血挤出重估",
    "risk_premium_wacc_rerating": "重大不确定性溢价与折现率重定价",
    "dealer_gamma_drag": "做市商负Gamma对冲盘顺周期砸盘",
}


class PriceShockAttributionEngine:
    """全方位股价异动因果归因与价格落差解构中枢."""

    def __init__(self):
        self.version = "2.0.0"

    def attribute_shock(
        self,
        base_price: float,
        actual_price: float,
        guidance: Optional[GuidanceTerminalImpact] = None,
        operating_leverage: Optional[OperatingLeverageImpact] = None,
        dilution: Optional[DilutionOverhangImpact] = None,
        sbc: Optional[SBCFreeCashFlowImpact] = None,
        wacc_rerating: Optional[RiskPremiumWACCImpact] = None,
        gamma_drag: Optional[DealerGammaDragImpact] = None,
        ticker: Optional[str] = None,
        market: Optional[str] = None,
        currency_symbol: Optional[str] = None,
    ) -> Dict[str, Any]:
        """全量归因解构:

        计算总价格落差 (Total Price Gap) 并逐项匹配各驱动力货币贡献度。
        输出自然商业中文直觉研报，杜绝暴露纯英文下划线代码与跨市场货币符号失真。
        """
        # 自适应推导市场与货币符号
        t_up = (ticker or "").upper()
        m_up = (market or "").upper()
        is_jp = m_up == "JP" or t_up.endswith(".T") or t_up.endswith(".JP") or (t_up.isdigit() and len(t_up) == 4)
        is_cn = m_up == "CN" or t_up.endswith(".SS") or t_up.endswith(".SZ") or (t_up.isdigit() and len(t_up) == 6)
        if currency_symbol:
            curr_sym = currency_symbol
        elif is_jp or is_cn:
            curr_sym = "¥"
        else:
            curr_sym = "$"

        total_observed_gap = actual_price - base_price
        explained_gap = 0.0
        factor_breakdown = {}
        factor_narratives = []

        if guidance:
            g_res = guidance.compute()
            g_res["factor_name_zh"] = FACTOR_CHINESE_NAMES.get("guidance_terminal_shock", "官方指引下修")
            impact = g_res["dollar_impact_per_share"]
            explained_gap += impact
            factor_breakdown["guidance_terminal_shock"] = g_res
            factor_narratives.append((abs(impact), f"【官方指引下修】造成每股 {curr_sym}{impact:+.2f} 估值折现下折"))

        if operating_leverage:
            ol_res = operating_leverage.compute()
            ol_res["factor_name_zh"] = FACTOR_CHINESE_NAMES.get("operating_leverage_shock", "经营杠杆反噬")
            impact = ol_res["dollar_impact_per_share"]
            explained_gap += impact
            factor_breakdown["operating_leverage_shock"] = ol_res
            factor_narratives.append((abs(impact), f"【经营杠杆反噬】造成每股 {curr_sym}{impact:+.2f} 利润塌陷冲击"))

        if dilution:
            d_res = dilution.compute()
            d_res["factor_name_zh"] = FACTOR_CHINESE_NAMES.get("dilution_and_shelf_shock", "定增摊薄压制")
            impact = d_res["dollar_impact_per_share"]
            explained_gap += impact
            factor_breakdown["dilution_and_shelf_shock"] = d_res
            factor_narratives.append((abs(impact), f"【定增摊薄压制】造成每股 {curr_sym}{impact:+.2f} 筹码稀释折价"))

        if sbc:
            sbc_res = sbc.compute()
            sbc_res["factor_name_zh"] = FACTOR_CHINESE_NAMES.get("sbc_true_fcf_shock", "股权激励挤出")
            impact = sbc_res["dollar_impact_per_share"]
            explained_gap += impact
            factor_breakdown["sbc_true_fcf_shock"] = sbc_res
            factor_narratives.append((abs(impact), f"【股权激励挤出】造成每股 {curr_sym}{impact:+.2f} 真实现金流重估"))

        if wacc_rerating:
            wacc_res = wacc_rerating.compute()
            wacc_res["factor_name_zh"] = FACTOR_CHINESE_NAMES.get("risk_premium_wacc_rerating", "风险溢价重估")
            impact = wacc_res["dollar_impact_per_share"]
            explained_gap += impact
            factor_breakdown["risk_premium_wacc_rerating"] = wacc_res
            factor_narratives.append((abs(impact), f"【风险溢价重估】造成每股 {curr_sym}{impact:+.2f} 资本成本加压"))

        if gamma_drag:
            gm_res = gamma_drag.compute()
            gm_res["factor_name_zh"] = FACTOR_CHINESE_NAMES.get("dealer_gamma_drag", "做市商负Gamma助跌")
            impact = gm_res["dollar_impact_per_share"]
            explained_gap += impact
            factor_breakdown["dealer_gamma_drag"] = gm_res
            if gm_res.get("gamma_drag_active"):
                factor_narratives.append((abs(impact), f"【做市商负Gamma助跌】造成每股 {curr_sym}{impact:+.2f} 踩踏加速抛压"))

        residual = total_observed_gap - explained_gap
        explained_ratio = (
            (explained_gap / total_observed_gap * 100.0)
            if abs(total_observed_gap) > 0.001
            else 100.0
        )

        # 按绝对影响金额降序排序生成通俗商业叙事
        factor_narratives.sort(key=lambda x: x[0], reverse=True)
        top_factors_text = "；".join([item[1] for item in factor_narratives[:3]]) if factor_narratives else "暂无显著单因子驱动"

        if total_observed_gap < -0.001:
            direction_zh = "下跌"
        elif total_observed_gap > 0.001:
            direction_zh = "上涨"
        else:
            direction_zh = "基本持平"

        narrative_zh = (
            f"标的自基准价 {curr_sym}{base_price:.2f} 异动{direction_zh}至 {curr_sym}{actual_price:.2f}，"
            f"总观察价格落差为 {curr_sym}{total_observed_gap:+.2f}。因果归因模型已解释了 {curr_sym}{explained_gap:+.2f} "
            f"(解释度达 {explained_ratio:.1f}%)。主要驱动原因如下：{top_factors_text}；"
            f"剩余未解释摩擦扰动为 {curr_sym}{residual:+.2f}。"
        )

        return {
            "base_price": round(base_price, 4),
            "actual_price": round(actual_price, 4),
            "total_observed_gap_dollars": round(total_observed_gap, 4),
            "total_explained_gap_dollars": round(explained_gap, 4),
            "unexplained_residual_dollars": round(residual, 4),
            "explained_ratio_pct": round(explained_ratio, 2),
            "direction_zh": direction_zh,
            "factor_contributions": factor_breakdown,
            "factor_chinese_names": FACTOR_CHINESE_NAMES,
            "narrative_zh": narrative_zh,
            "currency_symbol": curr_sym,
        }
