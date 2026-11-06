# staples_retail 行业驱动输入表

代表公司：Costco（US:COST）。

[统一目录](README.md) · [原始行业字典](../industry-specific/staples_retail.md)

## staples_retail_driver_1 — 可比零售销售增长

相同门店范围收入同比

选用口径：Costco FY2025 全年集团报告同店销售增长率（含燃油及汇率）。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| staples_retail_driver_1__input_1 | 同店销售披露 | 已绑定 | annual_company_comparable_sales_growth / ratio | industry-browser-excerpt:48c1e98194922b27dcbf45d5210e4d3218a27452ba485ca5e5ba6a19a71e3ad9 r1 |
| staples_retail_driver_1__input_2 | 店群规则 | 已绑定 | annual_company_comparable_sales_growth / ratio（范围元数据） | industry-browser-excerpt:48c1e98194922b27dcbf45d5210e4d3218a27452ba485ca5e5ba6a19a71e3ad9 r1 |

限制：包含燃油价格与汇率波动影响；剔除口径为 7.6%。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 全年集团同店销售增长（未调整） | 5.9 percent | 0.059 ratio | 2024-09-02 至 2025-08-31 / total_company_reported_including_gasoline_and_fx | reported_metric；52 周期间；含燃油价格及汇率影响；纳入店群规则仍需年度报告核对 |
| 全年集团同店销售增长（剔除燃油汇率） | 7.6 percent | 0.076 ratio | 2024-09-02 至 2025-08-31 / total_company_excluding_gasoline_price_and_fx | reported_metric；调整增长率与未调整增长率不可混用；不是客流增长 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## staples_retail_driver_2 — 零售损耗率

损耗金额/匹配销售或库存基数

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| staples_retail_driver_2__input_1 | 损耗金额 | 缺失 | 待补 | 无匹配证据 |
| staples_retail_driver_2__input_2 | 明确销售额或存货成本基数 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## staples_retail_driver_3 — 可比交易或客流增长

可比到店或交易数同比

选用口径：Costco FY2025 全球可比仓储店到店客流频次增长率与实际交易笔数。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| staples_retail_driver_3__input_1 | 本期可比交易数 | 已绑定 | cost_comparable_transactions_fy25 / transactions | industry-browser-excerpt:3c05d9bb6cf39cee68436739666b88b3d9778775dae477197eb8b9837f46144f r1 |
| staples_retail_driver_3__input_2 | 同期交易数或公司披露增长 | 已绑定 | cost_worldwide_traffic_growth_fy25 / ratio | industry-browser-excerpt:cced516feb4bc6b4cc8d589fe507880d8c49baba407735436e347b53d8372cb4 r1 |

限制：可比交易笔数 15.81 亿笔与报告频次增速 5.4% 同范围成对；同 FY2025 财年期间一致。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| Costco全球可比客流频次增长率 | 5.4 percent | 0.054 ratio | 2024-09-02 至 2025-08-31 / worldwide_comparable_traffic | reported_metric；全集团可比仓储会员店到店客流频次增长率 |
| Costco美国本土可比客流频次增长率 | 5.2 percent | 0.052 ratio | 2024-09-02 至 2025-08-31 / us_comparable_traffic | reported_metric；仅限美国本土可比仓储会员店客流频次变动 |
| 开市客 FY2025 全球可比仓储店交易次数 | 1,581 million_transactions | 1581000000 transactions | 2024-09-02 至 2025-08-31 / worldwide_comparable_traffic | formula_input；FY2025 全财年全球可比仓储店交易总笔数（1,581 million transactions）；与 5.4% 频次增速同范围 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

