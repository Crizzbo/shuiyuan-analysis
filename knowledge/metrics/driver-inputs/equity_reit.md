# equity_reit 行业驱动输入表

代表公司：Prologis（US:PLD）。

[统一目录](README.md) · [原始行业字典](../industry-specific/equity_reit.md)

## equity_reit_driver_1 — 可比物业 NOI 增长

固定可比物业群 NOI 同比

选用口径：Prologis 4Q25 权益份额现金同店净营业收入与报告增长率。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| equity_reit_driver_1__input_1 | same-store 本期 NOI | 已绑定 | pld_q4_same_store_cash_noi / USD | industry-browser-excerpt:edf83371eb019919c9c214206249c9d43aadd91b6429dafb2b774ba9514ffd82 r1 |
| equity_reit_driver_1__input_2 | 同群同期 NOI或披露增长 | 已绑定 | cash_same_store_noi_growth / ratio | industry-browser-excerpt:f1d3e930a8c5a681fea4de926fe64fc032dfafeef9d0c08efe98b26d52cd0c2c r1 |

限制：本期现金同店 NOI $1,281M 与增长率 5.7% 同群同期间对齐；同 4Q25 报告口径一致。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 权益份额现金同物业 NOI 增长 | 5.7 percent | 0.057 ratio | 2025-10-01 至 2025-12-31 / prologis_share_cash_same_store_noi | reported_metric；现金口径非 GAAP；物业群冻结与调节定义仍须补充表核验 |
| 普洛斯 4Q25 权益份额现金同店净营业收入 | 1,281 USD_million | 1281000000 USD | 2025-10-01 至 2025-12-31 / prologis_share_cash_same_store_noi | formula_input；2025 Q4 普洛斯权益份额现金同店净营业收入（$1,281 million）；与 5.7% 现金同店增速同范围同期间 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## equity_reit_driver_2 — 同物业面积出租率

出租面积/可出租面积

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| equity_reit_driver_2__input_1 | 已出租面积 | 缺失 | 待补 | 无匹配证据 |
| equity_reit_driver_2__input_2 | 可出租面积或报告 occupancy | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 自有及管理组合平均出租率 | 95.3 percent | 0.953 ratio | 2025-10-01 至 2025-12-31 / owned_and_managed_operating_portfolio_average | scope_mismatch_sample；整个自有管理组合；不能替代固定同物业群出租率 |
| 自有及管理组合期末出租率 | 95.8 percent | 0.958 ratio | None 至 2025-12-31 / owned_and_managed_operating_portfolio_period_end | scope_mismatch_sample；期末值不同于季度平均；不能替代同物业群出租率 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## equity_reit_driver_3 — FFO 至 AFFO 调节明细

FFO 到 AFFO 的逐项桥接

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| equity_reit_driver_3__input_1 | 起点 FFO | 缺失 | 待补 | 无匹配证据 |
| equity_reit_driver_3__input_2 | 经常资本支出 | 缺失 | 待补 | 无匹配证据 |
| equity_reit_driver_3__input_3 | 租赁佣金 | 缺失 | 待补 | 无匹配证据 |
| equity_reit_driver_3__input_4 | 非现金租金 | 缺失 | 待补 | 无匹配证据 |
| equity_reit_driver_3__input_5 | 其他调整 | 缺失 | 待补 | 无匹配证据 |
| equity_reit_driver_3__input_6 | 终点 AFFO | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

