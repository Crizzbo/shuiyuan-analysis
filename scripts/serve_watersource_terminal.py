# -*- coding: utf-8 -*-
"""水源分析终端本地 HTTP + SSE 服务网关 (WaterSource Terminal Server).

架构与安全约束：
1. 纯 Python 标准库实现 (`http.server.ThreadingHTTPServer`)，零新增第三方 Web 框架依赖。
2. 零修改既有金融工具：仅调用 `financial_reporting.watersource_terminal_service.WatersourceTerminalService`
   并通过回调函数向其注入 `scripts.env_discovery` 环境探测信息（严格保持四层单向依赖）。
3. 严格 1:1 前后端契约对齐：提供 14 个 REST 端点 + `/api/stream` SSE 实时推流通道 + `/` 前端原型托管。
"""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import mimetypes
from pathlib import Path
import queue
import re
import sys
import threading
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse
import webbrowser

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REACT_DIST_DIR = PROJECT_ROOT / "web" / "dist"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from financial_reporting.watersource_terminal_service import WatersourceTerminalService
from scripts import env_discovery
from scripts.terminal_scheduler import AUTOMATIC_TASKS, TASKS, TerminalScheduler


def _inspect_env() -> Dict[str, Any]:
    return {
        "gdrive_detected": bool(env_discovery.get_gdrive_executable()),
        "edge_detected": bool(env_discovery.get_edge_executable()),
        "python_executable": env_discovery.get_python_executable(),
    }


def _safe_int(value: Optional[str], default: int, *, min_val: int = 1, max_val: int = 500) -> int:
    if value is None or not str(value).strip():
        return default
    try:
        parsed = int(value)
        return max(min_val, min(max_val, parsed))
    except ValueError:
        return default


class WatersourceHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address: Tuple[str, int],
        RequestHandlerClass: Any,
        service: WatersourceTerminalService,
        frontend_html_path: Path,
    ):
        self.service = service
        self.frontend_html_path = frontend_html_path
        super().__init__(server_address, RequestHandlerClass)


class WatersourceRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "WaterSourceTerminal/1.0"

    def handle(self) -> None:
        try:
            super().handle()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            self.close_connection = True

    def log_message(self, format: str, *args: Any) -> None:
        # 静音默认 stderr 逐条请求刷屏，但写入 terminal_service 专属日志
        try:
            msg = format % args
            if "/api/stream" not in msg and "/assets/" not in msg:
                logging.getLogger("WatersourceHTTPServer").info(f"{getattr(self, 'command', 'HTTP')} {getattr(self, 'path', '')} - {msg}")
        except Exception:
            pass

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")

    def _send_json(self, status_code: int, payload: Dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, file_path: Path, content_type: Optional[str] = None) -> None:
        if not file_path.is_file():
            code, err = self.server.service.error_envelope(
                "FILE_NOT_FOUND", f"未找到静态文件: {file_path.name}", status_code=404
            )
            self._send_json(code, err)
            return
        body = file_path.read_bytes()
        ct = content_type or mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        if ct.startswith("text/") or ct in ("application/javascript", "application/json"):
            ct = f"{ct}; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html_path: Path) -> None:
        self._send_file(html_path, "text/html; charset=utf-8")

    def _read_json_body(self) -> Dict[str, Any]:
        length_str = self.headers.get("Content-Length")
        if not length_str:
            return {}
        try:
            length = int(length_str)
        except ValueError:
            return {}
        if length <= 0 or length > 1_048_576:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        parsed = json.loads(raw.decode("utf-8"))
        return parsed if isinstance(parsed, dict) else {}

    def _write_sse_frame(self, event_name: str, data_obj: Any) -> bool:
        try:
            payload_str = json.dumps(data_obj, ensure_ascii=False)
            frame = f"event: {event_name}\ndata: {payload_str}\n\n".encode("utf-8")
            self.wfile.write(frame)
            self.wfile.flush()
            return True
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            return False

    def _handle_sse_stream(self) -> None:
        svc: WatersourceTerminalService = self.server.service
        self.close_connection = True
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self._send_cors_headers()
        self.end_headers()

        sub_q = svc.subscribe_sse()
        try:
            # 初始推送握手与最新状态快照
            if not self._write_sse_frame("pipeline_status", svc.get_pipeline_status()["data"]):
                return
            if not self._write_sse_frame("snapshot", svc.get_dashboard_summary()["data"]):
                return

            last_heartbeat = time.monotonic()
            while True:
                try:
                    msg = sub_q.get(timeout=1.0)
                    ev_name = str(msg.get("event") or "message")
                    ev_payload = msg.get("payload")
                    if not self._write_sse_frame(ev_name, ev_payload):
                        break
                except queue.Empty:
                    now = time.monotonic()
                    if now - last_heartbeat >= 15.0:
                        last_heartbeat = now
                        if not self._write_sse_frame(
                            "heartbeat",
                            {
                                "pipeline_state": svc.get_pipeline_status()["data"]["pipeline_state"],
                                "ts": time.time(),
                            },
                        ):
                            break
        finally:
            svc.unsubscribe_sse(sub_q)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        svc: WatersourceTerminalService = self.server.service
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        def _q1(name: str, default: Optional[str] = None) -> Optional[str]:
            vals = qs.get(name)
            return vals[0] if vals else default

        try:
            if path in ("/api/terminal/tasks", "/api/terminal/news", "/api/terminal/market-archives"):
                scheduler = getattr(svc, "scheduler", None)
                if scheduler is None:
                    self._send_json(*svc.error_envelope("SCHEDULER_UNAVAILABLE", "调度器未启动", 503))
                else:
                    if path.endswith("/tasks"):
                        data = scheduler.snapshot()
                    elif path.endswith("/market-archives"):
                        data = {
                            "items": scheduler.market_archives(),
                            "reconciliation": {
                                "us": scheduler.reconciliation_summary("US"),
                                "jp": scheduler.reconciliation_summary("JP"),
                            },
                        }
                    else:
                        records = scheduler.news if path.endswith("/news") else scheduler.market_archives
                        data = {"items": records()}
                    self._send_json(200, svc._envelope(data, as_of="", source="terminal_scheduler", status="OK"))
                return

            if path in ("/", "/index.html", "/watersource_terminal_prototype.html"):
                react_index = REACT_DIST_DIR / "index.html"
                if react_index.is_file():
                    self._send_file(react_index, "text/html; charset=utf-8")
                elif getattr(self.server, "frontend_html_path", None) and self.server.frontend_html_path.is_file():
                    self._send_file(self.server.frontend_html_path, "text/html; charset=utf-8")
                else:
                    self._send_json(*svc.error_envelope("WEB_BUILD_REQUIRED", "请先运行 python scripts/build_web.py", 503))
                return

            if path.startswith("/assets/"):
                rel = path[len("/assets/") :].lstrip("/")
                asset_file = (REACT_DIST_DIR / "assets" / rel).resolve()
                if str(asset_file).startswith(str(REACT_DIST_DIR.resolve())) and asset_file.is_file():
                    self._send_file(asset_file)
                    return
                code, err = svc.error_envelope("ASSET_NOT_FOUND", f"未找到前端静态资源: {rel}", status_code=404)
                self._send_json(code, err)
                return

            if path in ("/favicon.svg", "/favicon.ico"):
                fav_file = (REACT_DIST_DIR / path.lstrip("/")).resolve()
                if fav_file.is_file():
                    self._send_file(fav_file)
                    return
                self.send_response(204)
                self.send_header("Content-Length", "0")
                self._send_cors_headers()
                self.end_headers()
                return

            # 允许安全访问 REACT_DIST_DIR 根目录下的静态页面（如 icon_preview.html）
            if path.count("/") == 1 and not path.startswith("/api/"):
                potential_file = (REACT_DIST_DIR / path.lstrip("/")).resolve()
                if potential_file.is_file() and str(potential_file).startswith(str(REACT_DIST_DIR.resolve())):
                    self._send_file(potential_file)
                    return

            if path == "/api/stream":
                self._handle_sse_stream()
                return

            if path == "/api/health":
                self._send_json(200, svc.get_health())
                return

            if path == "/api/dashboard/summary":
                self._send_json(200, svc.get_dashboard_summary())
                return

            if path in ("/api/market/statistics", "/api/markets/statistics"):
                self._send_json(200, svc._envelope(svc.get_market_statistics(), as_of="", source="market_statistics_engine", status="OK"))
                return

            if path == "/api/markets/quotes":
                market = (_q1("market", "ALL") or "ALL").upper()
                self._send_json(200, svc.get_market_quotes(market=market))
                return

            if path in ("/api/terminal/quotes/batch-collect", "/api/quotes/batch-collect"):
                raw_tickers = _q1("tickers") or ""
                tickers = [t.strip().upper() for t in re.split(r"[,;\s]+", raw_tickers) if t.strip()]
                force_refresh = (_q1("force_refresh", "false") or "false").lower() in ("true", "1")
                code, res = svc.batch_collect_stock_quotes(tickers, force_refresh=force_refresh)
                self._send_json(code, res)
                return

            if path == "/api/indicators/latest":
                self._send_json(200, svc.get_latest_indicators())
                return

            if path == "/api/events":
                limit = _safe_int(_q1("limit"), 50, min_val=1, max_val=200)
                res = svc.get_events(
                    severity=_q1("severity"),
                    verification_status=_q1("verification_status"),
                    date=_q1("date"),
                    q=_q1("q"),
                    limit=limit,
                )
                self._send_json(200, res)
                return

            if path.startswith("/api/events/"):
                ev_id = unquote(path[len("/api/events/") :]).strip()
                if not ev_id:
                    code, err = svc.error_envelope("MISSING_EVENT_ID", "事件 ID 不能为空", status_code=400)
                    self._send_json(code, err)
                    return
                detail = svc.get_event_detail(ev_id)
                if detail is None:
                    code, err = svc.error_envelope("EVENT_NOT_FOUND", f"未找到事件: {ev_id}", status_code=404)
                    self._send_json(code, err)
                    return
                self._send_json(200, detail)
                return

            if path == "/api/collection/overview":
                self._send_json(200, svc.get_collection_overview())
                return

            if path == "/api/finance/companies":
                self._send_json(200, svc.get_finance_companies())
                return

            if path == "/api/finance/models":
                ticker = (_q1("ticker") or "NVDA").strip()
                self._send_json(200, svc.get_finance_models(ticker=ticker))
                return

            if path == "/api/finance/auto-calculate":
                ticker = (_q1("ticker") or "").strip()
                if not ticker:
                    code, err = svc.error_envelope("MISSING_TICKER", "请提供查询参数 ?ticker=...", status_code=400)
                    self._send_json(code, err)
                    return
                self._send_json(*svc.auto_calculate_company_valuation(ticker))
                return

            if path == "/api/analytics/candidates":
                market = (_q1("market", "ALL") or "ALL").upper()
                limit = _safe_int(_q1("limit"), 20, min_val=1, max_val=100)
                page = _safe_int(_q1("page"), 1, min_val=1, max_val=10000)
                page_size = _safe_int(_q1("page_size"), limit, min_val=1, max_val=100)
                q_kw = (_q1("q") or "").strip()
                self._send_json(200, svc.get_analytics_candidates(market=market, limit=limit, page=page, page_size=page_size, q=q_kw))
                return

            if path == "/api/analytics/company":
                ticker = (_q1("ticker") or "").strip()
                if not ticker:
                    code, err = svc.error_envelope("MISSING_TICKER", "请提供查询参数 ?ticker=...", status_code=400)
                    self._send_json(code, err)
                    return
                self._send_json(200, svc.get_company_analysis(ticker))
                return

            if path == "/api/pipeline/status":
                self._send_json(200, svc.get_pipeline_status())
                return

            if path == "/api/pipeline/runs":
                self._send_json(200, svc.get_pipeline_runs())
                return

            if path == "/api/logs":
                limit = _safe_int(_q1("limit"), 100, min_val=1, max_val=500)
                res = svc.get_logs(
                    level=_q1("level", "ALL") or "ALL",
                    module=_q1("module"),
                    q=_q1("q"),
                    limit=limit,
                )
                self._send_json(200, res)
                return

            if path == "/api/settings":
                self._send_json(200, svc.get_settings())
                return

            if path in ("/api/tasks/config", "/api/terminal/tasks/config"):
                cfg = svc.get_terminal_tasks_config()
                self._send_json(200, svc._envelope(cfg, as_of="", source="config/terminal_tasks.json", status="OK"))
                return

            code, err = svc.error_envelope("NOT_FOUND", f"未知接口路径: {path}", status_code=404)
            self._send_json(code, err)
        except Exception as exc:
            code, err = svc.error_envelope("INTERNAL_ERROR", f"服务端处理异常: {exc}", status_code=500)
            self._send_json(code, err)

    def do_POST(self) -> None:
        svc: WatersourceTerminalService = self.server.service
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        try:
            origin = self.headers.get("Origin")
            if origin and urlparse(origin).netloc != self.headers.get("Host"):
                self._send_json(*svc.error_envelope("ORIGIN_DENIED", "操作需要同源请求", 403))
                return
            body = self._read_json_body()
        except Exception as exc:
            code, err = svc.error_envelope("INVALID_JSON", f"JSON 请求体解析失败: {exc}", status_code=400)
            self._send_json(code, err)
            return

        try:
            if path == "/api/finance/calculate":
                self._send_json(*svc.calculate_finance(body))
                return

            if path == "/api/finance/auto-calculate":
                ticker = str(body.get("ticker") or "").strip()
                adjustments = body.get("adjustments") if isinstance(body.get("adjustments"), dict) else None
                self._send_json(*svc.auto_calculate_company_valuation(ticker, adjustments=adjustments))
                return

            if path in ("/api/terminal/tasks/start", "/api/terminal/tasks/automatic"):
                scheduler = getattr(svc, "scheduler", None)
                if scheduler is None:
                    self._send_json(*svc.error_envelope("SCHEDULER_UNAVAILABLE", "调度器未启动", 503))
                elif path.endswith("/start"):
                    batch = scheduler.start_batch()
                    self._send_json(202, svc._envelope(batch, as_of="", source="terminal_scheduler", status="QUEUED"))
                elif not isinstance(body.get("enabled"), bool) or not scheduler.scheduled:
                    self._send_json(*svc.error_envelope("INVALID_SCHEDULE", "当前服务不能启用定时调度", 400))
                else:
                    scheduler.set_enabled("__automatic__", body["enabled"])
                    self._send_json(200, svc._envelope(scheduler.snapshot(), as_of="", source="terminal_scheduler", status="OK"))
                return

            if path in ("/api/terminal/tasks/run", "/api/terminal/tasks/schedule"):
                scheduler = getattr(svc, "scheduler", None)
                task = body.get("task")
                if not isinstance(task, str) or task not in TASKS:
                    self._send_json(*svc.error_envelope("INVALID_TASK", "未知任务", 400))
                elif scheduler is None:
                    self._send_json(*svc.error_envelope("SCHEDULER_UNAVAILABLE", "调度器未启动", 503))
                elif path.endswith("/run"):
                    target_ticker = (body.get("ticker") or body.get("target_ticker") or "").strip().upper()
                    slot = target_ticker if task == "STOCK_DOSSIER_COLLECT" and target_ticker else None
                    run_id, status = scheduler.submit_with_status(task, slot=slot)
                    self._send_json(200, svc._envelope({"run_id": run_id, "status": status, "task": task, "ticker": target_ticker}, as_of="", source="terminal_scheduler", status=status, run_id=run_id))
                elif task not in AUTOMATIC_TASKS or not isinstance(body.get("enabled"), bool):
                    self._send_json(*svc.error_envelope("INVALID_SCHEDULE", "请指定支持定时的任务及启用状态", 400))
                else:
                    scheduler.set_enabled(task, body["enabled"])
                    self._send_json(200, svc._envelope({"enabled": body["enabled"]}, as_of="", source="terminal_scheduler", status="OK"))
                return

            if path in ("/api/terminal/quotes/batch-collect", "/api/quotes/batch-collect"):
                tickers = body.get("tickers") or []
                force_refresh = bool(body.get("force_refresh", False))
                code, res = svc.batch_collect_stock_quotes(tickers, force_refresh=force_refresh)
                self._send_json(code, res)
                return

            if path == "/api/pipeline/start":
                mode = str(body.get("mode") or "local_audit_sync")
                market = str(body.get("market") or "ALL")
                accepted, res = svc.start_pipeline(mode=mode, market=market)
                self._send_json(200 if accepted else 409, res)
                return

            if path == "/api/pipeline/stop":
                run_id = body.get("run_id")
                res = svc.stop_pipeline(run_id=str(run_id) if run_id else None)
                self._send_json(200, res)
                return

            if path == "/api/collection/tasks/rerun":
                pipeline_id = str(body.get("pipeline_id") or body.get("task_id") or "").strip()
                if not pipeline_id:
                    code, err = svc.error_envelope("MISSING_TASK_ID", "请提供 pipeline_id 或 task_id 参数", status_code=400)
                    self._send_json(code, err)
                    return
                scheduler = getattr(svc, "scheduler", None)
                if scheduler is not None:
                    if pipeline_id == "EVENT_RADAR_POLLING":
                        run_id = scheduler.submit("OFFICIAL_NEWS")
                        self._send_json(202, svc._envelope(
                            {"run_id": run_id, "status": "QUEUED", "pipeline_id": pipeline_id, "task": "OFFICIAL_NEWS"},
                            as_of="", source="terminal_scheduler", status="QUEUED", run_id=run_id,
                        ))
                        return
                    if pipeline_id == "SEPA_UNIVERSE_SCREENER":
                        run_id = scheduler.submit("STOCK_SCREENING")
                        self._send_json(202, svc._envelope(
                            {"run_id": run_id, "status": "QUEUED", "pipeline_id": pipeline_id, "task": "STOCK_SCREENING"},
                            as_of="", source="terminal_scheduler", status="QUEUED", run_id=run_id,
                        ))
                        return
                    if pipeline_id == "UNIVERSE_567_BATCH":
                        run_id = scheduler.submit("FINANCE_CALC")
                        self._send_json(202, svc._envelope(
                            {"run_id": run_id, "status": "QUEUED", "pipeline_id": pipeline_id, "task": "FINANCE_CALC"},
                            as_of="", source="terminal_scheduler", status="QUEUED", run_id=run_id,
                        ))
                        return
                status_code, res = svc.rerun_collection_task(pipeline_id)
                self._send_json(status_code, res)
                return

            if path == "/api/collection/tasks/toggle":
                pipeline_id = str(body.get("pipeline_id") or body.get("task_id") or "").strip()
                if not pipeline_id:
                    code, err = svc.error_envelope("MISSING_TASK_ID", "请提供 pipeline_id 或 task_id 参数", status_code=400)
                    self._send_json(code, err)
                    return
                enabled = body.get("enabled")
                status_code, res = svc.toggle_collection_task(pipeline_id, enabled=enabled)
                self._send_json(status_code, res)
                return

            if path in ("/api/tasks/config", "/api/terminal/tasks/config"):
                self._send_json(*svc.update_terminal_tasks_config(body))
                return

            if path in ("/api/events/distill", "/api/terminal/events/distill"):
                code, payload = svc.distill_events()
                self._send_json(code, payload)
                return

            code, err = svc.error_envelope("NOT_FOUND", f"未知 POST 接口路径: {path}", status_code=404)
            self._send_json(code, err)
        except Exception as exc:
            code, err = svc.error_envelope("INTERNAL_ERROR", f"服务端处理异常: {exc}", status_code=500)
            self._send_json(code, err)


def create_terminal_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    service: Optional[WatersourceTerminalService] = None,
    frontend_html_path: Optional[Path] = None,
) -> WatersourceHTTPServer:
    svc = service or WatersourceTerminalService(project_root=PROJECT_ROOT, env_inspector=_inspect_env)
    html_path = frontend_html_path or (PROJECT_ROOT / "financial_reporting" / "watersource_terminal_prototype.html")
    return WatersourceHTTPServer((host, port), WatersourceRequestHandler, service=svc, frontend_html_path=html_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="启动水源分析终端 (WaterSource Terminal) HTTP+SSE 服务")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址 (默认 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="监听端口 (默认 8765)")
    parser.add_argument("--open", action="store_true", help="启动后自动在默认浏览器打开终端")
    parser.add_argument("--manual-only", action="store_true", help="关闭定时触发，保留手动任务")
    args = parser.parse_args()

    server = create_terminal_server(host=args.host, port=args.port)

    def _on_scheduler_status(run_id: str, task: str, status: str, result: Dict[str, Any]) -> None:
        server.service._broadcast_sse("collection_update", {"task": task, "run_id": run_id, "status": status})

    scheduler = TerminalScheduler(
        PROJECT_ROOT / ".cache/terminal",
        audit=server.service.audit_local_data,
        scheduled=not args.manual_only,
        on_status_change=_on_scheduler_status,
    )
    server.service.scheduler = scheduler
    scheduler.start()
    actual_host, actual_port = server.server_address
    url = f"http://{actual_host}:{actual_port}/"
    print(f"[WaterSource Terminal] 服务已启动: {url}")
    print("[WaterSource Terminal] 按 Ctrl+C 优雅停止服务")

    if args.open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[WaterSource Terminal] 正在停止服务...")
    finally:
        server.server_close()
        scheduler.close()


if __name__ == "__main__":
    main()
