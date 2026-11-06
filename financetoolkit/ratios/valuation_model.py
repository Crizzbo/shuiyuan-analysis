"""估值乘数模型 (Valuation Model).
实现标准：市盈率 (P/E)、市净率 (P/B)、企业价值倍数 (EV/EBITDA)。
中文注释与功能设计遵循 2026-10-11 计算开发授权。
"""

def get_price_to_earnings_ratio(price, earnings):
    """市盈率 (P/E) = 每股市价 / 每股收益。"""
    return price / earnings

def get_price_to_book_ratio(price, book_value):
    """市净率 (P/B) = 每股市价 / 每股账面净资产。"""
    return price / book_value

def get_ev_to_ebitda_ratio(ev, ebitda, zero=0.0):
    """企业价值倍数 (EV/EBITDA) = 企业价值 / 息税折旧摊销前利润。"""
    return ev / (ebitda + zero)
