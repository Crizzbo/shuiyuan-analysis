"""事件雷达与突发舆情因果解析引擎 (Event Radar Facade / Proxy Re-export).

遵循架构解耦与向后兼容原则：
1. 核心实现与配置已彻底抽离至 `financial_core.engines.event_radar` 业务领域子包；
2. 本模块作为顶层透明门面 (Transparent Facade)，保持既有全系统导入的 100% 向后兼容；
3. 严禁在本文件中硬编码任何散落词典或业务规则，统一由 `event_radar/config/` 配置驱动。
"""

from .event_radar import (
    EventCategory,
    EventRadarEngine,
    EventSeverity,
    RawNewsItem,
    SourceCredibilityTier,
    StructuredEventSummary,
    VerificationStatus,
    validate_event_schema,
)

__all__ = [
    "EventCategory",
    "EventRadarEngine",
    "EventSeverity",
    "RawNewsItem",
    "SourceCredibilityTier",
    "StructuredEventSummary",
    "VerificationStatus",
    "validate_event_schema",
]
