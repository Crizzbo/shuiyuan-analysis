"""同步所有已完成批次收据到 gap_manifest_567.json 确保准确性."""
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest_path = ROOT / "data" / "audits" / "drive-deep-analysis-20261012" / "gap_manifest_567.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

all_completed = {}
for p in sorted(glob.glob(str(ROOT / "data" / "audits" / "drive-deep-analysis-20261012" / "batch*-tackle-receipt.json"))):
    rec = json.loads(Path(p).read_text(encoding="utf-8"))
    for r in rec["results"]:
        all_completed[r["ticker"]] = r

print(f"Total completed across batches 1-8: {len(all_completed)}")

for tier in ["P0_flagship_megacap", "P1_core_industry_leader"]:
    if tier in manifest.get("gaps_by_tier", {}):
        for item in manifest["gaps_by_tier"][tier]:
            t = item.get("symbol") or item.get("ticker")
            if t in all_completed:
                item["status"] = "completed_deep_dossier"
                item["new_file_id"] = all_completed[t]["new_file_id"]

for item in manifest.get("all_gap_entries", []):
    t = item.get("symbol") or item.get("ticker")
    if t in all_completed:
        item["status"] = "completed_deep_dossier"
        item["new_file_id"] = all_completed[t]["new_file_id"]

rem = [x for x in manifest["all_gap_entries"] if x.get("status") != "completed_deep_dossier"]
manifest["verified_companies_count"] = 38 + len(all_completed)
manifest["gap_companies_count"] = len(rem)
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Manifest synced! Verified count: {manifest['verified_companies_count']}, Remaining gaps: {len(rem)}")
