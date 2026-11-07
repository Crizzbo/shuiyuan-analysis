"""AI 浏览器定向补数任务清单生成器 (Radar Browser Verification Checklist Generator).

严格遵循 2026-10-11 最新数据来源策略与合规契约:
1. 不采用需要 API Key、App ID、账号认证或额外联系身份配置的私有接口;
2. 本脚本专责从本地事件雷达账本 (data/ledger/event_radar.sqlite3) 中扫描待核查重大事件与社交媒体传闻;
3. 依据 16 大全景收集维度，自动生成针对官方监管/交易所/发行人权威门户的精准检索式与补数 SOP;
4. 脚本只生成浏览器补数清单，不扫描无关目录，不发起外部网络连接，由分析师或合法流程导入本地证据.
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# 将项目根目录添加至模块搜索路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


PORTAL_ROUTING_MAP = {
    "Geopolitical_CrossStrait": {
        "authority": "美国商务部工业与安全局 (BIS) / 台湾立法院公报处 / 美国财政部外国资产控制办公室 (OFAC)",
        "official_domains": ["bis.doc.gov", "federalregister.gov", "ly.gov.tw", "treasury.gov"],
        "recommended_query": 'site:federalregister.gov "Bureau of Industry and Security" OR site:bis.doc.gov "Entity List" "{entity}"',
        "document_type": "美国联邦公报正式规则 (Final Rule) / 出口管制实体清单更新公告 / 立法院三读公报",
        "archive_folder": "data_sources/official_filings/geopolitical",
    },
    "State_Policy_Regulatory": {
        "authority": "加州公用事业委员会 (CPUC) / 德州审计长公署经济发展处 / 州立法案跟踪系统",
        "official_domains": ["cpuc.ca.gov", "caiso.com", "comptroller.texas.gov", "leginfo.legislature.ca.gov"],
        "recommended_query": 'site:cpuc.ca.gov "Proposed Decision" OR "Order" "commercial demand" "{entity}"',
        "document_type": "州行政委员会裁决令 (Proposed Decision / Order) / 州立税收减免实施细则",
        "archive_folder": "data_sources/official_filings/regulations",
    },
    "Physical_Plant_Disruption": {
        "authority": "属地应急安全管理局 (DCMR/OSHA) / 上市公司投资者关系 (IR) 8-K / 港务安全通告",
        "official_domains": ["sec.gov", "osha.gov", "portofrotterdam.com"],
        "recommended_query": 'site:sec.gov "Item 8.01 Other Events" OR "Item 1.01" "{entity}" "fire" OR "disruption"',
        "document_type": "SEC 8-K 重大事件即时披露表 / 属地工业事故正式调查调查通报",
        "archive_folder": "data_sources/official_filings/disruptions",
    },
    "Supply_Chain_Chokepoint": {
        "authority": "英国海事贸易行动办公室 (UKMTO) / 苏伊士运河管理局 (SCA) / 巴拿马运河管理局 (ACP)",
        "official_domains": ["ukmto.org", "suezcanal.gov.eg", "pancanal.com"],
        "recommended_query": 'site:ukmto.org "Warning" OR "Notice" "{entity}" "Bab el-Mandeb" OR "Red Sea"',
        "document_type": "UKMTO 正式海事预警公报 (Warning/Advisory) / 运河管理局官方航行通告 (Circular)",
        "archive_folder": "data_sources/official_filings/maritime",
    },
    "Labor_Strikes_Port_Railways": {
        "authority": "国际码头工人协会 (ILA) / 美国海运联盟 (USMX) / 全国劳工关系委员会 (NLRB)",
        "official_domains": ["ilaunion.org", "usmx.com", "nlrb.gov", "fmcs.gov"],
        "recommended_query": 'site:ilaunion.org "Master Contract" OR "Statement" "{entity}" OR "strike"',
        "document_type": "工会官方联合谈判声明 / 劳资调解协议文本 (Tentative Agreement) / 罢工正式通告",
        "archive_folder": "data_sources/official_filings/labor",
    },
    "Antitrust_Litigation": {
        "authority": "美国国际贸易委员会 (USITC) / 美国司法部反垄断局 (DOJ) / 联邦贸易委员会 (FTC)",
        "official_domains": ["usitc.gov", "justice.gov", "ftc.gov"],
        "recommended_query": 'site:usitc.gov "337-TA-" "{entity}" OR "Limited Exclusion Order"',
        "document_type": "USITC 337 调查正式立案公报 (Notice of Institution) / 行政法官终裁裁决 (ID)",
        "archive_folder": "data_sources/official_filings/antitrust",
    },
    "Commodity_Physical_Squeeze": {
        "authority": "美国能源部化石能源与碳管理办公室 (DOE) / 伦敦金属交易所 (LME) 官方交割公报",
        "official_domains": ["energy.gov", "lme.com", "cme.com"],
        "recommended_query": 'site:energy.gov "Strategic Petroleum Reserve" "Solicitation" OR "Notice of Sale"',
        "document_type": "DOE 战略石油储备招标标书与中标结果 / LME 仓单交割官方日报 (Warehouse Stocks)",
        "archive_folder": "data_sources/official_filings/commodities",
    },
    "CentralBank_Liquidity_FX_Shock": {
        "authority": "日本央行 (Bank of Japan) / 纽约联储市场操作台 (NY Fed) / 国际清算银行 (BIS)",
        "official_domains": ["boj.or.jp", "newyorkfed.org", "federalreserve.gov"],
        "recommended_query": 'site:boj.or.jp "Monetary Policy Statement" OR "Market Operations" "Outright Purchases"',
        "document_type": "日本央行金融政策决策声明 / 隔夜贴现窗口与常备便利官方操作统计表",
        "archive_folder": "data_sources/official_filings/central_banks",
    },
    "Energy_Grid_Blackout_Rationing": {
        "authority": "美国能源信息署 (EIA) / 北美电力可靠性公司 (NERC) / 德州电力可靠性委员会 (ERCOT) / 德国联邦水文局 (BfG)",
        "official_domains": ["eia.gov", "nerc.com", "ercot.com", "bafg.de"],
        "recommended_query": 'site:eia.gov "Grid Monitor" OR site:nerc.com "Level 3 Emergency" "{entity}"',
        "document_type": "EIA 电网小时级负荷与削减监控报告 / NERC 电网可靠性紧急公报 / Kaub 驳船吃水标尺通报",
        "archive_folder": "data_sources/official_filings/energy_grid",
    },
    "Cyber_Critical_Infrastructure": {
        "authority": "美国网络安全与基础设施安全局 (CISA) / 各行业计算机应急响应组 (CERT) / 联邦储备银行清算台",
        "official_domains": ["cisa.gov", "cert.org", "federalreserve.gov"],
        "recommended_query": 'site:cisa.gov "Emergency Directive" OR "ICS Advisory" "{entity}"',
        "document_type": "CISA 工业控制系统应急指令 (Emergency Directive / ICS Advisory) / 清算网络日内运行通报",
        "archive_folder": "data_sources/official_filings/cyber",
    },
    "Biosecurity_Export_Embargo": {
        "authority": "美国国会法案审议跟踪台 (Congress.gov) / 美国食品药品监督管理局 (FDA) 进出口合规司",
        "official_domains": ["congress.gov", "fda.gov", "commerce.gov"],
        "recommended_query": 'site:congress.gov "Biosecure Act" OR site:fda.gov "Import Alert" "{entity}"',
        "document_type": "国会法案正式审议卷号 (Roll Call Vote) / FDA 进口警报红名单 (Import Alert 66-40 等)",
        "archive_folder": "data_sources/official_filings/biosecurity",
    },
    "Critical_Minerals_Export_Permit": {
        "authority": "商务部海关总署进出口管委会 / 印尼能矿部 (ESDM) / 美国地质调查局 (USGS)",
        "official_domains": ["mofcom.gov.cn", "customs.gov.cn", "esdm.go.id", "usgs.gov"],
        "recommended_query": 'site:customs.gov.cn "两用物项" OR site:esdm.go.id "RKAB" "{entity}"',
        "document_type": "海关两用物项出口许可证公告 / 印尼 RKAB 采矿配额批准令 / USGS 关键矿产库存分析",
        "archive_folder": "data_sources/official_filings/minerals",
    },
    "Defense_Procurement_Authorization": {
        "authority": "美国国防部 (DoD) / 国防安全合作局 (DSCA) / 国会武装力量委员会",
        "official_domains": ["defense.gov", "dsca.mil", "armedservices.senate.gov"],
        "recommended_query": 'site:defense.gov "Contracts" "{entity}" OR site:dsca.mil "Major Arms Sales"',
        "document_type": "五角大楼大额合同正式公告 (Contracts Announcement) / DSCA 对外军售国会通报",
        "archive_folder": "data_sources/official_filings/defense",
    },
    "Climate_Catastrophe_Insurance": {
        "authority": "美国国家飓风中心 (NHC/NOAA) / 沿海石化基地 / 联邦紧急事务管理局 (FEMA)",
        "official_domains": ["nhc.noaa.gov", "noaa.gov", "sec.gov", "fema.gov"],
        "recommended_query": 'site:nhc.noaa.gov "Advisory" OR site:sec.gov "Item 8.01" "hurricane" "{entity}"',
        "document_type": "NOAA 正式风暴预警通报 / 上市公司受损停产 8-K 披露 / 巨灾再保险损失评估报告",
        "archive_folder": "data_sources/official_filings/climate",
    },
    "Maritime_Insurance_Sanctions": {
        "authority": "国际保赔协会集团 (IG P&I) / 联合战争委员会 (JWC) / 美国财政部外国资产控制办公室 (OFAC)",
        "official_domains": ["igpandi.org", "lmalloyds.com", "treasury.gov/ofac"],
        "recommended_query": 'site:igpandi.org "Circular" OR site:treasury.gov "Price Cap" "{entity}"',
        "document_type": "保赔协会战争险与合规通函 (Circular) / OFAC 制裁扣押特别警报",
        "archive_folder": "data_sources/official_filings/maritime_sanctions",
    },
    "Sovereign_Debt_Liquidity": {
        "authority": "美国财政部债务管理办公室 (US Treasury) / 纽约联储公开市场操作台 (NY Fed) / 评级机构",
        "official_domains": ["treasury.gov", "newyorkfed.org", "fitchratings.com", "moodys.com"],
        "recommended_query": 'site:treasury.gov "Quarterly Refunding" OR "Debt Limit" "{entity}"',
        "document_type": "财政部季度再融资报告 (QRA) / 债务上限非常规措施通告 / 国债拍卖分配表",
        "archive_folder": "data_sources/official_filings/sovereign_debt",
    },
    "Other_Macro_Event": {
        "authority": "相关主权监管与权威政府信息公开网站",
        "official_domains": ["govinfo.gov", "sec.gov"],
        "recommended_query": 'site:govinfo.gov "{title}"',
        "document_type": "法定政府公报 / 行政通告",
        "archive_folder": "data_sources/official_filings/macro",
    },
}


def generate_radar_browser_checklist(
    db_path: str = "data/ledger/event_radar.sqlite3",
    output_path: str = "reports/radar_browser_checklist.md",
) -> str:
    """扫描事件数据库并生成买方标准 AI 浏览器补数与查验任务清单."""
    db_file = Path(db_path)
    if not db_file.exists():
        raise FileNotFoundError(f"未找到事件雷达数据库: {db_path}，请先执行种子生成脚本。")

    with sqlite3.connect(db_file) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # 筛选条件：P0/P1 重大事件、待核实传闻 (Unverified_Rumor) 或 非官方监管信源
        cursor.execute("""
            SELECT * FROM radar_events
            WHERE severity_level IN ('P0', 'P1')
               OR verification_status = 'Unverified_Rumor'
               OR credibility_tier IN ('Tier3_Mainstream_Wire', 'Tier4_Public_Flash_Social')
            ORDER BY
                CASE severity_level WHEN 'P0' THEN 1 WHEN 'P1' THEN 2 ELSE 3 END,
                published_at DESC
        """)
        rows = [dict(r) for r in cursor.fetchall()]

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines: List[str] = [
        "# 突发事件雷达 · AI 浏览器定向补数与法定信源核验任务清单",
        "",
        f"> **生成时间戳**：`{now_utc}`  ",
        "> **合规依据**：严格遵循《2026-10-11 最新数据来源策略》——不调私有收费接口，由 AI 浏览器进入官方监管/交易所/当事方页面核实原文。  ",
        f"> **待核查高优先事件总量**：**{len(rows)}** 项重大/待核实事实条目  ",
        "",
        "---",
        "",
        "## 一、 补数与鉴真作业守则 (SOP Guidelines)",
        "",
        "1. **原始事实原则**：搜索摘要与新闻二手转述不得充当投研底账；必须下载官方 PDF/HTML 原文至本地二级归档目录；",
        "2. **信源提级逻辑**：经 AI 浏览器获取官方监管公报并平账验证后，系统信源权威度提升至 `Tier1_Official_Regulatory` (权重 1.0)，状态由 `Unverified_Rumor` 提升为 `Confirmed_Fact`；",
        "3. **隔离与安全边界**：仅下载本次搜索明确指定的官方文件；严禁扫描用户下载目录的无关个人隐私文件；",
        "",
        "---",
        "",
        "## 二、 16 大全景维度定向核查任务明细表",
        "",
    ]

    for idx, item in enumerate(rows, 1):
        cat = item["category"]
        routing = PORTAL_ROUTING_MAP.get(cat, PORTAL_ROUTING_MAP["Other_Macro_Event"])
        entities = json.loads(item["involved_entities"]) if item["involved_entities"] else []
        main_entity = entities[0] if entities else "相关主体"
        query_text = routing["recommended_query"].format(entity=main_entity, title=item["title"][:20])

        status_badge = "🔴 待核实传闻 (熔断中)" if item["verification_status"] == "Unverified_Rumor" else "🟢 待补法定公报"
        sev_badge = f"**{item['severity_level']}**"

        lines.extend([
            f"### 任务 {idx:02d}：[{item['event_id']}] {item['title'][:48]}...",
            "",
            f"- **所属维度**：`{cat}` | **烈度等级**：{sev_badge} | **核验状态**：{status_badge}",
            f"- **当前信源**：`{item['source_name']}` ({item.get('credibility_tier', '未知')})",
            f"- **微观物理影响**：{item['micro_physical_impact']}",
            f"- **核查目标机构**：{routing['authority']}",
            f"- **官方权威域名**：`{', '.join(routing['official_domains'])}`",
            f"- **建议浏览器精准检索式**：",
            f"  ```text",
            f"  {query_text}",
            f"  ```",
            f"- **待采信官方文件类型**：{routing['document_type']}",
            f"- **本地推荐归档路径**：`{routing['archive_folder']}/{item['event_id']}_official_filing.pdf`",
            "",
            "---",
            "",
        ])

    lines.extend([
        "## 三、 补数结果闭环反馈机制",
        "",
        "当完成官方文件下载归档后，可执行以下命令完成信源升格与验签入库：",
        "```bash",
        "# 执行雷达账本信源提级与状态更新",
        "python scripts/confirm_event_verification.py --event-id <EVT_ID> --evidence-path <LOCAL_PATH>",
        "```",
        "",
        "_注：本任务清单由系统静态分析与账本扫描自动生成，符合项目单一事实来源 (SSOT) 规范。_",
    ])

    report_content = "\n".join(lines)
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(report_content, encoding="utf-8")
    print(f"Checklist generated successfully: {output_path} (Total tasks: {len(rows)})")
    return str(out_file)


if __name__ == "__main__":
    generate_radar_browser_checklist()
