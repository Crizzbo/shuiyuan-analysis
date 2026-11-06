# travel_leisure 行业驱动输入表

代表公司：Marriott International（US:MAR）。

[统一目录](README.md) · [原始行业字典](../industry-specific/travel_leisure.md)

## travel_leisure_driver_1 — 可比酒店入住率

售出间夜/可售间夜

选用口径：Marriott 2025 全年美加可比自营酒店售出间夜数与报告入住率。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| travel_leisure_driver_1__input_1 | 售出间夜 | 已绑定 | mar_comparable_rooms_sold_2025 / room_nights | industry-browser-excerpt:b6b336f6e8936e02dd79d7bf9b78477794d2d7c1aa250ed2eebbbbe10695f089 r1 |
| travel_leisure_driver_1__input_2 | 可售间夜或公司披露入住率 | 已绑定 | mar_company_operated_occupancy / ratio | industry-browser-excerpt:5bc6bda6db983c8a9cfe1cf03fe2717f945def88b4be188a20369b8a23fda900 r1 |

限制：售出间夜 18,740,000 间夜与报告入住率 69.0% 同范围成对；同 2025 财年报告期间一致。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 美加可比自营酒店年度入住率 | 69.0 percent | 0.690 ratio | 2025-01-01 至 2025-12-31 / comparable_company_operated_US_Canada | reported_metric；固定可比自营酒店群；不与加盟或全球系统酒店 ADR 混配；原始售出和可售房晚仍缺 |
| 万豪国际 2025 全年美加可比自营酒店售出间夜数 | 18,740,000 room_nights | 18740000 room_nights | 2025-01-01 至 2025-12-31 / comparable_company_operated_US_Canada | formula_input；2025 全年美加可比自营酒店实际售出客房物理间夜数（18,740,000 间夜）；与入住率口径同群同期间 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## travel_leisure_driver_2 — 可比酒店 ADR

客房收入/售出间夜

选用口径：Marriott 2025 全年美加可比自营酒店客房收入与报告 ADR。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| travel_leisure_driver_2__input_1 | 匹配客房收入 | 已绑定 | mar_comparable_rooms_revenue_2025 / USD | industry-browser-excerpt:b6b336f6e8936e02dd79d7bf9b78477794d2d7c1aa250ed2eebbbbe10695f089 r1 |
| travel_leisure_driver_2__input_2 | 售出间夜或公司 ADR | 已绑定 | mar_company_operated_adr / USD_per_room_night | industry-browser-excerpt:5bc6bda6db983c8a9cfe1cf03fe2717f945def88b4be188a20369b8a23fda900 r1 |

限制：客房收入 $5,047M 与报告 ADR $269.36 同范围成对；同 2025 财年报告期间一致。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 美加可比自营酒店年度日均房价 | 269.36 USD_per_room_night | 269.36 USD_per_room_night | 2025-01-01 至 2025-12-31 / comparable_company_operated_US_Canada | reported_metric；常量美元与可比酒店群口径；原始客房收入及售出房晚仍缺 |
| 万豪国际 2025 全年美加可比自营酒店匹配客房收入 | 5,047 USD_million | 5047000000 USD | 2025-01-01 至 2025-12-31 / comparable_company_operated_US_Canada | formula_input；2025 全年美加可比自营酒店客房收入（5,047 million USD）；与 ADR 同范围同期间 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## travel_leisure_driver_3 — 酒店预订群取消率

取消预订/匹配预订群

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| travel_leisure_driver_3__input_1 | 同一预订群取消数 | 缺失 | 待补 | 无匹配证据 |
| travel_leisure_driver_3__input_2 | 预订群总数 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

