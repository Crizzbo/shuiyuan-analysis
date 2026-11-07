"""突发微观事件与多业务分部 (SOTP) 穿透引擎 (Facade / Proxy Re-export).

遵循架构解耦与向后兼容原则：
1. 核心实现已划分至 `financial_core.engines.event_radar` 业务领域子包；
2. 本模块作为顶层透明门面 (Transparent Facade)，保持既有全系统导入的 100% 向后兼容。
"""

from .event_radar import (
    BusinessSegment,
    CompanySotpProfile,
    EnterpriseEventImpactResult,
    SegmentCausalImpact,
    SotpEventPenetrationEngine,
)

__all__ = [
    "BusinessSegment",
    "CompanySotpProfile",
    "EnterpriseEventImpactResult",
    "SegmentCausalImpact",
    "SotpEventPenetrationEngine",
]
