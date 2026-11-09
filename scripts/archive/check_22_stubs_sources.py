import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
audit_file = ROOT / "data" / "audits" / "drive_stubs_audit.json"
data = json.loads(audit_file.read_text(encoding="utf-8"))

target_tickers = [f["name"].split("_")[0].strip().upper() for f in data["us_stubs_alone"]]
print(f"Target 22 tickers to check:", target_tickers)

# Check all data_sources/*dossier*.py
found = {}
for p in (ROOT / "data_sources").glob("*dossier*.py"):
    content = p.read_text(encoding="utf-8", errors="ignore")
    for t in target_tickers:
        if f'"ticker": "{t}"' in content or f'"ticker": \'{t}\'' in content:
            found[t] = p.name

print(f"Already found in data_sources ({len(found)}):", found)
missing = [t for t in target_tickers if t not in found]
print(f"Missing from data_sources ({len(missing)}):", missing)
