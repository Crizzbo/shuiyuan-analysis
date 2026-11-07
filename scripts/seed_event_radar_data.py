"""事件雷达真实样本种子数据生成脚本 (Seed Event Radar Historical Data).

本脚本在 data/ledger/event_radar.sqlite3 中生成拟真买方实战的事件雷达与定时巡检记录：
涵盖台湾蓝营政局动向、美各州行业法案（加州电网负荷费、德州晶圆补贴）、化工厂爆炸物理破坏及供应链瓶颈等，
为仪表盘与后续第二阶段业务分部图谱穿透提供标准化基底。
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 将项目根目录添加至模块搜索路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from financial_core.engines.event_radar_engine import (
    EventRadarEngine,
    EventCategory,
    RawNewsItem,
    StructuredEventSummary,
)
from finance_tools.event_radar_collector import (
    RadarDatabaseManager,
    RadarProgressManager,
)


def seed_event_radar_database(db_path: str = "data/ledger/event_radar.sqlite3"):
    db_mgr = RadarDatabaseManager(db_path=db_path)
    now = datetime.now(timezone.utc)

    # 1. 拟真事件样本集合
    seed_news = [
        {
            "id": "SEED_GEO_001",
            "title": "海峡地缘动态：蓝营立院党团提案推动两岸半导体关键原料通关便利化与技术交流新框架",
            "content": "台北消息，立法院国民党党团今日正式领衔提出针对半导体及先进电子特种化学品通关的便利化框架案，旨在稳定台积电与两岸成熟制程封测厂之间的原料供应链与技术人员往来。法案引发多方博弈与关注。",
            "source": "Central_News_Agency",
            "published_at": (now - timedelta(minutes=25)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "category": EventCategory.GEOPOLITICAL.value,
            "involved_entities": ["蓝营党团", "台积电供应链", "海峡两岸成熟制程封测厂"],
            "micro_physical_impact": "推动两岸特种电子化学品通关审查时间缩短40%，稳定成熟制程特种原料跨海峡流转",
            "estimated_duration": "中期政策博弈(6-12个月)",
            "affected_business_segments": ["半导体封测代工", "电子级基础化学品", "成熟晶圆代工"],
            "severity_level": "P0",
            "requires_deep_analysis": True,
        },
        {
            "id": "SEED_POL_002",
            "title": "加州公用事业委员会(CPUC)表决通过新规：对50MW以上超大规模AI算力中心加征电网峰值负荷附加费",
            "content": "加州萨克拉门托消息，CPUC今日以4比1投票通过《2026商业重负荷电网支持法案》。根据新规，所有在加州电网接入超过50兆瓦的商业数据中心将按月每兆瓦额外加征3.2万美元的电网扩容与清洁能源平衡费，预计立即抬高大型云厂商北美电力OPEX。",
            "source": "California_Regulatory_Gazette",
            "published_at": (now - timedelta(minutes=55)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "category": EventCategory.STATE_POLICY.value,
            "involved_entities": ["加州公用事业委员会(CPUC)", "超大规模算力中心", "加州独立电网(CAISO)"],
            "micro_physical_impact": "单机柜等效电费增加8.5%，对加州硅谷及南加存量50MW+算力中心每月产生数百万美元新增负荷费",
            "estimated_duration": "法定长期生效(3年以上)",
            "affected_business_segments": ["云基础设施(IaaS)", "生成式AI算力集群", "商业公用事业电力"],
            "severity_level": "P1",
            "requires_deep_analysis": True,
        },
        {
            "id": "SEED_PHY_003",
            "title": "突发事故：鹿特丹港区核心特种单体与光刻胶前驱体树脂化工厂发生火灾爆炸并紧急全线停产",
            "content": "荷兰鹿特丹港消息，全球少数能够量产极紫外(EUV)/深紫外(DUV)光刻胶关键交联剂与特种酚醛树脂的化学品生产车间突发爆炸并燃起大火，应急管理部门已要求周边两公里人员疏散。厂方确认关键精馏塔严重受损，预计至少停产抢修16周。",
            "source": "Reuters_Global_Industrial",
            "published_at": (now - timedelta(minutes=90)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "category": EventCategory.PHYSICAL_DISRUPTION.value,
            "involved_entities": ["鹿特丹特种树脂化工厂", "全球半导体光刻胶供应链", "ASML生态伙伴"],
            "micro_physical_impact": "全球EUV光刻胶专用核心前驱体单体供应骤降35%，现存晶圆厂库存天数仅剩约45天",
            "estimated_duration": "中长期严重受阻(16周以上)",
            "affected_business_segments": ["先进制程晶圆制造", "电子化学品材料", "半导体代工"],
            "severity_level": "P1",
            "requires_deep_analysis": True,
        },
        {
            "id": "SEED_POL_004",
            "title": "德州州长签署通过第312章工业再投资法案修正案：针对先进半导体晶圆制造提供45亿美元超额水资源与基建税收减免",
            "content": "德克萨斯州奥斯汀消息，德州正式批准一揽子针对新建先进封装与晶圆制造基地的高性能水循环再利用与当地物业税减免细则。凡2027年前在德州破土动工的半导体前道晶圆项目，可享受前五年最高70%的地方税收折抵。",
            "source": "Texas_Tribune_Biz",
            "published_at": (now - timedelta(hours=2, minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "category": EventCategory.STATE_POLICY.value,
            "involved_entities": ["德克萨斯州经济发展局", "三星泰勒工厂", "德州仪器", "美光科技"],
            "micro_physical_impact": "降低德州新建晶圆厂前道初期固定资产投资资本开支折旧压力约12%，加速代工基地转产",
            "estimated_duration": "十年期州级法案",
            "affected_business_segments": ["半导体晶圆制造", "工业水处理基建", "高科技厂房工程"],
            "severity_level": "P1",
            "requires_deep_analysis": True,
        },
        {
            "id": "SEED_SUP_005",
            "title": "曼德海峡与红海南部关键航道突发商船避险改道：三艘超大型集装箱船遭遇无人机袭扰并暂停通行",
            "content": "亚丁湾消息，英国海事贸易行动办公室(UKMTO)通报，红海南部海域突发多轮无人机与快艇接近事件。全球前三大集装箱航运巨头宣布临时叫停苏伊士运河通行，全线绕行好望角，亚欧海运航程延长10-14天，现货运费指数盘中异动跳涨。",
            "source": "Lloyds_List_Maritime",
            "published_at": (now - timedelta(hours=3, minutes=40)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "category": EventCategory.SUPPLY_CHAIN_CHOKEPOINT.value,
            "involved_entities": ["UKMTO", "红海航运走廊", "马士基/地中海航运", "苏伊士运河管理局"],
            "micro_physical_impact": "亚欧航线集装箱周转效率下降15%，欧洲港口到港时间推迟2周，推高燃油附加费与运费基准",
            "estimated_duration": "阶段性航道封锁(3-6周)",
            "affected_business_segments": ["远洋集装箱海运", "欧洲零售与汽车零部件进口", "船用重油燃料"],
            "severity_level": "P1",
            "requires_deep_analysis": True,
        },
        {
            "id": "SEED_LAB_006",
            "title": "美东港口危机：国际码头工人协会(ILA)劳资谈判破裂，大西洋与墨西哥湾全线港口启动大罢工",
            "content": "新泽西与休斯敦消息，美东45,000名码头工人自今日零点起全面停止集装箱装卸作业，数十个关键海运集装箱码头彻底瘫痪。全美零售与汽车供应链警告，罢工每持续一周将导致物流滞港消化周期延长四周以上。",
            "source": "Journal_of_Commerce",
            "published_at": (now - timedelta(hours=4, minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "category": EventCategory.LABOR_STRIKES.value,
            "involved_entities": ["国际码头工人协会(ILA)", "美国海运联盟(USMX)", "美东各大枢纽港"],
            "micro_physical_impact": "美东海运集装箱装卸吞吐量归零，跨大西洋航线平均滞港周转天数跳涨12-18天",
            "estimated_duration": "高强度对峙(1-3周)",
            "affected_business_segments": ["海运港口装卸", "跨国集装箱物流", "零售与汽车供应链库存"],
            "severity_level": "P1",
            "requires_deep_analysis": True,
        },
        {
            "id": "SEED_AT_007",
            "title": "美国国际贸易委员会(ITC)正式对关键先进制程封装专利立案启动337调查并动议有限排除令(LEO)",
            "content": "华盛顿消息，美国ITC今日正式公告，就某跨国专利巨头针对2.5D/3D先进晶圆异构集成封装技术提出的侵权申诉立案启动337调查。申诉方请求对涉案相关核心高端算力芯片及下游整机发布有限排除令与禁止令。",
            "source": "USITC_Official_Gazette",
            "published_at": (now - timedelta(hours=4, minutes=50)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "category": EventCategory.ANTITRUST_LITIGATION.value,
            "involved_entities": ["美国国际贸易委员会(ITC)", "先进芯片设计原厂", "晶圆代工巨头"],
            "micro_physical_impact": "进入为期12-16个月的337法律调查程序，若裁定有限排除令将阻断涉及侵权架构芯片的美国海关清关",
            "estimated_duration": "法定司法审查期(12-16个月)",
            "affected_business_segments": ["先进封装与高端芯片架构", "跨国芯片分销与进口"],
            "severity_level": "P1",
            "requires_deep_analysis": True,
        },
        {
            "id": "SEED_COM_008",
            "title": "大宗商品逼仓异动：LME关键精炼金属现货升水急剧拉大，现货期限结构呈现极端倒挂(Backwardation)",
            "content": "伦敦消息，伦敦金属交易所(LME)注册交割仓单注销率单日暴增38%，可交割现货库存降至历史极限低位。近月合约较远期贴水转为深度现货升水每吨高达180美元，现货物理交割挤兑逼仓风险骤增，推高下游精密制造原材料即期采购成本。",
            "source": "LME_Market_Flash",
            "published_at": (now - timedelta(hours=5, minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "category": EventCategory.COMMODITY_SQUEEZE.value,
            "involved_entities": ["伦敦金属交易所(LME)", "实物大宗贸易巨头", "精密合金冶炼厂"],
            "micro_physical_impact": "现货升水倒挂每吨跳涨180美元，关键精炼金属即期物理现货提货周期延长并溢价走高",
            "estimated_duration": "流动性逼仓博弈(2-6周)",
            "affected_business_segments": ["上游特种金属冶炼", "高端电子精密合金", "工业原料库存管理"],
            "severity_level": "P1",
            "requires_deep_analysis": True,
        },
        {
            "id": "SEED_LIQ_009",
            "title": "全球宏观外汇异动：日元无预警剧烈升值突破关键技术关口，跨国套息交易(Carry Trade)遭遇连锁平仓挤压",
            "content": "东京与纽约外汇交易台消息，日本央行鹰派信号推动日元汇率盘中跳升超2.5%，直接引爆全球高杠杆跨资产套息交易的强制平仓潮。多只宏观对冲基金被迫抛售流动性资产以回补日元拆借负债，离岸美元隔夜融资利差出现短暂走阔。",
            "source": "Global_Macro_Liquidity_Wire",
            "published_at": (now - timedelta(hours=6, minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "category": EventCategory.CENTRAL_BANK_LIQUIDITY.value,
            "involved_entities": ["日本央行(BoJ)", "跨国宏观量化基金", "离岸美元流动性市场"],
            "micro_physical_impact": "高杠杆套息资金链短期快速撤出风险资产，推升跨资产波动率(VIX)并在短期冲击成长板块估值溢价",
            "estimated_duration": "流动性平仓冲击(1-2周)",
            "affected_business_segments": ["跨国金融机构自营交易", "高贝塔成长型权益资产", "外汇套期保值对冲"],
            "severity_level": "P0",
            "requires_deep_analysis": True,
        },
        {
            "id": "SEED_MIN_010",
            "title": "全球主要港口常规年度环保清淤工程计划按例公示",
            "content": "休斯敦港航运局发布2027财年第一季度航道疏浚与环境评估例行通告，通告属于年度计划例行公报，不涉及额外港口停航或关税变动。",
            "source": "Maritime_Port_Notice",
            "published_at": (now - timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "category": EventCategory.OTHER_MACRO.value,
            "involved_entities": ["休斯敦港航运局"],
            "micro_physical_impact": "日常例行工程公报，无实质商业与物理运输影响",
            "estimated_duration": "常规通告",
            "affected_business_segments": ["通用航运"],
            "severity_level": "P3",
            "requires_deep_analysis": False,
        },
        {
            "id": "SEED_RUMOR_011",
            "title": "网络快讯传闻：据社交平台传闻某晶圆先进制程厂突发紧急疏散并停工检修",
            "content": "未经证实的网络快讯称某地晶圆代工重镇厂区突发疏散警报，引发个别社群热议。官方与主流财经通讯社目前均未作任何确认，疑似虚假炒作谣言。",
            "source": "X_Social_Rumor_Flash",
            "published_at": (now - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "category": EventCategory.PHYSICAL_DISRUPTION.value,
            "involved_entities": ["某代工晶圆厂", "社交网络论坛"],
            "micro_physical_impact": "网络未经核实小道传闻，未见官方出险公报，已触发传闻熔断门禁",
            "estimated_duration": "待官方辟谣(数小时)",
            "affected_business_segments": ["先进制程晶圆代工"],
            "severity_level": "P2",
            "requires_deep_analysis": False,
        },
    ]

    engine = EventRadarEngine()

    for item in seed_news:
        raw = RawNewsItem(
            id=item["id"],
            title=item["title"],
            content=item["content"],
            source=item["source"],
            published_at=item["published_at"],
        )
        # 统一由引擎判定信源分级权威度与传闻熔断
        cred_tier, cred_score = engine.evaluate_source_credibility(item["source"])
        if cred_tier.value.startswith("Tier1"):
            v_status = "Confirmed_Fact"
            v_note = "官方监管机构或法定政府公报权威发布"
        elif cred_tier.value.startswith("Tier2"):
            v_status = "Confirmed_Fact"
            v_note = "上市公司IR或行业官方公报确认"
        elif cred_tier.value.startswith("Tier3"):
            v_status = "Corroborated_Report"
            v_note = "主流财经通讯社一线现场采信"
        else:
            v_status = "Unverified_Rumor"
            v_note = "社交媒体传闻/未获独立信源核实，已触发下游深研熔断门禁"

        requires_deep = item["requires_deep_analysis"]
        if v_status == "Unverified_Rumor":
            requires_deep = False

        summary = StructuredEventSummary(
            event_id=f"EVT_{raw.raw_hash[:12].upper()}",
            timestamp=item["published_at"],
            category=item["category"],
            involved_entities=item["involved_entities"],
            micro_physical_impact=item["micro_physical_impact"],
            estimated_duration=item["estimated_duration"],
            affected_business_segments=item["affected_business_segments"],
            severity_level=item["severity_level"],
            requires_deep_analysis=requires_deep,
            raw_title=item["title"],
            source_name=item["source"],
            credibility_tier=cred_tier.value,
            credibility_score=cred_score,
            verification_status=v_status,
            verification_note=v_note,
        )
        collected_at = (datetime.fromisoformat(item["published_at"].replace("Z", "+00:00")) + timedelta(seconds=12)).isoformat()
        db_mgr.insert_event(summary, raw, collected_at)

    # 2. 拟真巡检轮次数据 (涵盖 美股盘前、盘中、盘后各时段)
    cycles_data = [
        {
            "timestamp": (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "market_session": "pre_market",
            "status": "SUCCESS",
            "active_probe_node": "Google_Public_DNS (8.8.8.8:53)",
            "probe_latency_ms": 1.15,
            "scanned_count": 48,
            "filtered_in_count": 3,
            "summarized_count": 3,
            "p0_p1_triggered_count": 1,
            "estimated_tokens_consumed": 330,
        },
        {
            "timestamp": (now - timedelta(minutes=35)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "market_session": "pre_market",
            "status": "SUCCESS",
            "active_probe_node": "Cloudflare_DNS (1.1.1.1:53)",
            "probe_latency_ms": 1.28,
            "scanned_count": 52,
            "filtered_in_count": 4,
            "summarized_count": 4,
            "p0_p1_triggered_count": 1,
            "estimated_tokens_consumed": 440,
        },
        {
            "timestamp": (now - timedelta(hours=1, minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "market_session": "pre_market",
            "status": "SUCCESS",
            "active_probe_node": "Google_Public_DNS (8.8.8.8:53)",
            "probe_latency_ms": 1.09,
            "scanned_count": 65,
            "filtered_in_count": 6,
            "summarized_count": 6,
            "p0_p1_triggered_count": 2,
            "estimated_tokens_consumed": 660,
        },
        {
            "timestamp": (now - timedelta(hours=2, minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "market_session": "regular_market",
            "status": "SUCCESS",
            "active_probe_node": "Google_Public_DNS (8.8.8.8:53)",
            "probe_latency_ms": 1.42,
            "scanned_count": 82,
            "filtered_in_count": 5,
            "summarized_count": 5,
            "p0_p1_triggered_count": 1,
            "estimated_tokens_consumed": 550,
        },
        {
            "timestamp": (now - timedelta(hours=3, minutes=50)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "market_session": "regular_market",
            "status": "SUCCESS",
            "active_probe_node": "Cloudflare_DNS (1.1.1.1:53)",
            "probe_latency_ms": 1.35,
            "scanned_count": 76,
            "filtered_in_count": 7,
            "summarized_count": 7,
            "p0_p1_triggered_count": 1,
            "estimated_tokens_consumed": 770,
        },
        {
            "timestamp": (now - timedelta(hours=5, minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "market_session": "after_hours",
            "status": "SUCCESS",
            "active_probe_node": "Google_Public_DNS (8.8.8.8:53)",
            "probe_latency_ms": 1.21,
            "scanned_count": 41,
            "filtered_in_count": 2,
            "summarized_count": 2,
            "p0_p1_triggered_count": 0,
            "estimated_tokens_consumed": 220,
        },
        {
            "timestamp": (now - timedelta(hours=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "market_session": "market_closed",
            "status": "SUCCESS",
            "active_probe_node": "Google_Public_DNS (8.8.8.8:53)",
            "probe_latency_ms": 1.18,
            "scanned_count": 35,
            "filtered_in_count": 1,
            "summarized_count": 1,
            "p0_p1_triggered_count": 0,
            "estimated_tokens_consumed": 110,
        },
    ]

    for cycle in cycles_data:
        db_mgr.insert_cycle(cycle)

    stats = db_mgr.query_summary_statistics()
    print("Database seeding completed successfully!")
    print(f"Total events in SQLite: {stats['total_events_stored']}")
    print(f"Total P0/P1 major triggers: {stats['total_major_p0_p1']}")
    print(f"Total cycles recorded: {stats['total_cycles_executed']}")
    print(f"Total news scanned: {stats['total_scanned_news']}")
    print(f"Total tokens burned: {stats['total_tokens_burned']}")


if __name__ == "__main__":
    seed_event_radar_database()
