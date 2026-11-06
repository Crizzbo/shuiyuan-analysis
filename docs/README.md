# 水源智能投研系统 · 核心设计规格书总览与权责边界导航 (Design Specs Hub)

> **版本**：v2.0 权威重构版 (SSOT)  
> **工程哲学**：单一事实来源、一书专责一项核心系统职能、彻底合并同类项、全息覆盖六大功能域。

---

## 一、 12 本专责核心设计典籍导航矩阵

系统设计全面重构并归并为 **12 部独立高规格专责设计典籍**，每一本专责一项明确的系统职能：

| 典籍代号与文件名 | 专责核心职能（负责那一项） | 核心托管代码模块 | 对应测试与验证套件 |
|---|---|---|---|
| **[SPEC-01 系统总体架构与分层工程总纲](SPEC_01_系统总体架构与分层工程总纲.md)** | **系统顶层总览**：定义系统业务愿景、六大功能域地图、四层单向物理架构与零逆向依赖铁律。 | `financial_core/`<br>`finance_tools/`<br>`financial_reporting/`<br>`scripts/` | `scripts/verify_architecture_integrity.py` |
| **[SPEC-02 多模态视觉呈现与研报Token设计规范](SPEC_02_多模态视觉呈现与研报Token设计规范.md)** | **视觉与排版**：定义出版级 A4 矢量无截断排版、买方暗色仪表盘设计语言、设计 Token 与 5-Sheet Excel 样式。 | `financial_reporting/deep_pdf_renderer.py`<br>`financial_reporting/briefing_pdf_renderer.py` | `scripts/test_financial_reporting.py` |
| **[SPEC-03 行业知识中枢与微观商业机器解构规格书](SPEC_03_行业知识中枢与微观商业机器解构规格书.md)** | **行业知识与图谱**：11大板块、41个法定行业微观造血商业机器、产业链拓扑有向图与图谱边界防御。 | `knowledge/industry_knowledge_hub.py`<br>`financial_core/engines/knowledge_graph_engine.py` | `scripts/test_knowledge_graph_engine.py`<br>`scripts/test_industry_mapping.py` |
| **[SPEC-04 六步研究法与官方财报三表契约规范](SPEC_04_六步研究法与官方财报三表契约规范.md)** | **财务底账契约**：买方六步投研闭环、官方财报原始三表平账契约 ($Assets=Liab+Equity$) 与舞弊排查。 | `schemas/deep_dossier.schema.json`<br>`financial_core/models/accounting.py` | `scripts/test_research_contract.py` |
| **[SPEC-05 数据采集AI浏览器补数与证据治理规范](SPEC_05_数据采集AI浏览器补数与证据治理规范.md)** | **数据获取与治理**：SEC/JPX 双市场全息底账、公开数据采集 SOP、AI 浏览器补数与汇率折算清洗。 | `data/universe/`<br>`scripts/data_catalog.py`<br>`data/audits/` | `scripts/test_data_store.py` |
| **[SPEC-06 核心金融计算与多情景DCF估值引擎设计书](SPEC_06_核心金融计算与多情景DCF估值引擎设计书.md)** | **估值模型算法**：自由现金流折现 (FCFF)、加权平均资本成本 (WACC)、三态情景估值与反向 DCF 逆推。 | `financial_core/engines/dcf_valuation_engine.py`<br>`financial_core/calculators/wacc.py` | `scripts/test_financial_core_calculators.py` |
| **[SPEC-07 买方时机决策与技术足迹分析引擎设计书](SPEC_07_买方时机决策与技术足迹分析引擎设计书.md)** | **买入时机与技术形态**：米奈尔维尼 SEPA 时机决策、趋势模板阶段判定、波动收敛 (VCP) 与动态止损。 | `financial_core/engines/sepa_timing_engine.py` | `scripts/test_sepa_timing_engine.py` |
| **[SPEC-08 期权全周期因果分析与仓位风控引擎设计书](SPEC_08_期权全周期因果分析与仓位风控引擎设计书.md)** | **期权衍生品分析**：期权五级因果链条、交易时段时效门禁、内在价值与时间价值拆解、1/4 凯利仓位约束。 | `financial_core/engines/options_causal_analyzer.py` | `scripts/test_options_causal_analyzer.py` |
| **[SPEC-09 全球宏观流动性与跨资产配置体系设计书](SPEC_09_全球宏观流动性与跨资产配置体系设计书.md)** | **宏观传导与大类资产**：全球宏观流动性、实际利率与黄金大宗、核心 ETF 穿透与主权去美元化储备。 | `financial_core/engines/macro_transmission_engine.py`<br>`data_sources/tackle_phase2_batch1_gold_metals.py` | `scripts/test_macro_transmission_engine.py` |
| **[SPEC-10 千家资产池流式建档与公司深度档案生成流水线](SPEC_10_千家资产池流式建档与公司深度档案生成流水线.md)** | **海量标的建档**：全盘数千家资产池分级 (Tier 0/1/2/3)、Chunk-and-Stream 流式管道与断点续跑机制。 | `scripts/legacy_batch_runners/`<br>`data_sources/` | `scripts/test_stream_pipeline.py` |
| **[SPEC-11 云端无头每日行情与研报自动化调度流水线](SPEC_11_云端无头每日行情与研报自动化调度流水线.md)** | **云端自动化流水线**：无头跨平台渲染探测、GitHub Actions 定时调度、行情新鲜度门禁与独立三态推荐卡片。 | `scripts/cloud_daily_pipeline.py`<br>`.github/workflows/daily_market_pipeline.yml` | `scripts/test_cloud_daily_pipeline.py` |
| **[SPEC-12 系统质量工程密码学账本与全息测试验收标准](SPEC_12_系统质量工程密码学账本与全息测试验收标准.md)** | **工程质量与验收**：SHA-256 不可篡改预测账本、系统防劣变四大硬门禁、金融数学防御与测试规范。 | `financial_core/engines/prediction_ledger.py`<br>`scripts/verify_architecture_integrity.py` | `scripts/test_prediction_ledger.py` |

---

## 二、 历史碎片文档归档与平滑映射

为了保证历史可审计且严禁物理删除大段内容：
- 原有的 37+ 篇分散文档、使用说明附录与二级数据字典均已系统化合并提炼至上述 12 本专责典籍；
- 原始历史草稿与专项调研已安全归档至 `docs/archive_legacy/` 目录；
- 系统知识图谱 (`financial_core/engines/knowledge_graph_engine.py`) 已全量同步映射这 12 本核心设计典籍，确保 AI 与工程人员随时可机器化遍历确认知识边界。
