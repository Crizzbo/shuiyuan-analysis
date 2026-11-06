"""世界金融一般均衡与全链路定价总控引擎 (World Financial General Equilibrium Engine).

终极架构与全回路闭环:
1. 正向顶层自上而下全息拆解 (Top-Down Decomposition):
   [世界生产总量 + 生产增量]
     │ (索洛-阿吉翁 TFP 增量模型)
     ▼
   [全球 12 行业列昂惕夫投入产出网络]
     │ ((I - A)^(-1) 完全拉动矩阵与各赛道利润池分配)
     ▼
   [微观企业三表增加值映射]
     │ (Direct VA = Revenue - Intermediates = EBITDA + Wages + Taxes)
     ▼
   [居民个人部门要素收益与消费反哺]
     │ (劳动报酬 + 资本分红 => 可支配收入 => 最终消费 C => 闭环拉动 Y)
2. 反向底层自下而上全景聚合与守恒律验证 (Bottom-Up Aggregation & Conservation):
   - 增加值守恒律 (Value Added Invariant): sum(VA_s) == World GDP
   - 要素分配守恒律 (Factor Income Invariant): Wages + Operating Surplus + Taxes == World GDP
   - 宏观最终吸收守恒律 (Absorption Invariant): C + I + G == World GDP
3. 世界金融资产定价无套利检验 (Global Asset Pricing Equilibrium):
   对全人类生产活动所能榨取的全量自由现金流进行内生折现，
   与全球金融资产总市值对比，测算宏观泡沫溢价与定价均衡缺口。
"""

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
)
from .inter_country_trade_engine import (
    InterCountryTradeEngine,
    RegionTradeProfile,
)

ROOT = Path(__file__).resolve().parents[2]


class WorldFinancialEquilibriumEngine:
    """世界金融一般均衡与全回路贯通计算引擎."""

    def __init__(
        self,
        production_benchmark_file: Optional[Path] = None,
        icio_benchmark_file: Optional[Path] = None,
        trade_benchmark_file: Optional[Path] = None,
    ):
        self.production_engine = WorldProductionAggregateEngine(production_benchmark_file)
        self.icio_engine = GlobalInputOutputEngine(icio_benchmark_file)
        self.firm_bridge_engine = FirmValueAddedBridgeEngine()
        self.household_engine = FactorIncomeDistributionEngine()
        self.trade_engine = InterCountryTradeEngine(trade_benchmark_file)

    def run_full_circuit_simulation(
        self,
        # 1. 顶层宏观增量冲击 (Top-Level Macro Shocks)
        tfp_shock_bps: float = 0.0,
        investment_change_pct: float = 0.0,
        labor_supply_change_pct: float = 0.0,
        # 2. 行业特定需求外生拉动 (Industry Demand Shocks)
        sector_demand_shocks: Optional[Dict[str, float]] = None,
        # 3. 开放经济国际贸易与汇率冲击 (Open Economy Trade & FX Shocks)
        tariff_shock_bps: float = 0.0,
        jpy_depreciation_pct: float = 0.0,
        us_demand_shock_trillion: float = 0.0,
        # 4. 待穿透的微观代表企业列表 (Representative Firms)
        representative_firms: Optional[List[FirmFinancialFact]] = None,
        # 5. 全球资产贴现与定价参数 (Asset Pricing Parameters)
        global_wacc: float = 0.075,
        terminal_growth_rate: float = 0.030,
        current_global_equity_market_cap_trillion: float = 115.0,
        listed_equity_coverage_ratio: float = 0.28,
    ) -> Dict[str, Any]:
        """执行从世界生产总量到行业、企业、个人的全电路打通计算，并完成反向守恒核验."""
        shocks = sector_demand_shocks or {}

        # -------------------------------------------------------------
        # STEP 1: 顶层世界生产总量与边际生产增量模拟
        # -------------------------------------------------------------
        prod_result = self.production_engine.simulate_production_shock(
            tfp_shock_bps=tfp_shock_bps,
            investment_change_pct=investment_change_pct,
            labor_supply_change_pct=labor_supply_change_pct,
        )
        base_state = self.production_engine.get_current_state()
        marginal_increment = prod_result["marginal_increment_trillion"]

        # -------------------------------------------------------------
        # STEP 2: 中观行业投入产出与列昂惕夫网络完全拉动求解
        # -------------------------------------------------------------
        icio_result = self.icio_engine.propagate_final_demand_shock(
            sector_demand_shocks=shocks,
            marginal_gdp_increment=marginal_increment,
        )

        # 宏观与行业总需求拉动后的最终世界 GDP (基准 GDP + 全行业增加值增量总和)
        final_sim_gdp = base_state.world_nominal_gdp_trillion + icio_result["total_value_added_increment_trillion"]

        # 建立行业增加值与增量速查映射
        sector_va_growth_map = {}
        sim_va_map = {}
        for s in icio_result["sector_breakdown"]:
            sector_va_growth_map[s["sector_id"]] = s["va_growth_pct"]
            sim_va_map[s["sector_id"]] = s["new_value_added_trillion"]

        # 求解全球 12 大行业的分行业差异化营业盈余、自由现金流与真实公允资产价值
        sector_valuations_result = self.icio_engine.compute_sector_intrinsic_valuations(simulated_va_map=sim_va_map)
        sector_prof_map = {s.sector_id: s for s in self.icio_engine.sectors}

        # -------------------------------------------------------------
        # STEP 2B: 跨国贸易与开放经济出口流转模拟 (Open Economy Exports)
        # -------------------------------------------------------------
        trade_sim = self.trade_engine.simulate_trade_and_fx_shock(
            tariff_shock_bps=tariff_shock_bps,
            jpy_depreciation_pct=jpy_depreciation_pct,
            us_demand_shock_trillion=us_demand_shock_trillion,
        )

        # -------------------------------------------------------------
        # STEP 3: 微观代表性企业增加值穿透与业绩传导 (含出口敞口、存货周期与公允价值测算)
        # -------------------------------------------------------------
        firms_to_process = representative_firms or self._get_default_representative_firms()
        firm_results = []
        firm_valuations = []
        for firm in firms_to_process:
            sec_growth = sector_va_growth_map.get(firm.sector_id, prod_result["simulated_nominal_growth_pct"])
            # 为科技半导体等领军龙头赋予高加价率乘数 (Hall 加价率)
            mu = 1.35 if firm.sector_id == "TECH_SEMI" else (1.20 if firm.sector_id == "HEALTH_BIO" else 1.05)

            # 获取所属经济体的出口外需增速与汇率收益乘数
            ext_growth = trade_sim["region_trade_impacts"].get(firm.country_id, {}).get("export_growth_pct", sec_growth)
            fx_mult = trade_sim["jpy_export_revenue_multiplier"] if firm.country_id == "JP" else 1.0
            # 关税对存货周转天数的潜在拖累 (基点)
            inv_drag = (tariff_shock_bps / 100.0) * 12.0

            impact = self.firm_bridge_engine.map_sector_shock_to_firm(
                firm=firm,
                sector_va_growth_pct=sec_growth,
                firm_pricing_power_mu=mu,
                export_demand_growth_pct=ext_growth,
                fx_shock_multiplier=fx_mult,
                inventory_drag_bps=inv_drag,
            )

            # 结合所属行业的差异化贴现率与永续增长率，穿透测算微观个股的真实公允内在价值
            s_prof = sector_prof_map.get(firm.sector_id)
            sec_wacc = s_prof.benchmark_wacc if s_prof else global_wacc
            sec_g = s_prof.terminal_growth_rate if s_prof else terminal_growth_rate

            firm_val = self.firm_bridge_engine.compute_firm_intrinsic_valuation(
                firm=firm,
                simulated_fcf_million=impact["simulated_fcf_million"],
                sector_wacc=sec_wacc,
                terminal_growth_rate=sec_g,
            )
            impact["intrinsic_valuation"] = firm_val
            firm_results.append(impact)
            firm_valuations.append(firm_val)

        # -------------------------------------------------------------
        # STEP 4: 终端居民个人部门要素收益与消费反哺闭环 (分行业真实盈余加总)
        # -------------------------------------------------------------
        sec_totals = sector_valuations_result["summary_totals"]
        labor_comp = sec_totals["total_labor_wages_trillion"]
        capital_surplus = sec_totals["total_capital_operating_surplus_trillion"]
        net_taxes = sec_totals["total_taxes_trillion"]

        household_result = self.household_engine.compute_household_distribution(
            world_gdp_trillion=final_sim_gdp,
            labor_compensation_trillion=labor_comp,
            capital_operating_surplus_trillion=capital_surplus,
            net_taxes_trillion=net_taxes,
        )

        # -------------------------------------------------------------
        # STEP 5: 反向聚合校验与世界金融无套利资产定价检验
        # -------------------------------------------------------------
        # 1. 守恒律核验
        va_sum = sum(s["new_value_added_trillion"] for s in icio_result["sector_breakdown"])
        factor_sum = labor_comp + capital_surplus + net_taxes

        diff_va = abs(va_sum - final_sim_gdp)
        diff_factor = abs(factor_sum - final_sim_gdp)
        is_trade_conserved = trade_sim["is_global_trade_conserved"]

        is_balanced = (diff_va < 1e-3) and (diff_factor < 1e-3) and is_trade_conserved

        # 2. 全球金融资产定价中枢测算 (World Asset Intrinsic Value)
        # 自下而上分行业加总公允上市股票价值 (Bottom-Up Sum of 12 Sectors)
        bottom_up_equity_fair_val = sec_totals["total_fair_listed_equity_value_trillion"]
        bottom_up_gap_pct = ((current_global_equity_market_cap_trillion - bottom_up_equity_fair_val) / bottom_up_equity_fair_val) * 100.0

        # 自上而下宏观总盈余校准公允价值 (Top-Down Global Capital DCF)
        global_aggregate_fcf_trillion = sec_totals["total_annual_fcf_trillion"]
        discount_gap = max(0.01, global_wacc - terminal_growth_rate)
        intrinsic_total_capital_value = (global_aggregate_fcf_trillion * (1.0 + terminal_growth_rate)) / discount_gap

        cov_ratio = max(0.05, min(1.0, listed_equity_coverage_ratio))
        fair_intrinsic_listed_equity_value = intrinsic_total_capital_value * cov_ratio
        top_down_gap_pct = ((current_global_equity_market_cap_trillion - fair_intrinsic_listed_equity_value) / fair_intrinsic_listed_equity_value) * 100.0

        return {
            "meta": {
                "engine_version": "1.2.0",
                "framework": "World General Equilibrium SNA-Leontief-Solow-Trade Differentiated Pricing Closed Circuit",
            },
            "step1_world_production_macro": {
                "simulated_world_gdp_trillion": round(final_sim_gdp, 4),
                "marginal_increment_trillion": round(final_sim_gdp - base_state.world_nominal_gdp_trillion, 4),
                "real_growth_pct": prod_result["simulated_real_growth_pct"],
                "nominal_growth_pct": prod_result["simulated_nominal_growth_pct"],
                "growth_breakdown": prod_result["growth_source_decomposition"],
            },
            "step2_middle_industry_leontief": {
                "total_gross_output_expansion_trillion": icio_result["total_gross_output_expansion_trillion"],
                "global_output_multiplier": icio_result["global_output_multiplier"],
                "sector_results_summary": [
                    {
                        "sector_id": s["sector_id"],
                        "name_zh": s["name_zh"],
                        "new_va_trillion": s["new_value_added_trillion"],
                        "va_growth_pct": s["va_growth_pct"],
                    }
                    for s in icio_result["sector_breakdown"]
                ],
                "sector_intrinsic_valuations": sector_valuations_result["sectors"],
                "sector_totals": sector_valuations_result["summary_totals"],
            },
            "step2b_open_economy_trade_and_exports": {
                "total_world_gross_trade_trillion": trade_sim["total_simulated_world_gross_trade_trillion"],
                "world_net_exports_sum_trillion": trade_sim["world_net_exports_balance_check_trillion"],
                "is_trade_strictly_conserved": trade_sim["is_global_trade_conserved"],
                "jpy_export_revenue_multiplier": trade_sim["jpy_export_revenue_multiplier"],
                "region_trade_impacts": trade_sim["region_trade_impacts"],
            },
            "step3_micro_firm_transmission": firm_results,
            "step3_micro_firm_intrinsic_valuations": firm_valuations,
            "step4_household_personal_distribution": {
                "total_wages_trillion": household_result["household_income_breakdown"]["gross_wages_trillion"],
                "capital_dividends_interest_trillion": household_result["household_income_breakdown"]["capital_payouts_dividends_interest_trillion"],
                "net_disposable_income_trillion": household_result["household_income_breakdown"]["net_disposable_income_trillion"],
                "household_final_consumption_trillion": household_result["household_absorption_behavior"]["household_final_consumption_c_trillion"],
                "household_savings_trillion": household_result["household_absorption_behavior"]["household_savings_s_trillion"],
                "gross_capital_formation_i_trillion": household_result["financial_intermediation_and_investment"]["gross_capital_formation_i_trillion"],
                "government_expenditure_g_trillion": household_result["financial_intermediation_and_investment"]["government_expenditure_g_trillion"],
                "total_domestic_absorption_c_plus_i_plus_g_trillion": household_result["financial_intermediation_and_investment"]["total_domestic_absorption_c_plus_i_plus_g_trillion"],
                "average_annual_wage_usd": household_result["per_capita_metrics"]["average_annual_wage_usd"],
            },
            "step5_reverse_aggregation_and_equilibrium": {
                "conservation_invariants": {
                    "world_gdp_target_trillion": round(final_sim_gdp, 4),
                    "sum_of_sector_value_added_trillion": round(va_sum, 4),
                    "sum_of_factor_incomes_trillion": round(factor_sum, 4),
                    "is_value_added_conserved": (diff_va < 1e-3),
                    "is_factor_income_conserved": (diff_factor < 1e-3),
                    "is_global_trade_conserved": is_trade_conserved,
                    "is_planetary_absorption_strictly_conserved": household_result["financial_intermediation_and_investment"]["strict_macro_closure"]["is_strict_planetary_absorption_balanced"],
                    "absorption_leakage_gap_trillion": household_result["financial_intermediation_and_investment"]["strict_macro_closure"]["planetary_absorption_leakage_gap_trillion"],
                    "all_invariants_strictly_passed": is_balanced,
                },
                "world_financial_asset_pricing": {
                    "global_annual_fcf_trillion": round(global_aggregate_fcf_trillion, 3),
                    "bottom_up_sector_listed_equity_fair_value_trillion": round(bottom_up_equity_fair_val, 2),
                    "bottom_up_valuation_gap_pct": round(bottom_up_gap_pct, 2),
                    "two_stage_bottom_up_sector_listed_equity_fair_value_trillion": sec_totals.get("two_stage_total_fair_listed_equity_value_trillion", round(bottom_up_equity_fair_val, 2)),
                    "top_down_macro_equity_fair_value_trillion": round(fair_intrinsic_listed_equity_value, 2),
                    "top_down_valuation_gap_pct": round(top_down_gap_pct, 2),
                    "current_global_equity_market_cap_trillion": current_global_equity_market_cap_trillion,
                    "macro_valuation_status": (
                        "合理公允区间 (Fair Equilibrium)" if abs(bottom_up_gap_pct) <= 10.0 else
                        ("泡沫透支预警 (Overvalued Bubble)" if bottom_up_gap_pct > 10.0 else "低估击球区 (Undervalued)")
                    ),
                }
            }
        }

    def _get_default_representative_firms(self) -> List[FirmFinancialFact]:
        """获取典型代表性跨国巨头财务事实数据 (美日核心标的，含海外敞口与存货周期)."""
        return [
            # 1. 半导体算力龙头 (NVDA)
            FirmFinancialFact(
                ticker="NVDA",
                company_name="NVIDIA Corporation",
                market="US",
                sector_id="TECH_SEMI",
                revenue_million=120000.0,
                cogs_million=31200.0,
                operating_expenses_million=13800.0,
                ebitda_million=78000.0,
                wages_and_salaries_million=8500.0,
                taxes_paid_million=9200.0,
                capex_million=5500.0,
                annual_fcf_million=54500.0,
                market_cap_billion=3300.0,
                country_id="US",
                foreign_revenue_ratio=0.72,
                fx_sensitivity_elasticity=0.20,
                inventory_turnover_days_dio=75.0,
            ),
            # 2. 东证半导体设备胜负手 (8035 东京电子)
            FirmFinancialFact(
                ticker="8035",
                company_name="Tokyo Electron",
                market="JP",
                sector_id="TECH_SEMI",
                revenue_million=18500.0,
                cogs_million=10200.0,
                operating_expenses_million=3200.0,
                ebitda_million=5500.0,
                wages_and_salaries_million=1800.0,
                taxes_paid_million=950.0,
                capex_million=850.0,
                annual_fcf_million=3600.0,
                market_cap_billion=78.0,
                country_id="JP",
                foreign_revenue_ratio=0.86,
                fx_sensitivity_elasticity=0.90,
                inventory_turnover_days_dio=85.0,
            ),
            # 3. 医药健康创新巨头 (LLY 礼来)
            FirmFinancialFact(
                ticker="LLY",
                company_name="Eli Lilly and Company",
                market="US",
                sector_id="HEALTH_BIO",
                revenue_million=42000.0,
                cogs_million=8400.0,
                operating_expenses_million=18500.0,
                ebitda_million=16800.0,
                wages_and_salaries_million=6200.0,
                taxes_paid_million=2100.0,
                capex_million=3800.0,
                annual_fcf_million=11500.0,
                market_cap_billion=780.0,
                country_id="US",
                foreign_revenue_ratio=0.45,
                fx_sensitivity_elasticity=0.15,
                inventory_turnover_days_dio=60.0,
            ),
            # 4. 汽车与重型装备龙头 (7203 丰田汽车)
            FirmFinancialFact(
                ticker="7203",
                company_name="Toyota Motor Corporation",
                market="JP",
                sector_id="CAP_GOODS",
                revenue_million=285000.0,
                cogs_million=228000.0,
                operating_expenses_million=28000.0,
                ebitda_million=36000.0,
                wages_and_salaries_million=18500.0,
                taxes_paid_million=6800.0,
                capex_million=14500.0,
                annual_fcf_million=15200.0,
                market_cap_billion=260.0,
                country_id="JP",
                foreign_revenue_ratio=0.82,
                fx_sensitivity_elasticity=0.95,
                inventory_turnover_days_dio=45.0,
            ),
            # 5. 电网基础设施与先进工业 (6501 日立制作所)
            FirmFinancialFact(
                ticker="6501",
                company_name="Hitachi, Ltd.",
                market="JP",
                sector_id="CAP_GOODS",
                revenue_million=68000.0,
                cogs_million=47600.0,
                operating_expenses_million=12500.0,
                ebitda_million=9500.0,
                wages_and_salaries_million=7200.0,
                taxes_paid_million=1400.0,
                capex_million=2800.0,
                annual_fcf_million=5300.0,
                market_cap_billion=120.0,
                country_id="JP",
                foreign_revenue_ratio=0.55,
                fx_sensitivity_elasticity=0.60,
                inventory_turnover_days_dio=58.0,
            )
        ]
