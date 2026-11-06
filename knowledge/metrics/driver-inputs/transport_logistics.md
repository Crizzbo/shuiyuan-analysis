# transport_logistics 行业驱动输入表

代表公司：Delta Air Lines（US:DAL）。

[统一目录](README.md) · [原始行业字典](../industry-specific/transport_logistics.md)

## transport_logistics_driver_1 — 运输工作量载运率

已使用运力/可用运力

选用口径：Delta Air Lines 2025 全年客运载运率（RPM/ASM）。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| transport_logistics_driver_1__input_1 | 收入客公里或吨公里 | 已绑定 | annual_revenue_passenger_miles / passenger_miles | industry-browser-excerpt:937b67aca111dfe7b58175319096099db92b39a81e27cfd9a0f853eaf6f37d65 r1 |
| transport_logistics_driver_1__input_2 | 可用座公里或吨公里 | 已绑定 | annual_available_seat_miles / seat_miles | industry-browser-excerpt:937b67aca111dfe7b58175319096099db92b39a81e27cfd9a0f853eaf6f37d65 r1 |

限制：系统英里口径（RPM/ASM）；客座率报告值为 84%。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 年度收入客英里 | 249,578 million_passenger_miles | 249578000000 passenger_miles | 2025-01-01 至 2025-12-31 / consolidated_airline_passenger_traffic | formula_input；仍须审核完整公司定义和研究期间适用性 |
| 年度可用座英里 | 298,045 million_seat_miles | 298045000000 seat_miles | 2025-01-01 至 2025-12-31 / consolidated_airline_passenger_capacity | formula_input；仍须审核完整公司定义和研究期间适用性 |
| 年度客座率 | 84 percent | 0.84 ratio | 2025-01-01 至 2025-12-31 / consolidated_airline_passenger_traffic | reported_metric；发行人整数百分比；未取整工作量之比不应强制等于取整客座率 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## transport_logistics_driver_2 — 单位运输收入

可比运输收入/运输工作量

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| transport_logistics_driver_2__input_1 | 匹配客运或货运收入 | 缺失 | 待补 | 无匹配证据 |
| transport_logistics_driver_2__input_2 | 收入运输工作量 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 年度每收入客英里客运收益 | 20.74 US_cents_per_passenger_mile | 0.2074 USD_per_passenger_mile | 2025-01-01 至 2025-12-31 / consolidated_airline_passenger_revenue_yield | reported_metric；yield 不是 PRASM 或 TRASM；英里不可直接当公里 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## transport_logistics_driver_3 — 单位运输燃料成本

燃料支出/可比运输工作量

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| transport_logistics_driver_3__input_1 | 匹配燃料成本 | 缺失 | 待补 | 无匹配证据 |
| transport_logistics_driver_3__input_2 | 运输工作量 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

