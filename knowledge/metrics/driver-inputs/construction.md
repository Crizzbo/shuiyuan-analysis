# construction 行业驱动输入表

代表公司：Fluor（US:FLR）。

[统一目录](README.md) · [原始行业字典](../industry-specific/construction.md)

## construction_driver_1 — 可执行积压订单覆盖年数

可执行积压订单/可比年度收入

选用口径：Fluor 2024 年度合并工程建筑期末订单与同范围年度收入。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| construction_driver_1__input_1 | 可执行期末订单额 | 已绑定 | fluor_ending_backlog_2024 / USD | industry-browser-excerpt:536c6978c98f40585fdf3574e10b7b389c2dac3c89eef30623a6ee43871edbb3 r1 |
| construction_driver_1__input_2 | 同范围年度收入 | 已绑定 | fluor_annual_revenue_2024 / USD | industry-browser-excerpt:536c6978c98f40585fdf3574e10b7b389c2dac3c89eef30623a6ee43871edbb3 r1 |

限制：合并期末订单 28,484M 与同范围年度收入 16,315M 完整成对；同 2024 财年报告期间与口径一致。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 报告集团积压订单总额 | 25,536 USD_million | 25536000000 USD | None 至 2025-12-31 / consolidated_reported_total_backlog | scope_mismatch_sample；尚未取得可执行、已融资和可取消部分划分；不能直接计算可执行订单覆盖年数 |
| 工程集团全年收入 | 15,503 USD_million | 15503000000 USD | 2025-01-01 至 2025-12-31 / consolidated | formula_input；收入包含 Santos 项目收入冲回；可比范围仍须审核 |
| 福陆 2024 年末可执行期末订单总额（Backlog） | 28,484 USD_million | 28484000000 USD | 2024-01-01 至 2024-12-31 / consolidated_construction_engineering_2024 | formula_input；截至2024年末合并期末可执行未履约订单总额；与合并收入口径一致 |
| 福陆 2024 年度合并工程建筑收入 | 16,315 USD_million | 16315000000 USD | 2024-01-01 至 2024-12-31 / consolidated_construction_engineering_2024 | formula_input；2024 全年合并工程建筑营业收入（16,315 million USD）；与期末订单口径一致 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## construction_driver_2 — 工程项目成本偏差

预计总成本与合同预算之差

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| construction_driver_2__input_1 | 最新预计总成本 | 缺失 | 待补 | 无匹配证据 |
| construction_driver_2__input_2 | 合同预算 | 缺失 | 待补 | 无匹配证据 |
| construction_driver_2__input_3 | 项目编号 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## construction_driver_3 — 合同资产及客户预付款

合同资产与预收款分别记录

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| construction_driver_3__input_1 | 合同资产 | 缺失 | 待补 | 无匹配证据 |
| construction_driver_3__input_2 | 现金客户预付款 | 缺失 | 待补 | 无匹配证据 |
| construction_driver_3__input_3 | 合同负债 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

