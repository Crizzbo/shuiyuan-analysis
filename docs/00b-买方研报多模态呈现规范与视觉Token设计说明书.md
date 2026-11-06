# 买方研报多模态呈现规范与视觉 Token 设计说明书 (Multi-Modal Delivery & Visual Token Specification)

> **版本**：1.1.0 (敏捷工程 Living Architecture 物理对齐版)  
> **更新日期**：2026-11-03  
> **对应物理代码**：
> - 样式排版引擎：`financial_reporting/excel_styler.py` (`ExcelStyler`)
> - SEPA 呈现中枢：`financial_reporting/sepa_card_renderer.py` (`SepaCardRenderer`)
> - 每日大盘研报：`financial_reporting/daily_briefing_engine.py` (`DailyBriefingEngine`)
> - 5-Sheet Excel 建造器：`financial_reporting/excel_dossier_builder.py` (`ExcelDossierBuilder`)  
> **核心原则**：**视觉层级分明、CFI/FAST 色彩语法严格对齐、自适应排版、彻底去工程代号、1:1 代码镜像**。

---

## 一、 多模态渲染管道与四层物理架构 (Multi-Modal Architecture & Pipeline)

整个呈现子系统横向承接底层纯净量化引擎（`financial_core`）与业务数据，纵向为买方投委会与基金经理输出四种物理交付载体：

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        【底层数据与引擎输入源 (SSOT)】                                 │
│   • SepaBuySignalResult / SepaPriceBoundaries (米奈尔维尼时机与风控边界)               │
│   • CompanyDeepDossier (官方三表底稿、DIO、上下游集中度、三态 DCF 估值矩阵)            │
│   • DailyBriefing (宏观流动性、VIX/恐慌指数、资金净流向、PCR、顶层 AI 研判)            │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        【核心排版与样式渲染中枢 (Presentation Hub)】                  │
│   • financial_reporting/excel_styler.py (FAST 规范、色彩 Token、边框、会计格式)        │
│   • financial_reporting/sepa_card_renderer.py (HTML/MD/Excel 跨模态转换与自适应规范化)  │
└─────────────────────┬─────────────────────┬─────────────────────┬──────────────────────┘
                      │                     │                     │                      │
                      ▼                     ▼                     ▼                      ▼
┌───────────────────────────┐ ┌───────────────────────────┐ ┌───────────┐ ┌───────────────────────────┐
│     1. A4 矢量 HTML       │ │     2. 纯净无损 PDF       │ │ 3. 投委会 │ │    4. FAST 5-Sheet Excel    │
│  • CSS Paged Media 响应式 │ │  • Edge Headless 管道     │ │    Memo   │ │  • OpenPyXL 纯净渲染      │
│  • 12mm 边距、五列走廊    │ │  • 零溢出、分页感知       │ │  • 纯自然 │ │  • 动态配平自检公式注入   │
│  • 墨绿/红/金黄动态徽章   │ │  • A4 纵向无锯齿印刷级    │ │    语言   │ │  • 条件格式与击球区浅绿底 │
└───────────────────────────┘ └───────────────────────────┘ └───────────┘ └───────────────────────────┘
```

---

## 二、 买方权威视觉色彩 Token 体系 (Color Tokens - Code Mapping)

严格遵循华尔街 FAST Standard 与 CFI / Wall Street Prep 财务建模视觉准则，与 `financial_reporting/excel_styler.py` 物理常量 1:1 绝对镜像：

### 1. 物理调色板常量对照表 (`excel_styler.py:26-41`)

| 物理常量名称 | 16进制色值 | 视觉感知与语义直觉 | 严格适用范围 | 对应代码与报告元素 |
| :--- | :---: | :--- | :--- | :--- |
| `COLOR_PRIMARY_NAVY` | `1F4E79` | 华尔街机构经典深蓝 | 表格主标头底色、横幅底色、双下划线合计边框 | 工作表顶部 Banner、一级分节 Header、总表头 |
| `COLOR_WHITE` | `FFFFFF` | 纯白 | 主标头文字、深色底纹文字、纯净卡片背景 | Banner 主标题文字、徽章高对比度文字 |
| `COLOR_SECTION_BLUE` | `DDEBF7` | 次级小标题浅蓝底 | 模块分节条、表格列头、二级统计标题 | 二级分类小标题栏、表头分组栏 |
| `COLOR_SECTION_TEXT` | `1F4E79` | 次级标题深蓝文字 | 次级小标题文字、指标分类名称 | 次级分节栏加粗文字 |
| `COLOR_INPUT_BLUE` | `002060` | CFI 历史事实深蓝 | 官方历史财报三表原始录入数字 (Hardcoded) | 历史营业收入、归母净利润、原始库存金额 |
| `COLOR_CALC_BLACK` | `000000` | 纯净计算黑 | 表内动态派生计算、比率、DCF 折现 (Formulas) | 毛利率、ROE、公允内在价值、总资产合计 |
| `COLOR_LINK_GREEN` | `008000` | 跨表引用翠绿 | 跨工作表引用单元格、外链数据锚点 (Links) | 引用 Sheet 2 财报数据、HYPERLINK 跳转文字 |
| `COLOR_ASSUMPTION_YELLOW` | `FFF2CC` | 敏感度参数淡黄底 | 允许投资经理手动调节的估值假设开关 (Toggles) | 永续增长率 $g$、目标 WACC、情景切换开关 |
| `COLOR_BUY_ZONE_GREEN` | `E2EFDA` | 击球区柔和浅绿底 | 现价落入击球区、突破买点高亮行、安全边际达成 | SEPA 枢轴买点行、DCF 悲观底价达成行 |
| `COLOR_BUY_ZONE_TEXT` | `276A3C` | 击球区墨绿文字 | 允许开仓做多、安全边际充裕指令 | 动作指令：“果断击球开火”、“安全边际充足” |
| `COLOR_WARNING_ORANGE` | `FCE4D6` | 预警柔和浅橙底 | 追高超买脱轨、平账自检未过、违约高危 | SEPA 超买追高行、资产负债表不平告警行 |
| `COLOR_WARNING_TEXT` | `C00000` | 警戒深红文字 | 严禁追高、跌破止损线斩仓警示 | 动作指令：“严禁追高”、“破产高危预警” |
| `COLOR_GRAY_LIGHT` | `F2F2F2` | 合计浅灰底 | 资产负债表合计行、分类统计小计行 | 资产总计、负债与权益总计、现金流净额 |
| `COLOR_BORDER_LIGHT` | `D9D9D9` | 细浅灰边框 | 数据单元格常规四周边框 | 全表数据单元格薄边框 |
| `COLOR_BORDER_NAVY` | `1F4E79` | 深蓝主边框 | 表头上下边框、主表外围轮廓 | 顶级表格边框、Section 外围边框 |

---

### 2. HTML A4 动态徽章状态色彩映射 (`sepa_card_renderer.py:98-118`)

| 状态空间键名 (`BuySignalTier`) | 徽章背景色 (`badge_bg`) | 徽章说明文字 (`badge_text`) | 文字色彩 (`status_desc_color`) |
| :--- | :---: | :--- | :---: |
| `PIVOT_TRIGGERED` | `#2f855a` (墨绿) | `【买入触发】放量突破枢轴买点` | `#276749` |
| `EXTENDED_OVERBOUGHT` | `#c53030` (红色) | `【超买拦截】脱离买点超 5%，严禁追高` | `#9b2c2c` |
| `SQUAT_REVERSAL_WATCH`| `#d69e2e` (金黄) | `【深蹲洗盘】缩量回踩守住止损，等待逆转`| `#b7791f` |
| `WATCHLIST_FORMING` | `#3182ce` (经典蓝) | `【自选跟踪】第二阶段整理，等待收敛` | `#2b6cb0` |
| `OUT_OF_TREND` | `#718096` (中性灰) | `【趋势否决】未处于第二阶段主升浪` | `#4a5568` |

---

## 三、 会计与金融数字格式规范 (Number Formats - Code Mapping)

与 `financial_reporting/excel_styler.py:48-58` 物理常量严格保持一致：

```python
FMT_CURRENCY_USD_INT = '$#,##0;($#,##0);"-"'     # 美元整数级 (如总市值、总收入)
FMT_CURRENCY_USD_DEC = '$#,##0.00;($#,##0.00);"-"' # 美元美分级 (如股价、EPS、止损线)
FMT_CURRENCY_JPY_INT = '¥#,##0;(¥#,##0);"-"'       # 日元整数级 (如东证股价、亿日元金额)
FMT_PERCENT_ONE_DEC  = '0.0%'                     # 常规比率 (如毛利率 45.2%、止损率 7.0%)
FMT_PERCENT_TWO_DEC  = '0.00%'                    # 精准比率 (如 WACC 8.25%、自然利率缺口 0.45%)
FMT_MULTIPLE         = '0.0"x"'                   # 估值倍数 (如 P/E 25.4x、加成率 1.45x)
FMT_INTEGER          = '#,##0;(#,##0);"-"'        # 整数千分位 (如成交股数、员工人数)
FMT_DECIMAL          = '#,##0.00;(#,##0.00);"-"'  # 两位小数通用 (如 beta 值、DIO 天数)
FMT_DATE             = 'YYYY-MM-DD'               # 交易日标准时间契约
FMT_TEXT             = '@'                        # 纯文本单元格
```

*排版硬性铁律*：
1. **负数强制使用会计括号**：严禁出现 `-12.5%` 或 `-$186.00` 形式，必须规范为 `(12.5%)` 与 `($186.00)`；
2. **零值统一使用短横杠表示**：数值为 0 时必须显示为 `"-"`，严禁零值泛滥干扰视觉动线。

---

## 四、 FAST Standard 5-Sheet Excel 版面布局图 (Excel Layout Grid)

每个公司的深度研报工作簿（`ExcelDossierBuilder`）包含 5 个标准化工作表，版面物理网格严格规范如下：

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Sheet 1: 00_投资备忘录与决策中枢 (Executive Memo & Cockpit)                            │
│  ├─ Row 1~3: 华尔街机构经典双行 Banner (深蓝底色 #1F4E79，白字 14pt 加粗，冻结窗格)    │
│  ├─ Section 1: 一、投研顶层核心摘要与三态公允价值走廊 (Base / Conservative / Bull)    │
│  ├─ Section 2: 二、宏观微观血肉联合冲击诊断 (诺贝尔模型传导 WACC 与黑天鹅冲击)        │
│  └─ Section 3: 三、米奈尔维尼 SEPA 价格时机与买入决策操盘卡 (8 行关键价格走廊)         │
│                 [枢轴点 $200.00 | 硬止损 $186.00 | 追高上限 $210.00 | 3R保本 $242.00]  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Sheet 2: 01_官方财报三表全息底稿与杜邦拆解 (Financial Statements & DuPont)             │
│  ├─ Section 1: 资产负债表 ($A = L + E$ 动态平账自检公式，不平则红底 #FCE4D6 告警)      │
│  ├─ Section 2: 利润表与自由现金流 (FCF) 真实性还原                                     │
│  └─ Section 3: 杜邦分析三步法与 ROIC-WACC 价值创造动能透视                             │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Sheet 3: 02_供应链上下游集中度与护城河透视 (Supply Chain & Moat)                       │
│  ├─ Section 1: 前五大客户集中度与违约压力测试                                          │
│  ├─ Section 2: 核心供应商替代成本与交期风险                                            │
│  └─ Section 3: 晨星五维护城河量化打分 (网络效应、转换成本、规模优势、无形资产、再投资) │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Sheet 4: 03_库存周期与营运资本周转透视 (DIO & Working Capital)                         │
│  ├─ Section 1: 存货周转天数 (DIO) 跨周期演进与历史分位点                               │
│  ├─ Section 2: 应收账款天数 (DSO) 与应付账款天数 (DPO) 营运现金循环周期 (CCC)         │
│  └─ Section 3: 跌价准备与资产减值压力测试                                              │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Sheet 5: 04_双变量敏感度分析与蒙特卡洛估值矩阵 (Valuation & Sensitivity)               │
│  ├─ Section 1: WACC × 永续增长率 g 双变量敏感度热力矩阵 (淡黄底 #FFF2CC 开关)          │
│  ├─ Section 2: 蒙特卡洛 10,000 次向量化 DCF 模拟分布分位数 (10th, 50th, 90th)          │
│  └─ Section 3: 历史复盘对账与 PredictionLedger SHA-256 密码学指纹                      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 五、 去工程符号化文字标准 (Natural Language Guidelines - 1:1 Mapping)

面向投委会与外部读者的所有呈现界面，**严禁暴露纯代码下划线与枚举键名**：

| 内部代码变量 / 原始枚举 | 呈现层严禁暴露的形式 | 正确的买方自然语义翻译 (Mandatory) |
| :--- | :--- | :--- |
| `val_pivot_price` | `val_pivot_price: 200.0` | **枢轴买点 (Pivot): $200.00** |
| `val_stop_loss_price` | `stop_loss: 186.0` | **刚性硬止损 (-7.0%): $186.00** |
| `val_extended_limit_price` | `extended_limit: 210.0` | **超买追高上限 (+5.0%): $210.00** |
| `val_breakeven_trigger_price`| `breakeven_trigger: 242.0`| **3R 移动保本触发线: $242.00** |
| `val_target_profit_price` | `target_profit: 242.0` | **目标止盈靶心 (3:1): $242.00** |
| `Stage_1_Consolidation` | `Stage_1_Consolidation` | **第一阶段忽略筑底横盘期** |
| `Stage_2_Markup` | `Stage_2_Markup` | **第二阶段主升突围推进期 (主升浪)** |
| `Stage_3_Distribution` | `Stage_3_Distribution` | **第三阶段高位震荡派发期** |
| `Stage_4_Capitulation` | `Stage_4_Capitulation` | **第四阶段破位衰退投降期** |
| `Pivot_Triggered` | `PIVOT_TRIGGERED` | **【买入触发】放量突破枢轴买点** |
| `Extended_Overbought` | `EXTENDED_OVERBOUGHT` | **【超买拦截】脱离买点超 5%，严禁追高** |
| `Squat_Reversal_Watch` | `SQUAT_REVERSAL_WATCH` | **【深蹲洗盘】缩量回踩守住底线，等待逆转** |
| `Watchlist_Forming` | `WATCHLIST_FORMING` | **【自选跟踪】第二阶段整理，等待紧密收敛** |
| `Out_Of_Trend` | `OUT_OF_TREND` | **【趋势否决】未处于第二阶段主升浪** |
| `wicksellian_gap_bps` | `wicksellian_gap_bps: 45` | **自然利率缺口: +45.0 bps (紧缩区间)** |
| `is_trend_template_passed` | `is_trend_template_passed: true` | **8 大趋势指标全票核查: 全票通过** |
| `technical_footprint_code` | `technical_footprint_code: 8W 28/2.5 4T` | **技术足迹代码: 8W 28/2.5 4T** |
