import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("data/audits/drive-deep-analysis-20261012/cloud-replacement-receipt.json", encoding="utf-8") as f:
    d = json.load(f)

targets = sys.argv[1:] if len(sys.argv) > 1 else ['CRM', 'ADBE', 'TXN', 'CSCO', 'HD', '8306', '8058', '4568', '6367', '6501']
files = d.get('uploaded_files', [])
found = {it.get('symbol'): it for it in files}

for t in targets:
    it = found.get(t, {})
    print(f"{t} | {it.get('market')} | {it.get('new_file_id')} | {it.get('file_name')}")
