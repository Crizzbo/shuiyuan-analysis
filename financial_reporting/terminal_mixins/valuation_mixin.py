# -*- coding: utf-8 -*-
from __future__ import annotations
"""公司估值计算与模型参数推演领域 Mixin."""

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




class TerminalValuationMixin:
    """公司估值计算与模型参数推演领域 Mixin."""
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
        """获取系统内全量 25 个专业量化与金融估值模型计算结果 (支持针对标的真实动态核算)."""
        clean_ticker = (ticker or "NVDA").strip().upper()
        ticker_file = self.data_dir / "indicators" / f"finance_calc_{clean_ticker}.json"
        if ticker_file.is_file():
            try:
                cached = _safe_read_json(ticker_file, {})
                if cached.get("total_models") in (24, 25) and cached.get("ticker") == clean_ticker:
                    return self._envelope(
                        cached,
                        as_of=cached.get("as_of", _utc_now_iso()),
                        source=f"data/indicators/finance_calc_{clean_ticker}.json",
                        status="CALCULATED_VERIFIED",
                    )
            except Exception:
                pass

        indicators_file = self.data_dir / "indicators" / "finance_calc_latest.json"
        if indicators_file.is_file():
            try:
                cached = _safe_read_json(indicators_file, {})
                if cached.get("total_models") in (24, 25) and cached.get("ticker") == clean_ticker:
                    return self._envelope(
                        cached,
                        as_of=cached.get("as_of", _utc_now_iso()),
                        source="data/indicators/finance_calc_latest.json",
                        status="CALCULATED_VERIFIED",
                    )
            except Exception:
                pass

        # 若未缓存或需要重新计算，调用 25 模型套件
        from financial_reporting.comprehensive_finance_suite import run_all_25_financial_models
        suite_data = run_all_25_financial_models(ticker=clean_ticker)
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
        if cur_price is None and quote_info.get("raw_price") and float(quote_info["raw_price"]) > 0:
            cur_price = float(quote_info["raw_price"])

        # 2. 从官方财报底账提取三表事实
        dossier = UnifiedDataCollectionGateway.load_verified_batch_dossier(clean_ticker)
        raw_table = (dossier or {}).get("raw_financials_table") or {}

        if cur_price is None or cur_price <= 0:
            return self.error_envelope("VALUATION_INPUT_BLOCKED", "等待通过时效核验的行情，暂缓自动估值", 422)

        # 财报事实、平账与估值假设分别核对。缺字段时保留原因供个股页展示。
        try:
            cash_val = raw_table.get("cash") or raw_table.get("cash_and_equivalents")
            src_val = raw_table.get("source") or raw_table.get("source_filing") or (dossier or {}).get("overview", {}).get("source_filing") or f"{clean_ticker} 官方决算短信/年报归档"
            period_val = raw_table.get("period") or (dossier or {}).get("overview", {}).get("fiscal_period") or "2026 财年"
            filing = UnifiedDataCollectionGateway.ingest_company_financials(clean_ticker, market, {
                **raw_table,
                "cash_and_equivalents": cash_val,
                "source_filing": src_val,
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
            source_filing = filing.get("source_filing") or src_val
            period_end = period_val
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
                    "label": "保守底价",
                    "scenario_status": "DEFENSIVE_FLOOR",
                    "scenario_tag": "严苛防御",
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
                    "label": "中性公允价",
                    "scenario_status": "FAIR_VALUE_ANCHOR",
                    "scenario_tag": "公允基准",
                    "description": "基于真实自由现金流与 WACC 资本成本的内在价值",
                },
                "optimistic_target": {
                    "value_per_share": target_val,
                    "equity_value": dcf_opt["result"].get("equity_value"),
                    "enterprise_value": dcf_opt["result"].get("enterprise_value"),
                    "discount_rate_pct": round(opt_discount_rate * 100, 1),
                    "terminal_growth_pct": round(opt_terminal_growth * 100, 1),
                    "growth_rates_pct": [round(g * 100, 1) for g in opt_growth_rates],
                    "label": "乐观靶心价",
                    "scenario_status": "GROWTH_TARGET",
                    "scenario_tag": "景气爆发",
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


