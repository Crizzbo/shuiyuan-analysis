import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

analyzed = set()
for p in (ROOT / "data_sources").glob("*dossier*.py"):
    try:
        c = p.read_text(encoding="utf-8", errors="ignore")
        analyzed.update(re.findall(r'"ticker":\s*"([^"]+)"', c))
    except Exception:
        pass

for p in (ROOT / "scripts").glob("tackle_phase2*.py"):
    try:
        c = p.read_text(encoding="utf-8", errors="ignore")
        analyzed.update(re.findall(r'"ticker":\s*"([^"]+)"', c))
    except Exception:
        pass

jpx_file = ROOT / "data" / "universe" / "jpx_company_tickers.json"
jpx = json.loads(jpx_file.read_text(encoding="utf-8"))
items = jpx if isinstance(jpx, list) else list(jpx.values())

un = []
for item in items:
    code = str(item.get("code") or item.get("ticker", "")).replace("TYO:", "").strip()
    name = item.get("name") or item.get("title") or item.get("company_name", "")
    if code and code not in analyzed:
        un.append((code, name))

print(f"Total unanalyzed JPX: {len(un)}")
for c, n in un[:20]:
    print(f"  JP:{c} -> {n}")
