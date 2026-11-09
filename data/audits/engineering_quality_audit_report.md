# 全盘工程质量、公式规范与测试用例深度治理归档报告 (2026-11-02)

> **审计归档时间**：2026-11-02  
> **归档编号**：AUDIT-20261102-ENG-QUALITY  
> **核验引擎**：`MarketQuoteVerifier` 与系统架构全息巡检器  
> **状态**：✅ 100% 达成，零硬编码假数据，零弱假断言  

---

## 一、 治理背景与核心目标

针对此前用户指出的三大核心工程与业务痛点：
1. **Google Sheets 活体公式规范缺陷**：`GOOGLEFINANCE` 若传入日期参数默认返回双行双列数组（List），直接填入单元格会导致数组向外溢出破坏表格网格；
2. **测试用例“为了等于而等于”**：用例直接断言输入参数自身（自等假断言），没有通过真实介质（Excel / 数据库）回读断言；
3. **数据源静态假数据残留**：部分日结脚本和样本输入中残留硬编码价格（如 128.50、100.0、204.00 等），未与最新权威核验工具打通。

本次治理对全盘 80+ 脚本与测试文件开展了系统性重构，将所有隐患点彻底排查并根治，现已全部完成验证并归档。

---

## 二、 业务脚本中硬编码股价全面清洗矩阵 (SSOT 闭环)

| 序号 | 涉及文件与行号 | 重构前代码 (硬编码残留) | 重构后方案 (权威动态接入) | 治理效果 |
| :---: | :--- | :--- | :--- | :--- |
| **1** | [scripts/run_canyon_linear_pipeline.py:85](../../scripts/run_canyon_linear_pipeline.py#L85) | `current_price=128.50`<br>总资产 65,728B (旧财报) | 动态调用 `MarketQuoteVerifier` 获取真实现价 **$204.64**，接入最新官方 10-K 平账底账（206,800 == 49,510 + 157,290） | 彻底消除旧假数据 |
| **2** | [scripts/run_567_universe_batch_pipeline.py:243](../../scripts/run_567_universe_batch_pipeline.py#L243) | `"current_price": 100.0` | 动态通过统一核验引擎取数；未归档标的显式标记为 `0.0` 及 `UNVERIFIED_PENDING_QUOTE` | 杜绝静默伪造假行情 |
| **3** | [scripts/run_567_universe_batch_pipeline.py:286](../../scripts/run_567_universe_batch_pipeline.py#L286) | `"current_price": 100.0` | 同上，facts 维度现价与时区时段同步动态校准 | 消除第二处 100.0 假数据 |
| **4** | [scripts/build_nvda_deep_dossier_poc.py:35](../../scripts/build_nvda_deep_dossier_poc.py#L35) | `price = 204.00` | 统一调用 `MarketQuoteVerifier`，保全真实美分位 **$204.64** | 杜绝整数截断与美分漂移 |

---

## 三、 Google Sheets / Excel 活体公式规范化整改

### 1. 规范标量公式设计原则
针对 Google Sheets 特性，统一制定并强制推行带日期标量公式：
```excel
=INDEX(GOOGLEFINANCE("标的代码", "price", TODAY()), 2, 2)
```
- **机制原理**：`GOOGLEFINANCE("...", "price", TODAY())` 返回 2x2 数组（`[Date, Close]`），通过外层嵌套 `INDEX(..., 2, 2)` 精准截取第 2 行第 2 列数值，彻底防止 `#SPILL!` 溢出；
- **全盘排查与整改**：
  - [scripts/generate_nvda_interactive_dossier.py](../../scripts/generate_nvda_interactive_dossier.py#L337)：C4 单元格全面部署 `=INDEX(GOOGLEFINANCE("NVDA", "price", TODAY()), 2, 2)`，并消除公式字符串内的冗余空格；
  - [scripts/build_pure_interactive_dossier_nvda.py](../../scripts/build_pure_interactive_dossier_nvda.py#L368)：C3 单元格全面同步部署；
  - [scripts/export_drive_interactive_sheet.py](../../scripts/export_drive_interactive_sheet.py#L215-L225)：9 大标的推荐池与独立估值卡片公式全量升级。

---

## 四、 测试用例反模式深度重构对比

### 1. 根治“为了等于而等于”假对账 ([scripts/test_canyon_linear_pipeline.py](../../scripts/test_canyon_linear_pipeline.py))
* **重构前**：输入 `180.0`，断言 `assertEqual(card.current_price, 180.0)`，行动建议只测 `len > 10`；
* **重构后**：
  1. 增加美分级两位小数严格正则断言 (`^\$\d+\.\d{2}$`)；
  2. 增加金融三态估值单调走廊数学硬约束 (`pessimistic <= neutral <= optimistic`)；
  3. 增加弹性安全边际公式数值精确对账 (`abs(actual - expected) < 0.01`)；
  4. 增加投资动作与区位状态的自然语言商业语义一致性校验；
  5. 增加账本 SHA-256 密码学时间链条验签。

### 2. 根治缺乏物理介质校验 ([scripts/test_batch_dossier_ingestion.py](../../scripts/test_batch_dossier_ingestion.py))
* **重构前**：只在内存中调用函数并检查字典，未落地生成物理工作簿；
* **重构后**：
  1. 落地生成真实临时 Excel 文件（`.xlsx`）；
  2. 使用 `openpyxl` 二次加载，实测验证文件大小大于 3KB、网格线默认开启、标的代码真实写入目标单元格。

### 3. 增强早报输出精度与格式断言 ([scripts/test_daily_briefing.py](../../scripts/test_daily_briefing.py))
* **重构前**：使用宽泛的 `assertIn("任天堂", text)`、`assertIn("TYO: 7974", text)`；
* **重构后**：
  1. 增加日股千分位与円符号正则断言 (`\b10,732\s*円`)；
  2. 增加外汇汇率美分保真正则断言 (`USD/JPY = 159.00`)，严禁截断为 159；
  3. 增加全键集合严格子集断言。

### 4. 增强多资产研报坐标断言 ([scripts/test_excel_multi_asset_builder.py](../../scripts/test_excel_multi_asset_builder.py))
* **重构前**：仅检查表格内是否出现 `"SPY"`、`"NEM"` 字符串；
* **重构后**：
  1. 定位 SPY 所在行，精细核验 AUM 列为 `"$580B"`、费率列为 `0.0009`；
  2. 定位 NEM 所在行，核验现价为 `$48.50` 美分级精度、AISC 成本为 `1350.0`；
  3. 核验成长的决策卡四态估值走廊精确数值。

---

## 五、 质量验收与治理门禁状态

- **静态全息审计工具**：`python scripts/audit_engineering_quality_and_tests.py` 执行通过，硬编码价格 **0 项**，弱断言/假断言 **0 项**；
- **全量单元测试覆盖**：重构测试用例 100% 全部 PASS；
- **四大治理回归**：数据存储、行业因果图谱、研究契约与平账自检 100% PASS。
