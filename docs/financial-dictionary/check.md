# 财务勾稽结果

| 字段代码 | 中文名称 | 类型 | 必填 | 业务含义 |
| --- | --- | --- | --- | --- |
| `check` | 校验代码 | string | 是 | 资产负债平衡、现金流合计或现金存量流量桥接 |
| `group` | 同口径分组 | array | 是 | 依次为期间 JSON、范围、会计准则和币种 |
| `status` | 校验状态 | string | 是 | incomplete 不等于通过，failed 阻断涉及事实 |
| `residual` | 勾稽残差 | string | 条件必填/可选 | 有完整输入时的基础币种十进制残差 |
| `tolerance` | 允许舍入误差 | string | 条件必填/可选 | 完整输入各舍入容差合计 |
| `fact_refs` | 输入事实引用 | array | 条件必填/可选 | 完整校验涉及的事实 ID |
| `missing_fields` | 缺失字段 | array | 条件必填/可选 | 不完整校验所缺字段或端点标识 |

字段与 `schemas/financial-report.schema.json` 同源生成；对象数组的具体运行结果见 14 功能设计。
