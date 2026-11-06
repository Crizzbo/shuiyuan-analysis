"""输出本次人工核对的输入选用方案；不按名称相似度自动匹配字段。"""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from financial_reporting.industry_inputs import validate_binding_plans

def main():
    index=json.loads((ROOT/'data/financial/industry-specific-verification.json').read_text(encoding='utf8'))
    rows={o['component']:o for o in json.loads((ROOT/index['snapshot_path']).read_text(encoding='utf8'))['observations']}
    specs={s['parent_metric_id']:s for s in json.loads((ROOT/'knowledge/metrics/industry-specifications.json').read_text(encoding='utf8'))['specifications']}
    plans=[]
    def plan(parent,mappings,review,variant,notes,same=False):
        p={'parent_metric_id':parent,'selected_variant_zh':variant,'definition_reviewed':review,'requires_same_scope':same,'slots':{},'limitations_zh':notes}
        chosen=next(rows[key] for items in mappings.values() for key,kind in items)
        p.update(period_start=chosen['period_start'],period_end=chosen['period_end'])
        for name,items in mappings.items():
            if name not in specs[parent]['required_inputs_zh']: raise ValueError('输入名称漂移')
            p['slots'][name]=[{'component':key,'kind':kind,'scope':rows[key]['scope'],'unit':rows[key]['unit']} for key,kind in items]
        plans.append(p)
    num=lambda key:[(key,'numeric')]
    meta=lambda key:[(key,'scope_metadata')]
    plan('managed_care_driver_1',{'匹配医疗成本':num('unh_reported_medical_cost'),'医疗保费或公司 MCR':num('unh_reported_premium_revenue')},True,'UnitedHealth 2025 集团报告口径医疗成本率',['不混用调整后 88.9% 的分子分母；仅限该年度报告口径'],True)
    plan('banks_driver_1',{'年化净利息收入':num('jpm_managed_net_interest_income'),'平均生息资产或公司 NIM':num('jpm_average_interest_earning_assets')},True,'JPM 2025 全年完全税当量管理口径净息收益率',['全年无需再按季度年化；不是 GAAP 净利息收入或剔除 Markets 口径'],True)
    plan('capital_goods_driver_1',{'新增订单金额':num('company_new_orders'),'同期间确认收入':num('company_order_period_revenue')},True,'GE Vernova 2025 年集团报告订单收入比',['采用发行人报告订单定义；分部订单与收入必须分别成对，不能跨分部混配'],True)
    plan('it_services_driver_2',{'新签合同 bookings':num('acn_consulting_new_bookings'),'服务类别':meta('acn_consulting_new_bookings')},True,'Accenture FY2026 咨询服务新签合同报告金额',['咨询合同不是托管合同或确认收入；不能据此判断全部可执行'],True)
    plan('hardware_driver_1',{'产品 sell-in 出货量':num('sony_ps5_fy2025_sellin'),'地区':meta('sony_ps5_fy2025_sellin'),'期间':[('sony_ps5_fy2025_sellin','period_metadata')]},True,'Sony FY2025 全球 PS5 sell-in 数量',['含退回及翻新产品；不是终端零售或 Sony 全硬件出货'],True)
    plan('housing_durables_driver_2',{'完成 closing 的住宅数':num('homes_closed')},True,'D.R. Horton FY2025 住宅成交交割数',['closed 不是新签订单或开工量'],True)
    plan('software_driver_3',{'SBC 费用':num('ddog_annual_sbc_expense_2024'),'期初期末实际发行股数':num('ddog_actual_shares_outstanding_ye24'),'加权稀释股数':num('ddog_weighted_diluted_eps_shares_2024')},True,'Datadog 2024 年费用化股权激励、年末实际发行股数及 EPS 加权稀释股数',['覆盖资产负债表期末实际发行 Class A+B 股数与 EPS 加权股数；净费用包含 SBC 支出；同 2024 财年报告期间对齐'],False)
    plan('banks_driver_2',{'扣回收后的净核销额':num('jpm_firm_net_chargeoffs'),'平均同范围贷款':num('jpm_firm_average_retained_loans_2025')},True,'JPM 2025 全年全集团留存贷款净核销额及平均留存贷款',['净核销额 9,849M 与平均留存贷款 1,330,946M 成对；同 2025 财年报告期间与口径一致'],True)
    plan('media_entertainment_driver_2',{'内容现金支付':num('nflx_content_asset_additions_cf')+num('nflx_content_liability_change_cf'),'许可自制与预付口径':meta('nflx_content_asset_additions_cf')},True,'Netflix 2025 内容资产现金增加与内容负债净变动调节口径',['包含内容资产现金投入及负债变动；覆盖自制与许可内容；同 2025 财年报告现金流口径一致'],True)
    plan('media_entertainment_driver_3',{'内容资产摊销或内容成本附注':num('nflx_content_amortization_driver3')},True,'Netflix 2025 年度内容资产摊销',['仅限内容资产摊销；不等同现金支付或完整内容成本'],True)
    plan('travel_leisure_driver_1',{'售出间夜':num('mar_comparable_rooms_sold_2025'),'可售间夜或公司披露入住率':num('mar_company_operated_occupancy')},True,'Marriott 2025 全年美加可比自营酒店售出间夜数与报告入住率',['售出间夜 18,740,000 间夜与报告入住率 69.0% 同范围成对；同 2025 财年报告期间一致'],True)
    plan('travel_leisure_driver_2',{'匹配客房收入':num('mar_comparable_rooms_revenue_2025'),'售出间夜或公司 ADR':num('mar_company_operated_adr')},True,'Marriott 2025 全年美加可比自营酒店客房收入与报告 ADR',['客房收入 $5,047M 与报告 ADR $269.36 同范围成对；同 2025 财年报告期间一致'],True)
    plan('tobacco_driver_3',{'无烟产品净收入':num('smoke_free_net_revenue'),'同范围经营利润':num('pm_smoke_free_operating_income_2025')},True,'菲莫国际 2025 全年无烟业务净收入与分部经营利润',['无烟业务净收入 $16.9B 与分部经营利润 $6.8B 完整成对；同 2025 财年分部口径一致'],True)
    plan('health_services_driver_3',{'工资福利或匹配人工成本':num('consolidated_salaries_benefits'),'净服务收入':num('consolidated_healthcare_revenue')},False,'HCA 2025 集团工资福利收入比',['净服务收入定义等价性和合同工人工覆盖待核；数值输入齐备不放行完整人工成本结论'],True)
    plan('health_services_driver_1',{'住院或等价住院次数':num('same_facility_equivalent_admissions'),'院群定义':meta('same_facility_equivalent_admissions')},True,'HCA 2025 同院综合急性期医院等价住院量及院群定义',['仅限同院综合急性期医院；门诊按收入比折算等价住院量；同报告期间对齐'],True)
    plan('midstream_driver_1',{'产品吞吐量':num('gas_processing_inlet_daily_volume'),'披露单位':meta('gas_processing_inlet_daily_volume'),'日均或期间总量':[('gas_processing_inlet_daily_volume','period_metadata')]},False,'EPD 2025 第四季度天然气加工厂入口日均量',['入口处理量不自动代表所有中游运输吞吐量'])
    plan('staples_retail_driver_1',{'同店销售披露':num('annual_company_comparable_sales_growth'),'店群规则':meta('annual_company_comparable_sales_growth')},True,'Costco FY2025 全年集团报告同店销售增长率（含燃油及汇率）',['包含燃油价格与汇率波动影响；剔除口径为 7.6%'],True)
    plan('retail_driver_1',{'公司同店销售披露':num('walmart_us_comparable_sales_growth'),'门店纳入规则':meta('walmart_us_comparable_sales_growth')},True,'Walmart FY2026 Q4 沃尔玛美国可比门店销售增长率（剔除燃油）',['仅限沃尔玛美国分部且剔除燃油；山姆会员店及国际业务为独立口径'],True)
    plan('restaurants_driver_1',{'同店销售增长披露':num('global_comparable_sales_growth'),'店群规则':meta('global_comparable_sales_growth')},True,'McDonalds 2025 Q4 全球可比餐厅销售增长率',['包含自营与加盟可比餐厅；仅限开业满13个月以上店群'],True)
    plan('food_beverage_driver_2',{'公司价格组合桥接贡献':num('price_mix_contribution'),'公司桥接定义':meta('price_mix_contribution')},True,'Coca-Cola 2025 全年有机营收增长桥接价格与组合贡献率',['属于有机收入桥接分解项；不是绝对单价变动金额'],True)
    plan('insurance_driver_2',{'前期事故年度有利或不利发展':num('favorable_prior_period_reserve_development'),'再保险范围':meta('favorable_prior_period_reserve_development')},True,'Chubb 2025 Q4 税前有利前期事故准备金发展额',['正值表示有利发展（释放）；仅限当季净额，未涵盖全部事故年度精算分布'],True)
    plan('aerospace_defense_driver_3',{'验收交付量':num('lmt_f35_delivered'),'产品标识':meta('lmt_f35_delivered')},True,'Lockheed Martin 2025 全年 F-35 战机报告交付数量',['仅限报告交付给军方客户的 F-35；F-16/C-130J 为不同型号独立口径'],True)
    plan('transport_logistics_driver_1',{'收入客公里或吨公里':num('annual_revenue_passenger_miles'),'可用座公里或吨公里':num('annual_available_seat_miles')},True,'Delta Air Lines 2025 全年客运载运率（RPM/ASM）',['系统英里口径（RPM/ASM）；客座率报告值为 84%'],False)
    plan('oil_gas_driver_2',{'现金开采成本':num('eog_lease_well_cost')+num('eog_gather_processing_cost'),'匹配产量':num('eog_sales_equivalent_volume')},False,'EOG Resources 2025 全年租赁/井运营及集输运输现金成本',['不包含管理费及生产税；开采范围与实物权益产量匹配性待进一步审核'],False)
    plan('biotech_driver_2',{'可用现金和投资':num('mrna_cash_investments_reported'),'正常化月净消耗':num('mrna_monthly_cash_burn_2025'),'调整项':num('mrna_cash_runway_adjustments_2025')},True,'Moderna 2025 年末期末现金与正常化月净消耗额',['期末现金投资 $8.1B、正常化月均消耗 $200M 与限制调整项 $0M 对齐；同 2025 财年报告口径一致'],False)
    plan('insurance_driver_1',{'同范围赔付率':num('cb_pc_loss_ratio_q4'),'费用率或报告 combined ratio':num('cb_pc_acquisition_ratio_q4')+num('cb_pc_admin_ratio_q4')},True,'Chubb 2025 Q4 集团财险报告赔付及两项费用率之和',['54.3%+18.9%+8.0%=81.2%，与原表综合成本率交叉核对；剔除寿险、包含大灾及前期准备金发展、作物衍生品调整'],True)
    plan('equity_reit_driver_1',{'same-store 本期 NOI':num('pld_q4_same_store_cash_noi'),'同群同期 NOI或披露增长':num('cash_same_store_noi_growth')},True,'Prologis 4Q25 权益份额现金同店净营业收入与报告增长率',['本期现金同店 NOI $1,281M 与增长率 5.7% 同群同期间对齐；同 4Q25 报告口径一致'],True)
    plan('capital_goods_driver_2',{'期末 backlog':num('company_backlog_rpo'),'取消条款':meta('company_backlog_rpo'),'可执行条件':meta('company_backlog_rpo')},True,'GE Vernova 2025 年末集团剩余履约义务（RPO）口径积压订单与取消条款',['采用 ASC 606 RPO 披露口径；包含不可撤销履约承诺及违约终止条款附注说明'],True)
    plan('food_beverage_driver_1',{'本期可比销量':num('coca_cola_unit_case_volume_2025'),'同期可比销量或披露增长':num('system_unit_case_volume_growth')},True,'Coca-Cola 2025 全年全球系统标准箱物理销量与披露增长（持平）',['本期物理销量 333 亿箱与定性零增长（Even）同口径成对；同 2025 财年报告期间一致'],True)
    period=lambda key:[(key,'period_metadata')]
    plan('medical_devices_driver_2',{'当期系统 placement':num('da_vinci_placements'),'期末 installed base':num('da_vinci_installed_base'),'退役调整':num('isrg_tradein_retirements_q4')},True,'Intuitive Surgical 2025 Q4 达芬奇系统新增投放、期末在用装机量与退役调整数',['投放 532 台、期末装机 11,106 台、退役置换 79 台；同 2025 Q4 期间与装机量变动平衡对齐'],False)
    plan('digital_platforms_driver_1',{'DAU 或 MAU':num('family_daily_active_people'),'频率':period('family_daily_active_people'),'活跃规则':meta('family_daily_active_people')},True,'Meta 2025 年第四季度应用家族每日活跃人数 (DAP)',['去重单人统计；不包含非家族独立服务；不直接代表单应用 DAU'],True)
    plan('midstream_driver_3',{'公司披露 sustaining capex':num('sustaining_capex'),'范围说明':meta('sustaining_capex')},True,'Enterprise Products Partners 2025 Q4 维持资本支出现金额',['仅限合伙企业现有资产维持性开支；增长性项目与资产收购不属于本项'],True)
    plan('banks_driver_3',{'CET1 比率':num('jpm_standardized_cet1'),'LCR 比率':num('jpm_q4_average_lcr'),'NSFR 比率':num('jpm_nsfr_ratio_2025'),'适用规则':meta('jpm_standardized_cet1')},True,'JPMorgan Chase 2025 年末标准化 CET1、LCR 及 NSFR 监管指标群',['标准化 CET1 14.6%、LCR 111%、NSFR 116% 全面成套；同 2025 年末/Q4 截面一致'],False)
    plan('housing_durables_driver_1',{'取消订单数':num('dhi_cancelled_sales_orders_fy25'),'公司定义的匹配订单群':meta('home_order_cancellation_rate')},True,'D.R. Horton FY2025 全年住宅取消订单套数与匹配订单群口径',['取消订单 18,312 套与报告 18% 取消率订单群同期间；同 FY2025 报告期间对齐'],False)
    plan('asset_management_driver_1',{'客户流入':num('blk_gross_inflows_2025'),'流出':num('blk_gross_outflows_2025'),'资本返还':num('blk_capital_returned_2025'),'公司流量定义':meta('net_client_flows')},True,'BlackRock 2025 全年客户毛流入、毛流出、资本返还与净流量口径',['毛流入 $3,215B、毛流出 $2,502B、资本返还 $15B 完整成套；净流入 $698B 对齐；同 2025 财年口径一致'],True)
    plan('construction_driver_1',{'可执行期末订单额':num('fluor_ending_backlog_2024'),'同范围年度收入':num('fluor_annual_revenue_2024')},True,'Fluor 2024 年度合并工程建筑期末订单与同范围年度收入',['合并期末订单 28,484M 与同范围年度收入 16,315M 完整成对；同 2024 财年报告期间与口径一致'],True)
    plan('telecom_driver_2',{'断开用户数':num('vz_q4_postpaid_phone_disconnects'),'平均用户':num('vz_q4_postpaid_phone_average_connections'),'月数或披露 churn':num('vz_total_postpaid_phone_churn_q4')},True,'Verizon 2025 Q4 全无线零售后付费手机断开数、平均活跃连接数与报告流失率',['断开数 769,284 连接与平均 75,420,000 连接同范围成对；对应报告 1.02% 季度 churn；同 2025 Q4 期间一致'],True)
    plan('autos_driver_1',{'零售终端交付数':num('tm_retail_vehicle_deliveries_fy25'),'品牌地区':meta('tm_retail_vehicle_deliveries_fy25')},True,'丰田汽车 FY2025 全集团全球汽车零售交付总量（含大发与日野）',['包含丰田雷克萨斯大发日野全品牌全球零售交付数；非合并批发口径','含442.5万台混动及电动化车辆'],True)
    plan('staples_retail_driver_3',{'本期可比交易数':num('cost_comparable_transactions_fy25'),'同期交易数或公司披露增长':num('cost_worldwide_traffic_growth_fy25')},True,'Costco FY2025 全球可比仓储店到店客流频次增长率与实际交易笔数',['可比交易笔数 15.81 亿笔与报告频次增速 5.4% 同范围成对；同 FY2025 财年期间一致'],True)
    plan('retail_driver_2',{'匹配期间销售成本':num('wmt_cost_of_sales_fy25'),'期初期末同范围存货':num('wmt_average_inventories_fy25')},True,'Walmart FY2025 全集团销售成本与期初期末平均存货',['存货周转率计算分子分母完整成对；不混用单季度未年化分母'],True)
    plan('semiconductors_driver_3',{'产品收入':num('mu_dram_annual_revenue_fy26'),'匹配 bit 或芯片数量':num('mu_dram_annual_bit_shipments_fy26')},True,'Micron FY2026 全年 DRAM 业务产品收入与物理 bit 出货总量',['DRAM 业务分部收入 $100.68B 与 bit 出货量 968 亿 gigabits 同财年成对；同 FY2026 报告期间一致'],True)
    plan('pharma_driver_1',{'产品净收入':num('pfe_eliquis_worldwide_revenue_fy24'),'药品与地区标识':meta('pfe_eliquis_worldwide_revenue_fy24')},True,'Pfizer FY2024 全年 Eliquis 全球报告净销售额（含联盟分成）',['仅限 Eliquis 单药全球销售额；未包含其他专利到期药或直销拆分'],True)
    plan('payments_driver_1',{'支付处理量':num('visa_payments_volume_fy24'),'交易类型':meta('visa_payments_volume_fy24'),'地区币种':meta('visa_payments_volume_fy24')},True,'Visa FY2024 全财年名义支付处理总额（常量美元口径）',['全球 Visa 品牌卡片名义支付处理总额；不包含现金提现交易与欧洲双标卡剔除口径'],True)
    plan('mining_driver_1',{'商品净销售额':num('fcx_copper_average_realized_price_2024'),'商品销售数量':num('fcx_consolidated_copper_sales_volume_2024')},True,'Freeport-McMoRan 2024 全年铜综合实现平均售价与实物销售数量',['实现售价 $4.21/lb 与实物销量 41 亿磅成对；同 2024 财年合并口径完全一致'],True)
    plan('chemicals_driver_1',{'产品单位售价':num('dow_pe_average_selling_price_2024'),'匹配原料单位成本':num('dow_ethylene_feedstock_cost_2024'),'投入系数':num('dow_pe_feedstock_ratio_2024')},True,'Dow 2024 全年包装与特种塑料聚乙烯基准售价、乙烯原料成本与单耗系数',['聚乙烯售价 $1,180/MT、乙烯原料成本 $680/MT、单耗系数 1.02 完整成对；同 2024 财年报告期间一致'],True)
    plan('packaging_driver_1',{'包装产品出货量':num('pkg_corrugated_products_shipments_2024'),'单位':meta('pkg_corrugated_products_shipments_2024')},True,'Packaging Corp 2024 全年瓦楞制品出货销售面积（67 BSF）',['瓦楞包装制品出货面积；非箱板纸原纸造纸产量'],True)
    plan('business_services_driver_2',{'基期客户中本期留存数量':num('adp_es_client_revenue_retention_fy24'),'基期客户数量':num('adp_es_client_count_fy24')},True,'ADP FY2024 雇主服务分部客户收入留存率与基期客户总数',['收入留存率 92% 与基期 1,000,000 客户规模同财年对齐；解决原始物理客户基数'],True)
    plan('semi_equipment_driver_1',{'新增设备订单':num('tel_annual_new_orders_fy24'),'同期间设备收入':num('tel_annual_net_sales_fy24')},True,'Tokyo Electron FY2024 全财年合并半导体设备新签订单与同期间销售额',['新签订单 1,848.2 billion JPY 与销售额 1,830.5 billion JPY 完整成对；同 FY2024 财年口径一致'],True)
    plan('regulated_utilities_driver_2',{'allowed ROE':num('duk_carolinas_allowed_roe_2024'),'权益资本结构':num('duk_carolinas_equity_capital_ratio_2024'),'决定生效日':period('duk_carolinas_allowed_roe_2024')},True,'Duke Energy 2024 年度卡罗莱纳零售电力监管裁定核准 ROE、权益资本比例及生效期',['核准 ROE 9.8%、核准权益资本比例 52.0%、适用裁定生效期间对齐；同监管委员会裁定一致'],True)
    plan('merchant_power_driver_1',{'匹配售电净收入':num('ceg_annual_operating_revenues_2024'),'对应 MWh':num('ceg_annual_generation_mwh_2024')},True,'Constellation Energy 2024 全年商业售电合并营业收入与发电总量（MWh）',['合并售电营业收入 $23.568B 与发电产出 121 TWh (121,000,000 MWh) 成对；同 2024 财年报告期间一致'],True)
    plan('real_estate_services_driver_1',{'开发项目实际现金收款':num('hhh_mpc_land_sales_fy24'),'项目范围':meta('hhh_mpc_land_sales_fy24')},False,'Howard Hughes 2024 全年主要规划社区住宅土地销售额（4.53亿美元）',['取得 MPC 分部住宅土地销售金额；实际项目现金回款与分期定金待补'])
    document=validate_binding_plans({'schema_version':'1.0.0','plans':plans}, list(specs.values()))
    (ROOT/'knowledge/metrics/industry-input-binding-plans.json').write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    schema_path=ROOT/'schemas/industry-driver-inputs.schema.json'
    schema=json.loads(schema_path.read_text(encoding='utf8'));schema['title']='行业驱动输入台账'
    schema_path.write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f'已生成 {len(plans)} 个明确选用方案；其他驱动按原始规格列出全部缺口')

if __name__=='__main__': main()
