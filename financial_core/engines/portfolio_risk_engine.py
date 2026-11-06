"""组合在险价值与因子归因引擎 (Portfolio Risk, VaR & Factor Attribution Engine).

遵循 Google Python 编程风格指南与《SPEC-06 资产负债表健康度与信用风险规格书》:
1. 参数法与 Cornish-Fisher 修正 VaR / CVaR:
   - 标准参数法: VaR_alpha = - (mu - z_alpha * sigma) * W;
   - Cornish-Fisher 展开式: 依据样本偏度与超额峰度修正正态分位数 z_alpha，精确刻画厚尾与左偏极端损失风险;
   - 预期尾部损失 CVaR (Expected Shortfall): 度量击穿 VaR 后的平均下行亏损.
2. Ledoit-Wolf 收缩协方差矩阵估计:
   - 解决资产样本量不足或高度相关导致的样本协方差矩阵奇异性与过度拟合;
   - 将样本协方差矩阵向常量相关结构或对角目标阵最优收缩.
3. 组合边际与成分风险分解 (Marginal & Component VaR):
   - 边际风险贡献 (MRC_i = (Sigma @ w)_i / sigma_p);
   - 百分比风险贡献 (Percentage Risk Contribution, PRC_i = w_i * MRC_i / sigma_p)，满足 Euler 风险守恒;
   - 分散化比率 (Diversification Ratio) 与有效风险分散资产数量 (Effective N).
4. Fama-French 多因子归因与系统性/特异性风险剥离:
   - R_i - Rf = alpha + beta_MKT * MKT + beta_SMB * SMB + beta_HML * HML + ... + epsilon;
   - 计算纯 Alpha、因子 Beta 暴露度、t 检验统计量以及特异性风险占比.
5. 历史宏观极端情景压力测试 (Macro Stress Testing):
   - 2008 雷曼次贷危机、2020 新冠流动性挤兑、2022 美联储激进加息紧缩、2024 AI/半导体估值回调等.
"""

# 1. Python 标准库
from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple

# 2. 第三方数学与科学计算库
import numpy as np

try:
    from scipy import stats

    _ = stats.kurtosis([1.0, 2.0, 3.0])
    _ = stats.skew([1.0, 2.0, 3.0])
    _ = stats.norm.ppf(0.05)
    _ = stats.t.cdf(2.0, df=10)
except (ImportError, ValueError, AttributeError):

    class _NormFallback:
        """标准正态分布概率密度与分位数函数高精度备用实现."""

        @staticmethod
        def pdf(x: float) -> float:
            return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

        @staticmethod
        def cdf(x: float) -> float:
            return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

        @classmethod
        def ppf(cls, p: float) -> float:
            if p <= 0.0:
                return -float("inf")
            if p >= 1.0:
                return float("inf")
            if p == 0.5:
                return 0.0
            if p < 0.5:
                t = math.sqrt(-2.0 * math.log(p))
                c0, c1, c2 = 2.515517, 0.802853, 0.010328
                d1, d2, d3 = 1.432788, 0.189269, 0.001308
                x = -(
                    t
                    - ((c2 * t + c1) * t + c0)
                    / (((d3 * t + d2) * t + d1) * t + 1.0)
                )
            else:
                t = math.sqrt(-2.0 * math.log(1.0 - p))
                c0, c1, c2 = 2.515517, 0.802853, 0.010328
                d1, d2, d3 = 1.432788, 0.189269, 0.001308
                x = t - ((c2 * t + c1) * t + c0) / (
                    ((d3 * t + d2) * t + d1) * t + 1.0
                )
            for _ in range(3):
                err = cls.cdf(x) - p
                pdf = cls.pdf(x)
                if abs(pdf) > 1e-15:
                    x -= err / pdf
            return float(x)

    class _TFallback:
        """Student-t 分布累积分布函数高精度数值积分备用实现."""

        @staticmethod
        def pdf(u: float, df: float) -> float:
            coef = math.exp(
                math.lgamma((df + 1) / 2) - math.lgamma(df / 2)
            ) / math.sqrt(math.pi * df)
            return coef * ((1.0 + u * u / df) ** (-(df + 1) / 2))

        @classmethod
        def cdf(cls, t_val: float, df: float) -> float:
            if df <= 0:
                return 0.5
            if t_val == 0:
                return 0.5
            abs_t = abs(t_val)
            n = 200
            h = abs_t / n
            s = cls.pdf(0, df) + cls.pdf(abs_t, df)
            for i in range(1, n):
                w = 4 if i % 2 == 1 else 2
                s += w * cls.pdf(i * h, df)
            prob_half = (h / 3.0) * s
            prob = min(0.5 + prob_half, 1.0)
            return prob if t_val > 0 else (1.0 - prob)

    class _StatsKurtosisFallback:
        """项目原生纯净高精度统计分布备用引擎 (无外置 C 扩展依赖)."""

        norm = _NormFallback()
        t = _TFallback()

        @staticmethod
        def skew(arr: Any) -> float:
            a = np.asarray(arr, dtype=float)
            m = np.mean(a)
            s = np.std(a)
            if s <= 1e-12:
                return 0.0
            return float(np.mean(((a - m) / s) ** 3))

        @staticmethod
        def kurtosis(arr: Any, fisher: bool = True) -> float:
            a = np.asarray(arr, dtype=float)
            m = np.mean(a)
            s = np.std(a)
            if s <= 1e-12:
                return 0.0
            k = float(np.mean(((a - m) / s) ** 4))
            return (k - 3.0) if fisher else k

    stats = _StatsKurtosisFallback()


@dataclass(frozen=True)
class VaRResult:
    """组合或单资产在险价值与尾部风险度量结果数据契约.

    Attributes:
        confidence_level: 置信水平 (例如 0.95 或 0.99).
        time_horizon_days: 时间跨度 (天，如 1天、10天).
        portfolio_value: 组合总市值 / 本金.
        parametric_var: 标准正态分布参数法 VaR (金额).
        parametric_var_pct: 参数法 VaR 百分比.
        cornish_fisher_var: Cornish-Fisher 偏度峰度修正 VaR (金额).
        cornish_fisher_var_pct: 修正 VaR 百分比.
        historical_var: 历史模拟法 VaR (金额).
        historical_var_pct: 历史模拟法 VaR 百分比.
        expected_shortfall_cvar: 条件在险价值 CVaR / Expected Shortfall (金额).
        expected_shortfall_pct: CVaR 百分比.
        sample_skewness: 收益率样本偏度.
        sample_kurtosis: 收益率样本超额峰度 (Normal=0).
        risk_assessment_zh: 买方风险定性评级.
        narrative_zh: 买方通俗全息研报卡片 (去工程符号化).
        currency_symbol: 货币符号 ('$', '¥').
    """

    confidence_level: float
    time_horizon_days: int
    portfolio_value: float
    parametric_var: float
    parametric_var_pct: float
    cornish_fisher_var: float
    cornish_fisher_var_pct: float
    historical_var: Optional[float]
    historical_var_pct: Optional[float]
    expected_shortfall_cvar: float
    expected_shortfall_pct: float
    sample_skewness: float
    sample_kurtosis: float
    risk_assessment_zh: str
    narrative_zh: str = ""
    currency_symbol: str = "$"

    def to_dict(self) -> Dict[str, Any]:
        """序列化为买方可视化卡片字典."""
        return {
            "confidence_level": f"{self.confidence_level*100:.0f}%",
            "time_horizon_days": self.time_horizon_days,
            "portfolio_value": self.portfolio_value,
            "parametric_var": {
                "amount": self.parametric_var,
                "pct": f"{self.parametric_var_pct*100:.2f}%",
            },
            "cornish_fisher_var": {
                "amount": self.cornish_fisher_var,
                "pct": f"{self.cornish_fisher_var_pct*100:.2f}%",
            },
            "historical_var": {
                "amount": self.historical_var,
                "pct": (
                    f"{self.historical_var_pct*100:.2f}%"
                    if self.historical_var_pct is not None
                    else None
                ),
            },
            "expected_shortfall_cvar": {
                "amount": self.expected_shortfall_cvar,
                "pct": f"{self.expected_shortfall_pct*100:.2f}%",
            },
            "sample_skewness": self.sample_skewness,
            "sample_kurtosis": self.sample_kurtosis,
            "risk_assessment": self.risk_assessment_zh,
            "narrative_zh": self.narrative_zh or self.risk_assessment_zh,
            "currency_symbol": self.currency_symbol,
        }


@dataclass(frozen=True)
class RiskDecompositionResult:
    """组合风险分解与风险平价评估结果数据契约.

    Attributes:
        portfolio_volatility_annual: 组合年化总波动率.
        diversification_ratio: 分散化比率 (加权单资产波动率 / 组合波动率).
        effective_n_assets: 权重有效资产数 (1 / sum(w^2)).
        effective_n_risk: 风险平价有效资产数 (1 / sum(prc^2)).
        asset_names: 标的代码列表.
        weights: 资产权重向量.
        volatilities_annual: 单资产年化波动率.
        marginal_risk_contributions: 边际风险贡献 (MRC).
        percentage_risk_contributions: 风险贡献百分比 (PRC, sum=100%).
        is_risk_parity_balanced: 是否接近风险平价 (PRC 离散度 < 10%).
        narrative_zh: 买方通俗全息研报卡片 (去工程符号化).
    """

    portfolio_volatility_annual: float
    diversification_ratio: float
    effective_n_assets: float
    effective_n_risk: float
    asset_names: List[str]
    weights: List[float]
    volatilities_annual: List[float]
    marginal_risk_contributions: List[float]
    percentage_risk_contributions: List[float]
    is_risk_parity_balanced: bool
    narrative_zh: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """序列化为买方可视化卡片字典."""
        return {
            "portfolio_volatility_annual_pct": (
                f"{self.portfolio_volatility_annual*100:.2f}%"
            ),
            "diversification_ratio": self.diversification_ratio,
            "effective_n_assets": self.effective_n_assets,
            "effective_n_risk": self.effective_n_risk,
            "asset_breakdown": [
                {
                    "asset": self.asset_names[i],
                    "weight_pct": f"{self.weights[i]*100:.2f}%",
                    "volatility_annual_pct": f"{self.volatilities_annual[i]*100:.2f}%",
                    "mrc": self.marginal_risk_contributions[i],
                    "prc_pct": f"{self.percentage_risk_contributions[i]:.2f}%",
                }
                for i in range(len(self.asset_names))
            ],
            "is_risk_parity_balanced": self.is_risk_parity_balanced,
            "narrative_zh": self.narrative_zh,
        }


@dataclass(frozen=True)
class FactorAttributionResult:
    """多因子回归与风险收益归因结果数据契约.

    Attributes:
        alpha_annualized: 年化阿尔法超额收益 (对冲因子暴露后的纯 Alpha).
        alpha_t_stat: Alpha t 统计量.
        alpha_p_value: Alpha 显著性 p 值.
        factor_names: 因子名称列表 (MKT, SMB, HML, RMW, CMA 等).
        factor_betas: 各因子 Beta 暴露度字典.
        factor_t_stats: 因子 Beta 显著性 t 值字典.
        r_squared: 因子解释方差比 R^2.
        systematic_risk_pct: 系统性因子风险占比 (R^2 * 100).
        idiosyncratic_risk_pct: 个股特异性/残差风险占比 ((1 - R^2) * 100).
        attribution_summary_zh: 归因文字解读.
        narrative_zh: 买方通俗全息研报卡片 (去工程符号化).
    """

    alpha_annualized: float
    alpha_t_stat: float
    alpha_p_value: float
    factor_names: List[str]
    factor_betas: Dict[str, float]
    factor_t_stats: Dict[str, float]
    r_squared: float
    systematic_risk_pct: float
    idiosyncratic_risk_pct: float
    attribution_summary_zh: str
    narrative_zh: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """序列化为买方可视化卡片字典."""
        return {
            "alpha_annualized_pct": f"{self.alpha_annualized*100:+.2f}%",
            "alpha_t_stat": self.alpha_t_stat,
            "alpha_p_value": self.alpha_p_value,
            "factor_betas": self.factor_betas,
            "factor_t_stats": self.factor_t_stats,
            "r_squared": self.r_squared,
            "systematic_risk_pct": f"{self.systematic_risk_pct:.2f}%",
            "idiosyncratic_risk_pct": f"{self.idiosyncratic_risk_pct:.2f}%",
            "attribution_summary": self.attribution_summary_zh,
            "narrative_zh": self.narrative_zh or self.attribution_summary_zh,
        }


@dataclass(frozen=True)
class StressTestScenarioResult:
    """宏观历史极端压力测试情景输出数据契约.

    Attributes:
        scenario_name: 情景名称代号 (如 2008_Lehman, 2020_Covid).
        scenario_description_zh: 情景宏观历史背景说明.
        market_drawdown_pct: 宏观大盘假定跌幅 %.
        estimated_portfolio_drawdown_pct: 组合预估总跌幅 %.
        estimated_dollar_loss: 预估净损失金额.
        largest_contributor_loss: 承压最大亏损标的及金额说明.
        capital_preservation_score: 资本保全评分 (0-100).
        survival_verdict_zh: 承压生存判定.
        narrative_zh: 买方通俗全息研报卡片 (去工程符号化).
        scenario_name_zh: 情景自然中文名称 (去工程符号化).
        currency_symbol: 货币符号 ('$', '¥').
    """

    scenario_name: str
    scenario_description_zh: str
    market_drawdown_pct: float
    estimated_portfolio_drawdown_pct: float
    estimated_dollar_loss: float
    largest_contributor_loss: str
    capital_preservation_score: float
    survival_verdict_zh: str
    narrative_zh: str = ""
    scenario_name_zh: str = ""
    currency_symbol: str = "$"

    def to_dict(self) -> Dict[str, Any]:
        """序列化为买方可视化卡片字典."""
        return {
            "scenario_name": self.scenario_name,
            "scenario_name_zh": self.scenario_name_zh or self.scenario_name,
            "scenario_description": self.scenario_description_zh,
            "market_drawdown_pct": f"{self.market_drawdown_pct:+.2f}%",
            "estimated_portfolio_drawdown_pct": (
                f"{self.estimated_portfolio_drawdown_pct:+.2f}%"
            ),
            "estimated_dollar_loss": self.estimated_dollar_loss,
            "largest_contributor_loss": self.largest_contributor_loss,
            "capital_preservation_score": self.capital_preservation_score,
            "survival_verdict": self.survival_verdict_zh,
            "narrative_zh": self.narrative_zh or self.survival_verdict_zh,
            "currency_symbol": self.currency_symbol,
        }


class PortfolioRiskAndVaREngine:
    """机构级组合在险价值、收缩协方差、风险平价与压力测试中枢 (Google Python Style Guide 架构设计)."""

    DEFAULT_MACRO_STRESS_SCENARIOS = [
        {
            "name": "2008_GFC_Lehman_Crisis",
            "name_zh": "2008年次贷危机与雷曼破产挤兑",
            "desc": (
                "2008 年全球次贷危机与雷曼破产挤兑：高流动性与杠杆资产无差别抛售"
            ),
            "market_shock": -0.42,
            "vol_surge_mult": 2.8,
            "defensive_beta_damp": 0.65,
        },
        {
            "name": "2020_Covid_Liquidity_Drain",
            "name_zh": "2020年新冠流动性骤紧与踩踏",
            "desc": (
                "2020 年新冠疫情全球大封锁与美元流动性骤缩：短时间内暴跌并在极值反弹"
            ),
            "market_shock": -0.34,
            "vol_surge_mult": 3.2,
            "defensive_beta_damp": 0.70,
        },
        {
            "name": "2022_Fed_Aggressive_Tightening",
            "name_zh": "2022年美联储激进加息杀估值",
            "desc": (
                "2022 年美联储激进加息 450bps 抑制高通胀：杀高估值长久期科技资产，价值股相对坚挺"
            ),
            "market_shock": -0.22,
            "tech_growth_shock": -0.36,
            "value_defensive_shock": -0.06,
        },
        {
            "name": "2024_Semiconductor_AI_Correction",
            "name_zh": "2024年算力半导体估值过热回调",
            "desc": (
                "AI 算力与半导体估值过热震荡整固：资金大幅向低估值红利与防御公用事业再平衡"
            ),
            "market_shock": -0.15,
            "tech_growth_shock": -0.25,
            "value_defensive_shock": 0.04,
        },
    ]

    @classmethod
    def compute_var_cvar(
        cls,
        returns: np.ndarray,
        portfolio_value: float,
        confidence_level: float = 0.95,
        time_horizon_days: int = 1,
        currency_symbol: Optional[str] = None,
    ) -> VaRResult:
        """计算 Parametric VaR, Cornish-Fisher 修正 VaR, 历史模拟 VaR 与预期尾部损失 CVaR.

        Args:
            returns: 历史单期收益率数组 (1D 向量).
            portfolio_value: 资产总组合当前本金市值.
            confidence_level: 置信区间 (通常 0.95 或 0.99).
            time_horizon_days: 风险展望期天数 (1天或按 sqrt(T) 展开).
            currency_symbol: 货币符号 ("$", "¥", 默认 "$").

        Returns:
            VaRResult 包含参数法、CF修正法、CVaR及买方风控研判的结果契约.

        Raises:
            ValueError: 当本金市值 <= 0 或样本数量少于 10 时抛出.
        """
        curr_sym = currency_symbol or "$"
        if portfolio_value <= 0:
            raise ValueError("组合总市值 portfolio_value 必须为正数")
        arr = np.asarray(returns, dtype=float).ravel()
        if len(arr) < 10:
            raise ValueError(
                f"收益率样本数量过少 ({len(arr)} < 10)，无法完成可信的在险价值计量"
            )

        mu = float(np.mean(arr))
        sigma = float(np.std(arr, ddof=1))
        if sigma <= 1e-8:
            sigma = 1e-8

        skew = float(stats.skew(arr))
        kurt = float(stats.kurtosis(arr))

        sqrt_t = math.sqrt(time_horizon_days)
        mu_t = mu * time_horizon_days
        sigma_t = sigma * sqrt_t

        alpha_p = 1.0 - confidence_level
        z_norm = float(stats.norm.ppf(alpha_p))

        # 1. Cornish-Fisher 分位数修正与单调性防御
        z_cf = cls._compute_cornish_fisher_z(z_norm, skew, kurt)

        # 2. 参数法与 CF 法在险价值
        param_var_pct = min(1.0, max(0.0, -(mu_t + z_norm * sigma_t)))
        param_var_dollars = param_var_pct * portfolio_value

        cf_var_pct = min(1.0, max(0.0, -(mu_t + z_cf * sigma_t)))
        cf_var_dollars = cf_var_pct * portfolio_value

        # 3. 历史模拟法 VaR
        hist_cutoff = float(np.percentile(arr, alpha_p * 100))
        hist_var_pct = min(1.0, max(0.0, -hist_cutoff * sqrt_t))
        hist_var_dollars = hist_var_pct * portfolio_value

        # 4. 预期尾部损失 CVaR
        tail_losses = arr[arr <= hist_cutoff]
        if len(tail_losses) > 0:
            hist_cvar_pct = min(
                1.0, max(hist_var_pct, -float(np.mean(tail_losses)) * sqrt_t)
            )
        else:
            phi_z = stats.norm.pdf(z_norm)
            hist_cvar_pct = min(
                1.0, max(param_var_pct, -(mu_t - sigma_t * (phi_z / alpha_p)))
            )
        cvar_dollars = hist_cvar_pct * portfolio_value

        # 5. 买方风险评级研判
        risk_desc = cls._classify_var_risk(
            cf_var_pct=cf_var_pct,
            param_var_pct=param_var_pct,
            skew=skew,
            kurt=kurt,
            confidence_level=confidence_level,
            cf_var_dollars=cf_var_dollars,
            curr_sym=curr_sym,
        )

        # 6. 生成买方通俗自然语言研报卡片
        horizon_desc = "单日" if time_horizon_days == 1 else f"{time_horizon_days}天期"
        narrative_zh = (
            f"【组合极端尾部风险与在险价值 (VaR) 全息研判】"
            f"置信度 {int(confidence_level*100)}% 下，{horizon_desc}极端预期在险损失上限为 "
            f"{cf_var_pct*100:.2f}% ({curr_sym}{cf_var_dollars:,.2f})；"
            f"若击穿在险阈值，极端尾部预期亏损 (CVaR) 均值达 {hist_cvar_pct*100:.2f}% "
            f"({curr_sym}{cvar_dollars:,.2f})。"
            f"收益分布形态特征: 样本偏度 {skew:+.2f}，超额峰度 {kurt:+.2f}。"
            f"买方风控定性: {risk_desc}"
        )

        return VaRResult(
            confidence_level=confidence_level,
            time_horizon_days=time_horizon_days,
            portfolio_value=portfolio_value,
            parametric_var=round(param_var_dollars, 2),
            parametric_var_pct=round(param_var_pct, 4),
            cornish_fisher_var=round(cf_var_dollars, 2),
            cornish_fisher_var_pct=round(cf_var_pct, 4),
            historical_var=round(hist_var_dollars, 2),
            historical_var_pct=round(hist_var_pct, 4),
            expected_shortfall_cvar=round(cvar_dollars, 2),
            expected_shortfall_pct=round(hist_cvar_pct, 4),
            sample_skewness=round(skew, 3),
            sample_kurtosis=round(kurt, 3),
            risk_assessment_zh=risk_desc,
            narrative_zh=narrative_zh,
            currency_symbol=curr_sym,
        )

    @classmethod
    def compute_ledoit_wolf_covariance(
        cls,
        returns_matrix: np.ndarray,
        annualization_factor: float = 252.0,
    ) -> Tuple[np.ndarray, float]:
        """计算 Ledoit-Wolf 最优收缩协方差矩阵与收缩强度 delta.

        Args:
            returns_matrix: 形状为 (T, N) 的收益率矩阵，T 为时间序列长度，N 为资产数量.
            annualization_factor: 年化因子 (日频默认为 252).

        Returns:
            Tuple[np.ndarray, float]: (shrunk_cov_annualized, shrinkage_intensity).

        Raises:
            ValueError: 当收益率矩阵不是二维或样本维度不足时抛出.
        """
        x_mat = np.asarray(returns_matrix, dtype=float)
        if x_mat.ndim != 2:
            raise ValueError("收益率矩阵必须为二维矩阵 (T, N)")
        t_len, n_assets = x_mat.shape
        if t_len < 5 or n_assets < 1:
            raise ValueError(f"样本维度不足 (T={t_len}, N={n_assets})")

        try:
            from sklearn.covariance import LedoitWolf

            lw = LedoitWolf(assume_centered=False)
            lw.fit(x_mat)
            cov_daily = lw.covariance_
            shrinkage = float(lw.shrinkage_)
        except Exception:
            x_mean = np.mean(x_mat, axis=0)
            x_c = x_mat - x_mean
            sample_cov = (x_c.T @ x_c) / (t_len - 1)
            var_diag = np.diag(sample_cov)
            std_diag = np.sqrt(np.maximum(1e-8, var_diag))
            corr = sample_cov / np.outer(std_diag, std_diag)
            r_bar = (
                float((np.sum(corr) - n_assets) / (n_assets * (n_assets - 1)))
                if n_assets > 1
                else 0.0
            )
            target_f = r_bar * np.outer(std_diag, std_diag)
            np.fill_diagonal(target_f, var_diag)

            shrinkage = min(1.0, max(0.0, float(n_assets / t_len * 0.5)))
            cov_daily = shrinkage * target_f + (1.0 - shrinkage) * sample_cov

        cov_annual = cov_daily * annualization_factor
        return cov_annual, round(shrinkage, 4)

    @classmethod
    def decompose_portfolio_risk(
        cls,
        weights: np.ndarray,
        cov_matrix: np.ndarray,
        asset_names: Optional[List[str]] = None,
    ) -> RiskDecompositionResult:
        """执行 Euler 风险守恒分解，计算各资产边际风险贡献 (MRC) 与百分比风险贡献 (PRC).

        Args:
            weights: 资产配置权重向量.
            cov_matrix: 资产协方差矩阵 (N, N).
            asset_names: 标的代码列表 (可选).

        Returns:
            RiskDecompositionResult 包含组合波动率、分散化比率、有效资产数与 PRC 的契约.

        Raises:
            ValueError: 当协方差矩阵维度与权重维度不一致时抛出.
        """
        w = np.asarray(weights, dtype=float).ravel()
        n_assets = len(w)
        if cov_matrix.shape != (n_assets, n_assets):
            raise ValueError(
                f"协方差矩阵维度 ({cov_matrix.shape}) 与权重向量维度 ({n_assets}) 不一致"
            )

        total_w = np.sum(np.abs(w))
        if total_w > 1e-8:
            w_norm = w / np.sum(w)
        else:
            w_norm = np.ones(n_assets) / n_assets

        if asset_names is None or len(asset_names) != n_assets:
            asset_names = [f"Asset_{i+1}" for i in range(n_assets)]

        port_var = float(w_norm.T @ cov_matrix @ w_norm)
        port_vol = math.sqrt(max(1e-8, port_var))

        asset_vols = [
            math.sqrt(max(1e-8, cov_matrix[i, i])) for i in range(n_assets)
        ]

        cov_w = cov_matrix @ w_norm
        mrc = (cov_w / port_vol).tolist()

        prc_raw = [(w_norm[i] * mrc[i]) / port_vol for i in range(n_assets)]
        sum_prc = sum(prc_raw)
        prc_pct = [
            (p / sum_prc * 100.0) if abs(sum_prc) > 1e-8 else (100.0 / n_assets)
            for p in prc_raw
        ]

        weighted_individual_vol = float(np.sum(w_norm * np.array(asset_vols)))
        diversification_ratio = (
            weighted_individual_vol / port_vol if port_vol > 1e-8 else 1.0
        )

        eff_n_weights = (
            1.0 / float(np.sum(w_norm**2))
            if np.sum(w_norm**2) > 1e-8
            else float(n_assets)
        )
        eff_n_risk = (
            1.0 / float(np.sum((np.array(prc_pct) / 100.0) ** 2))
            if np.sum((np.array(prc_pct) / 100.0) ** 2) > 1e-8
            else float(n_assets)
        )

        is_parity = (max(prc_pct) - min(prc_pct)) < (100.0 / n_assets * 0.5)

        top_risk_idx = int(np.argmax(prc_pct))
        top_risk_asset = asset_names[top_risk_idx]
        top_risk_val = prc_pct[top_risk_idx]
        parity_status_zh = (
            "各资产风险贡献基本均衡，符合风险平价配置原则"
            if is_parity
            else f"风险分布显著集中于【{top_risk_asset}】(单一标的承担了 {top_risk_val:.1f}% 的总风险贡献)"
        )
        narrative_zh = (
            f"【组合风险分解与配置结构全息研判】"
            f"组合年化预期波动率为 {port_vol*100:.2f}%，分散化比率达 {diversification_ratio:.2f} "
            f"(有效分散风险标的数 {eff_n_risk:.1f})。风险均衡状态: {parity_status_zh}。"
        )

        return RiskDecompositionResult(
            portfolio_volatility_annual=round(port_vol, 4),
            diversification_ratio=round(diversification_ratio, 3),
            effective_n_assets=round(eff_n_weights, 2),
            effective_n_risk=round(eff_n_risk, 2),
            asset_names=asset_names,
            weights=[round(float(x), 4) for x in w_norm],
            volatilities_annual=[round(float(v), 4) for v in asset_vols],
            marginal_risk_contributions=[round(float(m), 5) for m in mrc],
            percentage_risk_contributions=[round(float(p), 2) for p in prc_pct],
            is_risk_parity_balanced=is_parity,
            narrative_zh=narrative_zh,
        )

    @classmethod
    def run_fama_french_factor_attribution(
        cls,
        asset_returns: np.ndarray,
        factor_returns_matrix: np.ndarray,
        factor_names: Optional[List[str]] = None,
        risk_free_rate_periodic: float = 0.0,
    ) -> FactorAttributionResult:
        """多元 OLS 回归实现 Fama-French 多因子分解与 Alpha/Beta 风险收益剥离.

        Args:
            asset_returns: 标的收益率时间序列 (T 维向量).
            factor_returns_matrix: 多因子收益率矩阵 (T, K).
            factor_names: 因子中文或英文名称列表 (K 维).
            risk_free_rate_periodic: 单期无风险基准利率.

        Returns:
            FactorAttributionResult 包含年化 Alpha、Beta 暴露度、R^2 及显著性检验的结果契约.

        Raises:
            ValueError: 当输入数据时间维度不一致或回归奇异时抛出.
        """
        y = np.asarray(asset_returns, dtype=float).ravel() - risk_free_rate_periodic
        x_mat = np.asarray(factor_returns_matrix, dtype=float)
        t_len = len(y)
        if x_mat.ndim == 1:
            x_mat = x_mat.reshape(-1, 1)
        if x_mat.shape[0] != t_len:
            raise ValueError(
                f"资产收益序列长度 ({t_len}) 与因子矩阵时间跨度 ({x_mat.shape[0]}) 不一致"
            )

        k_factors = x_mat.shape[1]
        if factor_names is None or len(factor_names) != k_factors:
            factor_names = [f"Factor_{j+1}" for j in range(k_factors)]

        x_design = np.column_stack([np.ones(t_len), x_mat])

        try:
            beta_hat, _, _, _ = np.linalg.lstsq(x_design, y, rcond=None)
        except Exception as err:
            raise ValueError(f"因子矩阵回归求解奇异: {str(err)}")

        alpha_periodic = float(beta_hat[0])
        factor_betas_raw = beta_hat[1:]
        alpha_annual = alpha_periodic * 252.0

        y_pred = x_design @ beta_hat
        resids = y - y_pred
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        ss_res = float(np.sum(resids**2))
        r2 = max(0.0, min(1.0, 1.0 - (ss_res / ss_tot))) if ss_tot > 1e-8 else 0.0

        dof = max(1, t_len - (k_factors + 1))
        sigma_sq = ss_res / dof
        try:
            cov_params = sigma_sq * np.linalg.inv(x_design.T @ x_design)
            se_params = np.sqrt(np.maximum(1e-12, np.diag(cov_params)))
        except Exception:
            se_params = np.ones(k_factors + 1) * 1e-4

        alpha_se = float(se_params[0])
        alpha_t = alpha_periodic / alpha_se if alpha_se > 1e-8 else 0.0
        alpha_p = 2.0 * (1.0 - stats.t.cdf(abs(alpha_t), df=dof))

        factor_beta_dict: Dict[str, float] = {}
        factor_t_dict: Dict[str, float] = {}
        for j in range(k_factors):
            b_val = float(factor_betas_raw[j])
            b_se = float(se_params[j + 1])
            b_t = b_val / b_se if b_se > 1e-8 else 0.0
            factor_beta_dict[factor_names[j]] = round(b_val, 4)
            factor_t_dict[factor_names[j]] = round(b_t, 3)

        sys_pct = round(r2 * 100.0, 2)
        idio_pct = round((1.0 - r2) * 100.0, 2)

        if alpha_p < 0.05 and alpha_annual > 0:
            summary = (
                f"【显著正向超额纯 Alpha】年化 Alpha 为 +{alpha_annual*100:.2f}% "
                f"(t={alpha_t:.2f}, p={alpha_p:.3f})，收益能力无法被标准因子完全解释，"
                f"具备核心投研 Alpha；特异性风险占比 {idio_pct}%。"
            )
        elif alpha_annual < 0 and alpha_p < 0.05:
            summary = (
                f"【负向超额拖累】年化 Alpha 为 {alpha_annual*100:.2f}% (显著落后)，"
                f"收益多为被动因子贝塔甚至产生负向执行摩擦；系统性因子解释比率高达 {sys_pct}%。"
            )
        else:
            summary = (
                f"【标准因子暴露型】Alpha 统计上不显著 ({alpha_annual*100:+.2f}%, p={alpha_p:.3f})，"
                f"{sys_pct}% 收益由已知因子风险溢价解释 (特异风险 {idio_pct}%)。"
            )

        narrative_zh = (
            f"【多因子收益归因与 Alpha 解构全息研报】"
            f"年化纯 Alpha 收益为 {alpha_annual*100:+.2f}% (统计显著性 p={alpha_p:.3f})；"
            f"系统性公共因子解释了收益波动的 {sys_pct:.1f}%，个股核心特异性风险占比 {idio_pct:.1f}%。"
            f"投研归因结论: {summary}"
        )

        return FactorAttributionResult(
            alpha_annualized=round(alpha_annual, 4),
            alpha_t_stat=round(alpha_t, 3),
            alpha_p_value=round(alpha_p, 4),
            factor_names=factor_names,
            factor_betas=factor_beta_dict,
            factor_t_stats=factor_t_dict,
            r_squared=round(r2, 4),
            systematic_risk_pct=sys_pct,
            idiosyncratic_risk_pct=idio_pct,
            attribution_summary_zh=summary,
            narrative_zh=narrative_zh,
        )

    @classmethod
    def run_macro_stress_test(
        cls,
        portfolio_positions: Dict[str, float],
        asset_betas: Dict[str, float],
        custom_scenarios: Optional[List[Dict[str, Any]]] = None,
        currency_symbol: Optional[str] = None,
    ) -> List[StressTestScenarioResult]:
        """运行历史极端宏观危机场景压力测试，测算组合最大回撤与资金承压损失.

        Args:
            portfolio_positions: 各资产当前持仓金额字典 {'NVDA': 100000.0, 'MSFT': 80000.0}.
            asset_betas: 各资产相对基准市场的 Beta 弹性字典 {'NVDA': 1.65, 'MSFT': 1.15}.
            custom_scenarios: 可选的定制宏观危机情景列表.
            currency_symbol: 货币符号 ("$", "¥", 未显式指定时按持仓标的代码自适应推导).

        Returns:
            List[StressTestScenarioResult] 宏观危机情景承压评估结果列表.

        Raises:
            ValueError: 当组合持仓总市值 <= 0 时抛出.
        """
        total_portfolio_val = sum(portfolio_positions.values())
        if total_portfolio_val <= 0:
            raise ValueError("组合持仓总市值必须为正数")

        curr_sym = cls._resolve_currency_symbol(
            portfolio_positions, currency_symbol
        )
        scenarios = (
            custom_scenarios
            if custom_scenarios
            else cls.DEFAULT_MACRO_STRESS_SCENARIOS
        )
        results: List[StressTestScenarioResult] = []

        for sc in scenarios:
            name = sc["name"]
            desc = sc["desc"]
            mkt_shock = sc["market_shock"]

            asset_drawdowns: Dict[str, float] = {}
            asset_dollar_losses: Dict[str, float] = {}

            for ticker, pos_val in portfolio_positions.items():
                beta = asset_betas.get(ticker, 1.0)
                clamped_shock, dollar_loss = cls._calculate_asset_stress_shock(
                    ticker=ticker,
                    pos_val=pos_val,
                    beta=beta,
                    mkt_shock=mkt_shock,
                    sc=sc,
                )
                asset_drawdowns[ticker] = clamped_shock
                asset_dollar_losses[ticker] = dollar_loss

            total_loss = sum(asset_dollar_losses.values())
            port_drawdown_pct = -(total_loss / total_portfolio_val)

            contributor_str = cls._format_largest_contributor(
                asset_dollar_losses=asset_dollar_losses,
                total_loss=total_loss,
                curr_sym=curr_sym,
            )

            score, verdict = cls._evaluate_capital_preservation(
                port_drawdown_pct=port_drawdown_pct,
                total_loss=total_loss,
                curr_sym=curr_sym,
            )

            name_zh = sc.get("name_zh") or name
            narrative_zh = (
                f"【宏观历史极端压力测试研报: {name_zh}】"
                f"宏观情景背景: {desc}；大盘基准冲击假定: {mkt_shock*100:+.1f}%。"
                f"预估组合承压回撤: {port_drawdown_pct*100:+.2f}% (预估净损失金额 {curr_sym}{total_loss:,.2f})；"
                f"承压最大受损标的: {contributor_str}；资本保全综合评分: {score:.1f}/100。"
                f"买方生存判定: {verdict}"
            )

            results.append(
                StressTestScenarioResult(
                    scenario_name=name,
                    scenario_description_zh=desc,
                    market_drawdown_pct=round(mkt_shock * 100.0, 2),
                    estimated_portfolio_drawdown_pct=round(
                        port_drawdown_pct * 100.0, 2
                    ),
                    estimated_dollar_loss=round(total_loss, 2),
                    largest_contributor_loss=contributor_str,
                    capital_preservation_score=round(score, 1),
                    survival_verdict_zh=verdict,
                    narrative_zh=narrative_zh,
                    scenario_name_zh=name_zh,
                    currency_symbol=curr_sym,
                )
            )

        return results

    # --------------------------------------------------------------------------
    # 私有辅助方法 (Private Helpers, Google Style Guide)
    # --------------------------------------------------------------------------

    @staticmethod
    def _compute_cornish_fisher_z(
        z_norm: float, skew: float, kurt: float
    ) -> float:
        """Cornish-Fisher 展开式与分位数反转夹逼防御 (私有辅助方法)."""
        raw_z_cf = (
            z_norm
            + (z_norm**2 - 1.0) * skew / 6.0
            + (z_norm**3 - 3.0 * z_norm) * kurt / 24.0
            - (2.0 * z_norm**3 - 5.0 * z_norm) * (skew**2) / 36.0
        )
        if skew <= 0.0 and kurt >= 0.0:
            return min(z_norm, raw_z_cf)
        return raw_z_cf

    @staticmethod
    def _classify_var_risk(
        cf_var_pct: float,
        param_var_pct: float,
        skew: float,
        kurt: float,
        confidence_level: float,
        cf_var_dollars: float,
        curr_sym: str,
    ) -> str:
        """根据分布矩与修正幅度分类买方风险研判 (私有辅助方法)."""
        if cf_var_pct > param_var_pct * 1.3:
            return (
                f"【极度肥尾左偏风险】Cornish-Fisher 修正 VaR ({cf_var_pct*100:.2f}%) "
                f"显著超越正态假设 ({param_var_pct*100:.2f}%)，历史超额峰度达 {kurt:.2f}，"
                "必须防范黑天鹅跳水！"
            )
        if skew < -0.8:
            return (
                f"【显著左偏下行暴露】收益率呈负偏态 (偏度 {skew:.2f})，"
                "常态微利但极端单日回撤风险剧烈。"
            )
        return (
            f"【风险形态相对温和】收益率分布接近正态走廊，"
            f"{int(confidence_level*100)}% 置信度下单日极端预期亏损上限约 "
            f"{cf_var_pct*100:.2f}% ({curr_sym}{cf_var_dollars:,.2f})。"
        )

    @staticmethod
    def _resolve_currency_symbol(
        portfolio_positions: Dict[str, float], currency_symbol: Optional[str]
    ) -> str:
        """推导组合货币符号 (私有辅助方法)."""
        if currency_symbol:
            return currency_symbol
        tickers = list(portfolio_positions.keys())
        if tickers and all(
            t.upper().endswith(".T")
            or t.upper().endswith(".JP")
            or (t.isdigit() and len(t) == 4)
            or t.upper().endswith(".SS")
            or t.upper().endswith(".SZ")
            or (t.isdigit() and len(t) == 6)
            for t in tickers
        ):
            return "¥"
        return "$"

    @staticmethod
    def _calculate_asset_stress_shock(
        ticker: str,
        pos_val: float,
        beta: float,
        mkt_shock: float,
        sc: Dict[str, Any],
    ) -> Tuple[float, float]:
        """测算单只资产在宏观冲击下的理论预期下挫 (私有辅助方法)."""
        beta_downside = (
            beta * (1.0 + 0.25 * abs(mkt_shock)) if mkt_shock < 0 else beta
        )
        convexity_drag = (
            0.20 * abs(beta) * (mkt_shock**2) if mkt_shock < 0 else 0.0
        )

        if "tech_growth_shock" in sc and beta > 1.2:
            ticker_shock = (
                sc["tech_growth_shock"] * (beta_downside / 1.3) - convexity_drag
            )
        elif "value_defensive_shock" in sc and beta < 0.9 and beta >= 0.0:
            ticker_shock = sc["value_defensive_shock"]
        else:
            ticker_shock = mkt_shock * beta_downside - convexity_drag

        clamped_shock = max(-0.99, ticker_shock)
        dollar_loss = -clamped_shock * pos_val
        return clamped_shock, dollar_loss

    @staticmethod
    def _format_largest_contributor(
        asset_dollar_losses: Dict[str, float], total_loss: float, curr_sym: str
    ) -> str:
        """格式化承压最大亏损标的描述 (私有辅助方法)."""
        worst_ticker = max(
            asset_dollar_losses.keys(), key=lambda t: asset_dollar_losses[t]
        )
        worst_loss = asset_dollar_losses[worst_ticker]
        if worst_loss <= 0:
            return "全部持仓均未发生亏损"
        if total_loss > 0:
            pct_contrib = worst_loss / total_loss * 100.0
            return (
                f"{worst_ticker} (亏损 {curr_sym}{worst_loss:,.2f}, "
                f"贡献组合损失 {pct_contrib:.1f}%)"
            )
        return f"{worst_ticker} 承压亏损 {curr_sym}{worst_loss:,.2f}，已被其余对冲持仓完全覆盖"

    @staticmethod
    def _evaluate_capital_preservation(
        port_drawdown_pct: float, total_loss: float, curr_sym: str
    ) -> Tuple[float, str]:
        """综合评估资本保全得分与买方生存定性 (私有辅助方法)."""
        if port_drawdown_pct >= 0:
            score = 100.0
        else:
            score = max(0.0, 100.0 - (abs(port_drawdown_pct) / 0.50) * 100.0)

        if total_loss < -1e-4:
            verdict = (
                f"【对冲逆势获利】预估组合在极端压力下逆势产生收益 "
                f"+{port_drawdown_pct*100:.2f}% (+{curr_sym}{abs(total_loss):,.2f})，"
                "避险与非对称对冲结构极佳。"
            )
        elif abs(total_loss) <= 1e-4:
            verdict = (
                f"【零回撤资本保全】预估组合净损失为 {curr_sym}0.00，"
                "完美免疫宏观下行冲击。"
            )
        elif port_drawdown_pct < -0.30:
            verdict = (
                f"【高危爆仓警戒】预估组合承压回撤高达 {abs(port_drawdown_pct)*100:.2f}% "
                f"(预估亏损 {curr_sym}{total_loss:,.2f})，击穿买方流动性防线！"
            )
        elif port_drawdown_pct < -0.15:
            verdict = (
                f"【中度承压可控】预估组合承压回撤 {abs(port_drawdown_pct)*100:.2f}% "
                f"(预估亏损 {curr_sym}{total_loss:,.2f})，处于买方对冲基金正常耐受带。"
            )
        else:
            verdict = (
                f"【极佳资本防御】预估组合承压回撤仅 {abs(port_drawdown_pct)*100:.2f}% "
                f"(预估亏损 {curr_sym}{total_loss:,.2f})，表现出优异的低贝塔抗跌能力。"
            )

        return score, verdict
