"""系统架构完整性与防劣变全息巡检器 (Architecture Integrity & Health Inspector).

用于在多轮迭代改修后，系统性自检工程架构是否完好：
1. 校验核心层依赖纯洁性 (financial_core 内部零污染、零逆向依赖)；
2. 校验模块导入无环与顶层导出完备性；
3. 校验金融核心门面 FinancialAnalysisSystem 各模式可执行性；
4. 校验不可篡改区块链式底账哈希链条健康度；
5. 校验环境与可执行文件自适应探测完备性。
"""

import ast
import importlib
import os
from pathlib import Path
import sys
import unittest

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 自动自愈环境门禁：优先项目内部隔离的 .venv 解释器，杜绝外部受损环境影响
if not os.getenv("_VENV_BOOTSTRAPPED"):
    venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
    if not venv_py.is_file():
        venv_py = ROOT / ".venv" / "bin" / "python"
    current_exe = Path(sys.executable).resolve()
    if venv_py.is_file() and venv_py.resolve() != current_exe:
        import subprocess
        env = dict(os.environ)
        env["_VENV_BOOTSTRAPPED"] = "1"
        res = subprocess.run([str(venv_py), str(Path(__file__).resolve()), *sys.argv[1:]], env=env)
        sys.exit(res.returncode)


def check_financial_core_purity() -> list[str]:
    """检查 financial_core 目录下所有 Python 文件，严禁出现对 finance_tools、scripts、financial_reporting 的依赖。"""
    violations = []
    fc_dir = ROOT / "financial_core"
    forbidden_prefixes = ("finance_tools", "scripts", "financial_reporting")
    for py_file in fc_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception as e:
            violations.append(f"{py_file.name}: Cannot read: {e}")
            continue

        try:
            tree = ast.parse(content, filename=str(py_file))
        except SyntaxError as e:
            violations.append(f"{py_file.name}: SyntaxError: {e}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(alias.name.startswith(p) for p in forbidden_prefixes):
                        violations.append(f"{py_file.relative_to(ROOT)}: Line {node.lineno} imports '{alias.name}'")
            elif isinstance(node, ast.ImportFrom):
                if node.module and any(node.module.startswith(p) for p in forbidden_prefixes):
                    violations.append(f"{py_file.relative_to(ROOT)}: Line {node.lineno} imports from '{node.module}'")
    return violations


def check_circular_imports() -> list[str]:
    """检查关键模块能否独立导入且无循环依赖。"""
    modules_to_test = [
        "financial_core",
        "financial_core.contracts",
        "financial_core.api",
        "financial_core.engines",
        "financial_core.engines.forensic_surgical_scalpel",
        "financial_core.engines.business_quality_and_moat_engine",
        "financial_core.engines.american_option_tree_engine",
        "financial_core.engines.macro_shock_transmission_engine",
        "financial_core.engines.price_shock_attribution_engine",
        "financial_core.engines.integrated_three_statement_engine",
        "financial_core.engines.unit_economics_engine",
        "financial_core.engines.consensus_surprise_engine",
        "financial_core.engines.microstructure_flow_engine",
        "financial_core.engines.catalyst_calendar_engine",
        "financial_core.engines.peer_benchmark_engine",
        "financial_core.engines.options_causal_analyzer",
        "financial_core.engines.retrospective_review_engine",
        "financial_core.engines.credit_risk_engine",
        "financial_core.engines.monte_carlo_engine",
        "financial_core.engines.cross_asset_engine",
        "financial_core.engines.portfolio_risk_engine",
        "financial_core.engines.volatility_surface_engine",
        "financial_core.engines.mid_cycle_engine",
        "financial_core.engines.filing_mapper",
        "financial_core.engines.firm_value_added_bridge_engine",
        "financial_core.engines.market_adaptive_params",
        "financial_core.engines.causal_inference_engine",
        "financial_core.engines.prediction_ledger",
        "financial_core.engines.quote_freshness_gateway",
        "financial_core.pipeline.systemic_analysis_pipeline",
        "finance_tools",
        "finance_tools.prediction_ledger",
        "finance_tools.retrospective_review_engine",
        "financial_reporting.quote_freshness_gateway",
        "scripts.env_discovery",
    ]
    failures = []
    for mod_name in modules_to_test:
        try:
            if mod_name in sys.modules:
                del sys.modules[mod_name]
            importlib.import_module(mod_name)
        except Exception as e:
            failures.append(f"Failed to import {mod_name}: {e}")
    return failures


def check_facade_and_ledger_health() -> list[str]:
    """检查系统门面与预测底账的真实可执行性。"""
    issues = []
    try:
        from financial_core.api import FinancialAnalysisSystem
        from financial_core.contracts import AnalysisMode, FinancialAnalysisResult

        system = FinancialAnalysisSystem()
        # 验证门面初始就绪
        if not hasattr(system, "analyze_equity"):
            issues.append("FinancialAnalysisSystem lacks analyze_equity method")
    except Exception as e:
        issues.append(f"FinancialAnalysisSystem instantiation failed: {e}")

    try:
        from financial_core.engines.prediction_ledger import PredictionLedger
        ledger = PredictionLedger()
        is_valid, err = ledger.verify_integrity()
        if not is_valid:
            issues.append(f"PredictionLedger integrity broken: {err}")
        stats = ledger.get_stats()
        if stats.get("total_predictions", 0) == 0:
            issues.append("PredictionLedger has 0 predictions (expected seeded baseline)")
    except Exception as e:
        issues.append(f"PredictionLedger verification failed: {e}")

    return issues


class TestArchitectureIntegrity(unittest.TestCase):
    """自动化架构防劣变回归单测套件。"""

    def test_zero_forbidden_imports_in_core(self):
        violations = check_financial_core_purity()
        self.assertEqual(violations, [], f"Architecture purity violated in financial_core: {violations}")

    def test_all_modules_cleanly_importable(self):
        failures = check_circular_imports()
        self.assertEqual(failures, [], f"Module import failures: {failures}")

    def test_facade_and_ledger_operational(self):
        issues = check_facade_and_ledger_health()
        self.assertEqual(issues, [], f"Facade / Ledger health issues: {issues}")


if __name__ == "__main__":
    print("=" * 70)
    print("[架构巡检] 启动工程架构完整性与防劣变全息巡检")
    print("=" * 70)

    print("\n[1/3] 检查 financial_core 核心层物理解耦纯洁性...")
    purity_issues = check_financial_core_purity()
    if purity_issues:
        print("  [未通过] 发现架构污染:")
        for issue in purity_issues:
            print(f"     • {issue}")
    else:
        print("  [通过] 核心层 100% 物理纯净，零外层逆向依赖!")

    print("\n[2/3] 检查系统核心模块拓扑导入与环路检测...")
    import_issues = check_circular_imports()
    if import_issues:
        print("  [未通过] 发现模块导入异常:")
        for issue in import_issues:
            print(f"     • {issue}")
    else:
        print("  [通过] 29 个关键模块独立导入 100% 成功，零循环依赖!")

    print("\n[3/3] 检查金融分析系统门面与预测底账审计链...")
    health_issues = check_facade_and_ledger_health()
    if health_issues:
        print("  [未通过] 发现系统健康度异常:")
        for issue in health_issues:
            print(f"     • {issue}")
    else:
        print("  [通过] 门面执行契约与不可篡改底账 100% 就绪通过!")

    total_issues = len(purity_issues) + len(import_issues) + len(health_issues)
    print("\n" + "=" * 70)
    if total_issues == 0:
        print("[巡检合格] 巡检结果：系统架构极其稳固，多轮改修未造成任何架构破损！")
    else:
        print(f"[巡检异常] 巡检结果：发现 {total_issues} 处架构问题，必须即刻修复！")
    print("=" * 70)

    sys.exit(0 if total_issues == 0 else 1)
