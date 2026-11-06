# regulated_utilities 行业驱动输入表

代表公司：Duke Energy（US:DUK）。

[统一目录](README.md) · [原始行业字典](../industry-specific/regulated_utilities.md)

## regulated_utilities_driver_1 — 监管批准费率资产基数

经批准的可获回报资产

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| regulated_utilities_driver_1__input_1 | 监管批准 rate base | 缺失 | 待补 | 无匹配证据 |
| regulated_utilities_driver_1__input_2 | 法律主体 | 缺失 | 待补 | 无匹配证据 |
| regulated_utilities_driver_1__input_3 | 决定日期 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## regulated_utilities_driver_2 — 监管批准权益回报率

适用监管决定的权益回报

选用口径：Duke Energy 2024 年度卡罗莱纳零售电力监管裁定核准 ROE、权益资本比例及生效期。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| regulated_utilities_driver_2__input_1 | allowed ROE | 已绑定 | duk_carolinas_allowed_roe_2024 / ratio | industry-browser-excerpt:011357fa7b8c5353145abe852694325cca45687812dc453aafda3fe691cdf74c r1 |
| regulated_utilities_driver_2__input_2 | 权益资本结构 | 已绑定 | duk_carolinas_equity_capital_ratio_2024 / ratio | industry-browser-excerpt:7aeb3222b7dda990f466803c563e1fcc2adc161d792145e0f94de221dd1bbd5c r1 |
| regulated_utilities_driver_2__input_3 | 决定生效日 | 已绑定 | duk_carolinas_allowed_roe_2024 / ratio（期间元数据） | industry-browser-excerpt:011357fa7b8c5353145abe852694325cca45687812dc453aafda3fe691cdf74c r1 |

限制：核准 ROE 9.8%、核准权益资本比例 52.0%、适用裁定生效期间对齐；同监管委员会裁定一致。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 杜克能源卡罗莱纳零售监管批准权益回报率 | 9.8 percent | 0.098 ratio | 2024-01-01 至 2024-12-31 / duke_energy_carolinas_retail_allowed_roe | formula_input；经监管委员会裁定批准之法定 ROE；适用范围为杜克能源卡罗莱纳零售电力业务 |
| 杜克能源卡罗莱纳监管核准权益资本结构比例 | 52.0 percent | 0.52 ratio | 2024-01-01 至 2024-12-31 / duke_energy_carolinas_retail_allowed_roe | formula_input；北卡罗莱纳公用事业委员会核准的法定权益资本结构比例（52.0%）；与 9.8% 允许 ROE 同裁定口径同期间 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## regulated_utilities_driver_3 — 监管成本回收滞后

支出到获准回收的期间

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| regulated_utilities_driver_3__input_1 | 支出日期 | 缺失 | 待补 | 无匹配证据 |
| regulated_utilities_driver_3__input_2 | 核准回收生效日期 | 缺失 | 待补 | 无匹配证据 |
| regulated_utilities_driver_3__input_3 | 监管机制 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

