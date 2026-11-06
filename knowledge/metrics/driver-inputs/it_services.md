# it_services 行业驱动输入表

代表公司：Accenture（US:ACN）。

[统一目录](README.md) · [原始行业字典](../industry-specific/it_services.md)

## it_services_driver_1 — 专业人员可计费利用率

计费工时/可用工时

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| it_services_driver_1__input_1 | 计费工时 | 缺失 | 待补 | 无匹配证据 |
| it_services_driver_1__input_2 | 可用专业人员工时或公司 utilization | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## it_services_driver_2 — 同范围新增合同金额

同范围签约金额

选用口径：Accenture FY2026 咨询服务新签合同报告金额。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| it_services_driver_2__input_1 | 新签合同 bookings | 已绑定 | acn_consulting_new_bookings / USD | industry-browser-excerpt:b4e74ba81e9956746c0d587bffed1d84a789d24a1be80c21d4e0bec5553551ff r1 |
| it_services_driver_2__input_2 | 服务类别 | 已绑定 | acn_consulting_new_bookings / USD（范围元数据） | industry-browser-excerpt:b4e74ba81e9956746c0d587bffed1d84a789d24a1be80c21d4e0bec5553551ff r1 |

限制：咨询合同不是托管合同或确认收入；不能据此判断全部可执行。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 年度集团新签合同 | 84.54 USD_billion | 84540000000.00 USD | 2025-09-01 至 2026-08-31 / consolidated | formula_input；保留公司合同估计金额；取消权、汇率及变动范围待核，不等同已确认收入 |
| 年度咨询新签合同 | 40.86 USD_billion | 40860000000.00 USD | 2025-09-01 至 2026-08-31 / consulting | formula_input；保留公司合同估计金额；取消权、汇率及变动范围待核，不等同已确认收入 |
| 年度托管服务新签合同 | 43.67 USD_billion | 43670000000.00 USD | 2025-09-01 至 2026-08-31 / managed_services | formula_input；保留公司合同估计金额；取消权、汇率及变动范围待核，不等同已确认收入 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## it_services_driver_3 — 单位计费服务费率

可比收入/计费单位

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| it_services_driver_3__input_1 | 同范围服务收入 | 缺失 | 待补 | 无匹配证据 |
| it_services_driver_3__input_2 | 实际计费工时 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

