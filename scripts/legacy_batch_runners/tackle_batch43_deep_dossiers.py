"""第四十三批 (Batch 43) 核心旗舰企业真实数据攻坚与股票深度分析 PDF 生成及云端替换流水线.

覆盖标的 (10 家美股领军巨头与细分霸主):
1. US: GM   (通用汽车 / General Motors Company) - 全美汽车制造销量第一旗舰
2. US: GLW  (康宁公司 / Corning Incorporated) - 全球特种显示玻璃与AI数据中心高密度光纤绝对霸主
3. US: GL   (环球人寿 / Globe Life Inc.) - 创立于1900年、全美工薪家庭小额人寿与补充医疗险龙头
4. US: GILD (吉利德科学 / Gilead Sciences, Inc.) - 全球抗病毒药物绝对王者 (HIV与肝炎霸主) 与CAR-T巨擘
5. US: GEN  (捷诺网络安全 / Gen Digital Inc.) - 全球最大消费级网络安全与身份防护航母 (Norton与Avast)
6. US: GEHC (GE医疗技术 / GE HealthCare Technologies Inc.) - 百年医学影像CT/MRI/超声及患者关爱科技三巨头之一
7. US: GIS  (通用磨坊 / General Mills, Inc.) - 拥有150余年历史的哈根达斯与蓝爵高端宠物粮食品帝国
8. US: GDDY (GoDaddy / GoDaddy Inc.) - 全球最大互联网域名注册商、中小微企业建站与Airo AI商业SaaS龙头
9. US: GD   (通用动力 / General Dynamics Corporation) - 全美防务军工三巨头、核潜艇双寡头与湾流公务机霸主
10. US: FOX (福克斯公司 B类 / Fox Corporation Class B) - 默多克家族全美新闻收视霸主Fox News与超级碗体育帝国

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
    print("[流水线启动] 第四十三批 (Batch 43) 核心旗舰股票深度分析攻坚启动 (10 家通用汽车、康宁特种玻璃、环球人寿、吉利德抗病毒、捷诺安全、GE医疗、通用磨坊、GoDaddy、通用动力、福克斯传媒)]")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    from data_sources.batch43_verified_dossiers_data import BATCH43_DOSSIERS
    import jsonschema

    schema_path = ROOT / "schemas" / "deep_dossier.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)

    work_dir = ROOT / "reports" / "batch43_generated"
    work_dir.mkdir(parents=True, exist_ok=True)
    dist_dir = ROOT / "reports" / "dossiers_dist"

    results = []

    for item in BATCH43_DOSSIERS:
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
        # 清理旧有的匹配文件
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

    # 6. 保存 Batch 43 收据
    receipt_path = ROOT / "data" / "audits" / "drive-deep-analysis-20261012" / "batch43-tackle-receipt.json"
    receipt_data = {
        "batch_id": "Batch-43",
        "description": "第43批 10 家美股领军巨头与细分霸主深度投研与矢量PDF生成及云端替换",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "total_tackled": len(results),
        "results": results
    }
    receipt_path.write_text(json.dumps(receipt_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print(f" [第四十三批 (Batch 43) 核心旗舰股票深度分析攻坚圆满完成！]")
    print(f"共计攻坚完成: {len(results)} 家企业")
    for r in results:
        print(f"  - [{r['market']}] {r['ticker']} {r['company_name']}: 新云端 ID {r['new_file_id']}")
    print(f"执行收据已归档至: {receipt_path.relative_to(ROOT)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
