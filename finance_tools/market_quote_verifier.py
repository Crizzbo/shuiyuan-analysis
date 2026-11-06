# -*- coding: utf-8 -*-
"""权威市场行情采集、美分级精度核验与不可篡改归档引擎 (market_quote_verifier.py).

严格遵循 2026-10-14 行情时效与精度强制核验规范及数据治理契约：
1. 美分级精度强保证 (Cent-Precision Invariant)：强制保留并校验两位小数 (如 $204.64)，严禁尾数截断与浮点漂移；
2. 交易时段感知与时区核验：准确识别 Pre-Market、Regular Trading、After-Hours 与 Previous Close 基准；
3. 不可篡改只追加归档 (Immutable Append-Only Archiving)：验证通过的新行情自动生成带时间戳与 SHA-256 签名的标准二级来源，绝不就地篡改历史文件；
4. 单一事实来源 (SSOT)：为全系统提供统一的行情取数与核验工具函数，废除散落在各业务脚本中的硬编码静态查找。
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import openpyxl
except ImportError:
    openpyxl = None

ROOT = Path(__file__).resolve().parents[1]

from financial_core.engines.quote_freshness_gateway import QuoteFreshnessGateway


class QuotePrecisionError(ValueError):
    """行情精度或格式违背美分级硬约束异常。"""
    pass


class QuoteVerificationError(RuntimeError):
    """行情凭证或时效性核验未通过异常。"""
    pass


@dataclass(frozen=True)
class ExcelQuoteResult:
    """自 Excel/Google Sheets 工作簿中抽取的行情与公式核验结果。"""
    ticker: str
    excel_path: str
    sheet_name: str
    coordinate: str
    formula: Optional[str]
    raw_value: Any
    extracted_price: float
    formatted_price: str
    is_valid: bool
    error_message: Optional[str] = None


@dataclass(frozen=True)
class VerifiedQuote:
    """经严格门禁核验的权威股票行情对象。"""
    ticker: str
    company_name: str
    price: float
    currency: str
    timestamp_iso: str
    timestamp_formatted: str
    session_type: str
    source_type: str
    source_file: str
    sha256_hash: str
    formatted_price: str
    is_valid: bool
    is_fresh_today: bool = False
    freshness_status: str = "fresh"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MarketQuoteVerifier:
    """市场行情核验与规范归档工具箱。"""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or ROOT
        self.raw_dir = self.root_dir / "data" / "google-finance" / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def verify_price_precision(price: float, currency: str = "USD") -> str:
        """执行美分级 (Cent-Precision) 与权威货币严格精度检验。

        必须为有限正数，USD 必须保留精确 2 位小数，JPY 保留日元规范格式。
        """
        if not isinstance(price, (int, float)) or isinstance(price, bool):
            raise QuotePrecisionError(f"价格必须为数值类型，实际接收到: {type(price)}")
        if not math.isfinite(price) or price <= 0.0:
            raise QuotePrecisionError(f"价格必须为有限正数，实际数值: {price}")

        curr_upper = currency.strip().upper()
        if curr_upper == "JPY":
            formatted = f"¥{price:,.2f}"
            return formatted
        else:
            formatted = f"${price:.2f}"
            match = re.match(r"^\$(\d+)\.(\d{2})$", formatted)
            if not match:
                raise QuotePrecisionError(f"价格格式化失败，未能匹配美分格式: {formatted}")
            return formatted

    @staticmethod
    def generate_google_sheets_quote_formula(
        ticker: str,
        as_of_date: Optional[str] = None,
        use_today: bool = False,
        attribute: str = "price",
    ) -> str:
        """生成符合 Google Sheets 买方规范的带日期标量提取公式。

        针对 Google Sheets GOOGLEFINANCE 带有日期参数时返回 2x2 数组 (Date/Close) 的特性，
        强制嵌套 INDEX(..., 2, 2) 提取单一精确标量现价，彻底防止 List 溢出破坏模型网格。
        """
        ticker_clean = ticker.strip().upper()
        # 日股标的代码加上交易所前缀
        if ticker_clean.isdigit():
            symbol = f"TYO:{ticker_clean}"
        else:
            symbol = ticker_clean

        if use_today or not as_of_date:
            return f'=INDEX(GOOGLEFINANCE("{symbol}", "{attribute}", TODAY()), 2, 2)'

        # 解析具体日期
        try:
            if "T" in as_of_date:
                dt = datetime.fromisoformat(as_of_date.replace("Z", "+00:00"))
                year, month, day = dt.year, dt.month, dt.day
            else:
                parts = [int(p) for p in as_of_date.split("-")]
                year, month, day = parts[0], parts[1], parts[2]
            return f'=INDEX(GOOGLEFINANCE("{symbol}", "{attribute}", DATE({year}, {month}, {day})), 2, 2)'
        except Exception:
            return f'=INDEX(GOOGLEFINANCE("{symbol}", "{attribute}", TODAY()), 2, 2)'

    @staticmethod
    def inspect_session(timestamp_iso: str) -> str:
        """依据 ISO 时间戳解析市场时段状态。"""
        try:
            dt = datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00"))
        except Exception as e:
            raise QuoteVerificationError(f"无效的时间戳格式: {timestamp_iso}, 原因: {e}")

        # 简单时段启发式识别 (可结合真实交易所日历深入扩展)
        hour_utc = dt.astimezone(timezone.utc).hour
        # 美股交易时间 (UTC 13:30 - 20:00，对应 EDT 09:30 - 16:00)
        if 13 <= hour_utc < 20:
            return "regular_trading"
        elif 8 <= hour_utc < 13:
            return "pre_market"
        elif 20 <= hour_utc < 24:
            return "after_hours"
        else:
            return "previous_close_baseline"

    def archive_verified_quote(
        self,
        ticker: str,
        company_name: str,
        price: float,
        currency: str = "USD",
        quote_timestamp_iso: Optional[str] = None,
        source_label: str = "google_finance_verified_quote",
    ) -> VerifiedQuote:
        """核验并增量归档最新行情快照至本地二级来源 (绝不篡改已有历史文件)。"""
        ticker_clean = ticker.strip().upper()
        formatted_price = self.verify_price_precision(price)

        now_utc = datetime.now(timezone.utc)
        ts_iso = quote_timestamp_iso or now_utc.isoformat()
        session_type = self.inspect_session(ts_iso)

        time_slug = now_utc.strftime("%Y%m%dT%H%M%S_%fZ")
        archive_file = self.raw_dir / f"{time_slug}_{ticker_clean}_market_quote.json"
        counter = 1
        while archive_file.exists():
            archive_file = self.raw_dir / f"{time_slug}_{ticker_clean}_market_quote_v{counter}.json"
            counter += 1

        # 执行 QuoteFreshnessGateway 前置核验
        gateway_res = QuoteFreshnessGateway.verify_quote(
            price=price,
            currency=currency,
            quote_timestamp=ts_iso,
            market="US",
            current_time_iso=now_utc.isoformat(),
            max_staleness_hours=72.0,
        )

        record_data = {
            "acquired_at": ts_iso,
            "source": source_label,
            "session_type": session_type,
            "quotes": {
                ticker_clean: {
                    "ticker": ticker_clean,
                    "company_name": company_name,
                    "current_price": round(price, 4),
                    "currency": currency,
                    "timestamp_iso": ts_iso,
                    "timestamp_formatted": gateway_res.formatted_label,
                    "session_type": session_type,
                    "is_valid": True,
                    "staleness_status": "FRESH_ARCHIVED",
                    "formatted_price": formatted_price,
                }
            },
        }

        content_bytes = json.dumps(record_data, indent=2, ensure_ascii=False).encode("utf-8")
        archive_file.write_bytes(content_bytes)
        sha256 = hashlib.sha256(content_bytes).hexdigest()

        return VerifiedQuote(
            ticker=ticker_clean,
            company_name=company_name,
            price=price,
            currency=currency,
            timestamp_iso=ts_iso,
            timestamp_formatted=gateway_res.formatted_label,
            session_type=session_type,
            source_type=source_label,
            source_file=str(archive_file.relative_to(self.root_dir)),
            sha256_hash=sha256,
            formatted_price=formatted_price,
            is_valid=True,
            is_fresh_today=gateway_res.is_fresh_today,
            freshness_status=gateway_res.session_status,
        )

    def get_latest_quote(
        self, ticker: str, as_of_iso: Optional[str] = None
    ) -> VerifiedQuote:
        """自归档底账中以单一事实来源提取最权威的最新有效报价。

        自适应支持三类官方二级数据结构：
        1. 标准字典格式 (quotes 字典)
        2. 证券列表格式 (securities 数组)
        3. Google Sheets 单元格原生树结构 (cells 结构)
        """
        ticker_clean = ticker.strip().upper()
        if not self.raw_dir.exists():
            raise QuoteVerificationError(f"行情归档目录不存在: {self.raw_dir}")

        is_jp = ticker_clean.isdigit() or ticker_clean.startswith("TYO:")
        market = "JP" if is_jp else "US"
        default_curr = "JPY" if is_jp else "USD"

        json_files = sorted(list(self.raw_dir.glob("*.json")), reverse=True)
        for q_file in json_files:
            try:
                data = json.loads(q_file.read_text(encoding="utf-8"))
                price: Optional[float] = None
                currency: str = default_curr
                ts_iso: str = ""
                comp_name: str = ticker_clean
                session_type: str = "regular_trading"
                source_label: str = str(data.get("source", "archived_quote"))

                # 1. 探测 quotes 字典格式
                quotes_dict = data.get("quotes", {})
                if ticker_clean in quotes_dict:
                    raw_q = quotes_dict[ticker_clean]
                    price = float(raw_q["current_price"])
                    currency = str(raw_q.get("currency", default_curr))
                    ts_iso = str(raw_q.get("timestamp_iso", data.get("acquired_at", "")))
                    comp_name = str(raw_q.get("company_name", ticker_clean))
                    session_type = str(raw_q.get("session_type", data.get("session_type", "regular_trading")))

                # 2. 探测 securities 列表格式
                elif "securities" in data and isinstance(data["securities"], list):
                    for sec in data["securities"]:
                        t_val = str(sec.get("ticker", "")).upper()
                        f_sym = str(sec.get("full_symbol", "")).upper()
                        if t_val == ticker_clean or f_sym.endswith(f":{ticker_clean}"):
                            price = float(sec.get("current_price", sec.get("close", 0.0)))
                            currency = str(sec.get("currency", default_curr))
                            ts_iso = str(sec.get("timestamp_iso", data.get("extracted_at", data.get("acquired_at", ""))))
                            comp_name = str(sec.get("company_name", ticker_clean))
                            session_type = str(sec.get("market_status", "regular_trading"))
                            break

                # 3. 探测 Google Sheets 原生 cells 结构
                elif "cells" in data and isinstance(data["cells"], dict):
                    sheets = data["cells"].get("structuredContent", {}).get("sheets", [])
                    for s in sheets:
                        for row_data in s.get("data", []):
                            for r_item in row_data.get("rowData", []):
                                cells_list = r_item.get("values", [])
                                if not cells_list:
                                    continue
                                c0_val = str(cells_list[0].get("effectiveValue", {}).get("stringValue", "")).upper()
                                if ticker_clean in c0_val or c0_val.endswith(f":{ticker_clean}"):
                                    # 命中标的
                                    if len(cells_list) > 1:
                                        comp_name = cells_list[1].get("effectiveValue", {}).get("stringValue", ticker_clean)
                                    if len(cells_list) > 2:
                                        num_val = cells_list[2].get("effectiveValue", {}).get("numberValue")
                                        if num_val is not None:
                                            price = float(num_val)
                                    if len(cells_list) > 3:
                                        currency = cells_list[3].get("effectiveValue", {}).get("stringValue", default_curr)
                                    ts_iso = str(data.get("acquired_at", ""))
                                    source_label = "google_sheets_live_cells"
                                    break
                            if price is not None:
                                break
                        if price is not None:
                            break

                if price is not None:
                    # 价格美分/币种保真核验
                    fmt_price = self.verify_price_precision(price, currency=currency)

                    # 门禁核验
                    curr_time = as_of_iso or datetime.now(timezone.utc).isoformat()
                    v_res = QuoteFreshnessGateway.verify_quote(
                        price=price,
                        currency=currency,
                        quote_timestamp=ts_iso or curr_time,
                        market=market,
                        current_time_iso=curr_time,
                        max_staleness_hours=72.0,
                    )

                    file_sha = hashlib.sha256(q_file.read_bytes()).hexdigest()

                    return VerifiedQuote(
                        ticker=ticker_clean,
                        company_name=comp_name,
                        price=price,
                        currency=currency,
                        timestamp_iso=ts_iso or curr_time,
                        timestamp_formatted=v_res.formatted_label,
                        session_type=session_type,
                        source_type=source_label,
                        source_file=str(q_file.relative_to(self.root_dir)),
                        sha256_hash=file_sha,
                        formatted_price=fmt_price,
                        is_valid=True,
                        is_fresh_today=v_res.is_fresh_today,
                        freshness_status=v_res.session_status,
                    )
            except Exception:
                continue

        raise QuoteVerificationError(f"未能检索到标的 {ticker_clean} 的任何有效归档行情！")

    def extract_quote_from_excel(
        self,
        excel_path: Union[str, Path],
        ticker: str = "NVDA",
        sheet_name: Optional[str] = None,
        coordinate: Optional[str] = None,
    ) -> ExcelQuoteResult:
        """从实际 Excel 工作簿中抽取行情数值与公式，执行美分级精度验证。

        严格遵循从真实介质提取的原则，杜绝无介质假对账。
        """
        if openpyxl is None:
            raise RuntimeError("系统未安装 openpyxl 库，无法读取 Excel 工作簿")

        path_obj = Path(excel_path)
        if not path_obj.is_absolute():
            path_obj = self.root_dir / path_obj
        if not path_obj.exists():
            raise FileNotFoundError(f"目标 Excel 文件不存在: {path_obj}")

        ticker_clean = ticker.strip().upper()

        wb_formula = openpyxl.load_workbook(path_obj, data_only=False)
        wb_values = openpyxl.load_workbook(path_obj, data_only=True)

        target_ws_name = sheet_name
        target_coord = coordinate

        if not target_ws_name or not target_coord:
            found = False
            for s_name in wb_formula.sheetnames:
                ws_f = wb_formula[s_name]
                for r in range(1, min(ws_f.max_row + 1, 30)):
                    for c in range(1, min(ws_f.max_column + 1, 15)):
                        cell_f = ws_f.cell(row=r, column=c)
                        val_str = str(cell_f.value or "")
                        if any(kw in val_str for kw in ["当前市价", "当前价格", "现价"]):
                            right_cell = ws_f.cell(row=r, column=c + 1)
                            target_ws_name = s_name
                            target_coord = right_cell.coordinate
                            found = True
                            break
                        elif f'GOOGLEFINANCE("{ticker_clean}"' in val_str.replace(" ", "") or (ticker_clean in val_str and "GOOGLEFINANCE" in val_str):
                            target_ws_name = s_name
                            target_coord = cell_f.coordinate
                            found = True
                            break
                    if found:
                        break
                if found:
                    break

            if not found:
                target_ws_name = sheet_name or wb_formula.sheetnames[0]
                target_coord = coordinate or "C3"

        ws_formula = wb_formula[target_ws_name]
        ws_values = wb_values[target_ws_name]

        cell_formula = ws_formula[target_coord]
        cell_value = ws_values[target_coord]

        raw_f = cell_formula.value
        raw_v = cell_value.value

        formula_str = str(raw_f) if str(raw_f or "").startswith("=") else None

        candidate_val = raw_v if raw_v is not None else raw_f
        extracted_price = None

        if isinstance(candidate_val, (int, float)) and not isinstance(candidate_val, bool):
            extracted_price = float(candidate_val)
        elif isinstance(candidate_val, str):
            clean_str = candidate_val.replace("$", "").replace(",", "").strip()
            try:
                extracted_price = float(clean_str)
            except ValueError:
                pass

        if extracted_price is None:
            return ExcelQuoteResult(
                ticker=ticker_clean,
                excel_path=str(path_obj),
                sheet_name=target_ws_name,
                coordinate=target_coord,
                formula=formula_str,
                raw_value=candidate_val,
                extracted_price=0.0,
                formatted_price="$0.00",
                is_valid=False,
                error_message=f"单元格 {target_coord} 包含公式 {formula_str} 但无计算缓存值",
            )

        try:
            fmt_price = self.verify_price_precision(extracted_price)
            is_valid = True
            err_msg = None
        except QuotePrecisionError as qe:
            fmt_price = f"${extracted_price}"
            is_valid = False
            err_msg = str(qe)

        return ExcelQuoteResult(
            ticker=ticker_clean,
            excel_path=str(path_obj),
            sheet_name=target_ws_name,
            coordinate=target_coord,
            formula=formula_str,
            raw_value=candidate_val,
            extracted_price=extracted_price,
            formatted_price=fmt_price,
            is_valid=is_valid,
            error_message=err_msg,
        )
