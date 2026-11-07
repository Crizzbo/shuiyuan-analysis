"""法证审计与风险防御业务子包 (financial_core.engines.risk_forensics).

聚合买方法证五刀穿透、信用违约与极端风险防御算法：
1. 财报法证五刀精准解剖手术刀 (Forensic Surgical Scalpel);
2. 结构化莫顿信用风险与破产概率引擎 (Merton Credit & Solvency Engine);
3. 组合非线性尾部风险与极端压力测试引擎 (Portfolio Risk & VaR/CVaR Engine);
4. 阿西莫格鲁制度约束与地缘攫取性风险引擎 (Acemoglu Institutional Risk Engine);
5. 阿吉翁创造性破坏与技术范式颠覆引擎 (Aghion Creative Destruction Engine).
"""

from ..forensic_surgical_scalpel import (
    ForensicDissectionResult,
    ForensicInputData,
    ForensicSurgicalScalpel,
)
from ..credit_risk_engine import (
    CreditRiskAndSolvencyEngine,
    CreditRiskResult,
    MertonCreditInput,
)
from ..portfolio_risk_engine import (
    FactorAttributionResult,
    PortfolioRiskAndVaREngine,
    RiskDecompositionResult,
    StressTestScenarioResult,
    VaRResult,
)
from ..acemoglu_institutional_risk_engine import (
    AcemogluInstitutionalInput,
    AcemogluInstitutionalResult,
    AcemogluInstitutionalRiskEngine,
)
from ..aghion_creative_destruction_engine import (
    AghionCreativeDestructionEngine,
    AghionDestructionInput,
    AghionDestructionResult,
)

__all__ = [
    "ForensicSurgicalScalpel",
    "ForensicInputData",
    "ForensicDissectionResult",
    "CreditRiskAndSolvencyEngine",
    "MertonCreditInput",
    "CreditRiskResult",
    "PortfolioRiskAndVaREngine",
    "VaRResult",
    "RiskDecompositionResult",
    "FactorAttributionResult",
    "StressTestScenarioResult",
    "AcemogluInstitutionalRiskEngine",
    "AcemogluInstitutionalInput",
    "AcemogluInstitutionalResult",
    "AghionCreativeDestructionEngine",
    "AghionDestructionInput",
    "AghionDestructionResult",
]
