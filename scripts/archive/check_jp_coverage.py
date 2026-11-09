import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

analyzed_jp = set()
for p in (ROOT / "data_sources").glob("*dossier*.py"):
    c = p.read_text(encoding="utf-8", errors="ignore")
    # find 4-digit tickers
    for m in re.finditer(r'"ticker":\s*"(\d{4})"', c):
        analyzed_jp.add(m.group(1))

print(f"Analyzed JP tickers: {len(analyzed_jp)}")

raw_jp = json.load(open(ROOT / "data/universe/jpx_company_tickers.json", encoding="utf-8"))
print(f"Total JPX tickers: {len(raw_jp)}")

# Check key Japanese tickers
key_jp = [
    ("6857", "Advantest"),
    ("6920", "Lasertec"),
    ("8035", "Tokyo Electron"),
    ("6146", "Disco"),
    ("6861", "Keyence"),
    ("4063", "Shin-Etsu Chemical"),
    ("6758", "Sony"),
    ("7203", "Toyota"),
    ("9984", "SoftBank Group"),
    ("9983", "Fast Retailing"),
    ("6501", "Hitachi"),
    ("7741", "HOYA"),
    ("6367", "Daikin"),
    ("4568", "Daiichi Sankyo"),
    ("6902", "Denso"),
    ("8058", "Mitsubishi Corp"),
    ("8001", "ITOCHU"),
    ("8031", "Mitsui & Co")
]

for code, name in key_jp:
    status = "YES" if code in analyzed_jp else "NO"
    print(f"  [{status}] {code} - {name}")
