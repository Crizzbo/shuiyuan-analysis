import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest_file = ROOT / "data" / "audits" / "drive-deep-analysis-20261012" / "gap_manifest_567.json"

data = json.loads(manifest_file.read_text(encoding="utf-8"))
entries = data.get("all_gap_entries", [])

pending = [x for x in entries if not x.get("status")]

print(f"Total pending entries: {len(pending)}")
print("Next 20 candidates:")
for i, c in enumerate(pending[:20]):
    symbol = c.get("symbol")
    market = c.get("market")
    fname = c.get("file_name")
    print(f"{i+1}. [{market}] {symbol}: {fname}")
