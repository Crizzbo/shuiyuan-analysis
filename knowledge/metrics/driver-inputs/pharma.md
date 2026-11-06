# pharma 行业驱动输入表

代表公司：Pfizer（US:PFE）。

[统一目录](README.md) · [原始行业字典](../industry-specific/pharma.md)

## pharma_driver_1 — 单药净销售收入

按药品及返利后口径

选用口径：Pfizer FY2024 全年 Eliquis 全球报告净销售额（含联盟分成）。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| pharma_driver_1__input_1 | 产品净收入 | 已绑定 | pfe_eliquis_worldwide_revenue_fy24 / USD | industry-browser-excerpt:56e68b52724a184b19d1c4bf4ccb34ebb3986f157e587c8da87fff2db907b8be r1 |
| pharma_driver_1__input_2 | 药品与地区标识 | 已绑定 | pfe_eliquis_worldwide_revenue_fy24 / USD（范围元数据） | industry-browser-excerpt:56e68b52724a184b19d1c4bf4ccb34ebb3986f157e587c8da87fff2db907b8be r1 |

限制：仅限 Eliquis 单药全球销售额；未包含其他专利到期药或直销拆分。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 辉瑞 Eliquis 全球年度净销售收入 | 7,366 USD_million | 7366000000 USD | 2024-01-01 至 2024-12-31 / worldwide_eliquis_alliance_and_direct_revenue | formula_input；全球 Eliquis 合并净销售额（含联盟分成与直接销售）；未拆分各国家地区单项净销售额 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## pharma_driver_2 — 指定窗口专利到期收入暴露

指定时间到期产品收入/匹配收入

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| pharma_driver_2__input_1 | 窗口内到期产品基期净收入 | 缺失 | 待补 | 无匹配证据 |
| pharma_driver_2__input_2 | 匹配总产品收入 | 缺失 | 待补 | 无匹配证据 |
| pharma_driver_2__input_3 | 期限清单 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## pharma_driver_3 — 药物研发里程碑事件

按项目阶段与终点记录

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| pharma_driver_3__input_1 | 药物项目 | 缺失 | 待补 | 无匹配证据 |
| pharma_driver_3__input_2 | 阶段 | 缺失 | 待补 | 无匹配证据 |
| pharma_driver_3__input_3 | 主要终点 | 缺失 | 待补 | 无匹配证据 |
| pharma_driver_3__input_4 | 结果 | 缺失 | 待补 | 无匹配证据 |
| pharma_driver_3__input_5 | 事件日期 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

