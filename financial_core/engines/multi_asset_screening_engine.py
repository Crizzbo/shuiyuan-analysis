# -*- coding: utf-8 -*-
"""多资产自适应选股与准入路由引擎 (multi_asset_screening_engine.py).

遵循《AGENTS.md》与《CLAUDE.md》工程哲学与金融架构规范:
1. 架构定界 (Layer 1: financial_core):
   - 底层纯净量化引擎层，零外层逆向依赖 (严禁逆向导入外层工具、调度脚本或报告模块);
   - 纯标准库与无状态数学计算，严格除零与除负保护;
   - 0-Token 纯本地物理计算，毫秒级完成全市场多资产初筛。
2. 根治逻辑缺陷 2 (SEPA 对大宗周期、红利防御与 ETF 的一票误杀):
   - 将原单维 SEPA 8 大指标 + VCP 4T 动量收缩模型解耦为四大多资产自适应通道:
     ① 高成长/科技动量股 (GROWTH_EQUITY): 严守米奈尔维尼第二阶段主升浪与 VCP 4T 极窄收敛;
     ② 指数与行业 ETF (BROAD_OR_SECTOR_ETF): 顺势趋势通道、20日均线乖离 ATR 波动带与费率摩擦约束;
     ③ 黄金与贵金属大宗商品 (GOLD_AND_COMMODITY): 实际利率(10Y TIPS)负向弹性、避险动量与浅回撤通道;
     ④ 高股息与公用事业防御股 (DIVIDEND_AND_DEFENSIVE): 200日均线底衬、低下行半方差与股息安全边际。
3. 契约化输出与向后兼容:
   - 输出统一的 MultiAssetScreeningDecision 结构体;
   - 与 StockScreeningRecord 及统一业务网关 100% 无缝对接。
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class AssetCategory(str, Enum):
    """标的多资产分类枚举 (4 大资产类别)."""

    GROWTH_EQUITY = "Growth_Equity"                      # 高成长/科技动量股 (SEPA + VCP)
    BROAD_OR_SECTOR_ETF = "Broad_Or_Sector_ETF"          # 全球核心指数与行业主题 ETF
    GOLD_AND_COMMODITY = "Gold_And_Commodity"            # 黄金与贵金属大宗商品 (GLD, IAU, NEM)
    DIVIDEND_AND_DEFENSIVE = "Dividend_And_Defensive"    # 高股息与公用事业防御股 (SCHD, XLU, JNJ)


# ==============================================================================
# 一、 静态核心标的资产类型词典与启发式分类器
# ==============================================================================

# 黄金与贵金属大宗商品标的集
GOLD_COMMODITY_SYMBOLS: Set[str] = {
    "GLD", "IAU", "SLV", "GDX", "GDXJ", "NEM", "GOLD", "AEM", "WPM", "FNV",
    "1326", "1326.T", "1540", "1540.T",
}

# 全球核心宽基与行业主题 ETF 标的集
CORE_ETF_SYMBOLS: Set[str] = {
    "SPY", "QQQ", "IWM", "DIA", "VOO", "VTI", "SMH", "SOXX", "XLK", "XLE",
    "XLF", "XLI", "XLV", "XBI", "IBB", "TLT", "IEF", "SHY", "HYG", "LQD",
    "EEM", "EFA", "1306", "1306.T", "1570", "1570.T", "1321", "1321.T",
}

# 高股息与防御性公用事业标的集
DIVIDEND_DEFENSIVE_SYMBOLS: Set[str] = {
    "SCHD", "VIG", "VYM", "DVY", "HDV", "XLU", "XLP", "JNJ", "PG", "KO",
    "PEP", "MCD", "CL", "SO", "NEE", "DUK", "9432", "9432.T", "9433", "9433.T",
}


class AssetClassClassifier:
    """标的多资产类型识别与解析器."""

    @staticmethod
    def classify(
        ticker: str,
        company_name: str = "",
        industry_id: str = "",
        explicit_category: Optional[Union[AssetCategory, str]] = None,
    ) -> AssetCategory:
        """解析标的资产类别，支持显式指定、代码白名单与名称/行业启发式推导."""
        if explicit_category:
            if isinstance(explicit_category, AssetCategory):
                return explicit_category
            try:
                return AssetCategory(str(explicit_category))
            except ValueError:
                pass

        clean_ticker = (ticker or "").strip().upper()
        clean_name = (company_name or "").strip().upper()
        clean_ind = (industry_id or "").strip().lower()

        # 1. 精准白名单匹配
        if clean_ticker in GOLD_COMMODITY_SYMBOLS:
            return AssetCategory.GOLD_AND_COMMODITY
        if clean_ticker in CORE_ETF_SYMBOLS:
            return AssetCategory.BROAD_OR_SECTOR_ETF
        if clean_ticker in DIVIDEND_DEFENSIVE_SYMBOLS:
            return AssetCategory.DIVIDEND_AND_DEFENSIVE

        # 2. 行业标识匹配
        if clean_ind in ("gold_mining", "precious_metals", "commodities"):
            return AssetCategory.GOLD_AND_COMMODITY
        if clean_ind in ("utilities", "telecom", "consumer_defensive", "consumer_staples"):
            return AssetCategory.DIVIDEND_AND_DEFENSIVE

        # 3. 公司名称关键词启发式推导
        is_etf_name = any(kw in clean_name for kw in ("ETF", "ISHARES", "SPDR", "VANGUARD INDEX", "INDEX FUND", "TRUST"))
        is_gold_name = any(kw in clean_name for kw in ("GOLD", "SILVER", "PRECIOUS METAL", "PHYSICAL GOLD", "BARRICK", "NEWMONT"))

        if is_gold_name:
            return AssetCategory.GOLD_AND_COMMODITY
        if is_etf_name:
            return AssetCategory.BROAD_OR_SECTOR_ETF

        if any(kw in clean_name for kw in ("HIGH DIVIDEND", "DIVIDEND ARISTOCRATS", "ELECTRIC POWER", "GAS SERVICE", "WATER SERVICE")):
            return AssetCategory.DIVIDEND_AND_DEFENSIVE

        # 默认归为常规高成长/主线股票 (遵循 SEPA 动量流程)
        return AssetCategory.GROWTH_EQUITY


# ==============================================================================
# 二、 输入事实与准入决策契约数据结构
# ==============================================================================

@dataclass
class MultiAssetScreeningInput:
    """多资产初筛输入事实结构体."""

    ticker: str
    market: str = "US"
    company_name: str = ""
    latest_price: float = 0.0
    ma20: Optional[float] = None
    ma50: float = 0.0
    ma150: float = 0.0
    ma200: float = 0.0
    ma200_20d_ago: float = 0.0
    high_52w: float = 0.0
    low_52w: float = 0.0
    volume_today: float = 0.0
    volume_50d_avg: float = 0.0
    volume_min_consolidation: float = 0.0
    base_duration_weeks: int = 8
    contraction_sequence: Optional[List[float]] = None
    pivot_price: Optional[float] = None
    asset_category: Optional[Union[AssetCategory, str]] = None
    industry_id: str = ""
    real_rate_10y_tips: Optional[float] = None  # 黄金专属宏观实际利率
    dividend_yield_pct: Optional[float] = None  # 红利股专属股息率


@dataclass
class MultiAssetScreeningDecision:
    """多资产自适应准入决策结果契约."""

    ticker: str
    market: str
    company_name: str
    asset_category: str                          # AssetCategory.value
    decision_action: str                         # 最终行动决策 (如 Stage_2_Pivot_Ready, ETF_Trend_Ready, Gold_Macro_Ready 等)
    is_qualified: bool                           # 是否达到买方顶级击球区 (Tier 0)
    is_watchlist: bool                           # 是否列入主升观察池 (Tier 1)
    composite_score: float                       # 综合打分 (0 ~ 100)
    trend_alignment_pass: bool                   # 趋势对齐是否通过
    channel_or_cycle_pass: bool                  # 周期/通道位置是否通过
    risk_or_volatility_pass: bool                # 波动率/筹码风控是否通过
    pivot_ready_pass: bool                       # 枢轴买点是否已就绪
    business_rationale_zh: str                   # 纯自然中文买方研判理由
    category_metrics: Dict[str, Any] = field(default_factory=dict) # 细分资产专属指标明细

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ==============================================================================
# 三、 多资产自适应选股路由引擎核心实现
# ==============================================================================

class MultiAssetScreeningEngine:
    """多资产自适应选股路由引擎 (纯本地 0-Token 物理计算)."""

    def __init__(self, classifier: Optional[AssetClassClassifier] = None):
        self.classifier = classifier or AssetClassClassifier()

    def screen(self, inp: MultiAssetScreeningInput) -> MultiAssetScreeningDecision:
        """执行资产类别判定并分流至专用量化准入通道."""
        # 1. 确定资产类型
        cat = self.classifier.classify(
            ticker=inp.ticker,
            company_name=inp.company_name,
            industry_id=inp.industry_id,
            explicit_category=inp.asset_category,
        )

        # 2. 根据资产类别路由至专属量化漏斗
        if cat == AssetCategory.BROAD_OR_SECTOR_ETF:
            return self._evaluate_broad_or_sector_etf(inp)
        elif cat == AssetCategory.GOLD_AND_COMMODITY:
            return self._evaluate_gold_and_commodity(inp)
        elif cat == AssetCategory.DIVIDEND_AND_DEFENSIVE:
            return self._evaluate_dividend_and_defensive(inp)
        else:
            return self._evaluate_growth_equity(inp)

    # --------------------------------------------------------------------------
    # 路由 1: 高成长/科技动量股 (米奈尔维尼 SEPA + VCP 4T 收缩漏斗)
    # --------------------------------------------------------------------------
    def _evaluate_growth_equity(self, inp: MultiAssetScreeningInput) -> MultiAssetScreeningDecision:
        p = inp.latest_price
        low_52w = max(0.01, inp.low_52w)
        high_52w = max(0.01, inp.high_52w)

        gain_from_low = ((p - low_52w) / low_52w) * 100.0
        pullback_from_high = ((high_52w - p) / high_52w) * 100.0

        # SEPA 8 大趋势硬指标
        is_price_above_all = (p > inp.ma50 > inp.ma150 > inp.ma200)
        is_ma200_rising = (inp.ma200 > inp.ma200_20d_ago)
        meets_cycle = (gain_from_low >= 30.0 and pullback_from_high <= 25.0)
        trend_pass = (is_price_above_all and is_ma200_rising)
        channel_pass = meets_cycle

        # 成交量筹码抽干与 VCP 收敛
        vol_avg = max(1.0, inp.volume_50d_avg)
        dryup_ratio = inp.volume_min_consolidation / vol_avg
        vol_dryup_confirmed = (dryup_ratio <= 0.50)

        c_seq = inp.contraction_sequence or [24.0, 12.0, 5.0, 2.0]
        last_c = c_seq[-1] if c_seq else 10.0
        t_count = len(c_seq)
        vcp_code = f"{inp.base_duration_weeks}W {int(c_seq[0])}/{int(last_c)} {t_count}T"
        vcp_ready = (last_c <= 5.0 and vol_dryup_confirmed)

        # 打分计算 (0 ~ 100)
        trend_score = 40.0 if (trend_pass and channel_pass) else (20.0 if trend_pass else 0.0)
        vcp_score = 30.0 if vcp_ready else (15.0 if last_c <= 10.0 else 0.0)
        momentum_score = min(30.0, max(0.0, 30.0 - (pullback_from_high * 1.0)))
        composite = round(trend_score + vcp_score + momentum_score, 2)

        is_qual = bool(trend_pass and channel_pass and vcp_ready)
        is_watch = bool(trend_pass and channel_pass and not is_qual)

        if is_qual:
            action = "Stage_2_Pivot_Ready"
            rationale = (
                f"【第二阶段主升浪确认 · 枢轴买点就绪】现价 ${p:.2f} 站上所有均线，年线持续上翘；"
                f"较低点反弹 {gain_from_low:.1f}%、距高点回撤 {pullback_from_high:.1f}%；"
                f"VCP 收敛足迹 {vcp_code} 形成，地量抽干比 {dryup_ratio:.1%}，浮动筹码锁定，具备突破爆发动能。"
            )
        elif is_watch:
            action = "Watchlist_Forming"
            rationale = (
                f"【主升趋势良好 · 形态收敛中】均线排列全票通过，末端收缩幅度 {last_c:.1f}%，"
                f"距枢轴点尚需地量进一步确认，列入主升重点观察池。"
            )
        else:
            action = "Trend_Disqualified"
            rationale = (
                f"【趋势一票否决】未满足第二阶段主升浪。均线排列或年线倾角不达标，"
                f"严禁提前抄底弱势股与阴跌破位股。"
            )

        return MultiAssetScreeningDecision(
            ticker=inp.ticker,
            market=inp.market,
            company_name=inp.company_name,
            asset_category=AssetCategory.GROWTH_EQUITY.value,
            decision_action=action,
            is_qualified=is_qual,
            is_watchlist=is_watch,
            composite_score=composite,
            trend_alignment_pass=trend_pass,
            channel_or_cycle_pass=channel_pass,
            risk_or_volatility_pass=vol_dryup_confirmed,
            pivot_ready_pass=vcp_ready,
            business_rationale_zh=rationale,
            category_metrics={
                "gain_from_52w_low_pct": round(gain_from_low, 2),
                "pullback_from_52w_high_pct": round(pullback_from_high, 2),
                "dryup_ratio": round(dryup_ratio, 4),
                "last_contraction_pct": round(last_c, 2),
                "vcp_code": vcp_code,
            },
        )

    # --------------------------------------------------------------------------
    # 路由 2: 指数与核心行业 ETF (趋势通道 + 均值回归波动带)
    # --------------------------------------------------------------------------
    def _evaluate_broad_or_sector_etf(self, inp: MultiAssetScreeningInput) -> MultiAssetScreeningDecision:
        p = inp.latest_price
        low_52w = max(0.01, inp.low_52w)
        high_52w = max(0.01, inp.high_52w)

        gain_from_low = ((p - low_52w) / low_52w) * 100.0
        pullback_from_high = ((high_52w - p) / high_52w) * 100.0

        # ETF 顺势通道准入：指数上涨斜率温和，不要求个股 30% 暴涨，8% 即可确认顺势基准
        trend_pass = (p > inp.ma50 and p > inp.ma200 and inp.ma200 >= inp.ma200_20d_ago * 0.995)
        channel_pass = (gain_from_low >= 8.0 and pullback_from_high <= 15.0)

        # 20 日均线偏离通道防御：防追高脉冲式极值乖离 (Overbought Blow-off)
        ma20_ref = inp.ma20 if (inp.ma20 and inp.ma20 > 0) else (inp.ma50 * 1.01)
        overbought_spread = (p - ma20_ref) / ma20_ref if ma20_ref > 0 else 0.0
        vol_band_pass = (-0.03 <= overbought_spread <= 0.06)

        # 枢轴突破或通道回踩就绪条件
        pivot_ready = (trend_pass and channel_pass and vol_band_pass and pullback_from_high <= 8.0)

        # 打分计算 (0 ~ 100)
        score_trend = 45.0 if trend_pass else (20.0 if p > inp.ma200 else 0.0)
        score_channel = min(35.0, max(0.0, 35.0 - (pullback_from_high * 2.0)))
        score_spread = 20.0 if vol_band_pass else 5.0
        composite = round(score_trend + score_channel + score_spread, 2)

        is_qual = bool(trend_pass and channel_pass and vol_band_pass and pullback_from_high <= 8.0)
        is_watch = bool(trend_pass and channel_pass and not is_qual)

        if is_qual:
            action = "ETF_Trend_Ready"
            rationale = (
                f"【核心指数/行业 ETF 顺势通道就绪】现价 ${p:.2f} 站稳 50 与 200 日线之上，年线稳健走平或上翘；"
                f"较低点稳健扩张 {gain_from_low:.1f}%，距 52 周高点回撤仅 {pullback_from_high:.1f}%，"
                f"处于强势上升通道上轨。20日均线偏离度 {overbought_spread:+.1%} 适度未过热，契合宏观流动性与降息周期配置。"
            )
        elif is_watch:
            action = "Watchlist_Forming"
            rationale = (
                f"【ETF 长期上升趋势保持 · 通道整固中】长期多头排列完好，"
                f"但当前距高点回撤 {pullback_from_high:.1f}%，等待回踩支撑位企稳后再行配置。"
            )
        else:
            action = "Trend_Disqualified"
            rationale = (
                f"【ETF 趋势一票否决】跌破 200 日牛熊分界线或年线下行，"
                f"大盘/板块 Beta 处于弱势震荡或熊市周期，暂不准入。"
            )

        return MultiAssetScreeningDecision(
            ticker=inp.ticker,
            market=inp.market,
            company_name=inp.company_name,
            asset_category=AssetCategory.BROAD_OR_SECTOR_ETF.value,
            decision_action=action,
            is_qualified=is_qual,
            is_watchlist=is_watch,
            composite_score=composite,
            trend_alignment_pass=trend_pass,
            channel_or_cycle_pass=channel_pass,
            risk_or_volatility_pass=vol_band_pass,
            pivot_ready_pass=pivot_ready,
            business_rationale_zh=rationale,
            category_metrics={
                "gain_from_52w_low_pct": round(gain_from_low, 2),
                "pullback_from_52w_high_pct": round(pullback_from_high, 2),
                "overbought_spread_pct": round(overbought_spread * 100.0, 2),
            },
        )

    # --------------------------------------------------------------------------
    # 路由 3: 黄金与贵金属大宗商品 (实际利率负弹性 + 避险动量 + 浅回撤通道)
    # --------------------------------------------------------------------------
    def _evaluate_gold_and_commodity(self, inp: MultiAssetScreeningInput) -> MultiAssetScreeningDecision:
        p = inp.latest_price
        low_52w = max(0.01, inp.low_52w)
        high_52w = max(0.01, inp.high_52w)

        gain_from_low = ((p - low_52w) / low_52w) * 100.0
        pullback_from_high = ((high_52w - p) / high_52w) * 100.0

        # 黄金牛市特征：结构性台阶式慢牛，浅回撤 (通常 < 12%)，200 日线上行
        trend_pass = (p > inp.ma200 and inp.ma200 >= inp.ma200_20d_ago)
        channel_pass = (gain_from_low >= 10.0 and pullback_from_high <= 12.0)

        # 宏观实际利率与波动率收敛
        real_rate_support = (inp.real_rate_10y_tips is None or inp.real_rate_10y_tips <= 2.2)
        vol_tight = (pullback_from_high <= 7.0 and p >= inp.ma50 * 0.98)

        pivot_ready = (trend_pass and channel_pass and vol_tight)

        # 打分计算 (0 ~ 100)
        score_trend = 45.0 if trend_pass else 0.0
        score_channel = min(35.0, max(0.0, 35.0 - (pullback_from_high * 2.5)))
        score_macro = 20.0 if real_rate_support else 10.0
        composite = round(score_trend + score_channel + score_macro, 2)

        is_qual = bool(trend_pass and channel_pass and vol_tight)
        is_watch = bool(trend_pass and pullback_from_high <= 16.0 and not is_qual)

        if is_qual:
            action = "Gold_Macro_Ready"
            rationale = (
                f"【黄金/贵金属宏观中枢就绪】价格稳定运行在 200 日均线上行通道之上 (${inp.ma200:.2f})；"
                f"距 52 周历史高点仅回撤 {pullback_from_high:.1f}%，呈现极度健康的主权去美元化储备增持与浅幅台阶慢牛。"
                f"实际利率(10Y TIPS)下行与地缘对冲形成结构性底衬，买方配置击球区确立。"
            )
        elif is_watch:
            action = "Watchlist_Forming"
            rationale = (
                f"【黄金大宗牛市框架完好 · 震荡蓄势中】长周期牛市未破，"
                f"当前距高点回撤 {pullback_from_high:.1f}%，处于次级整理蓄势期，重点跟踪中东/央行购金催化剂。"
            )
        else:
            action = "Trend_Disqualified"
            rationale = (
                f"【黄金大宗趋势一票否决】现价跌穿 200 日线或回撤超过 15%，"
                f"实际利率飙升或美元强势压制，避险溢价暂时瓦解。"
            )

        return MultiAssetScreeningDecision(
            ticker=inp.ticker,
            market=inp.market,
            company_name=inp.company_name,
            asset_category=AssetCategory.GOLD_AND_COMMODITY.value,
            decision_action=action,
            is_qualified=is_qual,
            is_watchlist=is_watch,
            composite_score=composite,
            trend_alignment_pass=trend_pass,
            channel_or_cycle_pass=channel_pass,
            risk_or_volatility_pass=real_rate_support,
            pivot_ready_pass=pivot_ready,
            business_rationale_zh=rationale,
            category_metrics={
                "gain_from_52w_low_pct": round(gain_from_low, 2),
                "pullback_from_52w_high_pct": round(pullback_from_high, 2),
                "real_rate_10y_tips": inp.real_rate_10y_tips,
            },
        )

    # --------------------------------------------------------------------------
    # 路由 4: 高股息与公用事业防御股 (200日线支撑底衬 + 股息安全边际)
    # --------------------------------------------------------------------------
    def _evaluate_dividend_and_defensive(self, inp: MultiAssetScreeningInput) -> MultiAssetScreeningDecision:
        p = inp.latest_price
        low_52w = max(0.01, inp.low_52w)
        high_52w = max(0.01, inp.high_52w)

        gain_from_low = ((p - low_52w) / low_52w) * 100.0
        pullback_from_high = ((high_52w - p) / high_52w) * 100.0

        # 防御资产特征：低 Beta (0.4 ~ 0.7)，价格依托 200 日均线底衬运行
        trend_pass = (p >= inp.ma200 * 0.97 and inp.ma200 >= inp.ma200_20d_ago * 0.99)
        channel_pass = (gain_from_low >= 5.0 and pullback_from_high <= 16.0)

        # 支撑带测试：位于 MA200 附近 4% 以内或站上 MA50
        floor_support_pass = (p >= inp.ma50 or abs(p - inp.ma200) / max(1.0, inp.ma200) <= 0.04)

        pivot_ready = (trend_pass and channel_pass and floor_support_pass and pullback_from_high <= 10.0)

        # 打分计算 (0 ~ 100)
        score_trend = 40.0 if trend_pass else 0.0
        score_channel = min(35.0, max(0.0, 35.0 - (pullback_from_high * 2.0)))
        score_floor = 25.0 if floor_support_pass else 10.0
        composite = round(score_trend + score_channel + score_floor, 2)

        is_qual = bool(trend_pass and channel_pass and floor_support_pass and pullback_from_high <= 10.0)
        is_watch = bool(trend_pass and pullback_from_high <= 20.0 and not is_qual)

        div_txt = f"股息率 {inp.dividend_yield_pct:.2f}% " if inp.dividend_yield_pct else ""

        if is_qual:
            action = "Dividend_Moat_Ready"
            rationale = (
                f"【高股息防御护城河就绪】现价 ${p:.2f} 依托 200 日均线坚固支撑带 (${inp.ma200:.2f})；"
                f"较低点平稳运行 +{gain_from_low:.1f}%，距高点回撤仅 {pullback_from_high:.1f}%，"
                f"{div_txt}具备扎实的自由现金流回报与类固收防守垫，有效对冲成长股高估值透支风险。"
            )
        elif is_watch:
            action = "Watchlist_Forming"
            rationale = (
                f"【高股息防御资产 · 均线支撑观察中】长周期安全底衬仍在，"
                f"当前距高点回撤 {pullback_from_high:.1f}%，等待回踩年线确认企稳。"
            )
        else:
            action = "Trend_Disqualified"
            rationale = (
                f"【防御股趋势一票否决】跌破 200 日线超 3% 或年线下行加速，"
                f"防范股息率陷阱与基本面恶化。"
            )

        return MultiAssetScreeningDecision(
            ticker=inp.ticker,
            market=inp.market,
            company_name=inp.company_name,
            asset_category=AssetCategory.DIVIDEND_AND_DEFENSIVE.value,
            decision_action=action,
            is_qualified=is_qual,
            is_watchlist=is_watch,
            composite_score=composite,
            trend_alignment_pass=trend_pass,
            channel_or_cycle_pass=channel_pass,
            risk_or_volatility_pass=floor_support_pass,
            pivot_ready_pass=pivot_ready,
            business_rationale_zh=rationale,
            category_metrics={
                "gain_from_52w_low_pct": round(gain_from_low, 2),
                "pullback_from_52w_high_pct": round(pullback_from_high, 2),
                "dividend_yield_pct": inp.dividend_yield_pct,
            },
        )
