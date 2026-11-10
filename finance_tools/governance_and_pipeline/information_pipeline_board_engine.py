# -*- coding: utf-8 -*-
"""信息流水线看板工具层门面 (finance_tools/governance_and_pipeline/information_pipeline_board_engine.py).

遵循《CLAUDE.md》与《AGENTS.md》四层单向架构铁律：
本文件作为 governance_and_pipeline 子包对底层核心算法与状态机的单向中继门面，
严格单一事实来源 (SSOT)，无任何反向逆向依赖。
"""

from financial_core.pipeline.information_pipeline_board_engine import (
    InformationPipelineBoardEngine,
    PipelineCategory,
    PipelineMessageItem,
    PipelineSeverity,
    ProcessStageStatus,
)

__all__ = [
    "InformationPipelineBoardEngine",
    "PipelineCategory",
    "PipelineMessageItem",
    "PipelineSeverity",
    "ProcessStageStatus",
]
