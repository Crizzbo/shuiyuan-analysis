# -*- coding: utf-8 -*-
"""冷热数据分层生命周期管理器门面 (finance_tools/governance_and_pipeline/data_lifecycle_manager.py).

严格遵循四层单向依赖铁律：
本模块仅作为工具层对底层纯净算法引擎 financial_core.engines.data_lifecycle_engine 的单向中继导出，
实现单一事实来源 (SSOT) 与零逻辑重复。
"""

from financial_core.engines.data_lifecycle_engine import (
    DataTier,
    TIER_METADATA_REGISTRY,
    LifecyclePolicyConfig,
    TieredFilingSplitResult,
    CompactionReport,
    RestoreVerificationResult,
    DataLeakCheckResult,
    DataLifecycleEngine,
)

__all__ = [
    "DataTier",
    "TIER_METADATA_REGISTRY",
    "LifecyclePolicyConfig",
    "TieredFilingSplitResult",
    "CompactionReport",
    "RestoreVerificationResult",
    "DataLeakCheckResult",
    "DataLifecycleEngine",
]
