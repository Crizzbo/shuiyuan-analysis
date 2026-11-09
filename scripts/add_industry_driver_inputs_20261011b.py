"""归档本次已经人工核对的官方原文；不联网，不把来源调查当自动采集。"""
import json
import sys
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from financial_reporting.pipeline import save_object, digest
from pypdf import PdfReader

def main():
    sources=[];bindings=[];approved={}
    discovery=json.loads((ROOT/'knowledge/metrics/representative-source-discovery.json').read_text(encoding='utf8'))['sources']
    def src(industry,date,locator,excerpts,url=None):
        s=dict(industry_id=industry,published_date=date,locator=locator,excerpts=excerpts,observations=[],source_url=url or discovery[industry])
        sources.append(s)
        if s['source_url']!=discovery[industry]: approved.setdefault(industry,[]).append(s['source_url'])
        return s
    def pdf(s,path,url,pages):
        # 完整 PDF 按字节哈希追加保存；摘录直接由指定页面提取，保持可复核。
        raw=(ROOT/path).read_bytes();stored,sha=save_object(raw,'pdf')
        s['original_document']=dict(path=stored,sha256=sha,source_url=url,excerpt_pages=pages)
        r=PdfReader(ROOT/path)
        s['excerpts']=[r.pages[p-1].extract_text() for p in pages]
    def obs(s,n,key,name,raw,rawunit,unit,scope,indices,start='2025-01-01',end='2025-12-31',period='annual',role='formula_input',note='仍需完整驱动输入及口径审核'):
        rules={'percent':('percent_divided_by_100','.01'),'USD_million':('million_times_1000000','1000000'),'USD_billion':('billion_times_1000000000','1000000000'),'USD_thousand':('accounting_thousand_times_1000','1000'),'thousand_shares':('accounting_thousand_times_1000','1000'),'million_units':('million_quantity_times_1000000','1000000')}
        rule,factor=rules.get(rawunit,('remove_thousands_separator','1'))
        text=raw.replace(',','')
        if text.startswith('('): text='-'+text[1:-1]
        parent=s['industry_id']+'_driver_'+str(n)
        b=dict(component=key,name_zh=name,parent_metric_id=parent,raw_unit=rawunit,unit=unit,binding_role=role,limitation_zh=note)
        bindings.append(b)
        s['observations'].append({**b,'raw_value':raw,'value':str(Decimal(text)*Decimal(factor)),'conversion':rule,'period_start':start,'period_end':end,'period_type':period,'scope':scope,'excerpt_indices':indices})

    s=src('oil_gas','2026-02-24','Volumes and Prices / Revenues, Costs and Margins per Boe; annual 2025 column',[
      'Volumes and Prices (Unaudited) 2024 2025 First Second Third Fourth Full First Second Third Fourth Full Quarter Quarter Quarter Quarter Year Quarter Quarter Quarter Quarter Year',
      'Composite Crude Oil and Condensate Average Price ($/Bbl) 65.63',
      'Composite Natural Gas Average Price ($/Mcf) 3.02',
      'Revenues, Costs and Margins Per Barrel of Oil Equivalent (Continued) 2025 2024 2023 2022 2021 (In millions, except per barrel of oil equivalent data) Volume - Million Barrels Oil Equivalent 449.8',
      'Lease and Well 1,675 Gathering, Processing and Transportation 2,134 General and Administrative 820 Taxes Other Than Income 1,234 Interest Expense 235',
      'Cash Operating Costs consist of LOE, GP&T and G&A. Cash Operating Costs 10.28'])
    obs(s,1,'eog_crude_realized_price','原油凝析油综合实现售价','65.63','USD_per_Bbl','USD_per_Bbl','composite_crude_condensate',[0,1],role='reported_metric',note='按产品单独保存；套保排除规则待完整脚注核对，不代替收入和销售量输入')
    obs(s,1,'eog_gas_realized_price','天然气综合实现售价','3.02','USD_per_Mcf','USD_per_Mcf','composite_natural_gas',[0,2],role='reported_metric',note='Mcf 不是 MMBtu；套保口径待完整脚注核对')
    for key,name,raw in [('eog_lease_well_cost','租赁及井运营成本','1,675'),('eog_gather_processing_cost','集输加工运输成本','2,134'),('eog_gaap_ga_cost','GAAP 管理费用','820'),('eog_production_other_tax','非所得税税费','1,234')]:
        obs(s,2,key,name,raw,'USD_million','USD','consolidated_reported_sales_cost_schedule',[3,4],note='分别保存成本项目；现金性、生产税归属及开采范围待核，不自动求和为开采现金成本')
    obs(s,2,'eog_sales_equivalent_volume','成本表油当量销售量','449.8','million_units','Boe','consolidated_reported_sales_cost_schedule',[3],note='销售量不能替代储量表含实物权益产量；是否匹配开采成本待核')
    obs(s,2,'eog_reported_cash_operating_cost','报告单位现金运营成本','10.28','USD_per_Boe','USD_per_Boe','LOE_plus_GPT_plus_GA_excluding_production_tax',[5],role='scope_mismatch_sample',note='公司定义包括管理费但排除生产税，与项目单位开采现金成本并非自动等价')

    s=src('aerospace_defense','2026-01-29','Aircraft Deliveries, years ended Dec. 31; 2025 annual column',[
      'Aircraft Deliveries Quarters Ended Dec. 31, Years Ended Dec. 31, 2025 2024 2025 2024',
      'F-35 48 62 191 110','F-16 4 7 16 16','C-130J — 8 2 21'])
    for key,name,raw,i in [('lmt_f35_delivered','F-35 年度交付数量','191',1),('lmt_f16_delivered','F-16 年度交付数量','16',2),('lmt_c130j_delivered','C-130J 年度交付数量','2',3)]:
        obs(s,3,key,name,raw,'aircraft','aircraft',key,[0,i],note='具体机型报告交付数；是否全部通过客户验收待核，不拼成跨型号单一产量')

    s=src('travel_leisure',None,'KEY LODGING STATISTICS, comparable company-operated US & Canada, twelve months ended Dec.31 2025',[
      'KEY LODGING STATISTICS In Constant $ Comparable Company-Operated U.S. & Canada Properties Twelve Months Ended December 31, 2025 and 2024',
      'U.S. & Canada - All5 $185.78 2.3% 69.0% -0.4% pts. $269.36 2.9%',
      'Occupancy, ADR and RevPAR comparisons between 2025 and 2024 reflect properties that are comparable in both years.'])
    obs(s,1,'mar_company_operated_occupancy','美加可比自营酒店年度入住率','69.0','percent','ratio','comparable_company_operated_US_Canada',[0,1,2],role='reported_metric',note='固定可比自营酒店群；不与加盟或全球系统酒店 ADR 混配；原始售出和可售房晚仍缺')
    obs(s,2,'mar_company_operated_adr','美加可比自营酒店年度日均房价','269.36','USD_per_room_night','USD_per_room_night','comparable_company_operated_US_Canada',[0,1,2],role='reported_metric',note='常量美元与可比酒店群口径；原始客房收入及售出房晚仍缺')

    s=src('it_services','2026-10-01','Official FY2026 results PDF, page 4, annual bookings and revenues',[])
    pdf(s,'data/browser-search/acn-fy2026-official.pdf','https://newsroom.accenture.com/content/4q-full-fy26-earnings/accenture-reports-fourth-quarter-and-full-year-fiscal-2026-results.pdf',[4])
    for key,name,raw,scope in [('acn_annual_new_bookings','年度集团新签合同','84.54','consolidated'),('acn_consulting_new_bookings','年度咨询新签合同','40.86','consulting'),('acn_managed_new_bookings','年度托管服务新签合同','43.67','managed_services')]:
        obs(s,2,key,name,raw,'USD_billion','USD',scope,[0],start='2025-09-01',end='2026-08-31',note='保留公司合同估计金额；取消权、汇率及变动范围待核，不等同已确认收入')

    s=src('software','2026-02-10','Condensed Statements / SBC reconciliation; annual 2025 column, in thousands',[
      'In thousands, except per share data; unaudited Three Months Ended December 31, Year Ended December 31, 2025 2024 2025 2024',
      'Stock-based compensation, net of amounts capitalized 205,386 158,461 750,671 570,336',
      'Weighted average shares used in computing net income per share: Diluted 365,516 360,940 363,471 358,636'])
    obs(s,3,'ddog_annual_sbc_expense','年度股权激励费用（扣资本化）','750,671','USD_thousand','USD','consolidated',[0,1],note='仅费用部分，资本化股权激励待补；不能独立生成稀释率')
    obs(s,3,'ddog_weighted_diluted_eps_shares','年度 EPS 加权稀释股数','363,471','thousand_shares','shares','consolidated',[0,2],role='context_sample',note='EPS 加权股数不是期末实际发行股数，禁止用于期初期末稀释计算')

    s=src('managed_care','2026-01-27','Official FY2025 results PDF, adjusted MCR table page 20, reported annual column',[])
    pdf(s,'data/browser-search/unh-fy2025-official.pdf','https://www.unitedhealthgroup.com/content/dam/UHG/PDF/investors/2025/unh-reports-2025-results-and-issues-2026-outlook.pdf',[20])
    obs(s,1,'unh_reported_premium_revenue','年度报告保费收入','352,229','USD_million','USD','consolidated_reported_medical_care',[0],note='报告口径，禁止与调整后医疗成本混配')
    obs(s,1,'unh_reported_medical_cost','年度报告医疗成本','313,995','USD_million','USD','consolidated_reported_medical_care',[0],note='报告口径，包括亏损合同调整影响；不能混配调整后保费')
    obs(s,1,'unh_reported_mcr','年度报告医疗成本率','89.1','percent','ratio','consolidated_reported_medical_care',[0],role='reported_metric',note='报告比例取整；调整后 88.9% 是另一口径')

    s=src('biotech',None,'Cash Position paragraph, Dec.31 2025 actual, not 2026 outlook',[
      'Cash, cash equivalents and investments as of December 31, 2025, were $8.1 billion, compared to compared to $9.5 billion as of December 31, 2024.',
      'The year-end balance included a $600 million initial draw on the Company’s $1.5 billion credit facility.'])
    obs(s,2,'mrna_cash_investments_reported','期末现金等价物及投资合计','8.1','USD_billion','USD','consolidated_cash_equivalents_and_investments',[0,1],start=None,period='instant',note='包含投资及借款提款；受限资金、投资可变现性和标准化月度现金消耗尚缺')

    s=src('hardware',None,'Worldwide PlayStation 5 Hardware Unit Sales, sell-in, FY2025 annual',[
      'Worldwide PlayStation 5 Hardware Unit Sales (Sell-in / Unit: millions)',
      'Q1 (April-June) Q2 (July-September) Q3 (October-December) Q4 (January-March) FY (April-March)',
      'FY2025 2.5 4.0 7.9 1.5 16.0','Including returned and refurbished products'])
    obs(s,1,'sony_ps5_fy2025_sellin','PS5 财年渠道出货量','16.0','million_units','systems','PS5_sellin_including_returned_refurbished',[0,1,2,3],start='2025-04-01',end='2026-03-31',note='sell-in 不是终端零售；包含退回和翻新产品，不能代表 Sony 全部硬件出货')

    s=src('media_entertainment','2026-01-23','2025 10-K consolidated cash flows, annual 2025 column',[
      'CONSOLIDATED STATEMENTS OF CASH FLOWS (in thousands) Year Ended December 31, 2025 2024 2023',
      'Additions to content assets (17,096,617) (16,223,617) (12,554,703)',
      'Change in content liabilities (610,838) (779,135) (585,602)',
      'Amortization of content assets 16,422,166 15,301,517 14,197,437'],url='https://www.sec.gov/Archives/edgar/data/1065280/000106528026000034/nflx-20251231.htm')
    obs(s,2,'nflx_content_asset_additions_cf','内容资产新增的现金流调节项','(17,096,617)','USD_thousand','USD','consolidated_content_cashflow',[0,1],note='按现金流表保留负号；单独该项不是内容现金支付，须结合内容负债变动')
    obs(s,2,'nflx_content_liability_change_cf','内容负债变动现金流项','(610,838)','USD_thousand','USD','consolidated_content_cashflow',[0,2],note='保留现金流负号，与同期间内容资产新增配对；不是期末负债余额')
    obs(s,2,'nflx_content_amortization','年度内容摊销','16,422,166','USD_thousand','USD','consolidated_content_cashflow',[0,3],note='非现金费用；不能直接视作内容现金支出')

    s=src('banks',None,'2025 10-K net interest income/selected metrics/capital risk tables; footnote b for Q4 average LCR',[
      'Year ended December 31, (in millions, except rates) 2025 2024 2023 Reported net interest income $95,443 Fully taxable-equivalent adjustments 425 Managed net interest income $95,868 Average interest-earning assets $3,834,359 Net yield on interest-earning assets 2.50%',
      'As of or for the year ended December 31, (in millions, except per share, ratio, employee data and where otherwise noted) 2025 2024 2023 Net charge-offs 9,849 Net charge-off rate 0.74%',
      'December 31, 2025 (in millions, except ratios) Standardized Advanced Firm JPMorgan Chase Bank, N.A. Firm JPMorgan Chase Bank, N.A. Common equity Tier 1 capital ratio 14.6% 15.3% 14.1% 15.8%',
      'Firm Liquidity coverage ratio (“LCR”) (average)(b) 111 113 113',
      'For the years ended December 31, 2025, 2024 and 2023, the percentage represents average ratios for the three months ended December 31, 2025, 2024 and 2023.'],url='https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/jpm-20251231.htm')
    obs(s,1,'jpm_managed_net_interest_income','年度税当量管理口径净利息收入','95,868','USD_million','USD','firm_managed_tax_equivalent',[0],note='管理税当量口径而非 GAAP 报告口径；分母使用同表生息资产')
    obs(s,1,'jpm_average_interest_earning_assets','年度平均生息资产','3,834,359','USD_million','USD','firm_managed_tax_equivalent',[0],note='不是期末总资产，也不是剔除 Markets 资产')
    obs(s,1,'jpm_managed_net_yield','年度管理口径净息收益率','2.50','percent','ratio','firm_managed_tax_equivalent',[0],role='reported_metric',note='完全税当量口径；取整披露比例')
    obs(s,2,'jpm_firm_net_chargeoffs','年度全集团净核销额','9,849','USD_million','USD','firm_retained_loans',[1],note='匹配平均留存贷款分母待补；不能使用批发业务单独分母')
    obs(s,2,'jpm_firm_net_chargeoff_rate','年度全集团净核销率','0.74','percent','ratio','firm_retained_loans',[1],role='reported_metric',note='报告比例；平均留存贷款原始输入尚缺')
    obs(s,3,'jpm_standardized_cet1','期末集团标准法 CET1 比率','14.6','percent','ratio','firm_standardized',[2],start=None,period='instant',role='reported_metric',note='标准法集团而非银行子公司或高级法；风险资产及资本分子待补')
    obs(s,3,'jpm_q4_average_lcr','第四季度平均流动性覆盖率','111','percent','ratio','firm_lcr_quarter_average',[3,4],start='2025-10-01',period='quarterly',role='reported_metric',note='脚注限定第四季度平均，不能登记为全年平均；NSFR 实际值仍缺')

    # 背景数值专门隔离，防止把集团收入或总资本开支当专属驱动的完整输入。
    s=src('household_personal','2026-07-29','FY2026 annual sales paragraph',[
      'The Company reported fiscal year 2026 net sales of $87.0 billion, an increase of three percent versus the prior year.'])
    obs(s,3,'pg_fy2026_net_sales','财年集团净销售额','87.0','USD_billion','USD','consolidated',[0],start='2025-07-01',end='2026-06-30',role='context_sample',note='营销费用覆盖范围及金额未取得；净收入不能独立构成营销费用率')
    s=src('telecom',None,'Annual cash flow and capital expenditure paragraph',[
      'Capital expenditures were $17.0 billion in 2025.'])
    obs(s,3,'vz_annual_total_capex','年度集团总资本开支','17.0','USD_billion','USD','consolidated_total_capex',[0],role='scope_mismatch_sample',note='集团总额缺网络、维持性与增长性拆分，不能替代网络资本开支强度')

    targets={
      'data/browser-search/industry-driver-inputs-20261011b.json':dict(schema_version='1.0.0',observed_at='2026-10-11T09:10:10Z',archive_kind='manual_browser_visible_excerpt_with_optional_original_pdf',sources=sources),
      'knowledge/metrics/industry-reviewed-bindings-20261011b.json':dict(schema_version='1.0.0',bindings=bindings),
      'knowledge/metrics/industry-reviewed-sources-20261011b.json':dict(schema_version='1.0.0',sources=approved),
    }
    for name,data in targets.items():
        text=json.dumps(data,ensure_ascii=False,indent=2)+'\n';path=ROOT/name
        if path.exists() and path.read_text(encoding='utf8')!=text: raise ValueError('不可覆盖已登记批次: '+name)
        path.write_text(text,encoding='utf8')
    print(f'追加 {len(sources)} 个来源，{len(bindings)} 个原子字段；PDF 完整文件另行登记')

if __name__=='__main__': main()

