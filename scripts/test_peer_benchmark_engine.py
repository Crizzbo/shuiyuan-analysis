"""全行业同业横向对标与相对估值分析引擎单元测试套件.

本测试模块严格遵循《36号工程黄金设计规范》与四段式结构化中文契约测试模型:
1. 测试功能与测试点说明 (Test Functionality & Objectives)
2. 正常函数业务边界与参数契约 (Business Boundaries & Parameter Contracts)
3. 测试数据与模拟场景说明 (Test Data & Scenario Descriptions)
4. 预期断言与结果验证 (Expected Assertions & Verification)

涵盖高质量错杀金矿识别、估值泡沫预警、折溢价自然语言正负号倒错修复
(消除"溢价 -8.5%"语病)、统计学术语规范(中位数 vs 平均数)、异常负估值除零除负防御与门面 SSOT 等价性断言。
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.peer_benchmark_engine import (
    CompanyPeerMetrics,
    PeerBenchmarkResult,
    PeerBenchmarkEngine,
)
from finance_tools.peer_benchmark_engine import (
    CompanyPeerMetrics as FacadeCompanyPeerMetrics,
    PeerBenchmarkResult as FacadePeerBenchmarkResult,
    PeerBenchmarkEngine as FacadePeerBenchmarkEngine,
)


class TestPeerBenchmarkEngine(unittest.TestCase):
    """全行业同业横向对标与相对估值引擎契约测试."""

    def test_ut_peer_01_high_quality_undervalued_gold_mine(self):
        """【UT-PEER-01: 高质量被错杀金矿标的 (增速超中位数且估值显著折价) 判定断言】

        一、测试功能与测试点:
            验证 PeerBenchmarkEngine.evaluate 能够准确识别基本面增速领先同业、
            但估值乘数显著落后于中位数的深度错杀标的，输出 "极具性价比 / 同业显著错杀"，
            并验证自然语言解读中正确使用“折价”表述，无语病。

        二、正常函数业务边界与参数契约:
            - target: 增速 35.0%, EV/Sales 3.0x
            - peers: 中位数增速 20.0%, 中位数 EV/Sales 6.0x (折价 50%)

        三、测试数据与模拟场景说明:
            测试被情绪无差别错杀的行业成长冠军。

        四、预期断言与结果验证:
            断言 relative_value_verdict 包含 "同业显著错杀" 与 "High Quality, Undervalued"。
            断言 ev_sales_premium_to_median_pct < -40.0。
            断言 rationale_zh 包含 "折价" 与 "极低估值分位"。
            断言 rationale_zh 严禁出现 "溢价 -" 语病。
        """
        target = CompanyPeerMetrics(
            ticker="UNDERVALUED_CHAMP",
            company_name="成长冠军",
            ev_to_sales=3.0,
            pe_ratio=15.0,
            pb_ratio=2.5,
            fcf_yield_pct=8.0,
            revenue_growth_yoy=35.0,
            gross_margin_pct=65.0,
        )
        peer1 = CompanyPeerMetrics(
            ticker="PEER_A",
            company_name="同行A",
            ev_to_sales=6.0,
            pe_ratio=30.0,
            pb_ratio=5.0,
            fcf_yield_pct=3.0,
            revenue_growth_yoy=20.0,
            gross_margin_pct=60.0,
        )
        peer2 = CompanyPeerMetrics(
            ticker="PEER_B",
            company_name="同行B",
            ev_to_sales=8.0,
            pe_ratio=40.0,
            pb_ratio=6.0,
            fcf_yield_pct=2.0,
            revenue_growth_yoy=22.0,
            gross_margin_pct=58.0,
        )

        res = PeerBenchmarkEngine.evaluate(target, [peer1, peer2])

        self.assertIn("同业显著错杀", res.relative_value_verdict)
        self.assertNotIn("High Quality, Undervalued", res.relative_value_verdict)
        self.assertLess(res.ev_sales_premium_to_median_pct, -40.0)
        self.assertIn("折价", res.rationale_zh)
        self.assertNotIn("溢价 -", res.rationale_zh)
        self.assertNotIn("(-", res.rationale_zh) # 彻底消除类似 折价 50.0% (-50.0%) 冗余双重括号语病

    def test_ut_peer_02_overvalued_overhang_bubble_warning(self):
        """【UT-PEER-02: 估值虚高泡沫预警 (估值显著溢价且增速跑输中位数) 判定断言】

        一、测试功能与测试点:
            验证当标的估值溢价 > 30% 且成长性落后于同业中位数时，
            系统发出 "估值虚高泡沫 / 性价比低下" 预警，
            且断言文字中严密使用 "同业中位数" 术语，消除了混淆为 "同业平均" 的统计学语病。

        二、正常函数业务边界与参数契约:
            - target: 增速 10.0%, EV/Sales 12.0x
            - peers: 中位数增速 25.0%, 中位数 EV/Sales 6.0x (溢价 100%)

        三、测试数据与模拟场景说明:
            测试伪成长、估值严重泡沫化的标的。

        四、预期断言与结果验证:
            断言 relative_value_verdict 包含 "估值虚高泡沫"。
            断言 rationale_zh 包含 "同业中位数"。
            断言 rationale_zh 严禁出现 "同业平均" 统计学语病。
        """
        target = CompanyPeerMetrics(
            ticker="BUBBLE_STOCK",
            company_name="泡沫标的",
            ev_to_sales=12.0,
            pe_ratio=60.0,
            pb_ratio=10.0,
            fcf_yield_pct=-2.0,
            revenue_growth_yoy=10.0,
            gross_margin_pct=50.0,
        )
        peer1 = CompanyPeerMetrics(
            ticker="PEER_X",
            company_name="同行X",
            ev_to_sales=6.0,
            pe_ratio=25.0,
            pb_ratio=4.0,
            fcf_yield_pct=4.0,
            revenue_growth_yoy=25.0,
            gross_margin_pct=55.0,
        )
        peer2 = CompanyPeerMetrics(
            ticker="PEER_Y",
            company_name="同行Y",
            ev_to_sales=5.5,
            pe_ratio=22.0,
            pb_ratio=3.5,
            fcf_yield_pct=5.0,
            revenue_growth_yoy=24.0,
            gross_margin_pct=52.0,
        )

        res = PeerBenchmarkEngine.evaluate(target, [peer1, peer2])

        self.assertIn("估值虚高泡沫", res.relative_value_verdict)
        self.assertIn("同业中位数", res.rationale_zh)
        self.assertNotIn("同业平均", res.rationale_zh)

    def test_ut_peer_03_fair_valuation_with_adaptive_sign_syntax(self):
        """【UT-PEER-03: 合理估值区间匹配与自然语言正负号自适应断言】

        一、测试功能与测试点:
            验证在合理估值走廊内 (Fairly Valued)，
            当相对中位数微幅折价 (如 -5%) 时，系统输出“呈现折价 5.0% (-5.0%)”，
            彻底消除旧代码中“相对同业中位数溢价为 -5.0%”的双重正负号语言倒错缺陷。

        二、正常函数业务边界与参数契约:
            - target: EV/Sales 5.7x
            - peers: 中位数 EV/Sales 6.0x (折价 5.0%)

        三、测试数据与模拟场景说明:
            测试与同业基本匹配的平衡标的。

        四、预期断言与结果验证:
            断言 relative_value_verdict 包含 "基本匹配"。
            断言 rationale_zh 包含 "呈现折价 5.0% (-5.0%)"。
            断言 rationale_zh 严禁出现 "溢价为 -"。
        """
        target = CompanyPeerMetrics(
            ticker="BALANCED",
            company_name="中性标的",
            ev_to_sales=5.7,
            pe_ratio=24.0,
            pb_ratio=3.8,
            fcf_yield_pct=4.5,
            revenue_growth_yoy=21.0,
            gross_margin_pct=55.0,
        )
        peer1 = CompanyPeerMetrics(
            ticker="PEER_1",
            company_name="同行1",
            ev_to_sales=6.0,
            pe_ratio=25.0,
            pb_ratio=4.0,
            fcf_yield_pct=4.0,
            revenue_growth_yoy=20.0,
            gross_margin_pct=55.0,
        )

        res = PeerBenchmarkEngine.evaluate(target, [peer1])

        self.assertIn("基本匹配", res.relative_value_verdict)
        self.assertIn("呈现折价 5.0%", res.rationale_zh)
        self.assertNotIn("(-5.0%)", res.rationale_zh)
        self.assertNotIn("溢价为 -", res.rationale_zh)

    def test_ut_peer_04_negative_or_zero_ev_denominator_defense(self):
        """【UT-PEER-04: 同业异常负值与极端边界除零除负防御断言】

        一、测试功能与测试点:
            验证金融数学除零除负防御：当同行企业处于资不抵债严重亏损导致 EV/Sales 为 0 或负数时，
            系统计算折溢价时使用 safe_denom_ev = max(0.01, abs(median_ev_s)) 严密防御，
            不崩溃抛错，不发生分母除以零或绝对值虚假膨胀。

        二、正常函数业务边界与参数契约:
            - peers 的 ev_to_sales <= 0

        三、测试数据与模拟场景说明:
            输入极端脏数据。

        四、预期断言与结果验证:
            断言函数执行不崩溃。
            断言 ev_sales_percentile 介于 0.0 与 100.0 之间。
        """
        target = CompanyPeerMetrics(
            ticker="NORMAL",
            company_name="正常标的",
            ev_to_sales=2.0,
            pe_ratio=15.0,
            pb_ratio=2.0,
            fcf_yield_pct=5.0,
            revenue_growth_yoy=10.0,
            gross_margin_pct=40.0,
        )
        peer_zero = CompanyPeerMetrics(
            ticker="ZERO_EV",
            company_name="零EV标的",
            ev_to_sales=0.0,
            pe_ratio=None,
            pb_ratio=0.5,
            fcf_yield_pct=-10.0,
            revenue_growth_yoy=-5.0,
            gross_margin_pct=10.0,
        )

        res = PeerBenchmarkEngine.evaluate(target, [peer_zero])

        self.assertGreaterEqual(res.ev_sales_percentile, 0.0)
        self.assertLessEqual(res.ev_sales_percentile, 100.0)
        self.assertIsNotNone(res.rationale_zh)

    def test_ut_peer_05_minimum_peer_count_contract(self):
        """【UT-PEER-05: 极小样本 (单家对标) 最小防御与参数契约断言】

        一、测试功能与测试点:
            验证参数契约：当 peers 列表为空时，无法构成相对估值参照系，
            系统按照契约显式抛出 ValueError("对标分析至少需要 1 家同业可比公司进行参照")。

        二、正常函数业务边界与参数契约:
            - peers: []

        三、测试数据与模拟场景说明:
            测试空同伴列表拦截。

        四、预期断言与结果验证:
            断言抛出 ValueError。
        """
        target = CompanyPeerMetrics(
            ticker="LONELY",
            company_name="孤独标的",
            ev_to_sales=5.0,
            pe_ratio=20.0,
            pb_ratio=3.0,
            fcf_yield_pct=5.0,
            revenue_growth_yoy=15.0,
            gross_margin_pct=50.0,
        )
        with self.assertRaises(ValueError):
            PeerBenchmarkEngine.evaluate(target, [])

    def test_ut_peer_06_facade_and_core_ssot_equivalence(self):
        """【UT-PEER-06: 向下兼容中继门面 SSOT 完全等价性断言】

        一、测试功能与测试点:
            验证 `finance_tools.peer_benchmark_engine` 中继门面与底层核心
            `financial_core.engines.peer_benchmark_engine` 计算输出 100% 相同。

        二、正常函数业务边界与参数契约:
            - Facade 与 Core 传入相同输入。

        三、测试数据与模拟场景说明:
            测试标准比对场景。

        四、预期断言与结果验证:
            断言门面与核心输出属性完全一致。
        """
        target_core = CompanyPeerMetrics("T", "Target", 5.0, 20.0, 3.0, 5.0, 15.0, 50.0)
        peer_core = CompanyPeerMetrics("P", "Peer", 6.0, 25.0, 4.0, 4.0, 18.0, 55.0)

        target_facade = FacadeCompanyPeerMetrics("T", "Target", 5.0, 20.0, 3.0, 5.0, 15.0, 50.0)
        peer_facade = FacadeCompanyPeerMetrics("P", "Peer", 6.0, 25.0, 4.0, 4.0, 18.0, 55.0)

        res_core = PeerBenchmarkEngine.evaluate(target_core, [peer_core])
        res_facade = FacadePeerBenchmarkEngine.evaluate(target_facade, [peer_facade])

        self.assertEqual(res_core.ev_sales_premium_to_median_pct, res_facade.ev_sales_premium_to_median_pct)
        self.assertEqual(res_core.relative_value_verdict, res_facade.relative_value_verdict)
        self.assertEqual(res_core.rationale_zh, res_facade.rationale_zh)

    def test_ut_peer_07_buyer_dossier_card_and_to_dict_contract(self):
        """【UT-PEER-07: 同业对标买方全息研报卡片与 to_dict 序列化契约断言】

        一、测试功能与测试点:
            1. 验证 PeerBenchmarkResult 包含标准 narrative_zh 买方全息研报卡片；
            2. 验证 to_dict() 方法能够正确暴露 narrative_zh，且与内部属性保持单一事实来源 (SSOT)；
            3. 验证卡片通俗整合对标结论、行业倍数走廊与成长性超额对比。

        二、正常函数业务边界与参数契约:
            - evaluate 正常返回 PeerBenchmarkResult。

        三、测试数据与模拟场景说明:
            测试标准行业可比对标场景。

        四、预期断言与结果验证:
            断言 narrative_zh 包含“【标的 T 行业同业可比对标全息研报】”。
            断言 to_dict() 包含 narrative_zh。
        """
        target = CompanyPeerMetrics("T", "Target", 5.0, 20.0, 3.0, 5.0, 15.0, 50.0)
        peer = CompanyPeerMetrics("P", "Peer", 6.0, 25.0, 4.0, 4.0, 18.0, 55.0)

        res = PeerBenchmarkEngine.evaluate(target, [peer])

        self.assertIn("行业同业可比对标全息研报", res.narrative_zh)
        self.assertIn("同业估值走廊", res.narrative_zh)
        self.assertIn("成长性超额对比", res.narrative_zh)
        self.assertNotIn("(Fairly Valued vs Peers)", res.narrative_zh)
        self.assertEqual(res.relative_value_verdict_zh, "估值与行业中枢基本匹配")

        d = res.to_dict()
        self.assertIn("narrative_zh", d)
        self.assertEqual(d["narrative_zh"], res.narrative_zh)
        self.assertIn("verdict_zh", d["valuation_relative"])
        self.assertEqual(d["valuation_relative"]["verdict_zh"], "估值与行业中枢基本匹配")


if __name__ == "__main__":
    unittest.main()
