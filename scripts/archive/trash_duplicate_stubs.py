import json
import subprocess
import sys
import time
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

audit_file = ROOT / "data" / "audits" / "drive_stubs_audit.json"
data = json.loads(audit_file.read_text(encoding="utf-8"))

us_stubs = data["us_stubs_with_real"]
jp_stubs = data["jp_stubs_with_real"]

all_to_trash = us_stubs + jp_stubs
print("=" * 70)
print(f"[清理启动] 启动云端残余存根清理流水线 | 待清理总数: {len(all_to_trash)} 个 (US: {len(us_stubs)}, JP: {len(jp_stubs)})")
print("=" * 70)

success_count = 0
failed_count = 0

for idx, item in enumerate(all_to_trash):
    fid = item["id"]
    name = item["name"]
    cmd = [GDRIVE_EXE, "mutate", "trash", fid, "--json"]
    cp = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if cp.returncode == 0:
        success_count += 1
        if (idx + 1) % 20 == 0 or idx == len(all_to_trash) - 1:
            print(f"  [{idx+1}/{len(all_to_trash)}] 已移入回收站: {name}")
    else:
        failed_count += 1
        print(f"  [清理失败] 移入回收站失败 ({name}): {cp.stderr.strip()[:60]}")

print("\n" + "=" * 70)
print(f"[清理完成] 残余存根清理完毕: 成功清理 {success_count} 个, 失败 {failed_count} 个")
print("=" * 70)
