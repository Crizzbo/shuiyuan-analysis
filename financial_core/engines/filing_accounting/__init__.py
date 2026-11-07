"""官方财报底账与会计平账映射业务子包 (financial_core.engines.filing_accounting).

聚合官方原始披露三表底账、会计恒等式刚性平账与标准化映射：
1. SEC EDGAR / EDINET 官方底账标准映射器 (Official Filing Mapper);
2. SEC EDGAR 官方披露采集引擎 (Official SEC EDGAR Collector);
3. 财务报表全息门面 (Financial Statement Facade);
4. 动态钩稽综合三表预测引擎 (Integrated Three-Statement Engine);
5. 跨周期标准化对账与进程互斥状态机 (Normalized Reconciliation Engine).
"""

from ..filing_mapper import (
    BalanceSheetIdentityError,
    IncompleteFilingFactError,
    OfficialFilingMapper,
)
from ..sec_edgar_collector import (
    OfficialSecEdgarCollector,
    SecExtractedFinancialFacts,
)
from ..financial_statement_facade import (
    FinancialStatementFacade,
    NormalizedFinancialProfile,
)
from ..integrated_three_statement_engine import (
    BaselineFinancials,
    IntegratedThreeStatementEngine,
)
from ..normalized_reconciliation_engine import (
    NormalizedReconciliationEngine,
    NormalizedReconciliationStateManager,
    ProcessLockError,
    ReconciliationProcessLock,
    ReconciliationRecord,
)

__all__ = [
    "OfficialFilingMapper",
    "BalanceSheetIdentityError",
    "IncompleteFilingFactError",
    "OfficialSecEdgarCollector",
    "SecExtractedFinancialFacts",
    "FinancialStatementFacade",
    "NormalizedFinancialProfile",
    "IntegratedThreeStatementEngine",
    "BaselineFinancials",
    "NormalizedReconciliationEngine",
    "NormalizedReconciliationStateManager",
    "ReconciliationProcessLock",
    "ReconciliationRecord",
    "ProcessLockError",
]
