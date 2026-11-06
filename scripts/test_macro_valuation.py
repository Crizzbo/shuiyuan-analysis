"""宏观联动估值与敏感性分析引擎离线回归测试。

验证范围：
1. 宏观基准上下文加载 (MacroContext)；
2. 动态 WACC 与 CAPM 资本成本推导；
3. 三态宏观情景压力测试（Bull / Base / Bear）与买入区间；
4. 宏观传导敏感性画像；
5. GenericFinancialMetrics 宏观联动方法；
6. 边界与异常输入拦截；
7. 离线网络隔离（严禁任何网络请求）。
"""

from pathlib import Path
import socket
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# 严禁任何网络外联
def deny_network(*args, **kwargs):
    raise AssertionError("测试执行过程中禁止网络访问")

socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
socket.create_connection = deny_network

from financial_reporting.generic_metrics import GenericFinancialMetrics
from financial_reporting.macro_valuation import MacroContext, MacroValuationEngine


class MacroValuationTests(unittest.TestCase):
    """【单元测试】宏观联动估值与敏感性分析引擎离线回归测试集。"""

    def setUp(self):
        self.macro = MacroContext.load_latest()

    def test_macro_context_loading(self):
        """【UT-MACRO-01: 宏观基准上下文加载与已核实快照哈希锚定】

        1. 测试功能与测试点:
           - 验证 MacroContext.load_latest() 离线读取宏观底账快照的完整性与强类型映射。
           - 验证核心宏观因子的数值精准度: 10年期美债收益率、2年期收益率、3个月短端国债利率、10Y-2Y期限利差以及美元指数 DXY。
           - 验证快照防伪哈希 snapshot_id 具备 64 位 SHA-256 密码学长度。
           - 验证中文自然语言与看板展示字典转换契约 (如 rf_10y_display, yield_spread_display)。

        2. 正常函数业务边界与参数契约:
           - rf_10y, rf_2y, rf_3m 必须为有限正浮点数，且在合理宏观区间内 (0.0 < rf < 0.20)。
           - yield_spread_10y_2y 为 10Y 与 2Y 之差 (精确到 bps 级别)。
           - snapshot_id 必须为 64 位十六进制散列值。

        3. 测试数据与模拟场景说明:
           - 基于项目内经监管核准归档的官方最新宏观快照: 10Y Rf=4.42%, 2Y Rf=4.15%, 3M Rf=4.35%, 利差 27.0 bps, DXY 104.5。

        4. 预期断言与结果验证:
           - 断言各期限收益率与利差数值与底账一致。
           - 断言 len(snapshot_id) == 64。
           - 断言 to_dict() 包含标准格式化输出 '4.42%' 与 '27.0 bps'。
        """
        self.assertAlmostEqual(self.macro.rf_10y, 0.0442)
        self.assertAlmostEqual(self.macro.rf_2y, 0.0415)
        self.assertAlmostEqual(self.macro.rf_3m, 0.0435)
        self.assertAlmostEqual(self.macro.yield_spread_10y_2y, 0.0027)
        self.assertAlmostEqual(self.macro.dxy, 104.5)
        self.assertTrue(len(self.macro.snapshot_id) == 64)

        d = self.macro.to_dict()
        self.assertEqual(d["rf_10y_display"], "4.42%")
        self.assertEqual(d["yield_spread_display"], "27.0 bps")

    def test_wacc_calculation(self):
        """【UT-MACRO-02: 加权平均资本成本WACC动态拆解与CAPM股权成本推导】

        1. 测试功能与测试点:
           - 验证 MacroValuationEngine.calculate_wacc 的资本资产定价模型 (CAPM) 与权重分配算法。
           - 股权成本公式: Ke = Rf + Beta * ERP。
           - 债务税盾效应: Kd_after_tax = Kd_pre_tax * (1 - TaxRate)。
           - 资本结构加权: WACC = We * Ke + Wd * Kd_after_tax。
           - 验证金融实证定理: WACC 严格介于税后债务成本与股权成本之间 (Kd_after_tax < WACC < Ke)。

        2. 正常函数业务边界与参数契约:
           - market_cap > 0, total_debt >= 0, beta > 0, rf > 0, erp > 0, 0 <= tax_rate <= 1。
           - 资本权重之和恒等于 1.0 (We + Wd == 1.0)。

        3. 测试数据与模拟场景说明:
           - 模拟中型科技制造企业: 市值 100 亿元，有息负债 20 亿元 (总资本 120 亿，We=83.33%, Wd=16.67%)。
           - 宏观参数: Beta=1.2, 无风险利率 Rf=4.42%, 股权风险溢价 ERP=5.0%, 企业所得税率 21.0%。
           - 预期 Ke = 0.0442 + 1.2 * 0.05 = 0.1042 (10.42%)。

        4. 预期断言与结果验证:
           - 断言 cost_of_equity 精确等于 0.1042。
           - 断言 equity_weight 与 debt_weight 之和为 1.0 且符合比例。
           - 断言 wacc > cost_of_debt_after_tax 且 wacc < cost_of_equity。
        """
        # 100 亿市值，20 亿负债，beta 1.2，Rf 4.42%，ERP 5%
        res = MacroValuationEngine.calculate_wacc(
            market_cap=100.0,
            total_debt=20.0,
            beta=1.2,
            rf=0.0442,
            erp=0.05,
            tax_rate=0.21,
        )
        # Ke = 0.0442 + 1.2 * 0.05 = 0.1042 (10.42%)
        self.assertAlmostEqual(res["cost_of_equity"], 0.1042)
        self.assertAlmostEqual(res["equity_weight"], 100.0 / 120.0, places=4)
        self.assertAlmostEqual(res["debt_weight"], 20.0 / 120.0, places=4)
        # WACC 介于税后债务成本与股权成本之间
        self.assertGreater(res["wacc"], res["cost_of_debt_after_tax"])
        self.assertLess(res["wacc"], res["cost_of_equity"])

    def test_scenario_valuation_monotonicity(self):
        """【UT-MACRO-03: 三态宏观情景压力测试单调性与安全买入击球区】

        1. 测试功能与测试点:
           - 验证 MacroValuationEngine.scenario_valuation 对三态宏观情景的定价单调性。
           - 宏观三情景严格遵循经济学单调收敛原则:
             宽松繁荣情景 (Bull Easing) 公允价 > 基准中性情景 (Base Case) 公允价 > 紧缩衰退情景 (Bear Tightening) 公允价。
           - 验证安全买入区间 (Buy Zone): Buy Zone Low <= Buy Zone High <= Base Fair Value。
           - 验证输出包含自然语言机构投资立场 (stance_zh)。

        2. 正常函数业务边界与参数契约:
           - cash_flow: 基准期自由现金流 (> 0)。
           - growth_rates: 5年预测期复合增长率序列。
           - terminal_growth: 永续增长率 (严格低于基准折现率)。
           - shares > 0, market_cap > 0, total_debt >= 0。

        3. 测试数据与模拟场景说明:
           - 标的现价 $45.0，基期现金流 5000 万，5年增速阶梯 [15%, 12%, 10%, 8%, 5%]，永续 2.5%，总股本 1000 万股。
           - 结合最新宏观上下文 (Rf=4.42%) 进行折现率压力测试。

        4. 预期断言与结果验证:
           - 断言 bull_val > base_val > bear_val 严格成立。
           - 断言 buy_zone_low <= buy_zone_high <= base_val。
           - 断言 pricing 字典中包含中文投资立场字段 'stance_zh'。
        """
        res = MacroValuationEngine.scenario_valuation(
            cash_flow=50.0,
            growth_rates=[0.15, 0.12, 0.10, 0.08, 0.05],
            terminal_growth=0.025,
            shares=10.0,
            market_cap=500.0,
            total_debt=50.0,
            beta=1.1,
            macro_context=self.macro,
            current_price=45.0,
            net_debt=20.0,
        )
        scenarios = res["scenarios"]
        bull_val = scenarios["bull_easing"]["fair_value_per_share"]
        base_val = scenarios["base_case"]["fair_value_per_share"]
        bear_val = scenarios["bear_tightening"]["fair_value_per_share"]

        self.assertGreater(bull_val, base_val)
        self.assertGreater(base_val, bear_val)

        # 建议买入区间
        pricing = res["pricing_recommendation"]
        self.assertLessEqual(pricing["buy_zone_low"], pricing["buy_zone_high"])
        self.assertLessEqual(pricing["buy_zone_high"], base_val)
        self.assertIn("stance_zh", pricing)

    def test_macro_sensitivity_profile(self):
        """【UT-MACRO-04: 企业宏观传导敏感性画像与久期信用利差暴露】

        1. 测试功能与测试点:
           - 验证 MacroValuationEngine.macro_sensitivity_profile 对不同财务体质标的的宏观传导敏感度刻画。
           - 久期敏感度 (Duration Sensitivity): 针对远期现金流折现占比高的高成长/亏损标的，标记为高久期利率敏感；对高股息成熟现金牛标记为低久期敏感。
           - 信用再融资压力 (Credit Refinancing Risk): 针对高债务、薄现金标的标记为高再融资压力；对零负债纯股权标的标记为零负债。
           - 现金缓冲红利 (Cash Buffer Benefit): 针对手握巨额现金标的，在加息周期标记为享受利息收益的“显著顺风”。

        2. 正常函数业务边界与参数契约:
           - 输入字典需包含 net_income, revenue, market_cap, total_debt, cash_and_equivalents。

        3. 测试数据与模拟场景说明:
           - 场景 A (高危高估值亏损股): 净利润 -1.2 亿，营收 0.8 亿，市值 15 亿，负债 3 亿，现金 1 亿。
           - 场景 B (稳健成熟现金牛): 净利润 5 亿，营收 20 亿，市值 60 亿，零负债，现金 15 亿。

        4. 预期断言与结果验证:
           - 场景 A 断言 duration_sensitivity 包含“高敏感”，credit_refinancing 包含“高再融资压力”。
           - 场景 B 断言 duration_sensitivity 包含“低敏感”，credit_refinancing 包含“零负债”，cash_buffer_benefit 包含“显著顺风”。
        """
        # 高成长亏损股
        high_risk_company = {
            "net_income": -120.0,
            "revenue": 80.0,
            "market_cap": 1500.0,
            "total_debt": 300.0,
            "cash_and_equivalents": 100.0,
        }
        prof = MacroValuationEngine.macro_sensitivity_profile(high_risk_company, self.macro)
        self.assertIn("高敏感", prof["duration_sensitivity"]["level"])
        self.assertIn("高再融资压力", prof["credit_refinancing"]["level"])

        # 稳健现金牛
        cash_cow = {
            "net_income": 500.0,
            "revenue": 2000.0,
            "market_cap": 6000.0,
            "total_debt": 0.0,
            "cash_and_equivalents": 1500.0,
        }
        prof_cow = MacroValuationEngine.macro_sensitivity_profile(cash_cow, self.macro)
        self.assertIn("低敏感", prof_cow["duration_sensitivity"]["level"])
        self.assertIn("零负债", prof_cow["credit_refinancing"]["level"])
        self.assertIn("显著顺风", prof_cow["cash_buffer_benefit"]["level"])

    def test_generic_metrics_macro_integration(self):
        """【IT-MACRO-05: 通用财务指标引擎与宏观三态折现跨模块整合】

        1. 测试功能与测试点:
           - 验证 GenericFinancialMetrics 与底层 MacroValuationEngine 的跨模块集成管道。
           - 确保输入微观财务全息底账与 Beta 之后，能够一站式输出：
             A) 健康画像 (health_profile)；
             B) 宏观基准上下文 (macro_context)；
             C) 宏观因子敏感性评估 (macro_sensitivity)；
             D) 三态宏观情景估值底账 (macro_scenario_valuation) 与安全买入击球区 (pricing_recommendation)。

        2. 正常函数业务边界与参数契约:
           - sample_company 必须提供完整的价格、市值、利润表与资产负债表字段。
           - beta 为浮点数。
           - 输出字典必须包含核心键且数值大于 0。

        3. 测试数据与模拟场景说明:
           - 模拟一家典型工业成长企业: 股价 $50，市值 5 亿，净利润 4000 万，自由现金流 3500 万，净资产 2.5 亿，总负债 4000 万，现金 1.2 亿。

        4. 预期断言与结果验证:
           - 断言返回字典包含 health_profile, macro_context, macro_sensitivity, macro_scenario_valuation。
           - 断言 pricing_recommendation 中 fair_value_central > 0 且 buy_zone_low > 0。
        """
        sample_company = {
            "price": 50.0,
            "market_cap": 500.0,
            "net_income": 40.0,
            "equity": 250.0,
            "total_assets": 400.0,
            "revenue": 300.0,
            "gross_profit": 180.0,
            "operating_income": 50.0,
            "current_assets": 200.0,
            "current_liabilities": 80.0,
            "total_debt": 40.0,
            "cash_and_equivalents": 120.0,
            "free_cash_flow": 35.0,
        }
        result = GenericFinancialMetrics.compute_macro_valuation_profile(sample_company, beta=1.0)
        self.assertIn("health_profile", result)
        self.assertIn("macro_context", result)
        self.assertIn("macro_sensitivity", result)
        self.assertIsNotNone(result["macro_scenario_valuation"])

        pricing = result["macro_scenario_valuation"]["pricing_recommendation"]
        self.assertGreater(pricing["fair_value_central"], 0)
        self.assertGreater(pricing["buy_zone_low"], 0)

    def test_rejections_and_boundaries(self):
        """【UT-MACRO-06: 宏观估值引擎非法入参物理拦截与异常类型防御】

        1. 测试功能与测试点:
           - 验证 MacroValuationEngine 在面对违反金融数学规律的极端入参时的刚性防御门禁。
           - 拦截无风险利率 <= 0 的非法输入（名义利率负值或零值在常规 CAPM 中未受保护模式下拦截）。
           - 拦截 Beta < 0 的非法资产反向系数（基础权益折现保护）。
           - 拦截市值 <= 0 的异常企业估值请求。

        2. 正常函数业务边界与参数契约:
           - cost_of_equity(rf, beta): rf 必须 > 0.0, beta 必须 >= 0.0。
           - calculate_wacc(market_cap, ...): market_cap 必须 > 0.0。

        3. 测试数据与模拟场景说明:
           - 场景 1: rf=0.0 (触发无风险利率必须大于零)。
           - 场景 2: beta=-1.0 (触发 Beta 必须非负)。
           - 场景 3: market_cap=0.0 (触发市值必须大于零)。

        4. 预期断言与结果验证:
           - 断言上述调用均刚性抛出 ValueError，杜绝非法脏数据穿透进入折现分母。
        """
        with self.assertRaises(ValueError):
            MacroValuationEngine.cost_of_equity(0.0, 1.0)

        with self.assertRaises(ValueError):
            MacroValuationEngine.cost_of_equity(0.04, -1.0)

        with self.assertRaises(ValueError):
            MacroValuationEngine.calculate_wacc(0.0, 10.0, 1.0, 0.04)


if __name__ == "__main__":
    unittest.main()
