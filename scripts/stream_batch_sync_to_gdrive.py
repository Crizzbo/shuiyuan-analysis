"""流式分批并发上传引擎 (Streaming Concurrent Chunk-and-Upload Engine).

支持多线程并发上传，边渲染边分批同步至 Google Drive AmericanStock 文件夹。
文件名严格遵循【股票代码】_【中文名称】.pdf 规范。
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PARENT_FOLDER_ID = "CONFIGURE_YOUR_OWN_CLOUD_TARGET"


def run_gdrive(cmd_args):
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
    ls_out, _, code = run_gdrive(["gdrive", "readonly", "ls", parent_id, "--max", "0", "--json"])
    if code == 0 and ls_out:
        try:
            items = json.loads(ls_out)
            for item in items:
                if item.get("name") == folder_name:
                    return item["id"]
        except Exception:
            pass
    mkdir_out, err, code = run_gdrive(["gdrive", "mutate", "mkdir", folder_name, "--parent", parent_id])
    if code == 0 and mkdir_out:
        m = re.search(r"\(ID:\s*([a-zA-Z0-9_-]+)\)", mkdir_out)
        if m:
            return m.group(1)
        try:
            data = json.loads(mkdir_out)
            return data["id"]
        except Exception:
            pass
    raise RuntimeError(f"无法在 {parent_id} 下创建文件夹 {folder_name}: {err or mkdir_out}")


def list_remote_files(folder_id: str) -> set:
    ls_out, _, code = run_gdrive(["gdrive", "readonly", "ls", folder_id, "--max", "0", "--json"])
    res = set()
    if code == 0 and ls_out:
        try:
            items = json.loads(ls_out)
            for it in items:
                if "name" in it:
                    res.add(it["name"])
        except Exception:
            pass
    return res


def upload_single_worker(item):
    pdf_path, parent_id = item
    out, err, code = run_gdrive(["gdrive", "mutate", "upload", str(pdf_path), "--parent", parent_id, "--mime-type", "application/pdf"])
    return pdf_path.name, code == 0


def main():
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"[流式上传启动] 目标: AmericanStock ({PARENT_FOLDER_ID})")

    # 1. 确保目录结构
    daily_root_id = get_or_create_folder("每日行情分析", PARENT_FOLDER_ID)
    dossiers_root_id = get_or_create_folder("公司深度分析档案", PARENT_FOLDER_ID)

    today_folder_id = get_or_create_folder(today_str, daily_root_id)
    dossiers_us_id = get_or_create_folder("US", dossiers_root_id)
    dossiers_jp_id = get_or_create_folder("JP", dossiers_root_id)

    # 获取远端现有文件 (防止重复上传)
    remote_today = list_remote_files(today_folder_id)
    remote_us = list_remote_files(dossiers_us_id)
    remote_jp = list_remote_files(dossiers_jp_id)

    print(f"[底账就绪] 远端底账就绪: 今日研报已存 {len(remote_today)} 份, US已存 {len(remote_us)} 份, JP已存 {len(remote_jp)} 份")

    # 2. 确保大盘研报已上传
    briefing_dir = ROOT / "reports" / "samples_for_review"
    for b_name in [f"{today_str}_美股市场每日总行情与推荐_v3.pdf", f"{today_str}_日股市场每日总行情与推荐_v3.pdf"]:
        b_path = briefing_dir / b_name
        if b_path.exists() and b_name not in remote_today:
            print(f"[大盘同步] 正在上传: {b_name}...")
            if upload_single_worker((b_path, today_folder_id))[1]:
                print(f"  [完成] [大盘研报同步成功] {b_name}")
                remote_today.add(b_name)

    # 3. 流式分批并发上传深度档案
    dossier_dist = ROOT / "reports" / "dossiers_dist"
    batch_num = 1

    while True:
        us_pending = [p for p in sorted((dossier_dist / "US").glob("*.pdf")) if p.name not in remote_us]
        jp_pending = [p for p in sorted((dossier_dist / "JP").glob("*.pdf")) if p.name not in remote_jp]

        total_pending = len(us_pending) + len(jp_pending)
        if total_pending > 0:
            print(f"\n[批次触发] 触发第 {batch_num} 批流式并发上传: 待同步 {total_pending} 份新档案 (US: {len(us_pending)}, JP: {len(jp_pending)})...")

            # 取当前批次 (最多 30 个任务)
            tasks = []
            for p in us_pending[:20]:
                tasks.append((p, dossiers_us_id, "US"))
            for p in jp_pending[:10]:
                tasks.append((p, dossiers_jp_id, "JP"))

            # 6 线程并发上传当前批次
            with ThreadPoolExecutor(max_workers=6) as executor:
                future_map = {executor.submit(upload_single_worker, (t[0], t[1])): t for t in tasks}
                for fut in as_completed(future_map):
                    t = future_map[fut]
                    fname, ok = fut.result()
                    mkt = t[2]
                    if ok:
                        if mkt == "US":
                            remote_us.add(fname)
                        else:
                            remote_jp.add(fname)
                        print(f"  [完成] [同步成功] [{mkt}] {fname}")
                    else:
                        print(f"  [警告] [同步失败] [{mkt}] {fname}")

            batch_num += 1
        else:
            total_uploaded = len(remote_us) + len(remote_jp)
            print(f"\n[全量完成] 全量流式上传圆满完成: 场景 2 全量 {total_uploaded} 份公司深度档案与每日研报已全部同步至 Google Drive！")
            break

        time.sleep(2)


if __name__ == "__main__":
    main()
