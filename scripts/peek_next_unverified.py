"""查询剩余待攻坚公司及其在 inventory.json 中的云端 ID 和文件名."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
inv_path = ROOT / "data" / "audits" / "drive-deep-analysis-20261012" / "inventory.json"
manifest_path = ROOT / "data" / "audits" / "drive-deep-analysis-20261012" / "gap_manifest_567.json"

inv = json.loads(inv_path.read_text(encoding="utf-8"))["files"]
ticker_map = {}
for f in inv:
    name = f.get("title") or f.get("name", "")
    parts = name.split("_")
    if parts:
        ticker = parts[0].strip().upper()
        ticker_map[ticker] = (name, f["id"])

manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
rem = [x for x in manifest["all_gap_entries"] if x.get("status") != "completed_deep_dossier"]

print(f"Total remaining gaps: {len(rem)}")
print("-" * 80)
for i, item in enumerate(rem[:25]):
    sym = (item.get("ticker") or item.get("symbol", "")).upper()
    mkt = item.get("market", "US")
    name, cid = ticker_map.get(sym, ("NOT_FOUND", "NONE"))
    print(f"{i+1:2d}. [{mkt}] {sym:<6} -> {name} | Cloud ID: {cid}")
