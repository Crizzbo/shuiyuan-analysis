# insurance 行业驱动输入表

代表公司：Chubb（US:CB）。

[统一目录](README.md) · [原始行业字典](../industry-specific/insurance.md)

## insurance_driver_1 — 财险报告综合成本率

财产险赔付率加匹配费用率

选用口径：Chubb 2025 Q4 集团财险报告赔付及两项费用率之和。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| insurance_driver_1__input_1 | 同范围赔付率 | 已绑定 | cb_pc_loss_ratio_q4 / ratio | industry-browser-excerpt:12b7c2a0e4ed894ef51cc69f20b6e3073f154d6ad8976c642de2195e2e87a40a r1 |
| insurance_driver_1__input_2 | 费用率或报告 combined ratio | 已绑定 | cb_pc_acquisition_ratio_q4 / ratio；cb_pc_admin_ratio_q4 / ratio | industry-browser-excerpt:12b7c2a0e4ed894ef51cc69f20b6e3073f154d6ad8976c642de2195e2e87a40a r1；industry-browser-excerpt:12b7c2a0e4ed894ef51cc69f20b6e3073f154d6ad8976c642de2195e2e87a40a r1 |

限制：54.3%+18.9%+8.0%=81.2%，与原表综合成本率交叉核对；剔除寿险、包含大灾及前期准备金发展、作物衍生品调整。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 报告财险综合成本率 | 81.2 percent | 0.812 ratio | 2025-10-01 至 2025-12-31 / company_property_and_casualty_reported_includes_cats_and_prior_development | 早期审核样本；完整定义待核 |
| 财险赔付及理赔费用率 | 54.3 percent | 0.543 ratio | 2025-10-01 至 2025-12-31 / group_pc_excludes_life_includes_cats_ppd_crop_derivatives | reported_metric；集团财险、剔除寿险；包含大灾、前期准备金发展及作物衍生品已实现损益调整；仅2025Q4报告精度 |
| 财险保单获取成本率 | 18.9 percent | 0.189 ratio | 2025-10-01 至 2025-12-31 / group_pc_excludes_life_includes_cats_ppd_crop_derivatives | reported_metric；集团财险、剔除寿险；包含大灾、前期准备金发展及作物衍生品已实现损益调整；仅2025Q4报告精度 |
| 财险管理费用率 | 8.0 percent | 0.080 ratio | 2025-10-01 至 2025-12-31 / group_pc_excludes_life_includes_cats_ppd_crop_derivatives | reported_metric；集团财险、剔除寿险；包含大灾、前期准备金发展及作物衍生品已实现损益调整；仅2025Q4报告精度 |
| 财险综合成本率 | 81.2 percent | 0.812 ratio | 2025-10-01 至 2025-12-31 / group_pc_excludes_life_includes_cats_ppd_crop_derivatives | reported_metric；集团财险、剔除寿险；包含大灾、前期准备金发展及作物衍生品已实现损益调整；仅2025Q4报告精度 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## insurance_driver_2 — 历史事故准备金发展

前期准备金有利或不利变化

选用口径：Chubb 2025 Q4 税前有利前期事故准备金发展额。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| insurance_driver_2__input_1 | 前期事故年度有利或不利发展 | 已绑定 | favorable_prior_period_reserve_development / USD | industry-browser-excerpt:75841bc63d1fc63aef356fecb6bbdc277df39456225f451d56e1ab664b69ea89 r1 |
| insurance_driver_2__input_2 | 再保险范围 | 已绑定 | favorable_prior_period_reserve_development / USD（范围元数据） | industry-browser-excerpt:75841bc63d1fc63aef356fecb6bbdc277df39456225f451d56e1ab664b69ea89 r1 |

限制：正值表示有利发展（释放）；仅限当季净额，未涵盖全部事故年度精算分布。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 税前有利前期准备金发展 | 268 USD_million | 268000000 USD | 2025-10-01 至 2025-12-31 / issuer_reported_favorable_prior_period_development_positive_is_favorable | 早期审核样本；完整定义待核 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## insurance_driver_3 — 资产负债期限币种匹配

期限和币种暴露

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| insurance_driver_3__input_1 | 资产久期 | 缺失 | 待补 | 无匹配证据 |
| insurance_driver_3__input_2 | 负债久期 | 缺失 | 待补 | 无匹配证据 |
| insurance_driver_3__input_3 | 币种敞口 | 缺失 | 待补 | 无匹配证据 |
| insurance_driver_3__input_4 | 匹配范围 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

