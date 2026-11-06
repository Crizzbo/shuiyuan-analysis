"""旧回归和新测试共享的项目内临时目录与账本注入。"""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]


def project_temp(test, prefix):
    parent = ROOT / ".cache"
    parent.mkdir(exist_ok=True)
    directory = TemporaryDirectory(prefix=prefix, dir=parent)
    test.addCleanup(directory.cleanup)
    return Path(directory.name)


def isolated_facade_ledger(test, ledger):
    from financial_core.pipeline import canyon_linear_pipeline

    binding = patch.object(canyon_linear_pipeline, "PredictionLedger", return_value=ledger)
    binding.start()
    test.addCleanup(binding.stop)
