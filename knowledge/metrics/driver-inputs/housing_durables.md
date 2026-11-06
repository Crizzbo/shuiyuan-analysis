# housing_durables 行业驱动输入表

代表公司：D.R. Horton（US:DHI）。

[统一目录](README.md) · [原始行业字典](../industry-specific/housing_durables.md)

## housing_durables_driver_1 — 住宅订单取消率

取消订单/明确订单群

选用口径：D.R. Horton FY2025 全年住宅取消订单套数与匹配订单群口径。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| housing_durables_driver_1__input_1 | 取消订单数 | 已绑定 | dhi_cancelled_sales_orders_fy25 / units | industry-browser-excerpt:85dd5011e410278bc2a0d4cb268abdeb2e4ab31e85699b9e48b0900ccd32f3fb r1 |
| housing_durables_driver_1__input_2 | 公司定义的匹配订单群 | 已绑定 | home_order_cancellation_rate / ratio（范围元数据） | industry-browser-excerpt:e7db522b136244971df8865f695c5ea2de5df3b4d0da4690a9bb71b5018902aa r1 |

限制：取消订单 18,312 套与报告 18% 取消率订单群同期间；同 FY2025 报告期间对齐。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 全年住宅毛销售订单取消率 | 18 percent | 0.18 ratio | 2024-10-01 至 2025-09-30 / homebuilding_cancelled_sales_orders_over_gross_sales_orders | 早期审核样本；完整定义待核 |
| 霍顿房屋 FY2025 全年取消住宅订单套数 | 18,312 units | 18312 units | 2024-10-01 至 2025-09-30 / homebuilding_cancelled_sales_orders_over_gross_sales_orders | formula_input；FY2025 全财年住宅取消订单物理套数（18,312 套）；与报告取消率 18% 订单群同期间 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## housing_durables_driver_2 — 已结算交付住宅数量

完成交付的单位数

选用口径：D.R. Horton FY2025 住宅成交交割数。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| housing_durables_driver_2__input_1 | 完成 closing 的住宅数 | 已绑定 | homes_closed / homes | industry-browser-excerpt:e7db522b136244971df8865f695c5ea2de5df3b4d0da4690a9bb71b5018902aa r1 |

限制：closed 不是新签订单或开工量。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 全年完成结算交付住宅数 | 84,863 homes | 84863 homes | 2024-10-01 至 2025-09-30 / homebuilding | 早期审核样本；完整定义待核 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## housing_durables_driver_3 — 持有与控制土地批次

持有及承诺土地分开

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| housing_durables_driver_3__input_1 | 持有地块数 | 缺失 | 待补 | 无匹配证据 |
| housing_durables_driver_3__input_2 | 期权或合同控制地块数 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

