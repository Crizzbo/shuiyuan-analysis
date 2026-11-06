# quote：证券行情

| 字段 | 中文名称 | 类型 | 业务含义 |
|---|---|---|---|
| ticker | 交易所证券代码 | string | 明确前缀的候选代码，不能跨证券类别替代 |
| name | 样本公司名称 | string | 本地采集计划名称，不是本次供应商确认的发行人名称 |
| industry_id | 项目行业标识 | string/null | 本地研究行业；不是供应商板块分类 |
| market | 样本市场 | enum | US或JP，按计划登记 |
| row | 来源行号 | integer | Google表中1起始的真实行号 |
| fields | 行情字段集合 | object | 十项固定属性，详见field表 |
| quote_status | 基础行情状态 | enum | available仅表示价格及币种有效，否则unavailable；不表示全字段、时效或真实性审核通过 |
| freshness_status | 时效审核状态 | enum | calendar_review_required；尚需核对交易日历及最近交易时间 |
| trade_timezone_status | 交易时间时区状态 | enum | unverified；不擅自换算UTC |
