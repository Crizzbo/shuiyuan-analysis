"""信用风险、违约距离与破产预警引擎 (Credit Risk & Solvency Engine).

遵循 Google Python 编程风格指南与《SPEC-06 资产负债表健康度与信用风险规格书》:
1. Merton (1974) 结构化信用违约模型:
   - 将公司股权视为以公司总资产为标的、负债面值为行权价的看涨期权;
   - 阻尼牛顿迭代求解资产市值 (V_A) 与资产波动率 (sigma_A);
   - 显式解耦真实物理测度 (DD_P, EDF_P) 与风险中性测度 (DD_Q, EDF_Q) 及公允信用利差 (bps);
2. Altman Z-Score 5 因子破产预警模型:
   - 制造业经典 5 因子 Z-Score 与非制造业/服务业通用 4 因子 Z''-Score;
   - 自动划分安全区 (Safe Zone)、灰色观察区 (Grey Zone) 与高危破产区 (Distress Zone);
3. 可转债 (Convertible Bond) 股债二元定价与潜在稀释分析:
   - 测算纯债底价 (Bond Floor) 与转股价值 (Conversion Value)，评估潜在股本稀释冲击.
"""

# 1. Python 标准库
from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple

# 2. 第三方数学与科学计算库
import numpy as np

try:
    from scipy.stats import norm
except (ImportError, ValueError):

    class _NormFallback:
        @staticmethod
        def cdf(x: float) -> float:
            return 0.5 * (1.0 + math.erf(float(x) / math.sqrt(2.0)))

        @staticmethod
        def pdf(x: float) -> float:
            return math.exp(-0.5 * float(x) * float(x)) / math.sqrt(2.0 * math.pi)

    norm = _NormFallback()


@dataclass(frozen=True)
class MertonCreditInput:
    """Merton 结构化信用模型输入参数数据契约.

    Attributes:
        equity_market_cap: 股权市场价值 (百万货币单位) E.
        total_debt_face_value: 总负债账面面值 (百万货币单位) D (通常取短期负债 + 0.5 * 长期负债).
        equity_volatility: 股票历史年化波动率 sigma_E (例如 0.35 代表 35%).
        risk_free_rate: 无风险利率 r (例如 0.045 代表 4.5%).
        time_to_maturity_years: 评估周期 T (默认 1 年).
        expected_asset_return: 资产期望真实回报率 mu_A (默认 r + 0.05 风险溢价).
    """

    equity_market_cap: float
    total_debt_face_value: float
    equity_volatility: float
    risk_free_rate: float
    time_to_maturity_years: float = 1.0
    expected_asset_return: Optional[float] = None


@dataclass(frozen=True)
class CreditRiskResult:
    """信用风险与违约概率评估结果数据契约.

    Attributes:
        ticker: 标的代码.
        asset_market_value: 估计总资产市场价值 V_A.
        asset_volatility: 估计资产波动率 sigma_A.
        distance_to_default: 违约距离 DD (标准差倍数，越大越安全).
        expected_default_frequency: 预期违约率 EDF (0.0 ~ 1.0).
        altman_z_score: Altman Z-Score 破产评分.
        altman_zone: 财务区域 ('Safe', 'Grey', 'Distress').
        credit_rating_proxy: 对标买方信用评级代号 ('AAA/AA', 'A/BBB', 'BB/B', 'CCC/D').
        credit_alert_flag: 是否触发高危信用警报.
        bond_floor_per_share: 可转债纯债底价 (若适用).
        convertible_dilution_shares: 潜在可转债转股稀释股数 (若适用).
        summary_zh: 中文投研简评.
        narrative_zh: 买方通俗全息研报卡片 (去工程符号化).
        physical_distance_to_default: 物理测度真实违约距离 DD_P (基于 mu_A).
        physical_default_probability: 物理测度真实破产率 EDF_P.
        risk_neutral_default_probability: 风险中性违约率 EDF_Q (基于 r).
        implied_credit_spread_bps: Merton 理论公允信用利差 (基点 bps).
        rating_proxy_zh: 信用评级通俗中文定性.
        altman_zone_zh: 财务健康区域中文命名.
        currency_symbol: 货币符号 ('$', '¥').
    """

    ticker: str
    asset_market_value: float
    asset_volatility: float
    distance_to_default: float
    expected_default_frequency: float
    altman_z_score: float
    altman_zone: str
    credit_rating_proxy: str
    credit_alert_flag: bool
    bond_floor_per_share: Optional[float] = None
    convertible_dilution_shares: Optional[float] = None
    summary_zh: str = ""
    narrative_zh: str = ""
    physical_distance_to_default: Optional[float] = None
    physical_default_probability: Optional[float] = None
    risk_neutral_default_probability: Optional[float] = None
    implied_credit_spread_bps: Optional[float] = None
    rating_proxy_zh: str = ""
    altman_zone_zh: str = ""
    currency_symbol: str = "$"

    def to_dict(self) -> Dict[str, Any]:
        """序列化为买方可视化卡片字典."""
        return {
            "ticker": self.ticker,
            "asset_market_value": round(self.asset_market_value, 2),
            "asset_volatility": round(self.asset_volatility, 4),
            "distance_to_default": round(self.distance_to_default, 2),
            "expected_default_frequency_pct": round(
                self.expected_default_frequency * 100, 4
            ),
            "physical_distance_to_default": (
                round(self.physical_distance_to_default, 2)
                if self.physical_distance_to_default is not None
                else None
            ),
            "physical_default_probability_pct": (
                round(self.physical_default_probability * 100, 4)
                if self.physical_default_probability is not None
                else None
            ),
            "risk_neutral_default_probability_pct": (
                round(self.risk_neutral_default_probability * 100, 4)
                if self.risk_neutral_default_probability is not None
                else None
            ),
            "implied_credit_spread_bps": self.implied_credit_spread_bps,
            "altman_z_score": round(self.altman_z_score, 2),
            "altman_zone": self.altman_zone,
            "altman_zone_zh": self.altman_zone_zh or self.altman_zone,
            "credit_rating_proxy": self.credit_rating_proxy,
            "credit_rating_proxy_zh": self.rating_proxy_zh or self.credit_rating_proxy,
            "credit_alert_flag": self.credit_alert_flag,
            "bond_floor_per_share": (
                round(self.bond_floor_per_share, 2)
                if self.bond_floor_per_share is not None
                else None
            ),
            "convertible_dilution_shares": (
                round(self.convertible_dilution_shares, 2)
                if self.convertible_dilution_shares is not None
                else None
            ),
            "summary": self.summary_zh,
            "narrative_zh": self.narrative_zh or self.summary_zh,
            "currency_symbol": self.currency_symbol,
        }


class CreditRiskAndSolvencyEngine:
    """信用风险、违约距离与破产预警中枢 (Google Python Style Guide 架构设计)."""

    def __init__(self):
        """初始化信用风险引擎."""
        self.version: str = "2.0.0"
        self._last_metrics: Dict[str, float] = {}

    def solve_merton_model(
        self, params: MertonCreditInput
    ) -> Tuple[float, float, float, float]:
        """联立求解 Merton (1974) 资产价值 V_A 与资产波动率 sigma_A.

        方程组:
        1) E = V_A * N(d1) - D * exp(-r * T) * N(d2)
        2) E * sigma_E = V_A * N(d1) * sigma_A

        Args:
            params: MertonCreditInput 结构化信用模型参数契约.

        Returns:
            Tuple[float, float, float, float]: (V_A 资产市值, sigma_A 资产波动率, DD_Q 风险中性违约距离, EDF_Q 违约率).
        """
        e_val = max(1.0, float(params.equity_market_cap))
        d_val = max(1.0, float(params.total_debt_face_value))
        sigma_e = max(0.01, float(params.equity_volatility))
        r_val = float(params.risk_free_rate)
        t_val = max(0.1, float(params.time_to_maturity_years))
        sqrt_t = math.sqrt(t_val)
        disc_d = d_val * math.exp(-r_val * t_val)

        v_a = e_val + d_val
        sigma_a = sigma_e * (e_val / (e_val + d_val))

        # 阻尼牛顿迭代法求解
        for _ in range(100):
            d1 = (math.log(v_a / d_val) + (r_val + 0.5 * sigma_a * sigma_a) * t_val) / (
                sigma_a * sqrt_t
            )
            d2 = d1 - sigma_a * sqrt_t

            nd1 = norm.cdf(d1)
            nd2 = norm.cdf(d2)

            model_e = v_a * nd1 - disc_d * nd2
            target_sigma_a = (e_val * sigma_e) / max(1e-4, v_a * nd1)

            err_e = abs(model_e - e_val) / e_val
            err_sigma = abs(target_sigma_a - sigma_a) / max(1e-4, sigma_a)

            if err_e < 1e-5 and err_sigma < 1e-5:
                break

            v_a = max(d_val * 0.5, v_a + (e_val - model_e) * 0.7)
            sigma_a = max(0.005, 0.5 * sigma_a + 0.5 * target_sigma_a)

        # 1. 风险中性测度 Q
        d1_q = (math.log(v_a / d_val) + (r_val + 0.5 * sigma_a * sigma_a) * t_val) / (
            sigma_a * sqrt_t
        )
        d2_q = d1_q - sigma_a * sqrt_t
        dd_q = d2_q
        edf_q = float(norm.cdf(-dd_q))

        # 2. 真实物理测度 P
        mu_a = (
            float(params.expected_asset_return)
            if params.expected_asset_return is not None
            else (r_val + 0.05)
        )
        d1_p = (math.log(v_a / d_val) + (mu_a + 0.5 * sigma_a * sigma_a) * t_val) / (
            sigma_a * sqrt_t
        )
        d2_p = d1_p - sigma_a * sqrt_t
        dd_p = d2_p
        edf_p = float(norm.cdf(-dd_p))

        self._last_metrics = {
            "dd_p": float(dd_p),
            "edf_p": float(edf_p),
            "dd_q": float(dd_q),
            "edf_q": float(edf_q),
            "d1_q": float(d1_q),
            "d2_q": float(d2_q),
        }

        return float(v_a), float(sigma_a), float(dd_q), edf_q

    def calculate_altman_z_score(
        self,
        working_capital: float,
        retained_earnings: float,
        ebit: float,
        equity_market_cap: float,
        total_revenue: float,
        total_assets: float,
        total_liabilities: float,
        is_manufacturing: bool = True,
    ) -> Tuple[float, str]:
        """计算 Altman Z-Score 破产预警评分与安全区间.

        Args:
            working_capital: 营运资本 (流动资产 - 流动负债).
            retained_earnings: 留存收益.
            ebit: 息税前营业利润 EBIT.
            equity_market_cap: 股权市场价值.
            total_revenue: 总营业收入.
            total_assets: 资产总额.
            total_liabilities: 负债总额.
            is_manufacturing: 是否为制造业 (True 为经典 5 因子，False 为 4 因子服务业模型).

        Returns:
            Tuple[float, str]: (Z-Score 评分值, 所属区域代号 'Safe'/'Grey'/'Distress').
        """
        assets = max(1.0, float(total_assets))
        liab = max(1.0, float(total_liabilities))

        x1 = working_capital / assets
        x2 = retained_earnings / assets
        x3 = ebit / assets
        x4 = equity_market_cap / liab
        x5 = total_revenue / assets

        if is_manufacturing:
            z_score = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 0.999 * x5
            if z_score > 2.99:
                zone = "Safe"
            elif z_score >= 1.81:
                zone = "Grey"
            else:
                zone = "Distress"
        else:
            z_score = 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4
            if z_score > 2.60:
                zone = "Safe"
            elif z_score >= 1.10:
                zone = "Grey"
            else:
                zone = "Distress"

        return float(z_score), zone

    def evaluate_convertible_bond(
        self,
        stock_price: float,
        conversion_price: float,
        par_value: float,
        coupon_rate: float,
        maturity_years: float,
        credit_spread: float,
        risk_free_rate: float,
        shares_outstanding: float,
        total_cb_par_amount: float,
    ) -> Dict[str, Any]:
        """可转债股债二元定价与潜在稀释压力测试.

        Args:
            stock_price: 标的正股现价.
            conversion_price: 转股价格.
            par_value: 可转债面值.
            coupon_rate: 票面年息率.
            maturity_years: 到期剩余年限.
            credit_spread: 标的信用风险利差.
            risk_free_rate: 无风险利率.
            shares_outstanding: 当前总股本.
            total_cb_par_amount: 可转债发行总面额.

        Returns:
            Dict[str, Any] 包含纯债底价、转股价值与稀释比例的字典.
        """
        s_val = max(0.01, float(stock_price))
        cp_val = max(0.01, float(conversion_price))
        par_val = max(1.0, float(par_value))
        t_val = max(0.1, float(maturity_years))
        y_rate = float(risk_free_rate) + float(credit_spread)
        coupon = par_val * float(coupon_rate)

        # 1. 纯债底价
        disc_base = max(0.0001, 1.0 + y_rate)
        bond_floor = 0.0
        n_periods = max(1, int(math.ceil(t_val)))
        for t in range(1, n_periods + 1):
            bond_floor += coupon / math.pow(disc_base, t)
        bond_floor += par_val / math.pow(disc_base, t_val)

        # 2. 转股价值
        conversion_ratio = par_val / cp_val
        conversion_value = conversion_ratio * s_val

        # 3. 潜在转股稀释股数
        potential_dilution_shares = float(total_cb_par_amount) / cp_val
        dilution_ratio_pct = (
            potential_dilution_shares / max(1.0, shares_outstanding)
        ) * 100.0

        in_the_money = s_val >= cp_val
        if s_val >= cp_val:
            conversion_status_zh = (
                "【实值转股区间】现价高于转股价，股性极强，具备行权转股价值"
            )
        elif s_val >= cp_val * 0.90:
            conversion_status_zh = (
                "【平价博弈区间】现价贴近转股价，股债平衡特征显著"
            )
        else:
            conversion_status_zh = (
                "【虚值纯债区间】现价显著低于转股价，缺乏转股吸引力，主要依靠债底支撑"
            )

        return {
            "straight_bond_floor": round(bond_floor, 2),
            "conversion_value": round(conversion_value, 2),
            "conversion_premium_pct": (
                round(((par_val - conversion_value) / conversion_value) * 100, 2)
                if conversion_value > 0
                else 0.0
            ),
            "potential_dilution_shares": round(potential_dilution_shares, 2),
            "dilution_ratio_pct": round(dilution_ratio_pct, 2),
            "is_in_the_money_conversion": in_the_money,
            "conversion_status_zh": conversion_status_zh,
        }

    def evaluate_comprehensive_credit(
        self,
        ticker: str,
        equity_market_cap: float,
        total_debt: float,
        current_assets: float,
        current_liabilities: float,
        retained_earnings: float,
        ebit: float,
        revenue: float,
        total_assets: float,
        total_liabilities: float,
        equity_volatility: float = 0.35,
        risk_free_rate: float = 0.045,
        cb_info: Optional[Dict[str, Any]] = None,
        market: Optional[str] = None,
        currency_symbol: Optional[str] = None,
    ) -> CreditRiskResult:
        """端到端综合信用风险、财务健康度与违约压力评估.

        Args:
            ticker: 标的代码.
            equity_market_cap: 总市值.
            total_debt: 总有息负债.
            current_assets: 流动资产.
            current_liabilities: 流动负债.
            retained_earnings: 留存收益.
            ebit: 息税前利润.
            revenue: 营业收入.
            total_assets: 总资产.
            total_liabilities: 总负债.
            equity_volatility: 股票年化波动率.
            risk_free_rate: 无风险利率.
            cb_info: 可转债信息字典 (可选).
            market: 交易市场 ('US', 'JP', 'CN').
            currency_symbol: 货币符号 ('$', '¥').

        Returns:
            CreditRiskResult 包含违约距离、EDF、Altman 评分与通俗研报卡片的结果对象.
        """
        curr_sym = self._resolve_currency_symbol(ticker, market, currency_symbol)

        # 1. Merton DD & EDF
        merton_input = MertonCreditInput(
            equity_market_cap=equity_market_cap,
            total_debt_face_value=total_debt,
            equity_volatility=equity_volatility,
            risk_free_rate=risk_free_rate,
        )
        va, sa, dd, edf = self.solve_merton_model(merton_input)

        # 2. Altman Z-Score
        working_cap = current_assets - current_liabilities
        z_score, z_zone = self.calculate_altman_z_score(
            working_capital=working_cap,
            retained_earnings=retained_earnings,
            ebit=ebit,
            equity_market_cap=equity_market_cap,
            total_revenue=revenue,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
        )

        # 3. 评级代理映射
        rating_proxy = self._map_credit_rating_proxy(dd, edf)
        alert_flag = (z_zone == "Distress") or (dd < 1.8) or (edf > 0.03)

        # 4. 可转债处理
        bond_floor = None
        cb_dilution = None
        if cb_info:
            cb_res = self.evaluate_convertible_bond(**cb_info)
            bond_floor = cb_res.get("straight_bond_floor")
            cb_dilution = cb_res.get("potential_dilution_shares")

        # 5. Merton 理论信用利差
        spread_bps, dd_p, edf_p = self._compute_merton_spread_and_physical_metrics(
            va=va,
            total_debt=total_debt,
            risk_free_rate=risk_free_rate,
            dd=dd,
            edf=edf,
        )

        # 6. 中文研报自然语言卡片
        summary_zh, narrative_zh, rating_proxy_zh, zone_desc = (
            self._render_narratives(
                ticker=ticker,
                dd_p=dd_p,
                edf_p=edf_p,
                edf=edf,
                spread_bps=spread_bps,
                z_score=z_score,
                z_zone=z_zone,
                rating_proxy=rating_proxy,
                alert_flag=alert_flag,
                bond_floor=bond_floor,
                cb_dilution=cb_dilution,
                curr_sym=curr_sym,
            )
        )

        return CreditRiskResult(
            ticker=ticker,
            asset_market_value=va,
            asset_volatility=sa,
            distance_to_default=dd,
            expected_default_frequency=edf,
            altman_z_score=z_score,
            altman_zone=z_zone,
            credit_rating_proxy=rating_proxy,
            credit_alert_flag=alert_flag,
            bond_floor_per_share=bond_floor,
            convertible_dilution_shares=cb_dilution,
            summary_zh=summary_zh,
            narrative_zh=narrative_zh,
            physical_distance_to_default=round(dd_p, 2),
            physical_default_probability=edf_p,
            risk_neutral_default_probability=edf,
            implied_credit_spread_bps=spread_bps,
            rating_proxy_zh=rating_proxy_zh,
            altman_zone_zh=zone_desc,
            currency_symbol=curr_sym,
        )

    # --------------------------------------------------------------------------
    # 私有辅助方法 (Private Helpers, Google Style Guide)
    # --------------------------------------------------------------------------

    @staticmethod
    def _resolve_currency_symbol(
        ticker: str, market: Optional[str], currency_symbol: Optional[str]
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
        if currency_symbol:
            return currency_symbol
        if is_jp or is_cn:
            return "¥"
        return "$"

    @staticmethod
    def _map_credit_rating_proxy(dd: float, edf: float) -> str:
        """根据违约距离与预期违约率映射对标买方信用评级 (私有辅助方法)."""
        if dd >= 4.5 and edf < 0.0001:
            return "AAA/AA"
        if dd >= 3.0 and edf < 0.005:
            return "A/BBB"
        if dd >= 1.5 and edf < 0.05:
            return "BB/B"
        return "CCC/D"

    def _compute_merton_spread_and_physical_metrics(
        self,
        va: float,
        total_debt: float,
        risk_free_rate: float,
        dd: float,
        edf: float,
    ) -> Tuple[float, float, float]:
        """计算 Merton 理论公允信用利差与物理测度指标 (私有辅助方法)."""
        last_m = getattr(self, "_last_metrics", {})
        d1_q = last_m.get("d1_q", 1.0)
        d2_q = last_m.get("d2_q", 0.5)

        disc_d = total_debt * math.exp(-max(-0.20, min(0.50, risk_free_rate)))
        debt_val_ratio = (va / max(1.0, disc_d)) * float(norm.cdf(-d1_q)) + float(
            norm.cdf(d2_q)
        )
        if debt_val_ratio > 1e-4:
            spread_annual = max(0.0, -math.log(min(1.0, debt_val_ratio)))
            spread_bps = round(spread_annual * 10000.0, 1)
        else:
            spread_bps = 5000.0

        dd_p = last_m.get("dd_p", dd)
        edf_p = last_m.get("edf_p", edf)
        return spread_bps, dd_p, edf_p

    @staticmethod
    def _render_narratives(
        ticker: str,
        dd_p: float,
        edf_p: float,
        edf: float,
        spread_bps: float,
        z_score: float,
        z_zone: str,
        rating_proxy: str,
        alert_flag: bool,
        bond_floor: Optional[float],
        cb_dilution: Optional[float],
        curr_sym: str,
    ) -> Tuple[str, str, str, str]:
        """生成通俗买方自然语言研报卡片 (私有辅助方法)."""
        zone_map = {
            "Distress": "破产预警高危区",
            "Grey": "灰色观察警戒区",
            "Safe": "财务稳健安全区",
        }
        zone_desc = zone_map.get(z_zone, z_zone)
        status_text = (
            "破产高危警报"
            if alert_flag
            else ("审慎关注" if z_zone == "Grey" else "财务安全稳健")
        )

        rating_map = {
            "AAA/AA": "特级优质无违约风险",
            "A/BBB": "投资级稳健",
            "BB/B": "投机级脆弱",
            "CCC/D": "重组或违约极高危",
        }
        rating_proxy_zh = rating_map.get(rating_proxy, rating_proxy)

        cb_clause = ""
        if bond_floor is not None and cb_dilution is not None:
            cb_clause = (
                f" 可转债保护垫: 纯债底价 {curr_sym}{bond_floor:.2f}，"
                f"转股潜在稀释股数 {cb_dilution:,.0f} 股。"
            )

        prob_qualifier = (
            "仅为"
            if (edf_p * 100.0) <= 1.0
            else ("约为" if (edf_p * 100.0) <= 5.0 else "高达")
        )
        prob_risk_neutral_qualifier = (
            "仅为"
            if (edf * 100.0) <= 1.0
            else ("约为" if (edf * 100.0) <= 5.0 else "高达")
        )

        summary_zh = (
            f"【{ticker} 信用风险与偿债能力深度研报】"
            f"物理违约安全垫为 {dd_p:.2f} 个标准差 (1年内实际违约概率{prob_qualifier} {edf_p*100:.2f}%)，"
            f"市场隐含风险中性违约预期{prob_risk_neutral_qualifier} {edf*100:.2f}% (公允信用利差 +{spread_bps:,.0f} 基点)；"
            f"Altman 财务健康度得分为 {z_score:.2f} (处于【{zone_desc}】)；"
            f"机构买方综合信用评级为【{rating_proxy_zh}】(评估定性：{status_text})。"
            f"{cb_clause}"
        )

        narrative_zh = (
            f"【{ticker} 买方偿债能力与违约风险全息研报】"
            f"机构买方综合信用评级为【{rating_proxy_zh}】(对标市场评级 {rating_proxy})，整体评估定性为【{status_text}】。"
            f"破产安全防线: 物理违约安全垫为 {dd_p:.2f} 个标准差，模型推算1年内实际违约概率{prob_qualifier} {edf_p*100:.2f}%。"
            f"债市隐含预期: 风险中性违约预期{prob_risk_neutral_qualifier} {edf*100:.2f}%，要求公允信用补偿利差 +{spread_bps:,.0f} 基点。"
            f"资产负债体魄: Altman 财务健康度得分为 {z_score:.2f} (处于【{zone_desc}】)。"
            f"{cb_clause}"
        )

        return summary_zh, narrative_zh, rating_proxy_zh, zone_desc
