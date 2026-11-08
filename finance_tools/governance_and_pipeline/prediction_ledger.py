"""向下兼容重导出层：不可篡改预测与复盘账本 (Prediction Ledger Compatibility Layer).

本模块由 financial_core.engines.prediction_ledger 承接真实实现。
"""

from financial_core.engines.prediction_ledger import (
    PredictionLedger,
    GENESIS_HASH,
)

__all__ = ["PredictionLedger", "GENESIS_HASH"]
