"""金融系统性投研管道层 (Systemic Pipeline Layer).

封装六道工序端到端投研主管道：
工序一：数据输入与时效核验门禁
工序二：法证级证据穿透手术刀 (五刀穿透)
工序三：商业品质与所有者收益测算
工序四：情景化 DCF 估值矩阵与 CRR 美式期权二叉树
工序五：跨市场宏观踩踏与套息交易压力测试
工序六：顶层综合研判与决策卡片生成
"""

from .systemic_analysis_pipeline import (
    SystemicCompanyInput,
    SystemicDecisionCard,
    SystemicAnalysisPipeline,
)
from .canyon_linear_pipeline import (
    CanyonStationInput,
    CanyonDecisionCard,
    CanyonLinearPipeline,
    QuoteFreshnessError,
    BalanceSheetInvariantError,
)
from .information_pipeline_board_engine import (
    InformationPipelineBoardEngine,
    PipelineMessageItem,
    ProcessStageStatus,
    PipelineCategory,
    PipelineSeverity,
)

__all__ = [
    "SystemicCompanyInput",
    "SystemicDecisionCard",
    "SystemicAnalysisPipeline",
    "CanyonStationInput",
    "CanyonDecisionCard",
    "CanyonLinearPipeline",
    "QuoteFreshnessError",
    "BalanceSheetInvariantError",
    "InformationPipelineBoardEngine",
    "PipelineMessageItem",
    "ProcessStageStatus",
    "PipelineCategory",
    "PipelineSeverity",
]
