# aerospace_defense 行业驱动输入表

代表公司：Lockheed Martin（US:LMT）。

[统一目录](README.md) · [原始行业字典](../industry-specific/aerospace_defense.md)

## aerospace_defense_driver_1 — 已拨款订单占比

已获拨款或承诺订单/可比订单

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| aerospace_defense_driver_1__input_1 | 已拨款或已承诺可执行订单 | 缺失 | 待补 | 无匹配证据 |
| aerospace_defense_driver_1__input_2 | 相同范围总订单 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## aerospace_defense_driver_2 — 项目总成本偏差

预计总成本与基准之差

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| aerospace_defense_driver_2__input_1 | 最新预计总成本 | 缺失 | 待补 | 无匹配证据 |
| aerospace_defense_driver_2__input_2 | 原始批准成本基准 | 缺失 | 待补 | 无匹配证据 |
| aerospace_defense_driver_2__input_3 | 项目标识 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## aerospace_defense_driver_3 — 分机型验收交付数量

按产品与验收口径披露

选用口径：Lockheed Martin 2025 全年 F-35 战机报告交付数量。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| aerospace_defense_driver_3__input_1 | 验收交付量 | 已绑定 | lmt_f35_delivered / aircraft | industry-browser-excerpt:61fca72d46f4c65abbbb1d2669708934d8053b338c43c0ef0e1c95f4b35fc4c5 r1 |
| aerospace_defense_driver_3__input_2 | 产品标识 | 已绑定 | lmt_f35_delivered / aircraft（范围元数据） | industry-browser-excerpt:61fca72d46f4c65abbbb1d2669708934d8053b338c43c0ef0e1c95f4b35fc4c5 r1 |

限制：仅限报告交付给军方客户的 F-35；F-16/C-130J 为不同型号独立口径。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| F-35 年度交付数量 | 191 aircraft | 191 aircraft | 2025-01-01 至 2025-12-31 / lmt_f35_delivered | formula_input；具体机型报告交付数；是否全部通过客户验收待核，不拼成跨型号单一产量 |
| F-16 年度交付数量 | 16 aircraft | 16 aircraft | 2025-01-01 至 2025-12-31 / lmt_f16_delivered | formula_input；具体机型报告交付数；是否全部通过客户验收待核，不拼成跨型号单一产量 |
| C-130J 年度交付数量 | 2 aircraft | 2 aircraft | 2025-01-01 至 2025-12-31 / lmt_c130j_delivered | formula_input；具体机型报告交付数；是否全部通过客户验收待核，不拼成跨型号单一产量 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

