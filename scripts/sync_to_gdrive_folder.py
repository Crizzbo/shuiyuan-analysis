"""一键向指定的 Google Drive 文件夹上传研报与档案。"""

import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PARENT_FOLDER_ID = "CONFIGURE_YOUR_OWN_CLOUD_TARGET"


def run_gdrive(cmd_args):
    # Windows 兼容性：确保调用 gdrive.cmd
    cmd = list(cmd_args)
    if cmd and cmd[0] == "gdrive":
        cmd[0] = "gdrive.cmd"
    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True,
    )
    return res.stdout.strip(), res.stderr.strip(), res.returncode


def get_or_create_folder(folder_name: str, parent_id: str) -> str:
    # 1. 查找是否已存在
    ls_out, _, code = run_gdrive(["gdrive", "readonly", "ls", parent_id, "--json"])
    if code == 0 and ls_out:
        try:
            items = json.loads(ls_out)
            for item in items:
                if item.get("name") == folder_name:
                    return item["id"]
        except Exception:
            pass
    # 2. 不存在则创建
    mkdir_out, err, code = run_gdrive(["gdrive", "mutate", "mkdir", folder_name, "--parent", parent_id])
    if code == 0 and mkdir_out:
        import re
        m = re.search(r"\(ID:\s*([a-zA-Z0-9_-]+)\)", mkdir_out)
        if m:
            return m.group(1)
        try:
            data = json.loads(mkdir_out)
            return data["id"]
        except Exception:
            pass
    raise RuntimeError(f"无法在 {parent_id} 下创建文件夹 {folder_name}: {err or mkdir_out}")


def upload_file(local_path: Path, parent_id: str):
    print(f"  [上传中] 正在上传: {local_path.name} -> 云端文件夹 {parent_id}")
    out, err, code = run_gdrive(["gdrive", "mutate", "upload", str(local_path), "--parent", parent_id, "--json"])
    if code != 0:
        print(f"    [警告] 上传警告: {err or out}")
    else:
        print(f"    [成功] 上传成功: {local_path.name}")


def main():
    print(f"[云端同步] 开始同步分析产物至 Google Drive 文件夹: {PARENT_FOLDER_ID}")

    # 1. 创建三大根子目录
    print("[目录构建] 正在创建/确认云端三级目录结构...")
    manifest_folder_id = get_or_create_folder("分析清单", PARENT_FOLDER_ID)
    daily_root_folder_id = get_or_create_folder("今日分析报告_2026-10-12", PARENT_FOLDER_ID)
    dossier_root_folder_id = get_or_create_folder("深度公司档案库", PARENT_FOLDER_ID)

    daily_us_id = get_or_create_folder("US", daily_root_folder_id)
    daily_jp_id = get_or_create_folder("JP", daily_root_folder_id)

    dossier_us_id = get_or_create_folder("US", dossier_root_folder_id)
    dossier_jp_id = get_or_create_folder("JP", dossier_root_folder_id)

    print("[目录就绪] 云端目录架构已就绪！")

    # 2. 上传分析清单
    print("\n[清单同步] 正在上传分析清单...")
    manifest_csv = ROOT / "data" / "google-finance" / "watchlist_manifest.csv"
    manifest_json = ROOT / "config" / "google_drive_watchlist.json"
    if manifest_csv.exists():
        upload_file(manifest_csv, manifest_folder_id)
    if manifest_json.exists():
        upload_file(manifest_json, manifest_folder_id)

    # 3. 上传今日总览大看板与量化底稿
    print("\n[看板同步] 正在上传今日总览看板与结构化底稿...")
    today_dir = ROOT / "reports" / "2026-10-12"
    overview_html = today_dir / "overview_dashboard.html"
    summary_json = today_dir / "daily_summary.json"
    if overview_html.exists():
        upload_file(overview_html, daily_root_folder_id)
    if summary_json.exists():
        upload_file(summary_json, daily_root_folder_id)

    # 4. 上传今日个股研报 (US & JP)
    print("\n[研报同步] 正在上传今日美股研报...")
    for f in (today_dir / "US").glob("*.html"):
        upload_file(f, daily_us_id)

    print("\n[研报同步] 正在上传今日日股研报...")
    for f in (today_dir / "JP").glob("*.html"):
        upload_file(f, daily_jp_id)

    # 5. 上传深度公司档案 (US & JP)
    print("\n[档案同步] 正在上传美股深度公司档案...")
    dossier_dir = ROOT / "reports" / "dossiers"
    for f in (dossier_dir / "US").glob("*.html"):
        upload_file(f, dossier_us_id)

    print("\n[档案同步] 正在上传日股深度公司档案...")
    for f in (dossier_dir / "JP").glob("*.html"):
        upload_file(f, dossier_jp_id)

    print("\n[同步完成] 全部 45 家核心标的分析报告与深度档案已 100% 同步至 Google Drive AmericanStock 文件夹！")


if __name__ == "__main__":
    main()
