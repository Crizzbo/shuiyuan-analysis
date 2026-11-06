# oil_gas 行业驱动输入表

代表公司：EOG Resources（US:EOG）。

[统一目录](README.md) · [原始行业字典](../industry-specific/oil_gas.md)

## oil_gas_driver_1 — 分产品实现售价

销售收入/可比销售量

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| oil_gas_driver_1__input_1 | 产品销售收入 | 缺失 | 待补 | 无匹配证据 |
| oil_gas_driver_1__input_2 | 产品销售量 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 原油凝析油综合实现售价 | 65.63 USD_per_Bbl | 65.63 USD_per_Bbl | 2025-01-01 至 2025-12-31 / composite_crude_condensate | reported_metric；按产品单独保存；套保排除规则待完整脚注核对，不代替收入和销售量输入 |
| 天然气综合实现售价 | 3.02 USD_per_Mcf | 3.02 USD_per_Mcf | 2025-01-01 至 2025-12-31 / composite_natural_gas | reported_metric；Mcf 不是 MMBtu；套保口径待完整脚注核对 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## oil_gas_driver_2 — 单位开采现金成本

可比开采现金成本/产量

选用口径：EOG Resources 2025 全年租赁/井运营及集输运输现金成本。输入状态：必需输入已齐备。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| oil_gas_driver_2__input_1 | 现金开采成本 | 已绑定 | eog_lease_well_cost / USD；eog_gather_processing_cost / USD | industry-browser-excerpt:31c7a62023a11e7226fdfc5d16d2ce67fd12a01dfd7af1151a366479fdb6eadb r1；industry-browser-excerpt:31c7a62023a11e7226fdfc5d16d2ce67fd12a01dfd7af1151a366479fdb6eadb r1 |
| oil_gas_driver_2__input_2 | 匹配产量 | 已绑定 | eog_sales_equivalent_volume / Boe | industry-browser-excerpt:31c7a62023a11e7226fdfc5d16d2ce67fd12a01dfd7af1151a366479fdb6eadb r1 |

限制：不包含管理费及生产税；开采范围与实物权益产量匹配性待进一步审核。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 租赁及井运营成本 | 1,675 USD_million | 1675000000 USD | 2025-01-01 至 2025-12-31 / consolidated_reported_sales_cost_schedule | formula_input；分别保存成本项目；现金性、生产税归属及开采范围待核，不自动求和为开采现金成本 |
| 集输加工运输成本 | 2,134 USD_million | 2134000000 USD | 2025-01-01 至 2025-12-31 / consolidated_reported_sales_cost_schedule | formula_input；分别保存成本项目；现金性、生产税归属及开采范围待核，不自动求和为开采现金成本 |
| GAAP 管理费用 | 820 USD_million | 820000000 USD | 2025-01-01 至 2025-12-31 / consolidated_reported_sales_cost_schedule | formula_input；分别保存成本项目；现金性、生产税归属及开采范围待核，不自动求和为开采现金成本 |
| 非所得税税费 | 1,234 USD_million | 1234000000 USD | 2025-01-01 至 2025-12-31 / consolidated_reported_sales_cost_schedule | formula_input；分别保存成本项目；现金性、生产税归属及开采范围待核，不自动求和为开采现金成本 |
| 成本表油当量销售量 | 449.8 million_units | 449800000.0 Boe | 2025-01-01 至 2025-12-31 / consolidated_reported_sales_cost_schedule | formula_input；销售量不能替代储量表含实物权益产量；是否匹配开采成本待核 |
| 报告单位现金运营成本 | 10.28 USD_per_Boe | 10.28 USD_per_Boe | 2025-01-01 至 2025-12-31 / LOE_plus_GPT_plus_GA_excluding_production_tax | scope_mismatch_sample；公司定义包括管理费但排除生产税，与项目单位开采现金成本并非自动等价 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## oil_gas_driver_3 — 已探明储量寿命

可比已探明储量/年产量

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| oil_gas_driver_3__input_1 | 已探明储量 | 缺失 | 待补 | 无匹配证据 |
| oil_gas_driver_3__input_2 | 同范围年产量 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

