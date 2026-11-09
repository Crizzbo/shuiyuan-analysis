# -*- coding: utf-8 -*-
"""震荡市高抛低吸副武器：均值回归与动态状态估计引擎 (mean_reversion_kalman_engine.py).

遵循《AGENTS.md》与《CLAUDE.md》：
1. 底层纯净金融核心层：零逆向依赖，纯数学与统计推导；
2. 震荡市高抛低吸两大副武器：
   - OU (Ornstein-Uhlenbeck) 连续均值回归过程：回归速率 theta、长期均衡中枢 mu、
     特征半衰期 half_life_days 以及标准差 Z-Score 偏离度计算；
   - 1D 自适应卡尔曼滤波 (Kalman Filter)：消除短期高频噪声，提取潜在真实资产价值，
     输出卡尔曼动态包络通道 (Kalman Bands) 与超买超卖信号；
3. 数学边界防护：除零保护、特征根平稳性检验 (b < 1.0)、有限责任下界。
"""

from dataclasses import dataclass, asdict
import math
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class OUProcessResult:
    """OU 均值回归过程参数契约."""
    is_mean_reverting: bool       # 是否具备统计显著的均值回归特性
    theta: float                  # 回归速度参数 (越大回归越快)
    equilibrium_mu: float         # 长期均衡中枢价格
    sigma: float                  # 扩散过程波动率
    half_life_days: float         # 特征半衰期 (单位: 交易日)
    current_zscore: float         # 当前价格偏离均衡中枢的标准化 Z-Score
    signal_recommendation: str    # "OVERSOLD_BUY" (超跌吸筹), "OVERBOUGHT_SELL" (超买抛出), "HOLD_WAIT"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KalmanFilterResult:
    """卡尔曼滤波去噪与动态通道契约."""
    filtered_price: float         # 最新卡尔曼滤波平滑真实价格
    estimation_error_std: float   # 估计误差标准差
    kalman_upper_band: float      # 自适应上轨 (高抛阻力位: Filtered + 2 * Std)
    kalman_lower_band: float      # 自适应下轨 (低吸支撑位: Filtered - 2 * Std)
    kalman_gain: float            # 当前时点卡尔曼增益 K_t
    raw_close: float              # 原始最新收盘价
    channel_position_pct: float   # 现价在通道内的相对百分比分位数 (0.0~1.0)
    noise_reduction_ratio: float  # 杂波过滤降噪比率

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MeanReversionVerdict:
    """震荡市高抛低吸综合研判决策契约."""
    ticker: str
    as_of_date: str
    ou_result: OUProcessResult
    kalman_result: KalmanFilterResult
    swing_action: str             # "STRONG_BUY_DIP", "STRONG_SELL_PEAK", "NEUTRAL"
    expected_profit_pct: float    # 预期回归中枢利润空间百分比
    rationale_zh: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "as_of_date": self.as_of_date,
            "ou_result": self.ou_result.to_dict(),
            "kalman_result": self.kalman_result.to_dict(),
            "swing_action": self.swing_action,
            "expected_profit_pct": self.expected_profit_pct,
            "rationale_zh": self.rationale_zh,
        }


class MeanReversionKalmanEngine:
    """震荡市副武器：OU 均值回归与卡尔曼动态状态估计引擎."""

    def __init__(
        self,
        dt: float = 1.0,                       # 日度时间步长
        min_half_life_days: float = 2.0,       # 最小合理半衰期 (低于2天为超高频噪声)
        max_half_life_days: float = 60.0,      # 最大合理半衰期 (高于60天视为失去均值回归时效)
        zscore_entry_threshold: float = 1.75,  # 触发高抛低吸的 Z 分数绝对值门槛
        process_noise_var: float = 1e-4,       # 卡尔曼滤波过程噪声方差 Q
        measurement_noise_var: float = 1e-2,   # 卡尔曼滤波观测噪声方差 R
    ):
        self.dt = dt
        self.min_half_life_days = min_half_life_days
        self.max_half_life_days = max_half_life_days
        self.zscore_entry_threshold = zscore_entry_threshold
        self.q_var = process_noise_var
        self.r_var = measurement_noise_var

    def fit_ou_process(self, price_series: List[float]) -> OUProcessResult:
        """拟合 Ornstein-Uhlenbeck (OU) 均值回归扩散模型并计算特征半衰期与 Z-Score."""
        if not price_series or len(price_series) < 20:
            raise ValueError(f"拟合 OU 过程需要至少 20 个价格时序点，当前提供: {len(price_series) if price_series else 0}")

        N = len(price_series) - 1
        X_prev = price_series[:-1]
        X_curr = price_series[1:]

        # OLS 最小二乘求解 AR(1): X_t = a + b * X_{t-1} + e_t
        mean_prev = sum(X_prev) / N
        mean_curr = sum(X_curr) / N

        cov_xy = sum((X_prev[i] - mean_prev) * (X_curr[i] - mean_curr) for i in range(N))
        var_x = sum((X_prev[i] - mean_prev) ** 2 for i in range(N))

        if var_x < 1e-12:
            return OUProcessResult(
                is_mean_reverting=False,
                theta=0.0,
                equilibrium_mu=price_series[-1],
                sigma=0.0,
                half_life_days=999.0,
                current_zscore=0.0,
                signal_recommendation="HOLD_WAIT",
            )

        b = cov_xy / var_x
        a = mean_curr - b * mean_prev

        # 计算回归残差方差
        residuals = [X_curr[i] - (a + b * X_prev[i]) for i in range(N)]
        sse = sum(e ** 2 for e in residuals)
        var_e = sse / max(N - 2, 1)

        # 平稳性判断: b 必须严格小于 1.0 (否则为单位根发散或趋势扩张)
        if b >= 0.9999 or b <= 0.0:
            return OUProcessResult(
                is_mean_reverting=False,
                theta=0.0,
                equilibrium_mu=round(price_series[-1], 2),
                sigma=round(math.sqrt(max(var_e, 0.0)), 4),
                half_life_days=999.0,
                current_zscore=0.0,
                signal_recommendation="HOLD_WAIT",
            )

        # 参数反解
        theta = -math.log(b) / self.dt
        equilibrium_mu = a / max(1.0 - b, 1e-6)

        # 稳态无条件方差: Var_inf = var_e / (1 - b^2)
        denom_var = max(1.0 - (b ** 2), 1e-6)
        steady_state_var = var_e / denom_var
        steady_state_std = math.sqrt(max(steady_state_var, 1e-8))

        # 连续过程扩散项 sigma = sqrt(2 * theta * Var_inf)
        sigma = math.sqrt(max(2.0 * theta * steady_state_var, 0.0))

        # 特征半衰期 t_half = ln(2) / theta
        half_life_days = math.log(2.0) / max(theta, 1e-6)

        # 当前价格偏离中枢的 Z-Score
        current_price = price_series[-1]
        zscore = (current_price - equilibrium_mu) / steady_state_std

        # 综合判定均值回归有效性与买卖信号
        is_mean_reverting = self.min_half_life_days <= half_life_days <= self.max_half_life_days

        if is_mean_reverting:
            if zscore <= -self.zscore_entry_threshold:
                signal = "OVERSOLD_BUY"  # 严重超跌，均值回归低吸
            elif zscore >= self.zscore_entry_threshold:
                signal = "OVERBOUGHT_SELL"  # 严重超买，均值回归高抛
            else:
                signal = "HOLD_WAIT"
        else:
            signal = "HOLD_WAIT"

        return OUProcessResult(
            is_mean_reverting=is_mean_reverting,
            theta=round(theta, 4),
            equilibrium_mu=round(equilibrium_mu, 2),
            sigma=round(sigma, 4),
            half_life_days=round(half_life_days, 1),
            current_zscore=round(zscore, 2),
            signal_recommendation=signal,
        )

    def apply_kalman_filter(self, price_series: List[float]) -> KalmanFilterResult:
        """运行 1D 线性自适应卡尔曼滤波算法，生成去噪价格与动态高抛低吸通道."""
        if not price_series or len(price_series) < 5:
            raise ValueError(f"卡尔曼滤波需要至少 5 个连续价格点，当前提供: {len(price_series) if price_series else 0}")

        # 状态初始化 (以首批样本均值为先验)
        x_hat = price_series[0]
        p_cov = self.r_var  # 初始估计误差协方差

        # 动态估计方差适应: 依据最近局部收益率动态缩放 Q 与 R
        if len(price_series) >= 10:
            returns = [
                price_series[i] / max(price_series[i - 1], 1e-6) - 1.0
                for i in range(1, len(price_series))
            ]
            ret_var = sum(r ** 2 for r in returns) / len(returns)
            q = max(ret_var * (x_hat ** 2) * 0.1, 1e-6)
            r = max(ret_var * (x_hat ** 2), 1e-4)
        else:
            q = self.q_var
            r = self.r_var

        filtered_history = []
        kalman_gains = []

        for z in price_series:
            # 1. 预测步 (Time Update)
            x_hat_minus = x_hat
            p_minus = p_cov + q

            # 2. 测量更新步 (Measurement Update)
            k = p_minus / (p_minus + r)
            x_hat = x_hat_minus + k * (z - x_hat_minus)
            p_cov = (1.0 - k) * p_minus

            filtered_history.append(x_hat)
            kalman_gains.append(k)

        current_raw = price_series[-1]
        latest_filtered = filtered_history[-1]
        latest_k = kalman_gains[-1]
        total_error_std = math.sqrt(max(p_cov + r, 1e-8))

        upper_band = latest_filtered + 2.0 * total_error_std
        lower_band = latest_filtered - 2.0 * total_error_std

        # 计算现价在通道内的百分比位置
        band_width = max(upper_band - lower_band, 1e-6)
        channel_pos = (current_raw - lower_band) / band_width
        channel_pos_clamped = max(0.0, min(1.0, channel_pos))

        # 噪声过滤比率 (原始序列一阶差分方差 vs 滤波后一阶差分方差)
        diff_raw = [price_series[i] - price_series[i - 1] for i in range(1, len(price_series))]
        diff_flt = [filtered_history[i] - filtered_history[i - 1] for i in range(1, len(filtered_history))]
        var_raw = sum(d ** 2 for d in diff_raw) / max(len(diff_raw), 1)
        var_flt = sum(d ** 2 for d in diff_flt) / max(len(diff_flt), 1)
        noise_reduction = 1.0 - (var_flt / max(var_raw, 1e-6))
        noise_reduction_clamped = max(0.0, min(0.99, noise_reduction))

        return KalmanFilterResult(
            filtered_price=round(latest_filtered, 2),
            estimation_error_std=round(total_error_std, 2),
            kalman_upper_band=round(upper_band, 2),
            kalman_lower_band=round(lower_band, 2),
            kalman_gain=round(latest_k, 4),
            raw_close=round(current_raw, 2),
            channel_position_pct=round(channel_pos_clamped, 2),
            noise_reduction_ratio=round(noise_reduction_clamped, 2),
        )

    def evaluate_swing_opportunity(
        self,
        ticker: str,
        as_of_date: str,
        price_series: List[float],
    ) -> MeanReversionVerdict:
        """综合 OU 均值回归特征与卡尔曼自适应通道，给出震荡市高抛低吸指令."""
        ou_res = self.fit_ou_process(price_series)
        kalman_res = self.apply_kalman_filter(price_series)

        current_price = price_series[-1]
        profit_space_pct = 0.0

        # 双模信号对撞融合
        # 1. 超跌做多低吸: OU 给出超卖 + 现价位于卡尔曼通道下轨附近 (channel_pos <= 0.20)
        if ou_res.is_mean_reverting and ou_res.current_zscore <= -self.zscore_entry_threshold and kalman_res.channel_position_pct <= 0.25:
            action = "STRONG_BUY_DIP"
            profit_space_pct = round(((ou_res.equilibrium_mu - current_price) / max(current_price, 1e-6)) * 100.0, 2)
            rationale = (
                f"标的具备显著均值回归特征(半衰期 {ou_res.half_life_days} 天)，现价严重击穿均值中枢(Z-Score {ou_res.current_zscore})，"
                f"并触及卡尔曼自适应下轨支撑位(${kalman_res.kalman_lower_band})，触发强烈左侧低吸信号，预期回归利润空间 {profit_space_pct}%。"
            )

        # 2. 超买高抛减仓: OU 给出超买 + 现价触及卡尔曼通道上轨 (channel_pos >= 0.80)
        elif ou_res.is_mean_reverting and ou_res.current_zscore >= self.zscore_entry_threshold and kalman_res.channel_position_pct >= 0.75:
            action = "STRONG_SELL_PEAK"
            profit_space_pct = round(((current_price - ou_res.equilibrium_mu) / max(current_price, 1e-6)) * 100.0, 2)
            rationale = (
                f"标的触及卡尔曼动态阻力上轨(${kalman_res.kalman_upper_band})且OU正偏离过度(Z-Score {ou_res.current_zscore})，"
                f"进入严重超买风险区，震荡市副武器发出强制高抛止盈防回撤指令。"
            )

        else:
            action = "NEUTRAL"
            rationale = (
                f"标的当前处于均衡通道内部运行(Z-Score {ou_res.current_zscore}，通道分位 {int(kalman_res.channel_position_pct * 100)}%)，"
                f"未触发统计套利极限偏离阈值，保持观望或交由主升浪趋势引擎接管。"
            )

        return MeanReversionVerdict(
            ticker=ticker,
            as_of_date=as_of_date,
            ou_result=ou_res,
            kalman_result=kalman_res,
            swing_action=action,
            expected_profit_pct=max(profit_space_pct, 0.0),
            rationale_zh=rationale,
        )
