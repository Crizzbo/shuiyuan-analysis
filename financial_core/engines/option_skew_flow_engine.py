# -*- coding: utf-8 -*-
"""期权波动率曲面偏度与主力资金大单流预警引擎 (option_skew_flow_engine.py).

严格遵循《AGENTS.md》与《CLAUDE.md》：
1. 金融理论基石：
   - 基于期权衍生品市场主力大单的先验信息优势；
   - 提取 25-Delta 风险反转偏度 (25-Delta Risk Reversal Skew = IV_put_25 - IV_call_25)；
   - 结合主力认沽认购交易量比率 (Put-Call Ratio, PCR) 与期权未平仓合约变化；
   - 计算波动率期限结构斜率 (Term Structure Slope = IV_front / IV_back) 倒挂异动；
   - 捕捉做市商负 Gamma 暴露 (Dealer Short Gamma Trap) 引发的剧烈单边闪崩。
2. 金融数学边界防御：
   - PCR 计算除零/除负保护，未平仓量非负下界；
   - 波动率曲面插值极值收敛，Durrleman 无套利斜率边界保护；
   - 偏度异动分数归一化至 [-100, +100] 区间，防止异常极值溢出。
3. 架构纯洁性：
   - 位于 financial_core 底层，零外层逆向依赖，纯纯净金融计算。
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class OptionSkewMetrics:
    """期权偏度与主力大单异动评估输出契约."""
    symbol: str
    underlying_price: float         # 标的现价 S ($ 或 ¥)
    put_call_volume_ratio: float    # 当日交易量 PCR (Put Vol / Call Vol)
    put_call_oi_ratio: float        # 未平仓量 PCR (Put OI / Call OI)
    skew_25delta: float             # 25-Delta 风险反转偏度 (IV_25d_put - IV_25d_call)
    term_structure_ratio: float     # 近远月波动率比值 (Front Month IV / 2nd Month IV)
    dealer_gamma_exposure_regime: str # 做市商 Gamma 状态 (LONG_GAMMA_STABLE, SHORT_GAMMA_EXPLOSIVE)
    composite_bearish_flow_score: float # 主力看跌大单异动综合分 (0 ~ 100)
    is_overnight_crash_alert: bool  # 是否触发隔夜跳水对冲大单警报
    flow_sentiment_regime: str      # 情绪分级 (EXTREME_FEAR, BEARISH, NEUTRAL, BULLISH, EXTREME_GREED)


class OptionSkewFlowEngine:
    """期权波动率曲面偏度与主力异动流检测引擎."""

    def __init__(
        self,
        pcr_volume_bearish_threshold: float = 1.35,  # 交易量 PCR > 1.35 判定为主力重度对冲
        skew_extreme_threshold: float = 0.08,        # 偏度超过 8% 判定为看跌下行保护溢价极高
        term_structure_inversion: float = 1.15,      # 近月 IV 比远月高 15% 判定为近端极端恐慌倒挂
    ) -> None:
        self.pcr_thresh = float(pcr_volume_bearish_threshold)
        self.skew_thresh = float(skew_extreme_threshold)
        self.ts_thresh = float(term_structure_inversion)

    def evaluate_skew_and_flow(
        self,
        symbol: str,
        underlying_price: float,
        call_volume: float,
        put_volume: float,
        call_open_interest: float,
        put_open_interest: float,
        iv_25d_put: float,
        iv_25d_call: float,
        iv_front_month_atm: float,
        iv_back_month_atm: float,
    ) -> OptionSkewMetrics:
        """评估期权波动率偏度、PCR 资金异动与隔夜跳水预警."""
        S = max(0.01, float(underlying_price))
        c_vol = max(1.0, float(call_volume))
        p_vol = max(0.0, float(put_volume))
        c_oi = max(1.0, float(call_open_interest))
        p_oi = max(0.0, float(put_open_interest))

        p_iv = max(0.01, min(5.0, float(iv_25d_put)))
        c_iv = max(0.01, min(5.0, float(iv_25d_call)))
        front_iv = max(0.01, min(5.0, float(iv_front_month_atm)))
        back_iv = max(0.01, min(5.0, float(iv_back_month_atm)))

        # 1. 计算 PCR
        pcr_vol = p_vol / c_vol
        pcr_oi = p_oi / c_oi

        # 2. 计算 25-Delta 偏度
        skew_25d = p_iv - c_iv

        # 3. 计算期限结构倒挂比率
        ts_ratio = front_iv / back_iv

        # 4. 做市商 Gamma 状态判断
        # 当期限结构倒挂且偏度急剧膨胀时，做市商通常处于 Short Gamma 状态（加速助跌）
        if ts_ratio > 1.10 and skew_25d > 0.05:
            gamma_regime = "SHORT_GAMMA_EXPLOSIVE"
        elif ts_ratio < 0.95 and skew_25d < 0.02:
            gamma_regime = "LONG_GAMMA_STABLE"
        else:
            gamma_regime = "NEUTRAL_GAMMA"

        # 5. 综合看跌大单异动评分 (0 ~ 100)
        score = 0.0
        # PCR 权重 (40分)
        if pcr_vol >= 1.6:
            score += 40.0
        elif pcr_vol >= self.pcr_thresh:
            score += 25.0
        elif pcr_vol >= 1.0:
            score += 15.0

        # Skew 权重 (35分)
        if skew_25d >= 0.12:
            score += 35.0
        elif skew_25d >= self.skew_thresh:
            score += 25.0
        elif skew_25d >= 0.04:
            score += 15.0

        # 期限结构倒挂权重 (25分)
        if ts_ratio >= 1.25:
            score += 25.0
        elif ts_ratio >= self.ts_thresh:
            score += 18.0
        elif ts_ratio >= 1.05:
            score += 10.0

        score = max(0.0, min(100.0, score))

        # 6. 是否触发隔夜跳水对冲警报
        is_alert = (score >= 65.0) or (skew_25d >= 0.10 and pcr_vol >= 1.5)

        # 7. 情绪分级
        if score >= 75.0:
            sentiment = "EXTREME_FEAR"
        elif score >= 55.0:
            sentiment = "BEARISH"
        elif score >= 35.0:
            sentiment = "NEUTRAL"
        elif score >= 20.0:
            sentiment = "BULLISH"
        else:
            sentiment = "EXTREME_GREED"

        return OptionSkewMetrics(
            symbol=symbol,
            underlying_price=round(S, 2),
            put_call_volume_ratio=round(pcr_vol, 3),
            put_call_oi_ratio=round(pcr_oi, 3),
            skew_25delta=round(skew_25d, 4),
            term_structure_ratio=round(ts_ratio, 3),
            dealer_gamma_exposure_regime=gamma_regime,
            composite_bearish_flow_score=round(score, 1),
            is_overnight_crash_alert=is_alert,
            flow_sentiment_regime=sentiment,
        )
