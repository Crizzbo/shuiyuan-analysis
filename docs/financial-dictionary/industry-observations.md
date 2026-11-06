# 行业指标观测映射封套

| 字段 | 中文名称 | 类型 | 必填 | 业务含义 |
| --- | --- | --- | --- | --- |
| `schema_version` | 映射契约版本 | string | 是 | 封套版本 |
| `entity_id` | 公司标识 | string | 是 | 与正式资料一致 |
| `industry_id` | 候选行业 | string | 是 | 用户指定的适配，不自动确认分部归类 |
| `classification_status` | 分类审核状态 | string | 是 | 指标计算不自动完成行业分类 |
| `scope_id` | 事实范围 | string | 是 | 合并或持续经营；不得跨范围混算 |
| `period_end` | 年度截止日 | string | 是 | 当前仅审核同报告年度或相邻年度 |
| `as_of` | 信息截止时点 | string | 是 | 正式事实可得时间不晚于此时点 |
| `mapping_results` | 逐指标执行结果 | array | 是 | computed 或 blocked，保留正式登记输入及原因 |
| `observations` | 有效指标观测 | array | 是 | 只写入可计算、单位和口径明确的观测 |
| `evidence` | 原始证据 | array | 是 | 保留发布时间精度和逐字摘录 |
| `source_map` | 登记来源版本映射 | object | 是 | 证据标识对应 sources 修订 |
| `calculation_refs` | 计算执行材料 | array | 是 | 内容寻址 JSON 路径和摘要 |
| `lineage` | 输入血缘 | array | 是 | 观测关联正式登记标识及完整报告快照 |
| `missing_required_metric_ids` | 必需行业指标缺口 | array | 是 | 不能由财务共享指标替代 |
| `industry_gate_status` | 行业指标门槛状态 | string | 是 | 缺必需项为 blocked；无缺口仍须分类审核 |

观测与原文证据复用研究契约；接入研究前从正式事实重新执行并核对整个封套。
