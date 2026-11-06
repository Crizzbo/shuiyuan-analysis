# 医疗器械与生命科学工具：行业专属指标数据字典

代表公司：Intuitive Surgical（US:ISRG）。适用范围：手术机器人及耗材。代表公司不覆盖所有子行业。

## medical_devices_driver_1 — 分手术产品操作数量

| 字段 | 中文说明 |
|---|---|
| 原驱动中文名称 | 手术或耗材量 |
| 业务含义 | 按产品与临床用途记录 |
| 值类型 | scalar |
| 单位 | physical_quantity |
| 必需原始数据项 | 实际手术数量,系统类型 |
| 口径与禁止替代项 | da Vinci 与 Ion 分开；增长率不能代替绝对数量 |
| 来源顺序 | 公司年报及经营补充表、监管原文、官方行业统计 |
| 采集方法 | AI 浏览器核验原文后归档；无 API 配置 |
| 缺数处理 | 保留空值、原因及核验材料范围；阻断对应结论 |
| 判断标准 | 比较同口径时间趋势并保留反证；无经验验证阈值 |

| 原子字段标识 | 中文名称 | 单位类型 | 期间类型 |
|---|---|---|---|
| medical_devices_driver_1__value | 分手术产品操作数量 | physical_quantity | source_dependent |

所有字段均须绑定具体原文。currency 必须另填币种；physical_quantity 必须另填产品物理单位。缺数不得补零。

## medical_devices_driver_2 — 新增装机及期末装机量

| 字段 | 中文说明 |
|---|---|
| 原驱动中文名称 | 装机数量 |
| 业务含义 | 新增和存量装机分开 |
| 值类型 | components |
| 单位 | components |
| 必需原始数据项 | 当期系统 placement,期末 installed base,退役调整 |
| 口径与禁止替代项 | 交付、租赁、装机和退役分别说明 |
| 来源顺序 | 公司年报及经营补充表、监管原文、官方行业统计 |
| 采集方法 | AI 浏览器核验原文后归档；无 API 配置 |
| 缺数处理 | 保留空值、原因及核验材料范围；阻断对应结论 |
| 判断标准 | 比较同口径时间趋势并保留反证；无经验验证阈值 |

| 原子字段标识 | 中文名称 | 单位类型 | 期间类型 |
|---|---|---|---|
| medical_devices_driver_2__placements | 当期系统投放数 | systems | duration |
| medical_devices_driver_2__installed_base | 有效装机存量 | systems | instant |
| medical_devices_driver_2__retired_systems | 当期退役系统数 | systems | duration |

所有字段均须绑定具体原文。currency 必须另填币种；physical_quantity 必须另填产品物理单位。缺数不得补零。

## medical_devices_driver_3 — 每匹配系统耗材收入

| 字段 | 中文说明 |
|---|---|
| 原驱动中文名称 | 耗材附着收入 |
| 业务含义 | 可比耗材收入/明确装机基数 |
| 值类型 | scalar |
| 单位 | currency_per_system |
| 必需原始数据项 | 同系统耗材收入,匹配平均有效装机基数 |
| 口径与禁止替代项 | 期末装机不能无说明代替平均基数；服务收入排除 |
| 来源顺序 | 公司年报及经营补充表、监管原文、官方行业统计 |
| 采集方法 | AI 浏览器核验原文后归档；无 API 配置 |
| 缺数处理 | 保留空值、原因及核验材料范围；阻断对应结论 |
| 判断标准 | 比较同口径时间趋势并保留反证；无经验验证阈值 |

| 原子字段标识 | 中文名称 | 单位类型 | 期间类型 |
|---|---|---|---|
| medical_devices_driver_3__value | 每匹配系统耗材收入 | currency_per_system | source_dependent |

所有字段均须绑定具体原文。currency 必须另填币种；physical_quantity 必须另填产品物理单位。缺数不得补零。
