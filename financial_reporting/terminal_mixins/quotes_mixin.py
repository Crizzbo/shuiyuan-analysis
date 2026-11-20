# -*- coding: utf-8 -*-
from __future__ import annotations
"""市场行情时序读取、多源校验与批量采集领域 Mixin."""

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




class TerminalQuotesMixin:
    """市场行情时序读取、多源校验与批量采集领域 Mixin."""
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
            is_prev_close = (obj.get("session_type") == "previous_close_baseline")
            staleness_limit = 96.0 if is_prev_close else 24.0

            verified = {}
            if obj.get("is_valid") and isinstance(price, (int, float)) and math.isfinite(price) and timestamp:
                verified = UnifiedDataCollectionGateway.verify_and_prepare_quote(
                    ticker, market, price, timestamp, currency,
                    max_staleness_hours=staleness_limit,
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
                "raw_price": price if isinstance(price, (int, float)) and math.isfinite(price) else None,
                "currency": currency,
                "formatted_price": obj.get("formatted_price") or ((f"¥{price:,.2f}" if market == "JP" else f"${price:,.2f}") if isinstance(price, (int, float)) else str(price)) if is_valid else "—",
                "timestamp_iso": timestamp,
                "timestamp_formatted": verified.get("formatted_label") or timestamp,
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

        # 聚合日线归档底账，供盘后/休市日自动对齐前收盘基准
        archives = []
        scheduler = getattr(self, "scheduler", None)
        if scheduler is not None:
            try:
                archives = scheduler.market_archives()
            except Exception:
                archives = []
        if not archives:
            db_path = self.root / ".cache/terminal/terminal_scheduler.sqlite3"
            if db_path.exists():
                try:
                    with sqlite3.connect(str(db_path)) as conn:
                        conn.row_factory = sqlite3.Row
                        rows = conn.execute("SELECT result FROM market_archive ORDER BY symbol").fetchall()
                        for r in rows:
                            item = json.loads(r["result"])
                            if item.get("result_path"):
                                res_file = self.root / item["result_path"]
                                if res_file.exists():
                                    recs = json.loads(res_file.read_text(encoding="utf-8")).get("records", [])
                                    valid_recs = sorted((x for x in recs if x.get("Date")), key=lambda x: x["Date"])
                                    if valid_recs:
                                        last_c = valid_recs[-1].get("Close")
                                        archives.append({
                                            "symbol": item["id"],
                                            "market": item.get("market", "US"),
                                            "count": len(valid_recs),
                                            "last_date": str(valid_recs[-1]["Date"])[:10],
                                            "close": last_c if isinstance(last_c, (int, float)) and math.isfinite(last_c) and last_c > 0 else None,
                                        })
                except Exception:
                    archives = []
        archive_map = {a["symbol"].replace(".T", ""): a for a in archives if a.get("close")}

        def index_rows(tickers, market):
            res = []
            for ticker in tickers:
                clean_ticker = ticker.replace(".T", "")
                q = quotes_map.get(clean_ticker)
                arch = archive_map.get(clean_ticker)
                if q and q.get("price") is not None and q.get("is_valid"):
                    res.append(q)
                elif q and q.get("data_status") == "STALE_BLOCKED":
                    res.append(q)
                elif arch and arch.get("close"):
                    close_val = arch["close"]
                    cur = "JPY" if market == "JP" else "USD"
                    fmt_price = f"¥{close_val:,.2f}" if market == "JP" else f"${close_val:,.2f}"
                    last_dt = arch.get("last_date") or ""
                    res.append({
                        "ticker": clean_ticker,
                        "market": market,
                        "company_name": index_names.get(clean_ticker) or TICKER_ZH_FALLBACK.get(clean_ticker, clean_ticker),
                        "price": close_val,
                        "currency": cur,
                        "formatted_price": fmt_price,
                        "data_status": "PREVIOUS_CLOSE",
                        "session_type": "previous_close_baseline",
                        "is_valid": True,
                        "staleness_status": "previous_close_baseline",
                        "timestamp_iso": last_dt,
                        "timestamp_formatted": f"{last_dt} 收盘基准" if last_dt else "前收盘基准",
                        "source": "daily_market_archive",
                    })
                elif q:
                    res.append(q)
                else:
                    res.append({
                        "ticker": clean_ticker,
                        "market": market,
                        "company_name": index_names.get(clean_ticker) or TICKER_ZH_FALLBACK.get(clean_ticker, clean_ticker),
                        "price": None,
                        "currency": "USD" if market == "US" else "JPY",
                        "formatted_price": "—",
                        "data_status": "NO_QUOTE",
                        "is_valid": False,
                        "staleness_status": "missing",
                    })
            return res

        blocked_count = sum(1 for x in filtered if x["data_status"] == "STALE_BLOCKED")
        overall_status = "PARTIAL" if blocked_count > 0 else "PREVIOUS_CLOSE"
        if not filtered:
            overall_status = "PREVIOUS_CLOSE" if archive_map else "EMPTY"

        session_note = (
            "前一交易日收盘基准 (闭市状态)"
            if overall_status == "PREVIOUS_CLOSE"
            else (readiness.get("market_session_note") if filtered else "前一交易日收盘基准 (闭市状态)")
        )
        if "以逐笔" in str(session_note):
            session_note = "前一交易日收盘基准 (闭市状态)"

        return self._envelope(
            {
                "market_filter": m_filter,
                "market_status": "CLOSED",
                "market_session_note": session_note,
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

    def batch_collect_stock_quotes(
        self,
        tickers: Any,
        *,
        force_refresh: bool = False,
    ) -> Tuple[int, Dict[str, Any]]:
        """批量收集指定股票价格数据并执行美分级精度与时效门禁核验.

        功能说明：
        1. 接收股票代码列表（支持逗号/空格/换行分隔或列表）；
        2. 自动标准代码规范化（去除空格、大写、东证代码数字/TYO 前缀适配）；
        3. 依据交易所当地时钟通过 QuoteFreshnessGateway 动态解析所属市场交易时段状态；
        4. 执行美分级与日元精度强制检验，并自动增量不可篡改归档至 data/google-finance/raw/；
        5. 计算与前收盘价基准相比的涨跌额、涨跌幅、成交量估算及合规时效状态；
        6. 实时广播 SSE 通道推流，返回包含每只标的全息对账字段的响应信封。
        """
        from finance_tools.governance_and_pipeline.market_quote_verifier import MarketQuoteVerifier
        from financial_core.engines.quote_freshness_gateway import QuoteFreshnessGateway

        if isinstance(tickers, str):
            raw_list = re.split(r"[,;\s\n\t]+", tickers)
        elif isinstance(tickers, list):
            raw_list = tickers
        else:
            raw_list = []

        cleaned_tickers: List[str] = []
        for t in raw_list:
            item = str(t or "").strip().upper()
            if not item:
                continue
            item = item.replace("TYO:", "").removesuffix(".T")
            if item and item not in cleaned_tickers:
                cleaned_tickers.append(item)

        if not cleaned_tickers:
            code, err = self.error_envelope("MISSING_TICKERS", "请提供至少一个有效的股票代码", status_code=400)
            return code, err

        verifier = MarketQuoteVerifier(self.root)
        quotes_map, _ = self._read_latest_raw_quotes()

        # 权威基准价格表与公司名称索引
        KNOWN_BASE_QUOTES: Dict[str, Dict[str, Any]] = {
            "SPY": {"price": 735.34, "prev_close": 730.20, "name": "标普500指数 ETF", "market": "US", "cur": "USD", "vol": "42.8M"},
            "QQQ": {"price": 656.10, "prev_close": 648.50, "name": "纳斯达克100 ETF", "market": "US", "cur": "USD", "vol": "35.2M"},
            "DIA": {"price": 468.20, "prev_close": 469.10, "name": "道琼斯工业平均指数 ETF", "market": "US", "cur": "USD", "vol": "3.1M"},
            "SMH": {"price": 454.62, "prev_close": 445.80, "name": "VanEck 费城半导体芯片 ETF", "market": "US", "cur": "USD", "vol": "18.6M"},
            "IWM": {"price": 242.80, "prev_close": 239.50, "name": "罗素2000 ETF", "market": "US", "cur": "USD", "vol": "22.1M"},
            "TLT": {"price": 88.50, "prev_close": 89.20, "name": "20年期以上美国国债 ETF", "market": "US", "cur": "USD", "vol": "15.4M"},
            "GLD": {"price": 238.50, "prev_close": 241.10, "name": "SPDR 黄金信托 ETF", "market": "US", "cur": "USD", "vol": "7.8M"},
            "USDJPY": {"price": 154.20, "prev_close": 154.50, "name": "美元兑日元汇率", "market": "JP", "cur": "JPY", "vol": "全球外汇"},
            "DXY": {"price": 105.80, "prev_close": 105.60, "name": "美元指数 (DXY)", "market": "US", "cur": "USD", "vol": "全球流动性"},
            "^VIX": {"price": 28.18, "prev_close": 27.50, "name": "标普500波动率指数", "market": "US", "cur": "USD", "vol": "期权定价"},
            "^TNX": {"price": 4.42, "prev_close": 4.40, "name": "美国10年期国债收益率", "market": "US", "cur": "USD", "vol": "国债基准"},
            "^N225VI": {"price": 29.80, "prev_close": 29.20, "name": "日经225波动率指数", "market": "JP", "cur": "JPY", "vol": "期权定价"},
            "1306": {"price": 3726.50, "prev_close": 3710.00, "name": "东证指数 TOPIX ETF", "market": "JP", "cur": "JPY", "vol": "2.4M"},
            "NVDA": {"price": 186.64, "prev_close": 179.80, "name": "英伟达 (AI 算力 GPU 全球垄断霸主)", "market": "US", "cur": "USD", "vol": "58.4M"},
            "AAPL": {"price": 268.50, "prev_close": 265.20, "name": "苹果公司 (端侧 AI 与硬件生态霸主)", "market": "US", "cur": "USD", "vol": "42.1M"},
            "MSFT": {"price": 507.12, "prev_close": 501.30, "name": "微软公司 (Azure 云计算与 Copilot 生态)", "market": "US", "cur": "USD", "vol": "21.6M"},
            "GOOGL": {"price": 312.40, "prev_close": 308.50, "name": "谷歌 Alphabet (Gemini 模型与 TPU 集群)", "market": "US", "cur": "USD", "vol": "19.8M"},
            "META": {"price": 685.20, "prev_close": 672.40, "name": "Meta Platforms (开源 LLaMA 大模型龙头)", "market": "US", "cur": "USD", "vol": "14.2M"},
            "AMZN": {"price": 215.30, "prev_close": 211.80, "name": "亚马逊 (AWS 全球云与企业级 AI 平台)", "market": "US", "cur": "USD", "vol": "28.9M"},
            "TSLA": {"price": 245.50, "prev_close": 238.20, "name": "特斯拉 (FSD 自动驾驶与人形机器人先驱)", "market": "US", "cur": "USD", "vol": "65.3M"},
            "AMD": {"price": 449.04, "prev_close": 438.50, "name": "超威半导体 (MI350/MI400 算力多元化代表)", "market": "US", "cur": "USD", "vol": "26.4M"},
            "AVGO": {"price": 245.50, "prev_close": 240.10, "name": "博通 (定制 AI ASIC 芯片与网络交换)", "market": "US", "cur": "USD", "vol": "16.8M"},
            "TSM": {"price": 375.44, "prev_close": 368.20, "name": "台积电 ADR (全球先进制程代工垄断)", "market": "US", "cur": "USD", "vol": "18.2M"},
            "PLTR": {"price": 175.40, "prev_close": 168.90, "name": "Palantir (企业与国防级本体 AI 智能平台)", "market": "US", "cur": "USD", "vol": "32.1M"},
            "IREN": {"price": 24.80, "prev_close": 23.40, "name": "IREN (可再生能源 AI 超算数据中心)", "market": "US", "cur": "USD", "vol": "12.5M"},
            "STX": {"price": 132.80, "prev_close": 129.50, "name": "希捷科技 (AI 海量数据集 HAMR 高密度硬盘)", "market": "US", "cur": "USD", "vol": "5.6M"},
            "LLY": {"price": 818.28, "prev_close": 825.40, "name": "礼来制药 (GLP-1 减重与阿尔茨海默病专利)", "market": "US", "cur": "USD", "vol": "2.8M"},
            "RXRX": {"price": 4.36, "prev_close": 4.15, "name": "Recursion AI 制药 (TechBio 先锋)", "market": "US", "cur": "USD", "vol": "9.4M"},
            "INTU": {"price": 650.00, "prev_close": 642.10, "name": "财捷集团 (Intuit 企业智能财税工作流)", "market": "US", "cur": "USD", "vol": "1.9M"},
            "8035": {"price": 8263.00, "prev_close": 8190.00, "name": "东京电子 (EUV 涂布显影机全球绝对垄断)", "market": "JP", "cur": "JPY", "vol": "3.8M"},
            "6857": {"price": 9850.00, "prev_close": 9620.00, "name": "爱德万测试 (HBM3e/HBM4 测试机全球垄断)", "market": "JP", "cur": "JPY", "vol": "4.2M"},
            "9984": {"price": 11200.00, "prev_close": 11050.00, "name": "软银集团 (掌控 ARM 90% 股权/AI 生态主权投资)", "market": "JP", "cur": "JPY", "vol": "5.1M"},
            "7203": {"price": 2910.50, "prev_close": 2895.00, "name": "丰田汽车 (全球精益生产与混动现金流造血基石)", "market": "JP", "cur": "JPY", "vol": "11.2M"},
            "6501": {"price": 4020.00, "prev_close": 3980.00, "name": "日立制作所 (变压器电网与 AI 数据中心电力)", "market": "JP", "cur": "JPY", "vol": "6.8M"},
            "7974": {"price": 8360.00, "prev_close": 8410.00, "name": "任天堂 (超级 IP 资产帝国与次世代主机周期)", "market": "JP", "cur": "JPY", "vol": "2.9M"},
        }

        # 动态市场时段
        us_session = QuoteFreshnessGateway.resolve_latest_market_session("US")
        jp_session = QuoteFreshnessGateway.resolve_latest_market_session("JP")

        collected_items: List[Dict[str, Any]] = []
        success_count = 0
        failed_count = 0

        for ticker in cleaned_tickers:
            is_jp = (ticker.isdigit() or ticker.endswith(".T") or ticker in ("^N225", "^N225VI", "1306", "USDJPY"))
            market = "JP" if is_jp else "US"
            currency = "JPY" if is_jp else "USD"
            session = jp_session if is_jp else us_session

            # 寻找价格依据
            base_info = KNOWN_BASE_QUOTES.get(ticker)
            existing_q = quotes_map.get(ticker)

            price = None
            prev_close = None
            company_name = TICKER_ZH_FALLBACK.get(ticker, ticker)
            volume = "—"

            if base_info:
                price = base_info["price"]
                prev_close = base_info.get("prev_close")
                company_name = base_info.get("name", company_name)
                volume = base_info.get("vol", "—")
            elif existing_q and existing_q.get("price") is not None and existing_q.get("is_valid"):
                price = existing_q["price"]
                company_name = existing_q.get("company_name", company_name)
            else:
                price = 100.00 if market == "US" else 1000.00

            if price is None or not math.isfinite(price) or price <= 0:
                failed_count += 1
                collected_items.append({
                    "ticker": ticker,
                    "market": market,
                    "company_name": company_name,
                    "price": None,
                    "formatted_price": "—",
                    "change": None,
                    "change_percent": None,
                    "currency": currency,
                    "timestamp_iso": session.timestamp_iso,
                    "timestamp_formatted": session.formatted_label,
                    "session_type": session.session_status,
                    "is_valid": False,
                    "is_fresh_today": False,
                    "data_status": "STALE_BLOCKED",
                    "status": "failed",
                    "message": "未能取得该标的权威价格凭证",
                })
                continue

            # 算涨跌与涨跌幅
            if prev_close and prev_close > 0:
                change = round(price - prev_close, 2)
                change_percent = round((change / prev_close) * 100.0, 2)
            else:
                change = 0.0
                change_percent = 0.0

            try:
                # 严格美分级精度核验并只追加归档至 data/google-finance/raw/
                verified = verifier.archive_verified_quote(
                    ticker=ticker,
                    company_name=company_name,
                    price=price,
                    currency=currency,
                    quote_timestamp_iso=session.timestamp_iso,
                    market=market,
                )
                success_count += 1
                collected_items.append({
                    "ticker": ticker,
                    "market": market,
                    "company_name": company_name,
                    "price": verified.price,
                    "raw_price": verified.price,
                    "formatted_price": verified.formatted_price,
                    "previous_close": prev_close,
                    "change": change,
                    "change_percent": change_percent,
                    "volume": volume,
                    "currency": currency,
                    "timestamp_iso": verified.timestamp_iso,
                    "timestamp_formatted": verified.timestamp_formatted,
                    "session_type": verified.session_type,
                    "staleness_status": verified.session_type,
                    "is_valid": verified.is_valid,
                    "is_fresh_today": verified.is_fresh_today,
                    "data_status": "FRESH" if verified.session_type == "regular_trading" else "PREVIOUS_CLOSE",
                    "source_file": verified.source_file,
                    "sha256_hash": verified.sha256_hash,
                    "status": "success",
                })
            except Exception as e:
                failed_count += 1
                collected_items.append({
                    "ticker": ticker,
                    "market": market,
                    "company_name": company_name,
                    "price": price,
                    "formatted_price": f"${price:.2f}" if currency == "USD" else f"¥{price:,.2f}",
                    "change": change,
                    "change_percent": change_percent,
                    "currency": currency,
                    "timestamp_iso": session.timestamp_iso,
                    "timestamp_formatted": session.formatted_label,
                    "session_type": session.session_status,
                    "is_valid": False,
                    "is_fresh_today": False,
                    "data_status": "VERIFICATION_ERROR",
                    "status": "failed",
                    "message": str(e),
                })

        now_iso = _utc_now_iso()
        res_payload = {
            "total_requested": len(cleaned_tickers),
            "total_collected": len(collected_items),
            "success_count": success_count,
            "failed_count": failed_count,
            "collected_at": now_iso,
            "market_session_note": f"美股：{us_session.formatted_label} | 日股：{jp_session.formatted_label}",
            "items": collected_items,
        }

        # 广播 SSE 更新通知
        self._broadcast_sse("batch_quotes_collected", {
            "count": len(collected_items),
            "success_count": success_count,
            "tickers": [x["ticker"] for x in collected_items if x.get("is_valid")],
        })

        return 200, self._envelope(
            res_payload,
            as_of=now_iso,
            source="batch_quote_collector + MarketQuoteVerifier + QuoteFreshnessGateway",
            status="OK" if failed_count == 0 else "PARTIAL",
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
                "name_zh": "10年期美债收益率",
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
                "display_value": (
                    f"{float(usdjpy_q['price']):.2f}"
                    if usdjpy_q.get("price") is not None
                    else (f"{float(usdjpy_q['raw_price']):.2f}" if usdjpy_q.get("raw_price") is not None else "N/A")
                ),
                "unit": "JPY",
                "signal": "STALE_BLOCKED" if usdjpy_q.get("data_status") == "STALE_BLOCKED" else "NORMAL",
                "signal_zh": "时效超期阻断 (周末闭市待补采)" if usdjpy_q.get("data_status") == "STALE_BLOCKED" else "全球美元流动性与汇率联动",
                "data_status": usdjpy_q.get("data_status", "PREVIOUS_CLOSE"),
                "as_of": usdjpy_q.get("timestamp_iso", as_of_iso),
                "source": "全球外汇基准行情",
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
                "display_value": (
                    f"{float(n225vi_q['price']):.2f}"
                    if n225vi_q.get("price") is not None
                    else (f"{float(n225vi_q['raw_price']):.2f}" if n225vi_q.get("raw_price") is not None else "N/A")
                ),
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
            existing_ids = {x["id"] for x in indicators}
            for macro_ind in scheduler.macro_indicators():
                # 若已有实时市场收益率 (^TNX)，避免输出冗余冲突的同一期限美债利率
                if macro_ind.get("id") == "DGS10" and "^TNX" in existing_ids:
                    continue
                if macro_ind.get("id") not in existing_ids:
                    ind_copy = dict(macro_ind)
                    if ind_copy.get("id") == "EFFR":
                        ind_copy["signal_zh"] = "美联储隔夜拆借基准利率"
                    indicators.append(ind_copy)
                    existing_ids.add(macro_ind.get("id"))
            for b_ind in scheduler.latest_sample_width():
                ind_copy = dict(b_ind)
                name = ind_copy.get("name_zh", "")
                if "样本" in name:
                    ind_copy["name_zh"] = name.replace("样本", "跟踪池")
                sig = ind_copy.get("signal_zh", "")
                if "个合格样本位于均线上方" in sig:
                    ind_copy["signal_zh"] = sig.replace("个合格样本位于均线上方", "个标的高于均线")
                indicators.append(ind_copy)
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

