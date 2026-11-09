# -*- coding: utf-8 -*-
"""全球核心标的与基准资产历史行情与公司行动收集与清洗引擎 (collect_strategy_market_history.py).

严格遵循《AGENTS.md》与《CLAUDE.md》：
1. 采用免认证公开数据源 (Yahoo Finance Chart API)，不读取项目外账户配置或私有凭据；
2. 下载原始响应先归档至 data/history/strategy_execution_inputs/<timestamp>/raw/；
3. 清洗并标准化逐日日线 (Open, High, Low, Close, AdjClose, Volume) 及公司行动 (Dividends, Splits)；
4. 登记至本地不可篡改资料目录 (LocalStore) 并生成 SHA-256 哈希校验；
5. 提供确定性、点时间 (Point-in-Time) 兼容的数据清洗与质量自检。
"""

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from scripts.data_store import LocalStore


def fetch_symbol_chart_data(symbol: str, period1: int, period2: int) -> Tuple[bytes, Dict[str, Any], str]:
    """通过免认证公开接口下载日线行情与分红/拆股事件原始响应."""
    base_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
    params = {
        "period1": str(period1),
        "period2": str(period2),
        "interval": "1d",
        "events": "div,splits",
        "includeAdjustedClose": "true"
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw_bytes = resp.read()
        parsed = json.loads(raw_bytes.decode("utf-8"))
        return raw_bytes, parsed, url


def parse_and_clean_chart_data(parsed: Dict[str, Any], symbol: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """清洗日线数据，剔除缺失值，保证日期单调递增，分离分红和拆股事件."""
    result_list = parsed.get("chart", {}).get("result")
    if not result_list:
        raise ValueError(f"标的 {symbol} 返回数据结构缺少 chart.result")

    data = result_list[0]
    timestamps = data.get("timestamp", [])
    indicators = data.get("indicators", {})
    quote = (indicators.get("quote") or [{}])[0]
    adjclose_list = (indicators.get("adjclose") or [{}])[0].get("adjclose", [])

    opens = quote.get("open", [])
    highs = quote.get("high", [])
    lows = quote.get("low", [])
    closes = quote.get("close", [])
    volumes = quote.get("volume", [])

    n = len(timestamps)
    bars = []
    last_date = ""

    for i in range(n):
        ts = timestamps[i]
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).date()
        date_str = dt.isoformat()

        o = opens[i] if i < len(opens) else None
        h = highs[i] if i < len(highs) else None
        l = lows[i] if i < len(lows) else None
        c = closes[i] if i < len(closes) else None
        adj = adjclose_list[i] if i < len(adjclose_list) else None
        vol = volumes[i] if i < len(volumes) else None

        # 过滤完全缺失的休市日
        if c is None or o is None or h is None or l is None:
            continue

        o = float(o)
        h = float(h)
        l = float(l)
        c = float(c)
        adj = float(adj) if adj is not None else c
        vol = int(vol) if vol is not None else 0

        # 防御性清洗：价格必须严格为正，满足有限责任下界
        if o <= 0 or h <= 0 or l <= 0 or c <= 0 or adj <= 0:
            continue

        # 严格检查日期递增
        if last_date and date_str <= last_date:
            continue
        last_date = date_str

        bars.append({
            "date": date_str,
            "timestamp": ts,
            "open": round(o, 4),
            "high": round(h, 4),
            "low": round(l, 4),
            "close": round(c, 4),
            "adj_close": round(adj, 4),
            "volume": vol
        })

    # 提取公司行动 (Dividends / Splits)
    events = data.get("events", {})
    dividends_raw = events.get("dividends", {})
    splits_raw = events.get("splits", {})

    dividends = []
    for div_ts, div_info in dividends_raw.items():
        div_dt = datetime.fromtimestamp(int(div_ts), tz=timezone.utc).date().isoformat()
        amount = div_info.get("amount")
        if amount and float(amount) > 0:
            dividends.append({
                "date": div_dt,
                "timestamp": int(div_ts),
                "amount": round(float(amount), 4)
            })
    dividends.sort(key=lambda x: x["date"])

    splits = []
    for split_ts, split_info in splits_raw.items():
        split_dt = datetime.fromtimestamp(int(split_ts), tz=timezone.utc).date().isoformat()
        numerator = split_info.get("numerator", 1)
        denominator = split_info.get("denominator", 1)
        split_ratio = float(numerator) / float(denominator) if denominator else 1.0
        splits.append({
            "date": split_dt,
            "timestamp": int(split_ts),
            "numerator": numerator,
            "denominator": denominator,
            "ratio": round(split_ratio, 6)
        })
    splits.sort(key=lambda x: x["date"])

    return bars, dividends, splits


def main() -> int:
    config_file = ROOT / "config/strategy_universe_sources.json"
    if not config_file.exists():
        print(f"错误: 配置文件不存在 {config_file}")
        return 1

    config = json.loads(config_file.read_text(encoding="utf-8"))
    targets = config.get("targets", [])
    period1 = config.get("period1", 1420070400)
    period2 = config.get("period2", 1735689600)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    out_dir = ROOT / "data/history/strategy_execution_inputs" / stamp
    raw_dir = out_dir / "raw"
    clean_dir = out_dir / "normalized"
    manifests_dir = out_dir / "manifests"

    raw_dir.mkdir(parents=True, exist_ok=True)
    clean_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    collection = {
        "schema_version": "1.0.0",
        "capture_id": stamp,
        "purpose": config.get("purpose"),
        "period_start": config.get("period_start"),
        "period_end": config.get("period_end"),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "sources": [],
        "failures": []
    }

    print("\n" + "=" * 90)
    print("【全球核心标的与基准资产历史行情采集与不可篡改归档管道】")
    print("=" * 90)
    print(f"输出批次 ID: {stamp}")
    print(f"回测区间  : {config.get('period_start')} 至 {config.get('period_end')}")
    print(f"待采集标的数: {len(targets)}")
    print("-" * 90)

    store = LocalStore("data/catalog")

    try:
        for idx, target in enumerate(targets, 1):
            symbol = target["symbol"]
            target_id = target["id"]
            name_zh = target["name_zh"]
            market = target["market"]

            print(f"[{idx:02d}/{len(targets):02d}] 正在采集 {market} | {symbol:<8} ({name_zh})...", end="", flush=True)

            try:
                raw_bytes, parsed, final_url = fetch_symbol_chart_data(symbol, period1, period2)
                bars, dividends, splits = parse_and_clean_chart_data(parsed, symbol)

                if len(bars) < 200:
                    raise ValueError(f"日线数量不足 ({len(bars)} 条)")

                # 保存原始 JSON
                raw_path = raw_dir / f"{target_id}.json"
                raw_path.write_bytes(raw_bytes)
                raw_sha = hashlib.sha256(raw_bytes).hexdigest()

                # 保存清洗后的标准 JSON 与 CSV
                clean_json_path = clean_dir / f"{target_id}_bars.json"
                clean_json_path.write_text(json.dumps({
                    "symbol": symbol,
                    "target_id": target_id,
                    "market": market,
                    "currency": target["currency"],
                    "bars_count": len(bars),
                    "start_date": bars[0]["date"],
                    "end_date": bars[-1]["date"],
                    "dividends": dividends,
                    "splits": splits,
                    "bars": bars
                }, ensure_ascii=False, indent=2), encoding="utf-8")

                clean_csv_path = clean_dir / f"{target_id}_bars.csv"
                with open(clean_csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=["date", "open", "high", "low", "close", "adj_close", "volume"])
                    writer.writeheader()
                    for b in bars:
                        writer.writerow({
                            "date": b["date"],
                            "open": b["open"],
                            "high": b["high"],
                            "low": b["low"],
                            "close": b["close"],
                            "adj_close": b["adj_close"],
                            "volume": b["volume"]
                        })

                # 登记 LocalStore 目录
                acquired_at = datetime.now(timezone.utc).isoformat()
                manifest = {
                    "schema_version": "1.1.0",
                    "source_id": f"strategy-price-{target_id}-{stamp}",
                    "revision": 1,
                    "source_path": raw_path.relative_to(ROOT).as_posix(),
                    "source_kind": "secondary",
                    "dataset_kind": "market",
                    "published_at": None,
                    "available_at": acquired_at,
                    "acquired_at": acquired_at,
                    "effective_period": {
                        "start": bars[0]["date"],
                        "end": bars[-1]["date"]
                    },
                    "license_notes": "Yahoo public historical response archived for local quantitative research only; no redistribution asserted.",
                    "quality_notes": [
                        f"Source URL: {final_url}",
                        f"Cleaned bars count: {len(bars)} ({bars[0]['date']} -> {bars[-1]['date']})",
                        f"Dividends events: {len(dividends)}, Splits events: {len(splits)}"
                    ],
                    "supersedes_revision": None,
                    "published_date": None,
                    "publication_precision": "unknown"
                }

                manifest_path = manifests_dir / f"{target_id}.manifest.json"
                manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

                reg_result = store.register_source(manifest)

                collection["sources"].append({
                    "id": target_id,
                    "symbol": symbol,
                    "name_zh": name_zh,
                    "market": market,
                    "currency": target["currency"],
                    "is_benchmark": target.get("is_benchmark", False),
                    "bars_count": len(bars),
                    "start_date": bars[0]["date"],
                    "end_date": bars[-1]["date"],
                    "dividends_count": len(dividends),
                    "splits_count": len(splits),
                    "raw_path": raw_path.relative_to(ROOT).as_posix(),
                    "clean_json": clean_json_path.relative_to(ROOT).as_posix(),
                    "clean_csv": clean_csv_path.relative_to(ROOT).as_posix(),
                    "raw_sha256": raw_sha,
                    "registration": reg_result
                })

                print(f" 完成! [有效K线: {len(bars):>4} 条, 分红: {len(dividends):>2} 次, 拆股: {len(splits):>2} 次]")
                time.sleep(0.3)  # 礼貌延迟，防止频控

            except Exception as e:
                err_msg = f"{type(e).__name__}: {e}"
                print(f" 失败! [{err_msg}]")
                collection["failures"].append({
                    "id": target_id,
                    "symbol": symbol,
                    "error": err_msg
                })

        # 写入批次采集汇总
        summary_path = out_dir / "collection.json"
        summary_path.write_text(json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8")

        # 同时维护当前最新的符号链接/固定快照文件
        latest_pointer = ROOT / "data/history/strategy_execution_inputs/latest_collection.json"
        latest_pointer.write_text(json.dumps({
            "latest_capture_id": stamp,
            "collection_path": summary_path.relative_to(ROOT).as_posix(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "successful_sources": len(collection["sources"]),
            "failed_sources": len(collection["failures"])
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        print("-" * 90)
        print(f"采集汇总: 成功归档 {len(collection['sources'])} 份, 失败 {len(collection['failures'])} 份")
        print(f"采集底账: {summary_path.relative_to(ROOT).as_posix()}")
        print("=" * 90)

    finally:
        store.close()

    return 0 if not collection["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
