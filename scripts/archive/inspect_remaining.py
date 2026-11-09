import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json


# Load all completed tickers up to Batch 54 + Batch 55
completed = set()
audit_dir = Path("data/audits/drive-deep-analysis-20261012")
for f in audit_dir.glob("*-receipt.json"):
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        for r in data.get("results", []):
            completed.add((r.get("market"), r.get("ticker")))
    except Exception:
        pass

from data_sources.batch55_verified_dossiers_data import BATCH55_DOSSIERS
for item in BATCH55_DOSSIERS:
    completed.add((item["overview"]["market"], item["overview"]["ticker"]))

# Read pending files from manifest / inventory
inv = json.loads(Path("data/audits/drive-deep-analysis-20261012/inventory.json").read_text(encoding="utf-8"))
files = inv.get("files", [])

remaining = []
for f in files:
    name = f.get("name", "")
    parent = f.get("parent_id", "")
    market = "JP" if parent == "CONFIGURE_YOUR_OWN_CLOUD_TARGET" else "US"
    if "_" in name:
        ticker = name.split("_")[0]
        if (market, ticker) not in completed:
            remaining.append({
                "id": f.get("id"),
                "name": name,
                "market": market,
                "ticker": ticker,
                "size": f.get("size")
            })

# Deduplicate remaining by (market, ticker)
seen = set()
unique_rem = []
for r in remaining:
    key = (r["market"], r["ticker"])
    if key not in seen:
        seen.add(key)
        unique_rem.append(r)

print(f"Remaining total unique tickers: {len(unique_rem)}")
for i, r in enumerate(unique_rem):
    print(f"{i+1:02d}. [{r['market']}] {r['ticker']}: {r['name']} | ID: {r['id']}")
