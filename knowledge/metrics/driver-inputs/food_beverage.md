# food_beverage 行业驱动输入表

代表公司：Coca-Cola（US:KO）。

[统一目录](README.md) · [原始行业字典](../industry-specific/food_beverage.md)

## food_beverage_driver_1 — 可比产品销量增长

可比销量同比

选用口径：Coca-Cola 2025 全年全球系统标准箱物理销量与披露增长（持平）。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| food_beverage_driver_1__input_1 | 本期可比销量 | 已绑定 | coca_cola_unit_case_volume_2025 / unit_cases | industry-browser-excerpt:6635f7b17b00f64b4bc718898c06d86d79aedc427e76d56080061068a60e53da r1 |
| food_beverage_driver_1__input_2 | 同期可比销量或披露增长 | 已绑定 | system_unit_case_volume_growth / ratio | industry-browser-excerpt:ee03c83840992516a8bc016b0ea734fb77b80b1239ff601b2484a494db486c7c r1 |

限制：本期物理销量 333 亿箱与定性零增长（Even）同口径成对；同 2025 财年报告期间一致。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 系统标准箱日均销量全年增长率 | Even qualitative_zero_growth | 0 ratio | 2025-01-01 至 2025-12-31 / global_system_average_daily_unit_case_volume | 早期审核样本；完整定义待核 |
| 可口可乐 2025 全年全球系统标准箱销量 | 33.3 billion_unit_cases | 33300000000 unit_cases | 2025-01-01 至 2025-12-31 / global_system_average_daily_unit_case_volume | formula_input；2025 全年全球系统标准箱物理销量（33.3 billion unit cases）；与持平增长率（Even）同口径同期间 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## food_beverage_driver_2 — 价格与组合增长贡献

明确方法的价格与产品组合收入变化

选用口径：Coca-Cola 2025 全年有机营收增长桥接价格与组合贡献率。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| food_beverage_driver_2__input_1 | 公司价格组合桥接贡献 | 已绑定 | price_mix_contribution / ratio | industry-browser-excerpt:ee03c83840992516a8bc016b0ea734fb77b80b1239ff601b2484a494db486c7c r1 |
| food_beverage_driver_2__input_2 | 公司桥接定义 | 已绑定 | price_mix_contribution / ratio（范围元数据） | industry-browser-excerpt:ee03c83840992516a8bc016b0ea734fb77b80b1239ff601b2484a494db486c7c r1 |

限制：属于有机收入桥接分解项；不是绝对单价变动金额。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 全年价格及产品组合贡献 | 4 percent | 0.04 ratio | 2025-01-01 至 2025-12-31 / global_company_organic_revenue_growth_bridge | 早期审核样本；完整定义待核 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## food_beverage_driver_3 — 渠道产品库存数量

按渠道覆盖记录存量

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| food_beverage_driver_3__input_1 | 经销商库存量 | 缺失 | 待补 | 无匹配证据 |
| food_beverage_driver_3__input_2 | 产品渠道覆盖 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

