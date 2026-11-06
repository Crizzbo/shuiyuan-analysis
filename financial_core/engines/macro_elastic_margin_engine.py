"""宏观流动性压力与动态弹性安全边际引擎 (Macro Elastic Margin of Safety Engine).

单一事实来源 (SSOT) 规范：
1. 宏观流动性综合压力指标 S_macro：
   综合美联储净流动性 (WALCL - TGA - RRP)、美债 10Y-2Y 期限利差、VIX 恐慌指数与期权做市商 GEX；
2. 动态弹性安全边际扩张方程：
   MOS_elastic = MOS_base * (1.0 + 0.75 * S_macro)
   杜绝牛市机械抄底与熊市踩踏接飞刀；
3. 流动性提款机效应 (ATM Effect) 监测：
   流动性枯竭恐慌期 (S_macro > 0.6 且 VIX > 25)，优质核心重仓资产因无差别平仓遭遇流动性折价，
   标记为非基本面杀跌的高不对称赔率击球机会。
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class MacroLiquidityState:
    """宏观流动性与微观结构状态。"""
    fed_net_liquidity_trillion: float = 5.85  # 美联储净流动性 (万亿美元)
    term_spread_10y_2y_bps: float = 15.0       # 10Y-2Y 利差 (基点)
    vix_index: float = 19.5                    # VIX 恐慌指数
    market_gex_billion: float = 1.2            # 全市场 Gamma 暴露 (十亿美元)


@dataclass(frozen=True)
class MacroElasticMarginResult:
    """宏观弹性安全边际计算结果。"""
    stress_score: float              # 0.0 ~ 1.0 宏观综合压力分
    base_margin_pct: float           # 基础安全边际要求 (如 20.0%)
    elastic_margin_pct: float        # 动态弹性安全边际要求 (如 23.0%)
    atm_effect_detected: bool        # 是否触发核心资产流动性提款机效应
    regime_label: str                # 宏观环境分层标签
    rationale: str                   # 商业投资直觉自然语言说明


class MacroElasticMarginEngine:
    """宏观流动性弹性安全边际引擎。"""

    DEFAULT_BASE_MOS_PCT: float = 20.0

    @classmethod
    def compute_stress_score(cls, state: MacroLiquidityState) -> float:
        """计算宏观综合压力分 S_macro (0.0 ~ 1.0)。"""
        # 1. 净流动性分量 (基准 6.0 万亿，低于 5.5 显著收紧)
        if state.fed_net_liquidity_trillion >= 6.2:
            liq_stress = 0.05
        elif state.fed_net_liquidity_trillion >= 5.8:
            liq_stress = 0.20
        elif state.fed_net_liquidity_trillion >= 5.4:
            liq_stress = 0.50
        else:
            liq_stress = 0.85

        # 2. 利差分量 (倒挂或急剧陡峭化反映衰退预期)
        if state.term_spread_10y_2y_bps < 0.0:
            curve_stress = 0.70  # 倒挂
        elif state.term_spread_10y_2y_bps < 25.0:
            curve_stress = 0.25  # 扁平温和
        else:
            curve_stress = 0.15  # 正常

        # 3. VIX 恐慌分量
        if state.vix_index < 16.0:
            vix_stress = 0.05
        elif state.vix_index < 22.0:
            vix_stress = 0.25
        elif state.vix_index < 30.0:
            vix_stress = 0.65
        else:
            vix_stress = 0.95

        # 4. GEX 做市商 Gamma 分量 (负 Gamma 加剧盘中单边踩踏)
        if state.market_gex_billion > 0.5:
            gex_stress = 0.10
        elif state.market_gex_billion >= -0.5:
            gex_stress = 0.35
        else:
            gex_stress = 0.80

        # 加权合成 S_macro
        total_stress = (
            liq_stress * 0.35 +
            curve_stress * 0.20 +
            vix_stress * 0.30 +
            gex_stress * 0.15
        )
        return round(min(1.0, max(0.0, total_stress)), 3)

    @classmethod
    def evaluate_elastic_margin(
        cls,
        state: Optional[MacroLiquidityState] = None,
        base_margin_pct: Optional[float] = None,
        is_tier0_quality: bool = True,
    ) -> MacroElasticMarginResult:
        """评估动态弹性安全边际。"""
        if state is None:
            state = MacroLiquidityState()
        if base_margin_pct is None:
            base_margin_pct = cls.DEFAULT_BASE_MOS_PCT

        stress = cls.compute_stress_score(state)

        # 弹性扩张公式: MOS_elastic = MOS_base * (1 + 0.75 * S_macro)
        elastic_mos = round(base_margin_pct * (1.0 + 0.75 * stress), 1)

        # ATM 提款机效应识别
        atm_detected = is_tier0_quality and (stress >= 0.55 or state.vix_index >= 24.0)

        # 宏观环境分层标签
        if stress < 0.25:
            regime = "LIQUIDITY_SURPLUS_BENIGN"
            desc = "宏观流动性充裕，系统性折价要求维持基准水平。"
        elif stress < 0.50:
            regime = "NORMAL_NEUTRAL_STRESS"
            desc = "宏观处于正常中性区间，估值折价要求适度上浮。"
        elif stress < 0.75:
            regime = "DELEVERAGING_PRESSURE"
            desc = "市场面临去杠杆与流动性收紧，要求大幅扩张安全边际防范踩踏。"
        else:
            regime = "ACUTE_LIQUIDITY_CRUNCH"
            desc = "流动性高度枯竭黑天鹅区间，必须要求最高等级防守折扣。"

        rationale = f"{desc} 当前综合宏观压力分: {stress:.1%}，要求最低安全边际从基准 {base_margin_pct:.1f}% 动态上调至 {elastic_mos:.1f}%。"
        if atm_detected:
            rationale += " 提示：优质蓝筹当前出现无差别套现抛压，具有不对称黄金击球窗口潜力。"

        return MacroElasticMarginResult(
            stress_score=stress,
            base_margin_pct=base_margin_pct,
            elastic_margin_pct=elastic_mos,
            atm_effect_detected=atm_detected,
            regime_label=regime,
            rationale=rationale,
        )
