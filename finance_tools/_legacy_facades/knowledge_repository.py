# -*- coding: utf-8 -*-
"""向下兼容门面：重定向至 finance_tools.governance_and_pipeline.knowledge_repository。

功能归属：数据底账、时效门禁与基础设施管道
业务定位：数据完备度追踪、行情交易时钟时效门禁、指标管道、不可篡改预测账本、复盘演进与微观资金流监测
此门面确保既有脚本、测试用例与历史引用零代码修改平滑过渡。
"""

import sys
from finance_tools.governance_and_pipeline.knowledge_repository import *
from finance_tools.governance_and_pipeline import knowledge_repository as _impl_module

# 保持模块元属性与引用透明性
__doc__ = _impl_module.__doc__
if hasattr(_impl_module, "__all__"):
    __all__ = _impl_module.__all__
