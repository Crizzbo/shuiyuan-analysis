"""HTML 研报与深度档案批量转 PDF 工具 (使用 Edge Headless Print to PDF)."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
import time

EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def convert_html_to_pdf(html_path: Path, pdf_path: Path) -> bool:
    """调用 Microsoft Edge 无头打印将 HTML 转为 PDF。"""
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    html_abs = str(html_path.resolve())
    pdf_abs = str(pdf_path.resolve())

    cmd = [
        EDGE_EXE,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_abs}",
        html_abs,
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if pdf_path.exists() and pdf_path.stat().st_size > 1000:
            return True
        return False
    except Exception as e:
        return False


def batch_convert_directory(src_dir: Path, dst_dir: Path, max_workers: int = 4) -> int:
    """批量将目录下所有 HTML 文件转为同名 PDF。"""
    html_files = list(src_dir.rglob("*.html"))
    if not html_files:
        return 0

    print(f"[批量转换] 正在批量转换 {len(html_files)} 个 HTML 研报为 PDF: {src_dir.name} -> {dst_dir.name}")
    success_count = 0

    def task(html_f: Path):
        rel = html_f.relative_to(src_dir)
        pdf_f = dst_dir / rel.with_suffix(".pdf")
        ok = convert_html_to_pdf(html_f, pdf_f)
        return ok, html_f.name

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for ok, name in executor.map(task, html_files):
            if ok:
                success_count += 1
            else:
                print(f"  [失败] 转换失败: {name}")

    print(f"[完成] 转换完成: {success_count}/{len(html_files)} 份 PDF 成功生成！")
    return success_count


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python convert_html_to_pdf.py <src_html_dir> <dst_pdf_dir>")
        sys.exit(1)
    batch_convert_directory(Path(sys.argv[1]), Path(sys.argv[2]))
