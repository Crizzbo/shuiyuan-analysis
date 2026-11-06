# medical_devices 行业驱动输入表

代表公司：Intuitive Surgical（US:ISRG）。

[统一目录](README.md) · [原始行业字典](../industry-specific/medical_devices.md)

## medical_devices_driver_1 — 分手术产品操作数量

按产品与临床用途记录

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| medical_devices_driver_1__input_1 | 实际手术数量 | 缺失 | 待补 | 无匹配证据 |
| medical_devices_driver_1__input_2 | 系统类型 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## medical_devices_driver_2 — 新增装机及期末装机量

新增和存量装机分开

选用口径：Intuitive Surgical 2025 Q4 达芬奇系统新增投放、期末在用装机量与退役调整数。输入状态：必需输入已齐备。定义状态：company_variant_reviewed。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| medical_devices_driver_2__input_1 | 当期系统 placement | 已绑定 | da_vinci_placements / systems | industry-browser-excerpt:843b690a1ec561085d7624c8c249730d5742b6d6533f563d9aef4839c43e67f0 r1 |
| medical_devices_driver_2__input_2 | 期末 installed base | 已绑定 | da_vinci_installed_base / systems | industry-browser-excerpt:843b690a1ec561085d7624c8c249730d5742b6d6533f563d9aef4839c43e67f0 r1 |
| medical_devices_driver_2__input_3 | 退役调整 | 已绑定 | isrg_tradein_retirements_q4 / systems | industry-browser-excerpt:0f44e0c2971898f558dd7f49cfe4600963e0eeadaebb6f26c243f47b19b4cd67 r1 |

限制：投放 532 台、期末装机 11,106 台、退役置换 79 台；同 2025 Q4 期间与装机量变动平衡对齐。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|
| 季度达芬奇系统投放量 | 532 systems | 532 systems | 2025-10-01 至 2025-12-31 / worldwide_da_vinci_including_leases | 早期审核样本；完整定义待核 |
| 期末达芬奇系统装机存量 | 11,106 systems | 11106 systems | None 至 2025-12-31 / worldwide_da_vinci | 早期审核样本；完整定义待核 |
| 直觉外科 2025 Q4 达芬奇系统置换与退役调整数 | 79 systems | 79 systems | 2025-10-01 至 2025-12-31 / worldwide_da_vinci | formula_input；2025 Q4 达芬奇手术系统置换与退役台数（79 systems）；同 2025 Q4 期间与装机量变化对齐 |

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

## medical_devices_driver_3 — 每匹配系统耗材收入

可比耗材收入/明确装机基数

选用口径：尚未选择经过审核的公司具体口径。输入状态：必需输入尚未绑定。定义状态：definition_review_pending。

| 输入槽位 | 中文名称 | 状态 | 原子观测 / 规范单位 | 来源版本 |
|---|---|---|---|---|
| medical_devices_driver_3__input_1 | 同系统耗材收入 | 缺失 | 待补 | 无匹配证据 |
| medical_devices_driver_3__input_2 | 匹配平均有效装机基数 | 缺失 | 待补 | 无匹配证据 |

限制：尚未绑定全部必需输入；已有观测不证明该份材料之外均未披露。

| 相关观测中文名称 | 原始值及单位 | 规范化值及单位 | 期间 / 范围 | 用途与限制 |
|---|---|---|---|---|

研究闸门：阻断。输入完成不会自动生成估值、交易或六步结论。

