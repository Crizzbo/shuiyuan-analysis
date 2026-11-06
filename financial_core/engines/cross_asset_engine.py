"""跨资产量化核算与穿透估值核心引擎 (Cross-Asset Valuation Core Engine).

物理架构定界 (Layer 1: financial_core):
- 纯净底层量化引擎，零外层依赖 (严禁导入任何外围工具、调度脚本或报告模块);
- 承担全球核心指数与行业 ETF 成分股加权穿透、Jaccard 相似度、集中度 (CR10/HHI)、多因子暴露与费率复利损耗计算;
- 承担黄金 10Y TIPS 真实利率定价锚、主权央行去美元化储备结构性溢价、期现基差与特级金矿股 AISC 营运杠杆模型;
- 纯无状态数学算法，内置严格除零与除负保护。
"""

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from .market_adaptive_params import GoldValuationAdaptiveParams


@dataclass(frozen=True)
class ETFOverlapResult:
    """成对 ETF 成分股加权穿透重叠度结果."""
    etf_a: str
    etf_b: str
    weighted_overlap_pct: float
    jaccard_similarity_pct: float
    common_holdings_count: int
    overlap_weights: Dict[str, Tuple[float, float, float]]  # sym -> (wA, wB, minW)
    is_high_overlap: bool
    overlap_level_zh: str = ""       # 纯自然中文重叠定性 (去工程符号化)
    narrative_zh: str = ""           # 买方通俗全息研报卡片 (去工程符号化)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "etf_a": self.etf_a,
            "etf_b": self.etf_b,
            "weighted_overlap_pct": round(self.weighted_overlap_pct, 2),
            "jaccard_similarity_pct": round(self.jaccard_similarity_pct, 2),
            "common_holdings_count": self.common_holdings_count,
            "is_high_overlap": self.is_high_overlap,
            "overlap_level_zh": self.overlap_level_zh,
            "overlap_weights": self.overlap_weights,
            "narrative_zh": self.narrative_zh,
        }


@dataclass(frozen=True)
class ETFPenetrationFact:
    """单个 ETF 全景穿透量化事实."""
    ticker: str
    expense_ratio: float
    aum_billion_usd: float
    top_holdings: Dict[str, float]
    factor_scores: Dict[str, float]
    cr10_pct: float
    hhi_index: float
    fee_drag_1y: float
    fee_drag_3y: float
    fee_drag_5y: float
    is_concentrated: bool
    concentration_level_zh: str = "" # 纯自然中文集中度定性 (去工程符号化)
    narrative_zh: str = ""           # 买方通俗全息研报卡片 (去工程符号化)
    currency_symbol: str = "$"       # 货币符号 ("$", "¥")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "currency_symbol": self.currency_symbol,
            "expense_ratio": round(self.expense_ratio, 4),
            "aum_billion_usd": round(self.aum_billion_usd, 2),
            "cr10_pct": round(self.cr10_pct, 2),
            "hhi_index": round(self.hhi_index, 1),
            "fee_drag_1y": round(self.fee_drag_1y, 2),
            "fee_drag_3y": round(self.fee_drag_3y, 2),
            "fee_drag_5y": round(self.fee_drag_5y, 2),
            "is_concentrated": self.is_concentrated,
            "concentration_level_zh": self.concentration_level_zh,
            "top_holdings": self.top_holdings,
            "factor_scores": self.factor_scores,
            "narrative_zh": self.narrative_zh,
        }


@dataclass(frozen=True)
class GoldValuationFact:
    """现货黄金宏观公允估值与三态情景事实."""
    spot_gold_usd: float
    tips_10y_real_yield_pct: float
    breakeven_inflation_pct: float
    dxy_index: float
    central_bank_net_tonnes: float
    sge_physical_premium_usd: float
    traditional_tips_anchor_usd: float
    central_bank_premium_usd: float
    central_bank_premium_pct: float
    macro_fair_value_usd: float
    deviation_pct: float
    bear_case_usd: float
    base_case_usd: float
    bull_case_usd: float
    valuation_status_zh: str = ""    # 纯自然中文估值定性 (去工程符号化)
    narrative_zh: str = ""           # 买方通俗全息研报卡片 (去工程符号化)
    currency_symbol: str = "$"       # 货币符号 ("$", "¥")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "currency_symbol": self.currency_symbol,
            "spot_gold_usd": round(self.spot_gold_usd, 2),
            "tips_10y_real_yield_pct": round(self.tips_10y_real_yield_pct, 2),
            "breakeven_inflation_pct": round(self.breakeven_inflation_pct, 2),
            "dxy_index": round(self.dxy_index, 2),
            "central_bank_net_tonnes": round(self.central_bank_net_tonnes, 1),
            "sge_physical_premium_usd": round(self.sge_physical_premium_usd, 2),
            "traditional_tips_anchor_usd": round(self.traditional_tips_anchor_usd, 1),
            "central_bank_premium_usd": round(self.central_bank_premium_usd, 1),
            "central_bank_premium_pct": round(self.central_bank_premium_pct, 2),
            "macro_fair_value_usd": round(self.macro_fair_value_usd, 1),
            "deviation_pct": round(self.deviation_pct, 2),
            "bear_case_usd": round(self.bear_case_usd, 1),
            "base_case_usd": round(self.base_case_usd, 1),
            "bull_case_usd": round(self.bull_case_usd, 1),
            "valuation_status_zh": self.valuation_status_zh,
            "narrative_zh": self.narrative_zh,
        }


@dataclass(frozen=True)
class GoldMinerLeverageFact:
    """特级金矿股营运杠杆与现金流弹性事实."""
    ticker: str
    current_price: float
    aisc_per_oz: float
    cash_margin_per_oz: float
    operating_leverage_multiplier: float
    annual_fcf_mil: float
    fcf_per_share: float
    fcf_yield_pct: float
    fair_target_price: float
    potential_upside_pct: float
    leverage_profile_zh: str = ""    # 纯自然中文杠杆定性 (去工程符号化)
    narrative_zh: str = ""           # 买方通俗全息研报卡片 (去工程符号化)
    currency_symbol: str = "$"       # 货币符号 ("$", "¥")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "currency_symbol": self.currency_symbol,
            "current_price": round(self.current_price, 2),
            "aisc_per_oz": round(self.aisc_per_oz, 2),
            "cash_margin_per_oz": round(self.cash_margin_per_oz, 2),
            "operating_leverage_multiplier": round(self.operating_leverage_multiplier, 2),
            "annual_fcf_mil": round(self.annual_fcf_mil, 2),
            "fcf_per_share": round(self.fcf_per_share, 2),
            "fcf_yield_pct": round(self.fcf_yield_pct, 2),
            "fair_target_price": round(self.fair_target_price, 2),
            "potential_upside_pct": round(self.potential_upside_pct, 2),
            "leverage_profile_zh": self.leverage_profile_zh,
            "narrative_zh": self.narrative_zh,
        }


class CrossAssetValuationEngine:
    """跨资产量化核算核心 (ETF 穿透、因子暴露、黄金宏观定价与金矿营运杠杆)."""

    def __init__(self):
        self.version = "1.0.0"

    @classmethod
    def compute_etf_overlap(
        cls,
        holdings_a: Dict[str, float],
        holdings_b: Dict[str, float],
        ticker_a: str = "ETF_A",
        ticker_b: str = "ETF_B",
    ) -> ETFOverlapResult:
        """计算两只 ETF 之间的成分股加权权重重叠 (Weighted Overlap) 与 Jaccard 相似度.

        公式:
        Overlap(A, B) = sum_{s in S_A cap S_B} min(w_{A,s}, w_{B,s})
        Jaccard(A, B) = |S_A cap S_B| / |S_A cup S_B|
        """
        sum_a = sum(float(w) for w in holdings_a.values())
        sum_b = sum(float(w) for w in holdings_b.values())
        if sum_a > 1.0001 or sum_b > 1.0001:
            raise ValueError(
                f"ETF 持仓权重合计超过 100% 被拒绝: sum(A)={sum_a:.4f}, sum(B)={sum_b:.4f}"
            )
        for sym, w in list(holdings_a.items()) + list(holdings_b.items()):
            if float(w) < 0.0 or not math.isfinite(float(w)):
                raise ValueError(f"ETF 成分股权重必须为有限非负数，收到 {sym}={w}")

        all_symbols: Set[str] = set(holdings_a.keys()).union(set(holdings_b.keys()))
        overlap_details: Dict[str, Tuple[float, float, float]] = {}
        weighted_overlap = 0.0

        for sym in all_symbols:
            w_a = float(holdings_a.get(sym, 0.0))
            w_b = float(holdings_b.get(sym, 0.0))
            if w_a > 0.0 and w_b > 0.0:
                common_w = min(w_a, w_b)
                weighted_overlap += common_w
                overlap_details[sym] = (round(w_a * 100.0, 2), round(w_b * 100.0, 2), round(common_w * 100.0, 2))

        common_count = len(overlap_details)
        union_count = len(all_symbols)
        jaccard = (common_count / union_count) if union_count > 0 else 0.0
        overlap_pct = min(100.0, max(0.0, round(weighted_overlap * 100.0, 2)))
        jaccard_pct = min(100.0, max(0.0, round(jaccard * 100.0, 2)))

        # 纯自然中文定性与买方研报卡片 (去工程符号化)
        if overlap_pct >= 50.0:
            overlap_level_zh = "高度持仓重叠 (配置显著冗余)"
            tactics_zh = (
                f"两只标的成分股加权持仓重叠度高达 {overlap_pct:.1f}%，共有重仓标的 {common_count} 只。"
                f"若组合中同时配置两只 ETF 将导致严重的头寸冗余与单点风险过度暴露，建议合并精简，优选费率更低、流动性更深者。"
            )
        elif overlap_pct >= 30.0:
            overlap_level_zh = "中度持仓重叠 (需防范头寸踩踏)"
            tactics_zh = (
                f"两只标的成分股重叠度达 {overlap_pct:.1f}%，属于中度重叠警戒线之上。"
                f"在配置组合时需穿透核算底层核心持仓的绝对权重累计，避免核心赛道龙头被隐形超配放大组合回撤。"
            )
        elif overlap_pct >= 15.0:
            overlap_level_zh = "轻度持仓重叠 (结构较为温和)"
            tactics_zh = (
                f"两只标的成分股重叠度为 {overlap_pct:.1f}%，重叠程度温和，存在部分跨行业或跨风格的共同龙头，"
                f"整体组合风险处于可控范围，可按主辅权重搭配配置。"
            )
        else:
            overlap_level_zh = "低度分散重叠 (具备良好互补性)"
            tactics_zh = (
                f"两只标的成分股加权持仓重叠度仅为 {overlap_pct:.1f}% (集合相似度 {jaccard_pct:.1f}%)，"
                f"底层持仓高度互补，可作为资产配置中分散单一赛道风险与风格因子的优质拼图。"
            )

        narrative_zh = (
            f"【ETF 穿透重叠度全息研报: {ticker_a} vs {ticker_b}】"
            f"重叠属性定性【{overlap_level_zh}】(加权持仓重叠度 {overlap_pct:.1f}%)。"
            f"持仓交集解构: 共有成分股 {common_count} 只，持仓集合相似度 {jaccard_pct:.1f}%。"
            f"买方资产配置指引: {tactics_zh}"
        )

        return ETFOverlapResult(
            etf_a=ticker_a,
            etf_b=ticker_b,
            weighted_overlap_pct=overlap_pct,
            jaccard_similarity_pct=jaccard_pct,
            common_holdings_count=common_count,
            overlap_weights=overlap_details,
            is_high_overlap=(overlap_pct >= 30.0),
            overlap_level_zh=overlap_level_zh,
            narrative_zh=narrative_zh,
        )

    @classmethod
    def compute_etf_penetration(
        cls,
        ticker: str,
        expense_ratio: float,
        aum_billion_usd: float,
        top_holdings: Dict[str, float],
        factor_scores: Dict[str, float],
        capital_baseline: float = 100000.0,
        market: Optional[str] = None,
        currency_symbol: Optional[str] = None,
    ) -> ETFPenetrationFact:
        """测算单个 ETF 集中度指标、多因子得分与复利费率损耗.

        CR10: sum_{i=1}^{10} w_i
        HHI: sum_{i=1}^{10} (w_i * 100)^2
        Drag(T): C0 * [(1 + r_exp)^T - 1]
        """
        # 自适应推导市场与货币符号 (SSOT: 兼容多市场多币种)
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

        cr10 = sum(float(w) for w in top_holdings.values()) * 100.0
        hhi = sum((float(w) * 100.0) ** 2 for w in top_holdings.values())

        c0 = max(1.0, float(capital_baseline))
        r_exp = max(0.0, float(expense_ratio))
        drag_1y = c0 * r_exp
        drag_3y = c0 * (((1.0 + r_exp) ** 3) - 1.0)
        drag_5y = c0 * (((1.0 + r_exp) ** 5) - 1.0)

        # 纯自然中文集中度定性与买方研报卡片 (去工程符号化)
        if cr10 >= 60.0:
            concentration_level_zh = "极度集中 (头部巨头强绑定)"
            guidance_zh = (
                f"前十大持仓占比高达 {cr10:.1f}% (赫芬达尔指数 {hhi:.1f})，ETF 净值几乎完全由头部少数个股支配，"
                f"波动性特征极度接近单只重仓股，投资该标的本质上是博弈核心龙头的超额收益，而非广泛分散。"
            )
        elif cr10 >= 50.0:
            concentration_level_zh = "显著集中 (权重显著倾斜)"
            guidance_zh = (
                f"前十大持仓占比达 {cr10:.1f}%，触发集中度警戒线。头部龙头具备决定性定价权，"
                f"需重点跟踪前三大权重公司的业绩催化剂与供应链动态。"
            )
        elif cr10 >= 30.0:
            concentration_level_zh = "中度均衡 (行业风格代表)"
            guidance_zh = (
                f"前十大持仓占比 {cr10:.1f}%，持仓分布兼顾了核心龙头的领涨弹性与行业二线中坚的稳健性，"
                f"属于结构健康的典型行业赛道指数工具。"
            )
        else:
            concentration_level_zh = "广泛分散 (全市场均权分散)"
            guidance_zh = (
                f"前十大持仓占比仅为 {cr10:.1f}%，持仓高度分散，能够最大程度消除个股特异性黑天鹅风险，"
                f"适合作为长周期宏观 Beta 底仓配置。"
            )

        narrative_zh = (
            f"【ETF {ticker} 全景穿透与费率摩擦全息研报】"
            f"持仓集中度评级【{concentration_level_zh}】(前十大重仓占比 {cr10:.1f}%，赫芬达尔集中度指数 {hhi:.1f})。"
            f"管理费率与复利损耗: 年化费率 {r_exp * 100:.2f}% (AUM {curr_sym}{aum_billion_usd:.1f}B)。"
            f"以 10 万基准投资测算，1年费用损耗 {curr_sym}{drag_1y:.2f}，3年复利摩擦 {curr_sym}{drag_3y:.2f}，5年累计损耗 {curr_sym}{drag_5y:.2f}。"
            f"买方配置指引: {guidance_zh}"
        )

        return ETFPenetrationFact(
            ticker=ticker,
            expense_ratio=r_exp,
            aum_billion_usd=float(aum_billion_usd),
            top_holdings=top_holdings,
            factor_scores=factor_scores,
            cr10_pct=round(cr10, 2),
            hhi_index=round(hhi, 1),
            fee_drag_1y=round(drag_1y, 2),
            fee_drag_3y=round(drag_3y, 2),
            fee_drag_5y=round(drag_5y, 2),
            is_concentrated=(cr10 >= 50.0),
            concentration_level_zh=concentration_level_zh,
            narrative_zh=narrative_zh,
            currency_symbol=curr_sym,
        )

    @classmethod
    def compute_gold_macro_valuation(
        cls,
        spot_gold_usd: float = 2650.0,
        nominal_10y_yield: float = 0.0440,
        breakeven_10y: float = 0.0235,
        dxy_index: float = 104.2,
        annual_cb_tonnes: float = 1050.0,
        sge_premium_usd: float = 28.5,
        adaptive_params: Optional[GoldValuationAdaptiveParams] = None,
        currency_symbol: Optional[str] = None,
    ) -> GoldValuationFact:
        """评估现货黄金宏观公允估值与三态情景.

        1. 10Y TIPS 真实利率: r_tips = y_nominal - pi_breakeven
        2. 传统定价锚: P_tips = P_base * [1 - (r_tips - r_pivot) * eta_tips]
        3. 央行去美元化储备溢价: theta_cb = min(cap, max(0, tonnes - baseline) / step * step_pct)
        4. 综合公允价值: P_fair = P_tips * (1 + theta_cb)
        """
        curr_sym = currency_symbol or "$"
        if not isinstance(spot_gold_usd, (int, float)) or not math.isfinite(spot_gold_usd) or spot_gold_usd <= 0.0:
            raise ValueError(f"现货黄金价格必须为有限正数，实际收到非法值: {spot_gold_usd}")

        params = adaptive_params or GoldValuationAdaptiveParams()
        tips_real_yield = float(nominal_10y_yield) - float(breakeven_10y)

        # 传统 TIPS 真实利率锚定价 (自适应参数驱动)
        base_tips_anchor = params.tips_base_price * (1.0 - (tips_real_yield - params.tips_pivot_yield) * params.tips_sensitivity)
        base_tips_anchor = max(1500.0, base_tips_anchor)

        # 新常态去美元化溢价项 (自适应参数驱动)
        cb_excess_tonnes = max(0.0, float(annual_cb_tonnes) - params.baseline_cb_tonnes)
        step_denominator = max(1.0, params.cb_tonnes_step)
        structural_premium_pct = min(params.cb_max_premium_cap, (cb_excess_tonnes / step_denominator) * params.cb_premium_step_pct)
        central_bank_premium_usd = base_tips_anchor * structural_premium_pct

        fair_value_gold = base_tips_anchor + central_bank_premium_usd
        gap_pct = ((float(spot_gold_usd) - fair_value_gold) / max(1.0, fair_value_gold)) * 100.0

        # 三态情景
        bear_gold = max(params.bear_floor_usd, base_tips_anchor * 0.95)
        base_gold = round(fair_value_gold, 1)
        bull_gold = round(fair_value_gold * params.bull_multiplier, 1)

        # 纯自然中文宏观定性与买方研报卡片 (去工程符号化)
        if gap_pct < -5.0:
            val_status_zh = "显著折价低估 (强宏观安全垫)"
            gold_tactics_zh = (
                f"当前金价 ({curr_sym}{spot_gold_usd:.1f}/oz) 显著低于宏观公允价值 ({curr_sym}{fair_value_gold:.1f}/oz)，折价幅度达 {abs(gap_pct):.1f}%。"
                f"主权央行去美元化购金需求持续提供托底支撑，当前价位具备绝佳的左侧配置安全边际，建议积极超配实物黄金与核心金矿资产。"
            )
        elif gap_pct <= 5.0:
            val_status_zh = "公允中性 (锚定宏观定价)"
            gold_tactics_zh = (
                f"当前金价与宏观公允估值高度契合 (偏离度仅 {gap_pct:+.1f}%)，"
                f"定价真实反映了当前真实利率底锚 ({curr_sym}{base_tips_anchor:.1f}/oz) 与主权央行储备溢价 (+{curr_sym}{central_bank_premium_usd:.1f}/oz)。"
                f"维持组合中黄金 5%~10% 的标准战略对冲仓位，平稳获取跨周期抗通胀收益。"
            )
        elif gap_pct <= 15.0:
            val_status_zh = "温和溢价 (计入地缘避险)"
            gold_tactics_zh = (
                f"金价相对宏观基准存在 {gap_pct:+.1f}% 的温和溢价，表明市场计入了额外的突发地缘动荡与避险买盘。"
                f"建议持有现有底仓并结合悲观底价 ({curr_sym}{bear_gold:.1f}) 做好防守，不宜盲目加杠杆追涨。"
            )
        else:
            val_status_zh = "情绪显著过热 (警惕均值回归)"
            gold_tactics_zh = (
                f"金价严重脱离基本面公允中枢，偏离溢价高达 {gap_pct:+.1f}%，投机多头极其拥挤。"
                f"一旦地缘情绪降温或长端真实利率反弹，极易引发深度多头踩踏回踩公允估值中枢 ({curr_sym}{fair_value_gold:.1f})，建议分批逢高止盈。"
            )

        narrative_zh = (
            f"【现货黄金宏观公允估值与情景全息研报】"
            f"宏观估值定性【{val_status_zh}】(现价 {curr_sym}{spot_gold_usd:.1f}/oz，宏观公允价值 {curr_sym}{fair_value_gold:.1f}/oz，偏离度 {gap_pct:+.1f}%)。"
            f"双轮定价解构: 10年期 TIPS 真实利率底锚 {curr_sym}{base_tips_anchor:.1f}/oz (真实利率 {tips_real_yield * 100:.2f}%)；"
            f"主权央行去美元化储备结构性溢价 +{curr_sym}{central_bank_premium_usd:.1f}/oz (+{structural_premium_pct * 100:.1f}%)。"
            f"三态宏观情景推演: 悲观底价 {curr_sym}{bear_gold:.1f}，基准公允 {curr_sym}{base_gold:.1f}，乐观靶心 {curr_sym}{bull_gold:.1f}。"
            f"买方资产配置指引: {gold_tactics_zh}"
        )

        return GoldValuationFact(
            spot_gold_usd=float(spot_gold_usd),
            tips_10y_real_yield_pct=round(tips_real_yield * 100.0, 2),
            breakeven_inflation_pct=round(float(breakeven_10y) * 100.0, 2),
            dxy_index=float(dxy_index),
            central_bank_net_tonnes=float(annual_cb_tonnes),
            sge_physical_premium_usd=float(sge_premium_usd),
            traditional_tips_anchor_usd=round(base_tips_anchor, 1),
            central_bank_premium_usd=round(central_bank_premium_usd, 1),
            central_bank_premium_pct=round(structural_premium_pct * 100.0, 2),
            macro_fair_value_usd=round(fair_value_gold, 1),
            deviation_pct=round(gap_pct, 2),
            bear_case_usd=round(bear_gold, 1),
            base_case_usd=base_gold,
            bull_case_usd=bull_gold,
            valuation_status_zh=val_status_zh,
            narrative_zh=narrative_zh,
            currency_symbol=curr_sym,
        )

    @classmethod
    def compute_gold_miner_leverage(
        cls,
        ticker: str,
        current_price: float,
        aisc_per_oz: float,
        annual_production_koz: float,
        shares_mil: float,
        net_debt_mil: float = 0.0,
        spot_gold_price: float = 2650.0,
        valuation_multiple: float = 12.0,
        market: Optional[str] = None,
        currency_symbol: Optional[str] = None,
    ) -> GoldMinerLeverageFact:
        """测算特级金矿股营运现金流杠杆与内在价值.

        Margin = max(10.0, P_gold - AISC)
        Operating Leverage = (Delta Margin / Margin) / (Delta Gold / Gold)
        FCF = (Prod_koz * 1000 * Margin * 0.70) / 1,000,000
        Fair Price = (FCF / Shares) * Multiple
        """
        # 自适应推导标的市场与货币符号 (SSOT: 兼容多市场多币种)
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

        cur_p = max(0.01, float(current_price))
        spot = max(100.0, float(spot_gold_price))
        aisc = float(aisc_per_oz)

        current_margin = spot - aisc
        if current_margin <= 0.0:
            current_margin = 10.0

        # 金价上涨 $100 敏感度测算
        gold_up_100 = spot + 100.0
        new_margin = max(10.0, gold_up_100 - aisc)
        margin_growth_pct = ((new_margin - current_margin) / current_margin) * 100.0
        gold_growth_pct = (100.0 / spot) * 100.0
        op_leverage = margin_growth_pct / max(0.001, gold_growth_pct)

        # 自由现金流核算 (扣除税与维系资本开支系数 0.70)
        prod_koz = max(0.1, float(annual_production_koz))
        annual_fcf = (prod_koz * 1000.0 * current_margin * 0.70) / 1000000.0
        shares = max(0.01, float(shares_mil))
        fcf_per_share = annual_fcf / shares
        fcf_yield_pct = (fcf_per_share / cur_p) * 100.0

        fair_price = max(0.0, fcf_per_share * float(valuation_multiple))
        upside_pct = ((fair_price - cur_p) / cur_p) * 100.0

        # 纯自然中文杠杆定性与买方研报卡片 (去工程符号化)
        if op_leverage >= 2.5:
            leverage_profile_zh = "超高营运杠杆 (高弹性强周期暴击标的)"
            miner_tactics_zh = (
                f"单盎司现金净毛利与 AISC 成本差结构赋予该标的高达 {op_leverage:.2f} 倍的营运放大杠杆。"
                f"金价向上突破时具备极强的业绩爆发弹力，适合在金价上行确立期作为买方进取进攻型资产配置。"
            )
        elif op_leverage >= 1.8:
            leverage_profile_zh = "显著营运杠杆 (标准金价放大器)"
            miner_tactics_zh = (
                f"具备 {op_leverage:.2f} 倍的标准金价营运杠杆，单盎司现金毛利 {curr_sym}{current_margin:.1f}/oz，"
                f"在分享金价上涨红利的同时兼顾充沛的自由现金流造血能力 ({curr_sym}{annual_fcf:.1f}M)，属于风险收益比极佳的核心矿业蓝筹。"
            )
        else:
            leverage_profile_zh = "温和营运杠杆 (低成本稳健现金牛)"
            miner_tactics_zh = (
                f"开采成本与金价差距极大，单盎司利润丰厚，营运杠杆倍数为 {op_leverage:.2f}x。"
                f"防御属性极强，即便金价大幅深度回调仍能维持充沛正向现金流与分红能力。"
            )

        narrative_zh = (
            f"【特级金矿龙头 {ticker} 营运杠杆与现金流弹性全息研报】"
            f"杠杆属性定性【{leverage_profile_zh}】(金价营运杠杆倍数 {op_leverage:.2f}x)。"
            f"单位经济学盈利空间: 全维持成本 AISC {curr_sym}{aisc:.1f}/oz，单盎司现金净毛利 {curr_sym}{current_margin:.1f}/oz。"
            f"金价每上涨1%，开采现金利润将非线性扩增 {op_leverage:.2f}%。"
            f"现金流与内在公允估值: 预估年化自由现金流 {curr_sym}{annual_fcf:.1f}M，每股自由现金流 {curr_sym}{fcf_per_share:.2f} "
            f"(自由现金流收益率 {fcf_yield_pct:.1f}%)。公允目标价 {curr_sym}{fair_price:.2f} (潜在预期上涨空间 {upside_pct:+.1f}%)。"
            f"买方操作建议: {miner_tactics_zh}"
        )

        return GoldMinerLeverageFact(
            ticker=ticker,
            current_price=cur_p,
            aisc_per_oz=aisc,
            cash_margin_per_oz=round(current_margin, 2),
            operating_leverage_multiplier=round(op_leverage, 2),
            annual_fcf_mil=round(annual_fcf, 2),
            fcf_per_share=round(fcf_per_share, 2),
            fcf_yield_pct=round(fcf_yield_pct, 2),
            fair_target_price=round(fair_price, 2),
            potential_upside_pct=round(upside_pct, 2),
            leverage_profile_zh=leverage_profile_zh,
            narrative_zh=narrative_zh,
            currency_symbol=curr_sym,
        )
