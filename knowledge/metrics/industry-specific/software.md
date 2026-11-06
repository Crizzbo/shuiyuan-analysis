# 软件与云服务：行业专属指标数据字典

代表公司：Datadog（US:DDOG）。适用范围：订阅及按使用量的软件服务。代表公司不覆盖所有子行业。

## software_driver_1 — 同客户群净收入留存率

| 字段 | 中文说明 |
|---|---|
| 原驱动中文名称 | 净收入留存率 |
| 业务含义 | 同群客户经常收入之比 |
| 值类型 | scalar |
| 单位 | ratio |
| 必需原始数据项 | 公司 NRR,同群窗口与定义 |
| 口径与禁止替代项 | 披露约数区间照原文保存；客户收入留存和数量留存不同 |
| 来源顺序 | 公司年报及经营补充表、监管原文、官方行业统计 |
| 采集方法 | AI 浏览器核验原文后归档；无 API 配置 |
| 缺数处理 | 保留空值、原因及核验材料范围；阻断对应结论 |
| 判断标准 | 比较同口径时间趋势并保留反证；无经验验证阈值 |

| 原子字段标识 | 中文名称 | 单位类型 | 期间类型 |
|---|---|---|---|
| software_driver_1__value | 同客户群净收入留存率 | ratio | source_dependent |

所有字段均须绑定具体原文。currency 必须另填币种；physical_quantity 必须另填产品物理单位。缺数不得补零。

## software_driver_2 — ARR 与期间订阅收入

| 字段 | 中文说明 |
|---|---|
| 原驱动中文名称 | 经常性收入 |
| 业务含义 | ARR 或订阅收入分开 |
| 值类型 | components |
| 单位 | components |
| 必需原始数据项 | 期末 ARR,期间订阅收入,订阅定义 |
| 口径与禁止替代项 | 按量计费收入不能自动改名 ARR；ARR 与收入分开 |
| 来源顺序 | 公司年报及经营补充表、监管原文、官方行业统计 |
| 采集方法 | AI 浏览器核验原文后归档；无 API 配置 |
| 缺数处理 | 保留空值、原因及核验材料范围；阻断对应结论 |
| 判断标准 | 比较同口径时间趋势并保留反证；无经验验证阈值 |

| 原子字段标识 | 中文名称 | 单位类型 | 期间类型 |
|---|---|---|---|
| software_driver_2__arr | 期末年化经常性收入 | currency | instant |
| software_driver_2__subscription_revenue | 期间订阅收入 | currency | duration |

所有字段均须绑定具体原文。currency 必须另填币种；physical_quantity 必须另填产品物理单位。缺数不得补零。

## software_driver_3 — 激励费用及股数变化

| 字段 | 中文说明 |
|---|---|
| 原驱动中文名称 | 股权稀释 |
| 业务含义 | 股数变化与股权激励成本分别记录 |
| 值类型 | components |
| 单位 | components |
| 必需原始数据项 | SBC 费用,期初期末实际发行股数,加权稀释股数 |
| 口径与禁止替代项 | 实际股数与 EPS 分母不同；拆股并购回购需调节 |
| 来源顺序 | 公司年报及经营补充表、监管原文、官方行业统计 |
| 采集方法 | AI 浏览器核验原文后归档；无 API 配置 |
| 缺数处理 | 保留空值、原因及核验材料范围；阻断对应结论 |
| 判断标准 | 比较同口径时间趋势并保留反证；无经验验证阈值 |

| 原子字段标识 | 中文名称 | 单位类型 | 期间类型 |
|---|---|---|---|
| software_driver_3__sbc | 股权激励费用 | currency | duration |
| software_driver_3__shares_start | 期初实际流通股数 | shares | instant |
| software_driver_3__shares_end | 期末实际流通股数 | shares | instant |
| software_driver_3__weighted_diluted_shares | 期间加权稀释股数 | shares | duration_average |

所有字段均须绑定具体原文。currency 必须另填币种；physical_quantity 必须另填产品物理单位。缺数不得补零。
