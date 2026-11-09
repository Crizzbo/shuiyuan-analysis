# data_max: 全盘万家美日企业资产池数据层规范与减法架构

## 一、 数据架构定位与极致做减法哲学

在全盘万家企业（美股 SEC 10,445 家、日股 JPX 4,447 家，共计 14,892 家上市主体）的工程实践中，为了兼顾**本地高吞吐量化计算性能**与**生产仓库轻量化版本控制（SSOT）**，本项目实行“本地留存全息缓存 × 远端受控核心底账”的数据层减法架构：

1. **本地环境（高频计算层，全量留存）**：
   - 本地完整保留 10 年跨度（2015-2026）的清洗后日线行情与技术指标缓存（位于 `data_max/normalized/`，覆盖 8,260+ 家有效标的，1,440 万+ 条逐日交易记录，体积约 2.89GB）；
   - 保留本地采集流水线数据库（`data_max/ledger/collection_progress.db`），支持断点秒级热恢复与增量流式追加。

2. **Git 仓库与远端协同（元数据清单与核心凭据层，极致瘦身）**：
   - 彻底阻断 1.6 万个高频散落碎片文件进入版本库；
   - 彻底阻断 Windows 操作系统保留设备文件名（如 `CON.json.gz`、`PRN.json.gz`），彻底根除 Windows 开发者在 `git checkout` / `git clone` 时的系统崩溃风险；
   - 仓库仅受控记录具备长期业务价值的资产元数据清单（`universe/`）、采集批次断点（`checkpoints/`）与回测指标报告（`reports/`）。

---

## 二、 资产池清单与目录索引

```text
data_max/
├── universe/
│   ├── sec_universe_manifest.json       # 10,445 家美股 SEC CIK、Ticker、标准法定全称与交易所索引
│   ├── jpx_universe_manifest.json       # 4,447 家东证全市场股票代码 (Code)、标准名称与板块分级
│   └── universe_tier_partition.json     # 资产池分级规则 (Tier 0 旗舰 / Tier 1 中坚 / Tier 2/3 全息)
├── checkpoints/
│   └── ingestion_checkpoint.json        # 采集流水线状态断点（记录已完成标的数与最新时间戳）
├── reports/                             # 结构化回测成果、指标对撞摘要与研报凭证
└── normalized/ (本地受控，gitignore 忽略) # 本地 2.89GB 原始历史日线行情 bars
```

---

## 三、 数据完整性与密码学存证

所有从 `data_max/` 驱动的模型计算、资产筛选与自适应回测流水线，均通过底层 `HistoryValidationLedger` SHA-256 密码学时间链条签名存证。任何新生成的研报与指标必须通过哈希对账和验签，杜绝未经审计的虚假数据流入生产系统。
