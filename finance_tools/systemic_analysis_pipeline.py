"""向下兼容重导出层：系统性投研分析主管道 (Systemic Analysis Pipeline Compatibility Layer).

本项目核心实现位于 financial_core.pipeline.systemic_analysis_pipeline。
本模块提供向下兼容重导出，确保历史脚本与外部调用无缝平稳过渡。
"""

from financial_core.pipeline.systemic_analysis_pipeline import (
    SystemicCompanyInput,
    SystemicDecisionCard,
    SystemicAnalysisPipeline,
)

__all__ = [
    "SystemicCompanyInput",
    "SystemicDecisionCard",
    "SystemicAnalysisPipeline",
]
