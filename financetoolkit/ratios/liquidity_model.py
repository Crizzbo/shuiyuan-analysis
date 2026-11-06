"""流动性比率模型 (Liquidity Model).
实现标准：流动比率 (Current Ratio)。
中文注释与功能设计遵循 2026-10-11 计算开发授权。
"""

def get_current_ratio(current_assets, current_liabilities):
    """流动比率 = 流动资产 / 流动负债。"""
    return current_assets / current_liabilities
