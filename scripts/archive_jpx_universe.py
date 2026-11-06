import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNIVERSE_DIR = ROOT / "data" / "universe"
UNIVERSE_DIR.mkdir(parents=True, exist_ok=True)

# URL for JPX listed companies (Excel)
jpx_url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
req = urllib.request.Request(
    jpx_url,
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
)
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read()
        jpx_path = UNIVERSE_DIR / "jpx_data_j.xls"
        jpx_path.write_bytes(content)
        print(f"[归档完成] JPX 全量东证上市公司原始底表已下载: {jpx_path} ({len(content)} 字节)")
except Exception as e:
    print(f"[归档异常] JPX 下载失败: {e}")
