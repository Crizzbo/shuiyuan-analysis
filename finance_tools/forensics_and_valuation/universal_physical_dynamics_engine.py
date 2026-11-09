# -*- coding: utf-8 -*-
"""通用商业物理与速度动力学计算引擎 (向下兼容中继门面).

实现托管于底层纯净核心: `financial_core.engines.universal_physical_dynamics_engine`
遵循单一事实来源 (SSOT) 规范与四层架构依赖单向性约束。
"""

from financial_core.engines.universal_physical_dynamics_engine import (
    PriceDynamicsMetrics,
    FundamentalSupplyChainMetrics,
    TerminalValuationDistribution,
    UniversalDynamicsProfile,
    UniversalPhysicalDynamicsEngine,
)

__all__ = [
    "PriceDynamicsMetrics",
    "FundamentalSupplyChainMetrics",
    "TerminalValuationDistribution",
    "UniversalDynamicsProfile",
    "UniversalPhysicalDynamicsEngine",
]
