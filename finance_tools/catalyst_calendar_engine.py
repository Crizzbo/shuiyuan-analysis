# -*- coding: utf-8 -*-
"""向下兼容门面：重定向至 finance_tools.events_and_verification.catalyst_calendar_engine。

功能归属：突发事件雷达与鉴真监控流水线
业务定位：0-Token突发事件全天候监控、SHA-256密码学法定信源防伪鉴真、AI浏览器核验、买方告警调度与预期差归因
此门面确保既有脚本、测试用例与历史引用零代码修改平滑过渡。
"""

import sys
from finance_tools.events_and_verification.catalyst_calendar_engine import *
from finance_tools.events_and_verification import catalyst_calendar_engine as _impl_module

# 保持模块元属性与引用透明性
__doc__ = _impl_module.__doc__
if hasattr(_impl_module, "__all__"):
    __all__ = _impl_module.__all__
