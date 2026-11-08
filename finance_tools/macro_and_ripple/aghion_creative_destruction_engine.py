"""向下兼容重导出层：阿吉翁创造性破坏与技术前沿引擎 (Aghion Creative Destruction Engine Compatibility Layer).

本模块由 financial_core.engines.aghion_creative_destruction_engine 承接真实实现。
"""

from financial_core.engines.aghion_creative_destruction_engine import (
    AghionDestructionInput,
    AghionDestructionResult,
    AghionCreativeDestructionEngine,
)

__all__ = [
    "AghionDestructionInput",
    "AghionDestructionResult",
    "AghionCreativeDestructionEngine",
]
