# 市场行情快照标准化与反向估值绑定技术设计规格书 (Market Snapshot & Valuation Binding Spec)

> **功能标识**：`MARKET_SNAPSHOT_NORMALIZATION_AND_VALUATION_BINDING`  
> **所属业务分类**：类别 E：底层数据工程层面（二级行情快照清洗、闭合 Schema 契约校验、52 周价格走廊测算与反向 DCF 估值绑定）  
> **技术成熟度**：生产基准 (Production)  
> **单一事实来源**：  
> - 行情处理核心：`financial_reporting/market_snapshot.py`  
> - 闭合契约定义：`schemas/market-snapshot.schema.json`  
> - 计划配置清单：`config/google-finance-industry-plan.json` 与 `config/google-finance-smoke-plan.json`  
> - 导入命令行程序：`scripts/import_market_snapshot.py`  
> - 自动化测试套件：`scripts/test_market_snapshot.py`  

---

## 一、 功能背景与业务用途

### 1. 业务背景
在买方证券投资体系中，标的市场报价（Price）直接决定了安全边际计算、动态市盈率/市净率乘数及反向现金流折现（Reverse DCF）隐含增长率推导。然而，二级市场报价接入面临四大工程与合规风险：一是“接口鉴权陷阱与费用”，依赖商业实时行情终端成本高昂且凭据易失效；二是“数据污染与幻觉注入”，部分爬虫直接将格式化带逗号文本或伪造时区的字符串注入计算引擎导致崩溃；三是“时效与时区漂移”，将盘前/盘后非流动性成交或前一交易日收盘价直接误作实时盘中价；四是“未知字段膨胀”，未经严格模式校验的行情响应容易携带冗余字段破坏序列化。本规范确立受控二级行情接入快照标准化流水线、闭合 JSON Schema 刚性拦截、52 周区间几何解耦与反向估值绑定标准。

### 2. 核心用途
本功能解决全系统三大行情接入与估值桥梁工程问题：
1. **闭合式强类型行情快照 (Closed Schema Contract)**：遵循 `schemas/market-snapshot.schema.json`，启用 `additionalProperties: false`，杜绝任何未经声明的脏字段注入系统；
2. **52 周价格空间解耦与异常截断**：在严格验证现价落在 52 周极值区间内（$\text{low52} \le P \le \text{high52}$）的前提下，精确计算距高点回撤比率与区间归一化位置；
3. **安全隔离的反向 DCF 估值桥梁**：仅将清洗后的有效现价注入 `reverse_dcf.target_price`，其他财务参数强制要求独立的本地证据供给，严禁从行情数据反推财务指标。

---

## 二、 系统架构上下文与依赖关系

### 1. 前置依赖 (Inputs From Upstream)
- `data/google-finance/raw/`：提供经 SHA-256 哈希锁定的宿主 MCP 二级行情原始响应 JSON。
- `config/google-finance-industry-plan.json`：提供 41 行业代表公司的确切表格行号与证券映射计划。

### 2. 后置消费 (Outputs To Downstream)
- `data/google-finance/normalized/`：落盘只追加的标准化行情快照。
- `financial_core/engines/valuation_engine.py`：消费标准行情快照执行反向 DCF 与隐含增长率求解。
- `reports/excel_dossiers/`：将标准化现价与 52 周走廊写入 5-Sheet Excel Sheet 1 决策看板。

### 3. 数据流转时序图
```
┌──────────────────────────────────────┐
│  宿主已授权只读 MCP 采集原始响应     │
└──────────────────┬───────────────────┘
                   │ (提取 raw JSON 并记录 SHA-256)
                   ▼
┌──────────────────────────────────────┐
│  行情标准化中枢 (market_snapshot.py) │
│  ├── 坐标与表格身份一致性核验        │
│  ├── 字段格式与数值有限性校验        │
│  ├── 52 周区间位置与跌幅测算         │
│  └── 闭合契约验证 (Draft 2020-12)    │
└──────────────────┬───────────────────┘
                   │ (合规纯净快照包)
                   ▼
┌──────────────────────────────────────┐
│  反向 DCF 估值绑定与多模态研报消费   │
└──────────────────────────────────────┘
```

---

## 三、 输入参数契约说明 (Input Contracts)

行情字段解析与标准化接口核心入参规范如下表：

### 1. 核心字段契约对照表
| 字段标识 | 数据类型 | 计量单位 | 约束边界 | 业务含义与说明 |
| :--- | :---: | :---: | :---: | :--- |
| `price` | `float` | 货币/股 | $> 0.0$ 且有限值 | 标的最近交易价格或基准收盘价。 |
| `currency` | `str` | ISO-4217 | 3位大写字母 | 交易计价法定货币代码（如 `USD`, `JPY`）。 |
| `marketcap`| `float` | 货币总额 | $\ge 0.0$ | 企业流通市值规模。 |
| `volume` | `float` | 股数/手 | $\ge 0.0$ | 当日累计成交量（保留真实 0）。 |
| `high52` | `float` | 货币/股 | $> 0.0$ 且 $\ge \text{low52}$ | 过去 52 周盘中最高成交价格。 |
| `low52` | `float` | 货币/股 | $> 0.0$ 且 $\le \text{high52}$ | 过去 52 周盘中最低成交价格。 |
| `datadelay`| `float` | 分钟 | $\ge 0.0$ | 交易所数据源延迟时长（分钟）。 |

---

## 四、 核心业务逻辑与数学计算模型

### 1. 强制规范图表 (Mandatory Diagrams)

#### 图 E-1：行情快照标准化与闭合契约验证拓扑图
```
┌────────────────────────────────────────────────────────┐
│             【原始 Google Sheets 行情单元格】          │
│  userEnteredValue: "=GOOGLEFINANCE($A2, "price")"      │
│  effectiveValue: { numberValue: 140.50 }              │
└───────────────────────────┬────────────────────────────┘
                            │ (坐标与公式校验)
                            ▼
┌────────────────────────────────────────────────────────┐
│             【单元格字段状态机清洗】                   │
│  • formula_mismatch: 公式被篡改或不匹配                 │
│  • provider_error: 上游返回 #N/A 或授权拒绝             │
│  • ok: 格式匹配且数值有限，提纯为标量                   │
└───────────────────────────┬────────────────────────────┘
                            │ (装配标准化 Quote 对象)
                            ▼
┌────────────────────────────────────────────────────────┐
│             【闭合式快照契约验证 (Closed Schema)】     │
│  • 验证: additionalProperties == false                 │
│  • 校验: 52 周价格区间单调性 (low52 <= price <= high52) │
│  • 绑定: 注入 reverse_dcf 计算并锁定哈希               │
└────────────────────────────────────────────────────────┘
```

#### 图 E-2：原始报文坐标核对与反向估值注入时序图
```
  调度器 (import_market_snapshot.py)
    │
    ├─► [加载原始报文与计划配置] ──> 核验 spreadsheet_id 与 sheet_name
    │
    ├─► [重叠坐标检测] ──> 断言不存在 (row, col) 物理碰撞
    │
    ├─► [逐证券提纯] ──> 解析 price, high52, low52, currency
    │     │
    │     ├─► [52周走廊校验] ──> 测算 drop_from_52w_high 与 position_52w
    │     │
    │     └─► [反向估值绑定] ──> 若提供 valuation_request，仅注入 target_price
    │
    └─► [落盘标准快照] ──> 写入 data/google-finance/normalized/{hash}.json
```

#### 图 E-3：行情有效性与 52 周走廊区间判定决策树
```
                   ┌─────────────────────────┐
                   │    行情字段提取输入     │
                   └────────────┬────────────┘
                                │
                 单元格有效值是否为正常数值且有限?
                                ├──────────────────────── 否 ──► 【STATUS: INVALID_VALUE / PROVIDER_ERROR】
                                │                                  (记录上游错误码，字段置空)
                                ▼ 是
                 price 是否严格落在 [low52, high52] 之间?
                                ├──────────────────────── 否 ──► 【RANGE_STATUS: INCONSISTENT_RANGE】
                                │                                  (数据源区间破损，拒绝生成位置指标)
                                ▼ 是
                   ┌─────────────────────────┐
                   │  【RANGE_STATUS: OK】   │
                   │  计算距高点跌幅与区间分位│
                   │  允许注入反向 DCF 求解  │
                   └─────────────────────────┘
```

---

### 2. 核心数学模型推导

1. **距 52 周最高点回撤比率方程**：
   $$\text{Drawdown}_{52w} = 1.0 - \frac{P}{\text{High}_{52w}}$$
   约束要求：当且仅当 $P > 0$ 且 $\text{High}_{52w} \ge P$ 时计算，产出正值回撤小数（如 $0.15$ 表示距高点回调 $15\%$）。
2. **52 周价格相对位置归一化分位数方程**：
   $$\text{Position}_{52w} = \frac{P - \text{Low}_{52w}}{\text{High}_{52w} - \text{Low}_{52w}}$$
   定义域断言：$\text{High}_{52w} > \text{Low}_{52w}$，且输出 $\text{Position}_{52w} \in [0.0, 1.0]$。
3. **反向 DCF 目标价格绑定方程**：
   $$P_{\text{target}} \equiv P_{\text{quote, normalized}}$$
   严禁在未获得经审计财报底账前根据市盈率逆推伪造现金流。

---

## 五、 状态机与字段生命周期 (Field Lifecycle)

### 1. 行情字段解析状态空间

| 状态代号 | 英文枚举标识 | 中文状态名称 | 判定特征 | 系统动作 |
| :--- | :--- | :--- | :--- | :--- |
| `FLD_01` | `ok` | 正常可用态 | 公式完全匹配且有效数值有限合法。 | 允许直接参与估值与看板计算。 |
| `FLD_02` | `missing` | 字段缺失态 | 单元格无有效值或公式未配置。 | 字段置空，标记缺失。 |
| `FLD_03` | `provider_error` | 上游异常态 | 返回 `#N/A`、`#REF!` 或权限拒绝。| 保留原始错误信息，阻断引用。 |
| `FLD_04` | `formula_mismatch`| 公式错配态 | 单元格公式被非预期公式篡改覆盖。| 抛出安全异常并阻断整批导入。 |
| `FLD_05` | `invalid_value` | 非法数值态 | 数值包含 `NaN`、`Inf` 或负价格。 | 拦截计算，记录数据源瑕疵。 |

---

## 六、 返回值与输出数据结构 (Output Contracts)

行情标准化完成后，输出闭合结构化快照记录：

```json
{
  "schema_version": "1.0.0",
  "source_kind": "secondary",
  "source_id": "google_finance_sheets",
  "source_path": "data/google-finance/raw/20261011T095029Z.json",
  "source_sha256": "4a7b8c...64位十六进制",
  "acquired_at": "2026-10-11T09:50:29+00:00",
  "spreadsheet_id": "1A2B3C...GoogleSheetID",
  "sheet_name": "IndustryQuotes",
  "spreadsheet_timezone": "America/New_York",
  "quotes": [
    {
      "ticker": "NVDA",
      "name": "NVIDIA Corporation",
      "industry_id": "ind_semiconductors",
      "market": "US",
      "row": 2,
      "fields": {
        "price": { "value": 140.50, "unit": "currency_per_share", "status": "ok" },
        "currency": { "value": "USD", "unit": "currency_code", "status": "ok" },
        "high52": { "value": 150.00, "unit": "currency_per_share", "status": "ok" },
        "low52": { "value": 75.60, "unit": "currency_per_share", "status": "ok" }
      },
      "quote_status": "ok",
      "freshness_status": "previous_close_baseline",
      "trade_timezone_status": "calendar_review_required"
    }
  ]
}
```

### 输出字段逐项业务释义
| 输出字段名称 | 字段标识 | 数据类型 | 计量单位 | 业务释义 |
| :--- | :--- | :---: | :---: | :--- |
| 来源性质 | `source_kind` | `str` | 常量 | 声明为 `secondary` 二级行情来源。 |
| 采集时点 | `acquired_at` | `str` | ISO-8601 | 包含明确时区的物理采集完成时点。 |
| 标的行情状态 | `quote_status` | `str` | 枚举字符串 | 标的核心报价是否全部合法可用（`ok`）。 |
| 行情新鲜度状态 | `freshness_status` | `str` | 枚举字符串 | 标的当前处于的交易时段状态。 |
| 时区核验状态 | `trade_timezone_status`| `str` | 枚举字符串 | 交易所日历与时区核验审查状态。 |

---

## 附录：工程实现与边界自查清单 (Engineering Defense Checklist)

- [ ] **严禁伪造不存在的时区时刻**：采集时间必须具备原始时区，严禁机械将未确认时区的交易时间转为 UTC 时间。
- [ ] **严格的闭合式 Schema 校验**：生产的快照文件必须通过 `schemas/market-snapshot.schema.json` 强校验，严禁包含任何未知扩展字段。
- [ ] **52 周区间绝对单调性断言**：当且仅当满足 $\text{low52} \le P \le \text{high52}$ 时才允许测算区间位置，出现倒挂必须标记 `inconsistent_range`。
- [ ] **反向估值单向注入保护**：反向 DCF 绑定仅允许将 `price` 注入 `target_price`，严禁由行情倒推任何资产负债表与现金流科目。
- [ ] **只追加不物理覆盖**：重新导入或更新行情快照必须新建带时间戳的文件名，严禁物理覆盖已归档的历史快照文件。
