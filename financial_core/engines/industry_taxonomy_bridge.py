"""三层行业分类映射桥梁 (Three-Tier Industry Taxonomy Bridge).

物理架构定界 (Layer 1: financial_core):
- 纯净底层架构，纯相对导入，零外层依赖;
- 承担将个股代码/业务标签、全系统 41 个细分行业契约、以及 OECD ICIO 12 大宏观投入产出部门
  进行严格的双向映射与一致性断言;
- 为宏观列昂惕夫投入产出双对偶价格传导与微观企业增加值分配提供统一行业枢纽。
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple


@dataclass(frozen=True)
class IndustryMappingRecord:
    """细分行业映射标准档案记录."""
    industry_id: str             # 内部 41 行业 ID (例如 semiconductors, biotech, food_beverage)
    industry_name_zh: str        # 行业中文名
    sector_id: str               # 所属板块 ID (例如 information_technology, health_care)
    sector_name_zh: str          # 板块中文名
    macro_sector_id: str         # OECD 12 宏观投入产出部门 ID (例如 TECH_SEMI, HEALTH_BIO)
    macro_sector_name_zh: str    # OECD 宏观部门中文名
    typical_cogs_ratio: float    # 典型营业成本占营收比重 (COGS / Revenue)
    typical_markup_ratio: float  # 典型霍尔微观加价率先验 (Hall Markup Ratio)


class IndustryTaxonomyBridge:
    """三层行业分类映射桥梁中枢."""

    # 41 细分行业标准全息定义与映射底账
    _RECORDS: Dict[str, IndustryMappingRecord] = {
        # 1. 能源 (energy)
        "oil_gas": IndustryMappingRecord(
            industry_id="oil_gas",
            industry_name_zh="油气勘探与生产",
            sector_id="energy",
            sector_name_zh="能源",
            macro_sector_id="ENERGY_MIN",
            macro_sector_name_zh="能源采掘、矿产开采与大宗原材料",
            typical_cogs_ratio=0.55,
            typical_markup_ratio=1.18,
        ),
        "energy_services": IndustryMappingRecord(
            industry_id="energy_services",
            industry_name_zh="油服与能源设备",
            sector_id="energy",
            sector_name_zh="能源",
            macro_sector_id="ENERGY_MIN",
            macro_sector_name_zh="能源采掘、矿产开采与大宗原材料",
            typical_cogs_ratio=0.68,
            typical_markup_ratio=1.10,
        ),
        "midstream": IndustryMappingRecord(
            industry_id="midstream",
            industry_name_zh="能源运输与加工",
            sector_id="energy",
            sector_name_zh="能源",
            macro_sector_id="ENERGY_MIN",
            macro_sector_name_zh="能源采掘、矿产开采与大宗原材料",
            typical_cogs_ratio=0.62,
            typical_markup_ratio=1.15,
        ),

        # 2. 原材料 (materials)
        "mining": IndustryMappingRecord(
            industry_id="mining",
            industry_name_zh="金属与采矿",
            sector_id="materials",
            sector_name_zh="原材料",
            macro_sector_id="ENERGY_MIN",
            macro_sector_name_zh="能源采掘、矿产开采与大宗原材料",
            typical_cogs_ratio=0.60,
            typical_markup_ratio=1.20,
        ),
        "chemicals": IndustryMappingRecord(
            industry_id="chemicals",
            industry_name_zh="化工",
            sector_id="materials",
            sector_name_zh="原材料",
            macro_sector_id="ENERGY_MIN",
            macro_sector_name_zh="能源采掘、矿产开采与大宗原材料",
            typical_cogs_ratio=0.72,
            typical_markup_ratio=1.08,
        ),
        "packaging": IndustryMappingRecord(
            industry_id="packaging",
            industry_name_zh="包装与林纸",
            sector_id="materials",
            sector_name_zh="原材料",
            macro_sector_id="CONS_GOODS",
            macro_sector_name_zh="耐用消费品、纺织服饰与通用轻工业制造",
            typical_cogs_ratio=0.78,
            typical_markup_ratio=1.05,
        ),

        # 3. 工业 (industrials)
        "capital_goods": IndustryMappingRecord(
            industry_id="capital_goods",
            industry_name_zh="工业设备与自动化",
            sector_id="industrials",
            sector_name_zh="工业",
            macro_sector_id="CAP_GOODS",
            macro_sector_name_zh="工业母机、智能制造装备与汽车交通设备",
            typical_cogs_ratio=0.65,
            typical_markup_ratio=1.16,
        ),
        "aerospace_defense": IndustryMappingRecord(
            industry_id="aerospace_defense",
            industry_name_zh="航空航天与国防",
            sector_id="industrials",
            sector_name_zh="工业",
            macro_sector_id="CAP_GOODS",
            macro_sector_name_zh="工业母机、智能制造装备与汽车交通设备",
            typical_cogs_ratio=0.75,
            typical_markup_ratio=1.12,
        ),
        "transport_logistics": IndustryMappingRecord(
            industry_id="transport_logistics",
            industry_name_zh="运输与物流",
            sector_id="industrials",
            sector_name_zh="工业",
            macro_sector_id="TRADE_LOG",
            macro_sector_name_zh="全球物流航运、仓储分拨与批发零售贸易",
            typical_cogs_ratio=0.82,
            typical_markup_ratio=1.06,
        ),
        "business_services": IndustryMappingRecord(
            industry_id="business_services",
            industry_name_zh="商业与专业服务",
            sector_id="industrials",
            sector_name_zh="工业",
            macro_sector_id="PROF_SERV",
            macro_sector_name_zh="专业科技研发、法律财税与企业综合服务",
            typical_cogs_ratio=0.55,
            typical_markup_ratio=1.15,
        ),
        "construction": IndustryMappingRecord(
            industry_id="construction",
            industry_name_zh="建筑与工程",
            sector_id="industrials",
            sector_name_zh="工业",
            macro_sector_id="CONST_RE",
            macro_sector_name_zh="建筑工程、城市基础设施与不动产",
            typical_cogs_ratio=0.88,
            typical_markup_ratio=1.04,
        ),

        # 4. 可选消费 (consumer_discretionary)
        "autos": IndustryMappingRecord(
            industry_id="autos",
            industry_name_zh="汽车与零部件",
            sector_id="consumer_discretionary",
            sector_name_zh="可选消费",
            macro_sector_id="CAP_GOODS",
            macro_sector_name_zh="工业母机、智能制造装备与汽车交通设备",
            typical_cogs_ratio=0.80,
            typical_markup_ratio=1.08,
        ),
        "retail": IndustryMappingRecord(
            industry_id="retail",
            industry_name_zh="零售与电商",
            sector_id="consumer_discretionary",
            sector_name_zh="可选消费",
            macro_sector_id="TRADE_LOG",
            macro_sector_name_zh="全球物流航运、仓储分拨与批发零售贸易",
            typical_cogs_ratio=0.70,
            typical_markup_ratio=1.12,
        ),
        "restaurants": IndustryMappingRecord(
            industry_id="restaurants",
            industry_name_zh="餐饮",
            sector_id="consumer_discretionary",
            sector_name_zh="可选消费",
            macro_sector_id="CONS_GOODS",
            macro_sector_name_zh="耐用消费品、纺织服饰与通用轻工业制造",
            typical_cogs_ratio=0.62,
            typical_markup_ratio=1.18,
        ),
        "travel_leisure": IndustryMappingRecord(
            industry_id="travel_leisure",
            industry_name_zh="旅游酒店与休闲",
            sector_id="consumer_discretionary",
            sector_name_zh="可选消费",
            macro_sector_id="CONS_GOODS",
            macro_sector_name_zh="耐用消费品、纺织服饰与通用轻工业制造",
            typical_cogs_ratio=0.58,
            typical_markup_ratio=1.16,
        ),
        "housing_durables": IndustryMappingRecord(
            industry_id="housing_durables",
            industry_name_zh="住宅建设与耐用品",
            sector_id="consumer_discretionary",
            sector_name_zh="可选消费",
            macro_sector_id="CONS_GOODS",
            macro_sector_name_zh="耐用消费品、纺织服饰与通用轻工业制造",
            typical_cogs_ratio=0.76,
            typical_markup_ratio=1.07,
        ),

        # 5. 必需消费 (consumer_staples)
        "food_beverage": IndustryMappingRecord(
            industry_id="food_beverage",
            industry_name_zh="食品饮料",
            sector_id="consumer_staples",
            sector_name_zh="必需消费",
            macro_sector_id="AGR",
            macro_sector_name_zh="农业、食品加工与林业资源",
            typical_cogs_ratio=0.52,
            typical_markup_ratio=1.35,
        ),
        "household_personal": IndustryMappingRecord(
            industry_id="household_personal",
            industry_name_zh="家庭与个人用品",
            sector_id="consumer_staples",
            sector_name_zh="必需消费",
            macro_sector_id="CONS_GOODS",
            macro_sector_name_zh="耐用消费品、纺织服饰与通用轻工业制造",
            typical_cogs_ratio=0.50,
            typical_markup_ratio=1.28,
        ),
        "staples_retail": IndustryMappingRecord(
            industry_id="staples_retail",
            industry_name_zh="必需消费零售",
            sector_id="consumer_staples",
            sector_name_zh="必需消费",
            macro_sector_id="TRADE_LOG",
            macro_sector_name_zh="全球物流航运、仓储分拨与批发零售贸易",
            typical_cogs_ratio=0.75,
            typical_markup_ratio=1.06,
        ),
        "tobacco": IndustryMappingRecord(
            industry_id="tobacco",
            industry_name_zh="烟草",
            sector_id="consumer_staples",
            sector_name_zh="必需消费",
            macro_sector_id="AGR",
            macro_sector_name_zh="农业、食品加工与林业资源",
            typical_cogs_ratio=0.35,
            typical_markup_ratio=1.45,
        ),

        # 6. 医疗保健 (health_care)
        "pharma": IndustryMappingRecord(
            industry_id="pharma",
            industry_name_zh="成熟制药",
            sector_id="health_care",
            sector_name_zh="医疗保健",
            macro_sector_id="HEALTH_BIO",
            macro_sector_name_zh="医疗保健、专利创新药与生物技术服务",
            typical_cogs_ratio=0.32,
            typical_markup_ratio=1.32,
        ),
        "biotech": IndustryMappingRecord(
            industry_id="biotech",
            industry_name_zh="研发型生物科技",
            sector_id="health_care",
            sector_name_zh="医疗保健",
            macro_sector_id="HEALTH_BIO",
            macro_sector_name_zh="医疗保健、专利创新药与生物技术服务",
            typical_cogs_ratio=0.25,
            typical_markup_ratio=1.30,
        ),
        "medical_devices": IndustryMappingRecord(
            industry_id="medical_devices",
            industry_name_zh="医疗器械与生命科学工具",
            sector_id="health_care",
            sector_name_zh="医疗保健",
            macro_sector_id="HEALTH_BIO",
            macro_sector_name_zh="医疗保健、专利创新药与生物技术服务",
            typical_cogs_ratio=0.45,
            typical_markup_ratio=1.25,
        ),
        "health_services": IndustryMappingRecord(
            industry_id="health_services",
            industry_name_zh="医疗服务与分销",
            sector_id="health_care",
            sector_name_zh="医疗保健",
            macro_sector_id="HEALTH_BIO",
            macro_sector_name_zh="医疗保健、专利创新药与生物技术服务",
            typical_cogs_ratio=0.85,
            typical_markup_ratio=1.06,
        ),
        "managed_care": IndustryMappingRecord(
            industry_id="managed_care",
            industry_name_zh="医疗保险与管理式医疗",
            sector_id="health_care",
            sector_name_zh="医疗保健",
            macro_sector_id="HEALTH_BIO",
            macro_sector_name_zh="医疗保健、专利创新药与生物技术服务",
            typical_cogs_ratio=0.82,
            typical_markup_ratio=1.08,
        ),

        # 7. 金融 (financials)
        "banks": IndustryMappingRecord(
            industry_id="banks",
            industry_name_zh="银行",
            sector_id="financials",
            sector_name_zh="金融",
            macro_sector_id="FIN_INS",
            macro_sector_name_zh="金融中介服务、商业银行与证券保险",
            typical_cogs_ratio=0.40,
            typical_markup_ratio=1.18,
        ),
        "insurance": IndustryMappingRecord(
            industry_id="insurance",
            industry_name_zh="保险与再保险",
            sector_id="financials",
            sector_name_zh="金融",
            macro_sector_id="FIN_INS",
            macro_sector_name_zh="金融中介服务、商业银行与证券保险",
            typical_cogs_ratio=0.65,
            typical_markup_ratio=1.12,
        ),
        "asset_management": IndustryMappingRecord(
            industry_id="asset_management",
            industry_name_zh="资产管理与资本市场",
            sector_id="financials",
            sector_name_zh="金融",
            macro_sector_id="FIN_INS",
            macro_sector_name_zh="金融中介服务、商业银行与证券保险",
            typical_cogs_ratio=0.45,
            typical_markup_ratio=1.22,
        ),
        "payments": IndustryMappingRecord(
            industry_id="payments",
            industry_name_zh="支付与金融基础设施",
            sector_id="financials",
            sector_name_zh="金融",
            macro_sector_id="FIN_INS",
            macro_sector_name_zh="金融中介服务、商业银行与证券保险",
            typical_cogs_ratio=0.48,
            typical_markup_ratio=1.25,
        ),

        # 8. 信息技术 (information_technology)
        "software": IndustryMappingRecord(
            industry_id="software",
            industry_name_zh="软件与云服务",
            sector_id="information_technology",
            sector_name_zh="信息技术",
            macro_sector_id="INFO_SOFT",
            macro_sector_name_zh="企业级软件、超大规模云服务与数字通信网络",
            typical_cogs_ratio=0.25,
            typical_markup_ratio=1.38,
        ),
        "semiconductors": IndustryMappingRecord(
            industry_id="semiconductors",
            industry_name_zh="半导体设计与制造",
            sector_id="information_technology",
            sector_name_zh="信息技术",
            macro_sector_id="TECH_SEMI",
            macro_sector_name_zh="前沿半导体、AI算力集群与高端计算硬件",
            typical_cogs_ratio=0.45,
            typical_markup_ratio=1.35,
        ),
        "semi_equipment": IndustryMappingRecord(
            industry_id="semi_equipment",
            industry_name_zh="半导体设备",
            sector_id="information_technology",
            sector_name_zh="信息技术",
            macro_sector_id="TECH_SEMI",
            macro_sector_name_zh="前沿半导体、AI算力集群与高端计算硬件",
            typical_cogs_ratio=0.52,
            typical_markup_ratio=1.28,
        ),
        "hardware": IndustryMappingRecord(
            industry_id="hardware",
            industry_name_zh="硬件与通信设备",
            sector_id="information_technology",
            sector_name_zh="信息技术",
            macro_sector_id="TECH_SEMI",
            macro_sector_name_zh="前沿半导体、AI算力集群与高端计算硬件",
            typical_cogs_ratio=0.68,
            typical_markup_ratio=1.14,
        ),
        "it_services": IndustryMappingRecord(
            industry_id="it_services",
            industry_name_zh="IT 服务与咨询",
            sector_id="information_technology",
            sector_name_zh="信息技术",
            macro_sector_id="INFO_SOFT",
            macro_sector_name_zh="企业级软件、超大规模云服务与数字通信网络",
            typical_cogs_ratio=0.65,
            typical_markup_ratio=1.12,
        ),

        # 9. 通信服务 (communication_services)
        "telecom": IndustryMappingRecord(
            industry_id="telecom",
            industry_name_zh="电信",
            sector_id="communication_services",
            sector_name_zh="通信服务",
            macro_sector_id="INFO_SOFT",
            macro_sector_name_zh="企业级软件、超大规模云服务与数字通信网络",
            typical_cogs_ratio=0.50,
            typical_markup_ratio=1.15,
        ),
        "digital_platforms": IndustryMappingRecord(
            industry_id="digital_platforms",
            industry_name_zh="互联网平台",
            sector_id="communication_services",
            sector_name_zh="通信服务",
            macro_sector_id="INFO_SOFT",
            macro_sector_name_zh="企业级软件、超大规模云服务与数字通信网络",
            typical_cogs_ratio=0.35,
            typical_markup_ratio=1.32,
        ),
        "media_entertainment": IndustryMappingRecord(
            industry_id="media_entertainment",
            industry_name_zh="媒体游戏与娱乐",
            sector_id="communication_services",
            sector_name_zh="通信服务",
            macro_sector_id="INFO_SOFT",
            macro_sector_name_zh="企业级软件、超大规模云服务与数字通信网络",
            typical_cogs_ratio=0.58,
            typical_markup_ratio=1.18,
        ),

        # 10. 公用事业 (utilities)
        "regulated_utilities": IndustryMappingRecord(
            industry_id="regulated_utilities",
            industry_name_zh="受监管公用事业",
            sector_id="utilities",
            sector_name_zh="公用事业",
            macro_sector_id="INFRA_UTIL",
            macro_sector_name_zh="电网公用事业、清洁电力与能源基础设施",
            typical_cogs_ratio=0.65,
            typical_markup_ratio=1.10,
        ),
        "merchant_power": IndustryMappingRecord(
            industry_id="merchant_power",
            industry_name_zh="市场化发电",
            sector_id="utilities",
            sector_name_zh="公用事业",
            macro_sector_id="INFRA_UTIL",
            macro_sector_name_zh="电网公用事业、清洁电力与能源基础设施",
            typical_cogs_ratio=0.60,
            typical_markup_ratio=1.14,
        ),

        # 11. 房地产 (real_estate)
        "equity_reit": IndustryMappingRecord(
            industry_id="equity_reit",
            industry_name_zh="权益型 REIT",
            sector_id="real_estate",
            sector_name_zh="房地产",
            macro_sector_id="CONST_RE",
            macro_sector_name_zh="建筑工程、城市基础设施与不动产",
            typical_cogs_ratio=0.35,
            typical_markup_ratio=1.25,
        ),
        "real_estate_services": IndustryMappingRecord(
            industry_id="real_estate_services",
            industry_name_zh="房地产开发与服务",
            sector_id="real_estate",
            sector_name_zh="房地产",
            macro_sector_id="CONST_RE",
            macro_sector_name_zh="建筑工程、城市基础设施与不动产",
            typical_cogs_ratio=0.75,
            typical_markup_ratio=1.08,
        ),
    }

    # 常见别名映射字典 (容错解析常见输入)
    _ALIAS_MAP: Dict[str, str] = {
        # 英文与缩写别名
        "semi": "semiconductors",
        "semiconductor": "semiconductors",
        "chips": "semiconductors",
        "tech_hardware": "hardware",
        "techhardware": "hardware",
        "biotechnology": "biotech",
        "pharma_biotech": "biotech",
        "pharmaceuticals": "pharma",
        "liquor": "food_beverage",
        "liquorconsumer": "food_beverage",
        "beverage": "food_beverage",
        "consumer_staple": "food_beverage",
        "software_cloud": "software",
        "saas": "software",
        "cloud": "software",
        "banking": "banks",
        "auto": "autos",
        "automotive": "autos",
        "oil": "oil_gas",
        "gas": "oil_gas",
        "utility": "regulated_utilities",
        "reit": "equity_reit",
        # 中文别名
        "半导体": "semiconductors",
        "芯片": "semiconductors",
        "生物医药": "biotech",
        "生物科技": "biotech",
        "制药": "pharma",
        "白酒": "food_beverage",
        "食品": "food_beverage",
        "银行": "banks",
        "软件": "software",
        "汽车": "autos",
    }

    def __init__(self):
        self.version = "1.0.0"

    def get_record(self, industry_id: str) -> IndustryMappingRecord:
        """根据细分行业 ID 获取映射档案 (支持大小写与别名兼容)."""
        clean_id = industry_id.strip().lower()
        clean_id = self._ALIAS_MAP.get(clean_id, clean_id)

        if clean_id in self._RECORDS:
            return self._RECORDS[clean_id]

        # 若未完全匹配，尝试按前缀或子串搜索
        for k, v in self._RECORDS.items():
            if k in clean_id or clean_id in k:
                return v

        # 默认安全降级到商业与专业服务 (PROF_SERV)
        return IndustryMappingRecord(
            industry_id=clean_id,
            industry_name_zh="通用综合行业",
            sector_id="industrials",
            sector_name_zh="工业与综合",
            macro_sector_id="PROF_SERV",
            macro_sector_name_zh="专业科技研发、法律财税与企业综合服务",
            typical_cogs_ratio=0.60,
            typical_markup_ratio=1.10,
        )

    def resolve_industry_from_ticker_or_sector(
        self,
        ticker: str,
        sector: str,
        raw_industry: Optional[str] = None,
    ) -> IndustryMappingRecord:
        """从标的代码、板块或原始行业标签解析三层归一映射."""
        if raw_industry:
            rec = self.get_record(raw_industry)
            if rec.industry_name_zh != "通用综合行业":
                return rec

        if sector:
            rec = self.get_record(sector)
            if rec.industry_name_zh != "通用综合行业":
                return rec

        # 从标的代码特定特征辅助推断
        t = ticker.strip().upper()
        if t in ["NVDA", "AMD", "INTC", "TSM", "ASML", "QCOM", "AVGO", "TXN", "MU", "ARM"]:
            return self._RECORDS["semiconductors"]
        elif t in ["RXRX", "MRNA", "BIIB", "VRTX", "REGN", "BNTX", "ILMN"]:
            return self._RECORDS["biotech"]
        elif t in ["PFE", "JNJ", "LLY", "ABBV", "NVO", "MRK"]:
            return self._RECORDS["pharma"]
        elif t in ["000858", "600519", "000568", "KO", "PEP", "BUD"]:
            return self._RECORDS["food_beverage"]
        elif t in ["MSFT", "ORCL", "CRM", "SAP", "ADBE", "SNOW", "PLTR"]:
            return self._RECORDS["software"]
        elif t in ["AAPL", "DELL", "HPQ", "STX", "WDC"]:
            return self._RECORDS["hardware"]
        elif t in ["JPM", "BAC", "WFC", "C", "GS", "MS"]:
            return self._RECORDS["banks"]
        elif t in ["TSLA", "TM", "F", "GM", "RACE"]:
            return self._RECORDS["autos"]

        # 从原始行业和板块综合字符串中提取行业关键词特征
        combined_text = f"{raw_industry or ''} {sector or ''}".lower()
        if any(k in combined_text for k in ["semi_equipment", "semiconductor_equipment", "wafer_fab"]):
            return self._RECORDS["semi_equipment"]
        if any(k in combined_text for k in ["semi", "chip", "wafer", "optics"]):
            return self._RECORDS["semiconductors"]
        if any(k in combined_text for k in ["hardware", "electronic_components", "mlcc"]):
            return self._RECORDS["hardware"]
        if any(k in combined_text for k in ["software", "cloud", "saas", "cyber"]):
            return self._RECORDS["software"]
        if any(k in combined_text for k in ["interactive_media", "streaming", "internet", "platform", "digital"]):
            return self._RECORDS["digital_platforms"]
        if any(k in combined_text for k in ["bank", "banking"]):
            return self._RECORDS["banks"]
        if any(k in combined_text for k in ["insurance"]):
            return self._RECORDS["insurance"]
        if any(k in combined_text for k in ["financial", "broker", "asset_mgmt", "holding", "invest"]):
            return self._RECORDS["asset_management"]
        if any(k in combined_text for k in ["oil", "gas", "energy", "petro"]):
            return self._RECORDS["oil_gas"]
        if any(k in combined_text for k in ["mining", "metals"]):
            return self._RECORDS["mining"]
        if any(k in combined_text for k in ["chemical", "materials"]):
            return self._RECORDS["chemicals"]
        if any(k in combined_text for k in ["biotech", "genom"]):
            return self._RECORDS["biotech"]
        if any(k in combined_text for k in ["pharma", "drug"]):
            return self._RECORDS["pharma"]
        if any(k in combined_text for k in ["medical", "health"]):
            return self._RECORDS["medical_devices"]
        if any(k in combined_text for k in ["auto", "motor", "vehicle"]):
            return self._RECORDS["autos"]
        if any(k in combined_text for k in ["aerospace", "defense"]):
            return self._RECORDS["aerospace_defense"]
        if any(k in combined_text for k in ["industrial", "automation", "machinery", "robot", "equipment"]):
            return self._RECORDS["capital_goods"]
        if any(k in combined_text for k in ["trade", "trading", "logistics", "shipping", "transport", "airline", "rail"]):
            return self._RECORDS["transport_logistics"]
        if any(k in combined_text for k in ["power", "utility", "grid", "water"]):
            return self._RECORDS["regulated_utilities"]
        if any(k in combined_text for k in ["reit"]):
            return self._RECORDS["equity_reit"]
        if any(k in combined_text for k in ["real_estate", "property", "construction"]):
            return self._RECORDS["construction"]
        if any(k in combined_text for k in ["food", "beverage", "drink", "tobacco", "agriculture"]):
            return self._RECORDS["food_beverage"]
        if any(k in combined_text for k in ["retail", "consumer", "apparel", "luxury"]):
            return self._RECORDS["retail"]
        if any(k in combined_text for k in ["household", "personal"]):
            return self._RECORDS["household_personal"]

        return self.get_record(sector or "general")

    def get_all_records(self) -> List[IndustryMappingRecord]:
        """获取全量 41 细分行业映射档案清单."""
        return list(self._RECORDS.values())

    def get_industries_by_macro_sector(self, macro_sector_id: str) -> List[IndustryMappingRecord]:
        """获取指定 OECD 宏观部门涵盖的所有细分行业."""
        m_id = macro_sector_id.strip().upper()
        return [r for r in self._RECORDS.values() if r.macro_sector_id == m_id]
