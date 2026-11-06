# payments 行业驱动输入表

代表公司：Visa（US:V）。

[统一目录](README.md) · [原始行业字典](../industry-specific/payments.md)

## payments_driver_1 — 定义内支付处理金额

按支付或交易定义

选用口径：Visa FY2024 全财年名义支付处理总额（常量美元口径）。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| payments_driver_1__input_1 | 支付处理量 | 已绑定 | visa_payments_volume_fy24 / USD | industry-browser-excerpt:3e6a5bee8c9a12234c15fc29df36df06bddaec9d9f91581c7515f4afa9713984 r1 |
| payments_driver_1__input_2 | 交易类型 | 已绑定 | visa_payments_volume_fy24 / USD（范围元数据） | industry-browser-excerpt:3e6a5bee8c9a12234c15fc29df36df06bddaec9d9f91581c7515f4afa9713984 r1 |
| payments_driver_1__input_3 | 地区币种 | 已绑定 | visa_payments_volume_fy24 / USD（范围元数据） | industry-browser-excerpt:3e6a5bee8c9a12234c15fc29df36df06bddaec9d9f91581c7515f4afa9713984 r1 |

限制：全球 Visa 品牌卡片名义支付处理总额；不包含现金提现交易与欧洲双标卡剔除口径。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| Visa 全财年名义支付处理总额 | 13.2 USD_trillion | 13200000000000 USD | 2023-10-01 至 2024-09-30 / global_nominal_payments_volume_fy24 | formula_input；全球 Visa 品牌卡片及支付形态名义支付处理总额（不含现金提现交易与欧洲双标卡剔除口径） |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## payments_driver_2 — 匹配净交易变现率

匹配交易相关净收入/处理金额

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| payments_driver_2__input_1 | 同期间净交易相关收入 | 缺失 | 待补 | 无匹配证据 |
| payments_driver_2__input_2 | 匹配处理金额 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| Visa 全财年合并净营业收入 | 35,926 USD_million | 35926000000 USD | 2023-10-01 至 2024-09-30 / consolidated_net_revenue_fy24 | formula_input；全财年合并净营业收入（含服务、数据处理、国际交易扣除客户激励后的净额） |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## payments_driver_3 — 承担的欺诈与信用损失率

损失/匹配处理或信贷基数

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| payments_driver_3__input_1 | 承担欺诈或贷款损失 | 缺失 | 待补 | 无匹配证据 |
| payments_driver_3__input_2 | 匹配交易量或贷款基数 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

