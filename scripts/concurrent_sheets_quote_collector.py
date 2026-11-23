#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Google Sheets 多表并发收集器 CLI 运行脚本与向下兼容适配器.

层级归属: Layer 4 (scripts/)
底层核心实现已迁移至 Layer 2: finance_tools.governance_and_pipeline.concurrent_sheets_quote_collector
符合工程 4 层单向依赖合规要求 (底层纯净解耦，禁止向上反向依赖)。
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 向下兼容重导出 Layer 2 核心引擎
from finance_tools.governance_and_pipeline.concurrent_sheets_quote_collector import (
    SheetShard,
    BatchCollectionResult,
    ConcurrentSheetsQuoteCollector,
    get_full_symbol,
    EXCHANGE_PREFIX_MAP,
    main,
)

if __name__ == "__main__":
    main()
