"""买方投研系统四层测试分层执行器 (Tiered Test Runner).

严格遵循敏捷工程原则:
1. 支持按【单体测试 (UT)、结合测试 (IT)、功能测试 (FT)、用户测试 (UAT)】四层架构精准过滤执行;
2. 支持 --tier ut|it|ft|uat|all 命令行调度;
3. 保持与既有 unittest 标准测试用例 100% 兼容，零侵入性。
"""

import argparse
import os
import sys
import time
import unittest
from pathlib import Path

# 确保项目根目录位于 sys.path 最前端，保证所有模块正常导入
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入分类器
from list_test_cases import scan_all_test_cases


def run_tests_by_tier(tier_target: str, failfast: bool = False, verbose: int = 1):
    """根据指定层级过滤并执行测试用例."""
    scripts_dir = Path(__file__).resolve().parent
    cases = scan_all_test_cases(scripts_dir)

    target = tier_target.lower()
    selected_files = set()

    tier_map = {
        "ut": "UT (单体测试/纯单元)",
        "it": "IT (结合测试/接口集成)",
        "ft": "FT (功能测试/系统测试)",
        "uat": "UAT (用户测试/场景验收)",
    }

    if target == "all":
        selected_files = sorted(list(set(c["file"] for c in cases)))
        target_desc = "全量测试用例 (UT + IT + FT + UAT)"
    elif target in tier_map:
        matched_tier = tier_map[target]
        selected_files = sorted(list(set(c["file"] for c in cases if c["tier"] == matched_tier)))
        target_desc = matched_tier
    else:
        print(f"[错误] 非法层级参数: '{tier_target}'. 可选值为: ut, it, ft, uat, all")
        sys.exit(1)

    print("=" * 80)
    print(f"[分层测试] 启动买方投研系统敏捷分层测试执行器")
    print(f"[目标层级] 【{target_desc}】")
    print(f"[测试文件] 共 {len(selected_files)} 个")
    print("=" * 80)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for fname in selected_files:
        mod_name = fname.replace(".py", "")
        try:
            mod_suite = loader.loadTestsFromName(mod_name)
            suite.addTests(mod_suite)
        except Exception as e:
            print(f"  [警告] 加载测试模块 {mod_name} 失败: {e}")

    total_test_count = suite.countTestCases()
    print(f"[用例组装] 组装完成可执行测试用例: 共 {total_test_count} 项")
    print("-" * 80)

    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=verbose, failfast=failfast)
    result = runner.run(suite)
    elapsed = time.time() - start_time

    print("\n" + "=" * 80)
    print(f"[执行报告] 分层测试执行汇总报告")
    print(f"  [耗时] {elapsed:.2f} 秒")
    print(f"  [总数] {result.testsRun} 项")
    print(f"  [失败] {len(result.failures)} 项")
    print(f"  [错误] {len(result.errors)} 项")
    print(f"  [跳过] {len(result.skipped)} 项")
    if result.wasSuccessful():
        print(f"[验收结论] 100% 全部通过 (PASS)")
    else:
        print(f"[验收结论] 存在失败用例，请排查上文详情")
    print("=" * 80)

    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="买方投研系统四层测试分层执行器")
    parser.add_argument(
        "--tier",
        type=str,
        default="ut",
        choices=["ut", "it", "ft", "uat", "all"],
        help="测试层级: ut(单体测试), it(结合测试), ft(功能测试), uat(用户场景测试), all(全量)",
    )
    parser.add_argument("--failfast", action="store_true", help="遇首个失败立即停止")
    parser.add_argument("-v", "--verbose", type=int, default=1, help="详细输出等级 (1或2)")

    args = parser.parse_args()
    run_tests_by_tier(args.tier, failfast=args.failfast, verbose=args.verbose)
