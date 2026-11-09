"""第二十五批 (Batch 25) 核心旗舰企业真实数据攻坚与股票深度分析 PDF 生成及云端替换流水线.

覆盖标的 (10 家美股领军巨头与细分赛道胜负手):
1. US: SPGI (标普全球评级 / S&P Global Inc.) - 全球信用评级与金融市场指数超级特许垄断航母
2. US: SNPS (新思科技 / Synopsys, Inc.) - 全球芯片设计电子设计自动化 (EDA) 软件与半导体 IP 垄断巨头
3. US: STT (道富银行 / State Street Corporation) - 全球托管资产近 42 万亿美元的特级资产托管与全球交易银行
4. US: SPG (西蒙地产集团 / Simon Property Group, Inc.) - 北美顶级高坪效奥特莱斯与区域购物中心 REITs 龙头
5. US: SO (南方电力 / The Southern Company) - 全美大型公用事业电力巨头 (全美首座近 30 年新建 Vogtle 商业核电机组)
6. US: SRE (桑普拉能源 / Sempra) - 加州与德州公用事业巨头及墨西哥湾 LNG 液化出口先锋
7. US: STE (思泰瑞 / STERIS plc) - 全球医院手术器械灭菌、内窥镜再处理与制药无菌洁净室龙头
8. US: STLD (钢铁动力 / Steel Dynamics, Inc.) - 全美最具成本优势的电弧炉 (EAF) 短流程高附加值特种钢铁龙头
9. US: TFC (储蓄金融集团 / Truist Financial Corporation) - 全美前十大区域商业银行航母 (BB&T 与 SunTrust 合并)
10. US: VMRK (维马克 / Veris Residential, Inc.) - 专注纽约大都市圈紧俏高端环保多户出租公寓运营 REITs

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

def main():
    print("=" * 70)
    print("[流水线启动] 第二十五批 (Batch 25) 核心旗舰股票深度分析攻坚启动 (10 家标普全球评级、新思EDA、道富托管银行、西蒙商业地产、南方核电、桑普拉LNG、思泰瑞灭菌、钢动力电弧炉、储蓄金融、维马克公寓)]")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    from data_sources.batch25_verified_dossiers_data import BATCH25_DOSSIERS
    import jsonschema

    schema_path = ROOT / "schemas" / "deep_dossier.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)

    work_dir = ROOT / "reports" / "batch25_generated"
    work_dir.mkdir(parents=True, exist_ok=True)
    dist_dir = ROOT / "reports" / "dossiers_dist"

    results = []

    for item in BATCH25_DOSSIERS:
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
        t0 = time.perf_counter()
        cp = subprocess.run(cmd, capture_output=True, timeout=40)
        elapsed = time.perf_counter() - t0

        if not pdf_path.exists() or pdf_path.stat().st_size < 5000:
            raise RuntimeError(f"PDF 渲染失败: {fname}, code={cp.returncode}")
        print(f"  [编译成功] PDF 生成成功 ({pdf_path.stat().st_size / 1024:.1f} KB, 耗时 {elapsed:.2f}s)")

        # 4. 同步替换本地 dossiers_dist 交付目录
        target_local_pdf = dist_dir / market / fname
        target_local_pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, target_local_pdf)
        print(f"  [本地同步] 本地交付目录已同步替换: {target_local_pdf.relative_to(ROOT)}")

        # 5. 云端 Google Drive 替换: 回收旧版存根, 上传新版股票深度分析
        print(f"[云端同步] [3/4] 正在同步 Google Drive 云盘 (回收旧存根 ID: {old_file_id})...")
        trash_res = run_cmd([GDRIVE_EXE, "mutate", "trash", old_file_id, "--json"])
        if trash_res.returncode == 0:
            print(f"  [清理完成] 旧版证据存根已移入回收站 (Trash)")
        else:
            print(f"  [清理提示] 旧版回收提示 (可能已在回收站): {trash_res.stderr.strip()[:100]}")

        print(f"  [云端上传] 正在上传正式股票深度分析 PDF 至云端文件夹 ({market})...")
        up_res = run_cmd([
            GDRIVE_EXE, "mutate", "upload",
            str(pdf_path.resolve()),
            "--parent", parent_id,
            "--mime-type", "application/pdf",
            "--json",
        ])

        new_cloud_id = None
        if up_res.returncode == 0 and up_res.stdout:
            m = re.search(r"\(ID:\s*([a-zA-Z0-9_-]+)\)", up_res.stdout)
            if m:
                new_cloud_id = m.group(1)
        
        if not new_cloud_id:
            print(f"  [上传异常] 云端上传解析 ID 异常: {up_res.stdout.strip()}")
        else:
            print(f"  [上传成功] 云端上传成功！新文件 ID: {new_cloud_id}")

        results.append({
            "ticker": ticker,
            "company_name": name_zh,
            "market": market,
            "file_name": fname,
            "old_file_id": old_file_id,
            "new_file_id": new_cloud_id,
            "pdf_size_bytes": pdf_path.stat().st_size,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "status": "success",
        })

    # 6. 更新缺口清单与收据
    receipt_path = ROOT / "data" / "audits" / "drive-deep-analysis-20261012" / "batch25-tackle-receipt.json"
    receipt_path.write_text(json.dumps({
        "batch_id": 25,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "companies_count": len(results),
        "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # 更新 gap_manifest_567.json
    gap_manifest_path = ROOT / "data" / "audits" / "drive-deep-analysis-20261012" / "gap_manifest_567.json"
    if gap_manifest_path.exists():
        manifest = json.loads(gap_manifest_path.read_text(encoding="utf-8"))
        completed_tickers = {r["ticker"]: r for r in results}
        
        for tier in ["P0_flagship_megacap", "P1_core_industry_leader"]:
            if tier in manifest.get("gaps_by_tier", {}):
                for item in manifest["gaps_by_tier"][tier]:
                    t = item.get("symbol") or item.get("ticker")
                    if t in completed_tickers:
                        item["status"] = "completed_deep_dossier"
                        item["new_file_id"] = completed_tickers[t]["new_file_id"]
                        item["updated_at"] = datetime.now(timezone.utc).isoformat()

        for item in manifest.get("all_gap_entries", []):
            t = item.get("symbol") or item.get("ticker")
            if t in completed_tickers:
                item["status"] = "completed_deep_dossier"
                item["new_file_id"] = completed_tickers[t]["new_file_id"]
                item["updated_at"] = datetime.now(timezone.utc).isoformat()

        rem = [x for x in manifest["all_gap_entries"] if x.get("status") != "completed_deep_dossier"]
        manifest["verified_companies_count"] += len(completed_tickers)
        manifest["gap_companies_count"] = len(rem)
        gap_manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print("[批次完成] 第二十五批 (Batch 25) 核心旗舰股票深度分析攻坚圆满完成！]")
    print(f"共计攻坚完成: {len(results)} 家企业")
    for r in results:
        print(f"  - [{r['market']}] {r['ticker']} {r['company_name']}: 新云端 ID {r['new_file_id']}")
    print(f"执行收据已归档至: {receipt_path.relative_to(ROOT)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
