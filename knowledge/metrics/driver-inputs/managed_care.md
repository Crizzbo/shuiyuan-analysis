# managed_care 行业驱动输入表

代表公司：UnitedHealth Group（US:UNH）。

[统一目录](README.md) · [原始行业字典](../industry-specific/managed_care.md)

## managed_care_driver_1 — 报告医疗成本率

匹配医疗成本/保费收入

选用口径：UnitedHealth 2025 集团报告口径医疗成本率。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| managed_care_driver_1__input_1 | 匹配医疗成本 | 已绑定 | unh_reported_medical_cost / USD | industry-browser-excerpt:7c988bbb268995946b3c9ce56a34c4e7c2d736c419232681da55c784e506d4fb r1 |
| managed_care_driver_1__input_2 | 医疗保费或公司 MCR | 已绑定 | unh_reported_premium_revenue / USD | industry-browser-excerpt:7c988bbb268995946b3c9ce56a34c4e7c2d736c419232681da55c784e506d4fb r1 |

限制：不混用调整后 88.9% 的分子分母；仅限该年度报告口径。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 年度报告保费收入 | 352,229 USD_million | 352229000000 USD | 2025-01-01 至 2025-12-31 / consolidated_reported_medical_care | formula_input；报告口径，禁止与调整后医疗成本混配 |
| 年度报告医疗成本 | 313,995 USD_million | 313995000000 USD | 2025-01-01 至 2025-12-31 / consolidated_reported_medical_care | formula_input；报告口径，包括亏损合同调整影响；不能混配调整后保费 |
| 年度报告医疗成本率 | 89.1 percent | 0.891 ratio | 2025-01-01 至 2025-12-31 / consolidated_reported_medical_care | reported_metric；报告比例取整；调整后 88.9% 是另一口径 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## managed_care_driver_2 — 分险种会员数

按险种与期间记录

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| managed_care_driver_2__input_1 | 医疗险会员数量 | 缺失 | 待补 | 无匹配证据 |
| managed_care_driver_2__input_2 | 险种 | 缺失 | 待补 | 无匹配证据 |
| managed_care_driver_2__input_3 | 期末或平均 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## managed_care_driver_3 — 同险种可比保费费率调整

同险种可比保费变化

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| managed_care_driver_3__input_1 | 同保障客户群保费变化 | 缺失 | 待补 | 无匹配证据 |
| managed_care_driver_3__input_2 | 险种及保障规则 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

