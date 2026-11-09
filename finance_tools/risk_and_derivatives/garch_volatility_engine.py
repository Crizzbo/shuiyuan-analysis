# -*- coding: utf-8 -*-
"""动态波动率引擎：GARCH(1,1) 条件异方差与前瞻预测 (向下兼容中继门面).

实现托管于底层纯净核心: `financial_core.engines.garch_volatility_engine`
遵循单一事实来源 (SSOT) 规范。
"""

from financial_core.engines.garch_volatility_engine import (
    GARCHModelResult,
    VolatilityForecastResult,
    GARCHVolatilityVerdict,
    GARCHVolatilityEngine,
)

__all__ = [
    "GARCHModelResult",
    "VolatilityForecastResult",
    "GARCHVolatilityVerdict",
    "GARCHVolatilityEngine",
]
