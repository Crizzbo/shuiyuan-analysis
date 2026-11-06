"""细分行业买方结构化知识中枢管理器 (Industry Knowledge Manager).

物理架构定界 (Layer 1: financial_core):
- 纯净底层架构，纯相对导入，零外层依赖，零网络调用;
- 单一事实来源 (SSOT)：底层统一委托 `KnowledgeRepository` 管理 `data/industry_knowledge/` 结构化配置;
- 内存级单例只读缓存，毫秒级解析响应;
- 完备防御性设计：对尚未完成 JSON 迁移的行业，无缝回退至 Taxonomy Bridge 契约，杜绝运行时中断。
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from .industry_taxonomy_bridge import IndustryTaxonomyBridge, IndustryMappingRecord
from .knowledge_repository import KnowledgeRepository, IndustryKnowledgeProfile


class IndustryKnowledgeManager:
    """行业结构化知识库加载与中枢管理器."""

    _instance: Optional["IndustryKnowledgeManager"] = None
    _taxonomy_bridge: IndustryTaxonomyBridge
    _repo: KnowledgeRepository

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._taxonomy_bridge = IndustryTaxonomyBridge()
            cls._instance._repo = KnowledgeRepository.get_instance()
        return cls._instance

    @classmethod
    def get_instance(cls) -> "IndustryKnowledgeManager":
        """获取全局单例中枢实例."""
        return cls()

    @classmethod
    def reset_cache(cls):
        """清空缓存 (测试时使用)."""
        KnowledgeRepository.reset_cache()
        cls._instance = None

    def get_profile(self, industry_id: str) -> IndustryKnowledgeProfile:
        """获取指定细分行业的高精度买方知识档案 (优先委托 KnowledgeRepository，带防御性回退)."""
        # 1. 优先命中统一知识中枢单例 (SSOT)
        repo_prof = self._repo.get_industry_knowledge(industry_id)
        if repo_prof is not None:
            return repo_prof

        # 2. 稳健回退：基于 Taxonomy Bridge 生成安全兜底档案
        rec = self._taxonomy_bridge.get_record(industry_id)
        fallback_profile = IndustryKnowledgeProfile(
            industry_id=rec.industry_id,
            industry_name_zh=rec.industry_name_zh,
            sector_id=rec.sector_id,
            sector_name_zh=rec.sector_name_zh,
            macro_sector_id=rec.macro_sector_id,
            macro_sector_name_zh=rec.macro_sector_name_zh,
            description_zh=f"{rec.industry_name_zh}通用行业基准配置",
            typical_cogs_ratio=rec.typical_cogs_ratio,
            typical_markup_ratio=rec.typical_markup_ratio,
            capex_intensity="中等偏高",
            operating_leverage_exposure="中等经营杠杆",
            typical_gross_margin_range=(0.20, 0.50),
            dio_healthy_days=90.0,
            dio_warning_days=150.0,
            rd_capitalization_max_allowed=0.10,
            top_customer_concentration_redline=0.30,
            debt_covenant_buffer_minimum_ratio=0.15,
            upstream_bottlenecks=("核心设备与原材料供应链采购周期",),
            downstream_profile="行业终端下游商业客户与消费者",
            pricing_power_verdict="受行业供需关系与竞对价格主导",
            leading_bull_triggers=("行业需求温和复苏、经营效率提升与毛利中枢修复",),
            leading_bear_defenses=("宏观流动性紧缩致使下游资本开支削减与需求不及预期",),
            core_catalyst_dimensions=("定期财务报告披露与行业权威数据发布",),
            red_flag_rules=("产成品库存增速超越营收增速 20 个百分点以上",),
            channel_and_revenue_checks=("合同负债单季大幅下滑超过 20%",),
            markdown_content="",
        )
        return fallback_profile

    def list_loaded_industries(self) -> List[str]:
        """返回当前已加载结构化知识的行业清单."""
        return sorted([k.industry_id for k in self._repo.list_industry_knowledge()])

