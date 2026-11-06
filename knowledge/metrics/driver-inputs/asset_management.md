# asset_management 行业驱动输入表

代表公司：BlackRock（US:BLK）。

[统一目录](README.md) · [原始行业字典](../industry-specific/asset_management.md)

## asset_management_driver_1 — 客户净资金流入

剔除市场变化的客户资金流

选用口径：BlackRock 2025 全年客户毛流入、毛流出、资本返还与净流量口径。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| asset_management_driver_1__input_1 | 客户流入 | 已绑定 | blk_gross_inflows_2025 / USD | industry-browser-excerpt:b5dcfebfaf2e51adda312880cfa7dc576c5856977f9421bdd604cd66bae19802 r1 |
| asset_management_driver_1__input_2 | 流出 | 已绑定 | blk_gross_outflows_2025 / USD | industry-browser-excerpt:b5dcfebfaf2e51adda312880cfa7dc576c5856977f9421bdd604cd66bae19802 r1 |
| asset_management_driver_1__input_3 | 资本返还 | 已绑定 | blk_capital_returned_2025 / USD | industry-browser-excerpt:b5dcfebfaf2e51adda312880cfa7dc576c5856977f9421bdd604cd66bae19802 r1 |
| asset_management_driver_1__input_4 | 公司流量定义 | 已绑定 | net_client_flows / USD（范围元数据） | industry-browser-excerpt:86ea1815654ccc802afbc066049cba284caa6c54fd7ca0cd9d1e0c97760e007f r1 |

限制：毛流入 $3,215B、毛流出 $2,502B、资本返还 $15B 完整成套；净流入 $698B 对齐；同 2025 财年口径一致。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 全年客户净资金流入 | 698 USD_billion | 698000000000 USD | 2025-01-01 至 2025-12-31 / company_reported_net_flows_including_cash_management | 早期审核样本；完整定义待核 |
| 贝莱德 2025 全年客户资金总流入额 | 3,215 USD_billion | 3215000000000 USD | 2025-01-01 至 2025-12-31 / company_reported_net_flows_including_cash_management | formula_input；2025 全年客户资金总流入（$3,215 billion）；与总流出及净流入 $698B 完整对齐 |
| 贝莱德 2025 全年客户资金总流出额 | 2,502 USD_billion | 2502000000000 USD | 2025-01-01 至 2025-12-31 / company_reported_net_flows_including_cash_management | formula_input；2025 全年客户资金总流出（$2,502 billion）；与净流入 $698B 完整对齐 |
| 贝莱德 2025 全年客户资本返还与分配额 | 15 USD_billion | 15000000000 USD | 2025-01-01 至 2025-12-31 / company_reported_net_flows_including_cash_management | formula_input；2025 全年客户资本返还与分配（$15 billion）；与总流量构成一致 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## asset_management_driver_2 — 匹配收费管理资产

按费率对应资产群

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| asset_management_driver_2__input_1 | 收费资产余额 | 缺失 | 待补 | 无匹配证据 |
| asset_management_driver_2__input_2 | 产品和费率范围 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## asset_management_driver_3 — 基础管理费有效年化率

管理费/匹配平均收费资产

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| asset_management_driver_3__input_1 | 基础管理费 | 缺失 | 待补 | 无匹配证据 |
| asset_management_driver_3__input_2 | 匹配平均收费资产 | 缺失 | 待补 | 无匹配证据 |
| asset_management_driver_3__input_3 | 年化方法 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

