"""第六十一批 (Batch 61 - 全量资产池中坚攻坚) 核心企业股票深度分析 PDF 生成及云端流式上传流水线.

覆盖标的 (10 家美股与日股主线成长及硬核中坚巨头):
1. US: SHOP (肖皮飞 / Shopify Inc.)
2. US: SNOW (雪花计算 / Snowflake Inc.)
3. US: ZS   (泽斯卡勒 / Zscaler, Inc.)
4. US: SQ   (布洛克 / Block, Inc.)
5. US: MDB  (芒果数据库 / MongoDB, Inc.)
6. US: TEAM (阿特拉斯 / Atlassian Corporation)
7. US: PDD  (拼多多 / PDD Holdings Inc.)
8. JP: 8001 (伊藤忠商事 / ITOCHU Corporation)
9. JP: 6954 (发那科 / FANUC Corporation)
10. JP: 4519 (中外制药 / Chugai Pharmaceutical Co., Ltd.)

流程:
1. 严格校验符合 schemas/deep_dossier.schema.json 契约;
2. 渲染买方机构级 A4 矢量 HTML;
3. 调用 Microsoft Edge Headless 编译无头矢量 PDF;
4. 归档本地 reports/dossiers_dist/ 对应市场目录;
5. 云端流式上传 (Streaming Pipelined Upload) 至 Google Drive (US/JP);
6. 归档执行收据至 data/audits/drive-deep-analysis-20261012/batch61-tackle-receipt.json。
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
    try:
        cmd = [GDRIVE_EXE, "readonly", "search", "--name-contains", f"{ticker}_", "--json"]
        cp = run_cmd(cmd)
        if cp.returncode == 0 and cp.stdout:
            data = json.loads(cp.stdout)
            cand = [f for f in data if int(f.get("size", 0)) > 100000]
            if cand:
                return cand[0]["id"]
    except Exception:
        pass
    return "UNKNOWN_NEW_ID"

def main():
    print("=" * 70)
    print("[流水线启动] 第六十一批 (Batch 61) 全量资产池中坚股票深度分析攻坚与流式上传启动]")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    from data_sources.batch61_verified_dossiers_data import BATCH61_DOSSIERS
    import jsonschema

    schema_path = ROOT / "schemas" / "deep_dossier.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)

    work_dir = ROOT / "reports" / "batch61_generated"
    work_dir.mkdir(parents=True, exist_ok=True)
    dist_dir = ROOT / "reports" / "dossiers_dist"

    results = []

    for item in BATCH61_DOSSIERS:
        ticker = item["overview"]["ticker"]
        name_zh = item["overview"]["company_name"]
        market = item["overview"]["market"]
        fname = item["file_name"]
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

        # 5. 云端流式上传
        print(f"[流式上传] [3/4] 正在流式上传 Google Drive 云盘 ({market})...")
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
        print(f"  [上传成功] 云端上传成功！文件 ID: {new_cloud_id}")

        results.append({
            "ticker": ticker,
            "company_name": name_zh,
            "market": market,
            "file_name": fname,
            "pdf_size_bytes": pdf_path.stat().st_size,
            "cloud_id": new_cloud_id,
            "upload_timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "COMPLETED_UPLOADED"
        })

    # 6. 保存 Batch 61 收据
    receipt_dir = ROOT / "data" / "audits" / "drive-deep-analysis-20261012"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / "batch61-tackle-receipt.json"
    receipt_data = {
        "batch_id": "Batch-61",
        "description": "第61批 10 家美股与日股核心成长及工业中坚巨头深度投研与矢量PDF生成及云端流式上传",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "total_tackled": len(results),
        "results": results
    }
    receipt_path.write_text(json.dumps(receipt_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print(f" [第六十一批 (Batch 61) 股票深度分析攻坚圆满完成！]")
    print(f"共计攻坚完成: {len(results)} 家企业")
    for r in results:
        print(f"  - [{r['market']}] {r['ticker']} {r['company_name']}: 云端 ID {r['cloud_id']}")
    print(f"执行收据已归档至: {receipt_path.relative_to(ROOT)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
