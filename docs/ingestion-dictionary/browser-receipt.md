# 浏览器来源登记表

对象：import_browser_source.py 的 receipt 输入。只登记 AI 实际打开和核对的页面，不以搜索摘要替代原文。

| 字段 | 中文名称 | 类型 | 业务含义与约束 |
|---|---|---|---|
| id | 浏览器资料标识 | string | 明确对应发行人、期间与文件类型；不是资料已审核结论 |
| entity_id | 发行人身份 | string | 本项目身份；集团、上市子公司、ADR 等分别确认 |
| search_url | 实际搜索入口 | string | 浏览器实际使用的查询地址，帮助重现来源发现 |
| page_url | 已核对原文页面 | HTTPS string | 必须位于已登记的发行人/交易所域名白名单 |
| document_url | 实际下载链接 | HTTPS string | 从可见官方页面取得，不能按名称猜测文件路径 |
| format | 下载文件形式 | enum string | 当前 zip/pdf；导入检查文件结构或签名，不解压执行内容 |
| published_date | 核对的发布日期 | date/null | 日期精度资料不伪装为精确 UTC 时刻；未知为 null |
| publication_precision | 发布信息精度 | enum string | date/unknown；与 published_date 是否为空一致 |
| verification_notes | 浏览器核对说明 | string | 写明页面可见的公司、报告类型、期间/发布日期及对应下载链接 |

归档输出含 artifact、zip_members、quality_notes；本版主要用于原始财报 PDF/XBRL 下载，不自动完成财务字段提取。published_at 仍为 null，available_at 为项目观察时刻。原始文件摘要在 artifact 内。
