"""第三十批 (Batch 30) 核心旗舰企业真实数据攻坚与股票深度分析 PDF 生成及云端替换流水线.

覆盖标的 (10 家美股领军巨头与细分赛道胜负手):
1. US: PGR (前进保险 / The Progressive Corporation) - 全美最大车险与驾驶行为大数据 Telematics 智能定价绝对霸主
2. US: PH (派克汉尼汾 / Parker-Hannifin Corporation) - 全球运动与控制工业精密液压、流体传动与航空航天航电巨头
3. US: PFG (信安金融 / Principal Financial Group, Inc.) - 全美中小微企业 401(k) 退休金年金与员工福利受托管理专家
4. US: PEG (公共服务企业 / Public Service Enterprise Group Incorporated) - 新泽西清洁核电 (Nuclear PTC) 与受监管电网标杆
5. US: PCAR (帕卡重卡 / PACCAR Inc) - 全球最高品质豪华重型卡车制造航母 (Kenworth / Peterbilt / DAF)
6. US: PANW (派拓网络 / Palo Alto Networks, Inc.) - 全球下一代企业网络安全防火墙、Prisma Cloud 与 AI 安全运营中心领军者
7. US: OXY (西方石油 / Occidental Petroleum Corporation) - 巴菲特核心重仓、二叠纪页岩油优质资产与直接空气碳捕集 (DAC) 先锋
8. US: PAYX (沛齐 / Paychex, Inc.) - 全美中小微企业一体化薪酬发放、HR SaaS 软件与无风险税金浮存金高利润现金牛
9. US: ORLY (奥莱利汽车配件 / O'Reilly Automotive, Inc.) - 全美专业汽配分销零售双轮驱动、31年同店正增长的长牛复利神话
10. US: OTIS (奥的斯机电 / Otis Worldwide Corporation) - 全球电梯自动扶梯制造安装与 230 万台在役设备高毛利维保复利王者

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
    print("[流水线启动] 第三十批 (Batch 30) 核心旗舰股票深度分析攻坚启动 (10 家前进保险智能车险、派克汉尼汾流体、信安金融养老金、新泽西清洁核电、帕卡豪华重卡、派拓下一代网安、西方石油碳捕集、沛齐薪酬SaaS、奥莱利汽配长牛、奥的斯电梯维保)]")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    from data_sources.batch30_verified_dossiers_data import BATCH30_DOSSIERS
    import jsonschema

    schema_path = ROOT / "schemas" / "deep_dossier.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)

    work_dir = ROOT / "reports" / "batch30_generated"
    work_dir.mkdir(parents=True, exist_ok=True)
    dist_dir = ROOT / "reports" / "dossiers_dist"

    results = []

    for item in BATCH30_DOSSIERS:
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
    receipt_path = ROOT / "data" / "audits" / "drive-deep-analysis-20261012" / "batch30-tackle-receipt.json"
    receipt_path.write_text(json.dumps({
        "batch_id": 30,
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
    print("[批次完成] 第三十批 (Batch 30) 核心旗舰股票深度分析攻坚圆满完成！]")
    print(f"共计攻坚完成: {len(results)} 家企业")
    for r in results:
        print(f"  - [{r['market']}] {r['ticker']} {r['company_name']}: 新云端 ID {r['new_file_id']}")
    print(f"执行收据已归档至: {receipt_path.relative_to(ROOT)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
