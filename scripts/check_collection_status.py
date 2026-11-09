# -*- coding: utf-8 -*-
"""查看全量万家标的采集断点进度与统计工具 (check_collection_status.py)."""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data_max/ledger/collection_progress.db"


def main() -> None:
    if not DB_PATH.exists():
        print(f"断点数据库尚未生成: {DB_PATH}")
        sys.exit(0)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("SELECT status, count(*) FROM collection_tasks GROUP BY status")
    status_counts = dict(cursor.fetchall())

    cursor.execute("SELECT market, count(*) FROM collection_tasks WHERE status = 'SUCCESS' GROUP BY market")
    market_succ = dict(cursor.fetchall())

    cursor.execute("SELECT sum(bars_count) FROM collection_tasks WHERE status = 'SUCCESS'")
    total_bars = cursor.fetchone()[0] or 0

    cursor.execute("SELECT count(*) FROM collection_tasks")
    total_targets = cursor.fetchone()[0] or 0

    succ = status_counts.get("SUCCESS", 0)
    failed = status_counts.get("FAILED", 0)
    pending = status_counts.get("PENDING", 0)
    pct = (succ / total_targets * 100.0) if total_targets > 0 else 0.0

    print("=" * 65)
    print("      美日万家标的 (14,892家) 全量数据采集进度看板")
    print("=" * 65)
    print(f" 标的总数: {total_targets:,} 家 (美股 10,445 + 日股 4,447)")
    print(f" 成功归档: {succ:,} 家 ({pct:.2f}%) [美股: {market_succ.get('US', 0):,}, 日股: {market_succ.get('JP', 0):,}]")
    print(f" 失败待重试: {failed:,} 家")
    print(f" 正在排队: {pending:,} 家")
    print(f" 已入库历史日线总行数: {total_bars:,} 条 (10年多周期OHLCV)")
    print("=" * 65)

    # 显示最近 5 条成功样本
    cursor.execute("SELECT symbol, market, name, bars_count, start_date, end_date, updated_at FROM collection_tasks WHERE status = 'SUCCESS' ORDER BY updated_at DESC LIMIT 5")
    rows = cursor.fetchall()
    if rows:
        print(" 最近落盘成功标的:")
        for r in rows:
            print(f"   [{r[1]}] {r[0]:<8} | {r[2][:20]:<20} | {r[3]:>5} bars ({r[4]} ~ {r[5]}) | {r[6][:19]}")
        print("=" * 65)

    conn.close()


if __name__ == "__main__":
    main()
