# -*- coding: utf-8 -*-
"""水源分析终端权威离线资产库与篮子定义 (Universe Definitions & Baskets).

层级归属: Layer 2 (finance_tools/governance_and_pipeline)
符合四层单向依赖架构规范，上层 reporting 与 scripts 均可合法引用。
"""

from typing import Any, Dict

# 权威离线资产库定义 (按行业与资产类别归类，涵盖买方精选核心池)
REPLENISHMENT_UNIVERSE: Dict[str, Dict[str, Any]] = {
    # --- 1. 全球核心指数与主题 ETF (Core & Thematic ETFs) ---
    "SPY": {"name_zh": "标普500指数 ETF", "category": "core_etfs", "market": "US", "currency": "USD", "price": 735.34, "prev_close": 730.20},
    "QQQ": {"name_zh": "纳斯达克100指数 ETF", "category": "core_etfs", "market": "US", "currency": "USD", "price": 656.10, "prev_close": 648.50},
    "DIA": {"name_zh": "道琼斯工业平均指数 ETF", "category": "core_etfs", "market": "US", "currency": "USD", "price": 468.20, "prev_close": 469.10},
    "IWM": {"name_zh": "罗素2000小型股 ETF", "category": "core_etfs", "market": "US", "currency": "USD", "price": 242.80, "prev_close": 239.50},
    "SMH": {"name_zh": "VanEck 费城半导体芯片 ETF", "category": "core_etfs", "market": "US", "currency": "USD", "price": 454.62, "prev_close": 445.80},
    "XLK": {"name_zh": "科技精选行业 SPDR 基金", "category": "core_etfs", "market": "US", "currency": "USD", "price": 248.50, "prev_close": 246.20},
    "XLE": {"name_zh": "能源精选行业 SPDR 基金", "category": "core_etfs", "market": "US", "currency": "USD", "price": 92.40, "prev_close": 91.80},
    "XBI": {"name_zh": "SPDR 标普生物科技 ETF", "category": "core_etfs", "market": "US", "currency": "USD", "price": 102.30, "prev_close": 100.90},
    "SCHD": {"name_zh": "嘉信美国高股息 ETF", "category": "core_etfs", "market": "US", "currency": "USD", "price": 82.40, "prev_close": 82.10},
    "VIG": {"name_zh": "Vanguard 股息增长 ETF", "category": "core_etfs", "market": "US", "currency": "USD", "price": 194.50, "prev_close": 193.80},
    "TLT": {"name_zh": "20年期以上美国国债 ETF", "category": "core_etfs", "market": "US", "currency": "USD", "price": 88.50, "prev_close": 89.20},
    "IEF": {"name_zh": "7-10年期美国国债 ETF", "category": "core_etfs", "market": "US", "currency": "USD", "price": 94.20, "prev_close": 94.50},
    "HYG": {"name_zh": "iShares 高收益公司债 ETF", "category": "core_etfs", "market": "US", "currency": "USD", "price": 78.60, "prev_close": 78.40},
    "1306": {"name_zh": "东证指数 TOPIX ETF (日本大盘)", "category": "core_etfs", "market": "JP", "currency": "JPY", "price": 3726.50, "prev_close": 3710.00},

    # --- 2. 黄金与特级贵金属大宗商品 (Gold & Precious Metals) ---
    "GLD": {"name_zh": "SPDR 黄金信托 (全球最大实物黄金ETF)", "category": "gold_metals", "market": "US", "currency": "USD", "price": 238.50, "prev_close": 241.10},
    "IAU": {"name_zh": "iShares 黄金信托 (低费率黄金储备)", "category": "gold_metals", "market": "US", "currency": "USD", "price": 48.20, "prev_close": 48.70},
    "SLV": {"name_zh": "iShares 白银信托 (工业与货币双属性)", "category": "gold_metals", "market": "US", "currency": "USD", "price": 28.40, "prev_close": 28.90},
    "NEM": {"name_zh": "纽蒙特矿业 (全球第一大特级金矿航母)", "category": "gold_metals", "market": "US", "currency": "USD", "price": 44.80, "prev_close": 43.90},
    "GOLD": {"name_zh": "巴里克黄金 (全球第二大特级金矿巨擘)", "category": "gold_metals", "market": "US", "currency": "USD", "price": 18.60, "prev_close": 18.20},
    "AEM": {"name_zh": "阿尼科阿格尼科矿业 (极低地缘政治风险金矿)", "category": "gold_metals", "market": "US", "currency": "USD", "price": 84.20, "prev_close": 82.80},
    "WPM": {"name_zh": "惠顿贵金属 (流转协议轻资产暴利现金牛)", "category": "gold_metals", "market": "US", "currency": "USD", "price": 62.50, "prev_close": 61.40},
    "GDX": {"name_zh": "VanEck 黄金矿业 ETF (金价经营杠杆放大器)", "category": "gold_metals", "market": "US", "currency": "USD", "price": 38.90, "prev_close": 38.20},

    # --- 3. 科技与 AI 产业链上下游核心标的 (Tech & AI Compute) ---
    "NVDA": {"name_zh": "英伟达 (AI 算力 GPU 全球垄断霸主)", "category": "tech_ai", "market": "US", "currency": "USD", "price": 186.64, "prev_close": 179.80},
    "AMD": {"name_zh": "超微半导体 (MI350/MI400 算力多元化代表)", "category": "tech_ai", "market": "US", "currency": "USD", "price": 449.04, "prev_close": 438.50},
    "TSM": {"name_zh": "台积电 ADR (先进制程晶圆代工与CoWoS绝对垄断)", "category": "tech_ai", "market": "US", "currency": "USD", "price": 375.44, "prev_close": 368.20},
    "AVGO": {"name_zh": "博通 (定制 AI ASIC 芯片与以太网高速光网络)", "category": "tech_ai", "market": "US", "currency": "USD", "price": 245.50, "prev_close": 241.00},
    "MSFT": {"name_zh": "微软公司 (Azure 云计算/Copilot生态)", "category": "tech_ai", "market": "US", "currency": "USD", "price": 507.12, "prev_close": 501.30},
    "GOOGL": {"name_zh": "谷歌母公司 Alphabet (Gemini多模态大模型/TPU)", "category": "tech_ai", "market": "US", "currency": "USD", "price": 312.40, "prev_close": 308.50},
    "META": {"name_zh": "Meta Platforms (开源 LLaMA 大模型/AI社交推荐)", "category": "tech_ai", "market": "US", "currency": "USD", "price": 685.20, "prev_close": 672.40},
    "AAPL": {"name_zh": "苹果公司 (端侧 AI 与 Apple Intelligence 硬件入口)", "category": "tech_ai", "market": "US", "currency": "USD", "price": 268.50, "prev_close": 265.20},
    "AMZN": {"name_zh": "亚马逊 (AWS 云计算与全球电商物流双引擎)", "category": "tech_ai", "market": "US", "currency": "USD", "price": 208.50, "prev_close": 206.20},
    "TSLA": {"name_zh": "特斯拉 (FSD 自动驾驶、Robotaxi 与新能源汽车)", "category": "tech_ai", "market": "US", "currency": "USD", "price": 248.50, "prev_close": 242.80},
    "STX": {"name_zh": "希捷科技 (HAMR 高密度机械硬盘海量存储)", "category": "tech_ai", "market": "US", "currency": "USD", "price": 132.80, "prev_close": 130.50},
    "PLTR": {"name_zh": "Palantir (企业与国防级本体 AI 智能平台 AIP)", "category": "tech_ai", "market": "US", "currency": "USD", "price": 175.40, "prev_close": 168.90},
    "IREN": {"name_zh": "IREN (可再生能源 AI 超算数据中心)", "category": "tech_ai", "market": "US", "currency": "USD", "price": 24.80, "prev_close": 23.90},
    "8035": {"name_zh": "东京电子 (EUV 涂布显影机 100% 绝对垄断)", "category": "tech_ai", "market": "JP", "currency": "JPY", "price": 8263.00, "prev_close": 8150.00},
    "6857": {"name_zh": "爱德万测试 (HBM3e/HBM4 测试机全球垄断)", "category": "tech_ai", "market": "JP", "currency": "JPY", "price": 9850.00, "prev_close": 9680.00},
    "9984": {"name_zh": "软银集团 (掌控 ARM 90% 股权/AI 生态主权投资)", "category": "tech_ai", "market": "JP", "currency": "JPY", "price": 11200.00, "prev_close": 11050.00},

    # --- 4. 高价值高成长潜力新星 (High-Value Growth Stars) ---
    "ARM": {"name_zh": "安谋控股 (移动端99%垄断/v9与自研CPU架构)", "category": "growth_stars", "market": "US", "currency": "USD", "price": 142.50, "prev_close": 139.80},
    "VRT": {"name_zh": "维谛技术 (AI算力中心液冷温控与高密电源基础设施)", "category": "growth_stars", "market": "US", "currency": "USD", "price": 108.40, "prev_close": 104.50},
    "CRWD": {"name_zh": "CrowdStrike (Falcon云原生平台与AI终端威胁防御)", "category": "growth_stars", "market": "US", "currency": "USD", "price": 324.60, "prev_close": 318.20},
    "NET": {"name_zh": "Cloudflare (全球边缘网络与Workers AI推理平台)", "category": "growth_stars", "market": "US", "currency": "USD", "price": 96.80, "prev_close": 94.20},
    "DDOG": {"name_zh": "Datadog (全栈云原生可观测性与大模型遥测监控)", "category": "growth_stars", "market": "US", "currency": "USD", "price": 128.50, "prev_close": 125.40},
    "MSTR": {"name_zh": "微策投资 (企业级比特币资本与杠杆国库运营)", "category": "growth_stars", "market": "US", "currency": "USD", "price": 218.40, "prev_close": 210.50},
    "ASTS": {"name_zh": "AST SpaceMobile (低轨宽带卫星直连手机蜂窝网络)", "category": "growth_stars", "market": "US", "currency": "USD", "price": 26.80, "prev_close": 25.40},
    "JOBY": {"name_zh": "Joby Aviation (eVTOL电动垂直起降低空经济先驱)", "category": "growth_stars", "market": "US", "currency": "USD", "price": 6.40, "prev_close": 6.25},
    "RKLB": {"name_zh": "火箭实验室 (商业运载火箭与太空航天器制造一体化)", "category": "growth_stars", "market": "US", "currency": "USD", "price": 11.20, "prev_close": 10.80},
    "MELI": {"name_zh": "自由市场 (拉美电商与Mercado Pago金融双飞轮)", "category": "growth_stars", "market": "US", "currency": "USD", "price": 2045.00, "prev_close": 2010.00},
    "IONQ": {"name_zh": "IonQ (离子阱量子计算全栈商业化系统前沿)", "category": "growth_stars", "market": "US", "currency": "USD", "price": 16.50, "prev_close": 15.90},
    "RDDT": {"name_zh": "Reddit (社区讨论与大模型知识库授权变现)", "category": "growth_stars", "market": "US", "currency": "USD", "price": 118.20, "prev_close": 112.50},
    "CAVA": {"name_zh": "CAVA Group (地中海风味高坪效连锁餐饮新星)", "category": "growth_stars", "market": "US", "currency": "USD", "price": 138.50, "prev_close": 134.20},
    "DUOL": {"name_zh": "多邻国 (AI原生自适应教育订阅变现独角兽)", "category": "growth_stars", "market": "US", "currency": "USD", "price": 295.40, "prev_close": 288.60},

    # --- 5. 买方防御与高质量现金流蓝筹 (Defensive Blue Chips) ---
    "LLY": {"name_zh": "礼来制药 (GLP-1 减重与阿尔茨海默病专利护城河)", "category": "defensive_bluechips", "market": "US", "currency": "USD", "price": 818.28, "prev_close": 815.00},
    "RXRX": {"name_zh": "Recursion AI制药 (BioNeMo 平台与TechBio先锋)", "category": "defensive_bluechips", "market": "US", "currency": "USD", "price": 4.36, "prev_close": 4.28},
    "INTU": {"name_zh": "财捷集团 (Intuit 企业智能财税工作流)", "category": "defensive_bluechips", "market": "US", "currency": "USD", "price": 650.00, "prev_close": 645.00},
    "7203": {"name_zh": "丰田汽车 (精益生产与HEV混动现金流造血基石)", "category": "defensive_bluechips", "market": "JP", "currency": "JPY", "price": 2910.50, "prev_close": 2895.00},
    "6501": {"name_zh": "日立制作所 (变压器电网与AI数据中心电力设备)", "category": "defensive_bluechips", "market": "JP", "currency": "JPY", "price": 4020.00, "prev_close": 3980.00},
    "7974": {"name_zh": "任天堂 (超级IP资产帝国与Switch次世代周期)", "category": "defensive_bluechips", "market": "JP", "currency": "JPY", "price": 8360.00, "prev_close": 8280.00},

    # --- 6. 宏观流动性与波动率指标 (Macro Sentiment) ---
    "^VIX": {"name_zh": "标普500波动率指数 (VIX 恐慌指数)", "category": "macro_sentiment", "market": "US", "currency": "USD", "price": 28.18, "prev_close": 27.50},
    "^N225VI": {"name_zh": "日经225波动率指数 (Nikkei VI)", "category": "macro_sentiment", "market": "JP", "currency": "JPY", "price": 29.80, "prev_close": 29.20},
    "DXY": {"name_zh": "美元指数 (DXY)", "category": "macro_sentiment", "market": "US", "currency": "USD", "price": 105.80, "prev_close": 105.60},
    "USDJPY": {"name_zh": "美元兑日元汇率 (USD/JPY)", "category": "macro_sentiment", "market": "JP", "currency": "JPY", "price": 154.20, "prev_close": 154.50},
    "^TNX": {"name_zh": "美国10年期国债收益率 (10Y Yield)", "category": "macro_sentiment", "market": "US", "currency": "USD", "price": 4.42, "prev_close": 4.40},
}

# 资产篮子定义与别名映射
BASKET_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "core_etfs": {
        "title": "全球核心指数与主题 ETF (14只)",
        "description": "涵盖宽基指数、芯片半导体、能源、生物科技、红利防御与美债基准",
        "category_key": "core_etfs",
    },
    "gold_metals": {
        "title": "黄金与特级贵金属体系 (8只)",
        "description": "实物黄金、白银信托、纽蒙特/巴里克等一级金矿资产与特许权公司",
        "category_key": "gold_metals",
    },
    "tech_ai": {
        "title": "科技与 AI 产业链算力垄断核心标的 (14只)",
        "description": "英伟达、台积电、博通、微软、谷歌、东京电子、爱德万测试等",
        "category_key": "tech_ai",
    },
    "growth_stars": {
        "title": "前沿领军高价值高成长新星 (14只)",
        "description": "ARM、维谛技术、CrowdStrike、Cloudflare、Palantir、太空经济与AI应用新星",
        "category_key": "growth_stars",
    },
    "defensive_bluechips": {
        "title": "高质量自由现金流防御蓝筹 (6只)",
        "description": "礼来、丰田汽车、日立制作所、任天堂等高护城河造血基石",
        "category_key": "defensive_bluechips",
    },
    "macro_sentiment": {
        "title": "宏观流动性与波动率恐慌指标 (5只)",
        "description": "VIX、日经VI、美元指数、美日汇率、10年期美债收益率",
        "category_key": "macro_sentiment",
    },
    "all_priority": {
        "title": "全盘全部重点优先标的 (共计 61 只)",
        "description": "覆盖上述所有六大核心篮子的全部优质资产",
        "category_key": "all",
    },
}
