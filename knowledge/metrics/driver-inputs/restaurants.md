# restaurants 行业驱动输入表

代表公司：McDonald’s（US:MCD）。

[统一目录](README.md) · [原始行业字典](../industry-specific/restaurants.md)

## restaurants_driver_1 — 可比餐厅销售增长

相同门店范围收入同比

选用口径：McDonalds 2025 Q4 全球可比餐厅销售增长率。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| restaurants_driver_1__input_1 | 同店销售增长披露 | 已绑定 | global_comparable_sales_growth / ratio | industry-browser-excerpt:bd89616a4a67f9b20fd0c43692afed2b25fbf2880556af0c750b3197afc698d8 r1 |
| restaurants_driver_1__input_2 | 店群规则 | 已绑定 | global_comparable_sales_growth / ratio（范围元数据） | industry-browser-excerpt:bd89616a4a67f9b20fd0c43692afed2b25fbf2880556af0c750b3197afc698d8 r1 |

限制：包含自营与加盟可比餐厅；仅限开业满13个月以上店群。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 全球第四季度同店销售增长 | 5.7 percent | 0.057 ratio | 2025-10-01 至 2025-12-31 / global_company_reported_comparable_restaurants | 早期审核样本；完整定义待核 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## restaurants_driver_2 — 单店经营利润

门店收入减门店成本且排除项明确

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| restaurants_driver_2__input_1 | 同范围门店经营利润 | 缺失 | 待补 | 无匹配证据 |
| restaurants_driver_2__input_2 | 加权平均店数 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## restaurants_driver_3 — 加盟商闭店与违约记录

闭店及违约记录

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| restaurants_driver_3__input_1 | 闭店事件 | 缺失 | 待补 | 无匹配证据 |
| restaurants_driver_3__input_2 | 违约事件 | 缺失 | 待补 | 无匹配证据 |
| restaurants_driver_3__input_3 | 加盟商范围 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

