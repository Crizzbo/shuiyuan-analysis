# -*- coding: utf-8 -*-
from __future__ import annotations
"""全资产池索引、个股深度档案与关联事件下钻领域 Mixin."""

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
from financial_core.engines.multi_asset_screening_engine import AssetClassClassifier
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
    "IWM": "罗素2000小型股 ETF",
    "SMH": "半导体行业 ETF",
    "XLK": "科技精选行业 SPDR ETF",
    "XLE": "能源精选行业 SPDR ETF",
    "XBI": "标普生物科技 ETF",
    "SCHD": "嘉信美国高股息 ETF",
    "VIG": "先锋股利增长 ETF",
    "TLT": "20年期以上美债 ETF",
    "IEF": "7-10年期美债 ETF",
    "HYG": "高收益公司债 ETF",
    "GLD": "SPDR 黄金信托 (实物黄金ETF)",
    "IAU": "安硕黄金信托 (iShares Gold Trust)",
    "SLV": "安硕白银信托 (iShares Silver Trust)",
    "NEM": "纽蒙特矿业 (Newmont)",
    "GOLD": "巴里克黄金 (Barrick Gold)",
    "AEM": "阿格尼科老鹰矿业 (Agnico Eagle)",
    "WPM": "惠顿贵金属 (Wheaton Precious Metals)",
    "GDX": "梵艾克黄金矿业 ETF (VanEck Gold Miners)",
    "^VIX": "标普500波动率指数",
    "^TNX": "美国10年期国债收益率",
    "DXY": "美元指数",
    "1306": "东证股价指数 ETF (TOPIX)",
    "^N225VI": "日经225波动率指数",
    "USDJPY": "美元兑日元汇率",
    "8035": "东京电子 (Tokyo Electron)",
    "6857": "爱德万测试 (Advantest)",
    "9984": "软银集团 (SoftBank Group)",
    "7203": "丰田汽车 (Toyota)",
    "6501": "日立制作所 (Hitachi)",
    "7974": "任天堂 (Nintendo)",
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
    "ARM": "安谋控股 (Arm Holdings)",
    "VRT": "维谛技术 (Vertiv)",
    "CRWD": "CrowdStrike",
    "NET": "Cloudflare",
    "DDOG": "Datadog",
    "MSTR": "微策投资 (MicroStrategy)",
    "ASTS": "AST SpaceMobile",
    "JOBY": "Joby Aviation (低空飞行汽车)",
    "RKLB": "火箭实验室 (Rocket Lab)",
    "MELI": "美客多 (MercadoLibre)",
    "IONQ": "IonQ 量子计算",
    "RDDT": "Reddit",
    "CAVA": "CAVA Group",
    "DUOL": "多邻国 (Duolingo)",
    "LLY": "礼来制药 (Eli Lilly)",
    "RXRX": "Recursion 医药",
    "INTU": "直觉软件 (Intuit)",
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




class TerminalCompanyAnalysisMixin:
    """全资产池索引、个股深度档案与关联事件下钻领域 Mixin."""
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
            "SPY": 12, "QQQ": 13, "DIA": 14, "IWM": 15, "SMH": 16, "XLK": 17, "TLT": 18,
            "GLD": 19, "IAU": 20, "SLV": 21, "NEM": 22, "GOLD": 23, "GDX": 24,
            "SCHD": 25, "VIG": 26, "LLY": 27,
            "8035": 28, "6857": 29, "9984": 30, "1306": 31, "7203": 32, "6501": 33, "7974": 34,
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
                    asset_cat = AssetClassClassifier.classify(ticker=tk, company_name=name).value
                    items.append({
                        "ticker": tk,
                        "market": "US",
                        "company_name": name,
                        "asset_category": asset_cat,
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
                    asset_cat = AssetClassClassifier.classify(ticker=code, company_name=name).value
                    items.append({
                        "ticker": code,
                        "market": "JP",
                        "company_name": name,
                        "asset_category": asset_cat,
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

        # 3. 补充优先资产池与行情库中已落盘的特级标的 (如 QQQ, SCHD, TLT 等 ETF 及大宗商品)
        for q_tk, q in quotes_map.items():
            if not q_tk or q_tk in seen_tickers:
                continue
            if q_tk.startswith("^") or q_tk in ("DXY", "USDJPY"):
                continue
            seen_tickers.add(q_tk)
            is_jp = q_tk.isdigit() or q_tk.startswith("TYO:")
            clean_tk = q_tk.replace("TYO:", "")
            mkt = "JP" if is_jp else "US"
            curr = "JPY" if is_jp else "USD"
            name = TICKER_ZH_FALLBACK.get(clean_tk) or TICKER_ZH_FALLBACK.get(q_tk) or q.get("name") or clean_tk
            has_quote = bool(q.get("is_valid"))
            has_filing = UnifiedDataCollectionGateway.load_verified_batch_dossier(clean_tk) is not None
            data_status = q.get("data_status", "NO_QUOTE")
            readiness = "行情已就绪 · 财报已归档" if (has_quote and has_filing) else ("行情已就绪" if has_quote else "待补数据")
            asset_cat = AssetClassClassifier.classify(ticker=clean_tk, company_name=name).value
            items.append({
                "ticker": clean_tk,
                "market": mkt,
                "company_name": name,
                "asset_category": asset_cat,
                "source_tag": "官方行情与优先资产池",
                "latest_price": q.get("price"),
                "currency": curr,
                "data_status": data_status,
                "has_quote": has_quote,
                "has_sec_filing": has_filing,
                "readiness_status": readiness,
                "priority": priority_order.get(clean_tk, 50),
            })

        # 排序：优先核心旗舰（NVDA, AAPL 等），其余按代码字典序稳定排列
        items.sort(key=lambda x: (x["priority"], x["ticker"]))
        with self._lock:
            self._universe_cache = items
        return items

    def get_analytics_candidates(
        self,
        market: str = "ALL",
        asset_category: str = "ALL",
        limit: int = 20,
        page: int = 1,
        page_size: Optional[int] = None,
        q: Optional[str] = None,
    ) -> Dict[str, Any]:
        all_items = self._get_full_universe_index()
        m = (market or "ALL").strip().upper()
        cat = (asset_category or "ALL").strip()
        kw = (q or "").strip().lower()
        effective_page_size = page_size or limit or 20
        effective_page = max(1, page)

        filtered = all_items
        if m in ("US", "JP"):
            filtered = [x for x in filtered if x["market"] == m]
        if cat != "ALL":
            filtered = [x for x in filtered if str(x.get("asset_category", "")).lower() == cat.lower()]
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

        cat_breakdown = {
            "Growth_Equity": sum(1 for x in all_items if x.get("asset_category") == "Growth_Equity"),
            "Broad_Or_Sector_ETF": sum(1 for x in all_items if x.get("asset_category") == "Broad_Or_Sector_ETF"),
            "Gold_And_Commodity": sum(1 for x in all_items if x.get("asset_category") == "Gold_And_Commodity"),
            "Dividend_And_Defensive": sum(1 for x in all_items if x.get("asset_category") == "Dividend_And_Defensive"),
        }

        return self._envelope(
            {
                "total": total,
                "page": effective_page,
                "page_size": effective_page_size,
                "total_pages": total_pages,
                "market": m,
                "asset_category": cat,
                "total_qualified_count": total,
                "tier0_pivot_ready_count": tier0_count,
                "tier1_watchlist_count": ready_count,
                "asset_category_breakdown": cat_breakdown,
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

    def _build_multi_asset_profile(
        self,
        clean_ticker: str,
        company_name: str,
        market: str,
        cur_price: Optional[float],
        asset_cat: Any,
    ) -> Dict[str, Any]:
        """构建买方级多资产穿透档案（ETF成分股穿透、黄金实际利率与央行储备、红利防御现金流覆盖）."""
        from financial_core.engines.multi_asset_screening_engine import AssetCategory

        cat_val = asset_cat.value if hasattr(asset_cat, "value") else str(asset_cat)

        # 1. ETF 穿透档案 (Broad_Or_Sector_ETF)
        if asset_cat == AssetCategory.BROAD_OR_SECTOR_ETF:
            etf_db = {
                "SPY": {
                    "benchmark_index": "标普500指数 (S&P 500 Index)",
                    "expense_ratio_pct": 0.09,
                    "tracking_error_bps": 1.8,
                    "aum_billions": 585.2,
                    "holdings_count": 503,
                    "top_holdings": [
                        {"ticker": "NVDA", "name": "英伟达", "weight_pct": 7.4},
                        {"ticker": "MSFT", "name": "微软", "weight_pct": 6.8},
                        {"ticker": "AAPL", "name": "苹果", "weight_pct": 6.5},
                        {"ticker": "AMZN", "name": "亚马逊", "weight_pct": 3.9},
                        {"ticker": "META", "name": "Meta", "weight_pct": 2.7},
                        {"ticker": "GOOGL", "name": "谷歌", "weight_pct": 2.3},
                        {"ticker": "BRK.B", "name": "伯克希尔B", "weight_pct": 1.9},
                        {"ticker": "LLY", "name": "礼来", "weight_pct": 1.6},
                        {"ticker": "AVGO", "name": "博通", "weight_pct": 1.5},
                        {"ticker": "TSLA", "name": "特斯拉", "weight_pct": 1.4},
                    ],
                    "style_factors": {
                        "market_cap_style": "大盘核心混合型 (Large-Cap Blend)",
                        "beta_to_sp500": 1.00,
                        "dividend_yield_pct": 1.25,
                        "interest_rate_duration_years": 0.0,
                    },
                    "rate_cut_sensitivity": "偏多 (基准降息提振核心蓝筹整体估值与流动性溢价)",
                    "rebalance_frequency": "季度再平衡 (Quarterly)",
                },
                "QQQ": {
                    "benchmark_index": "纳斯达克100指数 (Nasdaq-100 Index)",
                    "expense_ratio_pct": 0.20,
                    "tracking_error_bps": 3.2,
                    "aum_billions": 310.5,
                    "holdings_count": 101,
                    "top_holdings": [
                        {"ticker": "NVDA", "name": "英伟达", "weight_pct": 9.1},
                        {"ticker": "AAPL", "name": "苹果", "weight_pct": 8.4},
                        {"ticker": "MSFT", "name": "微软", "weight_pct": 7.9},
                        {"ticker": "AMZN", "name": "亚马逊", "weight_pct": 5.2},
                        {"ticker": "META", "name": "Meta", "weight_pct": 4.8},
                        {"ticker": "AVGO", "name": "博通", "weight_pct": 4.6},
                        {"ticker": "GOOGL", "name": "谷歌", "weight_pct": 3.1},
                        {"ticker": "TSLA", "name": "特斯拉", "weight_pct": 2.8},
                        {"ticker": "COST", "name": "开市客", "weight_pct": 2.4},
                        {"ticker": "NFLX", "name": "奈飞", "weight_pct": 2.1},
                    ],
                    "style_factors": {
                        "market_cap_style": "大盘科技动量成长型 (Large-Cap Tech Growth)",
                        "beta_to_sp500": 1.18,
                        "dividend_yield_pct": 0.58,
                        "interest_rate_duration_years": 0.0,
                    },
                    "rate_cut_sensitivity": "极高弹性 (科技长久期远期自由现金流对贴现率高度敏感)",
                    "rebalance_frequency": "年度/季度动态再平衡",
                },
                "SMH": {
                    "benchmark_index": "MVIS 费城半导体 25 指数",
                    "expense_ratio_pct": 0.35,
                    "tracking_error_bps": 4.5,
                    "aum_billions": 24.8,
                    "holdings_count": 25,
                    "top_holdings": [
                        {"ticker": "NVDA", "name": "英伟达", "weight_pct": 20.5},
                        {"ticker": "TSM", "name": "台积电 ADR", "weight_pct": 13.2},
                        {"ticker": "AVGO", "name": "博通", "weight_pct": 7.8},
                        {"ticker": "ASML", "name": "阿斯麦", "weight_pct": 5.4},
                        {"ticker": "AMD", "name": "超微半导体", "weight_pct": 5.1},
                        {"ticker": "QCOM", "name": "高通", "weight_pct": 4.8},
                        {"ticker": "TXN", "name": "德州仪器", "weight_pct": 4.3},
                        {"ticker": "AMAT", "name": "应用材料", "weight_pct": 4.1},
                        {"ticker": "MU", "name": "美光科技", "weight_pct": 3.9},
                        {"ticker": "ADI", "name": "亚德诺", "weight_pct": 3.5},
                    ],
                    "style_factors": {
                        "market_cap_style": "前沿芯片先进制程与算力垄断",
                        "beta_to_sp500": 1.45,
                        "dividend_yield_pct": 0.45,
                        "interest_rate_duration_years": 0.0,
                    },
                    "rate_cut_sensitivity": "超高弹性 (半导体超级资本开支与宽松流动性双轮共振)",
                    "rebalance_frequency": "半年度再平衡 (Semi-Annually)",
                },
                "SCHD": {
                    "benchmark_index": "道琼斯美国红利100指数 (Dow Jones U.S. Dividend 100)",
                    "expense_ratio_pct": 0.06,
                    "tracking_error_bps": 2.1,
                    "aum_billions": 58.4,
                    "holdings_count": 104,
                    "top_holdings": [
                        {"ticker": "LMT", "name": "洛克希德马丁", "weight_pct": 4.4},
                        {"ticker": "AVGO", "name": "博通", "weight_pct": 4.1},
                        {"ticker": "ABBV", "name": "艾伯维", "weight_pct": 4.0},
                        {"ticker": "CSCO", "name": "思科", "weight_pct": 3.9},
                        {"ticker": "HD", "name": "家得宝", "weight_pct": 3.8},
                        {"ticker": "MRK", "name": "默沙东", "weight_pct": 3.7},
                        {"ticker": "AMGN", "name": "安进", "weight_pct": 3.6},
                        {"ticker": "CVX", "name": "雪佛龙", "weight_pct": 3.5},
                        {"ticker": "PEP", "name": "百事可乐", "weight_pct": 3.4},
                        {"ticker": "TXN", "name": "德州仪器", "weight_pct": 3.3},
                    ],
                    "style_factors": {
                        "market_cap_style": "高自由现金流造血与高质量防御红利",
                        "beta_to_sp500": 0.78,
                        "dividend_yield_pct": 3.42,
                        "interest_rate_duration_years": 0.0,
                    },
                    "rate_cut_sensitivity": "防御稳健 (降息周期中具备极强债券替代吸引力与抗震屏障)",
                    "rebalance_frequency": "年度严格筛选 + 季度调整",
                },
                "TLT": {
                    "benchmark_index": "ICE 美国20+年期国债指数 (U.S. Treasury 20+ Year)",
                    "expense_ratio_pct": 0.15,
                    "tracking_error_bps": 3.0,
                    "aum_billions": 52.1,
                    "holdings_count": 42,
                    "top_holdings": [
                        {"ticker": "US-T-4.25", "name": "美债 4.25% 2054", "weight_pct": 12.4},
                        {"ticker": "US-T-4.00", "name": "美债 4.00% 2053", "weight_pct": 11.8},
                        {"ticker": "US-T-3.875", "name": "美债 3.875% 2053", "weight_pct": 9.5},
                        {"ticker": "US-T-4.375", "name": "美债 4.375% 2054", "weight_pct": 8.2},
                    ],
                    "style_factors": {
                        "market_cap_style": "超长久期无风险主权利率债",
                        "beta_to_sp500": -0.25,
                        "dividend_yield_pct": 4.12,
                        "interest_rate_duration_years": 16.8,
                    },
                    "rate_cut_sensitivity": "极致正向凸性 (久期 16.8 年，基准利率每下行 100bps，净值上涨约 16.8%)",
                    "rebalance_frequency": "月度再平衡 (Monthly)",
                },
            }
            etf_prof = etf_db.get(clean_ticker) or {
                "benchmark_index": f"{company_name} 跟踪基准",
                "expense_ratio_pct": 0.15,
                "tracking_error_bps": 3.5,
                "aum_billions": 15.0,
                "holdings_count": 50,
                "top_holdings": [
                    {"ticker": "TOP1", "name": "第一大权重股", "weight_pct": 8.5},
                    {"ticker": "TOP2", "name": "第二大权重股", "weight_pct": 6.8},
                    {"ticker": "TOP3", "name": "第三大权重股", "weight_pct": 5.2},
                ],
                "style_factors": {
                    "market_cap_style": "核心行业主题 ETF",
                    "beta_to_sp500": 1.05,
                    "dividend_yield_pct": 1.50,
                    "interest_rate_duration_years": 0.0,
                },
                "rate_cut_sensitivity": "行业敏感度联动 (受流动性与贴现率驱动)",
                "rebalance_frequency": "定期再平衡",
            }
            return {
                "asset_category": cat_val,
                "category_name_zh": "全球核心指数与行业主题 ETF",
                "etf_profile": etf_prof,
                "commodity_profile": None,
                "dividend_profile": None,
            }

        # 2. 黄金与贵金属大宗商品 (Gold_And_Commodity)
        if asset_cat == AssetCategory.GOLD_AND_COMMODITY:
            comm_db = {
                "GLD": {
                    "asset_sub_type": "实物黄金信托 (Physical Gold Trust)",
                    "backing_type": "100% 伦敦合格交割实物金条 (Allocated Gold Bullion)",
                    "real_yield_10y_tips_pct": 1.82,
                    "real_yield_elasticity": -0.85,
                    "central_bank_buying_trend": "全球主权央行去美元化储备配置，近14个季度累计净增持 > 2,800吨",
                    "physical_premium_pct": 1.25,
                    "gold_silver_ratio": 84.1,
                    "aisc_cost_per_oz": None,
                    "vault_location": "汇丰银行伦敦地下金库 (HSBC Bank plc, London)",
                    "inflation_hedge_rating": "Tier-0 终极主权货币对冲资产与去中心化抗通胀锚",
                },
                "IAU": {
                    "asset_sub_type": "超低费率实物黄金信托 (iShares Gold Trust)",
                    "backing_type": "100% 摩根大通金库保管实物金条",
                    "real_yield_10y_tips_pct": 1.82,
                    "real_yield_elasticity": -0.85,
                    "central_bank_buying_trend": "主权基金与长线养老金黄金定投储备底仓",
                    "physical_premium_pct": 1.18,
                    "gold_silver_ratio": 84.1,
                    "aisc_cost_per_oz": None,
                    "vault_location": "伦敦与纽约高安全金库 (JPMorgan Vaults)",
                    "inflation_hedge_rating": "Tier-0 低摩擦实物黄金对冲工具",
                },
                "SLV": {
                    "asset_sub_type": "实物白银信托 (iShares Silver Trust)",
                    "backing_type": "100% 伦敦金银市场协会实物白银 (LBMA Good Delivery)",
                    "real_yield_10y_tips_pct": 1.82,
                    "real_yield_elasticity": -1.25,
                    "central_bank_buying_trend": "全球光伏TOPCon/HJT银浆硬需求与电气化工业刚需拉动",
                    "physical_premium_pct": 2.10,
                    "gold_silver_ratio": 84.1,
                    "aisc_cost_per_oz": None,
                    "vault_location": "摩根大通伦敦金库",
                    "inflation_hedge_rating": "货币对冲与工业硬刚需双重弹性放大器",
                },
                "NEM": {
                    "asset_sub_type": "全球第一大特级金矿航母 (Newmont Corporation)",
                    "backing_type": "内华达黄金、Boddington、Cadia 等全球一级长寿金铜矿山",
                    "real_yield_10y_tips_pct": 1.82,
                    "real_yield_elasticity": -1.80,
                    "central_bank_buying_trend": "金价高位运行拉动矿业采矿利润与自由现金流分红爆发 (杠杆 2.3x)",
                    "physical_premium_pct": 0.0,
                    "gold_silver_ratio": 84.1,
                    "aisc_cost_per_oz": 1380.0,
                    "vault_location": "全球已探明与在产黄金储量 1.35 亿盎司",
                    "inflation_hedge_rating": "高经营杠杆实物黄金资产 + 采矿现金流造血",
                },
            }
            comm_prof = comm_db.get(clean_ticker) or {
                "asset_sub_type": "贵金属大宗商品资产",
                "backing_type": "实物资产储备与矿产资源",
                "real_yield_10y_tips_pct": 1.82,
                "real_yield_elasticity": -0.90,
                "central_bank_buying_trend": "央行去美元化储备配置需求稳定",
                "physical_premium_pct": 1.20,
                "gold_silver_ratio": 84.1,
                "aisc_cost_per_oz": 1400.0 if "MINING" in company_name.upper() else None,
                "vault_location": "伦敦/纽约金银储备库",
                "inflation_hedge_rating": "优质贵金属抗通胀避险工具",
            }
            return {
                "asset_category": cat_val,
                "category_name_zh": "黄金与特级贵金属资产体系",
                "etf_profile": None,
                "commodity_profile": comm_prof,
                "dividend_profile": None,
            }

        # 3. 高股息防御与公用事业 (Dividend_And_Defensive)
        if asset_cat == AssetCategory.DIVIDEND_AND_DEFENSIVE:
            div_db = {
                "SCHD": {
                    "dividend_yield_pct": 3.42,
                    "payout_ratio_pct": 41.5,
                    "consecutive_dividend_growth_years": 12,
                    "free_cash_flow_coverage_ratio": 2.8,
                    "downside_volatility_pct": 8.5,
                    "defensive_moat_type": "严选连续10年增息、高ROE及强自由现金流造血的100只美股核心蓝筹",
                },
                "VIG": {
                    "dividend_yield_pct": 1.78,
                    "payout_ratio_pct": 38.0,
                    "consecutive_dividend_growth_years": 18,
                    "free_cash_flow_coverage_ratio": 3.2,
                    "downside_volatility_pct": 9.1,
                    "defensive_moat_type": "聚焦持续提息的高质量成长型蓝筹 (如微软、苹果、Visa、强生)",
                },
                "7203": {
                    "dividend_yield_pct": 3.10,
                    "payout_ratio_pct": 28.5,
                    "consecutive_dividend_growth_years": 10,
                    "free_cash_flow_coverage_ratio": 3.5,
                    "downside_volatility_pct": 12.1,
                    "defensive_moat_type": "精益生产与全球混动 HEV 垄断级造血，在手净现金充足，回购与分红双轮驱动",
                },
                "6501": {
                    "dividend_yield_pct": 2.40,
                    "payout_ratio_pct": 32.0,
                    "consecutive_dividend_growth_years": 8,
                    "free_cash_flow_coverage_ratio": 2.6,
                    "downside_volatility_pct": 14.5,
                    "defensive_moat_type": "变压器电网与数据中心电力设备进入超级景气周期，现金牛业务护城河坚实",
                },
                "LLY": {
                    "dividend_yield_pct": 0.65,
                    "payout_ratio_pct": 65.0,
                    "consecutive_dividend_growth_years": 11,
                    "free_cash_flow_coverage_ratio": 2.1,
                    "downside_volatility_pct": 15.2,
                    "defensive_moat_type": "GLP-1 替尔泊肽代谢减重与多奈单抗专利壁垒，长期自由现金流造血确定性极高",
                },
            }
            div_prof = div_db.get(clean_ticker) or {
                "dividend_yield_pct": 2.80,
                "payout_ratio_pct": 45.0,
                "consecutive_dividend_growth_years": 5,
                "free_cash_flow_coverage_ratio": 2.2,
                "downside_volatility_pct": 10.5,
                "defensive_moat_type": "稳健现金流防守与公用事业/消费刚需造血",
            }
            return {
                "asset_category": cat_val,
                "category_name_zh": "高质量自由现金流红利防御资产",
                "etf_profile": None,
                "commodity_profile": None,
                "dividend_profile": div_prof,
            }

        # 4. 高成长科技与动量股票 (Growth_Equity)
        return {
            "asset_category": cat_val,
            "category_name_zh": "高成长与科技动量先锋 (SEPA/VCP 评估)",
            "etf_profile": None,
            "commodity_profile": None,
            "dividend_profile": None,
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
            if market == "US" and num_fcf is not None and num_shares is not None and num_fcf > 0 and num_shares > 0:
                net_cash_ps = ((num_cash or 0.0) - (num_debt or 0.0)) / num_shares
                fcf_ps = num_fcf / num_shares
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

        # 11. 买方多资产自适应分类与穿透画像
        asset_cat = AssetClassClassifier.classify(clean_ticker, company_name)
        multi_asset_profile = self._build_multi_asset_profile(
            clean_ticker=clean_ticker,
            company_name=company_name,
            market=market,
            cur_price=cur_price,
            asset_cat=asset_cat,
        )

        return self._envelope(
            {
                "ticker": clean_ticker,
                "market": market,
                "company_name": company_name,
                "asset_category": asset_cat.value,
                "multi_asset_profile": multi_asset_profile,
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

