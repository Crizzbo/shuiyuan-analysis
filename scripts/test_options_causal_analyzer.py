# -*- coding: utf-8 -*-
"""单元测试：期权因果链量化推导引擎与全周期损益分析 (Options Causal Analyzer Tests)"""

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finance_tools.options_causal_analyzer import (
    OptionContractInput,
    UnderlyingScenarios,
    OptionsCausalAnalyzer,
)


class TestOptionsCausalAnalyzer(unittest.TestCase):
    def setUp(self):
        # 标的情景分布 (总概率 = 1.0)
        self.rxrx_scenarios = UnderlyingScenarios(
            bear_price=2.00,  # 跌入资产底线附近
            bear_prob=0.25,
            base_price=6.50,  # 基准公允价
            base_prob=0.50,
            bull_price=12.00, # 乐观爆发
            bull_prob=0.25,
        )

    def test_otm_call_option_causal_analysis(self):
        """【UT-OPTION-01: 虚值看涨期权全周期损益推导与归零风险因果分析】

        1. 测试功能与测试点:
           - 验证 OptionsCausalAnalyzer 对虚值期权 (OTM Call) 的全生命周期定价与损益推导。
           - 验证虚值期权特征: 内在价值恒为 0，权利金全部为时间价值 (Time Value Ratio = 1.0)。
           - 验证保本点公式: Break-Even = Strike + Premium。
           - 验证三情景到期损益:
             悲观到期 (< Strike): 100% 权利金归零损耗 (-100%)；
             基准到期 (> Strike): 行权利润 Payoff = S_base - Strike - Premium；
             乐观到期 (>> Strike): 高杠杆非线性爆发。
           - 验证期权仓位风控硬约束: 四分之一凯利资金配置上限严格限制在 <= 2.0%。

        2. 正常函数业务边界与参数契约:
           - Underlying Spot < Strike 时被判定为 OTM Call。
           - Intrinsic Value = max(0, Spot - Strike) = 0。
           - Time Value = Premium - Intrinsic Value = Premium。

        3. 测试数据与模拟场景说明:
           - 标的: RXRX 现价 $3.835，行权价 $4.00 (OTM)，到期 45 天，市价权利金 $0.45。
           - 宏观三情景: 悲观 $2.00 (25%), 基准 $6.50 (50%), 乐观 $12.00 (25%)。

        4. 预期断言与结果验证:
           - 断言 moneyness_status 包含 'OTM'。
           - 断言 intrinsic_value == 0.0, time_value == 0.45, time_value_ratio == 1.0。
           - 断言 break_even_price 精确等于 4.45。
           - 断言 bear_payoff_per_share == -0.45 且 bear_return_pct == -100.0。
           - 断言 base_payoff_per_share 精确等于 2.05 (2.50 - 0.45)。
           - 断言 quarter_kelly_capital_pct <= 2.0% 且 > 0.0。
        """
        # 现价 $3.835，盘前 $3.89，行权价 $4.00，属于 OTM
        contract = OptionContractInput(
            underlying_ticker="RXRX",
            underlying_spot_price=3.835,
            spot_quote_timestamp="2026-10-14T06:00:00Z",
            market_session="pre_market",
            strike_price=4.00,
            option_type="call",
            days_to_expiration=45,
            market_premium=0.45,
        )

        res = OptionsCausalAnalyzer.analyze_option(
            contract,
            self.rxrx_scenarios,
            current_time_iso="2026-10-14T07:00:00Z",
        )

        # 1. 前项与中项推导断言
        self.assertIn("OTM", res.moneyness_status)
        self.assertEqual(res.intrinsic_value, 0.0)
        self.assertEqual(res.time_value, 0.45)
        self.assertEqual(res.time_value_ratio, 1.0)
        # 保本点 Break-Even = 4.00 + 0.45 = 4.45
        self.assertAlmostEqual(res.break_even_price, 4.45, places=2)
        # 必须上涨至少 (4.45 - 3.835) / 3.835 = +16.04%
        self.assertGreater(res.required_spot_move_pct, 15.0)
        self.assertIn("100%", res.zero_loss_risk_desc)

        # 2. 到期情景损益推导断言
        # 悲观到期 ($2.00): 行权价值为 0，净损失 -0.45 (100% 亏损)
        self.assertEqual(res.bear_payoff_per_share, -0.45)
        self.assertEqual(res.bear_return_pct, -100.0)
        # 基准到期 ($6.50): 行权价值 6.50 - 4.00 = 2.50，净利润 2.50 - 0.45 = +2.05
        self.assertAlmostEqual(res.base_payoff_per_share, 2.05, places=2)
        self.assertAlmostEqual(res.base_return_pct, 455.56, places=1)
        # 乐观到期 ($12.00): 行权价值 12.00 - 4.00 = 8.00，净利润 8.00 - 0.45 = +7.55
        self.assertAlmostEqual(res.bull_payoff_per_share, 7.55, places=2)

        # 3. 期望收益与凯利配置
        self.assertGreater(res.expected_profit_per_share, 0.0)
        # 期权配置严格限制在 <= 2.0% 总资金以内
        self.assertLessEqual(res.quarter_kelly_capital_pct, 2.0)
        self.assertGreater(res.quarter_kelly_capital_pct, 0.0)

    def test_stale_quote_raises_exception(self):
        """【UT-OPTION-02: 现货行情超期滞后物理阻断与时效硬约束拦截】

        1. 测试功能与测试点:
           - 验证期权定价引擎的行情时效硬约束: 严禁基于陈旧现货行情（>24小时）推导期权 Delta 与内在价值。
           - 当现货行情时间戳过时时，系统刚性抛出 ValueError 中断分析，防止投资人做出基于失真现货的错误对冲。

        2. 正常函数业务边界与参数契约:
           - spot_quote_timestamp 与 current_time_iso 时间差必须 <= 24 小时。

        3. 测试数据与模拟场景说明:
           - 当前系统分析时间为 2026-10-14T07:00:00Z。
           - 传入现货时间戳为 2026-10-10T00:00:00Z (相差 4 天超期滞后)。

        4. 预期断言与结果验证:
           - 断言抛出 ValueError，且异常详情中明确指出“行情时效硬约束阻断”。
        """
        stale_contract = OptionContractInput(
            underlying_ticker="RXRX",
            underlying_spot_price=4.36,
            spot_quote_timestamp="2026-10-10T00:00:00Z", # 4天前陈旧价格
            market_session="regular_trading",
            strike_price=4.00,
            option_type="call",
            days_to_expiration=45,
            market_premium=0.60,
        )

        with self.assertRaises(ValueError) as ctx:
            OptionsCausalAnalyzer.analyze_option(
                stale_contract,
                self.rxrx_scenarios,
                current_time_iso="2026-10-14T07:00:00Z",
            )
        self.assertIn("行情时效硬约束阻断", str(ctx.exception))

    def test_probability_conservation_check(self):
        """【UT-OPTION-03: 三情景概率守恒定理检验与非标概率阻断】

        1. 测试功能与测试点:
           - 验证宏观情景分布的柯尔莫哥洛夫公理概率守恒约束:
             P(bear) + P(base) + P(bull) 必须且仅恒等于 1.0。
           - 当分析师输入的情景概率之和不等于 1.0 时，引擎必须刚性抛出异常阻断。

        2. 正常函数业务边界与参数契约:
           - bear_prob + base_prob + bull_prob == 1.0 (容差 1e-6)。

        3. 测试数据与模拟场景说明:
           - 传入异常三情景概率: bear=0.3, base=0.3, bull=0.3 (总和为 0.9 != 1.0)。

        4. 预期断言与结果验证:
           - 断言 analyze_option 抛出 ValueError，且报错信息包含“情景概率之和必须等于 1.0”。
        """
        bad_scenarios = UnderlyingScenarios(
            bear_price=2.0, bear_prob=0.3,
            base_price=6.0, base_prob=0.3,
            bull_price=10.0, bull_prob=0.3, # 总和 0.9，违规
        )
        contract = OptionContractInput(
            underlying_ticker="TEST",
            underlying_spot_price=5.0,
            spot_quote_timestamp="2026-10-14T06:00:00Z",
            market_session="regular_trading",
            strike_price=5.0,
            option_type="call",
            days_to_expiration=30,
            market_premium=0.50,
        )
        with self.assertRaises(ValueError) as ctx:
            OptionsCausalAnalyzer.analyze_option(
                contract,
                bad_scenarios,
                current_time_iso="2026-10-14T07:00:00Z",
            )
        self.assertIn("情景概率之和必须等于 1.0", str(ctx.exception))

    def test_itm_call_option_analysis(self):
        """【UT-OPTION-04: 实值期权内在价值安全垫与时间价值剥离分析】

        1. 测试功能与测试点:
           - 验证实值看涨期权 (ITM Call) 的二元价值结构拆解:
             Intrinsic Value = Spot - Strike > 0；
             Time Value = Market Premium - Intrinsic Value。
           - 验证内在价值作为缓冲安全垫的度量。

        2. 正常函数业务边界与参数契约:
           - Underlying Spot > Strike。
           - Break-Even = Strike + Premium。

        3. 测试数据与模拟场景说明:
           - 标的: NVDA 现价 $132.00，行权价 $120.00 (深度实值 ITM)，到期 60 天，市价权利金 $18.00。
           - 拆解预期: 内在价值 $12.00 (132 - 120)，时间价值 $6.00 (18 - 12)，保本点 $138.00。

        4. 预期断言与结果验证:
           - 断言 moneyness_status 包含 'ITM'。
           - 断言 intrinsic_value == 12.0。
           - 断言 time_value == 6.0。
           - 断言 break_even_price 精确约为 138.0。
        """
        contract = OptionContractInput(
            underlying_ticker="NVDA",
            underlying_spot_price=132.00,
            spot_quote_timestamp="2026-10-14T06:00:00Z",
            market_session="pre_market",
            strike_price=120.00, # 实值
            option_type="call",
            days_to_expiration=60,
            market_premium=18.00,
        )
        scenarios = UnderlyingScenarios(
            bear_price=110.0, bear_prob=0.20,
            base_price=150.0, base_prob=0.60,
            bull_price=190.0, bull_prob=0.20,
        )
        res = OptionsCausalAnalyzer.analyze_option(
            contract,
            scenarios,
            current_time_iso="2026-10-14T07:00:00Z",
        )
        self.assertIn("ITM", res.moneyness_status)
        self.assertEqual(res.intrinsic_value, 12.0)
        self.assertEqual(res.time_value, 6.0)
        self.assertAlmostEqual(res.break_even_price, 138.0, places=1)

    def test_deep_itm_put_cushion_and_rebound_threshold(self):
        """【UT-OPTION-05: 深度实值看跌期权内在价值安全垫与反弹保本阈值因果推导】

        1. 测试功能与测试点:
           - 验证 OptionsCausalAnalyzer 针对深度实值看跌期权 (Deep ITM Put) 的因果链推导。
           - 标的物现价已低于保本点时 (Break-Even >= Spot)，判定标的已处于安全垫保护区间。
           - 验证语言与金融逻辑自洽性: 杜绝出现“需下跌至少 10% 方能保本”的语义倒错，正确表述为“允许反弹不超过 +X.X% 仍可保本”。
           - 验证内在价值与时间价值拆解 (Intrinsic Value = Strike - Spot > 0)。

        2. 正常函数业务边界与参数契约:
           - Underlying Spot < Strike 为 ITM Put。
           - Break-Even = Strike - Premium。
           - 当 Break-Even >= Spot 时，required_spot_move_pct >= 0。

        3. 测试数据与模拟场景说明:
           - 标的: 特斯拉 TSLA 现价 $210.00，看跌期权行权价 $250.00，到期 30 天，市价权利金 $32.00。
           - 保本点: $250.00 - $32.00 = $218.00。
           - 现价处于保本点下方：(218 - 210) / 210 = +3.81%，标的允许反弹高达 +3.81% 仍维持保本或盈利。
           - 宏观三情景: 悲观暴跌 $160 (30%), 基准震荡 $200 (50%), 乐观逼空 $270 (20%)。

        4. 预期断言与结果验证:
           - 断言 moneyness_status 包含 'ITM'。
           - 断言 intrinsic_value == 40.0 ($250 - $210)。
           - 断言 time_value == 0.0 (实值期权市价 $32 小于内在价值 $40 时下界钳制)。
           - 断言 break_even_price == 218.0。
           - 断言 rationale 中明确包含“反弹不超过”或“已处于安全垫区间”，杜绝“需进一步下跌”倒错。
        """
        contract = OptionContractInput(
            underlying_ticker="TSLA",
            underlying_spot_price=210.00,
            spot_quote_timestamp="2026-10-14T06:00:00Z",
            market_session="pre_market",
            strike_price=250.00,
            option_type="put",
            days_to_expiration=30,
            market_premium=32.00,
        )
        scenarios = UnderlyingScenarios(
            bear_price=160.0, bear_prob=0.30,
            base_price=200.0, base_prob=0.50,
            bull_price=270.0, bull_prob=0.20,
        )
        res = OptionsCausalAnalyzer.analyze_option(
            contract,
            scenarios,
            current_time_iso="2026-10-14T07:00:00Z",
        )
        self.assertIn("ITM", res.moneyness_status)
        self.assertEqual(res.intrinsic_value, 40.0)
        self.assertEqual(res.break_even_price, 218.0)
        self.assertGreaterEqual(res.required_spot_move_pct, 0.0)
        # 严密断言：语义中必须体现安全垫或允许反弹，杜绝倒错
        self.assertTrue(
            "安全垫" in res.rationale_zh or "反弹不超过" in res.rationale_zh,
            f"深度实值 Put 语义倒错，实际输出为: {res.rationale_zh}",
        )

    def test_atm_option_priority_order_branch(self):
        """【UT-OPTION-06: 平价 (ATM) 偏差 1.5% 优先命中判定断言】

        一、测试功能与测试点:
            验证平价判定分支顺序倒错修复：当现价微幅偏离行权价 (<= 1.5%) 时，
            系统必须优先判定为“平价 (ATM)”，严禁因微小溢价被提前错误拦截为“实值 (ITM)”。

        二、正常函数业务边界与参数契约:
            - 现价 100.8，行权价 100.0 (偏差 0.8% <= 1.5%)

        三、测试数据与模拟场景说明:
            测试微幅偏离行权价的看涨与看跌平价合约。

        四、预期断言与结果验证:
            断言 moneyness_status 包含 "平价 (ATM)"。
            断言 moneyness_status 严禁判定为 "实值 (ITM)"。
        """
        contract = OptionContractInput(
            underlying_ticker="ATM_STOCK",
            underlying_spot_price=100.8,
            spot_quote_timestamp="2026-10-14T06:00:00Z",
            market_session="regular_trading",
            strike_price=100.0,
            option_type="call",
            days_to_expiration=30,
            market_premium=4.0,
        )
        scenarios = UnderlyingScenarios(
            bear_price=80.0,
            bear_prob=0.30,
            base_price=105.0,
            base_prob=0.40,
            bull_price=130.0,
            bull_prob=0.30,
        )
        res = OptionsCausalAnalyzer.analyze_option(
            contract,
            scenarios,
            current_time_iso="2026-10-14T07:00:00Z",
        )
        self.assertIn("平价 (ATM", res.moneyness_status)
        self.assertNotIn("实值 (ITM", res.moneyness_status)

    def test_put_arbitrage_bound_exceeded_defense(self):
        """【UT-OPTION-07: 看跌期权买入权利金击穿行权价无套利边界防御断言】

        一、测试功能与测试点:
            验证金融数学无套利下界：当看跌期权买入权利金大于或等于行权价时 (p >= k)，
            即使标的归零亦无法保本，系统准确触发【极端无套利边界破损】警报与无法保本结论。

        二、正常函数业务边界与参数契约:
            - strike: 5.0, premium: 6.0 (p > k，违背无套利下界)

        三、测试数据与模拟场景说明:
            测试垃圾股高波动率下买方权利金严重畸高的极端场景。

        四、预期断言与结果验证:
            断言 zero_loss_risk_desc 包含 "极端无套利边界破损" 与 "严禁买入"。
        """
        contract = OptionContractInput(
            underlying_ticker="PENNY_PUT",
            underlying_spot_price=4.0,
            spot_quote_timestamp="2026-10-14T06:00:00Z",
            market_session="regular_trading",
            strike_price=5.0,
            option_type="put",
            days_to_expiration=15,
            market_premium=6.0,  # 权利金 6.0 > 行权价 5.0
        )
        scenarios = UnderlyingScenarios(
            bear_price=1.0,
            bear_prob=0.50,
            base_price=3.0,
            base_prob=0.30,
            bull_price=6.0,
            bull_prob=0.20,
        )
        res = OptionsCausalAnalyzer.analyze_option(
            contract,
            scenarios,
            current_time_iso="2026-10-14T07:00:00Z",
        )
        self.assertIn("极端无套利边界破损", res.zero_loss_risk_desc)
        self.assertIn("无法保本", res.rationale_zh)

    def test_facade_and_core_ssot_equivalence(self):
        """【UT-OPTION-08: 向下兼容中继门面 SSOT 完全等价性断言】

        一、测试功能与测试点:
            验证 `finance_tools.options_causal_analyzer` 中继门面与底层核心
            `financial_core.engines.options_causal_analyzer` 输出 100% 相同。

        二、正常函数业务边界与参数契约:
            - Facade 与 Core 传入相同输入。

        三、测试数据与模拟场景说明:
            测试标准期权分析场景。

        四、预期断言与结果验证:
            断言门面与核心输出属性完全一致。
        """
        from financial_core.engines.options_causal_analyzer import (
            OptionContractInput as CoreContractInput,
            UnderlyingScenarios as CoreScenarios,
            OptionsCausalAnalyzer as CoreOptionsCausalAnalyzer,
        )
        c_core = CoreContractInput("TEST", 50.0, "2026-10-14T06:00:00Z", "regular_trading", 50.0, "call", 30, 2.5)
        c_facade = OptionContractInput("TEST", 50.0, "2026-10-14T06:00:00Z", "regular_trading", 50.0, "call", 30, 2.5)
        s_core = CoreScenarios(35.0, 0.25, 55.0, 0.50, 75.0, 0.25)
        s_facade = UnderlyingScenarios(35.0, 0.25, 55.0, 0.50, 75.0, 0.25)

        res_core = CoreOptionsCausalAnalyzer.analyze_option(c_core, s_core, current_time_iso="2026-10-14T07:00:00Z")
        res_facade = OptionsCausalAnalyzer.analyze_option(c_facade, s_facade, current_time_iso="2026-10-14T07:00:00Z")

        self.assertEqual(res_core.moneyness_status, res_facade.moneyness_status)
        self.assertEqual(res_core.expected_return_pct, res_facade.expected_return_pct)
        self.assertEqual(res_core.verdict, res_facade.verdict)
        self.assertEqual(res_core.rationale_zh, res_facade.rationale_zh)

    def test_ut_option_09_negative_bull_payoff_language_consistency(self):
        """【UT-OPTION-09: 乐观情景期权仍亏损时语言因果自洽性断言】

        一、测试功能与测试点:
            验证当标的即使在最乐观情景下仍未越过行权价与保本点、导致乐观情景期权收益为负 (bull_ret <= 0) 时，
            引擎严禁出现“虽然乐观情景有较高弹性 (-100.0%)”的荒谬语病与逻辑倒错，
            必须准确自洽输出“即使在乐观情景下仍无法越过保本门槛导致本金折损”。

        二、正常函数业务边界与参数契约:
            - 深度虚值期权 (Strike $10.00, Premium $1.00, 现价 $3.00)
            - 乐观情景最高预期价格仅为 $7.00 (< Strike $10.00)
            - 导致 bear, base, bull 三情景到期行权价值均为 0，收益率均为 -100.0%

        三、测试数据与模拟场景说明:
            测试极度虚值彩票型期权在标的缺乏极端上行动力下的风控严惩。

        四、预期断言与结果验证:
            断言 bull_return_pct == -100.0。
            断言 rationale_zh 绝不包含“较高弹性”。
            断言 rationale_zh 包含“即使在乐观情景下仍无法越过保本门槛导致本金折损”。
        """
        contract = OptionContractInput(
            underlying_ticker="DEEP_OTM",
            underlying_spot_price=3.0,
            spot_quote_timestamp="2026-10-14T06:00:00Z",
            market_session="regular_trading",
            strike_price=10.0,
            option_type="call",
            days_to_expiration=30,
            market_premium=1.0,
        )
        scenarios = UnderlyingScenarios(
            bear_price=2.0, bear_prob=0.30,
            base_price=4.0, base_prob=0.50,
            bull_price=7.0, bull_prob=0.20, # 乐观情景 7.0 仍 < 行权价 10.0
        )
        res = OptionsCausalAnalyzer.analyze_option(
            contract,
            scenarios,
            current_time_iso="2026-10-14T07:00:00Z",
        )
        self.assertEqual(res.bull_return_pct, -100.0)
        self.assertNotIn("较高弹性", res.rationale_zh)
        self.assertIn("即使在乐观情景下仍无法越过保本门槛导致本金折损", res.rationale_zh)
        self.assertIn("严禁买入", res.verdict)

    def test_ut_option_10_narrative_zh_and_buyer_verdict_card_contract(self):
        """【UT-OPTION-10: 期权因果买方全息研报卡片 narrative_zh 与去工程符号化契约断言】

        一、测试功能与测试点:
            1. 验证 OptionAnalysisResult 包含标准 narrative_zh 买方全息研报卡片；
            2. 验证卡片通俗整合标的现价、行情新鲜度、合约类型、保本平衡点、胜率赔率与凯利资金配置上限；
            3. 验证 verdict_zh 提供纯自然中文决策判定（如 '严禁买入 (负期望彩票型期权)'、'高赔率非对称买入'）；
            4. 验证 to_dict() 契约能够完整输出 narrative_zh 与 verdict_zh。

        二、正常函数业务边界与参数契约:
            - analyze_option 返回合法结果实体

        三、测试数据与模拟场景说明:
            测试标准期权分析场景。

        四、预期断言与结果验证:
            断言 narrative_zh 包含“【标的 RXRX 期权因果全息研报】”；
            断言 verdict_zh 非空且为中文；
            断言 to_dict() 字典中包含 narrative_zh 与 verdict_zh。
        """
        contract = OptionContractInput(
            underlying_ticker="RXRX",
            underlying_spot_price=3.835,
            spot_quote_timestamp="2026-10-14T06:00:00Z",
            market_session="pre_market",
            strike_price=4.00,
            option_type="call",
            days_to_expiration=45,
            market_premium=0.45,
        )
        res = OptionsCausalAnalyzer.analyze_option(
            contract,
            self.rxrx_scenarios,
            current_time_iso="2026-10-14T07:00:00Z",
        )
        self.assertIn("期权因果全息研报", res.narrative_zh)
        self.assertIn("保本平衡点", res.narrative_zh)
        self.assertIn("买方风控与决策判定", res.narrative_zh)
        self.assertTrue(bool(res.verdict_zh))
        # 严密断言：彻底杜绝纯英文代码代号暴露与机械重复语病
        self.assertNotIn("Speculative OTM", res.verdict)
        self.assertNotIn("Lottery Bet", res.verdict)
        self.assertNotIn("Negative Expected Value", res.verdict)
        self.assertNotIn("(+", res.narrative_zh) # 杜绝类似 上涨至少 8.7% (+8.7%) 冗余符号拼贴

        d = res.to_dict()
        self.assertIn("narrative_zh", d)
        self.assertEqual(d["narrative_zh"], res.narrative_zh)
        self.assertIn("verdict_zh", d["decision_and_allocation"])


if __name__ == "__main__":
    unittest.main()
