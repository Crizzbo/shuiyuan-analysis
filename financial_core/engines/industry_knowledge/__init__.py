"""行业知识图谱、护城河与因果推理业务子包 (financial_core.engines.industry_knowledge).

聚合行业垂直认知、因果传导图谱与护城河定量算法：
1. 行业知识图谱推理与因果网络引擎 (Knowledge Graph Engine);
2. 行业知识库全生命周期管理器 (Industry Knowledge Manager & Knowledge Repository);
3. 行业因果策略注册表与微观传导链条 (Industry Causal Strategy Registry);
4. 商业品质、所有者收益与巴菲特护城河量化引擎 (Business Quality & Moat Engine);
5. 行业权威行业分类与映射网桥 (Industry Taxonomy Bridge);
6. 行业商品与服务价格冲击网桥 (Industry Price Shock Bridge);
7. 计量级因果推断引擎 (Quantitative Causal Inference Engine);
8. 单元经济学与创新资产价值模型 (Unit Economics Engine);
9. 可比公司同业对标与竞争格局引擎 (Peer Benchmark Engine).
"""

from ..knowledge_graph_engine import KnowledgeGraphEngine
from ..knowledge_repository import (
    BusinessModelProfile,
    IndustryKnowledgeProfile,
    IndustryNodeProfile,
    IndustryRuleProfile,
    KnowledgeRepository,
    MetricCatalogProfile,
)
from ..industry_knowledge_manager import IndustryKnowledgeManager
from ..industry_causal_registry import (
    IndustryCausalFacts,
    IndustryCausalStrategyRegistry,
)
from ..business_quality_and_moat_engine import (
    BusinessQualityAndMoatEngine,
    LiquorConsumerFleshInput,
    OwnerEarningsInput,
    TechHardwareFleshInput,
)
from ..industry_taxonomy_bridge import (
    IndustryMappingRecord,
    IndustryTaxonomyBridge,
)
from ..industry_price_shock_bridge import (
    IndustryPriceShockBridge,
    IndustryPriceShockResult,
)
from ..causal_inference_engine import (
    CausalInferenceResult,
    QuantitativeCausalInferenceEngine,
)
from ..unit_economics_engine import (
    PipelineAsset,
    UnitEconomicsEngine,
)
from ..peer_benchmark_engine import (
    CompanyPeerMetrics,
    PeerBenchmarkEngine,
    PeerBenchmarkResult,
)

__all__ = [
    "KnowledgeGraphEngine",
    "KnowledgeRepository",
    "IndustryKnowledgeManager",
    "BusinessModelProfile",
    "MetricCatalogProfile",
    "IndustryNodeProfile",
    "IndustryRuleProfile",
    "IndustryKnowledgeProfile",
    "IndustryCausalStrategyRegistry",
    "IndustryCausalFacts",
    "BusinessQualityAndMoatEngine",
    "OwnerEarningsInput",
    "LiquorConsumerFleshInput",
    "TechHardwareFleshInput",
    "IndustryTaxonomyBridge",
    "IndustryMappingRecord",
    "IndustryPriceShockBridge",
    "IndustryPriceShockResult",
    "QuantitativeCausalInferenceEngine",
    "CausalInferenceResult",
    "UnitEconomicsEngine",
    "PipelineAsset",
    "PeerBenchmarkEngine",
    "CompanyPeerMetrics",
    "PeerBenchmarkResult",
]
