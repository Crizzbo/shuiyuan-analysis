# banks 行业驱动输入表

代表公司：JPMorgan Chase（US:JPM）。

[统一目录](README.md) · [原始行业字典](../industry-specific/banks.md)

## banks_driver_1 — 同口径年化净息差

年化净利息收入/平均生息资产

选用口径：JPM 2025 全年完全税当量管理口径净息收益率。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| banks_driver_1__input_1 | 年化净利息收入 | 已绑定 | jpm_managed_net_interest_income / USD | industry-browser-excerpt:42baa8a1e82c79809619213d8b6cf8e7a6c8a83fec002cc1a4b6c08b81c6d002 r1 |
| banks_driver_1__input_2 | 平均生息资产或公司 NIM | 已绑定 | jpm_average_interest_earning_assets / USD | industry-browser-excerpt:42baa8a1e82c79809619213d8b6cf8e7a6c8a83fec002cc1a4b6c08b81c6d002 r1 |

限制：全年无需再按季度年化；不是 GAAP 净利息收入或剔除 Markets 口径。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 年度税当量管理口径净利息收入 | 95,868 USD_million | 95868000000 USD | 2025-01-01 至 2025-12-31 / firm_managed_tax_equivalent | formula_input；管理税当量口径而非 GAAP 报告口径；分母使用同表生息资产 |
| 年度平均生息资产 | 3,834,359 USD_million | 3834359000000 USD | 2025-01-01 至 2025-12-31 / firm_managed_tax_equivalent | formula_input；不是期末总资产，也不是剔除 Markets 资产 |
| 年度管理口径净息收益率 | 2.50 percent | 0.0250 ratio | 2025-01-01 至 2025-12-31 / firm_managed_tax_equivalent | reported_metric；完全税当量口径；取整披露比例 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## banks_driver_2 — 年化贷款净核销率

年化净核销额/平均贷款

选用口径：JPM 2025 全年全集团留存贷款净核销额及平均留存贷款。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| banks_driver_2__input_1 | 扣回收后的净核销额 | 已绑定 | jpm_firm_net_chargeoffs / USD | industry-browser-excerpt:42baa8a1e82c79809619213d8b6cf8e7a6c8a83fec002cc1a4b6c08b81c6d002 r1 |
| banks_driver_2__input_2 | 平均同范围贷款 | 已绑定 | jpm_firm_average_retained_loans_2025 / USD | industry-browser-excerpt:8e3c9f93db5504a764da21fef270b776b528130c8e2c7154197eb51a7755fcc5 r1 |

限制：净核销额 9,849M 与平均留存贷款 1,330,946M 成对；同 2025 财年报告期间与口径一致。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 年度全集团净核销额 | 9,849 USD_million | 9849000000 USD | 2025-01-01 至 2025-12-31 / firm_retained_loans | formula_input；匹配平均留存贷款分母待补；不能使用批发业务单独分母 |
| 年度全集团净核销率 | 0.74 percent | 0.0074 ratio | 2025-01-01 至 2025-12-31 / firm_retained_loans | reported_metric；报告比例；平均留存贷款原始输入尚缺 |
| 摩根大通 2025 全年全集团平均留存贷款 | 1,330,946 USD_million | 1330946000000 USD | 2025-01-01 至 2025-12-31 / firm_retained_loans | formula_input；全财年合并全集团平均留存贷款（1,330,946 million USD）；与全集团净核销额完全同口径同期间 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## banks_driver_3 — 资本与流动性监管比率

记录机构披露口径及适用要求

选用口径：JPMorgan Chase 2025 年末标准化 CET1、LCR 及 NSFR 监管指标群。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| banks_driver_3__input_1 | CET1 比率 | 已绑定 | jpm_standardized_cet1 / ratio | industry-browser-excerpt:42baa8a1e82c79809619213d8b6cf8e7a6c8a83fec002cc1a4b6c08b81c6d002 r1 |
| banks_driver_3__input_2 | LCR 比率 | 已绑定 | jpm_q4_average_lcr / ratio | industry-browser-excerpt:42baa8a1e82c79809619213d8b6cf8e7a6c8a83fec002cc1a4b6c08b81c6d002 r1 |
| banks_driver_3__input_3 | NSFR 比率 | 已绑定 | jpm_nsfr_ratio_2025 / ratio | industry-browser-excerpt:06e21eb58e5d947e86a347627eafff4db3142eaf9474ed356271509b9cec2183 r1 |
| banks_driver_3__input_4 | 适用规则 | 已绑定 | jpm_standardized_cet1 / ratio（范围元数据） | industry-browser-excerpt:42baa8a1e82c79809619213d8b6cf8e7a6c8a83fec002cc1a4b6c08b81c6d002 r1 |

限制：标准化 CET1 14.6%、LCR 111%、NSFR 116% 全面成套；同 2025 年末/Q4 截面一致。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 期末集团标准法 CET1 比率 | 14.6 percent | 0.146 ratio | None 至 2025-12-31 / firm_standardized | reported_metric；标准法集团而非银行子公司或高级法；风险资产及资本分子待补 |
| 第四季度平均流动性覆盖率 | 111 percent | 1.11 ratio | 2025-10-01 至 2025-12-31 / firm_lcr_quarter_average | reported_metric；脚注限定第四季度平均，不能登记为全年平均；NSFR 实际值仍缺 |
| 摩根大通 2025 年末全集团净稳定资金比率 NSFR | 116 percent | 1.16 ratio | 2025-10-01 至 2025-12-31 / firm_nsfr_ratio | formula_input；2025 年末全集团净稳定资金比率 NSFR（116%）；巴塞尔 III 监管流动性指标，与标准化 CET1 14.6% 同年末截面 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

