"""quantstats.stats 模块。
实现夏普比率、索提诺比率、波动率、最大回撤与复合年均增长率 (CAGR)。
"""

import math
import numpy as np
import pandas as pd


def _to_numpy(returns):
    if isinstance(returns, (pd.Series, pd.DataFrame)):
        return returns.values.flatten()
    return np.asarray(returns, dtype=float).flatten()


def sharpe(returns, rf=0.0, periods=252):
    """年化夏普比率 (Sharpe Ratio)."""
    vals = _to_numpy(returns)
    p = float(periods)
    rf_period = (1.0 + float(rf)) ** (1.0 / p) - 1.0
    excess = vals - rf_period
    std_val = float(np.std(vals, ddof=1))
    if std_val == 0.0 or not math.isfinite(std_val):
        return np.nan
    return float((np.mean(excess) / std_val) * math.sqrt(p))


def volatility(returns, periods=252):
    """年化波动率 (Volatility)."""
    vals = _to_numpy(returns)
    p = float(periods)
    std_val = float(np.std(vals, ddof=1))
    if std_val == 0.0 or not math.isfinite(std_val):
        return np.nan
    return float(std_val * math.sqrt(p))


def sortino(returns, rf=0.0, periods=252):
    """年化索提诺比率 (Sortino Ratio)."""
    vals = _to_numpy(returns)
    p = float(periods)
    rf_period = (1.0 + float(rf)) ** (1.0 / p) - 1.0
    excess = vals - rf_period
    neg = np.minimum(excess, 0.0)
    downside = float(np.sqrt(np.mean(neg ** 2)))
    if downside == 0.0 or not math.isfinite(downside):
        return np.nan
    return float((np.mean(excess) / downside) * math.sqrt(p))


def max_drawdown(returns):
    """最大回撤 (Max Drawdown)，包含期初资产 (Initial Wealth)。"""
    vals = _to_numpy(returns)
    comp = np.cumprod(1.0 + vals)
    wealth = np.insert(comp, 0, 1.0)
    peaks = np.maximum.accumulate(wealth)
    drawdowns = (wealth - peaks) / peaks
    return float(np.min(drawdowns))


def cagr(returns, periods=252):
    """复合年均增长率 (Compound Annual Growth Rate)."""
    vals = _to_numpy(returns)
    p = float(periods)
    tot = float(np.prod(1.0 + vals))
    years = len(vals) / p
    if years <= 0:
        return np.nan
    return float((tot ** (1.0 / years)) - 1.0)
