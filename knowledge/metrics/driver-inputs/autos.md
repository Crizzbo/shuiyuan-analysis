# autos 行业驱动输入表

代表公司：Toyota Motor（JP:7203）。

[统一目录](README.md) · [原始行业字典](../industry-specific/autos.md)

## autos_driver_1 — 终端零售车辆数量

交付终端客户的车辆数

选用口径：丰田汽车 FY2025 全集团全球汽车零售交付总量（含大发与日野）。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| autos_driver_1__input_1 | 零售终端交付数 | 已绑定 | tm_retail_vehicle_deliveries_fy25 / physical_quantity | industry-browser-excerpt:ba16759dae0cf9ca312f4381159c003fa32c7d5e0f7cb907c40a00b783b831f4 r1 |
| autos_driver_1__input_2 | 品牌地区 | 已绑定 | tm_retail_vehicle_deliveries_fy25 / physical_quantity（范围元数据） | industry-browser-excerpt:ba16759dae0cf9ca312f4381159c003fa32c7d5e0f7cb907c40a00b783b831f4 r1 |

限制：包含丰田雷克萨斯大发日野全品牌全球零售交付数；非合并批发口径；含442.5万台混动及电动化车辆。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 丰田全集团全球汽车零售交付总量 | 10,307,000 vehicles | 10307000 physical_quantity | 2024-04-01 至 2025-03-31 / group_retail_all_brands_global | reported_metric；包含丰田雷克萨斯大发日野全品牌全球零售交付数；非合并批发口径 |
| 丰田混动及电动化车辆零售交付量 | 4,425,000 vehicles | 4425000 physical_quantity | 2024-04-01 至 2025-03-31 / group_electrified_retail_sales | reported_metric；全集团电动化车辆零售交付，其中HEV占绝大多数；占零售总量46.1% |
| 合并报表批发汽车销售量 | 9,362,000 vehicles | 9362000 physical_quantity | 2024-04-01 至 2025-03-31 / consolidated_wholesale_deliveries | reported_metric；丰田汽车合并财务报表批发销量，不含未合并联营经销商零售数 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## autos_driver_2 — 经销商库存天数

渠道存量/匹配日销售量

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| autos_driver_2__input_1 | 经销商库存车辆 | 缺失 | 待补 | 无匹配证据 |
| autos_driver_2__input_2 | 匹配日均零售数 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## autos_driver_3 — 单车变动成本贡献

净收入减明确范围变动成本后除销量

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| autos_driver_3__input_1 | 车辆净收入 | 缺失 | 待补 | 无匹配证据 |
| autos_driver_3__input_2 | 明确变动成本 | 缺失 | 待补 | 无匹配证据 |
| autos_driver_3__input_3 | 匹配零售数量 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

