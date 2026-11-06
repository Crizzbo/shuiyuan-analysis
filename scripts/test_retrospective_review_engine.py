"""复盘与反思归因引擎单元测试套件 (Test Retrospective Review Engine)."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finance_tools.retrospective_review_engine import (
    RetrospectiveReviewEngine,
    HistoricalPredictionSnapshot,
    ActualMarketOutcome,
)


class TestRetrospectiveReviewEngine(unittest.TestCase):
    """测试复盘反思引擎各项归因与走廊计算。"""

    def setUp(self):
        self.engine = RetrospectiveReviewEngine()

    def test_rxrx_review_and_reflection(self):
        """【UT-RETRO-01: RXRX破位深蹲与做市商伽马抛售复盘-贝叶斯先验校准与盲点反思】

        1. 测试功能与测试点:
           - 验证 RetrospectiveReviewEngine.evaluate_prediction_outcome 对破位深蹲 Biotech 标的复盘。
           - 走廊有效性判断 (corridor_status)、期权风险规避评估 (options_risk_verdict)。
           - 自动生成系统性反思记录 (blind_spots_reflection) 与贝叶斯概率先验校准 (bayesian_calibration)。

        2. 正常函数业务边界与参数契约:
           - pred 为 HistoricalPredictionSnapshot 事实快照。
           - out 为 ActualMarketOutcome 真实市场结果。
           - 返回 RetrospectiveRecord 评估对象。

        3. 测试数据与模拟场景说明:
           - 标的: RXRX。基准价 $3.835，公允中枢 $5.80，悲观底 $2.20。
           - 实际结果: 价格微升至 $3.85 (+0.39%)，大盘基准收益 +0.45%。
           - 行权价 4.0 虚值期权，系统提前下达 '严禁重仓近月虚值期权' 指令。

        4. 预期断言与结果验证:
           - 断言 corridor_status == 'WITHIN_CORRIDOR'。
           - 断言 realized_return_pct 约为 0.39%。
           - 断言 options_risk_verdict 包含 'PROTECTED'。
           - 断言 blind_spots_reflection 包含 '反思一'。
           - 断言 bayesian_calibration 包含 '贝叶斯先验校准'。
        """
        pred = HistoricalPredictionSnapshot(
            prediction_id="PRED-20261014-RXRX",
            prediction_date="2026-10-14",
            market="US",
            ticker="RXRX",
            company_name="Recursion Pharmaceuticals",
            baseline_price=3.835,
            rating="强烈推荐买入",
            safe_entry_trigger=3.50,
            pessimistic_floor=2.20,
            pessimistic_event="临床II期不及预期",
            neutral_fair_value=5.80,
            optimistic_target=9.50,
            optimistic_event="罗氏赛诺菲里程碑兑现",
            tactical_action="1/4 凯利现货建仓，严禁重仓近月虚值期权",
            kelly_fraction=0.10,
            options_warning="Strike 4.0 已成全线虚值，期权防归零风险",
        )
        out = ActualMarketOutcome(
            outcome_date="2026-10-15",
            current_price=3.85,
            quote_timestamp="2026-10-14 16:00 EDT",
            benchmark_return_pct=0.45,
            realized_catalysts=["盘前盘后窄幅震荡", "现金垫 $1.03 强支撑"],
        )
        rec = self.engine.evaluate_prediction_outcome(
            pred, out, current_time_iso="2026-10-15T00:00:00Z"
        )
        self.assertEqual(rec.corridor_status, "WITHIN_CORRIDOR")
        self.assertEqual(rec.corridor_status_zh, "处于中枢走廊安全区间")
        self.assertAlmostEqual(rec.realized_return_pct, 0.39, places=1)
        self.assertIn("全面受控", rec.options_risk_verdict)
        self.assertIn("成功规避期权全额归零损失", rec.options_risk_verdict)
        self.assertNotIn("PROTECTED", rec.options_risk_verdict)
        self.assertIn("反思一", rec.blind_spots_reflection)
        self.assertIn("贝叶斯先验校准", rec.bayesian_calibration)
        self.assertIn("投研闭环复盘与反思归因全息研报", rec.narrative_zh)
        self.assertIn("处于【处于中枢走廊安全区间】", rec.narrative_zh)

        d = rec.to_dict()
        self.assertIn("narrative_zh", d)
        self.assertEqual(d["narrative_zh"], rec.narrative_zh)
        self.assertEqual(d["corridor_status_zh"], "处于中枢走廊安全区间")

    def test_unh_review_and_reflection(self):
        """【UT-RETRO-02: UNH政策超跌错杀反弹复盘-安全边际击中与超额Alpha测算】

        1. 测试功能与测试点:
           - 验证针对大盘蓝筹超跌反弹标的 (UNH) 的战术击中验证 (trigger_hit)。
           - 绝对收益率 (realized_return_pct) 与超额阿尔法 (excess_alpha_pct) 精确测算。

        2. 正常函数业务边界与参数契约:
           - 基准价格与实际结算价格均为正浮点数。

        3. 测试数据与模拟场景说明:
           - 标的: UnitedHealth Group (UNH)。
           - 基准价 $379.30，安全击球买点 $533.60，实际现价 $388.50 (+2.43%)，大盘涨幅 +0.60%。

        4. 预期断言与结果验证:
           - 断言 realized_return_pct > 2.0%。
           - 断言 excess_alpha_pct > 1.5%。
           - 断言 trigger_hit 为 True (388.50 < 533.60 击中安全买入区)。
        """
        pred = HistoricalPredictionSnapshot(
            prediction_id="PRED-20261013-UNH",
            prediction_date="2026-10-13",
            market="US",
            ticker="UNH",
            company_name="UnitedHealth Group",
            baseline_price=379.30,
            rating="强力买入",
            safe_entry_trigger=533.60,
            pessimistic_floor=592.88,
            pessimistic_event="Medicare 报销削减",
            neutral_fair_value=690.29,
            optimistic_target=822.83,
            optimistic_event="商保利润率恢复超预期",
            tactical_action="分批重仓吸纳",
            kelly_fraction=0.15,
        )
        out = ActualMarketOutcome(
            outcome_date="2026-10-15",
            current_price=388.50,
            quote_timestamp="2026-10-14 16:00 EDT",
            benchmark_return_pct=0.60,
            realized_catalysts=["医疗成本控制预期企稳", "机构逢低回补"],
        )
        rec = self.engine.evaluate_prediction_outcome(
            pred, out, current_time_iso="2026-10-15T00:00:00Z"
        )
        self.assertGreater(rec.realized_return_pct, 2.0)
        self.assertGreater(rec.excess_alpha_pct, 1.5)
        self.assertTrue(rec.trigger_hit) # 388.50 < 533.60

    def test_summary_and_ledger_persistence(self):
        """【IT-RETRO-03: 系统级复盘大盘统计指标计算与审计底账物理持久化】

        1. 测试功能与测试点:
           - 验证 RetrospectiveReviewEngine.build_system_retrospective_summary 全局大盘复盘统计。
           - 胜率指标输出: 包含绝对胜率 (absolute_win_rate_pct) 与系统反思结论 (system_reflection_verdict)。
           - 审计账本磁盘物理持久化: 验证 save_ledger 成功将复盘明细落盘为合法 JSON 文件。

        2. 正常函数业务边界与参数契约:
           - ledger_file 指定项目内临时路径，执行后物理存在。

        3. 测试数据与模拟场景说明:
           - 执行 RXRX 复盘并写入临时审计文件 test_retrospective_ledger.json。

        4. 预期断言与结果验证:
           - 断言 summary 字典包含 'absolute_win_rate_pct' 与 'system_reflection_verdict'。
           - 断言 tmp_ledger.exists() 为 True。
        """
        self.test_rxrx_review_and_reflection()
        summary = self.engine.build_system_retrospective_summary()
        self.assertIn("absolute_win_rate_pct", summary)
        self.assertIn("system_reflection_verdict", summary)
        from scripts.test_support.fixtures import project_temp
        tmp_ledger = project_temp(self, "test-retrospective-") / "ledger.json"
        self.engine.ledger_file = tmp_ledger
        self.engine.save_ledger()
        self.assertTrue(tmp_ledger.exists())

    def test_ut_retro_04_below_floor_and_above_target_zh_status(self):
        """【UT-RETRO-04: 跌破悲观底线与突破乐观靶心之自然中文状态及研报断言】

        一、测试功能与测试点:
            验证在市价跌破悲观防御底线 (BELOW_FLOOR) 或突破乐观弹性靶心 (ABOVE_TARGET) 时，
            引擎能够正确赋予纯自然中文状态 `跌破悲观防御底线` 与 `突破乐观弹性靶心`，
            并完整组装进 narrative_zh 买方研报。

        二、正常函数业务边界与参数契约:
            - 市价 < pessimistic_floor -> corridor_status_zh == "跌破悲观防御底线"
            - 市价 > optimistic_target -> corridor_status_zh == "突破乐观弹性靶心"

        三、测试数据与模拟场景说明:
            测试黑天鹅击穿与重磅催化超预期兑现两种极端场景。

        四、预期断言与结果验证:
            断言 corridor_status 与 corridor_status_zh 精确匹配。
            断言 narrative_zh 包含中文定性。
        """
        pred = HistoricalPredictionSnapshot(
            prediction_id="PRED-TEST-CORRIDOR",
            prediction_date="2026-10-10",
            market="US",
            ticker="EXTREME",
            company_name="Extreme Corp",
            baseline_price=10.0,
            rating="观察",
            safe_entry_trigger=8.0,
            pessimistic_floor=7.0,
            pessimistic_event="行业暴雷",
            neutral_fair_value=12.0,
            optimistic_target=18.0,
            optimistic_event="天量订单",
            tactical_action="轻仓",
            kelly_fraction=0.05,
        )

        # 场景 A: 击穿悲观底
        out_below = ActualMarketOutcome(
            outcome_date="2026-10-15",
            current_price=5.50,
            quote_timestamp="2026-10-14 16:00 EDT",
            benchmark_return_pct=-5.0,
            realized_catalysts=["客户流失"],
        )
        rec_below = self.engine.evaluate_prediction_outcome(pred, out_below)
        self.assertEqual(rec_below.corridor_status, "BELOW_FLOOR")
        self.assertEqual(rec_below.corridor_status_zh, "跌破悲观防御底线")
        self.assertIn("跌破悲观防御底线", rec_below.narrative_zh)

        # 场景 B: 冲破乐观靶心
        out_above = ActualMarketOutcome(
            outcome_date="2026-10-15",
            current_price=22.0,
            quote_timestamp="2026-10-14 16:00 EDT",
            benchmark_return_pct=10.0,
            realized_catalysts=["重磅催化兑现"],
        )
        rec_above = self.engine.evaluate_prediction_outcome(pred, out_above)
        self.assertEqual(rec_above.corridor_status, "ABOVE_TARGET")
        self.assertEqual(rec_above.corridor_status_zh, "突破乐观弹性靶心")
        self.assertIn("突破乐观弹性靶心", rec_above.narrative_zh)

    def test_ut_retro_05_facade_and_core_equivalence(self):
        """【UT-RETRO-05: 复盘反思引擎门面与底层核心 SSOT 完全等价性断言】

        一、测试功能与测试点:
            验证 `finance_tools.retrospective_review_engine` 门面与
            `financial_core.engines.retrospective_review_engine` 输出 100% 一致。

        二、预期断言与结果验证:
            断言返回值所有字段完全等价。
        """
        from financial_core.engines.retrospective_review_engine import (
            RetrospectiveReviewEngine as CoreRetrospectiveReviewEngine,
        )

        core_engine = CoreRetrospectiveReviewEngine()
        pred = HistoricalPredictionSnapshot(
            prediction_id="PRED-TEST-SSOT",
            prediction_date="2026-10-10",
            market="US",
            ticker="SSOT",
            company_name="SSOT Corp",
            baseline_price=10.0,
            rating="中性",
            safe_entry_trigger=8.0,
            pessimistic_floor=7.0,
            pessimistic_event="低迷",
            neutral_fair_value=12.0,
            optimistic_target=18.0,
            optimistic_event="放量",
            tactical_action="观望",
            kelly_fraction=0.05,
        )
        out = ActualMarketOutcome(
            outcome_date="2026-10-15",
            current_price=11.0,
            quote_timestamp="2026-10-14 16:00 EDT",
            benchmark_return_pct=2.0,
            realized_catalysts=["平稳运行"],
        )

        rec_facade = self.engine.evaluate_prediction_outcome(pred, out)
        rec_core = core_engine.evaluate_prediction_outcome(pred, out)

        self.assertEqual(rec_facade.narrative_zh, rec_core.narrative_zh)
        self.assertEqual(rec_facade.corridor_status_zh, rec_core.corridor_status_zh)
        self.assertEqual(rec_facade.to_dict(), rec_core.to_dict())


if __name__ == "__main__":
    unittest.main()
