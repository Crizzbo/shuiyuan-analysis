"""突发事件雷达交互大屏与轻量推流调度服务自动化测试集 (内存模拟与零网络依赖).

测试覆盖范围:
1. HTTP 静态大屏托管 (GET /) 与 HTML 渲染完整性;
2. 交易室动态推流接口 (GET /api/stream) 结构契约与状态探针;
3. 全量事件账本提取接口 (GET /api/events);
4. 官方鉴真防伪收据账本接口 (GET /api/receipts);
5. 扫描初筛效能统计接口 (GET /api/stats);
6. 异常边界与非法请求防御 (POST 校验与 404/400 处理);
7. 内存流级隔离测试，不依赖物理套接字，兼容全局离线测试契约。
"""

import io
import json
import os
import shutil
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finance_tools.event_radar_collector import RadarDatabaseManager, RawNewsItem
from financial_core.engines.event_radar_engine import StructuredEventSummary
from scripts.serve_radar_dashboard import RadarDashboardHandler


class MockSocket:
    """标准库 BaseHTTPRequestHandler 纯内存输入输出流套接字桩."""

    def __init__(self, data: bytes = b""):
        self.rfile = io.BytesIO(data)
        self.wfile = io.BytesIO()

    def makefile(self, mode: str, *args, **kwargs):
        if "r" in mode:
            return self.rfile
        return self.wfile

    def sendall(self, data: bytes) -> None:
        self.wfile.write(data)


class MockServer:
    """轻量虚拟服务器实例."""
    pass


class TestRadarDashboardServer(unittest.TestCase):
    """大屏推流服务与 REST API 纯内存隔离自动化测试套件."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = PROJECT_ROOT / f".cache/test_serve_{int(datetime.now().timestamp())}"
        cls.test_dir.mkdir(parents=True, exist_ok=True)
        cls.db_path = cls.test_dir / "test_radar.sqlite3"

        cls.db_mgr = RadarDatabaseManager(db_path=str(cls.db_path))
        now_iso = datetime.now(timezone.utc).isoformat()
        item = RawNewsItem(
            id="srv_test_raw_01",
            title="测试服务监控事件标题",
            content="测试资讯事实正文",
            source="Reuters_Test",
            published_at=now_iso,
            url="https://example.com/srv_test",
        )
        summary = StructuredEventSummary(
            event_id="EVT_SRV_TEST_9999",
            timestamp=now_iso,
            category="Supply_Chain_Chokepoint",
            involved_entities=["TSMC"],
            micro_physical_impact="物理供应链测试节点通畅",
            estimated_duration="短期",
            affected_business_segments=["先进制程代工"],
            severity_level="P1",
            requires_deep_analysis=True,
            raw_title="测试服务监控事件标题",
            source_name="Reuters_Test",
            credibility_tier="Tier1_Official_Regulatory",
            credibility_score=1.0,
            verification_status="Confirmed_Fact",
            verification_note="官方测试凭据验签属实",
        )
        cls.db_mgr.insert_event(summary, item, collected_at=now_iso)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def _execute_request(self, method: str, path: str, body: bytes = b"") -> Tuple[int, Dict[str, str], bytes]:
        """纯内存分发 HTTP 请求并捕获状态码、响应头与响应载荷."""
        raw_req = f"{method} {path} HTTP/1.1\r\nHost: localhost\r\nContent-Length: {len(body)}\r\n\r\n".encode("utf-8") + body
        mock_sock = MockSocket(raw_req)

        # 实例化处理器触发请求解析与执行
        RadarDashboardHandler(mock_sock, ("127.0.0.1", 54321), MockServer(), db_path=str(self.db_path))
        output = mock_sock.wfile.getvalue()

        parts = output.split(b"\r\n\r\n", 1)
        header_block = parts[0].decode("utf-8", errors="replace")
        body_bytes = parts[1] if len(parts) > 1 else b""

        lines = header_block.split("\r\n")
        status_code = int(lines[0].split()[1]) if lines and len(lines[0].split()) > 1 else 500

        headers = {}
        for h in lines[1:]:
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        return status_code, headers, body_bytes

    def test_get_dashboard_html(self):
        """测试 GET / 静态大屏 HTML 返回与拓扑视图标记."""
        status, headers, body = self._execute_request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        html = body.decode("utf-8")
        self.assertIn("突发事件雷达监控看板", html)
        self.assertIn("Causal Chain Topology", html)
        self.assertIn("verification_receipts", html)

    def test_get_api_stream(self):
        """测试 GET /api/stream 交易室推流探针接口."""
        status, headers, body = self._execute_request("GET", "/api/stream")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data.get("status"), "live")
        self.assertGreaterEqual(data.get("total_events", 0), 1)
        self.assertIn("server_time_utc", data)
        self.assertIn("stats", data)
        self.assertIn("latest_events", data)

    def test_get_api_events(self):
        """测试 GET /api/events 全量事件账本提取接口."""
        status, headers, body = self._execute_request("GET", "/api/events")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        events = data.get("events", [])
        self.assertGreaterEqual(len(events), 1)
        found = any(e.get("event_id") == "EVT_SRV_TEST_9999" for e in events)
        self.assertTrue(found)

    def test_get_api_receipts(self):
        """测试 GET /api/receipts 防伪收据账本提取接口."""
        status, headers, body = self._execute_request("GET", "/api/receipts")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("receipts", data)
        self.assertIsInstance(data["receipts"], list)

    def test_get_api_stats(self):
        """测试 GET /api/stats 统计数据指标接口."""
        status, headers, body = self._execute_request("GET", "/api/stats")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("total_scanned_news", data)
        self.assertIn("total_summarized", data)

    def test_post_verify_missing_fields_validation(self):
        """测试 POST /api/verify 缺失字段时的安全防御与 400 校验."""
        bad_payload = json.dumps({"event_id": "EVT_NON_EXISTENT"}).encode("utf-8")
        status, headers, body = self._execute_request("POST", "/api/verify", body=bad_payload)
        self.assertEqual(status, 400)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("error", data)


if __name__ == "__main__":
    unittest.main()
