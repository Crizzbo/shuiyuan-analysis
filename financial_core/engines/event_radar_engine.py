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
    """突发事件业务全息分类 (12大全景信息收集维度)."""
    GEOPOLITICAL = "Geopolitical_CrossStrait"
    STATE_POLICY = "State_Policy_Regulatory"
    PHYSICAL_DISRUPTION = "Physical_Plant_Disruption"
    SUPPLY_CHAIN_CHOKEPOINT = "Supply_Chain_Chokepoint"
    LABOR_STRIKES = "Labor_Strikes_Port_Railways"
    ANTITRUST_LITIGATION = "Antitrust_Litigation"
    COMMODITY_SQUEEZE = "Commodity_Physical_Squeeze"
    CENTRAL_BANK_LIQUIDITY = "CentralBank_Liquidity_FX_Shock"
    ENERGY_GRID = "Energy_Grid_Blackout_Rationing"
    CYBER_INFRASTRUCTURE = "Cyber_Critical_Infrastructure"
    BIOSECURITY_EMBARGO = "Biosecurity_Export_Embargo"
    CRITICAL_MINERALS = "Critical_Minerals_Export_Permit"
    OTHER_MACRO = "Other_Macro_Event"


class SourceCredibilityTier(str, Enum):
    """信源权威度分级 (买方真伪防伪过滤矩阵)."""
    TIER_1_OFFICIAL_REGULATORY = "Tier1_Official_Regulatory"  # 监管机构与法定政府公报 (权重 1.0)
    TIER_2_OFFICIAL_DISCLOSURE = "Tier2_Official_Disclosure"  # 上市公司官方IR/涉事港口局/工会官方公报 (权重 0.9)
    TIER_3_MAINSTREAM_WIRE = "Tier3_Mainstream_Wire"          # 主流财经通讯社与权威行业专刊 (权重 0.8)
    TIER_4_PUBLIC_FLASH = "Tier4_Public_Flash_Social"         # 社交媒体/公开快讯/网络传闻 (权重 0.45)


class VerificationStatus(str, Enum):
    """事实鉴真与交叉核实状态."""
    CONFIRMED_FACT = "Confirmed_Fact"              # 权威法定或主体官方核准事实
    CORROBORATED_REPORT = "Corroborated_Report"    # 经两个以上独立信源交叉印证
    UNVERIFIED_RUMOR = "Unverified_Rumor"          # 社交媒体/单一小道消息，待查证
    DEBUNKED = "Debunked"                          # 证实为虚假传闻或已被官方辟谣


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
    credibility_tier: str = SourceCredibilityTier.TIER_3_MAINSTREAM_WIRE.value
    credibility_score: float = 0.8
    verification_status: str = VerificationStatus.CORROBORATED_REPORT.value
    verification_note: str = "主流财经通讯社通告"

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
            "credibility_tier": self.credibility_tier,
            "credibility_score": self.credibility_score,
            "verification_status": self.verification_status,
            "verification_note": self.verification_note,
        }


class EventRadarEngine:
    """事件雷达核心算法与规则引擎."""

    DEFAULT_DICTIONARIES = {
        "geopolitical": [
            "蓝营", "绿营", "台海", "海峡", "出口管制", "实体清单", "制裁", "关税",
            "立法院", "大选", "摇摆州", "两党博弈", "军演", "封锁", "禁运",
            "sanction", "export control", "entity list", "tariff", "taiwan strait", "geopolitical",
            "blockade", "military drill", "embargo", "election polls", "legislative vote", "sdn list"
        ],
        "state_policy": [
            "法案", "监管", "补贴", "加州", "德州", "反垄断", "碳排放", "电网负荷",
            "公用事业", "水权配额", "工业电价", "冷却水", "pue", "分区规划",
            "legislation", "regulatory", "subsidy", "california", "texas", "antitrust",
            "grid fee", "ai bill", "mandate", "tax credit", "water rights", "environmental permit",
            "power tariff", "zoning"
        ],
        "physical_disruption": [
            "爆炸", "火灾", "停产", "受袭", "断供", "断水", "停电", "不可抗力",
            "光刻胶单体", "电子级氢氟酸", "前驱体特气", "特种化学品", "炼油催化", "变电站故障", "海底光缆",
            "explosion", "fire", "outage", "facility attack", "disruption", "chemical plant",
            "force majeure", "pipeline rupture", "blast", "photoresist precursor", "subsea cable"
        ],
        "supply_chain": [
            "台积电", "asml", "光刻机", "高纯试剂", "硅片", "晶圆厂", "关键原料", "红海", "苏伊士",
            "曼德海峡", "霍尔木兹", "马六甲", "巴拿马运河", "吃水限制", "好望角绕航", "baf", "集装箱运价",
            "foundry", "semiconductor", "wafer", "raw material", "red sea", "suez canal",
            "bab el-mandeb", "hormuz", "malacca", "panama canal", "draft limit", "chokepoint", "container freight"
        ],
        "labor_strikes": [
            "罢工", "码头工人", "工会", "劳资谈判", "怠工", "铁路停摆", "ila", "ilwu", "港口封锁", "运力瘫痪",
            "dockworker", "union", "labor strike", "contract negotiation", "railway halt", "port shutdown",
            "work stoppage", "slowdown"
        ],
        "antitrust_litigation": [
            "反垄断", "司法部", "ftc", "欧盟委员会", "英国cma", "337调查", "itc", "专利侵权", "排除令", "进口禁令",
            "antitrust", "doj", "ftc", "european commission", "cma", "itc 337", "patent infringement",
            "exclusion order", "import ban", "breakup"
        ],
        "commodity_squeeze": [
            "战略石油储备", "spr", "现货升水", "倒挂", "仓单注销", "逼仓", "挤兑提货", "稀土配额", "镓锗出口", "实物黄金溢价",
            "backwardation", "physical premium", "spr release", "warrant cancel", "short squeeze",
            "rare earth quota", "gallium", "germanium", "delivery default"
        ],
        "liquidity_central_bank": [
            "贴现窗口", "常备借贷便利", "srf", "隔夜逆回购", "on rrp", "套息平仓", "carry trade", "日元突涨", "cds飙升", "美元流动性",
            "discount window", "standing repo", "on rrp", "carry trade unwind", "yen spike", "cds spread",
            "liquidity squeeze", "dollar funding"
        ],
        "energy_grid": [
            "工业限电", "电网跳闸", "极端寒潮", "气井冻结", "枯水期", "水库死水位", "莱茵河水位", "kaub", "nerc", "eia", "ercot",
            "load shedding", "rolling blackout", "grid emergency", "low river gauge", "power rationing", "freeze off"
        ],
        "cyber_infrastructure": [
            "工控瘫痪", "勒索软件", "cisa", "内核驱动蓝屏", "海底光缆断裂", "清算系统故障", "fedwire", "swift",
            "ics advisory", "ransomware attack", "critical infrastructure cyber", "kernel crash", "backbone outage"
        ],
        "biosecurity_embargo": [
            "生物安全法案", "biosecure act", "cxo", "合同研发受限", "fda进口警报", "import alert", "先导化合物禁运",
            "原料药口岸查扣", "clinical trial hold", "select agent", "pathogen export"
        ],
        "critical_minerals": [
            "双用途出口许可证", "锗镓出口管制", "锑矿配额", "重稀土许可证", "印尼镍矿rkab", "采矿特许权", "战略矿产",
            "export license", "dual use export permit", "antimony quota", "rare earth license", "indonesia nickel rkab", "mining concession"
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
        """第一道防线：零 Token 物理去噪与关键词匹配 (12大全景信息收集维度).

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
            EventCategory.LABOR_STRIKES: 0,
            EventCategory.ANTITRUST_LITIGATION: 0,
            EventCategory.COMMODITY_SQUEEZE: 0,
            EventCategory.CENTRAL_BANK_LIQUIDITY: 0,
            EventCategory.ENERGY_GRID: 0,
            EventCategory.CYBER_INFRASTRUCTURE: 0,
            EventCategory.BIOSECURITY_EMBARGO: 0,
            EventCategory.CRITICAL_MINERALS: 0,
        }

        # 匹配 12 大核心领域词典
        category_mapping = [
            ("geopolitical", EventCategory.GEOPOLITICAL),
            ("state_policy", EventCategory.STATE_POLICY),
            ("physical_disruption", EventCategory.PHYSICAL_DISRUPTION),
            ("supply_chain", EventCategory.SUPPLY_CHAIN_CHOKEPOINT),
            ("labor_strikes", EventCategory.LABOR_STRIKES),
            ("antitrust_litigation", EventCategory.ANTITRUST_LITIGATION),
            ("commodity_squeeze", EventCategory.COMMODITY_SQUEEZE),
            ("liquidity_central_bank", EventCategory.CENTRAL_BANK_LIQUIDITY),
            ("energy_grid", EventCategory.ENERGY_GRID),
            ("cyber_infrastructure", EventCategory.CYBER_INFRASTRUCTURE),
            ("biosecurity_embargo", EventCategory.BIOSECURITY_EMBARGO),
            ("critical_minerals", EventCategory.CRITICAL_MINERALS),
        ]

        for dict_key, cat_enum in category_mapping:
            for tag in self.dictionaries.get(dict_key, []):
                if tag.lower() in combined_text:
                    matched_tags.append(tag)
                    category_hits[cat_enum] += 1

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

    def evaluate_source_credibility(self, source_name: str) -> Tuple[SourceCredibilityTier, float]:
        """评估信源权威度分级与基础信任权重 (买方多信源风控).

        返回: (SourceCredibilityTier, float 权重 0.0~1.0)
        """
        s_lower = str(source_name).lower()
        s_norm = s_lower.replace("_", " ").replace("-", " ")

        # Tier 4: 优先识别社交媒体快讯、未核实论坛与匿名小道消息
        tier4_signatures = [
            "x social", "twitter", "weibo", "reddit", "forum", "rumor",
            "leak", "anonymous", "gossip", "unverified", "community"
        ]
        if any(sig in s_norm for sig in tier4_signatures):
            return SourceCredibilityTier.TIER_4_PUBLIC_FLASH, 0.45

        # Tier 1: 官方监管机构、法院与法定政府公报
        tier1_signatures = [
            "sec", "edgar", "cpuc", "itc", "usitc", "federal register", "ukmto",
            "boj", "bank of japan", "federal reserve", "fed", "caiso", "boe", "ecb",
            "doj", "ftc", "cma", "regulatory gazette", "official gazette", "court",
            "legislative", "comptroller", "doe", "cisa", "eia", "nerc", "ercot",
            "fda", "esdm", "bfg", "stb"
        ]
        if any(sig in s_norm for sig in tier1_signatures):
            return SourceCredibilityTier.TIER_1_OFFICIAL_REGULATORY, 1.0

        # Tier 2: 发行人/涉事主体官方IR与行业工会公报
        tier2_signatures = [
            "investor relations", "press release", "port authority",
            "ila", "ilwu", "union", "lme official", "statement", "port notice",
            "ir pr", "_ir", "ir_"
        ]
        if any(sig in s_norm for sig in tier2_signatures) or s_norm.endswith(" pr") or s_norm.endswith(" ir"):
            return SourceCredibilityTier.TIER_2_OFFICIAL_DISCLOSURE, 0.9

        # Tier 3: 默认所有主流财经通讯社与专业行业出版物 (Reuters, Bloomberg, 日报, 专刊等)
        return SourceCredibilityTier.TIER_3_MAINSTREAM_WIRE, 0.8

    def parse_and_validate_summary(
        self,
        raw_model_output: str,
        fallback_item: RawNewsItem,
        default_category: EventCategory = EventCategory.OTHER_MACRO
    ) -> StructuredEventSummary:
        """解析并校验模型输出的 JSON 摘要，施加防伪平账、信源权威度评估与传闻熔断门禁."""
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

        # 规则修正：核心要害物理事实必须强制提升烈度
        high_critical_keywords = ["爆炸", "停产", "制裁", "出口管制", "封锁", "explosion", "blockade", "sanction"]
        if any(k in impact.lower() or k in fallback_item.title.lower() for k in high_critical_keywords):
            if raw_sev in ("P2", "P3"):
                raw_sev = "P1"

        # 信源权威度分级与交叉鉴真状态判定
        cred_tier, cred_score = self.evaluate_source_credibility(fallback_item.source)
        title_content_lower = f"{fallback_item.title} {fallback_item.content}".lower()
        rumor_keywords = ["传闻", "小道消息", "据传", "外媒爆料", "未证实", "rumor", "unconfirmed", "alleged"]
        has_rumor_keyword = any(rk in title_content_lower for rk in rumor_keywords)

        if cred_tier == SourceCredibilityTier.TIER_1_OFFICIAL_REGULATORY:
            v_status = VerificationStatus.CONFIRMED_FACT.value
            v_note = "官方监管机构或法定政府公报权威发布"
        elif cred_tier == SourceCredibilityTier.TIER_2_OFFICIAL_DISCLOSURE:
            v_status = VerificationStatus.CONFIRMED_FACT.value
            v_note = "上市公司IR或涉事机构官方公报确认"
        elif cred_tier == SourceCredibilityTier.TIER_3_MAINSTREAM_WIRE:
            if has_rumor_keyword:
                v_status = VerificationStatus.UNVERIFIED_RUMOR.value
                v_note = "主流通讯社引述市场传闻，未见监管或当事方确认，需审慎复核"
            else:
                v_status = VerificationStatus.CORROBORATED_REPORT.value
                v_note = "主流财经通讯社现场采信报道"
        else:
            # Tier 4: 社交媒体或非标快讯
            v_status = VerificationStatus.UNVERIFIED_RUMOR.value
            v_note = "社交媒体或网络快讯传闻，缺乏独立法定信源背书，已触发下游深研熔断门禁"

        # 传闻熔断门禁：未核实传闻 (Unverified_Rumor) 严禁下发下游 SOTP 深度穿透
        requires_deep = raw_sev in ("P0", "P1")
        if v_status == VerificationStatus.UNVERIFIED_RUMOR.value:
            requires_deep = False

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
            credibility_tier=cred_tier.value,
            credibility_score=cred_score,
            verification_status=v_status,
            verification_note=v_note,
        )
