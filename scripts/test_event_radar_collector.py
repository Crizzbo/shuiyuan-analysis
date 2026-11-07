"""单元测试：事件雷达收集器、自发断网检测、进度管理与事件触发门禁 (Phase 1)."""

import json
import os
from pathlib import Path
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
    MockModelSummarizer,
    EventRadarCollector,
)


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


class TestEventRadarCollectorEndToEnd(unittest.TestCase):
    """测试收集器端到端调度、极低 Token 消耗与门禁触发."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ckpt_path = Path(self.temp_dir.name) / "test_ckpt.json"
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
        self.collector = EventRadarCollector(
            config_path=str(self.cfg_path),
            watchdog=self.watchdog,
            progress_manager=self.progress_mgr,
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


if __name__ == "__main__":
    unittest.main()
