"""单元测试：突发事件微观事实与多业务分部 (SOTP) 穿透与因果加总引擎 (Phase 2).

验证内容：
1. SOTP 分部资产负债表与营收权重刚性平账自检；
2. 样本 A 打样断言：加州 50MW+ 算力电网新规仅冲击微软 Intelligent Cloud，Office与个人计算零受损；
3. 样本 B 打样断言：鹿特丹光刻胶工厂爆炸停产穿透台积电，验证 45 天 DIO 库存缓冲与转嫁权冲销；
4. 德州半导体制造补贴正面利好事件增厚 EBIT 断言；
5. 与 SQLite 真实事件账本跨资产池端到端因果穿透集成测试。
"""

import json
from pathlib import Path
import unittest

from financial_core.engines.sotp_event_penetration_engine import (
    BusinessSegment,
    CompanySotpProfile,
    SegmentCausalImpact,
    EnterpriseEventImpactResult,
    SotpEventPenetrationEngine,
)
from financial_core.engines.event_radar_engine import StructuredEventSummary
from finance_tools.sotp_event_analyzer import SotpEventAnalyzer
from scripts.test_support.sotp_fixtures import make_sotp_test_analyzer


class TestSotpProfileInvariants(unittest.TestCase):
    """测试 SOTP 档案平账自检与非法结构防御."""

    def test_valid_profile_passes_invariants(self):
        """测试正常平衡分部档案通过平账检验."""
        seg1 = BusinessSegment(
            segment_id="S1",
            name_zh="分部一",
            name_en="Seg 1",
            revenue=600.0,
            revenue_weight=0.60,
            operating_margin=0.30,
            operating_income=180.0,
            cost_pass_through_power=0.5,
            inventory_buffer_days=30.0,
        )
        seg2 = BusinessSegment(
            segment_id="S2",
            name_zh="分部二",
            name_en="Seg 2",
            revenue=400.0,
            revenue_weight=0.40,
            operating_margin=0.20,
            operating_income=80.0,
            cost_pass_through_power=0.4,
            inventory_buffer_days=20.0,
        )
        profile = CompanySotpProfile(
            ticker="TEST",
            company_name="Test Corp",
            fiscal_year="FY2024",
            total_revenue=1000.0,
            total_operating_income=260.0,
            effective_tax_rate=0.20,
            diluted_shares=100.0,
            current_share_price=50.0,
            segments=[seg1, seg2],
        )
        is_valid, msg = profile.verify_balance_sheet_invariants()
        self.assertTrue(is_valid)
        self.assertIn("PASS", msg)

    def test_unbalanced_weights_rejected(self):
        """测试分部权重之和不为 1.0 时刚性拦截."""
        seg1 = BusinessSegment(
            segment_id="S1",
            name_zh="分部一",
            name_en="Seg 1",
            revenue=600.0,
            revenue_weight=0.75,  # 错误：0.75 + 0.40 = 1.15
            operating_margin=0.30,
            operating_income=180.0,
            cost_pass_through_power=0.5,
            inventory_buffer_days=30.0,
        )
        seg2 = BusinessSegment(
            segment_id="S2",
            name_zh="分部二",
            name_en="Seg 2",
            revenue=400.0,
            revenue_weight=0.40,
            operating_margin=0.20,
            operating_income=80.0,
            cost_pass_through_power=0.4,
            inventory_buffer_days=20.0,
        )
        profile = CompanySotpProfile(
            ticker="TEST",
            company_name="Test Corp",
            fiscal_year="FY2024",
            total_revenue=1000.0,
            total_operating_income=260.0,
            effective_tax_rate=0.20,
            diluted_shares=100.0,
            current_share_price=50.0,
            segments=[seg1, seg2],
        )
        is_valid, msg = profile.verify_balance_sheet_invariants()
        self.assertFalse(is_valid)
        self.assertIn("权重之和", msg)


class TestSotpEventPenetrationSamples(unittest.TestCase):
    """测试核心业务实战打样用例."""

    def setUp(self):
        self.engine = SotpEventPenetrationEngine()
        self.analyzer = make_sotp_test_analyzer(self)

    def test_sample_a_california_grid_fee_penetration_on_msft(self):
        """样本 A 断言：加州 50MW+ 电网负荷费精准打击微软 Intelligent Cloud，Office与个人计算零受损."""
        event = StructuredEventSummary(
            event_id="EVT_CALIF_GRID_01",
            timestamp="2026-11-07T08:00:00Z",
            category="State_Policy_Regulatory",
            involved_entities=["加州公用事业委员会", "超大规模算力中心", "CAISO"],
            micro_physical_impact="单机柜等效电费增加 8.5%，对加州 50MW 以上算力中心加征商业电网负荷费",
            estimated_duration="法定长期生效(3年以上)",
            affected_business_segments=["云基础设施(IaaS)", "生成式AI算力集群", "商业公用事业电力"],
            severity_level="P1",
            requires_deep_analysis=True,
            raw_title="加州通过新规对50MW以上AI算力中心加征电网峰值负荷费",
            source_name="California_Regulatory_Gazette",
        )

        msft_profile = self.analyzer.get_company_sotp_profile("MSFT")
        self.assertIsNotNone(msft_profile)

        result = self.engine.analyze_company_impact(msft_profile, event)

        # 1. 断言分部因果差异化表现
        impact_by_id = {s.segment_id: s for s in result.segment_impacts}
        cloud_impact = impact_by_id["MSFT_CLOUD"]
        prod_impact = impact_by_id["MSFT_PROD"]
        mpc_impact = impact_by_id["MSFT_MPC"]

        # Intelligent Cloud 必须受到实质性冲击 (暴露度高)
        self.assertGreaterEqual(cloud_impact.exposure_score, 0.70)
        self.assertLess(cloud_impact.operating_income_impact, -100.0)  # 百万美元级负面影响

        # Productivity (Office) 与 More Personal Computing (Windows/Xbox) 必须零暴露
        self.assertEqual(prod_impact.exposure_score, 0.0)
        self.assertEqual(prod_impact.operating_income_impact, 0.0)
        self.assertEqual(mpc_impact.exposure_score, 0.0)
        self.assertEqual(mpc_impact.operating_income_impact, 0.0)

        # 2. 断言企业级总账加总平账
        expected_total_ebit = sum(s.operating_income_impact for s in result.segment_impacts)
        self.assertAlmostEqual(result.total_operating_income_impact, expected_total_ebit, places=2)

        # 3. 断言税后每股收益 ΔEPS 计算符合 18% 税率与 74.3 亿股稀释股本
        expected_net_income = expected_total_ebit * (1.0 - 0.18)
        self.assertAlmostEqual(result.net_income_impact, expected_net_income, places=2)
        expected_eps = expected_net_income / 7430.0
        self.assertAlmostEqual(result.eps_impact, expected_eps, places=4)

        # 4. 断言商业建议：由于微软多元化 SOTP 极为庞大，全公司 EBIT 受损比例极小，构成买入降噪点
        self.assertIn("BUY_ON_OVERSOLD_NOISE", result.scenario_signal)
        self.assertEqual(result.recommended_action, "SCENARIO_REVIEW_REQUIRED")
        self.assertFalse(result.is_actionable)

    def test_sample_b_rotterdam_explosion_penetration_on_tsm(self):
        """样本 B 断言：鹿特丹光刻胶工厂爆炸停产穿透台积电，验证 45 天 DIO 库存缓冲与转嫁权冲销."""
        event = StructuredEventSummary(
            event_id="EVT_ROTTERDAM_01",
            timestamp="2026-11-07T07:30:00Z",
            category="Physical_Plant_Disruption",
            involved_entities=["鹿特丹特种树脂化工厂", "全球半导体光刻胶供应链"],
            micro_physical_impact="全球EUV光刻胶专用核心前驱体单体供应骤降 35%，现存晶圆厂库存天数仅剩约 45 天",
            estimated_duration="停产抢修16周",
            affected_business_segments=["先进制程晶圆制造", "电子化学品材料", "半导体代工"],
            severity_level="P1",
            requires_deep_analysis=True,
            raw_title="鹿特丹港区核心特种单体化工厂突发爆炸全线停产16周",
            source_name="Reuters",
        )

        tsm_profile = self.analyzer.get_company_sotp_profile("TSM")
        self.assertIsNotNone(tsm_profile)

        result = self.engine.analyze_company_impact(tsm_profile, event)

        impact_by_id = {s.segment_id: s for s in result.segment_impacts}
        hpc_impact = impact_by_id["TSM_HPC"]
        auto_impact = impact_by_id["TSM_AUTO"]

        # 先进制程 HPC 命中
        self.assertGreaterEqual(hpc_impact.exposure_score, 0.80)
        # 45 天 DIO 库存缓冲吸收显著缓解冲击
        self.assertGreater(hpc_impact.inventory_absorption_factor, 0.25)
        # 下游 80% 转嫁权抵御大部分冲击
        self.assertLess(hpc_impact.net_cost_shock_pct, hpc_impact.gross_cost_shock_pct * 0.3)

        # 成熟车用芯片受波及极小
        self.assertLess(abs(auto_impact.operating_income_impact), abs(hpc_impact.operating_income_impact) * 0.1)

        # 全公司总 EBIT 冲击受控在 8% 以内，触发监控库存缓冲动作
        self.assertLess(abs(result.ebit_impact_percentage), 0.08)
        self.assertEqual(result.scenario_signal, "MONITOR_INVENTORY_BUFFER")
        self.assertTrue(result.focal_summary != "")

    def test_sample_c_texas_subsidy_favorable_event(self):
        """样本 C 断言：德州半导体晶圆补贴作为利好事件，产生正向 EBIT 增厚."""
        event = StructuredEventSummary(
            event_id="EVT_TEXAS_SUB_01",
            timestamp="2026-11-07T06:00:00Z",
            category="State_Policy_Regulatory",
            involved_entities=["德州经济发展局", "三星泰勒工厂", "德州仪器"],
            micro_physical_impact="德州提供45亿美元超额水资源与基建税收减免补贴，降低前道折旧压力约 12%",
            estimated_duration="十年期州级法案",
            affected_business_segments=["半导体晶圆制造", "工业水处理基建", "高科技厂房工程"],
            severity_level="P1",
            requires_deep_analysis=True,
            raw_title="德州州长签署通过第312章工业法案提供先进半导体晶圆制造补贴",
            source_name="Texas_Tribune",
        )

        tsm_profile = self.analyzer.get_company_sotp_profile("TSM")
        result = self.engine.analyze_company_impact(tsm_profile, event)

        # 利润变动额应为正数
        self.assertGreater(result.total_operating_income_impact, 0.0)
        self.assertGreater(result.eps_impact, 0.0)
        self.assertEqual(result.scenario_signal, "EXPEDITE_EXPANSION_OVERWEIGHT")


class TestSotpEventAnalyzerIntegration(unittest.TestCase):
    """测试 Analyzer 与 SQLite 数据库端到端集成查询."""

    def test_analyzer_end_to_end_from_sqlite(self):
        """从 SQLite 账本提取已持久化的事件并对全池执行分部穿透."""
        analyzer = make_sotp_test_analyzer(self)
        from financial_core.engines.event_radar_engine import RawNewsItem
        item = RawNewsItem(id="synthetic", title="合成云基础设施成本事件", content="合成输入",
                           source="synthetic", published_at="2026-10-16T14:00:00Z", url="")
        event = StructuredEventSummary(event_id="synthetic", timestamp=item.published_at,
            category="State_Policy_Regulatory", involved_entities=["云基础设施"],
            micro_physical_impact="合成成本冲击 5%", estimated_duration="30天",
            affected_business_segments=["云基础设施"], severity_level="P1", requires_deep_analysis=True,
            raw_title=item.title, source_name="synthetic")
        analyzer.db_mgr.insert_event(event, item, item.published_at)
        events = analyzer.db_mgr.query_events()
        self.assertGreater(len(events), 0)

        # 选取首条 P0/P1 事件
        target_evt_id = events[0]["event_id"]
        results = analyzer.analyze_stored_event_by_id(target_evt_id, ["MSFT", "TSM"])

        self.assertEqual(len(results), 2)
        tickers = {r.ticker for r in results}
        self.assertIn("MSFT", tickers)
        self.assertIn("TSM", tickers)

        # 验证 JSON 序列化无异常
        for r in results:
            d = r.to_dict()
            self.assertIn("ticker", d)
            self.assertIn("segment_impacts", d)
            self.assertIsInstance(d["segment_impacts"], list)

    def test_rumor_circuit_breaker_blocks_downstream_sotp(self):
        """测试传闻熔断门禁拦截：未核实社交快讯传闻坚决阻断下游 SOTP 深度计算."""
        analyzer = make_sotp_test_analyzer(self)
        msft_profile = analyzer.get_company_sotp_profile("MSFT")
        self.assertIsNotNone(msft_profile)

        rumor_event = StructuredEventSummary(
            event_id="EVT_RUMOR_001",
            timestamp="2026-11-07T08:15:00Z",
            category="State_Policy_Regulatory",
            involved_entities=["加州算力中心", "传闻政策"],
            micro_physical_impact="网传加州即将对算力加征 30% 巨额特别电网税",
            estimated_duration="传闻未知",
            affected_business_segments=["云基础设施(IaaS)", "生成式AI算力集群"],
            severity_level="P1",
            requires_deep_analysis=False,  # 传闻熔断标志
            raw_title="【传闻】加州或将对算力中心加征巨额电网特别税",
            source_name="X_Flash_Rumor",
            credibility_tier="Tier4_Public_Flash_Social",
            credibility_score=0.45,
            verification_status="Unverified_Rumor",
        )

        res = analyzer.engine.analyze_company_impact(msft_profile, rumor_event)

        # 断言已被熔断阻断
        self.assertEqual(res.recommended_action, "BLOCKED_BY_RUMOR_CIRCUIT_BREAKER")
        self.assertEqual(res.scenario_signal, "RUMOR_CIRCUIT_BREAKER_ACTIVE")
        self.assertEqual(res.total_operating_income_impact, 0.0)
        self.assertEqual(res.ebit_impact_percentage, 0.0)
        self.assertEqual(res.eps_impact, 0.0)
        self.assertEqual(res.segment_impacts, [])
        self.assertFalse(res.is_actionable)
        self.assertIn("传闻熔断触发", res.focal_summary)

    def test_confirmed_fact_lifts_circuit_breaker(self):
        """测试官方公报核验后解除传闻熔断，正常放行 SOTP 分部计算."""
        analyzer = make_sotp_test_analyzer(self)
        msft_profile = analyzer.get_company_sotp_profile("MSFT")

        confirmed_event = StructuredEventSummary(
            event_id="EVT_CONFIRMED_001",
            timestamp="2026-11-07T08:30:00Z",
            category="State_Policy_Regulatory",
            involved_entities=["加州公用事业委员会(CPUC)", "加州独立电网(CAISO)"],
            micro_physical_impact="加州CPUC正式发布第2026-1107号公报：单机柜等效电费增加 8.5%",
            estimated_duration="长期生效",
            affected_business_segments=["云基础设施(IaaS)", "生成式AI算力集群"],
            severity_level="P1",
            requires_deep_analysis=True,  # 熔断已解除
            raw_title="加州CPUC正式表决通过超大规模AI算力中心电网附加费新规",
            source_name="California_Regulatory_Gazette",
            credibility_tier="Tier1_Official_Regulatory",
            credibility_score=1.0,
            verification_status="Confirmed_Fact",
            evidence_path="data_sources/cpuc_official_ruling.txt",
            evidence_sha256="a" * 64,
            verified_at="2026-11-07T08:35:00Z",
        )

        res = analyzer.engine.analyze_company_impact(msft_profile, confirmed_event)

        # 断言熔断已解除并计算了真实分部冲击
        self.assertNotEqual(res.recommended_action, "BLOCKED_BY_RUMOR_CIRCUIT_BREAKER")
        self.assertNotEqual(res.scenario_signal, "RUMOR_CIRCUIT_BREAKER_ACTIVE")
        self.assertGreater(len(res.segment_impacts), 0)
        self.assertLess(res.total_operating_income_impact, 0.0)  # 负面冲击

    def test_analyze_all_verified_major_events_method(self):
        """测试批量穿透所有已就绪重大事件接口."""
        analyzer = make_sotp_test_analyzer(self)
        from financial_core.engines.event_radar_engine import RawNewsItem

        item = RawNewsItem(id="major_test_01", title="官方核实重大公报", content="公报内容",
                           source="official", published_at="2026-11-07T09:00:00Z", url="")
        event = StructuredEventSummary(
            event_id="EVT_BATCH_TEST_01", timestamp=item.published_at,
            category="State_Policy_Regulatory", involved_entities=["云基础设施"],
            micro_physical_impact="单机柜电费增加 5%", estimated_duration="30天",
            affected_business_segments=["云基础设施(IaaS)"], severity_level="P1",
            requires_deep_analysis=True, raw_title=item.title, source_name="official",
            credibility_tier="Tier1_Official_Regulatory", credibility_score=1.0,
            verification_status="Confirmed_Fact")

        analyzer.db_mgr.insert_event(event, item, item.published_at)

        results = analyzer.analyze_all_verified_major_events(target_tickers=["MSFT", "TSM"])
        self.assertIn("EVT_BATCH_TEST_01", results)
        self.assertEqual(len(results["EVT_BATCH_TEST_01"]), 2)


if __name__ == "__main__":
    unittest.main()
