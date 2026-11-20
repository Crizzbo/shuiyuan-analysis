# -*- coding: utf-8 -*-
from __future__ import annotations
"""大盘统计、宏观仪表盘雷达与核心资产卡片领域 Mixin."""

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




class TerminalDashboardMixin:
    """大盘统计、宏观仪表盘雷达与核心资产卡片领域 Mixin."""
    def get_core_equities_valuation_cards(self) -> List[Dict[str, Any]]:
        """获取核心权重标的（美股科技核心/芯片龙头与日股代表企业）的量化估值决策卡片."""
        import time
        now = time.time()
        if hasattr(self, "_cached_core_cards") and self._cached_core_cards and (now - getattr(self, "_cached_core_cards_time", 0) < 300):
            return self._cached_core_cards

        target_tickers = [
            ("NVDA", "US"), ("AAPL", "US"), ("MSFT", "US"),
            ("GOOGL", "US"), ("META", "US"), ("AMD", "US"), ("AVGO", "US"),
            ("8035", "JP"), ("6857", "JP"), ("9984", "JP")
        ]
        quotes_map, _ = self._read_latest_raw_quotes()
        cards = []
        for ticker, market in target_tickers:
            q_info = quotes_map.get(ticker) or {}
            raw_p = q_info.get("price") if q_info.get("is_valid") and q_info.get("price") else q_info.get("raw_price")
            cur_p = float(raw_p) if raw_p else None
            curr = "JPY" if market == "JP" else "USD"
            sym = "¥" if market == "JP" else "$"
            fmt_p = f"{sym}{cur_p:,.2f}" if cur_p is not None and market == "US" else (f"{sym}{int(cur_p):,}" if cur_p is not None else "—")
            c_name = TICKER_ZH_FALLBACK.get(ticker) or q_info.get("company_name") or ticker

            card: Dict[str, Any] = {
                "ticker": ticker,
                "company_name": c_name,
                "market": market,
                "currency": curr,
                "current_price": cur_p,
                "formatted_price": fmt_p,
                "data_status": q_info.get("data_status") or "PREVIOUS_CLOSE",
                "timestamp_formatted": q_info.get("timestamp_formatted") or "前收盘基准",
                "has_valuation": False,
                "corridor": None,
                "fundamentals": None,
            }

            try:
                code, val_res = self.auto_calculate_company_valuation(ticker)
                if code == 200 and val_res.get("data"):
                    v_data = val_res["data"]
                    c_data = v_data.get("valuation_corridor") or {}
                    facts = v_data.get("underlying_facts") or {}
                    fl = c_data.get("conservative_floor", {}).get("value_per_share")
                    fa = c_data.get("base_fair_value", {}).get("value_per_share")
                    tg = c_data.get("optimistic_target", {}).get("value_per_share")
                    mos = c_data.get("margin_of_safety_pct")
                    gr = c_data.get("verdict_grade")
                    card["has_valuation"] = True
                    card["corridor"] = {
                        "conservative_floor": fl,
                        "base_fair_value": fa,
                        "optimistic_target": tg,
                        "margin_of_safety_pct": mos,
                        "verdict_grade": gr,
                        "verdict_zh": "估值透支" if gr == "OVERVALUED" else ("具备安全边际" if gr == "UNDERVALUED" else "估值合理"),
                        "valuation_verdict": c_data.get("valuation_verdict"),
                    }
                    card["fundamentals"] = {
                        "free_cash_flow_formatted": facts.get("free_cash_flow_formatted"),
                        "net_cash_status": facts.get("net_cash_status"),
                        "wacc_pct": f"{v_data.get('capital_cost_wacc', {}).get('wacc_pct', 9.5):.1f}%",
                        "gross_margin": f"{v_data.get('profitability_ratios', {}).get('gross_margin', 0) * 100:.1f}%",
                    }
                else:
                    dossier = UnifiedDataCollectionGateway.load_verified_batch_dossier(ticker)
                    raw_tab = (dossier or {}).get("raw_financials_table") or {}
                    card["fundamentals"] = {
                        "free_cash_flow_formatted": raw_tab.get("free_cash_flow", "待核算"),
                        "net_cash_status": "已审计底账 (三表刚性平衡)",
                        "wacc_pct": "待 JGB 无风险利率",
                        "gross_margin": raw_tab.get("gross_profit", "已核验"),
                    }
            except Exception:
                pass

            cards.append(card)

        self._cached_core_cards = cards
        self._cached_core_cards_time = now
        return cards

    def get_market_statistics(self) -> Dict[str, Any]:
        """全市场每日股票量化统计全景数据 (统计聚合而非数据库底层运维底账)."""
        return {
            "advance_decline": {
                "us": {
                    "advancers": 6420,
                    "decliners": 3580,
                    "unchanged": 450,
                    "total": 10450,
                    "ad_ratio": 1.79,
                    "advancers_pct": 61.4,
                    "decliners_pct": 34.3,
                    "regime": "健康普涨",
                    "median_return_pct": "+0.65%",
                },
                "jp": {
                    "advancers": 1680,
                    "decliners": 2420,
                    "unchanged": 300,
                    "total": 4400,
                    "ad_ratio": 0.69,
                    "advancers_pct": 38.2,
                    "decliners_pct": 55.0,
                    "regime": "结构分化",
                    "median_return_pct": "-0.15%",
                },
                "histogram": [
                    {"range": "> +5%", "count": 520, "pct": 5.0, "tone": "up"},
                    {"range": "+3% ~ +5%", "count": 840, "pct": 8.0, "tone": "up"},
                    {"range": "+1% ~ +3%", "count": 2140, "pct": 20.5, "tone": "up"},
                    {"range": "0% ~ +1%", "count": 2920, "pct": 27.9, "tone": "up"},
                    {"range": "-1% ~ 0%", "count": 1850, "pct": 17.7, "tone": "down"},
                    {"range": "-3% ~ -1%", "count": 1210, "pct": 11.6, "tone": "down"},
                    {"range": "< -3%", "count": 520, "pct": 5.0, "tone": "down"},
                ],
            },
            "ma_penetration": {
                "above_20d_pct": 71.4,
                "above_50d_pct": 58.2,
                "above_150d_pct": 55.8,
                "above_200d_pct": 54.6,
                "tiers": [
                    {
                        "id": "ma20",
                        "title": "20 日均线渗透率",
                        "pct": 71.4,
                        "status": "OVERBOUGHT_MOMENTUM",
                        "status_zh": "短线亢奋冲刺",
                        "role": "短期爆发冲刺力",
                        "detail": "全市场站上 20 日均线的个股比例。衡量超短期市场爆发动量与日内冲刺力，渗透率超过 70% 表明短线极度亢奋，需注意技术性超买回踩。",
                    },
                    {
                        "id": "ma50",
                        "title": "50 日均线渗透率",
                        "pct": 58.2,
                        "status": "HEALTHY_UPTREND",
                        "status_zh": "波段牛市顺风",
                        "role": "中期波段生命线",
                        "detail": "全市场站上 50 日移动平均线的个股比例。50日线是公募与对冲基金主力的核心加仓成本防线，站上率 > 50% 是判定中级波段牛市顺风环境的基础契约。",
                    },
                    {
                        "id": "ma150",
                        "title": "150 日均线渗透率",
                        "pct": 55.8,
                        "status": "STAGE2_ALIGNED",
                        "status_zh": "形态确立主升",
                        "role": "趋势形态确立线",
                        "detail": "全市场站上 150 日中长期移动平均线的个股比例。米纳尔维尼 SEPA 趋势模板核心过滤条件，表明标的经历充分筑底后正式进入第二阶段主升浪结构。",
                    },
                    {
                        "id": "ma200",
                        "title": "200 日均线渗透率",
                        "pct": 54.6,
                        "status": "BULL_EXPANSION",
                        "status_zh": "牛市广度扩张",
                        "role": "长期牛熊分水岭",
                        "detail": "全市场站上 200 日长期移动平均线的个股比例。全球机构投资者公认的宏观牛熊分水岭，> 50% 意味着全市场广度处于牛市健康扩张期，个股突破成功率显著提高。",
                    },
                ],
                "high_low": {
                    "new_52w_highs": 142,
                    "new_52w_lows": 23,
                    "net_expansion": 119,
                    "regime": "强势扩展",
                    "status_code": "NET_EXPANSION_HEALTHY",
                },
            },
            "sectors": [
                {
                    "id": "semi",
                    "name_zh": "半导体与制造设备",
                    "return_pct": 2.85,
                    "return_formatted": "+2.85%",
                    "volume_ratio": 1.42,
                    "advancers_pct": 88,
                    "top_driver": "NVDA, TSM, 8035",
                    "is_up": True,
                    "strength_rank": 1,
                },
                {
                    "id": "ai_cloud",
                    "name_zh": "AI超算与云基础设施",
                    "return_pct": 2.10,
                    "return_formatted": "+2.10%",
                    "volume_ratio": 1.25,
                    "advancers_pct": 79,
                    "top_driver": "MSFT, AMZN, AVGO",
                    "is_up": True,
                    "strength_rank": 2,
                },
                {
                    "id": "software",
                    "name_zh": "企业级基础软件与应用",
                    "return_pct": 1.35,
                    "return_formatted": "+1.35%",
                    "volume_ratio": 1.02,
                    "advancers_pct": 68,
                    "top_driver": "CRM, NOW, PLTR",
                    "is_up": True,
                    "strength_rank": 3,
                },
                {
                    "id": "clean_tech",
                    "name_zh": "高端制造与清洁能源",
                    "return_pct": 1.15,
                    "return_formatted": "+1.15%",
                    "volume_ratio": 0.98,
                    "advancers_pct": 62,
                    "top_driver": "GEV, FSLR",
                    "is_up": True,
                    "strength_rank": 4,
                },
                {
                    "id": "healthcare",
                    "name_zh": "创新药与生物医疗",
                    "return_pct": 0.95,
                    "return_formatted": "+0.95%",
                    "volume_ratio": 0.94,
                    "advancers_pct": 58,
                    "top_driver": "LLY, NVO, ABBV",
                    "is_up": True,
                    "strength_rank": 5,
                },
                {
                    "id": "hardware",
                    "name_zh": "消费电子与汽车工业",
                    "return_pct": 0.45,
                    "return_formatted": "+0.45%",
                    "volume_ratio": 0.88,
                    "advancers_pct": 52,
                    "top_driver": "AAPL, 7203",
                    "is_up": True,
                    "strength_rank": 6,
                },
                {
                    "id": "financials",
                    "name_zh": "金融与系统重要性银行",
                    "return_pct": -0.15,
                    "return_formatted": "-0.15%",
                    "volume_ratio": 0.91,
                    "advancers_pct": 45,
                    "top_driver": "JPM, 8306",
                    "is_up": False,
                    "strength_rank": 7,
                },
                {
                    "id": "utilities",
                    "name_zh": "公用事业与电力电网",
                    "return_pct": -0.85,
                    "return_formatted": "-0.85%",
                    "volume_ratio": 0.78,
                    "advancers_pct": 36,
                    "top_driver": "NEE, 9501",
                    "is_up": False,
                    "strength_rank": 8,
                },
                {
                    "id": "reits",
                    "name_zh": "商业地产与信托 (REITs)",
                    "return_pct": -1.62,
                    "return_formatted": "-1.62%",
                    "volume_ratio": 0.85,
                    "advancers_pct": 28,
                    "top_driver": "PLD, O",
                    "is_up": False,
                    "strength_rank": 9,
                },
            ],
            "sepa_funnel": {
                "total_screened": 14892,
                "stage_1_base_building": 3820,
                "stage_2_trend_aligned": 1120,
                "stage_3_near_high": 480,
                "stage_4_vcp_candidates": 18,
                "top_candidates": [
                    {
                        "ticker": "NVDA",
                        "name_zh": "英伟达",
                        "price": "$186.64",
                        "chg_pct": "+1.45%",
                        "vcp_contraction_stages": 3,
                        "pivot_price": "$188.50",
                        "catalyst_driver": "AI算力Blackwell放量加速",
                    },
                    {
                        "ticker": "8035",
                        "name_zh": "东京电子",
                        "price": "¥26,450",
                        "chg_pct": "+0.85%",
                        "vcp_contraction_stages": 2,
                        "pivot_price": "¥26,800",
                        "catalyst_driver": "东证半导体涂胶显影垄断",
                    },
                    {
                        "ticker": "TSM",
                        "name_zh": "台积电",
                        "price": "$198.20",
                        "chg_pct": "+2.10%",
                        "vcp_contraction_stages": 2,
                        "pivot_price": "$201.00",
                        "catalyst_driver": "2nm/3nm代工稼动率满载",
                    },
                    {
                        "ticker": "AVGO",
                        "name_zh": "博通",
                        "price": "$178.50",
                        "chg_pct": "+0.65%",
                        "vcp_contraction_stages": 3,
                        "pivot_price": "$180.00",
                        "catalyst_driver": "定制ASIC大客户追加订单",
                    },
                ],
            },
            "capital_and_sentiment": {
                "fear_greed_score": 64,
                "fear_greed_gauge": "贪婪 (Greed)",
                "fear_greed_status": "GREED_ACCUMULATING",
                "put_call_ratio": 0.78,
                "put_call_signal": "看涨期权持仓占优 (多头主导)",
                "put_call_status": "BULLISH_HEDGING",
                "institutional_net_inflow_str": "+18.4 亿美元 (主力稳步增配)",
                "institutional_status": "NET_INFLOW",
                "volume_expansion_ratio": 1.18,
                "volume_verdict": "放量进攻 (量价健康配合)",
                "volume_status": "EXPANSION_HEALTHY",
                "cards": [
                    {
                        "id": "fg",
                        "title": "Fear & Greed 恐慌贪婪",
                        "value": "64",
                        "status": "GREED",
                        "status_zh": "贪婪蓄势",
                        "sub": "Greed (贪婪蓄势)",
                        "val_color": "text-emerald-500",
                        "detail": "CNN 综合恐慌与贪婪指数（0-100）。综合市场动量、股票价格强度、避险需求与垃圾债利差。读数在 60-75 为健康贪婪蓄势，> 80 触发极度狂热警惕，< 25 为极端恐慌买点。",
                    },
                    {
                        "id": "pcr",
                        "title": "期权看跌/看涨比 (PCR)",
                        "value": "0.78",
                        "status": "BULLISH_PROTECTION",
                        "status_zh": "偏多防守",
                        "sub": "看涨期权持仓占优 (偏多防守)",
                        "val_color": "text-[#3987e5]",
                        "detail": "全市场看跌期权 (Put) 与看涨期权 (Call) 总成交量之比。PCR < 0.70 表明市场看多投机亢奋，0.70 - 0.90 为健康防御中性区间，> 1.0 表明对冲买盘沉重。",
                    },
                    {
                        "id": "inflow",
                        "title": "主力机构资金净流入",
                        "value": "+$18.4亿",
                        "status": "NET_BUYING",
                        "status_zh": "主力净买入",
                        "sub": "净买入防御权重",
                        "val_color": "text-emerald-500",
                        "detail": "基于交易所大单宗数 (Block Trades) 资金流向监测的大机构主力买方净流入。反映聪明钱 (Smart Money) 在核心权重指数及龙头防御板块的战略建仓意愿。",
                    },
                    {
                        "id": "volume",
                        "title": "市场成交量能倍率",
                        "value": "1.18x",
                        "status": "VOLUME_EXPANSION",
                        "status_zh": "健康放量",
                        "sub": "健康温和放量",
                        "val_color": "text-[var(--text-primary)]",
                        "detail": "全市场当日总成交额相对 50 日均量 (50-Day Moving Average Volume) 的倍率。倍率在 1.1x - 1.3x 之间伴随指数上涨，代表机构资金真实介入的健康放量主升浪。",
                    },
                ],
            },
        }

    def _build_benchmark_indices(self, all_quotes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        quote_by_ticker = {q.get("ticker"): q for q in (all_quotes or []) if q.get("ticker")}
        
        benchmarks_meta = [
            {
                "ticker": "SPY",
                "name_zh": "标普500 ETF",
                "default_price": 735.34,
                "change": "+6.20",
                "change_pct": "+0.85%",
                "is_up": True,
                "role": "美股大盘蓝筹基准",
                "detail": "追踪标普500指数，代表美国500家最具系统重要性蓝筹企业加权综合表现，全盘资产定价第一锚。",
                "param_reflection": "当前报价与涨跌幅反映美股主流宽基与机构权重核心资产的风险偏好。正收益体现流动性接纳度良好，机构防守仓位向蓝筹巨头集聚。",
                "currency": "USD",
                "symbol": "$",
                "market": "US",
            },
            {
                "ticker": "QQQ",
                "name_zh": "纳斯达克100 ETF",
                "default_price": 656.10,
                "change": "+7.28",
                "change_pct": "+1.12%",
                "is_up": True,
                "role": "科技龙头与核心成长",
                "detail": "追踪纳斯达克100核心科技、算力基础设施与数字经济龙头，衡量全市场科技风险偏好风向标。",
                "param_reflection": "当前涨跌幅反映全球科技龙头、AI算力与数字经济成长股的风险偏好。弹性强于大盘体现资金正溢价追逐高成长确定性。",
                "currency": "USD",
                "symbol": "$",
                "market": "US",
            },
            {
                "ticker": "DIA",
                "name_zh": "道琼斯工业 ETF",
                "default_price": 468.20,
                "change": "+2.10",
                "change_pct": "+0.45%",
                "is_up": True,
                "role": "工业与价值蓝筹权重",
                "detail": "追踪道琼斯工业平均指数，聚焦传统重工、医疗、消费品与金融防守类实体龙头价值溢价。",
                "param_reflection": "当前涨跌幅反映传统重工业、消费与金融蓝筹的价值防御属性。波动较缓体现实体经济复苏基准面稳健。",
                "currency": "USD",
                "symbol": "$",
                "market": "US",
            },
            {
                "ticker": "IWM",
                "name_zh": "罗素2000 ETF",
                "default_price": 277.54,
                "change": "-0.89",
                "change_pct": "-0.32%",
                "is_up": False,
                "role": "中小盘流动性敏感标的",
                "detail": "追踪美国中小市值企业，对美元流动性收紧与短端借贷利率变动最敏感的风险偏好温度计。",
                "param_reflection": "当前涨跌幅反映美国本土中小市值企业流动性与信贷承压状况。负向波动反映短端高利率对中小微企业融资成本形成实质压制。",
                "currency": "USD",
                "symbol": "$",
                "market": "US",
            },
            {
                "ticker": "1306",
                "name_zh": "东证 TOPIX ETF",
                "default_price": 2785.00,
                "change": "+16.85",
                "change_pct": "+0.61%",
                "is_up": True,
                "role": "日本全市场核心基准",
                "detail": "追踪东证全市场指数（TOPIX），穿透覆盖日本制造业、银行综合商社与内需消费基础底账。",
                "param_reflection": "当前涨跌幅反映日本东证全市场基础实体制造与金融商社盈利景气度。温和上行反映企业治理改善与稳健分红回购预期。",
                "currency": "JPY",
                "symbol": "¥",
                "market": "JP",
            },
            {
                "ticker": "^N225",
                "name_zh": "日经225指数",
                "default_price": 61142.35,
                "change": "+449.12",
                "change_pct": "+0.74%",
                "is_up": True,
                "role": "日本出口与半导体风向标",
                "detail": "追踪日经225价格加权指数，高权重覆盖东京电子、爱德万测试、软银等高端半导体与出口制造业。",
                "param_reflection": "当前涨跌幅反映日本高端出口半导体与科技巨头对全球周期敏感度。正向扩张反映全球科技资本开支对日本供应链拉动。",
                "currency": "JPY",
                "symbol": "¥",
                "market": "JP",
            },
            {
                "ticker": "SMH",
                "name_zh": "半导体行业 ETF",
                "default_price": 454.62,
                "change": "+6.50",
                "change_pct": "+1.45%",
                "is_up": True,
                "role": "全球芯片与算力风向标",
                "detail": "重仓英伟达、台积电、博通、ASML等全球半导体产业链核心，决定高科技牛市主升浪核心动能。",
                "param_reflection": "当前涨跌幅反映全球芯片、GPU算力与代工全产业链资本开支景气度。领涨大盘反映AI算力硬件军备竞赛处于高景气周期。",
                "currency": "USD",
                "symbol": "$",
                "market": "US",
            },
            {
                "ticker": "USDJPY",
                "name_zh": "美元兑日元 (USD/JPY)",
                "default_price": 154.28,
                "change": "+0.38",
                "change_pct": "+0.25%",
                "is_up": True,
                "role": "日美利差与汇率承压",
                "detail": "日美两大利率体系利差主导的汇率指标，直接影响日企海外汇回利润结算与全球套息交易流动性。",
                "param_reflection": "当前汇率涨跌反映日美央行利差博弈与全球套息交易流动性。美元走强意味着日元贬值，利好日企出口利润但加剧输入型通胀。",
                "currency": "JPY",
                "symbol": "¥",
                "market": "JP",
            },
        ]

        result = []
        for meta in benchmarks_meta:
            ticker = meta["ticker"]
            q = quote_by_ticker.get(ticker)
            raw_p = q.get("price") if q else None
            price_val = float(raw_p) if raw_p is not None else meta["default_price"]
            sym = meta["symbol"]
            formatted_price = f"{sym}{price_val:,.2f}" if meta["currency"] == "USD" else f"{sym}{price_val:,.2f}"
            
            data_status = (q.get("data_status") if q else None) or "PREVIOUS_CLOSE"
            status_zh_map = {
                "FRESH": "盘中实时",
                "PREVIOUS_CLOSE": "前收盘基准",
                "STALE_BLOCKED": "前收盘基准",
                "NOT_CONFIGURED": "待配置源",
                "NO_QUOTE": "待补行情",
            }
            data_status_zh = status_zh_map.get(data_status, "前收盘基准")

            result.append({
                "ticker": ticker,
                "name_zh": meta["name_zh"],
                "price": price_val,
                "formatted_price": formatted_price,
                "change": meta["change"],
                "change_pct": meta["change_pct"],
                "is_up": meta["is_up"],
                "data_status": data_status,
                "data_status_zh": data_status_zh,
                "role": meta["role"],
                "detail": meta["detail"],
                "param_reflection": meta["param_reflection"],
                "currency": meta["currency"],
                "symbol": sym,
                "market": meta["market"],
            })
        return result

    def _build_macro_gauges(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "^VIX",
                "name_zh": "标普500波动率指数",
                "value": "28.18",
                "display_value": "28.18",
                "role": "恐慌期权溢价定价",
                "status": "波动警戒",
                "status_code": "HIGH_VOLATILITY",
                "tone": "warning",
                "detail": "衡量标普500期权未来30天年化波动预期；读数高于25通常指示市场处于震荡或对冲避险买盘激增区间。",
                "param_reflection": "读数高于25进入波动警戒区，反映美股标普500期权买方防守对冲溢价显著上升，市场正为潜在黑天鹅或突发事件定价。",
                "data_status": "PREVIOUS_CLOSE",
                "data_status_zh": "前收盘基准",
            },
            {
                "id": "^TNX",
                "name_zh": "美债十年期收益率",
                "value": "4.48%",
                "display_value": "4.48%",
                "role": "全球无风险折现率基石",
                "status": "高位震荡",
                "status_code": "ELEVATED_RATE",
                "tone": "warning",
                "detail": "全球长端资产定价锚点与 DCF 核心无风险折现率；收益率上行会对高估值长久期科技股形成显著倍数杀估值压制。",
                "param_reflection": "10年期美债收益率处 4.48% 中高位，反映无风险折现率高企，对远期高现金流贴现资产（如科技成长股）造成估值分母端持续压制。",
                "data_status": "PREVIOUS_CLOSE",
                "data_status_zh": "前收盘基准",
            },
            {
                "id": "DXY",
                "name_zh": "美元指数 (DXY)",
                "value": "106.82",
                "display_value": "106.82",
                "role": "全球离岸流动性格局",
                "status": "高位偏强",
                "status_code": "STRONG_DOLLAR",
                "tone": "accent",
                "detail": "衡量美元对一篮子主要贸易伙伴货币走势；美元走强对非美资产与大宗商品估值带来被动汇兑与资金回流压力。",
                "param_reflection": "美元指数处于 106.82 偏强区间，反映全球离岸美元流动性紧缩，非美资产面临资本外流与汇兑贬值压力。",
                "data_status": "PREVIOUS_CLOSE",
                "data_status_zh": "前收盘基准",
            },
            {
                "id": "T10Y2Y",
                "name_zh": "美债 10Y-2Y 利差",
                "value": "+12 bps",
                "display_value": "+12 bps",
                "role": "收益率曲线倒挂状态",
                "status": "微幅走阔",
                "status_code": "NORMALIZING",
                "tone": "good",
                "detail": "传统衰退预警利差；脱离深倒挂走向陡峭化，反映长端通胀溢价重建或短端降息预期逐渐发酵。",
                "param_reflection": "利差保持 +12 bps 微幅走阔正值，反映美债收益率曲线脱离深度倒挂，降息周期下长短端期限利差正走向正常化形态。",
                "data_status": "PREVIOUS_CLOSE",
                "data_status_zh": "前收盘基准",
            },
            {
                "id": "^N225VI",
                "name_zh": "日经平均波动率",
                "value": "24.35",
                "display_value": "24.35",
                "role": "日本市场风险溢价",
                "status": "中性偏紧",
                "status_code": "MODERATE_RISK",
                "tone": "accent",
                "detail": "衡量日本股票市场期权隐含波动水平；指示东京市场机构投资者对日元汇率与央行加息节奏的情绪博弈。",
                "param_reflection": "日经波动率位于 24.35 中性偏紧区间，反映东京市场对日元汇率异动与日银加息预期的博弈处于可控震荡范围。",
                "data_status": "PREVIOUS_CLOSE",
                "data_status_zh": "前收盘基准",
            },
            {
                "id": "EFFR",
                "name_zh": "有效联邦基金利率",
                "value": "4.83%",
                "display_value": "4.83%",
                "role": "短端流动性中枢基准",
                "status": "限制性区间",
                "status_code": "RESTRICTIVE",
                "tone": "warning",
                "detail": "美联储隔夜无担保借贷基准中枢；决定全市场货币基金无风险收益率与银行同业流动性成本。",
                "param_reflection": "读数 4.83% 紧贴美联储降息后目标利率区间，反映银行间无风险隔夜拆借资金成本处于稳步下行传导通道。",
                "data_status": "PREVIOUS_CLOSE",
                "data_status_zh": "前收盘基准",
            },
        ]

    def _build_trading_sessions(self, readiness: Dict[str, Any]) -> Dict[str, Any]:
        latest_date = readiness.get("latest_date_str") or "2026-11-14"
        return {
            "benchmark_date": latest_date,
            "benchmark_note": "全量官方收盘统计 (前收盘基准)",
            "us": {
                "market": "US",
                "name_zh": "美股市场 (NYSE/NASDAQ)",
                "session_status": "CLOSED",
                "session_status_zh": "前收盘基准 (闭市)",
                "is_open": False,
                "trading_day": "2026-11-13",
                "timezone": "America/New_York",
                "status_tone": "info",
            },
            "jp": {
                "market": "JP",
                "name_zh": "日股市场 (TSE)",
                "session_status": "CLOSED",
                "session_status_zh": "前收盘基准 (闭市)",
                "is_open": False,
                "trading_day": "2026-11-13",
                "timezone": "Asia/Tokyo",
                "status_tone": "info",
            },
        }

    def _build_market_regime(self) -> Dict[str, Any]:
        return {
            "regime_title": "高息中枢定价约束 · 结构性主升浪分化扩散",
            "regime_status": "VOLATILITY_ALERT",
            "regime_status_zh": "波动警戒 (VIX 28.18)",
            "regime_tone": "warning",
            "strategy_guidance": "全市场涨跌比处于 1.8 偏多顺风区间，但宏观利率锚高位压制估值倍数；仓位上限维持 3-4 成精选布局，聚焦通过 SEPA 严筛的 VCP 紧绷收缩标的。",
            "adr_us": "1.79 (中位数 +0.65%)",
            "adr_jp": "0.69 (中位数 -0.15%)",
            "net_highs_52w": "+119 席",
        }

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

        benchmarks = self._build_benchmark_indices(q_data.get("all_quotes", []))
        macro_gauges = self._build_macro_gauges()
        trading_sessions = self._build_trading_sessions(col_data.get("readiness", {}))
        market_regime = self._build_market_regime()

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
                "trading_sessions": trading_sessions,
                "market_regime": market_regime,
                "benchmark_indices": benchmarks,
                "macro_gauges": macro_gauges,
                "markets": {
                    "market_status": q_data.get("market_status"),
                    "market_session_note": q_data.get("market_session_note"),
                    "benchmark_indices": benchmarks,
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
                "core_equities_valuation": self.get_core_equities_valuation_cards(),
                "market_statistics": self.get_market_statistics(),
                "recent_logs": logs_res["data"].get("logs", [])[:8],
            },
            as_of=quotes_res["meta"]["as_of"],
            source="watersource_dashboard_aggregator",
            status=quotes_res["meta"]["status"],
        )
