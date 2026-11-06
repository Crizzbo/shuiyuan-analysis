"""金融知识库统一只读加载与中枢中介 (Knowledge Repository & Registry).

物理架构定界 (Layer 1: financial_core):
- 纯净底层架构，只依赖标准库，零外层工具/脚本/报告依赖，零网络调用；
- 单一事实来源 (SSOT)：统一加载管理 `knowledge/` 结构化配置 (.json) 与深度投研文档 (.md)；
- 采用选项 A 架构：JSON 管理机器结构化元数据与指标映射，MD 承载高质感深度业务分析；
- 内存级单例只读缓存，毫秒级解析响应；
- 零硬编码绝对路径：通过项目根目录相对路径解析。
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple


@dataclass(frozen=True)
class MetricCatalogProfile:
    """法定核心指标定义契约."""
    metric_id: str
    name: str
    unit: str
    definition: str = ""
    applicability: str = ""
    cadence: str = "quarterly"
    source_candidates: str = ""


@dataclass(frozen=True)
class BusinessModelProfile:
    """商业模式全息知识档案契约."""
    model_id: str
    name: str
    status: str
    profile_path: str
    metric_ids: Tuple[str, ...]
    markdown_content: str = ""

    @property
    def has_deep_research_markdown(self) -> bool:
        """是否包含买方深度研究文档."""
        return bool(self.markdown_content and len(self.markdown_content.strip()) > 50)


@dataclass(frozen=True)
class IndustryNodeProfile:
    """行业分类树状拓扑节点契约."""
    industry_id: str
    name: str
    level: str
    parent_id: Optional[str]
    business_model_ids: Tuple[str, ...]
    profile_path: str


@dataclass(frozen=True)
class IndustryRuleProfile:
    """41 细分行业买方估值路线与反证规则契约."""
    industry_id: str
    status: str
    statistical_validation_status: str
    metric_ids: Tuple[str, ...]
    required_segmentation: Tuple[str, ...]
    valuation_route: str
    counterevidence: str
    evidence_refs: Tuple[str, ...]
    judgment_improving: str = ""
    judgment_deteriorating: str = ""
    judgment_unknown: str = ""
    drawdown_policy: str = ""


@dataclass(frozen=True)
class IndustryKnowledgeProfile:
    """细分行业全息知识档案契约 (JSON结构化元数据 + Markdown深度研报上下文)."""
    industry_id: str
    industry_name_zh: str
    sector_id: str
    sector_name_zh: str
    macro_sector_id: str
    macro_sector_name_zh: str
    description_zh: str

    # 经济结构
    typical_cogs_ratio: float
    typical_markup_ratio: float
    capex_intensity: str
    operating_leverage_exposure: str
    typical_gross_margin_range: Tuple[float, float]

    # 金融与风控门禁
    dio_healthy_days: float
    dio_warning_days: float
    rd_capitalization_max_allowed: float
    top_customer_concentration_redline: float
    debt_covenant_buffer_minimum_ratio: float

    # 产业链结构
    upstream_bottlenecks: Tuple[str, ...]
    downstream_profile: str
    pricing_power_verdict: str

    # 买方因果与情景
    leading_bull_triggers: Tuple[str, ...]
    leading_bear_defenses: Tuple[str, ...]
    core_catalyst_dimensions: Tuple[str, ...]

    # 法证专属排雷
    red_flag_rules: Tuple[str, ...]
    channel_and_revenue_checks: Tuple[str, ...]

    # 人机共读深度研报 Markdown 文本
    markdown_content: str = ""

    @property
    def has_deep_research_markdown(self) -> bool:
        """是否包含代表性企业/行业深度研报上下文."""
        return bool(self.markdown_content and len(self.markdown_content.strip()) > 50)


class KnowledgeRepository:
    """知识库统一加载与中枢中介单例管理器."""

    _instance: Optional["KnowledgeRepository"] = None
    _root_dir: Path
    _business_models: Dict[str, BusinessModelProfile] = {}
    _metrics: Dict[str, MetricCatalogProfile] = {}
    _industries: Dict[str, IndustryNodeProfile] = {}
    _industry_rules: Dict[str, IndustryRuleProfile] = {}
    _industry_knowledge: Dict[str, IndustryKnowledgeProfile] = {}
    _is_initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._root_dir = Path(__file__).resolve().parents[2]
            cls._instance._load_all_knowledge()
        return cls._instance

    @classmethod
    def get_instance(cls) -> "KnowledgeRepository":
        """获取全局单例中枢实例."""
        return cls()

    @classmethod
    def reset_cache(cls):
        """清空缓存 (供测试及热重载使用)."""
        if cls._instance is not None:
            cls._instance._business_models.clear()
            cls._instance._metrics.clear()
            cls._instance._industries.clear()
            cls._instance._industry_rules.clear()
            cls._instance._industry_knowledge.clear()
            cls._instance._is_initialized = False
        cls._instance = None

    def _load_all_knowledge(self):
        """一次性加载 taxonomy, business_models 与 metrics."""
        if self._is_initialized:
            return

        knowledge_dir = self._root_dir / "knowledge"
        if not knowledge_dir.exists():
            # 防御极端环境路径错配
            self._is_initialized = True
            return

        # 1. 加载法定指标库 metrics/catalog.json
        metrics_file = knowledge_dir / "metrics" / "catalog.json"
        if metrics_file.exists():
            try:
                metrics_data = json.loads(metrics_file.read_text(encoding="utf-8"))
                for m in metrics_data.get("metrics", []):
                    m_id = m.get("id")
                    if m_id:
                        self._metrics[m_id] = MetricCatalogProfile(
                            metric_id=m_id,
                            name=m.get("name", m_id),
                            unit=m.get("unit", ""),
                            definition=m.get("definition", ""),
                            applicability=m.get("applicability", ""),
                            cadence=m.get("cadence", "quarterly"),
                            source_candidates=m.get("source_candidates", ""),
                        )
            except Exception:
                pass

        # 2. 加载商业模式库 taxonomy/business_models.json 与对应 *.md
        models_file = knowledge_dir / "taxonomy" / "business_models.json"
        if models_file.exists():
            try:
                models_data = json.loads(models_file.read_text(encoding="utf-8"))
                for bm in models_data.get("models", []):
                    bm_id = bm.get("id")
                    if not bm_id:
                        continue

                    rel_path = bm.get("profile_path", "")
                    md_text = ""
                    if rel_path:
                        md_file = self._root_dir / rel_path
                        if md_file.exists():
                            try:
                                md_text = md_file.read_text(encoding="utf-8")
                            except Exception:
                                md_text = ""

                    metric_ids = tuple(bm.get("metric_ids", []))
                    self._business_models[bm_id] = BusinessModelProfile(
                        model_id=bm_id,
                        name=bm.get("name", bm_id),
                        status=bm.get("status", "draft"),
                        profile_path=rel_path,
                        metric_ids=metric_ids,
                        markdown_content=md_text,
                    )
            except Exception:
                pass

        # 3. 加载行业拓扑库 taxonomy/industries.json
        industries_file = knowledge_dir / "taxonomy" / "industries.json"
        if industries_file.exists():
            try:
                ind_data = json.loads(industries_file.read_text(encoding="utf-8"))
                for ind in ind_data.get("nodes", []):
                    ind_id = ind.get("id")
                    if ind_id:
                        self._industries[ind_id] = IndustryNodeProfile(
                            industry_id=ind_id,
                            name=ind.get("name", ind_id),
                            level=ind.get("level", "industry"),
                            parent_id=ind.get("parent_id"),
                            business_model_ids=tuple(ind.get("business_model_ids", [])),
                            profile_path=ind.get("profile_path", ""),
                        )
            except Exception:
                pass

        # 4. 加载行业买方估值路线与反证规则库 taxonomy/industry_rules.json
        rules_file = knowledge_dir / "taxonomy" / "industry_rules.json"
        if rules_file.exists():
            try:
                rules_data = json.loads(rules_file.read_text(encoding="utf-8"))
                for r in rules_data.get("rules", []):
                    r_id = r.get("industry_id")
                    if not r_id:
                        continue
                    judgment = r.get("judgment", {})
                    self._industry_rules[r_id] = IndustryRuleProfile(
                        industry_id=r_id,
                        status=r.get("status", "industry_adapted"),
                        statistical_validation_status=r.get("statistical_validation_status", "not_validated"),
                        metric_ids=tuple(r.get("metric_ids", [])),
                        required_segmentation=tuple(r.get("required_segmentation", [])),
                        valuation_route=r.get("valuation_route", ""),
                        counterevidence=r.get("counterevidence", ""),
                        evidence_refs=tuple(r.get("evidence_refs", [])),
                        judgment_improving=judgment.get("improving", ""),
                        judgment_deteriorating=judgment.get("deteriorating", ""),
                        judgment_unknown=judgment.get("unknown", ""),
                        drawdown_policy=r.get("drawdown_policy", ""),
                    )
            except Exception:
                pass

        # 5. 加载细分行业经济结构与买方量化知识 data/industry_knowledge/*.json 及代表性研报 Markdown
        ind_k_dir = self._root_dir / "data" / "industry_knowledge"
        rep_md_dir = knowledge_dir / "companies" / "representatives-20261012"
        if ind_k_dir.exists():
            for p in ind_k_dir.glob("*.json"):
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    meta = data.get("meta", {})
                    ind_id = meta.get("industry_id")
                    if not ind_id:
                        continue

                    econ = data.get("economic_structure", {})
                    rails = data.get("financial_guardrails", {})
                    chain = data.get("supply_chain_dynamics", {})
                    causal = data.get("causal_scenarios", {})
                    forensic = data.get("forensic_audit_rules", {})

                    gm_range = econ.get("typical_gross_margin_range", [0.20, 0.50])
                    safe_gm_range = (float(gm_range[0]), float(gm_range[1])) if len(gm_range) >= 2 else (0.20, 0.50)

                    # 挂载深度研报 Markdown (优先使用 knowledge/industries/*.md，兜底使用 representatives/*.md)
                    md_text = ""
                    std_ind_md_path = knowledge_dir / "industries" / f"{ind_id}.md"
                    rep_ind_md_path = rep_md_dir / f"{ind_id}.md"

                    target_md_path = std_ind_md_path if std_ind_md_path.exists() else (rep_ind_md_path if rep_ind_md_path.exists() else None)
                    if target_md_path and target_md_path.exists():
                        try:
                            md_text = target_md_path.read_text(encoding="utf-8")
                        except Exception:
                            md_text = ""

                    self._industry_knowledge[ind_id] = IndustryKnowledgeProfile(
                        industry_id=ind_id,
                        industry_name_zh=meta.get("industry_name_zh", ind_id),
                        sector_id=meta.get("sector_id", "general"),
                        sector_name_zh=meta.get("sector_name_zh", "通用"),
                        macro_sector_id=meta.get("macro_sector_id", "CONS_GOODS"),
                        macro_sector_name_zh=meta.get("macro_sector_name_zh", "消费制造与综合服务"),
                        description_zh=meta.get("description_zh", ""),
                        typical_cogs_ratio=float(econ.get("typical_cogs_ratio", 0.60)),
                        typical_markup_ratio=float(econ.get("typical_markup_ratio", 1.15)),
                        capex_intensity=econ.get("capex_intensity", "中等偏高"),
                        operating_leverage_exposure=econ.get("operating_leverage_exposure", "中等经营杠杆"),
                        typical_gross_margin_range=safe_gm_range,
                        dio_healthy_days=float(rails.get("dio_healthy_days", 90.0)),
                        dio_warning_days=float(rails.get("dio_warning_days", 150.0)),
                        rd_capitalization_max_allowed=float(rails.get("rd_capitalization_max_allowed", 0.10)),
                        top_customer_concentration_redline=float(rails.get("top_customer_concentration_redline", 0.30)),
                        debt_covenant_buffer_minimum_ratio=float(rails.get("debt_covenant_buffer_minimum_ratio", 0.15)),
                        upstream_bottlenecks=tuple(chain.get("upstream_bottlenecks", ["核心供应链产能分配与原材料交期"])),
                        downstream_profile=chain.get("downstream_profile", "企业级或大众消费端客户"),
                        pricing_power_verdict=chain.get("pricing_power_verdict", "依赖行业竞争格局与产品差异化"),
                        leading_bull_triggers=tuple(causal.get("leading_bull_triggers", ["产能利用率回升、新产品放量订单超预期"])),
                        leading_bear_defenses=tuple(causal.get("leading_bear_defenses", ["下游需求萎缩、库存积压价格竞争加剧"])),
                        core_catalyst_dimensions=tuple(causal.get("core_catalyst_dimensions", ["定期财报发布与行业月度景气度指标"])),
                        red_flag_rules=tuple(forensic.get("red_flag_rules", ["产成品增速显著超越营收增速"])),
                        channel_and_revenue_checks=tuple(forensic.get("channel_and_revenue_checks", ["合同负债大幅异动下滑"])),
                        markdown_content=md_text,
                    )
                except Exception:
                    continue

        self._is_initialized = True

    # ==========================================================================
    # 外部只读检索 API (SSOT)
    # ==========================================================================

    def get_business_model(self, model_id: str) -> Optional[BusinessModelProfile]:
        """按模式 ID 获取商业模式档案 (如 'asset_management_fee')."""
        return self._business_models.get(model_id)

    def list_business_models(self) -> List[BusinessModelProfile]:
        """获取全量已注册商业模式列表."""
        return list(self._business_models.values())

    def get_metric(self, metric_id: str) -> Optional[MetricCatalogProfile]:
        """按指标 ID 获取核心指标定义档案 (如 'roe', 'fcf')."""
        return self._metrics.get(metric_id)

    def list_metrics(self) -> List[MetricCatalogProfile]:
        """获取全量已注册核心指标列表."""
        return list(self._metrics.values())

    def get_industry_node(self, industry_id: str) -> Optional[IndustryNodeProfile]:
        """按行业 ID 获取行业拓扑节点档案."""
        return self._industries.get(industry_id)

    def list_industry_nodes(self) -> List[IndustryNodeProfile]:
        """获取全量行业分类节点列表."""
        return list(self._industries.values())

    def get_metrics_for_business_model(self, model_id: str) -> List[MetricCatalogProfile]:
        """获取特定商业模式所绑定的全部法定指标定义档案."""
        bm = self.get_business_model(model_id)
        if not bm:
            return []
        res = []
        for mid in bm.metric_ids:
            metric = self.get_metric(mid)
            if metric:
                res.append(metric)
        return res

    def get_industry_rule(self, industry_id: str) -> Optional[IndustryRuleProfile]:
        """按细分行业 ID 获取买方估值路线与反证规则档案 (如 'oil_gas', 'semiconductors')."""
        return self._industry_rules.get(industry_id)

    def list_industry_rules(self) -> List[IndustryRuleProfile]:
        """获取全量已注册细分行业买方估值与反证规则列表."""
        return list(self._industry_rules.values())

    def get_industry_knowledge(self, industry_id: str) -> Optional[IndustryKnowledgeProfile]:
        """按细分行业 ID 获取全息买方经济结构、风控门禁与因果知识档案 (如 'semiconductors')."""
        return self._industry_knowledge.get(industry_id)

    def list_industry_knowledge(self) -> List[IndustryKnowledgeProfile]:
        """获取全量已注册细分行业买方经济结构与量化知识列表 (41 细分行业)."""
        return list(self._industry_knowledge.values())


