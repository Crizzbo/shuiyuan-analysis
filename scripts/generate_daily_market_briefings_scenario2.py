"""以场景 2 (606 家中坚主力池: 标普 500 + 日股核心 100 强) 为基础生成美股与日股大盘总行情与深度推荐研报."""

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from financial_reporting.scenario2_universe import get_scenario2_universe
from financial_reporting.macro_valuation import MacroContext
from financial_reporting.market_summary_generator import render_market_summary_briefing_html
from scripts.convert_html_to_pdf import convert_html_to_pdf

OUT_DIR = ROOT / "reports" / "samples_for_review"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_market_briefings_scenario2():
    macro = MacroContext.load_latest()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    all_companies = get_scenario2_universe()

    us_companies = [c for c in all_companies if c["market"] == "US"]
    jp_companies = [c for c in all_companies if c["market"] == "JP"]

    print("=" * 70)
    print("[研报生成] 正在以【场景 2 中坚主力资产池】为基底生成每日大盘总行情研报...")
    print(f"   - 美股资产池: {len(us_companies)} 家标普 500 核心成分股")
    print(f"   - 日股资产池: {len(jp_companies)} 家东证核心 100 强龙头")
    print("=" * 70)

    # 1. 美股大盘总行情研报 (A4 PDF)
    us_html = render_market_summary_briefing_html("US", us_companies, macro, today_str)
    us_html_path = OUT_DIR / f"{today_str}_美股市场每日总行情与推荐_v3.html"
    us_pdf_path = OUT_DIR / f"{today_str}_美股市场每日总行情与推荐_v3.pdf"
    us_html_path.write_text(us_html, encoding="utf-8")
    ok_us = convert_html_to_pdf(us_html_path, us_pdf_path)
    if ok_us:
        print(f"[完成] [美股] 成功生成基于标普500核心池的大盘总行情研报: {us_pdf_path.name}")
    else:
        print(f"[失败] [美股] 大盘研报 PDF 转换失败")

    # 2. 日股大盘总行情研报 (A4 PDF)
    jp_html = render_market_summary_briefing_html("JP", jp_companies, macro, today_str)
    jp_html_path = OUT_DIR / f"{today_str}_日股市场每日总行情与推荐_v3.html"
    jp_pdf_path = OUT_DIR / f"{today_str}_日股市场每日总行情与推荐_v3.pdf"
    jp_html_path.write_text(jp_html, encoding="utf-8")
    ok_jp = convert_html_to_pdf(jp_html_path, jp_pdf_path)
    if ok_jp:
        print(f"[完成] [日股] 成功生成基于东证核心100强的大盘总行情研报: {jp_pdf_path.name}")
    else:
        print(f"[失败] [日股] 大盘研报 PDF 转换失败")


if __name__ == "__main__":
    generate_market_briefings_scenario2()
