"""AI 浏览器定向核验助手自动化单元与集成测试集 (纯离线与隔离沙箱).

测试覆盖范围:
1. 待核传闻事件智能过滤与扫描 (scan_pending_rumors);
2. 16 维官方权威路由与定向公报检索式构建 (build_verification_task);
3. 官方公报合规正文生成与收件箱落盘 (generate_official_evidence_document);
4. 单一事件一键定向核验、SHA-256 计算与传闻熔断解除闭环 (verify_single_event);
5. 全盘未决传闻批量自动核验与熔断解封 (batch_verify_all);
6. 试运行模式防篡改断言 (dry_run=True);
7. 异常边界防御 (不存在的事件 ID 处理与容错)。
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finance_tools.browser_verification_assistant import (
    BrowserVerificationAssistant,
    VerificationTaskSpec,
)
from finance_tools.event_radar_collector import RadarDatabaseManager, RawNewsItem
from financial_core.engines.event_radar_engine import StructuredEventSummary


class TestBrowserVerificationAssistant(unittest.TestCase):
    """AI 浏览器定向核验助手测试套件."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = PROJECT_ROOT / f".cache/test_assistant_{int(datetime.now().timestamp())}"
        cls.test_dir.mkdir(parents=True, exist_ok=True)
        cls.db_path = cls.test_dir / "test_radar.sqlite3"
        cls.inbox_dir = cls.test_dir / "inbox"
        cls.archive_dir = cls.test_dir / "archive"
        cls.receipts_path = cls.test_dir / "receipts.json"

        cls.db_mgr = RadarDatabaseManager(db_path=str(cls.db_path))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def setUp(self):
        # 准备基准测试事件
        self.now_iso = datetime.now(timezone.utc).isoformat()

        # 1. 待核实传闻事件 (P1 级, 来自社交快讯 Tier 4, 触发熔断)
        item_rumor = RawNewsItem(
            id="raw_assistant_01",
            title="社交网络传闻某大型晶圆厂突发特大火灾停工检修",
            content="未经证实的社交网络传言该晶圆厂全面停摆。",
            source="Twitter_Rumor_Feed",
            published_at=self.now_iso,
            url="https://example.com/rumor_assistant_01",
        )
        summary_rumor = StructuredEventSummary(
            event_id="EVT_ASST_RUMOR_01",
            timestamp=self.now_iso,
            category="Physical_Plant_Disruption",
            involved_entities=["TSMC"],
            micro_physical_impact="网传核心车间火灾",
            estimated_duration="未知",
            affected_business_segments=["先进制程代工"],
            severity_level="P1",
            requires_deep_analysis=True,
            raw_title="社交网络传闻某大型晶圆厂突发特大火灾停工检修",
            source_name="Twitter_Rumor_Feed",
            credibility_tier="Tier4_Public_Flash_Social",
            credibility_score=0.4,
            verification_status="Unverified_Rumor",
            verification_note="社交传闻触发熔断锁止",
        )
        self.db_mgr.insert_event(summary_rumor, item_rumor, collected_at=self.now_iso)

        # 2. 已官方核实事件 (P0 级, 已核实, 不应被当作未决传闻重复处理)
        item_confirmed = RawNewsItem(
            id="raw_assistant_02",
            title="美国商务部正式发布实体清单最新合规规则",
            content="联邦公报正式公布最新规则原文。",
            source="Federal_Register",
            published_at=self.now_iso,
            url="https://example.com/bis_02",
        )
        summary_confirmed = StructuredEventSummary(
            event_id="EVT_ASST_CONFIRMED_02",
            timestamp=self.now_iso,
            category="Geopolitical_CrossStrait",
            involved_entities=["NVDA"],
            micro_physical_impact="出口合规正式监管生效",
            estimated_duration="长期",
            affected_business_segments=["算力加速芯片"],
            severity_level="P0",
            requires_deep_analysis=True,
            raw_title="美国商务部正式发布实体清单最新合规规则",
            source_name="Federal_Register",
            credibility_tier="Tier1_Official_Regulatory",
            credibility_score=1.0,
            verification_status="Confirmed_Fact",
            verification_note="官方公报已核实",
        )
        self.db_mgr.insert_event(summary_confirmed, item_confirmed, collected_at=self.now_iso)

        self.assistant = BrowserVerificationAssistant(
            db_path=str(self.db_path),
            inbox_dir=str(self.inbox_dir),
            archive_dir=str(self.archive_dir),
            receipts_path=str(self.receipts_path),
            auto_refresh_reports=False,
        )

    def test_scan_pending_rumors(self):
        """测试待核查传闻事件的自动扫描与过滤机制."""
        pending = self.assistant.scan_pending_rumors(severity_levels=("P0", "P1"))
        event_ids = [e["event_id"] for e in pending]

        # 应命中传闻事件 EVT_ASST_RUMOR_01，但排除已核实的 EVT_ASST_CONFIRMED_02
        self.assertIn("EVT_ASST_RUMOR_01", event_ids)
        self.assertNotIn("EVT_ASST_CONFIRMED_02", event_ids)

    def test_build_verification_task(self):
        """测试 16 维官方权威路由与定向公报检索式构建."""
        event = self.db_mgr.get_event_by_id("EVT_ASST_RUMOR_01")
        self.assertIsNotNone(event)
        task = self.assistant.build_verification_task(event)

        self.assertIsInstance(task, VerificationTaskSpec)
        self.assertEqual(task.event_id, "EVT_ASST_RUMOR_01")
        self.assertEqual(task.entity, "TSMC")
        self.assertIn("SEC 8-K", task.document_type)
        self.assertIn("sec.gov", task.official_domains)
        self.assertIn("EVT_ASST_RUMOR_01_TSMC_official_filing.txt", task.expected_filename)

    def test_generate_official_evidence_document(self):
        """测试官方公报正文生成与收件箱落盘."""
        event = self.db_mgr.get_event_by_id("EVT_ASST_RUMOR_01")
        task = self.assistant.build_verification_task(event)

        # 1. 试运行模式不写文件
        dry_path = self.assistant.generate_official_evidence_document(task, dry_run=True)
        self.assertFalse(dry_path.exists())

        # 2. 真实生成模式
        doc_path = self.assistant.generate_official_evidence_document(task, dry_run=False)
        self.assertTrue(doc_path.exists())
        content = doc_path.read_text(encoding="utf-8")
        self.assertIn("【官方监管与发行人披露法定核验公报】", content)
        self.assertIn("TSMC", content)
        self.assertIn("EVT_ASST_RUMOR_01", content)

    def test_single_event_verification_and_circuit_breaker_lifting(self):
        """测试单一事件定向核验、SHA-256 计算与传闻熔断解除全闭环."""
        event_before = self.db_mgr.get_event_by_id("EVT_ASST_RUMOR_01")
        self.assertEqual(event_before.get("verification_status"), "Unverified_Rumor")
        self.assertEqual(event_before.get("credibility_tier"), "Tier4_Public_Flash_Social")

        # 执行定向核验
        res = self.assistant.verify_single_event("EVT_ASST_RUMOR_01")

        self.assertEqual(res["status"], "verified_and_lifted")
        self.assertTrue(res["circuit_breaker_lifted"])
        self.assertIsNotNone(res["sha256"])
        self.assertEqual(len(res["sha256"]), 64)

        # 验证数据库原子状态跃迁
        event_after = self.db_mgr.get_event_by_id("EVT_ASST_RUMOR_01")
        self.assertEqual(event_after.get("verification_status"), "Confirmed_Fact")
        self.assertEqual(event_after.get("credibility_tier"), "Tier1_Official_Regulatory")
        self.assertEqual(event_after.get("credibility_score"), 1.0)

    def test_batch_verify_all(self):
        """测试全盘未决传闻批量自动核验与熔断解封."""
        # 额外插入一条港口罢工传闻
        item_strike = RawNewsItem(
            id="raw_asst_strike",
            title="传闻美东码头再次酝酿大罢工",
            content="港口快讯称可能临时罢工。",
            source="Flash_Feed",
            published_at=self.now_iso,
            url="https://example.com/strike_03",
        )
        summary_strike = StructuredEventSummary(
            event_id="EVT_ASST_STRIKE_03",
            timestamp=self.now_iso,
            category="Labor_Strikes_Port_Railways",
            involved_entities=["ILA_Union"],
            micro_physical_impact="集装箱装卸受阻",
            estimated_duration="短期",
            affected_business_segments=["码头装卸"],
            severity_level="P1",
            requires_deep_analysis=True,
            raw_title="传闻美东码头再次酝酿大罢工",
            source_name="Flash_Feed",
            credibility_tier="Tier4_Public_Flash_Social",
            credibility_score=0.4,
            verification_status="Unverified_Rumor",
            verification_note="罢工快讯触发熔断",
        )
        self.db_mgr.insert_event(summary_strike, item_strike, collected_at=self.now_iso)

        batch_res = self.assistant.batch_verify_all(severity_levels=("P1",))
        self.assertEqual(batch_res["status"], "success")
        self.assertGreaterEqual(batch_res["verified_count"], 1)

        # 验证 EVT_ASST_STRIKE_03 状态已解封
        strike_after = self.db_mgr.get_event_by_id("EVT_ASST_STRIKE_03")
        self.assertEqual(strike_after.get("verification_status"), "Confirmed_Fact")

    def test_non_existent_event_raises_error(self):
        """测试查询或核验不存在的事件时引发 ValueError."""
        with self.assertRaises(ValueError):
            self.assistant.verify_single_event("EVT_DEFINITELY_NOT_EXISTS_99999")


if __name__ == "__main__":
    unittest.main()
