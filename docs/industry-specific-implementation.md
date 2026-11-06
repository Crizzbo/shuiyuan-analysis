# 行业专属指标工程实现与样本验证技术设计规格书 (Industry-Specific Metrics Implementation Spec)

> **功能标识**：`INDUSTRY_SPECIFIC_METRICS_IMPLEMENTATION_SPEC`  
> **所属业务分类**：类别 B：中观行业存量博弈与增量产出（41 个细分行业专属胜负手指标、123 个行业驱动采集规格、高精度 Decimal 单位归一化与原子物理量隔离存储）  
> **技术成熟度**：生产基准 (Production)  
> **单一事实来源**：  
> - 专属指标核心：`financial_reporting/industry_specific.py`  
> - 闭合 Schema 契约：`schemas/industry-specific-specifications.schema.json`  
> - 行业规格底账：`knowledge/metrics/industry-specifications.json`  
> - 驱动输入统一目录：`knowledge/metrics/README.md`  
> - 规格生成脚本：`scripts/build_industry_specific_specs.py`  
> - 样本登记脚本：`scripts/register_industry_specific_samples.py`  
> - 契约更新脚本：`scripts/update_industry_specific_contracts.py`  
> - 覆盖报告生成器：`scripts/build_industry_sample_coverage.py`  
> - 自动化测试套件：`scripts/test_industry_specific.py`  

---

## 一、 功能背景与业务用途

### 1. 业务背景
在买方证券研究中，通用会计科目（如营业收入、净利润、总资产）无法刻画不同产业特有的商业模式胜负手。例如：半导体资本开支与晶圆出货量、航空运输的每客英里收益与可用座英里（ASM）、云计算的净收入留存率（NDR）与年度经常性收入（ARR）、银行的管理税当量净息差（NIM）等。传统量化系统处理此类数据时常出现四大系统性缺陷：一是“浮点失真”，直接使用 IEEE 754 二进制浮点数计算金额产生舍入误差；二是“量纲偷换”，将客英里、座次、用户数等物理量强制混入货币科目引发单位错位；三是“复合项滥用伪评分”，在底层数据缺失时擅自赋权合成综合评分；四是“缺乏样本隔离”，将单一样本公司的特异性指标误当成全行业标准规范。本规范确立 41 细分行业 123 个核心驱动的采集规格、十进制 Decimal 精度控制、物理量独立存储架构与只读核验流水线。

### 2. 核心用途
本功能解决全系统三大行业特异性量化工程问题：
1. **41 细分行业 123 个专属驱动规格定界**：明确每个行业代表公司的采集条件、法定物理单位、复合字段与严禁替代项，输出闭合的 `industry-specific-specifications` 结构体；
2. **高精度 Decimal 归一化与单位白名单转换**：使用 Python `Decimal` 进行数值缩放与百分比转化，杜绝浮点精度丢失；引入严格的物理单位白名单（如美分转美元、座英里换算），杜绝非法单位污染；
3. **财务货币与非标物理量严格物理隔离**：建立独立的原子样本存储结构，严禁将装机量、会员数、航线客运量等非货币物理量混入三表财务底账。

---

## 二、 系统架构上下文与依赖关系

### 1. 前置依赖 (Inputs From Upstream)
- `data_sources/official_filings/`：提供具备 SHA-256 哈希锁定的官方经审计原始披露文件（如 10-K/20-F/有価証券報告書）。
- `data/catalog/`：提供不可变内容寻址的原子观测与来源快照。
- `knowledge/metrics/industry-specifications.json`：提供 41 细分行业基础知识库契约。

### 2. 后置消费 (Outputs To Downstream)
- `knowledge/metrics/driver-inputs/`：生成 41 份结构化行业驱动分表与统一目录。
- `data/financial/industry-specific-verification.json`：发布行业专属指标实测核验结果底账。
- `data/browser-search/industry-specific-jobs.json`：输出缺失驱动的定向 AI 浏览器补数任务清单。

### 3. 数据流转时序图
```
┌──────────────────────────────────────┐
│  官方原件披露与可见页面人工核验摘录  │
└──────────────────┬───────────────────┘
                   │ (提取非标原始观测与页码定位)
                   ▼
┌──────────────────────────────────────┐
│  专属指标处理中枢 (industry_specific)│
│  ├── 规格生成 (build_specs)          │
│  ├── 样本登记 (register_samples)     │
│  ├── Decimal 十进制单位归一化        │
│  └── 契约引用更新 (update_contracts) │
└──────────────────┬───────────────────┘
                   │ (执行闭合 Schema 契约核验)
                   ▼
┌──────────────────────────────────────┐
│  生成 41 行业分表与未覆盖补数任务    │
└──────────────────────────────────────┘
```

---

## 三、 输入参数契约说明 (Input Contracts)

行业专属指标实体核心字段字典与约束规范如下表：

### 1. 核心实体契约对照表
| 字段标识 | 数据类型 | 计量单位 | 约束边界 | 业务含义与说明 |
| :--- | :---: | :---: | :---: | :--- |
| `industry_id` | `str` | 41行业代码 | 规范命名 | 41 内部研究行业分类唯一代号（如 `ind_semiconductors`）。|
| `metric_id` | `str` | 字符串 | 规范命名 | 专属驱动唯一业务键（如 `pct_cloud_ndr`）。 |
| `driver_name_zh` | `str` | 中文字符串 | 非空描述 | 核心驱动的自然中文业务名称。 |
| `allowed_units` | `List[str]` | 字符串列表 | 单位白名单 | 允许采纳的法定物理或货币计量单位（如 `USD`, `percent`）。|
| `decimal_places` | `int` | 整数 | $\ge 0$ | 该指标法定的十进制小数保留精度。 |
| `prohibited_substitutes_zh` | `List[str]` | 中文列表 | 非空列表 | 明确严禁用于粗暴替代该驱动的通用科目清单。 |
| `sample_company` | `str` | 股票代码/简称 | 真实标的 | 承担口径验证与样本采样的代表性企业。 |
| `observation_status` | `str` | 枚举字符串 | 3 态枚举 | 该专属指标在知识库中的实际观测覆盖状态。 |

---

## 四、 核心业务逻辑与数学计算模型

### 1. 强制规范图表 (Mandatory Diagrams)

#### 图 B-1：专属指标规格、样本与驱动台账多层拓扑图
```
┌────────────────────────────────────────────────────────┐
│             【IndustrySpecifications 全局规格库】      │
│  • 41 个行业板块、123 个核心胜负手驱动                 │
│  • 声明 allowed_units 白名单与禁止替代科目             │
└───────────────────────────┬────────────────────────────┘
                            │ (1 对多展开为专属指标)
                            ▼
┌────────────────────────────────────────────────────────┐
│             【IndustrySpecificMetric 专属指标对象】    │
│  • metric_id: "pct_aviation_passenger_yield"           │
│  • representative_ticker: "DAL" (达美航空样本)         │
└───────────────────────────┬────────────────────────────┘
                            │ (高精度归一化与单位换算)
                            ▼
┌────────────────────────────────────────────────────────┐
│             【Atomic Observation 原子物理量观测】      │
│  • numeric_value: Decimal("18.42") (美分)              │
│  • normalized_value: Decimal("0.1842") (美元/客英里)   │
│  • unit: "USD_per_RPM" (严禁直接塞入三表货币科目)      │
└────────────────────────────────────────────────────────┘
```

#### 图 B-2：样本登记、Decimal 提纯与双向验签时序图
```
  AI 浏览器人工核验摘录
    │
    ├─► [提取原始数值与单位文本] ──> 例如: "18.42 cents"
    │
    ├─► [单位白名单校验] ──> 匹配 "cents" -> 转换比率 Decimal("0.01")
    │
    ├─► [高精度数值转换] ──> Standardized = Decimal("18.42") * Decimal("0.01")
    │
    ├─► [物理证据 SHA-256 锁定] ──> 建立不可变内容寻址 .blob
    │
    ├─► [重新读取与一致性反向断言] ──> 校验存储值与原原件完全自洽
    │
    └─► [发布至行业验证底账] ──> 更新 data/financial/industry-specific-verification.json
```

#### 图 B-3：行业专属指标准入与计算准备度判定决策树
```
                   ┌─────────────────────────┐
                   │    行业专属指标核验     │
                   └────────────┬────────────┘
                                │
                 上报单位是否落在法定 allowed_units 白名单内?
                                ├──────────────────────── 否 ──► 【UNIT_PROHIBITED_ERROR】(阻断：单位非法)
                                ▼ 是
                 是否试图使用禁止替代项 (如用收入增幅替代NDR)?
                                ├──────────────────────── 是 ──► 【SUBSTITUTE_VIOLATION_ERROR】(阻断：口径偷换)
                                ▼ 否
                 各必需输入槽位是否已全部采齐并经 Decimal 归一化?
                                ├──────────────────────── 否 ──► 【OBSERVATION_PARTIAL】(保持局部样本，阻断计算)
                                ▼ 是
                   ┌─────────────────────────┐
                   │ 【SAMPLE_VERIFIED: OK】 │
                   │  样本通过核验并锁定台账 │
                   │  六步研究闸门保持 blocked│
                   └─────────────────────────┘
```

---

### 2. 核心数学模型推导

1. **十进制高精度尺度转换方程**：
   $$V_{\text{normalized}} = \text{Decimal}(S_{\text{raw}}) \times \text{Decimal}(M_{\text{unit\_factor}})$$
   严禁使用二进制 `float` 进行跨单位缩放，所有因子转换必须基于 Python `Decimal`。
2. **客运收益率 (Passenger Yield) 物理量方程**：
   $$Y = \frac{\text{Passenger Revenue (USD)}}{\text{Revenue Passenger Miles (RPM)}} \quad (\text{USD / RPM})$$
   分母客英里数严禁使用可售座英里（ASM）混淆，且属于独立物理量，严禁记入总资产或应收账款。
3. **净收入留存率 (Net Dollar Retention, NDR) 跨期动态方程**：
   $$NDR_t = \frac{\text{ARR}_{t-1, \text{existing}} + \text{Expansion} - \text{Contraction} - \text{Churn}}{\text{ARR}_{t-1, \text{existing}}} \times 100\%$$
   分子仅统计期初同一批客户在期末的收入贡献，严禁混入当期新增客户（New Logos）产生的 ARR。

---

## 五、 状态机与生命周期 (Metric Lifecycle)

### 1. 行业专属指标状态空间

| 状态代号 | 英文枚举标识 | 中文状态名称 | 判定特征 | 系统动作 |
| :--- | :--- | :--- | :--- | :--- |
| `SPC_01` | `SPEC_DEFINED` | 规格已定界 | 行业已指定代表公司与指标规格，尚无实测样本。 | 派发 AI 浏览器补数任务。 |
| `SPC_02` | `SAMPLE_REGISTERED`| 样本已核验 | 代表公司原子观测已录入，通过 Decimal 单位换算。| 记入样本库，更新台账。 |
| `SPC_03` | `INPUTS_PARTIAL` | 输入部分齐备 | 驱动所需槽位部分录入，尚未达到完整计算门槛。| 维持阻断状态，列入缺口。 |
| `SPC_04` | `INPUTS_COMPLETE`| 输入全部采齐 | 全部必需输入槽位均已绑定有效证据。 | 允许推进业务口径法证审核。|
| `SPC_05` | `GATE_BLOCKED` | 闸门刚性阻断 | 未完成大规模历史样本统计校准。 | 严禁输出定量买卖点。 |

---

## 六、 返回值与输出数据结构 (Output Contracts)

行业专属指标核验完成后，发布全局验证底账 JSON 契约：

```json
{
  "schema_version": "1.0.0",
  "verified_at": "2026-10-11T12:00:00Z",
  "summary": {
    "total_industries": 41,
    "total_drivers": 123,
    "observed_industries": 29,
    "total_observations": 81,
    "calculation_ready_drivers": 7,
    "research_gate_blocked": 123
  },
  "metrics": [
    {
      "metric_id": "pct_aviation_passenger_yield",
      "industry_id": "ind_aviation_transport",
      "driver_name_zh": "客运收益率 (Yield)",
      "sample_company": "DAL",
      "raw_value_str": "18.42",
      "raw_unit": "cents",
      "normalized_value": 0.1842,
      "normalized_unit": "USD_per_RPM",
      "status": "sample_verified",
      "research_gate": "blocked"
    }
  ]
}
```

### 输出字段逐项业务释义
| 输出字段名称 | 字段标识 | 数据类型 | 计量单位 | 业务释义 |
| :--- | :--- | :---: | :---: | :--- |
| 总覆盖行业数 | `total_industries` | `int` | 整数 | 系统纳管的 41 个内部细分行业总数。 |
| 核心胜负手总数 | `total_drivers` | `int` | 整数 | 全系统定义的行业胜负手驱动总数（123 个）。|
| 已观测行业数 | `observed_industries` | `int` | 整数 | 已至少录入 1 项有效代表样本的细分行业数。|
| 观测记录总数 | `total_observations` | `int` | 整数 | 经官方披露人工核验的原子物理量观测总数。|
| 可计算驱动数 | `calculation_ready_drivers`| `int` | 整数 | 槽位采齐且口径经法证审核的专属驱动总数。|
| 闸门阻断数 | `research_gate_blocked` | `int` | 整数 | 处于阻断状态的研究闸门总数（刚性 123）。 |

---

## 附录：工程实现与边界自查清单 (Engineering Defense Checklist)

- [ ] **严禁使用浮点数进行金额与量纲折算**：所有单位换算与数值缩放必须使用 Python `Decimal`，严禁直接使用 `float` 乘除。
- [ ] **物理量严禁污染会计科目**：装机量、会员数、客英里等物理指标必须独立存储在专属样本库中，严禁混入资产负债表与利润表科目。
- [ ] **复合字段严禁粗暴合成综合评分**：在底层原子槽位未完全采齐前，严禁通过经验权重合成虚假的行业综合景气度或健康度得分。
- [ ] **严禁禁止替代项越界充数**：必须严格拦截使用通用科目替代专属指标的行为（例如严禁使用营业利润率替代商业银行 NIM）。
- [ ] **样本更新幂等与不可篡改**：重复执行样本登记脚本必须能够复用既有不可变对象；追加新内容时必须生成带时间戳的新快照。
