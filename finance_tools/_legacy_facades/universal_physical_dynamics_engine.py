# -*- coding: utf-8 -*-
"""向下兼容门面：重定向至 finance_tools.forensics_and_valuation.universal_physical_dynamics_engine。

功能归属：财务法证审计与多情景估值模型
业务定位：通用商业物理动力学、速度参数提取、供应链周转与零增长停滞非对称估值底线
此门面确保既有脚本、测试用例与历史引用零代码修改平滑过渡。
"""

import sys
from finance_tools.forensics_and_valuation.universal_physical_dynamics_engine import *
from finance_tools.forensics_and_valuation import universal_physical_dynamics_engine as _impl_module

# 保持模块元属性与引用透明性
__doc__ = _impl_module.__doc__
if hasattr(_impl_module, "__all__"):
    __all__ = _impl_module.__all__
