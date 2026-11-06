"""Phase 3C 金融工程引擎单元测试 (Mid-Cycle Normalization & Shiller CAPE Valuation).

验证目标：
1. 跨周期正常化自由现金流 (Normalized Mid-Cycle FCF) 资产周转与利润率中枢重构；
2. 席勒周期调整市盈率 (Shiller CAPE) 10 年期真实盈利中枢与折溢价走廊；
3. 四象限宏观与商业周期阶段智能识别分类 (谷底反转 / 中周期稳健 / 见顶过热 / 晚周期收缩)；
4. 周期型企业端到端内在公允价值锚定；
5. FinancialAnalysisSystem 统一门面 API 在 MID_CYCLE 与 FULL_SYSTEMIC 模式下的终极全息闭环。
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from financial_core.contracts import (
    AnalysisMode,
    FinancialAnalysisResult,
    DecisionCardData,
    MidCycleValuationResult,
    CyclePhaseResult,
)
from financial_core.engines.mid_cycle_engine import (
    MidCycleNormalizationEngine,
    MidCycleFCFResult,
    ShillerCAPEResult,
)
from financial_core.api import FinancialAnalysisSystem


class TestPhase3CEngines(unittest.TestCase):
    """Phase 3C 跨周期正常化估值与全流程闭环单测套件."""

    def setUp(self):
        self.api = FinancialAnalysisSystem()

    def test_mid_cycle_fcf_normalization(self):
        """【UT-PH3C-01: 跨周期正常化自由现金流(Mid-Cycle FCF)重构与资产周转利润率中枢守恒】

        1. 测试功能与测试点:
           - 验证 MidCycleNormalizationEngine.normalize_cycle_fcf 重构高波动强周期企业（存储芯片/海运等）跨周期现金流。
           - 7 年历史周期数据回溯，剔除峰谷失真，推导中枢营业利润率与中枢资产周转率。
           - 验证正常化自由现金流公式严格闭环平账：$Normalized\ FCF = Normalized\ NOPAT - Normalized\ Net\ Capex$。
           - 验证历年显式 D&A 序列输入时的精确守恒性。

        2. 正常函数业务边界与参数契约:
           - 历史序列长度至少 3 年，总资产为正。
           - 返回 MidCycleFCFResult 强类型结果。

        3. 测试数据与模拟场景说明:
           - 模拟 7 年起伏剧烈周期（营收 8000M~20000M，EBIT 200M~7200M，资本开支 600M~1800M）。

        4. 预期断言与结果验证:
           - history_years_count == 7。
           - median_operating_margin 介于 10%~30% 之间。
           - normalized_mid_cycle_fcf > 0。
           - 显式 D&A 场景满足 FCF == NOPAT - Net Capex 平账。
        """
        # 模拟 7 年高低起伏周期 (单位：百万美元)
        hist_rev = [8000.0, 11000.0, 16000.0, 20000.0, 13000.0, 9500.0, 12000.0]
        hist_ebit = [400.0, 1800.0, 4800.0, 7200.0, 1900.0, 200.0, 2100.0] # 利润剧烈波动
        hist_capex = [600.0, 800.0, 1400.0, 1800.0, 1000.0, 700.0, 900.0]
        current_assets = 18000.0

        fcf_res = MidCycleNormalizationEngine.normalize_cycle_fcf(
            history_revenues=hist_rev,
            history_operating_incomes=hist_ebit,
            history_capex=hist_capex,
            current_total_assets=current_assets,
            tax_rate=0.21,
        )

        self.assertIsInstance(fcf_res, MidCycleFCFResult)
        self.assertEqual(fcf_res.history_years_count, 7)
        # 营业利润率中枢应在合理正常区间 (约 15%~25%)
        self.assertTrue(0.10 <= fcf_res.median_operating_margin <= 0.30)
        # 正常化 FCF 必须为有效有限正数
        self.assertGreater(fcf_res.normalized_mid_cycle_fcf, 0.0)
        self.assertGreater(fcf_res.normalized_mid_cycle_revenue, 0.0)
        self.assertGreater(fcf_res.normalized_mid_cycle_dna, 0.0)
        self.assertGreaterEqual(fcf_res.normalized_net_capex, 0.0)

        # 测试提供显式历年 D&A 序列时的精确守恒
        hist_dna = [500.0, 700.0, 1100.0, 1500.0, 900.0, 600.0, 800.0]
        fcf_with_dna = MidCycleNormalizationEngine.normalize_cycle_fcf(
            history_revenues=hist_rev,
            history_operating_incomes=hist_ebit,
            history_capex=hist_capex,
            current_total_assets=current_assets,
            history_dna=hist_dna,
        )
        self.assertGreater(fcf_with_dna.normalized_mid_cycle_dna, 0.0)
        self.assertAlmostEqual(
            fcf_with_dna.normalized_mid_cycle_fcf,
            fcf_with_dna.normalized_mid_cycle_nopat - fcf_with_dna.normalized_net_capex,
            places=1,
        )

    def test_shiller_cape_computation(self):
        """【UT-PH3C-02: 席勒周期调整市盈率(Shiller CAPE)真实盈利中枢与折溢价分级走廊核验】

        1. 测试功能与测试点:
           - 验证 MidCycleNormalizationEngine.compute_shiller_cape 测算跨周期席勒真实净利润中枢与真实 EPS。
           - 股价 120 美元，股数 100M，历史 7 年净利润均值 800M，真实 EPS = 8.0 美元。
           - 验证周期调整市盈率 CAPE = 120 / 8.0 = 15.0x。
           - 相对 18.0x 历史基准折价 -16.7%，精准判定进入“折价”估值梯队。

        2. 正常函数业务边界与参数契约:
           - 当前股价与股数为正数，基准 CAPE 为正。
           - 返回 ShillerCAPEResult 强类型结果。

        3. 测试数据与模拟场景说明:
           - 7 年净利润 [200, 600, 1200, 1800, 900, 100, 800]，当前股价 120。

        4. 预期断言与结果验证:
           - shiller_real_eps_10y 贴近 8.0。
           - shiller_cape_ratio 贴近 15.0。
           - cape_premium_discount_pct < 0 且 cape_valuation_tier_zh 包含 "折价"。
        """
        price = 120.0
        shares = 100.0 # 市值 12,000M
        # 7 年净利润 (均值 800M，真实 EPS = 8.0)
        hist_net_income = [200.0, 600.0, 1200.0, 1800.0, 900.0, 100.0, 800.0]

        shiller = MidCycleNormalizationEngine.compute_shiller_cape(
            current_price=price,
            shares_outstanding=shares,
            history_net_incomes=hist_net_income,
            historical_benchmark_cape=18.0,
        )

        self.assertIsInstance(shiller, ShillerCAPEResult)
        # 真实 EPS 均值应为 8.0，对应 CAPE = 120 / 8.0 = 15.0x
        self.assertAlmostEqual(shiller.shiller_real_eps_10y, 8.0, delta=0.5)
        self.assertAlmostEqual(shiller.shiller_cape_ratio, 15.0, delta=1.0)
        # 15.0x 相对 18.0x 基准为折价，归入中周期合理或深度折价
        self.assertLess(shiller.cape_premium_discount_pct, 0.0)
        self.assertIn("折价", shiller.cape_valuation_tier_zh)

    def test_detect_cycle_phase_all_quadrants(self):
        """【UT-PH3C-03: 宏观与商业周期四象限(谷底复苏/见顶过热/晚周期收缩/中周期稳健)智能识别断言】

        1. 测试功能与测试点:
           - 验证 detect_cycle_phase 对行业四象限商业周期阶段的精准研判：
             1. 谷底复苏 (TROUGH_RECOVERY): 利润率处于历史 P10 极低位但营收增速转正，触发买方“左侧布局”研判；
             2. 见顶过热 (PEAK_OVERHEAT): 利润率触及历史 P90 极端峰值但增速放缓，提示“警惕假低 PE 周期见顶陷阱”；
             3. 晚周期收缩 (LATE_CYCLE_CONTRACTION): 营收大幅负增长且利润率显著被挤压，给出“清仓回避”警示；
             4. 中周期稳健扩张 (MID_CYCLE_EXPANSION): 处于中枢稳健走廊，判定为“主升浪重仓”。

        2. 正常函数业务边界与参数契约:
           - 接收当前利润率、历史利润率分布与营收增速，返回 CyclePhaseResult 强类型结果。

        3. 测试数据与模拟场景说明:
           - 历史利润率基准 [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35]，分别测试四种边界。

        4. 预期断言与结果验证:
           - cycle_phase_code 分别等于 TROUGH_RECOVERY, PEAK_OVERHEAT, LATE_CYCLE_CONTRACTION, MID_CYCLE_EXPANSION。
           - 买方战略研判词包含对应商业关键词。
        """
        hist_margins = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35]

        # 1. 谷底复苏 (利润率处于极低 P10，但增速回正企稳)
        phase_trough = MidCycleNormalizationEngine.detect_cycle_phase(
            current_operating_margin=0.06,
            history_operating_margins=hist_margins,
            current_revenue_growth=0.08,
        )
        self.assertEqual(phase_trough.cycle_phase_code, "TROUGH_RECOVERY")
        self.assertIn("左侧", phase_trough.buy_side_strategic_verdict_zh)

        # 2. 繁荣见顶 (利润率处于极高 P90 极端高位)
        phase_peak = MidCycleNormalizationEngine.detect_cycle_phase(
            current_operating_margin=0.34,
            history_operating_margins=hist_margins,
            current_revenue_growth=-0.02,
        )
        self.assertEqual(phase_peak.cycle_phase_code, "PEAK_OVERHEAT")
        self.assertIn("假低 PE", phase_peak.buy_side_strategic_verdict_zh)

        # 3. 晚周期收缩 (负增长且利润率显著被挤压)
        phase_late = MidCycleNormalizationEngine.detect_cycle_phase(
            current_operating_margin=0.08,
            history_operating_margins=hist_margins,
            current_revenue_growth=-0.15,
            industry_median_margin=0.20,
        )
        self.assertEqual(phase_late.cycle_phase_code, "LATE_CYCLE_CONTRACTION")
        self.assertIn("回避", phase_late.buy_side_strategic_verdict_zh)

        # 4. 中周期稳健扩张 (中枢走廊稳健)
        phase_mid = MidCycleNormalizationEngine.detect_cycle_phase(
            current_operating_margin=0.20,
            history_operating_margins=hist_margins,
            current_revenue_growth=0.06,
        )
        self.assertEqual(phase_mid.cycle_phase_code, "MID_CYCLE_EXPANSION")
        self.assertIn("主升浪", phase_mid.buy_side_strategic_verdict_zh)

    def test_evaluate_mid_cycle_valuation_end_to_end(self):
        """【FT-PH3C-04: 周期型重资产企业端到端内在公允价值锚定与研报输出验证】

        1. 测试功能与测试点:
           - 验证 evaluate_mid_cycle_valuation 针对周期型重资产标的（如希捷科技 STX）执行全流程跨周期内在价值推导。
           - 融合正常化 FCF、席勒 CAPE 锚点与周期四象限修正，输出内在公允价值 (mid_cycle_fair_value)。
           - 输出隐含涨跌空间百分比并生成通俗买方自然语言研报摘要 (valuation_summary_zh)。

        2. 正常函数业务边界与参数契约:
           - 接收企业历史 7 年财务序列与即期资产负债参数，返回 MidCycleValuationResult。

        3. 测试数据与模拟场景说明:
           - 希捷科技 (STX) 7 年周期历史三表输入，现价 102.50 美元，股数 210M。

        4. 预期断言与结果验证:
           - mid_cycle_fair_value > 0。
           - implied_upside_downside_pct 非空。
           - valuation_summary_zh 包含 "STX 跨周期正常化估值研报"。
           - cycle_phase 非空。
        """
        res = MidCycleNormalizationEngine.evaluate_mid_cycle_valuation(
            ticker="STX",
            current_price=102.50,
            shares_outstanding=210.0,
            total_debt=5600.0,
            cash_and_equivalents=850.0,
            history_revenues=[9500.0, 10500.0, 11700.0, 8000.0, 7500.0, 8500.0, 10000.0],
            history_operating_incomes=[1400.0, 1700.0, 2100.0, 600.0, 300.0, 1100.0, 1600.0],
            history_capex=[550.0, 600.0, 750.0, 450.0, 300.0, 400.0, 500.0],
            history_net_incomes=[1100.0, 1350.0, 1700.0, 400.0, 150.0, 850.0, 1250.0],
            current_total_assets=8200.0,
            current_revenue_growth=0.12,
            wacc=0.09,
            terminal_growth=0.02,
        )

        self.assertIsInstance(res, MidCycleValuationResult)
        self.assertGreater(res.mid_cycle_fair_value, 0.0)
        self.assertIsNotNone(res.implied_upside_downside_pct)
        self.assertIn("STX 跨周期正常化估值研报", res.valuation_summary_zh)
        self.assertIsNotNone(res.cycle_phase)

    def test_api_mid_cycle_mode_facade(self):
        """【IT-PH3C-05: FinancialAnalysisSystem统一门面MID_CYCLE跨周期模式独立按需精准调度】

        1. 测试功能与测试点:
           - 验证 FinancialAnalysisSystem.analyze_equity 对 MID_CYCLE（跨周期正常化估值模式）的独立精准调度。
           - 验证执行状态 execution_success 为 True，分析模式为 "mid_cycle"。
           - 验证决策卡片装载 cycle_phase、mid_cycle_fair_value 与 shiller_cape。
           - 验证估值情景矩阵 (valuation_scenarios) 数量大于 0。

        2. 正常函数业务边界与参数契约:
           - 支持枚举 AnalysisMode.MID_CYCLE，返回 FinancialAnalysisResult 结果。

        3. 测试数据与模拟场景说明:
           - RXRX 样本标的在跨周期模式下独立调度。

        4. 预期断言与结果验证:
           - execution_success 为 True。
           - mid_cycle_valuation 非空。
           - 决策卡片装载 cycle_phase、mid_cycle_fair_value 与 shiller_cape。
        """
        res = self.api.analyze_equity(
            ticker="RXRX",
            mode=AnalysisMode.MID_CYCLE,
            allow_demo_sample=True,
        )
        self.assertTrue(res.execution_success)
        self.assertEqual(res.analysis_mode, "mid_cycle")
        self.assertIsNotNone(res.mid_cycle_valuation)
        self.assertIsNotNone(res.decision_card.cycle_phase)
        self.assertIsNotNone(res.decision_card.mid_cycle_fair_value)
        self.assertIsNotNone(res.decision_card.shiller_cape)
        self.assertGreater(len(res.valuation_scenarios), 0)

    def test_api_full_systemic_mode_all_phases_complete(self):
        """【FT-PH3C-06: 系统全息模式FULL_SYSTEMIC全盘实现Phase3A/3B/3C全阶段终极装配与决策卡片闭环】

        1. 测试功能与测试点:
           - 验证 FinancialAnalysisSystem 在全流程 FULL_SYSTEMIC 分析模式下，全盘熔铸三大阶段：
             * Phase 3A: 信用违约 (Merton DD, Altman Z) 与 10,000 次蒙特卡洛抽样估值；
             * Phase 3B: 组合风险 (VaR/CVaR)、极端宏观压力测试与波动率曲面希腊字母；
             * Phase 3C: 跨周期正常化现金流 (Normalized FCF)、Shiller CAPE 与周期四象限。
           - 验证顶层机构决策卡片 (decision_card) 100% 健全挂载三大阶段全部核心指标。

        2. 正常函数业务边界与参数契约:
           - 统一门面一键分析，保证无缺失、无未捕获异常、无环路依赖。

        3. 测试数据与模拟场景说明:
           - RXRX 样本标的全息端到端系统性运行。

        4. 预期断言与结果验证:
           - execution_success 为 True。
           - Phase 3A/3B/3C 核心分析对象与决策卡片字段全面装配。
        """
        res = self.api.analyze_equity(
            ticker="RXRX",
            mode=AnalysisMode.FULL_SYSTEMIC,
            allow_demo_sample=True,
        )
        self.assertTrue(res.execution_success)
        # Phase 3A: 信用风险与 10,000 次蒙特卡洛随机模拟
        self.assertIsNotNone(res.credit_risk)
        self.assertIsNotNone(res.monte_carlo_valuation)
        self.assertIsNotNone(res.decision_card.merton_dd)
        self.assertIsNotNone(res.decision_card.altman_z)
        self.assertIsNotNone(res.decision_card.monte_carlo_median)
        self.assertIsNotNone(res.decision_card.prob_undervalued_pct)

        # Phase 3B: 组合在险价值 (VaR/CVaR)、极端宏观压力测试与波动率希腊字母偏斜
        self.assertIsNotNone(res.portfolio_var)
        self.assertGreater(len(res.macro_stress_scenarios), 0)
        self.assertIsNotNone(res.decision_card.portfolio_var_95_pct)
        self.assertIsNotNone(res.decision_card.cvar_expected_shortfall_pct)
        if res.option_pricing and res.option_pricing.strike > 0:
            self.assertIsNotNone(res.volatility_greeks)
            self.assertIsNotNone(res.volatility_skew)
            self.assertIsNotNone(res.decision_card.option_delta)

        # Phase 3C: 跨周期正常化自由现金流与 Shiller CAPE
        self.assertIsNotNone(res.mid_cycle_valuation)
        self.assertIsNotNone(res.decision_card.cycle_phase)
        self.assertIsNotNone(res.decision_card.mid_cycle_fair_value)
        self.assertIsNotNone(res.decision_card.shiller_cape)


if __name__ == "__main__":
    unittest.main()
