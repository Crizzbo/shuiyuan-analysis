"""金融分析核心数据契约 (Financial Analysis Core Contracts).

纯净的金融分析数据模型，定义核心引擎的输入、输出及中间结果结构。
贯彻工程整改规范：
1. 贯穿币种 (currency)、市场 (market) 与单位契约;
2. 明确数据来源属性 (is_demo_sample, data_provenance);
3. 区分真实零值、未计算/缺失值 (None) 与假设值;
4. 结构化承载客观事实数据，预留 AI 投研日记归纳槽位 (ai_research_journal)，程序严禁越界进行武断的机械定论。
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from enum import Enum

from .engines.credit_risk_engine import CreditRiskResult
from .engines.monte_carlo_engine import MonteCarloValuationResult
from .engines.portfolio_risk_engine import (
    VaRResult,
    RiskDecompositionResult,
    FactorAttributionResult,
    StressTestScenarioResult,
)
from .engines.volatility_surface_engine import (
    OptionGreeksResult,
    PutCallParityCheckResult,
    VolatilitySkewResult,
)
from .engines.mid_cycle_engine import (
    MidCycleValuationResult,
    CyclePhaseResult,
)


class AnalysisMode(str, Enum):
    """分析模式枚举."""
    FULL_SYSTEMIC = "full_systemic"          # 全流程系统性六道工序分析
    FORENSIC_ONLY = "forensic_only"          # 纯法证级穿透五刀审计
    VALUATION_DCF = "valuation_dcf"          # 多情景差异化 DCF 与内在价值估值
    MACRO_STRESS = "macro_stress"            # 跨市场宏观冲击与套息交易压力测试
    MICRO_FOUNDED_MACRO = "micro_founded_macro" # 诺奖微观基础宏观传导分析 (Woodford/Hall/Acemoglu/Aghion)
    OPTION_TREE = "option_tree"              # CRR 美式期权二叉树与 Merton 跳跃扩散
    CREDIT_SOLVENCY = "credit_solvency"      # 信用风险违约距离 (Merton DD) 与破产预警
    MONTE_CARLO = "monte_carlo"              # 10,000 次多参数连续概率分布随机估值模拟
    PORTFOLIO_RISK = "portfolio_risk"        # 组合在险价值 (VaR/CVaR)、收缩协方差与多因子归因
    VOLATILITY_SURFACE = "volatility_surface"# 全阶希腊字母、平价套利与波动率偏斜曲面
    MID_CYCLE = "mid_cycle"                  # 跨周期正常化 FCF 贴现与 Shiller CAPE


@dataclass
class ForensicFinding:
    """法证穿透审计单项发现."""
    dimension: str                           # 维度名称（如受限现金、存货毒性等）
    alert_level: str                         # GREEN, YELLOW, RED
    raw_metric: float                        # 原始财务指标
    adjusted_metric: float                   # 法证核减/核准后指标
    evidence: str                            # 证据描述与穿透逻辑


@dataclass
class ValuationScenario:
    """估值情景数据 (严格基于可复算的模型参数)."""
    scenario_name: str                       # pessimistic, neutral, optimistic
    fair_value: float                        # 内在公允价值
    implied_upside_downside_pct: float       # 隐含上涨/下跌空间百分比
    terminal_growth_rate: Optional[float]    # 永续增长率 (若适用)
    wacc: Optional[float]                    # 加权平均资本成本 (若适用)
    valuation_model_used: str = "DCF"        # DCF, rNPV_Liquidation, Multiples


@dataclass
class OptionPricingResult:
    """期权定价与隐含波动率结构 (未计算项显式为 None，严禁填零掩盖)."""
    strike: float
    spot_price: float
    time_to_expiry_days: int
    implied_volatility: float
    crr_american_call: float
    crr_american_put: float
    merton_jump_call: Optional[float] = None
    merton_jump_put: Optional[float] = None
    early_exercise_premium: Optional[float] = None  # 美式提前行权溢价金额
    early_exercise_boundary: Optional[float] = None # 提前行权价格临界点 (若支持)


@dataclass
class MacroStressResult:
    """宏观压力测试结果 (真实反映底层评估引擎的折价幅度)."""
    scenario_name: str
    equity_shock_pct: float                  # 估值中枢变动百分比 (如 -15.2%)
    target_price_under_stress: float         # 承压后理论公允价
    transmission_channel: str                # 宏观传导路径 (Carry Trade, WACC Spread, Liquidity Drain)
    shocked_wacc_pct: float                  # 加压后折现率
    vix_sensitivity: float                   # VIX 敏感度
    fx_carry_sensitivity: float              # 汇率与套息敏感度


@dataclass
class MicroFoundedMacroContractResult:
    """基于诺奖微观基础宏观理论的综合评估契约 (Woodford/Hall/Acemoglu/Aghion)."""
    wicksellian_rate_gap_bps: float          # 维克塞尔自然利率缺口 (基点，正=紧缩)
    is_monetary_restrictive: bool            # 货币立场是否紧缩
    dynamic_wacc_vector: List[float]         # 1~N 年逐年动态内生 WACC 折现率向量
    average_wacc_pct: float                  # 平均动态 WACC %
    micro_markup_ratio: float                # 霍尔微观加成率 mu = P / MC
    pricing_power_tier: str                  # 定价转嫁权评级
    shocked_gross_margin_pct: float          # 摩擦冲击后毛利率 %
    precautionary_capex_curtailment_pct: float # 霍尔预防性流动性囤积导致的 Capex 削减 %
    institutional_quality_index: float       # 阿西莫格鲁制度质量指数 (0~100)
    institution_type: str                    # 包容性 vs 掠夺性制度类型
    institutional_risk_spread_bps: float     # 制度与地缘风险利差 (基点)
    distance_to_technology_frontier: float   # 阿吉翁技术前沿距离 DTF [0, 1]
    schumpeterian_survival_status: str       # 熊彼特创造性破坏地位 (领跑者 / 僵尸淘汰高危)
    terminal_growth_adj_bps: float           # 终值长期增长率调整基点
    governance_terminal_haircut_pct: float   # 超长远期制度风险折价率 %
    integrated_verdict: str                  # 顶层微观基础宏观总结


@dataclass
class DecisionCardData:
    """结构化事实与客观指标看板 (程序负责客观数据与警示，AI 负责日记归纳)."""
    ticker: str
    company_name: str
    market: str                              # US, CN, JP
    currency: str                            # USD, CNY, JPY
    currency_symbol: str                     # $, ¥
    sector: str
    quote_timestamp: str
    market_session: str
    current_price: float
    baseline_reference_price: float
    objective_signal: str                    # DATA_PACK_READY, FORENSIC_ALERT_ACTIVE, DISCOUNT_OBSERVED, PREMIUM_EXPENSIVE
    pessimistic_floor: float                 # 悲观底价
    neutral_fair_value: float                # 中性公允价值
    optimistic_target: float                 # 乐观靶心
    margin_of_safety_pct: float              # 安全边际百分比
    hard_runway_desc: str                    # 现金跑道状态 (例如: "持续净流入 (无需消耗储备)", "11.6 个月")
    forensic_red_flags_count: int            # 法证红牌数量
    forensic_yellow_flags_count: int         # 法证黄牌数量
    primary_catalysts: List[str]             # 核心催化事实
    key_risks: List[str]                     # 核心风险与破位事实
    summary_verdict: str                     # 程序客观总结
    is_demo_sample: bool = False             # 是否为测试演示样本
    kelly_fraction: Optional[float] = None   # 仓位建议 (若无经过校准的胜率/赔率，严格为 None)
    ai_research_journal: Optional[str] = None# AI 独立撰写的投研日记与定性归纳
    merton_dd: Optional[float] = None        # Merton 违约距离 (σ)
    altman_z: Optional[float] = None         # Altman Z-Score 评分
    monte_carlo_median: Optional[float] = None # 蒙特卡洛中位数公允价
    prob_undervalued_pct: Optional[float] = None # 现价低于公允价值概率 %
    portfolio_var_95_pct: Optional[float] = None # 95% 置信度参数法在险价值率 %
    cvar_expected_shortfall_pct: Optional[float] = None # 95% 置信度预期尾部损失率 %
    skew_25d: Optional[float] = None         # 期权 25-Delta 波动率偏斜 (Put IV - Call IV)
    option_delta: Optional[float] = None     # 标的期权 Delta 方向敏感度
    cycle_phase: Optional[str] = None        # 当前宏观与商业周期阶段
    mid_cycle_fair_value: Optional[float] = None # 跨周期正常化内在公允价值
    shiller_cape: Optional[float] = None     # 席勒周期调整市盈率
    wicksellian_gap_bps: Optional[float] = None # 维克塞尔自然利率缺口基点
    dynamic_wacc_t1: Optional[float] = None  # 伍德福德前瞻首期 WACC %
    pricing_power_tier: Optional[str] = None # 霍尔微观定价权评级
    distance_to_frontier: Optional[float] = None # 阿吉翁技术前沿距离 DTF
    institutional_quality_score: Optional[float] = None # 阿西莫格鲁制度质量指数 IQI


@dataclass
class FinancialAnalysisResult:
    """金融分析核心统一输出结果契约."""
    ticker: str
    company_name: str
    market: str
    currency: str
    sector: str
    analysis_mode: str
    timestamp: str
    execution_success: bool
    execution_status: str                    # SUCCESS, BLOCKED_ACCOUNTING_DISCREPANCY, BLOCKED_MISSING_EVIDENCE, BLOCKED_INVALID_INPUT
    decision_card: DecisionCardData
    is_demo_sample: bool = False
    forensic_findings: List[ForensicFinding] = field(default_factory=list)
    valuation_scenarios: List[ValuationScenario] = field(default_factory=list)
    macro_stress: Optional[MacroStressResult] = None
    option_pricing: Optional[OptionPricingResult] = None
    credit_risk: Optional[CreditRiskResult] = None
    monte_carlo_valuation: Optional[MonteCarloValuationResult] = None
    portfolio_var: Optional[VaRResult] = None
    risk_decomposition: Optional[RiskDecompositionResult] = None
    factor_attribution: Optional[FactorAttributionResult] = None
    macro_stress_scenarios: List[StressTestScenarioResult] = field(default_factory=list)
    volatility_greeks: Optional[OptionGreeksResult] = None
    put_call_parity: Optional[PutCallParityCheckResult] = None
    volatility_skew: Optional[VolatilitySkewResult] = None
    mid_cycle_valuation: Optional[MidCycleValuationResult] = None
    micro_founded_macro: Optional[MicroFoundedMacroContractResult] = None
    raw_forensic_metrics: Dict[str, Any] = field(default_factory=dict)
    raw_engine_payload: Dict[str, Any] = field(default_factory=dict)
    block_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典格式."""
        return asdict(self)
