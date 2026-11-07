"""事件雷达与突发事件因果解析业务子包 (financial_core.engines.event_radar).

涵盖舆情雷达、微观物理事实提取、多信源鉴真防伪、传闻熔断门禁与 SOTP 业务分部因果穿透。
遵循配置与代码彻底解耦原则，关键词词典统一由内置及外部 JSON 资产驱动。
"""

from .event_radar_engine import (
    EventCategory,
    EventRadarEngine,
    EventSeverity,
    RawNewsItem,
    SourceCredibilityTier,
    StructuredEventSummary,
    VerificationStatus,
    validate_event_schema,
)
from .sotp_event_penetration_engine import (
    BusinessSegment,
    CompanySotpProfile,
    EnterpriseEventImpactResult,
    SegmentCausalImpact,
    SotpEventPenetrationEngine,
)

__all__ = [
    "EventSeverity",
    "EventCategory",
    "SourceCredibilityTier",
    "VerificationStatus",
    "RawNewsItem",
    "StructuredEventSummary",
    "validate_event_schema",
    "EventRadarEngine",
    "BusinessSegment",
    "CompanySotpProfile",
    "SegmentCausalImpact",
    "EnterpriseEventImpactResult",
    "SotpEventPenetrationEngine",
]
