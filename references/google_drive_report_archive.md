# Google 云端硬盘研报归档与每日自动化执行规范

本文档定义每日美股与日股自动化全量分析结果在 Google 云端硬盘（Google Drive）中的存储目录架构、同步机制与定时自动化调度方案。

---

## 1. 目标与目录结构设计

每日研报由确定性 CLI 引擎批量生成，按日期建立独立根目录，并在该日期下区分美股 (`US/`)、日股 (`JP/`) 及全景看板 (`overview_dashboard.html`)。

### 推荐 Google Drive 目录架构

```text
Google Drive/ (我的云端硬盘)
└── 每日股票分析/
    ├── 2026-10-12/
    │   ├── overview_dashboard.html      <-- 每日美日全景大看板（支持浏览器直接交互与一键跳转）
    │   ├── daily_summary.json           <-- 机器可读的结构化量化底稿（用于二次分析）
    │   ├── US/                          <-- 美股深度研报目录（15 家以上）
    │   │   ├── aapl.html
    │   │   ├── msft.html
    │   │   ├── zm.html
    │   │   ├── stx.html
    │   │   └── ...
    │   └── JP/                          <-- 日股深度研报目录（原生日元 JPY + 美元 ADR 换算）
    │       ├── 7974_nintendo.html
    │       ├── 7203_toyota.html
    │       ├── 8035_tokyo_electron.html
    │       └── 6758_sony.html
    ├── 2026-10-13/
    │   └── ...
    └── README.md
```

---

## 2. CLI 运行与自动归档操作指令

### 2.1 本地生成（默认输出至项目内 `reports/`）
```powershell
.venv\Scripts\python.exe -X utf8 scripts/run_daily_analysis.py --market all --date 2026-10-12
```

### 2.2 自动同步到 Google Drive 同步目录
若您的电脑安装了 Google Drive 客户端（或指定了云端同步路径）：
```powershell
# 指定 --gdrive-dir 参数，系统将在生成本地报告后，自动按天归档至云盘目录
.venv\Scripts\python.exe -X utf8 scripts/run_daily_analysis.py `
    --market all `
    --date 2026-10-12 `
    --gdrive-dir "G:\我的云端硬盘\每日股票分析"
```

### 2.3 仅更新单一市场或自定义标的
```powershell
# 仅更新日股标的
.venv\Scripts\python.exe -X utf8 scripts/run_daily_analysis.py --market JP

# 仅更新特定关注标的
.venv\Scripts\python.exe -X utf8 scripts/run_daily_analysis.py --tickers ZM,STX,TYO:7974
```

---

## 3. 面向用户的报告规范（严格执行）

1. **绝对脱敏底层技术黑话**：
   - 严禁在 HTML 研报中出现“快照”、“SHA-256”、“代码哈希”、“固定值”等工程名词；
   - 统一使用金融研报语言：“官方基准联动”、“发布基准”、“微观基本面体检与宏观情景折现模型”。
2. **宏观关键数值解读**：
   - 每份报告均集成 6 大核心宏观基准（10Y美债、2Y美债、利差、3M短债、DXY、EFFR/CPI）与专业投资影响解读面板。
3. **跨币种自洽**：
   - 日股严格原生以 JPY（円）展示，并基于权威 USD/JPY 汇率提供 ADR 映射折算。

---

## 4. 定时自动化调度接入

支持两种调度模式：

### 模式 A：Antigravity Agentic 自动化（推荐）
在聊天界面输入 **`/automation`**，设置定时提示词：
> “每个交易日早上 08:30 自动运行 `python scripts/run_daily_analysis.py --market all`，检查是否有标的进入安全边际买入区间，并将报告归档到 Google 云盘。”

### 模式 B：Windows 计划任务（Task Scheduler）
通过操作系统的 Task Scheduler 每日定时调用批处理脚本：
```bat
@echo off
cd /d "C:\Users\shared_user\AppData\Roaming\Tencent\Marvis\User\SHARED_USER_ID\skills\custom\shuiyuan-analysis"
.venv\Scripts\python.exe -X utf8 scripts/run_daily_analysis.py --market all --gdrive-dir "G:\我的云端硬盘\每日股票分析"
```
