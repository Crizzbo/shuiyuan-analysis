"""行情时效性与时区/交易时段感知门禁网关 (向下兼容重导出层).

本模块真实实现已下沉至底层纯净量化核心：financial_core.engines.quote_freshness_gateway
本文件保留用于上层报告与脚本调用的完全向下兼容。
"""

from financial_core.engines.quote_freshness_gateway import (
    QuoteVerificationResult,
    QuoteFreshnessGateway,
)

__all__ = ["QuoteVerificationResult", "QuoteFreshnessGateway"]
