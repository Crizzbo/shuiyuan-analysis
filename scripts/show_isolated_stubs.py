import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
audit_file = ROOT / "data" / "audits" / "drive_stubs_audit.json"
data = json.loads(audit_file.read_text(encoding="utf-8"))

print("=== 22 个孤立的存根标的 (尚未有真实深度分析) ===")
for i, f in enumerate(data["us_stubs_alone"]):
    name = f.get("name")
    fid = f.get("id")
    size = f.get("size")
    print(f"{i+1:2d}. {name:40s} | ID: {fid} | Size: {size} bytes")

print("\n=== 1 个孤立的 JP 存根标的 ===")
for i, f in enumerate(data["jp_stubs_with_real"]):
    print(f"JP 残余: {f['name']} (ID: {f['id']})")
