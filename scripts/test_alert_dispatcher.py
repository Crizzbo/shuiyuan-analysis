"""突发事件多通道告警分发器与全天候常驻调度自动化单元测试.

测试覆盖范围:
1. SSOT 配置文件级联自发现与默认安全回退加载;
2. 告警烈度过滤门槛 (P0/P1) 与防刷屏冷却窗口 (Cooldown);
3. 实体与标的代码 (Ticker) 智能模糊映射;
4. 传闻熔断门禁前置拦截与通俗商业语言卡片呈现;
5. 权威信源准入后的 SOTP 业务分部因果自动穿透与财务损益测算;
6. 控制台、文件日志底账、Windows 原生弹窗安全容错分发。
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finance_tools.alert_dispatcher import (
    ACTION_ZH_MAP,
    AlertDispatcher,
    COMPANY_TICKER_MAP,
)
from financial_core.engines.sotp_event_penetration_engine import (
    BusinessSegment,
    CompanySotpProfile,
    EnterpriseEventImpactResult,
    SegmentCausalImpact,
    SotpEventPenetrationEngine,
)


class TestAlertDispatcher(unittest.TestCase):
    """突发重大事件告警分发系统核心功能测试集."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="radar_alert_test_")
        self.log_file = Path(self.temp_dir) / "test_alerts.log"
        self.custom_config = {
            "alert_level_threshold": "P0_AND_P1",
            "cooldown_seconds": 2,
            "auto_trigger_sotp": True,
            "max_entities_to_penetrate": 2,
            "channels": {
                "console": {"enabled": True, "show_sotp_summary": True, "use_color": False},
                "desktop_toast": {"enabled": False, "duration_seconds": 3, "sound": False},
                "file_log": {"enabled": True, "log_path": str(self.log_file)},
                "webhook": {"enabled": False, "url": "", "token": "", "platform": "generic"},
            },
        }
        self.config_file = Path(self.temp_dir) / "custom_alert_config.json"
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.custom_config, f, ensure_ascii=False, indent=2)

        self.dispatcher = AlertDispatcher(config_path=str(self.config_file))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ssot_config_loading(self):
        """测试外置配置的正确加载与级联探测."""
        self.assertEqual(self.dispatcher.config["alert_level_threshold"], "P0_AND_P1")
        self.assertEqual(self.dispatcher.config["cooldown_seconds"], 2)

        # 测试不存在文件时的默认回退
        fallback_dispatcher = AlertDispatcher(config_path=str(Path(self.temp_dir) / "non_existent.json"))
        self.assertIn("alert_level_threshold", fallback_dispatcher.config)
        self.assertIn("cooldown_seconds", fallback_dispatcher.config)

    def test_severity_filter_and_cooldown(self):
        """测试烈度门槛过滤与防刷屏冷却窗口."""
        # 1. P2 事件应被拦截
        p2_event = {
            "event_id": "EVT_TEST_P2",
            "title": "常规微观小道消息",
            "severity_level": "P2",
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
        ok, reason = self.dispatcher.should_alert(p2_event)
        self.assertFalse(ok)
        self.assertIn("未达到P0/P1烈度门槛", reason)

        # 2. P0 事件满足条件
        p0_event = {
            "event_id": "EVT_TEST_P0",
            "title": "某要害化工厂突发爆炸事故",
            "severity_level": "P0",
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
        ok, reason = self.dispatcher.should_alert(p0_event)
        self.assertTrue(ok)

        # 3. 首次分发成功
        res1 = self.dispatcher.dispatch_event_alert(p0_event)
        self.assertTrue(res1["dispatched"])

        # 4. 立即再次分发应触发冷却静音拦截
        ok2, reason2 = self.dispatcher.should_alert(p0_event)
        self.assertFalse(ok2)
        self.assertIn("处于冷却静音期", reason2)
        res2 = self.dispatcher.dispatch_event_alert(p0_event)
        self.assertFalse(res2["dispatched"])

    def test_match_entities_to_tickers(self):
        """测试自然语言公司实体识别与标准 Ticker 转换."""
        entities = ["台积电", "NVIDIA", "未知机构X", "ASML", "apple"]
        tickers = self.dispatcher.match_entities_to_tickers(entities)
        self.assertIn("TSM", tickers)
        self.assertIn("NVDA", tickers)
        self.assertIn("ASML", tickers)
        self.assertIn("AAPL", tickers)
        self.assertNotIn("未知机构X", tickers)

    def test_rumor_circuit_breaker_alert(self):
        """测试传闻熔断门禁激活时的卡片呈现与 SOTP 拦截."""
        rumor_event = {
            "event_id": "EVT_RUMOR_01",
            "title": "网络快讯传闻某晶圆厂停工检修",
            "category": "Physical_Plant_Disruption",
            "severity_level": "P1",
            "source_name": "X_Flash_News",
            "credibility_tier": "Tier4_Public_Flash_Social",
            "credibility_score": 0.45,
            "verification_status": "Unverified_Rumor",
            "micro_physical_impact": "网络未经核实小道传闻",
            "involved_entities": ["TSMC"],
            "published_at": datetime.now(timezone.utc).isoformat(),
        }

        res = self.dispatcher.dispatch_event_alert(rumor_event)
        self.assertTrue(res["dispatched"])

        # 验证卡片文本包含传闻熔断标识
        sotp_results = self.dispatcher.execute_sotp_penetration(rumor_event)
        card = self.dispatcher.format_alert_card(rumor_event, sotp_results)

        self.assertIn("待核传闻", card)
        self.assertIn("传闻熔断", card)
        if sotp_results:
            self.assertEqual(sotp_results[0].recommended_action, "BLOCKED_BY_RUMOR_CIRCUIT_BREAKER")

    def test_corroborated_event_sotp_penetration(self):
        """测试权威信源准入后自动触发 SOTP 因果穿透测算."""
        corroborated_event = {
            "event_id": "EVT_CORROBORATED_01",
            "title": "关键化学单体化工厂火灾爆炸全线停工",
            "category": "Physical_Plant_Disruption",
            "severity_level": "P1",
            "source_name": "Reuters_Industrial",
            "credibility_tier": "Tier3_Mainstream_Wire",
            "credibility_score": 0.8,
            "verification_status": "Confirmed_Fact",
            "micro_physical_impact": "全球EUV光刻胶专用核心单体供应骤降35%",
            "involved_entities": ["台积电"],
            "affected_business_segments": ["先进制程晶圆代工分部"],
            "published_at": datetime.now(timezone.utc).isoformat(),
        }

        sotp_results = self.dispatcher.execute_sotp_penetration(corroborated_event)
        self.assertGreaterEqual(len(sotp_results), 1)
        res_tsm = sotp_results[0]
        self.assertEqual(res_tsm.ticker, "TSM")
        self.assertLess(res_tsm.total_operating_income_impact, 0)
        self.assertLess(res_tsm.eps_impact, 0)

        # 验证卡片格式化不含崩溃字符且逻辑清晰
        card = self.dispatcher.format_alert_card(corroborated_event, sotp_results)
        self.assertIn("Taiwan Semiconductor Manufacturing Co", card)
        self.assertIn("ΔEPS", card)
        self.assertIn("库存抵御缓冲", card)
        self.assertIn("权威信源准入", card)

    def test_file_log_persistence(self):
        """测试告警记录持久化至日志底账."""
        event = {
            "event_id": "EVT_LOG_TEST",
            "title": "测试告警记录写入日志",
            "severity_level": "P0",
            "source_name": "Test_Wire",
            "credibility_tier": "Tier1_Official_Regulatory",
            "credibility_score": 1.0,
            "verification_status": "Confirmed_Fact",
            "micro_physical_impact": "测试微观物理影响",
            "involved_entities": ["NVDA"],
            "published_at": datetime.now(timezone.utc).isoformat(),
        }

        res = self.dispatcher.dispatch_event_alert(event)
        self.assertTrue(res["dispatched"])
        self.assertIn("file_log", res["channels"])

        # 检查日志文件是否真实写入
        self.assertTrue(self.log_file.exists())
        with open(self.log_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("EVT_LOG_TEST", content)
        self.assertIn("测试告警记录写入日志", content)


if __name__ == "__main__":
    unittest.main()
