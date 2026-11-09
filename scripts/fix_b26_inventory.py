import json
import re
from pathlib import Path

p = Path(r"c:\Users\shared_user\AppData\Roaming\Tencent\Marvis\User\SHARED_USER_ID\skills\custom\shuiyuan-analysis\data_sources\batch26_verified_dossiers_data.py")
text = p.read_text(encoding="utf-8")

replacements = [
    (
        '"inventory_cycle_position": "全球绿色生咖啡豆长周期锁定，门店鲜奶及包装辅料处于健康流转状态"',
        '"inventory_cycle_position": "全球绿色生咖啡豆长周期锁定，门店鲜奶及包装辅料处于健康流转状态",\n                "inventory_write_down_risk": "生豆物理质保期长达数年，滞销或减值准备占库存比不足 1.2%"'
    ),
    (
        '"inventory_cycle_position": "完全免受制造业库存周期影响，核心资产规模月度净流入超 200 亿美元"',
        '"inventory_cycle_position": "完全免受制造业库存周期影响，核心资产规模月度净流入超 200 亿美元",\n                "inventory_write_down_risk": "纯金融经纪与财富托管无实体商品，库存跌价减值风险为零"'
    ),
    (
        '"inventory_cycle_position": "离岸深海与中东钻井平台利用率饱满，高端油服技术工具处于供不应求良性阶段"',
        '"inventory_cycle_position": "离岸深海与中东钻井平台利用率饱满，高端油服技术工具处于供不应求良性阶段",\n                "inventory_write_down_risk": "随钻设备耐用度与定制化程度高，呆滞存货减值准备占总资产比例低于 0.3%"'
    ),
    (
        '"inventory_cycle_position": "下游新房开工平缓但翻新重涂需求韧性强，直营专卖店直控库存有效规避渠道积压"',
        '"inventory_cycle_position": "下游新房开工平缓但翻新重涂需求韧性强，直营专卖店直控库存有效规避渠道积压",\n                "inventory_write_down_risk": "标准调色乳胶漆保质期长且配方稳定，历史存货减值拨备率低于 1.5%"'
    ),
    (
        '"inventory_cycle_position": "移动厢式加盟商每周高频补货，无大宗滞销积压，整体供需极其平稳"',
        '"inventory_cycle_position": "移动厢式加盟商每周高频补货，无大宗滞销积压，整体供需极其平稳",\n                "inventory_write_down_risk": "高端精密五金工具无保质期过时风险，跌价拨备率常年稳定在 2% 以下"'
    ),
    (
        '"inventory_cycle_position": "正处于英伟达 Hopper 向量产 Blackwell 架构切换窗口期，在制品与高性能 GPU 备料充沛"',
        '"inventory_cycle_position": "正处于英伟达 Hopper 向量产 Blackwell 架构切换窗口期，在制品与高性能 GPU 备料充沛",\n                "inventory_write_down_risk": "芯片算力迭代速度极快，需密切跟踪 GPU 架构换代带来的在制品跌价风险"'
    ),
    (
        '"inventory_cycle_position": "果酱、花生酱及袋装咖啡保质期较长，渠道终端动销平稳，库存处于均衡中枢"',
        '"inventory_cycle_position": "果酱、花生酱及袋装咖啡保质期较长，渠道终端动销平稳，库存处于均衡中枢",\n                "inventory_write_down_risk": "快消包装食品保质期监控严密，存货滞销与临期减值率常年低于 1.0%"'
    ),
    (
        '"inventory_cycle_position": "无制造业商品库存，资产形态为长周期钢结构通信铁塔及地面不动产租赁权"',
        '"inventory_cycle_position": "无制造业商品库存，资产形态为长周期钢结构通信铁塔及地面不动产租赁权",\n                "inventory_write_down_risk": "纯数字基础设施与铁塔不动产租赁，无实体存货跌价风险"'
    ),
    (
        '"inventory_cycle_position": "造纸与包装行业经历去库存后触底回升，北美与欧洲纸箱出货量稳步复苏"',
        '"inventory_cycle_position": "造纸与包装行业经历去库存后触底回升，北美与欧洲纸箱出货量稳步复苏",\n                "inventory_write_down_risk": "原纸与瓦楞箱板为大宗工业标准品，回收循环率高，存货减值风险极低"'
    ),
    (
        '"inventory_cycle_position": "自 3M 分拆后完成供应链独立化，全球医疗耗材与牙科诊所备料进入稳态运营"',
        '"inventory_cycle_position": "自 3M 分拆后完成供应链独立化，全球医疗耗材与牙科诊所备料进入稳态运营",\n                "inventory_write_down_risk": "无菌医用耗材与齿科树脂有效期管理规范，存货跌价拨备率保持在 1.8% 以内"'
    ),
]

for orig, repl in replacements:
    if orig in text:
        text = text.replace(orig, repl)
        print("Replaced:", orig[:40])
    else:
        print("NOT FOUND:", orig[:40])

p.write_text(text, encoding="utf-8")
print("Done writing batch 26 update.")
