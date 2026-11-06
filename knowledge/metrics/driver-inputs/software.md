# software 行业驱动输入表

代表公司：Datadog（US:DDOG）。

[统一目录](README.md) · [原始行业字典](../industry-specific/software.md)

## software_driver_1 — 同客户群净收入留存率

同群客户经常收入之比

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| software_driver_1__input_1 | 公司 NRR | 缺失 | 待补 | 无匹配证据 |
| software_driver_1__input_2 | 同群窗口与定义 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## software_driver_2 — ARR 与期间订阅收入

ARR 或订阅收入分开

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| software_driver_2__input_1 | 期末 ARR | 缺失 | 待补 | 无匹配证据 |
| software_driver_2__input_2 | 期间订阅收入 | 缺失 | 待补 | 无匹配证据 |
| software_driver_2__input_3 | 订阅定义 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## software_driver_3 — 激励费用及股数变化

股数变化与股权激励成本分别记录

选用口径：Datadog 2024 年费用化股权激励、年末实际发行股数及 EPS 加权稀释股数。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| software_driver_3__input_1 | SBC 费用 | 已绑定 | ddog_annual_sbc_expense_2024 / USD | industry-browser-excerpt:75b11651c9a4b5075bbb6a703aa7d3f6de6c461da5bba54bcd7db943c987940c r1 |
| software_driver_3__input_2 | 期初期末实际发行股数 | 已绑定 | ddog_actual_shares_outstanding_ye24 / shares | industry-browser-excerpt:75b11651c9a4b5075bbb6a703aa7d3f6de6c461da5bba54bcd7db943c987940c r1 |
| software_driver_3__input_3 | 加权稀释股数 | 已绑定 | ddog_weighted_diluted_eps_shares_2024 / shares | industry-browser-excerpt:75b11651c9a4b5075bbb6a703aa7d3f6de6c461da5bba54bcd7db943c987940c r1 |

限制：覆盖资产负债表期末实际发行 Class A+B 股数与 EPS 加权股数；净费用包含 SBC 支出；同 2024 财年报告期间对齐。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 年度股权激励费用（扣资本化） | 750,671 USD_thousand | 750671000 USD | 2025-01-01 至 2025-12-31 / consolidated | formula_input；仅费用部分，资本化股权激励待补；不能独立生成稀释率 |
| 年度 EPS 加权稀释股数 | 363,471 thousand_shares | 363471000 shares | 2025-01-01 至 2025-12-31 / consolidated | context_sample；EPS 加权股数不是期末实际发行股数，禁止用于期初期末稀释计算 |
| Datadog 2024 年末实际发行普通股总股数 | 342,118,782 shares | 342118782 shares | 2024-01-01 至 2024-12-31 / class_a_and_b_actual_shares_outstanding | formula_input；资产负债表期末实际发行 Class A 与 Class B 普通股合计股数（342,118,782 股）；解决加权股数与实际股数差异 |
| Datadog 2024 年股权激励费用（净额口径） | 570,336 USD_thousand | 570336000 USD | 2024-01-01 至 2024-12-31 / consolidated | formula_input；2024 全年费用化股权激励支出（570,336 thousand USD）；净费用口径 |
| Datadog 2024 年 EPS 加权稀释股数 | 358,636 thousand_shares | 358636000 shares | 2024-01-01 至 2024-12-31 / consolidated | context_sample；2024 全年 EPS 加权稀释股数（358,636 thousand 股）；同报告期间稀释基数 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

