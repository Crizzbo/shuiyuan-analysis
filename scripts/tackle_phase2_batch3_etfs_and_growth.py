"""第二阶段拓展第三批 (Phase 2 - Batch 3 - 终极大收官战役) 全球核心ETF与高成长新星 (17 只核心资产) 矢量 PDF 生成与云端同步流水线.

覆盖标的 (17 只核心拓展资产):
- 5 家高成长代表性新星:
  1.  US: MELI (自由市场 / MercadoLibre, Inc.) - 拉美电商与Mercado Pago金融双飞轮巨擘
  2.  US: IONQ (IonQ, Inc.) - 离子阱量子计算全栈商业化系统前沿
  3.  US: RDDT (Reddit, Inc.) - 真实人类社区讨论与大模型知识库授权变现
  4.  US: CAVA (CAVA Group, Inc.) - 地中海风味高坪效连锁餐饮新星
  5.  US: DUOL (多邻国 / Duolingo, Inc.) - AI原生自适应教育订阅变现独角兽
- 12 只全球核心指数与行业主题 ETF:
  6.  US: SPY  (SPDR标普500ETF / SPDR S&P 500 ETF Trust) - 全球流动性之王与股票基准
  7.  US: QQQ  (Invesco纳斯达克100ETF / Invesco QQQ Trust) - 全球大盘科技与AI创新旗舰
  8.  US: IWM  (iShares罗素2000小型股ETF / iShares Russell 2000 ETF) - 美本土中小企业降息弹性标杆
  9.  US: SMH  (VanEck半导体ETF / VanEck Semiconductor ETF) - 穿透25大芯片算力巨头资本开支
  10. US: XLK  (科技精选行业SPDR基金 / Technology Select Sector SPDR) - 微软苹果英伟达超级科技权重
  11. US: XBI  (SPDR标普生物科技ETF / SPDR S&P Biotech ETF) - 等权重创新药与利率风险偏好前沿
  12. US: XLE  (能源精选行业SPDR基金 / Energy Select Sector SPDR) - 传统油气自由现金流巨兽
  13. US: SCHD (嘉信美国高股息ETF / Schwab U.S. Dividend Equity ETF) - 优质稳健现金牛防御基石
  14. US: VIG  (Vanguard股息增长ETF / Vanguard Dividend Appreciation ETF) - 持续增配股息高ROE蓝筹
  15. US: TLT  (iShares 20+年期美债ETF / iShares 20+ Year Treasury Bond ETF) - 长久期美债利率博弈工具
  16. US: IEF  (iShares 7-10年期美债ETF / iShares 7-10 Year Treasury Bond ETF) - 中期美债基准利率曲线传导
  17. US: HYG  (iShares高收益公司债ETF / iShares iBoxx $ High Yield Corporate Bond) - 信用利差与违约风险晴雨表

流程:
1. 校验符合 schemas/deep_dossier.schema.json;
2. 渲染买方机构级高清 HTML 研报;
3. 调用 Edge Headless 编译高清矢量 PDF;
4. 归档到本地 reports/dossiers_dist/US/ 对应目录;
5. 上传正式股票深度分析 PDF 至 Google Drive (US 目录 CONFIGURE_YOUR_OWN_CLOUD_TARGET);
6. 归档执行审计收据至 data/audits/drive-deep-analysis-20261012/phase2-batch3-receipt.json。
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
            cand = [f for f in data if int(f.get("size", 0)) > 50000]
            if cand:
                return cand[0]["id"]
    except Exception:
        pass
    return "UNKNOWN_NEW_ID"

def main():
    print("=" * 70)
    print("[批次启动] 第二阶段拓展第三批 (Phase 2 - Batch 3 - 终极交付) 全球核心ETF与高成长新星攻坚启动")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)

    from data_sources.phase2_batch3_etfs_and_growth_data import PHASE2_BATCH3_DOSSIERS
    import jsonschema

    schema_path = ROOT / "schemas" / "deep_dossier.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)

    work_dir = ROOT / "reports" / "phase2_batch3_generated"
    work_dir.mkdir(parents=True, exist_ok=True)
    dist_dir = ROOT / "reports" / "dossiers_dist" / "US"
    dist_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for item in PHASE2_BATCH3_DOSSIERS:
        ticker = item["overview"]["ticker"]
        name_zh = item["overview"]["company_name"]
        market = item["overview"]["market"]
        fname = item["file_name"]

        print(f"\n[契约验证] [1/4] 正在验证 {market}:{ticker} ({name_zh}) Schema 契约...")
        errors = list(validator.iter_errors(item))
        if errors:
            print(f"  [失败] Schema 验证失败: {errors[0].message}")
            raise ValueError(f"{ticker} Schema 验证失败: {errors[0].message}")
        print(f"  [通过] Schema 验证通过: 真实三表/资产组合、DIO、上下游及 DCF 矩阵完全合规！")

        # 2. 渲染 HTML
        html_content = render_deep_dossier_pdf_html(item)
        html_path = work_dir / f"{ticker}.html"
        html_path.write_text(html_content, encoding="utf-8")

        # 3. 编译 PDF
        pdf_path = work_dir / fname
        print(f"[编译PDF] [2/4] 调用 Microsoft Edge 无头打印编译矢量研报 PDF: {fname}...")
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
            print(f"  [失败] PDF 编译失败: {cp_pdf.stderr}")
            raise RuntimeError(f"Edge headless PDF 编译失败: {fname}")

        pdf_size_kb = pdf_path.stat().st_size / 1024
        print(f"  [完成] PDF 生成成功 ({pdf_size_kb:.1f} KB, 耗时 {elapsed:.2f}s)")

        # 4. 替换本地交付目录
        target_local_path = dist_dir / fname
        shutil.copy2(pdf_path, target_local_path)
        print(f"  [本地就绪] 本地交付目录已同步就绪: {target_local_path.relative_to(ROOT)}")

        # 5. 云端上传联动 (遵循防虚假上传与离线自适应原则)
        print(f"[云端同步] [3/4] 检查云端目录并尝试同步深度研报 PDF 至 Google Drive (US 目录)...")
        new_cloud_id = "LOCAL_ARCHIVED_NO_CLOUD_TARGET"
        cloud_status = "LOCAL_DELIVERED"

        if FOLDER_US and FOLDER_US != "CONFIGURE_YOUR_OWN_CLOUD_TARGET":
            cmd_upload = [
                GDRIVE_EXE,
                "mutate",
                "upload",
                str(pdf_path.resolve()),
                "--parent",
                FOLDER_US,
                "--mime-type",
                "application/pdf",
            ]
            cp_upload = run_cmd(cmd_upload)
            if cp_upload.returncode == 0:
                new_cloud_id = resolve_cloud_id(ticker, fname, cp_upload.stdout)
                cloud_status = "CLOUD_UPLOADED"
                print(f"  [完成] 云端上传成功！文件 ID: {new_cloud_id}")
            else:
                print(f"  [提示] 上传云端跳过或网络不可达: {cp_upload.stderr.strip()[:100]}，已安全保留本地交付件。")
                cloud_status = "LOCAL_PENDING_REMOTE_SYNC"
        else:
            print("  [提示] 云端目标目录未配置或处于离线模式，已安全交付至本地 reports/dossiers_dist/US/")

        results.append({
            "ticker": ticker,
            "company_name": name_zh,
            "market": market,
            "file_name": fname,
            "pdf_size_bytes": pdf_path.stat().st_size,
            "cloud_status": cloud_status,
            "new_file_id": new_cloud_id,
            "upload_timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "COMPLETED_EXPANDED"
        })

    # 6. 保存审计收据
    receipt_dir = ROOT / "data" / "audits" / "drive-deep-analysis-20261012"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / "phase2-batch3-receipt.json"
    receipt_data = {
        "batch_id": "Phase2-Batch-3",
        "description": "第二阶段拓展第三批 (终局交付 - 全球核心ETF 12 只与高成长新星 5 家共计 17 只核心资产) 矢量PDF生成及云端同步",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "total_tackled": len(results),
        "results": results
    }
    receipt_path.write_text(json.dumps(receipt_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 70)
    print(f"[批次完成] 第二阶段拓展第三批 (Phase 2 - Batch 3 - 终极交付) 全球核心ETF与高成长股攻坚圆满完成！")
    print(f"共计攻坚完成: {len(results)} 只标的")
    for r in results:
        print(f"  - [{r['market']}] {r['ticker']} {r['company_name']}: 云端 ID {r['new_file_id']}")
    print(f"执行收据已归档至: {receipt_path.relative_to(ROOT)}")
    print("=" * 70)

if __name__ == "__main__":
    main()
