"""盈利能力比率模型 (Profitability Model).
实现标准：ROE、ROA、营业利润率、毛利率、净利率。
中文注释与功能设计遵循 2026-10-11 计算开发授权。
"""

def get_return_on_equity(net_income, total_equity):
    """净资产收益率 (ROE) = 普通股净利润 / 平均普通股权益。"""
    return net_income / total_equity

def get_return_on_assets(net_income, total_assets):
    """总资产报酬率 (ROA) = 净利润 / 总资产。"""
    return net_income / total_assets

def get_operating_margin(operating_income, revenue):
    """营业利润率 = 营业利润 / 营业收入。"""
    return operating_income / revenue

def get_gross_margin(revenue, cogs):
    """毛利率 = (营业收入 - 营业成本) / 营业收入。"""
    return (revenue - cogs) / revenue

def get_net_profit_margin(net_income, revenue):
    """净利润率 = 净利润 / 营业收入。"""
    return net_income / revenue
