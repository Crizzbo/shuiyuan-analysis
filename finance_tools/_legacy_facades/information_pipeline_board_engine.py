# -*- coding: utf-8 -*-
"""向下兼容遗留导入虚拟门面 (finance_tools/_legacy_facades/information_pipeline_board_engine.py).

支持历史代码与脚本通过 `from finance_tools.information_pipeline_board_engine import ...` 直接导入。
"""

from ..governance_and_pipeline.information_pipeline_board_engine import (
    InformationPipelineBoardEngine,
    PipelineCategory,
    PipelineMessageItem,
    PipelineSeverity,
    ProcessStageStatus,
    collect_pipeline_events,
    MACRO_INDICATORS_TEMPLATE_SPECS,
    EQUITIES_SUMMARY_DEFAULT,
)

__all__ = [
    "InformationPipelineBoardEngine",
    "PipelineCategory",
    "PipelineMessageItem",
    "PipelineSeverity",
    "ProcessStageStatus",
    "collect_pipeline_events",
    "MACRO_INDICATORS_TEMPLATE_SPECS",
    "EQUITIES_SUMMARY_DEFAULT",
]
