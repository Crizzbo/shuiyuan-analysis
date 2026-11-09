"""生成美股与日股【每日总行情研报】样例 PDF."""

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from financial_reporting.company_universe import get_universe
from financial_reporting.macro_valuation import MacroContext
from financial_reporting.market_summary_generator import render_market_summary_briefing_html
from scripts.convert_html_to_pdf import convert_html_to_pdf

OUT_DIR = ROOT / "reports" / "samples_for_review"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_market_briefings():
    macro = MacroContext.load_latest()
    today_str = "2026-10-12"

    # 1. 美股总行情研报
    us_companies = get_universe(market="US")
    us_html = render_market_summary_briefing_html("US", us_companies, macro, today_str)
    us_html_path = OUT_DIR / f"{today_str}_美股市场每日总行情与推荐.html"
    us_pdf_path = OUT_DIR / f"{today_str}_美股市场每日总行情与推荐.pdf"
    us_html_path.write_text(us_html, encoding="utf-8")
    ok_us = convert_html_to_pdf(us_html_path, us_pdf_path)
    if ok_us:
        print(f"[完成] 成功生成【美股每日总行情与推荐】PDF: {us_pdf_path.name}")
    else:
        print(f"[失败] 生成美股总行情 PDF 失败")

    # 2. 日股总行情研报
    jp_companies = get_universe(market="JP")
    jp_html = render_market_summary_briefing_html("JP", jp_companies, macro, today_str)
    jp_html_path = OUT_DIR / f"{today_str}_日股市场每日总行情与推荐.html"
    jp_pdf_path = OUT_DIR / f"{today_str}_日股市场每日总行情与推荐.pdf"
    jp_html_path.write_text(jp_html, encoding="utf-8")
    ok_jp = convert_html_to_pdf(jp_html_path, jp_pdf_path)
    if ok_jp:
        print(f"[完成] 成功生成【日股每日总行情与推荐】PDF: {jp_pdf_path.name}")
    else:
        print(f"[失败] 生成日股总行情 PDF 失败")


if __name__ == "__main__":
    generate_market_briefings()
