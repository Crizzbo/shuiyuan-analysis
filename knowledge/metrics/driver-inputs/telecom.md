# telecom 行业驱动输入表

代表公司：Verizon（US:VZ）。

[统一目录](README.md) · [原始行业字典](../industry-specific/telecom.md)

## telecom_driver_1 — 单匹配用户服务 ARPU

可比服务收入/平均匹配用户

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| telecom_driver_1__input_1 | 服务收入 | 缺失 | 待补 | 无匹配证据 |
| telecom_driver_1__input_2 | 平均对应用户 | 缺失 | 待补 | 无匹配证据 |
| telecom_driver_1__input_3 | 月数 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 核心预付费每连接报告服务收入 | 32.90 USD_per_connection | 32.90 USD_per_connection | 2025-10-01 至 2025-12-31 / core_prepaid_excludes_safelink | context_sample；剔除SafeLink的预付费ARPU；不是后付费ARPA，服务收入及平均同群连接数未拆出，不能充当公式分子分母 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## telecom_driver_2 — 同用户群月均流失率

流失用户/明确平均用户基数

选用口径：Verizon 2025 Q4 全无线零售后付费手机断开数、平均活跃连接数与报告流失率。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| telecom_driver_2__input_1 | 断开用户数 | 已绑定 | vz_q4_postpaid_phone_disconnects / connections | industry-browser-excerpt:80604ab6ce364bb46ba7ef7060103b1b48dc17c8d4fb49de183a9238e6c81d1b r1 |
| telecom_driver_2__input_2 | 平均用户 | 已绑定 | vz_q4_postpaid_phone_average_connections / connections | industry-browser-excerpt:80604ab6ce364bb46ba7ef7060103b1b48dc17c8d4fb49de183a9238e6c81d1b r1 |
| telecom_driver_2__input_3 | 月数或披露 churn | 已绑定 | vz_total_postpaid_phone_churn_q4 / ratio | industry-browser-excerpt:db2008deee36299b265dc4e1305311fdaf8119fb0f82d444bf1b754f184925d3 r1 |

限制：断开数 769,284 连接与平均 75,420,000 连接同范围成对；对应报告 1.02% 季度 churn；同 2025 Q4 期间一致。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 全无线后付费电话季度报告流失率 | 1.02 percent | 0.0102 ratio | 2025-10-01 至 2025-12-31 / total_wireless_retail_postpaid_phone | reported_metric；消费者和企业无线合计后付费电话；不是全设备或预付费流失率；断开数和平均连接数未取得 |
| 威瑞森 2025 Q4 零售后付费电话断开连接数 | 769,284 connections | 769284 connections | 2025-10-01 至 2025-12-31 / total_wireless_retail_postpaid_phone | formula_input；2025 Q4 零售后付费手机断开总数（769,284 connections）；与 75,420,000 平均连接数及 1.02% 季度 churn 同口径对齐 |
| 威瑞森 2025 Q4 零售后付费电话平均活跃连接数 | 75,420,000 connections | 75420000 connections | 2025-10-01 至 2025-12-31 / total_wireless_retail_postpaid_phone | formula_input；2025 Q4 零售后付费手机平均连接规模（75,420,000 connections）；与断开数成对 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## telecom_driver_3 — 网络维持及扩张现金开支

现金投入按维持与扩张分开

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| telecom_driver_3__input_1 | 网络现金 capex | 缺失 | 待补 | 无匹配证据 |
| telecom_driver_3__input_2 | 维持部分 | 缺失 | 待补 | 无匹配证据 |
| telecom_driver_3__input_3 | 扩张部分 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 年度集团总资本开支 | 17.0 USD_billion | 17000000000.0 USD | 2025-01-01 至 2025-12-31 / consolidated_total_capex | scope_mismatch_sample；集团总额缺网络、维持性与增长性拆分，不能替代网络资本开支强度 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

