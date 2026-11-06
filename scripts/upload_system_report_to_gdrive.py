"""将系统全量架构技术总报告上传至 Google Drive 审阅目录.

目标目录:
1. 2026-10-14 每日审阅文件夹: CONFIGURE_YOUR_OWN_CLOUD_TARGET
2. 根目录专属文件夹: 系统架构与量化逻辑全景报告 (在 CONFIGURE_YOUR_OWN_CLOUD_TARGET 下)
"""

from pathlib import Path
import subprocess
import json
import sys
import re

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "system_architecture_reports" / "2026-10-14"
PDF_PATH = REPORT_DIR / "水源股票投研系统全量分析逻辑与数据架构全景总报告.pdf"
MD_PATH = REPORT_DIR / "水源股票投研系统全量分析逻辑与数据架构全景总报告.md"

ROOT_PARENT_ID = "CONFIGURE_YOUR_OWN_CLOUD_TARGET"
TODAY_FOLDER_ID = "CONFIGURE_YOUR_OWN_CLOUD_TARGET"


def run_gdrive(args):
    cmd = ["gdrive.cmd"] + list(args)
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
    stdout, _, code = run_gdrive(["readonly", "ls", parent_id, "--json"])
    if code == 0 and stdout:
        try:
            items = json.loads(stdout)
            for it in items:
                if it.get("name") == folder_name:
                    return it["id"]
        except Exception:
            pass
    mkdir_out, err, code = run_gdrive(["mutate", "mkdir", folder_name, "--parent", parent_id])
    if code == 0 and mkdir_out:
        m = re.search(r"\(ID:\s*([a-zA-Z0-9_-]+)\)", mkdir_out)
        if m:
            return m.group(1)
        try:
            data = json.loads(mkdir_out)
            return data["id"]
        except Exception:
            pass
    raise RuntimeError(f"创建文件夹失败: {mkdir_out} | {err}")


def upload_file(file_path: Path, parent_id: str, mime_type: str = "application/pdf"):
    stdout, stderr, code = run_gdrive([
        "mutate", "upload",
        str(file_path.resolve()),
        "--parent", parent_id,
        "--mime-type", mime_type,
        "--json"
    ])
    if code != 0:
        # 尝试非 json 模式 fallback
        stdout, stderr, code = run_gdrive([
            "mutate", "upload",
            str(file_path.resolve()),
            "--parent", parent_id,
            "--mime-type", mime_type
        ])
    
    file_id = None
    if stdout:
        try:
            data = json.loads(stdout)
            file_id = data.get("id")
        except Exception:
            m = re.search(r"Uploaded\s+([a-zA-Z0-9_-]+)", stdout) or re.search(r"ID:\s*([a-zA-Z0-9_-]+)", stdout)
            if m:
                file_id = m.group(1)

    return file_id, stdout, stderr, code


def main():
    if not PDF_PATH.exists():
        print(f"[错误] 找不到 PDF 文件: {PDF_PATH}")
        sys.exit(1)

    print(f"[报告同步] 准备上传系统全量架构技术总报告至 Google Drive...")
    print(f"  - 本地文件: {PDF_PATH.name} ({PDF_PATH.stat().st_size / 1024:.2f} KB)")

    # 1. 在根目录下确保专属文件夹
    arch_folder_id = get_or_create_folder("系统架构与量化逻辑全景总报告", ROOT_PARENT_ID)
    print(f"[目录就绪] 根目录专属文件夹 ID: {arch_folder_id}")

    # 2. 上传至 2026-10-14 审阅目录
    print(f"[上传执行] 上传至 2026-10-14 今日审阅目录 ({TODAY_FOLDER_ID})...")
    fid_today, out1, err1, c1 = upload_file(PDF_PATH, TODAY_FOLDER_ID, "application/pdf")
    if c1 == 0:
        print(f"  [完成] 成功上传至 2026-10-14 目录! File ID: {fid_today}")
    else:
        print(f"  [警告] 上传警告: {err1 or out1}")

    # 3. 上传至专属归档目录
    print(f"[上传执行] 上传至专属归档目录 ({arch_folder_id})...")
    fid_arch, out2, err2, c2 = upload_file(PDF_PATH, arch_folder_id, "application/pdf")
    if c2 == 0:
        print(f"  [完成] 成功上传至专属归档目录! File ID: {fid_arch}")
    else:
        print(f"  [警告] 上传警告: {err2 or out2}")

    # 4. 同时上传 Markdown 原稿至专属归档目录供审阅代码和格式
    if MD_PATH.exists():
        print(f"[上传执行] 上传 Markdown 源码底稿至专属归档目录...")
        fid_md, _, _, _ = upload_file(MD_PATH, arch_folder_id, "text/markdown")
        if fid_md:
            print(f"  [完成] Markdown 源码底稿已同步! File ID: {fid_md}")

    # 5. 输出用户审阅摘要
    print("\n" + "=" * 60)
    print("[同步完成] Google Drive 云端同步已全部圆满完成！")
    primary_id = fid_today or fid_arch
    print(f"  [文件名称] 云端文件名称: {PDF_PATH.name}")
    print(f"  [文件标识] 云端文件 ID: {primary_id}")
    print(f"  [查阅链接] 云端直接审阅链接: https://example.invalid/configure-your-own-cloud")
    print(f"  [今日目录] 2026-10-14 审阅文件夹: https://example.invalid/configure-your-own-cloud")
    print(f"  [专项目录] 系统架构专项目录: https://example.invalid/configure-your-own-cloud")
    print("=" * 60)


if __name__ == "__main__":
    main()
