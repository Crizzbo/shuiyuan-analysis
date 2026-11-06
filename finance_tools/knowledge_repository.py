"""中继门面: 知识库统一加载与中枢中介 (Knowledge Repository Facade).

物理架构定界 (Layer 2: finance_tools):
- 向下兼容门面，只单向导入 Layer 1: financial_core 核心实现；
- 严禁逆向依赖上层业务脚本。
"""

from financial_core.engines.knowledge_repository import (
    KnowledgeRepository,
    BusinessModelProfile,
    MetricCatalogProfile,
    IndustryNodeProfile,
    IndustryRuleProfile,
    IndustryKnowledgeProfile,
)

__all__ = [
    "KnowledgeRepository",
    "BusinessModelProfile",
    "MetricCatalogProfile",
    "IndustryNodeProfile",
    "IndustryRuleProfile",
    "IndustryKnowledgeProfile",
]
