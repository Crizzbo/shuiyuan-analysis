"""信用风险、违约距离 (DD) 与破产预警引擎单元测试套件.

本测试模块严格遵循《36号工程黄金设计规范》与四段式结构化中文契约测试模型:
1. 测试功能与测试点说明 (Test Functionality & Objectives)
2. 正常函数业务边界与参数契约 (Business Boundaries & Parameter Contracts)
3. 测试数据与模拟场景说明 (Test Data & Scenario Descriptions)
4. 预期断言与结果验证 (Expected Assertions & Verification)

涵盖 Merton (1974) 结构化信用违约模型、Altman Z-Score 破产预警、可转债严格实值转股判定及去工程符号化自然商业研报验证。
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.credit_risk_engine import (
    MertonCreditInput,
    CreditRiskResult,
    CreditRiskAndSolvencyEngine,
)


class TestCreditRiskAndSolvencyEngine(unittest.TestCase):
    """信用风险与违约概率引擎契约与边界测试."""

    def setUp(self):
        self.engine = CreditRiskAndSolvencyEngine()

    def test_ut_credit_01_merton_model_solution(self):
        """【UT-CREDIT-01: Merton (1974) 结构化信用模型资产价值与违约距离 (DD) 联立迭代求解】

        一、测试功能与测试点:
            验证 Merton 结构化信用模型在给定股权市值、负债面值与股票波动率下，
            能否通过阻尼牛顿迭代准确求解未观测的总资产市值 V_A 与总资产波动率 sigma_A，
            并推导出物理测度违约距离 DD_P 与风险中性违约率 EDF_Q。

        二、正常函数业务边界与参数契约:
            - equity_market_cap: 股权市值 (例如 $1000M)
            - total_debt_face_value: 负债面值 (例如 $500M)
            - equity_volatility: 年化波动率 (例如 30%)
            - risk_free_rate: 无风险利率 (例如 4%)

        三、测试数据与模拟场景说明:
            测试一家财务稳健的中大型企业，资产负债率合理 (负债/市值 = 0.5)，
            无风险利率 4%，评估周期 1 年。

        四、预期断言与结果验证:
            断言解出的资产价值 V_A > equity_market_cap，
            资产波动率 0 < sigma_A < equity_volatility，
            违约距离 DD > 3.0，预期违约率 EDF < 0.01。
        """
        params = MertonCreditInput(
            equity_market_cap=1000.0,
            total_debt_face_value=500.0,
            equity_volatility=0.30,
            risk_free_rate=0.04,
            time_to_maturity_years=1.0,
        )

        va, sa, dd, edf = self.engine.solve_merton_model(params)

        self.assertGreater(va, 1000.0)
        self.assertLess(sa, 0.30)
        self.assertGreater(sa, 0.05)
        self.assertGreater(dd, 3.0)
        self.assertLess(edf, 0.01)

    def test_ut_credit_02_altman_z_score_manufacturing_and_service(self):
        """【UT-CREDIT-02: Altman Z-Score 5因子制造业与4因子服务业破产区间划分与参数边界】

        一、测试功能与测试点:
            验证 Altman 破产预警评分在经典制造业 (5 因子) 与非制造业/服务业 (4 因子) 下，
            能够准确识别企业财务状况并划分至 Safe (安全区)、Grey (灰色带) 与 Distress (高危破产区)。

        二、正常函数业务边界与参数契约:
            - 资产总额、营运资金、留存收益、EBIT、营收与负债均大于零
            - is_manufacturing 标识区分制造业与非制造业模型

        三、测试数据与模拟场景说明:
            场景 1: 优质白马制造业公司，盈利强劲、留存丰富 (预期 Safe)；
            场景 2: 严重亏损、资不抵债的高危重组企业 (预期 Distress)。

        四、预期断言与结果验证:
            场景 1 断言 Z-Score > 2.99，区间为 Safe；
            场景 2 断言 Z-Score < 1.81，区间为 Distress。
        """
        # 场景 1: 优质制造
        z_safe, zone_safe = self.engine.calculate_altman_z_score(
            working_capital=300.0,
            retained_earnings=400.0,
            ebit=200.0,
            equity_market_cap=1500.0,
            total_revenue=1200.0,
            total_assets=1000.0,
            total_liabilities=300.0,
            is_manufacturing=True,
        )
        self.assertGreater(z_safe, 2.99)
        self.assertEqual(zone_safe, "Safe")

        # 场景 2: 破产边缘
        z_distress, zone_distress = self.engine.calculate_altman_z_score(
            working_capital=-100.0,
            retained_earnings=-200.0,
            ebit=-50.0,
            equity_market_cap=80.0,
            total_revenue=200.0,
            total_assets=500.0,
            total_liabilities=450.0,
            is_manufacturing=True,
        )
        self.assertLess(z_distress, 1.81)
        self.assertEqual(zone_distress, "Distress")

    def test_ut_credit_03_convertible_bond_valuation_and_itm_logic(self):
        """【UT-CREDIT-03: 可转债纯债底价 (Bond Floor)、严格实值转股判定与稀释冲击分析】

        一、测试功能与测试点:
            验证可转债评估函数能否正确贴现纯债底价，并依据严格金融定义 ($S \ge CP$) 判定是否为实值转股，
            杜绝将浮亏虚值转股误判为实值的因果倒错，同时准确计算潜在股本稀释率。

        二、正常函数业务边界与参数契约:
            - stock_price: 标的现价
            - conversion_price: 转股价格
            - par_value: 债券面值

        三、测试数据与模拟场景说明:
            设定转股价 CP = $100.0，面值 Par = $100.0:
            情况 A (严格实值): 现价 $110.0 (> $100.0)；
            情况 B (虚值浮亏): 现价 $96.0 (< $100.0，原代码判定为 True 的缺陷点)；
            情况 C (深度虚值): 现价 $60.0。

        四、预期断言与结果验证:
            情况 A is_in_the_money_conversion 为 True，包含“【实值转股区间】”；
            情况 B is_in_the_money_conversion 严格为 False，包含“【平价博弈区间】”；
            情况 C 包含“【虚值纯债区间】”，且纯债底价直观支撑转债价值。
        """
        # 情况 A: 现价 110，转股价 100
        res_a = self.engine.evaluate_convertible_bond(
            stock_price=110.0,
            conversion_price=100.0,
            par_value=100.0,
            coupon_rate=0.02,
            maturity_years=3.0,
            credit_spread=0.03,
            risk_free_rate=0.04,
            shares_outstanding=50.0,
            total_cb_par_amount=100.0,
        )
        self.assertTrue(res_a["is_in_the_money_conversion"])
        self.assertIn("实值转股区间", res_a["conversion_status_zh"])
        self.assertGreater(res_a["straight_bond_floor"], 80.0)

        # 情况 B: 现价 96，转股价 100 (原代码误判为 True 的核心测试点)
        res_b = self.engine.evaluate_convertible_bond(
            stock_price=96.0,
            conversion_price=100.0,
            par_value=100.0,
            coupon_rate=0.02,
            maturity_years=3.0,
            credit_spread=0.03,
            risk_free_rate=0.04,
            shares_outstanding=50.0,
            total_cb_par_amount=100.0,
        )
        self.assertFalse(res_b["is_in_the_money_conversion"])
        self.assertIn("平价博弈区间", res_b["conversion_status_zh"])

        # 情况 C: 现价 60，转股价 100
        res_c = self.engine.evaluate_convertible_bond(
            stock_price=60.0,
            conversion_price=100.0,
            par_value=100.0,
            coupon_rate=0.02,
            maturity_years=3.0,
            credit_spread=0.03,
            risk_free_rate=0.04,
            shares_outstanding=50.0,
            total_cb_par_amount=100.0,
        )
        self.assertFalse(res_c["is_in_the_money_conversion"])
        self.assertIn("虚值纯债区间", res_c["conversion_status_zh"])

    def test_ut_credit_04_comprehensive_rating_and_alert_flag(self):
        """【UT-CREDIT-04: 端到端综合信用评级代理映射与高危破产警报判定】

        一、测试功能与测试点:
            验证结合 Merton 违约距离与 Altman 财务健康度后，能否准确输出买方评级代理 (AAA/AA 至 CCC/D)，
            并在出现高危财务恶化时果断触发信用警报 (credit_alert_flag=True)。

        二、正常函数业务边界与参数契约:
            - evaluate_comprehensive_credit 完整参数输入

        三、测试数据与模拟场景说明:
            测试濒临重组的危困企业: 极高负债、微薄现金、巨额亏损。

        四、预期断言与结果验证:
            断言评级映射为 CCC/D，credit_alert_flag 为 True。
        """
        res = self.engine.evaluate_comprehensive_credit(
            ticker="DISTRESS_CORP",
            equity_market_cap=50.0,
            total_debt=800.0,
            current_assets=100.0,
            current_liabilities=300.0,
            retained_earnings=-400.0,
            ebit=-80.0,
            revenue=200.0,
            total_assets=600.0,
            total_liabilities=800.0,
            equity_volatility=0.80,
            risk_free_rate=0.045,
        )

        self.assertIsInstance(res, CreditRiskResult)
        self.assertEqual(res.credit_rating_proxy, "CCC/D")
        self.assertTrue(res.credit_alert_flag)
        self.assertEqual(res.altman_zone, "Distress")

    def test_ut_credit_05_natural_language_summary_no_engineering_symbols(self):
        """【UT-CREDIT-05: 消除希腊字母与工程代号暴露、英文枚举本地化通俗商业语义断言】

        一、测试功能与测试点:
            验证生成的中文研报字符串严格遵循《自然语言汇报偏好》与《去工程符号化》规范，
            彻底剔除 "DD_P=...σ"、"EDF_Q=..." 等晦涩数学符号，将英文枚举 (Distress/Safe/Grey)
            全面本地化为通俗易懂的中文买方风控研判。

        二、正常函数业务边界与参数契约:
            - summary_zh 研报字段

        三、测试数据与模拟场景说明:
            测试正常稳健白马企业。

        四、预期断言与结果验证:
            断言 summary_zh 包含“物理违约安全垫”、“Altman 财务健康度”、“【财务稳健安全区】”，
            严禁出现 "DD_P="、"EDF_Q="、"σ" 或英文 "(Safe)"。
        """
        res = self.engine.evaluate_comprehensive_credit(
            ticker="SAFE_CORP",
            equity_market_cap=2000.0,
            total_debt=400.0,
            current_assets=800.0,
            current_liabilities=300.0,
            retained_earnings=600.0,
            ebit=350.0,
            revenue=1800.0,
            total_assets=2500.0,
            total_liabilities=400.0,
            equity_volatility=0.22,
            risk_free_rate=0.04,
        )

        self.assertNotIn("DD_P=", res.summary_zh)
        self.assertNotIn("EDF_Q=", res.summary_zh)
        self.assertNotIn("(Safe)", res.summary_zh)
        self.assertIn("物理违约安全垫", res.summary_zh)
        self.assertIn("财务健康度", res.summary_zh)
        self.assertIn("财务稳健安全区", res.summary_zh)

    def test_ut_credit_06_buyer_dossier_card_and_convertible_clause_contract(self):
        """【UT-CREDIT-06: 机构买方偿债能力全息研报卡片与可转债保护垫因果自洽断言】

        一、测试功能与测试点:
            1. 验证 `CreditRiskResult` 具备标准 `narrative_zh` 买方全息研报卡片与 `to_dict()` 序列化契约。
            2. 验证评级代理具备中文语义 `rating_proxy_zh`（如 "特级优质无违约风险"），利差以“基点”准确表达。
            3. 验证当传入可转债信息时，研报卡片中自洽载入“可转债保护垫: 纯债底价”与稀释股数推导，杜绝遗漏。

        二、正常函数业务边界与参数契约:
            - cb_info 传入转股价、面值与票息。

        三、测试数据与模拟场景说明:
            测试发行有可转债的优质企业，验证债底与潜在稀释是否完整融入卡片。

        四、预期断言与结果验证:
            断言 narrative_zh 包含“【SAFE_CORP 买方偿债能力与违约风险全息研报】”与“可转债保护垫”。
            断言 to_dict() 字段齐全无异常。
        """
        cb_dict = {
            "stock_price": 50.0,
            "conversion_price": 45.0,
            "par_value": 100.0,
            "coupon_rate": 0.015,
            "maturity_years": 2.0,
            "credit_spread": 0.015,
            "risk_free_rate": 0.04,
            "shares_outstanding": 100.0,
            "total_cb_par_amount": 200.0,
        }
        res = self.engine.evaluate_comprehensive_credit(
            ticker="SAFE_CORP",
            equity_market_cap=5000.0,
            total_debt=500.0,
            current_assets=1200.0,
            current_liabilities=400.0,
            retained_earnings=1000.0,
            ebit=600.0,
            revenue=3000.0,
            total_assets=4000.0,
            total_liabilities=800.0,
            equity_volatility=0.20,
            risk_free_rate=0.04,
            cb_info=cb_dict,
        )

        self.assertIn("买方偿债能力与违约风险全息研报", res.narrative_zh)
        self.assertEqual(res.rating_proxy_zh, "特级优质无违约风险")
        self.assertIn("基点", res.narrative_zh)
        self.assertIn("可转债保护垫", res.narrative_zh)
        self.assertIn("纯债底价", res.narrative_zh)

        d = res.to_dict()
        self.assertIn("narrative_zh", d)
        self.assertEqual(d["credit_rating_proxy_zh"], "特级优质无违约风险")
        self.assertEqual(d["altman_zone_zh"], "财务稳健安全区")


if __name__ == "__main__":
    unittest.main()
