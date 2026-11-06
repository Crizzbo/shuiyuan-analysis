"""向下兼容重导出层：霍尔微观成本摩擦与加成率引擎 (Hall Discount Friction Engine Compatibility Layer).

本模块由 financial_core.engines.hall_discount_friction_engine 承接真实实现。
"""

from financial_core.engines.hall_discount_friction_engine import (
    HallFrictionInput,
    HallFrictionResult,
    HallDiscountFrictionEngine,
)

__all__ = [
    "HallFrictionInput",
    "HallFrictionResult",
    "HallDiscountFrictionEngine",
]
