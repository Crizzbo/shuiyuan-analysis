# -*- coding: utf-8 -*-
"""专属日志中枢与终端分流落盘单元测试 (Test Terminal Logging Hub & Dedicated Log Router)."""

import logging
from pathlib import Path
import tempfile
import unittest

from finance_tools.logging import (
    DedicatedModuleFilter,
    TerminalLogBridgeHandler,
    TerminalLoggingManager,
    normalize_log_level,
    normalize_module_name,
    setup_terminal_logging,
)
from financial_reporting.watersource_terminal_service import WatersourceTerminalService


class TestTerminalLoggingHub(unittest.TestCase):
    """测试专属物理日志落盘分流与终端日志中枢桥接。"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_dir = Path(self.temp_dir.name) / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.captured_logs = []

    def tearDown(self):
        root_logger = logging.getLogger()
        for h in list(root_logger.handlers):
            if isinstance(h, (TerminalLogBridgeHandler, logging.FileHandler)):
                root_logger.removeHandler(h)
                h.close()
        self.temp_dir.cleanup()

    def _bridge_callback(self, level, module, message, run_id=None, broadcast=True):
        self.captured_logs.append({
            "level": level,
            "module": module,
            "message": message,
            "run_id": run_id,
            "broadcast": broadcast,
        })

    def test_01_module_and_level_normalization(self):
        """测试模块名称与日志级别归一化。"""
        self.assertEqual(normalize_module_name("EventRadarCollector"), "event_radar")
        self.assertEqual(normalize_module_name("EvidenceVerificationPipeline"), "evidence_verification")
        self.assertEqual(normalize_module_name("AlertDispatcher"), "alert_dispatcher")
        self.assertEqual(normalize_module_name("TerminalScheduler"), "terminal_scheduler")
        self.assertEqual(normalize_module_name("WatersourceHTTPServer"), "terminal_service")

        self.assertEqual(normalize_log_level(logging.ERROR), "ERROR")
        self.assertEqual(normalize_log_level(logging.CRITICAL), "ERROR")
        self.assertEqual(normalize_log_level(logging.WARNING), "WARN")
        self.assertEqual(normalize_log_level(logging.INFO), "INFO")

    def test_02_dedicated_file_routing(self):
        """测试不同模块的日志精确分流落盘到对应的专属物理日志文件。"""
        mgr = TerminalLoggingManager(self.log_dir)
        mgr.initialize(service_callback=self._bridge_callback)

        logger_radar = logging.getLogger("EventRadarCollector")
        logger_verif = logging.getLogger("EvidenceVerificationPipeline")
        logger_alert = logging.getLogger("AlertDispatcher")
        logger_sched = logging.getLogger("TerminalScheduler")
        logger_http = logging.getLogger("WatersourceHTTPServer")

        logger_radar.info("Radar event EVT_01 distilled with P0 severity")
        logger_verif.warning("Unverified rumor quarantined: Rumor 02")
        logger_alert.error("Alert P0 triggered: Critical Supply Disruption")
        logger_sched.info("Scheduler task OFFICIAL_NEWS finished")
        logger_http.info("GET /api/dashboard/summary - 200 OK")

        # 刷新所有文件 handler
        for h in mgr.file_handlers.values():
            h.flush()

        # 断言桥接回调捕获全量日志
        self.assertEqual(len(self.captured_logs), 5)
        self.assertEqual(self.captured_logs[0]["module"], "event_radar")
        self.assertEqual(self.captured_logs[0]["level"], "INFO")
        self.assertEqual(self.captured_logs[1]["module"], "evidence_verification")
        self.assertEqual(self.captured_logs[1]["level"], "WARN")
        self.assertEqual(self.captured_logs[2]["module"], "alert_dispatcher")
        self.assertEqual(self.captured_logs[2]["level"], "ERROR")

        # 检查物理专属日志内容
        sys_content = (self.log_dir / "system.log").read_text(encoding="utf-8")
        radar_content = (self.log_dir / "event_radar.log").read_text(encoding="utf-8")
        verif_content = (self.log_dir / "verification.log").read_text(encoding="utf-8")
        alert_content = (self.log_dir / "alert.log").read_text(encoding="utf-8")
        sched_content = (self.log_dir / "scheduler.log").read_text(encoding="utf-8")
        http_content = (self.log_dir / "terminal_service.log").read_text(encoding="utf-8")

        # system.log 应包含全部日志
        self.assertIn("Radar event EVT_01", sys_content)
        self.assertIn("Unverified rumor quarantined", sys_content)
        self.assertIn("Alert P0 triggered", sys_content)
        self.assertIn("OFFICIAL_NEWS finished", sys_content)
        self.assertIn("GET /api/dashboard/summary", sys_content)

        # 专属日志仅应包含各自领域日志
        self.assertIn("Radar event EVT_01", radar_content)
        self.assertNotIn("Unverified rumor quarantined", radar_content)

        self.assertIn("Unverified rumor quarantined", verif_content)
        self.assertNotIn("Radar event EVT_01", verif_content)

        self.assertIn("Alert P0 triggered", alert_content)
        self.assertIn("OFFICIAL_NEWS finished", sched_content)
        self.assertIn("GET /api/dashboard/summary", http_content)

    def test_03_terminal_service_integration(self):
        """测试 WatersourceTerminalService 对专属日志概览与按模块过滤的完整支持。"""
        svc = WatersourceTerminalService(auto_seed_board=False)
        svc.logging_manager = TerminalLoggingManager(self.log_dir)
        svc.logging_manager.initialize(service_callback=svc._append_log)

        logging.getLogger("EventRadarCollector").info("Test radar log via terminal service")
        logging.getLogger("EvidenceVerificationPipeline").warning("Test verif log via terminal service")

        # 查询全量日志
        res_all = svc.get_logs(level="ALL")
        self.assertTrue(res_all["ok"])
        data_all = res_all["data"]
        self.assertIn("log_files", data_all)
        self.assertGreaterEqual(len(data_all["log_files"]), 5)

        # 校验专属日志文件信息
        files_map = {f["filename"]: f for f in data_all["log_files"]}
        self.assertIn("event_radar.log", files_map)
        self.assertIn("verification.log", files_map)
        self.assertIn("system.log", files_map)

        # 按专属模块过滤
        res_radar = svc.get_logs(module="event_radar")
        self.assertTrue(res_radar["ok"])
        radar_logs = res_radar["data"]["logs"]
        for l in radar_logs:
            self.assertEqual(l["module"], "event_radar")


if __name__ == "__main__":
    unittest.main()
