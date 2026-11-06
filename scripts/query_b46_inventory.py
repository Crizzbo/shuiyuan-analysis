import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
inv_file = ROOT / "data" / "audits" / "drive-deep-analysis-20261012" / "inventory.json"
manifest_file = ROOT / "data" / "audits" / "drive-deep-analysis-20261012" / "gap_manifest_567.json"

inv = json.loads(inv_file.read_text(encoding="utf-8"))
items = inv.get("files", [])

d = json.loads(manifest_file.read_text(encoding="utf-8"))
entries = d.get("all_gap_entries", [])
pending = [x for x in entries if not x.get("status")]

top10 = pending[:10]

print("Batch 46 Candidates details:")
for i, c in enumerate(top10):
    sym = c["symbol"]
    mkt = c["market"]
    fname = c["file_name"]
    matches = [f for f in items if f.get("title", "").startswith(f"{sym}_")]
    match_id = matches[0]["id"] if matches else "NONE"
    match_title = matches[0]["title"] if matches else fname
    print(f"{i+1}. {mkt}: {sym} | Old ID: {match_id} | Title: {match_title}")
