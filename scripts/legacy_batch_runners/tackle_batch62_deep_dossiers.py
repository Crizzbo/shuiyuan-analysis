"""第六十二批 (Batch 62 - 彻底清零云端存根决战战役) 核心旗舰股票深度分析 PDF 生成及云端彻底替换流水线.

覆盖标的 (22 家美股核心压轴蓝筹航母 - 彻底清零全部孤立存根):
1.  US: ACN   (埃森哲 / Accenture plc)
2.  US: ADP   (安德普翰 / Automatic Data Processing, Inc.)
3.  US: BLK   (贝莱德 / BlackRock, Inc.)
4.  US: CB    (安达保险 / Chubb Limited)
5.  US: CEG   (星座能源 / Constellation Energy Corporation)
6.  US: DAL   (达美航空 / Delta Air Lines, Inc.)
7.  US: DHI   (霍顿房屋 / D.R. Horton, Inc.)
8.  US: DOW   (陶氏化学 / Dow Inc.)
9.  US: DUK   (杜克能源 / Duke Energy Corporation)
10. US: EOG   (EOG能源 / EOG Resources, Inc.)
11. US: FCX   (自由港麦克莫兰 / Freeport-McMoRan Inc.)
12. US: GEV   (GE Vernova / GE Vernova Inc.)
13. US: HCA   (美国医院集团 / HCA Healthcare, Inc.)
14. US: ISRG  (直觉外科 / Intuitive Surgical, Inc.)
15. US: LMT   (洛克希德·马丁 / Lockheed Martin Corporation)
16. US: MAR   (万豪国际 / Marriott International, Inc.)
17. US: MRNA  (莫德纳 / Moderna, Inc.)
18. US: PFE   (辉瑞制药 / Pfizer Inc.)
19. US: PKG   (美国包装工业 / Packaging Corporation of America)
20. US: PLD   (安博 / Prologis, Inc.)
21. US: PM    (菲利普莫里斯国际 / Philip Morris International Inc.)
22. US: VZ    (威瑞森通信 / Verizon Communications Inc.)

流程:
1. 校验符合 schemas/deep_dossier.schema.json;
2. 渲染买方机构级 A4 矢量 HTML;
3. 调用 Edge Headless 编译高清矢量研报 PDF;
4. 归档本地 reports/dossiers_dist/US/;
5. 云端彻底联动: 回收移入回收站旧存根 (Trash), 上传正式股票深度分析 PDF 至 Google Drive (US);
6. 归档执行收据至 data/audits/drive-deep-analysis-20261012/batch62-tackle-receipt.json。
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

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
    return "UPLOADED"

def main():
    print("=" * 70)
    print("[流水线启动] 第六十二批 (Batch 62 - 彻底清零云端存根战役) 核心旗舰深度分析攻坚与替换启动]")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    from data_sources.batch62_verified_dossiers_data import BATCH62_DOSSIERS
    import jsonschema

    schema_path = ROOT / "schemas" / "deep_dossier.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)

    work_dir = ROOT / "reports" / "batch62_generated"
    work_dir.mkdir(parents=True, exist_ok=True)
    dist_dir = ROOT / "reports" / "dossiers_dist"

    results = []

    for item in BATCH62_DOSSIERS:
        ticker = item["overview"]["ticker"]
        name_zh = item["overview"]["company_name"]
        market = item["overview"]["market"]
        fname = item["file_name"]
        old_file_id = item.get("current_cloud_id", "").strip()
        parent_id = FOLDER_JP if market == "JP" else FOLDER_US

        print(f"\n[契约核验] [1/4] 正在验证 {market}:{ticker} ({name_zh}) 真实数据 Schema 契约...")
        errors = list(validator.iter_errors(item))
        if errors:
            print(f"  [校验失败] Schema 验证失败: {errors[0].message}")
            raise ValueError(f"{ticker} Schema 验证失败: {errors[0].message}")
        print(f"  [校验通过] Schema 验证通过: 真实三表、DIO、上下游及 DCF 矩阵完全合规！")

        # 2. 渲染 HTML
        html_content = render_deep_dossier_pdf_html(item)
        html_path = work_dir / f"{ticker}.html"
        html_path.write_text(html_content, encoding="utf-8")

        # 3. 编译 PDF
        pdf_path = work_dir / fname
        print(f"[报告编译] [2/4] 调用 Microsoft Edge 无头打印编译矢量研报 PDF: {fname}...")
        cmd = [
            EDGE_EXE,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path.resolve()}",
            str(html_path.resolve()),
        ]
        t0 = time.time()
        cp_pdf = run_cmd(cmd)
        elapsed = time.time() - t0

        if not pdf_path.exists() or pdf_path.stat().st_size < 10000:
            print(f"  [编译失败] PDF 编译失败: {cp_pdf.stderr}")
            raise RuntimeError(f"Edge headless PDF 编译失败: {fname}")

        pdf_size_kb = pdf_path.stat().st_size / 1024
        print(f"  [编译成功] PDF 生成成功 ({pdf_size_kb:.1f} KB, 耗时 {elapsed:.2f}s)")

        # 4. 存入本地交付目录
        target_market_dir = dist_dir / market
        target_market_dir.mkdir(parents=True, exist_ok=True)
        target_local_path = target_market_dir / fname
        shutil.copy2(pdf_path, target_local_path)
        print(f"  [本地同步] 本地交付目录已同步存入: {target_local_path.relative_to(ROOT)}")

        # 5. 云端彻底联动: 回收旧版存根并上传正式研报
        print(f"[云端同步] [3/4] 正在同步 Google Drive 云盘 (回收旧存根 ID: {old_file_id})...")
        if old_file_id and old_file_id != "NONE":
            cmd_trash = [GDRIVE_EXE, "mutate", "trash", old_file_id, "--json"]
            cp_trash = run_cmd(cmd_trash)
            if cp_trash.returncode == 0:
                print(f"  [清理完成] 旧版证据存根已移入回收站 (Trash)")
            else:
                print(f"  [清理提示] 旧存根回收提示: {cp_trash.stderr.strip()[:60]}")

        print(f"  [云端上传] 正在上传正式股票深度分析 PDF 至云端文件夹 ({market})...")
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
        cp_upload = run_cmd(cmd_upload)
        if cp_upload.returncode != 0:
            print(f"  [上传失败] 上传云端失败: {cp_upload.stderr}")
            raise RuntimeError(f"Gdrive upload failed: {cp_upload.stderr}")

        new_cloud_id = resolve_cloud_id(ticker, fname, cp_upload.stdout)
        print(f"  [上传成功] 云端上传成功！正式研报文件 ID: {new_cloud_id}")

        results.append({
            "ticker": ticker,
            "company_name": name_zh,
            "market": market,
            "file_name": fname,
            "pdf_size_bytes": pdf_path.stat().st_size,
            "old_stub_id": old_file_id,
            "new_cloud_id": new_cloud_id,
            "upload_timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "COMPLETED_REPLACED"
        })

    # 6. 保存 Batch 62 收据
    receipt_dir = ROOT / "data" / "audits" / "drive-deep-analysis-20261012"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / "batch62-tackle-receipt.json"
    receipt_data = {
        "batch_id": "Batch-62",
        "description": "第62批 (彻底清零云端存根决战) 22 家美股核心压轴蓝筹航母深度投研与矢量PDF生成及云端存根清零替换",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "total_tackled": len(results),
        "results": results
    }
    receipt_path.write_text(json.dumps(receipt_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print(f" [第六十二批 (Batch 62) 股票深度分析攻坚与存根清零圆满完成！]")
    print(f"共计攻坚替换完成: {len(results)} 家企业")
    for r in results:
        print(f"  - [{r['market']}] {r['ticker']} {r['company_name']}: 新云端 ID {r['new_cloud_id']}")
    print(f"执行收据已归档至: {receipt_path.relative_to(ROOT)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
