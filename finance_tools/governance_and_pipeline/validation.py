"""所有计算共用的输入校验；禁止隐式百分比转换和缺失值填零。"""

import math


def number(value, name, *, positive=False, nonnegative=False):
    """只接受有限实数，排除 Python 会当作整数处理的布尔值。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} 必须是有限数值，不能是百分号字符串或缺失值")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} 必须有限")
    if positive and result <= 0 or nonnegative and result < 0:
        raise ValueError(f"{name} 超出允许范围")
    return result


def rate(value, name, *, discount=False):
    """采用小数比例：0.1 表示 10%；大于等于 1 的输入需要另行评估。"""
    value = number(value, name)
    if not -1 < value < 1 or discount and value <= 0:
        raise ValueError(f"{name} 必须在 (-1,1) 内，折现率必须为正")
    return value


def sequence(values, name, *, rates=False):
    """序列不得为空；逐项检查，保留负现金流的经济含义。"""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError(f"{name} 必须是非空序列")
    check = rate if rates else number
    return [check(value, f"{name}[{i}]") for i, value in enumerate(values)]


def finite_output(value):
    """递归拒绝溢出、无穷和 NaN，避免伪造可用计算结果。"""
    if isinstance(value, dict):
        for item in value.values():
            finite_output(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            finite_output(item)
    elif isinstance(value, (int, float)):
        number(value, "计算输出")
    return value
