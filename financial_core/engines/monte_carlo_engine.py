"""蒙特卡洛多参数连续概率分布随机估值模拟引擎 (Monte Carlo DCF Engine).

遵循 Google Python 编程风格指南与《SPEC-05 估值矩阵与期权二叉树规格书》:
1. 摆脱孤立 3 组离散静态情景的局限，建立参数连续随机分布模型;
2. 支持营收复合增速 (g)、资本成本 (WACC) 与永续增长率 (terminal_g) 的多维随机采样;
3. 向量化并发执行 10,000 次蒙特卡洛多阶段 DCF 贴现模拟;
4. 严格加固金融数学边界：永续分母防除零除负、有限责任股权价值非负保护;
5. 输出内在价值统计分布 (均值、中位数、标准差)、10% 保守底价、90% 乐观靶心以及买方确定性低估概率 P(Fair_Value > Current_Price).
"""

# 1. Python 标准库
from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple

# 2. 第三方数学库
import numpy as np


@dataclass(frozen=True)
class DensityBin:
    """概率密度分布切片数据契约.

    Attributes:
        bin_lower: 区间下界.
        bin_upper: 区间上界.
        bin_midpoint: 区间中点.
        density: 离散概率密度值.
        cumulative_prob_pct: 累计概率百分比 %.
    """

    bin_lower: float
    bin_upper: float
    bin_midpoint: float
    density: float
    cumulative_prob_pct: float

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典输出."""
        return {
            "bin_lower": round(self.bin_lower, 2),
            "bin_upper": round(self.bin_upper, 2),
            "bin_midpoint": round(self.bin_midpoint, 2),
            "density": round(self.density, 6),
            "cumulative_prob_pct": round(self.cumulative_prob_pct, 2),
        }


@dataclass
class MonteCarloDCFInput:
    """蒙特卡洛估值模拟输入底账.

    Attributes:
        base_cash_flow: 基期自由现金流或真实所有者收益 (百万单位).
        current_price: 现行市场股价.
        shares_outstanding: 稀释总股本 (百万股).
        net_debt: 净负债 (总有息负债 - 非受限现金).
        forecast_years: 显式预测年数 (默认 5 年).
        growth_mean: 预期年化增速均值 (例如 0.10 代表 10%).
        growth_std: 增速标准差 (例如 0.06 代表 6%).
        growth_min: 增速硬下限 (例如极端萧条 -0.30 代表 -30%).
        growth_max: 增速硬上限 (例如超级爆发 +0.45 代表 +45%).
        wacc_mean: WACC 均值 (例如 0.10 代表 10%).
        wacc_std: WACC 标准差 (例如 0.015 代表 1.5%).
        wacc_min: WACC 下限 (流动性泛滥时最低折现率).
        wacc_max: WACC 上限 (流动性枯竭时最高折现率).
        terminal_g_mean: 永续增长均值 (例如 0.025 代表 2.5%).
        terminal_g_std: 永续增长标准差.
        terminal_g_max: 永续增长上限 (严禁超过长期名义 GDP 增速).
        currency_symbol: 自适应货币符号 (如 '$' 或 '¥').
        market: 标的市场 ('US', 'JP', 'CN').
    """

    base_cash_flow: float
    current_price: float
    shares_outstanding: float
    net_debt: float
    forecast_years: int = 5
    growth_mean: float = 0.10
    growth_std: float = 0.06
    growth_min: float = -0.30
    growth_max: float = 0.45
    wacc_mean: float = 0.10
    wacc_std: float = 0.015
    wacc_min: float = 0.065
    wacc_max: float = 0.16
    terminal_g_mean: float = 0.025
    terminal_g_std: float = 0.005
    terminal_g_max: float = 0.040
    currency_symbol: Optional[str] = None
    market: Optional[str] = None

    @classmethod
    def from_firm_financial_fact(
        cls,
        firm: Any,
        sector_wacc: float = 0.085,
        terminal_g: float = 0.025,
        forecast_years: int = 5,
        simulated_fcf_million: Optional[float] = None,
        currency_symbol: Optional[str] = None,
        market: Optional[str] = None,
    ) -> "MonteCarloDCFInput":
        """从微观财务底账构造蒙特卡洛 DCF 输入底账.

        Args:
            firm: 包含财务指标的微观企业底账对象.
            sector_wacc: 行业基准加权平均资本成本.
            terminal_g: 永续增长率均值.
            forecast_years: 预测显式年份.
            simulated_fcf_million: 外部模拟自由现金流 (可选).
            currency_symbol: 货币符号 ('$', '¥').
            market: 交易市场代码 ('US', 'JP', 'CN').

        Returns:
            MonteCarloDCFInput 构造完成的输入对象.
        """
        fcf = (
            simulated_fcf_million
            if simulated_fcf_million is not None
            else getattr(firm, "annual_fcf_million", 100.0)
        )
        market_cap_bil = getattr(firm, "market_cap_billion", 10.0)
        mkt = market or getattr(firm, "market", None)
        curr = currency_symbol or getattr(firm, "currency_symbol", None)

        shares = getattr(firm, "shares_diluted_million", None)
        price = getattr(firm, "current_price", None)
        if shares is None or shares <= 0:
            if price is not None and price > 0 and market_cap_bil > 0:
                shares = (market_cap_bil * 1000.0) / price
            else:
                shares = 100.0
                if price is None:
                    price = (
                        (market_cap_bil * 1000.0) / shares
                        if market_cap_bil > 0
                        else 10.0
                    )
        elif price is None:
            price = (market_cap_bil * 1000.0) / shares if market_cap_bil > 0 else 10.0

        tot_debt = getattr(firm, "total_debt_million", 0.0)
        cash = getattr(firm, "cash_and_equivalents_million", 0.0)
        net_debt = tot_debt - cash

        return cls(
            base_cash_flow=float(fcf),
            current_price=float(price),
            shares_outstanding=float(shares),
            net_debt=float(net_debt),
            forecast_years=forecast_years,
            wacc_mean=float(sector_wacc),
            terminal_g_mean=float(terminal_g),
            currency_symbol=curr,
            market=mkt,
        )


@dataclass
class MonteCarloValuationResult:
    """蒙特卡洛模拟估值统计结果.

    Attributes:
        ticker: 标的代码.
        iterations: 模拟抽样次数 (例如 10,000).
        current_price: 现行市价.
        mean_fair_value: 内在价值样本均值.
        median_fair_value: 内在价值中位数 (50% 分位数).
        std_dev: 估值标准差 (离散度).
        percentile_05: 5% 极度极端底价.
        percentile_10: 10% 机构保守安全边际底价 (Margin of Safety Floor).
        percentile_25: 25% 悲观分位数.
        percentile_50: 50% 中性公允价值.
        percentile_75: 75% 乐观分位数.
        percentile_90: 90% 乐观弹性靶心 (Bull Target).
        percentile_95: 95% 极度乐观天花板.
        prob_undervalued_pct: 现价处于低估区间的概率 P(Intrinsic > Price) * 100%.
        var_downside_pct: 在 90% 置信度下的最大理论下行空间 %.
        simulation_summary_zh: 买方决策解读.
        cvar_10_floor: 10% 尾部条件在险价值 (CVaR/Expected Shortfall).
        cvar_downside_pct: CVaR 相对于现价的下行空间 %.
        corridor_spread: 安全边际走廊宽度 (P90 - P10).
        relative_corridor_spread_pct: 相对走廊离散度 ((P90 - P10) / P50 * 100%).
        density_distribution: 连续概率密度分桶切片列表.
        valuation_regime_zh: 纯自然中文估值状态定性 (去工程符号化).
        narrative_zh: 买方通俗全息研报卡片 (去工程符号化).
        currency_symbol: 货币符号 (如 '$' 或 '¥').
    """

    ticker: str
    iterations: int
    current_price: float
    mean_fair_value: float
    median_fair_value: float
    std_dev: float
    percentile_05: float
    percentile_10: float
    percentile_25: float
    percentile_50: float
    percentile_75: float
    percentile_90: float
    percentile_95: float
    prob_undervalued_pct: float
    var_downside_pct: float
    simulation_summary_zh: str
    cvar_10_floor: float = 0.0
    cvar_downside_pct: float = 0.0
    corridor_spread: float = 0.0
    relative_corridor_spread_pct: float = 0.0
    density_distribution: List[DensityBin] = field(default_factory=list)
    valuation_regime_zh: str = ""
    narrative_zh: str = ""
    currency_symbol: str = "$"

    def to_dict(self) -> Dict[str, Any]:
        """序列化为买方可视化卡片字典."""
        return {
            "ticker": self.ticker,
            "currency_symbol": self.currency_symbol,
            "iterations": self.iterations,
            "current_price": round(self.current_price, 2),
            "mean_fair_value": round(self.mean_fair_value, 2),
            "median_fair_value": round(self.median_fair_value, 2),
            "std_dev": round(self.std_dev, 2),
            "percentiles": {
                "p05_extreme_floor": round(self.percentile_05, 2),
                "p10_conservative_floor": round(self.percentile_10, 2),
                "p25_bearish": round(self.percentile_25, 2),
                "p50_neutral_fair": round(self.percentile_50, 2),
                "p75_bullish": round(self.percentile_75, 2),
                "p90_bull_target": round(self.percentile_90, 2),
                "p95_extreme_ceiling": round(self.percentile_95, 2),
            },
            "prob_undervalued_pct": round(self.prob_undervalued_pct, 2),
            "var_downside_pct": round(self.var_downside_pct, 2),
            "cvar_10_floor": round(self.cvar_10_floor, 2),
            "cvar_downside_pct": round(self.cvar_downside_pct, 2),
            "corridor_spread": round(self.corridor_spread, 2),
            "relative_corridor_spread_pct": round(self.relative_corridor_spread_pct, 2),
            "density_distribution": [b.to_dict() for b in self.density_distribution],
            "valuation_regime_zh": self.valuation_regime_zh or self.simulation_summary_zh,
            "narrative_zh": self.narrative_zh or self.simulation_summary_zh,
            "summary": self.simulation_summary_zh,
        }


class MonteCarloValuationEngine:
    """蒙特卡洛多参数估值模拟中枢 (Google Python Style Guide 架构设计)."""

    def __init__(self):
        """初始化蒙特卡洛估值引擎."""
        self.version: str = "2.0.0"

    def run_monte_carlo_dcf(
        self,
        ticker: str,
        params: MonteCarloDCFInput,
        iterations: int = 10000,
        random_seed: Optional[int] = 42,
        market: Optional[str] = None,
        currency_symbol: Optional[str] = None,
    ) -> MonteCarloValuationResult:
        """执行 10,000 次向量化多阶段 DCF 蒙特卡洛抽样模拟.

        Args:
            ticker: 证券代码 (如 'NVDA', '7203.T').
            params: 蒙特卡洛连续概率分布参数输入对象.
            iterations: 模拟抽样次数 (默认 10,000 次，范围 [1000, 100000]).
            random_seed: 伪随机数种子 (设为整数确保结果可复现，None 则为真随机).
            market: 市场代码 ('US', 'JP', 'CN'，默认自适应推导).
            currency_symbol: 显式货币符号 ('$', '¥').

        Returns:
            MonteCarloValuationResult 包含内在价值分位数、低估概率与下行回撤的全息结果.
        """
        curr_sym = self._resolve_currency_symbol(ticker, params, market, currency_symbol)

        n_samples = max(1000, min(100000, int(iterations)))
        years = max(1, min(10, int(params.forecast_years)))
        shares = max(0.01, float(params.shares_outstanding))
        cf0 = max(0.01, float(params.base_cash_flow))
        net_debt = float(params.net_debt)
        cur_price = float(params.current_price)

        rng = np.random.default_rng(random_seed) if random_seed is not None else np.random.default_rng()

        # 向量化计算每股价值样本分布
        per_share_values = self._simulate_per_share_values(
            rng=rng,
            n_samples=n_samples,
            years=years,
            shares=shares,
            cf0=cf0,
            net_debt=net_debt,
            params=params,
        )

        # 统计特征与分位数走廊计算
        stats = self._compute_statistics(per_share_values, cur_price, n_samples)

        # 概率密度曲线离散分桶 (20 个等宽区间)
        density_bins = self._build_density_distribution(per_share_values, n_samples)

        # 投研解读与研报叙述
        narrative_zh, summary_zh, regime_zh = self._render_narratives(
            ticker=ticker,
            cur_price=cur_price,
            stats=stats,
            curr_sym=curr_sym,
        )

        return MonteCarloValuationResult(
            ticker=ticker,
            iterations=n_samples,
            current_price=cur_price,
            mean_fair_value=stats["mean"],
            median_fair_value=stats["median"],
            std_dev=stats["std"],
            percentile_05=stats["p05"],
            percentile_10=stats["p10"],
            percentile_25=stats["p25"],
            percentile_50=stats["p50"],
            percentile_75=stats["p75"],
            percentile_90=stats["p90"],
            percentile_95=stats["p95"],
            prob_undervalued_pct=stats["prob_undervalued"],
            var_downside_pct=stats["var_downside"],
            simulation_summary_zh=summary_zh,
            cvar_10_floor=stats["cvar_10"],
            cvar_downside_pct=stats["cvar_downside"],
            corridor_spread=stats["corridor_spread"],
            relative_corridor_spread_pct=stats["relative_corridor_spread"],
            density_distribution=density_bins,
            valuation_regime_zh=regime_zh,
            narrative_zh=narrative_zh,
            currency_symbol=curr_sym,
        )

    # --------------------------------------------------------------------------
    # 私有辅助方法 (Private Helpers, Google Style Guide)
    # --------------------------------------------------------------------------

    @staticmethod
    def _resolve_currency_symbol(
        ticker: str,
        params: MonteCarloDCFInput,
        market: Optional[str],
        currency_symbol: Optional[str],
    ) -> str:
        """根据证券代码和市场推导货币符号 (私有辅助方法)."""
        t_up = (ticker or "").upper()
        m_up = ((market or getattr(params, "market", None)) or "").upper()
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
        if currency_symbol:
            return currency_symbol
        if getattr(params, "currency_symbol", None):
            return params.currency_symbol
        if is_jp or is_cn:
            return "¥"
        return "$"

    @staticmethod
    def _simulate_per_share_values(
        rng: np.random.Generator,
        n_samples: int,
        years: int,
        shares: float,
        cf0: float,
        net_debt: float,
        params: MonteCarloDCFInput,
    ) -> np.ndarray:
        """执行向量化现金流模拟并返回每股价值样本数组 (私有辅助方法)."""
        # 1. 向量化抽样 WACC
        wacc_samples = rng.normal(params.wacc_mean, params.wacc_std, n_samples)
        wacc_samples = np.clip(wacc_samples, params.wacc_min, params.wacc_max)

        # 2. 向量化抽样永续增长率 g_term (防除零除负加固)
        g_term_samples = rng.normal(params.terminal_g_mean, params.terminal_g_std, n_samples)
        max_allowed_g = np.minimum(params.terminal_g_max, wacc_samples - 0.010)
        g_term_samples = np.minimum(g_term_samples, max_allowed_g)
        g_term_samples = np.maximum(-0.02, g_term_samples)

        # 3. 向量化抽样复合增速矩阵
        growth_matrix = np.zeros((n_samples, years))
        for t in range(years):
            decay = 1.0 - (t * 0.12)
            mu_t = params.growth_mean * decay
            sigma_t = params.growth_std * decay
            samples_t = rng.normal(mu_t, sigma_t, n_samples)
            growth_matrix[:, t] = np.clip(samples_t, params.growth_min, params.growth_max)

        # 4. 逐年折现现值
        cum_growth = np.cumprod(1.0 + growth_matrix, axis=1)
        cf_matrix = cf0 * cum_growth
        years_arr = np.arange(1, years + 1)
        wacc_col = wacc_samples[:, np.newaxis]
        discount_factors = 1.0 / np.power(1.0 + wacc_col, years_arr)
        pv_discrete = np.sum(cf_matrix * discount_factors, axis=1)

        # 5. Gordon 终值贴现
        terminal_cf = cf_matrix[:, -1] * (1.0 + g_term_samples)
        denom = np.maximum(0.01, wacc_samples - g_term_samples)
        tv = terminal_cf / denom
        pv_tv = tv / np.power(1.0 + wacc_samples, years)

        # 6. 企业价值与股权价值 (有限责任非负保护)
        ev_samples = pv_discrete + pv_tv
        equity_samples = ev_samples - net_debt
        equity_samples = np.maximum(0.0, equity_samples)

        return equity_samples / shares

    @staticmethod
    def _compute_statistics(
        per_share_values: np.ndarray, cur_price: float, n_samples: int
    ) -> Dict[str, float]:
        """计算内在价值分布的分位数与风险下行指标 (私有辅助方法)."""
        mean_val = float(np.mean(per_share_values))
        std_val = float(np.std(per_share_values))
        median_val = float(np.median(per_share_values))

        p05 = float(np.percentile(per_share_values, 5))
        p10 = float(np.percentile(per_share_values, 10))
        p25 = float(np.percentile(per_share_values, 25))
        p50 = median_val
        p75 = float(np.percentile(per_share_values, 75))
        p90 = float(np.percentile(per_share_values, 90))
        p95 = float(np.percentile(per_share_values, 95))

        prob_undervalued = float(np.mean(per_share_values > cur_price)) * 100.0
        var_downside = ((p10 - cur_price) / max(0.01, cur_price)) * 100.0

        sorted_values = np.sort(per_share_values)
        cutoff_idx_10 = max(1, int(0.10 * n_samples))
        cvar_10 = float(np.mean(sorted_values[:cutoff_idx_10]))
        cvar_downside = ((cvar_10 - cur_price) / max(0.01, cur_price)) * 100.0

        corridor_spread = float(p90 - p10)
        relative_corridor_spread = float((p90 - p10) / max(0.01, p50)) * 100.0

        return {
            "mean": mean_val,
            "std": std_val,
            "median": median_val,
            "p05": p05,
            "p10": p10,
            "p25": p25,
            "p50": p50,
            "p75": p75,
            "p90": p90,
            "p95": p95,
            "prob_undervalued": prob_undervalued,
            "var_downside": var_downside,
            "cvar_10": cvar_10,
            "cvar_downside": cvar_downside,
            "corridor_spread": corridor_spread,
            "relative_corridor_spread": relative_corridor_spread,
        }

    @staticmethod
    def _build_density_distribution(
        per_share_values: np.ndarray, n_samples: int
    ) -> List[DensityBin]:
        """构建离散直方图概率密度切片 (私有辅助方法)."""
        p01 = float(np.percentile(per_share_values, 1))
        p99 = float(np.percentile(per_share_values, 99))
        if p99 <= p01:
            return []

        bin_edges = np.linspace(p01, p99, 21)
        counts, _ = np.histogram(per_share_values, bins=bin_edges)
        bin_width = bin_edges[1] - bin_edges[0]
        density_bins: List[DensityBin] = []
        cum_count = 0
        for i in range(len(counts)):
            cnt = int(counts[i])
            cum_count += cnt
            mid = float((bin_edges[i] + bin_edges[i + 1]) / 2.0)
            density = float(cnt / (n_samples * max(0.0001, bin_width)))
            cum_prob = float(cum_count / n_samples) * 100.0
            density_bins.append(
                DensityBin(
                    bin_lower=float(bin_edges[i]),
                    bin_upper=float(bin_edges[i + 1]),
                    bin_midpoint=mid,
                    density=density,
                    cumulative_prob_pct=cum_prob,
                )
            )
        return density_bins

    @staticmethod
    def _render_narratives(
        ticker: str,
        cur_price: float,
        stats: Dict[str, float],
        curr_sym: str,
    ) -> Tuple[str, str, str]:
        """渲染买方自然语言决策与研报卡片 (私有辅助方法)."""
        prob = stats["prob_undervalued"]
        p10 = stats["p10"]
        p90 = stats["p90"]
        median_val = stats["median"]
        mean_val = stats["mean"]
        std_val = stats["std"]
        cvar_10 = stats["cvar_10"]
        var_downside = stats["var_downside"]
        cvar_downside = stats["cvar_downside"]
        corridor_spread = stats["corridor_spread"]

        if prob >= 75.0:
            status_text = "极高确定性安全边际 (具备强劲买入吸引力)"
            regime_zh = "显著低估 (强安全边际)"
            tactic_zh = (
                f"标的现价 ({curr_sym}{cur_price:.2f}) 处于内在价值分布的绝对底部区间，"
                f"低估概率高达 {prob:.1f}%。10% 保守底价 ({curr_sym}{p10:.2f}) 与极限亏损保底 "
                f"({curr_sym}{cvar_10:.2f}) 提供了坚实的安全垫，建议买方机构采取左侧分批建仓与底仓超配策略。"
            )
        elif prob >= 50.0:
            status_text = "合理中性价值区间 (股价与基本面匹配)"
            regime_zh = "公允中性 (估值合理)"
            tactic_zh = (
                f"标的现价 ({curr_sym}{cur_price:.2f}) 紧贴内在价值中位数 ({curr_sym}{median_val:.2f})，"
                f"低估概率为 {prob:.1f}%，股价已较充分计入基本面预期。"
                f"建议以持有观望为主，等待业绩超预期催化或深幅回调至保守底价 ({curr_sym}{p10:.2f}) 附近再行加仓。"
            )
        else:
            status_text = "高估透支与下行不对称风险 (股价透支基本面)"
            regime_zh = "显著高估 (下行风险高企)"
            tactic_zh = (
                f"标的现价 ({curr_sym}{cur_price:.2f}) 处于内在价值分布的上沿，低估概率仅为 {prob:.1f}%，"
                f"下行理论回撤空间达 {var_downside:+.1f}% (极端尾部下行风险 {cvar_downside:+.1f}%)。"
                f"下行赔率严重不对称，建议分批止盈降低仓位，或通过买入虚值看跌期权进行下行保护。"
            )

        summary_zh = (
            f"10,000 次蒙特卡洛随机模拟结果：内在价值中位数 {curr_sym}{median_val:.2f} "
            f"(均值 {curr_sym}{mean_val:.2f}，标准差 {curr_sym}{std_val:.2f})；"
            f"10% 保守底价 {curr_sym}{p10:.2f} (10% 尾部 CVaR 底价 {curr_sym}{cvar_10:.2f})，"
            f"90% 乐观靶心 {curr_sym}{p90:.2f}；"
            f"现价 ({curr_sym}{cur_price:.2f}) 低于公允价值的概率为 {prob:.1f}% ({status_text})。"
        )

        narrative_zh = (
            f"【标的 {ticker} 蒙特卡洛随机折现估值全息研报】"
            f"估值状态定性【{regime_zh}】(现价低于公允价值概率 {prob:.1f}%)。"
            f"内在价值分布: 连续模拟 10,000 次，公允价值中位数 {curr_sym}{median_val:.2f} "
            f"(均值 {curr_sym}{mean_val:.2f}，离散波动标准差 {curr_sym}{std_val:.2f})。"
            f"安全边际走廊: 10% 保守底价 {curr_sym}{p10:.2f} (10% 尾部极值底价 {curr_sym}{cvar_10:.2f})，"
            f"90% 乐观弹性靶心 {curr_sym}{p90:.2f}，走廊跨度 {curr_sym}{corridor_spread:.2f}。"
            f"下行风险测算: 90% 置信度最大回撤 {var_downside:+.1f}% (尾部预期亏损空间 {cvar_downside:+.1f}%)。"
            f"买方投资战术: {tactic_zh}"
        )

        return narrative_zh, summary_zh, regime_zh
