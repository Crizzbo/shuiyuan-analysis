"""霍尔微观成本摩擦与加成率引擎 (Hall Friction, Mark-up & Liquidity Hoarding Engine).

理论来源与微观基础：
罗伯特·霍尔 (Robert E. Hall, 2026年诺贝尔经济学奖得主) 经典理论：
1. 企业微观加成率与价格-边际成本偏离 (Price-Cost Mark-up):
   P = mu * MC. 企业抵抗宏观通胀冲击的实质是其加成率 (Mark-up) 的定价防御壁垒。
2. 名义价格与工资刚性摩擦 (Nominal & Wage Rigidity):
   不同行业面对单位劳动力成本 (ULC) 与大宗原材料上涨时，成本顺畅转嫁弹性 (Pass-Through)
   存在高度分化。
3. 折现率波动与预防性流动性囤积 (Precautionary Liquidity Hoarding):
   在宏观折现率剧烈波动时，微观企业会内生性收缩扩张性 Capex，优先强化现金安全壁垒。
"""

from dataclasses import dataclass
import math
from typing import Dict, Any, Optional


@dataclass
class HallFrictionInput:
    """霍尔微观成本摩擦输入."""
    reported_revenue: float                 # 营业收入
    reported_cogs: float                    # 营业成本 COGS
    reported_gross_margin_pct: float        # 当前毛利率 (例如 45.0 表示 45%)
    reported_capex: float                   # 当前资本开支
    cash_and_equivalents: float             # 现金与现金等价物
    total_debt: float                       # 总有息负债
    annual_fcf: float                       # 自由现金流 FCF

    # 宏观摩擦与投入品通胀因子
    commodity_input_inflation_pct: float = 5.0 # 原材料/中间品通胀率 % (如 5.0%)
    unit_labor_cost_inflation_pct: float = 4.0 # 单位劳动力成本 (ULC) 增速 % (如 4.0%)
    macro_vix_volatility: float = 20.0         # 宏观不确定性 (VIX 指数)

    # 标的微观护城河与成本构成参数
    labor_share_in_cogs_pct: float = 30.0      # 劳动力成本在 COGS 中占比 % (如 30%)
    pricing_pass_through_elasticity: float = 0.70 # 价格转嫁弹性 [0.0, 1.0] (1.0=完全转嫁，0.0=完全无法提价)
    variable_cost_ratio: float = 0.85          # 变动成本占总生产要素比例 (用于校准加成率)
    ticker: Optional[str] = None               # 标的代码 (用于跨市场自适应推导)
    market: Optional[str] = None               # 交易市场 ("US" / "JP" / "CN")
    currency_symbol: Optional[str] = None      # 显式货币符号 (未指定时自适应推导)


@dataclass
class HallFrictionResult:
    """霍尔微观摩擦与加成率评估输出."""
    micro_markup_ratio: float                # 微观加成率 mu = P / MC
    pricing_power_tier: str                  # 定价权评级 (STRONG_DEFENSE / MODERATE_PASSTHROUGH / SEVERE_MARGIN_SQUEEZE)
    gross_margin_shock_pct: float            # 通胀冲击后毛利率点数变动 (如 -2.1% 表示毛利从 45% 降至 42.9%)
    shocked_gross_margin_pct: float          # 承压后预测毛利率 %
    precautionary_capex_curtailment_pct: float # 预防性流动性囤积导致的资本开支自主收缩率 %
    curtailed_capex_amount: float            # 调整后资本开支金额
    liquidity_buffer_resilience_months: float# 压力情景下企业现金防御储备寿命 (月)
    friction_verdict: str                    # 霍尔微观摩擦深度定性研判
    pricing_power_tier_zh: str = ""          # 定价权通俗中文命名
    narrative_zh: str = ""                   # 买方通俗全息研报卡片 (去工程符号化)
    currency_symbol: str = "$"               # 货币符号 ("$", "¥")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "currency_symbol": self.currency_symbol,
            "micro_markup_ratio": self.micro_markup_ratio,
            "pricing_power_tier": self.pricing_power_tier,
            "pricing_power_tier_zh": self.pricing_power_tier_zh or self.pricing_power_tier,
            "gross_margin_shock_pct": f"{self.gross_margin_shock_pct:+.2f}%",
            "shocked_gross_margin_pct": f"{self.shocked_gross_margin_pct:.1f}%",
            "precautionary_capex_curtailment_pct": f"{self.precautionary_capex_curtailment_pct:.1f}%",
            "curtailed_capex_amount": self.curtailed_capex_amount,
            "liquidity_buffer_resilience_months": f"{self.liquidity_buffer_resilience_months:.1f} 个月",
            "verdict": self.friction_verdict,
            "narrative_zh": self.narrative_zh or self.friction_verdict,
        }


class HallDiscountFrictionEngine:
    """霍尔微观成本摩擦与加成率引擎."""

    def __init__(self):
        self.version = "1.0.0"

    def evaluate(self, inp: HallFrictionInput) -> HallFrictionResult:
        """测算加成率、成本通胀转嫁摩擦与预防性流动性囤积行为."""
        # 自适应推导市场与货币符号 (SSOT: 兼容美股、日股、A股多币种)
        t_up = (inp.ticker or "").upper()
        m_up = (inp.market or "").upper()
        is_jp = m_up == "JP" or t_up.endswith(".T") or t_up.endswith(".JP") or (t_up.isdigit() and len(t_up) == 4)
        is_cn = m_up == "CN" or t_up.endswith(".SS") or t_up.endswith(".SZ") or (t_up.isdigit() and len(t_up) == 6)
        if inp.currency_symbol:
            curr_sym = inp.currency_symbol
        elif is_jp or is_cn:
            curr_sym = "¥"
        else:
            curr_sym = "$"

        # 1. 霍尔微观加成率计算 (Hall 1988: mu = (Revenue / COGS) * (1 / variable_cost_ratio))
        cogs_safe = max(1.0, inp.reported_cogs)
        revenue_safe = max(cogs_safe, inp.reported_revenue)
        var_ratio = max(0.40, min(1.0, inp.variable_cost_ratio))

        # 粗加成率
        raw_markup = (revenue_safe / cogs_safe) * (1.0 / var_ratio)
        micro_markup = round(max(1.02, min(5.0, raw_markup)), 3)

        # 2. 定价权转嫁弹性与毛利侵蚀 (Cost Pass-Through & Margin Squeeze)
        elasticity = max(0.0, min(1.0, inp.pricing_pass_through_elasticity))
        labor_share = max(0.05, min(0.95, inp.labor_share_in_cogs_pct / 100.0))
        material_share = 1.0 - labor_share

        # 投入要素综合加权通胀率
        blended_input_inflation = (
            labor_share * inp.unit_labor_cost_inflation_pct +
            material_share * inp.commodity_input_inflation_pct
        )

        # 终端售价转嫁涨幅 = 弹性 * 综合通胀率
        realized_price_increase = elasticity * blended_input_inflation

        # 毛利率受压计算:
        # 新毛利率 = (P*(1+realized_price_increase) - COGS*(1+blended_input_inflation)) / P*(1+realized_price_increase)
        base_gm = max(0.01, min(0.95, inp.reported_gross_margin_pct / 100.0))
        price_factor = 1.0 + (realized_price_increase / 100.0)
        cost_factor = 1.0 + (blended_input_inflation / 100.0)

        # 简化有效毛利率变化推导
        shocked_gm = 1.0 - (1.0 - base_gm) * (cost_factor / price_factor)
        shocked_gm = max(0.005, min(0.95, shocked_gm))
        gm_change_pct = round((shocked_gm - base_gm) * 100.0, 2)
        shocked_gm_pct = round(shocked_gm * 100.0, 2)

        # 定价权分级
        if elasticity >= 0.85:
            tier = "STRONG_DEFENSE" # 强防御特许定价权 (如茅台、台积电、爱马仕)
            tier_zh = "强防御特许定价权"
        elif elasticity >= 0.50:
            tier = "MODERATE_PASSTHROUGH" # 适度转嫁中性 (多数工业制造/消费龙头)
            tier_zh = "中度成本转嫁弹性"
        else:
            tier = "SEVERE_MARGIN_SQUEEZE" # 严重成本挤压 (代工厂、无护城河组装)
            tier_zh = "利润率严重受压脆弱型"

        # 3. 霍尔折现率不确定性与预防性流动性囤积 (Precautionary Liquidity Hoarding)
        # 当 VIX 偏离 20 中枢且债务负担重时，企业削减非刚性资本开支
        net_cash_pool = inp.cash_and_equivalents - inp.total_debt
        capex_safe = max(0.0, inp.reported_capex)
        vix_excess = max(0.0, inp.macro_vix_volatility - 18.0)

        # 预防性削减系数: 不确定性越高、净负债越重，Capex 削减越剧烈 (上限 40%)
        leverage_penalty = max(0.1, min(2.0, (inp.total_debt / max(1.0, inp.cash_and_equivalents))))
        hoarding_intensity = min(0.40, (vix_excess / 40.0) * 0.15 * leverage_penalty)
        curtailed_capex = round(capex_safe * (1.0 - hoarding_intensity), 2)
        curtailment_pct = round(hoarding_intensity * 100.0, 1)

        # 4. 流动性储备寿命 (防卫寿命)
        effective_annual_burn = max(1.0, cogs_safe * 0.20 + curtailed_capex)
        if net_cash_pool > 0:
            buffer_months = round((net_cash_pool / (effective_annual_burn / 12.0)), 1)
        else:
            buffer_months = round((max(0.0, inp.cash_and_equivalents) / (effective_annual_burn / 12.0)), 1)

        # 5. 霍尔微观研判总结 (纯自然中文语义，消除英文代号暴露)
        verdict = (
            f"微观加成率 μ={micro_markup:.2f} ({tier_zh})；"
            f"面对复合投入品通胀 +{blended_input_inflation:.1f}%，"
            f"价格转嫁率 {elasticity * 100.0:.0f}%，毛利率受摩擦挤压 {gm_change_pct:+.2f}% (至 {shocked_gm_pct:.1f}%)；"
            f"宏观波动引发预防性流动性囤积，扩张性资本开支预计收缩 {curtailment_pct:.1f}%。"
        )

        # 6. 买方通俗全息研报卡片 (去工程符号化)
        narrative_zh = (
            f"【成本摩擦加成率与流动性防御全息研判】"
            f"定价权护城河评级【{tier_zh}】(微观价格-成本加成率 μ={micro_markup:.2f}倍)。"
            f"成本转嫁与毛利抗性: 面对上游要素复合通胀 +{blended_input_inflation:.1f}%，"
            f"终端售价转嫁弹性为 {elasticity * 100.0:.0f}%，"
            f"测算毛利率承压收缩 {gm_change_pct:+.2f}% (预测承压后毛利率为 {shocked_gm_pct:.1f}%)。"
            f"流动性防御与资本开支: 宏观折现波动驱动预防性现金囤积，"
            f"扩张性资本开支自主收缩 {curtailment_pct:.1f}% (调整后开支金额 {curr_sym}{curtailed_capex:.2f})；"
            f"极限压力情景下现金防卫储备寿命可支撑 {buffer_months:.1f} 个月。"
        )

        return HallFrictionResult(
            micro_markup_ratio=micro_markup,
            pricing_power_tier=tier,
            gross_margin_shock_pct=gm_change_pct,
            shocked_gross_margin_pct=shocked_gm_pct,
            precautionary_capex_curtailment_pct=curtailment_pct,
            curtailed_capex_amount=curtailed_capex,
            liquidity_buffer_resilience_months=buffer_months,
            friction_verdict=verdict,
            pricing_power_tier_zh=tier_zh,
            narrative_zh=narrative_zh,
            currency_symbol=curr_sym,
        )
