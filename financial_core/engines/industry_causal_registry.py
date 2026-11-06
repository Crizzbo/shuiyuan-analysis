"""41 细分行业买方专属因果推导策略注册中心 (Industry Causal Strategy Registry).

物理架构定界 (Layer 1: financial_core):
- 纯净底层架构，纯相对导入，零外层依赖;
- 针对 41 个行业投研契约，建立专属的买方量化因果策略路由;
- 克服传统通用模板千篇一律的痛点，精准结合行业特异性变量（如半导体先进制程良率/设备禁运、
  创新药双盲试验解盲/专利悬崖、白酒渠道批零倒挂/合同负债、银行净息差/拨备覆盖率、
  汽车价格战/锂电成本、SaaS软件留存率NDR/AI推理成本）产出高锐度的买方商业投资大白话事实清单;
- 严格遵循自然语言汇报规范：杜绝生硬数学符号与公式源码堆砌，杜绝 Emoji 表情符号。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from .industry_taxonomy_bridge import IndustryTaxonomyBridge, IndustryMappingRecord
from .industry_knowledge_manager import IndustryKnowledgeManager, IndustryKnowledgeProfile
from .knowledge_repository import KnowledgeRepository, IndustryRuleProfile


@dataclass
class IndustryCausalFacts:
    """行业特异性因果推导事实集合."""
    industry_id: str                      # 细分行业 ID
    industry_name_zh: str                 # 行业中文名
    industry_catalysts: List[str]         # 行业专属催化事实清单 (自然语言商业大白话)
    industry_risks: List[str]             # 行业专属警示事实清单 (自然语言商业大白话)
    leading_optimistic_trigger: str       # 行业主导乐观靶心触发路径
    leading_pessimistic_trigger: str      # 行业主导悲观底价防线触发路径
    valuation_route: str = ""             # 行业法定买方估值路线 (知识中枢驱动)
    counterevidence: str = ""             # 行业买方核心反证逻辑 (知识中枢驱动)


class IndustryCausalStrategyRegistry:
    """41 细分行业买方因果策略注册中心中枢."""

    def __init__(self):
        self.version = "1.0.0"
        self.taxonomy_bridge = IndustryTaxonomyBridge()
        self.knowledge_mgr = IndustryKnowledgeManager.get_instance()
        self.repo = KnowledgeRepository.get_instance()

    def evaluate_industry_causal_facts(
        self,
        industry_id: str,
        company_metrics: Dict[str, Any],
        forensic_findings: Dict[str, Any],
        macro_shock_data: Dict[str, Any],
    ) -> IndustryCausalFacts:
        """根据细分行业契约路由专属因果推导策略并合成买方事实清单."""
        rec = self.taxonomy_bridge.get_record(industry_id)
        ind_key = rec.industry_id
        prof = self.knowledge_mgr.get_profile(ind_key)

        catalysts: List[str] = []
        risks: List[str] = []

        # 提取微观常用变量
        dio = float(company_metrics.get("current_dio_days", 0.0))
        markup = float(company_metrics.get("micro_markup_ratio", rec.typical_markup_ratio))
        dtf = float(company_metrics.get("distance_to_technology_frontier", 1.0))
        top_cust_share = float(company_metrics.get("top_customer_share", 0.0))
        top_cust_risk = bool(company_metrics.get("top_customer_risk_flag", False))
        factory_quote = float(company_metrics.get("factory_quote", 0.0))
        wholesale_quote = float(company_metrics.get("real_wholesale_quote", 0.0))
        liab_drain = float(company_metrics.get("contract_liabilities_drain_pct", 0.0))
        runway_months = float(company_metrics.get("hard_runway_months", 999.0))
        revenue_growth = float(company_metrics.get("revenue_growth_pct", 0.0))

        # 动态知识库契约阈值
        dio_healthy = prof.dio_healthy_days if prof.dio_healthy_days > 0 else 60.0
        dio_warning = prof.dio_warning_days if prof.dio_warning_days > 0 else 120.0
        cust_redline_pct = prof.top_customer_concentration_redline * 100.0

        # =================================================================
        # 1. 前沿半导体、半导体设备与芯片硬件 (semiconductors, semi_equipment, hardware)
        # =================================================================
        if ind_key in ["semiconductors", "semi_equipment", "hardware"]:
            if dtf <= 0.15 or markup >= 1.25:
                catalysts.append(
                    f"【先进制程壁垒与技术领跑】紧贴全球半导体技术前沿（前沿距离仅 {dtf:.2f}，加价率 {markup:.2f}），"
                    f"在高端制程与 AI 算力芯片领域具备极高客户粘性，充分享受晶圆代工高产能利用率带来的规模效应红利。"
                )
            if dio > 0 and dio <= dio_healthy:
                catalysts.append(
                    f"【芯片库存水位处于健康良性区间】库存周转天数仅 {dio:.0f} 天（优于行业健康中枢 {dio_healthy:.0f} 天），"
                    f"未见渠道压库滞销包袱；下游服务器与终端换机需求一旦温和复苏，产能将快速转为高额经营现金流。"
                )
            if ind_key == "semi_equipment":
                catalysts.append(
                    "【晶圆厂扩产周期与设备在手订单饱满】先进制程与成熟特色制程双轮驱动，"
                    "刻蚀、薄膜沉积与量测检测核心设备交付顺畅，未交付在手订单为后续业绩提供高确定性能见度。"
                )
            elif ind_key == "hardware":
                catalysts.append(
                    "【高速算力互联与AI服务器硬件放量】800G/1.6T 高速光模块、AI 训练服务器与高密度配电硬件出货强劲，"
                    "云厂商大客户资本开支扩张直接拉动高附加值硬件毛利上行。"
                )

            if top_cust_share >= cust_redline_pct or top_cust_risk:
                risks.append(
                    f"【单一大客户依赖与供应链禁运脆弱性】前沿客户营收贡献达 {top_cust_share:.1f}%（触及行业集中度红线 {cust_redline_pct:.1f}%）；"
                    f"面临核心先进制程设备出口限制政策与客户自研替代双重敞口，供应链单点破裂风险显著。"
                )
            if dio >= dio_warning:
                risks.append(
                    f"【半导体去库存周期显著拉长】存货周转天数飙升至 {dio:.0f} 天（触及行业警戒线 {dio_warning:.0f} 天），"
                    f"显示下游终端提货迟缓；后续若芯片产品迭代加快，老代际晶圆将面临大额减值计提风险。"
                )

        # =================================================================
        # 2. 研发型生物科技、成熟制药与医疗器械 (biotech, pharma, medical_devices)
        # =================================================================
        elif ind_key in ["biotech", "pharma", "medical_devices"]:
            pipeline_val = float(company_metrics.get("pipeline_rnpv_value", 0.0))
            if pipeline_val > 0.0:
                catalysts.append(
                    f"【在研管线临床价值扎实】核心新药研发管线通过权威临床风险调整折现（在研价值估值超 {pipeline_val:,.0f} 单位），"
                    f"后续关键临床 II/III 期双盲试验解盲与 FDA 优先审评将构成强劲估值向上弹性催化剂。"
                )
            if runway_months >= 36.0 or (runway_months <= 0.0 and company_metrics.get("reported_operating_cash_flow", 0.0) > 0):
                catalysts.append(
                    "【研发资金池丰沛免除配股摊薄】不受限流动现金储备充盈或自身已实现经营性造血，"
                    "完全免除在二级市场低位折价定增增发对老股东权益造成的不可逆稀释。"
                )
            if ind_key == "medical_devices":
                catalysts.append(
                    "【高壁垒器械进院壁垒与耗材耗用黏性】高值医疗器械与体外诊断设备形成封闭式进院生态，"
                    "主机装机量稳步爬坡带动高毛利专用试剂与耗材持续消耗放量。"
                )

            if 0.0 < runway_months < 15.0:
                risks.append(
                    f"【现金跑道逼仄与临床失败归零风险】在研资金仅够支撑 {runway_months:.1f} 个月临床支出；"
                    f"创新药研发具备高试错与双盲试验不达标天然属性，迫近外部融资断粮与低位折价增发悬崖边缘。"
                )
            if ind_key == "pharma" and revenue_growth < -0.05:
                risks.append(
                    "【重磅核心药专利悬崖冲击】存量主力药品面临核心专利到期与低价仿制药准入冲击，"
                    "集采降价将导致传统基本盘营收中枢持续失血。"
                )
            if ind_key == "medical_devices":
                risks.append(
                    "【高值耗材带量集采价格重估】骨科、心血管等重点耗材品类面临带量集采大幅降价压力，"
                    "若不能凭借新一代差异化专利产品接续，出厂毛利率将面临结构性压缩。"
                )

        # =================================================================
        # 3. 医疗服务与管理式医疗 (health_services, managed_care)
        # =================================================================
        elif ind_key in ["health_services", "managed_care"]:
            if ind_key == "managed_care":
                catalysts.append(
                    "【管理式医疗控费网络与保费稳定沉淀】商业健康险与医疗服务网络深度协同，"
                    "精细化核保与医疗费用审查机制有效平抑赔付率波动，保费现金浮存金创造稳定投资收益。"
                )
                risks.append(
                    "【医疗赔付率超预期上升挤压承保利润】老年人与慢病人群择期就医需求反弹推升医疗服务赔付成本，"
                    "若联邦医疗保险补贴费率下调，综合承保毛利将遭遇双向挤压。"
                )
            else:  # health_services
                catalysts.append(
                    "【连锁专科医疗就诊量攀升与高毛利特需服务】核心专科医疗机构床位利用率与单床产出稳步改善，"
                    "高壁垒消费医疗与特需健康管理服务拓展支撑营收中枢稳健扩张。"
                )
                risks.append(
                    "【医保支付方式改革与医保基金垫资账期延长】DRGs/DIP 疾病诊断相关分组付费推行限制次均住院开支，"
                    "公立与商业医疗结算回款周期拉长推高应收账款周转天数与坏账敞口。"
                )

        # =================================================================
        # 4. 食品饮料、个人用品、必需零售与烟草 (food_beverage, household_personal, staples_retail, tobacco)
        # =================================================================
        elif ind_key in ["food_beverage", "household_personal", "staples_retail", "tobacco"]:
            if wholesale_quote > 0.0 and factory_quote > 0.0:
                if wholesale_quote >= factory_quote:
                    spread_pct = (wholesale_quote - factory_quote) / factory_quote * 100.0
                    catalysts.append(
                        f"【渠道批零顺价与品牌定价护城河】真实批发价高于出厂价（顺价差达 +{spread_pct:.1f}%），"
                        f"渠道商利润丰厚、回款顺畅，品牌具备跨越经济周期的刚性自发提价与控盘控价能力。"
                    )
                else:
                    spread_pct = (factory_quote - wholesale_quote) / factory_quote * 100.0
                    risks.append(
                        f"【渠道批价倒挂与经销商抛货危机】真实外场批发价低于标称出厂价（倒挂幅度 {spread_pct:.1f}%），"
                        f"渠道商利差倒挂导致甩货套现，厂家若强行压货将引发经销商大面积退网违约。"
                    )

            if liab_drain < -15.0:
                risks.append(
                    f"【合同负债蓄水池急剧干涸】预收账款单季环比净流出 {abs(liab_drain):.1f}%，"
                    f"下游经销商打款进货信心大幅消退，后续数个季度表观营收与现金流将丧失平滑缓冲垫。"
                )
            elif markup >= 1.25:
                catalysts.append(
                    f"【超高微观毛利与心智垄断】霍尔加价率达 {markup:.2f}，"
                    f"消费品牌心智根深蒂固，在原材料农产品或包装通胀周期具备全额顺价转嫁能力。"
                )

            if ind_key == "staples_retail":
                catalysts.append(
                    "【生鲜日用供应链直采与高坪效周转】核心生活物资直采比例提升，"
                    "会员制仓储与高频刚需业态构建强大客流吸引力，营运现金流周转天数保持极高流动性。"
                )
                risks.append(
                    "【即时零售平台分流与线下门店刚性租金】线上生鲜电商与社区团购对传统商超人流持续分流，"
                    "线下门店租金与人工成本刚性上涨压缩平效利润空间。"
                )
            elif ind_key == "tobacco":
                catalysts.append(
                    "【特许法定专营垄断与新型减害产品渗透】极高加价率与近乎零负债的超强自由现金流造血能力，"
                    "新型加热不燃烧烟草合规放量拓展全球增量市场空间。"
                )
                risks.append(
                    "【全球控烟健康法规收紧与消费税惩罚性上调】各国公共卫生政策持续提高烟草消费税与警示包装要求，"
                    "传统卷烟销量长周期自然下滑制约长期估值中枢。"
                )

        # =================================================================
        # 5. 商业银行、证券保险、资产管理与支付基础设施 (banks, insurance, asset_management, payments)
        # =================================================================
        elif ind_key in ["banks", "insurance", "asset_management", "payments"]:
            if ind_key == "banks":
                if markup >= 1.15:
                    catalysts.append(
                        "【负债端低成本活期存款与净息差韧性】拥有庞大零售存款低成本资金护城河，"
                        "在利率波动周期中具备稳固的生息资产收益率，净息差与非息收入结构保持优异。"
                    )
                catalysts.append(
                    "【拨备覆盖充足与信贷资产质量稳健】拨备覆盖率处于行业高位，具备抵御宏观信用周期的坚实安全垫。"
                )
                risks.append(
                    "【宏观信用下行与房地产化债信贷展期】宏观经济波动推高隐性不良贷款生成率，"
                    "存量贷款利率重定价持续压缩净息差空间。"
                )
            elif ind_key == "insurance":
                catalysts.append(
                    "【寿险新业务价值强劲复苏与长久期匹配】新单保费保质保量增长，"
                    "负债成本有效压降，投资端长久期国债与高股息资产资产负债期限匹配良好。"
                )
                risks.append(
                    "【长期低利率环境下的利差损敞口】长端国债利率低迷制约新配置固收资产收益率，"
                    "传统高预定利率保单面临长期利差损与综合偿付能力充足率压力。"
                )
            elif ind_key == "asset_management":
                catalysts.append(
                    "【资产管理规模逆市净流入与高费率另类业务】高净值财富管理与私募信贷、基础设施等另类投资规模扩张，"
                    "管理费收入具备极高客户粘性与抗波动特征。"
                )
                risks.append(
                    "【被动低费率指数化浪潮侵蚀主动管理费率】低成本 ETF 规模激增压低主动权益公募费率，"
                    "资本市场剧烈波动导致管理规模缩水与业绩报酬下滑。"
                )
            else:  # payments
                catalysts.append(
                    "【全球无现金化与跨境清算网络双边效应】总交易量 (TPV) 稳定增长，"
                    "商户与持卡人双边网络壁垒深厚，跨境高费率支付与企业增值软件服务提供强劲增长动力。"
                )
                risks.append(
                    "【刷卡手续费率监管封顶与新兴即时结算网络替代】反垄断监管对银行卡交换费率实施上限约束，"
                    "央行即时清算系统去中介化降低传统收单手续费收益。"
                )

        # =================================================================
        # 6. 汽车制造、智能装备与航空航天国防 (autos, capital_goods, aerospace_defense)
        # =================================================================
        elif ind_key in ["autos", "capital_goods", "aerospace_defense"]:
            if dio > 0 and dio <= dio_healthy:
                catalysts.append(
                    f"【精益供应链敏捷周转】库存周转天数仅 {dio:.0f} 天（优于行业健康中枢 {dio_healthy:.0f} 天），"
                    f"产销衔接平稳高效，上游核心零部件与动力电池价格回落直接转化为当期整车毛利率扩张空间。"
                )
            if markup >= 1.12:
                catalysts.append(
                    f"【产品溢价与出海高附加值放量】微观加价率达 {markup:.2f}，海外高毛利市场交付放量，"
                    f"带动单车/单机均价稳步攀升，有效对冲本土存量市场以价换量的内卷竞争。"
                )
            if ind_key == "aerospace_defense":
                catalysts.append(
                    "【国防军工确定性预算与民用大飞机交付提速】特种装备长周期采购订单提供极高能见度，"
                    "民用干线客机供应链瓶颈缓解带动高毛利售后航材维保需求全面释放。"
                )
                risks.append(
                    "【军工复杂型号研制周期长与供应链单点交付拖延】特种航空构件与关键发动机零部件交期拉长，"
                    "固定总价合同面临人工与特种原材料通胀成本超支风险。"
                )
            elif ind_key == "capital_goods":
                catalysts.append(
                    "【工业母机与高端自动化装备渗透】制造业数字化升级推动高精度机床与工业机器人需求，"
                    "设备出海业务与高毛利后市场备件服务收入占比持续提升。"
                )
                risks.append(
                    "【制造业资本开支周期性延后】全球工业品需求疲软导致下游工厂推迟产线技改投资，"
                    "重资产设备制造产能利用率不足反噬营业利润率。"
                )

            if dio >= dio_warning:
                risks.append(
                    f"【产成品积压与终端价格战降价】库房整机与配件周转周期高达 {dio:.0f} 天（触及行业警戒线 {dio_warning:.0f} 天）；"
                    f"行业价格战白热化背景下，库存贬值与终端促销折扣将严重吞噬企业营业利润率。"
                )

        # =================================================================
        # 7. 交通运输、海空物流、商业服务与建筑工程 (transport_logistics, business_services, construction)
        # =================================================================
        elif ind_key in ["transport_logistics", "business_services", "construction"]:
            if ind_key == "transport_logistics":
                catalysts.append(
                    "【主干航线运力紧平衡与智能物流枢纽降本】海空干线运力供需结构良好，"
                    "自动化分拣转运中心与智慧调度系统显著压低单票燃油与人工中转成本。"
                )
                risks.append(
                    "【全球贸易货量增速回落与燃油成本剧烈波动】国际地缘摩擦扰动主要海运走廊航运周转，"
                    "航空煤油与船用重油价格飙升无法及时通过燃油附加费全额传导。"
                )
            elif ind_key == "business_services":
                catalysts.append(
                    "【企业专业服务合规外包与高现金流轻资产运营】法律、财税咨询与人力外包需求刚性提升，"
                    "轻资产商业模式免除大额折旧包袱，自由现金流转化率处于全行业领先水准。"
                )
                risks.append(
                    "【企业削减非核心咨询预算与核心专业人才流失】经济下行期企业延长第三方专业服务招标审批，"
                    "核心团队变动或大客户流失直接造成合同履约中断风险。"
                )
            else:  # construction
                catalysts.append(
                    "【特种工业基建与绿色节能工程订单储备充足】重大能源基建与高科技产业园区工程总承包在手订单充沛，"
                    "专业化施工资质与 EPC 总包管理能力形成稳固竞争壁垒。"
                )
                risks.append(
                    "【工程垫资施工与业主方工程款结算拖欠坏账】下游业主资金链趋紧拉长工程进度款支付周期，"
                    "应收账款与合同资产大额减值计提对微薄的施工毛利率构成重大侵蚀。"
                )

        # =================================================================
        # 8. 零售电商、餐饮旅游与耐用消费品 (retail, restaurants, travel_leisure, housing_durables)
        # =================================================================
        elif ind_key in ["retail", "restaurants", "travel_leisure", "housing_durables"]:
            if ind_key == "retail":
                catalysts.append(
                    "【全渠道履约网络与自有品牌商品毛利扩张】线上线下无缝融合提升复购频次，"
                    "高毛利自营供应链与差异化大单品矩阵拉升综合毛利率水平。"
                )
                risks.append(
                    "【可选消费客单价走弱与获客成本居高不下】居民可选支出谨慎导致件单价承压，"
                    "线上平台买量转化效率下滑与线下核心商圈租金刚性挤压经营利润。"
                )
            elif ind_key == "restaurants":
                catalysts.append(
                    "【标准化中央厨房体系与单店模型快速回本】供应链集采保障食材成本优势，"
                    "单店模型标准化高、投资回收期短，同店销售额 (SSSG) 呈现良性内生复苏。"
                )
                risks.append(
                    "【商圈客流分化与食材人工店租三座大山】同质化餐饮竞品扎堆导致单店翻台率下滑，"
                    "一线员工薪资上涨与核心铺位租金刚性支出显著压制门店经营利润率。"
                )
            elif ind_key == "travel_leisure":
                catalysts.append(
                    "【跨境旅游商务出行强劲与轻资产酒店管理】高端度假与商旅综合需求景气，"
                    "特许经营加盟管理模式提升轻资产服务费变现比例，每间可售房收入 (RevPAR) 结构性走强。"
                )
                risks.append(
                    "【宏观可选旅游支出波动与固定资产折旧利息压力】直营重资产文旅设施与自持酒店面临沉重折旧摊销，"
                    "一旦突发宏观扰动导致入住率与客流量骤降，高固定杠杆将迅速吞噬微薄净利润。"
                )
            else:  # housing_durables
                catalysts.append(
                    "【以旧换新绿色节能更新与智能家居出海】高端智能白电与绿色节能厨电享受更新换代补贴红利，"
                    "自有品牌在拉美、东南亚及中东等新兴海外市场销售渗透加速。"
                )
                risks.append(
                    "【房地产新房竣工交付低迷与铜铝原料通胀】地产后周期家电安装采购新增需求疲软，"
                    "上游大宗工业原材料（铜管、铝材、塑胶）突发涨价削弱终端产品毛利空间。"
                )

        # =================================================================
        # 9. 企业级软件、云服务与 IT 咨询 (software, it_services)
        # =================================================================
        elif ind_key in ["software", "it_services"]:
            if markup >= 1.30:
                catalysts.append(
                    f"【高粘性订阅模式与超高毛利】霍尔加价率高达 {markup:.2f}，毛利率超 75% 且具备高净金额留存率；"
                    f"企业级软件嵌入客户核心工作流，替换成本极高，老客户持续扩容订阅构筑确定性现金流底座。"
                )
            catalysts.append(
                "【AI 赋能商业化提价弹性】云端企业级生产力工具深度整合大模型能力，"
                "推动合同未履约总价值 (RPO) 快速攀升，带动 ARPU 值与新签约规模双升。"
            )
            if ind_key == "it_services":
                catalysts.append(
                    "【企业数智化转型全栈部署与混合云运维服务】各行业核心系统向云原生及大模型私有化迁移，"
                    "端到端集成开发与长期系统托管运维合同带来持续可预测的递延收入。"
                )
                risks.append(
                    "【技术外包单价受压与高端交付工程师人力成本刚性】传统 IT 运维外包面临甲方降本控费砍价，"
                    "高技能人工智能与云架构师薪酬支出居高不下，挤压项目级综合净利润率。"
                )

            risks.append(
                "【大客户 IT 支出预算收紧审批拉长】宏观经济不确定性导致企业客户延长采购审批周期或精简软件授权席位，"
                "新单签约增速与净拓展率 (NDR) 面临承压回落隐患。"
            )
            risks.append(
                "【AI 算力基础设施与推理代工成本侵蚀】大规模模型部署推升云厂商计算与带宽开支，"
                "若商业化增值变现进度慢于算力采购投入，将对中枢毛利率造成阶段性结构性压制。"
            )

        # =================================================================
        # 10. 电信运营、互联网平台与数字文娱传媒 (telecom, digital_platforms, media_entertainment)
        # =================================================================
        elif ind_key in ["telecom", "digital_platforms", "media_entertainment"]:
            if ind_key == "telecom":
                catalysts.append(
                    "【5G网络资本开支达峰回落与高股息分红现金流】主干通信基建投资高峰过去，"
                    "自由现金流步入丰硕收获期，股息分红率常年处于高位，算网一体化政企专线业务稳步起量。"
                )
                risks.append(
                    "【移动通信用户渗透率见顶与数据中心高能耗电费支出】传统语音与流量 ARPU 增长停滞，"
                    "AI 超算中心与海量基站持续运行推高电力公用事业能源开销。"
                )
            elif ind_key == "digital_platforms":
                catalysts.append(
                    "【双边网络壁垒与广告算法商业化变现提升】庞大活跃用户生态形成天然数字护城河，"
                    "深度推荐算法赋能广告主转化率改善，电商履约闭环释放强劲的自由现金流。"
                )
                risks.append(
                    "【反垄断算法合规监管与线上流量大盘触顶】全球平台经济数据合规审查与应用商店分成博弈，"
                    "存量互联网用户在线时长见顶，新增买量拉新获客成本大幅抬升。"
                )
            else:  # media_entertainment
                catalysts.append(
                    "【长青核心 IP 跨媒介全球变现与重磅精品游戏上线】顶尖内容 IP 在影视、游戏、衍生品全链条变现能力卓越，"
                    "自研旗舰爆款大作首发流水超出预期，流媒体服务订阅规模稳步攀升。"
                )
                risks.append(
                    "【内容制作长周期高试错与爆款衰减断档风险】影视制作与大型游戏研制成本动辄上亿美元，"
                    "一旦上线口碑未达预期或买量转化率低迷，巨额前期资本化无形资产将面临一次性大额减值计提。"
                )

        # =================================================================
        # 11. 油气开采、油田服务与中游管输 (oil_gas, energy_services, midstream)
        # =================================================================
        elif ind_key in ["oil_gas", "energy_services", "midstream"]:
            if ind_key == "oil_gas":
                catalysts.append(
                    "【资源禀赋与低现金完全成本抗周期】优质主力油气田完全开采成本处于全球低位，"
                    "上游资本开支保持克制，充沛自由现金流优先支撑丰厚股息分红与股份注销回购。"
                )
                risks.append(
                    "【全球宏观工业需求转弱与大宗现货油价承压】主要经济体工业制造业降温削弱原油消费，"
                    "主要产油国供给配额政策调整可能引发国际原油现货价格深幅回调。"
                )
            elif ind_key == "energy_services":
                catalysts.append(
                    "【全球海上深水与非常规钻探资本开支复苏】海上自升式与半潜式钻井平台利用率高企，"
                    "高端测井与压裂技术服务日费率上调，海外长周期勘探服务订单交付景气。"
                )
                risks.append(
                    "【上游油气巨头突发削减钻探勘探预算】一旦原油现货跌破边际开采成本，"
                    "上游勘探开发企业迅速封井停钻，高固定设备折旧将引发油服企业利润断崖下跌。"
                )
            else:  # midstream
                catalysts.append(
                    "【长输管网照付不议长协费率锁定丰沛现金流】跨区域天然气与原油骨干管输设施签署长期服务协议，"
                    "不受短期商品价格暴跌波动的过路费商业模式，构筑稳健高股息防御资产。"
                )
                risks.append(
                    "【环保新管线审批收紧与存量管网监管核定降价】新建能源输送走廊面临严苛环境影响评价限制，"
                    "监管机构阶段性下调准许资产报酬率可能压缩管输单价收益。"
                )

        # =================================================================
        # 12. 矿产采掘、精细化工与绿色包装林纸 (mining, chemicals, packaging)
        # =================================================================
        elif ind_key in ["mining", "chemicals", "packaging"]:
            if ind_key == "mining":
                catalysts.append(
                    "【战略关键矿产长期供需缺口与低成本开采】顶级矿山资源品位优良，全维持成本 (AISC) 极具竞争力，"
                    "全球电气化与算力基建对铜、金等关键金属的长期刚性需求提供强劲价格支撑。"
                )
                risks.append(
                    "【矿山品位自然衰退与东道国矿业特许权税负提升】老旧矿区开采剥离比加大抬高单位矿石提炼成本，"
                    "资源所在国上调矿区土地税与暴利税压缩矿企自由现金流留存。"
                )
            elif ind_key == "chemicals":
                catalysts.append(
                    "【高端电子化学品与特种材料高附加值放量】半导体级高纯试剂、新能源特种聚合物实现技术破局，"
                    "上游基础原料油气价差适度扩大，一体化全产业链装置显著降低单吨综合制造成本。"
                )
                risks.append(
                    "【基础通用大宗化学品产能集中释放引发价格踩踏】传统聚烯烃与精细中间体行业新增产能密集投产，"
                    "同质化以价换量竞争打压产品出厂价，高能耗环保合规整改加重经营负担。"
                )
            else:  # packaging
                catalysts.append(
                    "【环保可降解包材替代与大客户直供长期协议】快消巨头与医药大健康客户长期包装框架协议保障开工率，"
                    "高强轻量化瓦楞纸箱与环保可循环缓冲材料渗透率持续提升。"
                )
                risks.append(
                    "【原材料木浆与废纸采购价格突发暴涨】上游制浆林木资源供应紧缩推升原浆采购成本，"
                    "对下游大型消费品客户议价转嫁存在时滞，直接侵蚀当期毛利率水平。"
                )

        # =================================================================
        # 13. 电网公用事业与市场化绿色发电 (regulated_utilities, merchant_power)
        # =================================================================
        elif ind_key in ["regulated_utilities", "merchant_power"]:
            if ind_key == "regulated_utilities":
                catalysts.append(
                    "【核准资产基础保障稳定回报与算力中心用电红利】输配电网享有受监管的合理权益报酬率 (ROE)，"
                    "人工智能超算集群与高端制造业用电负荷急剧增长，驱动资本开支加速转化为稳健现金流。"
                )
                risks.append(
                    "【极端极端气候引发输变电设备损毁与野火诉讼赔偿】飓风、极寒及山火导致电网基础设施大面积毁损，"
                    "高额灾后重建资本开支与巨额第三方民事责任诉讼产生一次性非经常性重创。"
                )
            else:  # merchant_power
                catalysts.append(
                    "【现货峰谷电价套利与容量电价政策补偿落地】清洁风光能源与高效火电机组梯级优化调度，"
                    "容量电价托底机制锁定基础收益，电力现货市场高峰期高溢价售电显著增厚经营性利润。"
                )
                risks.append(
                    "【火电燃料煤炭天然气暴涨与新能源弃电负电价冲击】动力煤等一次能源价格非理性飙升挤压火电边际利润，"
                    "局部电网消纳调峰能力不足导致风光机组出现弃风弃光与负电价售电窘境。"
                )

        # =================================================================
        # 14. 权益型不动产信托 REITs 与房地产综合开发服务 (equity_reit, real_estate_services)
        # =================================================================
        elif ind_key in ["equity_reit", "real_estate_services"]:
            if ind_key == "equity_reit":
                catalysts.append(
                    "【核心区位优质物业加权长租期与抗通胀阶梯递增】数据中心、冷链物流及现代产业园资产出租率超 95%，"
                    "加权平均剩余租期 (WALT) 长达数年，合同中明确租金阶梯递增条款抵御通胀侵蚀。"
                )
                risks.append(
                    "【宏观长端利率高企推升资本化率导致物业估值折价】高利率环境下商业地产资本化率 (Cap Rate) 上移，"
                    "写字楼等传统物业面临重估减值，大额再融资贷款到期面临借贷利息成本翻倍风险。"
                )
            else:  # real_estate_services
                catalysts.append(
                    "【代建管理轻资产转型与优质商业物业综合运营】从传统重资产拿地开发向高毛利代建与物管服务转型，"
                    "无借贷财务杠杆包袱，物业管理费与商业招商分成创造稳定的内生现金流。"
                )
                risks.append(
                    "【土地成交与新房开发投资持续低迷】传统房地产开工与竣工面积萎缩减少新增物业管理服务面积，"
                    "存量重资产商品房库存去化迟缓面临大额资产减值准备计提压力。"
                )

        # =================================================================
        # 15. 知识库自适应兜底保障 (结合单一事实来源 IndustryKnowledgeProfile)
        # =================================================================
        if not catalysts:
            if prof.leading_bull_triggers:
                catalysts.extend(prof.leading_bull_triggers[:2])
            else:
                catalysts.append(
                    f"【{rec.industry_name_zh}细分龙头稳健基本盘】依靠在{rec.sector_name_zh}领域的既有客户积累，"
                    f"保持平稳再投资回报率与内生现金流周转，推动公司估值向公允中枢平稳靠拢。"
                )

        if not risks:
            if prof.leading_bear_defenses:
                risks.extend(prof.leading_bear_defenses[:2])
            else:
                risks.append(
                    f"【宏观中枢波动与行业周期竞争】{rec.industry_name_zh}行业整体竞争加剧，"
                    f"需警惕宏观利率偏高与产业链上下游挤压对企业净利率空间的负向扰动。"
                )

        # 优先选取行业专属知识库提炼的第一因果触发器，确保买方研报具备最前沿专业直觉
        top_opt = prof.leading_bull_triggers[0] if prof.leading_bull_triggers else catalysts[0]
        top_pes = prof.leading_bear_defenses[0] if prof.leading_bear_defenses else risks[0]

        # 从知识库统一中枢调取行业法定估值路线与买方反证规则
        rule = self.repo.get_industry_rule(ind_key)
        val_route = rule.valuation_route if rule else ""
        counter_ev = rule.counterevidence if rule else ""

        return IndustryCausalFacts(
            industry_id=rec.industry_id,
            industry_name_zh=rec.industry_name_zh,
            industry_catalysts=catalysts,
            industry_risks=risks,
            leading_optimistic_trigger=top_opt,
            leading_pessimistic_trigger=top_pes,
            valuation_route=val_route,
            counterevidence=counter_ev,
        )
