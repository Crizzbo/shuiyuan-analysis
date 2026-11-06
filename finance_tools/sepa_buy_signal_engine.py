"""米奈尔维尼 SEPA 买入信号与精准价格时机引擎 (向下兼容中继门面).

本模块为向下兼容调用路径的中继层，实际实现全部托管于底层纯净核心:
`financial_core.engines.sepa_buy_signal_engine`

严格遵循《全栈工程命名架构与状态空间规范》与单一事实来源 (SSOT) 铁律，
杜绝在多处维护重复计算代码与状态判定。
"""

from financial_core.engines.sepa_buy_signal_engine import (
    TrendStageState,
    VcpContractionStatus,
    BuySignalTier,
    SEPA_SIGNAL_STATE_REGISTRY,
    get_sepa_state_metadata,
    SepaPriceBoundaries,
    SepaInputFacts,
    SepaBuySignalResult,
    SepaBuySignalEngine,
)

__all__ = [
    "TrendStageState",
    "VcpContractionStatus",
    "BuySignalTier",
    "SEPA_SIGNAL_STATE_REGISTRY",
    "get_sepa_state_metadata",
    "SepaPriceBoundaries",
    "SepaInputFacts",
    "SepaBuySignalResult",
    "SepaBuySignalEngine",
]
