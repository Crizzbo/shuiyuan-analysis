# 水源智能投研系统 · 质量工程、密码学账本与全息测试验收标准 (SPEC-12)

> **设计典籍代号**：`SPEC_12_QUALITY_ENGINEERING_LEDGER_AND_TEST_ACCEPTANCE`  
> **所属业务分类**：系统质量保障、密码学防伪对账、架构防劣变与全量测试套件  
> **专责系统职能**：定义系统防劣变四大硬门禁、SHA-256 密码学不可篡改预测账本、金融数学边界防御机制、测试用例中文规范与全息回归验收准则。  
> **权威单一事实来源 (SSOT)**：`scripts/verify_architecture_integrity.py`、`financial_core/engines/prediction_ledger.py` 与 `scripts/test_*.py`。

---

## 一、 质量工程哲学与买方防伪底线

在严肃买方金融量化系统中，任何代码重构或功能增补都绝不能牺牲底层架构的稳定性和计算结果的客观性：
1. **密码学时间链条存证**：
   任何研报中的个股预测价格、止损点与战术建议，生成时即刻通过 SHA-256 哈希计算形成不可逆的防伪链条存入轻量账本；杜绝任何人后验篡改历史预测以粉饰业绩；
2. **严密的架构防劣变安全网**：
   每次代码改修后，必须强制运行架构完整性巡检；严禁为了局部便利破坏核心层解耦原则，严禁引入任何反向依赖；
3. **金融数学边界防御**：
   所有金融估值与折现模型必须内置除零保护、除负保护、资产有限责任下界约束（股票价格不能为负）与极值收敛保护，确保在极端市场行情下系统绝不崩溃。

---

## 二、 SHA-256 密码学不可篡改预测账本 (PredictionLedger)

系统在 `financial_core/engines/prediction_ledger.py` 中实现了基于 SQLite 与 SHA-256 的不可篡改时间链条：
1. **数据块结构 (Block Payload)**：
   每次录入预测时，记录预测 ID、日期、标的代码、基准价格、安全边际触发价、三态情景价格与前一区块哈希；
2. **链条连续性校验 (ledger.verify_integrity())**：
   遍历账本中所有历史记录，递归验证每个区块的当前哈希是否与其内容一致、前置哈希指针是否严丝合缝；若发现任何一行数据被人工手动改动，验签立即失败并警报。

---

## 三、 代码交付四大硬验收门禁 (The Four Hard Gates)

任何代码修改或功能上线前，必须依次通过以下四道硬门禁方可交付：

| 门禁序号 | 门禁名称与执行命令 | 验收合格标准 (Pass Criteria) |
|---|---|---|
| **门禁 1** | **架构完整性全息巡检**<br>`python scripts/verify_architecture_integrity.py` | 断言底层 `financial_core` 零外部污染、全量模块导入零循环依赖、门面与底账就绪。 |
| **门禁 2** | **全量单元测试零失败**<br>`python -m unittest discover -s scripts -p "test_*.py"` | 所有测试用例 100% PASS，测试数量只增不减，断言全部通过。 |
| **门禁 3** | **四大数据治理回归全绿**<br>`python scripts/test_data_store.py`<br>`python scripts/validate_knowledge_structure.py`<br>`python scripts/test_research_contract.py`<br>`python scripts/test_industry_mapping.py` | 全量数据主账、行业分类映射、研究契约与知识图谱 100% 通过验证。 |
| **门禁 4** | **密码学账本防伪验签通过**<br>`python -c "from financial_core.engines.prediction_ledger import PredictionLedger; assert PredictionLedger().verify_integrity()"` | 账本 SHA-256 哈希链条 100% 自洽无篡改。 |

---

## 四、 单元测试用例规范与中文业务场景说明

所有测试文件（`scripts/test_*.py`）必须具备规范的编号与中文业务场景说明，杜绝含糊不清的断言：
- **用例编号标准**：采用 `【UT-模块-序号】`（单元测试）与 `【IT-模块-序号】`（集成测试）；
- **Docstring 结构规范**：
  明确写明“测试点功能”、“输入参数的正常边界”以及“模拟何种极端商业或市场情景”。
