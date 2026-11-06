"""[已归档] 跨市场宏观冲击与流动性压力测试引擎历史版本 (Legacy V1).

归档时间: 2026-11-03
归档原因: 全栈命名规范升级、状态空间注册表 (SSOT) 整合与黑天鹅微观血肉联合冲击升级。
替换版本: financial_core/engines/macro_shock_transmission_engine.py
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import math

from financial_core.engines.market_adaptive_params import MacroShockAdaptiveParams


@dataclass
class MacroShockInput:
    """宏观冲击输入参数."""
    us_10y_yield: float           # 10年期美债基准收益率 (例如 0.044 代表 4.4%)
    usdjpy_rate: float            # 美元兑日元汇率 (例如 152.0)
    vix_index: float              # 市场恐慌指数 VIX (例如 22.0)
    usdjpy_daily_change_pct: float # 日元汇率单日变动幅度 (例如 -0.025 代表日元急剧升值 2.5%, 套息平仓)
    fed_liquidity_drain_billion: float # 美联储单月缩表流动性收紧额度 (USD 10亿为单位)
    company_beta: float           # 标的企业对大盘系统贝塔
    company_debt_to_equity: float # 企业负债权益比 (D/E)
    base_wacc: float              # 标的企业初始基准 WACC (例如 0.09)


class MacroShockTransmissionEngine:
    """跨市场宏观冲击传导与多因子压力测试中枢."""

    def __init__(self, adaptive_params: Optional[MacroShockAdaptiveParams] = None):
        self.version = "1.0.0"
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

        # 2. 危机时跨资产相关性收敛乘数
        crisis_intensity = carry_trade_stress_score / 100.0
        correlation_span = max(0.01, cfg.max_correlation - cfg.base_correlation)
        converged_correlation = min(
            cfg.max_correlation,
            cfg.base_correlation + correlation_span * math.pow(crisis_intensity, cfg.stampede_power_exponent),
        )

        # 3. 宏观流动性紧缩对个股 WACC 的贝塔加压
        leverage_penalty = max(1.0, 1.0 + params.company_debt_to_equity * cfg.debt_leverage_multiplier)
        rf_drift_bps = max(0.0, (params.us_10y_yield - cfg.rf_benchmark_yield) * 10000.0)
        liquidity_spread_bps = (params.fed_liquidity_drain_billion / max(1.0, cfg.liquidity_drain_base_billion)) * cfg.liquidity_drain_spread_bps
        carry_trade_spread_bps = (carry_trade_stress_score / 100.0) * cfg.carry_trade_spread_bps_max

        total_wacc_spread_bps = (rf_drift_bps * cfg.rf_drift_passthrough + liquidity_spread_bps + carry_trade_spread_bps) * params.company_beta * leverage_penalty
        shocked_wacc = params.base_wacc + (total_wacc_spread_bps / 10000.0)

        # 4. 估值锚点收缩幅度
        g_rate = cfg.valuation_terminal_g
        base_spread = max(0.02, params.base_wacc - g_rate)
        shocked_spread = max(0.02, shocked_wacc - g_rate)
        valuation_haircut_pct = (1.0 - (base_spread / shocked_spread)) * 100.0

        return {
            "carry_trade_stress_score": round(carry_trade_stress_score, 2),
            "carry_trade_unwind_active": carry_trade_stress_score >= cfg.carry_trade_trigger_score,
            "converged_market_correlation": round(converged_correlation, 4),
            "macro_wacc_spread_bps": round(total_wacc_spread_bps, 1),
            "base_wacc_pct": round(params.base_wacc * 100, 2),
            "shocked_wacc_pct": round(shocked_wacc * 100, 2),
            "valuation_haircut_pct": round(valuation_haircut_pct, 2),
            "leverage_vulnerability_tier": "High" if leverage_penalty > 1.8 else ("Medium" if leverage_penalty > 1.3 else "Low"),
        }
