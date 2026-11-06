# calculation_input：计算输入

| 字段 | 中文名称 | 类型 | 业务含义 |
|---|---|---|---|
| ticker/industry_id | 证券/行业身份 | string/null | 从标准快照继承 |
| price/currency | 当前价格/币种 | number/string/null | 估值价格桥输入，不是内在价值 |
| market_available | 基础行情有效 | boolean | 仅检查价格及币种 |
| valuation_status | 估值状态 | string | missing_financial_inputs_and_model_selection，需要独立财务输入及模型选择 |
| reverse_dcf_price_binding | 反向DCF价格映射 | object | method、parameter、value；绑定target_price，不推断其他参数 |
| deep_decline_status | 行业深跌裁决状态 | string | 未校准阈值不启用；没有行业则待审核 |
| missing_fields | 区间计算缺失字段 | array | 价格、币种、高低点中未有效的属性 |
| valuation_route | 行业估值路线 | string/null | 本地行业规则文本，非自动选模结论 |
| range_descriptor | 52周区间描述 | object/null | 输入有效且区间一致时生成，非买卖信号 |
| range_descriptor.decline_from_52w_high | 距52周高跌幅 | number | 1-price/high52，0到1的小数，非路径最大回撤 |
| range_descriptor.position_in_52w_range | 52周区间位置 | number | (price-low)/(high-low)，0到1的小数 |
| range_status | 区间描述状态 | enum | available、missing_inputs或inconsistent_range |
| freshness_status | 时效状态 | string | 沿用行情的日历待审核状态 |
| action_gate | 交易动作门槛 | string | blocked；行情本身不能解除研究门槛 |
| source_ref | 原始资料定位 | object | source_path、sha256、row，支持本地追溯 |

上层 calculation_inputs.schema_version=1.0.0；as_of 是研究截止时点，inputs 是本表记录集合。截止时点早于采集时间时整批拒绝。
