"""经逐页人工核对的任天堂 J-GAAP 年报模板；仅适用 SHA 锁定的官方英文译本。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
plan={'id':'nintendo-2026-annual-v1','entity_id':'JP:7974','format':'pdf_reviewed',
 'receipt_path':'data/browser-search/receipts/496f23b72fe37aadd7585537bbaabeb8b3f5800a4b02c1f3cb2731926d67fe94.json',
 'expected_sha256':'adf1d61bfa20412235535f3689e3a52805e46947214f874377d428ffeb878d16',
 'currency':'JPY','accounting_basis':'J-GAAP','cover_text':'Nintendo Co., Ltd.',
 'basis_page':3,'basis_text':'generally accepted in Japan','rounding_tolerance':'1000000',
 'supersedes_report_id':None,'translation_notes':'发行人官方英文译本；日文原版优先。美元列仅为便利折算，不作为美元事实。', 'rows':[]}
def row(field,page,label,instant=False,tokens=None):
    plan['rows'].append({'field':field,'page':page,'label':label,'note':None,
      'scope_id':'consolidated','basis':'instant' if instant else 'annual','years':[2025,2026],
      'header':'Previous fiscal year' if instant else 'Consolidated statements of income' if page==61 else 'Consolidated statements of cash flows',
      'year_header':'March 31, 2026','unit_header':'(millions of yen)',
      'column_tokens':tokens or ['amount','amount','amount'],'selected_columns':[0,1]})
row('assets',59,'Total assets',True)
row('cash_deposits',59,'Cash and deposits',True)
row('liabilities',60,'Total liabilities',True)
row('equity',60,'Total net assets',True)
row('revenue',61,'Net sales')
row('operating_income',61,'Operating profit')
row('net_income',61,'Profit')
row('operating_cash_flow',66,'Net cash provided by (used in) operating activities')
row('investing_cash_flow',66,'Net cash provided by (used in) investing activities')
row('financing_cash_flow',66,'Net cash provided by (used in) financing activities')
row('fx_cash_change',66,'Effect of exchange rate change on cash and cash equivalents')
row('cash_change',66,'Net increase (decrease) in cash and cash equivalents')
row('cash_begin',66,'Cash and cash equivalents at beginning of period')
row('cash_end',66,'Cash and cash equivalents at end of period',tokens=['*1','amount','*1','amount','amount'])
row('capex_ppe_and_intangibles',66,'Purchase of property, plant and equipment and intangible\nassets')
(ROOT/'examples/financial/nintendo-2026.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
