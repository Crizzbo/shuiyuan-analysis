"""根据 605 份审计替换包，生成 567 家数据缺口企业的官方取数补全清单 (Gap Manifest).

严格遵循 AGENTS.md 最新数据来源策略:
- 不采用 API Key / 账号认证接口;
- 记录官方监管 (SEC EDGAR / 日本金融厅 EDINET / 交易所 TDnet / 发行人 IR) 的精确检索模版与定位器;
- 明确划分各公司缺失字段规范，为后续分批断点续传与取数登记提供标准底账。
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
ZIP_PATH = ROOT / "reports" / "replacements" / "company-data-corrected-20261012.zip"
SEC_TICKERS_PATH = ROOT / "data" / "universe" / "sec_company_tickers.json"
JPX_TICKERS_PATH = ROOT / "data" / "universe" / "jpx_company_tickers.json"
OUTPUT_PATH = ROOT / "data" / "audits" / "drive-deep-analysis-20261012" / "gap_manifest_567.json"


def load_universe_maps():
    sec_map = {}
    if SEC_TICKERS_PATH.exists():
        try:
            sec_data = json.loads(SEC_TICKERS_PATH.read_text(encoding="utf-8"))
            for _, v in sec_data.items():
                t = v.get("ticker", "").upper()
                sec_map[t] = {
                    "cik_str": str(v.get("cik_str", "")).zfill(10),
                    "title": v.get("title", ""),
                }
        except Exception:
            pass

    jpx_map = {}
    if JPX_TICKERS_PATH.exists():
        try:
            items = jpx_data if isinstance(jpx_data, list) else list(jpx_data.values())
            for v in items:
                if isinstance(v, dict):
                    code = str(v.get("code") or v.get("ticker", "")).replace("TYO:", "").strip()
                    if code:
                        jpx_map[code] = {
                            "company_name": v.get("name", "") or v.get("company_name", ""),
                            "market_segment": v.get("market_segment", "Prime"),
                            "sector_33_name": v.get("industry_33", "") or v.get("sector_33_name", ""),
                        }
        except Exception:
            pass

    return sec_map, jpx_map


def main():
    sec_map, jpx_map = load_universe_maps()

    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
        files = manifest.get("files", [])

        gaps = []
        verified = []

        for item in files:
            mkt = item["market"]
            sym = item["symbol"]
            fname = item["file_name"]
            json_name = f"{mkt}/{sym}.json"

            try:
                comp_data = json.loads(zf.read(json_name).decode("utf-8"))
            except Exception:
                continue

            st = comp_data.get("research_status")
            facts = comp_data.get("facts", [])

            if st == "evidence_missing" or len(facts) == 0:
                # 确定优先级
                p0_symbols = {
                    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG", "META", "TSLA", "AVGO",
                    "LLY", "JPM", "V", "XOM", "WMT", "MA", "PG", "HD", "COST", "ABBV", "MRK",
                    "NFLX", "AMD", "ADBE", "CRM", "INTC", "CSCO", "QCOM", "TXN",
                    "7203", "6758", "7974", "8035", "6861", "4063", "9984", "8058", "8306",
                    "6501", "6954", "6367", "4502", "4568"
                }
                tier = "P0_flagship_megacap" if sym in p0_symbols else "P1_core_industry_leader"

                entry = {
                    "symbol": sym,
                    "market": mkt,
                    "file_name": fname,
                    "tier": tier,
                    "unknowns": comp_data.get("unknowns", []),
                    "limitations": comp_data.get("limitations", []),
                }

                if mkt == "US":
                    sec_info = sec_map.get(sym, {})
                    cik = sec_info.get("cik_str", "")
                    entry["sec_entity_name"] = sec_info.get("title", "")
                    entry["sec_cik"] = cik
                    entry["target_filing_types"] = ["Form 10-K (Annual)", "Form 10-Q (Quarterly)", "Earnings Release 8-K"]
                    entry["primary_source_url"] = f"https://www.sec.gov/edgar/browse/?CIK={cik}" if cik else "https://www.sec.gov/edgar/searchedgar/companysearch"
                    entry["search_query_template"] = f"{sym} investor relations annual report 10-K balance sheet cash flows"
                else:
                    jpx_info = jpx_map.get(sym, {})
                    entry["jpx_company_name"] = jpx_info.get("company_name", "")
                    entry["jpx_market_segment"] = jpx_info.get("market_segment", "Prime")
                    entry["target_filing_types"] = ["有価証券報告書 (年度)", "決算短信 (四半期)", "決算説明会資料"]
                    entry["primary_source_url"] = "https://disclosure2.edinet-fsa.go.jp/"
                    entry["search_query_template"] = f"{sym} {jpx_info.get('company_name', '')} IR 決算短信 有価証券報告書"

                entry["required_components"] = [
                    "official_three_statements (rev, gross_profit, op_inc, net_inc, assets, equity, debt, cash, fcf, shares, eps)",
                    "segment_revenue_mix (actual business reporting segments percentages)",
                    "supply_chain_analysis (core upstream vendors & downstream customers with top-5 concentrations)",
                    "working_capital_and_dio (raw inventory, DIO turnover, accounts receivable DSO)",
                    "debt_structure_and_wall (short/long-term debt breakdown, interest rates, maturities)",
                ]
                gaps.append(entry)
            else:
                verified.append({
                    "symbol": sym,
                    "market": mkt,
                    "file_name": fname,
                    "verified_facts_count": len(facts),
                })

    output_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0.0",
        "total_audited_universe": len(files),
        "verified_companies_count": len(verified),
        "gap_companies_count": len(gaps),
        "verified_companies": verified,
        "gaps_by_tier": {
            "P0_flagship_megacap": [g for g in gaps if g["tier"] == "P0_flagship_megacap"],
            "P1_core_industry_leader": [g for g in gaps if g["tier"] == "P1_core_industry_leader"],
        },
        "all_gap_entries": gaps,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[完成] 567 家数据缺口补全清单已生成: {OUTPUT_PATH}")
    print(f"   - P0 顶层旗舰巨头缺口: {len(output_data['gaps_by_tier']['P0_flagship_megacap'])} 家")
    print(f"   - P1 中坚主力龙头缺口: {len(output_data['gaps_by_tier']['P1_core_industry_leader'])} 家")


if __name__ == "__main__":
    main()
