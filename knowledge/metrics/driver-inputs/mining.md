# mining 行业驱动输入表

代表公司：Freeport-McMoRan（US:FCX）。

[统一目录](README.md) · [原始行业字典](../industry-specific/mining.md)

## mining_driver_1 — 分商品实现售价

可比商品收入/销量

选用口径：Freeport-McMoRan 2024 全年铜综合实现平均售价与实物销售数量。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| mining_driver_1__input_1 | 商品净销售额 | 已绑定 | fcx_copper_average_realized_price_2024 / USD_per_pound | industry-browser-excerpt:199450b01d4d60a8db6f9d2d8de8e9225f14ca12d9d8e03fd795e4ade8d1dfbe r1 |
| mining_driver_1__input_2 | 商品销售数量 | 已绑定 | fcx_consolidated_copper_sales_volume_2024 / pounds | industry-browser-excerpt:55956fc84056fb957061b78f39c990586f29f2215d9c8a1e1d4bdc3e924f3d2c r1 |

限制：实现售价 $4.21/lb 与实物销量 41 亿磅成对；同 2024 财年合并口径完全一致。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 自由港麦克莫兰 2024 年度铜平均实现单价 | 4.21 USD_per_pound | 4.21 USD_per_pound | 2024-01-01 至 2024-12-31 / consolidated_copper_sales_2024 | formula_input；合并口径铜平均实现销售单价；含副产品抵扣前后需结合现金成本附注分析 |
| 自由港麦克莫兰 2024 全年铜实物销售数量 | 4.1 billion_pounds | 4100000000 pounds | 2024-01-01 至 2024-12-31 / consolidated_copper_sales_2024 | formula_input；全财年合并口径铜综合销售物理磅数（4.1 billion pounds）；与实现售价完全同范围 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## mining_driver_2 — 分商品现金单位成本

可比生产现金成本/商品产量

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| mining_driver_2__input_1 | 净现金生产成本 | 缺失 | 待补 | 无匹配证据 |
| mining_driver_2__input_2 | 匹配商品产量 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## mining_driver_3 — 矿石品位

有效成分量/矿石量

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| mining_driver_3__input_1 | 有效金属含量 | 缺失 | 待补 | 无匹配证据 |
| mining_driver_3__input_2 | 矿石处理量 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

