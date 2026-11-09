# -*- coding: utf-8 -*-
"""finance_tools - 买方机构级金融量化工具库 (v6.0 纯净分包架构版).

模块架构全面按 6 大专业业务领域划分高内聚子包：
  - screening: 全市场选股与价格时机引擎 (SEPA 8大趋势硬指标、VCP 4T、候选排序)
  - forensics_and_valuation: 财务法证审计与多情景估值模型 (法证手术刀、平账、DCF)
  - risk_and_derivatives: 风险管理与衍生品定价引擎 (美式期权二叉树、组合风险、违约)
  - macro_and_ripple: 宏观冲击与产业链涟漪分析器 (宏观传导、SOTP分部穿透、涟漪矩阵)
  - events_and_verification: 突发事件雷达与鉴真监控流水线 (0-Token初筛、SHA-256鉴真)
  - governance_and_pipeline: 数据底账、时效门禁与基础设施 (完备度追踪、时钟门禁)

【虚拟门面架构机制】：
通过标准 PEP 451 MetaPathFinder 与 PEP 562 模块级 __getattr__，
实现零冗余文件物理常驻，历史导入语句 `from finance_tools.xxx import yyy`
与 `import finance_tools.xxx` 100% 透明重定向至对应专业子包，
彻底消除根目录下散落的 42 个实体向下兼容跳转文件，保持目录极致整洁与单一事实来源 (SSOT)。
"""

import importlib
import importlib.abc
import importlib.util
import sys
from typing import Any, Dict

from . import (
    screening,
    forensics_and_valuation,
    risk_and_derivatives,
    macro_and_ripple,
    events_and_verification,
    governance_and_pipeline,
)

VERSION = "6.0.0"

# 6 大业务领域子包物理映射表 (SSOT)
_MODULE_TO_SUBPACKAGE: Dict[str, str] = {
    # 1. 突发事件雷达与鉴真监控流水线 (events_and_verification)
    "alert_dispatcher": "events_and_verification",
    "browser_verification_assistant": "events_and_verification",
    "catalyst_calendar_engine": "events_and_verification",
    "consensus_surprise_engine": "events_and_verification",
    "event_radar_collector": "events_and_verification",
    "evidence_verification_pipeline": "events_and_verification",
    # 2. 财务法证审计与多情景估值模型 (forensics_and_valuation)
    "business_quality_and_moat_engine": "forensics_and_valuation",
    "firm_value_added_bridge_engine": "forensics_and_valuation",
    "forensic_surgical_scalpel": "forensics_and_valuation",
    "forensics_and_trailing_exit_engine": "forensics_and_valuation",
    "integrated_three_statement_engine": "forensics_and_valuation",
    "peer_benchmark_engine": "forensics_and_valuation",
    "unit_economics_engine": "forensics_and_valuation",
    "valuation": "forensics_and_valuation",
    # 3. 数据底账、时效门禁与基础设施 (governance_and_pipeline)
    "basic": "governance_and_pipeline",
    "canyon_linear_pipeline": "governance_and_pipeline",
    "data_readiness_tracker": "governance_and_pipeline",
    "industry_knowledge_manager": "governance_and_pipeline",
    "knowledge_repository": "governance_and_pipeline",
    "market_quote_verifier": "governance_and_pipeline",
    "metric_pipeline": "governance_and_pipeline",
    "microstructure_flow_engine": "governance_and_pipeline",
    "prediction_ledger": "governance_and_pipeline",
    "retrospective_review_engine": "governance_and_pipeline",
    "service": "governance_and_pipeline",
    "systemic_analysis_pipeline": "governance_and_pipeline",
    "validation": "governance_and_pipeline",
    # 4. 宏观冲击与产业链涟漪分析器 (macro_and_ripple)
    "acemoglu_institutional_risk_engine": "macro_and_ripple",
    "aghion_creative_destruction_engine": "macro_and_ripple",
    "hall_discount_friction_engine": "macro_and_ripple",
    "macro_shock_transmission_engine": "macro_and_ripple",
    "mid_cycle_engine": "macro_and_ripple",
    "price_shock_attribution_engine": "macro_and_ripple",
    "sotp_event_analyzer": "macro_and_ripple",
    "supply_chain_ripple_analyzer": "macro_and_ripple",
    # 5. 风险管理与衍生品定价引擎 (risk_and_derivatives)
    "american_option_tree_engine": "risk_and_derivatives",
    "black_litterman_shrinkage_engine": "risk_and_derivatives",
    "black_swan_deep_analyzer": "risk_and_derivatives",
    "credit_risk_engine": "risk_and_derivatives",
    "garch_volatility_engine": "risk_and_derivatives",
    "options_causal_analyzer": "risk_and_derivatives",
    "portfolio_risk_engine": "risk_and_derivatives",
    # 6. 全市场选股与时机引擎 (screening)
    "macro_regime_hmm_valve_engine": "screening",
    "mean_reversion_kalman_engine": "screening",
    "screening_candidate_ranker": "screening",
    "screening_universe_builder": "screening",
    "sepa_buy_signal_engine": "screening",
}


class _FinanceToolsVirtualFacadeFinder(importlib.abc.MetaPathFinder):
    """动态虚拟门面导入拦截器.

    拦截形如 `finance_tools.<module_name>` 的导入请求，
    直接定位并代理到 `finance_tools.<subpackage>.<module_name>`，
    并自动注册至 sys.modules 保持模块单例与 mock/patch 透明性。
    """

    def find_spec(self, fullname: str, path: Any, target: Any = None) -> Any:
        parts = fullname.split(".")
        if len(parts) == 2 and parts[0] == "finance_tools":
            mod_name = parts[1]
            subpkg = _MODULE_TO_SUBPACKAGE.get(mod_name)
            if subpkg:
                target_fullname = f"finance_tools.{subpkg}.{mod_name}"
                submod = importlib.import_module(target_fullname)
                sys.modules[fullname] = submod
                return importlib.util.find_spec(target_fullname)
        return None


# 确保仅注册一次虚拟门面拦截器
if not any(isinstance(f, _FinanceToolsVirtualFacadeFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _FinanceToolsVirtualFacadeFinder())


def __getattr__(name: str) -> Any:
    """PEP 562 模块属性动态访问支持 (例如: finance_tools.service)."""
    subpkg = _MODULE_TO_SUBPACKAGE.get(name)
    if subpkg:
        target_fullname = f"finance_tools.{subpkg}.{name}"
        mod = importlib.import_module(target_fullname)
        sys.modules[f"finance_tools.{name}"] = mod
        return mod
    raise AttributeError(f"module 'finance_tools' has no attribute '{name}'")


def __dir__():
    """展示所有可直接访问的模块与子包列表."""
    return sorted(list(globals().keys()) + list(_MODULE_TO_SUBPACKAGE.keys()))


# 常用关键契约与类顶层解构导出 (保持历史顶层代码绝对兼容)
from .risk_and_derivatives.options_causal_analyzer import (
    OptionContractInput,
    UnderlyingScenarios,
    OptionAnalysisResult,
    OptionsCausalAnalyzer,
)
from .events_and_verification.consensus_surprise_engine import (
    ConsensusDataInput,
    ConsensusSurpriseResult,
    ConsensusSurpriseEngine,
)
from .governance_and_pipeline.microstructure_flow_engine import (
    MicrostructureInput,
    MicrostructureResult,
    MicrostructureFlowEngine,
)
from .events_and_verification.catalyst_calendar_engine import (
    CorporateEvent,
    EventEvaluationResult,
    CatalystCalendarEngine,
)
from .forensics_and_valuation.peer_benchmark_engine import (
    CompanyPeerMetrics,
    PeerBenchmarkResult,
    PeerBenchmarkEngine,
)
from .forensics_and_valuation.unit_economics_engine import (
    PipelineAsset,
    BiotechRNPVResult,
    UnitEconomicsEngine,
)
from .forensics_and_valuation.integrated_three_statement_engine import (
    BaselineFinancials,
    ProjectedYearResult,
    ThreeStatementSimulationResult,
    IntegratedThreeStatementEngine,
)
from .macro_and_ripple.price_shock_attribution_engine import (
    GuidanceTerminalImpact,
    OperatingLeverageImpact,
    DilutionOverhangImpact,
    SBCFreeCashFlowImpact,
    RiskPremiumWACCImpact,
    DealerGammaDragImpact,
    PriceShockAttributionEngine,
)
from .risk_and_derivatives.american_option_tree_engine import (
    AmericanOptionTreeInput,
    AmericanOptionTreeEngine,
)
from .macro_and_ripple.macro_shock_transmission_engine import (
    MacroShockInput,
    MacroShockTransmissionEngine,
)
from .forensics_and_valuation.business_quality_and_moat_engine import (
    OwnerEarningsInput,
    LiquorConsumerFleshInput,
    TechHardwareFleshInput,
    BusinessQualityAndMoatEngine,
)
from .forensics_and_valuation.forensic_surgical_scalpel import (
    ForensicInputData,
    ForensicDissectionResult,
    ForensicSurgicalScalpel,
)
from .governance_and_pipeline.systemic_analysis_pipeline import (
    SystemicCompanyInput,
    SystemicDecisionCard,
    SystemicAnalysisPipeline,
)
from .governance_and_pipeline.canyon_linear_pipeline import (
    CanyonStationInput,
    CanyonDecisionCard,
    CanyonLinearPipeline,
    QuoteFreshnessError,
    BalanceSheetInvariantError,
)
from .events_and_verification.event_radar_collector import (
    EventRadarCollector,
    NetworkHealthWatchdog,
    RadarProgressManager,
    RadarDatabaseManager,
    MockModelSummarizer,
)
from .macro_and_ripple.sotp_event_analyzer import (
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
