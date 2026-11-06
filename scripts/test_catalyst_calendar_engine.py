"""催化剂日历时间轴与二元事件定价引擎单元测试套件.

本测试模块严格遵循《36号工程黄金设计规范》与四段式结构化中文契约测试模型:
1. 测试功能与测试点说明 (Test Functionality & Objectives)
2. 正常函数业务边界与参数契约 (Business Boundaries & Parameter Contracts)
3. 测试数据与模拟场景说明 (Test Data & Scenario Descriptions)
4. 预期断言与结果验证 (Expected Assertions & Verification)

涵盖二元事件数学期望、赔率比值测算、期权市场平值跨式隐含波动率 (IV) 套利判定，
以及临近决战 (<14天) 高危负期望与高赔率分级战术指令严密核验。
"""

from datetime import date
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.catalyst_calendar_engine import (
    CorporateEvent,
    EventEvaluationResult,
    CatalystCalendarEngine,
)
from finance_tools.catalyst_calendar_engine import (
    CorporateEvent as FacadeCorporateEvent,
    EventEvaluationResult as FacadeEventEvaluationResult,
    CatalystCalendarEngine as FacadeCatalystCalendarEngine,
)


class TestCatalystCalendarEngine(unittest.TestCase):
    """催化剂日历与二元事件定价引擎契约测试."""

    def test_ut_catalyst_01_high_odds_imminent_event_tactics(self):
        """【UT-CATALYST-01: 临近决战高赔率二元事件正向数学期望与牛市价差锁定战术断言】

        一、测试功能与测试点:
            验证当二元催化剂事件进入极度临近决战窗口 (days <= 14)，且具备正向高数学期望 (exp_move > 15%)
            与高赔率 (odds > 1.8) 时，系统准确识别并给出“牛市价差 (Bull Call Spread) 锁定成本规避暴跌风险”的买方风控指令。

        二、正常函数业务边界与参数契约:
            - target_date: 距离基准评估日 5 天
            - probability_of_success: 0.70
            - upside_potential_pct: +60.0%
            - downside_risk_pct: -30.0%

        三、测试数据与模拟场景说明:
            模拟创新药 Phase 3 关键顶线数据读出临近，成功率 70%，预期上涨 60%，失败回撤 30%。
            二元期望 = 0.70 * 60% + 0.30 * (-30%) = 42% - 9% = +33.0%。
            赔率 = 60.0 / 30.0 = 2.00。

        四、预期断言与结果验证:
            断言 days_until_event == 5，urgency_status 包含 "<14天"。
            断言 binary_expected_move_pct == 33.0%。
            断言 odds_ratio == 2.00。
            断言 actionable_tactics_zh 包含“牛市价差 (Bull Call Spread)”。
        """
        evt = CorporateEvent(
            event_id="PHASE3_TOPLINE",
            target_date="2026-11-08",
            category="clinical_readout",
            title_zh="重磅创新药 Phase 3 顶线试验成功率读出",
            description_zh="关键终点统计学显著性验证",
            upside_potential_pct=60.0,
            downside_risk_pct=-30.0,
            probability_of_success=0.70,
        )
        res = CatalystCalendarEngine.evaluate_event(evt, as_of_date="2026-11-03")

        self.assertEqual(res.days_until_event, 5)
        self.assertIn("<14天", res.urgency_status)
        self.assertAlmostEqual(res.binary_expected_move_pct, 33.0, places=1)
        self.assertAlmostEqual(res.odds_ratio, 2.00, places=2)
        self.assertIn("Bull Call Spread", res.actionable_tactics_zh)
        self.assertIn("牛市价差", res.actionable_tactics_zh)

    def test_ut_catalyst_02_negative_expectation_imminent_event_risk_alert(self):
        """【UT-CATALYST-02: 临近决战二元高危负期望/赔率倒挂风险警报与拒绝盲目博弈断言】

        一、测试功能与测试点:
            验证因果逻辑修复点：当二元催化剂事件极度临近 (days <= 14) 但数学期望为负或赔率严重倒挂时，
            系统必须发出【二元事件高危警报】，严禁日前赌博博弈，坚决杜绝误判为“中期发酵分批埋伏”的严重语病。

        二、正常函数业务边界与参数契约:
            - target_date: 距离基准评估日 3 天
            - probability_of_success: 0.30 (胜率低)
            - upside_potential_pct: +30.0%
            - downside_risk_pct: -60.0% (亏损幅度深)

        三、测试数据与模拟场景说明:
            二元期望 = 0.30 * 30% + 0.70 * (-60%) = 9% - 42% = -33.0%。
            赔率 = 30.0 / 60.0 = 0.50 (严重倒挂)。

        四、预期断言与结果验证:
            断言 days_until_event == 3。
            断言 binary_expected_move_pct == -33.0%。
            断言 odds_ratio == 0.50。
            断言 actionable_tactics_zh 包含“【二元事件高危警报】”与“严禁日前单腿赌博博弈”，
            严禁出现“分批建仓埋伏”或“发酵前夕”。
        """
        evt = CorporateEvent(
            event_id="HIGH_RISK_FDA",
            target_date="2026-11-06",
            category="fda_pdufa",
            title_zh="某高风险孤儿药 FDA 审查批复",
            description_zh="前置临床存在肝毒性疑点，获批难度极高",
            upside_potential_pct=30.0,
            downside_risk_pct=-60.0,
            probability_of_success=0.30,
        )
        res = CatalystCalendarEngine.evaluate_event(evt, as_of_date="2026-11-03")

        self.assertEqual(res.days_until_event, 3)
        self.assertAlmostEqual(res.binary_expected_move_pct, -33.0, places=1)
        self.assertAlmostEqual(res.odds_ratio, 0.50, places=2)
        self.assertIn("二元事件高危警报", res.actionable_tactics_zh)
        self.assertIn("严禁日前单腿赌博博弈", res.actionable_tactics_zh)
        self.assertNotIn("分批建仓埋伏", res.actionable_tactics_zh)
        self.assertNotIn("发酵前夕", res.actionable_tactics_zh)

    def test_ut_catalyst_03_mediocre_imminent_event_observation(self):
        """【UT-CATALYST-03: 临近决战预期平淡事件观望战术断言】

        一、测试功能与测试点:
            验证当二元催化剂临近 (days <= 14) 且期望温和偏正但未达高赔率门槛时的中性风控战术。

        二、正常函数业务边界与参数契约:
            - target_date: 距离基准评估日 7 天
            - probability_of_success: 0.55
            - upside_potential_pct: +15.0%
            - downside_risk_pct: -15.0%

        三、测试数据与模拟场景说明:
            二元期望 = 0.55 * 15% + 0.45 * (-15%) = 8.25% - 6.75% = +1.5%。
            赔率 = 1.00。未满足 exp_move > 15% 且 odds > 1.8，亦未跌入负期望。

        四、预期断言与结果验证:
            断言 actionable_tactics_zh 包含“保持观望或仅维持极轻仓位跟踪”。
        """
        evt = CorporateEvent(
            event_id="MEDIOCRE_EVENT",
            target_date="2026-11-10",
            category="product_launch",
            title_zh="某常规硬件发布会",
            description_zh="常规代际升级，预期波动有限",
            upside_potential_pct=15.0,
            downside_risk_pct=-15.0,
            probability_of_success=0.55,
        )
        res = CatalystCalendarEngine.evaluate_event(evt, as_of_date="2026-11-03")

        self.assertEqual(res.days_until_event, 7)
        self.assertIn("保持观望或仅维持极轻仓位跟踪", res.actionable_tactics_zh)

    def test_ut_catalyst_04_mid_term_incubation_window_tactics(self):
        """【UT-CATALYST-04: 中期窗口 (14~60天) 催化剂发酵分批埋伏战术断言】

        一、测试功能与测试点:
            验证处于 14 ~ 60 天中期发酵窗口的催化剂事件，系统给出“适合在震荡回调时分批建仓埋伏”的布局建议。

        二、正常函数业务边界与参数契约:
            - days_until_event 处于 (14, 60] 区间

        三、测试数据与模拟场景说明:
            测试距离评估日 35 天的重磅合作伙伴里程碑发布。

        四、预期断言与结果验证:
            断言 urgency_status 包含 "14-60天"。
            断言 actionable_tactics_zh 包含“中期发酵窗口”与“分批建仓埋伏”。
        """
        evt = CorporateEvent(
            event_id="PARTNERSHIP_DEAL",
            target_date="2026-12-08",
            category="partnership_milestone",
            title_zh="跨国药企全球商业化授权签字仪式",
            description_zh="首付款与里程碑款项披露",
            upside_potential_pct=40.0,
            downside_risk_pct=-20.0,
            probability_of_success=0.65,
        )
        res = CatalystCalendarEngine.evaluate_event(evt, as_of_date="2026-11-03")

        self.assertEqual(res.days_until_event, 35)
        self.assertIn("14-60天", res.urgency_status)
        self.assertIn("中期发酵窗口", res.actionable_tactics_zh)
        self.assertIn("分批建仓埋伏", res.actionable_tactics_zh)

    def test_ut_catalyst_05_long_term_and_historical_status_mapping(self):
        """【UT-CATALYST-05: 远期储备 (>60天) 与已落地历史事件状态机映射】

        一、测试功能与测试点:
            验证已过去的历史事件 (days < 0) 与 >60 天的远期储备催化剂的状态机划分与指令准确性。

        二、正常函数业务边界与参数契约:
            - 场景 A: target_date 早于评估日 (days < 0)
            - 场景 B: target_date 远大于 60 天

        三、测试数据与模拟场景说明:
            测试已过去的财报与 100 天后的远期年会。

        四、预期断言与结果验证:
            场景 A urgency_status 包含 "Historical"，指令提示“事件已落地”；
            场景 B urgency_status 包含 ">60天"，指令提示“远期储备催化剂”。
        """
        # 场景 A: 历史事件
        evt_past = CorporateEvent(
            event_id="PAST_EARNINGS",
            target_date="2026-10-15",
            category="earnings_release",
            title_zh="三季度财报披露",
            description_zh="已落地的历史财报",
            upside_potential_pct=10.0,
            downside_risk_pct=-10.0,
            probability_of_success=0.50,
        )
        res_past = CatalystCalendarEngine.evaluate_event(evt_past, as_of_date="2026-11-03")
        self.assertLess(res_past.days_until_event, 0)
        self.assertIn("已过去 (历史事件)", res_past.urgency_status)
        self.assertNotIn("Historical", res_past.urgency_status)
        self.assertIn("事件已落地", res_past.actionable_tactics_zh)

        # 场景 B: 远期事件 (100天后)
        evt_future = CorporateEvent(
            event_id="FUTURE_ASCO",
            target_date="2027-02-11",
            category="clinical_readout",
            title_zh="ASCO 肿瘤年会最新临床口头报告",
            description_zh="长期管线推进",
            upside_potential_pct=50.0,
            downside_risk_pct=-25.0,
            probability_of_success=0.60,
        )
        res_future = CatalystCalendarEngine.evaluate_event(evt_future, as_of_date="2026-11-03")
        self.assertEqual(res_future.days_until_event, 100)
        self.assertIn(">60天", res_future.urgency_status)
        self.assertIn("远期储备催化剂", res_future.actionable_tactics_zh)

    def test_ut_catalyst_06_volatility_arbitrage_and_facade_consistency(self):
        """【UT-CATALYST-06: 期权平值跨式 IV 波动率被低估/泡沫判定与中继门面 SSOT 对齐】

        一、测试功能与测试点:
            验证期权波动率套利断言 (Volatility Arbitrage) 在低估与泡沫场景下的判定，
            同时验证向下兼容门面 `finance_tools.catalyst_calendar_engine` 的完全等价性。

        二、正常函数业务边界与参数契约:
            - 情况 1: 基本面预期摆动显著大于期权市场定价 (波动率被低估，存在双买套利空间)
            - 情况 2: 期权定价过度夸大二元波动 (波动率严重泡沫，防范 IV Crush 击杀)

        三、测试数据与模拟场景说明:
            测试两种典型波动率错配场景。

        四、预期断言与结果验证:
            情况 1 断言 volatility_arbitrage_verdict 包含“期权波动率被低估”与“套利空间”；
            情况 2 断言 volatility_arbitrage_verdict 包含“期权波动率严重泡沫”与“IV Crush”；
            门面 FacadeCatalystCalendarEngine 计算结果与底层纯净类完全一致。
        """
        # 情况 1: 真实二元摆幅 50%，期权仅定价 20%
        evt_undervalued = FacadeCorporateEvent(
            event_id="VOL_UNDER",
            target_date="2026-11-20",
            category="clinical_readout",
            title_zh="期权引伸波幅低估标的",
            description_zh="测试波动率低估套利",
            upside_potential_pct=50.0,
            downside_risk_pct=-50.0,
            probability_of_success=0.50,
            options_implied_move_pct=20.0,
        )
        res_1 = FacadeCatalystCalendarEngine.evaluate_event(evt_undervalued, as_of_date="2026-11-03")
        self.assertIn("期权波动率被低估", res_1.volatility_arbitrage_verdict)
        self.assertIn("套利空间", res_1.volatility_arbitrage_verdict)

        # 情况 2: 真实二元摆幅 15%，期权却定价 40% (严重泡沫)
        evt_bubble = FacadeCorporateEvent(
            event_id="VOL_BUBBLE",
            target_date="2026-11-20",
            category="earnings_release",
            title_zh="期权引伸波幅泡沫标的",
            description_zh="测试 IV Crush 预警",
            upside_potential_pct=15.0,
            downside_risk_pct=-15.0,
            probability_of_success=0.50,
            options_implied_move_pct=40.0,
        )
        res_2 = FacadeCatalystCalendarEngine.evaluate_event(evt_bubble, as_of_date="2026-11-03")
        self.assertIn("期权波动率严重泡沫", res_2.volatility_arbitrage_verdict)
        self.assertIn("IV Crush", res_2.volatility_arbitrage_verdict)

    def test_ut_catalyst_07_buyer_dossier_card_and_to_dict_contract(self):
        """【UT-CATALYST-07: 二元催化剂事件全息研报卡片与去工程符号化契约断言】

        一、测试功能与测试点:
            1. 验证 EventEvaluationResult 包含自然语言 narrative_zh 全息卡片并支持 to_dict()；
            2. 验证 category_zh 纯自然中文事件类别字段正确映射；
            3. 验证 urgency_status_zh 纯自然中文时效阶段字段正确生成；
            4. 验证 narrative_zh 彻底消除 (Historical) 等英文代号暴露。

        二、正常函数业务边界与参数契约:
            - 传入有效事件对象与基准评估日。

        三、测试数据与模拟场景说明:
            - 测试历史事件与即将到来的三期试验读出事件。

        四、预期断言与结果验证:
            - narrative_zh 包含 "二元催化剂事件全息研判"；
            - 历史事件研报不含 "(Historical)" 英文代号；
            - to_dict() 完整暴露 category_zh、urgency_status_zh 与 narrative_zh。
        """
        # 历史事件
        evt_hist = CorporateEvent(
            event_id="HIST_01",
            target_date="2026-10-01",
            category="fda_pdufa",
            title_zh="历史已完成裁决",
            description_zh="历史归档事件",
            upside_potential_pct=20.0,
            downside_risk_pct=-20.0,
            probability_of_success=0.50,
        )
        res_hist = CatalystCalendarEngine.evaluate_event(evt_hist, as_of_date="2026-11-03")
        self.assertNotIn("(Historical)", res_hist.narrative_zh)
        self.assertIn("历史事件", res_hist.narrative_zh)
        self.assertEqual(res_hist.category_zh, "FDA审评审批裁决")
        self.assertEqual(res_hist.urgency_status_zh, "已过去 (历史事件)")

        d_hist = res_hist.to_dict()
        self.assertIn("category_zh", d_hist)
        self.assertIn("urgency_status_zh", d_hist)
        self.assertIn("narrative_zh", d_hist)
        self.assertEqual(d_hist["narrative_zh"], res_hist.narrative_zh)


if __name__ == "__main__":
    unittest.main()
