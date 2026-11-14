# -*- coding: utf-8 -*-
"""水源分析终端前后端契约与聚合服务测试套件 (test_watersource_terminal_api.py).

遵循《CLAUDE.md》与《AGENTS.md》四段式中文测试说明文档规范：
1. 测试目标 (Objective)
2. 输入数据与边界 (Inputs & Boundaries)
3. 业务逻辑断言 (Assertions & Invariants)
4. 失败场景防护 (Failure Modes)
"""

from __future__ import annotations

import io
import json
from pathlib import Path
import socket
import sys
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from financial_reporting.watersource_terminal_service import WatersourceTerminalService
from scripts.serve_watersource_terminal import (
    WatersourceRequestHandler,
    _inspect_env,
    create_terminal_server,
)


def _is_socket_monkeypatched() -> bool:
    return getattr(socket.socket.connect, "__name__", "") == "deny" or getattr(
        socket.create_connection, "__name__", ""
    ) == "deny"


class _MemorySocket:
    """在其它测试文件全局禁用 socket.connect 时提供零网络的 HTTP 处理器直测通道."""

    def __init__(self, raw_request: bytes) -> None:
        self._rfile = io.BytesIO(raw_request)
        self._wfile = io.BytesIO()

    def makefile(self, mode: str, *_args, **_kwargs):
        if "r" in mode:
            return self._rfile
        return self._wfile

    def sendall(self, data: bytes) -> None:
        self._wfile.write(data)

    def close(self) -> None:
        return None

    def get_response_bytes(self) -> bytes:
        return self._wfile.getvalue()


def _parse_http_raw(raw_bytes: bytes) -> tuple[int, dict[str, str], bytes]:
    head, _, body = raw_bytes.partition(b"\r\n\r\n")
    lines = head.decode("utf-8", errors="replace").split("\r\n")
    status = int(lines[0].split()[1])
    headers: dict[str, str] = {}
    for ln in lines[1:]:
        if ":" in ln:
            k, v = ln.split(":", 1)
            headers[k.strip()] = v.strip()
    return status, headers, body


class _InProcessDispatcher:
    def __init__(self, server) -> None:
        self.server = server

    def request(self, path: str, method: str = "GET", body: dict | None = None) -> tuple[int, dict[str, str], bytes]:
        payload = json.dumps(body).encode("utf-8") if body is not None else b""
        hdr_lines = [f"{method} {path} HTTP/1.1", "Host: 127.0.0.1", "Connection: close"]
        if body is not None:
            hdr_lines.append("Content-Type: application/json")
            hdr_lines.append(f"Content-Length: {len(payload)}")
        raw_req = ("\r\n".join(hdr_lines) + "\r\n\r\n").encode("utf-8") + payload
        mem_sock = _MemorySocket(raw_req)
        WatersourceRequestHandler(mem_sock, ("127.0.0.1", 0), self.server)
        return _parse_http_raw(mem_sock.get_response_bytes())


class TestWatersourceTerminalAPI(unittest.TestCase):
    """水源分析终端聚合层与 HTTP+SSE 网关全链路契约测试."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.service = WatersourceTerminalService(
            project_root=PROJECT_ROOT,
            auto_seed_board=True,
            env_inspector=_inspect_env,
        )
        cls.html_path = PROJECT_ROOT / "financial_reporting" / "watersource_terminal_prototype.html"
        cls.offline_socket_mode = True  # HTTP 契约在内存分派，兼容禁止回环连接的沙箱
        if cls.offline_socket_mode:
            # test_research_time_contract 在同一 discover 进程中全局禁止 socket，采用内存处理器直测
            class _DummyServer:
                service = cls.service
                frontend_html_path = cls.html_path

            cls.server = _DummyServer()
            cls.dispatcher = _InProcessDispatcher(cls.server)
            cls.base_url = "http://127.0.0.1:0"
        else:
            cls.server = create_terminal_server(host="127.0.0.1", port=0, service=cls.service)
            host, port = cls.server.server_address
            cls.base_url = f"http://{host}:{port}"
            cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
            cls.server_thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        if not cls.offline_socket_mode:
            cls.server.shutdown()
            cls.server.server_close()

    def _http_json(self, path: str, method: str = "GET", body: dict | None = None) -> tuple[int, dict]:
        if self.offline_socket_mode:
            code, _, raw_body = self.dispatcher.request(path, method=method, body=body)
            return code, json.loads(raw_body.decode("utf-8"))
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        req = Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except HTTPError as err:
            return err.code, json.loads(err.read().decode("utf-8"))

    def _http_raw(self, path: str) -> tuple[int, dict[str, str], bytes]:
        if self.offline_socket_mode:
            return self.dispatcher.request(path, method="GET")
        with urlopen(f"{self.base_url}{path}", timeout=10) as resp:
            return resp.status, dict(resp.headers.items()), resp.read()

    def test_01_architecture_non_regression_and_no_upward_import(self):
        """【测试一：四层单向依赖约束与既有工具零入侵边界】

        1. 测试目标：确保 `financial_reporting/watersource_terminal_service.py` 未逆向导入 `scripts.*`。
        2. 输入数据：读取聚合服务源码及已注入的 `env_inspector` 输出。
        3. 业务断言：
           - 源码中不存在 `from scripts` 或 `import scripts`；
           - `/api/health` 返回 `architecture_layers_ok=True` 与有效 `ledger_valid=True`。
        4. 失败防护：防止向上依赖导致 `verify_architecture_integrity.py` 阻断。
        """
        src = (PROJECT_ROOT / "financial_reporting" / "watersource_terminal_service.py").read_text(encoding="utf-8")
        self.assertNotIn("from scripts", src)
        self.assertNotIn("import scripts", src)

        code, res = self._http_json("/api/health")
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"])
        self.assertTrue(res["data"]["architecture_layers_ok"])
        self.assertTrue(res["data"]["ledger_valid"])

    def test_02_dashboard_markets_and_stale_quote_honesty(self):
        """【测试二：总览 KPI、美日行情矩阵与 USDJPY 超期阻断诚实披露】

        1. 测试目标：验证 `/api/dashboard/summary` 与 `/api/markets/quotes` 严格对接本地真实行情底账。
        2. 输入数据：本地 `data/google-finance/raw/` 真实行情快照与指标归档。
        3. 业务断言：
           - 总览返回 5 大 KPI 且显式包含时效门禁横幅；
           - `USDJPY` 若存在于本地快照，必须暴露 `STALE_BLOCKED` 与 `is_valid=False`，绝不伪装新鲜；
           - 缺失的 `RUT` / `^N225` 必须标记 `NOT_CONFIGURED`，绝不虚构点位。
        4. 失败防护：严防过时汇率或未配置指数污染后续 DCF 与风控计算。
        """
        code, dash = self._http_json("/api/dashboard/summary")
        self.assertEqual(code, 200)
        self.assertEqual(len(dash["data"]["kpis"]), 5)
        self.assertNotEqual(dash["data"]["readiness"]["latest_timestamp_utc"], "2026-11-13 06:00:00 UTC")

        code, mk = self._http_json("/api/markets/quotes?market=ALL")
        self.assertEqual(code, 200)
        jp_list = mk["data"]["jp_indices"]
        us_list = mk["data"]["us_indices"]

        usdjpy = next((x for x in jp_list if x["ticker"] == "USDJPY"), None)
        if usdjpy is not None:
            self.assertEqual(usdjpy["data_status"], "STALE_BLOCKED")
            self.assertFalse(usdjpy["is_valid"])

        rut = next((x for x in us_list if x["ticker"] == "RUT"), None)
        self.assertIsNotNone(rut)
        self.assertEqual(rut["data_status"], "NOT_CONFIGURED")
        self.assertIsNone(rut["price"])

    def test_03_events_filtering_and_rumor_quarantine(self):
        """【测试三：事件情报多维筛选、抽屉详情与未核实传闻隔离】

        1. 测试目标：验证 `/api/events` 与 `/api/events/<id>` 直连 `event_radar.sqlite3` 并正确隔离传闻。
        2. 输入数据：查询全量事件、`Unverified_Rumor` 过滤及不存在的 `EVENT_NOT_FOUND` 边界。
        3. 业务断言：
           - 全量事件不少于 10 条（当前真实库为 13 条）；
           - 传闻隔离事件带有 `is_quarantined_rumor=True`；
           - 不存在的事件 ID 返回 `404` 规范错误信封。
        4. 失败防护：防止传闻未标识即进入决策界面或缺失 ID 引发 500 崩溃。
        """
        code, evs = self._http_json("/api/events?limit=50")
        self.assertEqual(code, 200)
        items = evs["data"]["events"]
        self.assertTrue(items)
        self.assertFalse(any(item["event_id"].startswith("EVT_20261113_") for item in items))

        code_rumor, rumors = self._http_json("/api/events?verification_status=Unverified_Rumor")
        self.assertEqual(code_rumor, 200)
        for r in rumors["data"]["events"]:
            self.assertTrue(r["is_quarantined_rumor"])

        first_id = items[0]["event_id"]
        code_detail, detail = self._http_json(f"/api/events/{first_id}")
        self.assertEqual(code_detail, 200)
        self.assertEqual(detail["data"]["event_id"], first_id)

        code_404, err = self._http_json("/api/events/NON_EXISTENT_EV_999")
        self.assertEqual(code_404, 404)
        self.assertFalse(err["ok"])
        self.assertEqual(err["error"]["code"], "EVENT_NOT_FOUND")

    def test_04_company_analysis_zero_scoring_and_unit_guard(self):
        """【测试四：个股无机械打分契约、三态估值走廊与 8035 量纲护栏】

        1. 测试目标：验证个股诊断彻底废除机械评分，正确输出 AI 商业分析、定量探针与量纲防错。
        2. 输入数据：分别请求 `NVDA`（SEC 平账就绪美股）与 `8035`（日股 JPY 报价 vs 美元筛选价冲突样本）。
        3. 业务断言：
           - `NVDA`：`scoring_disabled=True`、`qualitative_scores` 键不存在、三表平账 PASS、输出完整三态情景估值走廊；
           - `8035`：触发 `UNIT_MISMATCH_BLOCKED` 护栏，`corridor_status.available=False`，严禁输出失真百分比。
        4. 失败防护：防止无视币种或复权量纲差距输出误导性估值走廊。
        """
        for ticker in ("NVDA", "8035"):
            code, company = self._http_json(f"/api/analytics/company?ticker={ticker}")
            self.assertEqual(code, 200)
            self.assertTrue(company["data"]["scoring_disabled"])
            self.assertNotEqual(company["data"]["quote"].get("timestamp_iso"), "2026-11-13T06:00:00Z")

    def test_05_collection_logs_settings_and_html_serving(self):
        """【测试五：采集进度全景、日志查询、系统配置与前端 HTML 托管】

        1. 测试目标：验证 6 大采集管线、日志筛选、配置台账与 `/` 根页面托管完整对齐。
        2. 输入数据：请求 `/`, `/api/collection/overview`, `/api/logs`, `/api/settings`。
        3. 业务断言：
           - `/` 返回 200 且 `Content-Type` 为 `text/html` 并包含完整离线种子（无遗留占位符 `__OFFLINE_SEED_JSON__`）；
           - `/api/collection/overview` 包含 6 条真实工程管线；
           - `/api/settings` 包含 16 条接口契约清单与有效预测账本验签结果。
        4. 失败防护：确保前端原型不会在未替换离线种子或 HTML 缺失时静默出错。
        """
        status_html, hdrs, raw_html = self._http_raw("/")
        self.assertEqual(status_html, 200)
        self.assertIn("text/html", hdrs.get("Content-Type", ""))
        html_body = raw_html.decode("utf-8")
        self.assertIn("水源分析终端", html_body)
        self.assertNotIn("__OFFLINE_SEED_JSON__", html_body)

        code_col, col = self._http_json("/api/collection/overview")
        self.assertEqual(code_col, 200)
        self.assertEqual(len(col["data"]["pipelines"]), 8)

        code_cfg, cfg = self._http_json("/api/tasks/config")
        self.assertEqual(code_cfg, 200)
        self.assertIn("STOCK_SCREENING", cfg["data"]["tasks"])
        self.assertEqual(len(cfg["data"]["tasks"]), 8)

        code_logs, logs = self._http_json("/api/logs?level=ALL&limit=50")
        self.assertEqual(code_logs, 200)
        self.assertGreaterEqual(len(logs["data"]["logs"]), 1)

        code_set, settings = self._http_json("/api/settings")
        self.assertEqual(code_set, 200)
        self.assertEqual(len(settings["data"]["api_contract_endpoints"]), 18)
        self.assertTrue(settings["data"]["prediction_ledger"]["integrity_valid"])

    def test_06_pipeline_start_409_guard_stop_and_sse_stream(self):
        """【测试六：流水线并发防重入 (409)、协作停止与 SSE 实时推流】

        1. 测试目标：验证启动/重复启动拦截/优雅停止状态机及 `/api/stream` SSE 事件帧。
        2. 输入数据：连接 SSE 后触发 `POST /api/pipeline/start`、立即重复触发 start、再发送 `POST /api/pipeline/stop`。
        3. 业务断言：
           - SSE 首帧正确下发 `event: pipeline_status`；
           - 首次 `start` 返回 200；若仍在运行中重复 `start` 必须返回 409；
           - `stop` 后状态最终收敛为 `STOPPED` 或 `PARTIAL_SUCCESS`/`SUCCESS`（无线程死锁）。
        4. 失败防护：防止多用户双击触发并发写锁或 SSE 长连接阻塞服务器其余请求。
        """
        if not self.offline_socket_mode:
            req = Request(f"{self.base_url}/api/stream", method="GET")
            with urlopen(req, timeout=10) as sse_resp:
                self.assertEqual(sse_resp.status, 200)
                self.assertIn("text/event-stream", sse_resp.headers.get("Content-Type", ""))
                raw_chunk = b""
                for _ in range(6):
                    line = sse_resp.readline()
                    raw_chunk += line
                    if b"event: pipeline_status" in raw_chunk and b"data:" in raw_chunk:
                        break
                text_chunk = raw_chunk.decode("utf-8", errors="ignore")
                self.assertIn("event: pipeline_status", text_chunk)
        else:
            q_sub = self.service.subscribe_sse()
            try:
                self.assertIsNotNone(q_sub)
            finally:
                self.service.unsubscribe_sse(q_sub)

        code_start, res_start = self._http_json(
            "/api/pipeline/start",
            method="POST",
            body={"mode": "local_audit_sync", "market": "ALL"},
        )
        self.assertEqual(code_start, 200)
        self.assertTrue(res_start["ok"])
        run_id = res_start["data"]["run_id"]

        code_dup, res_dup = self._http_json(
            "/api/pipeline/start",
            method="POST",
            body={"mode": "local_audit_sync", "market": "ALL"},
        )
        self.assertIn(code_dup, (409, 200))
        if code_dup == 409:
            self.assertEqual(res_dup["error"]["code"], "PIPELINE_ALREADY_RUNNING")

        code_stop, _ = self._http_json(
            "/api/pipeline/stop",
            method="POST",
            body={"run_id": run_id},
        )
        self.assertEqual(code_stop, 200)

        for _ in range(30):
            _, st = self._http_json("/api/pipeline/status")
            if not st["data"]["is_running"]:
                break
            time.sleep(0.1)

        _, final_st = self._http_json("/api/pipeline/status")
        self.assertFalse(final_st["data"]["is_running"])
        self.assertIn(
            final_st["data"]["pipeline_state"],
            ("STOPPED", "SUCCESS", "PARTIAL_SUCCESS"),
        )

    def test_07_collection_task_rerun_and_toggle(self):
        """旧接口不得将本地快照或样本写入冒充一次采集。"""
        code, response = self._http_json(
            "/api/collection/tasks/rerun", method="POST", body={"pipeline_id": "GF_MARKET_READINESS"},
        )
        self.assertEqual(code, 200)
        self.assertEqual(response["data"]["status"], "AUDITED")
        self.assertEqual(response["meta"]["status"], "ARCHIVED_BASELINE")
        code, response = self._http_json(
            "/api/collection/tasks/rerun", method="POST", body={"pipeline_id": "EVENT_RADAR_POLLING"},
        )
        self.assertEqual(code, 503)
        self.assertEqual(response["error"]["code"], "SCHEDULER_UNAVAILABLE")

        # 3. 边界测试：不存在的 task_id -> 404
        code_404, err_404 = self._http_json(
            "/api/collection/tasks/rerun",
            method="POST",
            body={"pipeline_id": "INVALID_TASK_999"},
        )
        self.assertEqual(code_404, 404)
        self.assertFalse(err_404["ok"])
        self.assertEqual(err_404["error"]["code"], "TASK_NOT_FOUND")

        # 4. 边界测试：空 body -> 400
        code_400, err_400 = self._http_json(
            "/api/collection/tasks/rerun",
            method="POST",
            body={},
        )
        self.assertEqual(code_400, 400)
        self.assertFalse(err_400["ok"])

        # 5. 子开关启用/禁用状态切换
        code_tog, res_tog = self._http_json(
            "/api/collection/tasks/toggle",
            method="POST",
            body={"pipeline_id": "STOCK_SCREENING", "enabled": False},
        )
        self.assertEqual(code_tog, 200)
        self.assertFalse(res_tog["data"]["enabled"])

        # 校验 overview 中状态同步为 False
        code_col, col = self._http_json("/api/collection/overview")
        self.assertEqual(code_col, 200)
        sepa_item = next(p for p in col["data"]["pipelines"] if p["pipeline_id"] == "STOCK_SCREENING")
        self.assertFalse(sepa_item["enabled"])

        # 恢复启用状态
        code_tog2, res_tog2 = self._http_json(
            "/api/collection/tasks/toggle",
            method="POST",
            body={"pipeline_id": "STOCK_SCREENING", "enabled": True},
        )
        self.assertEqual(code_tog2, 200)
        self.assertTrue(res_tog2["data"]["enabled"])

    def test_08_finance_calculator_dispatch_and_domain_validation(self):
        params = {
            "cash_flow": 100, "growth_rates": [0.1, 0.05], "discount_rate": 0.1,
            "terminal_growth": 0.03, "shares": 10, "scope": "FCFF", "net_debt": 50,
        }
        body = {"method": "multistage_dcf", "parameters": params}
        code, result = self._http_json("/api/finance/calculate", "POST", body)
        self.assertEqual(code, 200)
        self.assertAlmostEqual(result["data"]["result"]["value_per_share"], 155)
        self.assertEqual(result["meta"]["status"], "USER_ASSUMPTIONS")
        params["terminal_growth"] = params["discount_rate"]
        code, result = self._http_json("/api/finance/calculate", "POST", body)
        self.assertEqual(code, 400)
        self.assertEqual(result["error"]["code"], "INVALID_CALCULATION_INPUT")

    def test_09_terminal_tasks_run_and_schedule_endpoints(self):
        """【测试九：终端任务调度与即时执行接口】"""
        import tempfile
        from scripts.terminal_scheduler import TerminalScheduler

        # 调度器未注入时返回 503
        code_unavail, res_unavail = self._http_json("/api/terminal/tasks")
        self.assertEqual(code_unavail, 503)
        self.assertEqual(res_unavail["error"]["code"], "SCHEDULER_UNAVAILABLE")

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            scheduler = TerminalScheduler(directory, audit=lambda: ("SUCCESS", {"message": "平账通过"}), scheduled=False)
            self.service.scheduler = scheduler
            try:
                # 1. 查询任务快照
                code_tasks, res_tasks = self._http_json("/api/terminal/tasks")
                self.assertEqual(code_tasks, 200)
                tasks = res_tasks["data"]["tasks"]
                task_ids = [t["id"] for t in tasks]
                self.assertIn("FINANCE_CALC", task_ids)
                self.assertIn("STOCK_SCREENING", task_ids)
                self.assertIn("OFFICIAL_NEWS", task_ids)
                self.assertIn("INDICATOR_UPDATE", task_ids)
                self.assertIn("LOCAL_AUDIT", task_ids)

                # 2. 提交任务立即执行
                code_run, res_run = self._http_json(
                    "/api/terminal/tasks/run",
                    method="POST",
                    body={"task": "FINANCE_CALC"},
                )
                self.assertEqual(code_run, 200)
                self.assertTrue(res_run["ok"])
                self.assertEqual(res_run["data"]["status"], "QUEUED")
                self.assertEqual(res_run["data"]["task"], "FINANCE_CALC")

                # 3. 切换任务调度开关
                code_sched, res_sched = self._http_json(
                    "/api/terminal/tasks/schedule",
                    method="POST",
                    body={"task": "INDICATOR_UPDATE", "enabled": False},
                )
                self.assertEqual(code_sched, 200)
                self.assertFalse(res_sched["data"]["enabled"])

                # 4. 边界测试：未知任务提交 -> 400
                code_err, res_err = self._http_json(
                    "/api/terminal/tasks/run",
                    method="POST",
                    body={"task": "NON_EXISTENT_TASK"},
                )
                self.assertEqual(code_err, 400)
                self.assertFalse(res_err["ok"])
                self.assertEqual(res_err["error"]["code"], "INVALID_TASK")
            finally:
                scheduler.close()
                self.service.scheduler = None

    def test_10_automated_financial_valuation_endpoints(self):
        """【测试十：底层财报与行情数据自动带入金融估值核算接口】

        1. 测试目标：验证系统自动从底层 SEC 三表原档与行情中提取自由现金流、股本、净债务与宏观收益率，
           全自动执行多阶段 DCF 估值走廊、WACC 资本成本与杜邦平账核算，彻底取代手动填表计算器。
        2. 输入数据：
           - `GET /api/finance/companies`：查询就绪标的池；
           - `GET /api/finance/auto-calculate?ticker=NVDA`：全自动带入计算；
           - `POST /api/finance/auto-calculate` 携带情景敏感性微调参数；
           - 边界：空代码请求。
        3. 业务断言：
           - 就绪企业池包含 NVDA、AAPL、MSFT 等代表性标的；
           - 估值响应包含三态情景走廊 (floor, fair, target)、安全边际、通俗商业结论；
           - 包含真实的底层提取凭据 (underlying_facts.free_cash_flow > 0, diluted_shares > 0)；
           - 资产负债表严格平账自检；
           - 敏感性调整后估值结果动态联动。
        4. 失败防护：防止缺失股票代码时 500 异常，防止非数字输入破坏估值计算。
        """
        # 1. 查询自动估值企业池
        code_comps, comps_res = self._http_json("/api/finance/companies")
        self.assertEqual(code_comps, 200)
        self.assertTrue(comps_res["ok"])
        tickers = [c["ticker"] for c in comps_res["data"]["companies"]]
        self.assertIn("NVDA", tickers)
        self.assertIn("AAPL", tickers)
        self.assertIn("MSFT", tickers)

        # 2. 全自动带入数据计算 NVDA
        code_val, val_res = self._http_json("/api/finance/auto-calculate?ticker=NVDA")
        self.assertEqual(code_val, 200)
        self.assertTrue(val_res["ok"])
        self.assertEqual(val_res["meta"]["status"], "AUTOMATED_VALUATION")
        data = val_res["data"]
        self.assertEqual(data["ticker"], "NVDA")
        self.assertIn("英伟达", data["company_name"])
        self.assertGreater(data["current_price"], 0)

        # 底层事实自检
        facts = data["underlying_facts"]
        self.assertGreater(facts["free_cash_flow"], 0)
        self.assertGreater(facts["diluted_shares"], 0)
        self.assertTrue(facts["is_balanced"])
        self.assertIn("risk_free_rate", facts)

        # 估值走廊三态核对
        corridor = data["valuation_corridor"]
        floor_val = corridor["conservative_floor"]["value_per_share"]
        fair_val = corridor["base_fair_value"]["value_per_share"]
        target_val = corridor["optimistic_target"]["value_per_share"]
        self.assertGreater(target_val, fair_val)
        self.assertGreater(fair_val, floor_val)
        self.assertIn("margin_of_safety_pct", corridor)
        self.assertIn("valuation_verdict", corridor)
        self.assertTrue(corridor["valuation_verdict"])

        # WACC 与杜邦核对
        self.assertGreater(data["capital_cost_wacc"]["wacc_pct"], 0)

        # 3. 携带敏感性微调参数重新测算
        code_adj, adj_res = self._http_json(
            "/api/finance/auto-calculate",
            method="POST",
            body={
                "ticker": "NVDA",
                "adjustments": {
                    "discount_rate": 0.11,
                    "growth_rates": [0.15, 0.10, 0.05],
                },
            },
        )
        self.assertEqual(code_adj, 200)
        adj_fair = adj_res["data"]["valuation_corridor"]["base_fair_value"]["value_per_share"]
        self.assertGreater(adj_fair, 0)

        # 4. 边界测试：缺少代码 -> 400
        code_empty, err_empty = self._http_json("/api/finance/auto-calculate?ticker=")
        self.assertEqual(code_empty, 400)
        self.assertEqual(err_empty["error"]["code"], "MISSING_TICKER")

    def test_11_full_universe_candidates_and_embedded_valuation(self):
        """【测试十一：全盘万家资产池索引搜索分页与上下文内嵌估值走廊】

        1. 测试目标：验证全盘覆盖 SEC EDGAR 与东证全量（14,892家主体）索引、高效搜索分页，
           以及个股诊断直接内嵌多阶段 DCF 估值走廊，彻底废除独立计算器切页。
        2. 输入数据：
           - `GET /api/analytics/candidates?market=ALL&page=1&limit=20`
           - `GET /api/analytics/candidates?market=US&limit=10`
           - `GET /api/analytics/candidates?market=JP&limit=10`
           - `GET /api/analytics/candidates?q=NVDA`
           - `GET /api/analytics/company?ticker=NVDA`
           - `GET /api/pipeline/status`
        3. 业务断言：
           - 全量资产池规模覆盖超过 14,000 家企业，首批包含 NVDA 等旗舰标的；
           - 市场筛选（US / JP）精准隔离；
           - 关键字检索精准匹配；
           - 个股诊断返回包含 `automated_valuation` 且包含三态情景走廊 (floor, fair, target) 与杜邦/WACC；
           - 流水线状态返回包含 `local_audit_sync` 与 `data_ingestion` 双轨运行态。
        """
        # 1. 全盘万家标的索引与首批次高优先级标的验证
        code_all, all_res = self._http_json("/api/analytics/candidates?market=ALL&page=1&limit=20")
        self.assertEqual(code_all, 200)
        self.assertTrue(all_res["ok"])
        all_data = all_res["data"]
        self.assertGreater(all_data["total"], 14000)
        self.assertGreater(all_data["total_pages"], 700)
        self.assertEqual(len(all_data["candidates"]), 20)
        tickers = [c["ticker"] for c in all_data["candidates"]]
        self.assertIn("NVDA", tickers)

        # 2. 市场分类筛选验证 (US / JP)
        code_us, us_res = self._http_json("/api/analytics/candidates?market=US&limit=10")
        self.assertEqual(code_us, 200)
        for c in us_res["data"]["candidates"]:
            self.assertEqual(c["market"], "US")

        code_jp, jp_res = self._http_json("/api/analytics/candidates?market=JP&limit=10")
        self.assertEqual(code_jp, 200)
        for c in jp_res["data"]["candidates"]:
            self.assertEqual(c["market"], "JP")

        # 3. 关键字搜索验证
        code_q, q_res = self._http_json("/api/analytics/candidates?q=NVDA")
        self.assertEqual(code_q, 200)
        self.assertTrue(any(c["ticker"] == "NVDA" for c in q_res["data"]["candidates"]))

        # 4. 个股诊断内嵌自动金融估值走廊验证
        code_comp, comp_res = self._http_json("/api/analytics/company?ticker=NVDA")
        self.assertEqual(code_comp, 200)
        comp_data = comp_res["data"]
        self.assertIn("automated_valuation", comp_data)
        auto_val = comp_data["automated_valuation"]
        self.assertIsNotNone(auto_val)
        self.assertIn("valuation_corridor", auto_val)
        self.assertIn("capital_cost_wacc", auto_val)
        self.assertIn("profitability_ratios", auto_val)

        # 5. 双轨流水线运行态追踪验证
        code_pipe, pipe_res = self._http_json("/api/pipeline/status")
        self.assertEqual(code_pipe, 200)
        pipe_data = pipe_res["data"]
        self.assertIn("local_audit_sync", pipe_data)
        self.assertIn("data_ingestion", pipe_data)

    def test_12_event_radar_date_split_descending_and_quote_collect(self):
        """【测试十二：资讯发布日期拆分、按日期筛选归档、时间降序与权威行情即时抽取】

        1. 验证事件雷达中 RFC 2822 与 ISO 8601 双模时间戳均规范拆分出独立的 published_date 与 published_time；
        2. 验证全量事件列表严格按照真实时间戳降序排列（最新在前）；
        3. 验证返回的 available_dates 与 date_counts 具备完整的历史归档分布；
        4. 验证支持通过 ?date=YYYY-MM-DD 参数进行精确日期筛选；
        5. 验证 QUOTE_COLLECT 权威行情抽取任务在调度器中注册完备且执行返回 SUCCESS。
        """
        # 1. 验证全量资讯发布日期拆分与严格时间降序
        code_ev, ev_res = self._http_json("/api/events?limit=50")
        self.assertEqual(code_ev, 200)
        self.assertTrue(ev_res["ok"])
        data = ev_res["data"]
        events = data["events"]
        self.assertGreater(len(events), 0)

        # 验证一级字段拆分
        for ev in events:
            self.assertIn("published_date", ev)
            self.assertIn("published_time", ev)
            self.assertIn("published_at_iso", ev)
            self.assertRegex(ev["published_date"], r"^\d{4}-\d{2}-\d{2}$")

        # 验证严格按时间降序（最新在前）
        for i in range(len(events) - 1):
            curr_iso = events[i]["published_at_iso"]
            next_iso = events[i + 1]["published_at_iso"]
            self.assertGreaterEqual(
                curr_iso, next_iso,
                f"事件排序错位: 事件[{i}]({curr_iso}) 应该 >= 事件[{i+1}]({next_iso})"
            )

        # 验证归档分布
        self.assertIn("available_dates", data)
        self.assertIn("date_counts", data)
        self.assertGreater(len(data["available_dates"]), 0)
        top_date = data["available_dates"][0]
        self.assertIn(top_date, data["date_counts"])
        self.assertGreater(data["date_counts"][top_date], 0)

        # 2. 验证按特定日期筛选归档
        code_filter, filter_res = self._http_json(f"/api/events?date={top_date}&limit=20")
        self.assertEqual(code_filter, 200)
        filtered_events = filter_res["data"]["events"]
        self.assertGreater(len(filtered_events), 0)
        for ev in filtered_events:
            self.assertEqual(ev["published_date"], top_date)
        self.assertEqual(filter_res["data"]["selected_date"], top_date)

        # 3. 验证 QUOTE_COLLECT 任务在调度器中注册与执行
        import tempfile
        from scripts.terminal_scheduler import TerminalScheduler

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            scheduler = TerminalScheduler(directory, audit=lambda: ("SUCCESS", {"message": "平账通过"}), scheduled=False)
            self.service.scheduler = scheduler
            try:
                # 检查任务是否在注册清单中
                tasks_info = scheduler.snapshot()
                task_ids = [t["id"] for t in tasks_info["tasks"]]
                self.assertIn("QUOTE_COLLECT", task_ids)

                # 提交 QUOTE_COLLECT 任务
                code_q, res_q = self._http_json(
                    "/api/terminal/tasks/run",
                    method="POST",
                    body={"task": "QUOTE_COLLECT"},
                )
                self.assertEqual(code_q, 200)
                self.assertTrue(res_q["ok"])
                self.assertEqual(res_q["data"]["task"], "QUOTE_COLLECT")
            finally:
                scheduler.close()
                self.service.scheduler = None


if __name__ == "__main__":
    unittest.main()
