# -*- coding: utf-8 -*-
"""向下兼容门面：重定向至 finance_tools.screening.screening_candidate_ranker。

功能归属：全市场选股与价格时机引擎
业务定位：SEPA 8大趋势硬指标、VCP 4T波动收缩形态、资产池构建与候选优选排序
此门面确保既有脚本、测试用例与历史引用零代码修改平滑过渡。
"""

import sys
from finance_tools.screening.screening_candidate_ranker import *
from finance_tools.screening import screening_candidate_ranker as _impl_module

# 保持模块元属性与引用透明性
__doc__ = _impl_module.__doc__
if hasattr(_impl_module, "__all__"):
    __all__ = _impl_module.__all__
