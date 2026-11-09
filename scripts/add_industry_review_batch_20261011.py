"""登记本次人工核对的官方表格摘录；脚本本身不联网、不执行浏览器采集。"""
import json
from pathlib import Path
from decimal import Decimal

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'data/browser-search/industry-specific-expansion-20261011.json'

def main():
    sources=[]; bindings=[]
    def source(industry, publication, locator, excerpts):
        record={'industry_id':industry,'published_date':publication,'locator':locator,
                'excerpts':excerpts,'observations':[]}
        sources.append(record)
        return record
    def observation(s, driver, component, name, raw, raw_unit, unit, conversion,
                    scope, indices, start='2025-01-01', end='2025-12-31', period='annual',
                    role='reported_metric', limitation='仍须审核完整公司定义和研究期间适用性'):
        # 金额倍数与百分数仅做单位转换；不在此处开发金融公式。
        factors={'identity':Decimal(1),'remove_thousands_separator':Decimal(1),
                 'percent_divided_by_100':Decimal('.01'),'million_times_1000000':Decimal(1000000),
                 'billion_times_1000000000':Decimal(1000000000),
                 'cents_divided_by_100':Decimal('.01'),'million_quantity_times_1000000':Decimal(1000000)}
        parent=s['industry_id']+'_driver_'+str(driver)
        value=str(Decimal(raw.replace(',',''))*factors[conversion])
        s['observations'].append({'parent_metric_id':parent,'component':component,'name_zh':name,
             'period_start':start,'period_end':end,'period_type':period,'scope':scope,
             'raw_value':raw,'raw_unit':raw_unit,'value':value,'unit':unit,'conversion':conversion,
             'excerpt_indices':indices,'binding_role':role,'limitation_zh':limitation})
        bindings.append({'component':component,'name_zh':name,'parent_metric_id':parent,
             'raw_unit':raw_unit,'unit':unit,'binding_role':role,'limitation_zh':limitation})

    s=source('transport_logistics','2026-01-13','Statistical Summary; annual 2025 column, not quarterly column',[
      'Statistical Summary\n(Unaudited)\nThree Months Ended\nYear Ended\nDecember 31,\nDecember 31,\n2025\n2024\nChange\n2025\n2024\nChange',
      'Revenue passenger miles (millions)\n59,861\n60,387\n(1)\n%\n249,578\n246,145\n1\n%',
      'Available seat miles (millions)\n72,946\n72,035\n1.3\n%\n298,045\n288,394\n3\n%',
      'Passenger mile yield (cents)\n21.58\n21.22\n2\n%\n20.74\n20.68\n—\n%',
      'Passenger load factor\n82 %\n84 %\n(2)\npts\n84 %\n85 %\n(1)\npt'])
    observation(s,1,'annual_revenue_passenger_miles','年度收入客英里','249,578','million_passenger_miles','passenger_miles','million_quantity_times_1000000','consolidated_airline_passenger_traffic',[0,1],role='formula_input')
    observation(s,1,'annual_available_seat_miles','年度可用座英里','298,045','million_seat_miles','seat_miles','million_quantity_times_1000000','consolidated_airline_passenger_capacity',[0,2],role='formula_input')
    observation(s,1,'annual_passenger_load_factor','年度客座率','84','percent','ratio','percent_divided_by_100','consolidated_airline_passenger_traffic',[0,4],limitation='发行人整数百分比；未取整工作量之比不应强制等于取整客座率')
    observation(s,2,'annual_passenger_mile_yield','年度每收入客英里客运收益','20.74','US_cents_per_passenger_mile','USD_per_passenger_mile','cents_divided_by_100','consolidated_airline_passenger_revenue_yield',[0,3],limitation='yield 不是 PRASM 或 TRASM；英里不可直接当公里')

    s=source('health_services','2026-01-27','Operating Statistics / Same Facility, annual 2025 column; annual consolidated income statement',[
      'Operating Statistics\nFourth Quarter\nFor the Year\nEnded December 31,\n2025\n2024\n2025\n2024',
      'Same Facility:\nAdmissions\n566,249\n553,200\n2,254,279\n2,203,778',
      'Equivalent Admissions\n1,008,489\n984,143\n3,987,820\n3,894,076',
      'Revenue per Equivalent Admission\n$\n18,708\n$\n18,175\n$\n18,314\n$\n17,587',
      'Condensed Consolidated Comprehensive Income Statements\nFor the Years Ended December 31, 2025 and 2024\nUnaudited\n(Dollars in millions, except per share amounts)\n2025\n2024\nAmount\nRatio\nAmount\nRatio',
      'Revenues\n$\n75,600\n100.0\n%\n$\n70,603\n100.0\n%',
      'Salaries and benefits\n32,859\n43.5\n31,170\n44.1'])
    observation(s,1,'same_facility_admissions','同院年度住院次数','2,254,279','admissions','admissions','remove_thousands_separator','same_facility',[0,1],limitation='同院医院群；不能与 reported 全部医院或等价住院次数混合')
    observation(s,1,'same_facility_equivalent_admissions','同院年度等价住院次数','3,987,820','equivalent_admissions','equivalent_admissions','remove_thousands_separator','same_facility',[0,1,2],limitation='保留公司门诊折算及同院纳入定义待核；不是实际住院人数')
    observation(s,2,'same_facility_revenue_per_equivalent_admission','同院每等价住院收入','18,314','USD_per_equivalent_admission','USD_per_equivalent_admission','remove_thousands_separator','same_facility',[0,1,3],limitation='不可与集团全部医院收入和服务量拼接；不是医院收费标价')
    observation(s,3,'consolidated_salaries_benefits','集团年度工资及福利费用','32,859','USD_million','USD','million_times_1000000','consolidated_all_facilities',[4,6],role='formula_input',limitation='集团范围；未确认合同工是否全部包含，不能视作完整人工成本')
    observation(s,3,'consolidated_healthcare_revenue','集团年度收入','75,600','USD_million','USD','million_times_1000000','consolidated_all_facilities',[4,5],role='formula_input',limitation='匹配集团工资福利表，不能与同院服务量计算单位收入')
    observation(s,3,'reported_salaries_benefits_revenue_ratio','报告工资福利收入比','43.5','percent','ratio','percent_divided_by_100','consolidated_all_facilities',[4,5,6],limitation='发行人取整百分比；不声称覆盖所有外包人员费用')

    s=source('staples_retail','2025-09-25','Comparable sales, total company, 52-week fiscal year column',[
      'today announced its operating results for the 16-week fourth quarter and the 52-week fiscal year ended August 31, 2025.',
      'Comparable sales for the fourth quarter and fiscal year were as follows:',
      '16 Weeks\n16 Weeks\n52 Weeks\n52 Weeks\nAdjusted*\nAdjusted*',
      'Total Company\n5.7%\n6.4%\n5.9%\n7.6%',
      '*Excluding the impacts from changes in gasoline prices and foreign exchange.'])
    observation(s,1,'annual_company_comparable_sales_growth','全年集团同店销售增长（未调整）','5.9','percent','ratio','percent_divided_by_100','total_company_reported_including_gasoline_and_fx',[0,1,2,3],start='2024-09-02',end='2025-08-31',limitation='52 周期间；含燃油价格及汇率影响；纳入店群规则仍需年度报告核对')
    observation(s,1,'annual_adjusted_comparable_sales_growth','全年集团同店销售增长（剔除燃油汇率）','7.6','percent','ratio','percent_divided_by_100','total_company_excluding_gasoline_price_and_fx',[0,1,2,3,4],start='2024-09-02',end='2025-08-31',limitation='调整增长率与未调整增长率不可混用；不是客流增长')

    s=source('equity_reit',None,'OPERATING PERFORMANCE, 4Q25; Owned & Managed versus Prologis Share',[
      'OPERATING PERFORMANCE', 'Owned & Managed\n4Q25\nAverage Occupancy\n95.3%\nPeriod End Occupancy\n95.8%',
      'Prologis Share\n4Q25\nAverage Occupancy\n95.2%\nCash Same Store NOI*\n5.7%',
      'This is a non-GAAP financial measure. See the Notes and Definitions in our supplemental information for further explanation and a reconciliation to the most directly comparable GAAP measure.'])
    observation(s,1,'cash_same_store_noi_growth','权益份额现金同物业 NOI 增长','5.7','percent','ratio','percent_divided_by_100','prologis_share_cash_same_store_noi',[0,2,3],start='2025-10-01',period='quarterly',limitation='现金口径非 GAAP；物业群冻结与调节定义仍须补充表核验')
    observation(s,2,'owned_managed_average_occupancy','自有及管理组合平均出租率','95.3','percent','ratio','percent_divided_by_100','owned_and_managed_operating_portfolio_average',[0,1],start='2025-10-01',period='quarterly',role='scope_mismatch_sample',limitation='整个自有管理组合；不能替代固定同物业群出租率')
    observation(s,2,'owned_managed_end_occupancy','自有及管理组合期末出租率','95.8','percent','ratio','percent_divided_by_100','owned_and_managed_operating_portfolio_period_end',[0,1],start=None,period='instant',role='scope_mismatch_sample',limitation='期末值不同于季度平均；不能替代同物业群出租率')

    s=source('capital_goods','2026-01-28','Full Year 2025 Highlights and segment descriptions; rounded billion USD',[
      'Full Year\n2025\n Highlights:\nOrders of \n$59.3\nB',
      'Revenue of \n$38.1\nB',
      'Defined as remaining performance obligation (RPO)',
      'We increased our backlog\n to $150 billion',
      'Power\nOrders\n of \n$32.8\n billion',
      'revenues\n of \n$19.8\n billion',
      'Wind\nOrders of \n$7.7\n billion',
      'Revenues of \n$9.1\n billion',
      'Electrification\nOrders of \n$19.3\n billion',
      'Revenues of \n$9.6\nbillion'])
    for component,name,raw,scope,idx in [
      ('company_new_orders','集团全年新增订单','59.3','consolidated',0),
      ('company_order_period_revenue','集团同期间收入','38.1','consolidated',1),
      ('power_new_orders','电力分部全年新增订单','32.8','power_segment',4),
      ('power_order_period_revenue','电力分部同期间收入','19.8','power_segment',5),
      ('wind_new_orders','风电分部全年新增订单','7.7','wind_segment',6),
      ('wind_order_period_revenue','风电分部同期间收入','9.1','wind_segment',7),
      ('electrification_new_orders','电气化分部全年新增订单','19.3','electrification_segment',8),
      ('electrification_order_period_revenue','电气化分部同期间收入','9.6','electrification_segment',9)]:
        observation(s,1,component,name,raw,'USD_billion','USD','billion_times_1000000000',scope,[idx],role='formula_input',limitation='十亿美元取整披露；订单取消处理与多年服务合同定义仍须年报核对；禁止跨分部拼接')
    observation(s,2,'company_backlog_rpo','集团剩余履约义务口径积压订单','150','USD_billion','USD','billion_times_1000000000','consolidated_rpo',[2,3],start=None,period='instant',role='formula_input',limitation='RPO 金额不是全部保证收入；缺取消条款及执行条件')

    s=source('construction','2026-02-17','Backlog and annual revenue tables, USD millions, 2025 columns',[
      '(in millions)\nDecember 31,\n2025\nDecember 31,\n2024',
      'Total backlog\n$\n25,536\n$\n28,484',
      'SUMMARY OF FINANCIALS AND U.S. GAAP RECONCILIATION OF CONSOLIDATED SEGMENT PROFIT (LOSS)\nThree Months Ended\nDecember 31,\nYear Ended\nDecember 31,\n(in millions)\n2025\n2024\n2025\n2024',
      'Total revenue\n$\n4,175\n$\n4,260\n$\n15,503\n$\n16,315',
      'Backlog:  $25.5 billion at 81% reimbursable; includes positive backlog adjustments of $941 million'])
    observation(s,1,'reported_total_construction_backlog','报告集团积压订单总额','25,536','USD_million','USD','million_times_1000000','consolidated_reported_total_backlog',[0,1,4],start=None,period='instant',role='scope_mismatch_sample',limitation='尚未取得可执行、已融资和可取消部分划分；不能直接计算可执行订单覆盖年数')
    observation(s,1,'construction_annual_revenue','工程集团全年收入','15,503','USD_million','USD','million_times_1000000','consolidated',[2,3],role='formula_input',limitation='收入包含 Santos 项目收入冲回；可比范围仍须审核')

    s=source('tobacco','2026-02-06','Full-year 2025 PMI / Smoke-Free Business / Combustibles table',[
      'PMI\nSmoke-Free\nBusiness\nCombustibles\nNet Revenues ($ bn)\n$40.6\n$16.9\n$23.8',
      'Gross Profit ($ bn)\n$27.3\n$11.7\n$15.6',
      'Our smoke-free business accounted for 41.5% of our total net revenues'])
    observation(s,3,'smoke_free_net_revenue','无烟业务全年净收入','16.9','USD_billion','USD','billion_times_1000000000','smoke_free_business',[0],role='formula_input',limitation='十亿美元取整披露；保留集团收入与业务收入不同范围')
    observation(s,3,'smoke_free_gross_profit','无烟业务全年毛利润','11.7','USD_billion','USD','billion_times_1000000000','smoke_free_business',[0,1],role='profit_basis_variant',limitation='毛利润不是营业利润或净利润；不可直接绑定 operating_profit 原子字段')
    observation(s,3,'smoke_free_revenue_share','无烟业务全年净收入占比','41.5','percent','ratio','percent_divided_by_100','smoke_free_share_of_company_net_revenue',[2],role='context_sample',limitation='发行人报告占比；取整收入之比不应强制等于此占比')

    s=source('retail','2026-02-19','Walmart U.S. comp sales and footnote 2; 13-week period ended January 30, 2026',[
      'Walmart U.S. comp sales2 grew 4.6%.',
      'Comp sales for the 13-week period ended January 30, 2026 compared to the 13-week period ended January 31, 2025 and excludes fuel. See Supplemental Financial Information for additional information.'])
    observation(s,1,'walmart_us_comparable_sales_growth','沃尔玛美国十三周同店销售增长','4.6','percent','ratio','percent_divided_by_100','walmart_us_excluding_fuel',[0,1],start='2025-11-01',end='2026-01-30',period='13_weeks',limitation='十三周经营期与财务季度结束日不同；线上范围及店群纳入细则仍需补充表核对')
    bundle={'schema_version':'1.0.0','archive_kind':'manual_archive_of_ai_browser_rendered_page_excerpts',
            'not_full_original_document':True,'observed_at':'2026-10-11T04:47:45+00:00','sources':sources}
    # 固定批次只可首次创建或字节相同重跑；历史原文草稿也不能静默覆盖。
    content=json.dumps(bundle,ensure_ascii=False,indent=2)+'\n'
    if TARGET.exists() and TARGET.read_text(encoding='utf8')!=content:
        raise ValueError('固定摘录批次已存在且内容不同，请创建新批次')
    TARGET.write_text(content,encoding='utf8')
    binding_path=ROOT/'knowledge/metrics/industry-reviewed-bindings-20261011.json'
    binding_content=json.dumps({'schema_version':'1.0.0','bindings':bindings},ensure_ascii=False,indent=2)+'\n'
    if binding_path.exists() and binding_path.read_text(encoding='utf8')!=binding_content:
        raise ValueError('审核绑定批次已存在且内容不同')
    binding_path.write_text(binding_content,encoding='utf8')
    print(json.dumps({'sources':len(sources),'observations':sum(len(s['observations']) for s in sources)},ensure_ascii=False))

if __name__=='__main__':
    main()
