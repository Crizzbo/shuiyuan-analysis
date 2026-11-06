import urllib.request
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNIVERSE_DIR = ROOT / "data" / "universe"
UNIVERSE_DIR.mkdir(parents=True, exist_ok=True)

# 1. Fetch and archive SEC EDGAR tickers
sec_url = "https://www.sec.gov/files/company_tickers.json"
req = urllib.request.Request(
    sec_url,
    headers={"User-Agent": "ShuiyuanResearch/1.0 (contact@shuiyuan.local)"}
)
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read()
        sec_path = UNIVERSE_DIR / "sec_company_tickers.json"
        sec_path.write_bytes(content)
        sec_data = json.loads(content.decode("utf-8"))
        print(f"[归档完成] SEC EDGAR 全量美股标的已归档至 data/universe/sec_company_tickers.json (总计: {len(sec_data)} 家)")
except Exception as e:
    print(f"[归档异常] SEC 归档失败: {e}")
