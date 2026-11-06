"""细分行业买方结构化知识中枢管理器 (向下兼容中继门面).

本模块为向下兼容旧版调用路径的中继层，实际实现全部托管于底层纯净核心:
`financial_core.engines.industry_knowledge_manager`

遵循《全栈工程命名架构与状态空间规范》与单一事实来源 (SSOT) 铁律，
杜绝在多处维护重复计算代码与状态判定。
"""

from financial_core.engines.industry_knowledge_manager import (
    IndustryKnowledgeProfile,
    IndustryKnowledgeManager,
)

__all__ = [
    "IndustryKnowledgeProfile",
    "IndustryKnowledgeManager",
]
