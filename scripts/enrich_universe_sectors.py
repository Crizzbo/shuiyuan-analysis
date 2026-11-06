"""美股全息资产池行业板块标准映射注入工具 (enrich_universe_sectors.py).

严格遵循 2026-10-15 架构防劣变准则与 IndustryTaxonomyBridge 行业契约：
1. 从 data/universe/sp500_universe.json 提取权威标普500 GICS 11 大行业板块与细分产业；
2. 转换为标准自然中文功能语义板块名称 (信息技术、医疗保健、可选消费、金融、工业等)；
3. 增量更新 D:/美股分析/00_资产池全息总索引/美股上市公司总览底账_Master_Universe.json，保持数据完整性。
"""

import json
from pathlib import Path
import sys
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SECTOR_EN_TO_ZH = {
    "Information Technology": "信息技术 (Information Technology)",
    "Health Care": "医疗保健 (Health Care)",
    "Consumer Discretionary": "可选消费 (Consumer Discretionary)",
    "Financials": "金融 (Financials)",
    "Industrials": "工业 (Industrials)",
    "Communication Services": "通信服务 (Communication Services)",
    "Consumer Staples": "必需消费 (Consumer Staples)",
    "Energy": "能源 (Energy)",
    "Utilities": "公用事业 (Utilities)",
    "Real Estate": "房地产 (Real Estate)",
    "Materials": "原材料 (Materials)",
}


def enrich_universe_master(base_dir: Path = Path("D:/美股分析")) -> Dict[str, Any]:
    master_path = base_dir / "00_资产池全息总索引" / "美股上市公司总览底账_Master_Universe.json"
    sp500_path = ROOT / "data" / "universe" / "sp500_universe.json"

    if not master_path.exists():
        raise FileNotFoundError(f"未找到全息总览底账: {master_path}")
    if not sp500_path.exists():
        raise FileNotFoundError(f"未找到标普500行业底账: {sp500_path}")

    master_data = json.loads(master_path.read_text(encoding="utf-8"))
    sp500_data = json.loads(sp500_path.read_text(encoding="utf-8"))

    sp500_map = {}
    for item in sp500_data.get("constituents", []):
        sym = item.get("symbol", "").upper()
        if sym:
            sp500_map[sym] = {
                "sector_en": item.get("sector", ""),
                "sector_zh": SECTOR_EN_TO_ZH.get(item.get("sector", ""), item.get("sector", "")),
                "industry": item.get("industry", ""),
            }

    updated_count = 0
    for company in master_data.get("companies", []):
        ticker = company.get("ticker", "").upper()
        if ticker in sp500_map:
            info = sp500_map[ticker]
            company["sector"] = info["sector_zh"]
            company["industry"] = info["industry"]
            updated_count += 1
        elif not company.get("sector"):
            company["sector"] = "未分类广谱长尾池 (Unclassified)"

    master_data["last_enriched_at"] = "2026-11-01T09:30:00Z"
    master_path.write_text(json.dumps(master_data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[板块注入] 成功将权威行业板块信息注入 {updated_count} 家标普500与核心龙头企业！")
    print(f"[底账更新] 资产池总览底账已更新: {master_path}")
    return {"updated_count": updated_count, "total_companies": len(master_data.get("companies", []))}


if __name__ == "__main__":
    enrich_universe_master()
