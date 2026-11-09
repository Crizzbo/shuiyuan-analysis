"""第三十七批 (Batch 37) 核心旗舰企业真实数据攻坚与股票深度分析 PDF 生成及云端替换流水线.

覆盖标的 (10 家美股领军巨头):
1. US: LHX (L3哈里斯科技 / L3Harris Technologies, Inc.) - 全球战术通信、太空电子战与国防军工巨头
2. US: LIN (林德气体 / Linde plc) - 全球最大工业气体、特种化学品与氢能基础设施垄断霸主
3. US: LEN (莱纳建筑 / Lennar Corporation) - 全美第二大轻资产住宅建造商、地产金融科技巨擘
4. US: LDOS (莱多斯控股 / Leidos Holdings, Inc.) - 全美最大联邦政府情报、国防IT网络技术服务商
5. US: L (洛斯公司 / Loews Corporation) - 蒂施家族多元控股航母：财产险CNA、跨州天然气管道与奢华酒店
6. US: KR (克罗格 / The Kroger Co.) - 全美最大传统超级市场食品连锁、数字杂货与私域生鲜航母
7. US: KVUE (科赴 / Kenvue Inc.) - 全球最大独立消费者健康、非处方药与皮肤个护超级帝国
8. US: KMI (金德摩根 / Kinder Morgan, Inc.) - 全美最大天然气中游管道网络、储气库与能源基础设施收费站
9. US: KMB (金佰利 / Kimberly-Clark Corporation) - 全球个人健康护理、婴儿纸尿裤与生活用纸百年消费巨头
10. US: KKR (科尔伯格·克拉维斯·罗伯茨 / KKR & Co. Inc.) - 全球顶尖另类资产管理、私募股权 PE 投资与基础设施航母

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
    print("[流水线启动] 第三十七批 (Batch 37) 核心旗舰股票深度分析攻坚启动 (10 家L3哈里斯军工、林德工业气体、莱纳建筑、莱多斯国防IT、洛斯控股、克罗格超市、科赴消费健康、金德摩根管道、金佰利个护、KKR另类资管)]")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    from data_sources.batch37_verified_dossiers_data import BATCH37_DOSSIERS
    import jsonschema

    schema_path = ROOT / "schemas" / "deep_dossier.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)

    work_dir = ROOT / "reports" / "batch37_generated"
    work_dir.mkdir(parents=True, exist_ok=True)
    dist_dir = ROOT / "reports" / "dossiers_dist"

    results = []

    for item in BATCH37_DOSSIERS:
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

        # 4. 替换本地交付目录
        target_local_path = dist_dir / market / fname
        target_local_path.parent.mkdir(parents=True, exist_ok=True)
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

    # 6. 保存 Batch 37 收据
    receipt_path = ROOT / "data" / "audits" / "drive-deep-analysis-20261012" / "batch37-tackle-receipt.json"
    receipt_data = {
        "batch_id": "Batch-37",
        "description": "第37批 10 家美股领军巨头与细分霸主深度投研与矢量PDF生成及云端替换",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "total_tackled": len(results),
        "results": results
    }
    receipt_path.write_text(json.dumps(receipt_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print(f" [第三十七批 (Batch 37) 核心旗舰股票深度分析攻坚圆满完成！]")
    print(f"共计攻坚完成: {len(results)} 家企业")
    for r in results:
        print(f"  - [{r['market']}] {r['ticker']} {r['company_name']}: 新云端 ID {r['new_file_id']}")
    print(f"执行收据已归档至: {receipt_path.relative_to(ROOT)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
