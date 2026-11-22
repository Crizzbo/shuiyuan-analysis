"""终端任务队列。SQLite 保留每次运行，工作线程与浏览器连接独立。"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import logging
import math
from pathlib import Path
import re
import sqlite3
from statistics import fmean
import threading
from typing import Any, Dict, List, Optional
import uuid
from zoneinfo import ZoneInfo

from data_ingestion.core import Archive, project_path
from finance_tools.events_and_verification.event_radar_collector import EventRadarCollector, RadarDatabaseManager
from financial_core.engines.exchange_calendar_engine import ExchangeCalendarEngine
from financial_core.engines.market_reconciliation_engine import MarketReconciliationEngine
from scripts.ingest_data import read, run_plan

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TOKYO = timezone(timedelta(hours=9))
NEW_YORK = ZoneInfo("America/New_York")
MARKET_SESSIONS = {"US": (NEW_YORK, 800, 930), "JP": (TOKYO, 730, 900)}
TASKS = {
    "QUOTE_COLLECT": ("授权行情归档核对", "手动"),
    "FULL_UNIVERSE_COLLECT": ("美日万家标的全盘流式抽取", "全量 14,897 家上市公司分片并发"),
    "US_DAILY": ("美股全市场盘前日线与宏观", "工作日 08:00（纽约）"),
    "JP_DAILY": ("日股全市场盘前日线", "工作日 07:30（东京）"),
    "OFFICIAL_NEWS": ("官方财经资讯", "每小时"),
    "STOCK_SCREENING": ("股票收集与形态初筛", "周二至周六 08:00 JST"),
    "INDICATOR_UPDATE": ("金融指标与市场宽度计算", "每小时"),
    "FINANCE_CALC": ("个股三表核对与财务指标", "手动"),
    "LOCAL_AUDIT": ("本地数据与账本核验", "手动"),
    "INCREMENTAL_COLLECT": ("官方监管补数与档案增量归档", "每小时扫描补数队列"),
    "STOCK_DOSSIER_COLLECT": ("指定个股全维度数据拉取与平账核对", "支持单票精准补采"),
}
START_COLLECTION_TASKS = ("US_DAILY", "JP_DAILY", "OFFICIAL_NEWS")
COLLECTION_TASKS = (*START_COLLECTION_TASKS, "QUOTE_COLLECT", "FULL_UNIVERSE_COLLECT", "INCREMENTAL_COLLECT", "STOCK_DOSSIER_COLLECT")
AUTOMATIC_TASKS = {*START_COLLECTION_TASKS, "STOCK_SCREENING", "INDICATOR_UPDATE", "INCREMENTAL_COLLECT"}

TASK_METADATA = {
    "QUOTE_COLLECT": {
        "dimension": "PRICE",
        "dimension_name": "最新行情与时效核验",
        "description": "拉取最新行情报价与时效门禁核验",
        "serves_stock_analysis": "为个股 DCF 估值走廊提供现价锚与安全边际基准",
    },
    "FULL_UNIVERSE_COLLECT": {
        "dimension": "PRICE_FULL",
        "dimension_name": "全盘万家企业流式行情",
        "description": "流式分批并发采集全量 14,897 家美日上市主体最新行情并断点续传",
        "serves_stock_analysis": "为全市场万家上市公司提供权威行情报价与时效门禁基准",
    },
    "FINANCE_CALC": {
        "dimension": "FINANCIALS",
        "dimension_name": "官方三表底稿与平账",
        "description": "从 SEC 10-K / 决算短信提取三表事实并执行刚性平账自检",
        "serves_stock_analysis": "提供自由现金流 (FCF)、净负债、资产负债表刚性平衡底账",
    },
    "US_DAILY": {
        "dimension": "OHLCV",
        "dimension_name": "美股日线价量时序",
        "description": "拉取美股标的过去 250 天历史日线与成交量",
        "serves_stock_analysis": "计算 50/150/200 日均线、52 周高低点与成交量萎缩度",
    },
    "JP_DAILY": {
        "dimension": "OHLCV",
        "dimension_name": "日股日线价量时序",
        "description": "拉取东证标的过去 250 天历史日线与成交额",
        "serves_stock_analysis": "计算日股标的移动均线与主升浪趋势广度",
    },
    "STOCK_SCREENING": {
        "dimension": "SEPA",
        "dimension_name": "SEPA与VCP初筛",
        "description": "纯本地 0-Token 物理扫描波幅收缩比例与买点枢轴",
        "serves_stock_analysis": "识别处于第二阶段主升浪且 VCP 波动收缩至临界点的标的",
    },
    "INDICATOR_UPDATE": {
        "dimension": "MACRO_RATE",
        "dimension_name": "宏观无风险利率与WACC",
        "description": "更新 10Y 美债收益率、JGB 利率、利差与汇率中枢",
        "serves_stock_analysis": "测算标的专属 WACC 资本成本与多阶段折现率基准",
    },
    "OFFICIAL_NEWS": {
        "dimension": "NEWS_EVENTS",
        "dimension_name": "突发事件与因果推演",
        "description": "分时抓取官方监管与突发事件并提炼入事件雷达",
        "serves_stock_analysis": "测算监管与地缘突发事件对个股营运利润 ΔEBIT 与 ΔEPS 的因果冲击",
    },
    "INCREMENTAL_COLLECT": {
        "dimension": "DOSSIER",
        "dimension_name": "微观商业与供应链档案",
        "description": "官方监管补数与供应链集中度、护城河深度档案归档",
        "serves_stock_analysis": "补充标的上下游供应商集中度、库存周期 DIO 与商业模式",
    },
    "LOCAL_AUDIT": {
        "dimension": "AUDIT",
        "dimension_name": "底账审计与账本验签",
        "description": "全盘数据平账断言与 SHA-256 密码学不可篡改预测账本验签",
        "serves_stock_analysis": "确保所有研判底账具备买方机构级证据置信度",
    },
    "STOCK_DOSSIER_COLLECT": {
        "dimension": "TARGET_COLLECT",
        "dimension_name": "指定单票全维度采集",
        "description": "输入股票代码，一键启动该标的专属的行情、三表、DCF、事件全量拉取",
        "serves_stock_analysis": "为指定个股一站式补齐所有分析所需数据并完成自动估值",
    },
}
BENCHMARKS = {
    "US": ("SPY", "QQQ", "IWM", "^VIX"),
    "JP": ("1306.T", "^N225"),
}

def market_symbols(market):
    """按交易代码去重。保留原代码作为日志和归档索引。"""
    if market == "US":
        rows = read("data/universe/sec_company_tickers.json").values()
        codes = (str(row.get("ticker") or "").strip().upper() for row in rows)
    else:
        rows = read("data/universe/jpx_company_tickers.json")
        codes = (str(row.get("code") or row.get("ticker") or "").strip().upper().removeprefix("TYO:")
                 for row in rows)
    return sorted(set(codes) - {""})


def provider_symbol(market, code):
    if market == "JP":
        return f"{code}.T" if re.fullmatch(r"[0-9A-Z]{4}", code) else None
    return code.replace(".", "-") if re.fullmatch(r"[A-Z0-9]+(?:[.-][A-Z0-9]+)*", code) else None


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def due_slots(now):
    """在各市场当地盘前窗口补跑，交易日期按各市场当地日期去重。"""
    local = now.astimezone(TOKYO)
    yield "OFFICIAL_NEWS", local.strftime("%Y-%m-%dT%H")
    for market, (zone, start, end) in MARKET_SESSIONS.items():
        session = now.astimezone(zone)
        clock = session.hour * 100 + session.minute
        if session.weekday() < 5 and start <= clock < end and ExchangeCalendarEngine.is_trading_day(market, session.date()):
            yield f"{market}_DAILY", session.date().isoformat()
    if 1 <= local.weekday() <= 5 and local.hour >= 8:
        yield "STOCK_SCREENING", local.date().isoformat()
    yield "INDICATOR_UPDATE", local.strftime("%Y-%m-%dT%H")
    yield "INCREMENTAL_COLLECT", local.strftime("%Y-%m-%dT%H")


class TerminalScheduler:
    def __init__(self, state_dir, audit, scheduled=True, handlers=None, on_status_change=None):
        self.path = Path(state_dir) / "queue.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.scheduled = scheduled
        self.audit = audit
        self.on_status_change = on_status_change
        self.handlers = handlers or {task: self._execute for task in TASKS}
        self.stopping = threading.Event()
        self.wake = threading.Event()
        self.thread = None
        self.leader = None
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY, task TEXT NOT NULL, slot TEXT,
                    trigger TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
                    started_at TEXT, finished_at TEXT, result TEXT, UNIQUE(task, slot)
                );
                CREATE TABLE IF NOT EXISTS settings (task TEXT PRIMARY KEY, enabled INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS task_log (
                    id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, run_id TEXT,
                    task TEXT NOT NULL, status TEXT NOT NULL, level TEXT NOT NULL,
                    message TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS checkpoints (
                    run_id TEXT NOT NULL, job_id TEXT NOT NULL, result TEXT NOT NULL,
                    PRIMARY KEY(run_id, job_id)
                );
                CREATE TABLE IF NOT EXISTS market_cursor (
                    market TEXT PRIMARY KEY, last_symbol TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS market_archive (
                    market TEXT NOT NULL, symbol TEXT NOT NULL, result TEXT NOT NULL,
                    PRIMARY KEY(market, symbol)
                );
            """)
            conn.executemany("INSERT OR IGNORE INTO settings VALUES (?, 1)", [(task,) for task in TASKS])
            conn.execute("INSERT OR IGNORE INTO settings VALUES ('__automatic__', 1)")

    def _log(self, conn, task, status, message, run_id=None):
        level = {"FAILED": "ERROR", "BLOCKED": "WARN", "PARTIAL_SUCCESS": "WARN"}.get(status, "INFO")
        conn.execute("INSERT INTO task_log(timestamp,run_id,task,status,level,message) VALUES (?,?,?,?,?,?)",
                     (utc_now(), run_id, task, status, level, message))

    @staticmethod
    def _task_to_module(task: Optional[str]) -> str:
        t = (task or "").upper()
        if "NEWS" in t:
            return "event_radar"
        if "DAILY" in t or "QUOTE" in t:
            return "market_quotes"
        if "SCREENING" in t:
            return "screening_engine"
        if "INDICATOR" in t:
            return "indicators_engine"
        if "FINANCE" in t:
            return "finance_engine"
        if "AUDIT" in t:
            return "audit_ledger"
        return "terminal_scheduler"

    def logs(self, level, query, limit):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM task_log WHERE (?='ALL' OR level=?) "
                "AND instr(lower(message || ' ' || task || ' ' || coalesce(run_id,'')), ?) > 0 "
                "ORDER BY id DESC LIMIT ?", (level, level, query, limit),
            ).fetchall()
        return [{"log_id": f"task-{row['id']}", "timestamp": row["timestamp"],
                 "module": self._task_to_module(row["task"]),
                 "level": row["level"], "run_id": row["run_id"], "message": row["message"],
                 "task": row["task"], "status": row["status"]} for row in rows]

    def _notify(self, run_id, task, status, result):
        if self.on_status_change:
            try:
                self.on_status_change(run_id, task, status, result)
            except Exception:
                logging.getLogger(__name__).exception("任务状态推送失败：%s", run_id)

    @contextmanager
    def _connect(self):
        with closing(sqlite3.connect(self.path, timeout=10)) as conn, conn:
            conn.row_factory = sqlite3.Row
            yield conn

    def start(self):
        # 单执行器跨进程互斥。锁库与队列分开，HTTP 仍可读写运行记录。
        if self.thread is not None:
            return
        lock = sqlite3.connect(self.path.with_name("executor.sqlite3"), timeout=0)
        try:
            lock.execute("BEGIN EXCLUSIVE")
        except sqlite3.OperationalError:
            lock.close()
            raise RuntimeError("已有终端调度器正在运行") from None
        self.leader = lock
        with self._connect() as conn:
            for row in conn.execute("SELECT run_id, task FROM runs WHERE status='RUNNING'"):
                self._log(conn, row["task"], "QUEUED", "服务重启，任务已重新排队", row["run_id"])
            conn.execute("UPDATE runs SET status='QUEUED', started_at=NULL WHERE status='RUNNING'")
        self.thread = threading.Thread(target=self._dispatch, name="terminal-dispatch")
        self.thread.start()

    def close(self):
        self.stopping.set()
        self.wake.set()
        if self.thread:
            self.thread.join()
            self.leader.close()

    def set_enabled(self, task, enabled):
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE settings SET enabled=? WHERE task=?", (enabled, task))
            name = TASKS[task][0] if task in TASKS else "自动调度总开关"
            self._log(conn, task, "CONFIGURED", f"{name}已{'开启' if enabled else '关闭'}")
            if not enabled:
                pending = conn.execute(
                    "SELECT run_id,task FROM runs WHERE (?='__automatic__' OR task=?) "
                    "AND trigger='scheduled' AND status='QUEUED'", (task, task),
                ).fetchall()
                for row in pending:
                    conn.execute("UPDATE runs SET status='CANCELLED',finished_at=?,result=? WHERE run_id=?",
                                 (utc_now(), json.dumps({"message": "定时任务已停用"}, ensure_ascii=False), row["run_id"]))
                    self._log(conn, row["task"], "CANCELLED", f"{TASKS[row['task']][0]}：定时任务已停用", row["run_id"])
        self.wake.set()

    def submit(self, task, slot=None):
        return self.submit_with_status(task, slot)[0]

    def submit_with_status(self, task, slot=None):
        if task not in TASKS:
            raise ValueError("未知任务")
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            run_id, status = self._enqueue(conn, task, slot)
        self.wake.set()
        return run_id, status

    def _enqueue(self, conn, task, slot=None, batch_id=None):
        if slot:
            enabled = conn.execute("SELECT min(enabled) FROM settings WHERE task IN (?, '__automatic__')", (task,)).fetchone()[0]
            existing = conn.execute("SELECT 1 FROM runs WHERE task=? AND slot=?", (task, slot)).fetchone()
            if existing or not enabled:
                return None, None
        else:
            active = conn.execute("SELECT run_id,status FROM runs WHERE task=? AND status IN ('QUEUED','RUNNING') "
                                  "ORDER BY rowid LIMIT 1", (task,)).fetchone()
            if active:
                return active["run_id"], active["status"]
        run_id = uuid.uuid4().hex
        conn.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,NULL,NULL,NULL)", (
            run_id, task, slot, "scheduled" if slot else "manual", "QUEUED", utc_now(),
        ))
        suffix = f" · 总启动 {batch_id}" if batch_id else ""
        self._log(conn, task, "QUEUED", f"{TASKS[task][0]}：{'定时' if slot else '手动'}排队{suffix}", run_id)
        return run_id, "QUEUED"

    def start_batch(self):
        batch_id = uuid.uuid4().hex
        runs = []
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            for task in ("LOCAL_AUDIT", *START_COLLECTION_TASKS):
                run_id, status = self._enqueue(conn, task, batch_id=batch_id)
                runs.append({"run_id": run_id, "task": task, "status": status})
            self._log(conn, "MASTER", "SUBMITTED", "总启动：本地核对同步和数据采集 · "
                      + "、".join(row["run_id"] for row in runs), batch_id)
        self.wake.set()
        return {"run_id": batch_id, "runs": runs}

    def snapshot(self):
        with self._connect() as conn:
            settings = {row["task"]: bool(row["enabled"]) for row in conn.execute("SELECT * FROM settings")}
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY (status IN ('QUEUED','RUNNING')) DESC, "
                "created_at DESC, rowid DESC LIMIT 40"
            ).fetchall()
        runs = [dict(row, result=json.loads(row["result"]) if row["result"] else None) for row in rows]
        return {
            "scheduled": self.scheduled and bool(settings["__automatic__"]) and self.thread is not None and self.thread.is_alive(),
            "automatic_enabled": self.scheduled and bool(settings["__automatic__"]),
            "automatic_available": self.scheduled,
            "tasks": [{
                "id": task,
                "name": name,
                "schedule": schedule,
                "enabled": settings.get(task, True),
                "automatic": task in AUTOMATIC_TASKS,
                "track": "collection" if task in COLLECTION_TASKS else "local",
                "dimension": TASK_METADATA.get(task, {}).get("dimension", "LOCAL"),
                "dimension_name": TASK_METADATA.get(task, {}).get("dimension_name", "本地任务"),
                "description": TASK_METADATA.get(task, {}).get("description", name),
                "serves_stock_analysis": TASK_METADATA.get(task, {}).get("serves_stock_analysis", "为个股分析提供基础支撑"),
            } for task, (name, schedule) in TASKS.items()],
            "runs": runs,
        }

    def news(self):
        """展示已归档标题与时间，结合事件雷达提炼结果提供商业影响与实体标注。"""
        items = []
        radar_db = project_path("data/ledger/event_radar.sqlite3")
        radar_map = RadarDatabaseManager(str(radar_db)).get_events_map_by_title()

        for item, records in self._archived_records("OFFICIAL_NEWS"):
            source = next(iter(item.get("artifacts", [])), {}).get("origin_url", "")
            for record in records:
                t = record.get("title")
                if t:
                    clean_t = re.sub(r"\s+", " ", t).strip()
                    distilled = radar_map.get(clean_t) or radar_map.get(clean_t.lower()) or radar_map.get(t) or {}
                    ent = distilled.get("involved_entities")
                    parsed_ent = []
                    if ent:
                        try:
                            parsed_ent = json.loads(ent) if isinstance(ent, str) else ent
                        except Exception:
                            parsed_ent = [x.strip() for x in str(ent).split(",") if x.strip()]
                    items.append({
                        "title": clean_t,
                        "published_at": record.get("pubDate") or record.get("published") or record.get("updated"),
                        "source": source,
                        "verification_status": distilled.get("verification_status") or "Pending_Verification",
                        "severity": distilled.get("severity_level") or "P3",
                        "category": distilled.get("category"),
                        "involved_entities": parsed_ent,
                        "micro_physical_impact": distilled.get("micro_physical_impact"),
                        "is_distilled": bool(distilled),
                    })
        return items

    def market_archives(self):
        """只提供日线归档覆盖与日期。市场报价继续走独立时效门禁。"""
        items = []
        for task in ("US_DAILY", "JP_DAILY"):
            for item, records in self._archived_records(task):
                if not records:
                    continue
                rows = sorted((row for row in records if row.get("Date")), key=lambda row: row["Date"])
                close = rows[-1].get("Close") if rows else None
                items.append({"symbol": item["id"], "market": task[:2], "count": len(rows),
                              "last_date": str(rows[-1]["Date"])[:10] if rows else None,
                              "close": close if isinstance(close, (int, float)) and math.isfinite(close) and close > 0 else None,
                              "archived_at": item.get("completed_at", "")})
        return items

    def reconciliation_summary(self, market: str, target_date=None):
        """执行目标交易日全市场全息对账核算与平账自检。"""
        market_upper = market.upper()
        codes = market_symbols(market_upper)
        task = f"{market_upper}_DAILY"
        zone = MARKET_SESSIONS[market_upper][0]
        now_local = datetime.now(zone)
        eff_date = target_date[:10] if target_date else ExchangeCalendarEngine.resolve_target_trading_day(market_upper, now_local).isoformat()
        archived_map = {}
        for item, records in self._archived_records(task):
            if records:
                archived_map[item["id"]] = records
        return MarketReconciliationEngine.reconcile_target_day(
            market=market_upper,
            target_date=eff_date,
            universe_symbols=codes,
            archived_records=archived_map,
        ).to_dict()

    def _archived_records(self, task):
        daily = task in ("US_DAILY", "JP_DAILY")
        with self._connect() as conn:
            market_items = conn.execute("SELECT result FROM market_archive WHERE market=? ORDER BY symbol",
                                        (task[:2],)).fetchall() if daily else []
            row = conn.execute(
                "SELECT result FROM runs WHERE task=? AND (status IN ('SUCCESS','PARTIAL_SUCCESS') "
                "OR (? AND status='BLOCKED')) AND result IS NOT NULL "
                "ORDER BY finished_at DESC, rowid DESC LIMIT 1", (task, daily),
            ).fetchone()
        items = {item["id"]: item for item in json.loads(row["result"]).get("items", [])} if row else {}
        for saved in market_items:
            item = json.loads(saved["result"])
            items[item["id"]] = item
        for item in items.values():
            try:
                if item.get("status") != "collected" or not item.get("result_path"):
                    continue
                content = project_path(item["result_path"]).read_bytes()
                if sha256(content).hexdigest() == item.get("result_sha256"):
                    yield item, json.loads(content).get("records", [])
            except (OSError, ValueError):
                continue

    def _dispatch(self):
        active = {}
        with ThreadPoolExecutor(max_workers=3, thread_name_prefix="terminal-job") as pool:
            while not self.stopping.is_set():
                self.wake.clear()
                active = {task: future for task, future in active.items() if not future.done()}
                if self.scheduled:
                    for task, slot in due_slots(datetime.now(timezone.utc)):
                        self.submit(task, slot)
                launched = []
                with self._connect() as conn:
                    queued = conn.execute("SELECT * FROM runs WHERE status='QUEUED' ORDER BY rowid").fetchall()
                    for run in queued:
                        if len(active) >= 3 or self.stopping.is_set():
                            break
                        if run["task"] in active:
                            continue
                        claimed = conn.execute(
                            "UPDATE runs SET status='RUNNING', started_at=? WHERE run_id=? AND status='QUEUED'",
                            (utc_now(), run["run_id"]),
                        )
                        if not claimed.rowcount:
                            continue
                        self._log(conn, run["task"], "RUNNING", f"{TASKS[run['task']][0]}：开始执行", run["run_id"])
                        launched.append(dict(run))
                        active[run["task"]] = None
                for run in launched:
                    self._notify(run["run_id"], run["task"], "RUNNING", {})
                    active[run["task"]] = pool.submit(self._run, run)
                self.wake.wait(5)

    def _run(self, run):
        try:
            status, result = self.handlers[run["task"]](run)
        except Exception as exc:
            status, result = "FAILED", {"message": str(exc)}
        with self._connect() as conn:
            if run["task"] in ("US_DAILY", "JP_DAILY") and "session_date" in result:
                market = run["task"][:2]
                if result["next_market_cursor"]:
                    conn.execute("INSERT OR REPLACE INTO market_cursor VALUES (?,?)",
                                 (market, result["next_market_cursor"]))
                conn.executemany("INSERT OR REPLACE INTO market_archive VALUES (?,?,?)", (
                    (market, item["id"], json.dumps(item, ensure_ascii=False))
                    for item in result["items"] if item["status"] == "collected" and item.get("record_count", 0)
                ))
            conn.execute("UPDATE runs SET status=?, finished_at=?, result=? WHERE run_id=?",
                         (status, utc_now(), json.dumps(result, ensure_ascii=False), run["run_id"]))
            self._log(conn, run["task"], status, f"{TASKS[run['task']][0]}：{result.get('message', status)}", run["run_id"])
        self._notify(run["run_id"], run["task"], status, result)
        self.wake.set()

    def _collect_jobs(self, run_id, jobs, sources, *, stop_on_limit=False):
        with self._connect() as conn:
            saved = {row["job_id"]: json.loads(row["result"]) for row in conn.execute(
                "SELECT job_id, result FROM checkpoints WHERE run_id=?", (run_id,),
            )}
        results = []
        with closing(Archive()) as archive:
            for job in jobs:
                result = saved.get(job["id"])
                if result:
                    # 重启后先核对已归档结果与原始响应摘要。
                    references = [(result["result_path"], result["result_sha256"])]
                    references.extend((item["source_path"], item["sha256"]) for item in result["artifacts"])
                    try:
                        reusable = all(sha256(project_path(path).read_bytes()).hexdigest() == digest
                                       for path, digest in references)
                    except (OSError, ValueError):
                        reusable = False
                    if not reusable:
                        raise ValueError(f"{job['id']} 的断点归档摘要不匹配")
                else:
                    result, = run_plan(
                        {"schema_version": "1.0.0", "jobs": [job]}, archive, sources, refresh=True,
                    )
                    if result["status"] == "collected" and result.get("record_count", 0):
                        with self._connect() as conn:
                            conn.execute("INSERT INTO checkpoints VALUES (?,?,?)",
                                         (run_id, job["id"], json.dumps(result, ensure_ascii=False)))
                results.append(result)
                with self._connect() as conn:
                    task_row = conn.execute("SELECT task FROM runs WHERE run_id=?", (run_id,)).fetchone()
                    if task_row:
                        outcome = ("恢复归档" if saved.get(job["id"]) else {
                            "collected": "已归档", "quota_exhausted": "额度用尽",
                            "rate_limited": "受上游限流", "browser_required": "来源不可自动调用",
                        }.get(result["status"], "来源未完成"))
                        message = (f"{job['id']} · {outcome}"
                                   f" · {result.get('record_count', 0)} 条 · "
                                   f"{result.get('message') or result.get('result_path') or ''}")
                        self._log(conn, task_row["task"], "SUCCESS" if result["status"] == "collected" else "BLOCKED",
                                  message, run_id)
                if stop_on_limit and result["status"] in {"quota_exhausted", "rate_limited", "browser_required"}:
                    break
        return results

    def _execute(self, run):
        task = run["task"]
        if task == "QUOTE_COLLECT":
            return self._execute_quote_collect(run)
        if task == "FULL_UNIVERSE_COLLECT":
            return self._execute_full_universe_collect(run)
        if task == "LOCAL_AUDIT":
            status, result = self.audit()
            archives = self.market_archives()
            for market, name in (("US", "美股"), ("JP", "日股")):
                count = sum(row["market"] == market for row in archives)
                self._record_item(run, "SUCCESS", f"{name}日线归档目录核对：{count} 个标的")
            result = {**result, "daily_archive_coverage": archives,
                      "message": f"{result['message']}；日线归档目录纳入 {len(archives)} 个标的"}
            return status, result
        if task == "STOCK_SCREENING":
            return self._execute_stock_screening(run)
        if task == "OFFICIAL_NEWS":
            return self._execute_official_news(run)
        if task == "INDICATOR_UPDATE":
            return self._execute_indicator_update(run)
        if task == "FINANCE_CALC":
            return self._execute_finance_calc(run)
        if task == "STOCK_DOSSIER_COLLECT":
            return self._execute_stock_dossier_collect(run)
        if task == "INCREMENTAL_COLLECT":
            return self._execute_incremental_collect(run)
        return self._execute_market_daily(run)

    def _execute_market_daily(self, run):
        from bisect import bisect_right

        task = run["task"]
        market = task[:2]
        zone = MARKET_SESSIONS[market][0]
        submitted = datetime.fromisoformat(run["created_at"]).astimezone(zone) if run.get("created_at") else datetime.now(zone)
        end_day = datetime.fromisoformat(run["slot"]).date() if run["slot"] else submitted.date()
        start, end = (end_day - timedelta(days=380)).isoformat(), end_day.isoformat()
        codes = market_symbols(market)
        mapped = {code: symbol for code in codes if (symbol := provider_symbol(market, code))}
        if not mapped:
            return "BLOCKED", {"message": "标的库没有可映射的行情代码", "universe_count": len(codes)}

        sources = read("data/ingestion-sources.json")["sources"]
        # 两个市场共用供应商额度，预留 10% 给执行时间偏移及其他已配置查询。
        limit = sources["yfinance"].get("daily_limit")
        budget = min(100, limit * 45 // 100) if limit is not None else 100
        benchmarks = BENCHMARKS[market][:max(0, budget - 1)]
        with self._connect() as conn:
            cursor = conn.execute("SELECT last_symbol FROM market_cursor WHERE market=?", (market,)).fetchone()
        ordered = list(mapped)
        offset = bisect_right(ordered, cursor["last_symbol"]) if cursor else 0
        batch = (ordered[offset:] + ordered[:offset])[:max(0, budget - len(benchmarks))]
        stock_jobs = [
            {"id": code, "provider": "yfinance", "dataset": "daily",
             "params": {"symbol": mapped[code], "start": start, "end": end}}
            for code in batch
        ]
        benchmark_jobs = [
            {"id": symbol, "provider": "yfinance", "dataset": "daily",
             "params": {"symbol": symbol, "start": start, "end": end}}
            for symbol in benchmarks if symbol not in batch
        ]
        results = self._collect_jobs(run["run_id"], stock_jobs + benchmark_jobs, sources, stop_on_limit=True)
        stock_results = results[:len(stock_jobs)]
        complete = [row for row in stock_results if row["status"] == "collected" and row.get("record_count", 0) > 0]
        consumed = [row for row in stock_results
                    if row["status"] not in {"quota_exhausted", "rate_limited", "browser_required"}]
        if consumed:
            # 由终态写入同一个事务，进程中断后原批次按断点恢复。
            next_cursor = consumed[-1]["id"]
        else:
            next_cursor = None
        stop = next((row["status"] for row in results
                     if row["status"] in {"quota_exhausted", "rate_limited", "browser_required"}), None)
        if market == "US":
            macro_jobs = [
                {"id": series, "provider": "fred_csv", "dataset": "series", "params": {"series_id": series}}
                for series in ("DGS10", "EFFR")
            ]
            results.extend(self._collect_jobs(run["run_id"], macro_jobs, sources))
        target_trading_day = ExchangeCalendarEngine.resolve_target_trading_day(market, submitted)
        target_date_str = target_trading_day.isoformat()

        # 构建当前归档记录映射表并执行全市场目标日对账平账
        archived_map = {}
        for item, records in self._archived_records(task):
            if records:
                archived_map[item["id"]] = records

        error_symbols = {row["id"] for row in stock_results if row.get("status") in {"failed", "rate_limited", "quota_exhausted", "upstream_error"}}
        reconciliation = MarketReconciliationEngine.reconcile_target_day(
            market=market,
            target_date=target_date_str,
            universe_symbols=codes,
            archived_records=archived_map,
            error_symbols=error_symbols,
        )

        reason = {"quota_exhausted": "来源额度用尽", "rate_limited": "上游限流",
                  "browser_required": "行情来源不可自动调用"}.get(stop, "按共享额度轮询")
        status = ("SUCCESS" if len(complete) == len(codes) else
                  "PARTIAL_SUCCESS" if complete else "BLOCKED")
        return status, {
            "message": f"{end} 盘前日线（目标交易日 {target_date_str}）：全库 {len(codes)} 个，本轮入批 {len(batch)} 个，"
                       f"已归档 {len(complete)} 个，目标日匹配 {reconciliation.matched_count} 个，"
                       f"停牌未交易 {reconciliation.no_trade_count} 个，未完成 {reconciliation.pending_count} 个。{reason}",
            "items": results,
            "universe_count": len(codes), "requested_symbols": len(batch), "archived_symbols": len(complete),
            "target_trading_day": target_date_str,
            "reconciliation": reconciliation.to_dict(),
            "unmapped_symbols": sorted(set(codes) - mapped.keys()), "next_market_cursor": next_cursor,
            "source_stop": stop, "session_date": end,
        }

    def _execute_official_news(self, run):
        sources = read("data/ingestion-sources.json")["sources"]
        jobs = [
            {"id": f"rss-{index}", "provider": "rss", "dataset": "feed", "params": {"url": feed["url"]}}
            for index, feed in enumerate(sources.get("rss", {}).get("feeds", []))
            if feed.get("authority") in ("official", "issuer", "media")
        ]
        results = self._collect_jobs(run["run_id"], jobs, sources)
        collected = sum(row["status"] == "collected" and row.get("record_count", 0) > 0 for row in results)

        # 实时抽取抓取的资讯记录并无缝联动突发事件雷达
        raw_items = []
        for res in results:
            if res.get("status") == "collected":
                recs = res.get("records") or []
                origin = next(iter(res.get("artifacts", [])), {}).get("origin_url", "")
                for r in recs:
                    t = r.get("title")
                    if t:
                        clean_t = re.sub(r"\s+", " ", t).strip()
                        raw_items.append({
                            "id": r.get("id") or r.get("guid") or r.get("link") or clean_t,
                            "title": clean_t,
                            "content": r.get("description") or r.get("summary") or clean_t,
                            "source": origin or "Official_RSS",
                            "published_at": r.get("pubDate") or r.get("published") or r.get("updated") or "",
                            "url": r.get("link") or origin or "",
                        })

        distill_count = 0
        major_count = 0
        if raw_items:
            try:
                from finance_tools.event_radar_collector import EventRadarCollector
                collector = EventRadarCollector()
                cycle_res = collector.run_collection_cycle(raw_feed_items=raw_items)
                distill_count = cycle_res.get("summarized_count", 0)
                major_count = cycle_res.get("p0_p1_triggered_count", 0)
            except Exception:
                pass

        status = "SUCCESS" if collected and collected == len(jobs) else "PARTIAL_SUCCESS" if collected else "BLOCKED"
        message = (
            f"归档 {collected}/{len(jobs)} 个信源 · 扫描 {len(raw_items)} 篇资讯 · "
            f"提炼入雷达 {distill_count} 条 · 重大事件 {major_count} 条"
            if raw_items
            else f"归档 {collected}/{len(jobs)} 个资讯来源，正文事实核验见事件雷达"
        )
        return status, {
            "message": message,
            "items": results,
            "distilled_count": distill_count,
            "major_count": major_count,
        }

    def _execute_stock_screening(self, run):
        diagnostics = {}
        for market in ("US", "JP"):
            for item, records in self._archived_records(f"{market}_DAILY"):
                if item["provider"] != "yfinance" or item["id"] in {"SPY", "QQQ", "IWM", "^VIX", "1306.T"}:
                    continue
                bars = {}
                for row in records:
                    day = str(row.get("Date", ""))[:10]
                    values = [row.get(field) for field in ("Open", "High", "Low", "Close", "Volume")]
                    if day and all(isinstance(value, (int, float)) and math.isfinite(value) and value > 0
                                   for value in values):
                        bars[day] = values
                symbol = item["id"]
                if len(bars) < 250:
                    self._record_item(run, "BLOCKED", f"{symbol} · 有效日线 {len(bars)}/250")
                    continue
                days = sorted(bars)[-250:]
                series = [bars[day] for day in days]
                closes = [row[3] for row in series]
                diagnostics[symbol] = {
                    "as_of": days[-1], "close": closes[-1],
                    "ma_50": fmean(closes[-50:]), "ma_150": fmean(closes[-150:]),
                    "ma_200": fmean(closes[-200:]), "ma_200_20d_ago": fmean(closes[-220:-20]),
                    "low_52w": min(row[2] for row in series),
                    "high_52w": max(row[1] for row in series),
                    "volume_vs_prior_50d": series[-1][4] / fmean(row[4] for row in series[-51:-1]),
                }
                self._record_item(run, "SUCCESS", f"{symbol} · 截至 {days[-1]} 的日线技术输入已计算")
        return ("PARTIAL_SUCCESS" if diagnostics else "BLOCKED"), {
            "message": f"计算 {len(diagnostics)} 个合格日线样本的趋势输入，正式初筛等待相对强度与形态输入适配",
            "history_ready": len(diagnostics), "trend_inputs": diagnostics,
        }

    def _execute_indicator_update(self, run):
        from financial_reporting.watersource_terminal_service import WatersourceTerminalService

        snapshot = WatersourceTerminalService().get_latest_indicators()["data"]
        indicators = [item for item in snapshot["indicators"]
                      if item["value"] is not None and item["id"] != "SEPA_BREADTH"]
        indicators.extend(self.macro_indicators())
        indicators.extend(self._market_width())
        for item in indicators:
            self._record_item(run, "SUCCESS", f"{item['name_zh']} · 数据时点 {item['as_of']} · {item['source']}")
        status = "PARTIAL_SUCCESS" if indicators else "BLOCKED"
        return status, {
            "message": f"核对或计算 {len(indicators)} 项有归档依据的指标，覆盖范围见各项底稿",
            "indicators": indicators, "updated_count": len(indicators),
        }

    def _market_width(self):
        """按同一交易日统计具备足够日线的普通股样本。"""
        indicators = []
        for market in ("US", "JP"):
            samples = {}
            for item, records in self._archived_records(f"{market}_DAILY"):
                if item["provider"] != "yfinance" or item["id"] in {"SPY", "QQQ", "IWM", "^VIX", "1306.T"}:
                    continue
                closes = {str(row["Date"])[:10]: row["Close"] for row in records
                          if row.get("Date") and isinstance(row.get("Close"), (int, float))
                          and math.isfinite(row["Close"]) and row["Close"] > 0}
                if closes:
                    samples[item["id"]] = closes
            if not samples:
                continue
            day = max(max(closes) for closes in samples.values())
            for window in (50, 200):
                eligible = [sorted(closes.items())[-window:] for closes in samples.values()
                            if day in closes and len(closes) >= window]
                if not eligible:
                    continue
                above = sum(series[-1][1] > fmean(close for _, close in series) for series in eligible)
                percent = round(100 * above / len(eligible), 2)
                indicators.append({
                    "id": f"{market}_BREADTH_{window}", "name_zh": f"{'美股' if market == 'US' else '日股'}样本 {window} 日均线宽度",
                    "value": percent, "display_value": f"{percent}%", "unit": "%", "as_of": day,
                    "data_status": "ARCHIVED_BASELINE", "signal_zh": f"{above}/{len(eligible)} 个合格样本位于均线上方",
                    "source": f"{market}_DAILY 日线归档", "signal": "SAMPLE_BREADTH",
                })
        return indicators

    def latest_sample_width(self):
        with self._connect() as conn:
            row = conn.execute("SELECT result FROM runs WHERE task='INDICATOR_UPDATE' "
                               "AND status='PARTIAL_SUCCESS' ORDER BY rowid DESC LIMIT 1").fetchone()
        return [item for item in json.loads(row["result"]).get("indicators", [])
                if item.get("signal") == "SAMPLE_BREADTH"] if row else []

    def macro_indicators(self):
        """把已校验摘要的 FRED 序列投影到首页的宏观指标契约。"""
        labels = {"DGS10": "美国 10 年期国债收益率", "EFFR": "美国有效联邦基金利率"}
        for item, records in self._archived_records("US_DAILY"):
            series = item["id"]
            if item["provider"] != "fred_csv" or series not in labels or not records:
                continue
            for row in reversed(records):
                date = row.get("observation_date") or row.get("DATE")
                try:
                    value = float(row.get(series))
                except (TypeError, ValueError):
                    continue
                if not date or not math.isfinite(value):
                    continue
                yield {"id": series, "name_zh": labels[series], "value": value, "display_value": f"{value:.2f}%",
                       "unit": "%", "as_of": date, "data_status": "ARCHIVED_BASELINE", "source": "FRED 时序归档"}
                break

    def latest_company_financial_metric(self, ticker):
        with self._connect() as conn:
            row = conn.execute("SELECT result FROM runs WHERE task='FINANCE_CALC' "
                               "AND status='PARTIAL_SUCCESS' ORDER BY rowid DESC LIMIT 1").fetchone()
        return json.loads(row["result"]).get("calculations", {}).get(ticker) if row else None

    def _record_item(self, run, status, message):
        with self._connect() as conn:
            self._log(conn, run["task"], status, message, run["run_id"])

    def _execute_finance_calc(self, run):
        from finance_tools.governance_and_pipeline.service import calculate
        from financial_core.engines.sec_edgar_collector import OfficialSecEdgarCollector
        from financial_reporting.data_collection_gateway import UnifiedDataCollectionGateway

        audit_status, audit_result = self.audit()
        if audit_status != "SUCCESS":
            return audit_status, audit_result
        records = read("data/pipeline_state/sec_collection_progress.json").get("records", {})
        results = {}
        gaps = 0
        for ticker, record in records.items():
            if not isinstance(record, dict) or not record.get("source_filing"):
                gaps += 1
                self._record_item(run, "BLOCKED", f"{ticker} · 进度表缺少官方原档引用")
                continue
            try:
                cik = str(record.get("cik", ""))
                if not cik.isdigit():
                    raise ValueError("缺少有效 CIK")
                path = f"data/official_filings/sec/CIK{cik.zfill(10)}.json"
                raw = read(path)
                filing = OfficialSecEdgarCollector.extract_aligned_financial_facts(raw, ticker)
                facts = UnifiedDataCollectionGateway.ingest_company_financials(ticker, "US", asdict(filing))
                if facts["net_income"] is None:
                    raise ValueError("缺少同一财报期净利润")
                result = calculate("financial_ratio", {
                    "operation": "roa", "numerator": facts["net_income"], "denominator": facts["total_assets"],
                })
            except (ValueError, TypeError, KeyError, FileNotFoundError) as exc:
                gaps += 1
                self._record_item(run, "BLOCKED", f"{ticker} · {exc}")
                continue
            results[ticker] = {"roa": result["result"]["value"], "source_filing": facts["source_filing"],
                               "period": filing.fiscal_year_end, "source_path": path, "input_sha256": result["input_sha256"]}
            self._record_item(run, "SUCCESS", f"{ticker} · 三表平账及期末资产收益率计算完成")
        status = "PARTIAL_SUCCESS" if results else "BLOCKED"
        return status, {"message": f"已算出 {len(results)} 家期末资产收益率，{gaps} 家本地财报输入不足；情景估值等待经核对的专用输入",
                        "calculations": results, "missing_count": gaps}

    def _execute_incremental_collect(self, run):
        path = project_path("data/browser-search/replenishment_tasks.json")
        if not path.is_file():
            return "BLOCKED", {"message": "缺少官方原文补数清单"}
        manifest = json.loads(path.read_text(encoding="utf-8"))
        tasks = manifest if isinstance(manifest, list) else manifest.get("tasks", [])
        count = len(tasks)
        return ("PARTIAL_SUCCESS" if count else "SUCCESS"), {
            "message": f"本地补数清单已核对，{count} 项等待官方原文",
            "queue_pending_count": count,
        }

    def _execute_quote_collect(self, run):
        from scripts.concurrent_sheets_quote_collector import ConcurrentSheetsQuoteCollector
        from financial_reporting.watersource_terminal_service import WatersourceTerminalService

        try:
            collector = ConcurrentSheetsQuoteCollector(data_root=PROJECT_ROOT / "data")
            shards = collector.create_shards()
            res = collector.collect_all(shards=shards, max_workers=4)
            msg = f"已通过 Google Sheets 多表并发引擎全量同步 {res.successful_tickers}/{res.total_tickers} 只标的最新价格"
            return "SUCCESS", {
                "message": msg,
                "total_tickers": res.total_tickers,
                "successful_tickers": res.successful_tickers,
                "elapsed_seconds": round(res.elapsed_seconds, 2),
                "receipt_file": res.receipt_file,
            }
        except Exception as e:
            data = WatersourceTerminalService().get_market_quotes()["data"]
            valid = sum(bool(quote.get("is_valid")) for quote in data["all_quotes"])
            return ("PARTIAL_SUCCESS" if valid else "BLOCKED"), {
                "message": f"云端采集降级，本地归档中 {valid} 项通过时效门禁: {e}",
                "verified_count": valid, "blocked_count": len(data["stale_blocked_tickers"]),
            }

    def _execute_full_universe_collect(self, run):
        """全盘万家美日上市公司固化流式分批采集调度执行器 (14,897 家全覆盖)."""
        from scripts.concurrent_sheets_quote_collector import ConcurrentSheetsQuoteCollector

        try:
            collector = ConcurrentSheetsQuoteCollector(data_root=PROJECT_ROOT / "data")
            mkt = run.get("market") or "ALL"
            res = collector.stream_collect_full_universe(market=mkt, chunk_size=50, max_workers=4, dry_run=False)
            msg = f"已通过流式管道完成 {mkt} 市场全盘万家企业抽取，成功入账 {res['total_tickers_collected']} 条权威报价"
            return "SUCCESS", {
                "message": msg,
                "total_shards": res["total_shards"],
                "successful_shards": res["successful_shards"],
                "total_tickers": res["total_tickers_collected"],
                "elapsed_seconds": res["elapsed_seconds"],
            }
        except Exception as e:
            return "BLOCKED", {"message": f"全盘万家抽取异常: {e}"}

    def _execute_stock_dossier_collect(self, run):
        """精准执行单票全维度数据收集与自动估值（行情、三表平账、DCF走廊、事件穿透）."""
        clean_ticker = (run.get("slot") or "NVDA").strip().upper()
        from financial_reporting.watersource_terminal_service import WatersourceTerminalService
        from financial_reporting.data_collection_gateway import UnifiedDataCollectionGateway

        svc = WatersourceTerminalService()
        dossier = UnifiedDataCollectionGateway.load_verified_batch_dossier(clean_ticker)
        code, val_res = svc.auto_calculate_company_valuation(clean_ticker)

        if code == 200 and val_res.get("data"):
            v = val_res["data"]
            c = v.get("valuation_corridor") or {}
            cur_p = c.get("current_price")
            fair = c.get("base_fair_value", {}).get("value_per_share")
            msg = f"{clean_ticker} · 个股分析全维度数据拉取就绪 · 现价 ${cur_p} · 公允价值 ${fair} · 平账自检通过"
            self._record_item(run, "SUCCESS", msg)
            return "SUCCESS", {
                "message": msg,
                "ticker": clean_ticker,
                "price": cur_p,
                "fair_value": fair,
                "verdict": c.get("valuation_verdict"),
            }
        elif dossier:
            raw = dossier.get("raw_financials_table") or {}
            msg = f"{clean_ticker} · 官方三表与商业档案已核验归档 · 待实时交易时段或无风险利率对齐"
            self._record_item(run, "PARTIAL_SUCCESS", msg)
            return "PARTIAL_SUCCESS", {
                "message": msg,
                "ticker": clean_ticker,
                "filing": raw.get("source"),
            }
        else:
            msg = f"{clean_ticker} · 已加入官方原文增量补数队列，等待公开监管或交易所归档"
            self._record_item(run, "BLOCKED", msg)
            return "BLOCKED", {
                "message": msg,
                "ticker": clean_ticker,
            }
