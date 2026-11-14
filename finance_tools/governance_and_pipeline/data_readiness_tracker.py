"""数据拉取完成度与时效新鲜度底账追踪器 (Data Readiness & Freshness Tracker).

遵循买方机构级数据治理与《AGENTS.md》2026-11-08 刚性规范:
1. 自动扫描本地落盘行情底账 (data/google-finance/raw/ 与 manifests/);
2. 提取最新批次时间戳与日期，精确识别哪些核心标的已完成最新数据拉取;
3. 分类输出宏观大盘指数与核心个股标的的落盘完备度状态;
4. 生成结构化自然语言提醒横幅，供 Agent 每次交互与研报输出前置挂载声明;
5. 纯本地物理扫描，零网络依赖，零大模型 Token 开销。
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def is_excluded_quote(path: Path, payload: Dict[str, Any]) -> bool:
    """识别曾写入正式目录的演示行情批次。"""
    if payload.get("source") == "authoritative_macro_and_tech_universe_quotes":
        return True
    if not path.name.startswith("20261113T060000_"):
        return False
    exclusions = json.loads((PROJECT_ROOT / "config/terminal-evidence-exclusions.json").read_text(encoding="utf-8"))
    price = exclusions["quote_files"].get(path.name)
    quotes = payload.get("quotes")
    return (
        price is not None and payload.get("source") == "google_finance_verified_quote"
        and isinstance(quotes, dict) and len(quotes) == 1
        and any(isinstance(row, dict) and row.get("current_price") == price for row in quotes.values())
    )


@dataclass(frozen=True)
class DataReadinessSnapshot:
    """最新日期核心数据拉取就绪快照契约."""

    latest_date_str: str
    latest_timestamp_utc: str
    macro_indices_completed: List[str]
    equities_completed: List[str]
    total_completed_count: int
    data_source_summary: str
    market_session_note: str
    banner_text: str

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典契约."""
        return {
            "latest_date": self.latest_date_str,
            "latest_timestamp_utc": self.latest_timestamp_utc,
            "macro_indices_count": len(self.macro_indices_completed),
            "macro_indices": self.macro_indices_completed,
            "equities_count": len(self.equities_completed),
            "equities": self.equities_completed,
            "total_completed": self.total_completed_count,
            "source_summary": self.data_source_summary,
            "session_note": self.market_session_note,
            "banner_text": self.banner_text,
        }


class DataReadinessTracker:
    """本地行情与核心数据拉取完备度追踪器."""

    # 宏观与宽基指数/资产代码集合
    MACRO_INDEX_TICKERS: Set[str] = {
        "SPY", "QQQ", "DIA", "SMH", "1306", "^VIX", "^N225VI",
        "DXY", "USDJPY", "^TNX", "TLT", "IEF", "GLD", "IAU", "XLE", "XLK", "XBI"
    }

    def __init__(self, raw_dir: Optional[Path] = None):
        self.raw_dir = raw_dir or (PROJECT_ROOT / "data/google-finance/raw")

    def inspect_latest_readiness(self) -> DataReadinessSnapshot:
        """扫描本地行情底账，提取最新日期拉取完成的核心标的清单."""
        if not self.raw_dir.exists() or not self.raw_dir.is_dir() or not any(self.raw_dir.iterdir()):
            return DataReadinessSnapshot(
                latest_date_str="未知",
                latest_timestamp_utc="无落盘数据",
                macro_indices_completed=[],
                equities_completed=[],
                total_completed_count=0,
                data_source_summary="本地行情目录未就绪",
                market_session_note="等待首次行情拉取",
                banner_text="【数据时效底账提醒】本地暂无行情数据落盘记录。",
            )

        # 匹配形如 20261107T124149_134772Z_SPY_market_quote.json 的文件
        pattern = re.compile(r"^(\d{8})T(\d{6})_(\d+Z)_([A-Za-z0-9_\^]+)_market_quote\.json$")

        batches: Dict[str, Dict[str, Any]] = {}

        for p in self.raw_dir.iterdir():
            if not p.is_file():
                continue
            m = pattern.match(p.name)
            if not m:
                continue
            try:
                payload = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(payload, dict) or is_excluded_quote(p, payload):
                continue
            quotes = payload.get("quotes")
            if not isinstance(quotes, dict) or not quotes:
                continue

            date_part, time_part, _, ticker = m.groups()
            batch_key = f"{date_part}T{time_part}"
            date_formatted = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:]}"

            if batch_key not in batches:
                batches[batch_key] = {
                    "date": date_formatted,
                    "batch_key": batch_key,
                    "tickers": set(),
                    "file_count": 0,
                }
            batches[batch_key]["tickers"].add(ticker)
            batches[batch_key]["file_count"] += 1

        if not batches:
            # 兼容历史无前缀格式如 20261014_market_quotes.json
            return DataReadinessSnapshot(
                latest_date_str="未知",
                latest_timestamp_utc="无可用批次",
                macro_indices_completed=[],
                equities_completed=[],
                total_completed_count=0,
                data_source_summary="暂无可识别的行情批次",
                market_session_note="待补数",
                banner_text="本地暂无可用的行情批次。",
            )

        # 按最新批次键排序获取最新批次
        latest_batch_key = sorted(batches.keys())[-1]
        latest_info = batches[latest_batch_key]
        latest_date = latest_info["date"]
        all_tickers = sorted(list(latest_info["tickers"]))

        # 分流宏观与个股
        macro_indices: List[str] = []
        equities: List[str] = []

        for t in all_tickers:
            if t in self.MACRO_INDEX_TICKERS or t.startswith("^"):
                macro_indices.append(t)
            else:
                equities.append(t)

        timestamp_utc = f"{latest_date} {latest_batch_key[9:11]}:{latest_batch_key[11:13]}:{latest_batch_key[13:15]} UTC"

        # 构造自然语言提醒横幅
        macro_str = ", ".join(macro_indices) if macro_indices else "暂无"
        equities_str = ", ".join(equities) if equities else "暂无"

        banner = (
            f"📊 **【最新数据拉取完成度与时效底账前置提醒】**\n"
            f"- **探测最新基准日期**：`{latest_date}`（精确时间戳：`{timestamp_utc}`，前收盘价基准 / 闭市状态）\n"
            f"- **已完成核心拉取标的**：共计 **{len(all_tickers)}** 只资产标的已完全落盘至 `data/google-finance/raw/`\n"
            f"  • **宏观与指数（{len(macro_indices)}只）**：{macro_str}\n"
            f"  • **核心美日个股（{len(equities)}只）**：{equities_str}\n"
            f"- **覆盖范围**：上述数量仅统计行情快照归档。日线、成交量与三表需要分别核对。"
        )

        return DataReadinessSnapshot(
            latest_date_str=latest_date,
            latest_timestamp_utc=timestamp_utc,
            macro_indices_completed=macro_indices,
            equities_completed=equities,
            total_completed_count=len(all_tickers),
            data_source_summary="Google Finance 授权专用行情表与公开交易所归档",
            market_session_note="交易时段以逐笔报价核验结果为准",
            banner_text=banner,
        )


def get_data_readiness_banner() -> str:
    """快捷获取当前系统最新数据拉取完备度提醒横幅文本."""
    tracker = DataReadinessTracker()
    return tracker.inspect_latest_readiness().banner_text
