"""旧回归和新测试共享的项目内临时目录与账本注入。"""

from pathlib import Path
from datetime import datetime, timezone
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


def freeze_quote_clock(test):
    """将门禁时钟固定到明确的美股开市时间，避免周末运行改变业务夹具。"""
    instant = datetime(2026, 10, 16, 14, 5, tzinfo=timezone.utc)
    binding = patch("financial_core.engines.quote_freshness_gateway.datetime", wraps=datetime)
    clock = binding.start()
    clock.now.return_value = instant
    test.addCleanup(binding.stop)
    return instant
