# 多资产横向拓展流水线与 4-Sheet 联动工作簿技术设计规格书 (Multi-Asset Pipeline & 4-Sheet Excel Specification)

> **功能标识**：`PIPELINE_MULTI_ASSET_WORKBOOK_BUILDER`  
> **所属业务分类**：类别 E：底层数据工程层面（多资产综合调度、4-Sheet Excel 报表建造与多模态交付）  
> **技术成熟度**：生产基准 (Production)  
> **单一事实来源**：  
> - 流水线调度器：`scripts/run_multi_asset_research_pipeline.py`  
> - 工作簿建造器：`financial_reporting/excel_multi_asset_builder.py` (`ExcelMultiAssetReportBuilder`)  
> - ETF 穿透中枢：`financial_reporting/etf_penetration.py`  
> - 黄金大宗框架：`financial_reporting/commodity_gold_framework.py`  
> - 自动化测试集：`scripts/test_excel_dossier_builder.py`、`scripts/test_cross_asset_engine.py`  

---

## 一、 功能背景与业务用途

### 1. 业务背景
在跨资产投资管理中，单一股票基本面档案无法满足机构多资产配置对宽基指数、行业主题 ETF、实物商品（黄金）以及高成长前沿标的的跨品类穿透对比需求。传统人工制作的多资产报表往往格式各异、公式割裂，且极易出现底层持仓过度集中的隐性风险。本功能构建由自动化批处理调度驱动的多资产投研管线，直接输出符合 FAST Standard 与 CFI 金融色彩规范的买方 4-Sheet 联动 Excel 深度投研报告书。

### 2. 核心用途
本功能解决三大报表交付与分析工程问题：
1. **跨资产大类自动化编排与对齐**：统一编排核心指数 ETF、实物黄金宏观估值模型、高价值成长股现金跑道以及 41 细分行业宏观因果图谱；
2. **买方 4-Sheet 联动 Excel 物理建造**：严格按照金融建模规范构建 4 大专业工作表，支持自适应列宽、首行首列冻结及底层跨表计算公式注入；
3. **文本洁净度与工程稳健性保障**：对所有进入工作簿的自然语言实施正则物理清洗，剔除 Emoji 表情符号，采用 `.tmp` 原子替换机制杜绝生成破损文件。

---

## 二、 系统架构上下文与依赖关系

### 1. 前置依赖 (Inputs From Upstream)
- `financial_core/engines/cross_asset_engine.py`：提供 ETF 穿透重叠度数据与黄金宏观定价中枢。
- `financial_core/engines/causal_inference_engine.py`：提供 41 细分行业宏观驱动事实清单。
- `data/macro/market_rates_snapshot.json`：提供基准收益率与宏观流动性指标。

### 2. 后置消费 (Outputs To Downstream)
- `reports/multi_asset_reports/`：落盘带时间戳的买方 4-Sheet 联动投研工作簿 (`.xlsx`)。
- `financial_core/engines/prediction_ledger.py`：消费多资产配置结论，写入不可篡改哈希时间链条。

### 3. 数据流转时序图
```
┌──────────────────────────────────────┐
│  ETF 全量成分、黄金利率锚与成长股事实 │
└──────────────────┬───────────────────┘
                   │ (强类型分析数据对象)
                   ▼
┌──────────────────────────────────────┐
│  多资产流水线调度器与 Excel 建造中枢  │
│  ├── 资产类别切片与数据聚合          │
│  ├── 4-Sheet 单元格网格与公式注入     │
│  └── 文本 Emoji 清洗与 FAST 样式渲染 │
└──────────────────┬───────────────────┘
                   │ (.tmp 写入与原子覆盖)
                   ▼
┌──────────────────────────────────────┐
│  买方机构级 4-Sheet 联动工作簿文件   │
│  ({YYYY-MM-DD}_多资产横向拓展深度.xlsx)│
└──────────────────────────────────────┘
```

---

## 三、 输入参数契约说明 (Input Contracts)

流水线执行与建造器调度核心输入参数定义如下表：

| 方法标识 | 参数名称 | 数据类型 | 计量单位 | 约束边界 | 业务释义 |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `run_pipeline`| `str_target_date` | `str` | ISO-8601日期 | `YYYY-MM-DD` | 报告生成的基准业务交易日。 |
| `run_pipeline`| `bool_use_cache` | `bool` | 布尔开关 | True / False | 是否复用已清洗的 ETF 成分持仓与宏观利率缓存。 |
| `build_sheet0`| `list_etf_records`| `List[dict]` | 结构化列表 | 长度 $\ge 1$ | 核心宽基与行业 ETF 全息指标及前十大持仓列表。 |
| `build_sheet1`| `dict_gold_data` | `dict` | 字典映射 | 非空键值对 | 黄金宏观三态公允估值与特级金矿股 AISC 成本数据。 |
| `build_sheet2`| `list_growth_stocks`| `List[dict]` | 结构化列表 | 长度 $\ge 1$ | 高价值成长股决策总表，包含现金跑道与击球买点。 |
| `build_sheet3`| `dict_industry_41`| `dict` | 字典映射 | 41个键值对 | 41 细分行业周期敏感度与胜负手因果驱动图谱。 |

---

## 四、 核心业务逻辑与数学计算模型

### 1. 强制规范图表 (Mandatory Diagrams)

#### 图 E-1：4-Sheet 多资产工作簿架构与单元格映射拓扑图
```
┌────────────────────────────────────────────────────────────────────────┐
│                   【买方 4-Sheet 多资产联动工作簿】                    │
├────────────────────────────────────────────────────────────────────────┤
│ Sheet 0: [00_ETF穿透与持仓重叠度]                                      │
│  ├── 宽基与主题 ETF 全景总表 (AUM、费率、CR10 集中度)                  │
│  ├── 前十大持仓加权重叠度矩阵 (揭示被动重仓与伪分散风险)               │
│  └── 1年/3年/5年费率复利摩擦损耗测算表 (Drag_T 侵蚀金额)                │
├────────────────────────────────────────────────────────────────────────┤
│ Sheet 1: [01_黄金与大宗商品宏观估值]                                   │
│  ├── 黄金公允中枢 (TIPS 利率锚 + 主权去美元化常态溢价)                 │
│  ├── 三态估值走廊 (紧缩防守底 $2,250、公允靶心 $2,650、地缘高弹 $2,950)│
│  └── 特级金矿股全息台账 (NEM, GOLD, AEM, AISC 维持成本与现金流杠杆)   │
├────────────────────────────────────────────────────────────────────────┤
│ Sheet 2: [02_高价值成长股决策走廊]                                     │
│  ├── AI算力与先锋龙头总表 (PLTR, ARM, VRT, CRWD, ASTS 决策矩阵)        │
│  ├── 硬跑道现金流保障期 (Cash Runway 支撑月数与低位增发稀释红线)        │
│  └── 核心催化与下行破位黑天鹅事实清单                                  │
├────────────────────────────────────────────────────────────────────────┤
│ Sheet 3: [03_全量41细分行业因果图谱]                                   │
│  └── 41 行业宏观敏感度评级、核心投入品风险与生命周期驱动因子全景图谱    │
└────────────────────────────────────────────────────────────────────────┘
```

#### 图 E-2：多资产流水线端到端生成与原子写入时序图
```
  时间轴
    │
    ├─► [启动流水线] ──> 解析命令行日期与环境探测 (env_discovery.py)
    │
    ├─► [数据装配阶段]
    │    ├── 运行 etf_penetration.py ──> 产出持仓重叠矩阵
    │    ├── 运行 commodity_gold_framework.py ──> 产出黄金三态与 AISC
    │    └── 提取行业与成长股因果策略 ──> 装配事实清单
    │
    ├─► [Excel 建造阶段]
    │    ├── 实例化 ExcelMultiAssetReportBuilder
    │    ├── 顺序填充 Sheet 0 至 Sheet 3 (FAST 色彩与网格线)
    │    └── 写入物理临时文件 .tmp
    │
    └─► [原子替换落盘] ──> os.replace 覆盖至正式目标路径
```

#### 图 E-3：高成长企业硬跑道与安全边际状态机
```
                   ┌─────────────────────────┐
                   │    成长股现金流健康     │
                   │  (Runway >= 24 个月)    │
                   └────────────┬────────────┘
                                │
                 净造血能力恶化 (OCF 持续净流出)?
                                │
                                ▼
                   ┌─────────────────────────┐
                   │    预警进入承压区间     │
                   │ (12 <= Runway < 24 个月)│
                   └────────────┬────────────┘
                                │
                 现金硬跑道跌破 12 个月红线?
                                ├──────────────────────── 否 ──► 维持观察
                                │
                                ▼ 是
                   ┌─────────────────────────┐
                   │  触发低位折价定增报警   │
                   │   (STATUS: RUNWAY_RED)  │
                   └─────────────────────────┘
```

---

### 2. 核心数学模型推导

1. **复利费率摩擦损耗方程**：
   $$\text{Drag}_T = 1 - (1 - \text{TER})^T$$
   其中 $\text{TER}$ 为基金总费率比率，$T \in \{1, 3, 5\}$ 为投资持有年限。
2. **高成长企业硬跑道现金流保障期 (Runway)**：
   $$\text{Cash Runway (Months)} = \frac{\text{Cash} + \text{Short-Term Investments}}{\max(|\text{Operating Cash Burn}|, \; 1.0)} \times 12$$
3. **金矿龙头综合营运杠杆放大倍数**：
   $$\text{Leverage Multiplier} = \frac{\text{Spot Price}}{\text{Spot Price} - AISC}$$
4. **成长股击球买点安全边际率**：
   $$\text{Margin of Safety} = \frac{\text{Fair Target Price} - P_{\text{current}}}{P_{\text{current}}} \times 100\%$$

---

## 五、 状态机与标的流转生命周期 (State Registry)

### 1. 成长股现金跑道与买点信号状态空间

| 状态代号 | 英文枚举标识 | 中文状态名称 | 判定条件 | 投研决策动作 |
| :--- | :--- | :--- | :--- | :--- |
| `GROW_01` | `STRIKE_ZONE_BUY` | 优质击球区买点 | 现价低于悲观底线且跑道 $> 24$ 个月。 | 建议分批建仓，安全边际充足。 |
| `GROW_02` | `FAIR_HOLD` | 公允持有观察 | 现价处于保守中性与悲观底线之间。 | 维持已有底仓，暂不追高。 |
| `GROW_03` | `OVEREXTENDED` | 估值过热透支 | 现价高于乐观靶心目标价。 | 建议止盈落袋，防范均值回归。 |
| `GROW_04` | `RUNWAY_DEFICIT` | 现金跑道告急 | 扣除负债后可用现金跑道 $< 12$ 个月。 | 警惕低位折价定增稀释风险。 |

---

## 六、 返回值与输出数据结构 (Output Contracts)

流水线执行完毕后，统一输出物理落盘摘要契约：

```json
{
  "report_date": "2026-10-18",
  "status_execution": "COMPLETED",
  "path_excel_report": "reports/multi_asset_reports/2026-10-18/2026-10-18_多资产横向拓展深度投研报告书.xlsx",
  "summary_metrics": {
    "cnt_etf_analyzed": 10,
    "pct_max_overlap_detected": 0.468,
    "gold_fair_value_anchor": 2650.0,
    "cnt_growth_stocks_covered": 8,
    "cnt_industries_mapped": 41
  },
  "hash_sha256": "5c9d2e...64位十六进制"
}
```

### 输出字段逐项业务释义
| 输出字段名称 | 字段标识 | 数据类型 | 计量单位 | 业务释义 |
| :--- | :--- | :---: | :---: | :--- |
| 报告基准日期 | `report_date` | `str` | YYYY-MM-DD | 报告书构建与市场行情切片日期。 |
| 工作簿落盘路径 | `path_excel_report` | `str` | 相对文件路径 | 4-Sheet Excel 报表在项目内的物理存储位置。 |
| 最大持仓重叠率 | `pct_max_overlap_detected`| `float` | 比率小数 | 组合内检测到的最高 ETF 成分加权共振重叠度。 |
| 覆盖成长股数量 | `cnt_growth_stocks_covered`| `int` | 家 | 纳入决策走廊并测算现金跑道的先锋企业数量。 |

---

## 附录：工程实现与边界自查清单 (Engineering Defense Checklist)

- [ ] **物理临时文件原子替换**：Excel 生成过程必须先写入 `.tmp` 临时扩展名文件，生成校验通过后方可执行 `os.replace` 原子替换，严禁遗留残缺工作簿。
- [ ] **单元格列宽自适应截断保护**：列宽计算依据内容字符加权，并强制设定最大列宽上限（如不超过 60 字符），防止长文本撑破打印版面。
- [ ] **文本 Emoji 物理清洗**：所有写入 Excel 单元格的文本必须经由 `AIResearchAgent.clean_text_no_emoji()` 正则过滤，杜绝任何表情符号残留。
- [ ] **除零防御下界保护**：在计算现金跑道与营运杠杆时，分母必须包裹保护下界 $\max(\text{Burn}, 1.0)$ 与 $\max(\text{Spread}, 1.0)$，严禁抛出 `ZeroDivisionError`。
