# retail 行业驱动输入表

代表公司：Walmart（US:WMT）。

[统一目录](README.md) · [原始行业字典](../industry-specific/retail.md)

## retail_driver_1 — 可比门店销售增长

相同门店范围收入同比

选用口径：Walmart FY2026 Q4 沃尔玛美国可比门店销售增长率（剔除燃油）。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| retail_driver_1__input_1 | 公司同店销售披露 | 已绑定 | walmart_us_comparable_sales_growth / ratio | industry-browser-excerpt:943646bf02d471646c25dca21dc5715533a9e124a7a0d6e48e4cafb5db509051 r1 |
| retail_driver_1__input_2 | 门店纳入规则 | 已绑定 | walmart_us_comparable_sales_growth / ratio（范围元数据） | industry-browser-excerpt:943646bf02d471646c25dca21dc5715533a9e124a7a0d6e48e4cafb5db509051 r1 |

限制：仅限沃尔玛美国分部且剔除燃油；山姆会员店及国际业务为独立口径。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 沃尔玛美国十三周同店销售增长 | 4.6 percent | 0.046 ratio | 2025-11-01 至 2026-01-30 / walmart_us_excluding_fuel | reported_metric；十三周经营期与财务季度结束日不同；线上范围及店群纳入细则仍需补充表核对 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## retail_driver_2 — 期间存货周转次数

销售成本/平均库存

选用口径：Walmart FY2025 全集团销售成本与期初期末平均存货。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| retail_driver_2__input_1 | 匹配期间销售成本 | 已绑定 | wmt_cost_of_sales_fy25 / USD | industry-browser-excerpt:06cda9fc3a0390d8a967189c0ec34b7e32003761aa018dd3ddb0eff530a8c362 r1 |
| retail_driver_2__input_2 | 期初期末同范围存货 | 已绑定 | wmt_average_inventories_fy25 / USD | industry-browser-excerpt:06cda9fc3a0390d8a967189c0ec34b7e32003761aa018dd3ddb0eff530a8c362 r1 |

限制：存货周转率计算分子分母完整成对；不混用单季度未年化分母。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 沃尔玛合并营业销售成本 | 516,879 USD_million | 516879000000 USD | 2024-02-01 至 2025-01-31 / consolidated_cost_of_sales | formula_input；全财年合并销售成本；包含全部商品采购与供应链物流成本 |
| 沃尔玛期初期末同范围平均存货 | 55,801.5 USD_million | 55801500000 USD | 2024-02-01 至 2025-01-31 / consolidated_cost_of_sales | formula_input；FY2025期初54892百万美元与期末56711百万美元平均值 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## retail_driver_3 — 履约成本占相关收入比

可比履约成本/相关收入

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| retail_driver_3__input_1 | 履约配送仓储成本 | 缺失 | 待补 | 无匹配证据 |
| retail_driver_3__input_2 | 相关收入 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

