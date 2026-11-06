# 标准财报记录

| 字段代码 | 中文名称 | 类型 | 必填 | 业务含义 |
| --- | --- | --- | --- | --- |
| `schema_version` | 契约版本 | string | 是 | 财报 staging 契约版本 |
| `report_id` | 报告版本标识 | string | 是 | 解析配置对应的报告标识；新财报及重述建立新标识 |
| `entity_id` | 公司标识 | string | 是 | 与浏览器登记公司身份一致；CIK 核对由解析器完成 |
| `supersedes_report_id` | 被替代报告标识 | string/null | 是 | 重述时显式链接旧报告；原历史不更新删除 |
| `artifact` | 原文归档记录 | object | 是 | 沿用接入原文对象，包含 ZIP/PDF 哈希及浏览器日期精度 |
| `parser` | 解析边界 | object | 是 | 成员哈希、准则证据或审核模板；完整 DTS 结果单独在 taxonomy_validation 保存 |
| `plan_sha256` | 解析配置摘要 | string | 是 | 可复现科目映射和列选择 |
| `implementation_sha256` | 解析实现摘要 | string | 是 | 运行时解析模块文件内容哈希 |
| `facts` | 标准事实列表 | array | 是 | 提取后归并的报表科目事实；不是正式研究 observation |
| `issues` | 解析异常列表 | array | 是 | 无法安全转换的原文定位与原因；不填零 |
| `checks` | 勾稽校验列表 | array | 是 | passed/failed/incomplete，残差和容差使用基础货币单位 |
| `calculations` | 计算结果列表 | array | 是 | 返回公式、开源库、事实引用；缺失或口径不符为 blocked |
| `release_status` | 发布状态 | string | 是 | 当前只能进入 staging，尚不自动发布研究结论 |
| `missing_capabilities` | 未执行能力 | array | 是 | 尚未执行的校验；不是六步分析完成状态 |
| `taxonomy_validation` | 完整分类标准校验 | object | 条件必填/可选 | passed/blocked/not_run/not_applicable；PDF 不适用 XBRL 校验，详细日志内容寻址归档 |

字段与 `schemas/financial-report.schema.json` 同源生成；对象数组的具体运行结果见 14 功能设计。
