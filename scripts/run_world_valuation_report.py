"""运行世界金融一般均衡全盘计算并输出 12 大行业与代表个股真实公允价值."""
import json
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.world_financial_equilibrium_engine import WorldFinancialEquilibriumEngine

def main():
    engine = WorldFinancialEquilibriumEngine()

    # 1. 现存真实基准场景 (Baseline: World GDP = $110.0T)
    res_base = engine.run_full_circuit_simulation(
        tfp_shock_bps=0.0,
        investment_change_pct=0.0,
        sector_demand_shocks={},
        tariff_shock_bps=0.0,
        jpy_depreciation_pct=0.0,
        us_demand_shock_trillion=0.0,
    )

    # 2. 宏观增量与产业链外生冲击场景 (Shocked: AI TFP + 跨国贸易重构)
    res_shock = engine.run_full_circuit_simulation(
        tfp_shock_bps=40.0,
        investment_change_pct=3.0,
        sector_demand_shocks={"TECH_SEMI": 0.4, "HEALTH_BIO": 0.2},
        tariff_shock_bps=100.0,
        jpy_depreciation_pct=8.0,
        us_demand_shock_trillion=0.5,
    )

    print("=" * 115)
    print("[场景 1] 当前全球宏观现实基准均衡 (World Macro Baseline: GDP = $110.00 万亿美元)")
    print("=" * 115)
    base_tot = res_base["step2_middle_industry_leontief"]["sector_totals"]
    print(f"总增加值 (GDP): ${base_tot['total_value_added_trillion']:.2f}T | 资本营业盈余: ${base_tot['total_capital_operating_surplus_trillion']:.2f}T | 劳动报酬: ${base_tot['total_labor_wages_trillion']:.2f}T | 生产税: ${base_tot['total_taxes_trillion']:.2f}T")
    print(f"全人类生产实体自由现金流: ${base_tot['total_annual_fcf_trillion']:.2f}T | 单阶段股票公允值: ${base_tot['total_fair_listed_equity_value_trillion']:.2f}T | 两阶段内生收敛公允值: ${base_tot['two_stage_total_fair_listed_equity_value_trillion']:.2f}T")
    p_base = res_base["step5_reverse_aggregation_and_equilibrium"]["world_financial_asset_pricing"]
    inv_base = res_base["step5_reverse_aggregation_and_equilibrium"]["conservation_invariants"]
    print(f"现存股市市值: ${p_base['current_global_equity_market_cap_trillion']:.2f}T | 估值偏离度: {p_base['bottom_up_valuation_gap_pct']:+.2f}% | 严格行星吸收平账: {inv_base['is_planetary_absorption_strictly_conserved']} | 状态: 【{p_base['macro_valuation_status']}】\n")

    print("=" * 125)
    print("[行业估值] 基准场景全球 12 大宏观行业差异化营业盈余、内生 ROIC 与两阶段真实公允价值")
    print("=" * 125)
    header = f"{'行业代码':<10} | {'行业名称':<18} | {'增加值 VA':<9} | {'盈余率':<7} | {'FCF转化':<8} | {'隐含ROIC':<8} | {'WACC':<6} | {'单阶段公允估值':<14} | {'两阶段收敛估值':<14}"
    print(header)
    print("-" * 125)
    for s in res_base["step2_middle_industry_leontief"]["sector_intrinsic_valuations"]:
        line = (
            f"{s['sector_id']:<10} | "
            f"{s['name_zh'][:10]:<18} | "
            f"${s['value_added_trillion']:>5.2f}T   | "
            f"{s['surplus_rate_pct']:>5.1f}% | "
            f"{s['fcf_conversion_pct']:>6.1f}% | "
            f"{s['implied_roic_pct']:>6.1f}% | "
            f"{s['benchmark_wacc_pct']:>4.1f}% | "
            f"${s['fair_listed_equity_value_trillion']:>8.2f} 万亿    | "
            f"${s['two_stage_fair_listed_equity_value_trillion']:>8.2f} 万亿"
        )
        print(line)

    print("\n" + "=" * 125)
    print("[个股估值] 基准场景微观代表性个股真实内在公允价值 (Baseline Firm Intrinsic Valuation Matrix)")
    print("=" * 125)
    f_header = f"{'代码':<6} | {'公司名称':<16} | {'市场':<4} | {'所属行业':<10} | {'当前市值':<10} | {'悲观安全底价':<12} | {'基准真实公允值':<12} | {'两阶段收敛公允值':<14} | {'隐含ROIC':<8} | {'机构评级研判'}"
    print(f_header)
    print("-" * 125)
    for f in res_base["step3_micro_firm_intrinsic_valuations"]:
        ts_val = f["two_stage_valuation"]["two_stage_fair_value_billion"]
        roic = f["endogenous_capital_consistency"]["implied_roic_pct"]
        f_line = (
            f"{f['ticker']:<6} | "
            f"{f['company_name'][:14]:<16} | "
            f"{f['market']:<4} | "
            f"{f['sector_id']:<10} | "
            f"${f['current_market_cap_billion']:>7.1f}B | "
            f"${f['pessimistic_floor_value_billion']:>9.1f}B   | "
            f"${f['fair_intrinsic_value_billion']:>9.1f}B   | "
            f"${ts_val:>11.1f}B   | "
            f"{roic:>6.1f}% | "
            f"{f['institutional_verdict']}"
        )
        print(f_line)

    print("\n" + "=" * 115)
    print("[场景 2] AI 全要素生产率爆发与全球贸易重构冲击 (Shocked: AI TFP + 跨国关税与汇率重构)")
    print("=" * 115)
    shock_tot = res_shock["step2_middle_industry_leontief"]["sector_totals"]
    print(f"总增加值 (GDP): ${shock_tot['total_value_added_trillion']:.2f}T | 资本营业盈余: ${shock_tot['total_capital_operating_surplus_trillion']:.2f}T | 劳动报酬: ${shock_tot['total_labor_wages_trillion']:.2f}T | 生产税: ${shock_tot['total_taxes_trillion']:.2f}T")
    print(f"全人类生产实体自由现金流: ${shock_tot['total_annual_fcf_trillion']:.2f}T | 单阶段股票公允值: ${shock_tot['total_fair_listed_equity_value_trillion']:.2f}T | 两阶段内生收敛公允值: ${shock_tot['two_stage_total_fair_listed_equity_value_trillion']:.2f}T")
    p_shock = res_shock["step5_reverse_aggregation_and_equilibrium"]["world_financial_asset_pricing"]
    inv_shock = res_shock["step5_reverse_aggregation_and_equilibrium"]["conservation_invariants"]
    print(f"现存股市市值: ${p_shock['current_global_equity_market_cap_trillion']:.2f}T | 估值偏离度: {p_shock['bottom_up_valuation_gap_pct']:+.2f}% | 严格行星吸收平账: {inv_shock['is_planetary_absorption_strictly_conserved']} | 状态: 【{p_shock['macro_valuation_status']}】\n")

    print("=" * 125)
    print("[冲击场景] 微观代表性个股估值响应对比 (Shock Scenario Firm Valuation Responses)")
    print("=" * 125)
    print(f_header)
    print("-" * 125)
    for f in res_shock["step3_micro_firm_intrinsic_valuations"]:
        ts_val = f["two_stage_valuation"]["two_stage_fair_value_billion"]
        roic = f["endogenous_capital_consistency"]["implied_roic_pct"]
        f_line = (
            f"{f['ticker']:<6} | "
            f"{f['company_name'][:14]:<16} | "
            f"{f['market']:<4} | "
            f"{f['sector_id']:<10} | "
            f"${f['current_market_cap_billion']:>7.1f}B | "
            f"${f['pessimistic_floor_value_billion']:>9.1f}B   | "
            f"${f['fair_intrinsic_value_billion']:>9.1f}B   | "
            f"${ts_val:>11.1f}B   | "
            f"{roic:>6.1f}% | "
            f"{f['institutional_verdict']}"
        )
        print(f_line)

if __name__ == "__main__":
    main()
