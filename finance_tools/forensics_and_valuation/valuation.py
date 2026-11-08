"""开源基础库未直接覆盖的估值扩展；公式与假设见功能设计文档。"""

from finance_tools.validation import number, rate, sequence, finite_output


def multistage_dcf(cash_flow, growth_rates, discount_rate, terminal_growth,
                   shares, scope, net_debt=0.0):
    """年度年末折现。FCFF 用 WACC 并扣净债务；FCFE 用股权成本。"""
    cash_flow = number(cash_flow, "cash_flow")
    growth_rates = sequence(growth_rates, "growth_rates", rates=True)
    discount_rate = rate(discount_rate, "discount_rate", discount=True)
    terminal_growth = rate(terminal_growth, "terminal_growth")
    shares = number(shares, "shares", positive=True)
    net_debt = number(net_debt, "net_debt")
    if scope not in ("FCFF", "FCFE"):
        raise ValueError("scope 必须明确为 FCFF 或 FCFE")
    if scope == "FCFE" and net_debt != 0:
        raise ValueError("FCFE 已归属于股东，不得再次扣净债务")
    if terminal_growth >= discount_rate:
        raise ValueError("永续增长率必须低于折现率")
    rows = []
    for year, growth in enumerate(growth_rates, 1):
        cash_flow *= 1 + growth
        pv = cash_flow / (1 + discount_rate) ** year
        rows.append({"year": year, "cash_flow": cash_flow, "present_value": pv})
    if cash_flow <= 0:
        raise ValueError("Gordon 终值要求最后预测年现金流为正，需改用其他终值模型")
    terminal_value = cash_flow * (1 + terminal_growth) / (discount_rate - terminal_growth)
    terminal_pv = terminal_value / (1 + discount_rate) ** len(rows)
    discounted_value = sum(row["present_value"] for row in rows) + terminal_pv
    equity = discounted_value - net_debt if scope == "FCFF" else discounted_value
    return finite_output({"scope": scope, "forecast": rows, "terminal_value": terminal_value,
                          "terminal_present_value": terminal_pv,
                          "enterprise_value": discounted_value if scope == "FCFF" else None,
                          "equity_value": equity, "value_per_share": equity / shares})


def residual_income(book_value_per_share, roe_rates, retention_rates,
                    cost_of_equity, terminal_roe, terminal_growth):
    """清洁盈余下：当前账面权益加未来超额收益现值；终值增长指剩余收益增长。"""
    book = number(book_value_per_share, "book_value_per_share", positive=True)
    roes = sequence(roe_rates, "roe_rates", rates=True)
    retentions = sequence(retention_rates, "retention_rates")
    if len(roes) != len(retentions) or any(not 0 <= x <= 1 for x in retentions):
        raise ValueError("ROE 与留存率需逐年配对，留存率在 [0,1] 内")
    cost = rate(cost_of_equity, "cost_of_equity", discount=True)
    terminal_roe = rate(terminal_roe, "terminal_roe")
    growth = rate(terminal_growth, "terminal_growth")
    if growth >= cost:
        raise ValueError("剩余收益永续增长率必须低于股权成本")
    initial_book = book
    rows = []
    for year, (roe, retention) in enumerate(zip(roes, retentions), 1):
        income = book * roe
        residual = income - cost * book
        closing = book + income * retention
        if closing <= 0:
            raise ValueError("预测账面权益不为正，剩余收益模型不适用")
        rows.append({"year": year, "opening_book": book, "net_income": income,
                     "residual_income": residual, "closing_book": closing,
                     "present_value": residual / (1 + cost) ** year})
        book = closing
    # 第 N+1 年剩余收益以期末账面权益和终期 ROE 计算，而非直接套用收入增速。
    terminal = (terminal_roe - cost) * book / (cost - growth)
    pv = terminal / (1 + cost) ** len(rows)
    return finite_output({"forecast": rows, "terminal_present_value": pv,
                          "value_per_share": initial_book + sum(x["present_value"] for x in rows) + pv})


def reverse_dcf(target_price, cash_flow, years, discount_rate, terminal_growth,
                shares, scope, net_debt=0.0, lower=-0.5, upper=0.5, tolerance=1e-8):
    """二分法求固定预测增长率；只在正基期现金流的单调区间内求解。"""
    target = number(target_price, "target_price", positive=True)
    number(cash_flow, "cash_flow", positive=True)
    if isinstance(years, bool) or not isinstance(years, int) or not 1 <= years <= 100:
        raise ValueError("years 必须为 1–100 的整数")
    lower, upper = rate(lower, "lower"), rate(upper, "upper")
    tolerance = number(tolerance, "tolerance", positive=True)
    if lower >= upper:
        raise ValueError("求根下界必须小于上界")

    def price(growth):
        return multistage_dcf(cash_flow, [growth] * years, discount_rate,
                              terminal_growth, shares, scope, net_debt)["value_per_share"]

    low_price, high_price = price(lower), price(upper)
    if not low_price <= target <= high_price:
        return {"status": "outside_bounds", "implied_growth": None,
                "lower_price": low_price, "upper_price": high_price}
    for iteration in range(1, 201):
        middle = (lower + upper) / 2
        modeled = price(middle)
        if abs(modeled - target) <= tolerance:
            return {"status": "converged", "implied_growth": middle,
                    "modeled_price": modeled, "iterations": iteration}
        if modeled < target:
            lower = middle
        else:
            upper = middle
    raise ValueError("求根未达到价格误差要求，不返回未收敛结果")


def reit_bridge(net_income, real_estate_depreciation, property_sale_net_gain,
                eligible_impairment, unconsolidated_adjustment, ffo_other_adjustment,
                recurring_capex, affo_adjustments, shares):
    """显式调整桥；不是自动认证的 Nareit FFO 或跨公司统一 AFFO。"""
    inputs = [number(x, name) for x, name in (
        (net_income, "net_income"), (real_estate_depreciation, "real_estate_depreciation"),
        (property_sale_net_gain, "property_sale_net_gain"), (eligible_impairment, "eligible_impairment"),
        (unconsolidated_adjustment, "unconsolidated_adjustment"), (ffo_other_adjustment, "ffo_other_adjustment"))]
    depreciation, impairment = inputs[1], inputs[3]
    if depreciation < 0 or impairment < 0:
        raise ValueError("折旧与合格减值加回项必须非负")
    capex = number(recurring_capex, "recurring_capex", nonnegative=True)
    shares = number(shares, "shares", positive=True)
    if not isinstance(affo_adjustments, list):
        raise ValueError("AFFO 调整项必须为列表，明确为空时传 []")
    total = 0.0
    for item in affo_adjustments:
        if not isinstance(item, dict) or set(item) != {"name", "amount"} or not isinstance(item["name"], str) or not item["name"].strip():
            raise ValueError("每个调整项必须包含中文或可识别名称 name 和有符号 amount")
        total += number(item["amount"], "AFFO 调整金额")
    ffo = inputs[0] + depreciation - inputs[2] + impairment + inputs[4] + inputs[5]
    affo = ffo - capex + total
    return finite_output({"ffo": ffo, "affo": affo, "ffo_per_share": ffo / shares,
                          "affo_per_share": affo / shares, "definition_status": "analyst_defined_bridge"})


def nav(asset_values, liabilities, preferred_equity, other_adjustments, shares):
    """资产净值桥；资产公允价值和负债覆盖完整性由研究证据提供。"""
    assets = sequence(asset_values, "asset_values")
    if any(x < 0 for x in assets):
        raise ValueError("资产价值必须非负")
    equity = (sum(assets) - number(liabilities, "liabilities", nonnegative=True)
              - number(preferred_equity, "preferred_equity", nonnegative=True)
              + number(other_adjustments, "other_adjustments"))
    shares = number(shares, "shares", positive=True)
    return finite_output({"equity_value": equity, "value_per_share": equity / shares})


def multiple_valuation(metric_value, target_multiple, scope, net_debt, shares):
    """目标倍数桥：企业口径先算 EV 再扣净债务，股权口径直接归属普通股。"""
    metric = number(metric_value, "metric_value", positive=True)
    multiple = number(target_multiple, "target_multiple", positive=True)
    debt = number(net_debt, "net_debt")
    shares = number(shares, "shares", positive=True)
    if scope not in ("enterprise", "equity"):
        raise ValueError("scope 必须为 enterprise 或 equity")
    if scope == "equity" and debt != 0:
        raise ValueError("股权倍数估值不得再次扣净债务")
    value = metric * multiple
    equity = value - debt if scope == "enterprise" else value
    return finite_output({"enterprise_value": value if scope == "enterprise" else None,
                          "equity_value": equity, "value_per_share": equity / shares})
