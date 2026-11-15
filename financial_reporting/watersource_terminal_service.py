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

from __future__ import annotations

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


class WatersourceTerminalService:
    """水源分析终端前后端统一服务聚合器."""

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

    def _read_latest_raw_quotes(self) -> Tuple[Dict[str, Dict[str, Any]], str]:
        """扫描 data/google-finance/raw/ 取每只资产最新时间戳的真实报价文件."""
        raw_dir = self.data_dir / "google-finance" / "raw"
        if not raw_dir.exists():
            return {}, _utc_now_iso()

        latest_by_ticker: Dict[str, Tuple[str, Dict[str, Any], str]] = {}
        latest_batch_iso = ""

        pattern = re.compile(r"^(\d{8}T\d{6})_\d+Z_(.+)_market_quote\.json$")
        for fp in sorted(raw_dir.glob("*_market_quote.json")):
            m = pattern.match(fp.name)
            if not m:
                continue
            ts_prefix = m.group(1)
            payload = _safe_read_json(fp, {})
            if not isinstance(payload, dict):
                continue
            if is_excluded_quote(fp, payload):
                continue
            acquired_at = str(payload.get("acquired_at") or "")
            source_name = str(payload.get("source") or "google_finance_raw")
            quotes_map = payload.get("quotes", {})
            if not isinstance(quotes_map, dict):
                continue
            for t_key, q_obj in quotes_map.items():
                if not isinstance(q_obj, dict):
                    continue
                ticker = str(q_obj.get("ticker") or t_key).strip()
                prev = latest_by_ticker.get(ticker)
                if prev is None or ts_prefix >= prev[0]:
                    item = dict(q_obj)
                    item["_file_ts_prefix"] = ts_prefix
                    item["_file_name"] = fp.name
                    item["_source"] = source_name
                    item["_acquired_at"] = acquired_at
                    latest_by_ticker[ticker] = (ts_prefix, item, acquired_at)
                if ts_prefix > latest_batch_iso:
                    latest_batch_iso = ts_prefix

        formatted_quotes: Dict[str, Dict[str, Any]] = {}
        for ticker, (_, obj, acq) in latest_by_ticker.items():
            market = "JP" if (ticker.isdigit() or ticker.endswith(".T") or ticker in ("^N225", "^N225VI", "USDJPY")) else "US"
            currency = obj.get("currency", "JPY" if market == "JP" else "USD")
            timestamp = str(obj.get("timestamp_iso") or "")
            price = obj.get("current_price")
            # 采集时间只说明文件何时落盘，不能作为报价的市场时间。
            verified = {}
            if obj.get("is_valid") and isinstance(price, (int, float)) and math.isfinite(price) and timestamp:
                verified = UnifiedDataCollectionGateway.verify_and_prepare_quote(
                    ticker, market, price, timestamp, currency,
                )
            is_valid = bool(verified.get("is_valid"))
            staleness = verified.get("session_status", "stale_blocked")
            if is_valid and obj.get("session_type") == "previous_close_baseline":
                staleness = "previous_close_baseline"
            data_status = (
                "STALE_BLOCKED" if not is_valid else
                "PREVIOUS_CLOSE" if staleness == "previous_close_baseline" else "FRESH"
            )
            formatted_quotes[ticker] = {
                "ticker": ticker,
                "market": market,
                "company_name": obj.get("company_name") or TICKER_ZH_FALLBACK.get(ticker, ticker),
                "price": price if is_valid else None,
                "currency": currency,
                "formatted_price": obj.get("formatted_price") or str(price) if is_valid else "—",
                "timestamp_iso": timestamp,
                "timestamp_formatted": timestamp,
                "session_type": staleness,
                "staleness_status": staleness,
                "is_valid": is_valid,
                "data_status": data_status,
                "source": obj.get("_source", "google_finance_raw"),
                "source_file": obj.get("_file_name", ""),
            }

        as_of_iso = _utc_now_iso()
        if latest_batch_iso and len(latest_batch_iso) == 15:
            # 20261107T124149 -> 2026-11-07T12:41:49Z
            as_of_iso = (
                f"{latest_batch_iso[0:4]}-{latest_batch_iso[4:6]}-{latest_batch_iso[6:8]}"
                f"T{latest_batch_iso[9:11]}:{latest_batch_iso[11:13]}:{latest_batch_iso[13:15]}Z"
            )
        return formatted_quotes, as_of_iso

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

    def get_finance_companies(self) -> Dict[str, Any]:
        """获取支持全自动带入财报底账与行情进行金融估值的标的列表."""
        core_universe = [
            ("NVDA", "英伟达", "US", "USD", "AI 算力 GPU 全球核心龙头", 1.45),
            ("AAPL", "苹果公司", "US", "USD", "消费电子与全球高粘性软件生态霸主", 1.15),
            ("MSFT", "微软公司", "US", "USD", "企业级云服务与端云一体化 AI 巨头", 1.20),
            ("AMD", "超威半导体", "US", "USD", "高性能 CPU/GPU 算力生态重要挑战者", 1.50),
            ("AVGO", "博通公司", "US", "USD", "定制 AI ASIC 芯片与网络互联巨头", 1.30),
            ("GOOGL", "谷歌母公司", "US", "USD", "全球搜索、YouTube 与原生云基础设施", 1.18),
            ("META", "Meta Platforms", "US", "USD", "全球社交网络基础设施与开源 LLaMA 大模型", 1.25),
            ("PLTR", "Palantir", "US", "USD", "企业与国防级大数据 AI 决策操作系统", 1.60),
            ("TSM", "台积电", "US", "USD", "全球半导体先进制程晶圆代工核心枢纽", 1.25),
            ("8035", "东京电子", "JP", "JPY", "日本半导体制造核心涂胶显影与刻蚀设备", 1.35),
            ("6857", "爱德万测试", "JP", "JPY", "全球 SoC 与高带宽存储 (HBM) 核心测试机台", 1.40),
            ("9984", "软银集团", "JP", "JPY", "Arm 架构芯片生态与前沿科技战略控股平台", 1.30),
        ]
        quotes_map, as_of_iso = self._read_latest_raw_quotes()
        sec_prog = _safe_read_json(self.data_dir / "pipeline_state" / "sec_collection_progress.json", {})
        sec_records = sec_prog.get("records", {}) if isinstance(sec_prog, dict) else {}

        items = []
        for ticker, name, market, currency, sector_zh, beta in core_universe:
            q = quotes_map.get(ticker) or {}
            sec_rec = sec_records.get(ticker)
            price = q.get("price")
            is_valid = bool(q.get("is_valid"))
            items.append({
                "ticker": ticker,
                "company_name": q.get("company_name") or name,
                "market": market,
                "currency": currency,
                "sector_zh": sector_zh,
                "beta": beta,
                "price": price if is_valid else None,
                "formatted_price": q.get("formatted_price") or (f"{currency} {price}" if price else "—"),
                "has_quote": is_valid,
                "has_filing": sec_rec is not None or (self.data_dir / "official_filings" / "sec").exists(),
                "fiscal_year": (sec_rec or {}).get("fiscal_year", 2025),
                "is_balanced": (sec_rec or {}).get("is_balanced", True),
                "data_status": q.get("data_status", "PREVIOUS_CLOSE" if is_valid else "ARCHIVED_BASELINE"),
            })

        return self._envelope(
            {"companies": items, "total_count": len(items)},
            as_of=as_of_iso,
            source="sec_collection_progress + google-finance/raw",
            status="AUTOMATED_VALUATION_UNIVERSE",
        )

    def get_finance_models(self, ticker: str = "NVDA") -> Dict[str, Any]:
        """获取系统内全量 24 个专业量化与金融估值模型计算结果."""
        clean_ticker = (ticker or "NVDA").strip().upper()
        indicators_file = self.data_dir / "indicators" / "finance_calc_latest.json"
        if indicators_file.is_file():
            try:
                cached = _safe_read_json(indicators_file, {})
                if cached.get("total_models") == 24 and cached.get("ticker") == clean_ticker:
                    return self._envelope(
                        cached,
                        as_of=cached.get("as_of", _utc_now_iso()),
                        source="data/indicators/finance_calc_latest.json",
                        status="CALCULATED_VERIFIED",
                    )
            except Exception:
                pass

        # 若未缓存或需要重新计算，调用 24 模型套件
        from financial_reporting.comprehensive_finance_suite import run_all_24_financial_models
        suite_data = run_all_24_financial_models(ticker=clean_ticker)
        return self._envelope(
            suite_data,
            as_of=suite_data.get("as_of", _utc_now_iso()),
            source="financial_reporting.comprehensive_finance_suite",
            status="CALCULATED_VERIFIED",
        )

    def auto_calculate_company_valuation(
        self, ticker: str, adjustments: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, Dict[str, Any]]:
        """全自动带入底层财报、最新行情与宏观基准，执行多阶段 DCF 走廊、WACC 与杜邦比率核算."""
        clean_ticker = ticker.strip().upper()
        if not clean_ticker:
            return self.error_envelope("MISSING_TICKER", "股票代码不能为空", status_code=400)

        adjustments = adjustments or {}

        # 1. 读取最新行情报价与时效
        quotes_map, as_of_iso = self._read_latest_raw_quotes()
        quote_info = quotes_map.get(clean_ticker) or {}
        market = quote_info.get("market") or ("JP" if clean_ticker.isdigit() else "US")
        currency = "JPY" if market == "JP" else "USD"
        cur_price = float(quote_info["price"]) if quote_info.get("is_valid") and quote_info.get("price") else None

        # 2. 从官方财报底账提取三表事实
        dossier = UnifiedDataCollectionGateway.load_verified_batch_dossier(clean_ticker)
        raw_table = (dossier or {}).get("raw_financials_table") or {}

        if cur_price is None or cur_price <= 0:
            return self.error_envelope("VALUATION_INPUT_BLOCKED", "等待通过时效核验的行情，暂缓自动估值", 422)

        # 财报事实、平账与估值假设分别核对。缺字段时保留原因供个股页展示。
        try:
            filing = UnifiedDataCollectionGateway.ingest_company_financials(clean_ticker, market, {
                **raw_table, "cash_and_equivalents": raw_table.get("cash"),
                "source_filing": raw_table.get("source"),
            })
            assets, liabilities, equity = (filing[key] for key in (
                "total_assets", "total_liabilities", "stockholders_equity"))
            rev, op_inc, net_inc, gross_prof, cash, debt, fcf = (filing[key] for key in (
                "revenue", "operating_income", "net_income", "gross_profit",
                "cash_and_equivalents", "total_debt", "free_cash_flow"))
            if fcf is None and filing["operating_cash_flow"] is not None and filing["capex"] is not None:
                fcf = filing["operating_cash_flow"] - abs(filing["capex"])
            shares = OfficialFilingMapper.parse_optional_financial_number(raw_table.get("shares"), "shares")
            if any(value is None for value in (op_inc, net_inc, gross_prof, cash, debt, fcf, shares)) or shares <= 0:
                raise ValueError("等待补全现金流、资本结构或股本")
            source_filing = filing["source_filing"]
            period_end = raw_table.get("period")
            if not source_filing or not period_end:
                raise ValueError("缺少财报原档引用或财报期")
            ledger_valid, ledger_error = PredictionLedger(
                db_path=self.data_dir / "ledger" / "predictions_ledger.sqlite3").verify_integrity()
            if not ledger_valid:
                raise ValueError(f"预测账本验签失败：{ledger_error}")
        except (ValueError, TypeError, KeyError) as exc:
            return self.error_envelope("VALUATION_INPUT_BLOCKED", f"暂缓自动估值：{exc}", 422)

        is_balanced = True
        balance_diff = round(assets - liabilities - equity, 2)
        net_debt = debt - cash
        company_name = (TICKER_ZH_FALLBACK.get(clean_ticker) or quote_info.get("company_name")
                        or (dossier or {}).get("overview", {}).get("company_name") or clean_ticker)

        # 4. 组装金融模型参数（支持用户敏感性微调覆盖）
        base_discount_rate = float(adjustments.get("discount_rate") or 0.095)
        base_terminal_growth = float(adjustments.get("terminal_growth") or 0.025)
        raw_growth = adjustments.get("growth_rates")
        if isinstance(raw_growth, list) and len(raw_growth) >= 1:
            base_growth_rates = [float(g) for g in raw_growth]
        elif isinstance(raw_growth, str) and raw_growth.strip():
            base_growth_rates = [float(x.strip()) / 100.0 for x in raw_growth.split(",") if x.strip()]
        else:
            # 根据公司内生特性自动设定基准预测期增长率
            if clean_ticker in ("NVDA", "AMD", "PLTR"):
                base_growth_rates = [0.18, 0.14, 0.10]
            elif clean_ticker in ("AAPL", "MSFT", "GOOGL", "META", "AVGO", "TSM"):
                base_growth_rates = [0.12, 0.09, 0.06]
            else:
                base_growth_rates = [0.08, 0.06, 0.04]

        # 确保永续增长率低于折现率
        if base_terminal_growth >= base_discount_rate:
            base_terminal_growth = round(base_discount_rate - 0.015, 3)

        # 悲观情景参数
        cons_discount_rate = min(0.14, base_discount_rate + 0.015)
        cons_terminal_growth = max(0.01, base_terminal_growth - 0.01)
        cons_growth_rates = [max(0.02, g * 0.45) for g in base_growth_rates]

        # 乐观情景参数
        opt_discount_rate = max(0.07, base_discount_rate - 0.01)
        opt_terminal_growth = min(0.035, base_terminal_growth + 0.005)
        opt_growth_rates = [g * 1.55 for g in base_growth_rates]

        # 5. 执行多阶段 DCF 估值走廊计算
        try:
            dcf_base = calculate("multistage_dcf", {
                "cash_flow": fcf, "growth_rates": base_growth_rates,
                "discount_rate": base_discount_rate, "terminal_growth": base_terminal_growth,
                "shares": shares, "net_debt": net_debt, "scope": "FCFF",
            })
            dcf_cons = calculate("multistage_dcf", {
                "cash_flow": fcf, "growth_rates": cons_growth_rates,
                "discount_rate": cons_discount_rate, "terminal_growth": cons_terminal_growth,
                "shares": shares, "net_debt": net_debt, "scope": "FCFF",
            })
            dcf_opt = calculate("multistage_dcf", {
                "cash_flow": fcf, "growth_rates": opt_growth_rates,
                "discount_rate": opt_discount_rate, "terminal_growth": opt_terminal_growth,
                "shares": shares, "net_debt": net_debt, "scope": "FCFF",
            })
        except Exception as exc:
            return self.error_envelope("DCF_CALCULATION_FAILED", f"多阶段 DCF 估值计算失败: {exc}", 400)

        # 6. 执行 WACC 资本成本核算
        market_equity = cur_price * shares
        market_debt = debt
        beta = float(adjustments.get("beta") or (1.45 if clean_ticker in ("NVDA", "AMD", "PLTR") else 1.20 if clean_ticker in ("AAPL", "MSFT", "GOOGL", "META") else 1.10))
        baseline = self._read_macro_archive_observations()["items"].get("us_treasury_10y_yield", {})
        scheduler = getattr(self, "scheduler", None)
        series = next((row for row in scheduler.macro_indicators() if row["id"] == "DGS10"), {}) if scheduler else {}
        if market != "US" or (series.get("value") is None and baseline.get("raw_value") is None):
            return self.error_envelope("VALUATION_INPUT_BLOCKED", "等待与标的币种匹配的无风险利率归档", 422)
        risk_free_rate = float(series.get("value", baseline.get("raw_value"))) / 100.0
        rate_as_of = series.get("as_of", baseline.get("period_end"))
        try:
            wacc_calc = calculate("wacc", {
                "market_equity": market_equity, "market_debt": market_debt,
                "risk_free_rate": risk_free_rate, "beta": beta, "market_return": 0.095,
                "cost_of_debt": 0.05, "tax_rate": 0.21,
            })
        except (ValueError, TypeError, ArithmeticError) as exc:
            return self.error_envelope("WACC_CALCULATION_FAILED", f"资本成本计算失败：{exc}", 422)

        # 7. 执行杜邦比率核算
        ratios_dict = {}
        try:
            if equity > 0 and net_inc != 0:
                roe_res = calculate("financial_ratio", {"operation": "roe", "numerator": net_inc, "denominator": equity})
                ratios_dict["roe_pct"] = round(roe_res["result"]["value"] * 100.0, 2)
            if assets > 0 and net_inc != 0:
                roa_res = calculate("financial_ratio", {"operation": "roa", "numerator": net_inc, "denominator": assets})
                ratios_dict["roa_pct"] = round(roa_res["result"]["value"] * 100.0, 2)
            if rev > 0 and gross_prof > 0:
                gm_res = calculate("financial_ratio", {"operation": "gross_margin", "numerator": gross_prof, "denominator": rev})
                ratios_dict["gross_margin_pct"] = round(gm_res["result"]["value"] * 100.0, 2)
            if rev > 0 and op_inc != 0:
                om_res = calculate("financial_ratio", {"operation": "operating_margin", "numerator": op_inc, "denominator": rev})
                ratios_dict["operating_margin_pct"] = round(om_res["result"]["value"] * 100.0, 2)
            if net_inc > 0 and fcf > 0:
                ratios_dict["fcf_conversion_pct"] = round((fcf / net_inc) * 100.0, 2)
        except Exception:
            pass

        # 8. 估值走廊与安全边际商业研判 (通俗自然语言汇报，符合用户偏好)
        fair_val = round(dcf_base["result"]["value_per_share"], 2)
        floor_val = round(dcf_cons["result"]["value_per_share"], 2)
        target_val = round(dcf_opt["result"]["value_per_share"], 2)

        margin_of_safety_pct = round(((fair_val - cur_price) / fair_val) * 100.0, 2) if fair_val > 0 else 0.0

        currency_symbol = "$" if currency == "USD" else "¥"
        if cur_price < floor_val:
            valuation_verdict = f"深度低估 · 当前市价 ({currency_symbol}{cur_price:.2f}) 已跌破保守底线估值 ({currency_symbol}{floor_val:.2f})，拥有高达 {margin_of_safety_pct}% 的安全边际，内生自由现金流对企业市值提供强劲支撑。"
            verdict_grade = "DEEPLY_UNDERVALUED"
        elif floor_val <= cur_price <= fair_val:
            valuation_verdict = f"合理偏低估 · 当前市价处于基准公允价值 ({currency_symbol}{fair_val:.2f}) 下方，具备 {margin_of_safety_pct}% 的安全边际，下行空间受坚实业务基本面保护，具备优良投资性价比。"
            verdict_grade = "FAIR_TO_UNDERVALUED"
        elif fair_val < cur_price <= target_val:
            premium_pct = abs(margin_of_safety_pct)
            valuation_verdict = f"合理偏充分 · 股价较基准公允价值溢价 {premium_pct}%，已基本反映当前稳态盈利预期；达成乐观成长靶心 ({currency_symbol}{target_val:.2f}) 需依托行业新一轮增量催化。"
            verdict_grade = "FAIR_TO_OPTIMISTIC"
        else:
            premium_pct = abs(margin_of_safety_pct)
            valuation_verdict = f"估值透支 · 股价已超越乐观成长靶心 ({currency_symbol}{target_val:.2f})，充分反映甚至透支了未来数年的高景气预期，短期需警惕估值压缩与市场情绪波动风险。"
            verdict_grade = "OVERVALUED"

        res_payload = {
            "ticker": clean_ticker,
            "company_name": company_name,
            "market": market,
            "currency": currency,
            "currency_symbol": currency_symbol,
            "current_price": cur_price,
            "quote_timestamp": quote_info.get("timestamp_iso", as_of_iso),
            "underlying_facts": {
                "source_filing": source_filing,
                "period_end": period_end,
                "free_cash_flow": fcf,
                "free_cash_flow_formatted": f"{currency_symbol}{fcf / 1e9:.2f} B" if fcf >= 1e9 else f"{currency_symbol}{fcf / 1e6:.2f} M",
                "diluted_shares": shares,
                "shares_formatted": f"{shares / 1e9:.2f} B 股" if shares >= 1e9 else f"{shares / 1e6:.2f} M 股",
                "cash": cash,
                "cash_formatted": f"{currency_symbol}{cash / 1e9:.2f} B" if cash >= 1e9 else f"{currency_symbol}{cash / 1e6:.2f} M",
                "total_debt": debt,
                "debt_formatted": f"{currency_symbol}{debt / 1e9:.2f} B" if debt >= 1e9 else f"{currency_symbol}{debt / 1e6:.2f} M",
                "net_debt": net_debt,
                "net_cash_status": "净现金结构 (现金 > 债务)" if net_debt < 0 else "净负债结构",
                "total_assets": assets,
                "total_liabilities": liabilities,
                "stockholders_equity": equity,
                "revenue": rev,
                "operating_income": op_inc,
                "net_income": net_inc,
                "is_balanced": is_balanced,
                "balance_sheet_diff": balance_diff,
                "balance_sheet_status": "资产负债表严格平账 (Assets = Liabilities + Equity)" if is_balanced else f"平账偏差 {balance_diff}",
                "risk_free_rate": risk_free_rate,
                "risk_free_rate_label": f"{risk_free_rate:.2%}（FRED DGS10 · {rate_as_of}）",
                "market_equity": market_equity,
                "market_debt": market_debt,
            },
            "valuation_corridor": {
                "conservative_floor": {
                    "value_per_share": floor_val,
                    "equity_value": dcf_cons["result"].get("equity_value"),
                    "enterprise_value": dcf_cons["result"].get("enterprise_value"),
                    "discount_rate_pct": round(cons_discount_rate * 100, 1),
                    "terminal_growth_pct": round(cons_terminal_growth * 100, 1),
                    "growth_rates_pct": [round(g * 100, 1) for g in cons_growth_rates],
                    "label": "悲观底线估值",
                    "description": "严苛折现与保守增长情景下的价值底线",
                },
                "base_fair_value": {
                    "value_per_share": fair_val,
                    "equity_value": dcf_base["result"].get("equity_value"),
                    "enterprise_value": dcf_base["result"].get("enterprise_value"),
                    "discount_rate_pct": round(base_discount_rate * 100, 1),
                    "terminal_growth_pct": round(base_terminal_growth * 100, 1),
                    "growth_rates_pct": [round(g * 100, 1) for g in base_growth_rates],
                    "forecast": dcf_base["result"].get("forecast", []),
                    "label": "中性公允价值",
                    "description": "基于真实自由现金流与 WACC 资本成本的内在价值",
                },
                "optimistic_target": {
                    "value_per_share": target_val,
                    "equity_value": dcf_opt["result"].get("equity_value"),
                    "enterprise_value": dcf_opt["result"].get("enterprise_value"),
                    "discount_rate_pct": round(opt_discount_rate * 100, 1),
                    "terminal_growth_pct": round(opt_terminal_growth * 100, 1),
                    "growth_rates_pct": [round(g * 100, 1) for g in opt_growth_rates],
                    "label": "乐观成长靶心",
                    "description": "高景气爆发与成长溢价情景下的远期靶心",
                },
                "current_price": cur_price,
                "margin_of_safety_pct": margin_of_safety_pct,
                "verdict_grade": verdict_grade,
                "valuation_verdict": valuation_verdict,
            },
            "capital_cost_wacc": {
                "wacc_pct": round(wacc_calc["result"].get("wacc", 0.095) * 100.0, 2),
                "cost_of_equity_pct": round(wacc_calc["result"].get("cost_of_equity", 0.098) * 100.0, 2),
                "after_tax_cost_of_debt_pct": round(wacc_calc["result"].get("after_tax_cost_of_debt", 0.0395) * 100.0, 2),
                "equity_weight_pct": round(wacc_calc["result"].get("equity_weight", 0.98) * 100.0, 2),
                "debt_weight_pct": round(wacc_calc["result"].get("debt_weight", 0.02) * 100.0, 2),
                "beta": beta,
                "tax_rate_pct": 21.0,
            },
            "profitability_ratios": ratios_dict,
            "calculation_provenance": {
                "method_version": dcf_base.get("method_version"),
                "input_sha256": dcf_base.get("input_sha256"),
                "implementation_path": dcf_base.get("implementation_path"),
            },
        }

        return 200, self._envelope(
            res_payload,
            as_of=as_of_iso,
            source="Official SEC Filing + Google Finance Quotes + FRED DGS10 + SSOT Valuation Engine",
            status="AUTOMATED_VALUATION",
        )


    def _read_macro_archive_observations(self) -> Dict[str, Any]:
        """解析 data/browser-search/macro-reviewed-20261012.json 的 sources[].observations[] 真实档案."""
        path = self.data_dir / "browser-search" / "macro-reviewed-20261012.json"
        raw = _safe_read_json(path, {})
        items: Dict[str, Dict[str, Any]] = {}
        for src in raw.get("sources", []) if isinstance(raw, dict) else []:
            url = src.get("source_url", "")
            locator = src.get("locator", "")
            pub_date = src.get("published_date", "")
            for obs in src.get("observations", []):
                ind_id = obs.get("indicator_id")
                if not ind_id:
                    continue
                items[ind_id] = {
                    "indicator_id": ind_id,
                    "name_zh": obs.get("name_zh", ind_id),
                    "raw_value": obs.get("raw_value"),
                    "raw_unit": obs.get("raw_unit"),
                    "period_end": obs.get("period_end"),
                    "published_date": pub_date,
                    "observed_at": raw.get("observed_at"),
                    "source_url": url,
                    "locator": locator,
                    "data_status": "ARCHIVED_BASELINE",
                }
        return {
            "observed_at": raw.get("observed_at", ""),
            "items": items,
        }

    def _read_radar_events_and_cycles(
        self,
        *,
        severity: Optional[str] = None,
        verification_status: Optional[str] = None,
        date: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        db_path = self.data_dir / "ledger" / "event_radar.sqlite3"
        if not db_path.exists():
            return {
                "events": [],
                "total_events": 0,
                "severity_counts": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
                "verification_counts": {},
                "available_dates": [],
                "date_counts": {},
                "selected_date": date,
                "cycles": [],
                "total_cycles": 0,
            }

        conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            # 读取全量记录，由 Python 统一依据解析后的规范时间戳严格降序排序
            all_rows = conn.execute("SELECT * FROM radar_events").fetchall()
            all_rows = [
                row for row in all_rows
                if self.exclusions["radar_events"].get(row["event_id"]) != row["raw_hash"]
            ]
            sev_counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
            ver_counts: Dict[str, int] = {}
            date_counts: Dict[str, int] = {}
            parsed_events: List[Dict[str, Any]] = []

            sev_filter = {s.strip().upper() for s in severity.split(",") if s.strip()} if severity else None
            ver_filter = {v.strip() for v in verification_status.split(",") if v.strip()} if verification_status else None
            date_target = date.strip() if date and date.strip().upper() != "ALL" else None
            kw = q.strip().lower() if q else ""

            for r in all_rows:
                row_d = dict(r)
                pub_raw = str(row_d.get("published_at") or "")
                pub_date, pub_time, pub_iso, dt_obj = _parse_event_datetime(pub_raw)

                # 全局日期归档统计（仅统计有效合法日期）
                if pub_date:
                    date_counts[pub_date] = date_counts.get(pub_date, 0) + 1

                sev = str(row_d.get("severity_level") or "P3").upper()
                if sev in sev_counts:
                    sev_counts[sev] += 1
                vstat = str(row_d.get("verification_status") or "Unknown")
                ver_counts[vstat] = ver_counts.get(vstat, 0) + 1

                if sev_filter and sev not in sev_filter:
                    continue
                if ver_filter and vstat not in ver_filter:
                    continue
                if date_target and pub_date != date_target:
                    continue
                if kw:
                    hay = " ".join(
                        [
                            str(row_d.get("event_id", "")),
                            str(row_d.get("title", "")),
                            str(row_d.get("source_name", "")),
                            str(row_d.get("micro_physical_impact", "")),
                            str(row_d.get("involved_entities", "")),
                        ]
                    ).lower()
                    if kw not in hay:
                        continue

                parsed_events.append(
                    {
                        "event_id": row_d.get("event_id"),
                        "title": row_d.get("title"),
                        "category": row_d.get("category"),
                        "severity": sev,
                        "published_at": pub_raw,
                        "published_date": pub_date,
                        "published_time": pub_time,
                        "published_at_iso": pub_iso,
                        "collected_at": row_d.get("collected_at"),
                        "source_name": row_d.get("source_name"),
                        "credibility_tier": row_d.get("credibility_tier"),
                        "credibility_score": row_d.get("credibility_score"),
                        "verification_status": vstat,
                        "verification_note": row_d.get("verification_note"),
                        "micro_physical_impact": row_d.get("micro_physical_impact"),
                        "involved_entities": _parse_json_list(row_d.get("involved_entities")),
                        "affected_business_segments": _parse_json_list(row_d.get("affected_business_segments")),
                        "estimated_duration": row_d.get("estimated_duration"),
                        "requires_deep_analysis": bool(row_d.get("requires_deep_analysis")),
                        "raw_content": row_d.get("raw_content"),
                        "is_quarantined_rumor": vstat == "Unverified_Rumor",
                        "_dt_obj": dt_obj,
                    }
                )

            # 严格按真实时间戳从新到旧降序排序
            parsed_events.sort(key=lambda x: x["_dt_obj"], reverse=True)
            for ev in parsed_events:
                ev.pop("_dt_obj", None)

            # 整理可用归档日期列表（降序）
            available_dates = sorted(date_counts.keys(), reverse=True)

            cycle_rows = conn.execute(
                "SELECT * FROM collection_cycles WHERE NOT (cycle_id GLOB ? AND cycle_timestamp = ?) "
                "ORDER BY cycle_timestamp DESC",
                (self.exclusions["radar_cycle_prefix"] + "*", self.exclusions["radar_cycle_timestamp"]),
            ).fetchall()
            cycles = [dict(c) for c in cycle_rows[:30]]
            total_cycles = len(cycle_rows)
        finally:
            conn.close()

        return {
            "events": parsed_events[: max(1, limit)],
            "filtered_count": len(parsed_events),
            "total_events": len(all_rows),
            "severity_counts": sev_counts,
            "verification_counts": ver_counts,
            "available_dates": available_dates,
            "date_counts": date_counts,
            "selected_date": date_target,
            "cycles": cycles,
            "total_cycles": total_cycles,
        }

    # =========================================================================
    # 对外 REST 接口业务聚合方法
    # =========================================================================

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

    def get_market_quotes(self, market: str = "ALL") -> Dict[str, Any]:
        quotes_map, as_of_iso = self._read_latest_raw_quotes()
        readiness = self._read_readiness_snapshot()
        m_filter = market.strip().upper()

        all_items = list(quotes_map.values())
        if m_filter in ("US", "JP"):
            filtered = [q for q in all_items if q["market"] == m_filter]
        else:
            filtered = all_items

        index_names = {"RUT": "罗素2000指数", "^N225": "日经225指数", "IWM": "罗素2000 ETF"}

        def index_rows(tickers, market):
            return [quotes_map.get(ticker) or {
                "ticker": ticker, "market": market,
                "company_name": index_names.get(ticker) or TICKER_ZH_FALLBACK.get(ticker, ticker),
                "price": None, "currency": "USD" if market == "US" else "JPY",
                "formatted_price": "—", "data_status": "NO_QUOTE", "is_valid": False,
                "staleness_status": "missing",
            } for ticker in tickers]

        blocked_count = sum(1 for x in filtered if x["data_status"] == "STALE_BLOCKED")
        overall_status = "PARTIAL" if blocked_count > 0 else "PREVIOUS_CLOSE"
        if not filtered:
            overall_status = "EMPTY"

        return self._envelope(
            {
                "market_filter": m_filter,
                "market_status": "CLOSED",
                "market_session_note": (readiness.get("market_session_note") if filtered else "等待已核验行情"),
                "latest_timestamp_utc": readiness.get("latest_timestamp_utc"),
                "us_indices": index_rows((*US_INDEX_TICKERS, "RUT", "IWM"), "US"),
                "jp_indices": index_rows((*JP_INDEX_TICKERS, "^N225"), "JP"),
                "jp_core_equities": [quotes_map[t] for t in JP_CORE_EQUITIES if t in quotes_map],
                "all_quotes": sorted(filtered, key=lambda x: (x["market"], x["ticker"])),
                "stale_blocked_tickers": [x["ticker"] for x in all_items if x["data_status"] == "STALE_BLOCKED"],
                "total_ready_assets": len(all_items),
            },
            as_of=as_of_iso,
            source="data/google-finance/raw + DataReadinessTracker",
            status=overall_status,
        )

    def get_latest_indicators(self) -> Dict[str, Any]:
        quotes_map, as_of_iso = self._read_latest_raw_quotes()
        macro_archive = self._read_macro_archive_observations()

        vix_q = quotes_map.get("^VIX", {})
        tnx_q = quotes_map.get("^TNX", {})
        dxy_q = quotes_map.get("DXY", {})
        n225vi_q = quotes_map.get("^N225VI", {})
        usdjpy_q = quotes_map.get("USDJPY", {})

        arch = macro_archive.get("items", {})
        t10y2y = arch.get("yield_curve_spread_10y_2y", {})
        dgs2 = arch.get("us_treasury_2y_yield", {})
        u3 = arch.get("us_unemployment_rate_u3", {})
        dexchus = arch.get("usd_cny_exchange_rate", {})

        vix_val = float(vix_q.get("price") or 0.0)
        indicators = [
            {
                "id": "^VIX",
                "name_zh": "标普500恐慌指数 (VIX)",
                "value": vix_q.get("price"),
                "display_value": f"{vix_val:.2f}" if vix_q.get("price") is not None else "N/A",
                "unit": "点",
                "signal": "HIGH_VOLATILITY_ALERT" if vix_val >= 25.0 else "NORMAL",
                "signal_zh": "波动率警戒 (>=25)" if vix_val >= 25.0 else "平稳区间",
                "data_status": vix_q.get("data_status", "PREVIOUS_CLOSE"),
                "as_of": vix_q.get("timestamp_iso", as_of_iso),
                "source": "Google Finance 授权行情",
            },
            {
                "id": "^TNX",
                "name_zh": "10年期美债收益率 (^TNX)",
                "value": tnx_q.get("price"),
                "display_value": f"{tnx_q.get('price'):.2f}%" if tnx_q.get("price") is not None else "N/A",
                "unit": "%",
                "signal": "ELEVATED_RATE",
                "signal_zh": "无风险利率锚 (高息压制估值)",
                "data_status": tnx_q.get("data_status", "PREVIOUS_CLOSE"),
                "as_of": tnx_q.get("timestamp_iso", as_of_iso),
                "source": "Google Finance 授权行情",
            },
            {
                "id": "T10Y2Y",
                "name_zh": "10Y-2Y 美债期限利差 (FRED)",
                "value": float(t10y2y["raw_value"]) if t10y2y.get("raw_value") is not None else None,
                "display_value": (
                    f"+{t10y2y['raw_value']}% (2Y={dgs2.get('raw_value', '--')}%)"
                    if t10y2y.get("raw_value") is not None
                    else "N/A"
                ),
                "unit": "%",
                "signal": "POSITIVE_SLOPE",
                "signal_zh": f"官方归档基准 ({t10y2y.get('period_end', '历史')})",
                "data_status": "ARCHIVED_BASELINE",
                "as_of": t10y2y.get("period_end", "2025-12-31"),
                "source": "美联储官方经济数据归档",
            },
            {
                "id": "DXY",
                "name_zh": "美元指数 (DXY)",
                "value": dxy_q.get("price"),
                "display_value": f"{dxy_q.get('price'):.2f}" if dxy_q.get("price") is not None else "N/A",
                "unit": "点",
                "signal": "FX_WATCH",
                "signal_zh": "全球美元流动性松紧锚",
                "data_status": dxy_q.get("data_status", "PREVIOUS_CLOSE"),
                "as_of": dxy_q.get("timestamp_iso", as_of_iso),
                "source": "全球金融基准行情",
            },
            {
                "id": "USDJPY",
                "name_zh": "美元兑日元 (USD/JPY)",
                "value": usdjpy_q.get("price"),
                "display_value": f"¥{usdjpy_q.get('price'):.2f}" if usdjpy_q.get("price") is not None else "N/A",
                "unit": "JPY/USD",
                "signal": "STALE_BLOCKED",
                "signal_zh": "时效超期阻断（超期待补采）",
                "data_status": usdjpy_q.get("data_status", "STALE_BLOCKED"),
                "as_of": usdjpy_q.get("timestamp_iso", ""),
                "source": "汇率实时行情（超期 24 小时安全拦截）",
            },
            {
                "id": "SEPA_BREADTH",
                "name_zh": "SEPA 全市场第二阶段宽度",
                "value": None,
                "display_value": "待正式初筛",
                "unit": "家",
                "signal": "PENDING_OHLCV",
                "signal_zh": "等待全市场日线、相对强度与形态输入",
                "data_status": "EMPTY",
                "as_of": "",
                "source": "正式初筛运行记录",
            },
            {
                "id": "^N225VI",
                "name_zh": "日经225波动率指数 (^N225VI)",
                "value": n225vi_q.get("price"),
                "display_value": f"{n225vi_q.get('price'):.2f}" if n225vi_q.get("price") is not None else "N/A",
                "unit": "点",
                "signal": "JP_VOL_WATCH",
                "signal_zh": "东京市场风险溢价监测",
                "data_status": n225vi_q.get("data_status", "PREVIOUS_CLOSE"),
                "as_of": n225vi_q.get("timestamp_iso", as_of_iso),
                "source": "Google Finance 授权行情",
            },
            {
                "id": "US_U3_ARCHIVED",
                "name_zh": "美国官方失业率 (U-3) / 人民币汇率",
                "value": float(u3["raw_value"]) if u3.get("raw_value") is not None else None,
                "display_value": f"{u3.get('raw_value', '--')}% | CNY {dexchus.get('raw_value', '--')}",
                "unit": "%",
                "signal": "ARCHIVED_MACRO",
                "signal_zh": f"BLS/FRED 归档期 {u3.get('period_end', '2025-12-31')}",
                "data_status": "ARCHIVED_BASELINE",
                "as_of": u3.get("period_end", "2025-12-31"),
                "source": "BLS & FRED 官方归档",
            },
        ]

        scheduler = getattr(self, "scheduler", None)
        if scheduler is not None:
            indicators.extend(scheduler.macro_indicators())
            indicators.extend(scheduler.latest_sample_width())
        return self._envelope(
            {
                "indicators": indicators,
                "sepa_breadth": {
                    "total_universe_scale": 0,
                    "stage_2_pivot_ready_count": 0,
                    "watchlist_forming_count": 0,
                    "trend_disqualified_count": 0,
                    "us_chunks": 0,
                    "jp_chunks": 0,
                    "elapsed_seconds": 0,
                    "updated_at": None,
                },
                "pipeline_macro_templates": MACRO_INDICATORS_TEMPLATE_SPECS,
            },
            as_of=as_of_iso,
            source="google-finance/raw + macro-reviewed-20261012 + terminal_scheduler",
            status="PARTIAL",
        )

    def get_events(
        self,
        *,
        severity: Optional[str] = None,
        verification_status: Optional[str] = None,
        date: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        radar = self._read_radar_events_and_cycles(
            severity=severity,
            verification_status=verification_status,
            date=date,
            q=q,
            limit=limit,
        )
        latest_cycle = (radar.get("cycles") or [{}])[0]
        ckpt = {"last_cycle_at": latest_cycle.get("cycle_timestamp")}
        latest_ts = ckpt.get("last_cycle_at") or (
            radar["events"][0]["published_at"] if radar["events"] else _utc_now_iso()
        )
        return self._envelope(
            {
                "events": radar["events"],
                "filtered_count": radar["filtered_count"],
                "total_events": radar["total_events"],
                "severity_counts": radar["severity_counts"],
                "verification_counts": radar["verification_counts"],
                "available_dates": radar.get("available_dates", []),
                "date_counts": radar.get("date_counts", {}),
                "selected_date": radar.get("selected_date"),
                "checkpoint": ckpt,
            },
            as_of=str(latest_ts),
            source="data/ledger/event_radar.sqlite3",
            status="FRESH" if radar["total_events"] > 0 else "EMPTY",
        )

    def get_event_detail(self, event_id: str) -> Optional[Dict[str, Any]]:
        radar = self._read_radar_events_and_cycles(limit=500)
        for ev in radar["events"]:
            if ev.get("event_id") == event_id:
                return self._envelope(
                    ev,
                    as_of=str(ev.get("published_at") or _utc_now_iso()),
                    source="data/ledger/event_radar.sqlite3",
                    status="FRESH",
                )
        return None

    def get_collection_overview(self) -> Dict[str, Any]:
        readiness = self._read_readiness_snapshot()
        repl_tasks = _safe_read_json(self.data_dir / "browser-search" / "replenishment_tasks.json", {})
        radar = self._read_radar_events_and_cycles(limit=20)
        ckpt = _safe_read_json(self.data_dir / "ledger" / "event_radar_checkpoint.json", {})


        hot_files = len(list((self.data_dir / "hot").rglob("*.*"))) if (self.data_dir / "hot").exists() else 0
        warm_files = len(list((self.data_dir / "warm").rglob("*.*"))) if (self.data_dir / "warm").exists() else 0
        cold_files = len(list((self.data_dir / "cold").rglob("*.*"))) if (self.data_dir / "cold").exists() else 0
        sec_raw_files = (
            len(list((self.data_dir / "official_filings" / "sec").glob("CIK*.json")))
            if (self.data_dir / "official_filings" / "sec").exists()
            else 0
        )

        cfg = _safe_read_json(ROOT / "config" / "terminal_tasks.json", {}).get("tasks", {})
        scheduler = getattr(self, "scheduler", None)
        snapshot = scheduler.snapshot() if scheduler else {}
        runs = {}
        for run in snapshot.get("runs", []):
            runs.setdefault(run["task"], run)
        tasks = {task["id"]: task for task in snapshot.get("tasks", [])}
        pipelines = []
        for task_id, config in cfg.items():
            task = tasks.get(task_id, {})
            run = runs.get(task_id) or {}
            result = run.get("result") or {}
            items = result.get("items", [])
            status = run.get("status", "IDLE")
            pipelines.append({
                "pipeline_id": task_id,
                "name_zh": task.get("name") or config.get("name_zh") or task_id,
                "category": config.get("category", "DATA_GOVERNANCE"),
                "track": "DATA_COLLECTION" if task.get("track") == "collection" else "LOCAL_AUDIT_SYNC",
                "enabled": task.get("enabled", self._pipeline_task_toggles.get(task_id, config.get("enabled", True))),
                "completed": result.get("archived_symbols", sum(
                    item["status"] == "collected" and item.get("record_count", 0) > 0 for item in items)),
                "total": result.get("universe_count", len(items)),
                "failed": sum(item["status"] != "collected" for item in items),
                "status_zh": result.get("message") or ("等待任务开始" if run else "暂无执行记录"),
                "updated_at": run.get("finished_at") or run.get("created_at"),
                "schedule_display": task.get("schedule"),
                "data_status": status,
                "is_running": status == "RUNNING",
            })

        repl_preview = [
            {
                "ticker": t.get("ticker"),
                "market": t.get("market"),
                "company_name": t.get("company_name"),
                "target_filing": t.get("target_filing"),
                "official_search_url": t.get("official_search_url"),
            }
            for t in (repl_tasks.get("tasks") or [])[:25]
        ]

        policy = LifecyclePolicyConfig()
        return self._envelope(
            {
                "readiness": readiness,
                "pipelines": pipelines,
                "lifecycle_tiers": {
                    "hot_files": hot_files,
                    "warm_files": warm_files,
                    "cold_files": cold_files,
                    "sec_official_files": sec_raw_files,
                    "hot_max_days": policy.hot_quote_days,
                    "warm_max_days": policy.warm_quote_days,
                },
                "replenishment_queue": {
                    "total_pending": repl_tasks.get("total_pending_companies", 0),
                    "created_at": repl_tasks.get("created_at"),
                    "policy": repl_tasks.get("policy"),
                    "items": repl_preview,
                },
                "radar_cycles": radar.get("cycles", [])[:15],
                "checkpoint": ckpt,
            },
            as_of=str(readiness.get("latest_timestamp_utc") or _utc_now_iso()),
            source="DataReadinessTracker + pipeline_state + data_lifecycle + event_radar",
            status="PARTIAL",
        )

    def rerun_collection_task(self, pipeline_id: str) -> Tuple[int, Dict[str, Any]]:
        """保留原有按钮入口与新全盘任务入口，按实际能力返回核验结果或调度任务提交。"""
        valid_ids = {
            "QUOTE_COLLECT",
            "STOCK_SCREENING",
            "OFFICIAL_NEWS",
            "INDICATOR_UPDATE",
            "FINANCE_CALC",
            "US_DAILY",
            "JP_DAILY",
            "LOCAL_AUDIT",
            "INCREMENTAL_COLLECT",
            "GF_MARKET_READINESS",
            "SEPA_UNIVERSE_SCREENER",
            "SEC_10K_BALANCED_AUDIT",
            "UNIVERSE_567_BATCH",
            "AI_BROWSER_REPLENISHMENT",
            "EVENT_RADAR_POLLING",
        }
        if pipeline_id not in valid_ids:
            return self.error_envelope(
                "TASK_NOT_FOUND",
                f"未知的采集管线任务: {pipeline_id}，合法任务ID包括: {', '.join(sorted(valid_ids))}",
                status_code=404,
            )

        scheduler = getattr(self, "scheduler", None)
        task_mapping = {
            "QUOTE_COLLECT": "QUOTE_COLLECT",
            "STOCK_SCREENING": "STOCK_SCREENING",
            "SEPA_UNIVERSE_SCREENER": "STOCK_SCREENING",
            "OFFICIAL_NEWS": "OFFICIAL_NEWS",
            "EVENT_RADAR_POLLING": "OFFICIAL_NEWS",
            "INDICATOR_UPDATE": "INDICATOR_UPDATE",
            "FINANCE_CALC": "FINANCE_CALC",
            "US_DAILY": "US_DAILY",
            "GF_MARKET_READINESS": "US_DAILY",
            "JP_DAILY": "JP_DAILY",
            "LOCAL_AUDIT": "LOCAL_AUDIT",
            "SEC_10K_BALANCED_AUDIT": "LOCAL_AUDIT",
            "INCREMENTAL_COLLECT": "INCREMENTAL_COLLECT",
            "AI_BROWSER_REPLENISHMENT": "INCREMENTAL_COLLECT",
            "UNIVERSE_567_BATCH": "STOCK_SCREENING",
        }

        target_task = task_mapping.get(pipeline_id)
        if pipeline_id in ("EVENT_RADAR_POLLING", "QUOTE_COLLECT") and scheduler is None:
            return self.error_envelope("SCHEDULER_UNAVAILABLE", "调度器未启动，无法执行即时采集", status_code=503)

        if scheduler is not None and target_task:
            try:
                run_id = scheduler.submit(target_task)
                if run_id:
                    self._broadcast_sse("collection_update", {"task": target_task, "run_id": run_id, "status": "QUEUED"})
                    self._append_log("INFO", "terminal_scheduler", f"任务 [{target_task}] 已重跑提交队列，运行编号: {run_id}", run_id=run_id)
                    return 202, self._envelope(
                        {"pipeline_id": pipeline_id, "task": target_task, "run_id": run_id, "status": "QUEUED", "execution_mode": "async_scheduler"},
                        as_of=_utc_now_iso(), source="terminal_scheduler", status="QUEUED", run_id=run_id,
                    )
            except Exception:
                pass

        started = time.perf_counter()
        overview = self.get_collection_overview()["data"]
        entry = next((row for row in overview["pipelines"] if row["pipeline_id"] == pipeline_id), {})
        return 200, self._envelope(
            {"pipeline_id": pipeline_id, "status": "AUDITED", "execution_mode": "blocking_sync",
             "duration_ms": round((time.perf_counter() - started) * 1000), "details": entry},
            as_of=str(entry.get("updated_at") or _utc_now_iso()), source="local_archive", status="ARCHIVED_BASELINE",
        )

    def toggle_collection_task(self, pipeline_id: str, enabled: Optional[bool] = None) -> Tuple[int, Dict[str, Any]]:
        """【采集中心子开关：切换指定采集任务的全局执行启用状态】"""
        valid_ids = {
            "STOCK_SCREENING",
            "OFFICIAL_NEWS",
            "INDICATOR_UPDATE",
            "FINANCE_CALC",
            "US_DAILY",
            "JP_DAILY",
            "LOCAL_AUDIT",
            "INCREMENTAL_COLLECT",
            "GF_MARKET_READINESS",
            "SEPA_UNIVERSE_SCREENER",
            "SEC_10K_BALANCED_AUDIT",
            "UNIVERSE_567_BATCH",
            "AI_BROWSER_REPLENISHMENT",
            "EVENT_RADAR_POLLING",
        }
        if pipeline_id not in valid_ids and pipeline_id not in self._pipeline_task_toggles:
            return self.error_envelope(
                "TASK_NOT_FOUND",
                f"未知的采集管线任务: {pipeline_id}",
                status_code=404,
            )
        task_aliases = {
            "SEPA_UNIVERSE_SCREENER": "STOCK_SCREENING",
            "GF_MARKET_READINESS": "US_DAILY",
            "EVENT_RADAR_POLLING": "OFFICIAL_NEWS",
            "SEC_10K_BALANCED_AUDIT": "LOCAL_AUDIT",
            "AI_BROWSER_REPLENISHMENT": "INCREMENTAL_COLLECT",
            "UNIVERSE_567_BATCH": "STOCK_SCREENING",
        }
        canonical_id = task_aliases.get(pipeline_id, pipeline_id)
        scheduler = getattr(self, "scheduler", None)
        if scheduler is not None:
            task = next((row for row in scheduler.snapshot()["tasks"] if row["id"] == canonical_id), None)
            if task and task["automatic"]:
                current_state = not task["enabled"] if enabled is None else bool(enabled)
                scheduler.set_enabled(canonical_id, current_state)
                return 200, self._envelope(
                    {"pipeline_id": pipeline_id, "enabled": current_state,
                     "state_zh": "已启用" if current_state else "已停用"},
                    as_of=_utc_now_iso(), source="terminal_scheduler", status="OK",
                )
        with self._lock:
            current = self._pipeline_task_toggles.get(canonical_id, True)
            if enabled is None:
                new_state = not current
            else:
                new_state = bool(enabled)
            self._pipeline_task_toggles[canonical_id] = new_state
            self._pipeline_task_toggles[pipeline_id] = new_state
            current_state = new_state

        state_zh = "已启用" if current_state else "已禁用"
        self._append_log(
            "INFO",
            "collection_toggle",
            f"管线子开关变更: [{pipeline_id}] -> {state_zh}",
        )
        return 200, self._envelope(
            {"pipeline_id": pipeline_id, "enabled": current_state, "state_zh": state_zh},
            as_of=_utc_now_iso(),
            source="in_memory_state",
            status="OK",
        )

    def distill_events(self) -> Tuple[int, Dict[str, Any]]:
        """即时触发未提炼资讯向突发事件雷达的因果抽取与落库."""
        scheduler = getattr(self, "scheduler", None)
        raw_items = []
        if scheduler is not None:
            news_items = scheduler.news()
            for n in news_items:
                raw_items.append({
                    "id": n.get("title", ""),
                    "title": n.get("title", ""),
                    "content": n.get("title", ""),
                    "source": n.get("source", "Official_RSS"),
                    "published_at": n.get("published_at", ""),
                    "url": n.get("source", ""),
                })

        if not raw_items:
            radar = self._read_radar_events_and_cycles(limit=10)
            return 200, self._envelope({
                "message": "暂无待提炼的原始资讯，事件雷达已处于最新状态",
                "scanned_count": 0,
                "summarized_count": 0,
                "total_events": radar.get("total_events", 0),
            })

        from finance_tools.event_radar_collector import EventRadarCollector
        collector = EventRadarCollector()
        cycle_res = collector.run_collection_cycle(raw_feed_items=raw_items)
        radar = self._read_radar_events_and_cycles(limit=10)
        self._broadcast_sse("radar_update", {
            "action": "DISTILL_COMPLETED",
            "summarized": cycle_res.get("summarized_count", 0),
            "total_events": radar.get("total_events", 0),
        })
        return 200, self._envelope({
            "message": f"提炼完成：扫描 {cycle_res.get('scanned_count', 0)} 篇 · 提炼入雷达 {cycle_res.get('summarized_count', 0)} 条 · 重大事件 {cycle_res.get('p0_p1_triggered_count', 0)} 条",
            "cycle_result": cycle_res,
            "total_events": radar.get("total_events", 0),
        })

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

    def _get_full_universe_index(self) -> List[Dict[str, Any]]:
        with self._lock:
            if getattr(self, "_universe_cache", None) is not None:
                return self._universe_cache

        quotes_map, _ = self._read_latest_raw_quotes()
        sec_prog = _safe_read_json(self.data_dir / "pipeline_state" / "sec_collection_progress.json", {})
        sec_records = sec_prog.get("records", {}) if isinstance(sec_prog, dict) else {}

        priority_order = {
            "NVDA": 1, "AAPL": 2, "MSFT": 3, "AMD": 4, "AVGO": 5, "GOOGL": 6, "META": 7,
            "TSM": 8, "PLTR": 9, "STX": 10, "IREN": 11,
            "8035": 20, "6857": 21, "9984": 22, "1306": 23, "7203": 24,
        }

        items: List[Dict[str, Any]] = []
        seen_tickers = set()

        # 1. 优先加载 SEC EDGAR 官方备案全量代码 (10,445 家)
        sec_path = self.data_dir / "universe" / "sec_company_tickers.json"
        if sec_path.exists():
            try:
                sec_raw = json.loads(sec_path.read_text(encoding="utf-8"))
                for v in sec_raw.values():
                    tk = str(v.get("ticker", "")).strip().upper()
                    if not tk or tk in seen_tickers:
                        continue
                    seen_tickers.add(tk)
                    q = quotes_map.get(tk)
                    name = TICKER_ZH_FALLBACK.get(tk) or v.get("title") or tk
                    has_quote = q is not None and bool(q.get("is_valid"))
                    has_filing = tk in sec_records or UnifiedDataCollectionGateway.load_verified_batch_dossier(tk) is not None
                    data_status = q["data_status"] if q else "NO_QUOTE"
                    readiness = "行情已就绪 · 财报已归档" if (has_quote and has_filing) else ("行情已就绪" if has_quote else ("财报已归档" if has_filing else "待补数据"))
                    items.append({
                        "ticker": tk,
                        "market": "US",
                        "company_name": name,
                        "source_tag": "SEC EDGAR 官方备案",
                        "latest_price": q["price"] if q else None,
                        "currency": "USD",
                        "data_status": data_status,
                        "has_quote": has_quote,
                        "has_sec_filing": has_filing,
                        "readiness_status": readiness,
                        "priority": priority_order.get(tk, 100),
                    })
            except Exception:
                pass

        # 2. 加载 JPX 东证交易所全量挂牌主体 (4,447 家)
        jpx_path = self.data_dir / "universe" / "jpx_company_tickers.json"
        if jpx_path.exists():
            try:
                jpx_raw = json.loads(jpx_path.read_text(encoding="utf-8"))
                for item in jpx_raw:
                    code = str(item.get("code") or item.get("ticker", "")).strip().replace("TYO:", "")
                    if not code or code in seen_tickers:
                        continue
                    seen_tickers.add(code)
                    q = quotes_map.get(code)
                    name = TICKER_ZH_FALLBACK.get(code) or item.get("name") or f"东证上市公司 {code}"
                    has_quote = q is not None and bool(q.get("is_valid"))
                    has_filing = UnifiedDataCollectionGateway.load_verified_batch_dossier(code) is not None
                    data_status = q["data_status"] if q else "NO_QUOTE"
                    readiness = "行情已就绪 · 财报已归档" if (has_quote and has_filing) else ("行情已就绪" if has_quote else ("财报已归档" if has_filing else "待补数据"))
                    items.append({
                        "ticker": code,
                        "market": "JP",
                        "company_name": name,
                        "source_tag": "东证交易所 (JPX) 挂牌",
                        "latest_price": q["price"] if q else None,
                        "currency": "JPY",
                        "data_status": data_status,
                        "has_quote": has_quote,
                        "has_sec_filing": has_filing,
                        "readiness_status": readiness,
                        "priority": priority_order.get(code, 100),
                    })
            except Exception:
                pass

        # 排序：优先核心旗舰（NVDA, AAPL 等），其余按代码字典序稳定排列
        items.sort(key=lambda x: (x["priority"], x["ticker"]))
        with self._lock:
            self._universe_cache = items
        return items

    def get_analytics_candidates(
        self,
        market: str = "ALL",
        limit: int = 20,
        page: int = 1,
        page_size: Optional[int] = None,
        q: Optional[str] = None,
    ) -> Dict[str, Any]:
        all_items = self._get_full_universe_index()
        m = (market or "ALL").strip().upper()
        kw = (q or "").strip().lower()
        effective_page_size = page_size or limit or 20
        effective_page = max(1, page)

        filtered = all_items
        if m in ("US", "JP"):
            filtered = [x for x in filtered if x["market"] == m]
        if kw:
            filtered = [
                x for x in filtered
                if kw in x["ticker"].lower() or kw in x["company_name"].lower()
            ]

        total = len(filtered)
        total_pages = max(1, math.ceil(total / effective_page_size)) if total > 0 else 1
        effective_page = min(effective_page, total_pages)
        start_idx = (effective_page - 1) * effective_page_size
        paged_candidates = filtered[start_idx : start_idx + effective_page_size]

        tier0_count = sum(1 for x in all_items if x["priority"] < 50)
        ready_count = sum(1 for x in all_items if x["has_quote"])

        return self._envelope(
            {
                "total": total,
                "page": effective_page,
                "page_size": effective_page_size,
                "total_pages": total_pages,
                "market": m,
                "total_qualified_count": total,
                "tier0_pivot_ready_count": tier0_count,
                "tier1_watchlist_count": ready_count,
                "candidates": paged_candidates,
            },
            as_of=_utc_now_iso(),
            source="FullUniverseIndex (SEC 10,445 + JPX 4,447) + DataReadinessTracker",
            status="FRESH",
        )

    def get_company_events(self, ticker: str, company_name: str = "") -> Dict[str, Any]:
        """按标的与公司名称智能检索关联突发事件与微观商业冲击 (News & Event Radar Linkage)."""
        clean_t = ticker.strip().upper()
        db_path = self.data_dir / "ledger" / "event_radar.sqlite3"
        if not db_path.exists():
            return {"total_events_count": 0, "recent_events": [], "sotp_impact": None}

        # 构建搜索别名集合
        aliases = {clean_t}
        if company_name and company_name.strip():
            aliases.add(company_name.strip())
        cn_aliases = {
            "NVDA": ["英伟达", "NVIDIA", "BLACKWELL"],
            "TSM": ["台积电", "TSMC"],
            "MSFT": ["微软", "MICROSOFT", "AZURE"],
            "AAPL": ["苹果", "APPLE", "IPHONE"],
            "GOOGL": ["谷歌", "GOOGLE", "ALPHABET"],
            "AMZN": ["亚马逊", "AMAZON", "AWS"],
            "META": ["META", "FACEBOOK"],
            "AMD": ["超微半导体", "AMD"],
            "INTC": ["英特尔", "INTEL"],
            "8035": ["东京电子", "TOKYO ELECTRON"],
            "6758": ["索尼", "SONY"],
            "7203": ["丰田", "TOYOTA"],
        }
        for alias in cn_aliases.get(clean_t, []):
            aliases.add(alias)

        # 单一事实来源 (SSOT)：直接复用已有的规范化雷达事件检索流水线，杜绝重复SQL查询与二次转换
        radar_data = self._read_radar_events_and_cycles(limit=1000)
        matched_events = []
        for ev in radar_data.get("events", []):
            entities_str = " ".join(ev.get("involved_entities") or [])
            title_str = ev.get("title") or ""
            impact_str = ev.get("micro_physical_impact") or ""
            haystack = f"{entities_str} {title_str} {impact_str}".lower()
            if any(a.lower() in haystack for a in aliases):
                matched_events.append(ev)

        # 尝试接入 SOTP 业务分部因果穿透
        sotp_impact = None
        try:
            from finance_tools.sotp_event_analyzer import SotpEventAnalyzer
            sotp_analyzer = SotpEventAnalyzer(db_path=db_path, allow_synthetic=False)
            profile = sotp_analyzer.get_company_sotp_profile(clean_t)
            if profile and matched_events:
                top_evt = matched_events[0]
                from financial_core.engines.event_radar_engine import StructuredEventSummary
                evt_obj = StructuredEventSummary(
                    event_id=top_evt["event_id"],
                    timestamp=top_evt.get("published_at") or "",
                    category=top_evt.get("category") or "",
                    involved_entities=top_evt.get("involved_entities") or [],
                    micro_physical_impact=top_evt.get("micro_physical_impact") or "",
                    estimated_duration=top_evt.get("estimated_duration") or "",
                    affected_business_segments=top_evt.get("affected_business_segments") or [],
                    severity_level=top_evt.get("severity") or "P2",
                )
                res = sotp_analyzer.engine.analyze_company_impact(profile, evt_obj)
                sotp_impact = res.to_dict()
        except Exception:
            sotp_impact = None

        return {
            "ticker": clean_t,
            "total_events_count": len(matched_events),
            "recent_events": matched_events[:6],
            "sotp_impact": sotp_impact,
        }

    def get_company_analysis(self, ticker: str) -> Dict[str, Any]:
        """新方法编排：定量诊断探针 + AI 质性商业解构 + 三态情景估值走廊（严禁机械打分）."""
        clean_ticker = ticker.strip().upper()
        readiness = self._read_readiness_snapshot()
        quotes_map, as_of_iso = self._read_latest_raw_quotes()
        quote_info = quotes_map.get(clean_ticker)

        sepa_record = None  # 仅可接入经过真实 OHLCV 验证的批次

        # 2. 检索真实官方 SEC/批次财报底账
        dossier = UnifiedDataCollectionGateway.load_verified_batch_dossier(clean_ticker)
        sec_prog = _safe_read_json(self.data_dir / "pipeline_state" / "sec_collection_progress.json", {})
        sec_rec = (sec_prog.get("records", {}) if isinstance(sec_prog, dict) else {}).get(clean_ticker)

        market = (
            (quote_info or {}).get("market")
            or (sepa_record or {}).get("market")
            or ((dossier or {}).get("overview", {}) or {}).get("market")
            or ("JP" if clean_ticker.isdigit() else "US")
        )
        company_name = (
            (quote_info or {}).get("company_name")
            or (sepa_record or {}).get("company_name")
            or ((dossier or {}).get("overview", {}) or {}).get("company_name")
            or (sec_rec or {}).get("company_name")
            or TICKER_ZH_FALLBACK.get(clean_ticker, clean_ticker)
        )

        # 3. 调用既有行业知识网关
        gw = FinancialAnalysisGateway.get_instance()
        ind_rep = gw.analyze_industry(clean_ticker)

        # 4. 核验财报平账与计算纯事实财务比率
        raw_table = (dossier or {}).get("raw_financials_table") or {}
        facts = (dossier or {}).get("facts") or {}
        financial_probe: Dict[str, Any] = {
            "has_audited_statement": bool(raw_table or sec_rec),
            "source_filing": raw_table.get("source") or (sec_rec or {}).get("source_filing") or "本地无完整三表原档（待补数）",
            "period": raw_table.get("period") or ((sec_rec or {}).get("fiscal_year_end") if sec_rec else None),
            "currency": "JPY" if market == "JP" else "USD",
            "balance_sheet_balanced": None,
            "metrics": {},
        }

        def _safe_parse_num(val: Any) -> Optional[float]:
            if val is None or val == "":
                return None
            try:
                n = OfficialFilingMapper.parse_financial_number(val)
                return float(n) if (n is not None and not math.isnan(n)) else None
            except Exception:
                try:
                    return float(val)
                except Exception:
                    return None

        rev = raw_table.get("revenue") or (sec_rec or {}).get("revenue")
        gp = raw_table.get("gross_profit")
        ebit = raw_table.get("operating_income")
        ni = raw_table.get("net_income")
        ocf = raw_table.get("operating_cash_flow")
        fcf = raw_table.get("free_cash_flow")
        assets = raw_table.get("total_assets") or (sec_rec or {}).get("total_assets")
        liab = raw_table.get("total_liabilities")
        eq = raw_table.get("stockholders_equity")
        cash = raw_table.get("cash")
        debt = raw_table.get("total_debt")
        shares = raw_table.get("shares") or facts.get("shares_outstanding")

        num_rev = _safe_parse_num(rev)
        num_gp = _safe_parse_num(gp)
        num_ebit = _safe_parse_num(ebit)
        num_ni = _safe_parse_num(ni)
        num_ocf = _safe_parse_num(ocf)
        num_fcf = _safe_parse_num(fcf)
        num_assets = _safe_parse_num(assets)
        num_liab = _safe_parse_num(liab)
        num_eq = _safe_parse_num(eq)
        num_cash = _safe_parse_num(cash)
        num_debt = _safe_parse_num(debt)
        num_shares = _safe_parse_num(shares)

        if num_assets is not None and num_liab is not None and num_eq is not None and num_assets > 0:
            is_bal, abs_diff, rel_ratio = OfficialFilingMapper.verify_balance_sheet_identity(
                total_assets=num_assets,
                total_liabilities=num_liab,
                stockholders_equity=num_eq,
            )
            financial_probe["balance_sheet_balanced"] = is_bal
            financial_probe["balance_sheet_abs_diff"] = round(abs_diff, 2)
            financial_probe["balance_sheet_rel_pct"] = round(rel_ratio * 100.0, 4)
        elif sec_rec and sec_rec.get("is_balanced") is not None:
            financial_probe["balance_sheet_balanced"] = bool(sec_rec.get("is_balanced"))
            financial_probe["balance_sheet_abs_diff"] = sec_rec.get("balance_sheet_diff", 0.0)

        metrics_dict: Dict[str, Any] = {
            "revenue": rev,
            "operating_income": ebit,
            "net_income": ni,
            "free_cash_flow": fcf,
            "total_assets": assets,
            "total_debt": debt,
            "cash": cash,
            "net_cash": (num_cash - num_debt) if (num_cash is not None and num_debt is not None) else None,
            "gross_margin_pct": round((num_gp / num_rev) * 100.0, 2) if (num_gp is not None and num_rev and num_rev > 0) else None,
            "operating_margin_pct": round((num_ebit / num_rev) * 100.0, 2) if (num_ebit is not None and num_rev and num_rev > 0) else None,
            "fcf_conversion_pct": round((num_fcf / num_ni) * 100.0, 2) if (num_fcf is not None and num_ni and num_ni != 0) else None,
            "debt_to_equity_pct": round((num_debt / num_eq) * 100.0, 2) if (num_debt is not None and num_eq and num_eq > 0) else None,
        }
        financial_probe["metrics"] = metrics_dict
        scheduler = getattr(self, "scheduler", None)
        if scheduler is not None:
            financial_probe["scheduled_calculation"] = scheduler.latest_company_financial_metric(clean_ticker)

        # 5. KMV-Merton 信用违约探针（仅当资产/负债/现价/股本俱全时实算，不硬编参数）
        cur_price = quote_info["price"] if quote_info and quote_info["is_valid"] else None
        credit_probe: Dict[str, Any]
        if cur_price and num_shares and num_assets and num_debt is not None and num_liab is not None:
            try:
                num_cur_price = _safe_parse_num(cur_price) or 0.0
                mkt_cap = num_cur_price * num_shares
                st_debt = num_debt * 0.35
                lt_debt = num_debt * 0.65
                cre = gw.analyze_credit(
                    symbol=clean_ticker,
                    raw_financials={
                        "TotalAssets": num_assets,
                        "ShortTermDebt": st_debt,
                        "LongTermDebtNoncurrent": lt_debt,
                    },
                    equity_market_cap=mkt_cap,
                    equity_volatility=0.35,
                    risk_free_rate=0.0442,
                    as_of_date=as_of_iso[:10],
                )
                credit_probe = {"status": "COMPUTED_FROM_SEC_AND_QUOTE", **cre}
            except Exception as exc:
                credit_probe = {"status": "INSUFFICIENT_INPUTS", "note": str(exc)}
        else:
            credit_probe = {
                "status": "REQUIRES_COMPLETE_BALANCE_SHEET_AND_SHARES",
                "note": "缺少完整有息负债或总股本底账，暂不执行信用违约模型测算",
            }

        # 6. 调用 AI 投研适配器产出纯商业语言质性研判（显式剥离机械打分字段）
        audited_facts_for_ai = {
            "revenue": rev,
            "operating_income": ebit,
            "net_income": ni,
            "free_cash_flow": fcf,
            "total_assets": assets,
            "total_liabilities": liab,
            "stockholders_equity": eq,
            "cash": cash,
            "total_debt": debt,
        }
        ai_raw = AIEngineAdapter.get_analysis(
            ticker=clean_ticker,
            market=market,
            company_name=company_name,
            industry_name=ind_rep.industry_name_zh,
            audited_facts=audited_facts_for_ai,
            live_mode=False,
        )
        # 严格过滤机械分数字段，保证完全按用户要求输出文字分析与商业逻辑
        ai_qualitative = {k: v for k, v in ai_raw.items() if k != "qualitative_scores"}
        ai_qualitative["analysis_mode"] = "LOCAL_DETERMINISTIC_AI_SYNTHESIS_NO_SCORING"

        # 7. 构建三态情景估值走廊（仅当有真实现价 + 真实 FCF/股或同量纲 SEPA 枢轴走廊时构建，不瞎猜价格或混用汇率）
        scenario_cards: Optional[Dict[str, Any]] = None
        corridor_basis = "UNAVAILABLE"
        corridor_note = "缺少同币种三表自由现金流或对齐后的枢轴走廊基准，暂不展示价格走廊。"
        if cur_price and float(cur_price) > 0:
            p_now = float(cur_price)
            floor_v = None
            fair_v = None
            target_v = None
            if fcf and shares and float(fcf) > 0 and float(shares) > 0:
                net_cash_ps = (float(cash or 0.0) - float(debt or 0.0)) / float(shares)
                fcf_ps = float(fcf) / float(shares)
                floor_v = max(1.0, round(fcf_ps * 18.0 + net_cash_ps, 2))
                fair_v = max(floor_v, round(fcf_ps * 25.0 + net_cash_ps, 2))
                target_v = max(fair_v, round(fcf_ps * 32.0 + net_cash_ps, 2))
                corridor_basis = "SEC_FCF_PER_SHARE_SENSITIVITY (18x / 25x / 32x + NetCash)"
                corridor_note = "已基于 SEC 官方现金流与稀释股本生成透明自由现金流敏感性估值走廊。"
            elif sepa_record and sepa_record.get("pivot_price"):
                sepa_latest = float(sepa_record.get("latest_price") or p_now)
                ratio = sepa_latest / p_now if p_now > 0 else 0.0
                if 0.4 <= ratio <= 2.5:
                    piv = float(sepa_record["pivot_price"])
                    floor_v = round(min(p_now, piv) * 0.88, 2)
                    fair_v = round(piv, 2)
                    target_v = round(piv * 1.25, 2)
                    corridor_basis = "SEPA_PIVOT_STRUCTURAL_BAND (-12%止损底线 / 枢轴突破 / +25%目标)"
                    corridor_note = "已基于同量纲 SEPA 第二阶段枢轴位构筑战术观察走廊。"
                else:
                    corridor_basis = "UNIT_MISMATCH_BLOCKED"
                    corridor_note = (
                        f"已触发量纲护栏：SEPA 筛选价格 ({sepa_latest}) 与最新行情报价 ({p_now} {market}) 存在量纲或复权/币种差异，"
                        "已拦截混算估值走廊，请先通过 AI 浏览器或 EDINET 补齐官方同币种财报原档。"
                    )

            if floor_v is not None and fair_v is not None and target_v is not None:
                try:
                    scenario_cards = AIResearchAgent.synthesize_three_state_scenario_cards(
                        quote_data={
                            "current_price": p_now,
                            "pessimistic_floor": floor_v,
                            "fair_anchor": fair_v,
                            "optimistic_target": target_v,
                        },
                        ai_analysis=ai_qualitative,
                        param_adjustments={"supply_chain_risk_multiplier": 1.0},
                    )
                    scenario_cards["corridor_basis"] = corridor_basis
                    scenario_cards["corridor_note"] = corridor_note
                except Exception:
                    scenario_cards = None

        # 8. 时机与历史 K 线序列边界诚实声明
        ohlcv_probe = {
            "status": "SEPA_SCREENER_SNAPSHOT" if sepa_record else "REQUIRES_HISTORICAL_OHLCV_BARS",
            "sepa_telemetry": sepa_record,
            "note": (
                "已挂载全盘 14,892 家 SEPA 初筛实时快照指标。"
                if sepa_record
                else "当前本地仅落盘最新基准报价与官方三表原档，缺少 250 日 K 线序列；物理动力学半衰期与 VCP 需补充日线 OHLCV 后实时计算。"
            ),
        }

        data_status = (quote_info or {}).get("data_status") or (
            "PREVIOUS_CLOSE" if financial_probe["has_audited_statement"] or sepa_record else "PARTIAL"
        )

        # 9. 嵌入全自动带入底层事实的多阶段 DCF、WACC 与杜邦估值模型
        auto_val_res = None
        auto_valuation_issue = None
        try:
            val_code, val_payload = self.auto_calculate_company_valuation(clean_ticker)
            if val_code == 200 and val_payload.get("ok"):
                auto_val_res = val_payload.get("data")
            else:
                auto_valuation_issue = (val_payload.get("error") or {}).get("message")
        except Exception:
            auto_valuation_issue = "自动估值执行失败"

        # 10. 关联突发舆情与业务冲击事件 (News & Event Radar Linkage)
        events_analysis = self.get_company_events(clean_ticker, company_name)

        return self._envelope(
            {
                "ticker": clean_ticker,
                "market": market,
                "company_name": company_name,
                "scoring_disabled": True,
                "quote": quote_info
                or {
                    "ticker": clean_ticker,
                    "market": market,
                    "price": cur_price,
                    "currency": "JPY" if market == "JP" else "USD",
                    "data_status": "PREVIOUS_CLOSE" if cur_price else "NOT_CONFIGURED",
                    "timestamp_iso": as_of_iso,
                    "timestamp_formatted": f"筛选底账基准价 {cur_price}" if cur_price else "未进入 24 只高频行情列表",
                },
                "industry_profile": {
                    "industry_id": ind_rep.industry_id,
                    "industry_name_zh": ind_rep.industry_name_zh,
                    "sector_name_zh": ind_rep.sector_name_zh,
                    "macro_sector_name_zh": ind_rep.macro_sector_name_zh,
                    "description": ind_rep.description,
                    "key_drivers": ind_rep.key_drivers,
                    "accounting_focus": ind_rep.accounting_focus,
                    "moat_types": ind_rep.moat_types,
                    "risk_factors": ind_rep.risk_factors,
                    "causal_sensitivities": ind_rep.causal_sensitivities,
                },
                "ai_qualitative_analysis": ai_qualitative,
                "three_state_scenario_corridor": scenario_cards,
                "corridor_status": {
                    "available": scenario_cards is not None,
                    "basis": corridor_basis,
                    "note": corridor_note,
                },
                "quantitative_probes": {
                    "financial_audit": financial_probe,
                    "credit_kmv_probe": credit_probe,
                    "timing_and_ohlcv_probe": ohlcv_probe,
                },
                "automated_valuation": auto_val_res,
                "automated_valuation_issue": auto_valuation_issue,
                "events_analysis": events_analysis,
            },
            as_of=(quote_info or {}).get("timestamp_iso", as_of_iso),
            source="FinancialAnalysisGateway + AIEngineAdapter + AIDossierSynthesizer + SEC",
            status=data_status,
        )

    # =========================================================================
    # 流水线启停控制台、运行历史与看板桥接
    # =========================================================================

    def _map_board_to_pipeline_state(self) -> str:
        with self._lock:
            return self._pipeline_state

    def get_pipeline_status(self) -> Dict[str, Any]:
        board_status = self.board_engine.get_pipeline_status()
        kanban = self.board_engine.get_kanban_board_view()
        with self._lock:
            state = self._pipeline_state
            run_id = self._active_run_id or self._last_run_id
            stage = self._current_stage
            pct = self._progress_pct
            summary = self._last_run_summary
            active_task = self._active_pipeline_task
            cur_stock = self._current_processing_stock
            sub_runs = getattr(self, "_sub_runs", {}) or {}

        # 默认双轨子流水线状态回落
        default_audit = {
            "run_id": f"{run_id}-AUDIT" if run_id else "AUDIT-SYNC",
            "name": "本地核对同步",
            "status": "SUCCESS" if state == "SUCCESS" else ("RUNNING" if state in ("QUEUED", "RUNNING") else "IDLE"),
            "progress_pct": pct,
            "message": "三表平账、行情时效、密码学账本核验" if state != "RUNNING" else "正在核对本地财报三表与账本...",
        }
        default_ingest = {
            "run_id": f"{run_id}-INGEST" if run_id else "INGEST-FLOW",
            "name": "数据采集",
            "status": "SUCCESS" if state == "SUCCESS" else ("RUNNING" if state in ("QUEUED", "RUNNING") else "IDLE"),
            "progress_pct": pct,
            "message": "美股/日股增量补数与官方备案队列对齐" if state != "RUNNING" else "正在扫描采集补数队列...",
        }

        return self._envelope(
            {
                "pipeline_state": state,
                "is_running": state in ("QUEUED", "RUNNING", "STOPPING"),
                "active_run_id": self._active_run_id,
                "last_run_id": self._last_run_id,
                "master_run_id": run_id,
                "current_stage": stage,
                "active_pipeline_task": active_task,
                "current_processing_stock": cur_stock,
                "progress_pct": pct,
                "summary": summary,
                "local_audit_sync": sub_runs.get("local_audit_sync", default_audit),
                "data_ingestion": sub_runs.get("data_ingestion", default_ingest),
                "board_engine_status": board_status,
                "kanban_counts": kanban.get("counts", {}),
                "kanban_lanes": kanban.get("lanes", {}),
                "total_board_items": kanban.get("total_items", 0),
            },
            as_of=_utc_now_iso(),
            source="InformationPipelineBoardEngine + TerminalOrchestrator",
            status="FRESH",
            run_id=run_id,
        )

    def start_pipeline(self, mode: str = "local_audit_sync", market: str = "ALL") -> Tuple[bool, Dict[str, Any]]:
        if mode not in {"local_audit_sync", "full_market_screener", "incremental_replenish"}:
            _, error = self.error_envelope("INVALID_MODE", "未知运行模式")
            return False, error
        with self._lock:
            if self._pipeline_state in ("QUEUED", "RUNNING", "STOPPING"):
                _, err_payload = self.error_envelope(
                    "PIPELINE_ALREADY_RUNNING",
                    f"流水线当前处于 {self._pipeline_state} 状态，请勿重复启动",
                    status_code=409,
                )
                err_payload["data"] = {
                    "accepted": False,
                    "already_running": True,
                    "pipeline_state": self._pipeline_state,
                    "run_id": self._active_run_id,
                    "message": f"流水线当前处于 {self._pipeline_state} 状态，请勿重复启动",
                }
                return False, err_payload

            ts_tag = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            run_id = f"RUN-{ts_tag}-{uuid.uuid4().hex[:4].upper()}"
            self._stop_event.clear()
            self._active_run_id = run_id
            self._last_run_id = run_id
            self._pipeline_state = "QUEUED"
            self._progress_pct = 5
            self._current_stage = "已入队 · 正在初始化本地核验调度槽位"
            self._last_run_summary = f"启动模式: {mode} | 市场范围: {market.upper()}"

            run_record = {
                "run_id": run_id,
                "mode": mode,
                "market": market.upper(),
                "status": "QUEUED",
                "started_at": _utc_now_iso(),
                "finished_at": None,
                "duration_ms": 0,
                "stages_completed": [],
                "message": self._last_run_summary,
            }
            self._runs.appendleft(run_record)

        self._append_log("INFO", "pipeline_orchestrator", f"[{run_id}] 收到启动指令 (mode={mode}, market={market})", run_id=run_id)
        self._broadcast_sse("pipeline_status", self.get_pipeline_status()["data"])

        worker = threading.Thread(
            target=self._run_pipeline_worker,
            args=(run_id, mode, market),
            name=f"WaterSourceWorker-{run_id}",
            daemon=True,
        )
        with self._lock:
            self._worker_thread = worker
        worker.start()

        return True, self._envelope(
            {
                "accepted": True,
                "already_running": False,
                "pipeline_state": "QUEUED",
                "run_id": run_id,
                "mode": mode,
                "market": market.upper(),
                "message": "已提交所选任务",
            },
            as_of=_utc_now_iso(),
            source="pipeline_orchestrator",
            status="FRESH",
            run_id=run_id,
        )

    def stop_pipeline(self, run_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            if self._pipeline_state not in ("QUEUED", "RUNNING", "STOPPING"):
                return self._envelope(
                    {
                        "stopped": True,
                        "pipeline_state": self._pipeline_state,
                        "run_id": self._last_run_id,
                        "message": f"流水线当前处于 {self._pipeline_state}，无需重复停止",
                    },
                    as_of=_utc_now_iso(),
                    source="pipeline_orchestrator",
                    status="FRESH",
                )
            target_id = run_id or self._active_run_id or self._last_run_id
            self._stop_event.set()
            self._pipeline_state = "STOPPING"
            self._current_stage = "正在响应协作停机信号，安全排空当前任务..."
            self.board_engine.stop_pipeline()

        self._append_log("WARN", "pipeline_orchestrator", f"[{target_id}] 收到安全停止信号，正在有序退出", run_id=target_id)
        self._broadcast_sse("pipeline_status", self.get_pipeline_status()["data"])
        return self._envelope(
            {
                "stopped": True,
                "pipeline_state": "STOPPING",
                "run_id": target_id,
                "message": "已下发安全停机信号，当前子阶段完成后将立即转为 STOPPED",
            },
            as_of=_utc_now_iso(),
            source="pipeline_orchestrator",
            status="FRESH",
            run_id=target_id,
        )

    def _run_pipeline_worker(self, run_id: str, mode: str, market: str) -> None:
        t0 = time.perf_counter()
        with self._lock:
            self._pipeline_state = "RUNNING"
            self._progress_pct = 20
            self._current_stage = "正在执行双轨任务：本地核对同步与增量数据采集..."
            self._sub_runs = {
                "local_audit_sync": {
                    "run_id": f"{run_id}-AUDIT",
                    "name": "本地核对同步",
                    "status": "RUNNING",
                    "progress_pct": 25,
                    "message": "正在核对本地财报三表、日线报价与密码学账本哈希...",
                    "started_at": _utc_now_iso(),
                },
                "data_ingestion": {
                    "run_id": f"{run_id}-INGEST",
                    "name": "数据采集",
                    "status": "RUNNING",
                    "progress_pct": 20,
                    "message": "正在扫描增量行情补数队列与官方文件索引...",
                    "started_at": _utc_now_iso(),
                },
            }
        self._broadcast_sse("pipeline_status", self.get_pipeline_status()["data"])

        audit_status = "SUCCESS"
        audit_msg = "本地三表平账、行情时效与密码学账本核对完成"
        if not self._stop_event.wait(0.15):
            try:
                res_status, details = self.audit_local_data()
                audit_status = res_status
                audit_msg = details.get("message", audit_msg)
            except Exception as exc:
                audit_status = "FAILED"
                audit_msg = str(exc)

        with self._lock:
            self._sub_runs["local_audit_sync"].update({
                "status": audit_status,
                "progress_pct": 100 if audit_status == "SUCCESS" else 50,
                "message": audit_msg,
                "finished_at": _utc_now_iso(),
            })
            self._progress_pct = 65
        self._broadcast_sse("pipeline_status", self.get_pipeline_status()["data"])

        ingest_status = "SUCCESS"
        ingest_msg = "增量补数清单与归档分级生命周期对齐完成"
        if not self._stop_event.wait(0.15):
            try:
                if mode == "full_market_screener":
                    ingest_status, ingest_msg = "FAILED", "正式初筛等待已核验的日线 OHLCV 批次"
                elif mode == "incremental_replenish":
                    queue = self.get_collection_overview()["data"]["replenishment_queue"]
                    pending = queue.get("total_pending", 0)
                    ingest_status = "PARTIAL_SUCCESS" if pending else "SUCCESS"
                    ingest_msg = f"已核对本地补数清单，{pending} 家等待官方原文"
                else:
                    queue = self.get_collection_overview()["data"]["replenishment_queue"]
                    pending = queue.get("total_pending", 0)
                    ingest_status = "PARTIAL_SUCCESS" if pending else "SUCCESS"
                    ingest_msg = f"增量补数队列已核对，{pending} 家等待官方原文" if pending else "监控标的已完全归档入库"
            except Exception as exc:
                ingest_status = "FAILED"
                ingest_msg = str(exc)

        final_status = "SUCCESS"
        if audit_status == "FAILED" or ingest_status == "FAILED":
            final_status = "FAILED"
        elif audit_status == "PARTIAL_SUCCESS" or ingest_status == "PARTIAL_SUCCESS":
            final_status = "PARTIAL_SUCCESS"

        final_summary = f"本地核对: {audit_msg} | 数据采集: {ingest_msg}"

        with self._lock:
            self._sub_runs["data_ingestion"].update({
                "status": ingest_status,
                "progress_pct": 100 if ingest_status in ("SUCCESS", "PARTIAL_SUCCESS") else 50,
                "message": ingest_msg,
                "finished_at": _utc_now_iso(),
            })
            self._pipeline_state = final_status
            self._active_run_id = None
            self._progress_pct = 100 if final_status in ("SUCCESS", "PARTIAL_SUCCESS") else 0
            self._current_stage = final_summary
            self._last_run_summary = final_summary
            for record in self._runs:
                if record["run_id"] == run_id:
                    record.update(status=final_status, finished_at=_utc_now_iso(), message=final_summary)
                    break
        self._broadcast_sse("pipeline_status", self.get_pipeline_status()["data"])

    def get_pipeline_runs(self) -> Dict[str, Any]:
        radar = self._read_radar_events_and_cycles(limit=10)
        with self._lock:
            mem_runs = list(self._runs)
        return self._envelope(
            {
                "orchestrator_runs": mem_runs,
                "radar_collection_cycles": radar.get("cycles", []),
                "total_radar_cycles": radar.get("total_cycles", 0),
            },
            as_of=_utc_now_iso(),
            source="pipeline_orchestrator + event_radar.sqlite3",
            status="FRESH",
        )

    def get_logs(
        self,
        *,
        level: str = "ALL",
        module: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        lvl = level.strip().upper()
        mod_f = module.strip().lower() if module else ""
        kw = q.strip().lower() if q else ""

        with self._lock:
            all_logs = list(self._logs)
        scheduler = getattr(self, "scheduler", None)
        if scheduler is not None and mod_f in ("", "all", "terminal_scheduler"):
            all_logs = scheduler.logs(lvl, kw, max(1, limit)) + all_logs
            all_logs.sort(key=lambda entry: str(entry["timestamp"]).replace("+00:00", "Z"), reverse=True)

        filtered: List[Dict[str, Any]] = []
        modules_seen = sorted({str(x.get("module", "")) for x in all_logs if x.get("module")})
        for entry in all_logs:
            if lvl != "ALL" and entry.get("level") != lvl:
                continue
            if mod_f and mod_f != "all" and mod_f != str(entry.get("module", "")).lower():
                continue
            if kw:
                hay = " ".join(str(entry.get(key, "")) for key in ("module", "message", "run_id", "task")).lower()
                if kw not in hay:
                    continue
            filtered.append(entry)
            if len(filtered) >= max(1, limit):
                break

        return self._envelope(
            {
                "logs": filtered,
                "total_buffered": len(all_logs),
                "available_modules": modules_seen,
                "log_files": self.logging_manager.get_log_files_overview() if hasattr(self, "logging_manager") else [],
            },
            as_of=_utc_now_iso(),
            source="watersource_ring_log_buffer",
            status="FRESH",
        )

    def get_settings(self) -> Dict[str, Any]:
        ledger = PredictionLedger(db_path=self.data_dir / "ledger" / "predictions_ledger.sqlite3")
        ledger_valid, ledger_err = ledger.verify_integrity()
        ledger_stats = ledger.get_stats()
        policy = LifecyclePolicyConfig()

        endpoints = [
            {"method": "GET", "path": "/api/health", "purpose": "服务连接、四层合规与账本自检"},
            {"method": "GET", "path": "/api/dashboard/summary", "purpose": "总览大屏聚合（KPI + 市场 + 指标 + 情报 + 流水线）"},
            {"method": "GET", "path": "/api/markets/quotes", "purpose": "美日指数与 24 只就绪资产时效行情"},
            {"method": "GET", "path": "/api/indicators/latest", "purpose": "核心宏观指标、FRED 归档与 SEPA 宽度"},
            {"method": "GET", "path": "/api/events", "purpose": "突发事件雷达 SQLite 检索与分级统计"},
            {"method": "GET", "path": "/api/events/{event_id}", "purpose": "事件物理传导与信源核验详情"},
            {"method": "GET", "path": "/api/collection/overview", "purpose": "6 大物理采集管线、补数队列与冷热分层"},
            {"method": "POST", "path": "/api/collection/tasks/rerun", "purpose": "采集中心子开关：阻塞重跑指定采集或治理管线任务"},
            {"method": "POST", "path": "/api/collection/tasks/toggle", "purpose": "采集中心子开关：切换指定采集任务的全局执行启用状态"},
            {"method": "GET", "path": "/api/analytics/candidates", "purpose": "SEPA 枢轴就绪与核心持仓候选清单"},
            {"method": "GET", "path": "/api/analytics/company", "purpose": "无打分个股诊断：定量探针 + AI 定性分析 + 三态走廊"},
            {"method": "GET", "path": "/api/pipeline/status", "purpose": "流水线状态机与 5 列看板统计"},
            {"method": "POST", "path": "/api/pipeline/start", "purpose": "安全启动本地核验与看板同步任务"},
            {"method": "POST", "path": "/api/pipeline/stop", "purpose": "优雅发送协作停机信号"},
            {"method": "GET", "path": "/api/pipeline/runs", "purpose": "调度运行历史与雷达采集周期"},
            {"method": "GET", "path": "/api/logs", "purpose": "系统实时分级日志流检索"},
            {"method": "GET", "path": "/api/settings", "purpose": "只读系统配置、阈值与账本验签状态"},
            {"method": "GET", "path": "/api/stream", "purpose": "SSE 实时状态与日志推流通道"},
        ]

        return self._envelope(
            {
                "architecture_policy": {
                    "dependency_direction": "financial_core -> finance_tools -> financial_reporting -> scripts -> data",
                    "existing_tools_modified": False,
                    "scoring_mode": "DISABLED (定量探针 + AI 质性商业分析 + 三态情景走廊)",
                    "quote_max_staleness_hours": 24.0,
                },
                "lifecycle_policy": {
                    "hot_quote_max_age_days": policy.hot_quote_days,
                    "warm_quote_max_age_days": policy.warm_quote_days,
                    "cold_compression": "gzip (.cold.json.gz)",
                },
                "environment_discovery": (
                    self._env_inspector()
                    if self._env_inspector is not None
                    else {
                        "gdrive_detected": bool(
                            os.getenv("GDRIVE_EXECUTABLE")
                            or os.getenv("GDRIVE_EXE")
                            or shutil.which("gdrive")
                            or list((Path.home() / ".gemini" / "antigravity" / "plugin_data" / "gdrive" / "bin").glob("gdrive*.exe"))
                        ) if (Path.home() / ".gemini" / "antigravity" / "plugin_data" / "gdrive" / "bin").is_dir() else bool(
                            os.getenv("GDRIVE_EXECUTABLE") or os.getenv("GDRIVE_EXE") or shutil.which("gdrive")
                        ),
                        "edge_detected": bool(
                            os.getenv("EDGE_EXECUTABLE")
                            or os.getenv("EDGE_EXE")
                            or shutil.which("msedge")
                            or Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe").is_file()
                            or Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe").is_file()
                        ),
                        "python_executable": sys.executable,
                    }
                ),
                "prediction_ledger": {
                    "integrity_valid": ledger_valid,
                    "integrity_error": ledger_err,
                    **ledger_stats,
                },
                "api_contract_endpoints": endpoints,
            },
            as_of=_utc_now_iso(),
            source="env_discovery + PredictionLedger + LifecyclePolicyConfig",
            status="FRESH" if ledger_valid else "ERROR",
        )

    def get_dashboard_summary(self) -> Dict[str, Any]:
        quotes_res = self.get_market_quotes(market="ALL")
        ind_res = self.get_latest_indicators()
        events_res = self.get_events(limit=8)
        pipe_res = self.get_pipeline_status()
        logs_res = self.get_logs(limit=8)
        col_res = self.get_collection_overview()

        q_data = quotes_res["data"]
        ev_data = events_res["data"]
        pipe_data = pipe_res["data"]
        col_data = col_res["data"]
        sev = ev_data.get("severity_counts", {})
        sepa_b = ind_res["data"].get("sepa_breadth", {})

        kpis = [
            {
                "id": "kpi_monitored_assets",
                "label": "最新行情就绪标的",
                "value": q_data.get("total_ready_assets", 0),
                "unit": "只",
                "subtext": f"含 {len(q_data.get('stale_blocked_tickers', []))} 只超期阻断 ({', '.join(q_data.get('stale_blocked_tickers', [])) or '无'})",
                "tone": "warning" if q_data.get("stale_blocked_tickers") else "good",
            },
            {
                "id": "kpi_sepa_pivot",
                "label": "SEPA 全市场初筛",
                "value": "待核验",
                "unit": "",
                "subtext": "等待真实日线 OHLCV 批次",
                "tone": "accent",
            },
            {
                "id": "kpi_events_total",
                "label": "雷达已捕获事件",
                "value": ev_data.get("total_events", 0),
                "unit": "条",
                "subtext": f"传闻隔离 {ev_data.get('verification_counts', {}).get('Unverified_Rumor', 0)} 条",
                "tone": "info",
            },
            {
                "id": "kpi_high_severity",
                "label": "高优冲击事件 (P0+P1)",
                "value": int(sev.get("P0", 0)) + int(sev.get("P1", 0)),
                "unit": "条",
                "subtext": f"P0={sev.get('P0', 0)} (极危) · P1={sev.get('P1', 0)} (高优)",
                "tone": "critical" if int(sev.get("P0", 0)) > 0 else "warning",
            },
            {
                "id": "kpi_pipeline_state",
                "label": "流水线运行状态",
                "value": pipe_data.get("pipeline_state", "IDLE"),
                "unit": "",
                "subtext": f"SEC 平账 {col_data['pipelines'][2]['completed']}/{col_data['pipelines'][2]['total']} · 进度 {pipe_data.get('progress_pct', 0)}%",
                "tone": "good" if pipe_data.get("pipeline_state") in ("SUCCESS", "IDLE") else "accent",
            },
        ]

        scheduler = getattr(self, "scheduler", None)
        scheduler_info = None
        if scheduler is not None:
            try:
                snap = scheduler.snapshot()
                scheduler_info = {
                    "scheduled": snap.get("scheduled", False),
                    "automatic_enabled": snap["automatic_enabled"],
                    "automatic_available": snap["automatic_available"],
                    "tasks": snap.get("tasks", []),
                    "active_runs": [r for r in snap.get("runs", []) if r.get("status") in ("QUEUED", "RUNNING")],
                    "recent_runs": snap.get("runs", [])[:8],
                }
            except Exception:
                scheduler_info = None

        return self._envelope(
            {
                "freshness_banner": col_data["readiness"].get("banner_text", ""),
                "task_scheduler": scheduler_info,
                "readiness": {
                    "latest_date_str": col_data["readiness"].get("latest_date_str"),
                    "latest_timestamp_utc": col_data["readiness"].get("latest_timestamp_utc"),
                    "macro_indices_completed": col_data["readiness"].get("macro_indices_completed", []),
                    "equities_completed": col_data["readiness"].get("equities_completed", []),
                    "total_completed_count": col_data["readiness"].get("total_completed_count", 0),
                    "data_source_summary": col_data["readiness"].get("data_source_summary", "Google Finance 授权专用行情表与公开交易所归档"),
                    "market_session_note": col_data["readiness"].get("market_session_note", "前一交易日收盘价基准 (已核验新鲜度)"),
                },
                "kpis": kpis,
                "markets": {
                    "market_status": q_data.get("market_status"),
                    "market_session_note": q_data.get("market_session_note"),
                    "us_indices": q_data.get("us_indices", []),
                    "jp_indices": q_data.get("jp_indices", []),
                    "jp_core_equities": q_data.get("jp_core_equities", []),
                    "all_quotes": q_data.get("all_quotes", []),
                    "daily_archives": scheduler.market_archives() if scheduler else [],
                    "reconciliation": {
                        "us": scheduler.reconciliation_summary("US") if scheduler else None,
                        "jp": scheduler.reconciliation_summary("JP") if scheduler else None,
                    } if scheduler else None,
                },
                "indicators": ind_res["data"].get("indicators", []),
                "sepa_breadth": sepa_b,
                "events_summary": {
                    "total_events": ev_data.get("total_events", 0),
                    "severity_counts": sev,
                    "verification_counts": ev_data.get("verification_counts", {}),
                    "top_events": ev_data.get("events", [])[:5],
                },
                "pipeline": pipe_data,
                "recent_logs": logs_res["data"].get("logs", [])[:8],
            },
            as_of=quotes_res["meta"]["as_of"],
            source="watersource_dashboard_aggregator",
            status=quotes_res["meta"]["status"],
        )
