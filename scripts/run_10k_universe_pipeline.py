"""全盘万家企业流式渲染与云端同步调度管线 (Streaming Pipelined Runner).

贯彻 2026-10-15 工程整改规范 Task 17 & Task 18:
1. 先筛选未完成项目，再截取 limit，彻底解决跳过已完成项后无法继续后续公司的缺陷;
2. 建立精准的渲染与云端状态机 (RENDERED_LOCAL, UPLOADED, UPLOAD_FAILED)，严禁未上传/仅本地渲染记录为 UPLOADED;
3. 逐项增量持久化进度账本与 SQLite，防止进程中断丢失已完成进度;
4. 动态检测并解耦 gdrive 工具路径，无外部工具时安全回退并如实记录本地完成状态。
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.env_discovery import get_gdrive_executable, get_edge_executable

GDRIVE_EXE = get_gdrive_executable()
EDGE_EXE = get_edge_executable() or "msedge.exe"

FOLDER_US = "CONFIGURE_YOUR_OWN_CLOUD_TARGET"
FOLDER_JP = "CONFIGURE_YOUR_OWN_CLOUD_TARGET"

from financial_reporting.deep_pdf_renderer import render_deep_dossier_pdf_html


def run_cmd(args):
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def resolve_cloud_id(ticker, fname, upload_stdout):
    m = re.search(r"\(ID:\s*([a-zA-Z0-9_-]+)\)", upload_stdout)
    if m:
        return m.group(1)
    m = re.search(r'"id":\s*"([^"]+)"', upload_stdout)
    if m:
        return m.group(1)
    return None


def main():
    parser = argparse.ArgumentParser(description="10K Universe Chunk Runner (State-Machine Hardened)")
    parser.add_argument("--chunk", type=int, default=1, help="Chunk index (1 to 100)")
    parser.add_argument("--limit", type=int, default=10, help="Number of unprocessed companies to process")
    parser.add_argument("--skip-upload", action="store_true", help="Only render locally without upload")
    parser.add_argument("--allow-synthetic-demo", action="store_true", help="显式允许消费未核准的历史合成分块数据 (仅限本地压测，强制禁用云端上传)")
    args = parser.parse_args()

    manifest_path = ROOT / "data" / "universe" / "universe_10k_manifest.json"
    is_unverified = False
    if manifest_path.exists():
        try:
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
            if m.get("status") == "UNVERIFIED_INDEX_REQUIRES_OFFICIAL_FILINGS":
                is_unverified = True
        except Exception:
            pass

    # 安全门禁 (Task 01 & 02): 阻断未核验的假数据编译与上传
    if is_unverified and not args.allow_synthetic_demo:
        print("[安全阻断] data/universe 资产池处于 UNVERIFIED_INDEX_REQUIRES_OFFICIAL_FILINGS 状态。")
        print("   历史分块数据包含未经官方三表核验的模板假数据（如将 NVDA 标记为快消零售、AAPL 标记为新药研发）。")
        print("   系统已刚性阻断正式渲染与云端上传！")
        print("   若仅用于本地渲染排版基准压测，必须显式传入 --allow-synthetic-demo。")
        sys.exit(1)

    if args.allow_synthetic_demo and not args.skip_upload:
        print("[安全保护] 合成样本模式下已强制启用 --skip-upload，禁止将未核实验证的报告上传至云盘！")
        args.skip_upload = True

    chunk_file = ROOT / "data" / "universe" / "chunks" / f"chunk_{args.chunk:03d}.json"
    if not chunk_file.exists():
        print(f"[错误] 分块文件不存在: {chunk_file}")
        sys.exit(1)

    chunk_data = json.loads(chunk_file.read_text(encoding="utf-8"))

    ledger_path = ROOT / "data" / "audits" / "universe_10k_progress_ledger.json"
    ledger = {}
    if ledger_path.exists():
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        except Exception:
            ledger = {}

    # Task 17: 先筛选未完成的项目，再截取 limit!
    unprocessed = []
    for item in chunk_data:
        t = item["overview"]["ticker"]
        # 如果要求上传，但之前仅本地渲染或上传失败，亦应重新处理上传
        if t not in ledger:
            unprocessed.append(item)
        elif not args.skip_upload and ledger[t].get("status") != "UPLOADED":
            unprocessed.append(item)

    targets = unprocessed[:args.limit]

    print("=" * 70)
    print(f"[管线启动] 万家资产池流式调度管线启动: 分块 #{args.chunk} (未完成待处理: {len(unprocessed)} 家, 本批目标: {len(targets)} 家)")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    if not targets:
        print(f"[完成] 分块 #{args.chunk} 中所有企业均已完成处理，无需重复执行。")
        return

    # 若为合成演示，隔离在 scratch/ 下
    if args.allow_synthetic_demo:
        work_dir = ROOT / "scratch" / "synthetic_universe_demo" / f"chunk_{args.chunk:03d}_generated"
        dist_dir = ROOT / "scratch" / "synthetic_universe_demo" / "dossiers_dist"
    else:
        work_dir = ROOT / "reports" / f"chunk_{args.chunk:03d}_generated"
        dist_dir = ROOT / "reports" / "dossiers_dist"

    work_dir.mkdir(parents=True, exist_ok=True)

    db_path = ROOT / "data" / "universe" / "universe_10k_dossiers.sqlite3"
    conn = None
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))

    completed_count = 0
    for item in targets:
        ticker = item["overview"]["ticker"]
        market = item["overview"]["market"]
        name = item["overview"]["company_name"]
        fname = item["file_name"]
        parent_id = FOLDER_JP if market == "JP" else FOLDER_US

        print(f"  [本地渲染] {market}:{ticker} ({name})...")
        html_content = render_deep_dossier_pdf_html(item)
        html_path = work_dir / f"{ticker}.html"
        html_path.write_text(html_content, encoding="utf-8")

        pdf_path = work_dir / fname
        cmd = [
            EDGE_EXE,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path.resolve()}",
            str(html_path.resolve()),
        ]
        cp_pdf = run_cmd(cmd)
        if not pdf_path.exists() or pdf_path.stat().st_size < 10000:
            print(f"  [警告] Edge 编译失败 ({ticker}): {cp_pdf.stderr[:80]}")
            continue

        # Save to local dist
        target_dir = dist_dir / market
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, target_dir / fname)

        # 状态机精准判定 (Task 17)
        now_iso = datetime.now(timezone.utc).isoformat()
        current_status = "RENDERED_LOCAL"
        cloud_id = None

        if not args.skip_upload:
            if not GDRIVE_EXE:
                print("  [提示] 未检测到有效 Google Drive CLI 工具，如实记录为本地完成，不伪造云端上传。")
                current_status = "RENDERED_LOCAL"
            else:
                cmd_upload = [
                    GDRIVE_EXE,
                    "mutate",
                    "upload",
                    str(pdf_path.resolve()),
                    "--parent",
                    parent_id,
                    "--mime-type",
                    "application/pdf",
                ]
                cp_up = run_cmd(cmd_upload)
                if cp_up.returncode == 0:
                    cloud_id = resolve_cloud_id(ticker, fname, cp_up.stdout)
                    if cloud_id:
                        current_status = "UPLOADED"
                        print(f"  [云端同步] 云端流式上传成功: ID {cloud_id}")
                    else:
                        current_status = "UPLOAD_RETURNED_UNKNOWN"
                        print(f"  [警告] 云端返回但未解析出有效 File ID")
                else:
                    current_status = "UPLOAD_FAILED"
                    print(f"  [警告] 云端上传失败: {cp_up.stderr.strip()[:60]}")
        else:
            current_status = "RENDERED_LOCAL"

        # 逐项增量写入数据库与账本 (防止中断丢失进度)
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE dossiers SET rendered_pdf_status=?, cloud_id=?, updated_at=? WHERE ticker=?",
                (current_status, cloud_id or "NONE", now_iso, ticker),
            )
            conn.commit()

        ledger[ticker] = {
            "market": market,
            "name": name,
            "status": current_status,
            "cloud_id": cloud_id,
            "pdf_size": pdf_path.stat().st_size,
            "timestamp": now_iso,
        }
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
        completed_count += 1

    if conn:
        conn.close()

    print(f"[批次完成] 分块 #{args.chunk} 执行完毕: 本批增量完成 {completed_count} 家，当前总账本累计 {len(ledger)} 家！")


if __name__ == "__main__":
    main()
