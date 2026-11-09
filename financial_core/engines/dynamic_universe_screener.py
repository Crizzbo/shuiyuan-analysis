# -*- coding: utf-8 -*-
"""买方机构级动态点时选股引擎 (dynamic_universe_screener.py).

严格遵循《AGENTS.md》与《CLAUDE.md》：
1. 底层纯净金融核心层：零逆向依赖，不依赖任何外层脚本与报告模块；
2. 零前视偏差 (Strict Point-in-Time)：输入必须仅包含截至历史调仓时刻 T 的已知历史日线；
3. 多因子全息击球区打分系统 (经实测根因重构全面升级)：
   - 模型 A (MOMENTUM_SEPA): Daniel & Moskowitz (2016) 动量崩盘防御体系，(12M - 1M) 中期动量解耦短期末月反转与异动波动率激增；
   - 模型 B (MOAT_VALUE): 彻底破除 EMA200 均线折价伪价值陷阱，以均线通道倾角、52周安全边际与极低下行半方差为核心护城河基石；
   - 模型 C (VAR_TAIL_RISK): 基于下行半方差 (Downside Semi-Variance) 与上行偏度凸性预算，精准规避肥尾踩踏；
   - 跨市场脱耦 (JP vs US): 日股 (.T) 针对性启用均值回归支撑与股息护城河底价，不再机械套用美股动量突破；
   - 滞后持仓缓冲区 (Hysteresis Buffer): 动态 Top-10 准入、Top-40 退出与 EMA50 护城保护，彻底根治过度换手磨损。
"""

from dataclasses import dataclass, asdict
import math
from typing import Any, Dict, List, Optional, Tuple

from .amihud_liquidity_engine import AmihudLiquidityEngine
from .merton_default_engine import MertonStructuralDefaultEngine
from .forensics_and_trailing_exit_engine import ForensicsAndTrailingExitEngine
from .mean_reversion_kalman_engine import MeanReversionKalmanEngine

VALID_STRATEGY_MODELS = {
    "FULL_QUANTAMENTAL",
    "MOMENTUM_SEPA",
    "MOAT_VALUE",
    "VAR_TAIL_RISK",
}


@dataclass
class StockScreeningScore:
    """个股点时打分明细结构体."""
    symbol: str
    date: str
    current_price: float
    is_stage2: bool
    rs_score: float                # 相对基准动量得分 (0 ~ 100)
    trend_score: float             # 均线趋势结构得分 (-40 ~ +40)
    valuation_penalty: float       # 估值透支惩罚分 (-50 ~ +35)
    volatility_score: float        # 波动率/下行风控得分 (-35 ~ +40)
    composite_score: float         # 综合得分
    in_strike_zone: bool           # 是否进入买方击球区
    disqualification_reason: Optional[str] = None
    amihud_ratio: float = 0.0      # Amihud 价格冲击比率 (* 10^6)
    liquidity_tier: str = "MID_CAP"# 流动性分级 (MEGA_LIQUID, LARGE_CAP, MID_CAP, SMALL_CAP, ILLIQUID_TRAP)
    distance_to_default: Optional[float] = None # KMV-Merton 违约距离 DD
    is_credit_distressed: bool = False          # 是否触发信用暴雷高危警报
    atr20: float = 0.0             # 20日真实波幅 ATR
    downside_vol20: float = 0.0    # 20日下行波动率 (半方差年化)
    inter_momentum: float = 0.0    # 中期动量 (12M - 1M)
    ret_1m: float = 0.0            # 近1个月收益率
    is_japan: bool = False         # 是否为日股标的
    beneish_m_score: Optional[float] = None     # Beneish M-Score 造假排雷分
    is_fraud_suspect: bool = False             # 是否触发财务造假一票否决
    kalman_z_score: Optional[float] = None      # 卡尔曼滤波中枢偏离 Z 分数
    ou_half_life: Optional[float] = None        # OU 均值回归半衰期 (交易日)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DynamicUniverseScreener:
    """动态点时选股筛选引擎."""

    def __init__(
        self,
        strategy_model: str = "FULL_QUANTAMENTAL",
        min_lookback_bars: int = 200,
        stage2_bonus: float = 30.0,
        stage4_penalty: float = -40.0,
        max_price_to_ema200: float = 1.45,
        max_acceptable_vol20: float = 0.55,
        enable_liquidity_gate: bool = True,
        enable_credit_gate: bool = True,
        enable_forensics_gate: bool = True,
        enable_kalman_filter: bool = True,
    ):
        if strategy_model not in VALID_STRATEGY_MODELS:
            raise ValueError(f"未知的策略模型类型: {strategy_model}，有效取值: {VALID_STRATEGY_MODELS}")
        if min_lookback_bars < 50:
            raise ValueError(f"回溯天数 min_lookback_bars 必须 >= 50，当前: {min_lookback_bars}")

        self.strategy_model = strategy_model
        self.min_lookback_bars = min_lookback_bars
        self.stage2_bonus = stage2_bonus
        self.stage4_penalty = stage4_penalty
        self.max_price_to_ema200 = max_price_to_ema200
        self.max_acceptable_vol20 = max_acceptable_vol20
        self.enable_liquidity_gate = enable_liquidity_gate
        self.enable_credit_gate = enable_credit_gate
        self.enable_forensics_gate = enable_forensics_gate
        self.enable_kalman_filter = enable_kalman_filter
        self.amihud_engine = AmihudLiquidityEngine(lookback_days=20)
        self.merton_engine = MertonStructuralDefaultEngine()
        self.forensics_engine = ForensicsAndTrailingExitEngine()
        self.kalman_engine = MeanReversionKalmanEngine()

    @staticmethod
    def _get_pit_bars(bars: List[Dict[str, Any]], as_of_date: str) -> List[Dict[str, Any]]:
        """以 O(log N) 二分极速定位点时已实现日线切片，消除全量列表推导开销."""
        if not bars:
            return []
        if str(bars[-1]["date"]) <= as_of_date:
            return bars
        if str(bars[0]["date"]) > as_of_date:
            return []
        lo, hi = 0, len(bars)
        while lo < hi:
            mid = (lo + hi) // 2
            if str(bars[mid]["date"]) <= as_of_date:
                lo = mid + 1
            else:
                hi = mid
        return bars[:lo]

    def screen_universe_at_date(
        self,
        as_of_date: str,
        historical_universe_bars: Dict[str, List[Dict[str, Any]]],
        historical_benchmark_bars: List[Dict[str, Any]],
        top_k: int = 12,
        company_debt_profiles: Optional[Dict[str, Dict[str, float]]] = None,
        company_financial_profiles: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> Tuple[List[StockScreeningScore], List[str]]:
        """在历史任意点时 as_of_date 截面上执行全资产池动态筛选与打分.

        Args:
            as_of_date: 调仓评估日期 (YYYY-MM-DD)，仅使用 <= 该日期的已发生数据
            historical_universe_bars: 各标的全部日线序列
            historical_benchmark_bars: 大盘基准全部日线序列
            top_k: 选出的击球区标的数量上限 (默认扩容至12)
            company_debt_profiles: 可选的企业债务与资产结构配置 (用于 Merton 信用违约门禁)
            company_financial_profiles: 可选的企业财报科目底账 (用于 Beneish M-Score 财务舞弊排雷门禁)

        Returns:
            Tuple[打分明细列表(按得分降序), 建议入池标的代码列表]
        """
        if top_k <= 0:
            raise ValueError(f"top_k 必须 > 0, 当前: {top_k}")
        if not historical_universe_bars:
            raise ValueError("候选资产池日线数据不能为空")
        if not historical_benchmark_bars:
            raise ValueError("大盘基准日线数据不能为空")

        # 1. 严格时点截断基准数据
        bench_point_in_time = self._get_pit_bars(historical_benchmark_bars, as_of_date)
        if len(bench_point_in_time) < 60:
            return [], []

        bench_curr = bench_point_in_time[-1]["close"]
        bench_120d_ago = bench_point_in_time[-120]["close"] if len(bench_point_in_time) >= 120 else bench_point_in_time[0]["close"]
        bench_perf_6m = (bench_curr / bench_120d_ago) - 1.0 if bench_120d_ago > 0 else 0.0

        scores: List[StockScreeningScore] = []

        # 2. 对每个标的进行点时指标提取与打分
        for symbol, all_bars in historical_universe_bars.items():
            # 严格时点截断：只看 <= as_of_date 的已实现行情
            pit_bars = self._get_pit_bars(all_bars, as_of_date)
            if len(pit_bars) < self.min_lookback_bars:
                # 历史长度不足，无法稳定计算 EMA200，安全排除
                continue

            today_bar = pit_bars[-1]
            c = float(today_bar["close"])
            if c <= 0:
                continue

            # 提取与计算指标
            closes = [float(b["close"]) for b in pit_bars]
            highs = [float(b.get("high", b["close"])) for b in pit_bars]
            lows = [float(b.get("low", b["close"])) for b in pit_bars]
            n = len(closes)

            # 52 周最高价、最低价与走廊
            lookback_52w = min(n, 252)
            high_52w = max(highs[-lookback_52w:])
            low_52w = min(lows[-lookback_52w:])

            # 计算 ATR20 (Average True Range 20日均值)
            tr_list = []
            for i in range(max(1, n - 20), n):
                h_i = highs[i]
                l_i = lows[i]
                c_prev = closes[i - 1]
                tr = max(h_i - l_i, abs(h_i - c_prev), abs(l_i - c_prev))
                tr_list.append(tr)
            atr20 = sum(tr_list) / len(tr_list) if tr_list else (highs[-1] - lows[-1])

            # 计算 EMA20, EMA50, EMA200 与 EMA200 通道倾角
            ema20 = self._calc_ema(closes, span=20)
            ema50 = self._calc_ema(closes, span=50)
            ema200 = self._calc_ema(closes, span=200)
            ema200_20d_ago = self._calc_ema(closes[:-20], span=200) if n >= 220 else ema200
            is_ema200_rising = (ema200 >= ema200_20d_ago)

            # 20日历史年化波动率与下行半方差 (严密数学边界防御：防零/负价格引发 math domain error)
            recent_20 = closes[-21:]
            log_returns = []
            for i in range(1, len(recent_20)):
                p_prev = recent_20[i - 1]
                p_curr = recent_20[i]
                if p_prev > 1e-6 and p_curr > 1e-6:
                    log_returns.append(math.log(p_curr / p_prev))
                else:
                    log_returns.append(0.0)

            mean_ret = sum(log_returns) / len(log_returns) if log_returns else 0.0
            variance = sum((r - mean_ret) ** 2 for r in log_returns) / (len(log_returns) - 1) if len(log_returns) > 1 else 0.0
            vol20 = math.sqrt(max(0.0, variance * 252.0))

            # 下行半方差与下行波动率 (Downside Volatility / Sortino 风险基准)
            downside_returns = [min(0.0, r) for r in log_returns]
            downside_var = sum(r ** 2 for r in downside_returns) / (len(downside_returns) - 1) if len(downside_returns) > 1 else 0.0
            downside_vol20 = math.sqrt(max(0.0, downside_var * 252.0))

            # 60日波动率以识别波动率异动飙升 (Volatility Surge)
            recent_60 = closes[-61:] if n >= 61 else closes
            log_ret_60 = []
            for i in range(1, len(recent_60)):
                p0 = recent_60[i - 1]
                p1 = recent_60[i]
                if p0 > 1e-6 and p1 > 1e-6:
                    log_ret_60.append(math.log(p1 / p0))
                else:
                    log_ret_60.append(0.0)
            mean_ret_60 = sum(log_ret_60) / len(log_ret_60) if log_ret_60 else 0.0
            var_60 = sum((r - mean_ret_60) ** 2 for r in log_ret_60) / (len(log_ret_60) - 1) if len(log_ret_60) > 1 else 0.0
            vol60 = math.sqrt(max(0.0, var_60 * 252.0))

            # 中期动量 (12M - 1M) 与短期 1M 收益解耦 (Daniel & Moskowitz 2016 动量崩盘防御)
            p_21_ago = closes[-21] if n >= 21 else closes[0]
            p_12m_ago = closes[-lookback_52w] if n >= lookback_52w else closes[0]
            inter_momentum_12_1 = (p_21_ago / p_12m_ago) - 1.0 if p_12m_ago > 1e-6 else 0.0
            ret_1m = (c / p_21_ago) - 1.0 if p_21_ago > 1e-6 else 0.0

            # 6个月超额收益 RS 计算（防除零与仙股负数）
            p_120_ago = closes[-120] if n >= 120 else closes[0]
            stock_perf_6m = (c / p_120_ago) - 1.0 if p_120_ago > 1e-6 else 0.0
            excess_return_6m = stock_perf_6m - bench_perf_6m

            # 市场属性判断 (日股 vs 美股)
            is_japan_stock = symbol.endswith(".T")

            # 3. 维度打分 (根据 strategy_model 区分流派哲学)
            is_stage2 = (c > ema50) and (ema20 > ema50) and (ema50 > ema200)
            is_stage4 = (c < ema50) and (ema50 < ema200)
            price_ema200_ratio = c / ema200 if ema200 > 0 else 1.0

            in_strike_zone = True
            disqualify_reason = None
            ou_half_life_val: Optional[float] = None
            kalman_z_val: Optional[float] = None
            beneish_m_val: Optional[float] = None
            is_fraud_suspect_val: bool = False

            if self.strategy_model == "MOMENTUM_SEPA":
                # 模型 A: 纯动量时机型 (SEPA / VCP + Daniel & Moskowitz 动量崩盘防御)
                # 动量评分基于 (12M - 1M) 中期动量，剔除末月噪音；融合超额收益
                rs_score = max(0.0, min(120.0, 50.0 + (excess_return_6m * 120.0) + (inter_momentum_12_1 * 50.0)))
                trend_score = 40.0 if (is_stage2 and is_ema200_rising) else (20.0 if is_stage2 else (-50.0 if is_stage4 else 0.0))
                valuation_penalty = 0.0

                # 动量崩盘防御门禁：
                # 1. 短期暴跌且波动激增 (Reversal Crash): 近1个月跌幅超过 15% 且 20日波动率 > 50%
                is_momentum_crash = (ret_1m < -0.15 and vol20 > 0.50)
                # 2. 波动率陡然脉冲式飙升 (Volatility Surge): vol20 超过 vol60 1.8倍
                is_vol_surge = (vol60 > 0.15 and vol20 > 1.8 * vol60 and vol20 > 0.45)

                volatility_score = -35.0 if is_vol_surge else (-20.0 if vol20 > 0.70 else 0.0)
                composite = rs_score + trend_score + valuation_penalty + volatility_score

                if is_stage4:
                    in_strike_zone = False
                    disqualify_reason = "STAGE4_BEARISH_TREND (动量模型严禁逆势持股)"
                elif is_momentum_crash:
                    in_strike_zone = False
                    disqualify_reason = "MOMENTUM_CRASH_DEFENSE (短期断崖回撤触发崩盘熔断)"
                elif is_vol_surge:
                    in_strike_zone = False
                    disqualify_reason = "VOLATILITY_BURST_SURGE (20日波动率陡增超60日1.8倍)"
                elif rs_score < 45.0:
                    in_strike_zone = False
                    disqualify_reason = "MOMENTUM_TOO_WEAK (相对动量不足)"
                elif vol20 > 0.75:
                    in_strike_zone = False
                    disqualify_reason = "EXTREME_VOLATILITY_BURST (极端波动率过高)"

            elif self.strategy_model == "MOAT_VALUE":
                # 模型 B: 护城河价值与安全边际型 (Moat & Safe Margin)
                # 彻底根治“均线中枢折价导致熊市接飞刀”的伪价值陷阱：
                # 1. 均线中枢必须具备向上倾斜或水平支撑 (is_ema200_rising)；
                # 2. 距离 52周低点必须有安全底衬 (c >= 1.10 * low_52w)，严禁抄底破位阴跌股；
                # 3. 距离 52周高点不过度深跌 (c >= 0.55 * high_52w)，防范价值毁灭；
                # 4. 奖励低下行半方差 (downside_vol20 < 0.18)，惩罚高下行肥尾风险。

                # 日股市场脱耦自适应：日股更侧重均值回归与股息护城河底价
                if is_japan_stock:
                    rs_score = max(0.0, min(100.0, 45.0 + (excess_return_6m * 40.0)))
                    trend_score = 25.0 if (c >= ema200 and is_ema200_rising) else (10.0 if c >= ema50 else -30.0)
                else:
                    rs_score = max(0.0, min(100.0, 40.0 + (excess_return_6m * 60.0)))
                    trend_score = 20.0 if (c > ema200 and is_ema200_rising) else (5.0 if c > ema200 else -35.0)

                # 估值与价格安全边际评分 (基于 52周走廊与均线支撑品质)
                ratio_52w_low = c / low_52w if low_52w > 1e-6 else 1.0

                if not is_ema200_rising and c < ema200:
                    # EMA200 向下倾斜且股价在其下方：典型破位飞刀，重罚！
                    valuation_penalty = -40.0
                elif 1.0 <= price_ema200_ratio <= 1.25 and is_ema200_rising:
                    # 健康上升通道中的合理折价中枢
                    valuation_penalty = 30.0
                elif price_ema200_ratio > 1.35:
                    overhang = price_ema200_ratio - 1.35
                    valuation_penalty = -min(50.0, overhang * 200.0)
                else:
                    valuation_penalty = 0.0

                # 下行半方差与下行波动率奖励 (真正护城河资产的核心特征是下行波动极低)
                if downside_vol20 < 0.16:
                    volatility_score = 30.0
                elif downside_vol20 < 0.25:
                    volatility_score = 15.0
                elif downside_vol20 > 0.35:
                    volatility_score = -25.0
                else:
                    volatility_score = 0.0

                # 卡尔曼滤波与 OU 均值回归副武器自适应支撑 (消除高频噪声与识别真实回归中枢)
                if self.enable_kalman_filter and n >= 30:
                    recent_series = closes[-60:] if n >= 60 else closes
                    try:
                        ou_res = self.kalman_engine.fit_ou_process(recent_series)
                        kalman_res = self.kalman_engine.apply_kalman_filter(recent_series)
                        ou_half_life_val = round(ou_res.half_life_days, 1)
                        kalman_z_val = round(ou_res.current_zscore, 2)

                        if ou_res.is_mean_reverting:
                            # 具备快速均值回归动力且偏离均衡中枢，给予强支撑加分
                            if ou_res.current_zscore < -1.0 and 3.0 <= ou_res.half_life_days <= 45.0:
                                trend_score += 15.0
                            elif ou_res.half_life_days > 75.0:
                                valuation_penalty -= 20.0
                        if kalman_res.channel_position_pct < 0.15:
                            trend_score += 10.0
                    except Exception:
                        pass

                composite = rs_score + trend_score + valuation_penalty + volatility_score

                # 硬门禁
                if is_stage4 or (c < ema200 and not is_ema200_rising):
                    in_strike_zone = False
                    disqualify_reason = "FALLING_KNIFE_BREAKDOWN (长期均线下行且破位，严防飞刀陷阱)"
                elif ratio_52w_low < 1.10:
                    in_strike_zone = False
                    disqualify_reason = "NEAR_52W_LOW_SPIRAL (距52周新低不足10%，防破产滑落)"
                elif price_ema200_ratio > 1.45:
                    in_strike_zone = False
                    disqualify_reason = "VALUATION_OVERHANG_EXCESSIVE (估值严重透支)"
                elif downside_vol20 > 0.42:
                    in_strike_zone = False
                    disqualify_reason = "DOWNSIDE_VOLATILITY_TOO_HIGH (下行肥尾风险过大)"

            elif self.strategy_model == "VAR_TAIL_RISK":
                # 模型 C: 动态尾部风控型 (VaR / Sortino 偏度下行风控)
                # 摆脱简单历史全方差无脑惩罚上行收益的缺陷，转向下行半方差与上/下偏度度量
                rs_score = max(0.0, min(100.0, 45.0 + (excess_return_6m * 100.0)))
                trend_score = 25.0 if (is_stage2 and is_ema200_rising) else (10.0 if not is_stage4 else -40.0)

                # 下行波动率与正偏度奖励
                upside_returns = [max(0.0, r) for r in log_returns]
                upside_var = sum(r ** 2 for r in upside_returns) / (len(upside_returns) - 1) if len(upside_returns) > 1 else 0.0
                upside_vol20 = math.sqrt(max(0.0, upside_var * 252.0))

                if downside_vol20 < 0.15:
                    volatility_score = 40.0
                elif downside_vol20 < 0.24:
                    volatility_score = 20.0
                elif downside_vol20 > 0.35:
                    volatility_score = -35.0
                else:
                    volatility_score = 0.0

                # 若具有显著正偏度 (上行波动 > 下行波动 1.2倍)，给予正偏度凸性奖励
                if upside_vol20 > 1.2 * (downside_vol20 + 1e-6):
                    volatility_score += 10.0

                valuation_penalty = -25.0 if price_ema200_ratio > 1.35 else 0.0
                composite = rs_score + trend_score + valuation_penalty + volatility_score

                if downside_vol20 > 0.38:
                    in_strike_zone = False
                    disqualify_reason = "DOWNSIDE_SEMI_VARIANCE_BREACH (超出下行半方差风险预算)"
                elif is_stage4:
                    in_strike_zone = False
                    disqualify_reason = "TAIL_RISK_STAGE4_EXIT (熊市破位强制避险)"

            else:
                # 模型 D: 机构全息复合型 (FULL_QUANTAMENTAL, 默认)
                rs_score = max(0.0, min(100.0, 50.0 + (excess_return_6m * 150.0)))
                trend_score = self.stage2_bonus if (is_stage2 and is_ema200_rising) else (self.stage2_bonus * 0.7 if is_stage2 else (self.stage4_penalty if is_stage4 else 0.0))

                if price_ema200_ratio > self.max_price_to_ema200:
                    overhang_pct = (price_ema200_ratio - self.max_price_to_ema200)
                    valuation_penalty = -min(30.0, overhang_pct * 100.0)
                elif price_ema200_ratio < 0.90 and not is_ema200_rising:
                    valuation_penalty = -25.0
                else:
                    valuation_penalty = 0.0

                if downside_vol20 < 0.18:
                    volatility_score = 20.0
                elif vol20 < 0.30:
                    volatility_score = 10.0
                elif vol20 > self.max_acceptable_vol20:
                    volatility_score = -25.0
                else:
                    volatility_score = 0.0

                composite = rs_score + trend_score + valuation_penalty + volatility_score

                if is_stage4:
                    in_strike_zone = False
                    disqualify_reason = "STAGE4_BEARISH_TREND (长期均线破位)"
                elif vol20 > 0.65:
                    in_strike_zone = False
                    disqualify_reason = "EXTREME_VOLATILITY_RISK (波动率超过65%)"
                elif price_ema200_ratio > 1.65:
                    in_strike_zone = False
                    disqualify_reason = "EXTREME_OVERBOUGHT (股价脱离EMA200超65%)"
                elif composite < 50.0:
                    in_strike_zone = False
                    disqualify_reason = "COMPOSITE_SCORE_TOO_LOW (综合得分低于50)"

            # 4. 微观流动性冲击与 Amihud 门禁核算
            market_type = "JP" if is_japan_stock else "US"
            amihud_res = self.amihud_engine.evaluate_liquidity(
                symbol=symbol,
                bars=pit_bars,
                market=market_type,
            )
            amihud_ratio_val = amihud_res.amihud_illiquidity_ratio
            liq_tier_val = amihud_res.capacity_tier

            if self.enable_liquidity_gate and amihud_res.is_illiquid_trap:
                in_strike_zone = False
                disqualify_reason = "ILLIQUID_MICRO_CAP_TRAP (微盘股流动性枯竭或冲击过大)"

            # 5. KMV-Merton 结构化信用违约与破产黑天鹅前瞻门禁
            dist_to_default_val = None
            is_credit_distressed_val = False

            if self.enable_credit_gate and company_debt_profiles and symbol in company_debt_profiles:
                debt_info = company_debt_profiles[symbol]
                m_cap = debt_info.get("market_cap", c * 10_000_000.0)
                std = debt_info.get("short_term_debt", 0.0)
                ltd = debt_info.get("long_term_debt", 0.0)
                merton_res = self.merton_engine.evaluate_credit_default_risk(
                    equity_market_cap=m_cap,
                    short_term_debt=std,
                    long_term_debt=ltd,
                    equity_volatility_annual=vol20,
                )
                dist_to_default_val = merton_res.distance_to_default
                is_credit_distressed_val = merton_res.is_black_swan_alert

                if merton_res.is_black_swan_alert:
                    in_strike_zone = False
                    disqualify_reason = f"CRITICAL_DEFAULT_RISK (KMV-Merton违约距离DD={merton_res.distance_to_default:.2f}破产预警)"

            # 6. Beneish M-Score 八维法务会计财务防舞弊排雷门禁 (一票否决)
            if self.enable_forensics_gate and company_financial_profiles and symbol in company_financial_profiles:
                fin = company_financial_profiles[symbol]
                try:
                    m_res = self.forensics_engine.compute_beneish_m_score(
                        curr_sales=fin.get("curr_sales", 100.0),
                        curr_cogs=fin.get("curr_cogs", 60.0),
                        curr_receivables=fin.get("curr_receivables", 20.0),
                        curr_current_assets=fin.get("curr_current_assets", 80.0),
                        curr_ppe_net=fin.get("curr_ppe_net", 50.0),
                        curr_securities=fin.get("curr_securities", 10.0),
                        curr_total_assets=fin.get("curr_total_assets", 150.0),
                        curr_depreciation=fin.get("curr_depreciation", 5.0),
                        curr_sga=fin.get("curr_sga", 15.0),
                        curr_long_term_debt=fin.get("curr_long_term_debt", 30.0),
                        curr_current_liabilities=fin.get("curr_current_liabilities", 25.0),
                        curr_net_income=fin.get("curr_net_income", 15.0),
                        curr_cfo=fin.get("curr_cfo", 18.0),
                        prev_sales=fin.get("prev_sales", 90.0),
                        prev_cogs=fin.get("prev_cogs", 55.0),
                        prev_receivables=fin.get("prev_receivables", 18.0),
                        prev_current_assets=fin.get("prev_current_assets", 75.0),
                        prev_ppe_net=fin.get("prev_ppe_net", 48.0),
                        prev_securities=fin.get("prev_securities", 10.0),
                        prev_total_assets=fin.get("prev_total_assets", 140.0),
                        prev_depreciation=fin.get("prev_depreciation", 4.8),
                        prev_sga=fin.get("prev_sga", 14.0),
                        prev_long_term_debt=fin.get("prev_long_term_debt", 28.0),
                        prev_current_liabilities=fin.get("prev_current_liabilities", 22.0),
                    )
                    beneish_m_val = m_res.m_score
                    is_fraud_suspect_val = m_res.is_manipulation_suspect
                    if m_res.is_manipulation_suspect:
                        in_strike_zone = False
                        flag_txt = ", ".join(m_res.flagged_dimensions[:2]) if m_res.flagged_dimensions else "财务指标异常"
                        disqualify_reason = f"BENEISH_FRAUD_ALERT (Beneish M-Score={m_res.m_score:.2f} 触发造假一票否决: {flag_txt})"
                except Exception:
                    pass

            scores.append(StockScreeningScore(
                symbol=symbol,
                date=as_of_date,
                current_price=c,
                is_stage2=is_stage2,
                rs_score=round(rs_score, 2),
                trend_score=round(trend_score, 2),
                valuation_penalty=round(valuation_penalty, 2),
                volatility_score=round(volatility_score, 2),
                composite_score=round(composite, 2),
                in_strike_zone=in_strike_zone,
                disqualification_reason=disqualify_reason,
                amihud_ratio=round(amihud_ratio_val, 4),
                liquidity_tier=liq_tier_val,
                distance_to_default=round(dist_to_default_val, 2) if dist_to_default_val is not None else None,
                is_credit_distressed=is_credit_distressed_val,
                atr20=round(atr20, 4),
                downside_vol20=round(downside_vol20, 4),
                inter_momentum=round(inter_momentum_12_1, 4),
                ret_1m=round(ret_1m, 4),
                is_japan=is_japan_stock,
                beneish_m_score=beneish_m_val,
                is_fraud_suspect=is_fraud_suspect_val,
                kalman_z_score=kalman_z_val,
                ou_half_life=ou_half_life_val,
            ))

        # 4. 按综合得分降序排列
        scores.sort(key=lambda s: s.composite_score, reverse=True)

        # 5. 选出进入击球区的 Top-K 标的
        eligible = [s.symbol for s in scores if s.in_strike_zone]
        selected_symbols = eligible[:top_k]

        return scores, selected_symbols

    def filter_with_hysteresis(
        self,
        current_holdings: List[str],
        ranked_scores: List[StockScreeningScore],
        top_k: int = 12,
        buffer_rank: int = 40,
        holding_bars_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        as_of_date: Optional[str] = None,
    ) -> Tuple[List[str], List[str]]:
        """应用滞后持仓缓冲区 (Hysteresis Buffer) 判定当期保留与买入标的.

        规则：
        1. 保留标的 (Keep): 存量持仓若当期排名仍位于 buffer_rank (默认40) 以内，
           且仍处于买方击球区 (未触发硬止损/破位/黑天鹅)，并且未跌破 EMA50，继续持有！
           彻底杜绝在第3名与第4名之间频繁调仓的无谓摩擦。
        2. 买入标的 (Buy): 若保留持仓数不足 top_k，从排名靠前的未持仓击球区标的中选优补足。

        Returns:
            Tuple[新增买入标的代码列表, 保留继续持有标的代码列表]
        """
        score_lookup = {s.symbol: (rank, s) for rank, s in enumerate(ranked_scores, start=1)}

        to_keep: List[str] = []
        for sym in current_holdings:
            if sym in score_lookup:
                rank, s = score_lookup[sym]
                # 检查是否破位 EMA50 (如果提供了历史日线)
                broke_ema50 = False
                if holding_bars_map and as_of_date and sym in holding_bars_map:
                    p_bars = self._get_pit_bars(holding_bars_map[sym], as_of_date)
                    if len(p_bars) >= 50:
                        c_now = float(p_bars[-1]["close"])
                        e50 = self._calc_ema([float(b["close"]) for b in p_bars], span=50)
                        if c_now < e50 * 0.98:  # 明确跌破 EMA50 2%
                            broke_ema50 = True

                if rank <= buffer_rank and s.in_strike_zone and not broke_ema50:
                    to_keep.append(sym)

        # 补足新标的
        needed_count = max(0, top_k - len(to_keep))
        to_buy: List[str] = []
        for s in ranked_scores:
            if len(to_buy) >= needed_count:
                break
            if s.symbol not in to_keep and s.in_strike_zone:
                to_buy.append(s.symbol)

        return to_buy, to_keep

    @staticmethod
    def _calc_ema(prices: List[float], span: int) -> float:
        """纯标准库高效计算单一序列的最终点位 EMA."""
        if not prices:
            return 0.0
        alpha = 2.0 / (span + 1.0)
        ema = prices[0]
        for p in prices[1:]:
            ema = alpha * p + (1.0 - alpha) * ema
        return ema
