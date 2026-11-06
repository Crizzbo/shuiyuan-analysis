"""波动率全息曲面与高阶希腊字母定价引擎 (Volatility Surface & Higher-Order Greeks Engine).

遵循 Google Python 编程风格指南与《SPEC-05 估值矩阵与期权二叉树规格书》:
1. 【连续红利 Black-Scholes-Merton 完备希腊字母闭式解】：
   - 一阶希腊字母：Delta (方向敞口), Vega (波动率敏感度), Theta (时间衰减), Rho (利率敏感度);
   - 二阶与交叉希腊字母：Gamma (凸性), Vanna (波动率变动对 Delta 的扰动),
     Volga/Vomma (Vega 凸性), Charm (时间衰减对 Delta 的漂移), Speed (Gamma 敏感度), Zomma (Gamma 波动率扰动);
2. 【Put-Call Parity 欧式看涨看跌平价套利检验】：
   - 捕捉偏离合成远期的正向转化 (Conversion) 与反向转化 (Reverse Conversion) 无风险套利机会;
3. 【高精度隐式波动率 (IV) 数值反解】：
   - 内嵌无套利内在价值边界校验，采用 Brent 混合区间单调夹逼算法;
4. 【波动率偏斜与微笑形态 (Volatility Skew & Smile)】：
   - 25-Delta 风险反转 (Risk Reversal Skew), 10-Delta 尾部黑天鹅保护溢价, Durrleman 无套利曲率约束与 Roger Lee 渐近界限防御.
"""

# 1. Python 标准库
from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional, Tuple

# 2. 第三方数学与科学计算库
import numpy as np

try:
    from scipy import optimize, stats

    # 验证 C-ABI 基础函数是否可用
    _ = stats.norm.cdf(0.0)
except (ImportError, ValueError):

    class _NormStats:
        @staticmethod
        def cdf(x: float) -> float:
            return 0.5 * (1.0 + math.erf(float(x) / math.sqrt(2.0)))

        @staticmethod
        def pdf(x: float) -> float:
            return math.exp(-0.5 * float(x) * float(x)) / math.sqrt(2.0 * math.pi)

    class _StatsFallback:
        norm = _NormStats

    class _OptimizeFallback:
        @staticmethod
        def brentq(f, a, b, xtol=1e-6, maxiter=100):
            fa = f(a)
            fb = f(b)
            if fa * fb > 0:
                return 0.5 * (a + b)
            for _ in range(maxiter):
                mid = 0.5 * (a + b)
                if abs(b - a) < xtol:
                    return mid
                fmid = f(mid)
                if abs(fmid) < xtol:
                    return mid
                if fa * fmid < 0:
                    b = mid
                    fb = fmid
                else:
                    a = mid
                    fa = fmid
            return 0.5 * (a + b)

    stats = _StatsFallback()
    optimize = _OptimizeFallback()


@dataclass(frozen=True)
class OptionGreeksResult:
    """期权理论定价与全阶希腊字母数据契约.

    Attributes:
        option_type: 期权类型 ('call' 或 'put').
        spot_price: 标的现价 S.
        strike_price: 行权价 K.
        time_to_expiry_years: 剩余到期时间 (年化 T).
        risk_free_rate: 无风险利率 r.
        dividend_yield: 连续红利股息率 q.
        volatility: 年化隐含波动率 sigma.
        theoretical_price: 理论期权公允价格.
        intrinsic_value: 内在价值.
        time_value: 时间价值.
        delta: Delta 一阶方向敏感度.
        vega_1pct: Vega 每 1% 波动率变动绝对损益.
        vega_total: Vega 理论总量 (d V / d sigma).
        theta_daily: Theta 每日时间损耗 (d V / dt / 365).
        theta_annual: Theta 年化时间损耗.
        rho_1pct: Rho 每 100 个基点利率变动绝对损益.
        gamma: Gamma 二阶凸性.
        vanna: Vanna 跨界敏感度 (d Delta / d sigma).
        volga: Volga 波动率凸性 (d Vega / d sigma).
        charm_daily: Charm 每日 Delta 衰减率.
        speed: Speed 三阶敏感度 (d Gamma / dS).
        zomma: Zomma 波动率对 Gamma 的扰动 (d Gamma / d sigma).
        narrative_zh: 买方通俗全息研报卡片 (去工程符号化).
        currency_symbol: 货币符号 ('$', '¥').
    """

    option_type: str
    spot_price: float
    strike_price: float
    time_to_expiry_years: float
    risk_free_rate: float
    dividend_yield: float
    volatility: float
    theoretical_price: float
    intrinsic_value: float
    time_value: float
    delta: float
    vega_1pct: float
    vega_total: float
    theta_daily: float
    theta_annual: float
    rho_1pct: float
    gamma: float
    vanna: float
    volga: float
    charm_daily: float
    speed: float
    zomma: float
    narrative_zh: str = ""
    currency_symbol: str = "$"

    def to_dict(self) -> Dict[str, Any]:
        """序列化为标准输出字典."""
        opt_label = "看涨期权" if self.option_type.lower() == "call" else "看跌期权"
        return {
            "currency_symbol": self.currency_symbol,
            "option_contract": {
                "type": self.option_type,
                "type_zh": opt_label,
                "spot_price": self.spot_price,
                "strike_price": self.strike_price,
                "time_to_expiry_years": self.time_to_expiry_years,
                "risk_free_rate": self.risk_free_rate,
                "dividend_yield": self.dividend_yield,
                "volatility": self.volatility,
            },
            "pricing": {
                "theoretical_price": self.theoretical_price,
                "intrinsic_value": self.intrinsic_value,
                "time_value": self.time_value,
            },
            "first_order_greeks": {
                "delta": self.delta,
                "vega_1pct": self.vega_1pct,
                "vega_total": self.vega_total,
                "theta_daily": self.theta_daily,
                "theta_annual": self.theta_annual,
                "rho_1pct": self.rho_1pct,
            },
            "second_order_greeks": {
                "gamma": self.gamma,
                "vanna": self.vanna,
                "volga": self.volga,
                "charm_daily": self.charm_daily,
                "speed": self.speed,
                "zomma": self.zomma,
            },
            "narrative_zh": self.narrative_zh,
        }


@dataclass(frozen=True)
class PutCallParityCheckResult:
    """看涨看跌平价套利核验数据契约.

    Attributes:
        spot_price: 标的现价.
        strike_price: 行权价.
        time_to_expiry_years: 剩余到期年限.
        actual_call_price: 市场看涨现价.
        actual_put_price: 市场看跌现价.
        synthetic_forward_diff: 合成远期理论价差 (S*exp(-qT) - K*exp(-rT)).
        actual_option_diff: 实际期权市价差 (C - P).
        parity_discrepancy: 平价偏离残差 ((C - P) - ForwardDiff).
        arbitrage_signal: 套利信号代号.
        max_arbitrage_profit: 理论无风险套利利润金额.
        rationale_zh: 平价套利诊断文字.
        arbitrage_signal_zh: 纯自然中文套利信号 (去工程符号化).
        narrative_zh: 买方通俗全息研报卡片.
        currency_symbol: 货币符号 ('$', '¥').
    """

    spot_price: float
    strike_price: float
    time_to_expiry_years: float
    actual_call_price: float
    actual_put_price: float
    synthetic_forward_diff: float
    actual_option_diff: float
    parity_discrepancy: float
    arbitrage_signal: str
    max_arbitrage_profit: float
    rationale_zh: str
    arbitrage_signal_zh: str = ""
    narrative_zh: str = ""
    currency_symbol: str = "$"

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典输出."""
        return {
            "currency_symbol": self.currency_symbol,
            "spot_price": self.spot_price,
            "strike_price": self.strike_price,
            "time_to_expiry_years": self.time_to_expiry_years,
            "actual_call_price": self.actual_call_price,
            "actual_put_price": self.actual_put_price,
            "synthetic_forward_diff": self.synthetic_forward_diff,
            "actual_option_diff": self.actual_option_diff,
            "parity_discrepancy": self.parity_discrepancy,
            "arbitrage_signal": self.arbitrage_signal,
            "arbitrage_signal_zh": self.arbitrage_signal_zh or self.arbitrage_signal,
            "max_arbitrage_profit": self.max_arbitrage_profit,
            "rationale_zh": self.rationale_zh,
            "narrative_zh": self.narrative_zh or self.rationale_zh,
        }


@dataclass(frozen=True)
class VolatilitySkewResult:
    """波动率偏斜与微笑结构分析数据契约.

    Attributes:
        spot_price: 标的现价.
        time_to_expiry_years: 剩余到期年限.
        atm_implied_vol: 50-Delta 平值隐含波动率 (ATM IV).
        put_25d_implied_vol: 25-Delta 虚值看跌 IV.
        call_25d_implied_vol: 25-Delta 虚值看涨 IV.
        skew_25d: 25-Delta 偏斜度 (Put_25D - Call_25D).
        tail_risk_wing_10d: 10-Delta 尾部暴跌防范溢价 (Put_10D - ATM).
        skew_curvature_convexity: 微笑曲线曲率 (二次拟合凸性系数 c).
        market_sentiment_signal: 市场情绪信号代码.
        market_sentiment_zh: 买方波动率情绪文字诊断.
        market_sentiment_signal_zh: 纯自然中文市场情绪信号.
        narrative_zh: 买方通俗全息研报卡片.
    """

    spot_price: float
    time_to_expiry_years: float
    atm_implied_vol: float
    put_25d_implied_vol: float
    call_25d_implied_vol: float
    skew_25d: float
    tail_risk_wing_10d: float
    skew_curvature_convexity: float
    market_sentiment_signal: str
    market_sentiment_zh: str
    market_sentiment_signal_zh: str = ""
    narrative_zh: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典输出."""
        return {
            "spot_price": self.spot_price,
            "time_to_expiry_years": self.time_to_expiry_years,
            "atm_implied_vol": self.atm_implied_vol,
            "put_25d_implied_vol": self.put_25d_implied_vol,
            "call_25d_implied_vol": self.call_25d_implied_vol,
            "skew_25d": self.skew_25d,
            "tail_risk_wing_10d": self.tail_risk_wing_10d,
            "skew_curvature_convexity": self.skew_curvature_convexity,
            "market_sentiment_signal": self.market_sentiment_signal,
            "market_sentiment_signal_zh": (
                self.market_sentiment_signal_zh or self.market_sentiment_signal
            ),
            "market_sentiment_zh": self.market_sentiment_zh,
            "narrative_zh": self.narrative_zh or self.market_sentiment_zh,
        }


class VolatilitySurfaceGreeksEngine:
    """全阶希腊字母、平价套利与波动率偏斜分析引擎 (Google Python Style Guide 架构设计)."""

    @classmethod
    def calculate_option_greeks(
        cls,
        spot: float,
        strike: float,
        time_to_expiry_years: float,
        risk_free_rate: float,
        dividend_yield: float,
        volatility: float,
        option_type: str = "call",
        ticker: Optional[str] = None,
        market: Optional[str] = None,
        currency_symbol: Optional[str] = None,
    ) -> OptionGreeksResult:
        """解析解计算连续红利 Merton (1973) 扩展 Black-Scholes 全阶希腊字母.

        Args:
            spot: 标的现价 S.
            strike: 行权价 K.
            time_to_expiry_years: 到期期限 T (年).
            risk_free_rate: 无风险利率 r.
            dividend_yield: 连续红利股息率 q.
            volatility: 年化波动率 sigma.
            option_type: 'call' 看涨期权或 'put' 看跌期权.
            ticker: 标的代码 (用于自适应币种).
            market: 交易市场 ('US', 'JP', 'CN').
            currency_symbol: 显式货币符号 ('$', '¥').

        Returns:
            OptionGreeksResult 包含理论价格、一阶及二阶交叉希腊字母的全息结果.
        """
        curr_sym = cls._resolve_currency_symbol(ticker, market, currency_symbol)

        s_val = float(spot)
        k_val = float(strike)
        t_val = max(1e-6, float(time_to_expiry_years))
        r_val = float(risk_free_rate)
        q_val = float(dividend_yield)
        sigma_val = max(1e-4, float(volatility))
        is_call = option_type.lower() == "call"

        sqrt_t = math.sqrt(t_val)
        d1 = (math.log(s_val / k_val) + (r_val - q_val + 0.5 * sigma_val**2) * t_val) / (
            sigma_val * sqrt_t
        )
        d2 = d1 - sigma_val * sqrt_t

        nd1 = float(stats.norm.cdf(d1))
        nd2 = float(stats.norm.cdf(d2))
        n_neg_d1 = float(stats.norm.cdf(-d1))
        n_neg_d2 = float(stats.norm.cdf(-d2))
        phi_d1 = float(stats.norm.pdf(d1))

        df_r = math.exp(-r_val * t_val)
        df_q = math.exp(-q_val * t_val)

        if is_call:
            price = max(0.0, s_val * df_q * nd1 - k_val * df_r * nd2)
            intrinsic = max(0.0, s_val - k_val)
        else:
            price = max(0.0, k_val * df_r * n_neg_d2 - s_val * df_q * n_neg_d1)
            intrinsic = max(0.0, k_val - s_val)
        time_val = max(0.0, price - intrinsic)

        # 希腊字母测算
        greeks = cls._compute_greeks_math(
            s_val=s_val,
            k_val=k_val,
            t_val=t_val,
            sqrt_t=sqrt_t,
            r_val=r_val,
            q_val=q_val,
            sigma_val=sigma_val,
            is_call=is_call,
            df_q=df_q,
            df_r=df_r,
            d1=d1,
            d2=d2,
            nd1=nd1,
            nd2=nd2,
            n_neg_d1=n_neg_d1,
            n_neg_d2=n_neg_d2,
            phi_d1=phi_d1,
        )

        opt_type_zh = "看涨期权" if is_call else "看跌期权"
        narrative_zh = (
            f"【{opt_type_zh} 全阶希腊字母与敏感度全息研报】"
            f"标的现价 {curr_sym}{s_val:.2f}，行权价 {curr_sym}{k_val:.2f}，到期期限 {t_val:.2f}年，"
            f"理论公允价为 {curr_sym}{price:.2f} "
            f"(内在价值 {curr_sym}{intrinsic:.2f}，时间价值 {curr_sym}{time_val:.2f})。"
            f"一阶风险敏感度: 方向 Delta {greeks['delta']:+.4f}，"
            f"波动率敏感度 Vega 每 1% 变动 {curr_sym}{greeks['vega_1pct']:+.4f}，"
            f"每日时间价值损耗 Theta {curr_sym}{greeks['theta_daily']:+.4f}，"
            f"利率敏感度 Rho 每 100 个基点变动 {curr_sym}{greeks['rho_1pct']:+.4f}。"
            f"二阶凸性与交叉风险: 加速度 Gamma {greeks['gamma']:.4f}，"
            f"跨界敏感度 Vanna {greeks['vanna']:+.4f}，波动率凸性 Volga {greeks['volga']:+.4f}。"
        )

        return OptionGreeksResult(
            option_type="call" if is_call else "put",
            spot_price=round(s_val, 4),
            strike_price=round(k_val, 4),
            time_to_expiry_years=round(t_val, 4),
            risk_free_rate=round(r_val, 4),
            dividend_yield=round(q_val, 4),
            volatility=round(sigma_val, 4),
            theoretical_price=round(price, 4),
            intrinsic_value=round(intrinsic, 4),
            time_value=round(time_val, 4),
            delta=round(greeks["delta"], 5),
            vega_1pct=round(greeks["vega_1pct"], 5),
            vega_total=round(greeks["vega_total"], 5),
            theta_daily=round(greeks["theta_daily"], 5),
            theta_annual=round(greeks["theta_annual"], 4),
            rho_1pct=round(greeks["rho_1pct"], 5),
            gamma=round(greeks["gamma"], 6),
            vanna=round(greeks["vanna"], 6),
            volga=round(greeks["volga"], 6),
            charm_daily=round(greeks["charm_daily"], 6),
            speed=round(greeks["speed"], 7),
            zomma=round(greeks["zomma"], 6),
            narrative_zh=narrative_zh,
            currency_symbol=curr_sym,
        )

    @classmethod
    def solve_implied_volatility(
        cls,
        market_price: float,
        spot: float,
        strike: float,
        time_to_expiry_years: float,
        risk_free_rate: float,
        dividend_yield: float = 0.0,
        option_type: str = "call",
    ) -> Optional[float]:
        """Brent 混合数值根求解器，从市价反解年化隐含波动率 (IV).

        Args:
            market_price: 期权市场实际成交现价.
            spot: 标的现价 S.
            strike: 行权价 K.
            time_to_expiry_years: 到期剩余年限 T.
            risk_free_rate: 无风险利率 r.
            dividend_yield: 连续红利股息率 q.
            option_type: 'call' 或 'put'.

        Returns:
            Optional[float]: 求解得到的年化隐含波动率 (若击穿无套利通道或无法收敛则返回 None).
        """
        p_mkt = float(market_price)
        s_val = float(spot)
        k_val = float(strike)
        t_val = max(1e-6, float(time_to_expiry_years))
        r_val = float(risk_free_rate)
        q_val = float(dividend_yield)
        is_call = option_type.lower() == "call"

        # 严格无套利下限与上限校验
        df_r = math.exp(-r_val * t_val)
        df_q = math.exp(-q_val * t_val)
        if is_call:
            intrinsic_floor = max(0.0, s_val * df_q - k_val * df_r)
            upper_bound = s_val * df_q
        else:
            intrinsic_floor = max(0.0, k_val * df_r - s_val * df_q)
            upper_bound = k_val * df_r

        if p_mkt < intrinsic_floor - 1e-4 or p_mkt > upper_bound + 1e-4:
            return None

        def objective(sigma_test: float) -> float:
            greeks = cls.calculate_option_greeks(
                spot=s_val,
                strike=k_val,
                time_to_expiry_years=t_val,
                risk_free_rate=r_val,
                dividend_yield=q_val,
                volatility=sigma_test,
                option_type=option_type,
            )
            return greeks.theoretical_price - p_mkt

        low_vol = 1e-4
        high_vol = 5.0
        f_low = objective(low_vol)
        f_high = objective(high_vol)

        if f_low * f_high > 0:
            high_vol = 10.0
            f_high = objective(high_vol)
            if f_low * f_high > 0:
                return None

        try:
            solved_iv = optimize.brentq(objective, low_vol, high_vol, xtol=1e-6, maxiter=100)
            return round(float(solved_iv), 4)
        except Exception:
            return None

    @classmethod
    def check_put_call_parity(
        cls,
        call_price: float,
        put_price: float,
        spot: float,
        strike: float,
        time_to_expiry_years: float,
        risk_free_rate: float,
        dividend_yield: float = 0.0,
        tolerance: float = 0.35,
        currency_symbol: Optional[str] = None,
        ticker: Optional[str] = None,
        market: Optional[str] = None,
    ) -> PutCallParityCheckResult:
        """检验看涨看跌平价关系，扫描转化与反向转化无风险套利机会.

        Args:
            call_price: 看涨期权市价.
            put_price: 看跌期权市价.
            spot: 标的现价.
            strike: 行权价.
            time_to_expiry_years: 剩余年限.
            risk_free_rate: 无风险利率.
            dividend_yield: 连续红利率.
            tolerance: 允许的点差容忍阈值.
            currency_symbol: 货币符号.
            ticker: 标的代码.
            market: 交易市场.

        Returns:
            PutCallParityCheckResult 平价残差与无风险套利诊断契约.
        """
        curr_sym = cls._resolve_currency_symbol(ticker, market, currency_symbol)

        s_val = float(spot)
        k_val = float(strike)
        t_val = max(1e-6, float(time_to_expiry_years))
        r_val = float(risk_free_rate)
        q_val = float(dividend_yield)

        forward_diff = s_val * math.exp(-q_val * t_val) - k_val * math.exp(-r_val * t_val)
        option_diff = call_price - put_price
        discrepancy = option_diff - forward_diff

        signal, signal_zh, profit, desc = cls._classify_parity_arbitrage(
            discrepancy=discrepancy,
            tolerance=tolerance,
            curr_sym=curr_sym,
        )

        narrative_zh = (
            f"【标的看涨看跌平价套利核验全息研报】"
            f"平价套利定性为【{signal_zh}】。"
            f"价格基准: 标的现价 {curr_sym}{s_val:.2f}，行权价 {curr_sym}{k_val:.2f}，"
            f"现行看涨市价 {curr_sym}{call_price:.2f}，看跌市价 {curr_sym}{put_price:.2f}。"
            f"套利空间与残差: 合成远期价差 {curr_sym}{forward_diff:+.2f}，实际期权价差 {curr_sym}{option_diff:+.2f}，"
            f"平价偏离度 {curr_sym}{discrepancy:+.2f}，理论无风险套利利润 {curr_sym}{profit:.2f}。"
            f"套利执行诊断: {desc}"
        )

        return PutCallParityCheckResult(
            spot_price=round(s_val, 2),
            strike_price=round(k_val, 2),
            time_to_expiry_years=round(t_val, 4),
            actual_call_price=round(call_price, 2),
            actual_put_price=round(put_price, 2),
            synthetic_forward_diff=round(forward_diff, 3),
            actual_option_diff=round(option_diff, 3),
            parity_discrepancy=round(discrepancy, 3),
            arbitrage_signal=signal,
            max_arbitrage_profit=round(profit, 2),
            rationale_zh=desc,
            arbitrage_signal_zh=signal_zh,
            narrative_zh=narrative_zh,
            currency_symbol=curr_sym,
        )

    @classmethod
    def analyze_volatility_skew(
        cls,
        strikes: List[float],
        implied_vols: List[float],
        spot: float,
        time_to_expiry_years: float,
        risk_free_rate: float,
        dividend_yield: float = 0.0,
    ) -> VolatilitySkewResult:
        """分析期权链波动率偏斜 (Skew) 与微笑 (Smile) 结构，识别买方防范下行黑天鹅溢价.

        Args:
            strikes: 各合约行权价列表.
            implied_vols: 对应的隐含波动率小数列表 (例如 0.25 代表 25%).
            spot: 标的现价.
            time_to_expiry_years: 到期剩余年限.
            risk_free_rate: 无风险利率.
            dividend_yield: 连续红利股息率.

        Returns:
            VolatilitySkewResult 包含偏斜斜率、凸性、尾部溢价与情绪信号的全息结果.

        Raises:
            ValueError: 当行权价少于 3 档时抛出.
        """
        if len(strikes) != len(implied_vols) or len(strikes) < 3:
            raise ValueError("至少需要提供 3 档以上的行权价与对应 IV 序列以建立偏斜结构")

        sorted_pairs = sorted(zip(strikes, implied_vols), key=lambda x: x[0])
        k_arr = np.array([p[0] for p in sorted_pairs], dtype=float)
        iv_arr = np.array([p[1] for p in sorted_pairs], dtype=float)

        log_k = np.log(k_arr / spot)
        poly_coefs = np.polyfit(log_k, iv_arr, deg=2)
        c_raw = float(poly_coefs[0])
        c_convexity = max(0.0, c_raw)
        poly_coefs[0] = c_convexity

        sigma_atm = max(0.05, float(np.polyval(poly_coefs, 0.0)))
        sqrt_t = math.sqrt(max(1e-4, time_to_expiry_years))
        k_25d_put = -0.67 * sigma_atm * sqrt_t
        k_25d_call = 0.67 * sigma_atm * sqrt_t
        k_10d_put = -1.28 * sigma_atm * sqrt_t

        min_iv = max(0.01, float(np.min(iv_arr)) * 0.5)
        iv_atm = max(min_iv, float(np.polyval(poly_coefs, 0.0)))
        iv_25d_put = max(min_iv, float(np.polyval(poly_coefs, k_25d_put)))
        iv_25d_call = max(min_iv, float(np.polyval(poly_coefs, k_25d_call)))
        iv_10d_put = max(min_iv, float(np.polyval(poly_coefs, k_10d_put)))

        skew_25d = iv_25d_put - iv_25d_call
        wing_tail = iv_10d_put - iv_atm

        signal, signal_zh, desc = cls._classify_skew_sentiment(skew_25d, wing_tail)

        narrative_zh = (
            f"【标的期权链波动率偏斜与情绪全息研报】"
            f"市场衍生品情绪定性为【{signal_zh}】。"
            f"波动率曲面关键节点: 平值隐含波动率 ATM IV 为 {iv_atm*100:.1f}%，"
            f"25-Delta 虚值看跌 IV 为 {iv_25d_put*100:.1f}%，虚值看涨 IV 为 {iv_25d_call*100:.1f}%，"
            f"25-Delta 偏斜度 Skew 为 {skew_25d*100:+.2f}%，10-Delta 极端尾部保护溢价为 {wing_tail*100:+.2f}%，"
            f"微笑曲线曲率凸性为 {c_convexity:.4f}。"
            f"买方对冲情绪研判: {desc}"
        )

        return VolatilitySkewResult(
            spot_price=round(spot, 2),
            time_to_expiry_years=round(time_to_expiry_years, 4),
            atm_implied_vol=round(iv_atm, 4),
            put_25d_implied_vol=round(iv_25d_put, 4),
            call_25d_implied_vol=round(iv_25d_call, 4),
            skew_25d=round(skew_25d, 4),
            tail_risk_wing_10d=round(wing_tail, 4),
            skew_curvature_convexity=round(c_convexity, 4),
            market_sentiment_signal=signal,
            market_sentiment_zh=desc,
            market_sentiment_signal_zh=signal_zh,
            narrative_zh=narrative_zh,
        )

    # --------------------------------------------------------------------------
    # 私有辅助方法 (Private Helpers, Google Style Guide)
    # --------------------------------------------------------------------------

    @staticmethod
    def _resolve_currency_symbol(
        ticker: Optional[str], market: Optional[str], currency_symbol: Optional[str]
    ) -> str:
        """根据证券代码和市场推导货币符号 (私有辅助方法)."""
        t_up = (ticker or "").upper()
        m_up = (market or "").upper()
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
        if currency_symbol and currency_symbol != "$":
            return currency_symbol
        if is_jp or is_cn:
            return "¥"
        return currency_symbol or "$"

    @staticmethod
    def _compute_greeks_math(
        s_val: float,
        k_val: float,
        t_val: float,
        sqrt_t: float,
        r_val: float,
        q_val: float,
        sigma_val: float,
        is_call: bool,
        df_q: float,
        df_r: float,
        d1: float,
        d2: float,
        nd1: float,
        nd2: float,
        n_neg_d1: float,
        n_neg_d2: float,
        phi_d1: float,
    ) -> Dict[str, float]:
        """计算完备一阶与二阶希腊字母数学闭式解 (私有辅助方法)."""
        delta = df_q * nd1 if is_call else -df_q * n_neg_d1
        gamma = (df_q * phi_d1) / (s_val * sigma_val * sqrt_t)
        vega_total = s_val * df_q * phi_d1 * sqrt_t
        vega_1pct = vega_total * 0.01

        term1 = -(s_val * df_q * phi_d1 * sigma_val) / (2.0 * sqrt_t)
        if is_call:
            theta_annual = term1 + q_val * s_val * df_q * nd1 - r_val * k_val * df_r * nd2
        else:
            theta_annual = term1 - q_val * s_val * df_q * n_neg_d1 + r_val * k_val * df_r * n_neg_d2
        theta_daily = theta_annual / 365.0

        if is_call:
            rho_total = k_val * t_val * df_r * nd2
        else:
            rho_total = -k_val * t_val * df_r * n_neg_d2
        rho_1pct = rho_total * 0.01

        vanna = -df_q * phi_d1 * (d2 / sigma_val)
        volga = vega_total * (d1 * d2 / sigma_val)

        bracket = (2.0 * (r_val - q_val) * t_val - d2 * sigma_val * sqrt_t) / (
            2.0 * t_val * sigma_val * sqrt_t
        )
        if is_call:
            charm_annual = q_val * df_q * nd1 - df_q * phi_d1 * bracket
        else:
            charm_annual = -q_val * df_q * n_neg_d1 - df_q * phi_d1 * bracket
        charm_daily = charm_annual / 365.0

        speed = -(gamma / s_val) * (d1 / (sigma_val * sqrt_t) + 1.0)
        zomma = gamma * ((d1 * d2 - 1.0) / sigma_val)

        return {
            "delta": delta,
            "gamma": gamma,
            "vega_total": vega_total,
            "vega_1pct": vega_1pct,
            "theta_annual": theta_annual,
            "theta_daily": theta_daily,
            "rho_total": rho_total,
            "rho_1pct": rho_1pct,
            "vanna": vanna,
            "volga": volga,
            "charm_daily": charm_daily,
            "speed": speed,
            "zomma": zomma,
        }

    @staticmethod
    def _classify_parity_arbitrage(
        discrepancy: float, tolerance: float, curr_sym: str
    ) -> Tuple[str, str, float, str]:
        """判定看涨看跌平价套利类型与利润 (私有辅助方法)."""
        if discrepancy > tolerance:
            signal = "CONVERSION_ARBITRAGE"
            signal_zh = "正向转化套利 (卖Call买Put买入合成现货)"
            profit = discrepancy
            desc = (
                f"【正向转化套利信号】Call 相对溢价 {curr_sym}{discrepancy:+.2f}；"
                "策略：卖出 Call + 买入 Put + 买入标的资产锁死固定收益。"
            )
        elif discrepancy < -tolerance:
            signal = "REVERSE_CONVERSION_ARBITRAGE"
            signal_zh = "反向转化套利 (买Call卖Put融券卖空)"
            profit = -discrepancy
            desc = (
                f"【反向转化套利信号】Put 相对溢价 {curr_sym}{-discrepancy:+.2f}；"
                "策略：买入 Call + 卖出 Put + 融券卖空标的资产套取无风险息差。"
            )
        else:
            signal = "FAIR_PRICING"
            signal_zh = "平价公允定价 (无套利空间)"
            profit = 0.0
            desc = (
                f"【市场平价契合】平价残差仅 {curr_sym}{discrepancy:+.2f}，"
                "在流动性买卖点差允许的无套利通道内。"
            )
        return signal, signal_zh, profit, desc

    @staticmethod
    def _classify_skew_sentiment(
        skew_25d: float, wing_tail: float
    ) -> Tuple[str, str, str]:
        """根据偏斜度与尾部溢价判定市场情绪等级 (私有辅助方法)."""
        if skew_25d > 0.08:
            signal = "SEVERE_CRASH_FEAR"
            signal_zh = "极度恐慌性下行对冲买需"
            desc = (
                f"【极度恐慌性下行对冲买需】25-Delta Skew 高达 +{skew_25d*100:.2f}%，"
                f"10-Delta 尾部黑天鹅保护溢价达 +{wing_tail*100:.2f}%；"
                "机构大单愿意支付极高波动率溢价买入虚值 Put 锁死下行黑天鹅！"
            )
        elif skew_25d > 0.02:
            signal = "NORMAL_EQUITY_SKEW"
            signal_zh = "健康标准权益偏斜"
            desc = (
                f"【健康标准权益偏斜】25-Delta Skew 为 +{skew_25d*100:.2f}%，"
                "呈现成熟股票市场典型的左偏下行保护需求，处于机构健康对冲区间。"
            )
        elif skew_25d < -0.03:
            signal = "CALL_GREED_BUBBLE"
            signal_zh = "虚值买权极度狂热逼空"
            desc = (
                f"【虚值 Call 极度狂热逼空】25-Delta Skew 为负 ({skew_25d*100:.2f}%)，"
                "看涨期权波动率显著高于看跌期权，通常出现于迷因股逼空暴涨或投机买权过热阶段。"
            )
        else:
            signal = "FLAT_SKEW"
            signal_zh = "扁平偏斜结构"
            desc = (
                f"【扁平偏斜结构】25-Delta Skew 仅 {skew_25d*100:+.2f}%，"
                "衍生品市场对方向性剧烈下行的预期极为平淡。"
            )
        return signal, signal_zh, desc
