# digital_platforms 行业驱动输入表

代表公司：Meta Platforms（US:META）。

[统一目录](README.md) · [原始行业字典](../industry-specific/digital_platforms.md)

## digital_platforms_driver_1 — 定义内活跃用户

明确活跃标准与频率

选用口径：Meta 2025 年第四季度应用家族每日活跃人数 (DAP)。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| digital_platforms_driver_1__input_1 | DAU 或 MAU | 已绑定 | family_daily_active_people / people | industry-browser-excerpt:54c699beee01fcf9814a020023f94ab30e6e74e822edc85f6d89878828365e8d r1 |
| digital_platforms_driver_1__input_2 | 频率 | 已绑定 | family_daily_active_people / people（期间元数据） | industry-browser-excerpt:54c699beee01fcf9814a020023f94ab30e6e74e822edc85f6d89878828365e8d r1 |
| digital_platforms_driver_1__input_3 | 活跃规则 | 已绑定 | family_daily_active_people / people（范围元数据） | industry-browser-excerpt:54c699beee01fcf9814a020023f94ab30e6e74e822edc85f6d89878828365e8d r1 |

限制：去重单人统计；不包含非家族独立服务；不直接代表单应用 DAU。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 十二月平均每日活跃人数 | 3.58 billion_people | 3580000000 people | 2025-12-01 至 2025-12-31 / family_of_apps_deduplicated_people | 早期审核样本；完整定义待核 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## digital_platforms_driver_2 — 匹配活跃用户变现收入

匹配收入/平均活跃用户

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| digital_platforms_driver_2__input_1 | 同产品收入 | 缺失 | 待补 | 无匹配证据 |
| digital_platforms_driver_2__input_2 | 平均活跃用户或公司 ARPP | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## digital_platforms_driver_3 — 平台交易净抽佣率

净交易收入/匹配交易额

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| digital_platforms_driver_3__input_1 | 净交易收入 | 缺失 | 待补 | 无匹配证据 |
| digital_platforms_driver_3__input_2 | 匹配 GMV | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

