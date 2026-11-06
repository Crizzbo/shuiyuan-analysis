import json
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]

# 1. 检验 SEC EDGAR 官方全量企业索引
sec_path = ROOT / "data" / "universe" / "sec_company_tickers.json"
sec_count = 0
if sec_path.exists():
    sec_data = json.loads(sec_path.read_text(encoding="utf-8"))
    sec_count = len(sec_data)

# 2. 检验 JPX 东证全市场官方全量企业索引
jpx_path = ROOT / "data" / "universe" / "jpx_company_tickers.json"
jpx_count = 0
if jpx_path.exists():
    jpx_data = json.loads(jpx_path.read_text(encoding="utf-8"))
    jpx_count = len(jpx_data)

# 3. 检验官方三表核验批次档案 (data_sources)
ds_dir = ROOT / "data_sources"
batch_files = list(ds_dir.glob("batch*_verified_dossiers_data.py")) if ds_dir.exists() else []

# 4. 检验主索引清单
manifest_path = ROOT / "data" / "universe" / "universe_10k_manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

print("=" * 60)
print(f"[官方底账索引] 美股 SEC EDGAR 官方备案代码企业数: {sec_count}")
print(f"[官方底账索引] 日股 东证交易所官方挂牌企业数: {jpx_count}")
print(f"[真实核验档案] 官方三表真实核验批次模块数: {len(batch_files)} 个")
print(f"[全景监管主账] 主账清单登记企业总数: {manifest.get('total_companies', 0)}")
print(f"[数据合规状态] {manifest.get('status', 'UNKNOWN')}")
print(f"[去伪隔离声明] {manifest.get('synthetic_data_status', 'UNKNOWN')}")
print("=" * 60)
