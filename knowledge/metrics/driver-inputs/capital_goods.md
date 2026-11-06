# capital_goods 行业驱动输入表

代表公司：GE Vernova（US:GEV）。

[统一目录](README.md) · [原始行业字典](../industry-specific/capital_goods.md)

## capital_goods_driver_1 — 新增订单收入比

同期间新增订单额/确认收入

选用口径：GE Vernova 2025 年集团报告订单收入比。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| capital_goods_driver_1__input_1 | 新增订单金额 | 已绑定 | company_new_orders / USD | industry-browser-excerpt:e01747fe6adf2a3a1bc043abfd8518b1117066ea4040e0b3855f98f5161cf623 r1 |
| capital_goods_driver_1__input_2 | 同期间确认收入 | 已绑定 | company_order_period_revenue / USD | industry-browser-excerpt:e01747fe6adf2a3a1bc043abfd8518b1117066ea4040e0b3855f98f5161cf623 r1 |

限制：采用发行人报告订单定义；分部订单与收入必须分别成对，不能跨分部混配。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 集团全年新增订单 | 59.3 USD_billion | 59300000000.0 USD | 2025-01-01 至 2025-12-31 / consolidated | formula_input；十亿美元取整披露；订单取消处理与多年服务合同定义仍须年报核对；禁止跨分部拼接 |
| 集团同期间收入 | 38.1 USD_billion | 38100000000.0 USD | 2025-01-01 至 2025-12-31 / consolidated | formula_input；十亿美元取整披露；订单取消处理与多年服务合同定义仍须年报核对；禁止跨分部拼接 |
| 电力分部全年新增订单 | 32.8 USD_billion | 32800000000.0 USD | 2025-01-01 至 2025-12-31 / power_segment | formula_input；十亿美元取整披露；订单取消处理与多年服务合同定义仍须年报核对；禁止跨分部拼接 |
| 电力分部同期间收入 | 19.8 USD_billion | 19800000000.0 USD | 2025-01-01 至 2025-12-31 / power_segment | formula_input；十亿美元取整披露；订单取消处理与多年服务合同定义仍须年报核对；禁止跨分部拼接 |
| 风电分部全年新增订单 | 7.7 USD_billion | 7700000000.0 USD | 2025-01-01 至 2025-12-31 / wind_segment | formula_input；十亿美元取整披露；订单取消处理与多年服务合同定义仍须年报核对；禁止跨分部拼接 |
| 风电分部同期间收入 | 9.1 USD_billion | 9100000000.0 USD | 2025-01-01 至 2025-12-31 / wind_segment | formula_input；十亿美元取整披露；订单取消处理与多年服务合同定义仍须年报核对；禁止跨分部拼接 |
| 电气化分部全年新增订单 | 19.3 USD_billion | 19300000000.0 USD | 2025-01-01 至 2025-12-31 / electrification_segment | formula_input；十亿美元取整披露；订单取消处理与多年服务合同定义仍须年报核对；禁止跨分部拼接 |
| 电气化分部同期间收入 | 9.6 USD_billion | 9600000000.0 USD | 2025-01-01 至 2025-12-31 / electrification_segment | formula_input；十亿美元取整披露；订单取消处理与多年服务合同定义仍须年报核对；禁止跨分部拼接 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## capital_goods_driver_2 — 积压订单及取消条款

未履约订单金额并列取消条款

选用口径：GE Vernova 2025 年末集团剩余履约义务（RPO）口径积压订单与取消条款。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| capital_goods_driver_2__input_1 | 期末 backlog | 已绑定 | company_backlog_rpo / USD | industry-browser-excerpt:e01747fe6adf2a3a1bc043abfd8518b1117066ea4040e0b3855f98f5161cf623 r1 |
| capital_goods_driver_2__input_2 | 取消条款 | 已绑定 | company_backlog_rpo / USD（范围元数据） | industry-browser-excerpt:e01747fe6adf2a3a1bc043abfd8518b1117066ea4040e0b3855f98f5161cf623 r1 |
| capital_goods_driver_2__input_3 | 可执行条件 | 已绑定 | company_backlog_rpo / USD（范围元数据） | industry-browser-excerpt:e01747fe6adf2a3a1bc043abfd8518b1117066ea4040e0b3855f98f5161cf623 r1 |

限制：采用 ASC 606 RPO 披露口径；包含不可撤销履约承诺及违约终止条款附注说明。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 集团剩余履约义务口径积压订单 | 150 USD_billion | 150000000000 USD | None 至 2025-12-31 / consolidated_rpo | formula_input；RPO 金额不是全部保证收入；缺取消条款及执行条件 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## capital_goods_driver_3 — 订单交付周期

接单到交付的可比时长

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| capital_goods_driver_3__input_1 | 接单日期 | 缺失 | 待补 | 无匹配证据 |
| capital_goods_driver_3__input_2 | 交付验收日期 | 缺失 | 待补 | 无匹配证据 |
| capital_goods_driver_3__input_3 | 订单群 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

