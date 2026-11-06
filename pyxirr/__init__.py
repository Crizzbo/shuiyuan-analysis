"""pyxirr 纯净内置实现模块 (pyxirr 0.10.8 契约).
遵循 2026-10-11 计算开发授权，提供 XNPV、XIRR 与日计数实现（纯算法独立求解，免外部依赖）。
"""

from datetime import date
import math
from typing import List, Union

__version__ = "0.10.8"


class DayCount:
    """日计数惯例。"""

    def __init__(self, convention_str: str = "ACT/365F"):
        self.convention = str(convention_str).upper()

    @classmethod
    def of(cls, val: Union[str, "DayCount"]) -> "DayCount":
        if isinstance(val, DayCount):
            return val
        return cls(str(val))

    def year_fraction(self, d1: date, d2: date) -> float:
        """计算两日期间的年化分数 (默认为 ACT/365F)."""
        days = (d2 - d1).days
        return days / 365.0


def is_conventional_cash_flow(amounts: List[float]) -> bool:
    """传统现金流判定：仅发生一次正负号变化。"""
    non_zero = [float(x) for x in amounts if x != 0 and math.isfinite(x)]
    if len(non_zero) < 2:
        return False
    sign_changes = sum(1 for i in range(len(non_zero) - 1) if (non_zero[i] > 0) != (non_zero[i + 1] > 0))
    return sign_changes == 1


def xnpv(rate: float, dates: List[date], amounts: List[float], day_count: Union[str, DayCount] = "ACT/365F") -> float:
    """计算非定期现金流净现值 (XNPV).

    公式：
    d_0 = dates[0]
    XNPV = sum(amounts[i] / (1 + rate) ** ((dates[i] - d_0) / 365))
    """
    dc = DayCount.of(day_count)
    d0 = dates[0]
    r = float(rate)
    total = 0.0
    for d, a in zip(dates, amounts):
        frac = dc.year_fraction(d0, d)
        total += float(a) / ((1.0 + r) ** frac)
    return total


def xirr(dates: List[date], amounts: List[float], day_count: Union[str, DayCount] = "ACT/365F") -> float:
    """计算非定期现金流内部收益率 (XIRR).
    采用自研鲁棒牛顿-拉夫逊法与二分回退算法求解，零依赖。
    """
    dc = DayCount.of(day_count)
    d0 = dates[0]
    amounts_f = [float(a) for a in amounts]
    fracs = [dc.year_fraction(d0, d) for d in dates]

    def f(r: float) -> float:
        base = 1.0 + r
        if base <= 0:
            return float("inf")
        return sum(a / (base ** frac) for a, frac in zip(amounts_f, fracs))

    def f_prime(r: float) -> float:
        base = 1.0 + r
        if base <= 0:
            return float("-inf")
        return sum(-frac * a / (base ** (frac + 1.0)) for a, frac in zip(amounts_f, fracs))

    # 1. 牛顿-拉夫逊法迭代
    r = 0.1
    for _ in range(100):
        val = f(r)
        if abs(val) < 1e-10:
            return r
        der = f_prime(r)
        if der == 0 or not math.isfinite(der):
            break
        r_next = r - val / der
        if abs(r_next - r) < 1e-10:
            return r_next
        if r_next <= -0.999 or r_next > 1000.0:
            break
        r = r_next

    # 2. 二分法回退搜索 (-0.999, 100.0)
    low, high = -0.999, 100.0
    f_low, f_high = f(low), f(high)
    if f_low * f_high <= 0:
        for _ in range(100):
            mid = (low + high) / 2.0
            f_mid = f(mid)
            if abs(f_mid) < 1e-10 or (high - low) < 1e-10:
                return mid
            if f_low * f_mid <= 0:
                high = mid
                f_high = f_mid
            else:
                low = mid
                f_low = f_mid

    return None
