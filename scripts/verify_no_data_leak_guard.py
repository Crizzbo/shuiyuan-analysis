#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""云端 GitHub 仓库防数据泄露物理守卫 (verify_no_data_leak_guard.py).

严格守护用户铁律：“云端 GitHub 仓库只放加工冷热数据的工具和方法，绝不推送任何数据文件！”
功能：
1. 扫描 Git 已追踪列表 (git ls-files) 与当前待提交暂存区 (git diff --cached --name-only)；
2. 调用底层 DataLifecycleEngine.check_paths_for_data_leak 核验每一条路径；
3. 发现任何 data/、data_max/、*.gz、*.sqlite3、*.blob、CIK*.json 等数据文件即刻非零退出拦截；
4. 支持 `--install-hook` 将本守卫挂载为本地 `.git/hooks/pre-commit`，在物理层面永久锁死防误推防线。
"""

import argparse
from pathlib import Path
import subprocess
import sys
from typing import List

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finance_tools.governance_and_pipeline.data_lifecycle_manager import DataLifecycleEngine


def _git_lines(args: List[str]) -> List[str]:
    res = subprocess.run(
        ["git", *args],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if res.returncode != 0:
        return []
    return [line.strip() for line in res.stdout.splitlines() if line.strip()]


def run_leak_guard(staged_only: bool = False) -> int:
    """执行 Git 路径防数据泄露检查."""
    engine = DataLifecycleEngine()

    if staged_only:
        paths_to_check = _git_lines(["diff", "--cached", "--name-only", "--diff-filter=ACMR"])
        scope_label = "当前待提交暂存区 (Staged Changes)"
    else:
        tracked = _git_lines(["ls-files"])
        staged = _git_lines(["diff", "--cached", "--name-only", "--diff-filter=ACMR"])
        paths_to_check = sorted(set(tracked) | set(staged))
        scope_label = "全量已追踪文件 + 暂存区 (Tracked & Staged)"

    result = engine.check_paths_for_data_leak(paths_to_check)

    print("=" * 72)
    print(f"[防数据泄露守卫] 检查范围: {scope_label}")
    print(f"已校验文件数量: {result.checked_paths_count}")
    if result.is_clean:
        print(f"[通过] {result.summary_message}")
        print("=" * 72)
        return 0

    print(f"[拦截失败] {result.summary_message}")
    for vp in result.violating_paths:
        print(f"  ❌ 违禁路径: {vp} -> {result.violation_reasons.get(vp)}")
    print("请执行 `git reset HEAD <file>` 撤回数据文件并确认 .gitignore 规则有效。")
    print("=" * 72)
    return 1


def install_pre_commit_hook() -> int:
    """将本守卫安装为本地 Git pre-commit 自动拦截钩子."""
    git_dir = PROJECT_ROOT / ".git"
    if not git_dir.is_dir():
        print("[失败] 当前目录不是有效的 Git 仓库，无法安装 pre-commit 钩子。")
        return 1

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_file = hooks_dir / "pre-commit"

    hook_script = (
        "#!/bin/sh\n"
        "# 自动生成的云端防数据泄露门禁：严禁向 GitHub 提交任何本地冷/温/热数据\n"
        "python scripts/verify_no_data_leak_guard.py --staged-only\n"
        "if [ $? -ne 0 ]; then\n"
        "  echo \"[拦截] 检测到违禁本地数据文件，提交已自动终止！\"\n"
        "  exit 1\n"
        "fi\n"
    )
    hook_file.write_text(hook_script, encoding="utf-8")
    print(f"[成功] 已安装物理防数据泄露 pre-commit 钩子至: {hook_file}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="GitHub 云端仓库防数据泄露检查守卫")
    parser.add_argument("--staged-only", action="store_true", help="仅检查本次 git commit 暂存区文件")
    parser.add_argument("--install-hook", action="store_true", help="将本守卫安装到本地 .git/hooks/pre-commit")
    args = parser.parse_args()

    if args.install_hook:
        return install_pre_commit_hook()
    return run_leak_guard(staged_only=args.staged_only)


if __name__ == "__main__":
    sys.exit(main())
