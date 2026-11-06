"""numpy_financial 纯净内置实现模块 (numpy-financial 1.1.0 契约).
遵循 2026-10-11 计算开发授权，提供现金流与年金基础计算。
"""

import numpy as np

__version__ = "1.1.0"


def _convert_when(when):
    if isinstance(when, str):
        when = when.lower()
        if when in ("b", "begin", "beginning", "start"):
            return 1
        elif when in ("e", "end"):
            return 0
    return int(when)


def fv(rate, nper, pmt, pv, when="end"):
    """终值 (Future Value)."""
    when_val = _convert_when(when)
    r = float(rate)
    n = float(nper)
    p = float(pmt)
    v = float(pv)
    if r == 0:
        return -(v + p * n)
    temp = (1.0 + r) ** n
    fact = (1.0 + r * when_val) * (temp - 1.0) / r
    return -(v * temp + p * fact)


def pv(rate, nper, pmt, fv=0, when="end"):
    """现值 (Present Value)."""
    when_val = _convert_when(when)
    r = float(rate)
    n = float(nper)
    p = float(pmt)
    f = float(fv)
    if r == 0:
        return -(f + p * n)
    temp = (1.0 + r) ** n
    fact = (1.0 + r * when_val) * (temp - 1.0) / r
    return -(f + p * fact) / temp


def pmt(rate, nper, pv, fv=0, when="end"):
    """每期付款 (Payment)."""
    when_val = _convert_when(when)
    r = float(rate)
    n = float(nper)
    v = float(pv)
    f = float(fv)
    if r == 0:
        return -(f + v) / n
    temp = (1.0 + r) ** n
    fact = (1.0 + r * when_val) * (temp - 1.0) / r
    return -(f + v * temp) / fact


def npv(rate, values):
    """净现值 (Net Present Value)."""
    r = float(rate)
    vals = np.asarray(values, dtype=float)
    weights = (1.0 + r) ** np.arange(len(vals))
    return float(np.sum(vals / weights))


def irr(values):
    """内部收益率 (Internal Rate of Return)."""
    vals = np.asarray(values, dtype=float)
    # p(y) = c0 * y^n + c1 * y^(n-1) + ... + cn where y = 1 + r
    p = np.poly1d(vals)
    roots = p.roots
    # 选取虚部为 0 且 1+r > 0 (即 r > -1) 的实根
    real_roots = roots[np.isreal(roots)].real
    valid = real_roots[real_roots > 0]
    if len(valid) == 0:
        return np.nan
    rates = valid - 1.0
    # 选择最接近 0 的根
    idx = np.argmin(np.abs(rates))
    return float(rates[idx])


def mirr(values, finance_rate, reinvest_rate):
    """修正内部收益率 (Modified Internal Rate of Return)."""
    vals = np.asarray(values, dtype=float)
    n = len(vals)
    fr = float(finance_rate)
    rr = float(reinvest_rate)
    pos = vals > 0
    neg = vals < 0
    if not (np.any(pos) and np.any(neg)):
        return np.nan
    numer = np.sum(np.where(pos, vals, 0.0) * (1.0 + rr) ** np.arange(n - 1, -1, -1))
    denom = np.sum(-np.where(neg, vals, 0.0) / (1.0 + fr) ** np.arange(0, n))
    return float((numer / denom) ** (1.0 / (n - 1)) - 1.0)


def nper(rate, pmt, pv, fv=0, when="end"):
    """期数 (Number of Periods)."""
    when_val = _convert_when(when)
    r = float(rate)
    p = float(pmt)
    v = float(pv)
    f = float(fv)
    if r == 0:
        return -(v + f) / p
    z = p * (1.0 + r * when_val) / r
    return np.log((z - f) / (z + v)) / np.log(1.0 + r)
