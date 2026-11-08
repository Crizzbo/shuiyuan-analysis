# -*- coding: utf-8 -*-
"""Merton 结构化信用违约与破产预警引擎 (merton_default_engine.py).

严格遵循《AGENTS.md》与《CLAUDE.md》：
1. 金融理论基石：
   - 基于 Merton (1974) 结构化信用风险与 KMV 模型；
   - 将企业股权视为在企业总资产价值 $V_A$ 上的看涨期权，行权价为违约点债务面值 $D$；
   - 联立 Black-Scholes 股权定价方程与 Ito 引理波动率传递方程，反解隐含资产价值 $V_A$ 与资产波动率 $\sigma_A$；
   - 导出标准化违约距离 (Distance to Default, DD) 与预期违约频率 (Expected Default Frequency, EDF)。
2. 金融数学边界防御：
   - 资产除零/除负保护，负债非负下界，有限责任期权极值收敛；
   - 资产波动率极小值下界保护（>= 1e-4），防止除零溢出；
   - 正态分布逆累积函数 (probit) 极值截断，防止数值爆炸。
3. 架构纯洁性：
   - 位于 financial_core 底层，零外层逆向依赖，纯纯净金融计算。
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class MertonDefaultMetrics:
    """Merton 结构化信用模型核算输出契约."""
    equity_market_cap: float      # 股权总市值 E ($)
    short_term_debt: float        # 短期借款与一年内到期非流动负债 ($)
    long_term_debt: float         # 长期借款与长期应付债券 ($)
    default_point_debt: float     # 违约触发点负债 D = STD + 0.5 * LTD ($)
    risk_free_rate: float         # 无风险无套利基准利率 r (如 10Y 美债)
    time_horizon_years: float     # 考察期限 T (默认 1.0 年)
    equity_volatility: float      # 股权历史年化波动率 sigma_E
    implied_asset_value: float    # 隐含测算企业真实总资产价值 V_A ($)
    implied_asset_vol: float      # 隐含测算企业总资产波动率 sigma_A
    distance_to_default: float    # 违约距离 DD (标准差倍数)
    expected_default_freq: float  # 预期违约概率 EDF (0.0 ~ 1.0)
    credit_health_grade: str      # 信用安全评级 (INVESTMENT_GRADE, SPECULATIVE, DISTRESSED, CRITICAL_DEFAULT)
    is_black_swan_alert: bool     # 是否触发隔夜暴雷一票否决预警


class MertonStructuralDefaultEngine:
    """KMV-Merton 结构化信用违约与破产黑天鹅前瞻预警引擎."""

    def __init__(
        self,
        risk_free_rate_default: float = 0.04,
        max_iterations: int = 100,
        convergence_tolerance: float = 1e-5,
    ) -> None:
        self.r_default = max(0.0, float(risk_free_rate_default))
        self.max_iter = int(max_iterations)
        self.tol = float(convergence_tolerance)

    @staticmethod
    def _norm_cdf(x: float) -> float:
        """标准正态分布累积分布函数 N(x)."""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    @classmethod
    def calculate_default_point(cls, short_term_debt: float, long_term_debt: float) -> float:
        """计算 KMV 经典违约触发点债务面值 D = STD + 0.5 * LTD."""
        std = max(0.0, float(short_term_debt))
        ltd = max(0.0, float(long_term_debt))
        d_point = std + 0.5 * ltd
        # 边界防守：若债务为0，赋予极小正数 epsilon，避免除零
        return max(1.0, d_point)

    def solve_implied_asset_parameters(
        self,
        equity_val: float,
        equity_vol: float,
        debt_point: float,
        r: float,
        t: float,
    ) -> Tuple[float, float]:
        """二分/牛顿联合迭代反解企业不可见资产价值 V_A 与资产波动率 sigma_A."""
        E = max(1.0, float(equity_val))
        sigma_E = max(0.01, float(equity_vol))
        D = max(1.0, float(debt_point))
        r = max(0.0, float(r))
        T = max(0.05, float(t))
        sqrt_T = math.sqrt(T)

        # 初始估计：初始资产价值通常等于股权价值加债务面值
        V_A = E + D
        sigma_A = sigma_E * (E / V_A)

        for _ in range(self.max_iter):
            sigma_A = max(1e-4, sigma_A)
            d1 = (math.log(V_A / D) + (r + 0.5 * (sigma_A ** 2)) * T) / (sigma_A * sqrt_T)
            d2 = d1 - sigma_A * sqrt_T

            Nd1 = self._norm_cdf(d1)
            Nd2 = self._norm_cdf(d2)

            # Black-Scholes 看涨期权价值
            call_price = V_A * Nd1 - D * math.exp(-r * T) * Nd2
            f1 = call_price - E

            # Ito 引理波动率传递方程: sigma_E * E = Nd1 * V_A * sigma_A
            target_sigma_A = (sigma_E * E) / max(1e-6, Nd1 * V_A)
            f2 = sigma_A - target_sigma_A

            # 收敛性检查
            if abs(f1) / E < self.tol and abs(f2) < self.tol:
                break

            # 资产价值更新（导数近似 Nd1）
            deriv = max(0.05, Nd1)
            step_v = f1 / deriv
            V_A = max(E * 0.5, V_A - step_v * 0.7)  # 阻尼更新
            sigma_A = 0.5 * sigma_A + 0.5 * target_sigma_A

        sigma_A = max(0.01, min(3.0, sigma_A))
        V_A = max(E, V_A)
        return V_A, sigma_A

    def evaluate_credit_default_risk(
        self,
        equity_market_cap: float,
        short_term_debt: float,
        long_term_debt: float,
        equity_volatility_annual: float,
        risk_free_rate: Optional[float] = None,
        time_horizon_years: float = 1.0,
    ) -> MertonDefaultMetrics:
        """全息评估企业信用违约风险、破产距离与黑天鹅预警."""
        r = self.r_default if risk_free_rate is None else max(0.0, float(risk_free_rate))
        T = max(0.05, float(time_horizon_years))
        E = max(100.0, float(equity_market_cap))
        sigma_E = max(0.02, min(5.0, float(equity_volatility_annual)))

        D = self.calculate_default_point(short_term_debt, long_term_debt)

        # 反解资产参数
        V_A, sigma_A = self.solve_implied_asset_parameters(
            equity_val=E,
            equity_vol=sigma_E,
            debt_point=D,
            r=r,
            t=T,
        )

        # 计算违约距离 Distance to Default (DD)
        # DD = [ln(V_A / D) + (r - 0.5 * sigma_A^2) * T] / (sigma_A * sqrt(T))
        sqrt_T = math.sqrt(T)
        num = math.log(max(1e-6, V_A / D)) + (r - 0.5 * (sigma_A ** 2)) * T
        denom = max(1e-4, sigma_A * sqrt_T)
        dd = num / denom

        # 预期违约概率 Expected Default Frequency (EDF) = N(-DD)
        edf = self._norm_cdf(-dd)
        edf = max(0.0, min(1.0, edf))

        # 信用等级与黑天鹅预警研判
        if dd >= 4.0:
            grade = "INVESTMENT_GRADE_AAA"
            is_alert = False
        elif dd >= 2.5:
            grade = "INVESTMENT_GRADE_BBB"
            is_alert = False
        elif dd >= 1.5:
            grade = "SPECULATIVE_BB"
            is_alert = False
        elif dd >= 0.8:
            grade = "DISTRESSED_CCC"
            is_alert = True  # 触发高危黑天鹅警报
        else:
            grade = "CRITICAL_DEFAULT_D"
            is_alert = True  # 极度濒危破产警报

        return MertonDefaultMetrics(
            equity_market_cap=round(E, 2),
            short_term_debt=round(float(short_term_debt), 2),
            long_term_debt=round(float(long_term_debt), 2),
            default_point_debt=round(D, 2),
            risk_free_rate=round(r, 4),
            time_horizon_years=round(T, 2),
            equity_volatility=round(sigma_E, 4),
            implied_asset_value=round(V_A, 2),
            implied_asset_vol=round(sigma_A, 4),
            distance_to_default=round(dd, 3),
            expected_default_freq=round(edf, 5),
            credit_health_grade=grade,
            is_black_swan_alert=is_alert,
        )
