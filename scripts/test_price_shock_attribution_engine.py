"""股价异动与公司信息披露因果归因引擎测试套件 (Price Shock Attribution Tests).

验证针对任何公司披露信息 (指引修改、增发、研发黑天鹅、SBC稀释) 或异动破位，
引擎能否精确指出异动原因，并对价格落差进行定量因果拆解。
"""

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from finance_tools.price_shock_attribution_engine import (
    GuidanceTerminalImpact,
    OperatingLeverageImpact,
    DilutionOverhangImpact,
    SBCFreeCashFlowImpact,
    RiskPremiumWACCImpact,
    DealerGammaDragImpact,
    PriceShockAttributionEngine,
)


class TestPriceShockAttributionEngine(unittest.TestCase):
    """测试异动因果归因引擎核心功能."""

    def setUp(self):
        self.engine = PriceShockAttributionEngine()

    def test_guidance_terminal_impact(self):
        """【UT-SHOCK-01: 前瞻指引下修对企业终值折现传导与每股价值落差拆解】

        1. 测试功能与测试点:
           - 验证 GuidanceTerminalImpact 前瞻指引增速下修对长期 DCF 终值的穿透传导。
           - 终值预期变化率公式: Terminal Revision Pct = (Revised Growth - Previous Growth) / Previous Growth * Terminal Value Weight。
           - 测算折现到基准每股价格上的绝对美元冲击 (Dollar Impact Per Share)。

        2. 正常函数业务边界与参数契约:
           - previous_guidance_growth > 0, revised_guidance_growth > 0。
           - 0.0 < terminal_value_weight <= 1.0 (终值在总企业价值中的占比)。
           - base_share_price > 0。

        3. 测试数据与模拟场景说明:
           - 模拟中型科技成长股: 基准市价 $50.0，终值权重 75%，此前官方指引增长 20%，季报骤然下修至 15% (下修 5 个百分点)。

        4. 预期断言与结果验证:
           - 断言 growth_revision_delta 精确等于 -0.05。
           - 断言 terminal_revision_pct 精确等于 -18.75% (-5/20 * 75%)。
           - 断言 dollar_impact_per_share 精确等于 -9.375 美元。
        """
        impact = GuidanceTerminalImpact(
            previous_guidance_growth=0.20,
            revised_guidance_growth=0.15,
            wacc=0.10,
            terminal_growth=0.025,
            base_share_price=50.0,
            terminal_value_weight=0.75,
        )
        res = impact.compute()
        self.assertEqual(res["growth_revision_delta"], -0.05)
        # 终值预期下修 = (-0.05 / 0.20) * 0.75 = -18.75%
        self.assertEqual(res["terminal_revision_pct"], -18.75)
        # 美元冲击 = 50 * -18.75% = -9.375
        self.assertEqual(res["dollar_impact_per_share"], -9.375)

    def test_operating_leverage_impact(self):
        """【UT-SHOCK-02: 高固定成本经营杠杆反噬效应与营业利润剧挫测算】

        1. 测试功能与测试点:
           - 验证 OperatingLeverageImpact 经营杠杆系数 (Degree of Operating Leverage, DOL) 测算。
           - 经营杠杆放大机制: 当企业存在重资产刚性固定成本 (Fixed Cost Ratio 较高) 且营业利润率较薄时，轻微的营业收入下滑将成倍反噬放大为营业利润的剧烈崩塌。
           - 利润崩塌穿透估值: 营业利润变动传导至 EPS 并由市盈率 PE 倍数放大为每股暴跌金额。

        2. 正常函数业务边界与参数契约:
           - revenue_change_pct < 0。
           - fixed_cost_ratio 在 (0, 1) 区间，baseline_operating_margin > 0。

        3. 测试数据与模拟场景说明:
           - 标的市价 $40.0，PE 为 25 倍，固定成本占比 70%，基准利润率 15%；营收仅微跌 5.0%。

        4. 预期断言与结果验证:
           - 断言 degree_of_operating_leverage > 4.5 (杠杆倍数达 4.97 倍)。
           - 断言 operating_income_shock_pct < -20.0% (跌幅成倍放大至 -24.8%)。
           - 断言 dollar_impact_per_share < -8.0 美元。
        """
        impact = OperatingLeverageImpact(
            revenue_change_pct=-0.05,
            fixed_cost_ratio=0.70,
            baseline_operating_margin=0.15,
            current_pe=25.0,
            base_share_price=40.0,
        )
        res = impact.compute()
        # DOL = 1 + (0.85 * 0.7) / 0.15 = 1 + 3.9667 = 4.97
        self.assertGreater(res["degree_of_operating_leverage"], 4.5)
        # 营业利润变动约为 -5% * 4.97 = -24.8%
        self.assertLess(res["operating_income_shock_pct"], -20.0)
        # 美元冲击应为负值
        self.assertLess(res["dollar_impact_per_share"], -8.0)

    def test_dilution_and_shelf_impact(self):
        """【UT-SHOCK-03: 定增折价发行与S-3货架压制导致的每股价值稀释】

        1. 测试功能与测试点:
           - 验证 DilutionOverhangImpact 针对二级市场低价定增、闪电配股或 ATM (At-The-Market) 货架增发的稀释冲击。
           - 稀释率测算: Dilution Ratio Pct = New Shares / (Current Shares + New Shares)。
           - 发行折价: Offering Discount Pct = (Offering Price - Market Price) / Market Price。
           - 增发后除权公允价测算: New Diluted Fair Price < Market Price。

        2. 正常函数业务边界与参数契约:
           - new_shares_issued > 0, current_shares_outstanding > 0。
           - offering_price < current_market_price 时体现折价抛售。

        3. 测试数据与模拟场景说明:
           - 标的现价 $10.0，当前股本 1 亿股；以 $8.0 严重折价 20% 增发 2000 万股 (稀释 16.67%)，同时存在 5000 万货架压制。

        4. 预期断言与结果验证:
           - 断言 dilution_ratio_pct 精确等于 16.67%。
           - 断言 offering_discount_pct 精确等于 -20.0%。
           - 断言 new_diluted_fair_price < 10.0。
           - 断言 dollar_impact_per_share < 0.0。
        """
        impact = DilutionOverhangImpact(
            new_shares_issued=20_000_000,
            current_shares_outstanding=100_000_000,
            offering_price=8.0,
            current_market_price=10.0,
            atm_shelf_remaining=50_000_000,
        )
        res = impact.compute()
        self.assertEqual(res["dilution_ratio_pct"], 16.67)
        self.assertEqual(res["offering_discount_pct"], -20.0)
        # 稀释后价格必然低于 10.0
        self.assertLess(res["new_diluted_fair_price"], 10.0)
        self.assertLess(res["dollar_impact_per_share"], 0.0)

    def test_sbc_fcf_stripping(self):
        """【UT-SHOCK-04: 员工股权激励(SBC)真实自由现金流剥离与价值重估】

        1. 测试功能与测试点:
           - 验证 SBCFreeCashFlowImpact 穿透员工股权激励对现金流的隐蔽侵蚀。
           - 表面自由现金流: Apparent FCF = Operating Cash Flow - CapEx。
           - 真实造血现金流: True FCF = Apparent FCF - Annual SBC。
           - 揭露企业依靠疯狂发股票充当薪酬、将经营开支隐蔽转嫁为股权稀释的虚假繁荣。

        2. 正常函数业务边界与参数契约:
           - annual_sbc > 0。
           - 当 Annual SBC > Apparent FCF 时，真实自由现金流转为负值 (True FCF < 0)。

        3. 测试数据与模拟场景说明:
           - 标的现价 $30.0，总股本 5000 万股 (市值 15 亿)；经营现金流 1.2 亿，资本开支 4000 万 (表面 FCF = 8000 万)；但全年股权激励高达 1.1 亿美元 (真实 FCF = -3000 万)。

        4. 预期断言与结果验证:
           - 断言 apparent_fcf == 80,000,000.0。
           - 断言 true_fcf == -30,000,000.0。
           - 断言 dollar_impact_per_share < -20.0 美元 (产生大幅估值重估惩罚)。
        """
        impact = SBCFreeCashFlowImpact(
            reported_operating_cash_flow=120_000_000,
            reported_capex=40_000_000,
            annual_sbc=110_000_000,  # SBC 甚至超过了自由现金流
            shares_outstanding=50_000_000,
            market_cap=1_500_000_000,
            base_share_price=30.0,
        )
        res = impact.compute()
        self.assertEqual(res["apparent_fcf"], 80_000_000)
        # 真实 FCF = 80M - 110M = -30M
        self.assertEqual(res["true_fcf"], -30_000_000)
        # 真实每股现金流为负，估值产生显著负向重定价差额
        self.assertLess(res["dollar_impact_per_share"], -20.0)

    def test_dealer_gamma_breakdown(self):
        """【UT-SHOCK-05: 跌破关键行权价做市商负Gamma顺势助跌与抛压测算】

        1. 测试功能与测试点:
           - 验证 DealerGammaDragImpact 期权做市商负 Gamma 顺势动态对冲助跌测算。
           - 机制: 当股价跌破看跌期权密集未平仓区 (Critical Strike) 时，做市商因负 Gamma 被迫在现货市场顺势加速抛售股票对冲 Delta，形成踩踏式流动性黑洞。

        2. 正常函数业务边界与参数契约:
           - current_price < critical_strike 时激活负 Gamma 助跌 (gamma_drag_active = True)。
           - forced_selling_shares 计算强制平仓抛售股数。

        3. 测试数据与模拟场景说明:
           - 标的由 $4.00 关键行权价破位跌至 $3.70，净 Gamma 暴露 200 万股，日均成交量 500 万股。

        4. 预期断言与结果验证:
           - 断言 gamma_drag_active 为 True。
           - 断言 forced_selling_shares == 600,000.0 股。
           - 断言 dollar_impact_per_share < 0.0。
        """
        impact = DealerGammaDragImpact(
            current_price=3.70,
            critical_strike=4.00,
            net_gamma_exposure_shares=2_000_000,
            average_daily_volume=5_000_000,
        )
        res = impact.compute()
        self.assertTrue(res["gamma_drag_active"])
        self.assertEqual(res["forced_selling_shares"], 600_000.0)
        self.assertLess(res["dollar_impact_per_share"], 0.0)

    def test_full_price_shock_attribution_workflow(self):
        """【IT-SHOCK-06: 股价深度异动多因子因果归因全流程与落差解释度闭环】

        1. 测试功能与测试点:
           - 验证 PriceShockAttributionEngine.attribute_shock 跨因子联合因果归因流水线。
           - 定量因果拆解: 将总观察价格落差 (Total Observed Gap) 分解为各微观基本面与衍生品结构因子的贡献分量。
           - 检验归因解释度: 解释落差金额与解释度占比 (explained_ratio_pct > 70%)。

        2. 正常函数业务边界与参数契约:
           - base_price > actual_price。
           - 因子贡献分量之和逼近实际总落差。

        3. 测试数据与模拟场景说明:
           - 标的股价从 $10.00 暴跌至 $6.80 (总落差 -$3.20)。
           - 注入三大约束因子: 指引终值下修 (Guidance)、定增稀释 (Dilution) 与做市商负 Gamma 助跌 (Gamma Drag)。

        4. 预期断言与结果验证:
           - 断言 total_observed_gap_dollars 精确等于 -3.20。
           - 断言 total_explained_gap_dollars < -2.00。
           - 断言 explained_ratio_pct > 70.0%。
           - 断言 factor_contributions 包含三大因子贡献项。
        """
        base_price = 10.00
        actual_price = 6.80  # 观察到的市场价格

        guidance = GuidanceTerminalImpact(
            previous_guidance_growth=0.25,
            revised_guidance_growth=0.20,
            wacc=0.10,
            terminal_growth=0.02,
            base_share_price=base_price,
            terminal_value_weight=0.70,
        )
        dilution = DilutionOverhangImpact(
            new_shares_issued=10_000_000,
            current_shares_outstanding=100_000_000,
            offering_price=7.50,
            current_market_price=base_price,
            atm_shelf_remaining=20_000_000,
        )
        gamma = DealerGammaDragImpact(
            current_price=actual_price,
            critical_strike=8.00,
            net_gamma_exposure_shares=1_500_000,
            average_daily_volume=4_000_000,
        )

        res = self.engine.attribute_shock(
            base_price=base_price,
            actual_price=actual_price,
            guidance=guidance,
            dilution=dilution,
            gamma_drag=gamma,
        )

        self.assertEqual(res["total_observed_gap_dollars"], -3.20)
        self.assertLess(res["total_explained_gap_dollars"], -2.00)
        self.assertGreater(res["explained_ratio_pct"], 70.0)
        self.assertIn("guidance_terminal_shock", res["factor_contributions"])
        self.assertIn("dilution_and_shelf_shock", res["factor_contributions"])
        self.assertIn("dealer_gamma_drag", res["factor_contributions"])

    def test_ut_shock_07_operating_leverage_limited_liability_floor(self):
        """【UT-SHOCK-07: 经营杠杆恶性坍塌股东有限责任公允价值下界归零防御断言】

        一、测试功能与测试点:
            验证股东有限责任金融物理法则防御:
            当企业营业利润遭遇恶性毁灭性打击 (利润下滑幅度超越 100%) 时，
            股价跌幅受有限责任约束封顶为 100% (-base_share_price)，
            系统严禁推导每股理论公允价值为负数 (如 -$15.00) 的金融常识错误。

        二、正常函数业务边界与参数契约:
            - base_share_price: 30.0
            - revenue_change_pct: -0.50 (营收腰斩)
            - fixed_cost_ratio: 0.90 (重资产极高固定成本)
            - 算出的 DOL 会远超 5.0，理论利润下滑将 > 200%

        三、测试数据与模拟场景说明:
            测试重资产周期型企业在行业断崖下行中的极限承压场景。

        四、预期断言与结果验证:
            断言 dollar_impact_per_share 精确钳制在 -30.0 (等于 -base_share_price)。
            断言 dollar_impact_per_share 绝不低于 -30.0。
        """
        impact = OperatingLeverageImpact(
            revenue_change_pct=-0.50,
            fixed_cost_ratio=0.90,
            baseline_operating_margin=0.08,
            current_pe=20.0,
            base_share_price=30.0,
        )
        res = impact.compute()
        self.assertEqual(res["dollar_impact_per_share"], -30.0)

    def test_ut_shock_08_gamma_negative_domain_math_pow_defense(self):
        """【UT-SHOCK-08: 做市商负 Gamma 顺周期助跌 math.pow 负数域异常防御断言】

        一、测试功能与测试点:
            验证 math.pow 浮点数指数运算边界防御:
            当输入异常数据 (如 negative net gamma 或 volume) 时，
            引擎刚性防御负数开小数次方引起的 ValueError: math domain error 崩溃，
            保证极端异常输入下依然平稳计算。

        二、正常函数业务边界与参数契约:
            - net_gamma_exposure_shares: -1000 (异常负值)
            - average_daily_volume: 0 (除零边界)

        三、测试数据与模拟场景说明:
            测试做市商仓位脏数据输入场景。

        四、预期断言与结果验证:
            断言函数无异常崩溃抛出。
            断言 dollar_impact_per_share 为有限非正数。
        """
        impact = DealerGammaDragImpact(
            current_price=5.0,
            critical_strike=6.0,
            net_gamma_exposure_shares=-1000.0,
            average_daily_volume=0.0,
        )
        res = impact.compute()
        self.assertIsInstance(res["dollar_impact_per_share"], float)
        self.assertLessEqual(res["dollar_impact_per_share"], 0.0)

    def test_ut_shock_09_buyer_commercial_narrative_and_deengineered_zh(self):
        """【UT-SHOCK-09: 买方通俗商业叙事与去工程符号化解读断言】

        一、测试功能与测试点:
            验证去工程符号化与买方自然语言输出规范:
            PriceShockAttributionEngine.attribute_shock 必须输出自然流畅的
            中文商业直觉归因研报 (narrative_zh)，杜绝向投资人暴露诸如
            `guidance_terminal_shock`、`dealer_gamma_drag` 等纯英文代码代号。

        二、正常函数业务边界与参数契约:
            - 正常多因子归因输入。

        三、测试数据与模拟场景说明:
            测试从 $20.0 跌至 $14.0 的综合异动场景。

        四、预期断言与结果验证:
            断言 narrative_zh 非空且包含 "总观察价格落差"。
            断言 narrative_zh 包含自然中文因子名称 (如 "官方指引下修" 或 "定增摊薄压制")。
            断言 narrative_zh 严禁包含英文工程下划线代号。
        """
        guidance = GuidanceTerminalImpact(0.20, 0.15, 0.10, 0.02, 20.0, 0.70)
        res = self.engine.attribute_shock(20.0, 14.0, guidance=guidance)
        narrative = res["narrative_zh"]
        self.assertIn("总观察价格落差", narrative)
        self.assertIn("官方指引下修", narrative)
        self.assertNotIn("guidance_terminal_shock", narrative)

    def test_ut_shock_10_facade_and_core_ssot_equivalence(self):
        """【UT-SHOCK-10: 向下兼容中继门面 SSOT 完全等价性断言】

        一、测试功能与测试点:
            验证 `finance_tools.price_shock_attribution_engine` 中继门面与底层核心
            `financial_core.engines.price_shock_attribution_engine` 计算输出 100% 相同。

        二、正常函数业务边界与参数契约:
            - Facade 与 Core 传入相同输入。

        三、测试数据与模拟场景说明:
            测试标准异动因果归因场景。

        四、预期断言与结果验证:
            断言门面与核心输出属性完全一致。
        """
        from financial_core.engines.price_shock_attribution_engine import (
            PriceShockAttributionEngine as CoreEngine,
            GuidanceTerminalImpact as CoreGuidance,
        )
        g_core = CoreGuidance(0.30, 0.20, 0.09, 0.025, 50.0, 0.80)
        g_facade = GuidanceTerminalImpact(0.30, 0.20, 0.09, 0.025, 50.0, 0.80)

        core_engine = CoreEngine()
        res_core = core_engine.attribute_shock(50.0, 42.0, guidance=g_core)
        res_facade = self.engine.attribute_shock(50.0, 42.0, guidance=g_facade)

        self.assertEqual(res_core["total_observed_gap_dollars"], res_facade["total_observed_gap_dollars"])
        self.assertEqual(res_core["total_explained_gap_dollars"], res_facade["total_explained_gap_dollars"])
        self.assertEqual(res_core["narrative_zh"], res_facade["narrative_zh"])

    def test_ut_shock_11_factor_chinese_name_and_flat_direction_contract(self):
        """【UT-SHOCK-11: 归因因子中文名称字典与价格持平方向语义断言】

        一、测试功能与测试点:
            1. 验证各因子计算子字典中已注入 factor_name_zh 自然中文名称；
            2. 验证输出字典包含全局 factor_chinese_names 字典；
            3. 验证当基准价与现价相等 (落差为0) 时，direction_zh 输出 '基本持平'，杜绝误写为 '上涨'。

        二、正常函数业务边界与参数契约:
            - base_price == actual_price (零落差)

        三、测试数据与模拟场景说明:
            测试价格未发生变动的横盘场景。

        四、预期断言与结果验证:
            断言 direction_zh == '基本持平'；
            断言 narrative_zh 包含 '基本持平'；
            断言 factor_chinese_names 包含 'guidance_terminal_shock'。
        """
        guidance = GuidanceTerminalImpact(0.20, 0.15, 0.10, 0.02, 20.0, 0.70)
        res_flat = self.engine.attribute_shock(20.0, 20.0, guidance=guidance)
        self.assertEqual(res_flat["direction_zh"], "基本持平")
        self.assertIn("基本持平", res_flat["narrative_zh"])
        self.assertIn("factor_chinese_names", res_flat)
        self.assertIn("factor_name_zh", res_flat["factor_contributions"]["guidance_terminal_shock"])
        self.assertEqual(
            res_flat["factor_contributions"]["guidance_terminal_shock"]["factor_name_zh"],
            "官方前瞻指引下修 (终值折现下折)",
        )


if __name__ == "__main__":
    unittest.main()
