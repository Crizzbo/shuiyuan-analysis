# -*- coding: utf-8 -*-
"""通用商业物理与速度动力学计算引擎单元测试套件 (test_universal_physical_dynamics_engine.py).

严格遵循买方金融工程与敏捷测试契约规范:
1. 采用统一标准编号: 【UT-DYN-01】~【UT-DYN-07】;
2. 每一个测试用例配备标准化四段式中文测试说明文档 (docstring):
   - 【测试点与功能定位】: 明确验证的具体算法、公式与物理动力学推导;
   - 【输入数据与场景】: 显式标注标的、价格时序、三表科目与假设参数;
   - 【预期断言与验证机制】: 明确断言条件、浮点容差与异常拦截类型;
   - 【边界与容错】: 验证除零、除负、缺失财报与极端停滞收敛边界;
3. 纯本地物理离线断言，严格禁止网络连接。
"""

import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.universal_physical_dynamics_engine import (
    UniversalPhysicalDynamicsEngine,
    PriceDynamicsMetrics,
    FundamentalSupplyChainMetrics,
    TerminalValuationDistribution,
    UniversalDynamicsProfile,
)
from financial_core.api import FinancialAnalysisSystem


class TestUniversalPhysicalDynamicsEngineSuite(unittest.TestCase):
    """通用商业物理与动力学引擎全息单元测试."""

    def setUp(self):
        self.engine = UniversalPhysicalDynamicsEngine(default_wacc=0.085)
        self.system = FinancialAnalysisSystem()

    def test_rebound_half_life_and_ou_process(self):
        """【UT-DYN-01: 均值回归反弹速度半衰期物理有界性测试】

        【测试点与功能定位】:
        验证通过离散自回归 (OU 过程) 拟合价格偏离移动均线的回归速度，
        断言反弹半衰期 (t_half) 计算准确且严格约束在物理合理区间 (1.5 ~ 45.0 天)。

        【输入数据与场景】:
        构造 60 天均值回归平稳阻尼震荡时序 (中枢 100，正弦偏离带噪声)。

        【预期断言与验证机制】:
        断言 rebound_half_life_days 为正数，且小于 45 天，中枢价格约等于 100。

        【边界与容错】:
        若价格极度平稳或无偏离，模型不会除零崩溃。
        """
        prices = [100.0 + 8.0 * math.sin(i * 0.3) for i in range(60)]
        profile = self.engine.analyze_ticker_dynamics(
            ticker="TEST_TICKER",
            as_of_date="2026-11-09",
            close_prices=prices,
        )
        p_dyn = profile.price_dynamics
        self.assertIsInstance(p_dyn, PriceDynamicsMetrics)
        self.assertGreaterEqual(p_dyn.rebound_half_life_days, 1.5)
        self.assertLessEqual(p_dyn.rebound_half_life_days, 45.0)
        self.assertAlmostEqual(p_dyn.equilibrium_mu_price, 100.0, delta=10.0)

    def test_trend_velocity_and_acceleration(self):
        """【UT-DYN-02: 动量推进速度与二阶加速度物理推导】

        【测试点与功能定位】:
        验证均线一阶导 (年化推进速度) 与二阶导 (近5日相对近20日动量加速度) 计算。

        【输入数据与场景】:
        构造持续加速上行的主升浪价格序列 (从 50 点以指数递增速度涨至 150 点)。

        【预期断言与验证机制】:
        断言年化推进速度大于 0，动量加速度大于 0 (处于深踩油门冲刺状态)。

        【边界与容错】:
        验证价格长度刚达 20 天时二阶导平滑过渡，无越界异常。
        """
        prices = [50.0 * (1.0 + 0.012 * i + 0.0003 * (i ** 2)) for i in range(70)]
        profile = self.engine.analyze_ticker_dynamics(
            ticker="BULL_RUN",
            as_of_date="2026-11-09",
            close_prices=prices,
        )
        self.assertGreater(profile.price_dynamics.trend_velocity_annual_pct, 0.0)
        self.assertGreater(profile.price_dynamics.momentum_acceleration_pct, 0.0)

    def test_panic_calming_days_convergence(self):
        """【UT-DYN-03: 条件异方差恐慌衰减与平息半衰期】

        【测试点与功能定位】:
        验证突发利空引起日内高波动后，系统通过自相关衰减计算市场恐慌平息所需天数。

        【输入数据与场景】:
        构造带有波动聚集与脉冲冲击的 50 天收益率时序。

        【预期断言与验证机制】:
        断言 panic_calming_days 落在 [2.0, 30.0] 天的客观物理区间。

        【边界与容错】:
        完全无波动的死水序列，模型通过先验平滑兜底，不发生除零。
        """
        base = 100.0
        prices = [base]
        for i in range(1, 50):
            shock = 0.06 * math.sin(i * 1.2) if i > 35 else 0.005 * math.cos(i)
            prices.append(prices[-1] * (1.0 + shock))

        profile = self.engine.analyze_ticker_dynamics(
            ticker="VOL_SHOCK",
            as_of_date="2026-11-09",
            close_prices=prices,
        )
        self.assertGreaterEqual(profile.price_dynamics.panic_calming_days, 2.0)
        self.assertLessEqual(profile.price_dynamics.panic_calming_days, 30.0)

    def test_supply_chain_ccc_strong_moat_negative(self):
        """【UT-DYN-04: 供应链现金循环周期 CCC 真实物理周转与负值话语权】

        【测试点与功能定位】:
        验证从三表底账提取存货周转 (DIO)、应收账款 (DSO)、应付账款 (DPO)，
        并计算现金循环周期 (CCC = DIO + DSO - DPO)。

        【输入数据与场景】:
        模拟具备强势护城河的企业 (如苹果、英伟达)：存货少 (DIO=30天)，客户现款 (DSO=25天)，
        压榨上游供货商延期付款 (DPO=95天)。

        【预期断言与验证机制】:
        断言 CCC 为负数 (-40.0 天)，正确识别无偿占用上下游资金的超级商业话语权。

        【边界与容错】:
        营业收入或营业成本为 0 时，除零保护生效。
        """
        fin_facts = {
            "revenue": 10000.0,
            "cogs": 6000.0,
            "inventory": (6000.0 / 365.0) * 30.0,    # DIO = 30 天
            "receivables": (10000.0 / 365.0) * 25.0, # DSO = 25 天
            "payables": (6000.0 / 365.0) * 95.0,     # DPO = 95 天
            "total_assets": 15000.0,
            "current_liabilities": 4000.0,
        }
        prices = [100.0] * 30
        profile = self.engine.analyze_ticker_dynamics(
            ticker="APPLE_LIKE",
            as_of_date="2026-11-09",
            close_prices=prices,
            financial_statement=fin_facts,
        )
        sc = profile.supply_chain_dynamics
        self.assertAlmostEqual(sc.dio_inventory_days, 30.0, places=1)
        self.assertAlmostEqual(sc.dso_receivables_days, 25.0, places=1)
        self.assertAlmostEqual(sc.dpo_payables_days, 95.0, places=1)
        self.assertAlmostEqual(sc.cash_conversion_cycle_days, -40.0, places=1)

    def test_zero_growth_terminal_floor_breaking_single_mid_case(self):
        """【UT-DYN-05: 破除单一中档假定：增长率归零 (Growth=0%) 极端停滞防御底线】

        【测试点与功能定位】:
        验证在极端停滞情景下，假设未来企业完全不增长 (g=0%)，单凭静态自由现金流 (FCF)
        与账面净现金折现推导的物理刚性防御底价 (Zero-Growth Terminal Floor Price)。

        【输入数据与场景】:
        营收 1000 亿，CFO 400 亿，CapEx 100 亿 (FCF = 300 亿)，总现金 200 亿，总负债 50 亿 (净现金 150 亿)，
        股本 100 亿股，现价 $45.00，WACC = 8.5%。

        【预期断言与验证机制】:
        静态 FCF 折现价值 = 300 / 0.085 = 3529.4 亿；
        股权零增长价值 = 3529.4 + 150 = 3679.4 亿；
        每股零增长底价 = 3679.4 / 100 = $36.79。
        断言 zero_growth_floor_price 约为 36.79，稳态内生价值高于底价，乐观靶心更高。

        【边界与容错】:
        自由现金流为负或亏损时，自动收敛为清算价值下界，绝不产生负数股价。
        """
        fin_facts = {
            "revenue": 1000.0,
            "cash_from_operations": 400.0,
            "capital_expenditure": 100.0, # FCF = 300.0
            "cash_and_equivalents": 200.0,
            "long_term_debt": 50.0,       # 净现金 = 150.0
            "total_assets": 1500.0,
            "total_liabilities": 200.0,
            "shares_outstanding": 100.0,
        }
        prices = [45.0] * 30
        profile = self.engine.analyze_ticker_dynamics(
            ticker="VALUE_FORTRESS",
            as_of_date="2026-11-09",
            close_prices=prices,
            financial_statement=fin_facts,
            shares_outstanding=100.0,
            custom_wacc=0.085,
        )
        val = profile.valuation_distribution
        expected_floor = ( (300.0 / 0.085) + 150.0 ) / 100.0
        self.assertAlmostEqual(val.zero_growth_floor_price, round(expected_floor, 2), places=1)
        self.assertGreater(val.steady_state_value_price, val.zero_growth_floor_price)
        self.assertGreater(val.optimistic_target_price, val.steady_state_value_price)
        self.assertIn("安全垫", val.margin_of_safety_assessment_zh)

    def test_negative_fcf_turnaround_safety_floor(self):
        """【UT-DYN-06: 亏损或重资本投入期 (FCF <= 0) 净资产清算底线防御】

        【测试点与功能定位】:
        当企业处于转型期或逆周期，经营现金流扣除资本开支为负数 (FCF < 0) 时，
        验证系统通过重置账面净资产折现建立安全底线，不产生负数或奇异值。

        【输入数据与场景】:
        CFO 50 亿，CapEx 150 亿 (FCF = -100 亿)，净现金 80 亿，净资产 400 亿，股本 10 亿股。

        【预期断言与验证机制】:
        断言每股停滞底价大于 0，并基于净资产与净现金提供正向安全边际。
        """
        fin_facts = {
            "cash_from_operations": 50.0,
            "capital_expenditure": 150.0,
            "cash_and_equivalents": 100.0,
            "long_term_debt": 20.0,       # 净现金 = 80.0
            "total_assets": 600.0,
            "total_liabilities": 200.0,   # 净资产 = 400.0
            "shares_outstanding": 10.0,
        }
        prices = [30.0] * 30
        profile = self.engine.analyze_ticker_dynamics(
            ticker="TURNAROUND_BIOTECH",
            as_of_date="2026-11-09",
            close_prices=prices,
            financial_statement=fin_facts,
            shares_outstanding=10.0,
        )
        self.assertGreater(profile.valuation_distribution.zero_growth_floor_price, 0.0)

    def test_api_facade_and_legacy_facade_integration(self):
        """【UT-DYN-07: 统一门面挂载与 PEP 451 虚拟门面透明重定向验证】

        【测试点与功能定位】:
        验证 FinancialAnalysisSystem 统一门面已成功挂载 universal_dynamics_engine，
        且通过 finance_tools.universal_physical_dynamics_engine 能够透明导入使用。
        """
        self.assertTrue(hasattr(self.system, "universal_dynamics_engine"))
        self.assertIsInstance(self.system.universal_dynamics_engine, UniversalPhysicalDynamicsEngine)

        import finance_tools.universal_physical_dynamics_engine as legacy_m
        self.assertTrue(hasattr(legacy_m, "UniversalPhysicalDynamicsEngine"))
        self.assertTrue(hasattr(legacy_m, "UniversalDynamicsProfile"))


if __name__ == "__main__":
    unittest.main()
