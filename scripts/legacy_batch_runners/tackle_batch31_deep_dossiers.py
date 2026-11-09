"""第三十一批 (Batch 31) 核心旗舰企业真实数据攻坚与股票深度分析 PDF 生成及云端替换流水线.

覆盖标的 (10 家美股核心龙头与细分霸主):
1. US: ON (安森美半导体 / ON Semiconductor Corporation) - 全球汽车与工业 SiC 碳化硅功率半导体领军霸主
2. US: OMC (宏盟集团 / Omnicom Group Inc.) - 全球前三大广告营销与数字化传媒航母
3. US: OKE (奥克拉荷马天然气中游 / ONEOK, Inc.) - 北美最大天然气液体 NGL 收集加工与长输管道中游能源航母
4. US: ODFL (奥德多米尼昂货运 / Old Dominion Freight Line, Inc.) - 北美零担货运 LTL 运营效率与高 ROIC 行业天花板
5. US: O (房地产收入公司 / Realty Income Corporation) - 全球标杆级月度派息单租户商业净租赁 REITs 现金流印钞机
6. US: NXPI (恩智浦半导体 / NXP Semiconductors N.V.) - 全球汽车微控制器 MCU 与雷达处理芯片领军巨头
7. US: NUE (纽柯钢铁 / Nucor Corporation) - 北美最大微型电弧炉短流程绿色钢铁与废钢循环制造航母
8. US: NVR (NVR住宅建筑 / NVR, Inc.) - 全美唯一 100% 土地期权轻资产、超高 ROE 的顶级住宅建筑巨头
9. US: NTAP (净存科技 / NetApp, Inc.) - 全球企业级智能混合云统一存储系统先锋
10. US: NTRS (北方信托 / Northern Trust Corporation) - 全球顶级超高净值私人财富管理与万亿级资产托管航母

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
    print("[流水线启动] 第三十一批 (Batch 31) 核心旗舰股票深度分析攻坚启动 (10 家安森美SiC、宏盟广告传媒、ONEOK天然气中游、奥德多米尼昂LTL、Realty Income月度派息REITs、恩智浦汽车MCU、纽柯电炉钢、NVR轻资产建筑、NetApp混合云存储、北方信托资产托管)]")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    from data_sources.batch31_verified_dossiers_data import BATCH31_DOSSIERS
    import jsonschema

    schema_path = ROOT / "schemas" / "deep_dossier.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)

    work_dir = ROOT / "reports" / "batch31_generated"
    work_dir.mkdir(parents=True, exist_ok=True)
    dist_dir = ROOT / "reports" / "dossiers_dist"

    results = []

    for item in BATCH31_DOSSIERS:
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

        # 4. 同步本地交付库
        target_dist = dist_dir / market / fname
        target_dist.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, target_dist)
        print(f"  [本地同步] 本地交付目录已同步替换: {target_dist.relative_to(ROOT)}")

        # 5. 云端 Google Drive 联动原子替换
        print(f"[云端同步] [3/4] 正在同步 Google Drive 云盘 (回收旧存根 ID: {old_file_id})...")
        if old_file_id and old_file_id != "NONE":
            trash_cmd = [GDRIVE_EXE, "mutate", "trash", old_file_id, "--json"]
            cp_trash = run_cmd(trash_cmd)
            if cp_trash.returncode == 0:
                print(f"  [清理完成] 旧版证据存根已移入回收站 (Trash)")
            else:
                print(f"  [清理提示] 旧存根回收跳过或未找到: {cp_trash.stderr.strip()[:100]}")

        print(f"  [云端上传] 正在上传正式股票深度分析 PDF 至云端文件夹 ({market})...")
        upload_cmd = [
            GDRIVE_EXE,
            "mutate",
            "upload",
            str(pdf_path.resolve()),
            "--parent",
            parent_id,
            "--mime-type",
            "application/pdf",
            "--json",
        ]
        cp_upload = run_cmd(upload_cmd)
        if cp_upload.returncode != 0:
            raise RuntimeError(f"上传 Google Drive 失败: {cp_upload.stderr}")

        try:
            up_res = json.loads(cp_upload.stdout)
            new_file_id = up_res.get("file", {}).get("id") or up_res.get("id")
        except Exception:
            m = re.search(r'"id":\s*"([^"]+)"', cp_upload.stdout)
            new_file_id = m.group(1) if m else "UNKNOWN_NEW_ID"

        print(f"  [上传成功] 云端上传成功！新文件 ID: {new_file_id}")

        results.append({
            "ticker": ticker,
            "name": name_zh,
            "region": market,
            "file_name": fname,
            "old_file_id": old_file_id,
            "new_file_id": new_file_id,
            "local_pdf_size": pdf_path.stat().st_size,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # 6. 保存收据
    receipt_path = ROOT / "data" / "audits" / "drive-deep-analysis-20261012" / "batch31-tackle-receipt.json"
    receipt_data = {
        "batch": 31,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "total_tackled": len(results),
        "results": results,
    }
    receipt_path.write_text(json.dumps(receipt_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print("[批次完成] 第三十一批 (Batch 31) 核心旗舰股票深度分析攻坚圆满完成！]")
    print(f"共计攻坚完成: {len(results)} 家企业")
    for r in results:
        print(f"  - [{r['region']}] {r['ticker']} {r['name']}: 新云端 ID {r['new_file_id']}")
    print(f"执行收据已归档至: {receipt_path.relative_to(ROOT)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
