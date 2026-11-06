"""加权平均资本成本模型 (WACC Model).
基于 CAPM 与税后债务成本推导加权资本成本。
中文注释与功能设计遵循 2026-10-11 计算开发授权。
"""
import pandas as pd


def get_weighted_average_cost_of_capital(
    share_price,
    total_shares_outstanding,
    interest_expense,
    total_debt,
    risk_free_rate,
    beta,
    benchmark_returns,
    income_tax_expense,
    income_before_tax,
):
    """计算加权平均资本成本 (WACC).

    公式：
    E = share_price * total_shares_outstanding (权益市值)
    D = total_debt (债务市值)
    V = E + D (总资本价值)
    Cost of Equity (Ke) = risk_free_rate + beta * (benchmark_returns - risk_free_rate)
    Effective Tax Rate (t) = income_tax_expense / income_before_tax
    Cost of Debt (Kd) = interest_expense / total_debt
    WACC = (E / V) * Ke + (D / V) * Kd * (1 - t)
    """
    equity = float(share_price.iloc[0] * total_shares_outstanding.iloc[0])
    debt = float(total_debt.iloc[0])
    total_val = equity + debt
    rf = float(risk_free_rate.iloc[0])
    b = float(beta.iloc[0])
    rm = float(benchmark_returns.iloc[0])
    tax = float(income_tax_expense.iloc[0] / income_before_tax.iloc[0])
    kd = float(interest_expense.iloc[0] / debt)
    ke = rf + b * (rm - rf)
    wacc_val = (equity / total_val) * ke + (debt / total_val) * kd * (1.0 - tax)
    return pd.DataFrame({"input": [wacc_val]}, index=["Weighted Average Cost of Capital"])
