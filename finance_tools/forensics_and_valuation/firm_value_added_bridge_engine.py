"""向下兼容重导出层：中观行业至微观企业增加值映射桥梁 (Firm Value Added Bridge Engine Compatibility Layer).

本模块由 financial_core.engines.firm_value_added_bridge_engine 承接真实实现。
"""

from financial_core.engines.firm_value_added_bridge_engine import (
    FirmFinancialFact,
    FirmValueAddedBridgeEngine,
)

__all__ = [
    "FirmFinancialFact",
    "FirmValueAddedBridgeEngine",
]
