"""重构 Google 云端硬盘投研目录结构 (Separate Dashboards from PDFs).

业务目标：
1. 彻底解决用户反馈的“交互看板与原来的 PDF 混在一个文件夹”的问题；
2. 在今日 2026-10-16 专属云盘文件夹 (CONFIGURE_YOUR_OWN_CLOUD_TARGET) 下创建清晰的两个独立子目录：
   - 买方动态交互看板库 (Interactive_Dashboards)
   - 机构研报PDF原件库 (Original_PDF_Reports)
3. 自动将现存的所有 PDF 移动归档至 机构研报PDF原件库；
4. 自动将现存的所有 Google Sheets 活体表格与 Web 交互看板移动至 买方动态交互看板库；
5. 在上层【公司深度分析档案】(CONFIGURE_YOUR_OWN_CLOUD_TARGET) 下同样建立【公司深度分析交互看板库】，确保长期公司档案也实现动静分离！
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from scripts.env_discovery import get_gdrive_executable, run_cmd

DAILY_FOLDER_ID = "CONFIGURE_YOUR_OWN_CLOUD_TARGET"        # 2026-10-16
DOSSIER_ROOT_ID = "CONFIGURE_YOUR_OWN_CLOUD_TARGET"        # 公司深度分析档案根目录


def get_or_create_subfolder(exe: str, folder_name: str, parent_id: str) -> str:
    """在指定父目录下查找或创建子文件夹。"""
    # 查找
    res = run_cmd([exe, "readonly", "search", "--parent-id", parent_id, "--type", "folder"])
    for line in res.stdout.splitlines():
        if folder_name in line:
            m = re.match(r"^([a-zA-Z0-9_-]+)\s+", line.strip())
            if m:
                fid = m.group(1)
                print(f"  [目录就绪] 已存在子文件夹: {folder_name} (ID: {fid})")
                return fid

    # 创建
    print(f"  [创建目录] 创建新子文件夹: {folder_name} (父级: {parent_id})...")
    res_mkdir = run_cmd([exe, "mutate", "mkdir", folder_name, "--parent", parent_id])
    m = re.search(r"\(ID:\s*([a-zA-Z0-9_-]+)\)", res_mkdir.stdout)
    if m:
        fid = m.group(1)
        print(f"    [创建完成] 创建成功: {folder_name} (ID: {fid})")
        return fid
    raise RuntimeError(f"创建子文件夹失败: {res_mkdir.stderr}")


def list_files_in_folder(exe: str, folder_id: str) -> List[Dict[str, str]]:
    """列出文件夹中的所有项目。"""
    res = run_cmd([exe, "readonly", "ls", folder_id])
    files = []
    lines = res.stdout.splitlines()
    if len(lines) < 3:
        return files

    for line in lines[2:]:
        line_clean = line.strip()
        if not line_clean:
            continue
        parts = re.split(r"\s{2,}", line_clean)
        if len(parts) >= 3:
            fid = parts[0]
            name = parts[1]
            ftype = parts[2]
            files.append({"id": fid, "name": name, "type": ftype})
    return files


def main():
    print("=" * 80)
    print("[目录重构] 启动 Google 云端硬盘目录动静彻底物理分离工程 (Dashboards vs PDFs)")
    print("=" * 80)

    exe = get_gdrive_executable()
    if not exe:
        raise RuntimeError("未检测到 gdrive 可执行文件！")

    # 1. 在今日目录 2026-10-16 (CONFIGURE_YOUR_OWN_CLOUD_TARGET) 创建两个分离目录
    print("\n[Step 1/3] 检查并创建今日 2026-10-16 专属动静分离子目录...")
    folder_dashboards_id = get_or_create_subfolder(exe, "买方动态交互看板库", DAILY_FOLDER_ID)
    folder_pdfs_id = get_or_create_subfolder(exe, "机构研报PDF原件库", DAILY_FOLDER_ID)

    # 2. 列出今日目录下的现有文件，并分别移动归档
    print("\n[Step 2/3] 执行文件分类与物理移动归类...")
    current_files = list_files_in_folder(exe, DAILY_FOLDER_ID)
    print(f"  当前待分类项目总数: {len(current_files)}")

    for f in current_files:
        fid = f["id"]
        name = f["name"]
        ftype = f["type"]

        # 跳过刚刚创建的子文件夹自身
        if fid in (folder_dashboards_id, folder_pdfs_id) or "folder" in ftype.lower():
            continue

        if "pdf" in ftype.lower() or name.endswith(".pdf"):
            print(f"  [归类移动] 移动 PDF 原件: {name} -> 机构研报PDF原件库...")
            res_mv = run_cmd([exe, "mutate", "mv", fid, folder_pdfs_id])
            if res_mv.returncode != 0:
                print(f"    [移动失败] 移动失败: {res_mv.stderr}")
        elif "spreadsheet" in ftype.lower() or "html" in ftype.lower() or "text" in ftype.lower() or "sheet" in name.lower() or name.endswith(".html"):
            print(f"  [归类移动] 移动交互看板: {name} -> 买方动态交互看板库...")
            res_mv = run_cmd([exe, "mutate", "mv", fid, folder_dashboards_id])
            if res_mv.returncode != 0:
                print(f"    [移动失败] 移动失败: {res_mv.stderr}")

    # 3. 在【公司深度分析档案】根目录下建立长期交互看板库
    print("\n[Step 3/3] 在长期【公司深度分析档案】目录下建立独立看板库...")
    dossier_dashboards_folder_id = get_or_create_subfolder(exe, "公司深度分析交互看板库", DOSSIER_ROOT_ID)

    # 把刚刚生成的 NVDA 交互看板与活体表格也上传一份至长期公司深度档案看板库
    nvda_sheet_local = ROOT / "reports" / "interactive_dossiers" / "NVDA_英伟达_深度分析活体交互模型.xlsx"
    nvda_html_local = ROOT / "reports" / "interactive_dossiers" / "NVDA_英伟达_公司全景深度分析交互看板.html"

    if nvda_sheet_local.exists():
        print(f"  [云端同步] 上传 NVDA 活体 Google Sheet 至长期公司看板库...")
        run_cmd([
            exe, "mutate", "upload", str(nvda_sheet_local.resolve()),
            "--parent", dossier_dashboards_folder_id,
            "--mime-type", "application/vnd.google-apps.spreadsheet"
        ])
    if nvda_html_local.exists():
        print(f"  [云端同步] 上传 NVDA Web 交互看板至长期公司看板库...")
        run_cmd([
            exe, "mutate", "upload", str(nvda_html_local.resolve()),
            "--parent", dossier_dashboards_folder_id,
            "--mime-type", "text/html"
        ])

    print("\n" + "=" * 80)
    print("[重构完成] 云端目录动静分离重构圆满达成！")
    print(f"1. [交互看板] 今日买方动态交互看板库: https://example.invalid/configure-your-own-cloud")
    print(f"2. [研报原件] 今日机构研报PDF原件库:   https://example.invalid/configure-your-own-cloud")
    print(f"3. [公司档案] 长期公司深度交互看板库: https://example.invalid/configure-your-own-cloud")
    print("=" * 80)


if __name__ == "__main__":
    main()
