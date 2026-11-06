"""单体标的数据源准确性核验报告 (verify_single_ticker_data_source.py).

严格遵循用户指示：“分步骤来，检查数据源的准确性，单体未确认完不开展计算”。
只读核验英伟达 (NVDA) 底层数据源，输出原始凭证、物理路径、时间戳与字段值。
"""

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def verify_nvda_data_sources():
    report = {}

    # =========================================================================
    # 1. 行情数据源原始凭证核对 (调用统一权威行情核验工具 MarketQuoteVerifier)
    # =========================================================================
    from finance_tools.market_quote_verifier import MarketQuoteVerifier
    verifier = MarketQuoteVerifier(PROJECT_ROOT)
    try:
        vq = verifier.get_latest_quote("NVDA")
        report["market_quote"] = {
            "source_file": vq.source_file,
            "source_type": vq.source_type,
            "session_type": vq.session_type,
            "ticker": vq.ticker,
            "raw_price": vq.price,
            "formatted_price": vq.formatted_price,
            "currency": vq.currency,
            "timestamp_iso": vq.timestamp_iso,
            "timestamp_formatted": vq.timestamp_formatted,
            "sha256_hash": vq.sha256_hash,
            "is_valid": vq.is_valid,
            "google_sheets_formula": '=INDEX(GOOGLEFINANCE("NVDA", "price", TODAY()), 2, 2)',
            "google_sheets_dated_formula": verifier.generate_google_sheets_quote_formula("NVDA", as_of_date=vq.timestamp_iso),
        }
    except Exception as e:
        report["market_quote"] = {"error": f"未能通过工具获取有效行情凭证: {e}"}

    # =========================================================================
    # 2. 官方财报底层原始凭证核对 (SEC EDGAR 10-K)
    # =========================================================================
    filing_file = Path("D:/美股分析/02_格式化标准三表库/JSON格式/NVDA_NVIDIA_CORP_标准财报底稿.json")
    internal_filing = PROJECT_ROOT / "reports" / "ai_dossiers" / "US" / "NVDA_deep_dossier.json"

    if filing_file.exists():
        f_raw = json.loads(filing_file.read_text(encoding="utf-8"))
        meta = f_raw.get("metadata", {})
        bs = f_raw.get("balance_sheet", {})
        inc = f_raw.get("income_statement", {})
        cf = f_raw.get("cash_flow_statement", {})

        tot_assets = bs.get("total_assets")
        tot_liab = bs.get("total_liabilities")
        equity = bs.get("stockholders_equity")
        balance_diff = abs(tot_assets - (tot_liab + equity)) if (tot_assets and tot_liab and equity) else None

        report["official_filing"] = {
            "source_file": str(filing_file),
            "source_type": "external_standardized_filings",
            "company_name": meta.get("company_name"),
            "ticker": meta.get("ticker"),
            "cik": meta.get("cik"),
            "fiscal_year": meta.get("fiscal_year"),
            "fiscal_year_end": meta.get("fiscal_year_end"),
            "form": meta.get("form"),
            "source_filing": meta.get("source_filing"),
            "balance_sheet_raw": {
                "total_assets": tot_assets,
                "total_liabilities": tot_liab,
                "stockholders_equity": equity,
                "cash_and_equivalents": bs.get("cash_and_cash_equivalents"),
                "inventory": bs.get("inventory"),
                "total_debt": bs.get("total_debt"),
                "accounting_balance_identity": f"{tot_assets} == {tot_liab} + {equity}",
                "accounting_balance_error": balance_diff,
            },
            "income_statement_raw": {
                "revenue": inc.get("revenue"),
                "cost_of_revenue": inc.get("cost_of_revenue"),
                "gross_profit": inc.get("gross_profit"),
                "operating_income": inc.get("operating_income"),
                "net_income": inc.get("net_income"),
                "diluted_shares": inc.get("diluted_shares"),
            },
            "cash_flow_statement_raw": {
                "operating_cash_flow": cf.get("operating_cash_flow"),
                "capital_expenditures": cf.get("capital_expenditures"),
                "free_cash_flow": cf.get("free_cash_flow"),
            }
        }
    elif internal_filing.exists():
        f_raw = json.loads(internal_filing.read_text(encoding="utf-8"))
        meta = f_raw.get("overview", {})
        stmts = f_raw.get("financial_statements", {})

        tot_assets = stmts.get("total_assets")
        tot_liab = stmts.get("total_liabilities")
        equity = stmts.get("stockholders_equity")
        balance_diff = abs(tot_assets - (tot_liab + equity)) if (tot_assets and tot_liab and equity) else None

        report["official_filing"] = {
            "source_file": str(internal_filing.relative_to(PROJECT_ROOT)),
            "source_type": "project_archived_official_dossier",
            "company_name": meta.get("company_name"),
            "ticker": meta.get("ticker"),
            "fiscal_year": stmts.get("fiscal_year"),
            "currency": stmts.get("currency"),
            "source_filing": stmts.get("source_filing"),
            "balance_sheet_raw": {
                "total_assets": tot_assets,
                "total_liabilities": tot_liab,
                "stockholders_equity": equity,
                "cash_and_equivalents": stmts.get("cash_and_equivalents"),
                "inventory": stmts.get("inventory"),
                "total_debt": stmts.get("total_debt"),
                "accounting_balance_identity": f"${tot_assets:,.2f} == ${tot_liab:,.2f} + ${equity:,.2f}",
                "accounting_balance_error": balance_diff,
                "balance_sheet_status": stmts.get("balance_sheet_status"),
            },
            "income_statement_raw": {
                "revenue": stmts.get("revenue"),
                "gross_profit": stmts.get("gross_profit"),
                "operating_income": stmts.get("operating_income"),
                "net_income": stmts.get("net_income"),
            },
            "cash_flow_statement_raw": {
                "operating_cash_flow": stmts.get("operating_cash_flow"),
                "capital_expenditures": stmts.get("capex"),
                "free_cash_flow": stmts.get("free_cash_flow"),
            }
        }
    else:
        report["official_filing"] = {"error": "未找到财报底稿文件"}

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return report


if __name__ == "__main__":
    verify_nvda_data_sources()
