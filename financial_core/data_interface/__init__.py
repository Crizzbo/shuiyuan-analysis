# -*- coding: utf-8 -*-
"""金融数据接口与特征加工层 (data_interface).

严格遵循《AGENTS.md》与《CLAUDE.md》：
1. 单一事实来源 (SSOT)：系统所有选股、回测、研报与风控流程的统一数据加工中枢；
2. 零逆向依赖：位于 financial_core 内部，纯相对导入，零外层依赖；
3. 对外导出统一门面与强类型数据契约。
"""

from .contracts import (
    StandardBar,
    MarketDataFeatureInput,
    ForensicsAccountingInput,
    CreditStructuralInput,
    LiquidityStressInput,
    OptionSurfaceFlowInput,
    MacroRegimeInput,
    UnifiedFeatureBundle,
)
from .market_adapter import MarketDataAdapter
from .accounting_adapter import FinancialStatementAdapter
from .derivative_adapter import DerivativeFlowAdapter
from .macro_adapter import MacroLiquidityAdapter
from .unified_facade import UnifiedFinancialDataInterfaceFacade

__all__ = [
    "StandardBar",
    "MarketDataFeatureInput",
    "ForensicsAccountingInput",
    "CreditStructuralInput",
    "LiquidityStressInput",
    "OptionSurfaceFlowInput",
    "MacroRegimeInput",
    "UnifiedFeatureBundle",
    "MarketDataAdapter",
    "FinancialStatementAdapter",
    "DerivativeFlowAdapter",
    "MacroLiquidityAdapter",
    "UnifiedFinancialDataInterfaceFacade",
]
