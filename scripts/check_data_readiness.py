#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查最新日期核心数据拉取完成度命令行工具 (Check Data Readiness CLI).

用法:
    python scripts/check_data_readiness.py
    python scripts/check_data_readiness.py --json
"""

import argparse
import json
import sys
from pathlib import Path

# 将项目根目录加入模块搜索路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finance_tools.data_readiness_tracker import DataReadinessTracker


def main() -> int:
    parser = argparse.ArgumentParser(description="扫描本地底账并检查最新日期核心数据拉取完成度")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出底账快照结构")
    args = parser.parse_args()

    tracker = DataReadinessTracker()
    snapshot = tracker.inspect_latest_readiness()

    if args.json:
        print(json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(snapshot.banner_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
