"""单元测试: 蒙特卡洛多参数连续随机 DCF 估值引擎与微观增加值桥接测试.

测试覆盖:
1. 10,000 次向量化抽样与数值收敛性 (均值、中位数、标准差)
2. 极值风险度量: VaR (10% 保守底价) 与 CVaR (10% 尾部条件在险价值 / Expected Shortfall)
3. 安全边际走廊与连续概率密度离散分桶 (DensityBin, 20 等分区间累积概率 ~100%)
4. 金融数学刚性边界: 永续分母防除零除负 (wacc - g >= 0.010) 与有限责任非负截断 (Equity >= 0)
5. 微观财务底账适配器 (from_firm_financial_fact) 与增加值桥梁集成 (run_firm_monte_carlo_valuation)
"""

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.monte_carlo_engine import (
    MonteCarloValuationEngine,
    MonteCarloDCFInput,
    MonteCarloValuationResult,
    DensityBin,
)
from financial_core.engines.firm_value_added_bridge_engine import (
    FirmFinancialFact,
    FirmValueAddedBridgeEngine,
)


class TestMonteCarloDCFUpgrade(unittest.TestCase):
    """【单元与集成测试】蒙特卡洛连续随机 DCF 估值引擎与微观增加值桥接测试套件."""

    def setUp(self):
        self.engine = MonteCarloValuationEngine()
        self.bridge_engine = FirmValueAddedBridgeEngine()

    def test_vectorized_convergence_and_risk_metrics(self):
        """【UT-MC-01: 10000次向量化模拟收敛性与VaR/CVaR尾部风险度量】

        1. 测试功能与测试点:
           - 验证 MonteCarloValuationEngine 在 10,000 次大规模抽样下的数值收敛性与统计自洽性。
           - 验证极值下行风险度量: 10% 分位数 (VaR_10 保守底价) 与 10% 尾部期望损失 (CVaR_10 极值条件在险价值)。
           - 验证数学单调性定理: 分位数序列严格单调递增，且尾部期望损失严格位于保底分位数之下 (CVaR_10 <= VaR_10)。
           - 验证 20 等分区间连续概率密度离散分桶 (DensityBin) 的累积分段概率收敛至 100%。

        2. 正常函数业务边界与参数契约:
           - base_cash_flow: 标的企业报告期基准所有者自由现金流 (> 0.0)。
           - shares_outstanding: 发行在外的流通总股本 (> 0.0)。
           - iterations: 模拟抽样次数，建议 >= 5,000，本用例为 10,000 次。
           - 统计输出: mean, median, std_dev, p05, p10, p25, p50, p75, p90, p95, cvar_10。

        3. 测试数据与模拟场景说明:
           - 标的: TEST_AAPL，模拟现金流 2,500M，现价 150.0，股本 1,000M 股，净负债 5,000M。
           - 增长率分布: 正态分布 N(12%, 5%)，预测期 5 年。
           - 折现率分布: 正态分布 N(9%, 1.2%)。
           - 永续增长率: 正态分布 N(2.5%, 0.5%)。

        4. 预期断言与结果验证:
           - 断言抽样样本数精确等于 10000。
           - 断言均值与中位数均 > 0.0。
           - 断言 p05 <= p10 <= p25 <= p50 <= p75 <= p90 <= p95 单调递增。
           - 断言 cvar_10_floor <= percentile_10 (符合 Expected Shortfall 数学性质)。
           - 断言密度分桶数量为 20，末桶累积概率在 100.0 ± 2.0% 范围内。
        """
        params = MonteCarloDCFInput(
            base_cash_flow=2500.0,
            current_price=150.0,
            shares_outstanding=1000.0,
            net_debt=5000.0,
            forecast_years=5,
            growth_mean=0.12,
            growth_std=0.05,
            wacc_mean=0.09,
            wacc_std=0.012,
            terminal_g_mean=0.025,
        )

        res = self.engine.run_monte_carlo_dcf("TEST_AAPL", params, iterations=10000, random_seed=42)

        # 1. 验证基础统计收敛
        self.assertEqual(res.ticker, "TEST_AAPL")
        self.assertEqual(res.iterations, 10000)
        self.assertGreater(res.mean_fair_value, 0.0)
        self.assertGreater(res.median_fair_value, 0.0)
        self.assertGreater(res.std_dev, 0.0)

        # 2. 验证分位数单调递增性
        self.assertLessEqual(res.percentile_05, res.percentile_10)
        self.assertLessEqual(res.percentile_10, res.percentile_25)
        self.assertLessEqual(res.percentile_25, res.percentile_50)
        self.assertLessEqual(res.percentile_50, res.percentile_75)
        self.assertLessEqual(res.percentile_75, res.percentile_90)
        self.assertLessEqual(res.percentile_90, res.percentile_95)

        # 3. 验证 CVaR 条件在险价值严守数学定义: CVaR_10 <= VaR_10
        self.assertLessEqual(res.cvar_10_floor, res.percentile_10)
        self.assertLessEqual(res.cvar_downside_pct, res.var_downside_pct)

        # 4. 验证走廊宽度与相对走廊离散度
        self.assertAlmostEqual(res.corridor_spread, res.percentile_90 - res.percentile_10, places=4)
        self.assertGreater(res.relative_corridor_spread_pct, 0.0)

        # 5. 验证连续概率密度分桶
        self.assertEqual(len(res.density_distribution), 20)
        self.assertAlmostEqual(res.density_distribution[-1].cumulative_prob_pct, 100.0, delta=2.0)

    def test_gordon_denominator_and_limited_liability_safety_boundary(self):
        """【UT-MC-02: 永续分母防除零除负与有限责任股权价值非负保护边界】

        1. 测试功能与测试点:
           - 验证金融计算核心工程防御: 戈登永续折现分母 (WACC - g) 的除零、除负与发散截断保护 (WACC - g >= 0.010)。
           - 验证公司金融法有限责任边界: 即使面临破产与巨额资不抵债，普通股每股公允价值下界绝不能跌破 0.0 (Equity >= 0)。

        2. 正常函数业务边界与参数契约:
           - 当抽样中的 terminal_g 接近或超过 WACC 时，引擎必须强制施行数值保底剪裁，严禁抛出 ZeroDivisionError 或计算出负无穷。
           - 当企业价值 Enterprise Value < Net Debt 时，股权价值归零，每股价值截断为 0.0。

        3. 测试数据与模拟场景说明:
           - 模拟濒临破产的僵尸失血企业 DISTRESSED_ZOMBIE:
             基准现金流微弱 10.0M，现价 2.0，巨额净负债高达 50,000M (净负债达现金流的 5,000 倍)；
             增长率暴跌 -20%，折现率偏低 7%，而永续增长率均值高达 3.5% (极度逼近 WACC)。

        4. 预期断言与结果验证:
           - 断言每股内在价值 percentile_05 >= 0.0。
           - 断言极值条件在险价值 cvar_10_floor >= 0.0。
           - 断言平均内在价值 mean_fair_value >= 0.0。
        """
        # 设置极端失血与低折现率输入
        distressed_params = MonteCarloDCFInput(
            base_cash_flow=10.0,
            current_price=2.0,
            shares_outstanding=500.0,
            net_debt=50000.0,  # 巨额净负债远超现金流现值
            forecast_years=5,
            growth_mean=-0.20,
            wacc_mean=0.07,
            wacc_min=0.065,
            wacc_max=0.08,
            terminal_g_mean=0.035, # 试图逼近 WACC
            terminal_g_max=0.08,
        )

        res = self.engine.run_monte_carlo_dcf("DISTRESSED_ZOMBIE", distressed_params, iterations=5000, random_seed=42)

        # 股东有限责任下界: 每股内在价值样本下界绝不能为负
        self.assertGreaterEqual(res.percentile_05, 0.0)
        self.assertGreaterEqual(res.cvar_10_floor, 0.0)
        self.assertGreaterEqual(res.mean_fair_value, 0.0)

    def test_from_firm_financial_fact_adapter(self):
        """【UT-MC-03: 微观企业底账向连续随机输入契约自动组装适配】

        1. 测试功能与测试点:
           - 验证 MonteCarloDCFInput.from_firm_financial_fact 适配器方法。
           - 验证净负债与净现金的准确数学正负号折算: NetDebt = TotalDebt - CashAndEquivalents。

        2. 正常函数业务边界与参数契约:
           - firm: 强类型 FirmFinancialFact 实体。
           - sector_wacc: 行业基准加权平均资本成本。
           - terminal_g: 宏观长期稳态名义 GDP 增速。

        3. 测试数据与模拟场景说明:
           - 标的: 英伟达 (NVDA) 事实底账: FCF 65,000M, 总债务 11,000M, 账面现金 35,000M (净现金 24,000M)。
           - 传入行业资本成本 8.5%，永续增长率 3.0%。

        4. 预期断言与结果验证:
           - 断言 base_cash_flow 精确等于 65,000M。
           - 断言 wacc_mean 精确等于 0.085。
           - 断言 net_debt 正确计算为 -24,000.0 (负净负债代表净现金企业)。
        """
        firm = FirmFinancialFact(
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            market="US",
            sector_id="TECH_SEMI",
            revenue_million=120000.0,
            cogs_million=30000.0,
            operating_expenses_million=15000.0,
            ebitda_million=75000.0,
            wages_and_salaries_million=8000.0,
            taxes_paid_million=10000.0,
            capex_million=6000.0,
            annual_fcf_million=65000.0,
            market_cap_billion=3200.0,
            total_debt_million=11000.0,
            cash_and_equivalents_million=35000.0,
        )

        mc_input = MonteCarloDCFInput.from_firm_financial_fact(firm, sector_wacc=0.085, terminal_g=0.030)

        self.assertEqual(mc_input.base_cash_flow, 65000.0)
        self.assertEqual(mc_input.wacc_mean, 0.085)
        self.assertEqual(mc_input.terminal_g_mean, 0.030)
        self.assertEqual(mc_input.net_debt, 11000.0 - 35000.0) # -24,000 (净现金)

    def test_bridge_engine_monte_carlo_integration(self):
        """【IT-MC-04: 增加值桥梁引擎与连续蒙特卡洛折现全流程集成】

        1. 测试功能与测试点:
           - 验证 FirmValueAddedBridgeEngine 增加值桥梁引擎集成调用 5,000 次蒙特卡洛折现。
           - 验证 compute_firm_intrinsic_valuation 在启用 include_monte_carlo=True 时的复合估值字典装配。

        2. 正常函数业务边界与参数契约:
           - 增加值底账与现金流底账无缝衔接。
           - 字典中必须挂载 monte_carlo_simulation 键，涵盖 cvar_10_floor、corridor_spread 及 density_distribution。

        3. 测试数据与模拟场景说明:
           - 标的: 台积电 (TSMC 2330 / TSM) 财报底账: 营收 70,000M, FCF 25,000M, 市值 750B, 债务 28,000M, 现金 45,000M。

        4. 预期断言与结果验证:
           - 断言 mc_res.ticker 为 'TSM'，median_fair_value 与 cvar_10_floor 均大于 0.0。
           - 断言返回字典包含 monte_carlo_simulation 复合节点，且密度分桶长度为 20。
        """
        firm = FirmFinancialFact(
            ticker="TSM",
            company_name="Taiwan Semiconductor",
            market="US",
            sector_id="TECH_SEMI",
            revenue_million=70000.0,
            cogs_million=32000.0,
            operating_expenses_million=8000.0,
            ebitda_million=40000.0,
            wages_and_salaries_million=7000.0,
            taxes_paid_million=5000.0,
            capex_million=30000.0,
            annual_fcf_million=25000.0,
            market_cap_billion=750.0,
            total_debt_million=28000.0,
            cash_and_equivalents_million=45000.0,
        )

        # 1. 独立运行桥接方法
        mc_res = self.bridge_engine.run_firm_monte_carlo_valuation(
            firm=firm,
            sector_wacc=0.085,
            terminal_growth_rate=0.030,
            iterations=5000,
            random_seed=42,
        )
        self.assertEqual(mc_res.ticker, "TSM")
        self.assertGreater(mc_res.median_fair_value, 0.0)
        self.assertGreater(mc_res.cvar_10_floor, 0.0)

        # 2. 在 compute_firm_intrinsic_valuation 中带 include_monte_carlo=True
        val = self.bridge_engine.compute_firm_intrinsic_valuation(
            firm=firm,
            sector_wacc=0.085,
            terminal_growth_rate=0.030,
            include_monte_carlo=True,
            mc_iterations=5000,
            mc_seed=42,
        )

        self.assertIn("monte_carlo_simulation", val)
        mc_dict = val["monte_carlo_simulation"]
        self.assertEqual(mc_dict["ticker"], "TSM")
        self.assertIn("cvar_10_floor", mc_dict)
        self.assertIn("corridor_spread", mc_dict)
        self.assertIn("density_distribution", mc_dict)
        self.assertEqual(len(mc_dict["density_distribution"]), 20)

    def test_ut_mc_05_buyer_dossier_card_and_to_dict_contract(self):
        """【UT-MC-05: 蒙特卡洛折现全息研报卡片与去工程符号化契约断言】

        1. 测试功能与测试点:
           - 验证 MonteCarloValuationResult 包含自然语言 narrative_zh 全息卡片并支持 to_dict() 序列化；
           - 验证 valuation_regime_zh 纯自然中文估值状态定性字段已正确生成；
           - 验证 narrative_zh 彻底消除 (Strong Buy Margin)、(Fair Value Range)、(Overvalued Overhang) 等英文代码代号暴露；
           - 验证 to_dict() 完整输出 valuation_regime_zh 与 narrative_zh。

        2. 正常函数业务边界与参数契约:
           - 针对低估高安全边际标的与高估标的输入，返回完整的去工程符号化买方研报。

        3. 测试数据与模拟场景说明:
           - 标的 A: 现金流充沛、现价极度低估标的 (低估概率 >= 75%)；
           - 标的 B: 现价极高透支基本面标的 (低估概率 < 50%)。

        4. 预期断言与结果验证:
           - narrative_zh 包含 "蒙特卡洛随机折现估值全息研报" 与 "买方投资战术"；
           - narrative_zh 与 simulation_summary_zh 绝不包含 "(Strong Buy Margin)" 等英文代号；
           - to_dict() 准确导出 valuation_regime_zh 与 narrative_zh。
        """
        # 场景 A: 强安全边际低估标的
        cheap_params = MonteCarloDCFInput(
            base_cash_flow=2000.0,
            current_price=10.0, # 现价极低
            shares_outstanding=500.0,
            net_debt=0.0,
            forecast_years=5,
            growth_mean=0.15,
            wacc_mean=0.08,
            terminal_g_mean=0.025,
        )
        res_cheap = self.engine.run_monte_carlo_dcf("CHEAP_GEM", cheap_params, iterations=3000, random_seed=42)

        self.assertIn("蒙特卡洛随机折现估值全息研报", res_cheap.narrative_zh)
        self.assertIn("买方投资战术", res_cheap.narrative_zh)
        self.assertNotIn("(Strong Buy Margin)", res_cheap.narrative_zh)
        self.assertNotIn("(Strong Buy Margin)", res_cheap.simulation_summary_zh)
        self.assertTrue(bool(res_cheap.valuation_regime_zh))
        self.assertIn("低估", res_cheap.valuation_regime_zh)

        d_cheap = res_cheap.to_dict()
        self.assertIn("valuation_regime_zh", d_cheap)
        self.assertIn("narrative_zh", d_cheap)
        self.assertEqual(d_cheap["narrative_zh"], res_cheap.narrative_zh)

        # 场景 B: 严重透支高估标的
        expensive_params = MonteCarloDCFInput(
            base_cash_flow=50.0,
            current_price=200.0, # 现价极高
            shares_outstanding=500.0,
            net_debt=5000.0,
            forecast_years=5,
            growth_mean=0.05,
            wacc_mean=0.10,
            terminal_g_mean=0.020,
        )
        res_exp = self.engine.run_monte_carlo_dcf("EXPENSIVE_BUBBLE", expensive_params, iterations=3000, random_seed=42)

        self.assertNotIn("(Overvalued Overhang)", res_exp.narrative_zh)
        self.assertNotIn("(Overvalued Overhang)", res_exp.simulation_summary_zh)
        self.assertIn("高估", res_exp.valuation_regime_zh)
        self.assertIn("下行风险高企", res_exp.valuation_regime_zh)

    def test_ut_mc_06_cross_market_currency_adaptation(self):
        """【UT-MC-06: 跨市场多币种自适应推导与日股/A股研报货币符号断言】

        一、测试功能与测试点:
            1. 验证传入日股标的代码 (如 6758.T, market="JP") 时，自动推导货币符号为 '¥'；
            2. 验证 narrative_zh 与 simulation_summary_zh 中均使用 '¥'，严禁死锁 '$'；
            3. 验证 to_dict() 序列化中包含 "currency_symbol": "¥"。

        二、正常函数业务边界与参数契约:
            - 日股索尼集团蒙特卡洛随机 DCF 模拟。

        三、预期断言与结果验证:
            断言 currency_symbol == "¥"，narrative_zh 与 simulation_summary_zh 中包含 "¥" 且无 "$" 符号。
        """
        jp_params = MonteCarloDCFInput(
            base_cash_flow=900000.0,
            current_price=2800.0,
            shares_outstanding=1200.0,
            net_debt=200000.0,
            forecast_years=5,
            growth_mean=0.08,
            wacc_mean=0.07,
            terminal_g_mean=0.02,
            market="JP",
        )
        res_jp = self.engine.run_monte_carlo_dcf("6758.T", jp_params, iterations=2000, random_seed=42, market="JP")

        self.assertEqual(res_jp.currency_symbol, "¥")
        self.assertIn("¥", res_jp.narrative_zh)
        self.assertNotIn("$", res_jp.narrative_zh)
        self.assertIn("¥", res_jp.simulation_summary_zh)
        self.assertNotIn("$", res_jp.simulation_summary_zh)
        self.assertEqual(res_jp.to_dict()["currency_symbol"], "¥")


if __name__ == "__main__":
    unittest.main()
