"""CI/CD 自动化集成门禁与预提交拦截器 (run_ci.py).

基于 pstack 严谨工程体系 (Thermos / 1k-Line Rule / Deslop / Boundary Discipline / Prove It Works):
分级执行全系统端到端门禁断言：
1. Stage 1: 架构完整性与 pstack 零追踪防御巡检 (verify_architecture_integrity.py)
2. Stage 2: 四大法定项目治理回归硬门禁 (test_data_store, validate_knowledge_structure, test_research_contract, test_industry_mapping)
3. Stage 3: 前端工程生产构建与 TypeScript 静态类型编译 (npm run build --prefix web)
4. Stage 4: 核心金融计算引擎、终端 API 契约与分批平账管道单元测试
5. Stage 5: (可选 --all) 全盘全量自动化单元测试发现与执行
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 快速便携核心回归测试清单 (无外部依赖、本地秒级完成、覆盖全部核心层与终端契约)
CORE_PORTABLE_TESTS = (
    "scripts.test_research_safety_regressions",
    "scripts.test_financial_statement_facade",
    "scripts.test_dossier_synthesis_with_facade",
    "scripts.test_release_audit",
    "scripts.test_sotp_event_penetration",
    "scripts.test_sotp_profiles",
    "scripts.test_historical_model_validation",
    "scripts.test_watersource_terminal_api",
    "scripts.test_normalized_universe_reconciliation",
    "scripts.test_sepa_buy_signal_engine",
)

MANDATORY_GOVERNANCE_SCRIPTS = (
    ("数据底账不可篡改审计", [sys.executable, "scripts/test_data_store.py"]),
    ("知识库结构与项目边界校验", [sys.executable, "scripts/validate_knowledge_structure.py"]),
    ("六步研究安全契约回归", [sys.executable, "scripts/test_research_contract.py"]),
    ("41行业映射与因子网格校验", [sys.executable, "scripts/test_industry_mapping.py"]),
)


def print_stage_banner(stage_num: int, title: str) -> None:
    print(f"\n{'=' * 72}")
    print(f"[{stage_num}] {title}")
    print(f"{'=' * 72}")


def run_stage_architecture() -> bool:
    print_stage_banner(1, "架构完整性与 pstack 零追踪防御巡检")
    cmd = [sys.executable, "scripts/verify_architecture_integrity.py"]
    res = subprocess.run(cmd, cwd=ROOT, check=False)
    if res.returncode != 0:
        print("\n[CI 失败] Stage 1 架构完整性巡检未通过！")
        return False
    print("[CI 通过] Stage 1 架构完整性与 Git/pstack 隔离防御 100% 合规。")
    return True


def run_stage_governance() -> bool:
    print_stage_banner(2, "四大法定项目治理回归硬门禁")
    for name, cmd in MANDATORY_GOVERNANCE_SCRIPTS:
        t0 = time.time()
        print(f"  --> 运行 {name}...")
        res = subprocess.run(cmd, cwd=ROOT, check=False)
        elapsed = time.time() - t0
        if res.returncode != 0:
            print(f"\n[CI 失败] 治理门禁 [{name}] 执行失败 (耗时 {elapsed:.2f}s)！")
            return False
        print(f"  [通过] {name} (耗时 {elapsed:.2f}s)")
    print("[CI 通过] Stage 2 四大治理回归全部 100% 通过。")
    return True


def run_stage_frontend() -> bool:
    print_stage_banner(3, "前端工程生产构建与 TypeScript 静态类型编译")
    web_dir = ROOT / "web"
    if not web_dir.exists():
        print("  [跳过] 未检测到 web/ 前端目录。")
        return True

    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    cmd = [npm_cmd, "run", "build", "--prefix", "web"]
    print(f"  --> 执行命令: {' '.join(cmd)}")
    t0 = time.time()
    res = subprocess.run(cmd, cwd=ROOT, check=False)
    elapsed = time.time() - t0

    if res.returncode != 0:
        print(f"\n[CI 失败] 前端构建存在 TypeScript 类型错误或编译异常 (耗时 {elapsed:.2f}s)！")
        return False

    print(f"[CI 通过] Stage 3 前端构建与静态检查完全通过 (耗时 {elapsed:.2f}s，0 错误)。")
    return True


def run_stage_core_tests() -> bool:
    print_stage_banner(4, "核心金融计算引擎、终端 API 契约与分批平账管道单元测试")
    (ROOT / ".cache").mkdir(exist_ok=True)
    t0 = time.time()
    suite = unittest.defaultTestLoader.loadTestsFromNames(CORE_PORTABLE_TESTS)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.time() - t0

    if not result.wasSuccessful():
        print(f"\n[CI 失败] 核心单元测试未全部通过 (耗时 {elapsed:.2f}s)！")
        return False

    print(f"[CI 通过] Stage 4 核心单元测试 {result.testsRun} 项全部通过 (耗时 {elapsed:.2f}s)。")
    return True


def run_stage_all_tests() -> bool:
    print_stage_banner(5, "全盘全量单元测试发现与执行 (--all 模式)")
    t0 = time.time()
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(ROOT / "scripts"), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    elapsed = time.time() - t0

    if not result.wasSuccessful():
        print(f"\n[CI 失败] 全量测试套件未完全通过 (耗时 {elapsed:.2f}s)！")
        return False

    print(f"[CI 通过] Stage 5 全盘单测 {result.testsRun} 项 100% 通过 (耗时 {elapsed:.2f}s)。")
    return True


def install_git_pre_commit_hook() -> int:
    hooks_dir = ROOT / ".git" / "hooks"
    if not hooks_dir.exists():
        print(f"[错误] 找不到 Git hooks 目录: {hooks_dir}")
        return 1

    hook_file = hooks_dir / "pre-commit"
    hook_script = (
        "#!/bin/sh\n"
        "# 由 scripts/run_ci.py 自动生成的预提交门禁钩子\n"
        "echo \"[Pre-Commit] 触发本地 CI 快速流水线自检...\"\n"
        "python scripts/run_ci.py --fast\n"
        "EXIT_CODE=$?\n"
        "if [ $EXIT_CODE -ne 0 ]; then\n"
        "    echo \"\\n[Pre-Commit 拦截] 架构门禁、前端构建或单元测试未通过，提交已终止！\"\n"
        "    exit $EXIT_CODE\n"
        "fi\n"
        "echo \"[Pre-Commit] 全部门禁自检通过，允许创建 Git 提交。\\n\"\n"
        "exit 0\n"
    )

    hook_file.write_text(hook_script, encoding="utf-8")
    try:
        # 在类 Unix / Git Bash 环境下赋予可执行权限
        import os
        os.chmod(hook_file, 0o755)
    except Exception:
        pass

    print(f"[成功] Git pre-commit 钩子已成功安装至: {hook_file}")
    print("每次执行 git commit 时，将自动前置执行 `python scripts/run_ci.py --fast`！")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="水泉终端 CI/CD 自动化集成门禁与预提交拦截器")
    parser.add_argument("--fast", action="store_true", default=True, help="快速门禁模式 (默认，~10s 完成前4阶段检查)")
    parser.add_argument("--all", action="store_true", help="全量回归模式 (运行全部 128 个测试模块)")
    parser.add_argument("--skip-frontend", action="store_true", help="跳过前端构建检查")
    parser.add_argument("--frontend-only", action="store_true", help="仅运行前端构建与类型检查")
    parser.add_argument("--architecture-only", action="store_true", help="仅运行架构完整性与 pstack 隔离巡检")
    parser.add_argument("--install-pre-commit", action="store_true", help="安装 Git pre-commit 钩子")

    args = parser.parse_args()

    if args.install_pre_commit:
        return install_git_pre_commit_hook()

    t_start = time.time()
    print("=" * 72)
    print("启动水泉终端 CI/CD 集成门禁自动化自检 (pstack 严谨工程标准)")
    print(f"工作目录: {ROOT}")
    print("=" * 72)

    if args.architecture_only:
        return 0 if run_stage_architecture() else 1

    if args.frontend_only:
        return 0 if run_stage_frontend() else 1

    # 1. 架构完整性巡检
    if not run_stage_architecture():
        return 1

    # 2. 四大治理回归硬门禁
    if not run_stage_governance():
        return 2

    # 3. 前端工程构建与静态检查
    if not args.skip_frontend:
        if not run_stage_frontend():
            return 3

    # 4. 核心金融计算与便携单测
    if not run_stage_core_tests():
        return 4

    # 5. 可选全量回归
    if args.all:
        if not run_stage_all_tests():
            return 5

    total_time = time.time() - t_start
    print("\n" + "=" * 72)
    print(f"[CI 验收合格] 所有阶段检查 100% PASS！总耗时: {total_time:.2f}s")
    print("系统处于极佳健康状态，完全满足发布与提交标准！")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
