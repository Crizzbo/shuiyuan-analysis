"""生成全量公司深度档案 (根据新 Schema，包含原始数据底稿与情景 DCF)."""

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from financial_reporting.company_universe import get_universe
from financial_reporting.macro_valuation import MacroContext
from financial_reporting.deep_schema_generator import build_deep_dossier_data
from financial_reporting.pdf_templates import render_deep_dossier_pdf_html
from scripts.convert_html_to_pdf import convert_html_to_pdf

DOSSIER_DIR = ROOT / "reports" / "dossiers_dist"
DOSSIER_DIR.mkdir(parents=True, exist_ok=True)
(DOSSIER_DIR / "US").mkdir(parents=True, exist_ok=True)
(DOSSIER_DIR / "JP").mkdir(parents=True, exist_ok=True)


def build_all_dossiers_pdf():
    macro = MacroContext.load_latest()
    universe = get_universe()
    print(f"[批量构建] 开始批量生成全量 {len(universe)} 家公司深度档案 (包含原始数据表与情景DCF)...")

    success = 0
    for comp in universe:
        cid = comp["company_id"]
        mkt = comp["market"]
        ticker = comp["ticker"]
        name_zh = comp["name_zh"]

        # 1. 结构化构建
        dossier_data = build_deep_dossier_data(comp, macro)
        html_content = render_deep_dossier_pdf_html(dossier_data)

        target_dir = DOSSIER_DIR / mkt
        html_path = target_dir / f"{cid}.html"
        pdf_path = target_dir / f"{cid}.pdf"

        html_path.write_text(html_content, encoding="utf-8")
        ok = convert_html_to_pdf(html_path, pdf_path)
        if ok:
            success += 1
            print(f"  [完成] [{mkt}] {name_zh} ({ticker}) 深度档案 PDF 已生成")
        else:
            print(f"  [失败] [{mkt}] {name_zh} ({ticker}) PDF 转换未成功")

    print(f"[全量完成] 公司深度档案生成完成: {success}/{len(universe)} 份 PDF 已就绪！")


if __name__ == "__main__":
    build_all_dossiers_pdf()
