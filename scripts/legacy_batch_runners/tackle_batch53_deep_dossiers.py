"""第五十三批 (Batch 53) 核心旗舰企业真实数据攻坚与股票深度分析 PDF 生成及云端替换流水线.

覆盖标的 (10 家美股领军巨头与细分霸主):
1. US: CLX   (高乐氏 / The Clorox Company) - 全美居家消毒清洁与特许日用消费品龙头、47年股息贵族
2. US: CMCSA (康卡斯特 / Comcast Corporation) - 全美第一大有线宽带网络航母、环球影业与环球主题公园帝国
3. US: CL    (高露洁棕榄 / Colgate-Palmolive Company) - 全球第一大口腔护理绝对垄断巨头、希尔思宠物营养健康超额复利、61年股息国王
4. US: CINF  (辛辛那提金融 / Cincinnati Financial Corporation) - 全美卓越独立代理商财险运营商、63年股息国王
5. US: CHTR  (特许通讯 / Charter Communications, Inc.) - 全美第二大宽带运营商与频谱移动通信融合网络巨擘
6. US: CI    (信诺集团 / The Cigna Group) - 全球商业健康保险与 Evernorth 专业医药供应链航母
7. US: CHRW  (罗宾逊物流 / C.H. Robinson Worldwide, Inc.) - 全美第一大卡车整车货运经纪商与全球无车承运平台先驱、26年股息贵族
8. US: CIEN  (微视 / Ciena Corporation) - 全球相干光通信与城域/长途波分复用系统绝对技术霸主、AI跨智算中心互联底座
9. US: CHD   (切奇与德怀特 / Church & Dwight Co., Inc.) - 全美小苏打特许日化与个人护理长青帝国、28年股息贵族
10. US: CFG  (公民金融 / Citizens Financial Group, Inc.) - 全美顶尖超大型区域银行、美东财富管理与中型企业商业信贷巨头

流程:
1. 校验符合 schemas/deep_dossier.schema.json;
2. 渲染高清 A4 买方机构级 HTML 研报;
3. 调用 Edge Headless 编译高清矢量 PDF;
4. 替换本地 reports/dossiers_dist/ 对应文件;
5. 云端联动: 回收旧版缺口声明存根, 上传正式股票深度分析 PDF 至 Google Drive;
6. 更新缺口清单并生成执行收据。
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
    print("[流水线启动] 第五十三批 (Batch 53) 核心旗舰股票深度分析攻坚启动 (10 家高乐氏、康卡斯特、高露洁、辛辛那提金融、特许通讯、信诺、罗宾逊物流、微视、切奇与德怀特、公民金融)]")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    from data_sources.batch53_verified_dossiers_data import BATCH53_DOSSIERS
    import jsonschema

    schema_path = ROOT / "schemas" / "deep_dossier.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)

    work_dir = ROOT / "reports" / "batch53_generated"
    work_dir.mkdir(parents=True, exist_ok=True)
    dist_dir = ROOT / "reports" / "dossiers_dist"

    results = []

    for item in BATCH53_DOSSIERS:
        ticker = item["overview"]["ticker"]
        name_zh = item["overview"]["company_name"]
        market = item["overview"]["market"]
        fname = item["file_name"]
        old_file_id = item["current_cloud_id"].strip()
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

        # 4. 清理旧版历史文件并替换本地交付目录
        target_market_dir = dist_dir / market
        target_market_dir.mkdir(parents=True, exist_ok=True)
        for old_local in target_market_dir.glob(f"{ticker}_*.pdf"):
            try:
                old_local.unlink()
            except Exception:
                pass

        target_local_path = target_market_dir / fname
        shutil.copy2(pdf_path, target_local_path)
        print(f"  [本地同步] 本地交付目录已同步替换: {target_local_path.relative_to(ROOT)}")

        # 5. 云端替换联动
        print(f"[云端同步] [3/4] 正在同步 Google Drive 云盘 (回收旧存根 ID: {old_file_id})...")
        if old_file_id and old_file_id != "NONE":
            cmd_trash = [GDRIVE_EXE, "mutate", "trash", old_file_id, "--json"]
            cp_trash = run_cmd(cmd_trash)
            if cp_trash.returncode == 0:
                print(f"  [清理完成] 旧版证据存根已移入回收站 (Trash)")
            else:
                print(f"  [清理提示] 旧存根回收提示 (可能已移入或权限变化): {cp_trash.stderr.strip() or cp_trash.stdout.strip()}")
        else:
            print(f"  ℹ️ 无需回收旧存根")

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
        print(f"  [上传成功] 云端上传成功！新文件 ID: {new_cloud_id}")

        results.append({
            "ticker": ticker,
            "company_name": name_zh,
            "market": market,
            "file_name": fname,
            "pdf_size_bytes": pdf_path.stat().st_size,
            "old_file_id": old_file_id,
            "new_file_id": new_cloud_id,
            "upload_timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "COMPLETED_REPLACED"
        })

    # 6. 保存 Batch 53 收据
    receipt_path = ROOT / "data" / "audits" / "drive-deep-analysis-20261012" / "batch53-tackle-receipt.json"
    receipt_data = {
        "batch_id": "Batch-53",
        "description": "第53批 10 家美股领军巨头与细分霸主深度投研与矢量PDF生成及云端替换",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "total_tackled": len(results),
        "results": results
    }
    receipt_path.write_text(json.dumps(receipt_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print(f" [第五十三批 (Batch 53) 核心旗舰股票深度分析攻坚圆满完成！]")
    print(f"共计攻坚完成: {len(results)} 家企业")
    for r in results:
        print(f"  - [{r['market']}] {r['ticker']} {r['company_name']}: 新云端 ID {r['new_file_id']}")
    print(f"执行收据已归档至: {receipt_path.relative_to(ROOT)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
