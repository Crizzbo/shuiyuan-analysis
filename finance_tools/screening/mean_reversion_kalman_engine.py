# -*- coding: utf-8 -*-
"""震荡市高抛低吸副武器：均值回归与卡尔曼动态状态估计引擎 (向下兼容中继门面).

实现托管于底层纯净核心: `financial_core.engines.mean_reversion_kalman_engine`
遵循单一事实来源 (SSOT) 规范。
"""

from financial_core.engines.mean_reversion_kalman_engine import (
    OUProcessResult,
    KalmanFilterResult,
    MeanReversionVerdict,
    MeanReversionKalmanEngine,
)

__all__ = [
    "OUProcessResult",
    "KalmanFilterResult",
    "MeanReversionVerdict",
    "MeanReversionKalmanEngine",
]
