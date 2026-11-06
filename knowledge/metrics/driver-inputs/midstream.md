# midstream 行业驱动输入表

代表公司：Enterprise Products Partners（US:EPD）。

[统一目录](README.md) · [原始行业字典](../industry-specific/midstream.md)

## midstream_driver_1 — 分产品吞吐量

按产品与运输单位披露

选用口径：EPD 2025 第四季度天然气加工厂入口日均量。输入状态：必需输入已齐备。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| midstream_driver_1__input_1 | 产品吞吐量 | 已绑定 | gas_processing_inlet_daily_volume / Bcf_per_day | industry-browser-excerpt:0e6ae6e525d2c42f75de53bc52effe5d6c03bc2a7479d0cb456441618a3d8d89 r1 |
| midstream_driver_1__input_2 | 披露单位 | 已绑定 | gas_processing_inlet_daily_volume / Bcf_per_day（范围元数据） | industry-browser-excerpt:0e6ae6e525d2c42f75de53bc52effe5d6c03bc2a7479d0cb456441618a3d8d89 r1 |
| midstream_driver_1__input_3 | 日均或期间总量 | 已绑定 | gas_processing_inlet_daily_volume / Bcf_per_day（期间元数据） | industry-browser-excerpt:0e6ae6e525d2c42f75de53bc52effe5d6c03bc2a7479d0cb456441618a3d8d89 r1 |

限制：入口处理量不自动代表所有中游运输吞吐量。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 天然气处理入口日均气量 | 8.1 Bcf_per_day | 8.1 Bcf_per_day | 2025-10-01 至 2025-12-31 / natural_gas_processing_plant_inlet | 早期审核样本；完整定义待核 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## midstream_driver_2 — 固定收费收入占比

固定收费合同收入/相关收入

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| midstream_driver_2__input_1 | 固定收费合同收入 | 缺失 | 待补 | 无匹配证据 |
| midstream_driver_2__input_2 | 匹配相关收入 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## midstream_driver_3 — 维持资本开支现金额

维持现有资产的现金投入

选用口径：Enterprise Products Partners 2025 Q4 维持资本支出现金额。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| midstream_driver_3__input_1 | 公司披露 sustaining capex | 已绑定 | sustaining_capex / USD | industry-browser-excerpt:0e6ae6e525d2c42f75de53bc52effe5d6c03bc2a7479d0cb456441618a3d8d89 r1 |
| midstream_driver_3__input_2 | 范围说明 | 已绑定 | sustaining_capex / USD（范围元数据） | industry-browser-excerpt:0e6ae6e525d2c42f75de53bc52effe5d6c03bc2a7479d0cb456441618a3d8d89 r1 |

限制：仅限合伙企业现有资产维持性开支；增长性项目与资产收购不属于本项。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 维持资本开支实际现金额 | 203 USD_million | 203000000 USD | 2025-10-01 至 2025-12-31 / partnership_existing_assets | 早期审核样本；完整定义待核 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

