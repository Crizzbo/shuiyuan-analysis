"""finance_tools - 买方机构级金融量化工具库 (v6.0 分包架构版)。

模块架构已全面按 6 大专业业务领域划分高内聚子包：
  - screening: 全市场选股与价格时机引擎 (SEPA 8大趋势硬指标、VCP 4T、候选排序)
  - forensics_and_valuation: 财务法证审计与多情景估值模型 (法证手术刀、平账、DCF)
  - risk_and_derivatives: 风险管理与衍生品定价引擎 (美式期权二叉树、组合风险、违约)
  - macro_and_ripple: 宏观冲击与产业链涟漪分析器 (宏观传导、SOTP分部穿透、涟漪矩阵)
  - events_and_verification: 突发事件雷达与鉴真监控流水线 (0-Token初筛、SHA-256鉴真)
  - governance_and_pipeline: 数据底账、时效门禁与基础设施 (完备度追踪、时钟门禁)

同时根目录保持 100% 向下兼容门面，既有导入语句 `from finance_tools.xxx import yyy` 零破坏直接可用。
"""

from . import (
    screening,
    forensics_and_valuation,
    risk_and_derivatives,
    macro_and_ripple,
    events_and_verification,
    governance_and_pipeline,
)

VERSION = "1.0.0"

from .options_causal_analyzer import (
    OptionContractInput,
    UnderlyingScenarios,
    OptionAnalysisResult,
    OptionsCausalAnalyzer,
)
from .consensus_surprise_engine import (
    ConsensusDataInput,
    ConsensusSurpriseResult,
    ConsensusSurpriseEngine,
)
from .microstructure_flow_engine import (
    MicrostructureInput,
    MicrostructureResult,
    MicrostructureFlowEngine,
)
from .catalyst_calendar_engine import (
    CorporateEvent,
    EventEvaluationResult,
    CatalystCalendarEngine,
)
from .peer_benchmark_engine import (
    CompanyPeerMetrics,
    PeerBenchmarkResult,
    PeerBenchmarkEngine,
)
from .unit_economics_engine import (
    PipelineAsset,
    BiotechRNPVResult,
    UnitEconomicsEngine,
)
from .integrated_three_statement_engine import (
    BaselineFinancials,
    ProjectedYearResult,
    ThreeStatementSimulationResult,
    IntegratedThreeStatementEngine,
)
from .price_shock_attribution_engine import (
    GuidanceTerminalImpact,
    OperatingLeverageImpact,
    DilutionOverhangImpact,
    SBCFreeCashFlowImpact,
    RiskPremiumWACCImpact,
    DealerGammaDragImpact,
    PriceShockAttributionEngine,
)
from .american_option_tree_engine import (
    AmericanOptionTreeInput,
    AmericanOptionTreeEngine,
)
from .macro_shock_transmission_engine import (
    MacroShockInput,
    MacroShockTransmissionEngine,
)
from .business_quality_and_moat_engine import (
    OwnerEarningsInput,
    LiquorConsumerFleshInput,
    TechHardwareFleshInput,
    BusinessQualityAndMoatEngine,
)
from .forensic_surgical_scalpel import (
    ForensicInputData,
    ForensicDissectionResult,
    ForensicSurgicalScalpel,
)
from .systemic_analysis_pipeline import (
    SystemicCompanyInput,
    SystemicDecisionCard,
    SystemicAnalysisPipeline,
)
from .canyon_linear_pipeline import (
    CanyonStationInput,
    CanyonDecisionCard,
    CanyonLinearPipeline,
    QuoteFreshnessError,
    BalanceSheetInvariantError,
)
from .event_radar_collector import (
    EventRadarCollector,
    NetworkHealthWatchdog,
    RadarProgressManager,
    RadarDatabaseManager,
    MockModelSummarizer,
)
from .sotp_event_analyzer import (
    SotpEventAnalyzer,
)

__all__ = [
    "OptionContractInput",
    "UnderlyingScenarios",
    "OptionAnalysisResult",
    "OptionsCausalAnalyzer",
    "ConsensusDataInput",
    "ConsensusSurpriseResult",
    "ConsensusSurpriseEngine",
    "MicrostructureInput",
    "MicrostructureResult",
    "MicrostructureFlowEngine",
    "CorporateEvent",
    "EventEvaluationResult",
    "CatalystCalendarEngine",
    "CompanyPeerMetrics",
    "PeerBenchmarkResult",
    "PeerBenchmarkEngine",
    "PipelineAsset",
    "BiotechRNPVResult",
    "UnitEconomicsEngine",
    "BaselineFinancials",
    "ProjectedYearResult",
    "ThreeStatementSimulationResult",
    "IntegratedThreeStatementEngine",
    "GuidanceTerminalImpact",
    "OperatingLeverageImpact",
    "DilutionOverhangImpact",
    "SBCFreeCashFlowImpact",
    "RiskPremiumWACCImpact",
    "DealerGammaDragImpact",
    "PriceShockAttributionEngine",
    "AmericanOptionTreeInput",
    "AmericanOptionTreeEngine",
    "MacroShockInput",
    "MacroShockTransmissionEngine",
    "OwnerEarningsInput",
    "LiquorConsumerFleshInput",
    "TechHardwareFleshInput",
    "BusinessQualityAndMoatEngine",
    "ForensicInputData",
    "ForensicDissectionResult",
    "ForensicSurgicalScalpel",
    "SystemicCompanyInput",
    "SystemicDecisionCard",
    "SystemicAnalysisPipeline",
    "CanyonStationInput",
    "CanyonDecisionCard",
    "CanyonLinearPipeline",
    "QuoteFreshnessError",
    "BalanceSheetInvariantError",
    "EventRadarCollector",
    "NetworkHealthWatchdog",
    "RadarProgressManager",
    "RadarDatabaseManager",
    "MockModelSummarizer",
    "SotpEventAnalyzer",
]
