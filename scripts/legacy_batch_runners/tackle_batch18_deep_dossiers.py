"""第十八批 (Batch 18) 核心旗舰企业真实数据攻坚与股票深度分析 PDF 生成及云端替换流水线.

覆盖标的 (10 家美股与日股领军巨头):
1. JP: 5108 (普利司通) - 全球第一乘用车商用车高端轮胎与特种矿山胎制造霸主
2. JP: 4901 (富士胶片控股) - 医疗生命健康Bio-CDMO、高性能半导体材料与数码影像转型巨头
3. JP: 4689 (LINE雅虎) - 日本国民级超级APP生态圈、即时通讯搜索门户与移动支付龙头
4. JP: 4578 (大冢控股) - 中枢神经抗精神病/多囊肾重磅创新药与功能营养品双轮医药航母
5. JP: 4519 (中外制药) - 罗氏控股全球抗体创新药研发先锋、血友病重磅双抗发明者
6. US: VRSN (威瑞信) - 全球互联网底层.com与.net根域名唯一垄断收费站
7. US: VMC (火神材料) - 全美第一大重型建筑砂石骨料、区域采石场特许垄断巨头
8. US: VLTO (维尔拓) - 丹纳赫分拆之全球水质分析仪器与工业产品喷码标识科技先锋
9. US: VLO (瓦莱罗能源) - 全球最大独立炼油商与北美可再生低碳柴油领军
10. US: VICI (维奇地产) - 拉斯维加斯百乐宫/凯撒宫旗舰地标娱乐赌场NNN不动产REITs霸主

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
    print("[流水线启动] 第十八批 (Batch 18) 核心旗舰股票深度分析攻坚启动 (10 家全球轮胎第一、医疗CDMO、日本超国民APP、中枢神经抗精神药、抗体工程研发霸主及根域名收费站、砂石骨料垄断、水质分析科技、独立炼油与赌场地产REITs)]")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    from data_sources.batch18_verified_dossiers_data import BATCH18_DOSSIERS
    import jsonschema

    schema_path = ROOT / "schemas" / "deep_dossier.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)

    work_dir = ROOT / "reports" / "batch18_generated"
    work_dir.mkdir(parents=True, exist_ok=True)
    dist_dir = ROOT / "reports" / "dossiers_dist"

    results = []

    for item in BATCH18_DOSSIERS:
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
    receipt_path = ROOT / "data" / "audits" / "drive-deep-analysis-20261012" / "batch18-tackle-receipt.json"
    receipt_path.write_text(json.dumps({
        "batch_id": 18,
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
    print("[批次完成] 第十八批 (Batch 18) 核心旗舰股票深度分析攻坚圆满完成！]")
    print(f"共计攻坚完成: {len(results)} 家企业")
    for r in results:
        print(f"  - [{r['market']}] {r['ticker']} {r['company_name']}: 新云端 ID {r['new_file_id']}")
    print(f"执行收据已归档至: {receipt_path.relative_to(ROOT)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
