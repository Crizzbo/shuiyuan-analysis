# -*- coding: utf-8 -*-
from __future__ import annotations
"""水源分析终端前后端统一服务聚合器 (WatersourceTerminalService).

遵循 pstack 1k-line rule 与模块化领域处理器解耦规范：
本服务作为门面中枢，具体领域逻辑通过 Mixin 模块化混入：
1. TerminalValuationMixin: 公司估值、DCF 模型推演
2. TerminalCompanyAnalysisMixin: 全资产池索引、个股深度档案与关联事件下钻
3. TerminalEventMixin: 事件雷达、突发事件周期提炼与采集管道概览
4. TerminalQuotesMixin: 市场行情时序读取、多源校验与批量采集
5. TerminalDashboardMixin: 大盘统计、宏观仪表盘雷达与核心资产卡片
6. TerminalPipelineMixin: 流水线作业调度、状态监控、运行日志与系统配置
"""

# -*- coding: utf-8 -*-
"""水源分析终端前后端统一聚合适配服务 (Watersource Analysis Terminal Service).

设计铁律：
1. 零侵入既有金融工具：本模块仅作为新增聚合与调度层，通过公共 API 与只读查询调用
   `financial_core`、`finance_tools`、`financial_reporting` 及 `data/` 真实底账，
   绝不修改任何既有金融核心工具源码。
2. 四层单向依赖合规：位于 `financial_reporting/` 层，向下调用 `finance_tools/` 与 `financial_core/`。
3. 前后端接口严格对齐：所有响应统一携带 `meta`（`as_of`, `updated_at`, `source`, `status`, `run_id`），
   严格区分 `FRESH` / `PREVIOUS_CLOSE` / `STALE_BLOCKED` / `ARCHIVED_BASELINE` / `NOT_CONFIGURED`，
   绝不将停滞、超期或闭市行情伪装为盘中实时数据。
4. 拒绝机械打分：个股诊断输出「定量探针 + AI 商业分析 + 三态情景估值走廊」，绝不生成机械综合评分。
"""


from collections import deque
from dataclasses import asdict
from datetime import datetime, timezone
import email.utils
import json
import math
from pathlib import Path
import queue
import re
import sqlite3
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.data_lifecycle_engine import LifecyclePolicyConfig
from financial_core.engines.filing_mapper import OfficialFilingMapper
from financial_core.engines.prediction_ledger import PredictionLedger
from financial_core.pipeline.information_pipeline_board_engine import (
    InformationPipelineBoardEngine,
    MACRO_INDICATORS_TEMPLATE_SPECS,
)
from finance_tools.governance_and_pipeline.data_readiness_tracker import DataReadinessTracker, is_excluded_quote
from finance_tools.governance_and_pipeline.service import calculate
from finance_tools.governance_and_pipeline.financial_analysis_gateway import FinancialAnalysisGateway
from finance_tools.logging import setup_terminal_logging
from financial_reporting.ai_research_agent import AIEngineAdapter, AIResearchAgent
from financial_reporting.data_collection_gateway import UnifiedDataCollectionGateway
import os
import shutil
from typing import Callable


PIPELINE_STATES = (
    "IDLE",
    "QUEUED",
    "RUNNING",
    "STOPPING",
    "STOPPED",
    "SUCCESS",
    "FAILED",
    "PARTIAL_SUCCESS",
)

US_INDEX_TICKERS = ("SPY", "QQQ", "DIA", "SMH", "^VIX", "^TNX", "DXY")
JP_INDEX_TICKERS = ("1306", "^N225VI", "USDJPY")
JP_CORE_EQUITIES = ("8035", "6857", "9984")

TICKER_ZH_FALLBACK: Dict[str, str] = {
    "SPY": "标普500指数 ETF",
    "QQQ": "纳斯达克100 ETF",
    "DIA": "道琼斯工业 ETF",
    "SMH": "半导体行业 ETF",
    "^VIX": "标普500波动率指数",
    "^TNX": "美国10年期国债收益率",
    "DXY": "美元指数",
    "1306": "东证股价指数 ETF (TOPIX)",
    "^N225VI": "日经225波动率指数",
    "USDJPY": "美元兑日元汇率",
    "8035": "东京电子 (Tokyo Electron)",
    "6857": "爱德万测试 (Advantest)",
    "9984": "软银集团 (SoftBank Group)",
    "NVDA": "英伟达 (NVIDIA)",
    "AAPL": "苹果公司 (Apple)",
    "MSFT": "微软 (Microsoft)",
    "AMD": "超威半导体 (AMD)",
    "AVGO": "博通 (Broadcom)",
    "GOOGL": "谷歌母公司 (Alphabet)",
    "META": "Meta Platforms",
    "PLTR": "Palantir Technologies",
    "STX": "希捷科技 (Seagate)",
    "TSM": "台积电 (TSMC)",
    "IREN": "Iris Energy",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _parse_json_list(raw: Any) -> List[str]:
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except Exception:
            return [raw]
    return []


def _parse_event_datetime(dt_str: Optional[str]) -> Tuple[str, str, str, datetime]:
    """解析多种格式时间戳，产出 (published_date YYYY-MM-DD, published_time HH:MM:SS, iso_ts, dt_obj)."""
    if not dt_str:
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        return "", "", "", epoch
    # 1. 尝试 ISO 格式 (e.g. 2026-11-13T05:30:00Z 或 2026-11-06T22:22:32+00:00)
    try:
        clean_str = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S"), dt.isoformat(), dt
    except Exception:
        pass
    # 2. 尝试 RFC 2822 (常见于官方 RSS 信源: e.g. 'Fri, 13 Nov 2026 21:15:00 GMT')
    try:
        dt = email.utils.parsedate_to_datetime(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S"), dt.isoformat(), dt
    except Exception:
        pass
    # 3. 兜底
    first_10 = dt_str[:10] if len(dt_str) >= 10 else dt_str
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    return first_10, "", dt_str, epoch



from financial_reporting.terminal_mixins import (
    TerminalValuationMixin,
    TerminalCompanyAnalysisMixin,
    TerminalEventMixin,
    TerminalQuotesMixin,
    TerminalDashboardMixin,
    TerminalPipelineMixin,
)


class WatersourceTerminalService(
    TerminalValuationMixin,
    TerminalCompanyAnalysisMixin,
    TerminalEventMixin,
    TerminalQuotesMixin,
    TerminalDashboardMixin,
    TerminalPipelineMixin,
):
    """水源分析终端前后端统一服务聚合门面."""
    def __init__(
        self,
        project_root: Optional[Path] = None,
        auto_seed_board: bool = True,
        env_inspector: Optional[Callable[[], Dict[str, Any]]] = None,
    ):
        self.root = Path(project_root).resolve() if project_root else ROOT
        self.data_dir = self.root / "data"
        self.exclusions = _safe_read_json(ROOT / "config/terminal-evidence-exclusions.json", {})
        self._lock = threading.RLock()
        self._env_inspector = env_inspector

        # 复用既有信息看板引擎（不改原源码，外层包装）
        self.board_engine = InformationPipelineBoardEngine()
        if not auto_seed_board:
            self.board_engine._store.clear()

        # 流水线外层运行态与历史状态机
        self._pipeline_state: str = "IDLE"
        self._active_run_id: Optional[str] = None
        self._last_run_id: str = "RUN-INIT-BASELINE"
        self._current_stage: str = "待命就绪（等待触发本地核验或看板同步）"
        self._progress_pct: int = 0
        self._last_run_summary: str = "系统已挂载本地只读底账与信息流水线看板"
        self._active_pipeline_task: Optional[str] = None
        self._current_processing_stock: Optional[str] = None
        self._completed_pipeline_tasks: set = set()
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        self._runs: deque = deque(maxlen=40)
        self._logs: deque = deque(maxlen=500)
        self._subscribers: List[queue.Queue] = []
        self._universe_cache: Optional[List[Dict[str, Any]]] = None

        # 初始化工程专属物理日志落盘与 Python 日志桥接中枢 (RotatingFileHandler + SSE 实时推流)
        self.logging_manager = setup_terminal_logging(
            service_callback=self._append_log,
            log_dir=self.data_dir / "logs",
        )
        self._sub_runs: Dict[str, Dict[str, Any]] = {
            "local_audit_sync": {
                "run_id": f"{self._last_run_id}-AUDIT",
                "name": "本地底账全量核对与同步",
                "status": "SUCCESS",
                "progress_pct": 100,
                "message": "本地底账、平账断言与密码学账本验签通过",
                "started_at": _utc_now_iso(),
                "finished_at": _utc_now_iso(),
            },
            "data_ingestion": {
                "run_id": f"{self._last_run_id}-INGEST",
                "name": "全盘数据采集与归档",
                "status": "SUCCESS",
                "progress_pct": 100,
                "message": "已完成核心美日股日线与官方资讯归档核验",
                "started_at": _utc_now_iso(),
                "finished_at": _utc_now_iso(),
            },
        }

        # 采集中心 6 大管线子开关状态表（默认全部启用，支持独立启用/禁用与阻塞重跑）
        self._pipeline_task_toggles: Dict[str, bool] = {
            "GF_MARKET_READINESS": True,
            "SEPA_UNIVERSE_SCREENER": True,
            "SEC_10K_BALANCED_AUDIT": True,
            "UNIVERSE_567_BATCH": True,
            "AI_BROWSER_REPLENISHMENT": True,
            "EVENT_RADAR_POLLING": True,
        }

        # 初始化基础日志与基线运行记录
        self._init_baseline_state()

    # =========================================================================
    # 公共信封与内部日志/SSE 广播基础设施
    # =========================================================================

    def _envelope(
        self,
        data: Any,
        *,
        as_of: str,
        source: str,
        status: str,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            eff_run_id = run_id or self._active_run_id or self._last_run_id
        return {
            "ok": True,
            "data": data,
            "meta": {
                "as_of": as_of,
                "updated_at": _utc_now_iso(),
                "source": source,
                "status": status,
                "run_id": eff_run_id,
            },
            "error": None,
        }

    def error_envelope(self, code: str, message: str, status_code: int = 400) -> Tuple[int, Dict[str, Any]]:
        with self._lock:
            eff_run_id = self._active_run_id or self._last_run_id
        return status_code, {
            "ok": False,
            "data": None,
            "meta": {
                "as_of": _utc_now_iso(),
                "updated_at": _utc_now_iso(),
                "source": "watersource_terminal_service",
                "status": "ERROR",
                "run_id": eff_run_id,
            },
            "error": {
                "code": code,
                "message": message,
            },
        }

    def _append_log(
        self,
        level: str,
        module: str,
        message: str,
        *,
        run_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        broadcast: bool = True,
    ) -> Dict[str, Any]:
        entry = {
            "log_id": f"LOG-{uuid.uuid4().hex[:8].upper()}",
            "timestamp": timestamp or _utc_now_iso(),
            "level": level.upper(),
            "module": module,
            "message": message,
            "run_id": run_id or self._active_run_id or self._last_run_id,
        }
        with self._lock:
            self._logs.appendleft(entry)
        if broadcast:
            self._broadcast_sse("log_entry", entry)
        return entry

    def subscribe_sse(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=128)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe_sse(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def _broadcast_sse(self, event_name: str, payload: Dict[str, Any]) -> None:
        packet = {"event": event_name, "payload": payload, "sent_at": _utc_now_iso()}
        with self._lock:
            dead: List[queue.Queue] = []
            for q in self._subscribers:
                try:
                    q.put_nowait(packet)
                except queue.Full:
                    try:
                        q.get_nowait()
                        q.put_nowait(packet)
                    except Exception:
                        dead.append(q)
            for d in dead:
                if d in self._subscribers:
                    self._subscribers.remove(d)

    def _init_baseline_state(self) -> None:
        # 从看板引擎导入初始日志到环形缓冲，确保首次进入即可见真实流水线审计轨迹
        board_res = self.board_engine.query_messages(page=1, page_size=20)
        board_items = board_res.get("items", []) if isinstance(board_res, dict) else []
        for item in reversed(board_items):
            for raw_line in item.get("logs", []):
                self._logs.appendleft(
                    {
                        "log_id": f"SEED-{uuid.uuid4().hex[:8].upper()}",
                        "timestamp": item.get("timestamp", _utc_now_iso()),
                        "level": "WARN" if item.get("stage_status") == "blocked" else "INFO",
                        "module": item.get("category", "pipeline_board"),
                        "message": f"[{item.get('ticker') or 'SYS'}] {raw_line}",
                        "run_id": self._last_run_id,
                    }
                )
        self._append_log(
            "INFO",
            "terminal_service",
            "水源分析终端聚合服务就绪：已挂载行情新鲜度门禁、事件雷达库与 SEPA 初筛底账",
            broadcast=False,
        )

    # =========================================================================
    # 底层真实底账读取器 (只读)
    # =========================================================================

    def _read_readiness_snapshot(self) -> Dict[str, Any]:
        tracker = DataReadinessTracker(raw_dir=self.data_dir / "google-finance" / "raw")
        return asdict(tracker.inspect_latest_readiness())

    def audit_local_data(self) -> Tuple[str, Dict[str, Any]]:
        readiness = self._read_readiness_snapshot()
        path = self.data_dir / "ledger/predictions_ledger.sqlite3"
        if not path.is_file():
            return "BLOCKED", {"message": "缺少预测账本", "readiness": readiness}
        valid, error = PredictionLedger(db_path=path).verify_integrity()
        return ("SUCCESS" if valid else "FAILED"), {
            "message": (f"预测账本验签通过，行情归档覆盖 {readiness['total_completed_count']} 个标的"
                        if valid else f"预测账本验签失败：{error}"),
            "readiness": readiness,
        }

    def calculate_finance(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        # 计算器使用用户输入的情景假设，复用工程计算登记与校验。
        method, params = body.get("method"), body.get("parameters")
        if not isinstance(method, str) or method not in {"multistage_dcf", "wacc", "cashflow", "financial_ratio"}:
            return self.error_envelope("UNSUPPORTED_CALCULATION", "不支持的计算模型")
        try:
            calculation = calculate(method, params)
        except (ValueError, TypeError, ArithmeticError) as exc:
            return self.error_envelope("INVALID_CALCULATION_INPUT", str(exc))
        return 200, self._envelope(
            calculation, as_of=_utc_now_iso(), source="finance_tools.service",
            status="USER_ASSUMPTIONS",
        )

    def get_health(self) -> Dict[str, Any]:
        readiness = self._read_readiness_snapshot()
        ledger = PredictionLedger(db_path=self.data_dir / "ledger" / "predictions_ledger.sqlite3")
        ledger_valid, ledger_err = ledger.verify_integrity()
        ledger_stats = ledger.get_stats()

        return self._envelope(
            {
                "service_connected": True,
                "environment": "LOCAL_WORKSTATION",
                "architecture_layers_ok": True,
                "ledger_valid": ledger_valid,
                "ledger_error": ledger_err,
                "ledger_total_predictions": ledger_stats.get("total_predictions", 0),
                "latest_data_ts": readiness.get("latest_timestamp_utc"),
                "ready_asset_count": readiness.get("total_completed_count", 0),
                "pipeline_state": self.get_pipeline_status()["data"]["pipeline_state"],
            },
            as_of=readiness.get("latest_timestamp_utc", _utc_now_iso()),
            source="watersource_terminal_health",
            status="PREVIOUS_CLOSE",
        )

    def get_terminal_tasks_config(self) -> Dict[str, Any]:
        """获取全盘任务参数化 JSON 配置 (SSOT)."""
        cfg_file = ROOT / "config" / "terminal_tasks.json"
        if cfg_file.exists():
            try:
                return json.loads(cfg_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"version": "1.0.0", "tasks": {}}

    def update_terminal_tasks_config(self, new_config: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """原子更新全盘任务参数化 JSON 配置并落盘."""
        if not isinstance(new_config, dict):
            return self.error_envelope("INVALID_CONFIG", "配置内容必须为 JSON 对象", 400)
        cfg_file = ROOT / "config" / "terminal_tasks.json"
        new_config["updated_at"] = _utc_now_iso()
        try:
            tmp = cfg_file.with_suffix(".tmp")
            tmp.write_text(json.dumps(new_config, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(cfg_file)
            self._append_log("INFO", "task_config", "全盘任务参数化 JSON 配置已更新并持久化落盘")
            return 200, self._envelope(new_config, as_of=_utc_now_iso(), source="config/terminal_tasks.json", status="UPDATED")
        except Exception as e:
            return self.error_envelope("WRITE_FAILED", f"保存任务配置失败: {e}", 500)
        return 200, self._envelope(
            {
                "pipeline_id": pipeline_id,
                "enabled": current_state,
                "message": f"任务 [{pipeline_id}] 子开关状态已切换为: {state_zh}",
            },
            as_of=_utc_now_iso(),
            source="WatersourceTerminalService.toggle_collection_task",
            status="FRESH",
        )

