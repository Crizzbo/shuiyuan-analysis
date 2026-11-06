# 任务结果表

对象：内容寻址结果 JSON 和 CLI 摘要。完整 records 在 result_path 指向的 JSON 内。

| 字段 | 中文名称 | 类型 | 业务含义与约束 |
|---|---|---|---|
| id | 任务名称 | string | 对应计划中的任务，不代表上市公司唯一 ID |
| provider | 来源标识 | string | 实际任务来源 |
| dataset | 数据集标识 | string | 实际查询用途 |
| status | 执行状态 | string | collected 仅采集成功，失败/partial/needs_configuration 均明确输出 |
| records | 供应商记录 | array，可选 | 原字段或轻量转换记录；未形成统一财务事实契约，摘要中不重复输出 |
| record_count | 顶层记录数量 | integer，仅摘要 | records 元素个数；一个嵌套三表/序列对象可能为 1，不是财务字段或观察值总数 |
| artifacts | 归档资料列表 | array | 本次请求或缓存所指原文、路径、摘要、时间；业务失败也可能有原文 |
| quality_notes | 业务边界说明 | string array，可选 | 修订、会计准则、复权、分页、权限等限制，不作为已完成审核的证据 |
| completed_at | 任务完成时刻 | ISO datetime | 本次任务结束 UTC 时刻，不当作资料发布时间 |
| message | 失败原因 | string，可选 | 简明错误，不回显密钥或服务器敏感正文 |
| result_path | 规范化结果路径 | string，仅摘要 | 项目内相对路径，保存完整结果 |
| result_sha256 | 规范化结果摘要 | string，仅摘要 | 对 result_path 文件字节求 SHA256；恢复时核验 |
| resumed | 从本地恢复 | boolean，可选 | true 表示未重新请求，不代表资料在当前时刻仍最新 |
| search_context | 浏览器补数上下文 | object，可选 | 被停用请求的公开查询参数，供 AI 代理定位公司、期间及所缺资料；browser_required 不代表补数完成 |

正式研究不得仅凭 collected 状态通关。财报事实仍需原文定位、报告期、单位、合并范围、发布时间和指标口径审核。
