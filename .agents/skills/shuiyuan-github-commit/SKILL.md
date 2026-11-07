---
name: shuiyuan-github-commit
description: 为水源分析（shuiyuan-analysis）快速整理、验收和创建 Git 提交。用户要求提交当前改动、生成 commit 或将选定改动推送到本项目的 GitHub 私有仓库时使用。
---

# 水源分析快速提交

默认完成一次范围清楚的本地提交。用户明确要求推送时才连接 GitHub，明确要求开 PR 时才创建 PR。当前仓库为 `Crizzbo/shuiyuan-analysis`，GitHub 默认分支为 `main`。

## 1. 判断工作区并锁定范围

- 读当前工作区适用的 `AGENTS.md`。用 `git status --short --branch`、`git diff --stat`、`git diff --cached --stat` 和必要的路径级 diff 确认分支、目标改动和已有暂存项。用户指定了文件或任务时，以该范围为准。
- 原工程的 `master` 含业务数据历史。即使 `origin` 指向 GitHub，也禁止从这套历史推送任何分支、标签或提交。可以在原工程做本地提交。向 GitHub 交付时，在单独的干净检出中从远端 `main` 创建或续用任务分支，只迁移审过的改动。保留远端已有改动和发布边界。
- 排除 `data/`、`data_sources/`、`reports/`、公司证据档案、真实财报样本、个人云端配置、分享导出包、缓存、环境文件、数据库及凭据。代码和 Markdown 也要查看新增内容，识别内嵌真实数据、历史研报摘录和私有云端链接。合成测试样例和 Schema 可按任务纳入。

## 2. 按变更类型验收

- 纯文档或技能说明检查内容、引用和 diff。README 是 `docs/SPEC_00_全盘设计典籍地图与SSOT总索引.md` 的首页展示副本。变更 SPEC 索引时核对两处内容，并从根目录重算 README 相对链接。修改结构化知识库时运行 `python scripts/validate_knowledge_structure.py`。
- 改代码前核对对应 SPEC 和四层依赖。保持 `financial_core/` 对外层零依赖，核心内部用相对导入。变更业务逻辑、算法或 Schema 时核对对应 SPEC 与兼容性，按适用的 `AGENTS.md` 同步更新设计说明。
- 原工程代码改动按顺序跑下列门禁，每条检查退出码和结果，失败时先解决或报告阻塞。

  ```text
  python scripts/verify_architecture_integrity.py
  python -m unittest discover -s scripts -p "test_*.py"
  python scripts/test_data_store.py
  python scripts/validate_knowledge_structure.py
  python scripts/test_research_contract.py
  python scripts/test_industry_mapping.py
  ```

  研判或对账还须核对 `PredictionLedger.verify_integrity()` 的实际结果。真实输入只在获准的本地环境使用。GitHub 检出缺少业务数据时，用本地环境验收同一组代码变更，再对照待提交 diff。缺少证据或门禁失败时，明确报告未通过，停止交付。

## 3. 精确暂存并提交

- 用 `git add -- 路径` 逐项暂存，文件中混有无关改动时只暂存目标补丁。保留用户既有暂存项。如果暂存区含范围外改动且无法安全隔离，先报告阻塞。
- 提交前运行 `git diff --cached --check`，复核 `git diff --cached --name-status` 和暂存补丁。以实际暂存内容核对数据边界和验证范围。空暂存区直接报告没有可提交的改动。
- 沿用 `类型(模块): 简述`，例如 `fix(reporting): 修复行情时段判定`。创建新提交后核对提交哈希、文件范围和工作区状态。

## 4. 按授权交付

- 推送前确认目标仍为预期私有仓库，任务分支基于远端 `main`，并复查 `origin/main..HEAD` 的每个待推送提交。历史、文件范围或远端状态不符时停止。使用普通推送，禁止强推、镜像推送和从原工程 `master` 推送。
- 需要 PR 时以 `main` 为目标，说明对应 SPEC、改动、验证结果和本地验证限制。业务数据、账本和凭据也应从 PR 正文、日志、截图和附件中排除。
- 最后报告提交哈希、范围、验证结果及推送状态。推送成功后核对远端分支的提交哈希。
