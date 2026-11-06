# health_services 行业驱动输入表

代表公司：HCA Healthcare（US:HCA）。

[统一目录](README.md) · [原始行业字典](../industry-specific/health_services.md)

## health_services_driver_1 — 同院可比医疗服务量

按就诊或服务单位记录

选用口径：HCA 2025 同院综合急性期医院等价住院量及院群定义。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| health_services_driver_1__input_1 | 住院或等价住院次数 | 已绑定 | same_facility_equivalent_admissions / equivalent_admissions | industry-browser-excerpt:827a93fbcacd26318cf46747a09f6f08810795435b717691f3c06694712f0666 r1 |
| health_services_driver_1__input_2 | 院群定义 | 已绑定 | same_facility_equivalent_admissions / equivalent_admissions（范围元数据） | industry-browser-excerpt:827a93fbcacd26318cf46747a09f6f08810795435b717691f3c06694712f0666 r1 |

限制：仅限同院综合急性期医院；门诊按收入比折算等价住院量；同报告期间对齐。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 同院年度住院次数 | 2,254,279 admissions | 2254279 admissions | 2025-01-01 至 2025-12-31 / same_facility | reported_metric；同院医院群；不能与 reported 全部医院或等价住院次数混合 |
| 同院年度等价住院次数 | 3,987,820 equivalent_admissions | 3987820 equivalent_admissions | 2025-01-01 至 2025-12-31 / same_facility | reported_metric；保留公司门诊折算及同院纳入定义待核；不是实际住院人数 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## health_services_driver_2 — 每等价住院净收入

净服务收入/匹配服务量

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| health_services_driver_2__input_1 | 匹配净服务收入 | 缺失 | 待补 | 无匹配证据 |
| health_services_driver_2__input_2 | 等价住院次数 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 同院每等价住院收入 | 18,314 USD_per_equivalent_admission | 18314 USD_per_equivalent_admission | 2025-01-01 至 2025-12-31 / same_facility | reported_metric；不可与集团全部医院收入和服务量拼接；不是医院收费标价 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## health_services_driver_3 — 医疗人工成本收入比

相关人工成本/服务收入

选用口径：HCA 2025 集团工资福利收入比。输入状态：必需输入已齐备。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| health_services_driver_3__input_1 | 工资福利或匹配人工成本 | 已绑定 | consolidated_salaries_benefits / USD | industry-browser-excerpt:827a93fbcacd26318cf46747a09f6f08810795435b717691f3c06694712f0666 r1 |
| health_services_driver_3__input_2 | 净服务收入 | 已绑定 | consolidated_healthcare_revenue / USD | industry-browser-excerpt:827a93fbcacd26318cf46747a09f6f08810795435b717691f3c06694712f0666 r1 |

限制：净服务收入定义等价性和合同工人工覆盖待核；数值输入齐备不放行完整人工成本结论。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 集团年度工资及福利费用 | 32,859 USD_million | 32859000000 USD | 2025-01-01 至 2025-12-31 / consolidated_all_facilities | formula_input；集团范围；未确认合同工是否全部包含，不能视作完整人工成本 |
| 集团年度收入 | 75,600 USD_million | 75600000000 USD | 2025-01-01 至 2025-12-31 / consolidated_all_facilities | formula_input；匹配集团工资福利表，不能与同院服务量计算单位收入 |
| 报告工资福利收入比 | 43.5 percent | 0.435 ratio | 2025-01-01 至 2025-12-31 / consolidated_all_facilities | reported_metric；发行人取整百分比；不声称覆盖所有外包人员费用 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

