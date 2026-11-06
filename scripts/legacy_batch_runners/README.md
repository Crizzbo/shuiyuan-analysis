# Legacy Batch Runners (归档目录)

本目录归档历史遗留的单批次投研渲染脚本 (`tackle_batch1.py` ~ `tackle_batch78.py`)。

## 架构升级说明
根据 2026-10-15 架构级整改规范，原 78 个重复分散的脚本已被全新的统一流水线调度器替代：
- **统一入口**：[`scripts/run_batch_dossier_pipeline.py`](../run_batch_dossier_pipeline.py)
- **核心升级点**：
  1. 动态自适应探测 `gdrive` 与 `Edge` 路径，彻底消除死代码绝对路径硬编码；
  2. 真实云端上传审计链（`data/audits/unified_batch_receipts/`），杜绝虚拟假回退；
  3. 支持单批、范围批次（如 `--range 1 10`）、阶段二批次（`--phase2-batch 1`）灵活调用；
  4. 解耦数据清洗与金融引擎计算，完全依托 `financial_core` 标准化输入输出。

本目录脚本保留仅作历史参考与溯源，日常运行请使用统一入口。
