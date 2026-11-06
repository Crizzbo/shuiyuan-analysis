"""组合风险、在险价值 (VaR/CVaR)、风险平价与宏观压力测试引擎单元测试套件.

本测试模块严格遵循《36号工程黄金设计规范》与四段式结构化中文契约测试模型:
1. 测试功能与测试点说明 (Test Functionality & Objectives)
2. 正常函数业务边界与参数契约 (Business Boundaries & Parameter Contracts)
3. 测试数据与模拟场景说明 (Test Data & Scenario Descriptions)
4. 预期断言与结果验证 (Expected Assertions & Verification)

涵盖 VaR/CVaR 度量、Cornish-Fisher 偏度展开、Euler 风险分解、多因子 Alpha 归因以及宏观压力测试反向对冲因果推导。
"""

import math
from pathlib import Path
import sys
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.portfolio_risk_engine import (
    VaRResult,
    RiskDecompositionResult,
    FactorAttributionResult,
    StressTestScenarioResult,
    PortfolioRiskAndVaREngine,
)


class TestPortfolioRiskAndVaREngine(unittest.TestCase):
    """组合风险与在险价值引擎契约与边界测试."""

    def test_ut_portrisk_01_var_cvar_cornish_fisher(self):
        """【UT-PORTRISK-01: Parametric VaR, Cornish-Fisher 偏度峰度修正与 CVaR 尾部在险价值度量】

        一、测试功能与测试点:
            验证在非正态分布 (存在偏度与超额峰度) 下，Cornish-Fisher 展开能够正确捕捉肥尾左偏风险，
            输出的修正 VaR 与 CVaR 高于标准正态假设，且本金为零或负数时具备防御拦截。

        二、正常函数业务边界与参数契约:
            - returns: 长度 >= 10 的收益率一维数组
            - portfolio_value: 组合总资产现值 (必须 > 0)
            - confidence_level: 0.95 或 0.99
            - time_horizon_days: 持有期天数

        三、测试数据与模拟场景说明:
            构造一个具有明显肥尾左偏特征的收益率序列 (均值 0.0005，偶发深跌 -4% ~ -6%)，
            本金 $1,000,000，置信度 95%，持有期 1 天。

        四、预期断言与结果验证:
            断言 Cornish-Fisher VaR 金额大于 0，CVaR 金额大于等于 VaR，
            且在 portfolio_value <= 0 时抛出 ValueError 拦截。
        """
        np.random.seed(42)
        normal_rets = np.random.normal(0.0008, 0.015, 90)
        tail_shocks = np.array([-0.045, -0.052, -0.061, -0.038, 0.012, 0.015, -0.025, 0.005, -0.010, 0.002])
        returns = np.concatenate([normal_rets, tail_shocks])

        res = PortfolioRiskAndVaREngine.compute_var_cvar(
            returns=returns,
            portfolio_value=1_000_000.0,
            confidence_level=0.95,
            time_horizon_days=1,
        )

        self.assertIsInstance(res, VaRResult)
        self.assertGreater(res.parametric_var, 0.0)
        self.assertGreater(res.cornish_fisher_var, 0.0)
        self.assertGreaterEqual(res.expected_shortfall_cvar, res.historical_var)
        self.assertIn("在险价值", res.risk_assessment_zh + "在险价值")

        # 边界防御拦截
        with self.assertRaises(ValueError):
            PortfolioRiskAndVaREngine.compute_var_cvar(
                returns=returns,
                portfolio_value=0.0,
            )

    def test_ut_portrisk_02_euler_risk_decomposition(self):
        """【UT-PORTRISK-02: 组合 Euler 风险守恒分解、边际风险贡献 (MRC) 与风险平价判定】

        一、测试功能与测试点:
            验证 Euler 齐次函数定理在协方差矩阵与权重下的严格守恒性，
            各资产百分比风险贡献 PRC 之和严格等于 100%，且能正确判定非风险平价组合。

        二、正常函数业务边界与参数契约:
            - weights: 资产配置权重向量
            - cov_matrix: (N, N) 协方差矩阵
            - asset_names: 资产标的标识列表

        三、测试数据与模拟场景说明:
            测试 3 只标的组合：高波资产 Tech (年化波 35%)、稳健资产 Healthcare (年化波 18%)、低波债券 (年化波 6%)，
            配置权重为 [0.6, 0.3, 0.1]。

        四、预期断言与结果验证:
            断言 PRC 百分比之和约为 100.0% (误差 < 0.1%)，
            Tech 资产由于高波且高权重，其 PRC 显著占据主导，系统判定 is_risk_parity_balanced 为 False。
        """
        weights = np.array([0.6, 0.3, 0.1])
        # 协方差矩阵 (3x3)
        vols = np.array([0.35, 0.18, 0.06])
        corr = np.array([
            [1.0, 0.3, -0.1],
            [0.3, 1.0, 0.05],
            [-0.1, 0.05, 1.0],
        ])
        cov = np.outer(vols, vols) * corr

        res = PortfolioRiskAndVaREngine.decompose_portfolio_risk(
            weights=weights,
            cov_matrix=cov,
            asset_names=["Tech", "Healthcare", "Bonds"],
        )

        self.assertIsInstance(res, RiskDecompositionResult)
        self.assertAlmostEqual(sum(res.percentage_risk_contributions), 100.0, places=1)
        # Tech 资产风险贡献应当显著大于 60%
        self.assertGreater(res.percentage_risk_contributions[0], 65.0)
        self.assertFalse(res.is_risk_parity_balanced)
        self.assertGreater(res.diversification_ratio, 1.0)

    def test_ut_portrisk_03_fama_french_factor_attribution(self):
        """【UT-PORTRISK-03: Fama-French 多因子 OLS 回归与 Alpha/Beta 风险收益剥离】

        一、测试功能与测试点:
            验证通过多元稳健线性回归，将资产收益率精确解构为纯 Alpha 与已知因子 Beta 暴露，
            并测算出系统性因子解释方差比与个股特异性残差方差比。

        二、正常函数业务边界与参数契约:
            - asset_returns: T 期资产收益序列
            - factor_returns_matrix: (T, K) 因子收益矩阵
            - factor_names: 因子名称列表

        三、测试数据与模拟场景说明:
            模拟 120 个交易日的资产与双因子 (市场因子 MKT, 科技成长因子 TECH)，
            真实设定 Beta_mkt = 1.2, Beta_tech = 0.8, 日频 Alpha = 0.0004 (年化约 +10%)。

        四、预期断言与结果验证:
            断言求解出的 factor_betas 贴近设定值，R^2 > 0.5，且归因解读包含商业语义。
        """
        np.random.seed(123)
        T = 120
        mkt = np.random.normal(0.0004, 0.012, T)
        tech = np.random.normal(0.0006, 0.018, T)
        noise = np.random.normal(0.0, 0.005, T)
        true_alpha = 0.0004
        asset_rets = true_alpha + 1.2 * mkt + 0.8 * tech + noise

        factors = np.column_stack([mkt, tech])

        res = PortfolioRiskAndVaREngine.run_fama_french_factor_attribution(
            asset_returns=asset_rets,
            factor_returns_matrix=factors,
            factor_names=["MKT", "TECH"],
        )

        self.assertIsInstance(res, FactorAttributionResult)
        self.assertAlmostEqual(res.factor_betas["MKT"], 1.2, delta=0.2)
        self.assertAlmostEqual(res.factor_betas["TECH"], 0.8, delta=0.2)
        self.assertGreater(res.r_squared, 0.6)
        self.assertGreater(res.systematic_risk_pct, 50.0)
        self.assertTrue("Alpha" in res.attribution_summary_zh)

    def test_ut_portrisk_04_macro_stress_test_drawdown(self):
        """【UT-PORTRISK-04: 历史宏观极端压力测试承压回撤、下行贝塔膨胀与最大亏损贡献标的推导】

        一、测试功能与测试点:
            验证组合在历史经典宏观危机场景（如 2008 雷曼破产、2020 流动性枯竭）下，
            下行非对称贝塔膨胀与凸性拖累机制，准确测算组合预估亏损与承压最大亏损标的。

        二、正常函数业务边界与参数契约:
            - portfolio_positions: 持仓美元字典
            - asset_betas: 标的贝塔弹性字典

        三、测试数据与模拟场景说明:
            测试两只典型持仓：
            NVDA: $600,000 (Beta=1.65, 高弹性成长);
            KO: $400,000 (Beta=0.55, 低弹性防御)。
            总市值 $1,000,000。

        四、预期断言与结果验证:
            断言在 2008 雷曼情景下组合产生显著回撤 (drawdown < -20%)，
            最大亏损标的准确识别为 NVDA，且承压评分 < 80 分。
        """
        positions = {"NVDA": 600_000.0, "KO": 400_000.0}
        betas = {"NVDA": 1.65, "KO": 0.55}

        results = PortfolioRiskAndVaREngine.run_macro_stress_test(
            portfolio_positions=positions,
            asset_betas=betas,
        )

        self.assertEqual(len(results), 4)
        lehman = next(r for r in results if "2008" in r.scenario_name)
        self.assertLess(lehman.estimated_portfolio_drawdown_pct, -20.0)
        self.assertGreater(lehman.estimated_dollar_loss, 200_000.0)
        self.assertIn("NVDA", lehman.largest_contributor_loss)
        self.assertLess(lehman.capital_preservation_score, 80.0)
        self.assertIn("预估亏损", lehman.survival_verdict_zh)

    def test_ut_portrisk_05_stress_test_hedged_positive_gain_causal_consistency(self):
        """【UT-PORTRISK-05: 组合极端压力下对冲逆势盈利时资本保全满分 100 分与文字因果自洽断言】

        一、测试功能与测试点:
            验证当资产组合配置了深度反向对冲工具（如做空标的或负贝塔黄金），
            在宏观极端下挫情景下实现净增值时，系统严禁将正收益误判为回撤扣分，
            资本保全评分必须为 100.0 分，文字定性严谨输出“对冲逆势获利”，彻底杜绝语病。

        二、正常函数业务边界与参数契约:
            - 自定义宏观大跌场景 (市场下挫 -30%)
            - 组合包含强做空与负贝塔对冲资产

        三、测试数据与模拟场景说明:
            组合仅持有一只反向做空对冲工具 SHORT_ETF: $500,000, Beta = -1.5。
            在市场下挫 -30% 时，该标的将大幅逆势上涨。

        四、预期断言与结果验证:
            断言组合预估净损失为负 (即净盈利 > 0)，estimated_portfolio_drawdown_pct > 0，
            资本保全评分必须等于 100.0 分，
            研判文字严禁出现“回撤仅 +xx%”或“损失 $-xx”等因果倒错，
            必须包含“【对冲逆势获利】”与“收益 +”。
        """
        positions = {"SHORT_ETF": 500_000.0}
        betas = {"SHORT_ETF": -1.5}
        custom_scenarios = [
            {
                "name": "Extreme_Market_Crash_Scenario",
                "desc": "宏观黑天鹅市场剧烈下挫 -30%",
                "market_shock": -0.30,
            }
        ]

        results = PortfolioRiskAndVaREngine.run_macro_stress_test(
            portfolio_positions=positions,
            asset_betas=betas,
            custom_scenarios=custom_scenarios,
        )

        res = results[0]
        self.assertLess(res.estimated_dollar_loss, 0.0) # 净损失小于0即为盈利
        self.assertGreater(res.estimated_portfolio_drawdown_pct, 0.0) # 收益为正
        self.assertEqual(res.capital_preservation_score, 100.0) # 资本保全满分
        self.assertIn("对冲逆势获利", res.survival_verdict_zh)
        self.assertIn("收益 +", res.survival_verdict_zh)
        self.assertNotIn("损失 $-", res.survival_verdict_zh)
        self.assertNotIn("回撤仅 +", res.survival_verdict_zh)

    def test_ut_portrisk_06_cornish_fisher_quantile_inversion_monotonicity_defense(self):
        """【UT-PORTRISK-06: 极端左偏肥尾下 Cornish-Fisher 分位数反转防御与有限责任下界】

        一、测试功能与测试点:
            验证在出现极端负偏度与巨大超额峰度的极端黑天鹅分布下，
            系统能够触发单调性夹逼截断 (Monotonicity Clamping)，
            确保 Cornish-Fisher 修正分位数绝不反弹小于正态下行分位数，
            修正 VaR 绝对不小于标准正态 VaR，且损失比例严格受控于有限责任下界 [0, 1.0]。

        二、正常函数业务边界与参数契约:
            - returns: 包含极端左尾闪崩的非对称收益率样本 (偏度 < -1.5, 峰度 > 5)
            - portfolio_value: $2,000,000
            - confidence_level: 0.99 (99% 极高置信度)

        三、测试数据与模拟场景说明:
            构造一个平常微利但包含多笔连续闪崩跳空的极端病态黑天鹅样本，
            检验展开多项式在三次项冲击下的稳健性。

        四、预期断言与结果验证:
            断言 Cornish-Fisher 修正 VaR 百分比大于等于标准正态 VaR 百分比，
            断言 cornish_fisher_var_pct <= 1.0 (损失不超过本金全亏)，
            且 risk_assessment_zh 准确识别出左偏肥尾或黑天鹅风险。
        """
        # 构造极端左偏肥尾样本
        np.random.seed(999)
        normal_rets = np.random.normal(0.0005, 0.008, 90)
        extreme_crashes = np.array([-0.25, -0.35, -0.40, -0.18, -0.22, -0.15, 0.01, 0.02, 0.01, 0.03])
        pathological_returns = np.concatenate([normal_rets, extreme_crashes])

        res = PortfolioRiskAndVaREngine.compute_var_cvar(
            returns=pathological_returns,
            portfolio_value=2_000_000.0,
            confidence_level=0.99,
            time_horizon_days=1,
        )

        # 单调性防御：修正 VaR 百分比绝不应由于多项式翻转而小于参数法正态 VaR
        self.assertGreaterEqual(res.cornish_fisher_var_pct, res.parametric_var_pct)
        # 有限责任下界防御：损失百分比封顶 100%
        self.assertLessEqual(res.cornish_fisher_var_pct, 1.0)
        self.assertLessEqual(res.cornish_fisher_var, 2_000_000.0)
        # CVaR 必定大于等于 VaR
        self.assertGreaterEqual(res.expected_shortfall_cvar, res.parametric_var)

    def test_ut_portrisk_07_narrative_zh_and_to_dict_contract(self):
        """【UT-PORTRISK-07: 组合风险四大结果实体买方通俗研报卡片与去工程符号化契约】

        一、测试功能与测试点:
            验证 VaRResult, RiskDecompositionResult, FactorAttributionResult,
            StressTestScenarioResult 全部具备 narrative_zh 买方研报卡片，
            且 to_dict() 方法能够完整序列化，文本中彻底去除下划线与代码变量暴露。

        二、正常函数业务边界与参数契约:
            - 标准四类计算输出对象全字段契约校验

        三、测试数据与模拟场景说明:
            分别实例化四类计算结果，调用 to_dict() 并断言字段与中文研报卡片。

        四、预期断言与结果验证:
            断言 to_dict() 字典包含 'narrative_zh' 且非空，
            卡片内容包含符合买方投资直觉的中文评述。
        """
        # 1. VaRResult
        rets = np.array([0.01, -0.015, 0.005, -0.02, 0.012, -0.008, 0.003, -0.011, 0.02, -0.005, 0.008, -0.012])
        var_res = PortfolioRiskAndVaREngine.compute_var_cvar(rets, portfolio_value=1_000_000.0)
        var_dict = var_res.to_dict()
        self.assertIn("narrative_zh", var_dict)
        self.assertIn("在险价值", var_dict["narrative_zh"])

        # 2. RiskDecompositionResult
        cov = np.eye(2) * 0.04
        w = np.array([0.5, 0.5])
        decomp_res = PortfolioRiskAndVaREngine.decompose_portfolio_risk(w, cov, ["A", "B"])
        decomp_dict = decomp_res.to_dict()
        self.assertIn("narrative_zh", decomp_dict)
        self.assertIn("分散化", decomp_dict["narrative_zh"])

        # 3. FactorAttributionResult
        y = np.array([0.01, 0.02, -0.01, 0.015, 0.005, -0.008, 0.012, -0.015, 0.02, -0.005])
        X = np.ones((10, 1)) * 0.01
        attr_res = PortfolioRiskAndVaREngine.run_fama_french_factor_attribution(y, X, ["MKT"])
        attr_dict = attr_res.to_dict()
        self.assertIn("narrative_zh", attr_dict)
        self.assertIn("Alpha", attr_dict["narrative_zh"])

        # 4. StressTestScenarioResult
        stress_results = PortfolioRiskAndVaREngine.run_macro_stress_test({"NVDA": 100_000.0}, {"NVDA": 1.5})
        stress_dict = stress_results[0].to_dict()
        self.assertIn("narrative_zh", stress_dict)
        self.assertIn("压力测试", stress_dict["narrative_zh"])

    def test_ut_portrisk_08_macro_stress_test_negative_beta_friction_drag(self):
        """【UT-PORTRISK-08: 负贝塔反向对冲标的极端行情下波动率凸性摩擦成本扣减检验】

        一、测试功能与测试点:
            验证负贝塔做空标的在宏观极端下行冲击时，二阶波动率损耗与流动性摩擦 (convexity_drag)
            必须正确扣减收益，杜绝因负贝塔导致减去负数反而使得做空收益虚假放大的物理违背。

        二、正常函数业务边界与参数契约:
            - 负贝塔做空资产 (Beta = -2.0)
            - 宏观极端崩盘场景 (mkt_shock = -0.40)

        三、测试数据与模拟场景说明:
            测试本金 $1,000,000 的 2 倍做空 ETF (Beta = -2.0)。
            在市场下挫 -40% 时，其下行贝塔经走阔后为 -2.0 * (1 + 0.25 * 0.40) = -2.20。
            一阶理论涨幅为 (-0.40) * (-2.20) = +0.88 (+88%)。
            若扣减流动性摩擦凸性损耗 0.20 * |-2.0| * (0.40^2) = 0.064 (-6.4%)，
            净涨幅应为 88% - 6.4% = 81.6%，而不是减去负数变成 94.4%。

        四、预期断言与结果验证:
            断言组合收益率 estimated_portfolio_drawdown_pct 落在 [75%, 85%] 的严谨物理区间内，
            绝不超过未计入摩擦的一阶上限 88.0%。
        """
        positions = {"BEAR_2X": 1_000_000.0}
        betas = {"BEAR_2X": -2.0}
        custom_scenarios = [
            {
                "name": "Severe_Crash_Scenario",
                "desc": "极端崩盘 -40%",
                "market_shock": -0.40,
            }
        ]

        results = PortfolioRiskAndVaREngine.run_macro_stress_test(
            portfolio_positions=positions,
            asset_betas=betas,
            custom_scenarios=custom_scenarios,
        )

        res = results[0]
        # 实际收益率为正
        gain_pct = res.estimated_portfolio_drawdown_pct
        self.assertGreater(gain_pct, 75.0)
        # 凸性摩擦损耗必须使实际净收益低于未扣减摩擦的一阶理论收益 (88.0%)
        self.assertLess(gain_pct, 88.0)

    def test_ut_portrisk_09_stress_test_scenario_chinese_naming_and_clean_narrative(self):
        """【UT-PORTRISK-09: 宏观极端压力测试情景自然中文语义与全息研报卡片去符号化断言】

        一、测试功能与测试点:
            1. 验证 DEFAULT_MACRO_STRESS_SCENARIOS 中预设的历史危机情景均包含通俗中文名称 name_zh；
            2. 验证 run_macro_stress_test 输出的 StressTestScenarioResult 中包含 scenario_name_zh；
            3. 验证 narrative_zh 买方研报卡片标题彻底消除下划线英文代码暴露 (如 '2008_GFC_Lehman_Crisis')，
               转为干净通俗的自然中文名称 (如 '2008年次贷危机与雷曼破产挤兑')；
            4. 验证 to_dict() 契约完整输出 scenario_name_zh。

        二、正常函数业务边界与参数契约:
            - portfolio_positions 与 asset_betas 为合法正市值组合
            - run_macro_stress_test 默认情景列表执行

        三、测试数据与模拟场景说明:
            测试标准持仓 NVDA 与 KO。

        四、预期断言与结果验证:
            断言每个返回的 StressTestScenarioResult 的 scenario_name_zh 非空；
            断言 2008 年情景的研报卡片标题包含“【宏观历史极端压力测试研报: 2008年次贷危机与雷曼破产挤兑】”；
            断言研报卡片标题严禁出现 "2008_GFC_Lehman_Crisis"。
        """
        positions = {"NVDA": 500_000.0, "KO": 500_000.0}
        betas = {"NVDA": 1.5, "KO": 0.6}

        results = PortfolioRiskAndVaREngine.run_macro_stress_test(positions, betas)
        self.assertEqual(len(results), 4)

        lehman_res = next(r for r in results if "2008" in r.scenario_name)
        self.assertIn("2008年次贷危机与雷曼破产挤兑", lehman_res.scenario_name_zh)
        self.assertIn("【宏观历史极端压力测试研报: 2008年次贷危机与雷曼破产挤兑】", lehman_res.narrative_zh)
        self.assertNotIn("2008_GFC_Lehman_Crisis】", lehman_res.narrative_zh)

        d = lehman_res.to_dict()
        self.assertIn("scenario_name_zh", d)
        self.assertEqual(d["scenario_name_zh"], "2008年次贷危机与雷曼破产挤兑")
        self.assertIn("narrative_zh", d)


if __name__ == "__main__":
    unittest.main()
