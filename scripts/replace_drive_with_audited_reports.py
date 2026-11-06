"""执行云盘假数据撤销与 605 份审计替换版重新上传流水线.

1. 从 reports/replacements/company-data-corrected-20261012.zip 解压 605 份合规 PDF 与 JSON;
2. 同步覆盖本地 reports/dossiers_dist/ (US 与 JP 目录);
3. 批量将 Google Drive 上的 605 份旧假数据移至回收站 (Trash);
4. 批量多线程上传 605 份审计替换版 PDF 到 Google Drive US 与 JP 目录;
5. 生成端到端执行凭证 receipts 归档。
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.env_discovery import get_gdrive_executable
GDRIVE_EXE = get_gdrive_executable()
ZIP_PATH = ROOT / "reports" / "replacements" / "company-data-corrected-20261012.zip"
UNPACK_DIR = ROOT / "reports" / "replacements" / "unpacked"
DOSSIERS_DIST = ROOT / "reports" / "dossiers_dist"

FOLDER_US = "CONFIGURE_YOUR_OWN_CLOUD_TARGET"
FOLDER_JP = "CONFIGURE_YOUR_OWN_CLOUD_TARGET"


def run_cmd(args):
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def trash_old_worker(item):
    old_id = item["old_file_id"]
    name = item["file_name"]
    res = run_cmd([GDRIVE_EXE, "mutate", "trash", old_id, "--json"])
    return old_id, name, res.returncode == 0


def upload_new_worker(item):
    pdf_path = item["pdf_path"]
    parent_id = item["parent_id"]
    market = item["market"]
    name = item["file_name"]
    res = run_cmd([
        GDRIVE_EXE, "mutate", "upload",
        str(pdf_path),
        "--parent", parent_id,
        "--mime-type", "application/pdf",
        "--json",
    ])
    new_id = None
    if res.returncode == 0 and res.stdout:
        # e.g. Uploaded: filename.pdf (ID: 1Jsbr6eW...)
        import re
        m = re.search(r"\(ID:\s*([a-zA-Z0-9_-]+)\)", res.stdout)
        if m:
            new_id = m.group(1)
    return name, market, new_id, res.returncode == 0


def main():
    print("=" * 70)
    print("[管线启动] 云端未核实数据彻底清理与 605 份审计替换版流式重新上传")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    # 1. 解压替换包
    print(f"\n[解压包体] 1. 正在解压审计合规替换包: {ZIP_PATH.name}...")
    UNPACK_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        zf.extractall(UNPACK_DIR)
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))

    files = manifest.get("files", [])
    print(f"  [就绪] 解压就绪: 检索到清单内 {len(files)} 份替换档案 (包含 38 家已有核实字段, 567 家保留数据缺口)")

    # 2. 覆盖本地 dossiers_dist
    print("\n[本地同步] 2. 正在同步更新本地 reports/dossiers_dist 目录...")
    local_updated = 0
    for it in files:
        mkt = it["market"]
        fname = it["file_name"]
        src_pdf = UNPACK_DIR / mkt / fname
        target_pdf = DOSSIERS_DIST / mkt / fname
        if src_pdf.exists():
            shutil.copy2(src_pdf, target_pdf)
            local_updated += 1
    print(f"  [完成] 本地 dossiers_dist 覆盖完成: 共更新 {local_updated} 份本地标准档案")

    # 3. 批量删除云盘旧假数据 (8 线程并发)
    print(f"\n[清理存根] 3. 正在以 8 线程并发将 Google Drive 上 {len(files)} 份未核实数据移入回收站...")
    trash_success = 0
    trash_fail = 0
    t0_trash = time.perf_counter()

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(trash_old_worker, it): it for it in files}
        total = len(futures)
        done = 0
        for fut in as_completed(futures):
            old_id, name, ok = fut.result()
            done += 1
            if ok:
                trash_success += 1
            else:
                trash_fail += 1
            if done % 100 == 0 or done == total:
                print(f"  [清理进度] {done}/{total} 已处理 (成功移入回收站: {trash_success}, 失败: {trash_fail})")

    t_trash = time.perf_counter() - t0_trash
    print(f"  [完成] 旧数据清理完成！耗时: {t_trash:.1f} 秒 (成功删除: {trash_success} 份)")

    # 4. 批量重新上传 605 份新版审计档案 (8 线程并发)
    print(f"\n[并发上传] 4. 正在以 8 线程并发向 Google Drive 上传 {len(files)} 份新版审计替换档案...")
    upload_tasks = []
    for it in files:
        mkt = it["market"]
        fname = it["file_name"]
        pdf_path = UNPACK_DIR / mkt / fname
        parent_id = FOLDER_US if mkt == "US" else FOLDER_JP
        upload_tasks.append({
            "pdf_path": pdf_path,
            "parent_id": parent_id,
            "market": mkt,
            "file_name": fname,
            "symbol": it["symbol"],
            "old_file_id": it["old_file_id"],
        })

    upload_success = 0
    upload_fail = 0
    uploaded_records = []
    t0_up = time.perf_counter()

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(upload_new_worker, task): task for task in upload_tasks}
        total = len(futures)
        done = 0
        for fut in as_completed(futures):
            name, mkt, new_id, ok = fut.result()
            task = futures[fut]
            done += 1
            if ok:
                upload_success += 1
                uploaded_records.append({
                    "symbol": task["symbol"],
                    "market": mkt,
                    "file_name": name,
                    "new_file_id": new_id,
                    "old_file_id": task["old_file_id"],
                })
            else:
                upload_fail += 1
            if done % 50 == 0 or done == total:
                print(f"  [上传进度] {done}/{total} 已完成 (成功: {upload_success}, 失败: {upload_fail})")

    t_up = time.perf_counter() - t0_up
    print(f"  [完成] 重新上传完成！耗时: {t_up:.1f} 秒 ({t_up/60:.1f} 分钟)")

    # 5. 校验远端数量
    print("\n[远端核验] 5. 正在核验 Google Drive 远端最新状态...")
    res_us = run_cmd([GDRIVE_EXE, "readonly", "ls", FOLDER_US, "--max", "0", "--json"])
    res_jp = run_cmd([GDRIVE_EXE, "readonly", "ls", FOLDER_JP, "--max", "0", "--json"])
    items_us = json.loads(res_us.stdout) if res_us.returncode == 0 else []
    items_jp = json.loads(res_jp.stdout) if res_jp.returncode == 0 else []

    print(f"  [存量统计] 远端实时存量: US 目录现有 {len(items_us)} 份, JP 目录现有 {len(items_jp)} 份 (总计: {len(items_us)+len(items_jp)} 份)")

    # 6. 保存归档收据
    receipt_path = ROOT / "data" / "audits" / "drive-deep-analysis-20261012" / "cloud-replacement-receipt.json"
    receipt_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_audited_reports": len(files),
        "old_reports_trashed": trash_success,
        "new_reports_uploaded": upload_success,
        "remote_us_count": len(items_us),
        "remote_jp_count": len(items_jp),
        "with_verified_fields": manifest.get("with_verified_facts", 38),
        "evidence_missing_reports": len(files) - manifest.get("with_verified_facts", 38),
        "uploaded_files": uploaded_records,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[流程收据] 执行完成！全流程收据已保存至: {receipt_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
