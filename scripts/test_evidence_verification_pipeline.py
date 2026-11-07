"""AI 浏览器定向补数与信源法定鉴真流水线自动化单元测试.

测试覆盖范围:
1. SHA-256 密码学指纹精确计算与越界路径安全防御 (Boundary Defense);
2. 单事件官方公报验签、信源升格与传闻熔断解除 (Circuit Breaker Lifting);
3. 收件箱 (Inbox) 自动扫描、智能正则提取事件 ID 与批量归档解封;
4. 密码学防伪收据记录与审计追踪账本持久化;
5. 待补数与熔断中事件清单筛选逻辑。
"""

import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finance_tools.event_radar_collector import RadarDatabaseManager, RawNewsItem
from finance_tools.evidence_verification_pipeline import EvidenceVerificationPipeline
from financial_core.engines.event_radar_engine import StructuredEventSummary


class TestEvidenceVerificationPipeline(unittest.TestCase):
    """法定证据验签与传闻熔断解封流水线核心测试集."""

    def setUp(self):
        # 创建位于项目根目录内的隔离测试临时目录以满足安全路径断言
        self.test_dir = PROJECT_ROOT / f".cache/test_evidence_{int(datetime.now().timestamp())}"
        self.test_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.test_dir / "test_radar.sqlite3"
        self.inbox_dir = self.test_dir / "inbox"
        self.archive_dir = self.test_dir / "archive"
        self.receipts_path = self.test_dir / "receipts.json"

        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        # 初始化临时数据库
        self.db_mgr = RadarDatabaseManager(db_path=str(self.db_path))

        # 预插一条测试传闻事件 (处于熔断状态)
        self.test_event_id = "EVT_TEST_RUMOR_8888"
        now_iso = datetime.now(timezone.utc).isoformat()
        item = RawNewsItem(
            id="test_rumor_raw_01",
            title="网络传闻某芯片工厂发生事故停产",
            content="未经证实网络快讯小道传闻",
            source="Twitter_Flash",
            published_at=now_iso,
            url="https://example.com/rumor",
        )
        summary = StructuredEventSummary(
            event_id=self.test_event_id,
            timestamp=now_iso,
            category="Physical_Plant_Disruption",
            involved_entities=["TSMC"],
            micro_physical_impact="小道快讯传闻，无官方公报证实",
            estimated_duration="未知",
            affected_business_segments=["先进制程代工"],
            severity_level="P1",
            requires_deep_analysis=False,
            raw_title="网络传闻某芯片工厂发生事故停产",
            source_name="Twitter_Flash",
            credibility_tier="Tier4_Public_Flash_Social",
            credibility_score=0.45,
            verification_status="Unverified_Rumor",
            verification_note="社交网络快讯传闻，待核实",
        )
        self.db_mgr.insert_event(summary, item, collected_at=now_iso)

        # 初始化待测流水线 (禁用自动更新主看板以保持纯净)
        self.pipeline = EvidenceVerificationPipeline(
            db_path=str(self.db_path),
            evidence_inbox_dir=str(self.inbox_dir.relative_to(PROJECT_ROOT)),
            archive_dir=str(self.archive_dir.relative_to(PROJECT_ROOT)),
            receipts_path=str(self.receipts_path.relative_to(PROJECT_ROOT)),
            auto_refresh_reports=False,
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_sha256_computation_and_safety_checks(self):
        """测试 SHA-256 计算与越界路径安全防御."""
        sample_file = self.test_dir / "sample_official_sec_8k.txt"
        sample_content = b"SEC Form 8-K: Official report on physical facility minor inspection."
        sample_file.write_bytes(sample_content)

        expected_hash = hashlib.sha256(sample_content).hexdigest()
        actual_hash = self.pipeline.compute_sha256(sample_file)
        self.assertEqual(actual_hash, expected_hash)

        # 验证合法路径解析
        p, rel = self.pipeline.validate_file_safety(sample_file)
        self.assertEqual(p, sample_file.resolve())
        self.assertTrue(rel.startswith(".cache/"))

        # 验证越界外部路径应被刚性拒绝 (PermissionError)
        with self.assertRaises(PermissionError):
            outside_path = Path("C:/Windows/System32/drivers/etc/hosts")
            self.pipeline.validate_file_safety(outside_path)

        # 验证不存在文件抛出 FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            self.pipeline.validate_file_safety(self.test_dir / "non_existent.txt")

    def test_verify_single_event_and_circuit_breaker_lifting(self):
        """测试单事件法定公报核验、SHA-256 验签与传闻熔断彻底解除."""
        evidence_file = self.test_dir / "sec_official_filing_verified.pdf"
        evidence_file.write_text("Official confirmation of industrial recovery.", encoding="utf-8")

        receipt = self.pipeline.verify_single_event(
            event_id=self.test_event_id,
            evidence_file=evidence_file,
            note="分析师核验 SEC 官方文件确认属实",
            archive_copy=False,
        )

        # 1. 验证返回的收据
        self.assertEqual(receipt["event_id"], self.test_event_id)
        self.assertEqual(receipt["new_status"], "Confirmed_Fact")
        self.assertEqual(receipt["new_credibility"], "Tier1_Official_Regulatory")
        self.assertTrue(receipt["circuit_breaker_lifted"])
        self.assertGreater(len(receipt["evidence_sha256"]), 32)

        # 2. 验证数据库中该事件已被升格
        updated_evt = self.db_mgr.get_event_by_id(self.test_event_id)
        self.assertEqual(updated_evt["verification_status"], "Confirmed_Fact")
        self.assertEqual(updated_evt["credibility_tier"], "Tier1_Official_Regulatory")
        self.assertEqual(updated_evt["credibility_score"], 1.0)
        self.assertTrue(updated_evt["requires_deep_analysis"])
        self.assertIsNotNone(updated_evt["verified_at"])

        # 3. 验证收据持久化账本
        receipts = self.pipeline.load_receipts()
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["event_id"], self.test_event_id)

    def test_scan_and_process_inbox(self):
        """测试收件箱自动扫描、正则匹配事件编号与批量验签入库."""
        # 在 inbox 中放入以事件 ID 命名的证据文件
        inbox_file = self.inbox_dir / f"download_{self.test_event_id}_regulatory_notice.txt"
        inbox_file.write_text("Notice from Regulatory Authority confirming fact.", encoding="utf-8")

        receipts = self.pipeline.scan_and_process_inbox()
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["event_id"], self.test_event_id)

        # 验证文件已被归档移出收件箱
        self.assertFalse(inbox_file.exists())

        # 验证数据库状态已转为 Confirmed_Fact
        updated_evt = self.db_mgr.get_event_by_id(self.test_event_id)
        self.assertEqual(updated_evt["verification_status"], "Confirmed_Fact")

    def test_list_pending_verification_events(self):
        """测试待核验事件清单筛选."""
        pending = self.pipeline.list_pending_verification_events()
        self.assertGreaterEqual(len(pending), 1)
        self.assertEqual(pending[0]["event_id"], self.test_event_id)
        self.assertEqual(pending[0]["current_status"], "Unverified_Rumor")


if __name__ == "__main__":
    unittest.main()
