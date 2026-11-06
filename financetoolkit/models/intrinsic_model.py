"""内在价值模型 (Intrinsic Value Model / DCF).
基于 Gordon 永续增长与多期自由现金流折现推导企业价值与每股内在价值。
中文注释与功能设计遵循 2026-10-11 计算开发授权。
"""

import pandas as pd


def get_intrinsic_value(
    free_cash_flow,
    growth_rate,
    terminal_growth_rate,
    discount_rate,
    cash,
    debt,
    total_shares_outstanding,
    years,
):
    """计算折现现金流内在价值 (FCFF DCF).

    公式：
    预测期现金流: CF_t = CF_0 * (1 + g)^t
    折现现金流: PV_t = CF_t / (1 + r)^t
    终值: TV = CF_n * (1 + g_term) / (r - g_term)
    折现终值: PV_TV = TV / (1 + r)^n
    企业价值 (Enterprise Value) = sum(PV_t) + PV_TV
    权益价值 (Equity Value) = Enterprise Value + cash - debt
    每股内在价值 (Intrinsic Value) = Equity Value / total_shares_outstanding
    """
    cf = float(free_cash_flow)
    g = float(growth_rate)
    g_term = float(terminal_growth_rate)
    r = float(discount_rate)
    c = float(cash)
    d = float(debt)
    shares = float(total_shares_outstanding)
    n = int(years)

    pv_sum = 0.0
    current_cf = cf
    for t in range(1, n + 1):
        current_cf *= 1.0 + g
        pv_sum += current_cf / ((1.0 + r) ** t)

    tv = current_cf * (1.0 + g_term) / (r - g_term)
    pv_tv = tv / ((1.0 + r) ** n)

    enterprise_value = pv_sum + pv_tv
    equity_value = enterprise_value + c - d
    intrinsic_value = equity_value / shares

    return pd.DataFrame(
        {"input": [enterprise_value, equity_value, intrinsic_value]},
        index=["Enterprise Value", "Equity Value", "Intrinsic Value"],
    )
