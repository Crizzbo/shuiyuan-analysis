# -*- coding: utf-8 -*-
"""向下兼容门面：重定向至 finance_tools.macro_and_ripple.hall_discount_friction_engine。

功能归属：宏观冲击与产业链涟漪分析器
业务定位：宏观流动性冲击传导、SOTP跨业务分部因果穿透、多标的供应链上下游涟漪效应矩阵与制度风险评级
此门面确保既有脚本、测试用例与历史引用零代码修改平滑过渡。
"""

import sys
from finance_tools.macro_and_ripple.hall_discount_friction_engine import *
from finance_tools.macro_and_ripple import hall_discount_friction_engine as _impl_module

# 保持模块元属性与引用透明性
__doc__ = _impl_module.__doc__
if hasattr(_impl_module, "__all__"):
    __all__ = _impl_module.__all__
