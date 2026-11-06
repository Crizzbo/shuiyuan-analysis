"""将公司深度档案批量重命名为【代码】_【中文名称】.pdf 规范格式 (安全复制/移动版本)."""

from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from financial_reporting.scenario2_universe import get_scenario2_universe
from financial_reporting.chinese_names_registry import get_dossier_filename

DOSSIER_DIR = ROOT / "reports" / "dossiers_dist"

def safe_move(src: Path, dst: Path):
    if src == dst or not src.exists():
        return False
    try:
        shutil.copy2(src, dst)
        try:
            src.unlink()
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"Error moving {src.name} -> {dst.name}: {e}")
        return False

def main():
    universe = get_scenario2_universe()
    print(f"[批量重命名] 开始将场景 2 全量 {len(universe)} 家公司深度档案重命名为【股票代码】_【中文标准名称】...")
    
    renamed_pdf = 0
    renamed_html = 0

    for comp in universe:
        cid = comp["company_id"]
        ticker = comp.get("ticker", "").split(":")[-1].upper()
        mkt = comp["market"]
        target_dir = DOSSIER_DIR / mkt
        
        target_pdf_name = get_dossier_filename(comp)
        target_html_name = target_pdf_name.replace(".pdf", ".html")
        
        target_pdf = target_dir / target_pdf_name
        target_html = target_dir / target_html_name

        old_pdf_candidates = [
            target_dir / f"{cid}.pdf",
            target_dir / f"{ticker.lower()}.pdf",
            target_dir / f"{ticker}.pdf",
        ]
        old_html_candidates = [
            target_dir / f"{cid}.html",
            target_dir / f"{ticker.lower()}.html",
            target_dir / f"{ticker}.html",
        ]
        
        existing_pdfs = [p for p in target_dir.glob(f"{ticker}_*.pdf") if p != target_pdf]
        if not existing_pdfs and not target_pdf.exists():
            existing_pdfs = [p for p in old_pdf_candidates if p.exists() and p != target_pdf]
            
        for p in existing_pdfs:
            if safe_move(p, target_pdf):
                renamed_pdf += 1
                break
                
        existing_htmls = [h for h in target_dir.glob(f"{ticker}_*.html") if h != target_html]
        if not existing_htmls and not target_html.exists():
            existing_htmls = [h for h in old_html_candidates if h.exists() and h != target_html]

        for h in existing_htmls:
            if safe_move(h, target_html):
                renamed_html += 1
                break

    print(f"[完成] 重命名完成！成功重命名 {renamed_pdf} 份 PDF 和 {renamed_html} 份 HTML 文件为【股票代码_中文名称】格式。")

if __name__ == "__main__":
    main()
