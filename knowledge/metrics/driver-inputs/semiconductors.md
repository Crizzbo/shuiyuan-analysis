# semiconductors 行业驱动输入表

代表公司：Micron Technology（US:MU）。

[统一目录](README.md) · [原始行业字典](../industry-specific/semiconductors.md)

## semiconductors_driver_1 — 终端渠道库存量或天数

按终端与口径记录

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| semiconductors_driver_1__input_1 | 渠道产品库存量 | 缺失 | 待补 | 无匹配证据 |
| semiconductors_driver_1__input_2 | 匹配渠道日销量 | 缺失 | 待补 | 无匹配证据 |
| semiconductors_driver_1__input_3 | 终端类别 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## semiconductors_driver_2 — 有效晶圆产能利用率

产出/可比有效产能

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| semiconductors_driver_2__input_1 | 实际产出 | 缺失 | 待补 | 无匹配证据 |
| semiconductors_driver_2__input_2 | 同工艺有效产能 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## semiconductors_driver_3 — 同产品单位平均售价

可比产品收入/销量

选用口径：Micron FY2026 全年 DRAM 业务产品收入与物理 bit 出货总量。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| semiconductors_driver_3__input_1 | 产品收入 | 已绑定 | mu_dram_annual_revenue_fy26 / USD | industry-browser-excerpt:4752b86827c1fe8b01fc3b771dc16b125342070eaebf342091436fcaa678a827 r1 |
| semiconductors_driver_3__input_2 | 匹配 bit 或芯片数量 | 已绑定 | mu_dram_annual_bit_shipments_fy26 / gigabits | industry-browser-excerpt:c3d31c797e799359b6ea4fcf1dd1fad952e5f93bf98af8747f36126ce3d24415 r1 |

限制：DRAM 业务分部收入 $100.68B 与 bit 出货量 968 亿 gigabits 同财年成对；同 FY2026 报告期间一致。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 美光科技 DRAM 年度产品报告收入 | 100,680 USD_million | 100680000000 USD | 2025-08-29 至 2026-09-03 / dram_products_annual | formula_input；全财年DRAM产品合并收入；未拆分HBM与传统DRAM单项；匹配bit出货量待核 |
| 美光科技 NAND 年度产品报告收入 | 31,790 USD_million | 31790000000 USD | 2025-08-29 至 2026-09-03 / nand_products_annual | formula_input；全财年NAND产品合并收入；匹配bit出货量待核 |
| 美光科技 FY2026 全年 DRAM 业务物理 bit 出货总量 | 96,800,000,000 gigabits | 96800000000 gigabits | 2025-08-29 至 2026-09-03 / dram_products_annual | formula_input；FY2026 全财年 DRAM 物理 bit 出货总量（96,800,000,000 gigabits）；与 $100.68B 业务收入同财年同口径 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

