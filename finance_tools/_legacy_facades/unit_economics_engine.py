# -*- coding: utf-8 -*-
"""向下兼容门面：重定向至 finance_tools.forensics_and_valuation.unit_economics_engine。

功能归属：财务法证审计与多情景估值模型
业务定位：财务法证手术刀(受限现金/存货DIO/应收周转)、三表整合刚性平账、多情景DCF折现、单位经济学与护城河评估
此门面确保既有脚本、测试用例与历史引用零代码修改平滑过渡。
"""

import sys
from finance_tools.forensics_and_valuation.unit_economics_engine import *
from finance_tools.forensics_and_valuation import unit_economics_engine as _impl_module

# 保持模块元属性与引用透明性
__doc__ = _impl_module.__doc__
if hasattr(_impl_module, "__all__"):
    __all__ = _impl_module.__all__
