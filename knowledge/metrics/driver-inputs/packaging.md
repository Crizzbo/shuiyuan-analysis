# packaging 行业驱动输入表

代表公司：Packaging Corporation of America（US:PKG）。

[统一目录](README.md) · [原始行业字典](../industry-specific/packaging.md)

## packaging_driver_1 — 分品类出货数量

按品类与单位披露

选用口径：Packaging Corp 2024 全年瓦楞制品出货销售面积（67 BSF）。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| packaging_driver_1__input_1 | 包装产品出货量 | 已绑定 | pkg_corrugated_products_shipments_2024 / billion_square_feet | industry-browser-excerpt:e149a40414a9f9a2c42f14096d0245531886801057d8268012cbffae69df913f r1 |
| packaging_driver_1__input_2 | 单位 | 已绑定 | pkg_corrugated_products_shipments_2024 / billion_square_feet（范围元数据） | industry-browser-excerpt:e149a40414a9f9a2c42f14096d0245531886801057d8268012cbffae69df913f r1 |

限制：瓦楞包装制品出货面积；非箱板纸原纸造纸产量。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 包装公司 2024 全年瓦楞制品出货销售面积 | 67 billion_square_feet | 67 billion_square_feet | 2024-01-01 至 2024-12-31 / corrugated_products_annual_shipments | formula_input；全年瓦楞包装制品工厂销售出货量；以十亿平方英尺（BSF）为披露单位 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## packaging_driver_2 — 成本传导合同滞后

成本变化至合同调价的时间

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| packaging_driver_2__input_1 | 成本变化日期 | 缺失 | 待补 | 无匹配证据 |
| packaging_driver_2__input_2 | 合同调价生效日期 | 缺失 | 待补 | 无匹配证据 |
| packaging_driver_2__input_3 | 合同机制 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## packaging_driver_3 — 回收材料单位投入成本

可比单位投入成本

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| packaging_driver_3__input_1 | 回收原料采购成本 | 缺失 | 待补 | 无匹配证据 |
| packaging_driver_3__input_2 | 采购数量 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

