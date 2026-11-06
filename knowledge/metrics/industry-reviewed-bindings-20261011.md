# 追加原子字段数据字典

每个字段保存原始值、原始单位、规范化值、期间、范围、摘录索引、来源版本及可得时间。计算输入不代表已计算；差异和背景项不计为可用输入。
[机器可读绑定](industry-reviewed-bindings-20261011.json) · [覆盖报告](industry-sample-coverage.md)

## transport_logistics_driver_1

| 字段标识 | 中文名称 | 原始单位 | 规范化单位 | 用途 | 业务限制 |
|---|---|---|---|---|---|
| annual_revenue_passenger_miles | 年度收入客英里 | million_passenger_miles | passenger_miles | 计算输入，未计算 | 仍须审核完整公司定义和研究期间适用性 |
| annual_available_seat_miles | 年度可用座英里 | million_seat_miles | seat_miles | 计算输入，未计算 | 仍须审核完整公司定义和研究期间适用性 |
| annual_passenger_load_factor | 年度客座率 | percent | ratio | 报告指标 | 发行人整数百分比；未取整工作量之比不应强制等于取整客座率 |

## transport_logistics_driver_2

| 字段标识 | 中文名称 | 原始单位 | 规范化单位 | 用途 | 业务限制 |
|---|---|---|---|---|---|
| annual_passenger_mile_yield | 年度每收入客英里客运收益 | US_cents_per_passenger_mile | USD_per_passenger_mile | 报告指标 | yield 不是 PRASM 或 TRASM；英里不可直接当公里 |

## health_services_driver_1

| 字段标识 | 中文名称 | 原始单位 | 规范化单位 | 用途 | 业务限制 |
|---|---|---|---|---|---|
| same_facility_admissions | 同院年度住院次数 | admissions | admissions | 报告指标 | 同院医院群；不能与 reported 全部医院或等价住院次数混合 |
| same_facility_equivalent_admissions | 同院年度等价住院次数 | equivalent_admissions | equivalent_admissions | 报告指标 | 保留公司门诊折算及同院纳入定义待核；不是实际住院人数 |

## health_services_driver_2

| 字段标识 | 中文名称 | 原始单位 | 规范化单位 | 用途 | 业务限制 |
|---|---|---|---|---|---|
| same_facility_revenue_per_equivalent_admission | 同院每等价住院收入 | USD_per_equivalent_admission | USD_per_equivalent_admission | 报告指标 | 不可与集团全部医院收入和服务量拼接；不是医院收费标价 |

## health_services_driver_3

| 字段标识 | 中文名称 | 原始单位 | 规范化单位 | 用途 | 业务限制 |
|---|---|---|---|---|---|
| consolidated_salaries_benefits | 集团年度工资及福利费用 | USD_million | USD | 计算输入，未计算 | 集团范围；未确认合同工是否全部包含，不能视作完整人工成本 |
| consolidated_healthcare_revenue | 集团年度收入 | USD_million | USD | 计算输入，未计算 | 匹配集团工资福利表，不能与同院服务量计算单位收入 |
| reported_salaries_benefits_revenue_ratio | 报告工资福利收入比 | percent | ratio | 报告指标 | 发行人取整百分比；不声称覆盖所有外包人员费用 |

## staples_retail_driver_1

| 字段标识 | 中文名称 | 原始单位 | 规范化单位 | 用途 | 业务限制 |
|---|---|---|---|---|---|
| annual_company_comparable_sales_growth | 全年集团同店销售增长（未调整） | percent | ratio | 报告指标 | 52 周期间；含燃油价格及汇率影响；纳入店群规则仍需年度报告核对 |
| annual_adjusted_comparable_sales_growth | 全年集团同店销售增长（剔除燃油汇率） | percent | ratio | 报告指标 | 调整增长率与未调整增长率不可混用；不是客流增长 |

## equity_reit_driver_1

| 字段标识 | 中文名称 | 原始单位 | 规范化单位 | 用途 | 业务限制 |
|---|---|---|---|---|---|
| cash_same_store_noi_growth | 权益份额现金同物业 NOI 增长 | percent | ratio | 报告指标 | 现金口径非 GAAP；物业群冻结与调节定义仍须补充表核验 |

## equity_reit_driver_2

| 字段标识 | 中文名称 | 原始单位 | 规范化单位 | 用途 | 业务限制 |
|---|---|---|---|---|---|
| owned_managed_average_occupancy | 自有及管理组合平均出租率 | percent | ratio | 范围差异，仅作记录 | 整个自有管理组合；不能替代固定同物业群出租率 |
| owned_managed_end_occupancy | 自有及管理组合期末出租率 | percent | ratio | 范围差异，仅作记录 | 期末值不同于季度平均；不能替代同物业群出租率 |

## capital_goods_driver_1

| 字段标识 | 中文名称 | 原始单位 | 规范化单位 | 用途 | 业务限制 |
|---|---|---|---|---|---|
| company_new_orders | 集团全年新增订单 | USD_billion | USD | 计算输入，未计算 | 十亿美元取整披露；订单取消处理与多年服务合同定义仍须年报核对；禁止跨分部拼接 |
| company_order_period_revenue | 集团同期间收入 | USD_billion | USD | 计算输入，未计算 | 十亿美元取整披露；订单取消处理与多年服务合同定义仍须年报核对；禁止跨分部拼接 |
| power_new_orders | 电力分部全年新增订单 | USD_billion | USD | 计算输入，未计算 | 十亿美元取整披露；订单取消处理与多年服务合同定义仍须年报核对；禁止跨分部拼接 |
| power_order_period_revenue | 电力分部同期间收入 | USD_billion | USD | 计算输入，未计算 | 十亿美元取整披露；订单取消处理与多年服务合同定义仍须年报核对；禁止跨分部拼接 |
| wind_new_orders | 风电分部全年新增订单 | USD_billion | USD | 计算输入，未计算 | 十亿美元取整披露；订单取消处理与多年服务合同定义仍须年报核对；禁止跨分部拼接 |
| wind_order_period_revenue | 风电分部同期间收入 | USD_billion | USD | 计算输入，未计算 | 十亿美元取整披露；订单取消处理与多年服务合同定义仍须年报核对；禁止跨分部拼接 |
| electrification_new_orders | 电气化分部全年新增订单 | USD_billion | USD | 计算输入，未计算 | 十亿美元取整披露；订单取消处理与多年服务合同定义仍须年报核对；禁止跨分部拼接 |
| electrification_order_period_revenue | 电气化分部同期间收入 | USD_billion | USD | 计算输入，未计算 | 十亿美元取整披露；订单取消处理与多年服务合同定义仍须年报核对；禁止跨分部拼接 |

## capital_goods_driver_2

| 字段标识 | 中文名称 | 原始单位 | 规范化单位 | 用途 | 业务限制 |
|---|---|---|---|---|---|
| company_backlog_rpo | 集团剩余履约义务口径积压订单 | USD_billion | USD | 计算输入，未计算 | RPO 金额不是全部保证收入；缺取消条款及执行条件 |

## construction_driver_1

| 字段标识 | 中文名称 | 原始单位 | 规范化单位 | 用途 | 业务限制 |
|---|---|---|---|---|---|
| reported_total_construction_backlog | 报告集团积压订单总额 | USD_million | USD | 范围差异，仅作记录 | 尚未取得可执行、已融资和可取消部分划分；不能直接计算可执行订单覆盖年数 |
| construction_annual_revenue | 工程集团全年收入 | USD_million | USD | 计算输入，未计算 | 收入包含 Santos 项目收入冲回；可比范围仍须审核 |

## tobacco_driver_3

| 字段标识 | 中文名称 | 原始单位 | 规范化单位 | 用途 | 业务限制 |
|---|---|---|---|---|---|
| smoke_free_net_revenue | 无烟业务全年净收入 | USD_billion | USD | 计算输入，未计算 | 十亿美元取整披露；保留集团收入与业务收入不同范围 |
| smoke_free_gross_profit | 无烟业务全年毛利润 | USD_billion | USD | 利润层次不同，不能替代 | 毛利润不是营业利润或净利润；不可直接绑定 operating_profit 原子字段 |
| smoke_free_revenue_share | 无烟业务全年净收入占比 | percent | ratio | 背景信息 | 发行人报告占比；取整收入之比不应强制等于此占比 |

## retail_driver_1

| 字段标识 | 中文名称 | 原始单位 | 规范化单位 | 用途 | 业务限制 |
|---|---|---|---|---|---|
| walmart_us_comparable_sales_growth | 沃尔玛美国十三周同店销售增长 | percent | ratio | 报告指标 | 十三周经营期与财务季度结束日不同；线上范围及店群纳入细则仍需补充表核对 |

