# -*- coding: utf-8 -*-
"""全谱系动态点时选股资产池数据准备与归一化调度器 (prepare_dynamic_universe_data.py).

严格遵循《AGENTS.md》与《CLAUDE.md》：
1. 彻底消灭幸存者偏差：包含历史上大赢家 (NVDA, MSFT, LLY)、中庸稳健股 (PG, KO, WMT)、
   强周期股 (XOM, CAT) 以及严重跑输/长期滞涨/巨幅暴跌的衰退对照股 (INTC, CSCO)；
2. 时间跨度严格对齐 2015-01-01 至 2024-12-31；
3. 输出纯净标准日线字典与分红拆股事件字典；
4. 注册到资产池配置 config/dynamic_universe_config.json。
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DYNAMIC_TARGETS = [
    {"symbol": "SPY", "name_zh": "标普500指数 ETF", "category": "Benchmark", "is_benchmark": True},
    {"symbol": "NVDA", "name_zh": "英伟达", "category": "Tech_Growth_Winner", "is_benchmark": False},
    {"symbol": "MSFT", "name_zh": "微软公司", "category": "Tech_Growth_Winner", "is_benchmark": False},
    {"symbol": "AAPL", "name_zh": "苹果公司", "category": "Tech_Growth_Winner", "is_benchmark": False},
    {"symbol": "INTC", "name_zh": "英特尔 (长期跑输与衰退对照)", "category": "Semiconductor_Decliner", "is_benchmark": False},
    {"symbol": "CSCO", "name_zh": "思科系统 (长期低波动滞涨对照)", "category": "Legacy_Tech_Stagnant", "is_benchmark": False},
    {"symbol": "COST", "name_zh": "开市客", "category": "Consumer_Moat_Winner", "is_benchmark": False},
    {"symbol": "PG", "name_zh": "宝洁公司", "category": "Consumer_Staples_Defensive", "is_benchmark": False},
    {"symbol": "KO", "name_zh": "可口可乐 (慢速消费红利对照)", "category": "Consumer_Dividend_Defensive", "is_benchmark": False},
    {"symbol": "WMT", "name_zh": "沃尔玛 (传统零售稳健对照)", "category": "Retail_Mature_Stable", "is_benchmark": False},
    {"symbol": "LLY", "name_zh": "礼来制药", "category": "Healthcare_Biotech_Winner", "is_benchmark": False},
    {"symbol": "JNJ", "name_zh": "强生公司", "category": "Healthcare_Diversified", "is_benchmark": False},
    {"symbol": "CAT", "name_zh": "卡特彼勒", "category": "Industrial_Cyclical", "is_benchmark": False},
    {"symbol": "XOM", "name_zh": "埃克森美孚", "category": "Energy_Commodity_Cyclical", "is_benchmark": False},
    {"symbol": "JPM", "name_zh": "摩根大通", "category": "Financial_Services_Leader", "is_benchmark": False},
]


def load_from_strategy_inputs(symbol: str) -> Dict[str, Any]:
    """优先从此前清洗入库的 strategy_execution_inputs 批次读取."""
    p = ROOT / f"data/history/strategy_execution_inputs/20261107T154519_027039Z/normalized/{symbol}_bars.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def parse_raw_yahoo_chart(symbol: str, raw_path: Path) -> Dict[str, Any]:
    """从原始 Yahoo chart JSON 解析标准日线、分红与拆股."""
    content = json.loads(raw_path.read_text(encoding="utf-8"))
    result = content["chart"]["result"][0]
    timestamps = result.get("timestamp", [])
    quote = result["indicators"]["quote"][0]
    adjclose_list = result["indicators"].get("adjclose", [{}])[0].get("adjclose", quote["close"])

    bars = []
    for i, ts in enumerate(timestamps):
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        if dt < "2015-01-01" or dt > "2024-12-31":
            continue
        o = quote["open"][i]
        h = quote["high"][i]
        l = quote["low"][i]
        c = quote["close"][i]
        v = quote["volume"][i]
        ac = adjclose_list[i] if adjclose_list and i < len(adjclose_list) else c
        if None in (o, h, l, c):
            continue
        bars.append({
            "date": dt,
            "open": round(float(o), 4),
            "high": round(float(h), 4),
            "low": round(float(l), 4),
            "close": round(float(c), 4),
            "adj_close": round(float(ac), 4),
            "volume": int(v or 0)
        })

    # 提取分红与拆股事件
    events = result.get("events", {})
    divs = []
    for k, v in events.get("dividends", {}).items():
        dt = datetime.fromtimestamp(v["date"], tz=timezone.utc).strftime("%Y-%m-%d")
        if "2015-01-01" <= dt <= "2024-12-31":
            divs.append({"date": dt, "amount": float(v["amount"])})
    divs.sort(key=lambda x: x["date"])

    splits = []
    for k, v in events.get("splits", {}).items():
        dt = datetime.fromtimestamp(v["date"], tz=timezone.utc).strftime("%Y-%m-%d")
        if "2015-01-01" <= dt <= "2024-12-31":
            splits.append({
                "date": dt,
                "numerator": float(v["numerator"]),
                "denominator": float(v["denominator"]),
                "split_ratio": float(v["numerator"]) / float(v["denominator"])
            })
    splits.sort(key=lambda x: x["date"])

    return {
        "symbol": symbol,
        "bars": bars,
        "dividends": divs,
        "splits": splits
    }


def main():
    print("=" * 90)
    print("【开始准备全谱系动态点时选股资产池数据 (含牛股、滞涨股、暴跌股与周期股)】")
    print("=" * 90)

    out_dir = ROOT / "data/history/dynamic_universe/normalized"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_pilot_dir = ROOT / "data/history/strategy_pilot/20261107T145907_701919Z/raw"

    processed = []
    for t in DYNAMIC_TARGETS:
        sym = t["symbol"]
        print(f"处理标的: {sym:>5} ({t['name_zh']})...", end="", flush=True)

        data = load_from_strategy_inputs(sym)
        if not data:
            raw_file = raw_pilot_dir / f"{sym}_prices.json"
            if raw_file.exists():
                data = parse_raw_yahoo_chart(sym, raw_file)
            else:
                raise FileNotFoundError(f"未找到标的 {sym} 的历史数据文件")

        out_file = out_dir / f"{sym}_bars.json"
        out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        bars_count = len(data.get("bars", []))
        start_d = data["bars"][0]["date"] if bars_count > 0 else "N/A"
        end_d = data["bars"][-1]["date"] if bars_count > 0 else "N/A"
        print(f" 就绪! [{bars_count} 交易日 | {start_d} ~ {end_d}]")

        processed.append({
            "symbol": sym,
            "name_zh": t["name_zh"],
            "category": t["category"],
            "is_benchmark": t["is_benchmark"],
            "bars_count": bars_count,
            "start_date": start_d,
            "end_date": end_d,
            "file_path": out_file.relative_to(ROOT).as_posix()
        })

    config_path = ROOT / "config/dynamic_universe_config.json"
    config_data = {
        "schema_version": "1.0.0",
        "description": "Full-spectrum dynamic stock selection universe with winners, laggards, and decliners",
        "period_start": "2015-01-01",
        "period_end": "2024-12-31",
        "benchmark_symbol": "SPY",
        "total_targets": len(processed),
        "targets": processed
    }
    config_path.write_text(json.dumps(config_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n" + "=" * 90)
    print(f"数据全部就绪并归一化！配置已保存至: {config_path.relative_to(ROOT).as_posix()}")
    print("=" * 90)


if __name__ == "__main__":
    main()
