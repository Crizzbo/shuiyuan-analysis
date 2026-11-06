# business_services 行业驱动输入表

代表公司：Automatic Data Processing（US:ADP）。

[统一目录](README.md) · [原始行业字典](../industry-specific/business_services.md)

## business_services_driver_1 — 服务人员计费利用率

可计费工时/可用工时

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| business_services_driver_1__input_1 | 可计费工时 | 缺失 | 待补 | 无匹配证据 |
| business_services_driver_1__input_2 | 可用工时 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## business_services_driver_2 — 客户数量留存率

留存客户/基期客户

选用口径：ADP FY2024 雇主服务分部客户收入留存率与基期客户总数。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| business_services_driver_2__input_1 | 基期客户中本期留存数量 | 已绑定 | adp_es_client_revenue_retention_fy24 / ratio | industry-browser-excerpt:8783595e9cfd69fa19296abd2d3365cea5bd3cd8fb048f09a42c85b019a63289 r1 |
| business_services_driver_2__input_2 | 基期客户数量 | 已绑定 | adp_es_client_count_fy24 / clients | industry-browser-excerpt:dbea70d0128cc5f0167c623f1780e6f904866179c012219c5ac66bab38f2bd97 r1 |

限制：收入留存率 92% 与基期 1,000,000 客户规模同财年对齐；解决原始物理客户基数。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| ADP FY2024 雇主服务客户收入留存率 | 92 percent | 0.92 ratio | 2023-07-01 至 2024-06-30 / employer_services_client_revenue_retention_fy24 | formula_input；全财年雇主服务分部收入加权口径留存率；原始物理客户家数留存待附注拆分 |
| ADP FY2024 雇主服务分部基期客户总数量 | 1,000,000 clients | 1000000 clients | 2023-07-01 至 2024-06-30 / employer_services_client_revenue_retention_fy24 | formula_input；FY2024 全财年雇主服务分部基期客户服务总数（1,000,000 客户）；与收入留存率 92% 同财年对齐 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## business_services_driver_3 — 标准服务合同单价

可比服务收入/计费单位

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| business_services_driver_3__input_1 | 可比服务收入 | 缺失 | 待补 | 无匹配证据 |
| business_services_driver_3__input_2 | 匹配计费单位 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

