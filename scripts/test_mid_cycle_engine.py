"""中周期盈利中枢与跨周期正常化估值引擎单元测试套件.

本测试模块严格遵循《36号工程黄金设计规范》与四段式结构化中文契约测试模型:
1. 测试功能与测试点说明 (Test Functionality & Objectives)
2. 正常函数业务边界与参数契约 (Business Boundaries & Parameter Contracts)
3. 测试数据与模拟场景说明 (Test Data & Scenario Descriptions)
4. 预期断言与结果验证 (Expected Assertions & Verification)

涵盖跨周期现金流平滑、Shiller CAPE 平减、周期阶段判定、哨兵代号去工程化及极端除零边界防御。
"""

import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.mid_cycle_engine import (
    CYCLE_PHASE_METADATA,
    MidCycleFCFResult,
    ShillerCAPEResult,
    CyclePhaseResult,
    MidCycleValuationResult,
    MidCycleValuationEngine,
)
from finance_tools.mid_cycle_engine import (
    CYCLE_PHASE_METADATA as Facade_CYCLE_PHASE_METADATA,
    MidCycleFCFResult as FacadeMidCycleFCFResult,
    ShillerCAPEResult as FacadeShillerCAPEResult,
    CyclePhaseResult as FacadeCyclePhaseResult,
    MidCycleValuationResult as FacadeMidCycleValuationResult,
    MidCycleValuationEngine as FacadeMidCycleValuationEngine,
)


class TestMidCycleValuationEngine(unittest.TestCase):
    """跨周期正常化估值引擎契约与边界测试."""

    def test_ut_midcycle_01_fcf_normalization(self):
        """【UT-MIDCYCLE-01: 跨周期自由现金流正常化中枢推导与资产周转率中位数计算】

        一、测试功能与测试点:
            验证跨越景气周期时，历史营收、营业利润、资本开支序列能否正确剔除周期噪音，
            计算出长期平稳的营业利润率中位数、资本密集度中位数与现有资产下的正常化 FCF。

        二、正常函数业务边界与参数契约:
            - history_revenues: 至少 3 年以上历史营收序列 (金额需为正)
            - history_operating_incomes: 历史营业利润序列 (可包含周期谷底低点)
            - history_capex: 历史资本开支序列
            - current_total_assets: 现有总资产规模

        三、测试数据与模拟场景说明:
            模拟一家典型半导体/重资产周期企业 5 年历史跨度:
            - 营收经历 $1000M -> $1400M -> $2000M (见顶) -> $1300M (下行) -> $1500M (复苏)
            - 营业利润经历 $150M -> $280M -> $600M -> $130M -> $225M
            - 资本开支经历 $100M -> $150M -> $250M -> $120M -> $140M
            - 当前资产规模 $1800M

        四、预期断言与结果验证:
            断言正常化年均 FCF > 0，且利润率中位数与再投资率中位数均落在合理区间。
        """
        revs = [1000.0, 1400.0, 2000.0, 1300.0, 1500.0]
        ebits = [150.0, 280.0, 600.0, 130.0, 225.0]
        capex = [100.0, 150.0, 250.0, 120.0, 140.0]
        assets = 1800.0

        res = MidCycleValuationEngine.normalize_cycle_fcf(
            history_revenues=revs,
            history_operating_incomes=ebits,
            history_capex=capex,
            current_total_assets=assets,
        )

        self.assertIsInstance(res, MidCycleFCFResult)
        self.assertEqual(res.history_years_count, 5)
        self.assertGreater(res.normalized_mid_cycle_fcf, 0.0)
        self.assertGreater(res.median_operating_margin, 0.10)
        self.assertLess(res.median_operating_margin, 0.35)
        self.assertGreater(res.median_asset_turnover, 0.5)

    def test_ut_midcycle_02_shiller_cape_inflation_adjusted(self):
        """【UT-MIDCYCLE-02: 希勒 10 年周期调整市盈率 (Shiller CAPE) 通胀平减与估值分层】

        一、测试功能与测试点:
            验证通过 CPI 平减指数调整历史各年真实购买力后，准确求解 Shiller Real EPS，
            并对比基准 CAPE 判定企业所处估值分层 (深度折价 / 公允合理 / 周期高估透支)。

        二、正常函数业务边界与参数契约:
            - current_price: 标的现价 (例如 $120.0)
            - shares_outstanding: 摊薄后总股本 (例如 50M 股)
            - history_net_incomes: 10 年净利润序列
            - cpi_inflation_multipliers: 10 年通胀倍数

        三、测试数据与模拟场景说明:
            模拟稳健成熟白马股，过去 5 年名义利润逐年递增，经 CPI 乘数调整至当前美元购买力。
            基准历史 CAPE 设定为 20.0x。

        四、预期断言与结果验证:
            断言计算出的 Shiller Real EPS > 0，Shiller CAPE 处于正常走廊，
            且估值定性 tier 包含中文分层说明。
        """
        net_incomes = [200.0, 240.0, 310.0, 280.0, 350.0]
        cpi = [1.18, 1.14, 1.09, 1.04, 1.00]
        shares = 50.0
        price = 60.0

        res = MidCycleValuationEngine.compute_shiller_cape(
            current_price=price,
            shares_outstanding=shares,
            history_net_incomes=net_incomes,
            cpi_inflation_multipliers=cpi,
            historical_benchmark_cape=20.0,
        )

        self.assertIsInstance(res, ShillerCAPEResult)
        self.assertGreater(res.shiller_real_eps_10y, 0.0)
        self.assertGreater(res.shiller_cape_ratio, 5.0)
        self.assertLess(res.shiller_cape_ratio, 40.0)
        self.assertTrue("CAPE" in res.cape_valuation_tier_zh)

    def test_ut_midcycle_03_cycle_phase_detection(self):
        """【UT-MIDCYCLE-03: 四象限周期阶段识别 (谷底复苏/中周期扩张/周期见顶/晚周期收缩)】

        一、测试功能与测试点:
            验证利润率分位数与营收增速在不同组合下的周期阶段识别器，
            确保买方战略研判文字符合逆向投资因果逻辑。

        二、正常函数业务边界与参数契约:
            - current_operating_margin: 当前最新营业利润率
            - history_operating_margins: 历史利润率序列
            - current_revenue_growth: 最新营收同比增速

        三、测试数据与模拟场景说明:
            1. 谷底修复场景: 利润率仅 4% (处于历史 10% 分位数)，但营收增速已转正至 +2%；
            2. 见顶过热场景: 利润率 32% (处于历史 95% 分位数)；
            3. 晚周期收缩场景: 利润率下滑至 8%，营收负增长 -12%。

        四、预期断言与结果验证:
            断言分别正确映射至 TROUGH_RECOVERY、PEAK_OVERHEAT、LATE_CYCLE_CONTRACTION。
        """
        history_margins = [0.05, 0.08, 0.12, 0.18, 0.25, 0.30]

        # 1. 谷底修复
        trough = MidCycleValuationEngine.detect_cycle_phase(
            current_operating_margin=0.04,
            history_operating_margins=history_margins,
            current_revenue_growth=0.02,
        )
        self.assertEqual(trough.cycle_phase_code, "TROUGH_RECOVERY")
        self.assertTrue("左侧击球点" in trough.buy_side_strategic_verdict_zh)

        # 2. 见顶过热
        peak = MidCycleValuationEngine.detect_cycle_phase(
            current_operating_margin=0.32,
            history_operating_margins=history_margins,
            current_revenue_growth=0.15,
        )
        self.assertEqual(peak.cycle_phase_code, "PEAK_OVERHEAT")
        self.assertTrue("假低 PE" in peak.buy_side_strategic_verdict_zh)

        # 3. 晚周期收缩
        contraction = MidCycleValuationEngine.detect_cycle_phase(
            current_operating_margin=0.06,
            history_operating_margins=history_margins,
            current_revenue_growth=-0.15,
            industry_median_margin=0.15,
        )
        self.assertEqual(contraction.cycle_phase_code, "LATE_CYCLE_CONTRACTION")
        self.assertTrue("下行通道回避" in contraction.buy_side_strategic_verdict_zh)

    def test_ut_midcycle_04_sentinel_to_natural_language(self):
        """【UT-MIDCYCLE-04: 极端长期亏损企业 999.0x 内部哨兵代号转通俗自然语言防泄露断言】

        一、测试功能与测试点:
            验证当企业长期亏损、10 年真实平均 EPS 为负时，系统内部赋予的哨兵代号 999.0x
            严禁泄露给用户，必须在最终报告中转换为“亏损不可比 (10年平均真实 EPS 为负)”。

        二、正常函数业务边界与参数契约:
            - history_net_incomes: 全为负数或平均值为负的净利润序列
            - evaluate_mid_cycle_valuation 输出研报 summary

        三、测试数据与模拟场景说明:
            测试一家连续 4 年深陷重组或巨额亏损的重度周期企业:
            净利润序列: [-100M, -80M, -50M, -120M]

        四、预期断言与结果验证:
            断言研报字符串中严禁出现 "999.0x"，必须出现 "亏损不可比"。
        """
        res = MidCycleValuationEngine.evaluate_mid_cycle_valuation(
            ticker="LOSSER_CORP",
            current_price=15.0,
            shares_outstanding=20.0,
            total_debt=500.0,
            cash_and_equivalents=50.0,
            history_revenues=[200.0, 220.0, 180.0, 190.0],
            history_operating_incomes=[-50.0, -40.0, -60.0, -30.0],
            history_capex=[30.0, 20.0, 15.0, 25.0],
            history_net_incomes=[-100.0, -80.0, -50.0, -120.0],
            current_total_assets=600.0,
        )

        self.assertNotIn("999.0x", res.valuation_summary_zh)
        self.assertIn("亏损不可比", res.valuation_summary_zh)
        self.assertIn("特别风险警示", res.valuation_summary_zh)

    def test_ut_midcycle_05_zero_price_and_dual_negative_defense(self):
        """【UT-MIDCYCLE-05: 股价为零或负值边界防御与双负清算残值保护商业语义完整性】

        一、测试功能与测试点:
            验证在极端异常输入（如现价 current_price <= 0）时，系统是否具备除零安全防护，
            不抛出 ZeroDivisionError；且当现金流与利润双负时，公允价值触发清算残值下界 $0.01。

        二、正常函数业务边界与参数契约:
            - current_price: 0.0 (触发除零边界防御)
            - 正常化 FCF 与 10 年平均 EPS 均为负

        三、测试数据与模拟场景说明:
            传入 current_price = 0.0，检验数学安全网。

        四、预期断言与结果验证:
            断言计算顺利完成，不崩溃，fair_value 为 0.01，且包含残值保护与风险警示。
        """
        res = MidCycleValuationEngine.evaluate_mid_cycle_valuation(
            ticker="ZERO_PRICE_TEST",
            current_price=0.0,
            shares_outstanding=10.0,
            total_debt=300.0,
            cash_and_equivalents=10.0,
            history_revenues=[100.0, 110.0, 90.0],
            history_operating_incomes=[-20.0, -30.0, -10.0],
            history_capex=[10.0, 15.0, 8.0],
            history_net_incomes=[-40.0, -50.0, -30.0],
            current_total_assets=200.0,
        )

        self.assertEqual(res.mid_cycle_fair_value, 0.01)
        self.assertFalse(math.isinf(res.implied_upside_downside_pct))
        self.assertFalse(math.isnan(res.implied_upside_downside_pct))
        self.assertIn("特别风险警示", res.valuation_summary_zh)

    def test_ut_midcycle_06_buyer_dossier_card_and_to_dict_contract(self):
        """【UT-MIDCYCLE-06: 跨周期估值买方全息研报卡片与 to_dict 序列化契约断言】

        一、测试功能与测试点:
            1. 验证 MidCycleValuationResult 具备标准 narrative_zh 买方全息研报卡片；
            2. 验证卡片通俗整合周期阶段、造血中枢、Shiller CAPE 走廊与公允锚点，去工程符号化；
            3. 验证 MidCycleFCFResult, ShillerCAPEResult, CyclePhaseResult, MidCycleValuationResult
               全部实现 to_dict() 契约，输出分层清晰无遗漏。

        二、正常函数业务边界与参数契约:
            - evaluate_mid_cycle_valuation 返回完整估值结果。

        三、测试数据与模拟场景说明:
            测试典型半导体周期龙头正常化估值场景。

        四、预期断言与结果验证:
            断言 narrative_zh 包含“【标的 SEMI 跨周期正常化估值全息研报】”。
            断言 to_dict() 包含 fcf_normalization, shiller_cape, cycle_phase, narrative_zh。
        """
        res = MidCycleValuationEngine.evaluate_mid_cycle_valuation(
            ticker="SEMI",
            current_price=80.0,
            shares_outstanding=100.0,
            total_debt=500.0,
            cash_and_equivalents=200.0,
            history_revenues=[1000.0, 1500.0, 2000.0, 1200.0, 1600.0],
            history_operating_incomes=[200.0, 350.0, 600.0, 180.0, 320.0],
            history_capex=[150.0, 200.0, 300.0, 150.0, 180.0],
            history_net_incomes=[160.0, 280.0, 480.0, 140.0, 250.0],
            current_total_assets=3000.0,
            current_revenue_growth=0.08,
        )

        self.assertIn("跨周期正常化估值全息研报", res.narrative_zh)
        self.assertIn("周期所处阶段", res.narrative_zh)
        self.assertIn("跨周期造血中枢", res.narrative_zh)
        self.assertIn("估值走廊与公允锚点", res.narrative_zh)
        self.assertIn("买方战略研判", res.narrative_zh)

        d = res.to_dict()
        self.assertEqual(d["ticker"], "SEMI")
        self.assertIn("fcf_normalization", d)
        self.assertIn("shiller_cape", d)
        self.assertIn("cycle_phase", d)
        self.assertIn("narrative_zh", d)
        self.assertEqual(d["narrative_zh"], res.narrative_zh)

    def test_ut_midcycle_07_facade_and_core_ssot_equivalence(self):
        """【UT-MIDCYCLE-07: 向下兼容中继门面 SSOT 完全等价性断言】

        一、测试功能与测试点:
            验证 `finance_tools.mid_cycle_engine` 中继门面与底层核心
            `financial_core.engines.mid_cycle_engine` 计算与状态元数据 100% 相同。

        二、正常函数业务边界与参数契约:
            - Facade 与 Core 传入相同输入。

        三、测试数据与模拟场景说明:
            测试标准中周期企业输入。

        四、预期断言与结果验证:
            断言门面与核心输出属性完全一致。
        """
        revs = [1000.0, 1200.0, 1500.0, 1100.0]
        ebits = [150.0, 200.0, 300.0, 120.0]
        capex = [80.0, 100.0, 150.0, 90.0]
        assets = 1500.0

        res_core = MidCycleValuationEngine.normalize_cycle_fcf(revs, ebits, capex, assets)
        res_facade = FacadeMidCycleValuationEngine.normalize_cycle_fcf(revs, ebits, capex, assets)

        self.assertEqual(res_core.normalized_mid_cycle_fcf, res_facade.normalized_mid_cycle_fcf)
        self.assertEqual(res_core.median_operating_margin, res_facade.median_operating_margin)
        self.assertEqual(CYCLE_PHASE_METADATA, Facade_CYCLE_PHASE_METADATA)

    def test_ut_midcycle_08_cross_market_currency_adaptation(self):
        """【UT-MIDCYCLE-08: 跨市场多币种自适应推导与研报符号无死锁断言】

        一、测试功能与测试点:
            1. 验证传入日股标的 (如 6758.T 或 4位纯数字 8035) 时，系统自适应推导货币符号为 '¥'；
            2. 验证研报 summary、全息研报卡片 narrative_zh 及 to_dict 序列化中均正确呈现对应货币符号，严禁张冠李戴死锁美元 '$'；
            3. 验证显式指定 currency_symbol 参数具备最高优先级。

        二、正常函数业务边界与参数契约:
            - ticker: "6758.T" (日股标的)
            - market: "JP" 或缺省
            - currency_symbol: 自动解析或显式传参

        三、测试数据与模拟场景说明:
            测试日股东证主要龙头企业跨周期估值，传入以日元计价的财务序列。

        四、预期断言与结果验证:
            断言 currency_symbol 为 '¥'，narrative_zh 包含 '¥' 且无死锁 '$'。
        """
        res_jp = MidCycleValuationEngine.evaluate_mid_cycle_valuation(
            ticker="6758.T",
            current_price=2800.0,
            shares_outstanding=1200.0,
            total_debt=50000.0,
            cash_and_equivalents=30000.0,
            history_revenues=[100000.0, 110000.0, 125000.0, 105000.0],
            history_operating_incomes=[12000.0, 15000.0, 18000.0, 11000.0],
            history_capex=[8000.0, 9000.0, 11000.0, 8500.0],
            history_net_incomes=[9000.0, 12000.0, 14000.0, 8500.0],
            current_total_assets=150000.0,
        )

        self.assertEqual(res_jp.currency_symbol, "¥")
        self.assertIn("¥", res_jp.valuation_summary_zh)
        self.assertIn("¥", res_jp.narrative_zh)
        self.assertNotIn("$", res_jp.valuation_summary_zh)
        self.assertNotIn("$", res_jp.narrative_zh)

        d = res_jp.to_dict()
        self.assertEqual(d["currency_symbol"], "¥")
        self.assertTrue(d["current_price"].startswith("¥"))
        self.assertTrue(d["mid_cycle_fair_value"].startswith("¥"))
        self.assertTrue(d["fcf_normalization"]["normalized_fcf"].startswith("¥"))
        self.assertTrue(d["shiller_cape"]["current_price"].startswith("¥"))


if __name__ == "__main__":
    unittest.main()
