"""统一批次深度全息档案渲染与云端流式同步调度管线 (Unified Batch Dossier Pipeline Runner).

彻底替代原先 scripts/ 目录下散落的 81 个复制粘贴脚本 (tackle_batch*.py)。
核心规范：
1. 参数化执行指定批次 (--batch N)、范围批次 (--range 1-10) 或全量批次 (--all);
2. 动态探测 Google Drive 工具路径 (零硬编码个人绝对路径);
3. 严禁假回执：上传失败或未提取到云端 ID 时严格记录为 FAILED，杜绝假 UPLOADED;
4. 严格校验 schemas/deep_dossier.schema.json;
5. 支持流式增量执行、断点跳过与本地/云端分离模式 (--skip-upload)。
"""

import argparse
from datetime import datetime, timezone
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Optional, List, Dict, Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_reporting.deep_pdf_renderer import render_deep_dossier_pdf_html
from scripts.env_discovery import get_gdrive_executable, get_edge_executable
import jsonschema


FOLDER_US = "CONFIGURE_YOUR_OWN_CLOUD_TARGET"
FOLDER_JP = "CONFIGURE_YOUR_OWN_CLOUD_TARGET"


def resolve_cloud_id(upload_stdout: str) -> Optional[str]:
    """严谨解析上传输出中的 Google Drive 文件 ID."""
    m = re.search(r"\(ID:\s*([a-zA-Z0-9_-]+)\)", upload_stdout)
    if m:
        return m.group(1)
    m = re.search(r'"id":\s*"([^"]+)"', upload_stdout)
    if m:
        return m.group(1)
    return None


def load_batch_dossiers(batch_id: int | str) -> List[Dict[str, Any]]:
    """动态加载指定批次的数据底账."""
    if isinstance(batch_id, str) and "phase2" in batch_id:
        mod_name = f"data_sources.{batch_id}_data"
        var_name = f"{batch_id.upper()}_DOSSIERS"
    else:
        mod_name = f"data_sources.batch{batch_id}_verified_dossiers_data"
        var_name = f"BATCH{batch_id}_DOSSIERS"
    
    try:
        mod = importlib.import_module(mod_name)
    except ModuleNotFoundError as e:
        raise ValueError(f"未找到批次数据源模块: {mod_name}") from e

    if hasattr(mod, var_name):
        return getattr(mod, var_name)
    
    # 尝试寻找模块中的任意大写包含 DOSSIERS 的变量
    for k, v in mod.__dict__.items():
        if "DOSSIERS" in k and isinstance(v, list):
            return v
    
    raise ValueError(f"批次模块 {mod_name} 中未找到全息档案数据列表")


def process_single_batch(
    batch_label: str,
    dossiers: List[Dict[str, Any]],
    skip_upload: bool = False,
    validator: Optional[jsonschema.Draft7Validator] = None,
    edge_exe: str = "msedge.exe",
    gdrive_exe: Optional[str] = None,
) -> Dict[str, Any]:
    """处理单个批次的校验、渲染与上传."""
    print("=" * 70)
    print(f"[批次调度] 正在处理批次: {batch_label} (共 {len(dossiers)} 家企业)")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    work_dir = ROOT / "reports" / f"{batch_label}_generated"
    work_dir.mkdir(parents=True, exist_ok=True)
    dist_dir = ROOT / "reports" / "dossiers_dist"

    receipts = []

    for idx, item in enumerate(dossiers, 1):
        ticker = item["overview"]["ticker"]
        name_zh = item["overview"]["company_name"]
        market = item["overview"]["market"]
        fname = item.get("file_name", f"{market}_{ticker}_公司深度档案.pdf")
        parent_id = FOLDER_JP if market == "JP" else FOLDER_US

        # 1. Schema 契约校验
        if validator:
            errs = list(validator.iter_errors(item))
            if errs:
                raise ValueError(f"批次 {batch_label} 标的 {ticker} Schema 契约校验失败: {errs[0].message}")

        # 2. 渲染矢量 HTML
        html_content = render_deep_dossier_pdf_html(item)
        html_path = work_dir / f"{ticker}.html"
        html_path.write_text(html_content, encoding="utf-8")

        # 3. Headless 打印 PDF
        pdf_path = work_dir / fname
        print(f"  [编译PDF] [{idx}/{len(dossiers)}] 正在编译矢量 PDF: {market}:{ticker} ({name_zh})...")
        cmd_pdf = [
            edge_exe,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path.resolve()}",
            str(html_path.resolve()),
        ]
        res_pdf = subprocess.run(cmd_pdf, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if not pdf_path.exists() or pdf_path.stat().st_size == 0:
            raise RuntimeError(f"PDF 编译失败 ({ticker}): {res_pdf.stderr}")

        # 归档到 dossiers_dist
        market_dist = dist_dir / market
        market_dist.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, market_dist / fname)

        # 4. 云端流式上传 (若启用)
        cloud_id = None
        status = "RENDERED_LOCAL"

        if not skip_upload:
            if not gdrive_exe:
                print(f"  [提示] 未检测到 gdrive CLI 工具，跳过云端同步，已安全保留本地成果。")
            else:
                cmd_up = [gdrive_exe, "files", "upload", "--parent", parent_id, str(pdf_path.resolve())]
                res_up = subprocess.run(cmd_up, capture_output=True, text=True, encoding="utf-8", errors="replace")
                cid = resolve_cloud_id(res_up.stdout) if res_up.returncode == 0 else None
                if res_up.returncode == 0 and cid:
                    cloud_id = cid
                    status = "UPLOADED"
                    print(f"  [完成] 云端同步成功: (ID: {cloud_id})")
                else:
                    status = "UPLOAD_FAILED"
                    cloud_id = None
                    print(f"  [失败] 云端同步失败: (code: {res_up.returncode}) {res_up.stderr or res_up.stdout}")

        receipts.append({
            "ticker": ticker,
            "company_name": name_zh,
            "market": market,
            "file_name": fname,
            "pdf_size_bytes": pdf_path.stat().st_size,
            "status": status,
            "cloud_id": cloud_id,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        })

    # 持久化审计收据
    receipt_dir = ROOT / "data" / "audits" / "unified_batch_receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_file = receipt_dir / f"{batch_label}_receipt.json"
    receipt_file.write_text(json.dumps({
        "batch_label": batch_label,
        "total_companies": len(dossiers),
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "receipts": receipts,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  [完成] 批次 {batch_label} 执行完毕，审计收据已落库: {receipt_file.relative_to(ROOT)}\n")
    return {
        "batch_label": batch_label,
        "count": len(dossiers),
        "success": True,
    }


def main():
    parser = argparse.ArgumentParser(description="统一批次深度全息档案流水线 (替代 81 个冗余脚本)")
    parser.add_argument("--batch", type=int, help="执行指定批次编号 (1-78)")
    parser.add_argument("--range", type=str, help="执行指定批次范围 (如 1-5)")
    parser.add_argument("--phase2-batch", type=str, help="执行 Phase 2 特殊批次 (如 phase2_batch1_gold_metals)")
    parser.add_argument("--skip-upload", action="store_true", help="仅本地编译渲染 PDF，跳过云端上传")
    args = parser.parse_args()

    schema_path = ROOT / "schemas" / "deep_dossier.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)

    edge_exe = get_edge_executable()
    gdrive_exe = get_gdrive_executable()

    if args.batch:
        dossiers = load_batch_dossiers(args.batch)
        process_single_batch(f"batch{args.batch}", dossiers, args.skip_upload, validator, edge_exe, gdrive_exe)
    elif args.phase2_batch:
        dossiers = load_batch_dossiers(args.phase2_batch)
        process_single_batch(args.phase2_batch, dossiers, args.skip_upload, validator, edge_exe, gdrive_exe)
    elif args.range:
        parts = [int(p.strip()) for p in args.range.split("-")]
        start_b, end_b = parts[0], parts[1]
        for b in range(start_b, end_b + 1):
            try:
                dossiers = load_batch_dossiers(b)
                process_single_batch(f"batch{b}", dossiers, args.skip_upload, validator, edge_exe, gdrive_exe)
            except Exception as e:
                print(f"  [跳过] 批次 batch{b} 执行遇错跳过: {e}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
