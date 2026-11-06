"""跨市场宏观冲击与流动性压力测试引擎 (Cross-Asset Macro Shock & Liquidity Stress Engine).

严格遵循《全栈工程命名架构与状态空间规范 (08-全栈工程命名架构与状态空间规范.md)》:
1. 建立日美利率汇率联动与日元套息交易平仓 (Carry Trade Unwind) 去杠杆传导方程;
2. 刻画极端黑天鹅危机时刻跨资产相关性急剧收敛向 1.0 的踩踏压力测试;
3. 建立宏观金融条件收紧对微观个股折现率 (WACC) 的动态贝塔与杠杆加压模型;
4. 深度穿透微观血肉（研发烧钱跑道、大客户集中度、物理垄断护城河），识别是否为“流动性提款机 (ATM) 错杀”还是“基本面暴雷”;
5. 单一事实来源 (SSOT) 状态空间注册表 (MACRO_SHOCK_STATE_REGISTRY): 显式记载宏观分层状态与资产脆弱性画像。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Union
import math

from .market_adaptive_params import MacroShockAdaptiveParams


# ==============================================================================
# 一、 强类型区间状态空间枚举 (State Enums)
# ==============================================================================

class MacroRegimeState(str, Enum):
    """宏观系统性流动性分层状态 (4 态空间)."""
    SURPLUS_BENIGN = "Liquidity_Surplus_Benign"        # 充裕宽松平稳期 (压力分 < 0.25)
    NEUTRAL_NORMAL = "Neutral_Normal_Stress"           # 中性震荡常态期 (0.25 ~ 0.50)
    DELEVERAGING_PRESSURE = "Deleveraging_Pressure"    # 机构去杠杆承压期 (0.50 ~ 0.75)
    ACUTE_BLACK_SWAN_CRUNCH = "Acute_Black_Swan_Crunch"# 急性黑天鹅踩踏期 (>= 0.75)


class LeverageVulnerabilityTier(str, Enum):
    """杠杆脆弱性评级 (3 态空间)."""
    LOW = "Low"                                        # 低杠杆安全
    MEDIUM = "Medium"                                  # 中杠杆警惕
    HIGH = "High"                                      # 高杠杆危急


class AssetMicroVulnerabilityType(str, Enum):
    """微观资产在宏观冲击下的承压画像 (4 态空间)."""
    MOATED_PHYSICAL_MONOPOLY = "Moated_Physical_Monopoly" # 物理垄断硬资产 (跌幅多为流动性错杀 ATM)
    CASH_BURN_LONG_DURATION = "Cash_Burn_Long_Duration"   # 纯研发烧钱高久期 (贴现率抬升直接杀估值)
    CAPEX_CYCLICAL_CONCENTRATED = "Capex_Cyclical_Concentrated" # 资本开支周期+大客户单点依赖 (砍单重灾区)
    BALANCED_ROBUST = "Balanced_Robust"                   # 财务结构健康均衡 (正常防守)


# ==============================================================================
# 二、 单一事实来源状态元数据注册表 (SSOT)
# ==============================================================================

MACRO_SHOCK_STATE_REGISTRY: Dict[str, Dict[str, Dict[str, Any]]] = {
    "macro_regime": {
        MacroRegimeState.SURPLUS_BENIGN.value: {
            "state_id": "MR_01",
            "state_name": "流动性充裕宽松期",
            "numerical_interval": "[0.0, 0.25) 综合压力分",
            "severity_level": 1,
            "business_intuition_zh": "宏观无风险利率平稳，借贷成本低廉，套息交易平稳，市场资金追逐成长题材。",
            "action_directive_zh": "可积极布局高贝塔优质成长标的，享受估值扩张红利。",
        },
        MacroRegimeState.NEUTRAL_NORMAL.value: {
            "state_id": "MR_02",
            "state_name": "中性均衡常态期",
            "numerical_interval": "[0.25, 0.50) 综合压力分",
            "severity_level": 2,
            "business_intuition_zh": "宏观多空因素胶着，无风险利率处于合理中枢，资金倾向于精选个股。",
            "action_directive_zh": "严格按照公允内在价值操作，杜绝溢价追高，保持 20% 基准现金仓位。",
        },
        MacroRegimeState.DELEVERAGING_PRESSURE.value: {
            "state_id": "MR_03",
            "state_name": "机构去杠杆承压期",
            "numerical_interval": "[0.50, 0.75) 综合压力分",
            "severity_level": 3,
            "business_intuition_zh": "日元升值或美债收益率反弹引发对冲基金被动降杠杆，高估值与带息负债重的标的开始失血。",
            "action_directive_zh": "将现金水位提升至 40% 以上，主动收缩未盈利小市值股票敞口，严防踩踏。",
        },
        MacroRegimeState.ACUTE_BLACK_SWAN_CRUNCH.value: {
            "state_id": "MR_04",
            "state_name": "急性黑天鹅踩踏期",
            "numerical_interval": "[0.75, 1.00] 综合压力分",
            "severity_level": 5,
            "business_intuition_zh": "集体黑天鹅爆发！跨资产相关性急剧收敛逼近 1.0，算法风控引发无差别抛售，流动性严重枯竭。",
            "action_directive_zh": "执行最高级别防守！拉高现金至 60%+，严禁左侧接飞刀，保护本金；仅对被无差别错杀的物理垄断资产准备右侧逆向击球计划。",
        },
    },
    "asset_vulnerability": {
        AssetMicroVulnerabilityType.MOATED_PHYSICAL_MONOPOLY.value: {
            "state_id": "AV_01",
            "state_name": "物理垄断硬资产",
            "severity_level": 1,
            "business_intuition_zh": "拥有全球不可替代的物理级运力、网络垄断或国家刚性订单，盘面下挫主要是大资金因流动性枯竭而被迫变现（ATM 提款机效应）。",
            "action_directive_zh": "坚决不割肉！守住核心基准线，这类标的在恐慌消退后具备最强均值回归与反弹弹性。",
        },
        AssetMicroVulnerabilityType.CASH_BURN_LONG_DURATION.value: {
            "state_id": "AV_02",
            "state_name": "研发烧钱失血型",
            "severity_level": 4,
            "business_intuition_zh": "缺乏自身造血净利润，现金跑道持续消耗，无风险利率高位直接斩断远期估值溢价，极易演变为价值陷阱。",
            "action_directive_zh": "严禁逢低盲目补仓！反弹分批减持控制风险敞口，总仓位控制在 5%~10% 以内。",
        },
        AssetMicroVulnerabilityType.CAPEX_CYCLICAL_CONCENTRATED.value: {
            "state_id": "AV_03",
            "state_name": "算力周期与大客户集中脆弱型",
            "severity_level": 5,
            "business_intuition_zh": "处于下游资本开支收缩风暴眼，大客户订单一旦削减或遭审查，将面临断崖式减值与估值崩溃。",
            "action_directive_zh": "绝不盲目抄底！等待大客户多元化落地或存货减值充分出清后的右侧信号。",
        },
        AssetMicroVulnerabilityType.BALANCED_ROBUST.value: {
            "state_id": "AV_04",
            "state_name": "财务均衡稳健型",
            "severity_level": 2,
            "business_intuition_zh": "资产负债平衡，有稳定经营现金流，受宏观波动影响处于可控范围。",
            "action_directive_zh": "维持正常跟踪与买点配置。",
        },
    },
}


def get_macro_state_metadata(domain_key: str, state_value: Union[str, Enum]) -> Dict[str, Any]:
    """统一查询宏观状态元数据."""
    raw_val = state_value.value if isinstance(state_value, Enum) else str(state_value)
    domain = MACRO_SHOCK_STATE_REGISTRY.get(domain_key, {})
    meta = domain.get(raw_val)
    if meta:
        return {"domain_key": domain_key, "state_key": raw_val, **meta}
    return {
        "domain_key": domain_key,
        "state_key": raw_val,
        "state_id": "UNKNOWN",
        "state_name": "未收录状态",
        "severity_level": 0,
        "business_intuition_zh": "未定义状态",
        "action_directive_zh": "谨慎核对数据源",
    }


# ==============================================================================
# 三、 宏观冲击输入数据契约 (Macro Shock Input Contract)
# ==============================================================================

@dataclass
class MacroShockInput:
    """宏观冲击与微观血肉联合输入参数契约."""
    us_10y_yield: float           # 10年期美债基准收益率 (例如 0.044 代表 4.4%)
    usdjpy_rate: float            # 美元兑日元汇率 (例如 152.0)
    vix_index: float              # 市场恐慌指数 VIX (例如 22.0)
    usdjpy_daily_change_pct: float # 日元汇率单日变动幅度 (例如 -0.025 代表日元急剧升值 2.5%, 套息平仓)
    fed_liquidity_drain_billion: float # 美联储单月缩表流动性收紧额度 (USD 10亿为单位)
    company_beta: float           # 标的企业对大盘系统贝塔
    company_debt_to_equity: float # 企业负债权益比 (D/E)
    base_wacc: float              # 标的企业初始基准 WACC (例如 0.09)

    # 拓展微观血肉穿透字段 (自解释与全生命周期)
    months_cash_runway: Optional[float] = None    # 现金维持经营跑道月数 (<12个月高度危险)
    top_5_customer_share: Optional[float] = None  # 前五大客户营收集中度 (0.0 ~ 1.0)
    has_monopoly_moat: bool = False               # 是否具备实体/网络垄断护城河


# ==============================================================================
# 四、 核心引擎实现 (MacroShockTransmissionEngine)
# ==============================================================================

class MacroShockTransmissionEngine:
    """跨市场宏观黑天鹅传导与微观血肉联合冲击中枢."""

    def __init__(self, adaptive_params: Optional[MacroShockAdaptiveParams] = None):
        self.version = "2.0.0"
        self.adaptive_params = adaptive_params

    def evaluate_macro_shock(
        self,
        params: MacroShockInput,
        adaptive_params: Optional[MacroShockAdaptiveParams] = None,
    ) -> Dict[str, Any]:
        """测算跨市场宏观冲击对个股资本成本 (WACC) 与估值锚点的综合压力测试."""
        cfg = adaptive_params or self.adaptive_params or MacroShockAdaptiveParams()

        # 1. 日元套息平仓风险指数 (Carry Trade Unwind Score: 0 ~ 100)
        fx_jpy_stress = min(100.0, max(0.0, (-params.usdjpy_daily_change_pct / max(0.001, cfg.fx_jpy_threshold)) * 60.0))
        vix_stress = min(100.0, max(0.0, ((params.vix_index - cfg.vix_baseline) / max(1.0, cfg.vix_span)) * 40.0))
        carry_trade_stress_score = min(100.0, fx_jpy_stress + vix_stress)

        # 2. 危机时跨资产相关性收敛乘数 (相关性急剧向 1.0 收敛)
        crisis_intensity = carry_trade_stress_score / 100.0
        correlation_span = max(0.01, cfg.max_correlation - cfg.base_correlation)
        converged_correlation = min(
            cfg.max_correlation,
            cfg.base_correlation + correlation_span * math.pow(crisis_intensity, cfg.stampede_power_exponent),
        )

        # 3. 宏观流动性紧缩对个股 WACC 的贝塔与微观脆弱度加压
        # 债务杠杆惩罚
        leverage_penalty = max(1.0, 1.0 + params.company_debt_to_equity * cfg.debt_leverage_multiplier)

        # 现金跑道与失血惩罚 (微观血肉)
        runway_penalty = 1.0
        if params.months_cash_runway is not None:
            if params.months_cash_runway < 12.0:
                runway_penalty = 1.45  # 严重失血惩罚加压 45%
            elif params.months_cash_runway < 24.0:
                runway_penalty = 1.20

        # 大客户集中度惩罚 (微观血肉)
        customer_penalty = 1.0
        if params.top_5_customer_share is not None and params.top_5_customer_share > 0.60:
            customer_penalty = 1.35  # 单点脆弱惩罚加压 35%

        # 美债利率基准偏离冲击
        rf_drift_bps = max(0.0, (params.us_10y_yield - cfg.rf_benchmark_yield) * 10000.0)

        # 流动性紧缩与套息平仓利差加点
        liquidity_spread_bps = (params.fed_liquidity_drain_billion / max(1.0, cfg.liquidity_drain_base_billion)) * cfg.liquidity_drain_spread_bps
        carry_trade_spread_bps = (carry_trade_stress_score / 100.0) * cfg.carry_trade_spread_bps_max

        # 综合 WACC 加压
        # 金融常识防御：宏观系统性流动性挤兑对权益资产是普遍抽水冲击，有效敏感贝塔不得低于 0.10，防止负贝塔导致折现率反向塌陷跌穿无风险利率
        effective_beta = max(0.10, abs(params.company_beta))
        total_wacc_spread_bps = (
            (rf_drift_bps * cfg.rf_drift_passthrough + liquidity_spread_bps + carry_trade_spread_bps)
            * effective_beta
            * leverage_penalty
            * runway_penalty
            * customer_penalty
        )
        raw_shocked_wacc = params.base_wacc + (total_wacc_spread_bps / 10000.0)
        # 金融公理下界防御：资本成本 WACC 绝不得低于无风险基准利率 (us_10y_yield)
        shocked_wacc = max(max(0.015, params.us_10y_yield), raw_shocked_wacc)

        # 4. 估值锚点收缩幅度 (宏观加压导致 PE/DCF 理论下折百分比)
        g_rate = cfg.valuation_terminal_g
        base_spread = max(0.02, params.base_wacc - g_rate)
        shocked_spread = max(0.02, shocked_wacc - g_rate)
        valuation_haircut_pct = (1.0 - (base_spread / shocked_spread)) * 100.0

        # 5. 宏观环境状态机映射
        overall_stress_score = min(1.0, max(0.0, (carry_trade_stress_score / 100.0) * 0.6 + (params.vix_index / 40.0) * 0.4))
        if overall_stress_score >= 0.75:
            regime_state = MacroRegimeState.ACUTE_BLACK_SWAN_CRUNCH
        elif overall_stress_score >= 0.50:
            regime_state = MacroRegimeState.DELEVERAGING_PRESSURE
        elif overall_stress_score >= 0.25:
            regime_state = MacroRegimeState.NEUTRAL_NORMAL
        else:
            regime_state = MacroRegimeState.SURPLUS_BENIGN
        regime_meta = get_macro_state_metadata("macro_regime", regime_state)

        # 6. 微观资产脆弱度画像与 ATM 提款机错杀识别
        if params.has_monopoly_moat:
            micro_type = AssetMicroVulnerabilityType.MOATED_PHYSICAL_MONOPOLY
            is_atm_victim = overall_stress_score >= 0.50  # 优质资产在恐慌中沦为提款机
        elif params.top_5_customer_share is not None and params.top_5_customer_share > 0.60:
            # 大客户集中度 > 60%，处于下游资本开支收缩与单点依赖首要风暴眼
            micro_type = AssetMicroVulnerabilityType.CAPEX_CYCLICAL_CONCENTRATED
            is_atm_victim = False
        elif params.months_cash_runway is not None and params.months_cash_runway < 18.0:
            # 研发失血长久期
            micro_type = AssetMicroVulnerabilityType.CASH_BURN_LONG_DURATION
            is_atm_victim = False
        else:
            micro_type = AssetMicroVulnerabilityType.BALANCED_ROBUST
            is_atm_victim = False
        micro_meta = get_macro_state_metadata("asset_vulnerability", micro_type)

        # 杠杆评级与去工程符号化自然中文映射 (SSOT)
        if leverage_penalty > 1.8:
            leverage_tier = LeverageVulnerabilityTier.HIGH
            leverage_tier_zh = "高杠杆危急"
        elif leverage_penalty > 1.3:
            leverage_tier = LeverageVulnerabilityTier.MEDIUM
            leverage_tier_zh = "中杠杆警惕"
        else:
            leverage_tier = LeverageVulnerabilityTier.LOW
            leverage_tier_zh = "低杠杆安全"

        # 7. 生成通俗买方商业直觉全息研报卡片 (去工程符号化)
        regime_name_zh = regime_meta.get("state_name", "未知宏观周期")
        micro_name_zh = micro_meta.get("state_name", "未知微观画像")
        carry_trade_desc_zh = (
            f"触发日元套息平仓警报 (压力度 {carry_trade_stress_score:.1f}分)"
            if carry_trade_stress_score >= cfg.carry_trade_trigger_score
            else f"套息平仓风险可控 (压力度 {carry_trade_stress_score:.1f}分)"
        )
        tactical_directive_zh = (
            "【物理垄断硬资产】跌幅为流动性错杀提款机抛盘，坚决不割肉，守住基准底线！"
            if is_atm_victim
            else micro_meta.get("action_directive_zh", "")
        )

        narrative_zh = (
            f"【宏观流动性与微观承压全息研判】当前系统处于【{regime_name_zh}】，{carry_trade_desc_zh}；"
            f"跨市场资产极端相关性收敛至 {converged_correlation:.2f}。"
            f"微观个股基准资本成本 {params.base_wacc * 100:.2f}% 经宏观利差加压 {total_wacc_spread_bps:.0f} 个基点后抬升至 {shocked_wacc * 100:.2f}%，"
            f"导致理论公允估值承压下折 {valuation_haircut_pct:.1f}%。"
            f"标的微观画像归属【{micro_name_zh}】(财务杠杆评级: {leverage_tier_zh})。"
            f"买方战术策略: {tactical_directive_zh}"
        )

        return {
            "carry_trade_stress_score": round(carry_trade_stress_score, 2),
            "carry_trade_unwind_active": carry_trade_stress_score >= cfg.carry_trade_trigger_score,
            "converged_market_correlation": round(converged_correlation, 4),
            "macro_wacc_spread_bps": round(total_wacc_spread_bps, 1),
            "base_wacc_pct": round(params.base_wacc * 100, 2),
            "shocked_wacc_pct": round(shocked_wacc * 100, 2),
            "valuation_haircut_pct": round(valuation_haircut_pct, 2),
            "leverage_vulnerability_tier": leverage_tier.value,
            "leverage_vulnerability_tier_zh": leverage_tier_zh,
            "leverage_vulnerability_enum": leverage_tier,
            "macro_regime_state": regime_state.value,
            "macro_regime_state_zh": regime_name_zh,
            "macro_regime_enum": regime_state,
            "macro_regime_metadata": regime_meta,
            "micro_vulnerability_type": micro_type.value,
            "micro_vulnerability_type_zh": micro_name_zh,
            "micro_vulnerability_enum": micro_type,
            "micro_vulnerability_metadata": micro_meta,
            "is_atm_liquidity_victim": is_atm_victim,
            "tactical_directive_zh": tactical_directive_zh,
            "narrative_zh": narrative_zh,
        }
