# -*- coding: utf-8 -*-
"""攻防护航工具：Beneish M-Score 财务舞弊排雷与吊灯移动止盈棘轮系统 (向下兼容中继门面).

实现托管于底层纯净核心: `financial_core.engines.forensics_and_trailing_exit_engine`
遵循单一事实来源 (SSOT) 规范。
"""

from financial_core.engines.forensics_and_trailing_exit_engine import (
    BeneishMetrics,
    BeneishScoreResult,
    ChandelierExitResult,
    ForensicsAndTrailingExitEngine,
)

__all__ = [
    "BeneishMetrics",
    "BeneishScoreResult",
    "ChandelierExitResult",
    "ForensicsAndTrailingExitEngine",
]
