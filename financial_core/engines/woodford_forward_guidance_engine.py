"""伍德福德前瞻指引与自然利率缺口引擎 (Woodford Forward Guidance & Natural Rate Engine).

理论来源与微观基础：
迈克尔·伍德福德 (Michael Woodford, 2026年诺贝尔经济学奖得主) 经典理论：
1. 维克塞尔自然利率缺口 (Wicksellian Natural Rate Gap):
   实际货币政策的紧缩度取决于实际利率偏离中性自然利率 (r*) 的差额：
   Gap = (i - E[pi]) - r*
2. 前瞻指引与纯预期收益率曲线 (Whole Path of Policy Rates):
   折现率不应是单一年化固定值，而是基于央行利率路径预期与期限溢价 (Term Premium) 逐年递进的折现向量：
   y(t) = (1/t) * sum(E[i_k]) + TP(t)
   WACC(t) = (E/V) * Ke(t) + (D/V) * Kd(t) * (1 - tau)
"""

from dataclasses import dataclass, field
import math
from typing import List, Optional, Dict, Any


@dataclass
class WoodfordGuidanceInput:
    """伍德福德前瞻指引计算输入."""
    policy_rate: float                      # 当期央行政策利率 (如 0.050 表示 5.0%)
    expected_inflation_1y: float            # 1年期前瞻通胀预期 (如 0.025 表示 2.5%)
    natural_rate_r_star: float = 0.0125      # 维克塞尔中性自然实际利率 r* (通常 1.0%~1.5%)
    equity_beta: float = 1.0                # 标的资产股权 Beta
    equity_risk_premium: float = 0.055       # 基础股权风险溢价 ERP (如 5.5%)
    debt_to_equity: float = 0.30            # 产权比率 D/E
    credit_spread: float = 0.0180           # 企业信用违约利差 (如 180 bps)
    tax_rate: float = 0.21                  # 有效企业所得税率
    forecast_years: int = 10                # 预测年限 (默认 10 年)
    dot_plot_rate_path: Optional[List[float]] = None # 美联储/央行点阵图预期利率路径


@dataclass
class WoodfordGuidanceResult:
    """伍德福德前瞻指引与期限结构输出."""
    wicksellian_rate_gap_bps: float          # 维克塞尔自然利率缺口 (基点，正=紧缩，负=宽松)
    is_restrictive: bool                     # 是否处于实质性货币紧缩区间
    current_real_rate_pct: float             # 当前实际政策利率 %
    term_premium_10y_bps: float              # 10年期公债内生期限溢价 (基点)
    spot_yield_curve: List[float]            # 1~N 年无风险基准即期利率曲线
    dynamic_wacc_vector: List[float]         # 1~N 年逐年动态内生 WACC 折现率向量
    average_wacc: float                      # 跨期几何平均 WACC 折现率
    cumulative_discount_factors: List[float] # 逐年累积折现因子 [DF_1, DF_2, ..., DF_N]
    monetary_stance_summary: str             # 货币政策立场微观定性总结
    is_monetary_restrictive: bool = False    # 别名兼容字段
    monetary_stance_zh: str = ""             # 货币立场通俗中文命名
    narrative_zh: str = ""                   # 买方通俗全息研报卡片 (去工程符号化)

    def __post_init__(self):
        self.is_monetary_restrictive = self.is_restrictive

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wicksellian_rate_gap_bps": f"{self.wicksellian_rate_gap_bps:+.0f} bps",
            "is_restrictive": self.is_restrictive,
            "monetary_stance_zh": self.monetary_stance_zh or ("货币紧缩" if self.is_restrictive else "中性宽松"),
            "current_real_rate_pct": f"{self.current_real_rate_pct:.2f}%",
            "term_premium_10y_bps": f"{self.term_premium_10y_bps:+.0f} bps",
            "average_wacc": f"{self.average_wacc * 100:.2f}%",
            "first_year_wacc": f"{self.dynamic_wacc_vector[0] * 100:.2f}%" if self.dynamic_wacc_vector else "N/A",
            "terminal_year_wacc": f"{self.dynamic_wacc_vector[-1] * 100:.2f}%" if self.dynamic_wacc_vector else "N/A",
            "verdict": self.monetary_stance_summary,
            "narrative_zh": self.narrative_zh or self.monetary_stance_summary,
        }


class WoodfordForwardGuidanceEngine:
    """伍德福德宏观前瞻指引与期限结构折现引擎."""

    def __init__(self):
        self.version = "1.0.0"

    def evaluate(self, inp: WoodfordGuidanceInput) -> WoodfordGuidanceResult:
        """评估维克塞尔利率缺口并推导逐年动态 WACC 期限折现向量."""
        # 1. 维克塞尔自然利率缺口计算
        real_policy_rate = inp.policy_rate - inp.expected_inflation_1y
        wicksellian_gap = real_policy_rate - inp.natural_rate_r_star
        gap_bps = round(wicksellian_gap * 10000.0, 1)
        is_restrictive = (wicksellian_gap > 0.0005) # 超过 5 bps 视为紧缩

        # 2. 利率预期路径构建 (若无点阵图显式输入，采用对中性利率的均值回归模型)
        horizon = max(3, min(30, inp.forecast_years))
        rate_path: List[float] = []
        neutral_nominal_rate = inp.natural_rate_r_star + inp.expected_inflation_1y

        if inp.dot_plot_rate_path and len(inp.dot_plot_rate_path) > 0:
            for t in range(horizon):
                if t < len(inp.dot_plot_rate_path):
                    rate_path.append(inp.dot_plot_rate_path[t])
                else:
                    # 超出点阵图年限，平滑收敛于中性利率
                    rate_path.append(rate_path[-1] * 0.70 + neutral_nominal_rate * 0.30)
        else:
            # 霍华德-伍德福德预期收敛动态方程: i(t) = i(t-1) + kappa * (neutral - i(t-1))
            speed = 0.35 # 货币政策收敛半衰期速度
            current_i = inp.policy_rate
            for t in range(horizon):
                rate_path.append(current_i)
                current_i = current_i + speed * (neutral_nominal_rate - current_i)

        # 3. 期限溢价模型与即期收益率曲线 y(t)
        # 期限溢价随久期呈非线性对数递增: TP(t) = TP_max * (1 - exp(-t / 3.0))
        tp_max = 0.0120 # 最大期限溢价中枢 120 bps
        spot_curve: List[float] = []
        running_sum = 0.0
        for t in range(1, horizon + 1):
            running_sum += rate_path[t - 1]
            pure_expectation = running_sum / float(t)
            tp_t = tp_max * (1.0 - math.exp(-float(t) / 3.5))
            spot_y = pure_expectation + tp_t
            spot_curve.append(round(spot_y, 5))

        tp_10y_bps = round(tp_max * (1.0 - math.exp(-10.0 / 3.5)) * 10000.0, 1)

        # 4. 资本结构权重与逐年动态 WACC 计算
        d_e = max(0.0, inp.debt_to_equity)
        we = 1.0 / (1.0 + d_e)
        wd = d_e / (1.0 + d_e)
        tax = max(0.0, min(0.50, inp.tax_rate))
        beta = max(0.1, inp.equity_beta)

        dynamic_wacc: List[float] = []
        cumulative_df: List[float] = []
        running_df = 1.0

        for t in range(horizon):
            rf_t = spot_curve[t]
            # 权益成本 Ke(t) = rf(t) + beta * ERP
            ke_t = rf_t + beta * inp.equity_risk_premium
            # 债务成本 Kd(t) = rf(t) + CreditSpread
            kd_t = rf_t + inp.credit_spread
            # 动态 WACC(t)
            wacc_t = we * ke_t + wd * kd_t * (1.0 - tax)
            # 刚性边界防御: 确保 WACC 不低于 3.5%，避免除零与负折现
            wacc_t = max(0.035, wacc_t)
            dynamic_wacc.append(round(wacc_t, 5))

            # 计算逐年累积折现因子: DF_t = DF_{t-1} / (1 + WACC_t)
            running_df = running_df / (1.0 + wacc_t)
            cumulative_df.append(round(running_df, 6))

        # 计算几何平均 WACC
        geom_wacc = (1.0 / (cumulative_df[-1] ** (1.0 / float(horizon)))) - 1.0

        # 5. 政策定性总结与通俗中文研判
        if gap_bps > 100.0:
            stance_zh = "深度货币紧缩走廊"
            summary = (
                f"处于深度货币紧缩区间 (维克塞尔缺口 +{gap_bps:.0f} 基点)；"
                f"实际政策利率 {real_policy_rate * 100.0:.2f}% 显著压制投机乘数，"
                f"前端折现率承压高达 {dynamic_wacc[0] * 100.0:.2f}%，远端逐步释放至 {dynamic_wacc[-1] * 100.0:.2f}%。"
            )
        elif gap_bps < -50.0:
            stance_zh = "实质宽松刺激区间"
            summary = (
                f"处于实质性货币宽松区间 (维克塞尔缺口 {gap_bps:.0f} 基点)；"
                f"实际利率低于中性水平，支撑高久期长尾成长资产估值中枢。"
            )
        else:
            stance_zh = "中性平衡利率走廊"
            summary = (
                f"处于中性货币政策走廊 (维克塞尔缺口 {gap_bps:+.0f} 基点)；"
                f"利率期限结构平稳，平均 WACC 锚定在 {geom_wacc * 100.0:.2f}%。"
            )

        # 6. 买方通俗全息研报卡片 (去工程符号化)
        narrative_zh = (
            f"【央行前瞻指引与自然利率期限折现全息研判】"
            f"宏观货币政策立场【{stance_zh}】(实际自然利率缺口 {gap_bps:+.0f} 基点)。"
            f"政策利率与通胀预期: 当期政策利率 {inp.policy_rate * 100:.2f}%，"
            f"前瞻通胀预期 {inp.expected_inflation_1y * 100:.2f}%，推导实际政策利率 {real_policy_rate * 100:.2f}%。"
            f"公债收益率期限结构: 10年期公债内生期限溢价 +{tp_10y_bps:.0f} 基点，"
            f"跨期全息动态 WACC 折现中枢为 {geom_wacc * 100:.2f}%，"
            f"第 1 年即期折现率 {dynamic_wacc[0] * 100:.2f}% 平滑释放至第 {horizon} 年远端 {dynamic_wacc[-1] * 100:.2f}%。"
        )

        return WoodfordGuidanceResult(
            wicksellian_rate_gap_bps=gap_bps,
            is_restrictive=is_restrictive,
            current_real_rate_pct=round(real_policy_rate * 100.0, 3),
            term_premium_10y_bps=tp_10y_bps,
            spot_yield_curve=spot_curve,
            dynamic_wacc_vector=dynamic_wacc,
            average_wacc=round(geom_wacc, 5),
            cumulative_discount_factors=cumulative_df,
            monetary_stance_summary=summary,
            monetary_stance_zh=stance_zh,
            narrative_zh=narrative_zh,
        )
