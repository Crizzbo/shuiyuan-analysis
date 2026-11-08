# -*- coding: utf-8 -*-
"""向下兼容门面：重定向至 finance_tools.risk_and_derivatives.american_option_tree_engine。

功能归属：风险管理与衍生品定价引擎
业务定位：美式期权二叉树定价、期权因果分析、投资组合风险预算、信用违约与极端黑天鹅压力测试
此门面确保既有脚本、测试用例与历史引用零代码修改平滑过渡。
"""

import sys
from finance_tools.risk_and_derivatives.american_option_tree_engine import *
from finance_tools.risk_and_derivatives import american_option_tree_engine as _impl_module

# 保持模块元属性与引用透明性
__doc__ = _impl_module.__doc__
if hasattr(_impl_module, "__all__"):
    __all__ = _impl_module.__all__
