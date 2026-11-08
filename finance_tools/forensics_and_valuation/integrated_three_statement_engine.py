"""动态三表强勾稽与现金跑道联动引擎 (向下兼容中继门面).

本模块为向下兼容旧版调用路径的中继层，实际实现全部托管于底层纯净核心:
`financial_core.engines.integrated_three_statement_engine`

遵循《全栈工程命名架构与状态空间规范》与单一事实来源 (SSOT) 铁律，
杜绝在多处维护重复计算代码与状态判定。
"""

from financial_core.engines.integrated_three_statement_engine import (
    BaselineFinancials,
    ProjectedYearResult,
    ThreeStatementSimulationResult,
    IntegratedThreeStatementEngine,
)

__all__ = [
    "BaselineFinancials",
    "ProjectedYearResult",
    "ThreeStatementSimulationResult",
    "IntegratedThreeStatementEngine",
]
