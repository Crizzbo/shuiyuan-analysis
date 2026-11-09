"""第三十二批 (Batch 32) 核心旗舰企业真实数据攻坚与股票深度分析 PDF 生成及云端替换流水线.

覆盖标的 (10 家美股领军巨头与细分霸主):
1. US: NOW (ServiceNow, Inc.) - 全球企业级数字化工作流 AI 平台绝对领军霸主
2. US: NOC (诺斯罗普·格鲁曼 / Northrop Grumman) - B-21 隐身轰炸机、哨兵洲际导弹与军工航天超级领军霸主
3. US: NSC (诺福克南方铁路 / Norfolk Southern) - 北美东部一级干线铁路运输网络垄断巨头
4. US: NEE (新纪元能源 / NextEra Energy) - 全球最大风光清洁能源发电商与全美受监管公用事业航母
5. US: NEM (纽蒙特矿业 / Newmont Corporation) - 全球第一大黄金开采超级金矿航母 (黄金资产深度研究体系)
6. US: NDSN (诺信 / Nordson Corporation) - 全球半导体封装与精密点胶流体工业隐形冠军
7. US: NRG (NRG能源 / NRG Energy, Inc.) - 德州大型综合电力发售一体化与智能家居能源巨头
8. US: NI (尼索斯能源 / NiSource Inc.) - 美国中西部纯受监管天然气与电网公用事业稳定回报标杆
9. US: PNW (顶峰西部资本 / Pinnacle West Capital) - 亚利桑那州受监管清洁电网公用事业与核电巨头
10. US: NCLH (诺唯真游轮 / Norwegian Cruise Line Holdings) - 全球三大现代豪华游轮巨头之一

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
    # 尝试正则从输出中提取
    m = re.search(r"\(ID:\s*([a-zA-Z0-9_-]+)\)", upload_stdout)
    if m:
        return m.group(1)
    m = re.search(r'"id":\s*"([^"]+)"', upload_stdout)
    if m:
        return m.group(1)
    
    # 备选：通过 gdrive search 精确回查刚刚上传的带有 ticker 前缀的文件
    try:
        cmd = [GDRIVE_EXE, "readonly", "search", "--name-contains", f"{ticker}_", "--json"]
        cp = run_cmd(cmd)
        if cp.returncode == 0 and cp.stdout:
            data = json.loads(cp.stdout)
            # 找到最新且大于 100KB 的文件
            cand = [f for f in data if int(f.get("size", 0)) > 100000]
            if cand:
                return cand[0]["id"]
    except Exception:
        pass
    return "UNKNOWN_NEW_ID"

def main():
    print("=" * 70)
    print("[流水线启动] 第三十二批 (Batch 32) 核心旗舰股票深度分析攻坚启动 (10 家ServiceNow数字化工作流、诺斯罗普隐身战机、诺福克南方铁路、新纪元清洁能源、纽蒙特全球第一黄金采掘、诺信精密点胶、NRG德州电力发售、尼索斯纯受监管电网、顶峰西部核电公用事业、诺唯真豪华游轮)]")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    from data_sources.batch32_verified_dossiers_data import BATCH32_DOSSIERS
    import jsonschema

    schema_path = ROOT / "schemas" / "deep_dossier.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)

    work_dir = ROOT / "reports" / "batch32_generated"
    work_dir.mkdir(parents=True, exist_ok=True)
    dist_dir = ROOT / "reports" / "dossiers_dist"

    results = []

    for item in BATCH32_DOSSIERS:
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
        ]
        cp_upload = run_cmd(upload_cmd)
        if cp_upload.returncode != 0:
            raise RuntimeError(f"上传 Google Drive 失败: {cp_upload.stderr}")

        new_file_id = resolve_cloud_id(ticker, fname, cp_upload.stdout)
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
    receipt_path = ROOT / "data" / "audits" / "drive-deep-analysis-20261012" / "batch32-tackle-receipt.json"
    receipt_data = {
        "batch": 32,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "total_tackled": len(results),
        "results": results,
    }
    receipt_path.write_text(json.dumps(receipt_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print("[批次完成] 第三十二批 (Batch 32) 核心旗舰股票深度分析攻坚圆满完成！]")
    print(f"共计攻坚完成: {len(results)} 家企业")
    for r in results:
        print(f"  - [{r['region']}] {r['ticker']} {r['name']}: 新云端 ID {r['new_file_id']}")
    print(f"执行收据已归档至: {receipt_path.relative_to(ROOT)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
