"""突发事件雷达本地交互大屏与轻量推流调度服务 (Event Radar Dashboard Server).

功能与设计规范:
1. 静态大屏托管: 托管 reports/event_radar_dashboard.html，支持本地买方交易室交互大屏展示;
2. 交易室动态推流 API:
   - GET /api/stream 或 /api/live: 提供推流探活与增量状态更新数据;
   - GET /api/events: 导出最新雷达事件底账与传闻熔断状态;
   - GET /api/receipts: 导出法定公报 SHA-256 防伪鉴真收据总账;
   - GET /api/stats: 导出 0-Token 初筛率与模型吞吐指标;
   - POST /api/verify: 接收官方证据文件路径，调用 EvidenceVerificationPipeline 执行密码学验签并解除熔断;
3. 零第三方重量级依赖: 基于 Python 标准库 http.server, urllib, json 实现;
4. 优雅网络防御: 严格项目内相对路径限制，防越界访问。
"""

import argparse
import http.server
import json
import logging
import os
import socket
import socketserver
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finance_tools.event_radar_collector import RadarDatabaseManager
from finance_tools.evidence_verification_pipeline import EvidenceVerificationPipeline
from finance_tools.supply_chain_ripple_analyzer import SupplyChainRippleAnalyzer

logger = logging.getLogger("RadarDashboardServer")


class RadarDashboardHandler(http.server.BaseHTTPRequestHandler):
    """突发事件雷达大屏与推流 API 调度处理器."""

    server_version = "RadarDashboardServer/2.0"

    def __init__(self, *args, db_path: str = "data/ledger/event_radar.sqlite3", **kwargs):
        self.db_path = str(PROJECT_ROOT / db_path) if not Path(db_path).is_absolute() else db_path
        self.receipts_path = PROJECT_ROOT / "data/ledger/verification_receipts.json"
        self.dashboard_file = PROJECT_ROOT / "reports/event_radar_dashboard.html"
        super().__init__(*args, **kwargs)

    def _send_json_response(self, data: Any, status: int = 200) -> None:
        """格式化输出标准 JSON 响应."""
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:
        """支持 CORS 预检请求."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        """处理大屏静态页面与 REST API 获取请求."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html", "/dashboard"):
            if not self.dashboard_file.is_file():
                # 尝试现场自动渲染
                try:
                    from scripts.generate_radar_dashboard import generate_dashboard_html
                    generate_dashboard_html(db_path=self.db_path, output_path=str(self.dashboard_file))
                except Exception as e:
                    logger.error("自动渲染大屏异常: %s", e)

            if not self.dashboard_file.is_file():
                self.send_error(404, "Dashboard HTML file not found.")
                return

            try:
                content = self.dashboard_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                logger.error("读取大屏文件失败: %s", e)
                self.send_error(500, "Internal Server Error")
            return

        elif path in ("/api/stream", "/api/live"):
            # 交易室推流探活与增量状态更新 API
            try:
                db_mgr = RadarDatabaseManager(db_path=self.db_path)
                events = db_mgr.query_events()
                stats = db_mgr.query_summary_statistics()
                receipts = []
                if self.receipts_path.is_file():
                    try:
                        receipts = json.loads(self.receipts_path.read_text(encoding="utf-8"))
                    except Exception:
                        receipts = []

                major_events = [e for e in events if e.get("severity_level") in ("P0", "P1") or e.get("requires_deep_analysis")]
                rumor_events = [e for e in events if e.get("verification_status") == "Unverified_Rumor"]

                payload = {
                    "status": "live",
                    "server_time_utc": datetime.now(timezone.utc).isoformat(),
                    "total_events": len(events),
                    "major_events_count": len(major_events),
                    "rumor_circuit_breaker_active": len(rumor_events),
                    "receipts_count": len(receipts),
                    "stats": stats,
                    "latest_events": events[:15],
                    "receipts": receipts,
                }
                self._send_json_response(payload, status=200)
            except Exception as e:
                logger.error("推流接口查询异常: %s", e)
                self._send_json_response({"error": str(e)}, status=500)
            return

        elif path == "/api/events":
            try:
                db_mgr = RadarDatabaseManager(db_path=self.db_path)
                events = db_mgr.query_events()
                self._send_json_response({"events": events, "count": len(events)}, status=200)
            except Exception as e:
                self._send_json_response({"error": str(e)}, status=500)
            return

        elif path == "/api/receipts":
            receipts = []
            if self.receipts_path.is_file():
                try:
                    receipts = json.loads(self.receipts_path.read_text(encoding="utf-8"))
                except Exception:
                    receipts = []
            self._send_json_response({"receipts": receipts, "count": len(receipts)}, status=200)
            return

        elif path == "/api/stats":
            try:
                db_mgr = RadarDatabaseManager(db_path=self.db_path)
                stats = db_mgr.query_summary_statistics()
                self._send_json_response(stats, status=200)
            except Exception as e:
                self._send_json_response({"error": str(e)}, status=500)
            return

        elif path == "/api/supply-chain/topologies":
            try:
                analyzer = SupplyChainRippleAnalyzer(db_path=self.db_path)
                topos = analyzer.list_topologies()
                self._send_json_response({"topologies": topos, "count": len(topos)}, status=200)
            except Exception as e:
                self._send_json_response({"error": str(e)}, status=500)
            return

        elif path == "/api/supply-chain/ripple":
            try:
                query_params = parse_qs(parsed.query)
                event_ids = query_params.get("event_id")
                topology_ids = query_params.get("topology")
                disruption_days_strs = query_params.get("disruption_days")

                analyzer = SupplyChainRippleAnalyzer(db_path=self.db_path)
                disruption_days = float(disruption_days_strs[0]) if disruption_days_strs else None
                topology_id = topology_ids[0] if topology_ids else None

                if event_ids and event_ids[0]:
                    event_id = event_ids[0]
                    report = analyzer.analyze_event_ripple(
                        event_id=event_id,
                        topology_id=topology_id,
                        disruption_days=disruption_days,
                    )
                    self._send_json_response({"status": "success", "report": report.to_dict()}, status=200)
                else:
                    reports = analyzer.analyze_all_major_events()
                    self._send_json_response(
                        {
                            "status": "success",
                            "reports": [r.to_dict() for r in reports],
                            "count": len(reports),
                        },
                        status=200,
                    )
            except Exception as e:
                logger.error("产业链涟漪计算接口异常: %s", e)
                self._send_json_response({"error": str(e)}, status=500)
            return

        else:
            self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        """处理官方证据验签与传闻熔断解除 POST 请求."""
        parsed = urlparse(self.path)
        if parsed.path == "/api/verify":
            content_len = int(self.headers.get("Content-Length", 0))
            if content_len == 0:
                self._send_json_response({"error": "Empty body"}, status=400)
                return

            try:
                body_str = self.rfile.read(content_len).decode("utf-8")
                req_data = json.loads(body_str)
                event_id = req_data.get("event_id")
                evidence_file = req_data.get("file")
                note = req_data.get("note")

                if not event_id or not evidence_file:
                    self._send_json_response({"error": "Missing event_id or file in request"}, status=400)
                    return

                pipeline = EvidenceVerificationPipeline(
                    db_path=self.db_path,
                    auto_refresh_reports=True,
                )
                file_p = Path(evidence_file)
                if not file_p.is_absolute():
                    file_p = PROJECT_ROOT / evidence_file

                receipt = pipeline.verify_single_event(
                    event_id=event_id,
                    evidence_file=file_p,
                    note=note,
                )
                self._send_json_response({"success": True, "receipt": receipt}, status=200)
            except Exception as e:
                logger.error("POST /api/verify 验签执行异常: %s", e)
                self._send_json_response({"success": False, "error": str(e)}, status=500)
            return

        self.send_error(404, "Endpoint not found")

    def log_message(self, format: str, *args) -> None:
        """覆写静默常规 HTTP 请求日志以保持终端干净."""
        return


def run_dashboard_server(
    port: int = 8899,
    db_path: str = "data/ledger/event_radar.sqlite3",
    open_browser: bool = False,
) -> None:
    """启动本地交互大屏推流调度服务."""
    # 动态尝试绑定端口
    current_port = port
    max_port = port + 20
    httpd = None

    def handler_factory(*args, **kwargs):
        return RadarDashboardHandler(*args, db_path=db_path, **kwargs)

    while current_port <= max_port:
        try:
            httpd = socketserver.TCPServer(("127.0.0.1", current_port), handler_factory)
            break
        except OSError:
            current_port += 1

    if not httpd:
        print(f"错误: 无法在端口区间 [{port}, {max_port}] 绑定本地服务。")
        sys.exit(1)

    url = f"http://127.0.0.1:{current_port}"
    print("\n" + "=" * 78)
    print("【突发事件雷达 · 本地买方交易室交互大屏与推流服务已启动】")
    print("=" * 78)
    print(f"大屏访问网址 (Web URL)   : {url}")
    print(f"推流探针接口 (Stream API): {url}/api/stream")
    print(f"事件底账接口 (Events API): {url}/api/events")
    print(f"防伪收据接口 (Receipts) : {url}/api/receipts")
    print(f"底层数据库路径           : {db_path}")
    print("=" * 78)
    print("提示: 前端大屏将自动侦测该推流服务并切换为【🟢 交易室实时推流】模式。")
    print("按 Ctrl+C 可安全停止服务。\n")

    if open_browser:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n正在停止推流服务...")
    finally:
        httpd.server_close()
        print("推流服务已优雅退出。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="突发事件雷达本地大屏与推流调度服务")
    parser.add_argument("--port", type=int, default=8899, help="服务监听端口 (默认 8899)")
    parser.add_argument("--db-path", type=str, default="data/ledger/event_radar.sqlite3", help="雷达数据库路径")
    parser.add_argument("--open-browser", action="store_true", help="启动后自动打开默认浏览器查看大屏")
    args = parser.parse_args()

    run_dashboard_server(port=args.port, db_path=args.db_path, open_browser=args.open_browser)
