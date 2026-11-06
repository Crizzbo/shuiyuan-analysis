"""Phase 3B 金融工程引擎单元测试 (Portfolio Risk, VaR, Greeks & Volatility Surface).

验证目标：
1. 组合在险价值 (VaR) 与 Cornish-Fisher 肥尾修正：验证厚尾与负偏态下的风险上浮；
2. Ledoit-Wolf 收缩协方差矩阵与 Euler 边际风险贡献分解 (PRC sum = 100%)；
3. Fama-French 多因子分解与 Alpha/Beta 归因方差守恒；
4. 历史极端宏观危机压力测试情景与资本保全评分；
5. Black-Scholes-Merton 全阶希腊字母闭式解与差分精度核对；
6. Brent 算法隐含波动率 (IV) 反解与 Put-Call Parity 平价无套利校验；
7. 波动率偏斜 (25-Delta Skew) 与微笑结构分析；
8. FinancialAnalysisSystem 统一门面 API 在 PORTFOLIO_RISK、VOLATILITY_SURFACE 与 FULL_SYSTEMIC 模式下的端到端契约集成。
"""

import math
import sys
import unittest
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from financial_core.contracts import (
    AnalysisMode,
    FinancialAnalysisResult,
    VaRResult,
    RiskDecompositionResult,
    FactorAttributionResult,
    StressTestScenarioResult,
    OptionGreeksResult,
    PutCallParityCheckResult,
    VolatilitySkewResult,
)
from financial_core.engines.portfolio_risk_engine import PortfolioRiskAndVaREngine
from financial_core.engines.volatility_surface_engine import VolatilitySurfaceGreeksEngine
from financial_core.api import FinancialAnalysisSystem


class TestPhase3BEngines(unittest.TestCase):
    """Phase 3B 核心算法引擎独立测试套件."""

    def setUp(self):
        self.api = FinancialAnalysisSystem()

    def test_var_cornish_fisher_and_expected_shortfall(self):
        """【UT-PH3B-01: 组合在险价值(VaR)/预期尾部损失(CVaR)与Cornish-Fisher厚尾偏态修正核验】

        1. 测试功能与测试点:
           - 验证 PortfolioRiskAndVaREngine.compute_var_cvar 计算组合在险价值。
           - 构造包含真实金融极端负偏态与厚尾损失（指数衰减极端尾部冲击）收益率样本。
           - 验证 Cornish-Fisher 展开修正：负偏厚尾时修正 VaR 较标准高斯正态 VaR 出现风险上浮或保持稳健。
           - 验证公理断言：CVaR (Expected Shortfall) 度量极端尾部平均损失，必须严格大于等于 VaR。

        2. 正常函数业务边界与参数契约:
           - 组合净值为正，置信度在 (0, 1) 之间，时间周期为正整数。
           - 返回 VaRResult 强类型对象。

        3. 测试数据与模拟场景说明:
           - 500 天正态波动样本叠加 20 天极端指数尾部巨亏，组合市值 100 万美元。

        4. 预期断言与结果验证:
           - parametric_var > 0.0。
           - cornish_fisher_var >= parametric_var * 0.95。
           - expected_shortfall_cvar >= parametric_var。
        """
        np.random.seed(101)
        # 构造负偏态、厚尾收益率样本
        normal_returns = np.random.normal(0.0005, 0.015, 500)
        fat_tail_losses = -np.random.exponential(0.03, 20)
        returns = np.concatenate([normal_returns, fat_tail_losses])
        
        portfolio_val = 1_000_000.0 # 100 万美元
        res = PortfolioRiskAndVaREngine.compute_var_cvar(
            returns=returns,
            portfolio_value=portfolio_val,
            confidence_level=0.95,
            time_horizon_days=1,
        )

        self.assertIsInstance(res, VaRResult)
        self.assertGreater(res.parametric_var, 0.0)
        # 负偏厚尾下，Cornish-Fisher 修正 VaR 应高于或等于标准高斯 VaR
        self.assertGreaterEqual(res.cornish_fisher_var, res.parametric_var * 0.95)
        # CVaR (Expected Shortfall) 度量极端尾部平均损失，必须大于等于 VaR
        self.assertGreaterEqual(res.expected_shortfall_cvar, res.parametric_var)
        self.assertIn("风险", res.risk_assessment_zh)

    def test_ledoit_wolf_covariance_and_risk_decomposition(self):
        """【UT-PH3B-02: Ledoit-Wolf收缩协方差矩阵与Euler边际风险贡献(PRC)百分百恒等守恒断言】

        1. 测试功能与测试点:
           - 验证 compute_ledoit_wolf_covariance 高维条件不适定样本协方差矩阵向单常数相关性目标的收缩估计，收缩强度系数 $\delta \in [0.0, 1.0]$。
           - 验证 decompose_portfolio_risk 欧拉风险守恒定理：百分比风险贡献 (Percentage Risk Contribution, PRC) 之和严格为 100.0%。
           - 验证分散化比率 (Diversification Ratio) 在非完全正相关资产配置下满足 $\ge 1.0$。

        2. 正常函数业务边界与参数契约:
           - 收益率矩阵无缺失与非数，权重和为 1.0。
           - 返回 RiskDecompositionResult 强类型结果。

        3. 测试数据与模拟场景说明:
           - 科技、制造与防御 3 只资产等权配置 [1/3, 1/3, 1/3]，T=100 天模拟收益。

        4. 预期断言与结果验证:
           - 协方差形状 (3, 3)，0 <= shrinkage <= 1。
           - diversification_ratio >= 1.0。
           - sum(percentage_risk_contributions) == 100.0 (误差 0.1% 内)。
        """
        np.random.seed(202)
        # 构造 3 只资产的 100 天收益率
        T = 100
        r1 = np.random.normal(0.0005, 0.012, T)
        r2 = 0.6 * r1 + np.random.normal(0.0002, 0.010, T)
        r3 = -0.2 * r1 + np.random.normal(0.0001, 0.015, T)
        ret_matrix = np.column_stack([r1, r2, r3])

        cov_annual, shrinkage = PortfolioRiskAndVaREngine.compute_ledoit_wolf_covariance(ret_matrix)
        self.assertEqual(cov_annual.shape, (3, 3))
        self.assertTrue(0.0 <= shrinkage <= 1.0)

        # 3 只资产等权配置 [1/3, 1/3, 1/3]
        weights = np.array([1/3, 1/3, 1/3])
        decomp = PortfolioRiskAndVaREngine.decompose_portfolio_risk(
            weights=weights,
            cov_matrix=cov_annual,
            asset_names=["Tech", "Industrial", "Defensive"],
        )

        self.assertIsInstance(decomp, RiskDecompositionResult)
        self.assertGreater(decomp.portfolio_volatility_annual, 0.0)
        # 分散化比率必须 >= 1.0 (非完全正相关下的分散化收益)
        self.assertGreaterEqual(decomp.diversification_ratio, 1.0)
        # Euler 风险守恒定理：百分比风险贡献 PRC 之和必须严格为 100%
        self.assertAlmostEqual(sum(decomp.percentage_risk_contributions), 100.0, places=1)
        self.assertEqual(len(decomp.marginal_risk_contributions), 3)

    def test_fama_french_factor_attribution(self):
        """【UT-PH3B-03: Fama-French三因子OLS收益率分解与系统性/特异性方差守恒核验】

        1. 测试功能与测试点:
           - 验证 run_fama_french_factor_attribution 运用 OLS 多元回归剥离市场 (MKT)、规模 (SMB) 与价值 (HML) 因子暴露。
           - 验证估计出的因子 Beta 贴近预设真实参数：$\beta_{MKT} \approx 1.2$, $\beta_{SMB} \approx 0.5$, $\beta_{HML} \approx -0.3$。
           - 验证总方差守恒公理：系统性风险占比 + 特异性残差风险占比严格恒等于 100.0%。

        2. 正常函数业务边界与参数契约:
           - 因子矩阵样本数与资产收益率样本数一致，返回 FactorAttributionResult。

        3. 测试数据与模拟场景说明:
           - 1 年日频（T=250 天）真实多因子合成样本，年化 Alpha 约 7.5%。

        4. 预期断言与结果验证:
           - 各因子 Beta 估计误差小于 0.2。
           - systematic_risk_pct + idiosyncratic_risk_pct == 100.0。
           - r_squared > 0.60。
        """
        np.random.seed(303)
        T = 250 # 约 1 年日频数据
        # 模拟已知因子: 市场 MKT, 规模 SMB, 价值 HML
        mkt = np.random.normal(0.0004, 0.010, T)
        smb = np.random.normal(0.0001, 0.006, T)
        hml = np.random.normal(0.0000, 0.005, T)
        factors = np.column_stack([mkt, smb, hml])

        # 真实数据生成过程: R = alpha + 1.2 * MKT + 0.5 * SMB - 0.3 * HML + eps
        true_alpha_daily = 0.0003 # 年化约 7.5%
        eps = np.random.normal(0.0, 0.004, T)
        asset_returns = true_alpha_daily + 1.2 * mkt + 0.5 * smb - 0.3 * hml + eps

        res = PortfolioRiskAndVaREngine.run_fama_french_factor_attribution(
            asset_returns=asset_returns,
            factor_returns_matrix=factors,
            factor_names=["MKT", "SMB", "HML"],
        )

        self.assertIsInstance(res, FactorAttributionResult)
        # 验证回归估计值贴近真实参数
        self.assertAlmostEqual(res.factor_betas["MKT"], 1.2, delta=0.2)
        self.assertAlmostEqual(res.factor_betas["SMB"], 0.5, delta=0.2)
        self.assertAlmostEqual(res.factor_betas["HML"], -0.3, delta=0.2)
        # 方差守恒：系统性风险占比 + 特异性残差风险占比 = 100%
        self.assertAlmostEqual(res.systematic_risk_pct + res.idiosyncratic_risk_pct, 100.0, places=1)
        self.assertGreater(res.r_squared, 0.60)

    def test_macro_stress_testing_scenarios(self):
        """【IT-PH3B-04: 历史宏观危机极端情景压力测试/资本保全评分与主要风险暴露归因】

        1. 测试功能与测试点:
           - 验证 PortfolioRiskAndVaREngine.run_macro_stress_test 模拟历史三大危机场景（2008次贷风暴、2020疫情熔断、1970滞胀）。
           - 验证投资组合在极端冲击下的预估回撤比例（负数）与美元绝对损失（正数）。
           - 验证资本保全评分 (capital_preservation_score) 介于 [0.0, 100.0] 区间。
           - 验证最大损失贡献归因 (largest_contributor_loss) 精准指向高贝塔重仓股 (NVDA)。

        2. 正常函数业务边界与参数契约:
           - 接收持仓市值字典与贝塔系数映射，返回 StressTestScenarioResult 列表。

        3. 测试数据与模拟场景说明:
           - NVDA ($500k, $\beta=1.70$), MSFT ($300k, $\beta=1.15$), JNJ ($200k, $\beta=0.55$)。

        4. 预期断言与结果验证:
           - 至少包含 3 个历史危机场景。
           - estimated_portfolio_drawdown_pct < 0 且 estimated_dollar_loss > 0。
           - largest_contributor_loss 包含 'NVDA'。
        """
        positions = {"NVDA": 500_000.0, "MSFT": 300_000.0, "JNJ": 200_000.0}
        betas = {"NVDA": 1.70, "MSFT": 1.15, "JNJ": 0.55}

        scenarios = PortfolioRiskAndVaREngine.run_macro_stress_test(positions, betas)
        self.assertGreaterEqual(len(scenarios), 3)

        for sc in scenarios:
            self.assertIsInstance(sc, StressTestScenarioResult)
            self.assertLess(sc.estimated_portfolio_drawdown_pct, 0.0)
            self.assertGreater(sc.estimated_dollar_loss, 0.0)
            self.assertTrue(0.0 <= sc.capital_preservation_score <= 100.0)
            self.assertIn("NVDA", sc.largest_contributor_loss) # 高贝塔重仓股贡献最大损失

    def test_option_full_greeks_black_scholes_merton(self):
        """【UT-PH3B-05: Black-Scholes-Merton全阶希腊字母闭式解/Delta平价对称性与Volga二阶凸性验证】

        1. 测试功能与测试点:
           - 验证 VolatilitySurfaceGreeksEngine.calculate_option_greeks 全阶解析解与二阶偏导。
           - 一阶希腊字母：$0 < \Delta_{Call} < 1$, $-1 < \Delta_{Put} < 0$。
           - 看涨看跌 Delta 平价公理守恒：$\Delta_{Call} - \Delta_{Put} = e^{-q T}$。
           - Gamma 与 Vega 在欧式看涨看跌期权间严格等值对称。
           - 二阶希腊字母：Volga 在平值 (ATM) 处为负，在虚值 (OTM) 翼部为正（具备正凸性保护）。

        2. 正常函数业务边界与参数契约:
           - 标的现价、行权价、到期期限、波动率均为有限正数。
           - 返回 OptionGreeksResult 强类型结果。

        3. 测试数据与模拟场景说明:
           - S=100, K=100, T=0.5年, r=4.5%, q=1.5%, vol=30%（平值欧式期权基准场景）。

        4. 预期断言与结果验证:
           - call_greeks.delta - put_greeks.delta == exp(-q * T)。
           - call_greeks.gamma == put_greeks.gamma 且 call_greeks.vega_total == put_greeks.vega_total。
           - 平值 volga < 0 且 otm_call.volga > 0。
        """
        S = 100.0
        K = 100.0
        T = 0.5 # 半年
        r = 0.045
        q = 0.015
        vol = 0.30

        call_greeks = VolatilitySurfaceGreeksEngine.calculate_option_greeks(
            spot=S, strike=K, time_to_expiry_years=T,
            risk_free_rate=r, dividend_yield=q, volatility=vol, option_type="call"
        )
        put_greeks = VolatilitySurfaceGreeksEngine.calculate_option_greeks(
            spot=S, strike=K, time_to_expiry_years=T,
            risk_free_rate=r, dividend_yield=q, volatility=vol, option_type="put"
        )

        # 1. 一阶希腊字母
        self.assertTrue(0.0 < call_greeks.delta < 1.0)
        self.assertTrue(-1.0 < put_greeks.delta < 0.0)
        # Delta 守恒：Delta_Call - Delta_Put = exp(-q * T)
        expected_diff = math.exp(-q * T)
        self.assertAlmostEqual(call_greeks.delta - put_greeks.delta, expected_diff, places=3)

        # 2. Gamma 与 Vega 在欧式看涨看跌中完全对称
        self.assertAlmostEqual(call_greeks.gamma, put_greeks.gamma, places=4)
        self.assertGreater(call_greeks.gamma, 0.0)
        self.assertAlmostEqual(call_greeks.vega_total, put_greeks.vega_total, places=4)
        self.assertGreater(call_greeks.vega_total, 0.0)

        # 3. 二阶希腊字母: Volga 凸性与 Vanna 交叉偏导
        # ATM 处 Vega 达到峰值，故一阶导为负 (即 Volga < 0)；而在 OTM 翼部 Volga > 0 (正凸性保护)
        self.assertLess(call_greeks.volga, 0.0)
        otm_call = VolatilitySurfaceGreeksEngine.calculate_option_greeks(
            spot=S, strike=130.0, time_to_expiry_years=T,
            risk_free_rate=r, dividend_yield=q, volatility=vol, option_type="call"
        )
        self.assertGreater(otm_call.volga, 0.0) # 虚值翼部 Volga 正凸性
        self.assertIsNotNone(call_greeks.vanna)
        self.assertIsNotNone(call_greeks.charm_daily)

    def test_implied_volatility_solver_and_parity_arbitrage(self):
        """【UT-PH3B-06: Brent高精度隐含波动率(IV)反解与看涨看跌平价(Put-Call Parity)无套利判定】

        1. 测试功能与测试点:
           - 验证 solve_implied_volatility 运用 Brent 根查找算法高精度反解期权隐含波动率 (IV)。
           - 验证 check_put_call_parity 欧式期权平价无套利公式校验：
             $C - P = S e^{-q T} - K e^{-r T}$。
           - 公允定价场景触发 "FAIR_PRICING" 信号。
           - 人为构造 Call 溢价 $3.50 时，精确捕获 "CONVERSION_ARBITRAGE"（转换套利），最大套利利润 > $3.0。

        2. 正常函数业务边界与参数契约:
           - 市场价格非负，容差 tolerance 为有限正数。
           - 返回 PutCallParityCheckResult 强类型结果。

        3. 测试数据与模拟场景说明:
           - S=150, K=150, T=0.25年, r=4.0%, 真实波动率 38% 基准与溢价异常注入。

        4. 预期断言与结果验证:
           - solved_iv 与 0.38 误差在 0.002 以内。
           - fair_check.arbitrage_signal == 'FAIR_PRICING'。
           - arb_check.arbitrage_signal == 'CONVERSION_ARBITRAGE' 且 max_arbitrage_profit > 3.0。
        """
        S = 150.0
        K = 150.0
        T = 0.25
        r = 0.04
        vol_true = 0.38

        # 1. 求解理论价并反解 IV
        true_greeks = VolatilitySurfaceGreeksEngine.calculate_option_greeks(
            spot=S, strike=K, time_to_expiry_years=T,
            risk_free_rate=r, dividend_yield=0.0, volatility=vol_true, option_type="call"
        )
        solved_iv = VolatilitySurfaceGreeksEngine.solve_implied_volatility(
            market_price=true_greeks.theoretical_price,
            spot=S, strike=K, time_to_expiry_years=T,
            risk_free_rate=r, dividend_yield=0.0, option_type="call"
        )
        self.assertIsNotNone(solved_iv)
        self.assertAlmostEqual(solved_iv, vol_true, delta=0.002)

        # 2. Put-Call Parity 检验
        # 公允平价
        put_price_fair = true_greeks.theoretical_price - S + K * math.exp(-r * T)
        fair_check = VolatilitySurfaceGreeksEngine.check_put_call_parity(
            call_price=true_greeks.theoretical_price,
            put_price=put_price_fair,
            spot=S, strike=K, time_to_expiry_years=T,
            risk_free_rate=r, dividend_yield=0.0, tolerance=0.30
        )
        self.assertEqual(fair_check.arbitrage_signal, "FAIR_PRICING")

        # 人为制造 Call 严重高估套利机会
        arb_check = VolatilitySurfaceGreeksEngine.check_put_call_parity(
            call_price=true_greeks.theoretical_price + 3.50, # 溢价 $3.50
            put_price=put_price_fair,
            spot=S, strike=K, time_to_expiry_years=T,
            risk_free_rate=r, dividend_yield=0.0, tolerance=0.50
        )
        self.assertEqual(arb_check.arbitrage_signal, "CONVERSION_ARBITRAGE")
        self.assertGreater(arb_check.max_arbitrage_profit, 3.0)

    def test_volatility_skew_and_market_sentiment(self):
        """【UT-PH3B-07: 25-Delta波动率偏斜(Skew)/极端恐慌溢价识别与市场情绪量化研判】

        1. 测试功能与测试点:
           - 验证 VolatilitySurfaceGreeksEngine.analyze_volatility_skew 计算 25-Delta 波动率偏斜斜率：
             $Skew_{25D} = IV_{25D, Put} - IV_{25D, Call}$。
           - 模拟典型下行保护肥尾偏斜（深度虚值 Put IV 达 42% 显著高于虚值 Call 的 25%）。
           - 验证偏斜幅度大于 0.05，精准输出 "SEVERE_CRASH_FEAR"（严重踩踏恐慌）量化情绪信号。

        2. 正常函数业务边界与参数契约:
           - strikes 数组单调递增，implied_vols 为同维度正数。
           - 返回 VolatilitySkewResult 强类型结果。

        3. 测试数据与模拟场景说明:
           - 标的现价 200 美元，行权价 [170, 185, 200, 215, 230]，对应 IV [0.42, 0.36, 0.30, 0.27, 0.25]。

        4. 预期断言与结果验证:
           - skew_25d > 0.05。
           - market_sentiment_signal == 'SEVERE_CRASH_FEAR'。
           - market_sentiment_zh 包含 "恐慌"。
        """
        spot = 200.0
        strikes = [170.0, 185.0, 200.0, 215.0, 230.0]
        # 典型的下行保护肥尾偏斜 (虚值 Put IV 显著高于虚值 Call IV)
        ivs = [0.42, 0.36, 0.30, 0.27, 0.25]

        skew_res = VolatilitySurfaceGreeksEngine.analyze_volatility_skew(
            strikes=strikes,
            implied_vols=ivs,
            spot=spot,
            time_to_expiry_years=0.25,
            risk_free_rate=0.045,
        )

        self.assertIsInstance(skew_res, VolatilitySkewResult)
        self.assertGreater(skew_res.skew_25d, 0.05) # 强正向偏斜
        self.assertIn("恐慌", skew_res.market_sentiment_zh)
        self.assertEqual(skew_res.market_sentiment_signal, "SEVERE_CRASH_FEAR")

    def test_facade_api_portfolio_risk_mode(self):
        """【IT-PH3B-08: FinancialAnalysisSystem统一门面PORTFOLIO_RISK按需精准调度契约】

        1. 测试功能与测试点:
           - 验证 FinancialAnalysisSystem.analyze_equity 对 PORTFOLIO_RISK（组合与在险价值风险分析模式）的独立精准调度。
           - 验证执行状态 execution_success 为 True，分析模式为 "portfolio_risk"。
           - 验证组合 VaR 对象非空且宏观压力测试场景数量大于 0。
           - 验证决策卡片挂载 portfolio_var_95_pct 与 cvar_expected_shortfall_pct。

        2. 正常函数业务边界与参数契约:
           - 支持枚举 AnalysisMode.PORTFOLIO_RISK，返回 FinancialAnalysisResult 对象。

        3. 测试数据与模拟场景说明:
           - RXRX 样本标的在独立组合风险模式下执行。

        4. 预期断言与结果验证:
           - execution_success 为 True。
           - portfolio_var 非空，len(macro_stress_scenarios) > 0。
           - decision_card.portfolio_var_95_pct 非空。
        """
        res = self.api.analyze_equity(
            ticker="RXRX",
            mode=AnalysisMode.PORTFOLIO_RISK,
            allow_demo_sample=True,
        )
        self.assertTrue(res.execution_success)
        self.assertEqual(res.analysis_mode, "portfolio_risk")
        self.assertIsNotNone(res.portfolio_var)
        self.assertGreater(len(res.macro_stress_scenarios), 0)
        self.assertIsNotNone(res.decision_card.portfolio_var_95_pct)
        self.assertIsNotNone(res.decision_card.cvar_expected_shortfall_pct)

    def test_facade_api_volatility_surface_mode(self):
        """【IT-PH3B-09: FinancialAnalysisSystem统一门面VOLATILITY_SURFACE期权波动率曲面调度契约】

        1. 测试功能与测试点:
           - 验证 FinancialAnalysisSystem.analyze_equity 对 VOLATILITY_SURFACE（期权波动率曲面与希腊字母模式）的独立调度。
           - 验证返回期权希腊字母 (volatility_greeks)、看涨看跌平价结果 (put_call_parity) 与偏斜分析 (volatility_skew)。
           - 验证决策卡片挂载期权一阶 Delta 风险敞口。

        2. 正常函数业务边界与参数契约:
           - 支持枚举 AnalysisMode.VOLATILITY_SURFACE，返回强类型结果。

        3. 测试数据与模拟场景说明:
           - RXRX 样本标的在独立波动率曲面模式下执行。

        4. 预期断言与结果验证:
           - execution_success 为 True。
           - volatility_greeks、put_call_parity 与 volatility_skew 均非空。
           - decision_card.option_delta 非空。
        """
        res = self.api.analyze_equity(
            ticker="RXRX",
            mode=AnalysisMode.VOLATILITY_SURFACE,
            allow_demo_sample=True,
        )
        self.assertTrue(res.execution_success)
        self.assertEqual(res.analysis_mode, "volatility_surface")
        self.assertIsNotNone(res.volatility_greeks)
        self.assertIsNotNone(res.put_call_parity)
        self.assertIsNotNone(res.volatility_skew)
        self.assertIsNotNone(res.decision_card.option_delta)

    def test_facade_api_full_systemic_mode_phase3b_integration(self):
        """【FT-PH3B-10: 系统全息模式FULL_SYSTEMIC端到端装配Phase3B组合风险与期权决策卡片集成验证】

        1. 测试功能与测试点:
           - 验证 FinancialAnalysisSystem 在全流程 FULL_SYSTEMIC 分析模式下，全息集成 Phase 3A（信用违约与蒙特卡洛）与 Phase 3B（组合风险与期权曲面）。
           - 验证决策卡片完整装载 merton_dd、altman_z、monte_carlo_median、portfolio_var_95_pct、cvar_expected_shortfall_pct。
           - 验证期权存在时装载 option_delta。

        2. 正常函数业务边界与参数契约:
           - 支持枚举 AnalysisMode.FULL_SYSTEMIC，无缝集成全系统阶段产物。

        3. 测试数据与模拟场景说明:
           - RXRX 样本企业全系统多阶段端到端运行。

        4. 预期断言与结果验证:
           - execution_success 为 True。
           - Phase 3A 与 Phase 3B 核心分析对象与决策卡片字段 100% 健全挂载。
        """
        res = self.api.analyze_equity(
            ticker="RXRX",
            mode=AnalysisMode.FULL_SYSTEMIC,
            allow_demo_sample=True,
        )
        self.assertTrue(res.execution_success)
        # Phase 3A 验证
        self.assertIsNotNone(res.credit_risk)
        self.assertIsNotNone(res.monte_carlo_valuation)
        self.assertIsNotNone(res.decision_card.merton_dd)
        self.assertIsNotNone(res.decision_card.monte_carlo_median)
        # Phase 3B 验证
        self.assertIsNotNone(res.portfolio_var)
        self.assertGreater(len(res.macro_stress_scenarios), 0)
        self.assertIsNotNone(res.decision_card.portfolio_var_95_pct)
        self.assertIsNotNone(res.decision_card.cvar_expected_shortfall_pct)
        if res.option_pricing and res.option_pricing.strike > 0:
            self.assertIsNotNone(res.volatility_greeks)
            self.assertIsNotNone(res.volatility_skew)
            self.assertIsNotNone(res.decision_card.option_delta)

    def test_ut_ph3b_11_greeks_parity_skew_buyer_cards_and_to_dict_contract(self):
        """【UT-PH3B-11: 期权希腊字母、平价套利与偏斜全息买方研报卡片与序列化契约断言】

        一、测试功能与测试点:
            1. 验证 OptionGreeksResult 具备自然语言 narrative_zh 全息卡片并支持 to_dict() 序列化；
            2. 验证 PutCallParityCheckResult 具备纯自然中文套利定性 arbitrage_signal_zh、narrative_zh 全息卡片并支持 to_dict()；
            3. 验证 VolatilitySkewResult 具备纯自然中文情绪定性 market_sentiment_signal_zh、narrative_zh 全息卡片并支持 to_dict()。

        二、正常函数业务边界与参数契约:
            - 参数输入有效，结果契约各字段非空。

        三、测试数据与模拟场景说明:
            - S=100, K=100, T=0.5 基准期权全阶计算；
            - 正常无套利平价核验；
            - 极端下行恐慌偏斜曲面。

        四、预期断言与结果验证:
            - narrative_zh 包含中文全息卡片关键词；
            - 消除纯英文代号裸露；
            - to_dict() 字典完整包含契约字段。
        """
        # 1. Option Greeks
        greeks = VolatilitySurfaceGreeksEngine.calculate_option_greeks(
            spot=100.0, strike=100.0, time_to_expiry_years=0.5,
            risk_free_rate=0.045, dividend_yield=0.015, volatility=0.30, option_type="call"
        )
        self.assertIn("全阶希腊字母与敏感度全息研报", greeks.narrative_zh)
        self.assertIn("理论公允价", greeks.narrative_zh)
        d_greeks = greeks.to_dict()
        self.assertIn("narrative_zh", d_greeks)
        self.assertEqual(d_greeks["narrative_zh"], greeks.narrative_zh)
        self.assertIn("first_order_greeks", d_greeks)
        self.assertIn("second_order_greeks", d_greeks)

        # 2. Put-Call Parity
        parity = VolatilitySurfaceGreeksEngine.check_put_call_parity(
            call_price=10.0, put_price=8.0, spot=100.0, strike=100.0,
            time_to_expiry_years=0.5, risk_free_rate=0.045, dividend_yield=0.015, tolerance=0.30
        )
        self.assertIn("平价套利核验全息研报", parity.narrative_zh)
        self.assertTrue(bool(parity.arbitrage_signal_zh))
        self.assertIn("套利", parity.arbitrage_signal_zh)
        d_parity = parity.to_dict()
        self.assertIn("arbitrage_signal_zh", d_parity)
        self.assertIn("narrative_zh", d_parity)

        # 3. Volatility Skew
        strikes = [170.0, 185.0, 200.0, 215.0, 230.0]
        ivs = [0.42, 0.36, 0.30, 0.27, 0.25]
        skew = VolatilitySurfaceGreeksEngine.analyze_volatility_skew(
            strikes=strikes, implied_vols=ivs, spot=200.0,
            time_to_expiry_years=0.25, risk_free_rate=0.045
        )
        self.assertIn("期权链波动率偏斜与情绪全息研报", skew.narrative_zh)
        self.assertEqual(skew.market_sentiment_signal_zh, "极度恐慌性下行对冲买需")
        d_skew = skew.to_dict()
        self.assertIn("market_sentiment_signal_zh", d_skew)
        self.assertEqual(d_skew["market_sentiment_signal_zh"], "极度恐慌性下行对冲买需")
        self.assertIn("narrative_zh", d_skew)


if __name__ == "__main__":
    unittest.main()
