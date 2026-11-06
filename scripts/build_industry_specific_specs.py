"""生成行业专属采集规格和逐行业中文数据字典；不联网、不生成原始事实。"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 每项：中文名称、单位、必需原始输入、口径约束。复合项独立保存，禁止平均成评分。
SPEC = {
 'oil_gas': [
  '分产品实现售价|currency_per_unit|产品销售收入,产品销售量|原油 USD/bbl、天然气 USD/Mcf 分开；套期保值前后分开',
  '单位开采现金成本|currency_per_unit|现金开采成本,匹配产量|租赁运营费、生产税、运输费逐项定义；折旧和勘探资本支出排除',
  '已探明储量寿命|years|已探明储量,同范围年产量|储量期末、产量年度；净权益及 BOE 换算一致；开发未开发分别保留'],
 'energy_services': [
  '设备日利用率|ratio|运营设备天数,可用设备日历天数|钻井船与陆上设备分开；收入效率不能替代利用率',
  '新增订单收入比|ratio|当期新增订单金额,同期间服务收入|新增订单与期末 backlog 不同；新增合同天数按公司定义计价',
  '实际合同日收入|currency_per_day|匹配合同收入,合同运营天数|实际日收入与新签合同日费率分别保存；排除终止补偿及报销按原文'],
 'midstream': [
  '分产品吞吐量|physical_quantity|产品吞吐量,披露单位,日均或期间总量|原油 NGL 天然气分开；Bcf/d 和 bbl/d 不直接相加',
  '固定收费收入占比|ratio|固定收费合同收入,匹配相关收入|收费处理量占比不能替代收费收入占比；最低量承诺条款另列',
  '维持资本开支现金额|currency|公司披露 sustaining capex,范围说明|实际与预算分开；增长资本开支及并购不能混入'],
 'mining': [
  '分商品实现售价|currency_per_unit|商品净销售额,商品销售数量|铜 USD/lb、金 USD/oz 分开；临时定价及副产品信用说明',
  '分商品现金单位成本|currency_per_unit|净现金生产成本,匹配商品产量|副产品抵扣前后分开；不得用全部营业成本代替',
  '矿石品位|ratio|有效金属含量,矿石处理量|矿区和工艺分开；品位与回收率是两个变量'],
 'chemicals': [
  '同产品原料价差|currency_per_unit|产品单位售价,匹配原料单位成本,投入系数|不同产品链分开；销售价格同比不是绝对价差',
  '有效产能开工率|ratio|同产品实际产出,有效产能|检修停机与永久关厂另列；名义产能不替代有效产能',
  '指定化工链行业库存|physical_quantity|行业库存量,覆盖企业地区产品|公司账面存货不是行业库存；覆盖范围缺失不计算'],
 'packaging': [
  '分品类出货数量|physical_quantity|包装产品出货量,单位|纸箱平方英尺、纸板吨分别保存；增长率作为补充不能当数量',
  '成本传导合同滞后|days|成本变化日期,合同调价生效日期,合同机制|按同一客户产品合同；季度价格实现不等于滞后天数',
  '回收材料单位投入成本|currency_per_unit|回收原料采购成本,采购数量|OCC 等品类及地区分开；原生浆成本不能替代'],
 'capital_goods': [
  '新增订单收入比|ratio|新增订单金额,同期间确认收入|按分部同币种；订单含取消和服务多年合同的定义保留',
  '积压订单及取消条款|components|期末 backlog,取消条款,可执行条件|金额与合同条款分别保存；不得全部视作保证收入',
  '订单交付周期|days|接单日期,交付验收日期,订单群|平均中位数和区间分开；库存周转不能替代'],
 'aerospace_defense': [
  '已拨款订单占比|ratio|已拨款或已承诺可执行订单,相同范围总订单|funded 与 unfunded backlog 分开；总 backlog 不能替代比例',
  '项目总成本偏差|currency|最新预计总成本,原始批准成本基准,项目标识|项目亏损准备仅为相关证据；缺原始基准不能计算偏差',
  '分机型验收交付数量|physical_quantity|验收交付量,产品标识|飞机导弹等不能相加；交付、产出、订单分别保存'],
 'transport_logistics': [
  '运输工作量载运率|ratio|收入客公里或吨公里,可用座公里或吨公里|航空、货运分开；单位距离口径相同',
  '单位运输收入|currency_per_distance_unit|匹配客运或货运收入,收入运输工作量|yield 与含附加业务 PRASM 不同；英里公里不可混合',
  '单位运输燃料成本|currency_per_distance_unit|匹配燃料成本,运输工作量|每加仑油价不是每座英里燃料成本；炼厂及对冲调整另列'],
 'business_services': [
  '服务人员计费利用率|ratio|可计费工时,可用工时|工资处理平台不必采用人员利用率；培训休假纳入规则保存',
  '客户数量留存率|ratio|基期客户中本期留存数量,基期客户数量|客户收入留存率不是客户数量留存率；新增客户排除',
  '标准服务合同单价|currency_per_unit|可比服务收入,匹配计费单位|客户工资人数、合同数、计费小时分别定义；不混分部'],
 'construction': [
  '可执行积压订单覆盖年数|years|可执行期末订单额,同范围年度收入|总订单若包括未融资或可取消部分须披露差异',
  '工程项目成本偏差|currency|最新预计总成本,合同预算,项目编号|亏损准备与预算偏差分别保存；不能从分部利润反推',
  '合同资产及客户预付款|components|合同资产,现金客户预付款,合同负债|合同负债可能含非现金项；不得直接视作现金预收款'],
 'autos': [
  '终端零售车辆数量|physical_quantity|零售终端交付数,品牌地区|批发销量和产量不能代替零售；含合营子公司须注明',
  '经销商库存天数|days|经销商库存车辆,匹配日均零售数|制造商自有账面库存不能代替渠道库存',
  '单车变动成本贡献|currency_per_vehicle|车辆净收入,明确变动成本,匹配零售数量|缺变动成本时留空；营业利润除以销量只能作另一个代理指标'],
 'retail': [
  '可比门店销售增长|ratio|公司同店销售披露,门店纳入规则|线上业务、燃油、汇率和 53 周调整明确',
  '期间存货周转次数|turns|匹配期间销售成本,期初期末同范围存货|平均库存至少期初期末；未年化的季度次数不称年度周转',
  '履约成本占相关收入比|ratio|履约配送仓储成本,相关收入|销售管理费用总额不能代替；物流与广告业务分开'],
 'restaurants': [
  '可比餐厅销售增长|ratio|同店销售增长披露,店群规则|直营加盟及地区分开；汇率口径保留',
  '单店经营利润|currency_per_store|同范围门店经营利润,加权平均店数|排除总部费、折旧等依原文记录；加盟租金收入不等于加盟店利润',
  '加盟商闭店与违约记录|event_records|闭店事件,违约事件,加盟商范围|净开店数不能证明没有闭店或违约；原因及日期保留'],
 'travel_leisure': [
  '可比酒店入住率|ratio|售出间夜,可售间夜或公司披露入住率|同物业群、地区、品牌；管理加盟与自营分开',
  '可比酒店 ADR|currency_per_room_night|匹配客房收入,售出间夜或公司 ADR|ADR 与 RevPAR 不同；币种和固定汇率口径保留',
  '酒店预订群取消率|ratio|同一预订群取消数,预订群总数|取消日期与入住日期不同；退款金额不是取消数量'],
 'housing_durables': [
  '住宅订单取消率|ratio|取消订单数,公司定义的匹配订单群|取消除以毛订单或期初订单分别保留',
  '已结算交付住宅数量|physical_quantity|完成 closing 的住宅数|签约订单和开工数量不能代替交付',
  '持有与控制土地批次|components|持有地块数,期权或合同控制地块数|owned 与 controlled 不相加冒充持有；金额和批次数分开'],
 'food_beverage': [
  '可比产品销量增长|ratio|本期可比销量,同期可比销量或披露增长|系统销量与母公司浓缩液销售分别保存；日均与实际日历总量区分',
  '价格与组合增长贡献|ratio|公司价格组合桥接贡献,公司桥接定义|price/mix 不等于纯价格；销量与汇率贡献分别保存',
  '渠道产品库存数量|physical_quantity|经销商库存量,产品渠道覆盖|公司存货与渠道库存不同；覆盖不完整不可外推'],
 'household_personal': [
  '有机可比销量增长|ratio|公司可比销量披露,范围调整|并购退出与汇率排除方法保留；销售额增速不能替代',
  '分产品地区市场份额|ratio|品牌销售量或额,匹配市场总量|市场份额变化百分点与份额水平分开；第三方覆盖注明',
  '营销费用收入比|ratio|明确广告或营销费用,匹配收入|广告费用不等于全部营销投入；SG&A 总额不能替代'],
 'staples_retail': [
  '可比零售销售增长|ratio|同店销售披露,店群规则|燃油汇率和线上范围明确；调整前后分别保存',
  '零售损耗率|ratio|损耗金额,明确销售额或存货成本基数|报废盗损原因保留；没有损耗金额不能从毛利率倒推',
  '可比交易或客流增长|ratio|本期可比交易数,同期交易数或公司披露增长|客流与客单价分开；会员数增长不能替代'],
 'tobacco': [
  '传统卷烟出货量|physical_quantity|传统卷烟数量,地区产品|加热烟与尼古丁袋单独保存；出货不等于终端消费',
  '卷烟扣税单位净售价|currency_per_unit|扣消费税传统产品收入,匹配传统产品数量|替代产品和渠道补贴排除；货币和单位一致',
  '替代产品收入及利润|components|无烟产品净收入,同范围经营利润|收入占比不能作为盈利率；利润未披露保留缺口'],
 'pharma': [
  '单药净销售收入|currency|产品净收入,药品与地区标识|返利折扣计入方式保留；联合销售和合作分成分开',
  '指定窗口专利到期收入暴露|ratio|窗口内到期产品基期净收入,匹配总产品收入,期限清单|专利与监管独占期及诉讼结果不同；不以 LOE 预测损失替代收入暴露',
  '药物研发里程碑事件|event_records|药物项目,阶段,主要终点,结果,事件日期|临床成功和商业审批不同；试验终点及来源版本保留'],
 'biotech': [
  '临床研发里程碑事件|event_records|试验标识,阶段,预设终点,结果,日期|实际读出与预期读出分别保存；公司计划不能当已实现结果',
  '正常化现金跑道|months|可用现金和投资,正常化月净消耗,调整项|受限现金和不可变现投资排除；正经营现金流时不强算消耗',
  '融资缺口与稀释情景|scenario|研发现金预算,债务到期,可用资金,发行价格,新增股数|情景假设不是原始事实；回购后净股数变化不等于 SBC 造成的稀释'],
 'medical_devices': [
  '分手术产品操作数量|physical_quantity|实际手术数量,系统类型|da Vinci 与 Ion 分开；增长率不能代替绝对数量',
  '新增装机及期末装机量|components|当期系统 placement,期末 installed base,退役调整|交付、租赁、装机和退役分别说明',
  '每匹配系统耗材收入|currency_per_system|同系统耗材收入,匹配平均有效装机基数|期末装机不能无说明代替平均基数；服务收入排除'],
 'health_services': [
  '同院可比医疗服务量|physical_quantity|住院或等价住院次数,院群定义|admission 与 equivalent admission 不同；全部医院与同院分开',
  '每等价住院净收入|currency_per_admission|匹配净服务收入,等价住院次数|医院收费标价不是净收入；门诊折算规则保留',
  '医疗人工成本收入比|ratio|工资福利或匹配人工成本,净服务收入|合同工是否含入须明确；人工成本与全部运营成本不同'],
 'managed_care': [
  '报告医疗成本率|ratio|匹配医疗成本,医疗保费或公司 MCR|报告与调整后 MCR 分开；监管 MLR 不直接替代',
  '分险种会员数|physical_quantity|医疗险会员数量,险种,期末或平均|Optum 客户及服务人数不能当保险会员；按险种防重叠',
  '同险种可比保费费率调整|ratio|同保障客户群保费变化,险种及保障规则|总保费增长含会员结构变化；政府支付削减单列'],
 'banks': [
  '同口径年化净息差|ratio|年化净利息收入,平均生息资产或公司 NIM|税等价与 GAAP 分开；年化天数方法保留',
  '年化贷款净核销率|ratio|扣回收后的净核销额,平均同范围贷款|拨备费用不是净核销；信贷卡与全部贷款分开',
  '资本与流动性监管比率|components|CET1 比率,LCR 比率,NSFR 比率,适用规则|标准法与高级法分开；现金金额不能替代 LCR；不得平均成评分'],
 'insurance': [
  '财险报告综合成本率|ratio|同范围赔付率,费用率或报告 combined ratio|事故年度排灾与报告值分开；寿险不能使用',
  '历史事故准备金发展|currency|前期事故年度有利或不利发展,再保险范围|有利不利符号明确；当年灾害损失不等于准备金发展',
  '资产负债期限币种匹配|components|资产久期,负债久期,币种敞口,匹配范围|投资组合久期不能代替负债久期；缺负债数据不能计算缺口'],
 'asset_management': [
  '客户净资金流入|currency|客户流入,流出,资本返还,公司流量定义|市场收益外汇并购增加剔除；realizations 是否另列按原文',
  '匹配收费管理资产|currency|收费资产余额,产品和费率范围|总 AUM 可能含不收费资产；期末与平均 AUM 分开',
  '基础管理费有效年化率|ratio|基础管理费,匹配平均收费资产,年化方法|业绩费和技术服务收入排除；期末总 AUM 不能替代'],
 'payments': [
  '定义内支付处理金额|currency|支付处理量,交易类型,地区币种|支付量与含现金提取总量分开；跨境增速不是总处理额',
  '匹配净交易变现率|ratio|同期间净交易相关收入,匹配处理金额|服务收入确认可能基于上季度交易；全部收入不能不经调节直接除',
  '承担的欺诈与信用损失率|ratio|承担欺诈或贷款损失,匹配交易量或贷款基数|网络品牌通常不承担发卡行全部损失；无承担关系记不适用'],
 'software': [
  '同客户群净收入留存率|ratio|公司 NRR,同群窗口与定义|披露约数区间照原文保存；客户收入留存和数量留存不同',
  'ARR 与期间订阅收入|components|期末 ARR,期间订阅收入,订阅定义|按量计费收入不能自动改名 ARR；ARR 与收入分开',
  '激励费用及股数变化|components|SBC 费用,期初期末实际发行股数,加权稀释股数|实际股数与 EPS 分母不同；拆股并购回购需调节'],
 'semiconductors': [
  '终端渠道库存量或天数|components|渠道产品库存量,匹配渠道日销量,终端类别|企业账面存货与渠道库存不同；缺渠道数据留空',
  '有效晶圆产能利用率|ratio|实际产出,同工艺有效产能|bit shipment 增长不是利用率；晶圆厂与无厂业务分别适用',
  '同产品单位平均售价|currency_per_unit|产品收入,匹配 bit 或芯片数量|ASP 变化百分数只为补充；产品密度及 DRAM NAND 分开'],
 'semi_equipment': [
  '半导体设备订单收入比|ratio|新增设备订单,同期间设备收入|设备与服务分开；公司停止披露订单时保留缺口',
  '分客户制程资本开支|currency|客户实际 capex,工艺及客户标识|必须引用客户财报；设备厂自己的 capex 不能代替',
  '客户取消及延期订单|components|取消订单金额,延期订单金额,合同与日期|取消与延期分开；订单净变动不能反推出取消金额'],
 'hardware': [
  '分产品硬件出货数量|physical_quantity|产品 sell-in 出货量,地区,期间|sell-in 与 sell-through 分开；游戏主机和传感器不能相加',
  '硬件渠道存量|physical_quantity|渠道库存量,渠道产品覆盖|公司 inventory 不能代替经销商库存',
  '分产品毛利及收入组合|components|产品毛利,产品收入,同范围总收入|分部营业利润率不是产品毛利；产品收入份额单列'],
 'it_services': [
  '专业人员可计费利用率|ratio|计费工时,可用专业人员工时或公司 utilization|培训与交付支持排除按公司定义保留',
  '同范围新增合同金额|currency|新签合同 bookings,服务类别|咨询与托管服务合同不同年限；合同额不是当期收入',
  '单位计费服务费率|currency_per_hour|同范围服务收入,实际计费工时|人均收入不能替代小时费率；外包转售收入剔除'],
 'telecom': [
  '单匹配用户服务 ARPU|currency_per_subscriber|服务收入,平均对应用户,月数|ARPA 是账户而非用户；账户收入不能直接改名 ARPU',
  '同用户群月均流失率|ratio|断开用户数,平均用户,月数或披露 churn|电话流失与全部设备流失分开；后付费和预付费分开',
  '网络维持及扩张现金开支|components|网络现金 capex,维持部分,扩张部分|频谱购买及融资租赁分开；只披露总额不能填拆分'],
 'digital_platforms': [
  '定义内活跃用户|physical_quantity|DAU 或 MAU,频率,活跃规则|跨产品用户去重；平均月与期末日不能混用',
  '匹配活跃用户变现收入|currency_per_user|同产品收入,平均活跃用户或公司 ARPP|DAU 与 MAU 分母不同；ARPP 公司方法完整保留',
  '平台交易净抽佣率|ratio|净交易收入,匹配 GMV|纯广告平台业务不适用；广告收入不能除虚构 GMV'],
 'media_entertainment': [
  '付费订阅用户数量|physical_quantity|paid membership,平均或期末,产品地区|MAU 及广告受众不能代替付费用户；停披露后旧值不能冒充本期',
  '内容现金投入|currency|内容现金支付,许可自制与预付口径|资本化新增额与当期现金支付不同；研发费用不能代替',
  '当期内容摊销|currency|内容资产摊销或内容成本附注|现金购买与摊销分开；公司全部折旧摊销不能替代'],
 'regulated_utilities': [
  '监管批准费率资产基数|currency|监管批准 rate base,法律主体,决定日期|集团 PP&E 与预测 rate base 不能当获批资产',
  '监管批准权益回报率|ratio|allowed ROE,权益资本结构,决定生效日|申请 ROE 与批准 ROE 分开；实际 ROE 不是 allowed ROE',
  '监管成本回收滞后|days|支出日期,核准回收生效日期,监管机制|燃料附加条款和一般费率案分开；不从利润猜测时滞'],
 'merchant_power': [
  '匹配售电捕获价格|currency_per_mwh|匹配售电净收入,对应 MWh|批发零售和对冲结算分开；集团收入不能直接除总发电量',
  '效率调整后燃料电价差|currency_per_mwh|同范围电价,燃料价格,热耗效率,单位换算|核电与燃气燃煤分别定义；燃料价格需按热耗换算',
  '匹配预期发电对冲覆盖率|ratio|已对冲电量,同窗口预计售电量|资产负债表衍生品公允价值不能替代；风险窗口与概率保留'],
 'equity_reit': [
  '可比物业 NOI 增长|ratio|same-store 本期 NOI,同群同期 NOI或披露增长|现金与直线法净有效租金分别保存；物业群冻结规则记录',
  '同物业面积出租率|ratio|已出租面积,可出租面积或报告 occupancy|平均与期末出租率不同；自有与管理组合分开',
  'FFO 至 AFFO 调节明细|components|起点 FFO,经常资本支出,租赁佣金,非现金租金,其他调整,终点 AFFO|Core FFO 不是 AFFO；逐项勾稽及公司定义齐备才完成'],
 'real_estate_services': [
  '开发销售现金回款|currency|开发项目实际现金收款,项目范围|确认收入与销售合同额不能代替现金回款',
  '同预售群取消率|ratio|预售取消数量或金额,匹配同预售群基数|开发项目适用；经纪纯服务业务不适用',
  '经纪管理服务佣金率|ratio|匹配佣金服务收入,实际交易金额或数量|开发销售收入不能代替佣金；开发与经纪需分部或第二样本']
}

COMPANIES = {
 'oil_gas': ('EOG','EOG Resources','US','油气勘探生产'),
 'energy_services': ('RIG','Transocean','US','海上合同钻井'),
 'midstream': ('EPD','Enterprise Products Partners','US','管输处理与储运'),
 'mining': ('FCX','Freeport-McMoRan','US','铜金矿业'),
 'chemicals': ('DOW','Dow','US','基础及特种化工'),
 'packaging': ('PKG','Packaging Corporation of America','US','纸箱与箱板纸'),
 'capital_goods': ('GEV','GE Vernova','US','电力及电网设备'),
 'aerospace_defense': ('LMT','Lockheed Martin','US','国防航空项目'),
 'transport_logistics': ('DAL','Delta Air Lines','US','航空运输'),
 'business_services': ('ADP','Automatic Data Processing','US','工资处理与人力资源服务'),
 'construction': ('FLR','Fluor','US','工程建设合同'),
 'autos': ('7203','Toyota Motor','JP','整车零售与生产，金融分部单列'),
 'retail': ('WMT','Walmart','US','一般零售分部'),
 'restaurants': ('MCD','McDonald’s','US','直营及加盟餐饮'),
 'travel_leisure': ('MAR','Marriott International','US','管理及加盟酒店'),
 'housing_durables': ('DHI','D.R. Horton','US','住宅建造交付'),
 'food_beverage': ('KO','Coca-Cola','US','饮料系统及浓缩液'),
 'household_personal': ('PG','Procter & Gamble','US','家庭及个人消费品'),
 'staples_retail': ('COST','Costco','US','会员仓储必需消费零售'),
 'tobacco': ('PM','Philip Morris International','US','卷烟及无烟产品'),
 'pharma': ('PFE','Pfizer','US','商业化药品与研发管线'),
 'biotech': ('MRNA','Moderna','US','生物技术研发与产品'),
 'medical_devices': ('ISRG','Intuitive Surgical','US','手术机器人及耗材'),
 'health_services': ('HCA','HCA Healthcare','US','医院医疗服务'),
 'managed_care': ('UNH','UnitedHealth Group','US','UnitedHealthcare 医疗保险，Optum 单列'),
 'banks': ('JPM','JPMorgan Chase','US','银行及贷款业务'),
 'insurance': ('CB','Chubb','US','财产险分部，寿险单列'),
 'asset_management': ('BLK','BlackRock','US','收费资产管理，技术服务单列'),
 'payments': ('V','Visa','US','支付网络，非发卡贷款业务'),
 'software': ('DDOG','Datadog','US','订阅及按使用量的软件服务'),
 'semiconductors': ('MU','Micron Technology','US','DRAM 与 NAND 制造'),
 'semi_equipment': ('8035','Tokyo Electron','JP','半导体制造设备'),
 'hardware': ('6758','Sony Group','JP','游戏硬件等明确产品分部'),
 'it_services': ('ACN','Accenture','US','咨询与托管 IT 服务'),
 'telecom': ('VZ','Verizon','US','无线消费者及企业通信分部'),
 'digital_platforms': ('META','Meta Platforms','US','社交广告平台'),
 'media_entertainment': ('NFLX','Netflix','US','订阅影视内容服务'),
 'regulated_utilities': ('DUK','Duke Energy','US','受监管公用事业法律主体'),
 'merchant_power': ('CEG','Constellation Energy','US','竞争性发电及售电'),
 'equity_reit': ('PLD','Prologis','US','物流物业权益 REIT'),
 'real_estate_services': ('HHH','Howard Hughes Holdings','US','地产开发分部；集团及其他业务单列')
}

# 复合驱动的输出原子字段：名称、计量单位、统计期间相互独立。
COMPOSITE = {
 'capital_goods_driver_2':[('backlog','积压订单金额','currency','instant'),('cancellation_terms','取消及履约条件','text','event')],
 'construction_driver_3':[('contract_assets','合同资产','currency','instant'),('cash_advances','已收客户预付款','currency','instant'),('contract_liabilities','合同负债','currency','instant')],
 'housing_durables_driver_3':[('owned_lots','持有地块数','lots','instant'),('controlled_lots','期权及合同控制地块数','lots','instant')],
 'tobacco_driver_3':[('smoke_free_revenue','无烟产品净收入','currency','duration'),('smoke_free_profit','同范围无烟业务经营利润','currency','duration')],
 'medical_devices_driver_2':[('placements','当期系统投放数','systems','duration'),('installed_base','有效装机存量','systems','instant'),('retired_systems','当期退役系统数','systems','duration')],
 'banks_driver_3':[('cet1','普通股一级资本充足率','ratio','instant'),('lcr','流动性覆盖率','ratio','source_defined_average'),('nsfr','净稳定资金比例','ratio','instant')],
 'insurance_driver_3':[('asset_duration','资产久期','years','instant'),('liability_duration','负债久期','years','instant'),('currency_exposure','分币种未匹配敞口','currency','instant')],
 'software_driver_2':[('arr','期末年化经常性收入','currency','instant'),('subscription_revenue','期间订阅收入','currency','duration')],
 'software_driver_3':[('sbc','股权激励费用','currency','duration'),('shares_start','期初实际流通股数','shares','instant'),('shares_end','期末实际流通股数','shares','instant'),('weighted_diluted_shares','期间加权稀释股数','shares','duration_average')],
 'semiconductors_driver_1':[('channel_units','渠道存货数量','physical_quantity','instant'),('channel_days','渠道库存覆盖天数','days','instant')],
 'semi_equipment_driver_3':[('cancellations','订单取消额','currency','duration'),('deferrals','订单延期额','currency','duration')],
 'hardware_driver_3':[('product_gross_profit','分产品毛利','currency','duration'),('product_revenue_share','同产品收入占比','ratio','duration')],
 'telecom_driver_3':[('maintenance_capex','网络维持现金开支','currency','duration'),('growth_capex','网络扩张现金开支','currency','duration'),('total_network_capex','网络现金开支总额','currency','duration')],
 'equity_reit_driver_3':[('ffo','调节起点 FFO','currency','duration'),('maintenance_capex','经常维持资本开支','currency','duration'),('leasing_commissions','租赁佣金','currency','duration'),('noncash_rent_adjustments','非现金租金调节','currency','duration'),('other_adjustments','逐项其他调节','currency','duration'),('affo','调节终点 AFFO','currency','duration')]
}

def build():
    catalog = json.loads((ROOT/'knowledge/metrics/catalog.json').read_text(encoding='utf-8'))
    parents = {m['id']: m for m in catalog['metrics'] if '_driver_' in m['id']}
    contracts = {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'knowledge/contracts/industries').glob('*.json')}
    assert set(SPEC) == set(COMPANIES) == set(contracts), '行业集合不完整'
    directory = ROOT/'knowledge/metrics/industry-specific'
    directory.mkdir(exist_ok=True)
    specifications=[]; representatives=[]; index=['# 行业专属指标统一目录','', '每个文件独立说明该行业的三个驱动。来源发现、原文核验、数值登记分别管理。', '', '| 行业 | 代表公司 | 单表说明 |','|---|---|---|']
    for industry, rules in SPEC.items():
        ticker,name,market,scope=COMPANIES[industry]
        rep={'industry_id':industry,'ticker':ticker,'name':name,'market':market,'scope_zh':scope,'selection_reason_zh':'以该具体业务作为经营披露和口径验证样本；不将集团总数自动映射为分部指标','classification_status':'candidate_requires_segment_review','source_discovery_refs':[], 'original_review_status':'pending_original_review'}
        representatives.append(rep)
        title=contracts[industry].get('name_zh',industry)
        lines=[f'# {title}：行业专属指标数据字典','', f'代表公司：{name}（{market}:{ticker}）。适用范围：{scope}。代表公司不覆盖所有子行业。','']
        for n, rule in enumerate(rules,1):
            label,unit,inputs,restriction=rule.split('|')
            parent=parents[f'{industry}_driver_{n}']
            item={'parent_metric_id':parent['id'],'industry_id':industry,'name_zh':label,'parent_name_zh':parent['name'],'business_definition_zh':parent['definition'],'value_kind': unit if unit in ['components','event_records','scenario'] else 'scalar','unit':unit,'required_inputs_zh':inputs.split(','),'comparability_rules_zh':restriction,'source_priority':['issuer_annual_report','issuer_operating_supplement','regulator_original','official_industry_statistics'],'collection_method':'ai_browser_original_review','validation_status':'specification_defined_observation_pending','numeric_threshold':None}
            if unit=='components':
                components=COMPOSITE[parent['id']]
            elif unit=='event_records':
                components=[('event_id','事件及项目标识','text','event'),('event_date','事件实际发生日期','date','event'),('status','状态或实际结果','text','event'),('conditions','预设终点及生效条件','text','event')]
            elif unit=='scenario':
                components=[('scenario_id','假设情景标识','text','forecast'),('funding_gap','情景融资缺口','currency','forecast'),('issue_price','情景发行价格','currency_per_share','forecast'),('new_shares','情景新增股数','shares','forecast'),('dilution_ratio','情景稀释比例','ratio','forecast')]
            else:
                components=[('value',label,unit,'source_dependent')]
            item['component_specs']=[{'component_id':parent['id']+'__'+cid,'name_zh':cname,'unit_family':cunit,'period_basis':cperiod,'requires_explicit_source_definition':True} for cid,cname,cunit,cperiod in components]
            specifications.append(item)
            lines += [f"## {parent['id']} — {label}",'','| 字段 | 中文说明 |','|---|---|',f"| 原驱动中文名称 | {parent['name']} |",f"| 业务含义 | {parent['definition']} |",f'| 值类型 | {item["value_kind"]} |',f'| 单位 | {unit} |',f'| 必需原始数据项 | {inputs} |',f'| 口径与禁止替代项 | {restriction} |','| 来源顺序 | 公司年报及经营补充表、监管原文、官方行业统计 |','| 采集方法 | AI 浏览器核验原文后归档；无 API 配置 |','| 缺数处理 | 保留空值、原因及核验材料范围；阻断对应结论 |','| 判断标准 | 比较同口径时间趋势并保留反证；无经验验证阈值 |','']
            lines += ['| 原子字段标识 | 中文名称 | 单位类型 | 期间类型 |','|---|---|---|---|']
            for c in item['component_specs']:
                lines.append(f"| {c['component_id']} | {c['name_zh']} | {c['unit_family']} | {c['period_basis']} |")
            lines += ['', '所有字段均须绑定具体原文。currency 必须另填币种；physical_quantity 必须另填产品物理单位。缺数不得补零。','']
        (directory/f'{industry}.md').write_text('\n'.join(lines),encoding='utf-8')
        index.append(f'| {title} | {name}（{market}:{ticker}） | [{industry}]({industry}.md) |')
    assert len(specifications)==123
    for path,data in [('industry-specifications.json',{'schema_version':'1.0.0','specifications':specifications}),('representatives.json',{'schema_version':'1.0.0','selection_is_not_investment_recommendation':True,'representatives':representatives})]:
        target=ROOT/'knowledge/metrics'/path
        # 来源调查后不得由生成器覆盖人工核验记录。
        if path=='representatives.json' and target.exists():
            old=json.loads(target.read_text(encoding='utf-8'))
            assert {r['industry_id'] for r in old['representatives']}==set(COMPANIES)
            continue
        target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (directory/'README.md').write_text('\n'.join(index)+'\n',encoding='utf-8')
    # 独立采集规格契约：字段中文名与约束直接随 Schema 保存。
    string_fields={
      'parent_metric_id':'父驱动标识','industry_id':'行业标识','name_zh':'原子口径中文名称',
      'parent_name_zh':'父驱动中文名称','business_definition_zh':'父驱动业务定义',
      'unit':'单位类型','comparability_rules_zh':'口径及禁止替代规则'}
    properties={k:{'type':'string','minLength':1,'title':v} for k,v in string_fields.items()}
    properties.update({
      'value_kind':{'enum':['scalar','components','event_records','scenario'],'title':'值结构类型'},
      'required_inputs_zh':{'type':'array','minItems':1,'items':{'type':'string','minLength':1},'title':'必需原始输入项'},
      'source_priority':{'type':'array','minItems':1,'items':{'enum':['issuer_annual_report','issuer_operating_supplement','regulator_original','official_industry_statistics']},'title':'原始来源优先级'},
      'collection_method':{'const':'ai_browser_original_review','title':'原文采集方法'},
      'validation_status':{'const':'specification_defined_observation_pending','title':'规格与观测状态'},
      'numeric_threshold':{'type':'null','title':'未经验证禁用的数值阈值'}})
    cp={k:{'type':'string','minLength':1,'title':v} for k,v in {'component_id':'原子字段标识','name_zh':'原子字段中文名称','unit_family':'单位类型','period_basis':'统计期间类型'}.items()}
    cp['requires_explicit_source_definition']={'const':True,'title':'必须绑定原文口径'}
    properties['component_specs']={'type':'array','minItems':1,'title':'原子字段数据字典','items':{'type':'object','additionalProperties':False,'required':list(cp),'properties':cp}}
    schema={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:shuiyuan:industry-specific-specifications:1.0.0','title':'行业专属原子采集规格','type':'object','additionalProperties':False,'required':['schema_version','specifications'],'properties':{'schema_version':{'const':'1.0.0'},'specifications':{'type':'array','minItems':123,'items':{'type':'object','additionalProperties':False,'required':list(properties),'properties':properties}}}}
    (ROOT/'schemas/industry-specific-specifications.schema.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'industries':len(COMPANIES),'driver_specifications':len(specifications)},ensure_ascii=False))

if __name__=='__main__':
    build()
