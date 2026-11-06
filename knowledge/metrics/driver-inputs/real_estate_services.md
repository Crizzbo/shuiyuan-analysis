# real_estate_services 行业驱动输入表

代表公司：Howard Hughes Holdings（US:HHH）。

[统一目录](README.md) · [原始行业字典](../industry-specific/real_estate_services.md)

## real_estate_services_driver_1 — 开发销售现金回款

实际现金回款与确认收入分开

选用口径：Howard Hughes 2024 全年主要规划社区住宅土地销售额（4.53亿美元）。输入状态：必需输入已齐备。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| real_estate_services_driver_1__input_1 | 开发项目实际现金收款 | 已绑定 | hhh_mpc_land_sales_fy24 / USD | industry-browser-excerpt:47cbcbc19beae20ab14d8959fba2d24dc5e28f863ebe9c51d18fd4d7bdd5e9eb r1 |
| real_estate_services_driver_1__input_2 | 项目范围 | 已绑定 | hhh_mpc_land_sales_fy24 / USD（范围元数据） | industry-browser-excerpt:47cbcbc19beae20ab14d8959fba2d24dc5e28f863ebe9c51d18fd4d7bdd5e9eb r1 |

限制：取得 MPC 分部住宅土地销售金额；实际项目现金回款与分期定金待补。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 霍华德休斯 2024 全年主要规划社区住宅土地销售额 | 453,195 USD_thousand | 453195000 USD | 2024-01-01 至 2024-12-31 / mpc_residential_land_sales_fy24 | formula_input；全财年 MPC 分部住宅土地销售报告金额；实际分期现金回款与预售定金待按项目附注拆分 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## real_estate_services_driver_2 — 同预售群取消率

取消/匹配订单群

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| real_estate_services_driver_2__input_1 | 预售取消数量或金额 | 缺失 | 待补 | 无匹配证据 |
| real_estate_services_driver_2__input_2 | 匹配同预售群基数 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## real_estate_services_driver_3 — 经纪管理服务佣金率

服务收入/匹配成交基数

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| real_estate_services_driver_3__input_1 | 匹配佣金服务收入 | 缺失 | 待补 | 无匹配证据 |
| real_estate_services_driver_3__input_2 | 实际交易金额或数量 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

