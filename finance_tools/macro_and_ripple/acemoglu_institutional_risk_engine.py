"""向下兼容重导出层：阿西莫格鲁制度风险与主权治理溢价引擎 (Acemoglu Institutional Risk Compatibility Layer).

本模块由 financial_core.engines.acemoglu_institutional_risk_engine 承接真实实现。
"""

from financial_core.engines.acemoglu_institutional_risk_engine import (
    AcemogluInstitutionalInput,
    AcemogluInstitutionalResult,
    AcemogluInstitutionalRiskEngine,
)

__all__ = [
    "AcemogluInstitutionalInput",
    "AcemogluInstitutionalResult",
    "AcemogluInstitutionalRiskEngine",
]
