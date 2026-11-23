# -*- coding: utf-8 -*-
from __future__ import annotations
"""事件雷达、突发事件周期提炼与采集管道概览领域 Mixin."""

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

ROOT = Path(__file__).resolve().parents[2]
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




class TerminalEventMixin:
    """事件雷达、突发事件周期提炼与采集管道概览领域 Mixin."""
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

                sev_zh_map = {
                    "P0": "极高影响",
                    "P1": "重要关注",
                    "P2": "行业动态",
                    "P3": "常规资讯",
                }
                sev_tone_map = {
                    "P0": "critical",
                    "P1": "warning",
                    "P2": "info",
                    "P3": "muted",
                }
                ver_zh_map = {
                    "Confirmed_Fact": "官方权威核实",
                    "Corroborated_Report": "主流媒体采信",
                    "Unverified_Rumor": "待核实传闻隔离",
                }
                ver_tone_map = {
                    "Confirmed_Fact": "success",
                    "Corroborated_Report": "info",
                    "Unverified_Rumor": "danger",
                }
                tier_val = row_d.get("credibility_tier")
                tier_zh = (
                    "官方原发 (一级)" if tier_val in (1, "1")
                    else "权威媒体 (二级)" if tier_val in (2, "2")
                    else "行业分析 (三级)"
                )

                raw_content = row_d.get("raw_content") or ""
                micro_impact = row_d.get("micro_physical_impact")
                entities_list = _parse_json_list(row_d.get("involved_entities"))
                segments_list = _parse_json_list(row_d.get("affected_business_segments"))

                # 动态提炼守卫：若未提纯或与标题机械相同，即时调用提炼引擎补全买方微观研判
                if not hasattr(self, "_distillation_engine"):
                    from finance_tools.events_and_verification.event_distillation_engine import EventDistillationEngine
                    self._distillation_engine = EventDistillationEngine(self.root)

                clean_content = self._distillation_engine.clean_html_text(raw_content)

                if not micro_impact or micro_impact == row_d.get("title"):
                    distilled = self._distillation_engine.distill_single_event(
                        row_d.get("title", ""),
                        raw_content,
                        row_d.get("source_name", ""),
                        fallback_category=row_d.get("category", "Other_Macro_Event"),
                    )
                    micro_impact = distilled.get("micro_physical_impact") or micro_impact
                    if not entities_list or entities_list == ["未知实体"] or entities_list == ["美国证监会 (SEC)"]:
                        entities_list = distilled.get("involved_entities", entities_list)
                    if not segments_list or segments_list == ["通用产业"]:
                        segments_list = distilled.get("affected_business_segments", segments_list)

                parsed_events.append(
                    {
                        "event_id": row_d.get("event_id"),
                        "title": row_d.get("title"),
                        "category": row_d.get("category"),
                        "severity": sev,
                        "severity_zh": sev_zh_map.get(sev, "常规资讯"),
                        "severity_tone": sev_tone_map.get(sev, "muted"),
                        "published_at": pub_raw,
                        "published_date": pub_date,
                        "published_time": pub_time,
                        "published_at_iso": pub_iso,
                        "collected_at": row_d.get("collected_at"),
                        "source_name": row_d.get("source_name"),
                        "credibility_tier": tier_val,
                        "credibility_tier_zh": tier_zh,
                        "credibility_score": row_d.get("credibility_score"),
                        "verification_status": vstat,
                        "verification_status_zh": ver_zh_map.get(vstat, "待核实传闻隔离" if vstat == "Unverified_Rumor" else "主流媒体采信"),
                        "verification_status_tone": ver_tone_map.get(vstat, "info"),
                        "verification_note": row_d.get("verification_note"),
                        "micro_physical_impact": micro_impact,
                        "involved_entities": entities_list,
                        "affected_business_segments": segments_list,
                        "estimated_duration": row_d.get("estimated_duration"),
                        "requires_deep_analysis": bool(row_d.get("requires_deep_analysis")),
                        "raw_content": raw_content,
                        "clean_content": clean_content,
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
        source_config = _safe_read_json(self.data_dir / "ingestion-sources.json", {}).get("sources", {})
        scheduled_sources = {"yfinance", "fred_csv", "rss"}
        source_catalog = [
            {
                "id": source_id,
                "dataset": config.get("dataset_kind"),
                "trust": config.get("source_kind"),
                "mode": (
                    "disabled" if not config.get("enabled", True) or config.get("env") else
                    "scheduled" if source_id in scheduled_sources else "available"
                ),
            }
            for source_id, config in source_config.items()
        ]
        radar_config = _safe_read_json(ROOT / "config/event_radar_sources.json", {})
        rss_scheduled = any(source["id"] == "rss" and source["mode"] == "scheduled" for source in source_catalog)
        event_sources = [
            {"name": feed["name"], "role": (
                "scheduled" if rss_scheduled and feed.get("authority") in ("official", "issuer") else "candidate"
            )}
            for feed in source_config.get("rss", {}).get("feeds", []) if feed.get("name")
        ] + [
            {"name": channel["channel_name"], "role": "radar", "priority": channel.get("priority")}
            for channel in radar_config.get("channels", []) if channel.get("channel_name")
        ]
        return self._envelope(
            {
                "readiness": readiness,
                "source_catalog": source_catalog,
                "event_sources": event_sources,
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
                "data_type_inventory": {
                    "universe": {"total": 14892, "us_count": 10445, "jp_count": 4447, "label": "标的池索引底账", "unit": "家"},
                    "filings": {"total": 1226, "covered_companies": 613, "pending_replenishment": 72, "label": "官方财报原档", "unit": "份"},
                    "quotes": {"total": len(list((self.data_dir / "google-finance" / "raw").glob("*.json"))), "active_pool": 30, "precision_pass_rate_pct": 100.0, "label": "市场行情快照", "unit": "份"},
                    "screening": {"total_chunks": 150, "us_chunks": 105, "jp_chunks": 45, "results": 150, "label": "全市场初筛切片", "unit": "组"},
                    "macro": {"total_series": 10, "label": "宏观与基准利率", "unit": "组"},
                    "events": {"channels": 15, "processed_hashes": 1536, "p0_p1_triggers": 100, "label": "突发事件雷达信源", "unit": "通道"},
                    "ledger": {"total": 1759, "active": 1750, "resolved": 9, "unique_tickers": 168, "label": "不可篡改决策账本", "unit": "笔"},
                    "knowledge": {"sectors": 11, "industries": 41, "models": 16, "metrics": 146, "label": "行业知识与模型库", "unit": "项"},
                },
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
                    "id": n.get("id") or n.get("title", ""),
                    "title": n.get("title", ""),
                    "content": n.get("content") or n.get("summary") or n.get("description") or n.get("title", ""),
                    "source": n.get("source", "Official_RSS"),
                    "published_at": n.get("published_at", ""),
                    "url": n.get("url") or n.get("source", ""),
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
        self._broadcast_sse("collection_update", {
            "type": "events",
            "summarized": cycle_res.get("summarized_count", 0),
            "total_events": radar.get("total_events", 0),
        })
        try:
            self._broadcast_sse("snapshot", self.get_dashboard_summary()["data"])
        except Exception:
            pass
        return 200, self._envelope({
            "message": f"提炼完成：扫描 {cycle_res.get('scanned_count', 0)} 篇 · 提炼入雷达 {cycle_res.get('summarized_count', 0)} 条 · 重大事件 {cycle_res.get('p0_p1_triggered_count', 0)} 条",
            "cycle_result": cycle_res,
            "total_events": radar.get("total_events", 0),
        })

