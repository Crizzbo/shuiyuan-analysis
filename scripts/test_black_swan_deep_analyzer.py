"""黑天鹅深度分析引擎与用户持仓穿透回归测试 (Test Black Swan Deep Analyzer).

覆盖范围:
1. 宏观急性黑天鹅流动性踩踏状态机映射 (MacroRegimeState);
2. 针对 SpaceX (物理垄断)、Cerebras (算力大客户集中)、Recursion (研发失血) 三大典型标的的微观血肉穿透分类;
3. 物理垄断资产“流动性提款机 (ATM Effect)”错杀识别与防割肉指令断言;
4. 算力周期大客户依赖资产的高估值削减与严禁抄底指令断言;
5. 大资金避险路径结构化输出完备性与自然语言买方兵法断言。
"""

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.black_swan_deep_analyzer import (
    BlackSwanDeepAnalyzer,
    HoldingAssetSpec,
    BlackSwanAnalysisResult,
)
from finance_tools.black_swan_deep_analyzer import (
    BlackSwanDeepAnalyzer as FacadeBlackSwanDeepAnalyzer,
    HoldingAssetSpec as FacadeHoldingAssetSpec,
    BlackSwanAnalysisResult as FacadeBlackSwanAnalysisResult,
)
from financial_core.engines.macro_shock_transmission_engine import (
    MacroRegimeState,
    AssetMicroVulnerabilityType,
    MACRO_SHOCK_STATE_REGISTRY,
    get_macro_state_metadata,
)
from financial_core.engines.macro_elastic_margin_engine import MacroLiquidityState


class TestBlackSwanDeepAnalyzer(unittest.TestCase):
    """测试黑天鹅深度分析引擎与持仓穿透."""

    def setUp(self):
        self.analyzer = BlackSwanDeepAnalyzer()

        # 模拟当前 2026 年 10 月末/ 11 月初的实际黑天鹅宏观环境:
        # 美债 10Y-2Y 倒挂结束并走阔至 25bps，净流动性收紧至 5.3 万亿，VIX 飙升至 28.5，做市商负 Gamma
        self.black_swan_macro = MacroLiquidityState(
            fed_net_liquidity_trillion=5.35,
            term_spread_10y_2y_bps=22.0,
            vix_index=28.5,
            market_gex_billion=-1.8,
        )

        # 准备用户手头的 3 大代表性持仓标的
        self.holdings = [
            HoldingAssetSpec(
                ticker="SPCX",
                company_name_zh="SpaceX (太空探索技术公司)",
                current_price=136.50,
                market_session="pre_market",
                beta=1.35,
                debt_to_equity=0.25,
                base_wacc=0.085,
                months_cash_runway=48.0,
                top_5_customer_share=0.35,
                has_monopoly_moat=True,
                core_investment_thesis="全球商业运力绝对垄断，星链现金流全面转正，背靠 NASA 刚性防务订单",
            ),
            HoldingAssetSpec(
                ticker="CBRS",
                company_name_zh="Cerebras Systems (晶圆级算力芯片)",
                current_price=108.77,
                market_session="pre_market",
                beta=2.20,
                debt_to_equity=0.60,
                base_wacc=0.105,
                months_cash_runway=16.0,
                top_5_customer_share=0.82,  # 80%+ 依赖阿联酋 G42，极度脆弱
                has_monopoly_moat=False,
                core_investment_thesis="WSE-3 性能卓越，但下游资本开支收缩且高度依赖单一外资大客户",
            ),
            HoldingAssetSpec(
                ticker="RXRX",
                company_name_zh="Recursion Pharmaceuticals (AI制药)",
                current_price=4.03,
                market_session="pre_market",
                beta=1.95,
                debt_to_equity=0.10,
                base_wacc=0.115,
                months_cash_runway=14.0,  # 研发烧钱持续消耗营运资金
                top_5_customer_share=0.40,
                has_monopoly_moat=False,
                core_investment_thesis="英伟达生态 AI 药筛平台，纯研发高贝塔高久期，无商业化净利润",
            ),
        ]

    def test_01_macro_regime_and_margin_expansion(self):
        """【IT-BLACKSWAN-01: 宏观黑天鹅急性流动性踩踏状态机映射与弹性安全边际扩张】

        1. 测试功能与测试点:
           - 验证 BlackSwanDeepAnalyzer.analyze_event 对黑天鹅宏观冲击状态的精准推导。
           - 状态机识别: 当美联储净流动性紧缩、日元急升触发全球套息平仓、VIX 飙升至恐慌高位时，精准判定为去杠杆压力 (DELEVERAGING_PRESSURE) 或急性流动性危机 (ACUTE_LIQUIDITY_CRUNCH)。
           - 严重级别评级: 宏观冲击烈度 macro_severity_level >= 3。
           - 弹性安全边际 (Elastic Margin of Safety): 黑天鹅时期买点折价率必须大幅扩张 (required_elastic_margin_pct > 25.0%)。
           - 大资金避险路径 (Capital Flight Destinations): 必须覆盖现金超短债、黄金硬通货与高股息公用事业三大防御支柱。

        2. 正常函数业务边界与参数契约:
           - macro_state: MacroLiquidityState 包含净流动性、期限利差、VIX 与 GEX Gamma 暴露。
           - usdjpy_daily_change_pct: 日元汇率单日波动 (例如 -2.2% 表示日元暴涨)。
           - fed_liquidity_drain_billion: 美联储单周抽水规模。

        3. 测试数据与模拟场景说明:
           - 模拟 2026 年底典型黑天鹅环境: 美债 10Y-2Y 倒挂结束走阔至 22bps，美联储净流动性收紧至 5.35 万亿，VIX 飙升至 28.5，做市商 GEX 为深负 -1.8B，日元单日跳涨 2.2%。

        4. 预期断言与结果验证:
           - 断言 macro_regime 属于 DELEVERAGING_PRESSURE 或 ACUTE_LIQUIDITY_CRUNCH。
           - 断言 macro_severity_level >= 3。
           - 断言 required_elastic_margin_pct > 25.0%。
           - 断言 capital_flight_destinations 长度为 3 且涵盖三类避险资产。
        """
        result = self.analyzer.analyze_event(
            macro_state=self.black_swan_macro,
            usdjpy_daily_change_pct=-0.022,  # 日元急升 2.2% 触发套息平仓
            fed_liquidity_drain_billion=60.0,
            holdings=self.holdings,
            as_of_date="2026-11-03",
        )

        self.assertIsInstance(result, BlackSwanAnalysisResult)
        self.assertEqual(result.as_of_date, "2026-11-03")

        # 1. 宏观环境必须识别为去杠杆或黑天鹅紧缩状态
        self.assertIn(result.macro_regime, ["DELEVERAGING_PRESSURE", "ACUTE_LIQUIDITY_CRUNCH"])
        self.assertGreaterEqual(result.macro_severity_level, 3)
        self.assertGreater(result.required_elastic_margin_pct, 25.0, "黑天鹅时期弹性安全边际必须大幅扩张")

        # 2. 校验大资金避险去向三大支柱完备性
        self.assertEqual(len(result.capital_flight_destinations), 3)
        dest_categories = [d["category"] for d in result.capital_flight_destinations]
        self.assertTrue(any("现金" in cat or "超短债" in cat for cat in dest_categories))
        self.assertTrue(any("黄金" in cat or "硬通货" in cat for cat in dest_categories))
        self.assertTrue(any("现金牛" in cat or "传统" in cat for cat in dest_categories))

    def test_02_physical_monopoly_atm_effect_dissection(self):
        """【UT-BLACKSWAN-02: 物理垄断资产“流动性提款机 (ATM Effect)”错杀识别与防割肉指令】

        1. 测试功能与测试点:
           - 验证法证诊断对具有“物理垄断护城河 + 充沛现金跑道”资产（如 SpaceX SPCX）的辨识。
           - 错杀机制 (ATM Liquidity Victim): 机构在对冲基金爆仓与保证金追缴时，由于垃圾资产缺乏流动性，被迫优先抛售流动性极佳的高质量硬通货资产变现救命，造成非理性暴跌。
           - 战术指令: 系统严禁发出任何恐慌止损建议，强制发出“坚决不割肉 / 逢极端错杀按兵不动或分批逆势布局”的买方指令。

        2. 正常函数业务边界与参数契约:
           - has_monopoly_moat=True, months_cash_runway >= 36.0, debt_to_equity 低。

        3. 测试数据与模拟场景说明:
           - 标的: SpaceX (SPCX)，具备全球发射运力物理垄断，现金跑道 48 个月，负债率仅 0.25。

        4. 预期断言与结果验证:
           - 断言 micro_vulnerability_type 精确等于 MOATED_PHYSICAL_MONOPOLY。
           - 断言 is_atm_liquidity_victim 为 True。
           - 断言 tactical_directive_zh 包含“坚决不割肉”。
        """
        result = self.analyzer.analyze_event(
            macro_state=self.black_swan_macro,
            usdjpy_daily_change_pct=-0.022,
            fed_liquidity_drain_billion=60.0,
            holdings=[self.holdings[0]],  # 仅测试 SpaceX
            as_of_date="2026-11-03",
        )
        diag = result.holdings_diagnostics[0]
        self.assertEqual(diag["ticker"], "SPCX")
        self.assertEqual(diag["micro_vulnerability_type"], AssetMicroVulnerabilityType.MOATED_PHYSICAL_MONOPOLY.value)
        self.assertTrue(diag["is_atm_liquidity_victim"], "SpaceX 必须被识别为流动性提款机错杀标的")
        self.assertIn("坚决不割肉", diag["tactical_directive_zh"])

    def test_03_fragile_assets_haircut_and_bottom_fishing_ban(self):
        """【UT-BLACKSWAN-03: 算力大客户集中与研发长久期烧钱资产估值深度折价及抄底禁令】

        1. 测试功能与测试点:
           - 验证在黑天鹅流动性收紧情景下，针对两类高危微观体质资产的惩罚性估值折价 (Valuation Haircut):
             A) 算力大客户集中脆弱资产 (Cerebras CBRS): 前五大客户集中度 > 80%，施加 >20% 的硬性估值扣减；
             B) 研发烧钱长久期无盈利资产 (Recursion RXRX): 现金跑道短、无商业化正利润，久期极度敏感。
           - 战术风控硬指令: 严禁将表面的股价暴跌误判为低估机会，强制下达“绝不盲目抄底”与“严禁逢低盲目补仓”的纪律约束。

        2. 正常函数业务边界与参数契约:
           - 大客户集中度 top_5_customer_share > 0.80。
           - 研发期现金跑道 months_cash_runway < 24.0。

        3. 测试数据与模拟场景说明:
           - 标的 CBRS: 82% 收入依赖阿联酋单一客户，高 Beta 2.2。
           - 标的 RXRX: 研发失血，跑道仅 14 个月，Beta 1.95。

        4. 预期断言与结果验证:
           - CBRS 断言 valuation_haircut_pct > 20.0 且指令包含“绝不盲目抄底”。
           - RXRX 断言 micro_vulnerability_type 为 CASH_BURN_LONG_DURATION 且指令包含“严禁逢低盲目补仓”。
           - 断言全案战术兵法摘要 tactical_playbook_summary 包含宏观防守反击策略。
        """
        fragile_holdings = [self.holdings[1], self.holdings[2]]
        result = self.analyzer.analyze_event(
            macro_state=self.black_swan_macro,
            usdjpy_daily_change_pct=-0.022,
            fed_liquidity_drain_billion=60.0,
            holdings=fragile_holdings,
            as_of_date="2026-11-03",
        )
        diag_cbrs = result.holdings_diagnostics[0]
        self.assertEqual(diag_cbrs["ticker"], "CBRS")
        self.assertEqual(diag_cbrs["micro_vulnerability_type"], AssetMicroVulnerabilityType.CAPEX_CYCLICAL_CONCENTRATED.value)
        self.assertFalse(diag_cbrs["is_atm_liquidity_victim"])
        self.assertGreater(diag_cbrs["valuation_haircut_pct"], 20.0, "大客户脆弱资产估值折让必须超过 20%")
        self.assertIn("绝不盲目抄底", diag_cbrs["tactical_directive_zh"])

        diag_rxrx = result.holdings_diagnostics[1]
        self.assertEqual(diag_rxrx["ticker"], "RXRX")
        self.assertEqual(diag_rxrx["micro_vulnerability_type"], AssetMicroVulnerabilityType.CASH_BURN_LONG_DURATION.value)
        self.assertIn("严禁逢低盲目补仓", diag_rxrx["tactical_directive_zh"])

        # 战术兵法总结
        self.assertIn("宏观黑天鹅防守反击策略", result.tactical_playbook_summary)

    def test_04_dynamic_tactical_playbook_no_hardcoded_fake_tickers(self):
        """【UT-BLACKSWAN-04: 动态持仓买方战术兵法提炼与杜绝硬编码假标的断言】

        一、测试功能与测试点:
            验证在传入与历史测试标的完全无关的全新持仓组合（如 AAPL, MSFT）时，
            系统战术操盘兵法摘要 tactical_playbook_summary 必须根据当前真实持仓动态聚合提炼，
            彻底杜绝在报告中凭空冒出未持有的硬编码假标的 (如 SpaceX、CBRS、RXRX)。

        二、正常函数业务边界与参数契约:
            - holdings 传入全新的两只标的: AAPL (稳健提款机错杀护城河), TECH_RISK (大客户集中脆弱)
            - 验证 tactical_playbook_summary 的文本动态契约

        三、测试数据与模拟场景说明:
            测试一组全新资产组合，检验动态文本聚合器的自适应性与真实业务自洽性。

        四、预期断言与结果验证:
            断言战术摘要中必须包含当前持仓的代码 AAPL 或 TECH_RISK，
            严禁出现 "SpaceX"、"CBRS"、"RXRX" 等历史硬编码假标的。
        """
        custom_holdings = [
            HoldingAssetSpec(
                ticker="AAPL",
                company_name_zh="苹果公司",
                current_price=230.0,
                market_session="regular_trading",
                beta=1.05,
                debt_to_equity=0.40,
                base_wacc=0.075,
                months_cash_runway=60.0,
                top_5_customer_share=0.10,
                has_monopoly_moat=True,
                core_investment_thesis="全球顶级软硬件闭环护城河",
            ),
            HoldingAssetSpec(
                ticker="TECH_RISK",
                company_name_zh="某高危大客户依赖芯片公司",
                current_price=50.0,
                market_session="regular_trading",
                beta=2.10,
                debt_to_equity=0.50,
                base_wacc=0.10,
                months_cash_runway=12.0,
                top_5_customer_share=0.85,
                has_monopoly_moat=False,
                core_investment_thesis="高度依赖单一客户，砍单风险高",
            ),
        ]

        result = self.analyzer.analyze_event(
            macro_state=self.black_swan_macro,
            usdjpy_daily_change_pct=-0.02,
            fed_liquidity_drain_billion=50.0,
            holdings=custom_holdings,
            as_of_date="2026-11-03",
        )

        summary = result.tactical_playbook_summary
        # 绝不能出现硬编码假标的
        self.assertNotIn("SpaceX", summary)
        self.assertNotIn("CBRS", summary)
        self.assertNotIn("RXRX", summary)
        # 必须动态包含实际持仓标的建议
        self.assertTrue("AAPL" in summary or "TECH_RISK" in summary)

    def test_05_all_robust_holdings_playbook_consistency(self):
        """【UT-BLACKSWAN-05: 组合全稳健资产下的全案战术兵法安抚与自洽性断言】

        一、测试功能与测试点:
            验证当用户持仓均为低负债、高现金、无大客户集中度的全稳健防御资产时，
            系统战术兵法能够自洽输出整体稳健持有建议，不无病呻吟或发出错误斩仓警告。

        二、正常函数业务边界与参数契约:
            - 所有持仓的 beta 低、负债低、无流动性错杀，财务极度安全

        三、测试数据与模拟场景说明:
            测试全稳健公用事业/红利防守标的。

        四、预期断言与结果验证:
            断言战术兵法包含“持仓整体财务稳健”或“资产负债表与现金造血能力优异”。
        """
        safe_holdings = [
            HoldingAssetSpec(
                ticker="DEF_UTILITY",
                company_name_zh="防御性公用事业",
                current_price=100.0,
                market_session="regular_trading",
                beta=0.45,
                debt_to_equity=0.30,
                base_wacc=0.065,
                months_cash_runway=100.0,
                top_5_customer_share=0.05,
                has_monopoly_moat=False,
                core_investment_thesis="高股息防御特许经营权",
            )
        ]

        result = self.analyzer.analyze_event(
            macro_state=self.black_swan_macro,
            usdjpy_daily_change_pct=-0.01,
            fed_liquidity_drain_billion=20.0,
            holdings=safe_holdings,
            as_of_date="2026-11-03",
        )

        self.assertIn("持仓整体财务稳健", result.tactical_playbook_summary)

    def test_06_customer_and_runway_risk_filtering_regression(self):
        """【UT-BLACKSWAN-06: 大客户集中与烧钱跑道微观脆弱性战术兵法精准捕获回归断言】

        一、测试功能与测试点:
            回归验证：彻底根除旧代码中因在 `micro_vulnerability_type` 中匹配不存在的 `"CUSTOMER"`
            与 `"RUNWAY"` 子串导致大客户集中与短跑道失血标的在战术兵法中 100% 漏报的重大 Bug。
            断言当持仓中仅有大客户依赖公司时，战术兵法必须精准包含“下游大客户高集中度标的”；
            当持仓中仅有失血研发公司时，战术兵法必须精准包含“现金跑道紧缩/长久期无造血标的”。

        二、正常函数业务边界与参数契约:
            - 单独测试大客户高集中标的（CBRS，集中度 82%）
            - 单独测试现金跑道紧张标的（RXRX，跑道 14 个月）

        三、测试数据与模拟场景说明:
            测试隔离场景，确保不会被其他标的掩盖逻辑缺陷。

        四、预期断言与结果验证:
            断言 CBRS 独立触发“下游大客户高集中度标的（CBRS）”。
            断言 RXRX 独立触发“现金跑道紧缩/长久期无造血标的（RXRX）”。
        """
        # 1. 仅大客户依赖标的
        res_cust = self.analyzer.analyze_event(
            macro_state=self.black_swan_macro,
            usdjpy_daily_change_pct=-0.02,
            fed_liquidity_drain_billion=40.0,
            holdings=[self.holdings[1]],  # CBRS
            as_of_date="2026-11-03",
        )
        self.assertIn("下游大客户高集中度标的（CBRS）", res_cust.tactical_playbook_summary)
        self.assertNotIn("持仓整体财务稳健", res_cust.tactical_playbook_summary)

        # 2. 仅现金跑道失血标的
        res_runway = self.analyzer.analyze_event(
            macro_state=self.black_swan_macro,
            usdjpy_daily_change_pct=-0.02,
            fed_liquidity_drain_billion=40.0,
            holdings=[self.holdings[2]],  # RXRX
            as_of_date="2026-11-03",
        )
        self.assertIn("现金跑道紧缩/长久期无造血标的（RXRX）", res_runway.tactical_playbook_summary)
        self.assertNotIn("持仓整体财务稳健", res_runway.tactical_playbook_summary)

    def test_07_buyer_dossier_card_and_to_dict_contract(self):
        """【UT-BLACKSWAN-07: 黑天鹅深度分析买方全息研报卡片与 to_dict 序列化契约断言】

        一、测试功能与测试点:
            1. 验证 BlackSwanAnalysisResult 包含标准 narrative_zh 买方全息研报卡片；
            2. 验证卡片通俗整合宏观流动性烈度、套息平仓压力、避险路径与战术兵法；
            3. 验证 holdings_diagnostics 中每个标的包含自然中文画像 micro_vulnerability_name_zh 与 leverage_vulnerability_tier_zh；
            4. 验证 to_dict() 契约能够完整输出字典化数据。

        二、正常函数业务边界与参数契约:
            - analyze_event 返回标准实体。

        三、测试数据与模拟场景说明:
            测试标准持仓组合。

        四、预期断言与结果验证:
            断言 narrative_zh 包含“【宏观黑天鹅巨震与持仓微观穿透全息研报】”。
            断言 to_dict() 包含 narrative_zh 与 holdings_diagnostics。
        """
        res = self.analyzer.analyze_event(
            macro_state=self.black_swan_macro,
            usdjpy_daily_change_pct=-0.02,
            fed_liquidity_drain_billion=50.0,
            holdings=self.holdings,
            as_of_date="2026-11-03",
        )

        self.assertIn("宏观黑天鹅巨震与持仓微观穿透全息研报", res.narrative_zh)
        self.assertIn("宏观流动性烈度", res.narrative_zh)
        self.assertIn("大资金避险迁徙路径", res.narrative_zh)
        self.assertIn("操盘战术兵法指令", res.narrative_zh)

        diag0 = res.holdings_diagnostics[0]
        self.assertIn("micro_vulnerability_name_zh", diag0)
        self.assertEqual(diag0["micro_vulnerability_name_zh"], "物理垄断硬资产")
        self.assertIn("leverage_vulnerability_tier_zh", diag0)

        d = res.to_dict()
        self.assertEqual(d["as_of_date"], "2026-11-03")
        self.assertIn("narrative_zh", d)
        self.assertIn("holdings_diagnostics", d)
        self.assertEqual(d["narrative_zh"], res.narrative_zh)

    def test_08_facade_and_core_ssot_equivalence(self):
        """【UT-BLACKSWAN-08: 向下兼容中继门面 SSOT 完全等价性断言】

        一、测试功能与测试点:
            验证 `finance_tools.black_swan_deep_analyzer` 中继门面与底层核心
            `financial_core.engines.black_swan_deep_analyzer` 运算输出 100% 相同。

        二、正常函数业务边界与参数契约:
            - Facade 与 Core 传入相同输入。

        三、测试数据与模拟场景说明:
            测试标准持仓。

        四、预期断言与结果验证:
            断言门面与核心输出属性完全一致。
        """
        analyzer_core = BlackSwanDeepAnalyzer()
        analyzer_facade = FacadeBlackSwanDeepAnalyzer()

        res_core = analyzer_core.analyze_event(
            macro_state=self.black_swan_macro,
            usdjpy_daily_change_pct=-0.015,
            fed_liquidity_drain_billion=30.0,
            holdings=self.holdings,
            as_of_date="2026-11-03",
        )
        res_facade = analyzer_facade.analyze_event(
            macro_state=self.black_swan_macro,
            usdjpy_daily_change_pct=-0.015,
            fed_liquidity_drain_billion=30.0,
            holdings=self.holdings,
            as_of_date="2026-11-03",
        )

        self.assertEqual(res_core.macro_regime, res_facade.macro_regime)
        self.assertEqual(res_core.carry_trade_stress_score, res_facade.carry_trade_stress_score)
        self.assertEqual(res_core.tactical_playbook_summary, res_facade.tactical_playbook_summary)
        self.assertEqual(res_core.narrative_zh, res_facade.narrative_zh)


if __name__ == "__main__":
    unittest.main()
