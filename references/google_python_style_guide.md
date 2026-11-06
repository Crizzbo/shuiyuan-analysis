# Google Python 编程风格指南与水源投研工程落地规范 (Google Python Style Guide)

> **权威来源**：Google Official Python Style Guide  
> **落地目标**：确立水源投研系统全局统一的代码风格、类型安全、文档标准与异常防御规范。

---

## 一、 命名规范 (Naming Conventions)

| 元素类型 | 命名规则 | 示例 | 禁用反例 |
|---|---|---|---|
| **模块 (Module / File)** | 全小写 + 下划线 | `options_causal_analyzer.py` | `OptionsAnalyzer.py`, `opt-analyzer.py` |
| **包名 (Package / Dir)** | 全小写短名词 | `financial_core`, `engines` | `FinancialCore`, `my_engines` |
| **类名 (Class)** | 大驼峰 (CapWords / PascalCase) | `OptionsCausalAnalyzer`, `OptionContractInput` | `options_causal_analyzer`, `optionsAnalyzer` |
| **函数与方法 (Function / Method)** | 全小写 + 下划线 | `calculate_break_even_price()` | `calculateBreakEvenPrice()`, `calc_break_even` |
| **常量 (Constant)** | 全大写 + 下划线 | `MAX_KELLY_CAPITAL_RATIO = 0.02` | `max_kelly_ratio = 0.02` |
| **变量与字段 (Variable / Field)** | 全小写 + 下划线 | `underlying_spot_price` | `UnderlyingSpotPrice`, `spotP` |
| **私有成员 (Internal / Private)** | 单下划线前缀 | `_validate_market_session()` | `validateMarketSession_()` |

---

## 二、 导入规范与分组 (Imports)

所有 Python 文件头部的导入语句必须严格分为三组，每组之间空一行，禁止跨组混写：

```python
# 1. Python 标准库 (Standard Library Imports)
import math
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# 2. 第三方第三方库 (Third-Party Imports)
import jsonschema
import numpy as np

# 3. 本地与工程内部纯净核心库 (Local Application Imports)
from financial_core.models.accounting import FinancialStatement
from financial_reporting.quote_freshness_gateway import QuoteFreshnessGateway
```

### 导入红线：
- **严禁通配符导入**：严禁 `from module import *`，必须显式列出需要的类与函数；
- **纯相对导入优先**：`financial_core` 内部模块之间必须使用相对导入（如 `from .dcf_valuation_engine import DCFValuationEngine`）。

---

## 三、 Google 风格文档字符串 (Google-style Docstrings)

每个公有类、方法与函数必须包含符合 Google 风格的 Docstring，严格包含业务概述、`Args:`、`Returns:`、`Raises:`：

```python
def analyze_option_contract(
    contract_input: OptionContractInput,
    scenarios: UnderlyingScenarios,
) -> OptionAnalysisResult:
    """全面推导期权合约因果损益分布与仓位控制上限.

    严格基于标的现价、交易时段时效与行权盘口展开五级因果推导，
    拆解内在价值与纯时间价值，并计算三态情景到期损益与四分之一凯利仓位.

    Args:
        contract_input: 期权合约前项真实输入对象，包含现价、时效、行权价、权利金等.
        scenarios: 标的股票到期三态价格分布假设 (悲观/基准/乐观，概率守恒).

    Returns:
        包含实值虚值状态、保本点、三态收益率、期望盈亏与凯利仓位比重的全息结果对象.

    Raises:
        ValueError: 当权利金小于等于零、距离到期天数小于零或情景概率之和不为 1 时抛出.
        RuntimeError: 当标的现价数据超期被时效门禁硬阻断时抛出.
    """
```

---

## 四、 强类型注解 (Type Annotations, PEP 484)

1. 所有函数的参数与返回值必须提供显式类型注解；
2. 复合类型必须使用 `typing` 模块的规范表达：
   - 允许为 None 的值必须用 `Optional[T]` 显式声明；
   - 字典与列表必须声明键值类型：`Dict[str, Any]`、`List[float]`；
3. 数据传输对象推荐使用不可变数据类 `@dataclass(frozen=True)`，保证多线程与批处理中的线程安全与单一事实来源。

---

## 五、 异常处理与防御性编程 (Exception Handling)

1. **严禁裸写 `except:`**：
   必须显式捕获具体的预期异常（如 `except (KeyError, ValueError) as err:`）；
2. **金融数学除零与边界防御**：
   - 所有除法运算前必须前置断言除数不为零；
   - 资产价值、价格与到期收益必须有下限保护（股票价格下界为 0.0，体现股东有限责任）；
3. **禁止静默吞噬严重错误**：
   在关键金融计算中，若输入非法，必须明确抛出带有详细上下文信息的自定义异常，严禁返回假数据或静默 `pass`。

---

## 六、 格式与排版规范 (Formatting)

1. **缩进**：严格使用 4 个空格缩进，禁止使用制表符 (Tab)；
2. **行宽**：最大字符行宽控制在 100 字符以内（长表达式与长字符串必须换行对齐）；
3. **不可变默认参数**：严禁在函数默认入参中使用可变对象（如 `def func(items=[]):` 是严重的 bug，必须写为 `def func(items: Optional[List[str]] = None):`并在函数内初始化）。
