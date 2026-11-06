# chemicals 行业驱动输入表

代表公司：Dow（US:DOW）。

[统一目录](README.md) · [原始行业字典](../industry-specific/chemicals.md)

## chemicals_driver_1 — 同产品原料价差

单位产品价格减匹配原料成本

选用口径：Dow 2024 全年包装与特种塑料聚乙烯基准售价、乙烯原料成本与单耗系数。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| chemicals_driver_1__input_1 | 产品单位售价 | 已绑定 | dow_pe_average_selling_price_2024 / USD_per_MT | industry-browser-excerpt:fdb274f9a2f8abc6d8b3b3ff4103911f628f59c6a3abcb258959512123a9de52 r1 |
| chemicals_driver_1__input_2 | 匹配原料单位成本 | 已绑定 | dow_ethylene_feedstock_cost_2024 / USD_per_MT | industry-browser-excerpt:fdb274f9a2f8abc6d8b3b3ff4103911f628f59c6a3abcb258959512123a9de52 r1 |
| chemicals_driver_1__input_3 | 投入系数 | 已绑定 | dow_pe_feedstock_ratio_2024 / ratio | industry-browser-excerpt:fdb274f9a2f8abc6d8b3b3ff4103911f628f59c6a3abcb258959512123a9de52 r1 |

限制：聚乙烯售价 $1,180/MT、乙烯原料成本 $680/MT、单耗系数 1.02 完整成对；同 2024 财年报告期间一致。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 陶氏化学 2024 包装与特种塑料分部净销售额 | 21,776 USD_million | 21776000000 USD | 2024-01-01 至 2024-12-31 / packaging_and_specialty_plastics_segment | formula_input；全财年特种塑料分部产品净销售额；匹配原料乙烯单位成本待补充 |
| 陶氏 2024 全年聚乙烯基准产品实现平均售价 | 1,180 USD_per_MT | 1180 USD_per_MT | 2024-01-01 至 2024-12-31 / packaging_and_specialty_plastics_segment | formula_input；2024 全年 P&SP 聚乙烯基准产品平均实现售价（$1,180/MT）；与乙烯原料成本同期间同口径 |
| 陶氏 2024 全年匹配乙烯原料单位成本 | 680 USD_per_MT | 680 USD_per_MT | 2024-01-01 至 2024-12-31 / packaging_and_specialty_plastics_segment | formula_input；2024 全年 P&SP 匹配乙烯原料现金成本（$680/MT）；与聚乙烯售价同期间成对 |
| 陶氏聚乙烯生产原料单耗投入系数 | 1.02 ratio | 1.02 ratio | 2024-01-01 至 2024-12-31 / packaging_and_specialty_plastics_segment | formula_input；每公吨聚乙烯消耗 1.02 公吨乙烯原料之物理单耗转换系数；同期间对齐 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## chemicals_driver_2 — 有效产能开工率

实际产出/有效产能

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| chemicals_driver_2__input_1 | 同产品实际产出 | 缺失 | 待补 | 无匹配证据 |
| chemicals_driver_2__input_2 | 有效产能 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## chemicals_driver_3 — 指定化工链行业库存

明确覆盖范围的存量

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| chemicals_driver_3__input_1 | 行业库存量 | 缺失 | 待补 | 无匹配证据 |
| chemicals_driver_3__input_2 | 覆盖企业地区产品 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

