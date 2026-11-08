"""执行干净克隆可运行的源码、契约与合成回归检查。"""

from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# 本清单只选择不依赖私有财报、行情和正式账本的回归。
PORTABLE_TESTS = (
    "scripts.test_research_safety_regressions",
    "scripts.test_financial_statement_facade",
    "scripts.test_dossier_synthesis_with_facade",
    "scripts.test_release_audit",
    "scripts.test_sotp_event_penetration",
    "scripts.test_sotp_profiles",
    "scripts.test_alert_dispatcher",
    "scripts.test_evidence_verification_pipeline",
    "scripts.test_radar_dashboard_serve",
    "scripts.test_browser_verification_assistant",
    "scripts.test_supply_chain_ripple_engine",
)


def main() -> int:
    """核验核心层依赖方向及模块导入，然后运行合成测试。"""
    # 导入巡检会重载模块，在独立进程运行，保持测试中的类型身份一致。
    check_code = (
        "from scripts.verify_architecture_integrity import check_circular_imports, check_financial_core_purity\n"
        "violations = check_financial_core_purity() + check_circular_imports()\n"
        "print('\\n'.join(violations))\n"
        "raise SystemExit(bool(violations))\n"
    )
    architecture = subprocess.run([sys.executable, "-c", check_code], cwd=ROOT, check=False)
    if architecture.returncode:
        return architecture.returncode
    (ROOT / ".cache").mkdir(exist_ok=True)
    suite = unittest.defaultTestLoader.loadTestsFromNames(PORTABLE_TESTS)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
