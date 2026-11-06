"""场景 2 中坚主力资产池 (606 家，标普 500 + 日股核心 100 强) 8 进程并发建档脚本."""

from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from financial_reporting.scenario2_universe import get_scenario2_universe
from financial_reporting.macro_valuation import MacroContext
from financial_reporting.deep_schema_generator import build_deep_dossier_data
from financial_reporting.pdf_templates import render_deep_dossier_pdf_html
from financial_reporting.chinese_names_registry import get_dossier_filename

DOSSIER_DIR = ROOT / "reports" / "dossiers_dist"
DOSSIER_DIR.mkdir(parents=True, exist_ok=True)
(DOSSIER_DIR / "US").mkdir(parents=True, exist_ok=True)
(DOSSIER_DIR / "JP").mkdir(parents=True, exist_ok=True)


def convert_pdf_worker(item):
    """单个无头浏览器 PDF 转换工作进程。"""
    html_p, pdf_p = item
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    edge = next((p for p in edge_paths if Path(p).exists()), "msedge")
    cmd = [
        edge,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_p}",
        str(html_p),
    ]
    try:
        t0 = time.perf_counter()
        res = subprocess.run(cmd, capture_output=True, timeout=40)
        elapsed = time.perf_counter() - t0
        return str(pdf_p.name), res.returncode == 0, elapsed
    except Exception as e:
        return str(pdf_p.name), False, 0.0


def main():
    print("=" * 70)
    print("[场景管线启动] 场景 2 中坚主力资产池: 8 进程并发建档管线启动")
    print("=" * 70)

    macro = MacroContext.load_latest()
    universe = get_scenario2_universe()
    us_count = sum(1 for c in universe if c["market"] == "US")
    jp_count = sum(1 for c in universe if c["market"] == "JP")
    print(f"[资产规模] 共计 {len(universe)} 家核心企业 (美股: {us_count} 家, 日股: {jp_count} 家)")

    t_html_start = time.perf_counter()
    tasks_to_convert = []

    print("\n[阶段一] 正在生成全量 606 份深度档案 HTML 底表 (三表底稿 + DIO + 上下游 + 情景DCF)...")
    for comp in universe:
        mkt = comp["market"]

        # 结构化生成数据与 HTML
        dossier_data = build_deep_dossier_data(comp, macro)
        html_content = render_deep_dossier_pdf_html(dossier_data)

        target_dir = DOSSIER_DIR / mkt
        pdf_name = get_dossier_filename(comp)
        html_name = pdf_name.replace(".pdf", ".html")
        html_path = target_dir / html_name
        pdf_path = target_dir / pdf_name


        html_path.write_text(html_content, encoding="utf-8")
        tasks_to_convert.append((html_path, pdf_path))

    html_time = time.perf_counter() - t_html_start
    print(f"[完成] 全量 606 份深度档案 HTML 生成完成！耗时: {html_time:.2f} 秒 (平均 {(html_time/len(universe))*1000:.1f}ms/家)")

    print(f"\n[阶段二] 正在以 8 进程并发调度进行 Headless Chromium PDF 高规格矢量渲染 (总计 {len(tasks_to_convert)} 份)...")
    t_pdf_start = time.perf_counter()
    success_count = 0
    fail_count = 0

    # 8 进程并发调度
    with ProcessPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(convert_pdf_worker, task): task for task in tasks_to_convert}
        total = len(futures)
        completed = 0
        for fut in as_completed(futures):
            pdf_name, ok, elap = fut.result()
            completed += 1
            if ok:
                success_count += 1
            else:
                fail_count += 1
            if completed % 50 == 0 or completed == total:
                pct = completed / total * 100
                print(f"  [并发进度] {completed}/{total} ({pct:.1f}%) 已渲染完成 (成功: {success_count}, 失败: {fail_count})")

    pdf_time = time.perf_counter() - t_pdf_start
    throughput = pdf_time / len(tasks_to_convert) if tasks_to_convert else 0
    print("\n" + "=" * 70)
    print(f"[完成] 场景 2 全量深度档案 PDF 生成完成！")
    print(f"   - 成功生成: {success_count} 份高规格 PDF")
    print(f"   - 总渲染耗时: {pdf_time:.1f} 秒 ({pdf_time/60:.1f} 分钟)")
    print(f"   - 8 进程等效吞吐: {throughput:.2f} 秒 / 份 PDF")
    print("=" * 70)


if __name__ == "__main__":
    main()
