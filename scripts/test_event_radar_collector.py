"""单元测试：事件雷达收集器、自发断网检测、进度管理与事件触发门禁 (Phase 1)."""

import io
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest

from financial_core.engines.event_radar_engine import (
    EventRadarEngine,
    EventSeverity,
    EventCategory,
    RawNewsItem,
    StructuredEventSummary,
)
from finance_tools.event_radar_collector import (
    NetworkHealthWatchdog,
    RadarProgressManager,
    RadarDatabaseManager,
    MockModelSummarizer,
    EventRadarCollector,
)
from scripts.run_event_radar_collector import EventRadarService


class TestEventRadarEngine(unittest.TestCase):
    """测试事件雷达底层计算引擎与规则过滤."""

    def setUp(self):
        self.engine = EventRadarEngine()

    def test_pre_filter_blacklist_noise(self):
        """测试黑名单噪声直接剔除 (0 Token 消耗)."""
        item = RawNewsItem(
            id="noise_01",
            title="今日收评：机构看好某某股票大涨，点击查看",
            content="投资顾问免责声明：广告赞助内容，不构成投资建议。",
            source="WeChat_Media",
            published_at="2026-11-07T08:00:00Z",
        )
        matched, tags, cat = self.engine.pre_filter(item)
        self.assertFalse(matched)
        self.assertIn("blacklisted_noise", tags)

    def test_pre_filter_irrelevant_news(self):
        """测试完全不相关的日常娱乐/体育新闻剔除."""
        item = RawNewsItem(
            id="irrelevant_01",
            title="某电影周末票房突破三亿美元",
            content="导演在发布会上感谢观众支持，演员分享拍摄趣事。",
            source="Entertainment_Daily",
            published_at="2026-11-07T08:05:00Z",
        )
        matched, tags, cat = self.engine.pre_filter(item)
        self.assertFalse(matched)
        self.assertEqual(len(tags), 0)

    def test_pre_filter_state_policy_and_severity(self):
        """测试加州算力中心电网法案命中与 P1 烈度门禁判定."""
        item = RawNewsItem(
            id="policy_01",
            title="加州通过商业电网新规对50MW以上算力中心加征负荷基础设施费",
            content="加州公用事业委员会 (CPUC) 今日正式签署电网负荷法案，涉及商业超大规模数据中心新增税费。",
            source="California_Gazette",
            published_at="2026-11-07T07:10:00Z",
        )
        matched, tags, cat = self.engine.pre_filter(item)
        self.assertTrue(matched)
        self.assertEqual(cat, EventCategory.STATE_POLICY)

        prompt_payload = self.engine.build_summary_prompt(item, cat)
        self.assertIn("加州", prompt_payload["user"])

        summarizer = MockModelSummarizer()
        raw_json = summarizer.generate_summary_json(prompt_payload, item)
        summary = self.engine.parse_and_validate_summary(raw_json, item, cat)

        self.assertEqual(summary.severity_level, "P1")
        self.assertTrue(summary.requires_deep_analysis)
        self.assertIn("加州", "".join(summary.involved_entities))

    def test_pre_filter_physical_disruption_explosion(self):
        """测试关键原料工厂爆炸与 P1 烈度门禁判定."""
        item = RawNewsItem(
            id="plant_01",
            title="突发：某特种化工前驱体生产车间发生火灾爆炸并紧急停产",
            content="该工厂为全球先进制程光刻胶核心特种树脂关键供应商，目前全线停产抢修。",
            source="Reuters_Flash",
            published_at="2026-11-07T06:30:00Z",
        )
        matched, tags, cat = self.engine.pre_filter(item)
        self.assertTrue(matched)
        self.assertEqual(cat, EventCategory.PHYSICAL_DISRUPTION)

        summarizer = MockModelSummarizer()
        prompt_payload = self.engine.build_summary_prompt(item, cat)
        raw_json = summarizer.generate_summary_json(prompt_payload, item)
        summary = self.engine.parse_and_validate_summary(raw_json, item, cat)

        self.assertEqual(summary.severity_level, "P1")
        self.assertTrue(summary.requires_deep_analysis)
        self.assertIn("特种材料", "".join(summary.involved_entities))

    def test_pre_filter_geopolitical_sanctions_p0(self):
        """测试地缘制裁与蓝营/出口管制 P0 系统级烈度门禁判定."""
        item = RawNewsItem(
            id="geo_01",
            title="商务部宣布突发对高端芯片先进制程供应链实施定向出口管制与制裁",
            content="涉及关键实体清单调整与海峡供应链审查，立即生效。",
            source="Official_Gov_Release",
            published_at="2026-11-07T06:00:00Z",
        )
        matched, tags, cat = self.engine.pre_filter(item)
        self.assertTrue(matched)
        self.assertEqual(cat, EventCategory.GEOPOLITICAL)

        summarizer = MockModelSummarizer()
        prompt_payload = self.engine.build_summary_prompt(item, cat)
        raw_json = summarizer.generate_summary_json(prompt_payload, item)
        summary = self.engine.parse_and_validate_summary(raw_json, item, cat)

        self.assertEqual(summary.severity_level, "P0")
        self.assertTrue(summary.requires_deep_analysis)

    def test_pre_filter_supply_chain_chokepoint(self):
        """测试红海曼德海峡与苏伊士咽喉绕航初筛判定."""
        item = RawNewsItem(
            id="choke_01",
            title="红海曼德海峡商船避险改道好望角运价指数跳涨",
            content="集装箱航运枢纽苏伊士运河通行受阻，好望角绕航燃油附加费飙升。",
            source="Maritime_Flash",
            published_at="2026-11-07T05:30:00Z",
        )
        matched, tags, cat = self.engine.pre_filter(item)
        self.assertTrue(matched)
        self.assertEqual(cat, EventCategory.SUPPLY_CHAIN_CHOKEPOINT)

        summarizer = MockModelSummarizer()
        prompt_payload = self.engine.build_summary_prompt(item, cat)
        raw_json = summarizer.generate_summary_json(prompt_payload, item)
        summary = self.engine.parse_and_validate_summary(raw_json, item, cat)
        self.assertEqual(summary.severity_level, "P1")
        self.assertTrue(summary.requires_deep_analysis)

    def test_pre_filter_labor_strikes(self):
        """测试美东码头工人工会大罢工与物流瘫痪初筛判定."""
        item = RawNewsItem(
            id="labor_01",
            title="国际码头工人协会(ILA)劳资谈判破裂美东港口全面罢工运力瘫痪",
            content="美东各大港口工会工人全线离岗，集装箱装卸业务停摆，运力周转受阻。",
            source="Journal_Commerce",
            published_at="2026-11-07T05:00:00Z",
        )
        matched, tags, cat = self.engine.pre_filter(item)
        self.assertTrue(matched)
        self.assertEqual(cat, EventCategory.LABOR_STRIKES)

        summarizer = MockModelSummarizer()
        prompt_payload = self.engine.build_summary_prompt(item, cat)
        raw_json = summarizer.generate_summary_json(prompt_payload, item)
        summary = self.engine.parse_and_validate_summary(raw_json, item, cat)
        self.assertEqual(summary.severity_level, "P1")
        self.assertTrue(summary.requires_deep_analysis)
        self.assertIn("国际码头工人协会", "".join(summary.involved_entities))

    def test_pre_filter_antitrust_and_itc337(self):
        """测试美国司法部反垄断诉讼与 ITC 337 调查排除令初筛判定."""
        item = RawNewsItem(
            id="at_01",
            title="美国ITC正式针对先进制程专利侵权启动337调查并动议排除令",
            content="涉及反垄断诉讼与关键半导体架构专利侵权禁令审查。",
            source="USITC_Notice",
            published_at="2026-11-07T04:30:00Z",
        )
        matched, tags, cat = self.engine.pre_filter(item)
        self.assertTrue(matched)
        self.assertEqual(cat, EventCategory.ANTITRUST_LITIGATION)

        summarizer = MockModelSummarizer()
        prompt_payload = self.engine.build_summary_prompt(item, cat)
        raw_json = summarizer.generate_summary_json(prompt_payload, item)
        summary = self.engine.parse_and_validate_summary(raw_json, item, cat)
        self.assertEqual(summary.severity_level, "P1")
        self.assertTrue(summary.requires_deep_analysis)

    def test_pre_filter_commodity_squeeze(self):
        """测试大宗现货倒挂升水逼仓与战略石油储备(SPR)释出初筛判定."""
        item = RawNewsItem(
            id="comm_01",
            title="战略石油储备SPR招标释出且LME现货升水倒挂逼仓风险骤增",
            content="仓单注销率飙升，现货期限结构深度倒挂，逼仓挤兑提货风险加剧。",
            source="Commodity_Wire",
            published_at="2026-11-07T04:00:00Z",
        )
        matched, tags, cat = self.engine.pre_filter(item)
        self.assertTrue(matched)
        self.assertEqual(cat, EventCategory.COMMODITY_SQUEEZE)

        summarizer = MockModelSummarizer()
        prompt_payload = self.engine.build_summary_prompt(item, cat)
        raw_json = summarizer.generate_summary_json(prompt_payload, item)
        summary = self.engine.parse_and_validate_summary(raw_json, item, cat)
        self.assertEqual(summary.severity_level, "P1")
        self.assertTrue(summary.requires_deep_analysis)

    def test_pre_filter_central_bank_liquidity(self):
        """测试日元套息平仓流动性冲击与紧急贴现窗口调用初筛判定."""
        item = RawNewsItem(
            id="liq_01",
            title="日元汇率突涨引爆全球跨国套息平仓carry trade流动性挤压贴现窗口",
            content="日本央行与离岸美元流动性异动，对冲基金遭遇强制平仓潮。",
            source="FX_Macro_Wire",
            published_at="2026-11-07T03:30:00Z",
        )
        matched, tags, cat = self.engine.pre_filter(item)
        self.assertTrue(matched)
        self.assertEqual(cat, EventCategory.CENTRAL_BANK_LIQUIDITY)

        summarizer = MockModelSummarizer()
        prompt_payload = self.engine.build_summary_prompt(item, cat)
        raw_json = summarizer.generate_summary_json(prompt_payload, item)
        summary = self.engine.parse_and_validate_summary(raw_json, item, cat)
        self.assertEqual(summary.severity_level, "P0")
        self.assertTrue(summary.requires_deep_analysis)

    def test_source_credibility_tiering(self):
        """测试买方信源权威度分级判定 (Tier 1 到 Tier 4)."""
        # Tier 1: 官方监管机构与政府公报
        tier, score = self.engine.evaluate_source_credibility("USITC_Official_Gazette")
        self.assertEqual(tier.value, "Tier1_Official_Regulatory")
        self.assertEqual(score, 1.0)

        tier, score = self.engine.evaluate_source_credibility("CPUC_Proceedings")
        self.assertEqual(tier.value, "Tier1_Official_Regulatory")
        self.assertEqual(score, 1.0)

        # Tier 2: 上市公司官方IR与工会公报
        tier, score = self.engine.evaluate_source_credibility("TSMC_Investor_Relations_PR")
        self.assertEqual(tier.value, "Tier2_Official_Disclosure")
        self.assertEqual(score, 0.9)

        tier, score = self.engine.evaluate_source_credibility("ILA_Union_Official")
        self.assertEqual(tier.value, "Tier2_Official_Disclosure")
        self.assertEqual(score, 0.9)

        # Tier 3: 主流财经通讯社
        tier, score = self.engine.evaluate_source_credibility("Reuters_Industrial_Wire")
        self.assertEqual(tier.value, "Tier3_Mainstream_Wire")
        self.assertEqual(score, 0.8)

        # Tier 4: 社交媒体网络快讯
        tier, score = self.engine.evaluate_source_credibility("X_Social_Flash_Anonymous")
        self.assertEqual(tier.value, "Tier4_Public_Flash_Social")
        self.assertEqual(score, 0.45)

    def test_rumor_circuit_breaker_blocks_deep_analysis(self):
        """测试传闻熔断门禁：来自 Tier 4 的小道传闻即使命中高危物理关键词也强制熔断深研."""
        item = RawNewsItem(
            id="rumor_test_01",
            title="据社交媒体传闻某先进制程晶圆厂突发爆炸停产",
            content="未经核实的小道消息称某晶圆厂停产检修，官方目前未发布任何公告。",
            source="X_Social_Rumor_Flash",
            published_at="2026-11-07T09:00:00Z",
        )
        matched, tags, cat = self.engine.pre_filter(item)
        self.assertTrue(matched)

        summarizer = MockModelSummarizer()
        prompt_payload = self.engine.build_summary_prompt(item, cat)
        raw_json = summarizer.generate_summary_json(prompt_payload, item)
        summary = self.engine.parse_and_validate_summary(raw_json, item, cat)

        # 核心断言：命中爆炸停产通常提升为 P1，但因信源为 Tier 4 且含传闻字样，必须被判定为 Unverified_Rumor 且深研门禁被强制熔断
        self.assertEqual(summary.verification_status, "Unverified_Rumor")
        self.assertFalse(summary.requires_deep_analysis)
        self.assertIn("熔断门禁", summary.verification_note)


class TestNetworkHealthWatchdog(unittest.TestCase):
    """测试自发断网检测与自治恢复看门狗."""

    def test_watchdog_connectivity_live(self):
        """测试常规网络探针探测能力 (若本机环境离线则优雅返回 False)."""
        watchdog = NetworkHealthWatchdog(timeout_sec=1.0)
        is_online, node, lat = watchdog.check_connectivity()
        # 无论在线还是离线，探针必须返回布尔值和非空字符串，绝不抛出未捕获异常
        self.assertIsInstance(is_online, bool)
        self.assertIsInstance(node, str)
        self.assertIsInstance(lat, float)

    def test_watchdog_offline_simulation_and_backoff(self):
        """测试断网模拟时指数退避与重试机制."""
        # 设置必然失败的虚拟 IP 与端口 (RFC 5737 测试 IP)
        unreachable_probes = [{"host": "192.0.2.1", "port": 53, "provider": "Test_Unreachable"}]
        watchdog = NetworkHealthWatchdog(
            probe_endpoints=unreachable_probes,
            timeout_sec=0.1,
            max_offline_retries=3,
            backoff_intervals=[0.01, 0.02, 0.03],
        )

        status_logs = []

        def record_status(state: str, msg: str):
            status_logs.append((state, msg))

        # 模拟执行休眠，使用即时 dummy sleep
        def dummy_sleep(s: float):
            pass

        recovered = watchdog.wait_for_recovery(
            max_retries=3,
            sleep_func=dummy_sleep,
            on_status_change=record_status,
        )

        self.assertFalse(recovered)
        self.assertGreaterEqual(len(status_logs), 3)
        self.assertEqual(status_logs[-1][0], "RETRY_EXHAUSTED")


class TestRadarProgressManager(unittest.TestCase):
    """测试断点续传、SHA-256 唯一指纹排重与状态管理."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ckpt_path = Path(self.temp_dir.name) / "test_checkpoint.json"
        self.mgr = RadarProgressManager(checkpoint_path=str(self.ckpt_path))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_deduplication_and_watermark_save(self):
        """测试文章指纹排重与状态保存恢复."""
        hash_val = "abc123def456"
        self.assertFalse(self.mgr.is_hash_processed(hash_val))

        self.mgr.record_processed_hash(hash_val)
        self.assertTrue(self.mgr.is_hash_processed(hash_val))

        cycle_metrics = {
            "scanned": 10,
            "filtered_in": 3,
            "summarized": 3,
            "p0_p1_triggered": 1,
            "estimated_tokens": 330,
        }
        self.mgr.save_checkpoint("2026-11-07T08:00:00Z", cycle_metrics)
        self.assertTrue(self.ckpt_path.is_file())

        # 重建一个新实例，测试从落盘文件无损读取
        new_mgr = RadarProgressManager(checkpoint_path=str(self.ckpt_path))
        self.assertTrue(new_mgr.is_hash_processed(hash_val))
        self.assertEqual(new_mgr.state["last_successful_timestamp"], "2026-11-07T08:00:00Z")
        self.assertEqual(new_mgr.state["cumulative_metrics"]["total_scanned"], 10)
        self.assertEqual(new_mgr.state["cumulative_metrics"]["total_p0_p1_triggered"], 1)


class TestRadarDatabaseManager(unittest.TestCase):
    """测试事件雷达 SQLite 数据库持久化、结构化查询与统计."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_event_radar.sqlite3"
        self.db_mgr = RadarDatabaseManager(db_path=str(self.db_path))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_insert_and_query_events(self):
        """测试事件入库与按烈度等级筛选."""
        item = RawNewsItem(
            id="db_item_01",
            title="加州通过商业算力电网新规",
            content="加州公用事业委员会签署法案",
            source="California_Gazette",
            published_at="2026-11-07T08:00:00Z",
        )
        summary = StructuredEventSummary(
            event_id="EVT_CALIF_001",
            timestamp="2026-11-07T08:00:00Z",
            category="State_Policy_Regulatory",
            involved_entities=["加州能源委员会", "商业算力中心"],
            micro_physical_impact="加州对50MW以上商业算力中心加征电网负荷费",
            estimated_duration="长期法定",
            affected_business_segments=["云计算中心", "电力"],
            severity_level="P1",
            requires_deep_analysis=True,
            raw_title=item.title,
            source_name=item.source,
        )

        self.db_mgr.insert_event(summary, item, "2026-11-07T08:05:00Z")
        events = self.db_mgr.query_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_id"], "EVT_CALIF_001")
        self.assertEqual(events[0]["severity_level"], "P1")
        self.assertTrue(events[0]["requires_deep_analysis"])
        self.assertIn("加州能源委员会", events[0]["involved_entities"])
        self.assertEqual(events[0]["credibility_tier"], "Tier3_Mainstream_Wire")
        self.assertEqual(events[0]["credibility_score"], 0.8)
        self.assertEqual(events[0]["verification_status"], "Corroborated_Report")

        # 测试仅筛选重大 P0/P1 事件
        major_events = self.db_mgr.query_events(severity_filter=["P0", "P1"], only_requires_deep=True)
        self.assertEqual(len(major_events), 1)

        # 测试 P3 筛选无结果
        p3_events = self.db_mgr.query_events(severity_filter=["P3"])
        self.assertEqual(len(p3_events), 0)

    def test_database_cycle_insert_and_stats(self):
        """测试巡检轮次审计入库与全量统计指标."""
        cycle_report = {
            "timestamp": "2026-11-07T08:10:00Z",
            "market_session": "pre_market",
            "status": "SUCCESS",
            "active_probe_node": "Google_Public_DNS (8.8.8.8:53)",
            "probe_latency_ms": 1.5,
            "scanned_count": 20,
            "filtered_in_count": 5,
            "summarized_count": 5,
            "p0_p1_triggered_count": 2,
            "estimated_tokens_consumed": 550,
        }
        self.db_mgr.insert_cycle(cycle_report)
        cycles = self.db_mgr.query_cycles()
        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0]["market_session"], "pre_market")
        self.assertEqual(cycles[0]["scanned_count"], 20)

        stats = self.db_mgr.query_summary_statistics()
        self.assertEqual(stats["total_cycles_executed"], 1)
        self.assertEqual(stats["total_scanned_news"], 20)
        self.assertEqual(stats["total_summarized"], 5)
        self.assertEqual(stats["total_tokens_burned"], 550)


class TestEventRadarCollectorEndToEnd(unittest.TestCase):
    """测试收集器端到端调度、极低 Token 消耗与门禁触发."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ckpt_path = Path(self.temp_dir.name) / "test_ckpt.json"
        self.db_path = Path(self.temp_dir.name) / "test_event_radar.sqlite3"
        self.cfg_path = Path(self.temp_dir.name) / "test_config.json"

        # 写入简版配置
        cfg_data = {
            "network_watchdog": {
                "timeout_seconds": 0.5,
                "max_offline_retries": 1,
                "backoff_intervals_seconds": [0.01],
            },
            "progress_management": {
                "checkpoint_file": str(self.ckpt_path),
                "database_file": str(self.db_path),
                "max_hash_history_size": 100,
            },
            "scheduler": {
                "polling_intervals_minutes": {
                    "pre_market": 5,
                    "regular_market": 15,
                    "market_closed": 60,
                }
            },
        }
        with open(self.cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg_data, f)

        # 构造常开在线看门狗
        class AlwaysOnlineWatchdog(NetworkHealthWatchdog):
            def check_connectivity(self):
                return True, "Mock_Online_Node", 1.2

        self.watchdog = AlwaysOnlineWatchdog()
        self.progress_mgr = RadarProgressManager(checkpoint_path=str(self.ckpt_path))
        self.db_mgr = RadarDatabaseManager(db_path=str(self.db_path))
        self.collector = EventRadarCollector(
            config_path=str(self.cfg_path),
            watchdog=self.watchdog,
            progress_manager=self.progress_mgr,
            database_manager=self.db_mgr,
            model_client=MockModelSummarizer(),
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_collector_cycle_with_filtering_and_idempotence(self):
        """测试收集周期：过滤掉噪音、总结重要事件、二次执行幂等 0 Token."""
        test_feed = [
            {
                "id": "1",
                "title": "今日收评：五大行业大涨揭秘",
                "content": "广告推广，点击查看详情。",
                "source": "Noise_Feed",
            },
            {
                "id": "2",
                "title": "加州通过法案要求算力中心电网基础设施负担专项费",
                "content": "加州立法机关正式签署通过算力中心电网监管法案。",
                "source": "California_Policy_Feed",
            },
            {
                "id": "3",
                "title": "某关键半导体材料工厂发生突发火灾爆炸停产",
                "content": "为全球主要晶圆厂供应关键化学品的生产车间停工检修。",
                "source": "Global_Disruption_Feed",
            },
            {
                "id": "4",
                "title": "某地足球联赛决赛落幕",
                "content": "现场观众气氛热烈，球员发表赛后感言。",
                "source": "Sports_Feed",
            },
        ]

        # 第一轮执行：扫描 4 篇，初筛命中 2 篇，模型摘要 2 篇，触发 P0/P1 2 篇
        result_1 = self.collector.run_collection_cycle(test_feed)
        self.assertEqual(result_1["status"], "SUCCESS")
        self.assertEqual(result_1["scanned_count"], 4)
        self.assertEqual(result_1["filtered_in_count"], 2)
        self.assertEqual(result_1["summarized_count"], 2)
        self.assertEqual(result_1["p0_p1_triggered_count"], 2)
        self.assertEqual(len(result_1["triggered_events"]), 2)
        self.assertEqual(result_1["estimated_tokens_consumed"], 220)

        # 第二轮执行：传入完全相同的资讯流 -> 必须全部被 SHA-256 拦截，0 摘要，0 Token！
        result_2 = self.collector.run_collection_cycle(test_feed)
        self.assertEqual(result_2["status"], "SUCCESS")
        self.assertEqual(result_2["scanned_count"], 4)
        self.assertEqual(result_2["filtered_in_count"], 0)
        self.assertEqual(result_2["summarized_count"], 0)
        self.assertEqual(result_2["p0_p1_triggered_count"], 0)
        self.assertEqual(result_2["estimated_tokens_consumed"], 0)

        # 验证 SQLite 数据库已落盘 2 条摘要事件与巡检记录
        db_events = self.collector.query_stored_events()
        self.assertEqual(len(db_events), 2)
        major_db_events = self.collector.query_stored_events(only_requires_deep=True)
        self.assertEqual(len(major_db_events), 2)
        db_cycles = self.collector.query_stored_cycles()
        self.assertGreaterEqual(len(db_cycles), 1)
        stats = self.collector.query_stored_statistics()
        self.assertEqual(stats["total_events_stored"], 2)
        self.assertEqual(stats["total_major_p0_p1"], 2)

    def test_collector_offline_graceful_hold(self):
        """测试在断网状态下收集器平滑挂起，不抛出任何异常崩溃."""
        class AlwaysOfflineWatchdog(NetworkHealthWatchdog):
            def check_connectivity(self):
                return False, "OFFLINE", -1.0

            def wait_for_recovery(self, max_retries=None, sleep_func=None, on_status_change=None):
                return False

        offline_collector = EventRadarCollector(
            config_path=str(self.cfg_path),
            watchdog=AlwaysOfflineWatchdog(),
            progress_manager=self.progress_mgr,
        )

        res = offline_collector.run_collection_cycle([{"title": "test", "content": "test"}])
        self.assertEqual(res["status"], "OFFLINE_HOLD")
        self.assertEqual(res["scanned_count"], 0)
        self.assertIn("网络处于断开状态", res["message"])


class TestEventRadarService(unittest.TestCase):
    """测试事件雷达 CLI 守护与调度中枢服务."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ckpt_path = Path(self.temp_dir.name) / "test_service_ckpt.json"
        self.db_path = Path(self.temp_dir.name) / "test_service_radar.sqlite3"
        self.cfg_path = Path(self.temp_dir.name) / "test_service_config.json"

        cfg_data = {
            "network_watchdog": {
                "timeout_seconds": 0.5,
                "max_offline_retries": 1,
                "backoff_intervals_seconds": [0.01],
            },
            "progress_management": {
                "checkpoint_file": str(self.ckpt_path),
                "database_file": str(self.db_path),
                "max_hash_history_size": 100,
            },
            "scheduler": {
                "polling_intervals_minutes": {
                    "pre_market": 5,
                    "regular_market": 15,
                    "market_closed": 60,
                }
            },
        }
        with open(self.cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg_data, f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_service_run_single_cycle_and_shutdown(self):
        """测试服务单次巡检调度与优雅停机信号."""
        class MockOnlineWatchdog(NetworkHealthWatchdog):
            def check_connectivity(self):
                return True, "Mock_Online_Test_Node", 1.0

        collector = EventRadarCollector(
            config_path=str(self.cfg_path),
            watchdog=MockOnlineWatchdog(),
            progress_manager=RadarProgressManager(checkpoint_path=str(self.ckpt_path)),
            database_manager=RadarDatabaseManager(db_path=str(self.db_path)),
            model_client=MockModelSummarizer(),
        )

        service = EventRadarService(
            config_path=str(self.cfg_path),
            auto_generate_reports=False,
            collector=collector,
        )

        test_feed = [
            {
                "id": "svc_test_01",
                "title": "某关键半导体材料工厂发生突发火灾爆炸停产",
                "content": "为全球主要晶圆厂供应关键化学品的生产车间停工检修。",
                "source": "Global_Disruption_Feed",
            }
        ]

        # 执行单轮次巡检
        cycle_result = service.run_single_cycle(raw_feed_items=test_feed)
        self.assertEqual(cycle_result["status"], "SUCCESS")
        self.assertEqual(cycle_result["scanned_count"], 1)
        self.assertEqual(cycle_result["p0_p1_triggered_count"], 1)

        # 验证状态打印输出
        captured_out = io.StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = captured_out
            service.print_status()
        finally:
            sys.stdout = old_stdout

        output_text = captured_out.getvalue()
        self.assertIn("【突发事件雷达系统 · 运行状态与账本审计】", output_text)
        self.assertIn("已持久化事件总量", output_text)
        self.assertIn("P0/P1 重大事件总数", output_text)

        # 测试优雅停机信号触发
        self.assertTrue(service._is_running)
        service._handle_shutdown(signal.SIGINT, None)
        self.assertFalse(service._is_running)


if __name__ == "__main__":
    unittest.main()
