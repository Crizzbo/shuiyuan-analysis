"""全球列昂惕夫投入产出与中观行业传导引擎 (Global Leontief Input-Output Engine).

理论基础与数学架构:
1. 列昂惕夫投入产出平衡方程 (Leontief Balance Equation):
   X = A * X + Y  ==>  (I - A) * X = Y  ==>  X = (I - A)^(-1) * Y
   其中 X 为各行业总产出向量，Y 为各行业最终需求向量，A 为直接消耗系数矩阵。
2. 霍金斯-西蒙条件 (Hawkins-Simon Condition):
   矩阵 (I - A) 的各阶顺序主子式全为正，且 A 的谱半径 rho(A) < 1.0，确保经济系统具备现实再生产能力。
3. 增加值生成与分配恒等式:
   VA_j = v_j * X_j，其中 v_j = 1 - sum_{i=1}^n a_{ij} 为行业增加值率。
   sum_{j=1}^n VA_j 严格等于 sum_{j=1}^n Y_j == World GDP。
"""

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class SectorProfile:
    """细分宏观行业投入产出与资本资产档案."""
    sector_id: str
    name_zh: str
    name_en: str
    value_added_trillion: float
    gross_output_trillion: float
    value_added_ratio: float
    final_demand_trillion: float
    capital_operating_surplus_share_ratio: float = 0.38
    labor_compensation_share_ratio: float = 0.53
    taxes_on_production_share_ratio: float = 0.09
    fcf_conversion_ratio: float = 0.42
    benchmark_wacc: float = 0.075
    terminal_growth_rate: float = 0.028
    public_listing_ratio: float = 0.20


class GlobalInputOutputEngine:
    """全球投入产出与产业链完全拉动引擎."""

    DEFAULT_BENCHMARK_PATH = ROOT / "data" / "macro" / "global_input_output_benchmark.json"

    def __init__(self, benchmark_file: Optional[Path] = None):
        self.benchmark_path = benchmark_file or self.DEFAULT_BENCHMARK_PATH
        self.sectors: List[SectorProfile] = []
        self.sector_ids: List[str] = []
        self.A_matrix: np.ndarray = np.array([])
        self.leontief_inverse: np.ndarray = np.array([])
        self.Y_vector: np.ndarray = np.array([])
        self.X_vector: np.ndarray = np.array([])
        self.V_ratios: np.ndarray = np.array([])
        self._load_and_compile()

    def _load_and_compile(self) -> None:
        """加载 ICIO 数据并编译列昂惕夫逆矩阵 (I - A)^(-1)."""
        with open(self.benchmark_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.sectors = []
        self.sector_ids = []
        v_list = []
        y_list = []
        x_list = []

        for s in data["sectors"]:
            sid = s["sector_id"]
            self.sector_ids.append(sid)
            self.sectors.append(SectorProfile(
                sector_id=sid,
                name_zh=s["sector_name_zh"],
                name_en=s["sector_name_en"],
                value_added_trillion=float(s["value_added_trillion_usd"]),
                gross_output_trillion=float(s["gross_output_trillion_usd"]),
                value_added_ratio=float(s["value_added_ratio"]),
                final_demand_trillion=float(s["final_demand_trillion_usd"]),
                capital_operating_surplus_share_ratio=float(s.get("capital_operating_surplus_share_ratio", 0.38)),
                labor_compensation_share_ratio=float(s.get("labor_compensation_share_ratio", 0.53)),
                taxes_on_production_share_ratio=float(s.get("taxes_on_production_share_ratio", 0.09)),
                fcf_conversion_ratio=float(s.get("fcf_conversion_ratio", 0.42)),
                benchmark_wacc=float(s.get("benchmark_wacc", 0.075)),
                terminal_growth_rate=float(s.get("terminal_growth_rate", 0.028)),
                public_listing_ratio=float(s.get("public_listing_ratio", 0.20)),
            ))
            v_list.append(float(s["value_added_ratio"]))
            y_list.append(float(s["final_demand_trillion_usd"]))
            x_list.append(float(s["gross_output_trillion_usd"]))

        n = len(self.sector_ids)
        A = np.zeros((n, n), dtype=np.float64)
        coeff_dict = data["direct_requirement_coefficients_a"]
        for row_idx, sid in enumerate(self.sector_ids):
            row_vals = coeff_dict.get(sid, [0.0] * n)
            A[row_idx, :] = np.array(row_vals[:n], dtype=np.float64)

        self.A_matrix = A
        self.V_ratios = np.array(v_list, dtype=np.float64)
        self.Y_vector = np.array(y_list, dtype=np.float64)
        self.X_vector = np.array(x_list, dtype=np.float64)

        # 检查霍金斯-西蒙条件: A 的谱半径必须小于 1.0
        eigvals = np.linalg.eigvals(A)
        spectral_radius = float(np.max(np.abs(eigvals)))
        if spectral_radius >= 1.0:
            raise ValueError(f"直接消耗矩阵 A 违反霍金斯-西蒙稳定性条件，谱半径 {spectral_radius:.4f} >= 1.0")

        # 求解列昂惕夫逆矩阵 L = (I - A)^(-1)
        I = np.eye(n, dtype=np.float64)
        self.leontief_inverse = np.linalg.inv(I - A)

    def get_sector_profiles(self) -> List[SectorProfile]:
        """获取所有细分行业概览列表."""
        return self.sectors

    def get_leontief_multiplier_table(self) -> Dict[str, Any]:
        """获取各行业的完全产出拉动乘数 (Output Multiplier).

        完全拉动乘数定义为列昂惕夫逆矩阵的列和，代表某行业最终需求增加 1 单位时，
        对全社会所有产业链上下游引发的总产出扩张倍数。
        """
        multipliers = np.sum(self.leontief_inverse, axis=0)
        res = {}
        for idx, sid in enumerate(self.sector_ids):
            res[sid] = {
                "name_zh": self.sectors[idx].name_zh,
                "output_multiplier": round(float(multipliers[idx]), 3),
                "direct_va_ratio": round(float(self.V_ratios[idx]), 3),
            }
        return res

    def compute_sector_intrinsic_valuations(
        self,
        simulated_va_map: Optional[Dict[str, float]] = None,
        stage1_years: int = 5,
        terminal_growth_cap: float = 0.030,
    ) -> Dict[str, Any]:
        """计算全球 12 大细分宏观行业的分行业差异化营业盈余、自由现金流与真实公允资产价值 (含戈登与两阶段折现及内生ROIC)."""
        sector_valuations = []
        tot_va = 0.0
        tot_surplus = 0.0
        tot_labor = 0.0
        tot_taxes = 0.0
        tot_fcf = 0.0
        tot_enterprise_val = 0.0
        tot_listed_equity_val = 0.0
        tot_two_stage_enterprise_val = 0.0
        tot_two_stage_listed_equity_val = 0.0

        for s in self.sectors:
            va = simulated_va_map.get(s.sector_id, s.value_added_trillion) if simulated_va_map else s.value_added_trillion
            surplus = va * s.capital_operating_surplus_share_ratio
            labor = va * s.labor_compensation_share_ratio
            taxes = va * s.taxes_on_production_share_ratio
            fcf = surplus * s.fcf_conversion_ratio

            # 1. 传统戈登单阶段折现 (Gordon Growth Model)
            discount_gap = max(0.008, s.benchmark_wacc - s.terminal_growth_rate)
            enterprise_val = (fcf * (1.0 + s.terminal_growth_rate)) / discount_gap
            listed_equity_val = enterprise_val * s.public_listing_ratio

            # 2. 内生收敛的两阶段有限生命折现模型 (Two-Stage Finite-Horizon Convergence DCF)
            # 阶段一: 5年显式高增长阶段 g_1; 阶段二: 平滑收敛至世界潜在名义增速 g_inf
            g1 = s.terminal_growth_rate
            wacc = s.benchmark_wacc
            g_inf = min(g1, terminal_growth_cap)
            T = max(1, stage1_years)

            if abs(wacc - g1) < 1e-4:
                pv_stage1 = fcf * T
            else:
                beta = (1.0 + g1) / (1.0 + wacc)
                pv_stage1 = fcf * ((1.0 + g1) / (wacc - g1)) * (1.0 - (beta ** T))

            tv_T = (fcf * ((1.0 + g1) ** T) * (1.0 + g_inf)) / max(0.008, wacc - g_inf)
            pv_tv = tv_T / ((1.0 + wacc) ** T)
            two_stage_ent_val = pv_stage1 + pv_tv
            two_stage_listed_val = two_stage_ent_val * s.public_listing_ratio

            # 3. 达摩达兰资本再投资守恒律: 隐含投入资本回报率 Implied ROIC = g / (1 - FCF_conv)
            reinvestment_rate = max(0.01, 1.0 - s.fcf_conversion_ratio)
            implied_roic = (s.terminal_growth_rate / reinvestment_rate) * 100.0

            tot_va += va
            tot_surplus += surplus
            tot_labor += labor
            tot_taxes += taxes
            tot_fcf += fcf
            tot_enterprise_val += enterprise_val
            tot_listed_equity_val += listed_equity_val
            tot_two_stage_enterprise_val += two_stage_ent_val
            tot_two_stage_listed_equity_val += two_stage_listed_val

            sector_valuations.append({
                "sector_id": s.sector_id,
                "name_zh": s.name_zh,
                "name_en": s.name_en,
                "value_added_trillion": round(va, 3),
                "capital_operating_surplus_trillion": round(surplus, 3),
                "surplus_rate_pct": round(s.capital_operating_surplus_share_ratio * 100.0, 1),
                "labor_wages_trillion": round(labor, 3),
                "labor_share_pct": round(s.labor_compensation_share_ratio * 100.0, 1),
                "taxes_trillion": round(taxes, 3),
                "tax_share_pct": round(s.taxes_on_production_share_ratio * 100.0, 1),
                "annual_fcf_trillion": round(fcf, 3),
                "fcf_conversion_pct": round(s.fcf_conversion_ratio * 100.0, 1),
                "reinvestment_rate_pct": round(reinvestment_rate * 100.0, 1),
                "implied_roic_pct": round(implied_roic, 2),
                "benchmark_wacc_pct": round(s.benchmark_wacc * 100.0, 2),
                "terminal_growth_pct": round(s.terminal_growth_rate * 100.0, 2),
                "total_sector_capital_value_trillion": round(enterprise_val, 2),
                "two_stage_sector_capital_value_trillion": round(two_stage_ent_val, 2),
                "public_listing_ratio_pct": round(s.public_listing_ratio * 100.0, 1),
                "fair_listed_equity_value_trillion": round(listed_equity_val, 2),
                "two_stage_fair_listed_equity_value_trillion": round(two_stage_listed_val, 2),
            })

        return {
            "summary_totals": {
                "total_value_added_trillion": round(tot_va, 3),
                "total_capital_operating_surplus_trillion": round(tot_surplus, 3),
                "total_labor_wages_trillion": round(tot_labor, 3),
                "total_taxes_trillion": round(tot_taxes, 3),
                "total_annual_fcf_trillion": round(tot_fcf, 3),
                "total_world_capital_enterprise_value_trillion": round(tot_enterprise_val, 2),
                "total_fair_listed_equity_value_trillion": round(tot_listed_equity_val, 2),
                "two_stage_total_fair_listed_equity_value_trillion": round(tot_two_stage_listed_equity_val, 2),
                "effective_global_fcf_conversion_pct": round((tot_fcf / max(1e-6, tot_surplus)) * 100.0, 2),
                "effective_global_listing_ratio_pct": round((tot_listed_equity_val / max(1e-6, tot_enterprise_val)) * 100.0, 2),
            },
            "sectors": sector_valuations,
        }

    def solve_leontief_dual_price_system(
        self,
        delta_unit_va_costs: Dict[str, float],
    ) -> Dict[str, Any]:
        """求解列昂惕夫投入产出对偶价格体系 (Leontief Dual Price Model).

        数学推导:
        P = A^T * P + V_p  ==>  (I - A^T) * P = V_p  ==>  P = (I - A^T)^(-1) * V_p
        当某上游行业单位增加值成本发生变动 (例如 AI 芯片降价 delta_Vp < 0)，
        通过供应链消耗网络全息传导下游各产业的价格冲击:
        delta_P = (I - A^T)^(-1) * delta_Vp
        """
        n = len(self.sector_ids)
        dVp = np.zeros(n, dtype=np.float64)
        for sid, shock in delta_unit_va_costs.items():
            if sid in self.sector_ids:
                idx = self.sector_ids.index(sid)
                dVp[idx] = float(shock)

        # 列昂惕夫对偶价格逆矩阵 L_price = (I - A^T)^(-1) == (L)^T
        dual_inverse = np.linalg.inv(np.eye(n, dtype=np.float64) - self.A_matrix.T)
        dP = dual_inverse @ dVp

        sector_price_responses = []
        for idx, sid in enumerate(self.sector_ids):
            s = self.sectors[idx]
            sector_price_responses.append({
                "sector_id": sid,
                "name_zh": s.name_zh,
                "direct_cost_shock_pct": round(float(dVp[idx]) * 100.0, 3),
                "supply_chain_price_impact_pct": round(float(dP[idx]) * 100.0, 3),
            })

        return {
            "dual_price_multiplier_spectral_radius": round(float(np.max(np.abs(np.linalg.eigvals(self.A_matrix.T)))), 4),
            "sector_price_responses": sector_price_responses,
        }

    def adjust_factor_shares_with_markup(
        self,
        sector_markups: Dict[str, float],
    ) -> Dict[str, Any]:
        """根据霍尔-巴苏-弗纳尔德加价率 (Hall Markup mu) 修正中观行业要素分配份额.

        数学推导 (Euler's Exhaustion with Markup):
        厂商一阶条件: W*L / (P*Y) = alpha_L / mu
        超额纯垄断利润地租占增加值份额: pi* = (1 - 1/mu) * theta_L
        修正后:
        theta_L* = theta_L / mu
        theta_K* = theta_K + (1 - 1/mu) * theta_L
        严格守恒: theta_K* + theta_L* + theta_T == 1.0
        """
        adjusted_sectors = []
        for s in self.sectors:
            mu = max(1.0, sector_markups.get(s.sector_id, 1.0))
            old_k = s.capital_operating_surplus_share_ratio
            old_l = s.labor_compensation_share_ratio
            old_t = s.taxes_on_production_share_ratio

            new_l = old_l / mu
            pure_rents = old_l * (1.0 - 1.0 / mu)
            new_k = old_k + pure_rents

            diff = abs((new_k + new_l + old_t) - 1.0)
            assert diff < 1e-6, "加价率要素调整必须严格守恒"

            adjusted_sectors.append({
                "sector_id": s.sector_id,
                "name_zh": s.name_zh,
                "markup_mu": round(mu, 2),
                "pure_economic_rents_share_pct": round(pure_rents * 100.0, 2),
                "adjusted_capital_surplus_share_pct": round(new_k * 100.0, 2),
                "adjusted_labor_share_pct": round(new_l * 100.0, 2),
                "tax_share_pct": round(old_t * 100.0, 2),
            })

        return {
            "framework": "Hall-Basu-Fernald Markup-Adjusted Factor Income Distribution",
            "sectors": adjusted_sectors,
        }

    def propagate_final_demand_shock(
        self,
        sector_demand_shocks: Dict[str, float],
        marginal_gdp_increment: Optional[float] = None,
    ) -> Dict[str, Any]:
        """测算特定行业或全球总量边际需求冲击通过投入产出网络的全局传导.

        参数:
        - sector_demand_shocks: 行业特定最终需求增量 (万亿美元)，例如 {"TECH_SEMI": 0.5, "INFRA_UTIL": 0.3}
        - marginal_gdp_increment: 若提供全球宏观生产增量，自动按现存最终需求权重同比例分解至全行业
        """
        n = len(self.sector_ids)
        dY = np.zeros(n, dtype=np.float64)

        # 1. 处理全球宏观生产增量的比例分配
        if marginal_gdp_increment is not None and marginal_gdp_increment > 0:
            total_y = np.sum(self.Y_vector)
            dY += self.Y_vector * (marginal_gdp_increment / total_y)

        # 2. 叠加行业特定冲击
        for sid, shock in sector_demand_shocks.items():
            if sid in self.sector_ids:
                idx = self.sector_ids.index(sid)
                dY[idx] += float(shock)

        # 3. 列昂惕夫网络完全拉动求解: dX = (I - A)^(-1) * dY
        dX = self.leontief_inverse @ dY

        # 4. 行业增加值增量与产业链各环节利润池求解
        dVA = self.V_ratios * dX

        sector_results = []
        for idx, sid in enumerate(self.sector_ids):
            s = self.sectors[idx]
            new_x = float(self.X_vector[idx] + dX[idx])
            new_va = float(s.value_added_trillion + dVA[idx])
            va_growth_pct = (dVA[idx] / s.value_added_trillion) * 100.0 if s.value_added_trillion > 0 else 0.0

            sector_results.append({
                "sector_id": sid,
                "name_zh": s.name_zh,
                "baseline_va_trillion": s.value_added_trillion,
                "delta_demand_trillion": round(float(dY[idx]), 4),
                "delta_gross_output_trillion": round(float(dX[idx]), 4),
                "delta_value_added_trillion": round(float(dVA[idx]), 4),
                "new_value_added_trillion": round(new_va, 4),
                "va_growth_pct": round(va_growth_pct, 2),
                "simulated_gross_output_trillion": round(new_x, 4),
            })

        total_dY = float(np.sum(dY))
        total_dX = float(np.sum(dX))
        total_dVA = float(np.sum(dVA))

        # 宏观恒等核验: 全社会增加值总增量必须严格等于最终需求总增量
        assert abs(total_dVA - total_dY) < 1e-4, f"增加值拉动残差过大: dVA={total_dVA}, dY={total_dY}"

        return {
            "total_final_demand_shock_trillion": round(total_dY, 4),
            "total_gross_output_expansion_trillion": round(total_dX, 4),
            "total_value_added_increment_trillion": round(total_dVA, 4),
            "global_output_multiplier": round(total_dX / max(1e-6, total_dY), 3),
            "sector_breakdown": sector_results,
            "is_macro_balanced": True,
        }
