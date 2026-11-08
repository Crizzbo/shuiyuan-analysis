"""基础公式委托开源库；近零利率年金采用稳定因子补充，详见阶段审核设计。"""

from datetime import date
import math
from finance_tools.validation import number, rate, sequence, finite_output


def cashflow(operation, cashflows=None, interest_rate=None, periods=None,
             payment=None, present_value=None, future_value=0.0, when="end",
             finance_rate=None, reinvest_rate=None):
    """期末现金流；NPV 第一个元素为 t=0；年金付款按流入正、流出负。"""
    import numpy_financial as nf
    if operation in ("npv", "irr", "mirr"):
        values = sequence(cashflows, "cashflows")
        if operation == "npv":
            result = nf.npv(rate(interest_rate, "interest_rate"), values)
        else:
            if not min(values) < 0 < max(values):
                raise ValueError("IRR/MIRR 需要现金流同时有正负值")
            changes = sum(a * b < 0 for a, b in zip([x for x in values if x], [x for x in values if x][1:]))
            if operation == "irr" and changes != 1:
                raise ValueError("非传统现金流可能多根，禁止输出默认单一 IRR")
            result = nf.irr(values) if operation == "irr" else nf.mirr(
                values, rate(finance_rate, "finance_rate"), rate(reinvest_rate, "reinvest_rate"))
    elif operation in ("pv", "fv", "pmt"):
        r = rate(interest_rate, "interest_rate")
        n = number(periods, "periods", positive=True)
        if when not in ("begin", "end"):
            raise ValueError("when 必须为 begin 或 end")
        fv = number(future_value, "future_value")
        if abs(r) < 1e-4:
            # 开源库的 ((1+r)**n-1)/r 在近零利率下存在消减误差。
            # 保留真实非零利率，用 log1p/expm1 稳定计算，不将利率截成零。
            # 分界处直接相减的误差量级约 eps/|r|；此阈值为数值策略而非金融阈值。
            try:
                log_growth = n * math.log1p(r)
                growth = math.exp(log_growth)
                factor = n if r == 0 else math.expm1(log_growth) / r
                factor *= 1 + (r if when == "begin" else 0)
                if operation == "pv":
                    result = -(fv + number(payment, "payment") * factor) / growth
                elif operation == "fv":
                    result = -(number(present_value, "present_value") * growth
                               + number(payment, "payment") * factor)
                else:
                    result = -(fv + number(present_value, "present_value") * growth) / factor
            except (OverflowError, ZeroDivisionError) as exc:
                raise ValueError("年金参数超出可表示数值范围") from exc
        elif operation == "pv":
            result = nf.pv(r, n, number(payment, "payment"), fv, when=when)
        elif operation == "fv":
            result = nf.fv(r, n, number(payment, "payment"), number(present_value, "present_value"), when=when)
        else:
            result = nf.pmt(r, n, number(present_value, "present_value"), fv, when=when)
    else:
        raise ValueError("不支持的现金流工具")
    return finite_output({"value": float(result)})


def dated_cashflow(operation, dates, amounts, interest_rate=None, day_count="ACT/365F"):
    """严格递增 ISO 日期和显式日计数；多符号变化阻断默认 XIRR 根。"""
    import pyxirr
    values = sequence(amounts, "amounts")
    if not isinstance(dates, list) or len(dates) != len(values):
        raise ValueError("日期和金额需逐项配对")
    parsed = [date.fromisoformat(x) for x in dates]
    if len(parsed) < 2 or any(a >= b for a, b in zip(parsed, parsed[1:])):
        raise ValueError("至少两个日期，且必须严格递增")
    convention = pyxirr.DayCount.of(day_count)
    if operation == "xnpv":
        result = pyxirr.xnpv(rate(interest_rate, "interest_rate"), parsed, values, day_count=convention)
    elif operation == "xirr":
        if not pyxirr.is_conventional_cash_flow(values):
            raise ValueError("XIRR 仅接受传统现金流，非传统现金流需另行分析多根")
        result = pyxirr.xirr(parsed, values, day_count=convention)
    else:
        raise ValueError("operation 必须为 xnpv 或 xirr")
    if result is None:
        raise ValueError("没有找到可用现金流解")
    return finite_output({"value": float(result)})


def financial_ratio(operation, numerator, denominator):
    """ROE 使用普通股净利润/平均普通股权益；分母需为正且已统一单位。"""
    from financetoolkit.ratios import profitability_model as pm, valuation_model as vm, liquidity_model as lm
    a = number(numerator, "numerator")
    b = number(denominator, "denominator", positive=True)
    functions = {"roe": pm.get_return_on_equity, "roa": pm.get_return_on_assets,
                 "operating_margin": pm.get_operating_margin,
                 "gross_margin": pm.get_gross_margin, "net_margin": pm.get_net_profit_margin,
                 "pe": vm.get_price_to_earnings_ratio, "pb": vm.get_price_to_book_ratio,
                 "ev_ebitda": vm.get_ev_to_ebitda_ratio, "current_ratio": lm.get_current_ratio}
    if operation not in functions:
        raise ValueError("不支持的财务比率")
    # 开源毛利率接口接收收入和成本，其他接口接收利润与分母。
    if operation == "gross_margin":
        result = functions[operation](b, b - a)
    elif operation == "ev_ebitda":
        # 库以 operating_income+D&A 为分母，直接映射已核实 EBITDA 为前项，后项为零。
        result = functions[operation](a, b, 0.0)
    else:
        result = functions[operation](a, b)
    return finite_output({"value": float(result)})


def wacc(market_equity, market_debt, risk_free_rate, beta, market_return,
         cost_of_debt, tax_rate):
    """权重采用市场价值；显式提供前瞻税前债务成本，不混用账面利息比率。"""
    import pandas as pd
    from financetoolkit.models import wacc_model
    equity = number(market_equity, "market_equity", positive=True)
    debt = number(market_debt, "market_debt", positive=True)
    tax = number(tax_rate, "tax_rate")
    if not 0 <= tax <= 1:
        raise ValueError("tax_rate 必须在 [0,1] 内")
    debt_cost = rate(cost_of_debt, "cost_of_debt")
    if debt_cost < 0:
        raise ValueError("债务成本不能为负")
    # 底层库用 interest/debt 求债务成本；构造等价输入保持指定的前瞻债务成本。
    def scalar(value):
        return pd.Series([value], index=["input"])
    result = wacc_model.get_weighted_average_cost_of_capital(
        share_price=scalar(equity), total_shares_outstanding=scalar(1.0),
        interest_expense=scalar(debt_cost * debt), total_debt=scalar(debt),
        risk_free_rate=scalar(rate(risk_free_rate, "risk_free_rate")),
        beta=scalar(number(beta, "beta")), benchmark_returns=scalar(rate(market_return, "market_return")),
        income_tax_expense=scalar(tax), income_before_tax=scalar(1.0))
    return finite_output({"value": float(result.loc["Weighted Average Cost of Capital"].iloc[0])})


def fixed_dcf(cash_flow, growth_rate, discount_rate, terminal_growth, cash, debt, shares, years):
    """固定增长 FCFF DCF 直接使用 FinanceToolkit，不用于 FCFE 或负终期现金流。"""
    from financetoolkit.models import intrinsic_model
    cf = number(cash_flow, "cash_flow", positive=True)
    growth = rate(growth_rate, "growth_rate")
    discount = rate(discount_rate, "discount_rate", discount=True)
    terminal = rate(terminal_growth, "terminal_growth")
    if terminal >= discount:
        raise ValueError("永续增长必须小于折现率")
    if isinstance(years, bool) or not isinstance(years, int) or not 1 <= years <= 100:
        raise ValueError("years 必须为 1–100 的整数")
    result = intrinsic_model.get_intrinsic_value(cf, growth, terminal, discount,
        number(cash, "cash", nonnegative=True), number(debt, "debt", nonnegative=True),
        number(shares, "shares", positive=True), years)
    return finite_output({"enterprise_value": float(result.loc["Enterprise Value"].iloc[0]),
                          "equity_value": float(result.loc["Equity Value"].iloc[0]),
                          "value_per_share": float(result.loc["Intrinsic Value"].iloc[0])})


def performance(returns, dates, periods_per_year, risk_free_rate):
    """只接收本地简单收益率，年化无风险利率；不接受 ticker 或自动下载。"""
    import pandas as pd
    from quantstats import stats
    values = sequence(returns, "returns")
    if len(values) < 3 or any(not -1 < x <= 1 for x in values):
        raise ValueError("至少三期简单收益率，支持范围为 (-1,1]；更大收益需专用输入适配")
    if not isinstance(dates, list) or len(dates) != len(values):
        raise ValueError("收益日期需逐项配对")
    parsed = [date.fromisoformat(x) for x in dates]
    if any(a >= b for a, b in zip(parsed, parsed[1:])):
        raise ValueError("收益日期必须严格递增")
    if isinstance(periods_per_year, bool) or not isinstance(periods_per_year, int) or periods_per_year <= 0:
        raise ValueError("periods_per_year 必须为正整数")
    rf = rate(risk_free_rate, "risk_free_rate")
    series = pd.Series(values, index=pd.to_datetime(parsed), dtype=float)
    result = {"sharpe": float(stats.sharpe(series, rf=rf, periods=periods_per_year)),
              "volatility": float(stats.volatility(series, periods=periods_per_year)),
              "sortino": float(stats.sortino(series, rf=rf, periods=periods_per_year)),
              "max_drawdown": float(stats.max_drawdown(series)),
              "cagr": float(stats.cagr(series, periods=periods_per_year))}
    return finite_output(result)
