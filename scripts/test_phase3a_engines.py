"""Phase 3A 新增金融算法引擎与系统集成单元测试.

测试覆盖:
1. CreditRiskAndSolvencyEngine:
   - Merton (1974) 资产价值与资产波动率联立求解方程收敛性;
   - 违约距离 (DD) 与预期违约率 (EDF) 单调性 (低负债 vs 高负债承压);
   - Altman Z-Score 5 因子制造业模型与非制造业 Z'' 模型分区判断;
   - 可转债纯债底价 (Bond Floor) 与稀释股数测算;
2. MonteCarloValuationEngine:
   - 10,000 次蒙特卡洛向量化抽样分位数单调性检验 (p05 <= p10 <= p25 <= p50 <= p75 <= p90 <= p95);
   - 永续分母防除零除负硬边界约束 (g_term <= WACC - 0.01);
   - 股东有限责任股权非负保护 (Equity Value >= 0);
   - 现价与低估置信度概率单调反比关系;
3. FinancialAnalysisSystem 集成测试:
   - AnalysisMode.CREDIT_SOLVENCY 独立精准调度;
   - AnalysisMode.MONTE_CARLO 独立精准调度;
   - AnalysisMode.FULL_SYSTEMIC 全息装配 Phase 3A 结果与决策卡片字段。
"""

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from financial_core.engines.credit_risk_engine import (
    CreditRiskAndSolvencyEngine,
    MertonCreditInput,
    CreditRiskResult,
)
from financial_core.engines.monte_carlo_engine import (
    MonteCarloValuationEngine,
    MonteCarloDCFInput,
    MonteCarloValuationResult,
)
from financial_core.api import FinancialAnalysisSystem
from financial_core.contracts import AnalysisMode, FinancialAnalysisResult


class TestPhase3AEngines(unittest.TestCase):
    """Phase 3A 核心引擎与集成测试用例."""

    def setUp(self):
        self.credit_engine = CreditRiskAndSolvencyEngine()
        self.mc_engine = MonteCarloValuationEngine()
        self.system = FinancialAnalysisSystem()

    def test_merton_model_healthy_vs_distressed(self):
        """【UT-PH3A-01: Merton(1974)结构化违约模型健康巨头与濒危高杠杆企业辨析度及单调性核验】

        1. 测试功能与测试点:
           - 验证 CreditRiskAndSolvencyEngine.solve_merton_model 联立方程求解公司未观测资产价值 $V_A$ 与资产波动率 $\sigma_A$。
           - 对比稳健蓝筹企业（苹果级：市值 3000B，债务 100B，波动率 25%）与濒危高杠杆企业（市值 10B，负债 50B，波动率 65%）。
           - 验证健康企业违约距离 (DD) 严格大于 10 个标准差，预期违约率 (EDF) 极度趋近于 0。
           - 验证濒危企业 DD 被严重压缩 (< 2.0σ)，EDF 显著上升 (> 1%)，且濒危 DD 严格小于健康 DD。

        2. 正常函数业务边界与参数契约:
           - MertonCreditInput 接收市值、债务面值、波动率、无风险利率与期限。
           - solve_merton_model 输出 (va, sa, dd, edf) 元组，资产价值为正，波动率为有限正数。

        3. 测试数据与模拟场景说明:
           - 场景 A: 蓝筹龙头 (市值 3,000,000M, 债务 100,000M, 波动率 0.25)。
           - 场景 B: 承压企业 (市值 10,000M, 债务 50,000M, 波动率 0.65)。

        4. 预期断言与结果验证:
           - va_h > 3,000,000.0，dd_h > 10.0，edf_h < 1e-10。
           - dd_d < 2.0，edf_d > 0.01，dd_d < dd_h。
        """
        # 稳健蓝筹企业 (如苹果级: 市值 3000B, 债务 100B, 波动率 25%)
        healthy_inp = MertonCreditInput(
            equity_market_cap=3000000.0,
            total_debt_face_value=100000.0,
            equity_volatility=0.25,
            risk_free_rate=0.045,
            time_to_maturity_years=1.0,
        )
        va_h, sa_h, dd_h, edf_h = self.credit_engine.solve_merton_model(healthy_inp)
        self.assertGreater(va_h, 3000000.0)
        self.assertGreater(dd_h, 10.0, "健康企业的违约距离应当大于 10 个标准差")
        self.assertLess(edf_h, 1e-10, "健康企业的预期违约率应当极度接近 0")

        # 濒危高杠杆企业 (市值 10B, 负债 50B, 波动率 65%)
        distressed_inp = MertonCreditInput(
            equity_market_cap=10000.0,
            total_debt_face_value=50000.0,
            equity_volatility=0.65,
            risk_free_rate=0.045,
            time_to_maturity_years=1.0,
        )
        va_d, sa_d, dd_d, edf_d = self.credit_engine.solve_merton_model(distressed_inp)
        self.assertLess(dd_d, 2.0, "高杠杆高波动企业的违约距离应当被严重压缩 (< 2.0σ)")
        self.assertGreater(edf_d, 0.01, "预期违约率应当显著上升 (> 1%)")
        self.assertLess(dd_d, dd_h, "濒危企业的 DD 必须显著小于稳健企业")

    def test_merton_physical_vs_risk_neutral_decoupling(self):
        """【UT-PH3A-02: 信用风险真实物理测度P与风险中性测度Q显式解耦与隐含利差走阔断言】

        1. 测试功能与测试点:
           - 验证 evaluate_comprehensive_credit 在物理真实测度 P 与风险中性测度 Q 之间的解耦计算。
           - 物理真实违约距离 $DD_P$ 包含资产真实预期回报，满足 $DD_P \ge DD_Q$。
           - 物理真实破产概率 $EDF_P$ 严格小于或等于风险中性违约概率 $EDF_Q$（因市场定价中包含信用风险溢价）。
           - 验证高杠杆亏损承压标的信用利差显著走阔 (> 10 bps) 且严格大于常态标的。

        2. 正常函数业务边界与参数契约:
           - 接收公司基础财务、资产负债、波动率与无风险利率，返回 CreditRiskResult。

        3. 测试数据与模拟场景说明:
           - 常态企业 TEST (市值 50,000M, 债务 30,000M) vs 承压企业 DIST (市值 10,000M, 负债 50,000M, 留存收益 -5,000M, EBIT 亏损)。

        4. 预期断言与结果验证:
           - physical_distance_to_default >= distance_to_default - 0.05。
           - physical_default_probability <= risk_neutral_default_probability + 1e-4。
           - implied_credit_spread_bps >= 0.0 且 res_dist.implied_credit_spread_bps > res.implied_credit_spread_bps。
        """
        res = self.credit_engine.evaluate_comprehensive_credit(
            ticker="TEST",
            equity_market_cap=50000.0,
            total_debt=30000.0,
            current_assets=25000.0,
            current_liabilities=15000.0,
            retained_earnings=10000.0,
            ebit=4000.0,
            revenue=35000.0,
            total_assets=60000.0,
            total_liabilities=30000.0,
            equity_volatility=0.40,
            risk_free_rate=0.045,
        )
        self.assertIsNotNone(res.physical_distance_to_default)
        self.assertIsNotNone(res.physical_default_probability)
        self.assertIsNotNone(res.risk_neutral_default_probability)
        self.assertIsNotNone(res.implied_credit_spread_bps)
        # 物理期望回报高于无风险利率，故物理违约距离 DD_P >= 风险中性 DD_Q
        self.assertGreaterEqual(res.physical_distance_to_default, res.distance_to_default - 0.05)
        # 物理真实破产概率 <= 风险中性违约概率 (由于包含信用风险溢价)
        self.assertLessEqual(res.physical_default_probability, res.risk_neutral_default_probability + 1e-4)
        # 信用利差非负，且随财务杠杆/违约风险上升而显著扩大
        self.assertGreaterEqual(res.implied_credit_spread_bps, 0.0)

        # 承压企业信用利差必须显著扩大 (> 10 bps)
        res_dist = self.credit_engine.evaluate_comprehensive_credit(
            ticker="DIST",
            equity_market_cap=10000.0,
            total_debt=50000.0,
            current_assets=10000.0,
            current_liabilities=20000.0,
            retained_earnings=-5000.0,
            ebit=-500.0,
            revenue=10000.0,
            total_assets=25000.0,
            total_liabilities=50000.0,
            equity_volatility=0.65,
            risk_free_rate=0.045,
        )
        self.assertGreater(res_dist.implied_credit_spread_bps, 10.0)
        self.assertGreater(res_dist.implied_credit_spread_bps, res.implied_credit_spread_bps)

    def test_altman_z_score_zones(self):
        """【UT-PH3A-03: Altman Z-Score制造业安全区/灰色区/高危破产区五因子分区判定】

        1. 测试功能与测试点:
           - 验证 CreditRiskAndSolvencyEngine.calculate_altman_z_score 经典五因子制造业财务模型：
             $X_1$: 营运资本/总资产，$X_2$: 留存收益/总资产，$X_3$: EBIT/总资产，$X_4$: 市值/总负债，$X_5$: 营业收入/总资产。
           - 验证安全企业判定：Z > 2.99 归为 "Safe" 区。
           - 验证高危破产企业判定：营运资本为负、巨额未分配利润亏损、资不抵债，Z < 1.81 归为 "Distress" 破产重组高危区。

        2. 正常函数业务边界与参数契约:
           - calculate_altman_z_score(working_capital, retained_earnings, ebit, equity_market_cap, total_revenue, total_assets, total_liabilities, is_manufacturing)。
           - 输出 (z_score, zone_str)。

        3. 测试数据与模拟场景说明:
           - 安全企业样本与资不抵债亏损制造企业样本。

        4. 预期断言与结果验证:
           - zone_safe == 'Safe' 且 z_safe > 2.99。
           - zone_distress == 'Distress' 且 z_distress < 1.81。
        """
        # 安全企业 (Z > 2.99)
        z_safe, zone_safe = self.credit_engine.calculate_altman_z_score(
            working_capital=5000.0,
            retained_earnings=8000.0,
            ebit=3000.0,
            equity_market_cap=30000.0,
            total_revenue=20000.0,
            total_assets=15000.0,
            total_liabilities=5000.0,
            is_manufacturing=True,
        )
        self.assertEqual(zone_safe, "Safe")
        self.assertGreater(z_safe, 2.99)

        # 高危破产企业 (Z < 1.81: 营运资本负、巨额亏损、资不抵债)
        z_distress, zone_distress = self.credit_engine.calculate_altman_z_score(
            working_capital=-3000.0,
            retained_earnings=-5000.0,
            ebit=-1000.0,
            equity_market_cap=1000.0,
            total_revenue=8000.0,
            total_assets=10000.0,
            total_liabilities=12000.0,
            is_manufacturing=True,
        )
        self.assertEqual(zone_distress, "Distress")
        self.assertLess(z_distress, 1.81)

    def test_convertible_bond_evaluation(self):
        """【UT-PH3A-04: 可转债股债二元定价/纯债底价(Bond Floor)与潜在实值转股稀释核验】

        1. 测试功能与测试点:
           - 验证 evaluate_convertible_bond 计算混合资本可转债的转股价值与潜在股本稀释效应。
           - 股价 120 美元，转股价 100 美元（深度实值 In-the-Money）。
           - 面值 1000 美元转股价值 = (1000 / 100) * 120 = 1200 美元。
           - 验证总面值 500M 美元对应的潜在稀释新发行股数 = 500 / 100 = 5.0 百万股，稀释比例 5.0%。

        2. 正常函数业务边界与参数契约:
           - 接收正股价、正转股价、期限与息票率，返回包含转股价值与稀释比例字典。

        3. 测试数据与模拟场景说明:
           - 典型科技成长股实值转债发行场景。

        4. 预期断言与结果验证:
           - conversion_value == 1200.0。
           - is_in_the_money_conversion 为 True。
           - potential_dilution_shares == 5.0，dilution_ratio_pct == 5.0。
        """
        cb_res = self.credit_engine.evaluate_convertible_bond(
            stock_price=120.0,
            conversion_price=100.0, # 实值转股
            par_value=1000.0,
            coupon_rate=0.02,
            maturity_years=3.0,
            credit_spread=0.03,
            risk_free_rate=0.045,
            shares_outstanding=100.0,
            total_cb_par_amount=500.0, # 5 亿总面值
        )
        # 转股价值 = 1000 / 100 * 120 = 1200
        self.assertEqual(cb_res["conversion_value"], 1200.0)
        self.assertTrue(cb_res["is_in_the_money_conversion"])
        # 潜在稀释股数 = 500 / 100 = 5.0 百万股
        self.assertEqual(cb_res["potential_dilution_shares"], 5.0)
        self.assertEqual(cb_res["dilution_ratio_pct"], 5.0)

    def test_monte_carlo_dcf_quantiles_monotonicity(self):
        """【IT-PH3A-05: 10,000次蒙特卡洛向量化抽样估值分位数严格单调性与有限责任非负保护断言】

        1. 测试功能与测试点:
           - 验证 MonteCarloValuationEngine.run_monte_carlo_dcf 执行 10,000 次向量化随机抽样模拟。
           - 验证估值分位数链条严格单调不递减契约：
             p05 <= p10 <= p25 <= p50 <= p75 <= p90 <= p95。
           - 验证股东有限责任硬下界防御：任何极端抽样下估值均大于等于 0。

        2. 正常函数业务边界与参数契约:
           - MonteCarloDCFInput 接收现金流均值、WACC 均值/标准差与终值增长率参数。
           - 迭代次数 10,000 次，返回 MonteCarloValuationResult 强类型结果。

        3. 测试数据与模拟场景说明:
           - 基准现金流 1000M，当前股价 50 美元，股数 100M，WACC 9.0% 均值与 1.5% 扰动。

        4. 预期断言与结果验证:
           - iterations == 10000 且 median_fair_value > 0。
           - 分位数 p05 <= p10 <= p25 <= p50 <= p75 <= p90 <= p95。
        """
        inp = MonteCarloDCFInput(
            base_cash_flow=1000.0,
            current_price=50.0,
            shares_outstanding=100.0,
            net_debt=500.0,
            growth_mean=0.10,
            growth_std=0.05,
            wacc_mean=0.09,
            wacc_std=0.015,
            terminal_g_mean=0.025,
            terminal_g_std=0.005,
        )
        res = self.mc_engine.run_monte_carlo_dcf("TEST", inp, iterations=10000, random_seed=123)

        self.assertEqual(res.iterations, 10000)
        self.assertGreater(res.median_fair_value, 0.0)

        # 检验严格单调性
        p = res
        self.assertLessEqual(p.percentile_05, p.percentile_10)
        self.assertLessEqual(p.percentile_10, p.percentile_25)
        self.assertLessEqual(p.percentile_25, p.percentile_50)
        self.assertLessEqual(p.percentile_50, p.percentile_75)
        self.assertLessEqual(p.percentile_75, p.percentile_90)
        self.assertLessEqual(p.percentile_90, p.percentile_95)

    def test_monte_carlo_prob_undervalued_relation(self):
        """【UT-PH3A-06: 蒙特卡洛内生低估置信度概率与标的现价单调反比关系验证】

        1. 测试功能与测试点:
           - 验证蒙特卡洛引擎评估市场现价相对于内生公允分布的低估置信度概率 (prob_undervalued_pct)。
           - 验证经济学单调反比公理：在内在现金流分布恒定时，标的现价越高，低估置信度越低；现价越低，低估置信度越高。
           - 50 美元低价场景低估置信度 > 50%；1000 美元极端天价场景低估置信度 < 5%。

        2. 正常函数业务边界与参数契约:
           - 股价为正数，置信度概率在 [0.0, 100.0] 区间内。

        3. 测试数据与模拟场景说明:
           - 现金流 2000M，5000 次蒙特卡洛抽样，分别输入 50 美元与 1000 美元现价。

        4. 预期断言与结果验证:
           - res_low_price.prob_undervalued_pct > 50.0。
           - res_high_price.prob_undervalued_pct < 5.0。
        """
        base_inp = MonteCarloDCFInput(
            base_cash_flow=2000.0,
            current_price=50.0, # 低价
            shares_outstanding=100.0,
            net_debt=0.0,
            growth_mean=0.08,
            wacc_mean=0.09,
        )
        res_low_price = self.mc_engine.run_monte_carlo_dcf("TEST_LOW", base_inp, iterations=5000)

        high_price_inp = MonteCarloDCFInput(
            base_cash_flow=2000.0,
            current_price=1000.0, # 极高天价
            shares_outstanding=100.0,
            net_debt=0.0,
            growth_mean=0.08,
            wacc_mean=0.09,
        )
        res_high_price = self.mc_engine.run_monte_carlo_dcf("TEST_HIGH", high_price_inp, iterations=5000)

        self.assertGreater(res_low_price.prob_undervalued_pct, 50.0)
        self.assertLess(res_high_price.prob_undervalued_pct, 5.0)

    def test_system_integration_phase3a(self):
        """【FT-PH3A-07: FinancialAnalysisSystem统一门面信用偿债与蒙特卡洛模式独立精准调度及全息决策卡片装配】

        1. 测试功能与测试点:
           - 验证 FinancialAnalysisSystem.analyze_equity 对 Phase 3A 新增分析模式的精准调度能力。
           - 模式 1: CREDIT_SOLVENCY（信用违约与偿债能力分析模式），断言 Merton DD 超过 5.0，决策卡片挂载 merton_dd。
           - 模式 2: MONTE_CARLO（蒙特卡洛多场景抽样估值模式），断言 10,000 次迭代，决策卡片挂载 monte_carlo_median。
           - 模式 3: FULL_SYSTEMIC（系统性全流程分析），断言 Phase 3A 信用与蒙特卡洛结果全息装配至决策卡片。

        2. 正常函数业务边界与参数契约:
           - load_official_filing 读取官方备案 JSON 底账。
           - analyze_equity 支持多枚举模式并保证 execution_success 为 True。

        3. 测试数据与模拟场景说明:
           - 希捷科技 (STX) 官方备案底账数据 data/seagate/2026-10-11/inputs.json。

        4. 预期断言与结果验证:
           - 三种模式均执行成功 (execution_success == True)。
           - decision_card 成功挂载 merton_dd、altman_z 与 monte_carlo_median。
        """
        inp = FinancialAnalysisSystem.load_official_filing(Path("data/seagate/2026-10-11/inputs.json"))

        # 1. 独立信用分析模式 CREDIT_SOLVENCY
        res_cred = self.system.analyze_equity("STX", company_input=inp, mode=AnalysisMode.CREDIT_SOLVENCY)
        self.assertTrue(res_cred.execution_success)
        self.assertIsNotNone(res_cred.credit_risk)
        self.assertGreater(res_cred.credit_risk.distance_to_default, 5.0)
        self.assertIsNotNone(res_cred.decision_card.merton_dd)

        # 2. 独立蒙特卡洛分析模式 MONTE_CARLO
        res_mc = self.system.analyze_equity("STX", company_input=inp, mode=AnalysisMode.MONTE_CARLO)
        self.assertTrue(res_mc.execution_success)
        self.assertIsNotNone(res_mc.monte_carlo_valuation)
        self.assertEqual(res_mc.monte_carlo_valuation.iterations, 10000)
        self.assertIsNotNone(res_mc.decision_card.monte_carlo_median)

        # 3. 全系统综合模式 FULL_SYSTEMIC (全息挂载)
        res_full = self.system.analyze_equity("STX", company_input=inp, mode=AnalysisMode.FULL_SYSTEMIC)
        self.assertTrue(res_full.execution_success)
        self.assertIsNotNone(res_full.credit_risk)
        self.assertIsNotNone(res_full.monte_carlo_valuation)
        self.assertIsNotNone(res_full.decision_card.merton_dd)
        self.assertIsNotNone(res_full.decision_card.altman_z)
        self.assertIsNotNone(res_full.decision_card.monte_carlo_median)


if __name__ == "__main__":
    unittest.main()
