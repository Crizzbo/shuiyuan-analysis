# 来源配置表

对象：`data/ingestion-sources.json`。来源配置表示允许的访问行为，不等于已经验证成功的资料。

| 字段 | 中文名称 | 类型 | 业务含义与约束 |
|---|---|---|---|
| schema_version | 配置版本 | string | 当前为 1.0.0 |
| policy.free_only | 仅免费策略 | boolean | 必须 true；不自动购买、更改套餐 |
| policy.automatic_paid_fallback | 自动收费回退 | boolean | 必须 false |
| policy.reviewed_on | 选型核对日期 | date string | 文档和计划的核对日期，不表示最后成功访问时间 |
| policy.runtime | 运行模式 | string | explicit_jobs_only，仅显式任务执行 |
| policy.no_credentials_required | 免配置策略 | boolean | 当前 true；不采用需 Key、App ID、账号或额外身份配置来源 |
| policy.missing_data_fallback | 缺失补数方式 | string | ai_browser_search；由 AI 代理搜索，不表示 CLI 内置 AI 服务 |
| sources | 来源集合 | object | 键为 provider 标识；多个 dataset 共用供应商额度 |
| hosts | 允许域名 | string array | 公共 HTTP 请求白名单；HTTPS，按完整域名匹配 |
| source_kind | 默认来源性质 | enum string | primary/secondary；按已实现请求用途可细分，不能依据“免费”决定权威性 |
| dataset_kind | 默认数据用途 | enum string | 正式来源契约已有的数据用途，按请求调整 |
| interval_seconds | 最小请求间隔 | number | 秒；项目自设保守约束，不能当成官方 SLA |
| daily_limit | 项目请求预算 | integer/null | UTC 日及滚动 24 小时预算；重试计数；SDK 按任务计数 |
| ttl_seconds | 缓存有效期 | number | 秒；超过期限可重新发请求，不证明资料仍为最新 |
| env | 凭据环境变量名 | string/null | 只存名称，null 表示无需该凭据；不存 Key 值 |
| enabled | 来源启用状态 | boolean | false 必须拦截；env 非空也拦截，不读取现有凭据 |
| disabled_reason | 停用原因 | string/null | user_rejected_configuration 为用户拒绝额外配置；未停用为 null |
| docs | 来源文档网址 | string | 选型书目，不充当本地事实证据 |
| notes | 来源边界说明 | string | 免费条件、使用限制和实现边界 |
| feeds | RSS 入口集合 | array | 仅 RSS 适配器使用，明确登记 URL |
| feeds[].name | RSS 名称 | string | 展示名称，不据此推定官方身份 |
| feeds[].url | RSS 地址 | HTTPS string | 需命中 hosts 且与请求 URL 一致 |
| feeds[].authority | 发布主体性质 | string | official/issuer/media/unreviewed；前两项有依据时可标 primary |
| feeds[].status | 入口检查状态 | string | candidate 等候选状态；不替代实际验收记录 |
