"""第三十四批 (Batch 34) 核心旗舰企业真实数据攻坚与股票深度分析 PDF 生成及云端替换流水线.

覆盖标的 (10 家美股领军巨头与细分霸主):
1. US: MPWR (芯源系统 / Monolithic Power Systems, Inc.) - 全球高性能模拟电源管理与 AI 服务器供电绝对龙头
2. US: MOS (美盛公司 / The Mosaic Company) - 全球最大磷肥与钾肥综合农业化肥战略巨头
3. US: MO (奥驰亚集团 / Altria Group, Inc.) - 全美最大烟草万宝路垄断现金流印钞机与高股息君主
4. US: MMM (3M公司 / 3M Company) - 全球工业材料、胶带、过滤与安全防护百年发明创新巨擘
5. US: MNST (怪物饮料 / Monster Beverage Corporation) - 全球功能能量饮料长牛神话与可口可乐战略盟友
6. US: MLM (马丁-玛丽埃塔材料 / Martin Marietta Materials, Inc.) - 北美重型砂石骨料与水泥基础设施巨头
7. US: MGM (美高梅国际酒店 / MGM Resorts International) - 全球顶尖综合娱乐度假村与数字体育博彩集团
8. US: MET (大都会人寿 / MetLife, Inc.) - 全球最大人寿保险、年金与员工福利资产管理航母
9. US: MDLZ (亿滋国际 / Mondelez International, Inc.) - 全球休闲零食与奥利奥/吉百利超级消费巨擘
10. US: MCHP (微芯科技 / Microchip Technology Incorporated) - 全球嵌入式微控制器 MCU 与模拟芯片常青树

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
    print("[流水线启动] 第三十四批 (Batch 34) 核心旗舰股票深度分析攻坚启动 (10 家芯源AI电源管理、美盛化肥、奥驰亚烟草印钞机、3M工业材料科技、怪物饮料、马丁玛丽埃塔重工骨料、美高梅娱乐度假、大都会人寿、亿滋国际奥利奥、微芯科技嵌入式MCU)]")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    from data_sources.batch34_verified_dossiers_data import BATCH34_DOSSIERS
    import jsonschema

    schema_path = ROOT / "schemas" / "deep_dossier.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)

    work_dir = ROOT / "reports" / "batch34_generated"
    work_dir.mkdir(parents=True, exist_ok=True)
    dist_dir = ROOT / "reports" / "dossiers_dist"

    results = []

    for item in BATCH34_DOSSIERS:
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
    receipt_path = ROOT / "data" / "audits" / "drive-deep-analysis-20261012" / "batch34-tackle-receipt.json"
    receipt_data = {
        "batch": 34,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "total_tackled": len(results),
        "results": results,
    }
    receipt_path.write_text(json.dumps(receipt_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print("[批次完成] 第三十四批 (Batch 34) 核心旗舰股票深度分析攻坚圆满完成！]")
    print(f"共计攻坚完成: {len(results)} 家企业")
    for r in results:
        print(f"  - [{r['region']}] {r['ticker']} {r['name']}: 新云端 ID {r['new_file_id']}")
    print(f"执行收据已归档至: {receipt_path.relative_to(ROOT)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
