# -*- coding: utf-8 -*-
"""牛熊状态总阀门引擎 (向下兼容中继门面).

实现托管于底层纯净核心: `financial_core.engines.macro_regime_hmm_valve_engine`
遵循单一事实来源 (SSOT) 规范。
"""

from financial_core.engines.macro_regime_hmm_valve_engine import (
    MarketRegimeState,
    HMMModelResult,
    TrendFilterResult,
    MacroValveDecision,
    MacroRegimeHMMValveEngine,
)

__all__ = [
    "MarketRegimeState",
    "HMMModelResult",
    "TrendFilterResult",
    "MacroValveDecision",
    "MacroRegimeHMMValveEngine",
]
