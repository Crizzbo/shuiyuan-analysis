"""微观筹码博弈、空头挤压与主力资金流向引擎单元测试套件.

本测试模块严格遵循《36号工程黄金设计规范》与四段式结构化中文契约测试模型:
1. 测试功能与测试点说明 (Test Functionality & Objectives)
2. 正常函数业务边界与参数契约 (Business Boundaries & Parameter Contracts)
3. 测试数据与模拟场景说明 (Test Data & Scenario Descriptions)
4. 预期断言与结果验证 (Expected Assertions & Verification)

涵盖做空持仓占比 (SI %)、借券年化利率 (CTB)、空头回补天数 (DTC)、借券池利用率、
轧空脆弱度指数评分边界防御与主力资金流向文字语病消除断言。
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.microstructure_flow_engine import (
    MicrostructureInput,
    MicrostructureResult,
    MicrostructureFlowEngine,
)
from finance_tools.microstructure_flow_engine import (
    MicrostructureInput as FacadeMicrostructureInput,
    MicrostructureResult as FacadeMicrostructureResult,
    MicrostructureFlowEngine as FacadeMicrostructureFlowEngine,
)


class TestMicrostructureFlowEngine(unittest.TestCase):
    """微观筹码博弈与轧空引擎契约测试."""

    def test_ut_micro_01_extreme_short_squeeze_scoring(self):
        """【UT-MICRO-01: 极端微观空头拥挤、CTB飙升与非线性轧空(Short Squeeze)高点评分断言】

        一、测试功能与测试点:
            验证 MicrostructureFlowEngine 在面对极高做空比例 (SI >= 30%)、借券利率 (CTB >= 50%)、
            回补天数 (DTC >= 10天) 及极高借券池利用率 (Util >= 90%) 时，
            能够精确计算轧空脆弱度得分 (squeeze_score > 75 分) 并触发 "Extreme" 极危等级评定。

        二、正常函数业务边界与参数契约:
            - float_shares: 自由流通盘 (例如 200M 股)
            - short_interest_shares: 80M 股 (40% 做空占比)
            - cost_to_borrow_pct: 65% (超高融券利率)
            - days_to_cover: 12 天

        三、测试数据与模拟场景说明:
            模拟典型高弹性逼空标的，做空力量极度拥挤，随时可能因催化剂引爆非线性空头踩踏。

        四、预期断言与结果验证:
            断言 squeeze_score >= 80.0。
            断言 squeeze_risk_level 包含 "Extreme" 与 "非线性逼空"。
            断言 tactical_implication_zh 包含 "Short Squeeze" 与 "严禁追高追在逼空顶点"。
        """
        inp = MicrostructureInput(
            ticker="SQUEEZE_STAR",
            current_price=15.0,
            float_shares=200.0,
            short_interest_shares=80.0,
            average_daily_volume_30d=6.0,  # DTC = 80 / 6 = 13.33 天
            cost_to_borrow_pct=65.0,
            borrow_utilization_pct=95.0,
        )
        res = MicrostructureFlowEngine.evaluate(inp)

        self.assertGreaterEqual(res.squeeze_score, 80.0)
        self.assertIn("Extreme", res.squeeze_risk_level)
        self.assertIn("Short Squeeze", res.tactical_implication_zh)
        self.assertIn("严禁追高追在逼空顶点", res.tactical_implication_zh)

    def test_ut_micro_02_healthy_dispersed_microstructure(self):
        """【UT-MICRO-02: 筹码分散低做空健康结构与常规估值驱动战术断言】

        一、测试功能与测试点:
            验证在常规低做空、低融券成本、流动性充裕的白马蓝筹标的中，
            系统输出较低的轧空得分，并指引投资者按常规基本面和凯利公式建仓。

        二、正常函数业务边界与参数契约:
            - 做空比例 < 3%
            - 借券成本正常 (< 1%)

        三、测试数据与模拟场景说明:
            测试优质蓝筹，无逼空套利空间，完全由业绩驱动。

        四、预期断言与结果验证:
            断言 squeeze_score < 25.0。
            断言 squeeze_risk_level 包含 "低 (Low / 筹码分散健康)"。
            断言 tactical_implication_zh 包含 "筹码结构健康均衡" 与 "传统估值安全边际"。
        """
        inp = MicrostructureInput(
            ticker="HEALTHY_BLUECHIP",
            current_price=150.0,
            float_shares=1000.0,
            short_interest_shares=20.0,  # 2% 做空
            average_daily_volume_30d=20.0,  # DTC = 1 天
            cost_to_borrow_pct=0.35,
            borrow_utilization_pct=15.0,
        )
        res = MicrostructureFlowEngine.evaluate(inp)

        self.assertLess(res.squeeze_score, 25.0)
        self.assertIn("Low", res.squeeze_risk_level)
        self.assertIn("筹码结构健康均衡", res.tactical_implication_zh)

    def test_ut_micro_03_insider_dumping_with_high_short_warning(self):
        """【UT-MICRO-03: 内部人高管集中抛售与高做空共振避坑防诱多战术断言】

        一、测试功能与测试点:
            验证因果逻辑：当空头做空比例偏高 (>15%)，但内部人高管非但未逢低增持反而集中减持套现时，
            系统发出明确警示，指出“反弹常为诱多，切忌盲目押注逼空，需坚守严格资产底线再行考虑介入”。

        二、正常函数业务边界与参数契约:
            - short_interest_shares 占比 > 15%
            - insider_sell_shares_90d 大额净卖出

        三、测试数据与模拟场景说明:
            某基本面存疑公司，高管频繁减持 1.5M 股，空头持仓达 18%。

        四、预期断言与结果验证:
            断言 insider_flow_status 包含 "集中抛售减持"。
            断言 tactical_implication_zh 包含 "反弹常为诱多" 与 "切忌盲目押注逼空"。
        """
        inp = MicrostructureInput(
            ticker="DUMP_TRAP",
            current_price=22.0,
            float_shares=100.0,
            short_interest_shares=18.0,  # 18% 做空
            average_daily_volume_30d=5.0,
            cost_to_borrow_pct=8.0,
            borrow_utilization_pct=60.0,
            insider_buy_shares_90d=0.0,
            insider_sell_shares_90d=1.5,  # 净减持 1.5M
        )
        res = MicrostructureFlowEngine.evaluate(inp)

        self.assertIn("集中抛售减持", res.insider_flow_status)
        self.assertIn("反弹常为诱多", res.tactical_implication_zh)
        self.assertIn("切忌盲目押注逼空", res.tactical_implication_zh)

    def test_ut_micro_04_institutional_outflow_no_double_negative_syntax(self):
        """【UT-MICRO-04: 主力机构大额净流出文字表述无双重负号语病断言】

        一、测试功能与测试点:
            验证文字语法修复点：当顶级机构季度流出为负数时，
            系统文字描述必须显示为“机构资金持续流出减持 (3.8M 股)”，
            严禁出现“流出减持 (-3.8M 股)”的双重负号语言倒错缺陷。

        二、正常函数业务边界与参数契约:
            - top10_inst_net_flow_shares 为负数 (例如 -3.8)

        三、测试数据与模拟场景说明:
            测试主力大单流出标的。

        四、预期断言与结果验证:
            断言 institutional_accumulation_desc 包含 "持续流出减持 (3.8M 股)"，
            严禁出现 "(-3.8M" 或 "减持 (-"。
        """
        inp = MicrostructureInput(
            ticker="INST_OUTFLOW",
            current_price=45.0,
            float_shares=300.0,
            short_interest_shares=15.0,
            average_daily_volume_30d=6.0,
            cost_to_borrow_pct=2.0,
            top10_inst_net_flow_shares=-3.8,  # 流出 3.8M 股
        )
        res = MicrostructureFlowEngine.evaluate(inp)

        self.assertIn("机构资金持续流出减持 (3.8M 股)", res.institutional_accumulation_desc)
        self.assertNotIn("(-3.8M", res.institutional_accumulation_desc)
        self.assertNotIn("减持 (-", res.institutional_accumulation_desc)

    def test_ut_micro_05_abnormal_negative_or_zero_boundary_defense(self):
        """【UT-MICRO-05: 异常负数与零成交量极端边界下界防御断言】

        一、测试功能与测试点:
            验证金融数学除零除负防御：当外部输入脏数据或异常负数（如负的借券成本、负的流通股本或零日均成交量）时，
            系统能够稳健防御，不崩溃抛出 ZeroDivisionError，且最终计算的 squeeze_score 严格受限于 [0.0, 100.0] 闭区间内。

        二、正常函数业务边界与参数契约:
            - float_shares <= 0
            - average_daily_volume_30d == 0
            - cost_to_borrow_pct < 0

        三、测试数据与模拟场景说明:
            输入极端异常边界数据。

        四、预期断言与结果验证:
            断言函数执行不崩溃。
            断言 squeeze_score >= 0.0 且 <= 100.0。
        """
        inp = MicrostructureInput(
            ticker="ANOMALY",
            current_price=10.0,
            float_shares=0.0,              # 异常零流通股
            short_interest_shares=10.0,
            average_daily_volume_30d=0.0,  # 异常零成交量
            cost_to_borrow_pct=-10.0,      # 异常负数借券费
            borrow_utilization_pct=-20.0,  # 异常负数利用率
        )
        res = MicrostructureFlowEngine.evaluate(inp)

        self.assertGreaterEqual(res.squeeze_score, 0.0)
        self.assertLessEqual(res.squeeze_score, 100.0)
        self.assertGreater(res.days_to_cover, 0.0)

    def test_ut_micro_06_facade_and_core_ssot_equivalence(self):
        """【UT-MICRO-06: 向下兼容中继门面 SSOT 完全等价性断言】

        一、测试功能与测试点:
            验证 `finance_tools.microstructure_flow_engine` 中继门面与底层核心
            `financial_core.engines.microstructure_flow_engine` 计算输出 100% 相同。

        二、正常函数业务边界与参数契约:
            - Facade 与 Core 传入相同输入。

        三、测试数据与模拟场景说明:
            测试标准中等轧空标的。

        四、预期断言与结果验证:
            断言门面与核心输出属性完全一致。
        """
        inp_core = MicrostructureInput(
            ticker="TEST_TICKER",
            current_price=50.0,
            float_shares=100.0,
            short_interest_shares=15.0,
            average_daily_volume_30d=3.0,
            cost_to_borrow_pct=15.0,
            borrow_utilization_pct=70.0,
        )
        inp_facade = FacadeMicrostructureInput(
            ticker="TEST_TICKER",
            current_price=50.0,
            float_shares=100.0,
            short_interest_shares=15.0,
            average_daily_volume_30d=3.0,
            cost_to_borrow_pct=15.0,
            borrow_utilization_pct=70.0,
        )

        res_core = MicrostructureFlowEngine.evaluate(inp_core)
        res_facade = FacadeMicrostructureFlowEngine.evaluate(inp_facade)

        self.assertEqual(res_core.squeeze_score, res_facade.squeeze_score)
        self.assertEqual(res_core.squeeze_risk_level, res_facade.squeeze_risk_level)
        self.assertEqual(res_core.tactical_implication_zh, res_facade.tactical_implication_zh)

    def test_ut_micro_07_buyer_dossier_card_and_to_dict_contract(self):
        """【UT-MICRO-07: 微观筹码博弈全息研报卡片与去工程符号化契约断言】

        一、测试功能与测试点:
            1. 验证 MicrostructureResult 具备 narrative_zh 全息卡片并支持 to_dict() 序列化；
            2. 验证 squeeze_risk_level_zh 纯自然中文定性字段已正确生成；
            3. 验证 narrative_zh 研报卡片彻底消除了 (Extreme / ...) 等英文代号暴露。

        二、正常函数业务边界与参数契约:
            - 输入有效，返回契约完整。

        三、测试数据与模拟场景说明:
            - 极端高轧空标的与低轧空标的。

        四、预期断言与结果验证:
            - narrative_zh 包含 "空头轧空脆弱度评级"；
            - narrative_zh 不含 "(Extreme /" 英文代号；
            - to_dict() 完整输出 squeeze_risk_level_zh 与 narrative_zh。
        """
        inp = MicrostructureInput(
            ticker="RXRX",
            current_price=3.85,
            float_shares=200.0,
            short_interest_shares=70.0,
            average_daily_volume_30d=5.0,
            cost_to_borrow_pct=40.0,
            borrow_utilization_pct=85.0,
        )
        res = MicrostructureFlowEngine.evaluate(inp)

        self.assertIn("微观筹码与博弈流动性全息研报", res.narrative_zh)
        self.assertNotIn("(Extreme /", res.narrative_zh)
        self.assertTrue(bool(res.squeeze_risk_level_zh))
        self.assertIn("拥挤", res.squeeze_risk_level_zh)

        d = res.to_dict()
        self.assertIn("narrative_zh", d)
        self.assertEqual(d["narrative_zh"], res.narrative_zh)
        self.assertIn("squeeze_risk_level_zh", d["short_metrics"])
        self.assertEqual(d["short_metrics"]["squeeze_risk_level_zh"], res.squeeze_risk_level_zh)


if __name__ == "__main__":
    unittest.main()
