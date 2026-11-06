# media_entertainment 行业驱动输入表

代表公司：Netflix（US:NFLX）。

[统一目录](README.md) · [原始行业字典](../industry-specific/media_entertainment.md)

## media_entertainment_driver_1 — 付费订阅用户数量

明确平均与期末口径

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| media_entertainment_driver_1__input_1 | paid membership | 缺失 | 待补 | 无匹配证据 |
| media_entertainment_driver_1__input_2 | 平均或期末 | 缺失 | 待补 | 无匹配证据 |
| media_entertainment_driver_1__input_3 | 产品地区 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## media_entertainment_driver_2 — 内容现金投入

当期内容现金支出

选用口径：Netflix 2025 内容资产现金增加与内容负债净变动调节口径。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| media_entertainment_driver_2__input_1 | 内容现金支付 | 已绑定 | nflx_content_asset_additions_cf / USD；nflx_content_liability_change_cf / USD | industry-browser-excerpt:47ac5adff8750a569906291784594671aee190f33324344b15254d672785f29d r1；industry-browser-excerpt:47ac5adff8750a569906291784594671aee190f33324344b15254d672785f29d r1 |
| media_entertainment_driver_2__input_2 | 许可自制与预付口径 | 已绑定 | nflx_content_asset_additions_cf / USD（范围元数据） | industry-browser-excerpt:47ac5adff8750a569906291784594671aee190f33324344b15254d672785f29d r1 |

限制：包含内容资产现金投入及负债变动；覆盖自制与许可内容；同 2025 财年报告现金流口径一致。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 内容资产新增的现金流调节项 | (17,096,617) USD_thousand | -17096617000 USD | 2025-01-01 至 2025-12-31 / consolidated_content_cashflow | formula_input；按现金流表保留负号；单独该项不是内容现金支付，须结合内容负债变动 |
| 内容负债变动现金流项 | (610,838) USD_thousand | -610838000 USD | 2025-01-01 至 2025-12-31 / consolidated_content_cashflow | formula_input；保留现金流负号，与同期间内容资产新增配对；不是期末负债余额 |
| 年度内容摊销 | 16,422,166 USD_thousand | 16422166000 USD | 2025-01-01 至 2025-12-31 / consolidated_content_cashflow | formula_input；非现金费用；不能直接视作内容现金支出 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## media_entertainment_driver_3 — 当期内容摊销

当期确认的内容成本

选用口径：Netflix 2025 年度内容资产摊销。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| media_entertainment_driver_3__input_1 | 内容资产摊销或内容成本附注 | 已绑定 | nflx_content_amortization_driver3 / USD | industry-browser-excerpt:d8c0c310474860b376d573605e7dfe7dfa3efe7bc3ca386e1ed97fe2711a4c19 r1 |

限制：仅限内容资产摊销；不等同现金支付或完整内容成本。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 年度内容资产摊销费用 | 16,422,166 USD_thousand | 16422166000 USD | 2025-01-01 至 2025-12-31 / consolidated_content_cashflow | reported_metric；现金流表同期间内容摊销；不是新增内容资产或现金支付，不覆盖其他内容成本 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

