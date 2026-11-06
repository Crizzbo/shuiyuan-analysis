# 原始资料归档表

对象：结果 artifacts 元素和 SQLite responses.metadata。归档仅证明取回这份资料，不证明所有正文事实已审核。

| 字段 | 中文名称 | 类型 | 业务含义与约束 |
|---|---|---|---|
| provider | 来源标识 | string | 实际采集来源，保留供应商身份 |
| origin_url | 原始访问地址 | string | 成功响应 URL，敏感 query 参数脱敏；不是正式证据路径 |
| content_type | 上游内容类型 | string，可选 | HTTP Content-Type；仍须检查文件签名和业务结构 |
| source_path | 项目内原文路径 | string | 相对路径，内容寻址；不允许越出项目 |
| sha256 | 原文摘要 | string | 文件字节 SHA256，读取缓存/恢复任务时核对 |
| source_kind | 来源性质 | string | primary/secondary；代表出处，不代表结论可靠度 |
| dataset_kind | 数据用途 | string | financial/market/news 等，按任务用途分类 |
| acquired_at | 实际取得时刻 | ISO datetime | UTC 含时区，程序生成 |
| available_at | 保守可得时刻 | ISO datetime | 初值等于取得时刻，只代表本项目观察到此版本，不是历史发布时刻 |
| availability_basis | 可得时刻依据 | string | first_observed_by_project；缓存保留原取得依据 |
| published_at | 已核对发布时间 | datetime/null | 未核对为 null，不以财报期末或抓取时间补填 |
| quality_status | 资料审核状态 | string | 初始 unreviewed，业务错误正文也可能归档，不得据此使用为财务证据 |
| currency | 行情币种 | string/null，可选 | yfinance 历史元数据；缺失不猜 USD/JPY |
| exchange_timezone | 市场时区 | string/null，可选 | yfinance 元数据；用于将 UTC 索引还原交易日 |
| symbol | 供应商证券代码 | string，可选 | 如 INTU、7203.T；不同于 CIK 或集团名称 |
| price_adjustment | 行情复权设置 | string，可选 | 保存 auto_adjust=false 的供应商 OHLC/Adj Close；不等于未拆股调整成交原价 |
| raw_transport | 归档来源形式 | string，可选 | yfinance_library_dataframe_snapshot 为库表格快照；browser_download 为 AI 浏览器实际下载原文 |
| browser_receipt | 浏览器核对登记 | object，可选 | 搜索、官方页面、实际文件链接、发行人及已核对发布时间精度，见独立浏览器来源表 |

禁止用 `.raw` 扩展名推断真实 MIME；查看、解析前参考内容签名和上游类型。PDF/ZIP 尚未自动转换成已审核的财务事实。
