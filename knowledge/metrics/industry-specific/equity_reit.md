# 权益型 REIT：行业专属指标数据字典

代表公司：Prologis（US:PLD）。适用范围：物流物业权益 REIT。代表公司不覆盖所有子行业。

## equity_reit_driver_1 — 可比物业 NOI 增长

| 字段 | 中文说明 |
|---|---|
| 原驱动中文名称 | 同物业 NOI 增长 |
| 业务含义 | 固定可比物业群 NOI 同比 |
| 值类型 | scalar |
| 单位 | ratio |
| 必需原始数据项 | same-store 本期 NOI,同群同期 NOI或披露增长 |
| 口径与禁止替代项 | 现金与直线法净有效租金分别保存；物业群冻结规则记录 |
| 来源顺序 | 公司年报及经营补充表、监管原文、官方行业统计 |
| 采集方法 | AI 浏览器核验原文后归档；无 API 配置 |
| 缺数处理 | 保留空值、原因及核验材料范围；阻断对应结论 |
| 判断标准 | 比较同口径时间趋势并保留反证；无经验验证阈值 |

| 原子字段标识 | 中文名称 | 单位类型 | 期间类型 |
|---|---|---|---|
| equity_reit_driver_1__value | 可比物业 NOI 增长 | ratio | source_dependent |

所有字段均须绑定具体原文。currency 必须另填币种；physical_quantity 必须另填产品物理单位。缺数不得补零。

## equity_reit_driver_2 — 同物业面积出租率

| 字段 | 中文说明 |
|---|---|
| 原驱动中文名称 | 出租率 |
| 业务含义 | 出租面积/可出租面积 |
| 值类型 | scalar |
| 单位 | ratio |
| 必需原始数据项 | 已出租面积,可出租面积或报告 occupancy |
| 口径与禁止替代项 | 平均与期末出租率不同；自有与管理组合分开 |
| 来源顺序 | 公司年报及经营补充表、监管原文、官方行业统计 |
| 采集方法 | AI 浏览器核验原文后归档；无 API 配置 |
| 缺数处理 | 保留空值、原因及核验材料范围；阻断对应结论 |
| 判断标准 | 比较同口径时间趋势并保留反证；无经验验证阈值 |

| 原子字段标识 | 中文名称 | 单位类型 | 期间类型 |
|---|---|---|---|
| equity_reit_driver_2__value | 同物业面积出租率 | ratio | source_dependent |

所有字段均须绑定具体原文。currency 必须另填币种；physical_quantity 必须另填产品物理单位。缺数不得补零。

## equity_reit_driver_3 — FFO 至 AFFO 调节明细

| 字段 | 中文说明 |
|---|---|
| 原驱动中文名称 | AFFO 调节 |
| 业务含义 | FFO 到 AFFO 的逐项桥接 |
| 值类型 | components |
| 单位 | components |
| 必需原始数据项 | 起点 FFO,经常资本支出,租赁佣金,非现金租金,其他调整,终点 AFFO |
| 口径与禁止替代项 | Core FFO 不是 AFFO；逐项勾稽及公司定义齐备才完成 |
| 来源顺序 | 公司年报及经营补充表、监管原文、官方行业统计 |
| 采集方法 | AI 浏览器核验原文后归档；无 API 配置 |
| 缺数处理 | 保留空值、原因及核验材料范围；阻断对应结论 |
| 判断标准 | 比较同口径时间趋势并保留反证；无经验验证阈值 |

| 原子字段标识 | 中文名称 | 单位类型 | 期间类型 |
|---|---|---|---|
| equity_reit_driver_3__ffo | 调节起点 FFO | currency | duration |
| equity_reit_driver_3__maintenance_capex | 经常维持资本开支 | currency | duration |
| equity_reit_driver_3__leasing_commissions | 租赁佣金 | currency | duration |
| equity_reit_driver_3__noncash_rent_adjustments | 非现金租金调节 | currency | duration |
| equity_reit_driver_3__other_adjustments | 逐项其他调节 | currency | duration |
| equity_reit_driver_3__affo | 调节终点 AFFO | currency | duration |

所有字段均须绑定具体原文。currency 必须另填币种；physical_quantity 必须另填产品物理单位。缺数不得补零。
