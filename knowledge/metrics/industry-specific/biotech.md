# 研发型生物科技：行业专属指标数据字典

代表公司：Moderna（US:MRNA）。适用范围：生物技术研发与产品。代表公司不覆盖所有子行业。

## biotech_driver_1 — 临床研发里程碑事件

| 字段 | 中文说明 |
|---|---|
| 原驱动中文名称 | 研发里程碑 |
| 业务含义 | 项目阶段及预设终点 |
| 值类型 | event_records |
| 单位 | event_records |
| 必需原始数据项 | 试验标识,阶段,预设终点,结果,日期 |
| 口径与禁止替代项 | 实际读出与预期读出分别保存；公司计划不能当已实现结果 |
| 来源顺序 | 公司年报及经营补充表、监管原文、官方行业统计 |
| 采集方法 | AI 浏览器核验原文后归档；无 API 配置 |
| 缺数处理 | 保留空值、原因及核验材料范围；阻断对应结论 |
| 判断标准 | 比较同口径时间趋势并保留反证；无经验验证阈值 |

| 原子字段标识 | 中文名称 | 单位类型 | 期间类型 |
|---|---|---|---|
| biotech_driver_1__event_id | 事件及项目标识 | text | event |
| biotech_driver_1__event_date | 事件实际发生日期 | date | event |
| biotech_driver_1__status | 状态或实际结果 | text | event |
| biotech_driver_1__conditions | 预设终点及生效条件 | text | event |

所有字段均须绑定具体原文。currency 必须另填币种；physical_quantity 必须另填产品物理单位。缺数不得补零。

## biotech_driver_2 — 正常化现金跑道

| 字段 | 中文说明 |
|---|---|
| 原驱动中文名称 | 现金跑道 |
| 业务含义 | 可用现金/正常化期现金消耗 |
| 值类型 | scalar |
| 单位 | months |
| 必需原始数据项 | 可用现金和投资,正常化月净消耗,调整项 |
| 口径与禁止替代项 | 受限现金和不可变现投资排除；正经营现金流时不强算消耗 |
| 来源顺序 | 公司年报及经营补充表、监管原文、官方行业统计 |
| 采集方法 | AI 浏览器核验原文后归档；无 API 配置 |
| 缺数处理 | 保留空值、原因及核验材料范围；阻断对应结论 |
| 判断标准 | 比较同口径时间趋势并保留反证；无经验验证阈值 |

| 原子字段标识 | 中文名称 | 单位类型 | 期间类型 |
|---|---|---|---|
| biotech_driver_2__value | 正常化现金跑道 | months | source_dependent |

所有字段均须绑定具体原文。currency 必须另填币种；physical_quantity 必须另填产品物理单位。缺数不得补零。

## biotech_driver_3 — 融资缺口与稀释情景

| 字段 | 中文说明 |
|---|---|
| 原驱动中文名称 | 稀释需求 |
| 业务含义 | 情景融资需求与可能股数变化 |
| 值类型 | scenario |
| 单位 | scenario |
| 必需原始数据项 | 研发现金预算,债务到期,可用资金,发行价格,新增股数 |
| 口径与禁止替代项 | 情景假设不是原始事实；回购后净股数变化不等于 SBC 造成的稀释 |
| 来源顺序 | 公司年报及经营补充表、监管原文、官方行业统计 |
| 采集方法 | AI 浏览器核验原文后归档；无 API 配置 |
| 缺数处理 | 保留空值、原因及核验材料范围；阻断对应结论 |
| 判断标准 | 比较同口径时间趋势并保留反证；无经验验证阈值 |

| 原子字段标识 | 中文名称 | 单位类型 | 期间类型 |
|---|---|---|---|
| biotech_driver_3__scenario_id | 假设情景标识 | text | forecast |
| biotech_driver_3__funding_gap | 情景融资缺口 | currency | forecast |
| biotech_driver_3__issue_price | 情景发行价格 | currency_per_share | forecast |
| biotech_driver_3__new_shares | 情景新增股数 | shares | forecast |
| biotech_driver_3__dilution_ratio | 情景稀释比例 | ratio | forecast |

所有字段均须绑定具体原文。currency 必须另填币种；physical_quantity 必须另填产品物理单位。缺数不得补零。
