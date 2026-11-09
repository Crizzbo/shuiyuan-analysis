# -*- coding: utf-8 -*-
"""牛熊状态总阀门引擎 (macro_regime_hmm_valve_engine.py).

遵循《AGENTS.md》与《CLAUDE.md》：
1. 底层纯净金融核心层：零逆向依赖，不依赖外层模块，纯相对导入与标准数学库；
2. 零前视偏差 (Strict Point-in-Time)：仅依赖历史已知大盘日收益率与基准收盘价；
3. HMM 隐马尔可夫三状态识别 (高斯发射概率 + 前向-后向算法 EM 参数估计)：
   - 状态 0: 低波动主升牛市 (BULL_CALM)，仓位上限 100%；
   - 状态 1: 高波动无序震荡市 (RANGE_VOLATILE)，仓位上限 50%；
   - 状态 2: 剧烈流动性危机熊市 (CRISIS_BEAR)，仓位上限 0%~20%；
4. 大盘 200 日长期均线 (Trend Switch) 硬核门禁与斜率过滤器；
5. 全流程数值下溢防护、除零保护与边界有限性防御。
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple


class MarketRegimeState(str, Enum):
    """市场隐状态枚举."""
    BULL_CALM = "BULL_CALM"              # 低波动稳健牛市
    RANGE_VOLATILE = "RANGE_VOLATILE"    # 高波动震荡市
    CRISIS_BEAR = "CRISIS_BEAR"          # 危机/下行熊市


@dataclass
class HMMModelResult:
    """HMM 状态识别输出契约."""
    current_state: MarketRegimeState
    state_probabilities: Dict[str, float]
    state_means: List[float]
    state_volatilities: List[float]
    transition_matrix: List[List[float]]
    confidence_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_state": self.current_state.value,
            "state_probabilities": self.state_probabilities,
            "state_means": self.state_means,
            "state_volatilities": self.state_volatilities,
            "transition_matrix": self.transition_matrix,
            "confidence_score": self.confidence_score,
        }


@dataclass
class TrendFilterResult:
    """大盘长期趋势均线开关契约."""
    current_price: float
    ma50: float
    ma200: float
    is_above_ma200: bool
    is_golden_cross: bool
    ma200_slope_pct: float
    trend_verdict: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MacroValveDecision:
    """牛熊状态总阀门最高决策中枢契约."""
    as_of_date: str
    valve_status: str                     # "OPEN" (全面进攻), "CAUTION" (控仓震荡), "CLOSED" (紧急防御)
    total_position_ceiling_pct: float     # 全局持仓上限 (0.0 ~ 1.0)
    hmm_result: HMMModelResult
    trend_result: TrendFilterResult
    rationale_zh: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "as_of_date": self.as_of_date,
            "valve_status": self.valve_status,
            "total_position_ceiling_pct": self.total_position_ceiling_pct,
            "hmm_result": self.hmm_result.to_dict(),
            "trend_result": self.trend_result.to_dict(),
            "rationale_zh": self.rationale_zh,
        }


class MacroRegimeHMMValveEngine:
    """牛熊状态总阀门引擎 (三状态高斯 HMM + 200 日大盘趋势开关)."""

    def __init__(
        self,
        n_states: int = 3,
        max_em_iter: int = 40,
        convergence_tol: float = 1e-4,
        min_volatility: float = 1e-4,
    ):
        if n_states != 3:
            raise ValueError("当前实战引擎刚性设计为 3 隐状态架构 (牛/震/熊)")
        self.n_states = n_states
        self.max_em_iter = max_em_iter
        self.convergence_tol = convergence_tol
        self.min_volatility = min_volatility

    @staticmethod
    def _gaussian_pdf(x: float, mean: float, std: float) -> float:
        """数值安全的一维高斯概率密度函数."""
        s = max(std, 1e-6)
        denom = math.sqrt(2.0 * math.pi) * s
        exponent = -0.5 * ((x - mean) / s) ** 2
        # 防下溢截断
        if exponent < -700.0:
            return 1e-300
        return max(math.exp(exponent) / denom, 1e-300)

    def fit_and_predict_hmm(self, returns: List[float]) -> HMMModelResult:
        """基于历史日收益率时序拟合高斯 HMM 并推断最新时刻状态后验概率."""
        if not returns or len(returns) < 30:
            raise ValueError(f"HMM 拟合至少需要 30 个日收益率样本，当前提供: {len(returns) if returns else 0}")

        T = len(returns)
        K = self.n_states

        # 1. 经验分位数初始化 3 个状态 (牛: 高均值低波动, 震: 中均值中波动, 熊: 负均值高波动)
        sorted_rets = sorted(returns)
        q1 = sorted_rets[int(T * 0.33)]
        q2 = sorted_rets[int(T * 0.67)]

        bear_sample = [r for r in returns if r <= q1] or returns[:T//3]
        range_sample = [r for r in returns if q1 < r <= q2] or returns[T//3:2*T//3]
        bull_sample = [r for r in returns if r > q2] or returns[2*T//3:]

        def _stats(arr: List[float], fallback_mean: float, fallback_std: float) -> Tuple[float, float]:
            if not arr:
                return fallback_mean, fallback_std
            m = sum(arr) / len(arr)
            var = sum((x - m) ** 2 for x in arr) / max(len(arr) - 1, 1)
            return m, max(math.sqrt(var), self.min_volatility)

        # 初始均值与方差 (State 0: BULL, State 1: RANGE, State 2: CRISIS)
        m0, s0 = _stats(bull_sample, 0.001, 0.008)
        m1, s1 = _stats(range_sample, 0.000, 0.015)
        m2, s2 = _stats(bear_sample, -0.002, 0.025)

        means = [m0, m1, m2]
        stds = [s0, s1, s2]

        # 初始转移概率 (具有高自相关粘性)
        trans = [
            [0.85, 0.12, 0.03],
            [0.10, 0.80, 0.10],
            [0.05, 0.15, 0.80],
        ]
        # 初始状态分布
        pi = [0.4, 0.4, 0.2]

        # 2. EM (Baum-Welch) 迭代收敛
        prev_log_lik = -1e12

        for _ in range(self.max_em_iter):
            # E 步: 前向 (Forward) 概率计算
            alpha = [[0.0] * K for _ in range(T)]
            scale = [0.0] * T

            # t = 0 初始化
            for j in range(K):
                pdf = self._gaussian_pdf(returns[0], means[j], stds[j])
                alpha[0][j] = pi[j] * pdf
            scale[0] = sum(alpha[0]) or 1e-12
            for j in range(K):
                alpha[0][j] /= scale[0]

            # 前向递推
            for t in range(1, T):
                for j in range(K):
                    acc = sum(alpha[t - 1][i] * trans[i][j] for i in range(K))
                    pdf = self._gaussian_pdf(returns[t], means[j], stds[j])
                    alpha[t][j] = acc * pdf
                scale[t] = sum(alpha[t]) or 1e-12
                for j in range(K):
                    alpha[t][j] /= scale[t]

            # 后向 (Backward) 概率计算
            beta = [[0.0] * K for _ in range(T)]
            for j in range(K):
                beta[T - 1][j] = 1.0 / scale[T - 1]

            for t in range(T - 2, -1, -1):
                for i in range(K):
                    acc = 0.0
                    for j in range(K):
                        pdf = self._gaussian_pdf(returns[t + 1], means[j], stds[j])
                        acc += trans[i][j] * pdf * beta[t + 1][j]
                    beta[t][i] = acc / scale[t]

            # 计算 Gamma (后验状态概率) 与 Xi (状态转移概率)
            gamma = [[0.0] * K for _ in range(T)]
            for t in range(T):
                denom = sum(alpha[t][i] * beta[t][i] for i in range(K)) or 1e-12
                for i in range(K):
                    gamma[t][i] = (alpha[t][i] * beta[t][i]) / denom

            log_lik = sum(math.log(max(s, 1e-12)) for s in scale)
            if abs(log_lik - prev_log_lik) < self.convergence_tol:
                break
            prev_log_lik = log_lik

            # M 步: 更新参数
            for i in range(K):
                gamma_sum = sum(gamma[t][i] for t in range(T)) or 1e-12
                # 更新均值
                new_mean = sum(gamma[t][i] * returns[t] for t in range(T)) / gamma_sum
                # 更新方差
                new_var = sum(gamma[t][i] * ((returns[t] - new_mean) ** 2) for t in range(T)) / gamma_sum
                means[i] = new_mean
                stds[i] = max(math.sqrt(max(new_var, 0.0)), self.min_volatility)

            # 更新转移矩阵
            for i in range(K):
                denom_xi = sum(gamma[t][i] for t in range(T - 1)) or 1e-12
                for j in range(K):
                    numer_xi = 0.0
                    for t in range(T - 1):
                        pdf = self._gaussian_pdf(returns[t + 1], means[j], stds[j])
                        numer_xi += alpha[t][i] * trans[i][j] * pdf * beta[t + 1][j]
                    trans[i][j] = max(numer_xi / denom_xi, 1e-6)
                row_sum = sum(trans[i]) or 1.0
                trans[i] = [p / row_sum for p in trans[i]]

        # 3. 按波动率升序标准化映射 (State 0: 最小波动 -> BULL_CALM, State 2: 最大波动 -> CRISIS_BEAR)
        indices_by_vol = sorted(range(K), key=lambda idx: stds[idx])
        mapping = {
            indices_by_vol[0]: MarketRegimeState.BULL_CALM,
            indices_by_vol[1]: MarketRegimeState.RANGE_VOLATILE,
            indices_by_vol[2]: MarketRegimeState.CRISIS_BEAR,
        }

        latest_gamma = gamma[-1]
        probs = {
            MarketRegimeState.BULL_CALM.value: round(float(latest_gamma[indices_by_vol[0]]), 4),
            MarketRegimeState.RANGE_VOLATILE.value: round(float(latest_gamma[indices_by_vol[1]]), 4),
            MarketRegimeState.CRISIS_BEAR.value: round(float(latest_gamma[indices_by_vol[2]]), 4),
        }

        # 归一化后验概率
        prob_sum = sum(probs.values()) or 1.0
        probs = {k: round(v / prob_sum, 4) for k, v in probs.items()}

        current_state_val = max(probs.keys(), key=lambda k: probs[k])
        current_state = MarketRegimeState(current_state_val)

        confidence = probs[current_state.value]

        ordered_means = [round(means[idx], 6) for idx in indices_by_vol]
        ordered_vols = [round(stds[idx] * math.sqrt(252), 4) for idx in indices_by_vol]  # 年化波动率

        return HMMModelResult(
            current_state=current_state,
            state_probabilities=probs,
            state_means=ordered_means,
            state_volatilities=ordered_vols,
            transition_matrix=[[round(v, 4) for v in row] for row in trans],
            confidence_score=confidence,
        )

    @staticmethod
    def compute_trend_filter(close_prices: List[float]) -> TrendFilterResult:
        """计算大盘 200 日与 50 日均线开关及长期斜率."""
        if not close_prices or len(close_prices) < 200:
            raise ValueError(f"大盘趋势开关计算需要至少 200 个交易日收盘价，当前仅提供: {len(close_prices) if close_prices else 0}")

        current_price = close_prices[-1]
        ma50 = sum(close_prices[-50:]) / 50.0
        ma200 = sum(close_prices[-200:]) / 200.0

        # 计算 20 交易日前 MA200 的斜率
        ma200_prev20 = sum(close_prices[-220:-20]) / 200.0 if len(close_prices) >= 220 else ma200
        ma200_slope_pct = ((ma200 - ma200_prev20) / max(ma200_prev20, 1e-6)) * 100.0

        is_above_ma200 = current_price >= ma200
        is_golden_cross = ma50 >= ma200

        if is_above_ma200 and ma200_slope_pct >= 0.0:
            trend_verdict = "STRONG_BULL_TREND"  # 均线多头且斜率向上
        elif is_above_ma200 and ma200_slope_pct < 0.0:
            trend_verdict = "WEAK_BULL_CORRECTION"  # 站上均线但长期均线走平向下
        elif not is_above_ma200 and is_golden_cross:
            trend_verdict = "PULLBACK_BELOW_MA200"  # 跌破 200 均线但中期金叉未散
        else:
            trend_verdict = "CONFIRMED_BEAR_DOWNTREND"  # 破位深跌确认空头

        return TrendFilterResult(
            current_price=round(current_price, 2),
            ma50=round(ma50, 2),
            ma200=round(ma200, 2),
            is_above_ma200=is_above_ma200,
            is_golden_cross=is_golden_cross,
            ma200_slope_pct=round(ma200_slope_pct, 2),
            trend_verdict=trend_verdict,
        )

    def evaluate_valve(
        self,
        as_of_date: str,
        benchmark_close_series: List[float],
    ) -> MacroValveDecision:
        """综合 HMM 隐状态与 200 日大盘开关，输出全交易室全局仓位总阀门决策."""
        if len(benchmark_close_series) < 200:
            raise ValueError("评估总阀门至少需要 200 个交易日的大盘连续收盘价序列")

        # 计算日对数收益率
        returns = [
            math.log(benchmark_close_series[t] / max(benchmark_close_series[t - 1], 1e-6))
            for t in range(1, len(benchmark_close_series))
        ]

        hmm_res = self.fit_and_predict_hmm(returns[-120:])  # 取最近半年活跃窗口拟合状态
        trend_res = self.compute_trend_filter(benchmark_close_series)

        # 综合矩阵决断
        # 1. 均线在下方且 HMM 为牛市 -> 阀门全开 (仓位上限 100%)
        if trend_res.is_above_ma200 and hmm_res.current_state == MarketRegimeState.BULL_CALM:
            valve_status = "OPEN"
            ceiling = 1.00
            rationale = "大盘位于MA200生命线之上且HMM确认为低波动牛市主升浪，总阀门完全放开，全仓积极进攻。"

        # 2. 均线在上方但 HMM 识别为高波动震荡 -> 限制仓位至 60%
        elif trend_res.is_above_ma200 and hmm_res.current_state == MarketRegimeState.RANGE_VOLATILE:
            valve_status = "CAUTION"
            ceiling = 0.60
            rationale = "大盘虽在MA200之上但HMM探测到波动率显著放大、资金分歧剧烈，进入宽幅震荡态势，总仓位上限压低至60%，防范假突破磨损。"

        # 3. 均线跌破 MA200，无论 HMM 状态为何，强制触发降仓防御 (上限 20%~30%)
        elif not trend_res.is_above_ma200 and hmm_res.current_state != MarketRegimeState.CRISIS_BEAR:
            valve_status = "DEFENSE"
            ceiling = 0.30
            rationale = "大盘失守MA200长期生命线，均线硬性开关触发防御熔断，即使短期未现恐慌踩踏，总仓位上限刚性锁死在30%以下。"

        # 4. 破位跌破 MA200 且 HMM 确诊为危机熊市 -> 全面闭阀防守 (上限 0%~10%)
        else:
            valve_status = "CLOSED"
            ceiling = 0.05
            rationale = "大盘严重破位且HMM确认为高波动危机熊市，空头主导极端流动性冲击，总阀门紧急闭锁，强制空仓或保留极低底仓绝对避险。"

        return MacroValveDecision(
            as_of_date=as_of_date,
            valve_status=valve_status,
            total_position_ceiling_pct=ceiling,
            hmm_result=hmm_res,
            trend_result=trend_res,
            rationale_zh=rationale,
        )
