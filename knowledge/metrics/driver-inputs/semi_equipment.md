# semi_equipment 行业驱动输入表

代表公司：Tokyo Electron（JP:8035）。

[统一目录](README.md) · [原始行业字典](../industry-specific/semi_equipment.md)

## semi_equipment_driver_1 — 半导体设备订单收入比

同期间新增订单额/收入

选用口径：Tokyo Electron FY2024 全财年合并半导体设备新签订单与同期间销售额。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| semi_equipment_driver_1__input_1 | 新增设备订单 | 已绑定 | tel_annual_new_orders_fy24 / JPY | industry-browser-excerpt:290159e93041ff4a41a2cc26e0000d3aa2a9a4af185924150a80ce69c551ed77 r1 |
| semi_equipment_driver_1__input_2 | 同期间设备收入 | 已绑定 | tel_annual_net_sales_fy24 / JPY | industry-browser-excerpt:00e9fe39c25de53cc7150ae5ac71e50df93f5031f8f4a3914d3fb6252d2264cd r1 |

限制：新签订单 1,848.2 billion JPY 与销售额 1,830.5 billion JPY 完整成对；同 FY2024 财年口径一致。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 东京电子 FY2024 半导体制造装置为主合并净销售额 | 1,830.5 JPY_billion | 1830500000000 JPY | 2023-04-01 至 2024-03-31 / consolidated_net_sales_fy24 | formula_input；全财年合并净销售额（以半导体制造设备为主，十亿日元口径）；匹配新增订单待核 |
| 东京电子 FY2024 全财年合并半导体制造设备新签订单额 | 1,848.2 JPY_billion | 1848200000000 JPY | 2023-04-01 至 2024-03-31 / consolidated_net_sales_fy24 | formula_input；FY2024 全财年合并新签订单总额（1,848.2 billion JPY）；与净销售额 1,830.5 billion JPY 同财年同口径 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## semi_equipment_driver_2 — 分客户制程资本开支

按制程和客户记录

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| semi_equipment_driver_2__input_1 | 客户实际 capex | 缺失 | 待补 | 无匹配证据 |
| semi_equipment_driver_2__input_2 | 工艺及客户标识 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## semi_equipment_driver_3 — 客户取消及延期订单

取消与延期分别记录

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| semi_equipment_driver_3__input_1 | 取消订单金额 | 缺失 | 待补 | 无匹配证据 |
| semi_equipment_driver_3__input_2 | 延期订单金额 | 缺失 | 待补 | 无匹配证据 |
| semi_equipment_driver_3__input_3 | 合同与日期 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

