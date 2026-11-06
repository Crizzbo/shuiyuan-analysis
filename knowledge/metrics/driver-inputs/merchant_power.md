# merchant_power 行业驱动输入表

代表公司：Constellation Energy（US:CEG）。

[统一目录](README.md) · [原始行业字典](../industry-specific/merchant_power.md)

## merchant_power_driver_1 — 匹配售电捕获价格

售电收入/匹配售电量

选用口径：Constellation Energy 2024 全年商业售电合并营业收入与发电总量（MWh）。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| merchant_power_driver_1__input_1 | 匹配售电净收入 | 已绑定 | ceg_annual_operating_revenues_2024 / USD | industry-browser-excerpt:1634ae4e33493039b4cfdb0156ec9a2f97d2febcfd7213ab5866ea26901d6b2e r1 |
| merchant_power_driver_1__input_2 | 对应 MWh | 已绑定 | ceg_annual_generation_mwh_2024 / MWh | industry-browser-excerpt:1388d7cb4a9bd201c834956911812afcb2d56ad9c87281919105baaa21bc593d r1 |

限制：合并售电营业收入 $23.568B 与发电产出 121 TWh (121,000,000 MWh) 成对；同 2024 财年报告期间一致。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 星座能源 2024 全年合并营业总收入 | 23,568 USD_million | 23568000000 USD | 2024-01-01 至 2024-12-31 / consolidated_operating_revenues_2024 | formula_input；全财年合并营业收入（含 Mid-Atlantic、Midwest 及 ERCOT 各大区电力销售）；匹配发电量 MWh 待分部细拆 |
| 星座能源 2024 全年发电总量（MWh口径） | 121 TWh | 121000000 MWh | 2024-01-01 至 2024-12-31 / consolidated_operating_revenues_2024 | formula_input；全财年发电总产出（121 TWh 折合 121,000,000 MWh）；与营业收入同报告期间 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## merchant_power_driver_2 — 效率调整后燃料电价差

单位电价减效率调整燃料成本

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| merchant_power_driver_2__input_1 | 同范围电价 | 缺失 | 待补 | 无匹配证据 |
| merchant_power_driver_2__input_2 | 燃料价格 | 缺失 | 待补 | 无匹配证据 |
| merchant_power_driver_2__input_3 | 热耗效率 | 缺失 | 待补 | 无匹配证据 |
| merchant_power_driver_2__input_4 | 单位换算 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## merchant_power_driver_3 — 匹配预期发电对冲覆盖率

已对冲或长约电量/匹配预期电量

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| merchant_power_driver_3__input_1 | 已对冲电量 | 缺失 | 待补 | 无匹配证据 |
| merchant_power_driver_3__input_2 | 同窗口预计售电量 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

