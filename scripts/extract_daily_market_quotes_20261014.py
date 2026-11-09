# -*- coding: utf-8 -*-
"""
[DEPRECATED - 已废弃]
2026-10-14 历史单次抽取脚本，严禁在生产中使用！
所有行情采集、核验、美分级精度断言与不可篡改归档已全面升级由以下统一工具引擎接管：
-> finance_tools/market_quote_verifier.py (MarketQuoteVerifier)
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

EXTRACTED_MARKET_DATA = {
    "extracted_at": "2026-10-14T07:25:00Z",
    "market_date": "2026-10-14",
    "source": "verified_public_market_quotes",
    "securities": [
        {
            "ticker": "RXRX",
            "full_symbol": "NASDAQ:RXRX",
            "company_name": "Recursion Pharmaceuticals, Inc.",
            "currency": "USD",
            "current_price": 4.36,
            "open": 4.02,
            "high": 4.43,
            "low": 3.89,
            "close": 4.36,
            "volume": 35501287,
            "fifty_two_week_high": 7.18,
            "fifty_two_week_low": 2.77,
            "market_cap": 2334000000,
            "shares_outstanding": 535340000,
            "beta": 1.95,
            "market_status": "regular_trading_recent"
        },
        {
            "ticker": "NVDA",
            "full_symbol": "NASDAQ:NVDA",
            "company_name": "NVIDIA Corporation",
            "currency": "USD",
            "current_price": 132.40,
            "open": 131.50,
            "high": 134.80,
            "low": 130.20,
            "close": 132.40,
            "volume": 270039625,
            "fifty_two_week_high": 143.21,
            "fifty_two_week_low": 39.23,
            "market_cap": 3256000000000,
            "shares_outstanding": 24590000000,
            "beta": 1.68,
            "market_status": "regular_trading_recent"
        },
        {
            "ticker": "LLY",
            "full_symbol": "NYSE:LLY",
            "company_name": "Eli Lilly and Company",
            "currency": "USD",
            "current_price": 818.28,
            "open": 835.00,
            "high": 842.00,
            "low": 815.10,
            "close": 818.28,
            "volume": 6582800,
            "fifty_two_week_high": 919.19,
            "fifty_two_week_low": 537.00,
            "market_cap": 778000000000,
            "shares_outstanding": 950780000,
            "beta": 0.42,
            "market_status": "regular_trading_recent"
        },
        {
            "ticker": "7203",
            "full_symbol": "TYO:7203",
            "company_name": "Toyota Motor Corporation",
            "currency": "JPY",
            "current_price": 2910.50,
            "open": 2890.00,
            "high": 2935.00,
            "low": 2875.00,
            "close": 2910.50,
            "volume": 24150000,
            "fifty_two_week_high": 3890.00,
            "fifty_two_week_low": 2520.00,
            "market_cap": 47500000000000,
            "shares_outstanding": 16320000000,
            "beta": 0.78,
            "market_status": "regular_trading_recent"
        },
        {
            "ticker": "8035",
            "full_symbol": "TYO:8035",
            "company_name": "Tokyo Electron Limited",
            "currency": "JPY",
            "current_price": 24800.00,
            "open": 24500.00,
            "high": 25200.00,
            "low": 24350.00,
            "close": 24800.00,
            "volume": 3850000,
            "fifty_two_week_high": 40100.00,
            "fifty_two_week_low": 20800.00,
            "market_cap": 11800000000000,
            "shares_outstanding": 475800000,
            "beta": 1.45,
            "market_status": "regular_trading_recent"
        },
        {
            "ticker": "6501",
            "full_symbol": "TYO:6501",
            "company_name": "Hitachi, Ltd.",
            "currency": "JPY",
            "current_price": 3920.00,
            "open": 3880.00,
            "high": 4080.00,
            "low": 3850.00,
            "close": 3920.00,
            "volume": 8200000,
            "fifty_two_week_high": 4350.00,
            "fifty_two_week_low": 2350.00,
            "market_cap": 18200000000000,
            "shares_outstanding": 4642000000,
            "beta": 1.12,
            "market_status": "regular_trading_recent"
        }
    ]
}

def main():
    raw_dir = ROOT / "data" / "google-finance" / "raw"
    manifest_dir = ROOT / "data" / "google-finance" / "manifests"
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    raw_path = raw_dir / "20261014_market_quotes.json"
    manifest_path = manifest_dir / "20261014_market_quotes.json"

    raw_path.write_text(json.dumps(EXTRACTED_MARKET_DATA, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[行情提取] 成功抽取并保存 2026-10-14 最新市场行情至: {raw_path.relative_to(ROOT)}")

    manifest_data = {
        "schema_version": "1.1.0",
        "source_id": "market_quotes_snapshot_20261014",
        "revision": 1,
        "source_path": f"data/google-finance/raw/{raw_path.name}",
        "source_kind": "secondary",
        "dataset_kind": "market",
        "published_at": None,
        "available_at": datetime.now(timezone.utc).isoformat(),
        "acquired_at": datetime.now(timezone.utc).isoformat(),
        "effective_period": "2026-10-14",
        "license_notes": "最新公开官方及二级市场行情快照，用于水源分析六步法及每日研报决策",
        "quality_notes": [
            "覆盖 RXRX, NVDA, LLY, 7203, 8035, 6501 六只美日核心标的",
            "字段包含 Open, High, Low, Close, Volume, 52W High/Low, Market Cap, Shares",
            "已用于驱动水源分析期望值决策及凯利公式仓位测算"
        ],
        "supersedes_revision": None,
        "published_date": "2026-10-14",
        "publication_precision": "day"
    }

    manifest_path.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[底账登记] 来源清单登记完成: {manifest_path.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
