"""事件雷达与突发舆情因果解析引擎 (Event Radar & Causal Parsing Engine).

本引擎专责微观物理事实与宏观突发舆情的第一阶段处理:
1. 基于本地关键词与物理实体词典的高速去噪初筛 (零 Token 物理初筛);
2. 选项 2-B 统一微型模型摘要协议构建与 JSON Schema 刚性解析;
3. 突发事件烈度门禁评估 (P0/P1/P2/P3), 严控下游深度分析派发边界.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple


class EventSeverity(str, Enum):
    """事件烈度与影响层级."""
    P0_CRITICAL = "P0"  # 系统级冲击：关键要道/晶圆厂停产/跨国全面制裁
    P1_MAJOR = "P1"     # 主线行业冲击：各州产业重磅立法/重点工厂爆炸/大客户严重砍单
    P2_MODERATE = "P2"  # 常规行业扰动：常规合规调查/一般政策探讨/日常诉讼
    P3_MINOR = "P3"     # 边缘消息/普通噪音备选


class EventCategory(str, Enum):
    """突发事件业务分类."""
    GEOPOLITICAL = "Geopolitical_CrossStrait"
    STATE_POLICY = "State_Policy_Regulatory"
    PHYSICAL_DISRUPTION = "Physical_Plant_Disruption"
    SUPPLY_CHAIN_CHOKEPOINT = "Supply_Chain_Chokepoint"
    ANTITRUST_LITIGATION = "Antitrust_Litigation"
    OTHER_MACRO = "Other_Macro_Event"


@dataclass
class RawNewsItem:
    """原始新闻与公告事实条目."""
    id: str
    title: str
    content: str
    source: str
    published_at: str
    url: str = ""
    raw_hash: str = field(init=False)

    def __post_init__(self):
        # 基于标题与前 200 字符生成唯一指纹，确保幂等排重
        fingerprint = f"{self.title.strip()}::{self.content[:200].strip()}"
        self.raw_hash = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


@dataclass
class StructuredEventSummary:
    """经由 2-B 统一模型提纯后的结构化事件摘要."""
    event_id: str
    timestamp: str
    category: str
    involved_entities: List[str]
    micro_physical_impact: str
    estimated_duration: str
    affected_business_segments: List[str]
    severity_level: str
    requires_deep_analysis: bool
    raw_title: str
    source_name: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "category": self.category,
            "involved_entities": self.involved_entities,
            "micro_physical_impact": self.micro_physical_impact,
            "estimated_duration": self.estimated_duration,
            "affected_business_segments": self.affected_business_segments,
            "severity_level": self.severity_level,
            "requires_deep_analysis": self.requires_deep_analysis,
            "raw_title": self.raw_title,
            "source_name": self.source_name,
        }


class EventRadarEngine:
    """事件雷达核心算法与规则引擎."""

    DEFAULT_DICTIONARIES = {
        "geopolitical": [
            "蓝营", "绿营", "台海", "海峡", "出口管制", "实体清单", "制裁", "关税",
            "sanction", "export control", "entity list", "tariff", "taiwan strait", "geopolitical",
            "blockade", "military drill", "embargo"
        ],
        "state_policy": [
            "法案", "监管", "补贴", "加州", "德州", "反垄断", "碳排放", "电网负荷",
            "legislation", "regulatory", "subsidy", "california", "texas", "antitrust",
            "grid fee", "ai bill", "mandate", "tax credit"
        ],
        "physical_disruption": [
            "爆炸", "火灾", "停产", "受袭", "罢工", "封锁", "断供", "断水", "停电",
            "explosion", "fire", "outage", "strike", "facility attack", "disruption",
            "force majeure", "pipeline rupture", "blast"
        ],
        "supply_chain": [
            "台积电", "ASML", "光刻机", "高纯试剂", "硅片", "晶圆厂", "关键原料", "红海", "苏伊士",
            "foundry", "semiconductor", "wafer", "raw material", "red sea", "suez canal",
            "chokepoint", "fab shut"
        ]
    }

    DEFAULT_BLACKLIST = [
        "盘后点评", "今日收评", "涨停揭秘", "机构看好", "点击查看", "广告",
        "stock pick", "sponsored", "ad disclaimer", "bullish sentiment", "click here"
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        filter_rules = self.config.get("filtering_rules", {})
        self.dictionaries = filter_rules.get("keyword_dictionaries", self.DEFAULT_DICTIONARIES)
        self.blacklist = filter_rules.get("noise_blacklist", self.DEFAULT_BLACKLIST)

    def pre_filter(self, item: RawNewsItem) -> Tuple[bool, List[str], EventCategory]:
        """第一道防线：零 Token 物理去噪与关键词匹配.

        返回: (is_matched, matched_tags, likely_category)
        """
        combined_text = f"{item.title} {item.content}".lower()

        # 1. 噪声黑名单一票否决
        for bad in self.blacklist:
            if bad.lower() in combined_text:
                return False, ["blacklisted_noise"], EventCategory.OTHER_MACRO

        # 2. 关键词与业务分类命中
        matched_tags: List[str] = []
        category_hits: Dict[EventCategory, int] = {
            EventCategory.GEOPOLITICAL: 0,
            EventCategory.STATE_POLICY: 0,
            EventCategory.PHYSICAL_DISRUPTION: 0,
            EventCategory.SUPPLY_CHAIN_CHOKEPOINT: 0,
        }

        # 匹配各领域词典
        for tag in self.dictionaries.get("geopolitical", []):
            if tag.lower() in combined_text:
                matched_tags.append(tag)
                category_hits[EventCategory.GEOPOLITICAL] += 1

        for tag in self.dictionaries.get("state_policy", []):
            if tag.lower() in combined_text:
                matched_tags.append(tag)
                category_hits[EventCategory.STATE_POLICY] += 1

        for tag in self.dictionaries.get("physical_disruption", []):
            if tag.lower() in combined_text:
                matched_tags.append(tag)
                category_hits[EventCategory.PHYSICAL_DISRUPTION] += 1

        for tag in self.dictionaries.get("supply_chain", []):
            if tag.lower() in combined_text:
                matched_tags.append(tag)
                category_hits[EventCategory.SUPPLY_CHAIN_CHOKEPOINT] += 1

        if not matched_tags:
            return False, [], EventCategory.OTHER_MACRO

        # 选取命中频率最高的业务分类
        best_cat = max(category_hits.items(), key=lambda x: x[1])[0]
        return True, matched_tags, best_cat

    def build_summary_prompt(self, item: RawNewsItem, category: EventCategory) -> Dict[str, str]:
        """构建 2-B 统一微型模型摘要的标准低 Token 提示词包."""
        system_instruction = (
            "你是一名资深买方宏观与产业突发事件分析师。你的职责是从快讯中剔除情绪炒作，"
            "提取微观物理冲击事实，输出严格标准的 JSON，总字数严控在 80 字以内。"
        )

        user_content = (
            f"请将以下资讯提炼为严格 JSON 对象，不得输出任何其他文字：\n"
            f"标题: {item.title}\n"
            f"信源: {item.source}\n"
            f"发布时间: {item.published_at}\n"
            f"正文: {item.content[:500]}\n\n"
            f"输出 JSON 字段规范：\n"
            f"{{\n"
            f'  "category": "{category.value}",\n'
            f'  "involved_entities": ["涉及的机构、地区、公司或关键产品"],\n'
            f'  "micro_physical_impact": "一句话客观物理事实与受损/政策影响",\n'
            f'  "estimated_duration": "预期持续期(如 数日/数月/永久)",\n'
            f'  "affected_business_segments": ["受波及的业务分部或产业链环节"],\n'
            f'  "severity_level": "P0 或 P1 或 P2 或 P3"\n'
            f"}}"
        )
        return {"system": system_instruction, "user": user_content}

    def parse_and_validate_summary(
        self,
        raw_model_output: str,
        fallback_item: RawNewsItem,
        default_category: EventCategory = EventCategory.OTHER_MACRO
    ) -> StructuredEventSummary:
        """解析并校验模型输出的 JSON 摘要，施加防伪平账与门禁分级防御."""
        parsed_data = {}
        cleaned_text = raw_model_output.strip()

        # 剥离 markdown ```json 包裹
        if "```" in cleaned_text:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned_text)
            if match:
                cleaned_text = match.group(1).strip()

        try:
            parsed_data = json.loads(cleaned_text)
        except Exception:
            # 容错降级：若模型生成非标字符串，提取安全底线摘要
            parsed_data = {
                "category": default_category.value,
                "involved_entities": [fallback_item.source],
                "micro_physical_impact": fallback_item.title[:60],
                "estimated_duration": "待定",
                "affected_business_segments": ["通用产业链"],
                "severity_level": "P2"
            }

        # 字段防御赋值
        category_val = parsed_data.get("category", default_category.value)
        entities = parsed_data.get("involved_entities", [])
        if not isinstance(entities, list) or not entities:
            entities = ["未知主体"]
        impact = parsed_data.get("micro_physical_impact", fallback_item.title)
        duration = parsed_data.get("estimated_duration", "短期")
        segments = parsed_data.get("affected_business_segments", [])
        if not isinstance(segments, list) or not segments:
            segments = ["全产业链"]

        raw_sev = str(parsed_data.get("severity_level", "P2")).upper()
        if raw_sev not in ("P0", "P1", "P2", "P3"):
            raw_sev = "P2"

        # 规则修正：核心要害事实必须强制提升烈度
        high_critical_keywords = ["爆炸", "停产", "制裁", "出口管制", "封锁", "explosion", "blockade", "sanction"]
        if any(k in impact.lower() or k in fallback_item.title.lower() for k in high_critical_keywords):
            if raw_sev in ("P2", "P3"):
                raw_sev = "P1"

        requires_deep = raw_sev in ("P0", "P1")

        return StructuredEventSummary(
            event_id=f"EVT_{fallback_item.raw_hash[:12].upper()}",
            timestamp=fallback_item.published_at,
            category=category_val,
            involved_entities=[str(e) for e in entities],
            micro_physical_impact=str(impact),
            estimated_duration=str(duration),
            affected_business_segments=[str(s) for s in segments],
            severity_level=raw_sev,
            requires_deep_analysis=requires_deep,
            raw_title=fallback_item.title,
            source_name=fallback_item.source,
        )
