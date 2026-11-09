from pathlib import Path

p = Path("data_sources/batch56_verified_dossiers_data.py")
text = p.read_text(encoding="utf-8")
text = text.replace('"financial_three_sheets_audit":', '"financial_statement_deep_dive":')
p.write_text(text, encoding="utf-8")
print("Successfully replaced financial_three_sheets_audit with financial_statement_deep_dive")
