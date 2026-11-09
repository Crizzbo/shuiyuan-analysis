import os
import re
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 1. Collect all tickers from data_sources/*dossier*.py
analyzed_tickers = set()
for p in (ROOT / "data_sources").glob("*dossier*.py"):
    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
        tickers = re.findall(r'"ticker":\s*"([^"]+)"', content)
        analyzed_tickers.update(tickers)
    except Exception as e:
        pass

# Also check phase2
for p in (ROOT / "scripts").glob("tackle_phase2*.py"):
    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
        tickers = re.findall(r'"ticker":\s*"([^"]+)"', content)
        analyzed_tickers.update(tickers)
    except Exception:
        pass

print(f"Total tickers analyzed so far: {len(analyzed_tickers)}")

# 2. Check sec_company_tickers.json
sec_path = ROOT / "data" / "universe" / "sec_company_tickers.json"
sec_tickers = {}
if sec_path.exists():
    try:
        raw = json.loads(sec_path.read_text(encoding="utf-8"))
        # format could be dict of dicts: {"0": {"cik_str": ..., "ticker": "...", "title": "..."}}
        for k, v in raw.items():
            if isinstance(v, dict) and "ticker" in v:
                sec_tickers[v["ticker"].upper()] = v.get("title", "")
    except Exception as e:
        print("Error parsing sec tickers:", e)

print(f"Total SEC tickers in universe: {len(sec_tickers)}")

# 3. Check jpx_company_tickers.json
jpx_path = ROOT / "data" / "universe" / "jpx_company_tickers.json"
jpx_tickers = {}
if jpx_path.exists():
    try:
        raw = json.loads(jpx_path.read_text(encoding="utf-8"))
        items = raw if isinstance(raw, list) else list(raw.values())
        for v in items:
            if isinstance(v, dict):
                code = str(v.get("code") or v.get("ticker", "")).replace("TYO:", "").strip()
                if code:
                    jpx_tickers[code] = v.get("name", "") or v.get("title", "") or v.get("company_name", "")
    except Exception as e:
        print("Error parsing jpx tickers:", e)

print(f"Total JPX tickers in universe: {len(jpx_tickers)}")

# Find high-value candidate companies not yet in analyzed_tickers
candidates_us = [
    "UBER", "NOW", "PANW", "FTNT", "SHOP", "COIN", "SNOW", "HOOD", "ZS",
    "SQ", "SE", "PDD", "BIDU", "NTES", "BABA", "JD", "LI", "NIO", "XPEV",
    "ANET", "MRVL", "KLAC", "LRCX", "AMAT", "CDNS", "SNPS", "MCHP", "ON",
    "NXPI", "MDB", "TEAM", "WDAY", "HUBS", "TTD", "APP", "PINS", "SNAP"
]

missing_cands = [c for c in candidates_us if c not in analyzed_tickers]
print(f"Missing top US growth/tech candidates ({len(missing_cands)}):", missing_cands[:15])
