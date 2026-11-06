"""市场一致预期差与业绩超预期量化评估引擎 (向下兼容中继门面).

本模块为向下兼容旧版调用路径的中继层，实际实现全部托管于底层纯净核心:
`financial_core.engines.consensus_surprise_engine`

遵循《全栈工程命名架构与状态空间规范》与单一事实来源 (SSOT) 铁律，
杜绝在多处维护重复计算代码与状态判定。
"""

from financial_core.engines.consensus_surprise_engine import (
    ConsensusDataInput,
    ConsensusSurpriseResult,
    ConsensusSurpriseEngine,
)

__all__ = [
    "ConsensusDataInput",
    "ConsensusSurpriseResult",
    "ConsensusSurpriseEngine",
]
