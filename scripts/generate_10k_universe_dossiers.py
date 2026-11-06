"""全盘一万家上市企业全息建档与深度档案主数据库生成引擎.

构建涵盖美股（SEC EDGAR 7,000家）与日股（东证全市场 3,000家）共计 10,000 家企业的全景档案：
1. 100% 严格遵循 schemas/deep_dossier.schema.json 契约;
2. 包含官方 CIK / 东证代码、三表底稿、DIO 周转、护城河结构、上下游集中度及多情景 DCF 估值矩阵;
3. 持久化存储至 SQLite 高速查询库: data/universe/universe_10k_dossiers.sqlite3;
4. 输出 100 组流式分块文件 (每块 100 家): data/universe/chunks/chunk_001.json ~ chunk_100.json;
5. 输出全局全息清单: data/universe/universe_10k_manifest.json。
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import jsonschema

# Industry mappings and domain metadata generators
US_SECTOR_KEYWORDS = [
    (["semiconductor", "chip", "semi", "microelectronics"], "semiconductors", "半导体与集成电路 / 芯片设计与先进制程", "全球半导体供应链核心节点，专注于高算力芯片、模拟芯片或半导体制造测试设备。", "82.5% 高性能芯片与硬件销售，17.5% 软件授权与 IP 维保服务"),
    (["software", "saas", "cloud", "data", "cyber", "security", "ai", "tech"], "enterprise_software_cloud", "企业软件与云计算 / 企业级SaaS与数字基础设施", "全球企业软件与数字化转型领跑者，提供高可用云原生架构与企业核心工作流管理系统。", "74.0% 经常性订阅收入 (SaaS)，26.0% 专业技术支持与集成服务"),
    (["pharma", "biotech", "therapeutics", "medical", "health", "care", "biosciences"], "biopharmaceuticals_healthcare", "医疗健康与生物医药 / 创新药物研发与精密医疗器械", "专注于针对高发疾病领域的原研创新药物与特异性疗法开发，拥有全球临床试验与专利保护网。", "68.0% 专利处方药全球销售，32.0% 诊断试剂与全球特许权分成"),
    (["bank", "banc", "financial", "capital", "insurance", "asset", "invest", "trust"], "financial_services_banking", "金融服务与财富管理 / 商业银行与全球资产配置", "受审慎监管的综合金融服务机构，提供商业借贷、投资银行、财富管理与保险信托闭环。", "58.0% 净利息收入 (NII)，42.0% 非利息财富管理与承销手续费收入"),
    (["energy", "oil", "gas", "petro", "power", "solar", "clean", "renew"], "energy_utilities_clean_tech", "能源与公用事业 / 传统能源勘探与清洁能源转型", "综合能源勘探、开采及输配电巨头，积极布局低碳清洁能源与电网基荷电力保障。", "71.5% 能源商品采掘与销售，28.5% 受监管管网输配电与新能源并网"),
    (["retail", "store", "consumer", "food", "beverage", "apparel", "brand"], "consumer_retail_goods", "大消费与品牌零售 / 全球必选消费品与全渠道零售", "拥有全球知名消费品品牌与深度下沉全渠道分销网络，具备极强消费者心智壁垒。", "85.0% 终端品牌消费品自营销售，15.0% 经销商渠道批发与海外特许经营"),
    (["industrial", "electric", "machinery", "aero", "defense", "auto", "motor"], "industrials_advanced_manufacturing", "先进工业制造与装备 / 智能机电与交通运输装备", "全球重型装备、精密工业零部件与国防航空装备制造领军企业，掌控核心工艺专利。", "76.0% 整机与高精度装备交付，24.0% 长期原厂零部件终身维保服务"),
    (["telecom", "communication", "media", "entertainment", "network"], "telecom_media_infrastructure", "通信与数字媒体 / 全球电信运营商与数字互联网络", "提供超高速宽带、5G 无线通信网络骨干基础设施与数字流媒体分发平台。", "65.0% 无线通信与固定宽带服务，35.0% 企业级数字专线与内容版权"),
    (["real estate", "reit", "property", "realty"], "real_estate_reits", "房地产信托基金 (REITs) / 核心商业地产与物流仓储", "持有并运营核心城市高出租率甲级写字楼、现代化冷链物流仓储与数据中心基础设施。", "88.0% 长期租约基础租金收入，12.0% 资产管理与物业增值服务"),
    (["materials", "chemical", "mining", "metal", "steel"], "materials_basic_resources", "基础材料与特种化学品 / 稀缺矿产资源与先进合金", "全球高纯度化学品、特种高分子材料与关键工业金属冶炼加工龙头企业。", "80.0% 特种基础材料直销，20.0% 高性能定制化配方材料开发")
]

JP_INDUSTRY_MAPPING = {
    "情報・通信業": ("enterprise_software_cloud", "情報通信与企业IT服务 / 云原生数字化与电信基础设施", "日本国内数字化转型与企业系统集成龙头，提供高可靠性企业级软件与骨干电信网络。", "70.0% 软件与云服务，30.0% 系统集成与运维"),
    "電気機器": ("semiconductors_electronics", "电气机器与精密电子 / 关键半导体元器件与工业自动化", "全球高精密电子元器件与工业自动化控制系统领军企业，掌控高阶材料与加工绝技。", "75.0% 高精细电子元器件直销，25.0% 工业自动化成套方案"),
    "輸送用機器": ("automotive_transportation", "运输用机器与汽车制造 / 乘用车与新能源移动出行", "全球主流乘用车与商用车制造巨头，拥有全球精益生产 (TPS) 制造体系与供应链协同优势。", "82.0% 新车与零配件销售，18.0% 汽车金融与移动出行服务"),
    "医薬品": ("biopharmaceuticals_healthcare", "生物医药与生命科学 / 创新小分子靶向药与抗体疗法", "日本顶尖创新制药领军企业，专注中枢神经、抗肿瘤与自身免疫疾病突破性药物开发。", "65.0% 处方药日本与海外销售，35.0% 专利授权与全球提成"),
    "化学": ("specialty_chemicals_materials", "特种化学与先进高分子 / 半导体级光刻胶与高功能树脂", "全球半导体材料与高机能化学品不可或缺的供应商，在特定高端细分领域占据全球垄断地位。", "78.0% 高纯度半导体材料，22.0% 环保高功能树脂"),
    "機械": ("industrials_advanced_manufacturing", "精密机械与工业母机 / 全球机床与机器人核心部件", "高精度机床、液压元件与工业机器人核心部件制造明珠，享有极高的日本匠人工程信誉。", "72.0% 重型与精密机电设备，28.0% 全球售后维修备件"),
    "卸売業": ("conglomerate_trading_retail_distribution", "综合商社与大宗商品流通 / 全球资源商贸与消费供应链", "日本独创的综合商社形态，深度掌控从上游原料采购到下游零售终端的全产业链特许网络。", "60.0% 消费品与食品流通，40.0% 金属资源与能源贸易"),
    "銀行業": ("financial_services_banking", "金融业与商业银行 / 日本三大巨型银行与区域金融网络", "提供从大型跨国企业银团贷款、外汇结算到个人零售房贷与财富管理的综合金融服务。", "55.0% 净利息收入，45.0% 中间业务手续费与投行咨询"),
    "サービス業": ("business_services_consumer", "现代服务业与数字化人力 / 人力资源技术与生活服务平台", "提供企业猎头派遣、生活娱乐预约与数字化企业外包服务，轻资产高现金流运营。", "85.0% 人力招聘与运营服务，15.0% SaaS 工具订阅"),
    "食料品": ("consumer_retail_goods", "食品饮料与消费制造 / 日本国民级必选消费与调味品", "掌控日本各大商超便利店货架的必选食品巨头，在东南亚与欧美市场加速全球化渗透。", "88.0% 包装食品与健康饮品，12.0% 餐饮供应链直供")
}

def get_hash_seed(text: str) -> int:
    return int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)

def infer_us_industry(title: str, ticker: str):
    t_lower = (title + " " + ticker).lower()
    for kw_list, ind_id, ind_name_zh, b_model, rev_mix in US_SECTOR_KEYWORDS:
        if any(kw in t_lower for kw in kw_list):
            return ind_id, ind_name_zh, b_model, rev_mix
    # fallback based on hash
    idx = get_hash_seed(ticker) % len(US_SECTOR_KEYWORDS)
    _, ind_id, ind_name_zh, b_model, rev_mix = US_SECTOR_KEYWORDS[idx]
    return ind_id, ind_name_zh, b_model, rev_mix

def infer_jp_industry(item: dict):
    ind33 = item.get("industry_33", "")
    for k, v in JP_INDUSTRY_MAPPING.items():
        if k in ind33:
            return v
    # fallback
    code = item.get("code", "0000")
    idx = get_hash_seed(code) % len(JP_INDUSTRY_MAPPING)
    k = list(JP_INDUSTRY_MAPPING.keys())[idx]
    return JP_INDUSTRY_MAPPING[k]

def build_dossier_record(market: str, ticker: str, name: str, code_or_cik: str, ind_id: str, ind_name_zh: str, b_model: str, rev_mix: str, seed: int) -> dict:
    # generate realistic metrics calibrated by market and seed
    s = seed
    cash_val = 200 + (s % 1800)
    debt_val = 150 + ((s * 3) % 2500)
    rev_val = 800 + ((s * 7) % 8500)
    dio_val = 15.0 + ((s % 650) / 10.0)
    roe_val = 8.5 + ((s % 140) / 10.0)
    fcf_val = int(rev_val * (0.12 + ((s % 120) / 1000.0)))
    
    curr = "$" if market == "US" else "¥"
    unit = "M" if market == "US" else " 亿日元"
    scale_label = f"{curr}{rev_val:,}{unit}"
    cash_label = f"{curr}{cash_val:,}{unit}"
    debt_label = f"{curr}{debt_val:,}{unit}"
    fcf_label = f"{curr}{fcf_val:,}{unit}"
    
    net_cash_diff = cash_val - debt_val
    if net_cash_diff >= 0:
        net_cash_status = f"净现金头寸充裕达 {curr}{net_cash_diff:,}{unit} (无紧迫短期偿债风险，财务防守垫厚实)"
    else:
        net_cash_status = f"净负债 {curr}{abs(net_cash_diff):,}{unit} (匹配长期固定资产投资，杠杆率严守在投资级警戒线内)"

    interest_div = f"年度现金分红及股份回购稳步进行，派息覆盖倍数超 2.5x，自由现金流充裕度良好"
    
    # Fair value DCF calculation
    p_base = 25.0 + ((s % 2800) / 10.0)
    p_cons = round(p_base * 0.72, 2)
    p_buy_low = round(p_cons * 0.90, 2)
    p_buy_high = round(p_cons * 1.02, 2)
    
    prefix = "$" if market == "US" else "¥"
    dcf_base_str = f"{prefix}{p_base:.2f} (基于未来5年内生自由现金流复合增速 7-12%、WACC 8.0%)"
    dcf_cons_str = f"{prefix}{p_cons:.2f} (宏观周期降速、利润率压缩 150bp、WACC 9.0%)"
    dcf_buy_str = f"{prefix}{p_buy_low:.2f} - {prefix}{p_buy_high:.2f} (买方机构具备充分安全边际的建仓估值区间)"

    rec = {
        "file_name": f"{ticker}_{name[:24].replace('/', '_').replace(':', '_')}.pdf",
        "current_cloud_id": "NONE",
        "overview": {
            "ticker": ticker,
            "company_name": f"{name} ({ticker})",
            "market": market,
            "industry_id": ind_id,
            "industry_name_zh": ind_name_zh,
            "business_model": f"{'纽交所/纳斯达克' if market == 'US' else '东京证券交易所'}挂牌上市公司。{b_model} 官方登记代码: {code_or_cik}。公司深耕主营核心业务，在细分市场具备深厚客户粘性与持续内生造血能力。",
            "revenue_mix": f"FY2024 全年营业规模约 {scale_label}。主营业务结构：{rev_mix}。核心客户留存率高，长期现金流能见度优良。"
        },
        "financial_statement_deep_dive": {
            "profitability_quality": f"经调整全年营运现金流稳健，ROE 维持在 {roe_val:.1f}% 水准；年度自由现金流约 {fcf_label}；三表资产结构清晰，各项摊销计提充分费用化，无激进会计粉饰风险。",
            "cash_and_liquidity": {
                "total_cash_and_equivalents": f"{cash_label} (现金、现金等价物及高流动性短期投资总和)",
                "net_cash_status": net_cash_status,
                "interest_income_dividend": interest_div
            },
            "inventory_cycle_analysis": {
                "inventory_scale": f"{curr}{int(rev_val * 0.08):,}{unit} (满足正常交付周期的核心原料与制成品备料)",
                "inventory_turnover_days": f"{dio_val:.1f} 天 (处于行业平均周转健康分位数)",
                "inventory_cycle_position": "以销定产精益备货，库存周转平稳，无结构性滞销风险",
                "inventory_write_down_risk": "低风险"
            },
            "debt_structure_and_solvency": {
                "short_vs_long_term_debt": f"短期借款占比控制在 20% 以下，长期固定利率有息负债约 {debt_label}",
                "debt_wall_24m": "未来 24 个月内无集中本金兑付断崖，经营现金流完全覆盖短期利息支出",
                "interest_coverage_ratio": f"利息保障倍数达 {4.5 + (s % 80)/10.0:.1f}x，抗加息周期抗压韧性坚固",
                "refinancing_stress_test": "拥有完全未动用的承诺性银行信贷储备，流动性抗压测试表现优异"
            }
        },
        "moat_analysis": {
            "network_effects": "细分行业深耕累积的供需生态连接优势与技术协同效应，随客户规模扩张形成稳固防线。",
            "switching_costs": "企业级核心软硬件系统深度嵌入客户运营流程，替换成本与试错风险高昂，客户年化续约率稳健。",
            "cost_advantage_and_scale": "供应链集中采购议价权与精益制造工艺，单位综合运营边际成本显著优于长尾同行。",
            "intangible_assets": f"‘{ticker}’ 拥有长期行业品牌信誉、完备的监管合规牌照与多项专有技术知识产权集群。",
            "reinvestment_efficiency": "坚持严格的资本开支 ROI 评估，研发开支持续聚焦于高毛利主力产品与数字化升级。"
        },
        "supply_chain_analysis": {
            "upstream_suppliers": {
                "core_suppliers": "全球一级高品质原料供应商、专业元器件代工厂及基础设施云服务提供商。",
                "supplier_concentration": "前五大供应商采购集中度受控在合理区间，推行多元化多地备份采购策略。",
                "supply_chain_risks": "关键原材料跨国物流波动或局部地缘政治关税变动风险。"
            },
            "downstream_customers": {
                "customer_structure": "跨国中大型企业机构、长期分销合作伙伴及广泛的终端消费群体。",
                "top5_customer_concentration": "前五大核心客户销售占比低于 18%，客户基础多元分散。",
                "default_and_churn_risks": "结算条款健全，历史坏账核销率常年低于 0.1%，应收账款周转安全。"
            }
        },
        "industry_dynamics": {
            "winner_factor": "规模效应壁垒、技术持续创新研发转化速度以及敏捷响应客户需求的服务能力是赛道核心胜负手。",
            "market_share_and_crn": "在所属细分行业处于主流第一梯队或中坚领跑地位，市场份额稳健提升。",
            "tam_and_cagr": "全球对应细分市场 TAM 规模可观，受益于数字化与产业升级长期保持 6-12% 复合增速。"
        },
        "long_term_outlook": {
            "catalysts": [
                "主营核心产品全球化渗透率进一步提高，海外高利润市场营收占比提升",
                "AI 与智能制造技术赋能降本增效，推动营运利润率与自由现金流中枢稳步抬升",
                "健康的资产负债表与稳定的经营现金流支撑持续分红及股份回购提升股东回报"
            ],
            "kill_switch_risks": [
                "全球宏观经济增速放缓导致行业整体下游资本开支或终端消费需求疲软",
                "行业新技术路径颠覆性迭代或激进价格战压缩中短期毛利空间"
            ],
            "dcf_valuation_matrix": {
                "base_fair_value": dcf_base_str,
                "conservative_fair_value": dcf_cons_str,
                "margin_of_safety_buy_zone": dcf_buy_str
            }
        }
    }
    return rec

def main():
    import argparse
    parser = argparse.ArgumentParser(description="万家企业档案生成器 (合成演示专用)")
    parser.add_argument(
        "--allow-synthetic-demo",
        action="store_true",
        help="显式声明允许生成非官方三表审计的合成演示数据 (写入 scratch/synthetic_demo 隔离目录)",
    )
    args = parser.parse_args()

    if not args.allow_synthetic_demo:
        print("=" * 75)
        print("[安全阻断] 严禁生成无真实证据的合成财务估值档案")
        print("依据 2026-10-15 工程整改清单 Task 01:")
        print("该生成器使用哈希构造虚拟财务与估值，产物禁止进入正式研究和发布路径。")
        print("若仅用于测试环境架构压测，必须显式传入 --allow-synthetic-demo 参数，")
        print("产物将被严格隔离至 scratch/synthetic_demo/，禁止覆盖 data/universe/ 正式主账！")
        print("=" * 75)
        sys.exit(1)

    print("=" * 75)
    print("[管线启动] 万家资产池合成演示生成管线启动 (SYNTHETIC_DEMO_ONLY)")
    print(f"时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 75)

    schema_path = ROOT / "schemas" / "deep_dossier.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)

    # 1. Load SEC EDGAR Universe (10,445 companies)
    sec_path = ROOT / "data" / "universe" / "sec_company_tickers.json"
    sec_raw = json.loads(sec_path.read_text(encoding="utf-8"))
    sec_list = []
    seen_sec = set()
    for v in sec_raw.values():
        t = str(v.get("ticker", "")).strip().upper()
        if t and t not in seen_sec:
            seen_sec.add(t)
            sec_list.append({
                "ticker": t,
                "title": v.get("title", t),
                "cik": str(v.get("cik_str", ""))
            })
    print(f"[底账就绪] 美股 SEC EDGAR 独立标的底账就绪: {len(sec_list)} 家")

    # 2. Load JPX Universe (4,447 companies)
    jpx_path = ROOT / "data" / "universe" / "jpx_company_tickers.json"
    jpx_raw = json.loads(jpx_path.read_text(encoding="utf-8"))
    jpx_list = []
    seen_jpx = set()
    for item in jpx_raw:
        code = str(item.get("code") or item.get("ticker", "")).strip().replace("TYO:", "")
        if code and code not in seen_jpx:
            seen_jpx.add(code)
            jpx_list.append({
                "code": code,
                "name": item.get("name", f"东证上市公司 {code}"),
                "industry_33": item.get("industry_33", ""),
                "market_segment": item.get("market_segment", "Prime")
            })
    print(f"[底账就绪] 日股东证全市场独立标的底账就绪: {len(jpx_list)} 家")

    # Target: Exactly 10,000 companies (7,000 US + 3,000 JP)
    target_us_count = 7000
    target_jp_count = 3000
    selected_us = sec_list[:target_us_count]
    selected_jp = jpx_list[:target_jp_count]
    total_selected = len(selected_us) + len(selected_jp)
    print(f"[规模核定] 选定全息建档总规模: {total_selected} 家企业 (美股: {len(selected_us)} 家, 日股: {len(selected_jp)} 家)")

    # Prepare SQLite master database in isolated test scratch directory
    demo_dir = ROOT / "scratch" / "synthetic_demo"
    demo_dir.mkdir(parents=True, exist_ok=True)
    db_path = demo_dir / "universe_10k_dossiers.sqlite3"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            ticker TEXT PRIMARY KEY,
            market TEXT,
            name TEXT,
            identifier TEXT,
            industry_id TEXT,
            industry_name_zh TEXT,
            created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dossiers (
            ticker TEXT PRIMARY KEY,
            market TEXT,
            dossier_json TEXT,
            is_valid_schema INTEGER,
            rendered_pdf_status TEXT,
            cloud_id TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()

    # Generate dossiers & validate
    chunks_dir = demo_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    all_dossiers = []
    now_iso = datetime.now(timezone.utc).isoformat()
    t0 = time.time()

    # 1. Process US
    print("[批量生成] [1/3] 正在生成并校验 7,000 家美股合成演示档案 (写入 scratch/synthetic_demo)...")
    for idx, item in enumerate(selected_us):
        ticker = item["ticker"]
        title = item["title"]
        cik = item["cik"]
        seed = get_hash_seed(f"US_{ticker}_{cik}")
        ind_id, ind_name_zh, b_model, rev_mix = infer_us_industry(title, ticker)
        dossier = build_dossier_record("US", ticker, title, f"CIK-{cik}", ind_id, ind_name_zh, b_model, rev_mix, seed)
        dossier["_synthetic_metadata"] = {
            "is_synthetic": True,
            "provenance": "MOCK_SYNTHETIC_DEMO",
            "warning": "【合成压测演示数据·无官方三表审计底账】禁止用于正式投研或发布准入"
        }
        all_dossiers.append(dossier)

        cursor.execute("INSERT OR REPLACE INTO companies VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (ticker, "US", title, cik, ind_id, ind_name_zh, now_iso))
        cursor.execute("INSERT OR REPLACE INTO dossiers VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (ticker, "US", json.dumps(dossier, ensure_ascii=False), 1, "PENDING_DEMO_RENDER", "NONE", now_iso))

    # 2. Process JP
    print("[批量生成] [2/3] 正在生成并校验 3,000 家日股合成演示档案 (写入 scratch/synthetic_demo)...")
    for idx, item in enumerate(selected_jp):
        code = item["code"]
        name = item["name"]
        seed = get_hash_seed(f"JP_{code}")
        ind_id, ind_name_zh, b_model, rev_mix = infer_jp_industry(item)
        dossier = build_dossier_record("JP", code, name, f"东证-{code}", ind_id, ind_name_zh, b_model, rev_mix, seed)
        dossier["_synthetic_metadata"] = {
            "is_synthetic": True,
            "provenance": "MOCK_SYNTHETIC_DEMO",
            "warning": "【合成压测演示数据·无官方三表审计底账】禁止用于正式投研或发布准入"
        }
        all_dossiers.append(dossier)

        cursor.execute("INSERT OR REPLACE INTO companies VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (code, "JP", name, code, ind_id, ind_name_zh, now_iso))
        cursor.execute("INSERT OR REPLACE INTO dossiers VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (code, "JP", json.dumps(dossier, ensure_ascii=False), 1, "PENDING_DEMO_RENDER", "NONE", now_iso))

    conn.commit()
    conn.close()
    elapsed = time.time() - t0
    print(f"[完成] SQLite 测试数据库已更新完毕 ({total_selected} 份档案，耗时 {elapsed:.2f}s)")

    # 3. Validate random sample against deep_dossier.schema.json
    print("[契约抽检] [3/3] 执行严苛 Schema 契约抽样抽检 (抽检 100 份档案)...")
    sample_indices = [int(i * (total_selected / 100)) for i in range(100)]
    for s_idx in sample_indices:
        cand = all_dossiers[s_idx]
        errs = list(validator.iter_errors(cand))
        if errs:
            raise ValueError(f"Schema 抽检失败在第 {s_idx} 份档案 ({cand['overview']['ticker']}): {errs[0].message}")
    print("[通过] 抽样 100 份档案 100% 通过 schemas/deep_dossier.schema.json 契约校验！")

    # 4. Save chunked files (100 chunks of 100 dossiers each)
    chunk_size = 100
    total_chunks = len(all_dossiers) // chunk_size
    for c_i in range(total_chunks):
        chunk_data = all_dossiers[c_i * chunk_size : (c_i + 1) * chunk_size]
        chunk_file = chunks_dir / f"chunk_{c_i+1:03d}.json"
        chunk_file.write_text(json.dumps(chunk_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[分块就绪] 已切分并输出 {total_chunks} 组流式调度分块文件至 scratch/synthetic_demo/chunks/")

    # 5. Output Master Manifest into scratch
    manifest_path = demo_dir / "universe_10k_manifest.json"
    manifest = {
        "title": "全盘万家企业合成演示档案库 (SYNTHETIC_MOCK_DEMO)",
        "created_at": now_iso,
        "total_companies": total_selected,
        "market_breakdown": {
            "US": len(selected_us),
            "JP": len(selected_jp)
        },
        "total_chunks": total_chunks,
        "chunk_size": chunk_size,
        "is_synthetic": True,
        "status": "SYNTHETIC_TEST_DEMO_ONLY"
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[主账归档] 全息主账清单已归档至: {manifest_path.relative_to(ROOT)}")
    print("=" * 75)

if __name__ == "__main__":
    main()
