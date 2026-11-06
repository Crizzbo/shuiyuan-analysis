"""世界生产总量与边际生产增量计算引擎 (World Production Aggregate & Marginal Increment Engine).

数学与理论基础:
1. 国民经济核算体系 (UN SNA 2008 / IMF WEO)：
   世界总产出 (World Gross Output, X) 与世界增加值 (World GDP / Value Added, Y) 的宏观等式；
2. 索洛-阿吉翁-霍尔 (Solow-Aghion-Hall) 内生总生产函数：
   Y_t = A_t * K_t^alpha * L_t^(1-alpha)
   边际产出增量 dY_t = Y_t * [ alpha * (dK/K) + (1-alpha) * (dL/L) + (dA/A) ]
3. 要素分配恒等式：
   World GDP 严格等于 全球劳动报酬总额 (Wages) + 全球资本营业盈余 (Gross Operating Surplus / EBITDA) + 生产税净额 (Taxes).
"""

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class WorldProductionState:
    """全球宏观生产总量与要素分配快照."""
    world_nominal_gdp_trillion: float         # 世界名义 GDP (万亿美元)
    world_gross_output_trillion: float        # 世界总产出 / 营业流转总规模 (万亿美元)
    value_added_ratio: float                  # 增加值率 (VALU / PROD)
    real_gdp_growth_rate: float               # 实际经济增速 (如 0.032 代表 3.2%)
    gdp_deflator_inflation: float             # GDP 平减通胀率 (如 0.026 代表 2.6%)
    nominal_growth_rate: float                # 名义总增速
    marginal_increment_trillion: float        # 当期名义生产增量 (万亿美元)
    capital_stock_trillion: float             # 全球资本存量 (万亿美元)
    annual_investment_trillion: float         # 全球资本形成总额 (CapEx / 投资)
    labor_force_billion: float                # 全球就业劳动力总量 (十亿人)
    tfp_annual_growth: float                  # 全要素生产率 (TFP) 增速
    capital_share_alpha: float                # 资本产出弹性 alpha
    labor_share_one_minus_alpha: float        # 劳动产出弹性 1 - alpha

    # 要素分配 (Factor Income Shares)
    labor_compensation_trillion: float        # 劳动总报酬
    capital_operating_surplus_trillion: float # 资本总盈余 (EBITDA / 租金 / 利润)
    net_production_taxes_trillion: float      # 政府生产税及进口税净额


class WorldProductionAggregateEngine:
    """世界生产总量与边际增量分析引擎."""

    DEFAULT_BENCHMARK_PATH = ROOT / "data" / "macro" / "world_production_benchmark.json"

    def __init__(self, benchmark_file: Optional[Path] = None):
        self.benchmark_path = benchmark_file or self.DEFAULT_BENCHMARK_PATH
        self.cached_state: Optional[WorldProductionState] = None
        self._load_benchmark()

    def _load_benchmark(self) -> None:
        """从本地归档的官方基准数据加载世界生产参数."""
        if not self.benchmark_path.exists():
            # 安全默认值兜底 (IMF WEO 2024 基准)
            self.cached_state = WorldProductionState(
                world_nominal_gdp_trillion=110.0,
                world_gross_output_trillion=222.1,
                value_added_ratio=0.4953,
                real_gdp_growth_rate=0.032,
                gdp_deflator_inflation=0.026,
                nominal_growth_rate=0.0588,
                marginal_increment_trillion=6.468,
                capital_stock_trillion=350.0,
                annual_investment_trillion=28.6,
                labor_force_billion=3.65,
                tfp_annual_growth=0.011,
                capital_share_alpha=0.45,
                labor_share_one_minus_alpha=0.55,
                labor_compensation_trillion=58.3,
                capital_operating_surplus_trillion=41.8,
                net_production_taxes_trillion=9.9,
            )
            return

        with open(self.benchmark_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        m = data["world_aggregate_metrics"]
        fid = data["factor_income_distribution"]

        self.cached_state = WorldProductionState(
            world_nominal_gdp_trillion=float(m["world_nominal_gdp_trillion_usd"]),
            world_gross_output_trillion=float(m["world_gross_output_trillion_usd"]),
            value_added_ratio=float(m["value_added_to_gross_output_ratio"]),
            real_gdp_growth_rate=float(m["world_real_gdp_growth_rate"]),
            gdp_deflator_inflation=float(m["world_gdp_deflator_inflation"]),
            nominal_growth_rate=float(m["world_nominal_growth_rate"]),
            marginal_increment_trillion=float(m["marginal_production_increment_trillion_usd"]),
            capital_stock_trillion=float(m["world_capital_stock_trillion_usd"]),
            annual_investment_trillion=float(m["world_gross_capital_formation_trillion_usd"]),
            labor_force_billion=float(m["world_labor_force_billion_persons"]),
            tfp_annual_growth=float(m["tfp_annual_growth_rate"]),
            capital_share_alpha=float(m["capital_elasticity_alpha"]),
            labor_share_one_minus_alpha=float(m["labor_elasticity_one_minus_alpha"]),
            labor_compensation_trillion=float(fid["labor_compensation_trillion_usd"]),
            capital_operating_surplus_trillion=float(fid["capital_operating_surplus_trillion_usd"]),
            net_production_taxes_trillion=float(fid["net_production_taxes_trillion_usd"]),
        )

    def get_current_state(self) -> WorldProductionState:
        """获取当前世界生产基础态."""
        if self.cached_state is None:
            self._load_benchmark()
        return self.cached_state

    def simulate_production_shock(
        self,
        tfp_shock_bps: float = 0.0,
        investment_change_pct: float = 0.0,
        labor_supply_change_pct: float = 0.0,
        inflation_shock_bps: float = 0.0,
    ) -> Dict[str, Any]:
        """测算全要素生产率冲击、全球资本开支或通胀变动对世界总产值及边际增量的外生冲击传导.

        参数:
        - tfp_shock_bps: 全要素生产率额外变动基点 (例如 +50 bps = +0.5% AI算力突破)
        - investment_change_pct: 全球资本开支/投资变动百分比 (如 +5.0%)
        - labor_supply_change_pct: 全球有效劳动力供给变动百分比 (如 -1.0% 老龄化摩擦)
        - inflation_shock_bps: 全球 GDP 平减指数通胀变动基点
        """
        base = self.get_current_state()

        # 1. 实际增长分解 (Solow-Aghion 生产增量)
        delta_tfp = base.tfp_annual_growth + (tfp_shock_bps / 10000.0)
        capital_growth = (base.annual_investment_trillion * (1.0 + investment_change_pct / 100.0) - (base.capital_stock_trillion * 0.05)) / base.capital_stock_trillion
        labor_growth = (labor_supply_change_pct / 100.0)

        sim_real_growth = (
            base.capital_share_alpha * capital_growth
            + base.labor_share_one_minus_alpha * labor_growth
            + delta_tfp
        )
        sim_inflation = max(-0.05, base.gdp_deflator_inflation + (inflation_shock_bps / 10000.0))
        sim_nominal_growth = (1.0 + sim_real_growth) * (1.0 + sim_inflation) - 1.0

        # 2. 测算新的生产总量与边际生产增量
        new_gdp = base.world_nominal_gdp_trillion * (1.0 + sim_nominal_growth)
        marginal_increment = new_gdp - base.world_nominal_gdp_trillion
        new_gross_output = new_gdp / max(0.1, base.value_added_ratio)

        # 3. 要素报酬恒等重配 (保持要素份额中枢稳定)
        sim_labor_comp = new_gdp * (base.labor_compensation_trillion / base.world_nominal_gdp_trillion)
        sim_capital_surplus = new_gdp * (base.capital_operating_surplus_trillion / base.world_nominal_gdp_trillion)
        sim_taxes = new_gdp * (base.net_production_taxes_trillion / base.world_nominal_gdp_trillion)

        # 校验恒等式: Labor + Capital + Taxes == New GDP
        factor_sum = sim_labor_comp + sim_capital_surplus + sim_taxes
        diff = abs(factor_sum - new_gdp)
        assert diff < 1e-6, f"要素分配不平账，残差: {diff}"

        return {
            "baseline_gdp_trillion": base.world_nominal_gdp_trillion,
            "simulated_gdp_trillion": round(new_gdp, 4),
            "marginal_increment_trillion": round(marginal_increment, 4),
            "simulated_gross_output_trillion": round(new_gross_output, 4),
            "simulated_real_growth_pct": round(sim_real_growth * 100.0, 3),
            "simulated_nominal_growth_pct": round(sim_nominal_growth * 100.0, 3),
            "simulated_inflation_pct": round(sim_inflation * 100.0, 3),
            "factor_income_distribution": {
                "labor_compensation_trillion": round(sim_labor_comp, 4),
                "capital_operating_surplus_trillion": round(sim_capital_surplus, 4),
                "net_production_taxes_trillion": round(sim_taxes, 4),
                "is_balanced": True,
            },
            "growth_source_decomposition": {
                "capital_accumulation_contribution_pct": round(base.capital_share_alpha * capital_growth * 100.0, 3),
                "labor_supply_contribution_pct": round(base.labor_share_one_minus_alpha * labor_growth * 100.0, 3),
                "tfp_technology_contribution_pct": round(delta_tfp * 100.0, 3),
            }
        }
