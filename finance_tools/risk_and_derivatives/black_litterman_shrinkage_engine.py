# -*- coding: utf-8 -*-
"""基本面与动量权重转化器：Ledoit-Wolf 协方差收缩与 Black-Litterman 贝叶斯组合配置引擎 (向下兼容中继门面).

实现托管于底层纯净核心: `financial_core.engines.black_litterman_shrinkage_engine`
遵循单一事实来源 (SSOT) 规范。
"""

from financial_core.engines.black_litterman_shrinkage_engine import (
    ShrinkageResult,
    BlackLittermanResult,
    BlackLittermanShrinkageEngine,
)

__all__ = [
    "ShrinkageResult",
    "BlackLittermanResult",
    "BlackLittermanShrinkageEngine",
]
