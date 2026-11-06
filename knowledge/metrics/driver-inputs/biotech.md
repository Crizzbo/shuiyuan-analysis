# biotech 行业驱动输入表

代表公司：Moderna（US:MRNA）。

[统一目录](README.md) · [原始行业字典](../industry-specific/biotech.md)

## biotech_driver_1 — 临床研发里程碑事件

项目阶段及预设终点

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| biotech_driver_1__input_1 | 试验标识 | 缺失 | 待补 | 无匹配证据 |
| biotech_driver_1__input_2 | 阶段 | 缺失 | 待补 | 无匹配证据 |
| biotech_driver_1__input_3 | 预设终点 | 缺失 | 待补 | 无匹配证据 |
| biotech_driver_1__input_4 | 结果 | 缺失 | 待补 | 无匹配证据 |
| biotech_driver_1__input_5 | 日期 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## biotech_driver_2 — 正常化现金跑道

可用现金/正常化期现金消耗

选用口径：Moderna 2025 年末期末现金与正常化月净消耗额。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| biotech_driver_2__input_1 | 可用现金和投资 | 已绑定 | mrna_cash_investments_reported / USD | industry-browser-excerpt:80eb83fad1d171c43680846687e1334d23d834514526ef458c4f1a28b1e10f63 r1 |
| biotech_driver_2__input_2 | 正常化月净消耗 | 已绑定 | mrna_monthly_cash_burn_2025 / USD | industry-browser-excerpt:e9522a029249e863e8b7d35a109fa3db4a3476b2e1af2648ebc80b5a5b7f158f r1 |
| biotech_driver_2__input_3 | 调整项 | 已绑定 | mrna_cash_runway_adjustments_2025 / USD | industry-browser-excerpt:e9522a029249e863e8b7d35a109fa3db4a3476b2e1af2648ebc80b5a5b7f158f r1 |

限制：期末现金投资 $8.1B、正常化月均消耗 $200M 与限制调整项 $0M 对齐；同 2025 财年报告口径一致。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 期末现金等价物及投资合计 | 8.1 USD_billion | 8100000000.0 USD | None 至 2025-12-31 / consolidated_cash_equivalents_and_investments | formula_input；包含投资及借款提款；受限资金、投资可变现性和标准化月度现金消耗尚缺 |
| 莫德纳 2025 全年正常化月均现金净消耗额 | 200 USD_million | 200000000 USD | 2025-01-01 至 2025-12-31 / consolidated_cash_equivalents_and_investments | formula_input；2025 全年正常化月均研发与营运现金消耗（$200 million）；与期末现金 $8.1B 同截面对齐 |
| 莫德纳 2025 年末现金跑道债务或限制调整项 | 0 USD_million | 0 USD | 2025-01-01 至 2025-12-31 / consolidated_cash_equivalents_and_investments | formula_input；2025 年末现金跑道测算之限制性调整项（$0 million）；同 2025 财年报告期间 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## biotech_driver_3 — 融资缺口与稀释情景

情景融资需求与可能股数变化

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| biotech_driver_3__input_1 | 研发现金预算 | 缺失 | 待补 | 无匹配证据 |
| biotech_driver_3__input_2 | 债务到期 | 缺失 | 待补 | 无匹配证据 |
| biotech_driver_3__input_3 | 可用资金 | 缺失 | 待补 | 无匹配证据 |
| biotech_driver_3__input_4 | 发行价格 | 缺失 | 待补 | 无匹配证据 |
| biotech_driver_3__input_5 | 新增股数 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

