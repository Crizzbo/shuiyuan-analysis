"""生成符合全新 Schema 规范的样例 PDF 文件 (用于用户审阅)."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from financial_reporting.company_universe import get_universe
from financial_reporting.macro_valuation import MacroContext
from financial_reporting.deep_schema_generator import build_deep_dossier_data, build_daily_briefing_data
from financial_reporting.pdf_templates import render_deep_dossier_pdf_html, render_daily_briefing_pdf_html
from scripts.convert_html_to_pdf import convert_html_to_pdf

OUT_DIR = ROOT / "reports" / "samples_for_review"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_samples():
    macro = MacroContext.load_latest()
    
    # 选取美股龙头 NVDA 与日股龙头 7203 (丰田) 作为样例
    targets = ["NASDAQ:NVDA", "TYO:7203"]
    companies = get_universe(tickers=targets)

    sample_pdfs = []

    for comp in companies:
        ticker_clean = comp["ticker"].replace(":", "_").lower()
        
        # 1. 深度档案生成与转换
        dossier_data = build_deep_dossier_data(comp, macro)
        dossier_html = render_deep_dossier_pdf_html(dossier_data)
        dossier_html_path = OUT_DIR / f"{ticker_clean}_公司深度档案.html"
        dossier_pdf_path = OUT_DIR / f"{ticker_clean}_公司深度档案.pdf"
        dossier_html_path.write_text(dossier_html, encoding="utf-8")
        
        ok1 = convert_html_to_pdf(dossier_html_path, dossier_pdf_path)
        if ok1:
            sample_pdfs.append(dossier_pdf_path)
            print(f"[完成] 成功生成公司深度档案 PDF: {dossier_pdf_path.name}")
        else:
            print(f"[失败] 生成公司深度档案 PDF 失败: {dossier_pdf_path.name}")

        # 2. 每日行情研报生成与转换
        briefing_data = build_daily_briefing_data(comp, macro)
        briefing_html = render_daily_briefing_pdf_html(briefing_data)
        briefing_html_path = OUT_DIR / f"{ticker_clean}_每日行情研报.html"
        briefing_pdf_path = OUT_DIR / f"{ticker_clean}_每日行情研报.pdf"
        briefing_html_path.write_text(briefing_html, encoding="utf-8")

        ok2 = convert_html_to_pdf(briefing_html_path, briefing_pdf_path)
        if ok2:
            sample_pdfs.append(briefing_pdf_path)
            print(f"[完成] 成功生成每日行情研报 PDF: {briefing_pdf_path.name}")
        else:
            print(f"[失败] 生成每日行情研报 PDF 失败: {briefing_pdf_path.name}")

    print("\n[就绪] 样例 PDF 生成完毕，路径位于 reports/samples_for_review/")


if __name__ == "__main__":
    generate_samples()
