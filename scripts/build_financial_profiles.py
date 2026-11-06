"""生成已核对的两份财报解析配置；PDF 配置锁定原文件哈希，不套用到其他报告。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
profiles=ROOT/'examples/financial'
profiles.mkdir(parents=True,exist_ok=True)
intu={'id':'intu-2026-10k-v1','entity_id':'US:INTU:CIK896878','format':'inline_zip',
 'receipt_path':'data/browser-search/receipts/c989109050cec976f2be61f1953b27120b4e2f0a91c1e76784058e43d55c3396.json',
 'expected_sha256':'d2c2584bc5662aa133c531a93e716fcea29367cebd7784458d25d205458045fb',
 'member':'intu-20260731.htm','cik':'896878','currency':'USD','accounting_basis':'GAAP',
 'taxonomy_namespace':'http://fasb.org/us-gaap/2026','supersedes_report_id':None}
sony={'id':'sony-2026-20f-v1','entity_id':'JP:6758:CIK313838','format':'pdf_reviewed',
 'receipt_path':'data/browser-search/receipts/58e2ad2f7c9e9641ca491d7def964f25991a321d596cce83a7c0a51df4dc394c.json',
 'expected_sha256':'ea208480be5f6ba6c76a15377b6ea67addc69b274a0fcc9ba479876e40516772',
 'currency':'JPY','accounting_basis':'IFRS','cover_text':'For the fiscal year ended March 31, 2026',
 'basis_page':135,'basis_text':'prepared in accordance with IFRS® Accounting Standards',
 'supersedes_report_id':None,'rows':[]}
def row(field,page,label,note=None,scope='consolidated',instant=False):
    header='Consolidated Statements of Financial Position' if instant else 'Consolidated Statements of Income' if page==128 else 'Consolidated Statements of Cash Flows'
    years=[2025,2026] if instant else [2024,2025,2026]
    sony['rows'].append(dict(field=field,page=page,label=label,note=note,scope_id=scope,
                            basis='instant' if instant else 'annual',years=years,header=header,
                            year_header='March 31,\n2025\nMarch 31,\n2026' if instant else 'Note\n2024\n2025\n2026'))
row('assets',126,'Total assets',instant=True)
row('cash',126,'Cash and cash equivalents','27',instant=True)
row('liabilities',127,'Total liabilities',instant=True)
row('equity',127,'Total equity',instant=True)
row('revenue',128,'Sales','22',scope='consolidated_continuing')
row('operating_income',128,'Operating income',scope='consolidated_continuing')
row('net_income',128,'Net income (loss)')
row('operating_cash_flow',132,'Net cash provided by operating activities')
row('operating_cash_flow',132,'Total net cash provided by operating activities from continuing operations',scope='consolidated_continuing')
row('investing_cash_flow',133,'Net cash used in investing activities')
row('financing_cash_flow',133,'Net cash used in financing activities')
row('fx_cash_change',133,'Effect of exchange rate changes on cash and cash equivalents')
row('cash_change',133,'Net increase (decrease) in cash and cash equivalents')
row('cash_begin',133,'Cash and cash equivalents at beginning of the fiscal year','27')
row('cash_end',133,'Cash and cash equivalents at end of the fiscal year','27')
# 此行同时含固定资产与无形资产，禁止冒充纯 PPE capex。
row('capex_ppe_and_intangibles',133,'Payments for property, plant and equipment and other intangible assets',scope='consolidated_continuing')
for name,data in [('intu-2026',intu),('sony-2026',sony)]:
    (profiles/f'{name}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
