"""金融分析核心系统 (Financial Analysis Core System).

机构级独立金融量化分析、法证审计与估值模型系统，与 Agent / Skill 彻底解耦。
"""

from .contracts import (
    AnalysisMode,
    FinancialAnalysisResult,
    DecisionCardData,
    ForensicFinding,
    ValuationScenario,
    OptionPricingResult,
    MacroStressResult,
)
from .api import FinancialAnalysisSystem
from .engines import (
    UniversalPhysicalDynamicsEngine,
    PriceDynamicsMetrics,
    FundamentalSupplyChainMetrics,
    TerminalValuationDistribution,
    UniversalDynamicsProfile,
)
from .pipeline import (
    CanyonStationInput,
    CanyonDecisionCard,
    CanyonLinearPipeline,
    QuoteFreshnessError,
    BalanceSheetInvariantError,
)

__version__ = "1.0.0"

__all__ = [
    "AnalysisMode",
    "FinancialAnalysisResult",
    "DecisionCardData",
    "ForensicFinding",
    "ValuationScenario",
    "OptionPricingResult",
    "MacroStressResult",
    "FinancialAnalysisSystem",
    "CanyonStationInput",
    "CanyonDecisionCard",
    "CanyonLinearPipeline",
    "QuoteFreshnessError",
    "BalanceSheetInvariantError",
    "UniversalPhysicalDynamicsEngine",
    "PriceDynamicsMetrics",
    "FundamentalSupplyChainMetrics",
    "TerminalValuationDistribution",
    "UniversalDynamicsProfile",
]
