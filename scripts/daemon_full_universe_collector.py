# -*- coding: utf-8 -*-
"""美日万家标的全量数据后台异步采集与断点续传守护引擎 (daemon_full_universe_collector.py).

严格遵循《AGENTS.md》与《CLAUDE.md》：
1. 资产池全量覆盖：
   - 美股 10,445 家 (SEC EDGAR 注册)；
   - 日股 4,447 家 (东证全市场 Prime/Standard/Growth)；
   - 合计 14,892 家上市主体。
2. 架构防劣变与高性能：
   - 采用 asyncio + aiohttp 异步非阻塞高并发流水线；
   - 令牌桶限流控制（安全限制 8~10 req/s），指数退避重试，防止 HTTP 429；
   - 两级分桶压缩落盘 (Windows NTFS MFT 防索引退化设计)；
   - SQLite WAL 模式原子事务状态机，支持秒级热启动与断点续传。
3. 数据规范与免密公开：
   - 采用免密公开行情端点，严禁读取账户私密配置；
   - 产物写入 data_max/，每次写入生成 SHA-256 校验和。
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sqlite3
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA_MAX_DIR = ROOT / "data_max"
RAW_DIR = DATA_MAX_DIR / "raw"
NORMALIZED_DIR = DATA_MAX_DIR / "normalized"
LEDGER_DIR = DATA_MAX_DIR / "ledger"
DB_PATH = LEDGER_DIR / "collection_progress.db"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


class AsyncTokenBucket:
    """异步非阻塞令牌桶速率限制器."""

    def __init__(self, rate: float = 8.0, capacity: float = 12.0) -> None:
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.last_update = now
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
            await asyncio.sleep(0.05)


class ProgressLedger:
    """基于 SQLite WAL 模式的 ACID 断点状态机."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collection_tasks (
                    symbol TEXT PRIMARY KEY,
                    market TEXT,
                    raw_code TEXT,
                    name TEXT,
                    tier TEXT,
                    status TEXT, -- PENDING, SUCCESS, FAILED, SKIPPED
                    bars_count INTEGER DEFAULT 0,
                    start_date TEXT,
                    end_date TEXT,
                    raw_file_path TEXT,
                    raw_sha256 TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    updated_at TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON collection_tasks(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_market ON collection_tasks(market)")

    def sync_manifest_targets(self, targets: List[Dict[str, Any]]) -> Tuple[int, int]:
        """批量同步资产池清单至任务表，保留已有进度."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            inserted = 0
            for t in targets:
                cursor.execute("""
                    INSERT OR IGNORE INTO collection_tasks
                    (symbol, market, raw_code, name, tier, status, retry_count, updated_at)
                    VALUES (?, ?, ?, ?, ?, 'PENDING', 0, ?)
                """, (
                    t["symbol"],
                    t["market"],
                    t["raw_code"],
                    t["name"],
                    t.get("tier", "Tier 2"),
                    datetime.now(timezone.utc).isoformat()
                ))
                if cursor.rowcount > 0:
                    inserted += 1
            conn.commit()
            cursor.execute("SELECT count(*) FROM collection_tasks")
            total = cursor.fetchone()[0]
            return inserted, total

    def get_pending_tasks(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取待抓取任务列表（支持重试小于 3 次的失败任务）."""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            query = """
                SELECT * FROM collection_tasks
                WHERE status IN ('PENDING', 'FAILED') AND retry_count < 3
                ORDER BY
                    CASE tier
                        WHEN 'Tier 0' THEN 1
                        WHEN 'Tier 1' THEN 2
                        ELSE 3
                    END,
                    symbol ASC
            """
            if limit:
                query += f" LIMIT {int(limit)}"
            rows = conn.execute(query).fetchall()
            return [dict(r) for r in rows]

    def update_task_success(
        self,
        symbol: str,
        bars_count: int,
        start_date: str,
        end_date: str,
        raw_file_path: str,
        raw_sha256: str,
    ) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE collection_tasks
                SET status = 'SUCCESS',
                    bars_count = ?,
                    start_date = ?,
                    end_date = ?,
                    raw_file_path = ?,
                    raw_sha256 = ?,
                    error_message = NULL,
                    updated_at = ?
                WHERE symbol = ?
            """, (
                bars_count,
                start_date,
                end_date,
                raw_file_path,
                raw_sha256,
                datetime.now(timezone.utc).isoformat(),
                symbol
            ))

    def update_task_failure(self, symbol: str, error_msg: str) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE collection_tasks
                SET status = 'FAILED',
                    error_message = ?,
                    retry_count = retry_count + 1,
                    updated_at = ?
                WHERE symbol = ?
            """, (
                error_msg,
                datetime.now(timezone.utc).isoformat(),
                symbol
            ))

    def get_statistics(self) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, count(*) FROM collection_tasks GROUP BY status")
            counts = dict(cursor.fetchall())
            cursor.execute("SELECT sum(bars_count) FROM collection_tasks WHERE status = 'SUCCESS'")
            total_bars = cursor.fetchone()[0] or 0
            cursor.execute("SELECT count(*) FROM collection_tasks")
            total = cursor.fetchone()[0] or 0
            return {
                "total_targets": total,
                "success": counts.get("SUCCESS", 0),
                "pending": counts.get("PENDING", 0),
                "failed": counts.get("FAILED", 0),
                "total_bars_collected": total_bars,
                "progress_pct": (counts.get("SUCCESS", 0) / total * 100.0) if total > 0 else 0.0,
            }


def build_full_universe_targets() -> List[Dict[str, Any]]:
    """加载 14,892 家全量美日资产池清单."""
    us_manifest_file = DATA_MAX_DIR / "universe/sec_universe_manifest.json"
    jp_manifest_file = DATA_MAX_DIR / "universe/jpx_universe_manifest.json"

    if not us_manifest_file.exists() or not jp_manifest_file.exists():
        raise FileNotFoundError("全量 manifest 未就绪，请先执行 ingest_full_universe_data_max.py")

    us_data = json.loads(us_manifest_file.read_text(encoding="utf-8"))
    jp_data = json.loads(jp_manifest_file.read_text(encoding="utf-8"))

    targets: List[Dict[str, Any]] = []

    # 美股 targets
    for item in us_data["entities"]:
        ticker = item["ticker"].strip()
        if not ticker:
            continue
        targets.append({
            "symbol": ticker,
            "market": "US",
            "raw_code": item["cik"],
            "name": item["name"],
            "tier": item.get("tier", "Tier 2"),
        })

    # 日股 targets
    for item in jp_data["entities"]:
        code = item["code"].strip()
        if not code:
            continue
        targets.append({
            "symbol": f"{code}.T",
            "market": "JP",
            "raw_code": code,
            "name": item["name"],
            "tier": item.get("tier", "Tier 2"),
        })

    return targets


def get_sub_bucket(symbol: str) -> str:
    """根据符号生成两级分桶目录名称，防止单目录下文件过多."""
    clean = symbol.replace(".", "_").replace("-", "_")
    if len(clean) >= 2:
        return clean[:2].upper()
    return clean[:1].upper() if clean else "XX"


async def fetch_symbol_chart(
    session: aiohttp.ClientSession,
    symbol: str,
    rate_limiter: AsyncTokenBucket,
    max_retries: int = 3,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """单只股票 10 年日线数据异步抓取与指数退避重试."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {
        "range": "10y",
        "interval": "1d",
        "events": "div,splits",
    }

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
    }

    for attempt in range(max_retries):
        await rate_limiter.acquire()
        try:
            async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=20.0)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data, None
                elif resp.status == 429:
                    backoff = (2 ** attempt) * 2.0 + random.uniform(0.5, 1.5)
                    await asyncio.sleep(backoff)
                    continue
                elif resp.status in (404, 400):
                    return None, f"HTTP_{resp.status}_NOT_FOUND_OR_DELISTED"
                else:
                    await asyncio.sleep(1.0)
        except Exception as e:
            if attempt == max_retries - 1:
                return None, f"{type(e).__name__}: {str(e)}"
            await asyncio.sleep(1.5)

    return None, "MAX_RETRIES_EXCEEDED"


def parse_and_normalize_chart(raw_data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """解析原始 Chart JSON 为标准化日线、分红与拆股结构."""
    chart = raw_data.get("chart", {})
    results = chart.get("result", [])
    if not results:
        return [], [], []

    res = results[0]
    timestamps = res.get("timestamp", [])
    indicators = res.get("indicators", {})
    quote_list = indicators.get("quote", [])
    adjclose_list = indicators.get("adjclose", [])

    if not timestamps or not quote_list:
        return [], [], []

    q = quote_list[0]
    opens = q.get("open", [])
    highs = q.get("high", [])
    lows = q.get("low", [])
    closes = q.get("close", [])
    volumes = q.get("volume", [])
    adj_closes = adjclose_list[0].get("adjclose", []) if adjclose_list else closes

    bars: List[Dict[str, Any]] = []
    n = len(timestamps)

    for i in range(n):
        o = opens[i] if i < len(opens) else None
        h = highs[i] if i < len(highs) else None
        l = lows[i] if i < len(lows) else None
        c = closes[i] if i < len(closes) else None
        v = volumes[i] if i < len(volumes) else None
        ac = adj_closes[i] if i < len(adj_closes) else c

        if None in (o, h, l, c) or c <= 0:
            continue

        dt_str = datetime.fromtimestamp(timestamps[i], tz=timezone.utc).strftime("%Y-%m-%d")
        bars.append({
            "date": dt_str,
            "open": round(float(o), 4),
            "high": round(float(h), 4),
            "low": round(float(l), 4),
            "close": round(float(c), 4),
            "adjusted_close": round(float(ac), 4) if ac is not None else round(float(c), 4),
            "volume": int(v) if v is not None else 0,
        })

    # 事件提取
    events = res.get("events", {})
    divs_raw = events.get("dividends", {})
    splits_raw = events.get("splits", {})

    dividends: List[Dict[str, Any]] = []
    for ts, d_item in divs_raw.items():
        dt_str = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
        dividends.append({
            "date": dt_str,
            "amount": float(d_item.get("amount", 0.0)),
        })

    splits: List[Dict[str, Any]] = []
    for ts, s_item in splits_raw.items():
        dt_str = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
        nomer = float(s_item.get("numerator", 1.0))
        denom = float(s_item.get("denominator", 1.0))
        ratio = nomer / denom if denom > 0 else 1.0
        splits.append({
            "date": dt_str,
            "ratio": round(ratio, 6),
        })

    return bars, dividends, splits


async def process_task(
    session: aiohttp.ClientSession,
    task: Dict[str, Any],
    rate_limiter: AsyncTokenBucket,
    ledger: ProgressLedger,
) -> bool:
    """处理单个标的的抓取、清洗与落盘事务."""
    sym = task["symbol"]
    market = task["market"].lower()
    sub_bucket = get_sub_bucket(sym)

    raw_dir_target = RAW_DIR / market / sub_bucket
    norm_dir_target = NORMALIZED_DIR / market
    raw_dir_target.mkdir(parents=True, exist_ok=True)
    norm_dir_target.mkdir(parents=True, exist_ok=True)

    raw_file = raw_dir_target / f"{sym}.json.gz"
    clean_sym = sym.replace(".", "_")
    norm_file = norm_dir_target / f"{clean_sym}_bars.json"

    # 若本地规范化文件已存在且有效，直接标记成功
    if norm_file.exists() and norm_file.stat().st_size > 500:
        try:
            existing = json.loads(norm_file.read_text(encoding="utf-8"))
            e_bars = existing.get("bars", [])
            if len(e_bars) > 50:
                ledger.update_task_success(
                    symbol=sym,
                    bars_count=len(e_bars),
                    start_date=e_bars[0]["date"],
                    end_date=e_bars[-1]["date"],
                    raw_file_path=str(norm_file),
                    raw_sha256=hashlib.sha256(norm_file.read_bytes()).hexdigest(),
                )
                return True
        except Exception:
            pass

    # 远程异步抓取
    raw_data, error_msg = await fetch_symbol_chart(session, sym, rate_limiter)
    if error_msg or not raw_data:
        ledger.update_task_failure(sym, error_msg or "EMPTY_RAW_RESPONSE")
        return False

    bars, divs, splits = parse_and_normalize_chart(raw_data)
    if not bars:
        ledger.update_task_failure(sym, "NO_VALID_OHLCV_BARS")
        return False

    # 1. 原始 JSON Gzip 压缩落盘
    raw_bytes = json.dumps(raw_data, ensure_ascii=False).encode("utf-8")
    raw_sha = hashlib.sha256(raw_bytes).hexdigest()
    with gzip.open(raw_file, "wb") as f_out:
        f_out.write(raw_bytes)

    # 2. 清洗规范化 JSON 落盘
    norm_payload = {
        "symbol": sym,
        "market": task["market"],
        "name": task["name"],
        "tier": task.get("tier", "Tier 2"),
        "total_bars": len(bars),
        "start_date": bars[0]["date"],
        "end_date": bars[-1]["date"],
        "bars": bars,
        "dividends": divs,
        "splits": splits,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    norm_file.write_text(json.dumps(norm_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3. 更新事务状态机
    ledger.update_task_success(
        symbol=sym,
        bars_count=len(bars),
        start_date=bars[0]["date"],
        end_date=bars[-1]["date"],
        raw_file_path=str(raw_file),
        raw_sha256=raw_sha,
    )
    return True


async def run_collector_daemon(
    concurrency: int = 8,
    rate_limit: float = 8.0,
    batch_size: int = 100,
    max_total_tasks: Optional[int] = None,
) -> None:
    """采集守护进程主循环."""
    print(">>> 启动美日万家标的后台数据采集与断点续传守护进程...")
    ledger = ProgressLedger(DB_PATH)
    targets = build_full_universe_targets()
    inserted, total = ledger.sync_manifest_targets(targets)
    print(f"资产池底账已同步至断点数据库: 总量 {total} 家, 新增待采 {inserted} 家")

    stats = ledger.get_statistics()
    print(f"当前进度基准: 成功 {stats['success']}/{stats['total_targets']} ({stats['progress_pct']:.2f}%), 历史日线总行数: {stats['total_bars_collected']:,}")

    rate_limiter = AsyncTokenBucket(rate=rate_limit, capacity=rate_limit * 1.5)
    connector = aiohttp.TCPConnector(limit=concurrency * 2)

    processed_in_session = 0
    t_start = time.monotonic()

    async with aiohttp.ClientSession(connector=connector) as session:
        while True:
            pending_tasks = ledger.get_pending_tasks(limit=batch_size)
            if not pending_tasks:
                print(">>> 全部待抓取任务已处理完毕！")
                break

            tasks = [
                process_task(session, task, rate_limiter, ledger)
                for task in pending_tasks
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            batch_succ = sum(1 for r in results if r is True)
            processed_in_session += len(pending_tasks)

            # 计算吞吐速率与进度
            elapsed = time.monotonic() - t_start
            cur_stats = ledger.get_statistics()
            speed = processed_in_session / elapsed if elapsed > 0 else 0.0
            remaining = cur_stats["total_targets"] - cur_stats["success"]
            eta_mins = (remaining / speed / 60.0) if speed > 0 else 0.0

            print(
                f"[进度心跳] 已完成: {cur_stats['success']}/{cur_stats['total_targets']} ({cur_stats['progress_pct']:.2f}%) | "
                f"当前批次成功: {batch_succ}/{len(pending_tasks)} | "
                f"采集速率: {speed:.1f} req/s | "
                f"预计剩余时间: {eta_mins:.1f} 分钟"
            )

            if max_total_tasks and processed_in_session >= max_total_tasks:
                print(f">>> 达到设定的单次会话上限 ({max_total_tasks})，安全挂起等待下次调度。")
                break

            await asyncio.sleep(0.1)

    final_stats = ledger.get_statistics()
    print(f">>> 会话结束！最终累计成功: {final_stats['success']}/{final_stats['total_targets']} ({final_stats['progress_pct']:.2f}%)")


def main() -> None:
    concurrency = 8
    rate_limit = 8.0
    batch_size = 50
    max_tasks = None

    if "--quick-test" in sys.argv:
        max_tasks = 20
    elif "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            max_tasks = int(sys.argv[idx + 1])

    asyncio.run(run_collector_daemon(
        concurrency=concurrency,
        rate_limit=rate_limit,
        batch_size=batch_size,
        max_total_tasks=max_tasks
    ))


if __name__ == "__main__":
    main()
