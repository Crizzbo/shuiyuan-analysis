"""偿债能力比率模型 (Solvency Model).
实现标准：资产负债率 (Debt to Assets Ratio)。
中文注释与功能设计遵循 2026-10-11 计算开发授权。
"""


def get_debt_to_assets_ratio(total_debt, total_assets):
    """总负债占资产比率 = 总负债 / 总资产。"""
    return total_debt / total_assets
