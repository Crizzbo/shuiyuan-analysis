"""世界生产总量与全电路端到端金融一般均衡计算测试集 (Unit Tests for World Financial System).

测试矩阵覆盖:
1. WorldProductionAggregateEngine: 索洛-阿吉翁 TFP 增量、要素分配守恒律 (Labor + Capital + Taxes == GDP);
2. GlobalInputOutputEngine: 列昂惕夫逆矩阵 (I - A)^(-1)、霍金斯-西蒙稳定性、完全拉动乘数与需求冲击传导;
3. FirmValueAddedBridgeEngine: 企业增加值直接法与间接法平账、外购中间消耗倒轧与自由现金流转化;
4. FactorIncomeDistributionEngine: 居民部门可支配收入、消费与储蓄决策及最终需求闭环反哺;
5. WorldFinancialEquilibriumEngine: 全电路端到端穿透、反向全景聚合守恒律检验与世界金融资产无套利定价缺口测算.
"""

import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from financial_core.engines.world_production_aggregate_engine import (
    WorldProductionAggregateEngine,
    WorldProductionState,
)
from financial_core.engines.global_input_output_engine import (
    GlobalInputOutputEngine,
    SectorProfile,
)
from financial_core.engines.firm_value_added_bridge_engine import (
    FirmValueAddedBridgeEngine,
    FirmFinancialFact,
)
from financial_core.engines.factor_income_distribution_engine import (
    FactorIncomeDistributionEngine,
)
from financial_core.engines.world_financial_equilibrium_engine import (
    WorldFinancialEquilibriumEngine,
)
from financial_core.engines.inter_country_trade_engine import (
    InterCountryTradeEngine,
    RegionTradeProfile,
)


class TestWorldFinancialSystem(unittest.TestCase):
    """世界金融一般均衡与全链路定价系统单元测试集."""

    def test_01_world_production_aggregate_engine(self):
        """【UT-WORLDSYS-01: 世界生产总量基准加载与索洛-阿吉翁TFP边际增量模拟及要素分配守恒断言】

        1. 测试功能与测试点:
           - 验证 WorldProductionAggregateEngine 加载全球生产总值基准数据（符合 IMF WEO 事实）：
             名义 GDP 约 110 万亿美元，总产出大于 200 万亿美元，增加值率约 49.53%。
           - 验证初次要素分配守恒公理：劳动者报酬 + 资本营业盈余 + 生产税净额 == 世界名义 GDP。
           - 模拟索洛-阿吉翁 TFP 技术冲击提升 50 bps（AI 生产力大爆发）：
             验证全要素生产率跃迁与投资资本深化带来的边际 GDP 增量，并断言模拟后的要素分配依然严格守恒。

        2. 正常函数业务边界与参数契约:
           - tfp_shock_bps, investment_change_pct, labor_supply_change_pct 均为有限实数。
           - 返回包含 simulated_gdp_trillion 与 factor_income_distribution 的结果字典。

        3. 测试数据与模拟场景说明:
           - 全球宏观经济基准状态（2026年 110 万亿美元总池）；
           - 模拟 TFP 提高 50 个基点、资本开支投资增加 4.0%、有效劳动供给增加 0.5% 的技术爆发场景。

        4. 预期断言与结果验证:
           - world_nominal_gdp_trillion 贴近 110.0。
           - factor_sum == world_nominal_gdp_trillion。
           - simulated_gdp_trillion > 110.0，marginal_increment_trillion > 0。
           - factor_income_distribution['is_balanced'] 为 True。
        """
        engine = WorldProductionAggregateEngine()
        state = engine.get_current_state()

        # 断言基准数据符合 IMF WEO 事实
        self.assertAlmostEqual(state.world_nominal_gdp_trillion, 110.0, places=1)
        self.assertGreater(state.world_gross_output_trillion, 200.0)
        self.assertAlmostEqual(state.value_added_ratio, 0.4953, places=3)

        # 要素分配初值守恒
        factor_sum = (
            state.labor_compensation_trillion
            + state.capital_operating_surplus_trillion
            + state.net_production_taxes_trillion
        )
        self.assertAlmostEqual(factor_sum, state.world_nominal_gdp_trillion, places=4)

        # 模拟 TFP 提升 50 bps (AI 生产力大爆发场景)
        sim = engine.simulate_production_shock(
            tfp_shock_bps=50.0,
            investment_change_pct=4.0,
            labor_supply_change_pct=0.5,
        )
        self.assertGreater(sim["simulated_gdp_trillion"], 110.0)
        self.assertGreater(sim["marginal_increment_trillion"], 0.0)
        self.assertTrue(sim["factor_income_distribution"]["is_balanced"])

    def test_02_global_input_output_leontief_engine(self):
        """【FT-WORLDSYS-02: 全球投入产出网络列昂惕夫逆矩阵乘数/对偶价格体系与霍金斯-西蒙稳定性验证】

        1. 测试功能与测试点:
           - 验证 GlobalInputOutputEngine 维护的 12 大全球中观产业部门投入产出拓扑网络。
           - 验证霍金斯-西蒙稳定性公理 (Hawkins-Simon Condition)：直接消耗矩阵 A 的谱半径必须严格小于 1.0。
           - 验证列昂惕夫逆矩阵 $(I - A)^{-1}$ 完全拉动乘数表，前沿半导体 (TECH_SEMI) 乘数大于 1.4。
           - 模拟最终需求外生冲击传导（科技芯片需求激增 0.5 万亿美元、基础设施 0.3 万亿美元）：
             断言宏观平账，拉动的总产出扩张严格大于增加值增量，且总增加值增量等于最终需求冲击总和。
           - 验证全行业内生资产估值与两阶段折现模型，全行业上市股票公允价值总额精准锚定全球 115.95 万亿美元。
           - 求解列昂惕夫对偶价格体系（半导体降价 5% 引发的全产业链通缩扩散）与罗伯特·霍尔加价率对要素份额的内生修正。

        2. 正常函数业务边界与参数契约:
           - 投入产出矩阵非负，列和小于 1。
           - 求解对偶价格和加价率调整返回强类型行业响应字典。

        3. 测试数据与模拟场景说明:
           - 全球 12 大部门投入产出表与最终需求外生冲击向量。

        4. 预期断言与结果验证:
           - len(sectors) == 12，spectral_radius < 1.0。
           - mult_table['TECH_SEMI']['output_multiplier'] > 1.4。
           - shock_res['is_macro_balanced'] 为 True。
           - summary['total_fair_listed_equity_value_trillion'] 介于 110.0~125.0 之间。
           - 对偶价格体系降价扩散且霍尔加价率提高资本盈余份额。
        """
        engine = GlobalInputOutputEngine()
        sectors = engine.get_sector_profiles()
        self.assertEqual(len(sectors), 12)

        # 验证霍金斯-西蒙稳定性
        eigvals = np.linalg.eigvals(engine.A_matrix)
        spectral_radius = float(np.max(np.abs(eigvals)))
        self.assertLess(spectral_radius, 1.0, "投入产出矩阵必须满足谱半径小于 1.0")

        # 检查乘数表
        mult_table = engine.get_leontief_multiplier_table()
        self.assertIn("TECH_SEMI", mult_table)
        # 前沿硬件通常具有大于 1.5 的全社会产出扩张乘数
        self.assertGreater(mult_table["TECH_SEMI"]["output_multiplier"], 1.4)

        # 传导特定需求冲击 (科技芯片需求增加 0.5 万亿美元)
        shock_res = engine.propagate_final_demand_shock(
            sector_demand_shocks={"TECH_SEMI": 0.5, "INFRA_UTIL": 0.3},
            marginal_gdp_increment=2.0,
        )
        self.assertTrue(shock_res["is_macro_balanced"])
        self.assertGreater(shock_res["total_gross_output_expansion_trillion"], shock_res["total_value_added_increment_trillion"])
        self.assertAlmostEqual(
            shock_res["total_value_added_increment_trillion"],
            shock_res["total_final_demand_shock_trillion"],
            places=3,
        )

        # 验证分行业差异化营业盈余与内生资产估值计算
        sec_vals = engine.compute_sector_intrinsic_valuations()
        self.assertEqual(len(sec_vals["sectors"]), 12)
        summary = sec_vals["summary_totals"]
        self.assertAlmostEqual(summary["total_value_added_trillion"], 110.0, places=1)
        self.assertAlmostEqual(summary["total_capital_operating_surplus_trillion"], 41.8, places=1)
        self.assertAlmostEqual(summary["total_labor_wages_trillion"], 58.3, places=1)
        self.assertAlmostEqual(summary["total_taxes_trillion"], 9.9, places=1)
        # 上市股票公允估值总和约 115.95 万亿美元，精准锚定全球上市股票总市值
        self.assertGreater(summary["total_fair_listed_equity_value_trillion"], 110.0)
        self.assertLess(summary["total_fair_listed_equity_value_trillion"], 125.0)

        # 验证行业差异化特征 (如半导体盈余率 58% vs 农业 22%)
        semi_sec = next(s for s in sec_vals["sectors"] if s["sector_id"] == "TECH_SEMI")
        agr_sec = next(s for s in sec_vals["sectors"] if s["sector_id"] == "AGR")
        self.assertEqual(semi_sec["surplus_rate_pct"], 58.0)
        self.assertEqual(agr_sec["surplus_rate_pct"], 22.0)
        self.assertEqual(semi_sec["fcf_conversion_pct"], 65.0)
        self.assertEqual(agr_sec["fcf_conversion_pct"], 35.0)
        self.assertIn("implied_roic_pct", semi_sec)
        self.assertGreater(semi_sec["implied_roic_pct"], 5.0)
        self.assertIn("two_stage_fair_listed_equity_value_trillion", semi_sec)

        # 验证两阶段折现全行业总值
        self.assertGreater(summary["two_stage_total_fair_listed_equity_value_trillion"], 100.0)
        self.assertLess(summary["two_stage_total_fair_listed_equity_value_trillion"], 120.0)

        # 验证列昂惕夫对偶价格体系求解 (半导体技术突破降价 5%)
        price_res = engine.solve_leontief_dual_price_system({"TECH_SEMI": -0.05})
        self.assertEqual(len(price_res["sector_price_responses"]), 12)
        semi_price = next(p for p in price_res["sector_price_responses"] if p["sector_id"] == "TECH_SEMI")
        self.assertLess(semi_price["supply_chain_price_impact_pct"], -5.0)

        # 验证霍尔加价率修正要素分配 (欧拉穷竭定理内生反馈)
        markup_res = engine.adjust_factor_shares_with_markup({"TECH_SEMI": 1.35})
        semi_adj = next(p for p in markup_res["sectors"] if p["sector_id"] == "TECH_SEMI")
        self.assertGreater(semi_adj["adjusted_capital_surplus_share_pct"], semi_sec["surplus_rate_pct"])
        self.assertLess(semi_adj["adjusted_labor_share_pct"], semi_sec["labor_share_pct"])

    def test_03_firm_value_added_bridge_engine(self):
        """【UT-WORLDSYS-03: 微观企业三表增加值映射直接法与间接法平账/汇率存货DIO弹性与三情景估值核验】

        1. 测试功能与测试点:
           - 验证 FirmValueAddedBridgeEngine 将微观企业财务三表指标直接穿透映射至国民经济核算体系 (SNA) 增加值：
             * 直接法：$VA = EBITDA + 工资报酬 + 生产税$；
             * 间接法：$外购中间消耗 = 营收 - 增加值$。
           - 验证行业增长冲击向微观个股（如 NVDA 英伟达）的映射传导与自由现金流推导。
           - 验证微观代表企业内在公允价值、悲观底价、乐观靶心与买方机构建议。
           - 验证两阶段有限生命期折现与内生资本回报率 ROIC 经济可行性自检。
           - 验证开放经济出口敞口与汇率弹性（如 8035 东京电子 86% 海外出口敞口、日元贬值 10% 收益乘数与存货 DIO 周转拖累）。

        2. 正常函数业务边界与参数契约:
           - FirmFinancialFact 实体输入三表主要数值大于等于零。
           - compute_firm_value_added 严格保证要素分配恒等式成立。

        3. 测试数据与模拟场景说明:
           - NVDA（美股龙头）微观财报与行业 8% 扩张冲击；
           - 8035（东京电子）86% 外销、日元汇率与 DIO 存货周期场景。

        4. 预期断言与结果验证:
           - corporate_value_added_million == 95700.0，intermediate_purchases_million == 24300.0。
           - is_distribution_identity_held 为 True。
           - 悲观底价 < 公允内在价值 < 乐观靶心。
           - endogenous_capital_consistency['is_economically_feasible'] 为 True。
           - 东京电子外销比重 86%，存货周转天数 85 天。
        """
        engine = FirmValueAddedBridgeEngine()

        nvda = FirmFinancialFact(
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
        )

        res = engine.compute_firm_value_added(nvda)
        # VA = 78000 + 8500 + 9200 = 95700 百万美元
        expected_va = 78000.0 + 8500.0 + 9200.0
        self.assertEqual(res["corporate_value_added_million"], expected_va)
        # 外购中间消耗 = 120000 - 95700 = 24300 百万美元
        self.assertEqual(res["intermediate_purchases_million"], 120000.0 - expected_va)
        self.assertTrue(res["factor_distribution"]["is_distribution_identity_held"])

        # 模拟行业 8% 扩张冲击传导
        shock_firm = engine.map_sector_shock_to_firm(nvda, sector_va_growth_pct=8.0, firm_pricing_power_mu=1.35)
        self.assertGreater(shock_firm["simulated_revenue_million"], 120000.0)
        self.assertGreater(shock_firm["simulated_ebitda_million"], 78000.0)
        self.assertGreater(shock_firm["simulated_fcf_million"], 54500.0)

        # 验证微观代表企业真实公允内在价值与三情景估值测算
        nvda_val = engine.compute_firm_intrinsic_valuation(
            firm=nvda,
            simulated_fcf_million=shock_firm["simulated_fcf_million"],
            sector_wacc=0.082,
            terminal_growth_rate=0.038,
        )
        self.assertGreater(nvda_val["fair_intrinsic_value_billion"], 1000.0)
        self.assertLess(nvda_val["pessimistic_floor_value_billion"], nvda_val["fair_intrinsic_value_billion"])
        self.assertGreater(nvda_val["optimistic_target_value_billion"], nvda_val["fair_intrinsic_value_billion"])
        self.assertIn("institutional_verdict", nvda_val)
        self.assertIn("recommended_action", nvda_val)
        # 验证两阶段有限生命期折现与内生资本回报 ROIC
        self.assertIn("two_stage_valuation", nvda_val)
        self.assertIn("endogenous_capital_consistency", nvda_val)
        self.assertTrue(nvda_val["endogenous_capital_consistency"]["is_economically_feasible"])
        self.assertGreater(nvda_val["two_stage_valuation"]["two_stage_fair_value_billion"], 900.0)

        # 开放经济出口与日元汇率弹性验证 (8035 东京电子: 86% 海外出口敞口)
        tel = FirmFinancialFact(
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
        )
        tel_shock = engine.map_sector_shock_to_firm(
            tel,
            sector_va_growth_pct=6.0,
            firm_pricing_power_mu=1.35,
            export_demand_growth_pct=8.5,
            fx_shock_multiplier=1.095,  # 日元贬值 10%
            inventory_drag_bps=20.0,    # 存货周转拖累
        )
        self.assertEqual(tel_shock["foreign_revenue_ratio_pct"], 86.0)
        self.assertGreater(tel_shock["simulated_revenue_million"], 18500.0)
        self.assertGreater(tel_shock["effective_firm_growth_pct"], 8.0)
        self.assertEqual(tel_shock["inventory_dio_days"], 85.0)

    def test_04_factor_income_distribution_engine(self):
        """【UT-WORLDSYS-04: 居民个人部门要素收益分解/边际消费倾向MPC与宏观资金流量严格吸收闭环断言】

        1. 测试功能与测试点:
           - 验证 FactorIncomeDistributionEngine 对要素报酬向居民个人可支配收入的二次映射分解。
           - 验证居民部门在边际消费倾向 (MPC=0.72) 下的消费与储蓄跨期配置决策。
           - 验证居民储蓄向金融中介资产与全社会资本形成 (Gross Capital Formation, I) 的转化。
           - 验证宏观资金流量总吸收严格闭环：$C + I + G \equiv GDP$（行星级吸收总额平账，误差在 0.01 万亿美元以内）。

        2. 正常函数业务边界与参数契约:
           - MPC 介于 0 到 1 之间，劳动报酬与资本盈余为正。
           - strict_macro_closure 标记断言吸收守恒。

        3. 测试数据与模拟场景说明:
           - 全球 GDP 110 万亿、劳动报酬 58.3 万亿、资本盈余 41.8 万亿、劳动力人口 36.5 亿。

        4. 预期断言与结果验证:
           - net_disposable_income_trillion > 0。
           - household_final_consumption_c_trillion > 40.0。
           - is_circular_flow_stable 为 True。
           - is_strict_planetary_absorption_balanced 为 True，吸收总额精准对齐 110.0 万亿美元。
        """
        engine = FactorIncomeDistributionEngine()
        dist = engine.compute_household_distribution(
            world_gdp_trillion=110.0,
            labor_compensation_trillion=58.3,
            capital_operating_surplus_trillion=41.8,
            net_taxes_trillion=9.9,
            labor_force_billion=3.65,
            mpc=0.72,
        )

        self.assertGreater(dist["household_income_breakdown"]["net_disposable_income_trillion"], 0.0)
        self.assertGreater(dist["household_absorption_behavior"]["household_final_consumption_c_trillion"], 40.0)
        self.assertGreater(dist["per_capita_metrics"]["average_annual_wage_usd"], 10000.0)
        self.assertTrue(dist["macro_consumption_feedback"]["is_circular_flow_stable"])

        # 储蓄向实体投资转化与总吸收闭环
        fin = dist["financial_intermediation_and_investment"]
        self.assertGreater(fin["gross_capital_formation_i_trillion"], 15.0)
        self.assertGreater(fin["government_expenditure_g_trillion"], 10.0)
        self.assertGreater(fin["total_domestic_absorption_c_plus_i_plus_g_trillion"], 80.0)
        # 验证宏观资金流量严格吸收闭环
        self.assertIn("strict_macro_closure", fin)
        self.assertTrue(fin["strict_macro_closure"]["is_strict_planetary_absorption_balanced"])
        self.assertAlmostEqual(fin["strict_macro_closure"]["strict_total_absorption_c_plus_i_plus_g_trillion"], 110.0, places=2)

        # 验证买方全息研报卡片与去工程符号化契约
        self.assertIn("narrative_zh", dist)
        self.assertIn("全球要素收入分配与居民消费循环流转全息研报", dist["narrative_zh"])
        self.assertIn("居民最终消费支出", dist["narrative_zh"])
        self.assertIn("行星尺度内生宏观吸收", dist["narrative_zh"])

    def test_05_world_financial_equilibrium_full_circuit(self):
        """【FT-WORLDSYS-05: 世界金融一般均衡全电路端到端穿透/五大守恒律(增加值/要素/贸易/吸收)与两阶段资产定价无套利闭环】

        1. 测试功能与测试点:
           - 验证 WorldFinancialEquilibriumEngine 全电路端到端仿真管线：
             * Step 1: 世界生产总量索洛宏观层；
             * Step 2: 中观产业列昂惕夫投入产出层；
             * Step 2b: 开放经济跨国贸易与汇率传导层；
             * Step 3: 微观代表企业三表映射与内在公允估值层 (NVDA, 8035, LLY, 7203, 6501)；
             * Step 4: 居民家庭要素收益分配与总吸收闭环层；
             * Step 5: 反向全景聚合与全球金融资产无套利定价层。
           - 验证反向聚合五大不可变守恒律 (Conservation Invariants)：
             1. 增加值守恒律 (is_value_added_conserved);
             2. 要素分配守恒律 (is_factor_income_conserved);
             3. 全球贸易平衡守恒律 (is_global_trade_conserved);
             4. 行星级总吸收守恒律 (is_planetary_absorption_strictly_conserved);
             5. 全量守恒硬门禁 (all_invariants_strictly_passed)。
           - 验证自下而上各行业上市股票公允价值与自上而下宏观折现价值，处于“合理公允区间”。

        2. 正常函数业务边界与参数契约:
           - 接收宏观 TFP、资本投入、行业需求、关税基点、日元汇率贬值幅度与 WACC 利率参数，返回结构化仿真总账。

        3. 测试数据与模拟场景说明:
           - TFP 40 bps、投资 +3%、科技需求 +0.4T、关税 100 bps、日元贬值 8%、美需求 +0.5T。

        4. 预期断言与结果验证:
           - 六大阶段输出完整存在。
           - 贸易守恒与日元出口乘数 > 1.0。
           - 5 家代表企业估值健康。
           - all_invariants_strictly_passed 为 True。
           - macro_valuation_status 为 '合理公允区间 (Fair Equilibrium)'。
        """
        engine = WorldFinancialEquilibriumEngine()

        result = engine.run_full_circuit_simulation(
            tfp_shock_bps=40.0,
            investment_change_pct=3.0,
            sector_demand_shocks={"TECH_SEMI": 0.4, "HEALTH_BIO": 0.2},
            tariff_shock_bps=100.0,
            jpy_depreciation_pct=8.0,
            us_demand_shock_trillion=0.5,
            global_wacc=0.075,
            terminal_growth_rate=0.030,
            current_global_equity_market_cap_trillion=115.0,
            listed_equity_coverage_ratio=0.28,
        )

        # 1. 验证五大步骤 + 开放经济进出口全部打通
        self.assertIn("step1_world_production_macro", result)
        self.assertIn("step2_middle_industry_leontief", result)
        self.assertIn("step2b_open_economy_trade_and_exports", result)
        self.assertIn("step3_micro_firm_transmission", result)
        self.assertIn("step4_household_personal_distribution", result)
        self.assertIn("step5_reverse_aggregation_and_equilibrium", result)

        # 2. 验证开放经济跨国贸易守恒与日股汇率乘数
        trade = result["step2b_open_economy_trade_and_exports"]
        self.assertTrue(trade["is_trade_strictly_conserved"])
        self.assertGreater(trade["jpy_export_revenue_multiplier"], 1.0)
        self.assertIn("US", trade["region_trade_impacts"])
        self.assertIn("JP", trade["region_trade_impacts"])

        # 3. 验证微观企业贯通结果 (NVDA, 8035, LLY, 7203, 6501)
        firms_out = result["step3_micro_firm_transmission"]
        firm_vals = result["step3_micro_firm_intrinsic_valuations"]
        self.assertEqual(len(firms_out), 5)
        self.assertEqual(len(firm_vals), 5)
        tickers = [f["ticker"] for f in firms_out]
        self.assertIn("NVDA", tickers)
        self.assertIn("8035", tickers)
        self.assertIn("7203", tickers)
        for v in firm_vals:
            self.assertGreater(v["fair_intrinsic_value_billion"], 0.0)
            self.assertLess(v["pessimistic_floor_value_billion"], v["fair_intrinsic_value_billion"])
            self.assertGreater(v["optimistic_target_value_billion"], v["fair_intrinsic_value_billion"])
            self.assertIn("institutional_verdict", v)

        # 4. 验证反向聚合守恒律 (Conservation Invariants: 增加值、要素分配与贸易平衡 100% 严格平账)
        invariants = result["step5_reverse_aggregation_and_equilibrium"]["conservation_invariants"]
        self.assertTrue(invariants["is_value_added_conserved"])
        self.assertTrue(invariants["is_factor_income_conserved"])
        self.assertTrue(invariants["is_global_trade_conserved"])
        self.assertTrue(invariants["is_planetary_absorption_strictly_conserved"])
        self.assertTrue(invariants["all_invariants_strictly_passed"])

        # 5. 验证上市资产切片校准后的金融资产公允折现值
        pricing = result["step5_reverse_aggregation_and_equilibrium"]["world_financial_asset_pricing"]
        self.assertGreater(pricing["bottom_up_sector_listed_equity_fair_value_trillion"], 110.0)
        self.assertLess(pricing["bottom_up_sector_listed_equity_fair_value_trillion"], 130.0)
        self.assertIn("two_stage_bottom_up_sector_listed_equity_fair_value_trillion", pricing)
        self.assertGreater(pricing["two_stage_bottom_up_sector_listed_equity_fair_value_trillion"], 100.0)
        self.assertGreater(pricing["top_down_macro_equity_fair_value_trillion"], 100.0)
        self.assertLess(pricing["top_down_macro_equity_fair_value_trillion"], 150.0)
        self.assertEqual(pricing["macro_valuation_status"], "合理公允区间 (Fair Equilibrium)")

    def test_06_inter_country_trade_engine(self):
        """【FT-WORLDSYS-06: 跨国双边贸易矩阵/全球进出口守恒(净出口和恒为零)与关税汇率宏观冲击传导断言】

        1. 测试功能与测试点:
           - 验证 InterCountryTradeEngine 全球 5 大经济体（美、中、日、欧、其他）双边贸易矩阵。
           - 验证全球跨国进出口宏观守恒公理：
             * 全球总出口严格等于全球总进口（约 34.50 万亿美元）；
             * 全球所有国家净出口 $(Exports - Imports)$ 代数和恒等于 0.0。
           - 模拟外生关税壁垒激增 200 bps 与日元外生贬值 10%：
             断言冲击后贸易矩阵仍然保持严格守恒，且日本出口商获得正向营收乘数补偿。

        2. 正常函数业务边界与参数契约:
           - 地区列表涵盖主流经济体，贸易矩阵非负且对角线（国内消耗）不列入国际跨国贸易。

        3. 测试数据与模拟场景说明:
           - 全球双边贸易真实基准矩阵与 200 bps 关税上调/10% 日元贬值/1 万亿美元美需扩张冲击。

        4. 预期断言与结果验证:
           - is_trade_strictly_conserved 为 True。
           - world_net_exports_sum_trillion 严格为 0.0。
           - jpy_export_revenue_multiplier > 1.08。
           - 区域贸易冲击涵盖 'JP' 与 'US'。
        """
        engine = InterCountryTradeEngine()
        regions = engine.get_region_profiles()
        self.assertEqual(len(regions), 5)
        region_ids = [r.region_id for r in regions]
        self.assertIn("US", region_ids)
        self.assertIn("JP", region_ids)
        self.assertIn("CN", region_ids)

        # 1. 核验全球进出口守恒: 总出口 == 总进口, 净出口之和恒为 0.0
        check = engine.verify_global_trade_conservation()
        self.assertTrue(check["is_trade_strictly_conserved"])
        self.assertAlmostEqual(check["total_world_exports_trillion"], 34.50, places=2)
        self.assertAlmostEqual(check["total_world_imports_trillion"], 34.50, places=2)
        self.assertAlmostEqual(check["world_net_exports_sum_trillion"], 0.0, places=4)

        # 2. 模拟关税与汇率冲击
        sim = engine.simulate_trade_and_fx_shock(
            tariff_shock_bps=200.0,
            jpy_depreciation_pct=10.0,
            us_demand_shock_trillion=1.0,
        )
        self.assertTrue(sim["is_global_trade_conserved"])
        self.assertGreater(sim["jpy_export_revenue_multiplier"], 1.08)
        self.assertIn("JP", sim["region_trade_impacts"])
        self.assertIn("US", sim["region_trade_impacts"])


if __name__ == "__main__":
    unittest.main()
