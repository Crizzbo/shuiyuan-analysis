"""单元测试: 负向测试与财务困境/僵尸企业/破产压力测试 (Negative Distress & Zombie Valuation Tests).

验证数学估值引擎在面对自由现金流失血、利息无法覆盖、负资产净值及巨额债务墙时的防御边界:
1. 股东有限责任与清算残值防御 (Merton 1974: E >= 0)
2. 运营折现负值黑洞与股权下界解耦
3. 达摩达兰资本侵蚀防御与负向隐含 ROIC 诊断
4. 现金跑道与流动性枯竭预警 (Cash Runway < 12m)
5. 僵尸企业 (Zombie Firm: ICR < 1.0) 与高危债务墙识别
6. 机构研判排斥陷阱 (严禁发出伪买入或普通减持，强制剔除/回避)
"""
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.firm_value_added_bridge_engine import (
    FirmFinancialFact,
    FirmValueAddedBridgeEngine,
)


class TestNegativeDistressValuation(unittest.TestCase):
    """负向测试与财务困境压力测试套件."""

    def setUp(self):
        self.bridge_engine = FirmValueAddedBridgeEngine()

    def test_limited_liability_and_liquidation_floor_for_bleeding_firm(self):
        """【UT-DISTRESS-01: 现金流严重失血企业的股东有限责任下界与清算残值防御】

        1. 测试功能与测试点:
           - 验证当微观企业自由现金流发生数十亿美元级严重亏损（失血）时，折现引擎的核心防御：
             A) 原始运营折现 (raw_operational_dcf) 如实呈现负值黑洞 (< 0.0)；
             B) 依据 Merton (1974) 股东有限责任与清算残值底线，最终每股内在价值与底价绝不能跌破 0.0 (Fair Value >= 0)；
             C) 达摩达兰资本内生增长检验判定为“资本持续侵蚀”且在经济上不可持续；
             D) 顶层研判必须发出“高危财务预警”，严禁产生虚假买入信号。

        2. 正常函数业务边界与参数契约:
           - annual_fcf_million < 0.0。
           - 估值引擎必须将经营资产价值截断为 0.0，同时考虑有形资产清算残值。

        3. 测试数据与模拟场景说明:
           - 模拟英特尔 (INTC) 代工业务巨亏转型期底账: 营收 54,000M, 资本开支 22,000M, 全年自由现金流 -12,500M (失血 125 亿美元)；总债务 52,000M，现金 24,000M，利息支出 1,800M。

        4. 预期断言与结果验证:
           - 断言 raw_operational_dcf_billion < 0.0。
           - 断言 fair_intrinsic_value_billion 与 pessimistic_floor_value_billion 均 >= 0.0。
           - 断言 is_economically_feasible 为 False，capital_status 包含“资本持续侵蚀”。
           - 断言 institutional_verdict 包含“高危财务预警”，recommended_action 包含“严禁买入”。
        """
        # 模拟英特尔 (INTC): 代工巨亏，FCF = -$12.5B
        intc = FirmFinancialFact(
            ticker="INTC",
            company_name="Intel Corporation",
            market="US",
            sector_id="TECH_SEMI",
            revenue_million=54000.0,
            cogs_million=32000.0,
            operating_expenses_million=12500.0,
            ebitda_million=9500.0,
            wages_and_salaries_million=13000.0,
            taxes_paid_million=500.0,
            capex_million=22000.0,
            annual_fcf_million=-12500.0,  # 严重负现金流
            market_cap_billion=105.0,
            total_debt_million=52000.0,
            cash_and_equivalents_million=24000.0,
            interest_expense_million=1800.0,
            tangible_book_value_million=65000.0,
        )

        val = self.bridge_engine.compute_firm_intrinsic_valuation(intc, sector_wacc=0.080, terminal_growth_rate=0.025)

        # 1. 原始运营折现揭示现金失血黑洞 (必须为负)
        self.assertLess(val["raw_operational_dcf_billion"], 0.0)
        self.assertLess(val["two_stage_valuation"]["raw_two_stage_operational_dcf_billion"], 0.0)

        # 2. 股东有限责任防御: 最终公允内在价值与底价必须 >= 0
        self.assertGreaterEqual(val["fair_intrinsic_value_billion"], 0.0)
        self.assertGreaterEqual(val["pessimistic_floor_value_billion"], 0.0)
        self.assertGreaterEqual(val["two_stage_valuation"]["two_stage_fair_value_billion"], 0.0)

        # 3. 达摩达兰资本内生增长检验: 判定为资本侵蚀且不可行
        self.assertFalse(val["endogenous_capital_consistency"]["is_economically_feasible"])
        self.assertIn("资本持续侵蚀", val["endogenous_capital_consistency"]["capital_status"])

        # 4. 机构研判防范: 必须提示失血风险，严禁提示低估买入
        self.assertIn("高危财务预警", val["institutional_verdict"])
        self.assertIn("严禁买入", val["recommended_action"])

    def test_insolvency_crisis_and_cash_runway_alert(self):
        """【UT-DISTRESS-02: 极度失血与现金耗尽企业的破产跑道预警与强制回避】

        1. 测试功能与测试点:
           - 验证濒临破产企业的现金消耗跑道 (Cash Burn Runway):
             Runway = (Cash & Equivalents) / |Annual FCF| * 12 个月。
           - 当跑道低于 12 个月（特别是极危的 < 4 个月）时，系统刚性触发破产倒计时告警。
           - 判定为“极度破产重组风险”，推荐动作强制标记为“强制回避 / 剔除出投资池”。

        2. 正常函数业务边界与参数契约:
           - cash_and_equivalents_million / |annual_fcf_million| * 12。
           - 跑道时间必须精确计算为有限月数，严禁返回 999 哨兵值。

        3. 测试数据与模拟场景说明:
           - 模拟普拉格能源 (PLUG) 破产危机状态: 营收 700M，成本高达 1180M (毛利润亏损)，EBITDA 负 850M；年失血 11 亿美元，账面仅剩 3 亿美元现金 (跑道仅 300 / 1100 * 12 = 3.27 个月)。

        4. 预期断言与结果验证:
           - 断言 cash_burn_runway_months 非空且 < 4.0 个月。
           - 断言 is_zombie_firm 为 True。
           - 断言 institutional_verdict 包含“极度破产重组风险”。
           - 断言 recommended_action 包含“强制回避 / 剔除出投资池”。
        """
        # 模拟普拉格能源 (PLUG): 毛利为负，现金跑道不足 4 个月
        plug = FirmFinancialFact(
            ticker="PLUG",
            company_name="Plug Power Inc.",
            market="US",
            sector_id="IND_MACH",
            revenue_million=700.0,
            cogs_million=1180.0,  # 毛亏损
            operating_expenses_million=370.0,
            ebitda_million=-850.0,  # EBITDA 严重为负
            wages_and_salaries_million=220.0,
            taxes_paid_million=10.0,
            capex_million=250.0,
            annual_fcf_million=-1100.0,  # 年失血 11 亿美元
            market_cap_billion=1.8,
            total_debt_million=950.0,
            cash_and_equivalents_million=300.0,  # 仅剩 3 亿美元现金
            interest_expense_million=70.0,
            tangible_book_value_million=500.0,
        )

        val = self.bridge_engine.compute_firm_intrinsic_valuation(plug, sector_wacc=0.095, terminal_growth_rate=0.020)
        diag = val["financial_distress_diagnostics"]

        # 1. 现金失血跑道低于 4 个月 (300 / 1100 * 12 = 3.3 个月)
        self.assertIsNotNone(diag["cash_burn_runway_months"])
        self.assertLess(diag["cash_burn_runway_months"], 4.0)

        # 2. 僵尸企业标志触发
        self.assertTrue(diag["is_zombie_firm"])

        # 3. 破产重组极危警报
        self.assertIn("极度破产重组风险", val["institutional_verdict"])
        self.assertIn("强制回避 / 剔除出投资池", val["recommended_action"])

    def test_zombie_debt_wall_and_icr_collapse(self):
        """【UT-DISTRESS-03: 僵尸企业利息保障倍数崩溃与巨额债务墙识别】

        1. 测试功能与测试点:
           - 验证 BIS 国际清算银行标准“僵尸企业 (Zombie Firm)”的识别规则:
             EBITDA < 利息支出 (即利息保障倍数 ICR < 1.0)。
           - 当利息都无法通过核心主营业务覆盖时，即便企业规模庞大，系统也必须将其定性为僵尸企业危机。

        2. 正常函数业务边界与参数契约:
           - interest_coverage_ratio = EBITDA / Interest Expense。
           - 若 ICR < 1.0，is_zombie_firm 必须置为 True。

        3. 测试数据与模拟场景说明:
           - 模拟日本乐天集团 (Rakuten 4755.T) 移动通信基建巨债危机:
             EBITDA 为 1,100 亿日元，但年利息支出高达 1,350 亿日元 (ICR = 0.81 < 1.0)；总债务高达 22,000 亿日元。

        4. 预期断言与结果验证:
           - 断言 interest_coverage_ratio < 1.0。
           - 断言 is_zombie_firm 为 True。
           - 断言 institutional_verdict 包含“僵尸企业债务危机”。
           - 断言 recommended_action 包含“强制剔除”。
        """
        rakuten = FirmFinancialFact(
            ticker="4755.T",
            company_name="Rakuten Group Inc.",
            market="JP",
            sector_id="COMM_SERV",
            revenue_million=14000.0,
            cogs_million=9000.0,
            operating_expenses_million=3900.0,
            ebitda_million=1100.0,
            wages_and_salaries_million=2100.0,
            taxes_paid_million=120.0,
            capex_million=2400.0,
            annual_fcf_million=-1300.0,
            market_cap_billion=12.0,
            total_debt_million=22000.0,  # 巨额负债
            cash_and_equivalents_million=4500.0,
            interest_expense_million=1350.0,  # 利息 13.5 亿 > EBITDA 11 亿
            tangible_book_value_million=3000.0,
        )

        val = self.bridge_engine.compute_firm_intrinsic_valuation(rakuten, sector_wacc=0.075, terminal_growth_rate=0.015)
        diag = val["financial_distress_diagnostics"]

        # 1. 利息保障倍数 ICR < 1.0
        self.assertLess(diag["interest_coverage_ratio"], 1.0)
        self.assertTrue(diag["is_zombie_firm"])

        # 2. 判定为僵尸企业危机
        self.assertIn("僵尸企业债务危机", val["institutional_verdict"])
        self.assertIn("强制剔除", val["recommended_action"])

    def test_value_trap_discrimination(self):
        """【UT-DISTRESS-04: 微薄正现金流但资不抵债企业的价值陷阱鉴别】

        1. 测试功能与测试点:
           - 验证“价值陷阱 (Value Trap)”防伪鉴别算法:
             传统筛选器常因企业具有微弱的正自由现金流 (FCF > 0) 或低市盈率而误判为便宜货；
             法证引擎结合“债务/EBITDA > 10x”与“有形账面净资产 (Tangible Book Value) 为负”双重穿透，精准排查价值陷阱。

        2. 正常函数业务边界与参数契约:
           - debt_to_ebitda_ratio = Total Debt / EBITDA。
           - 当 Debt/EBITDA > 10.0 且 Tangible Book Value < 0 时，is_value_trap 必为 True。

        3. 测试数据与模拟场景说明:
           - 模拟沃博联 (WBA 零售药房巨头): 自由现金流微正 450M，看似能自给自足；但总负债高达 33,500M，EBITDA 仅 3,200M (债务杠杆倍数达 10.47x)，有形净资产为深负 -9,800M。

        4. 预期断言与结果验证:
           - 断言 is_value_trap 为 True。
           - 断言 debt_to_ebitda_ratio > 10.0。
           - 断言 institutional_verdict 包含“价值陷阱警报”。
           - 断言 recommended_action 包含“规避债务悬崖”。
        """
        wba = FirmFinancialFact(
            ticker="WBA",
            company_name="Walgreens Boots Alliance",
            market="US",
            sector_id="HEALTH_BIO",
            revenue_million=144500.0,
            cogs_million=116000.0,
            operating_expenses_million=25300.0,
            ebitda_million=3200.0,
            wages_and_salaries_million=18500.0,
            taxes_paid_million=350.0,
            capex_million=1900.0,
            annual_fcf_million=450.0,
            market_cap_billion=8.2,
            total_debt_million=33500.0,
            cash_and_equivalents_million=720.0,
            interest_expense_million=2650.0,
            tangible_book_value_million=-9800.0,
        )

        val = self.bridge_engine.compute_firm_intrinsic_valuation(wba, sector_wacc=0.080, terminal_growth_rate=0.025)
        diag = val["financial_distress_diagnostics"]

        # 1. 触发价值陷阱判定
        self.assertTrue(diag["is_value_trap"])
        self.assertGreater(diag["debt_to_ebitda_ratio"], 10.0)

        # 2. 严禁误判为低估买入，必须警示价值陷阱
        self.assertIn("价值陷阱警报", val["institutional_verdict"])
        self.assertIn("规避债务悬崖", val["recommended_action"])

    def test_positive_control_remains_intact(self):
        """【UT-DISTRESS-05: 高质量正向控制组企业的健康指标与投资评级基线保持】

        1. 测试功能与测试点:
           - 验证负向压力测试防御机制不误伤健康标的（正向对照组基线测试）。
           - 确保高盈利、高资本回报率 (ROIC) 与充裕净现金企业依然保持优异评价。

        2. 正常函数业务边界与参数契约:
           - 健康企业必须满足: is_zombie_firm == False, cash_burn_runway_months is None, ICR >> 10.0。

        3. 测试数据与模拟场景说明:
           - 标的: 英伟达 (NVDA) 真实底账: 营收 120,000M, EBITDA 75,000M, FCF 65,000M, 现金 35,000M, 利息 300M (ICR = 250x)。

        4. 预期断言与结果验证:
           - 断言 is_zombie_firm 为 False。
           - 断言 cash_burn_runway_months 为 None (正向造血可持续)。
           - 断言 interest_coverage_ratio > 100.0。
           - 断言 is_economically_feasible 为 True。
           - 断言内在公允价值 fair_intrinsic_value_billion > 1000.0B 美元。
        """
        nvda = FirmFinancialFact(
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
            interest_expense_million=300.0,
            tangible_book_value_million=45000.0,
        )

        val = self.bridge_engine.compute_firm_intrinsic_valuation(nvda, sector_wacc=0.082, terminal_growth_rate=0.040)
        diag = val["financial_distress_diagnostics"]

        # 正向指标全面优异
        self.assertFalse(diag["is_zombie_firm"])
        self.assertIsNone(diag["cash_burn_runway_months"])
        self.assertGreater(diag["interest_coverage_ratio"], 100.0)
        self.assertTrue(val["endogenous_capital_consistency"]["is_economically_feasible"])
        self.assertGreater(val["fair_intrinsic_value_billion"], 1000.0)


if __name__ == "__main__":
    unittest.main()
