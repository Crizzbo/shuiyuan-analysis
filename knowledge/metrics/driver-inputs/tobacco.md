# tobacco 行业驱动输入表

代表公司：Philip Morris International（US:PM）。

[统一目录](README.md) · [原始行业字典](../industry-specific/tobacco.md)

## tobacco_driver_1 — 传统卷烟出货量

按产品和地区披露

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| tobacco_driver_1__input_1 | 传统卷烟数量 | 缺失 | 待补 | 无匹配证据 |
| tobacco_driver_1__input_2 | 地区产品 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## tobacco_driver_2 — 卷烟扣税单位净售价

扣税后的可比收入/销量

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| tobacco_driver_2__input_1 | 扣消费税传统产品收入 | 缺失 | 待补 | 无匹配证据 |
| tobacco_driver_2__input_2 | 匹配传统产品数量 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## tobacco_driver_3 — 替代产品收入及利润

替代业务收入与利润分开

选用口径：菲莫国际 2025 全年无烟业务净收入与分部经营利润。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| tobacco_driver_3__input_1 | 无烟产品净收入 | 已绑定 | smoke_free_net_revenue / USD | industry-browser-excerpt:1c09afeb706ab58f6aef3f896e582f47a2535989f75695366be43df357e76bf8 r1 |
| tobacco_driver_3__input_2 | 同范围经营利润 | 已绑定 | pm_smoke_free_operating_income_2025 / USD | industry-browser-excerpt:e08bde100ba0709d738d6d36190a5acf2e34c98db41296add4b54a5bd0aa1c7f r1 |

限制：无烟业务净收入 $16.9B 与分部经营利润 $6.8B 完整成对；同 2025 财年分部口径一致。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 无烟业务全年净收入 | 16.9 USD_billion | 16900000000.0 USD | 2025-01-01 至 2025-12-31 / smoke_free_business | formula_input；十亿美元取整披露；保留集团收入与业务收入不同范围 |
| 无烟业务全年毛利润 | 11.7 USD_billion | 11700000000.0 USD | 2025-01-01 至 2025-12-31 / smoke_free_business | profit_basis_variant；毛利润不是营业利润或净利润；不可直接绑定 operating_profit 原子字段 |
| 无烟业务全年净收入占比 | 41.5 percent | 0.415 ratio | 2025-01-01 至 2025-12-31 / smoke_free_share_of_company_net_revenue | context_sample；发行人报告占比；取整收入之比不应强制等于此占比 |
| 菲莫国际 2025 全年无烟业务经营利润 | 6,800 USD_million | 6800000000 USD | 2025-01-01 至 2025-12-31 / smoke_free_business | formula_input；2025 全年无烟业务分部经营利润（6,800 million USD）；与无烟业务净收入同范围同期间 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

