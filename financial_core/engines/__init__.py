"""金融分析算法与模型引擎层 (Financial Analysis Model & Algorithmic Engines).

聚合底层专业量化算法，包括法证五刀穿透、商业品质与所有者收益、情景DCF、期权二叉树、宏观压力测试等。
"""

from .forensic_surgical_scalpel import (
    ForensicSurgicalScalpel,
    ForensicInputData,
    ForensicDissectionResult,
)
from .business_quality_and_moat_engine import (
    BusinessQualityAndMoatEngine,
    OwnerEarningsInput,
    LiquorConsumerFleshInput,
    TechHardwareFleshInput,
)
from .american_option_tree_engine import (
    AmericanOptionTreeEngine,
    AmericanOptionTreeInput,
)
from .macro_shock_transmission_engine import (
    MacroShockTransmissionEngine,
    MacroShockInput,
)
from .price_shock_attribution_engine import (
    PriceShockAttributionEngine,
    GuidanceTerminalImpact,
    OperatingLeverageImpact,
    DilutionOverhangImpact,
    DealerGammaDragImpact,
)
from .integrated_three_statement_engine import (
    IntegratedThreeStatementEngine,
    BaselineFinancials,
)
from .unit_economics_engine import (
    UnitEconomicsEngine,
    PipelineAsset,
)
from .consensus_surprise_engine import (
    ConsensusSurpriseEngine,
    ConsensusDataInput,
)
from .microstructure_flow_engine import (
    MicrostructureFlowEngine,
    MicrostructureInput,
)
from .catalyst_calendar_engine import (
    CatalystCalendarEngine,
    CorporateEvent,
)
from .peer_benchmark_engine import (
    PeerBenchmarkEngine,
    CompanyPeerMetrics,
    PeerBenchmarkResult,
)
from .options_causal_analyzer import (
    OptionsCausalAnalyzer,
    OptionContractInput,
    UnderlyingScenarios,
)
from .filing_mapper import (
    OfficialFilingMapper,
    BalanceSheetIdentityError,
    IncompleteFilingFactError,
)
from .credit_risk_engine import (
    CreditRiskAndSolvencyEngine,
    MertonCreditInput,
    CreditRiskResult,
)
from .monte_carlo_engine import (
    MonteCarloValuationEngine,
    MonteCarloDCFInput,
    MonteCarloValuationResult,
    DensityBin,
)
from .cross_asset_engine import (
    CrossAssetValuationEngine,
    ETFOverlapResult,
    ETFPenetrationFact,
    GoldValuationFact,
    GoldMinerLeverageFact,
)
from .portfolio_risk_engine import (
    PortfolioRiskAndVaREngine,
    VaRResult,
    RiskDecompositionResult,
    FactorAttributionResult,
    StressTestScenarioResult,
)
from .volatility_surface_engine import (
    VolatilitySurfaceGreeksEngine,
    OptionGreeksResult,
    PutCallParityCheckResult,
    VolatilitySkewResult,
)
from .mid_cycle_engine import (
    MidCycleNormalizationEngine,
    MidCycleFCFResult,
    ShillerCAPEResult,
    CyclePhaseResult,
    MidCycleValuationResult,
)
from .retrospective_review_engine import (
    RetrospectiveReviewEngine,
    HistoricalPredictionSnapshot,
    ActualMarketOutcome,
)
from .black_swan_deep_analyzer import (
    BlackSwanDeepAnalyzer,
    HoldingAssetSpec,
    BlackSwanAnalysisResult,
)
from .macro_shock_transmission_engine import (
    MacroRegimeState,
    AssetMicroVulnerabilityType,
    LeverageVulnerabilityTier,
    MACRO_SHOCK_STATE_REGISTRY,
    get_macro_state_metadata,
)
from .prediction_ledger import (
    PredictionLedger,
    GENESIS_HASH,
)
from .quote_freshness_gateway import (
    QuoteFreshnessGateway,
    QuoteVerificationResult,
)
from .woodford_forward_guidance_engine import (
    WoodfordForwardGuidanceEngine,
    WoodfordGuidanceInput,
    WoodfordGuidanceResult,
)
from .hall_discount_friction_engine import (
    HallDiscountFrictionEngine,
    HallFrictionInput,
    HallFrictionResult,
)
from .acemoglu_institutional_risk_engine import (
    AcemogluInstitutionalRiskEngine,
    AcemogluInstitutionalInput,
    AcemogluInstitutionalResult,
)
from .aghion_creative_destruction_engine import (
    AghionCreativeDestructionEngine,
    AghionDestructionInput,
    AghionDestructionResult,
)
from .micro_founded_macro_engine import (
    MicroFoundedMacroEngine,
    MicroFoundedMacroInput,
    MicroFoundedMacroCompositeResult,
)
from .world_production_aggregate_engine import (
    WorldProductionAggregateEngine,
    WorldProductionState,
)
from .global_input_output_engine import (
    GlobalInputOutputEngine,
    SectorProfile,
)
from .firm_value_added_bridge_engine import (
    FirmValueAddedBridgeEngine,
    FirmFinancialFact,
)
from .factor_income_distribution_engine import (
    FactorIncomeDistributionEngine,
    HouseholdSectorState,
)
from .world_financial_equilibrium_engine import (
    WorldFinancialEquilibriumEngine,
)
from .inter_country_trade_engine import (
    InterCountryTradeEngine,
    RegionTradeProfile,
)
from .market_adaptive_params import (
    MarketAdaptiveParamsRegistry,
    GoldValuationAdaptiveParams,
    MacroShockAdaptiveParams,
    FirmValueAddedAdaptiveParams,
    SepaAdaptiveParams,
)
from .sepa_buy_signal_engine import (
    SepaBuySignalEngine,
    SepaInputFacts,
    SepaPriceBoundaries,
    SepaBuySignalResult,
    TrendStageState,
    VcpContractionStatus,
    BuySignalTier,
    SEPA_SIGNAL_STATE_REGISTRY,
    get_sepa_state_metadata,
)
from .causal_inference_engine import (
    QuantitativeCausalInferenceEngine,
    CausalInferenceResult,
)
from .industry_taxonomy_bridge import (
    IndustryTaxonomyBridge,
    IndustryMappingRecord,
)
from .industry_price_shock_bridge import (
    IndustryPriceShockBridge,
    IndustryPriceShockResult,
)
from .industry_causal_registry import (
    IndustryCausalStrategyRegistry,
    IndustryCausalFacts,
)
from .sec_edgar_collector import (
    OfficialSecEdgarCollector,
    SecExtractedFinancialFacts,
)
from .tiered_universe_manager import (
    TieredUniverseManager,
    UniverseCompanyRecord,
    TieredUniverseStats,
)
from .normalized_reconciliation_engine import (
    NormalizedReconciliationEngine,
    NormalizedReconciliationStateManager,
    ReconciliationProcessLock,
    ReconciliationRecord,
    ProcessLockError,
)
from .knowledge_repository import (
    KnowledgeRepository,
    BusinessModelProfile,
    MetricCatalogProfile,
    IndustryNodeProfile,
    IndustryRuleProfile,
    IndustryKnowledgeProfile,
)
from .knowledge_graph_engine import KnowledgeGraphEngine
from .financial_statement_facade import (
    FinancialStatementFacade,
    NormalizedFinancialProfile,
)

__all__ = [
    "FinancialStatementFacade",
    "NormalizedFinancialProfile",
    "KnowledgeGraphEngine",
    "KnowledgeRepository",
    "BusinessModelProfile",
    "MetricCatalogProfile",
    "IndustryNodeProfile",
    "IndustryRuleProfile",
    "IndustryKnowledgeProfile",
    "QuoteFreshnessGateway",
    "QuoteVerificationResult",
    "PredictionLedger",
    "GENESIS_HASH",
    "RetrospectiveReviewEngine",
    "HistoricalPredictionSnapshot",
    "ActualMarketOutcome",
    "MidCycleNormalizationEngine",
    "MidCycleFCFResult",
    "ShillerCAPEResult",
    "CyclePhaseResult",
    "MidCycleValuationResult",
    "PortfolioRiskAndVaREngine",
    "VaRResult",
    "RiskDecompositionResult",
    "FactorAttributionResult",
    "StressTestScenarioResult",
    "VolatilitySurfaceGreeksEngine",
    "OptionGreeksResult",
    "PutCallParityCheckResult",
    "VolatilitySkewResult",
    "CreditRiskAndSolvencyEngine",
    "MertonCreditInput",
    "CreditRiskResult",
    "MonteCarloValuationEngine",
    "MonteCarloDCFInput",
    "MonteCarloValuationResult",
    "DensityBin",
    "CrossAssetValuationEngine",
    "ETFOverlapResult",
    "ETFPenetrationFact",
    "GoldValuationFact",
    "GoldMinerLeverageFact",
    "OfficialFilingMapper",
    "BalanceSheetIdentityError",
    "ForensicSurgicalScalpel",
    "ForensicInputData",
    "ForensicDissectionResult",
    "BusinessQualityAndMoatEngine",
    "OwnerEarningsInput",
    "LiquorConsumerFleshInput",
    "TechHardwareFleshInput",
    "AmericanOptionTreeEngine",
    "AmericanOptionTreeInput",
    "MacroShockTransmissionEngine",
    "MacroShockInput",
    "PriceShockAttributionEngine",
    "GuidanceTerminalImpact",
    "OperatingLeverageImpact",
    "DilutionOverhangImpact",
    "DealerGammaDragImpact",
    "IntegratedThreeStatementEngine",
    "BaselineFinancials",
    "UnitEconomicsEngine",
    "PipelineAsset",
    "ConsensusSurpriseEngine",
    "ConsensusDataInput",
    "MicrostructureFlowEngine",
    "MicrostructureInput",
    "CatalystCalendarEngine",
    "CorporateEvent",
    "PeerBenchmarkEngine",
    "CompanyPeerMetrics",
    "PeerBenchmarkResult",
    "OptionsCausalAnalyzer",
    "OptionContractInput",
    "UnderlyingScenarios",
    "WoodfordForwardGuidanceEngine",
    "WoodfordGuidanceInput",
    "WoodfordGuidanceResult",
    "HallDiscountFrictionEngine",
    "HallFrictionInput",
    "HallFrictionResult",
    "AcemogluInstitutionalRiskEngine",
    "AcemogluInstitutionalInput",
    "AcemogluInstitutionalResult",
    "AghionCreativeDestructionEngine",
    "AghionDestructionInput",
    "AghionDestructionResult",
    "MicroFoundedMacroEngine",
    "MicroFoundedMacroInput",
    "MicroFoundedMacroCompositeResult",
    "WorldProductionAggregateEngine",
    "WorldProductionState",
    "GlobalInputOutputEngine",
    "SectorProfile",
    "FirmValueAddedBridgeEngine",
    "FirmFinancialFact",
    "FactorIncomeDistributionEngine",
    "HouseholdSectorState",
    "WorldFinancialEquilibriumEngine",
    "InterCountryTradeEngine",
    "RegionTradeProfile",
    "MarketAdaptiveParamsRegistry",
    "GoldValuationAdaptiveParams",
    "MacroShockAdaptiveParams",
    "FirmValueAddedAdaptiveParams",
    "QuantitativeCausalInferenceEngine",
    "CausalInferenceResult",
    "IndustryTaxonomyBridge",
    "IndustryMappingRecord",
    "IndustryPriceShockBridge",
    "IndustryPriceShockResult",
    "IndustryCausalStrategyRegistry",
    "IndustryCausalFacts",
    "OfficialSecEdgarCollector",
    "SecExtractedFinancialFacts",
    "TieredUniverseManager",
    "UniverseCompanyRecord",
    "TieredUniverseStats",
    "NormalizedReconciliationEngine",
    "NormalizedReconciliationStateManager",
    "ReconciliationProcessLock",
    "ReconciliationRecord",
    "ProcessLockError",
    "SepaBuySignalEngine",
    "SepaInputFacts",
    "SepaPriceBoundaries",
    "SepaBuySignalResult",
    "TrendStageState",
    "VcpContractionStatus",
    "BuySignalTier",
    "SEPA_SIGNAL_STATE_REGISTRY",
    "SepaAdaptiveParams",
]
