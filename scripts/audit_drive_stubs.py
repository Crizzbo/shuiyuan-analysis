import json
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
from scripts.env_discovery import get_gdrive_executable
GDRIVE_EXE = get_gdrive_executable()

FOLDER_US = "CONFIGURE_YOUR_OWN_CLOUD_TARGET"
FOLDER_JP = "CONFIGURE_YOUR_OWN_CLOUD_TARGET"

def get_folder_files(folder_id):
    cmd = [GDRIVE_EXE, "readonly", "ls", folder_id, "--max", "0", "--json"]
    cp = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if cp.returncode != 0:
        print(f"Error reading folder {folder_id}: {cp.stderr}")
        return []
    try:
        return json.loads(cp.stdout)
    except Exception as e:
        print(f"Error parsing JSON for {folder_id}: {e}")
        return []

print("[审计扫描] 正在扫描 Google Drive [公司深度分析/US] ...")
us_files = get_folder_files(FOLDER_US)
print(f"  US 总文件数: {len(us_files)}")

print("[审计扫描] 正在扫描 Google Drive [公司深度分析/JP] ...")
jp_files = get_folder_files(FOLDER_JP)
print(f"  JP 总文件数: {len(jp_files)}")

# Categorize files by size
# Real deep dossiers are >= 200 KB (typically 500 KB - 1 MB)
# Small stubs/evidence files are < 100 KB (typically 35 KB - 45 KB)

us_stubs = [f for f in us_files if int(f.get("size", 0)) < 150000]
us_real = [f for f in us_files if int(f.get("size", 0)) >= 150000]

jp_stubs = [f for f in jp_files if int(f.get("size", 0)) < 150000]
jp_real = [f for f in jp_files if int(f.get("size", 0)) >= 150000]

print("\n" + "=" * 60)
print(f"[审计结果] 云端文件深度审计结果:")
print(f"  US: 真实研报 ({len(us_real)} 份) | 旧存根证据 ({len(us_stubs)} 份)")
print(f"  JP: 真实研报 ({len(jp_real)} 份) | 旧存根证据 ({len(jp_stubs)} 份)")
print("=" * 60)

# Check which stubs have a corresponding real file already
def extract_ticker(name):
    return name.split("_")[0].strip().upper()

us_real_tickers = set(extract_ticker(f["name"]) for f in us_real)
us_stubs_with_real = [f for f in us_stubs if extract_ticker(f["name"]) in us_real_tickers]
us_stubs_alone = [f for f in us_stubs if extract_ticker(f["name"]) not in us_real_tickers]

jp_real_tickers = set(extract_ticker(f["name"]) for f in jp_real)
jp_stubs_with_real = [f for f in jp_stubs if extract_ticker(f["name"]) in jp_real_tickers]
jp_stubs_alone = [f for f in jp_stubs if extract_ticker(f["name"]) not in jp_real_tickers]

print(f"\nUS 存根分析:")
print(f"  - 已经有真实研报、只需清理的残余存根: {len(us_stubs_with_real)} 个")
print(f"  - 尚未有真实研报、仍孤立处于存根状态的企业: {len(us_stubs_alone)} 个")

print(f"\nJP 存根分析:")
print(f"  - 已经有真实研报、只需清理的残余存根: {len(jp_stubs_with_real)} 个")
print(f"  - 尚未有真实研报、仍孤立处于存根状态的企业: {len(jp_stubs_alone)} 个")

# Save detailed inventory
audit_summary = {
    "us_total": len(us_files),
    "us_real_count": len(us_real),
    "us_stubs_count": len(us_stubs),
    "us_stubs_with_real": us_stubs_with_real,
    "us_stubs_alone": us_stubs_alone,
    "jp_total": len(jp_files),
    "jp_real_count": len(jp_real),
    "jp_stubs_count": len(jp_stubs),
    "jp_stubs_with_real": jp_stubs_with_real,
    "jp_stubs_alone": jp_stubs_alone,
}

out_path = ROOT / "data" / "audits" / "drive_stubs_audit.json"
out_path.write_text(json.dumps(audit_summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n[审计落盘] 审计明细已保存至: {out_path.relative_to(ROOT)}")

if us_stubs_alone:
    print("\n[待攻坚的孤立 US 存根标的前 15 个]:")
    for f in us_stubs_alone[:15]:
        print(f"  - {f['name']} (ID: {f['id']}, Size: {f.get('size')} bytes)")

if jp_stubs_alone:
    print("\n[待攻坚的孤立 JP 存根标的前 15 个]:")
    for f in jp_stubs_alone[:15]:
        print(f"  - {f['name']} (ID: {f['id']}, Size: {f.get('size')} bytes)")
