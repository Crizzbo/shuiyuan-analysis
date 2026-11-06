#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/build_knowledge_graph.py

根据系统设计书、41个行业深度研报、商业模式字典与指标目录，
自动抽取构建强类型、图拓扑化、机器自验证的单一事实来源知识图谱底账：
`knowledge/graph/knowledge_graph.json`。
"""

import json
import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent

# 1. 产业链上下游核心供应映射（有向拓扑边: source 供应给 target）
SUPPLY_CHAIN_EDGES = [
    # 基础材料与能源向上中游供给
    {"source": "mining", "target": "chemicals", "mechanism": "提供硫磺、磷矿石与基础金属矿原料"},
    {"source": "mining", "target": "hardware", "mechanism": "提供高纯阴极铜、金与稀贵金属导电材料"},
    {"source": "mining", "target": "building_products", "mechanism": "提供铁矿石与骨料用于水泥钢材冶炼"},
    {"source": "oil_gas", "target": "midstream", "mechanism": "原油天然气管输交割"},
    {"source": "oil_gas", "target": "chemicals", "mechanism": "提供轻烃乙烷与石脑油裂解原料"},
    {"source": "midstream", "target": "chemicals", "mechanism": "提供乙烷/丙烷长输管网直供"},
    {"source": "midstream", "target": "utilities", "mechanism": "向燃气电厂输送管道天然气基荷燃料"},
    {"source": "energy_services", "target": "oil_gas", "mechanism": "提供定向钻井与高压压裂压裂车组技术服务"},
    {"source": "chemicals", "target": "pharmaceuticals", "mechanism": "提供原料药 API 基础化学中间体"},
    {"source": "chemicals", "target": "packaging", "mechanism": "提供 PET 树脂与聚乙烯塑料母粒"},
    {"source": "chemicals", "target": "automobiles", "mechanism": "提供工程塑料、合成橡胶与动力电池电解液"},
    {"source": "chemicals", "target": "semiconductors", "mechanism": "提供超纯电子级双氧水、光刻胶与特种气体"},
    {"source": "packaging", "target": "food_beverage", "mechanism": "提供无菌两片铝罐与无菌纸包装盒"},
    {"source": "packaging", "target": "household_personal", "mechanism": "提供日化洗护高阻隔泵头与包装瓶"},
    {"source": "packaging", "target": "retail_ecommerce", "mechanism": "提供瓦楞纸箱与环保物流包装耗材"},

    # 科技与芯片产业链
    {"source": "semi_equipment", "target": "semiconductors", "mechanism": "提供 EUV 光刻机、等离子薄膜沉积与刻蚀机台"},
    {"source": "semiconductors", "target": "hardware", "mechanism": "提供 AI 算力 GPU、主控芯片、基带与存储颗粒"},
    {"source": "semiconductors", "target": "automobiles", "mechanism": "提供智能座舱芯片、自动驾驶算力芯片与碳化硅功率模块"},
    {"source": "hardware", "target": "digital_platforms", "mechanism": "提供 AI 超算高密液冷服务器机架与 800G 高速以太网交换机"},
    {"source": "hardware", "target": "telecom", "mechanism": "提供 5G 宏基站 AAU、室分系统与核心网路由器"},
    {"source": "software", "target": "it_services", "mechanism": "提供云平台底座与 SaaS 记录系统软件产品授权"},
    {"source": "it_services", "target": "banks", "mechanism": "提供核心账务系统云原生重构与数字化战略咨询"},
    {"source": "digital_platforms", "target": "retail_ecommerce", "mechanism": "提供高意向搜索与社交信息流广告转化闭环"},
    {"source": "telecom", "target": "digital_platforms", "mechanism": "提供长途光纤骨干传输与移动无线通信网络接入"},

    # 公用事业与工业基建
    {"source": "merchant_power", "target": "digital_platforms", "mechanism": "通过 20 年长约 PPA 专供数据中心 24/7 零碳核电基荷"},
    {"source": "regulated_utilities", "target": "machinery", "mechanism": "提供高可靠电网输配动力电源"},
    {"source": "machinery", "target": "mining", "mechanism": "提供重型露天采矿卡车与超大型挖掘设备"},
    {"source": "machinery", "target": "aerospace_defense", "mechanism": "提供高精度五轴数控机床与航空特种锻压机"},
    {"source": "aerospace_defense", "target": "transportation", "mechanism": "提供商用干线客机与航空发动机备件服务"},
    {"source": "building_products", "target": "equity_reit", "mechanism": "提供现代高标仓与数据中心建筑结构构件"},
    {"source": "equity_reit", "target": "retail_ecommerce", "mechanism": "提供核心枢纽港口高标物流仓储租赁"},
    {"source": "commercial_services", "target": "real_estate_services", "mechanism": "提供综合设施固体危险废物环保清运"},

    # 金融与消费流通
    {"source": "banks", "target": "equity_reit", "mechanism": "提供商业不动产抵押贷款与银团信贷支持"},
    {"source": "insurance", "target": "transportation", "mechanism": "提供航空货运、海运船体与重卡车辆综合险保单保障"},
    {"source": "payments", "target": "retail_ecommerce", "mechanism": "提供全渠道线上收单网关与跨国卡组织双边结算网络"},
    {"source": "staples_retail", "target": "food_beverage", "mechanism": "提供全美与全球实体货架排他性陈列渠道"},
    {"source": "health_services", "target": "managed_care", "mechanism": "作为定点医疗机构向医保会员提供住院与手术诊疗服务"},
    {"source": "pharmaceuticals", "target": "health_services", "mechanism": "向医院与诊所供应原研创新处方药与靶向生物药"},

    # 宏观传导补齐：消除产业链孤岛（餐饮、文旅、耐用品、烟草、生科、器械、资管、互娱）
    {"source": "food_beverage", "target": "restaurants", "mechanism": "提供肉类蛋白、乳品、食用油脂与预制食材原料底料"},
    {"source": "packaging", "target": "restaurants", "mechanism": "提供食品级降解餐盒、冷热饮杯与外卖安全密封耗材"},
    {"source": "transportation", "target": "travel_leisure", "mechanism": "通过民航航线与地面干线交通输送跨国游客流与商务客流"},
    {"source": "digital_platforms", "target": "travel_leisure", "mechanism": "提供 OTA 聚合预订、酒店直连分销与高价值旅游内容流量闭环"},
    {"source": "mining", "target": "housing_durables", "mechanism": "提供轻量化铝合金挤压型材、不锈钢板与精密五金铜管"},
    {"source": "chemicals", "target": "housing_durables", "mechanism": "提供环保聚氨酯保温发泡料、工程塑料粒子与功能涂料"},
    {"source": "packaging", "target": "tobacco", "mechanism": "提供高阻隔内衬铝箔、防伪特种纸烟标与瓦楞外箱耗材"},
    {"source": "food_beverage", "target": "tobacco", "mechanism": "提供高等级醇化烟叶、天然食用香精香料与甘油保润剂"},
    {"source": "biotech", "target": "pharmaceuticals", "mechanism": "向成熟跨国大药企转让首创 FIC 候选分子与全球临床商业化授权"},
    {"source": "semiconductors", "target": "medical_devices", "mechanism": "提供高灵敏度超声传感器、医学影像高算力 DSP 与专用 MCU 芯片"},
    {"source": "chemicals", "target": "medical_devices", "mechanism": "提供医用级高刚度 PEEK 聚合物、医用硅胶与生物相容性材料"},
    {"source": "banks", "target": "asset_management", "mechanism": "提供公募与私募基金全额第三方资产托管、大额拆借做市与清算网络"},
    {"source": "digital_platforms", "target": "media_entertainment", "mechanism": "提供高并发短视频流媒体云分发平台与数字文娱内容流量放大器"},
    {"source": "semiconductors", "target": "media_entertainment", "mechanism": "提供专业级实时光线追踪 GPU 芯片与端侧 3D 图形渲染硬件加速器"}
]

# 行业标准别名归一化（将 md 文件名映射到 industries.json 官方 ID）
ID_NORM_MAP = {
    "automobiles": "autos",
    "consumer_durables": "housing_durables",
    "retail_ecommerce": "retail",
    "leisure_services": "travel_leisure",
    "pharmaceuticals": "pharma",
    "machinery": "capital_goods",
    "transportation": "transport_logistics",
    "commercial_services": "business_services",
    "building_products": "construction",
}

# 2. 行业与功能设计书映射关系表 (统一以 industries.json 官方 ID 为准)
INDUSTRY_SPEC_MAPPINGS = {
    "software": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.SoftwareStrategy"},
    "semiconductors": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.SemiconductorStrategy"},
    "semi_equipment": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.SemiEquipmentStrategy"},
    "hardware": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.HardwareStrategy"},
    "it_services": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.ITServicesStrategy"},
    "banks": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.BanksStrategy"},
    "insurance": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.InsuranceStrategy"},
    "asset_management": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.AssetManagementStrategy"},
    "payments": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.PaymentsStrategy"},
    "pharma": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.PharmaStrategy"},
    "pharmaceuticals": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.PharmaStrategy"},
    "biotech": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.BiotechStrategy"},
    "medical_devices": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.MedTechStrategy"},
    "health_services": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.HealthServicesStrategy"},
    "managed_care": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.ManagedCareStrategy"},
    "autos": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.AutosStrategy"},
    "automobiles": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.AutosStrategy"},
    "housing_durables": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.ConsumerDurablesStrategy"},
    "consumer_durables": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.ConsumerDurablesStrategy"},
    "restaurants": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.RestaurantsStrategy"},
    "retail": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.RetailEcommerceStrategy"},
    "retail_ecommerce": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.RetailEcommerceStrategy"},
    "travel_leisure": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.LeisureServicesStrategy"},
    "leisure_services": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.LeisureServicesStrategy"},
    "food_beverage": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.FoodBeverageStrategy"},
    "household_personal": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.HouseholdPersonalStrategy"},
    "staples_retail": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.StaplesRetailStrategy"},
    "tobacco": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.TobaccoStrategy"},
    "aerospace_defense": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.AerospaceDefenseStrategy"},
    "capital_goods": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.MachineryStrategy"},
    "machinery": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.MachineryStrategy"},
    "transport_logistics": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.TransportationStrategy"},
    "transportation": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.TransportationStrategy"},
    "business_services": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.CommercialServicesStrategy"},
    "commercial_services": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.CommercialServicesStrategy"},
    "construction": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.BuildingProductsStrategy"},
    "building_products": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.BuildingProductsStrategy"},
    "oil_gas": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.OilGasStrategy"},
    "energy_services": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.EnergyServicesStrategy"},
    "midstream": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.MidstreamStrategy"},
    "chemicals": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.ChemicalsStrategy"},
    "mining": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.MiningStrategy"},
    "packaging": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.PackagingStrategy"},
    "telecom": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.TelecomStrategy"},
    "digital_platforms": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.DigitalPlatformsStrategy"},
    "media_entertainment": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.MediaEntertainmentStrategy"},
    "regulated_utilities": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.RegulatedUtilitiesStrategy"},
    "merchant_power": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.MerchantPowerStrategy"},
    "real_estate_services": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.RealEstateServicesStrategy"},
    "equity_reit": {"spec_doc": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md", "engine": "financial_core.engines.industry_causal_registry.EquityREITStrategy"}
}

# 3. 全系统核心主设计书全息拓扑注册表 (涵盖全盘系统架构、金融计算、研报呈现、资产池调度与测试治理)
SYSTEM_DESIGN_SPECS = [
    {
        "spec_id": "spec_00",
        "spec_number": "00",
        "title": "水源投研系统产品设计总纲与分层工程方法论",
        "doc_path": "docs/00-水源投研系统产品设计总纲与分层工程方法论.md",
        "subsystem": "architecture_foundation",
        "core_features": ["四层架构分工", "金融计算核心纯净性", "单一事实来源SSOT", "零逆向依赖铁律", "四道硬门禁验收"],
        "key_algorithms": ["四层单向解耦法则", "零循环导入检测", "物理隔离原则"],
        "code_bindings": [
            {"module": "financial_core", "file": "financial_core/__init__.py", "description": "底层金融计算核心库"},
            {"module": "financial_reporting", "file": "financial_reporting/__init__.py", "description": "研报呈现与网关层"},
            {"module": "finance_tools", "file": "finance_tools/__init__.py", "description": "工具中继层"},
            {"module": "scripts", "file": "scripts/verify_architecture_integrity.py", "description": "架构合规巡检调度"}
        ],
        "test_bindings": [
            {"file": "scripts/test_financial_core_decoupling.py", "test_class": "TestFinancialCoreDecoupling", "tier": "IT"},
            {"file": "scripts/verify_architecture_integrity.py", "test_class": "ArchitectureIntegrityCheck", "tier": "IT"}
        ],
        "upstream_specs": []
    },
    {
        "spec_id": "spec_00a",
        "spec_number": "00a",
        "title": "买方投研业务场景需求调研与一二期边界划分书",
        "doc_path": "docs/00a-买方投研业务场景需求调研与一二期边界划分书.md",
        "subsystem": "product_requirements",
        "core_features": ["买方四大岗位动线(CIO/策略师/研究员/交易员)", "一二期系统边界划分", "投委会决策业务闭环"],
        "key_algorithms": ["买方动线分工模型"],
        "code_bindings": [],
        "test_bindings": [
            {"file": "scripts/test_canyon_linear_pipeline.py", "test_class": "TestCanyonLinearPipeline", "tier": "UAT"}
        ],
        "upstream_specs": ["spec_00"]
    },
    {
        "spec_id": "spec_00b",
        "spec_number": "00b",
        "title": "买方研报多模态呈现规范与视觉Token设计说明书",
        "doc_path": "docs/00b-买方研报多模态呈现规范与视觉Token设计说明书.md",
        "subsystem": "financial_reporting",
        "core_features": ["买方机构级视觉Token设计", "A4矢量HTML印刷规范", "5-Sheet Excel纯净配色", "物理消除全部Emoji与非人类符号"],
        "key_algorithms": ["自然中文商业语义映射", "买方墨绿/深红/炭黑配色Token"],
        "code_bindings": [
            {"module": "financial_reporting.excel_styler", "file": "financial_reporting/excel_styler.py", "description": "买方Excel样式与Token定义器"},
            {"module": "financial_reporting.sepa_card_renderer", "file": "financial_reporting/sepa_card_renderer.py", "description": "买方富文本卡片渲染器"}
        ],
        "test_bindings": [
            {"file": "scripts/test_financial_reporting.py", "test_class": "ReportingTests", "tier": "FT"},
            {"file": "scripts/test_sepa_card_renderer.py", "test_class": "TestSepaCardRenderer", "tier": "IT"}
        ],
        "upstream_specs": ["spec_00"]
    },
    {
        "spec_id": "spec_01",
        "spec_number": "01",
        "title": "系统范围与总体框架",
        "doc_path": "docs/01-项目范围与总体框架.md",
        "subsystem": "architecture_foundation",
        "core_features": ["纯离线日结快照模式", "本地证据链只追加不可篡改", "密码学哈希账本防伪"],
        "key_algorithms": ["SHA-256 密码学时间链条"],
        "code_bindings": [
            {"module": "financial_core.engines.prediction_ledger", "file": "financial_core/engines/prediction_ledger.py", "description": "不可篡改对账账本"}
        ],
        "test_bindings": [
            {"file": "scripts/test_research_contract.py", "test_class": "ResearchContractTests", "tier": "IT"}
        ],
        "upstream_specs": ["spec_00"]
    },
    {
        "spec_id": "spec_02",
        "spec_number": "02",
        "title": "行业分类与知识库结构",
        "doc_path": "docs/02-行业分类与知识库结构.md",
        "subsystem": "knowledge_repository",
        "core_features": ["11板块41行业三层分类树", "商业模式与驱动指标绑定", "行业知识底账结构设计"],
        "key_algorithms": ["三层分类拓扑匹配", "行业规则动态加载"],
        "code_bindings": [
            {"module": "financial_core.engines.knowledge_repository", "file": "financial_core/engines/knowledge_repository.py", "description": "知识库仓库门面"},
            {"module": "financial_core.engines.knowledge_graph_engine", "file": "financial_core/engines/knowledge_graph_engine.py", "description": "知识图谱与边界核验引擎"}
        ],
        "test_bindings": [
            {"file": "scripts/test_knowledge_graph_engine.py", "test_class": "KnowledgeGraphEngineTests", "tier": "UT"},
            {"file": "scripts/validate_knowledge_structure.py", "test_class": "KnowledgeStructureValidation", "tier": "IT"},
            {"file": "scripts/test_industry_mapping.py", "test_class": "MappingTests", "tier": "UT"}
        ],
        "upstream_specs": ["spec_01"]
    },
    {
        "spec_id": "spec_03",
        "spec_number": "03",
        "title": "六步分析Schema与流程规则",
        "doc_path": "docs/03-六步分析Schema与流程规则.md",
        "subsystem": "research_contract",
        "core_features": ["六步法投研流(业务/事实/指标/估值/反证/决策)", "步骤前置强依赖校验", "门禁状态机"],
        "key_algorithms": ["单向六步依赖判定", "步骤降级阻断"],
        "code_bindings": [
            {"module": "financial_core.contracts", "file": "financial_core/contracts.py", "description": "投研数据契约"}
        ],
        "test_bindings": [
            {"file": "scripts/test_research_contract.py", "test_class": "ResearchContractTests", "tier": "IT"}
        ],
        "upstream_specs": ["spec_01"]
    },
    {
        "spec_id": "spec_04",
        "spec_number": "04",
        "title": "数据与证据管理系统",
        "doc_path": "docs/04-数据与证据管理.md",
        "subsystem": "data_governance",
        "core_features": ["证据目录只追加不可手改", "时间单调性保障", "正式财务事实登记与指纹审计"],
        "key_algorithms": ["不可变账本验签", "前视信息防穿越时钟判定"],
        "code_bindings": [
            {"module": "financial_core.engines.prediction_ledger", "file": "financial_core/engines/prediction_ledger.py", "description": "密码学对账账本"}
        ],
        "test_bindings": [
            {"file": "scripts/test_data_store.py", "test_class": "DataStoreTests", "tier": "IT"},
            {"file": "scripts/test_financial_registry.py", "test_class": "RegistryTests", "tier": "UT"},
            {"file": "scripts/test_research_time_contract.py", "test_class": "TimeContractTests", "tier": "IT"}
        ],
        "upstream_specs": ["spec_01"]
    },
    {
        "spec_id": "spec_06",
        "spec_number": "06",
        "title": "行业知识契约与软件样板",
        "doc_path": "docs/06-行业知识契约与软件样板.md",
        "subsystem": "knowledge_repository",
        "core_features": ["行业知识标准化契约", "法定核心反证逻辑规范", "估值模型强绑定约束"],
        "key_algorithms": ["买方证伪触发判定"],
        "code_bindings": [
            {"module": "financial_core.engines.knowledge_repository", "file": "financial_core/engines/knowledge_repository.py", "description": "知识库仓库门面"}
        ],
        "test_bindings": [
            {"file": "scripts/test_industry_mapping.py", "test_class": "MappingTests", "tier": "UT"}
        ],
        "upstream_specs": ["spec_02", "spec_03"]
    },
    {
        "spec_id": "spec_07",
        "spec_number": "07",
        "title": "开源金融计算库选型与计算架构",
        "doc_path": "docs/07-开源金融计算库选型与缺口.md",
        "subsystem": "financial_core",
        "core_features": ["第三方开源金融数学库选型边界", "自研金融核心补缺", "纯净计算无外部依赖"],
        "key_algorithms": ["自研金融数学除零除负防御", "极值下界收敛"],
        "code_bindings": [
            {"module": "financial_core.engines", "file": "financial_core/engines/__init__.py", "description": "底层算法引擎集合"}
        ],
        "test_bindings": [
            {"file": "scripts/test_finance_tools.py", "test_class": "FinanceTests", "tier": "UT"}
        ],
        "upstream_specs": ["spec_00"]
    },
    {
        "spec_id": "spec_08",
        "spec_number": "08",
        "title": "全栈工程命名架构与状态空间规范",
        "doc_path": "docs/08-全栈工程命名架构与状态空间规范.md",
        "subsystem": "architecture_foundation",
        "core_features": ["状态机枚举定义", "自然中文命名规范", "去工程符号化与代码代号消除"],
        "key_algorithms": ["有限状态机跳转合法性验证"],
        "code_bindings": [
            {"module": "financial_core.contracts", "file": "financial_core/contracts.py", "description": "数据契约与状态空间"}
        ],
        "test_bindings": [
            {"file": "scripts/test_sepa_buy_signal_engine.py", "test_class": "TestSepaBuySignalEngine", "tier": "UT"}
        ],
        "upstream_specs": ["spec_00"]
    },
    {
        "spec_id": "spec_09",
        "spec_number": "09",
        "title": "金融核心计算工具功能设计",
        "doc_path": "docs/09-金融计算工具功能设计.md",
        "subsystem": "financial_core",
        "core_features": ["多阶段情景现金流折现(DCF)", "杜邦三阶段与五阶段拆解", "巴菲特所有者收益(Owner Earnings)", "格雷厄姆净现值(NCAV)"],
        "key_algorithms": ["杜邦ROE分解算法", "有形账面价值TBV计算", "净现金底线测算"],
        "code_bindings": [
            {"module": "financial_core.engines.business_quality_and_moat_engine", "file": "financial_core/engines/business_quality_and_moat_engine.py", "description": "商业血肉与所有者收益引擎"},
            {"module": "financial_core.engines.integrated_three_statement_engine", "file": "financial_core/engines/integrated_three_statement_engine.py", "description": "三表一体化预测引擎"}
        ],
        "test_bindings": [
            {"file": "scripts/test_finance_tools.py", "test_class": "FinanceTests", "tier": "UT"},
            {"file": "scripts/test_business_quality_engine.py", "test_class": "TestBusinessQualityAndMoatEngine", "tier": "UT"},
            {"file": "scripts/test_advanced_analytics.py", "test_class": "TestAdvancedAnalytics", "tier": "UT"},
            {"file": "scripts/test_strong_constrained_valuation.py", "test_class": "TestStronglyConstrainedValuation", "tier": "UT"}
        ],
        "upstream_specs": ["spec_07"]
    },
    {
        "spec_id": "spec_09b",
        "spec_number": "09b",
        "title": "高阶金融定价与风控算法子说明书",
        "doc_path": "docs/09b-高阶金融定价与风控算法子说明书.md",
        "subsystem": "financial_core",
        "core_features": ["美式期权二叉树定价(CRR)", "蒙特卡洛DCF估值分布", "默顿(Merton)信用违约距离", "波动率曲面与希腊字母", "投资组合VaR在险价值"],
        "key_algorithms": ["CRR美式期权早熟倒推", "Durrleman无套利波动率偏斜", "Merton结构化违约距离", "历史模拟法与参数法VaR"],
        "code_bindings": [
            {"module": "financial_core.engines.american_option_tree_engine", "file": "financial_core/engines/american_option_tree_engine.py", "description": "美式期权二叉树引擎"},
            {"module": "financial_core.engines.monte_carlo_engine", "file": "financial_core/engines/monte_carlo_engine.py", "description": "蒙特卡洛DCF引擎"},
            {"module": "financial_core.engines.credit_risk_engine", "file": "financial_core/engines/credit_risk_engine.py", "description": "信用风险与偿债能力引擎"},
            {"module": "financial_core.engines.volatility_surface_engine", "file": "financial_core/engines/volatility_surface_engine.py", "description": "波动率曲面引擎"},
            {"module": "financial_core.engines.portfolio_risk_engine", "file": "financial_core/engines/portfolio_risk_engine.py", "description": "投资组合风险与VaR引擎"}
        ],
        "test_bindings": [
            {"file": "scripts/test_phase3a_engines.py", "test_class": "TestPhase3AEngines", "tier": "IT"},
            {"file": "scripts/test_phase3b_engines.py", "test_class": "TestPhase3BEngines", "tier": "UT"}
        ],
        "upstream_specs": ["spec_09"]
    },
    {
        "spec_id": "spec_10",
        "spec_number": "10",
        "title": "行业财务指标批量流水线执行",
        "doc_path": "docs/10-指标计算接入与行业样板.md",
        "subsystem": "financial_core",
        "core_features": ["行业专属财务指标批量提取", "除零除负分母阻断", "期间口径对齐与单位缩放"],
        "key_algorithms": ["指标公式安全求值", "量纲自动化转换"],
        "code_bindings": [
            {"module": "financial_reporting.generic_metrics", "file": "financial_reporting/generic_metrics.py", "description": "通用与特定财务指标计算"}
        ],
        "test_bindings": [
            {"file": "scripts/test_metric_pipeline.py", "test_class": "MetricTests", "tier": "FT"},
            {"file": "scripts/test_generic_metrics.py", "test_class": "GenericFinancialMetricsTests", "tier": "UT"}
        ],
        "upstream_specs": ["spec_09", "spec_06"]
    },
    {
        "spec_id": "spec_12",
        "spec_number": "12",
        "title": "免费数据接入网关与免配置取数",
        "doc_path": "docs/12-免费数据接入功能设计.md",
        "subsystem": "data_governance",
        "core_features": ["公开官方监管数据摄入(SEC/EDINET/J-Quants)", "配额持久化与限流重试", "路径遍历越界安全防御"],
        "key_algorithms": ["安全凭证过滤", "零配置公开接口供给"],
        "code_bindings": [
            {"module": "financial_reporting.data_collection_gateway", "file": "financial_reporting/data_collection_gateway.py", "description": "统一数据收集网关"}
        ],
        "test_bindings": [
            {"file": "scripts/test_data_ingestion.py", "test_class": "IngestionTests", "tier": "UT"},
            {"file": "scripts/test_data_collection_gateway.py", "test_class": "TestDataCollectionGateway", "tier": "IT"}
        ],
        "upstream_specs": ["spec_04"]
    },
    {
        "spec_id": "spec_13",
        "spec_number": "13",
        "title": "免配置公开来源与AI浏览器官方补数",
        "doc_path": "docs/13-免配置来源与AI浏览器补数.md",
        "subsystem": "data_governance",
        "core_features": ["AI浏览器定向补数清单生成", "官方监管回执校验", "禁止无序自动化网络爬虫"],
        "key_algorithms": ["缺失数据清单自动生成", "下载回执哈希核对"],
        "code_bindings": [
            {"module": "financial_reporting.market_snapshot", "file": "financial_reporting/market_snapshot.py", "description": "市场快照与定向补数比对器"}
        ],
        "test_bindings": [
            {"file": "scripts/test_data_ingestion.py", "test_class": "IngestionTests", "tier": "UT"}
        ],
        "upstream_specs": ["spec_12"]
    },
    {
        "spec_id": "spec_14",
        "spec_number": "14",
        "title": "官方财报清洗标准化与刚性平账自检",
        "doc_path": "docs/14-财报解析标准化与计算功能设计.md",
        "subsystem": "financial_core",
        "core_features": ["三准则科目归一化(J-GAAP/US-GAAP/IFRS)", "资产负债刚性平账自检(A=L+E)", "三表自动跨表勾稽", "微小舍入误差智能容差", "统一财报防腐门面"],
        "key_algorithms": ["资产负债恒等式平衡检验", "非标字符串清洗映射", "防腐数据模型归一化"],
        "code_bindings": [
            {"module": "financial_core.engines.filing_mapper", "file": "financial_core/engines/filing_mapper.py", "description": "官方财报标准映射与平账引擎"},
            {"module": "financial_core.engines.financial_statement_facade", "file": "financial_core/engines/financial_statement_facade.py", "description": "企业财报防腐中继门面"}
        ],
        "test_bindings": [
            {"file": "scripts/test_filing_mapper_balance.py", "test_class": "TestFilingMapperBalance", "tier": "IT"},
            {"file": "scripts/test_financial_statement_facade.py", "test_class": "TestFinancialStatementFacade", "tier": "UT"},
            {"file": "scripts/test_financial_reporting.py", "test_class": "ReportingTests", "tier": "UT"}
        ],
        "upstream_specs": ["spec_04", "spec_12"]
    },
    {
        "spec_id": "spec_14b",
        "spec_number": "14b",
        "title": "数据转换、汇率清洗与异常点拦截",
        "doc_path": "docs/14b-数据转换与汇率清洗程序设计文档.md",
        "subsystem": "data_governance",
        "core_features": ["多币种汇率统一折算(USD/JPY/CNY)", "突发异常数据点剔除", "时间窗口平滑滤波"],
        "key_algorithms": ["汇率动态加权平价折算", "孤立极值点滤波算法"],
        "code_bindings": [
            {"module": "financial_reporting.data_converter", "file": "financial_reporting/data_converter.py", "description": "数据清洗与汇率转换器"}
        ],
        "test_bindings": [
            {"file": "scripts/test_data_converter.py", "test_class": "DataConverterTests", "tier": "IT"}
        ],
        "upstream_specs": ["spec_14"]
    },
    {
        "spec_id": "spec_17",
        "spec_number": "17",
        "title": "通用财务指标类与行业特定指标架构",
        "doc_path": "docs/17-通用财务指标类与行业特定指标架构设计文档.md",
        "subsystem": "financial_core",
        "core_features": ["通用财务指标基类抽象", "行业专属指标策略解耦", "指标计算零硬编码"],
        "key_algorithms": ["面向对象指标继承与重载模式"],
        "code_bindings": [
            {"module": "financial_reporting.generic_metrics", "file": "financial_reporting/generic_metrics.py", "description": "通用与特定财务指标计算"}
        ],
        "test_bindings": [
            {"file": "scripts/test_generic_metrics.py", "test_class": "GenericFinancialMetricsTests", "tier": "UT"}
        ],
        "upstream_specs": ["spec_14", "spec_06"]
    },
    {
        "spec_id": "spec_18",
        "spec_number": "18",
        "title": "跨市场美日股核心标的归档与分析规范",
        "doc_path": "docs/18-美股与日股核心标的归档与分析规范设计文档.md",
        "subsystem": "tiered_universe",
        "core_features": ["美股SEC CIK与日股东证代码双目录底账", "全息标的元数据索引", "跨国公司主营业务分类对齐"],
        "key_algorithms": ["跨交易所证券身份识别与映射"],
        "code_bindings": [
            {"module": "financial_core.engines.sec_edgar_collector", "file": "financial_core/engines/sec_edgar_collector.py", "description": "SEC官方标的归档器"},
            {"module": "financial_core.engines.tiered_universe_manager", "file": "financial_core/engines/tiered_universe_manager.py", "description": "分级资产池管理器"}
        ],
        "test_bindings": [
            {"file": "scripts/test_data_store.py", "test_class": "DataStoreTests", "tier": "IT"}
        ],
        "upstream_specs": ["spec_14", "spec_02"]
    },
    {
        "spec_id": "spec_19",
        "spec_number": "19",
        "title": "每日大盘研报工程化规范与生成程序",
        "doc_path": "docs/19-每日大盘研报工程化规范与生成程序设计文档.md",
        "subsystem": "financial_reporting",
        "core_features": ["美股日股宏观流动性全息透视", "恐慌指数VIX与资金流向监控", "期权大单PCR异动", "重点推荐股票独立富文本卡片"],
        "key_algorithms": ["宏观流动性压力合成指数", "期权PCR大单偏斜算法"],
        "code_bindings": [
            {"module": "financial_reporting.daily_briefing_engine", "file": "financial_reporting/daily_briefing_engine.py", "description": "每日大盘研报生成引擎"}
        ],
        "test_bindings": [
            {"file": "scripts/test_daily_briefing.py", "test_class": "DailyBriefingTests", "tier": "FT"}
        ],
        "upstream_specs": ["spec_00b", "spec_09b", "spec_18"]
    },
    {
        "spec_id": "spec_21",
        "spec_number": "21",
        "title": "公司深度投研档案全息生成与契约设计",
        "doc_path": "docs/21-公司深度档案全息生成与契约设计文档.md",
        "subsystem": "financial_reporting",
        "core_features": ["官方三表全息底稿穿透", "财报质量解读与法证五刀", "净现金与利息红利", "库存周期DIO", "上下游核心供应商集中度", "长短期情景DCF估值"],
        "key_algorithms": ["法证五刀造假排查算法", "存货周转天数DIO分解", "情景触发买点靶心算法"],
        "code_bindings": [
            {"module": "financial_reporting.ai_dossier_synthesizer", "file": "financial_reporting/ai_dossier_synthesizer.py", "description": "AI深度档案合成器"}
        ],
        "test_bindings": [
            {"file": "scripts/test_financial_reporting.py", "test_class": "ReportingTests", "tier": "FT"},
            {"file": "scripts/test_ai_research_agent.py", "test_class": "TestAIResearchAgent", "tier": "FT"}
        ],
        "upstream_specs": ["spec_14", "spec_09"]
    },
    {
        "spec_id": "spec_22",
        "spec_number": "22",
        "title": "全球核心指数ETF与黄金大宗商品研究体系",
        "doc_path": "docs/22-核心指数ETF与黄金大宗商品研究体系设计文档.md",
        "subsystem": "financial_core",
        "core_features": ["ETF持仓权重穿透重叠度算法", "风格因子暴露分析", "10Y TIPS实际利率黄金定价", "金矿股经营与财务双重杠杆传导"],
        "key_algorithms": ["ETF成份重合度算法", "实际利率-美元指数黄金宏观定价模型"],
        "code_bindings": [
            {"module": "financial_core.engines.cross_asset_engine", "file": "financial_core/engines/cross_asset_engine.py", "description": "跨资产估值引擎"}
        ],
        "test_bindings": [
            {"file": "scripts/test_etf_and_commodity.py", "test_class": "TestETFAndCommodity", "tier": "UT"}
        ],
        "upstream_specs": ["spec_09"]
    },
    {
        "spec_id": "spec_23",
        "spec_number": "23",
        "title": "微观基础宏观传导与制度风险引擎",
        "doc_path": "docs/23-微观基础宏观传导与制度风险引擎设计文档.md",
        "subsystem": "financial_core",
        "core_features": ["伍德福德前瞻指引与泰勒规则", "霍尔贴现摩擦与跨期消费", "阿西莫格鲁产权与制度风险折现", "阿吉翁内生增长与创造性破坏"],
        "key_algorithms": ["Woodford泰勒规则指引算法", "Hall消费资本摩擦贴现", "Acemoglu征收风险贴现率惩罚", "Aghion前沿创新更替概率"],
        "code_bindings": [
            {"module": "financial_core.engines.micro_founded_macro_engine", "file": "financial_core/engines/micro_founded_macro_engine.py", "description": "微观基础宏观综合引擎"},
            {"module": "financial_core.engines.woodford_forward_guidance_engine", "file": "financial_core/engines/woodford_forward_guidance_engine.py", "description": "前瞻指引引擎"},
            {"module": "financial_core.engines.hall_discount_friction_engine", "file": "financial_core/engines/hall_discount_friction_engine.py", "description": "贴现摩擦引擎"},
            {"module": "financial_core.engines.acemoglu_institutional_risk_engine", "file": "financial_core/engines/acemoglu_institutional_risk_engine.py", "description": "制度风险引擎"},
            {"module": "financial_core.engines.aghion_creative_destruction_engine", "file": "financial_core/engines/aghion_creative_destruction_engine.py", "description": "创造性破坏引擎"}
        ],
        "test_bindings": [
            {"file": "scripts/test_micro_founded_macro.py", "test_class": "TestMicroFoundedMacroArchitecture", "tier": "UT"}
        ],
        "upstream_specs": ["spec_09"]
    },
    {
        "spec_id": "spec_24",
        "spec_number": "24",
        "title": "全球宏观生产总量与企业微观增加值闭环核算",
        "doc_path": "docs/24-全球宏观生产总量与微观增加值闭环核算设计文档.md",
        "subsystem": "financial_core",
        "core_features": ["世界生产总量恒等式", "全球投入产出表WIOD关联", "企业增加值桥接核算", "要素收入分配模型"],
        "key_algorithms": ["Leontief投入产出闭环逆矩阵", "增加值微观拆解恒等式"],
        "code_bindings": [
            {"module": "financial_core.engines.world_production_aggregate_engine", "file": "financial_core/engines/world_production_aggregate_engine.py", "description": "世界生产总量引擎"},
            {"module": "financial_core.engines.global_input_output_engine", "file": "financial_core/engines/global_input_output_engine.py", "description": "全球投入产出引擎"},
            {"module": "financial_core.engines.firm_value_added_bridge_engine", "file": "financial_core/engines/firm_value_added_bridge_engine.py", "description": "企业增加值桥接引擎"},
            {"module": "financial_core.engines.factor_income_distribution_engine", "file": "financial_core/engines/factor_income_distribution_engine.py", "description": "要素收入分配引擎"}
        ],
        "test_bindings": [
            {"file": "scripts/test_world_financial_system.py", "test_class": "TestWorldFinancialSystem", "tier": "IT"}
        ],
        "upstream_specs": ["spec_23", "spec_14"]
    },
    {
        "spec_id": "spec_25",
        "spec_number": "25",
        "title": "市场自适应参数体系与买方量化因果推导网络",
        "doc_path": "docs/25-市场自适应参数体系与买方量化因果推导网络设计文档.md",
        "subsystem": "financial_core",
        "core_features": ["41行业因果策略注册表", "价格异动归因与经营杠杆分析", "业绩双超(Double Beat)修正动量", "三层行业映射桥"],
        "key_algorithms": ["三层因果推导拓扑算法", "异动冲击四刀归因(指引/经营杠杆/稀释压制/做市商Gamma)"],
        "code_bindings": [
            {"module": "financial_core.engines.market_adaptive_params", "file": "financial_core/engines/market_adaptive_params.py", "description": "自适应参数中枢"},
            {"module": "financial_core.engines.causal_inference_engine", "file": "financial_core/engines/causal_inference_engine.py", "description": "量化因果推导引擎"},
            {"module": "financial_core.engines.industry_causal_registry", "file": "financial_core/engines/industry_causal_registry.py", "description": "41行业因果策略注册表"},
            {"module": "financial_core.engines.price_shock_attribution_engine", "file": "financial_core/engines/price_shock_attribution_engine.py", "description": "价格异动因果归因引擎"},
            {"module": "financial_core.engines.industry_taxonomy_bridge", "file": "financial_core/engines/industry_taxonomy_bridge.py", "description": "三层行业映射桥"}
        ],
        "test_bindings": [
            {"file": "scripts/test_market_adaptive_and_causal_network.py", "test_class": "TestMarketAdaptiveAndCausalNetwork", "tier": "IT"},
            {"file": "scripts/test_price_shock_attribution_engine.py", "test_class": "TestPriceShockAttributionEngine", "tier": "UT"},
            {"file": "scripts/test_industry_taxonomy_and_causal_bridge.py", "test_class": "TestIndustryTaxonomyAndCausalBridge", "tier": "IT"}
        ],
        "upstream_specs": ["spec_02", "spec_09", "spec_23"]
    },
    {
        "spec_id": "spec_26",
        "spec_number": "26",
        "title": "千家全量资产池批量平账与流式建档技术设计",
        "doc_path": "docs/26-千家全量资产池批量平账与流式建档技术设计文档.md",
        "subsystem": "tiered_universe",
        "core_features": ["美股SEC与东证数千家企业全量资产池", "分级架构(Tier 0/1/2/3)", "分批切片批处理(50-100家/批)", "原子断点续传与并发防锁", "流式边渲染边上传Google Drive"],
        "key_algorithms": ["批次切片状态机算法", "原子文件锁并发控制"],
        "code_bindings": [
            {"module": "financial_core.engines.tiered_universe_manager", "file": "financial_core/engines/tiered_universe_manager.py", "description": "分级资产池管理器"},
            {"module": "financial_core.engines.normalized_reconciliation_engine", "file": "financial_core/engines/normalized_reconciliation_engine.py", "description": "常态化平账引擎与状态机"},
            {"module": "scripts.run_567_universe_batch_pipeline", "file": "scripts/run_567_universe_batch_pipeline.py", "description": "资产池分批执行流水线"}
        ],
        "test_bindings": [
            {"file": "scripts/test_normalized_universe_reconciliation.py", "test_class": "TestNormalizedUniverseReconciliation", "tier": "FT"},
            {"file": "scripts/test_567_universe_batch_pipeline.py", "test_class": "Test567UniverseBatchPipeline", "tier": "FT"}
        ],
        "upstream_specs": ["spec_14", "spec_18"]
    },
    {
        "spec_id": "spec_27",
        "spec_number": "27",
        "title": "买方机构级5-Sheet Excel深度研报建造器",
        "doc_path": "docs/27-买方机构级5-Sheet Excel深度研报建造器技术文档.md",
        "subsystem": "financial_reporting",
        "core_features": ["5张标准工作表(估值决策/官方三表/核心驱动/反证压力/对账复盘)", "openpyxl底层物理级渲染", "冻结窗格与自适应列宽", "绝对零Emoji表情符号"],
        "key_algorithms": ["无模板动态Excel样式构建算法", "金融格式化数值引擎"],
        "code_bindings": [
            {"module": "financial_reporting.excel_dossier_builder", "file": "financial_reporting/excel_dossier_builder.py", "description": "买方5-Sheet工作簿建造器"}
        ],
        "test_bindings": [
            {"file": "scripts/test_financial_reporting.py", "test_class": "ReportingTests", "tier": "FT"}
        ],
        "upstream_specs": ["spec_00b", "spec_21"]
    },
    {
        "spec_id": "spec_28",
        "spec_number": "28",
        "title": "多资产横向拓展流水线与4-Sheet联动工作簿",
        "doc_path": "docs/28-多资产横向拓展流水线与4-Sheet联动工作簿技术文档.md",
        "subsystem": "financial_reporting",
        "core_features": ["股票+ETF+黄金大宗商品多资产横向拓展", "4-Sheet工作簿联动", "跨资产相关性矩阵与对冲仓位计算"],
        "key_algorithms": ["跨资产全天候风险平价对冲算法"],
        "code_bindings": [
            {"module": "financial_core.engines.cross_asset_engine", "file": "financial_core/engines/cross_asset_engine.py", "description": "跨资产估值引擎"},
            {"module": "financial_reporting.excel_multi_asset_builder", "file": "financial_reporting/excel_multi_asset_builder.py", "description": "多资产联动工作簿建造器"}
        ],
        "test_bindings": [
            {"file": "scripts/test_canyon_multi_asset_pipeline.py", "test_class": "TestCanyonMultiAssetPipeline", "tier": "FT"},
            {"file": "scripts/test_etf_and_commodity.py", "test_class": "TestETFAndCommodity", "tier": "UT"}
        ],
        "upstream_specs": ["spec_22", "spec_27"]
    },
    {
        "spec_id": "spec_29",
        "spec_number": "29",
        "title": "AI智能投研代理与深度档案合成器",
        "doc_path": "docs/29-AI智能投研代理与深度档案合成器技术与功能设计文档.md",
        "subsystem": "financial_reporting",
        "core_features": ["深度档案全自动装配与质量控制", "四重逻辑严密校验(自洽/完整/非模版/反证)", "情景触发事件推演"],
        "key_algorithms": ["自然语言投研质量检验与一致性断言"],
        "code_bindings": [
            {"module": "financial_reporting.ai_research_agent", "file": "financial_reporting/ai_research_agent.py", "description": "AI智能投研代理核心"}
        ],
        "test_bindings": [
            {"file": "scripts/test_ai_research_agent.py", "test_class": "TestAIResearchAgent", "tier": "FT"}
        ],
        "upstream_specs": ["spec_21", "spec_25"]
    },
    {
        "spec_id": "spec_30",
        "spec_number": "30",
        "title": "数据治理闭环：AI浏览器定向补数中枢与官方归档SOP",
        "doc_path": "docs/30-数据治理闭环：AI浏览器定向补数中枢与官方归档SOP文档.md",
        "subsystem": "data_governance",
        "core_features": ["数据缺口自动化定向清单输出", "AI浏览器人工核验与官方下载闭环", "数据防伪与证据链完整归档"],
        "key_algorithms": ["官方监管三级核验SOP"],
        "code_bindings": [
            {"module": "financial_reporting.evidence_dossiers", "file": "financial_reporting/evidence_dossiers.py", "description": "数据证据目录与归档管理器"}
        ],
        "test_bindings": [
            {"file": "scripts/test_data_ingestion.py", "test_class": "IngestionTests", "tier": "UT"}
        ],
        "upstream_specs": ["spec_12", "spec_13"]
    },
    {
        "spec_id": "spec_31",
        "spec_number": "31",
        "title": "千家资产池顶层动态雷达与价值洼地主看板",
        "doc_path": "docs/31-千家资产池顶层动态雷达与价值洼地主看板技术文档.md",
        "subsystem": "financial_reporting",
        "core_features": ["千家资产池全景主看板(Master Living Screener)", "超链接物理穿透至个股5-Sheet Excel", "价值洼地综合排序", "深蹲假摔识别"],
        "key_algorithms": ["安全边际多因子加权排序算法", "深蹲假摔形态识别"],
        "code_bindings": [
            {"module": "financial_reporting.excel_master_screener_builder", "file": "financial_reporting/excel_master_screener_builder.py", "description": "主看板建造器"}
        ],
        "test_bindings": [
            {"file": "scripts/test_master_screener.py", "test_class": "TestExcelMasterScreenerBuilder", "tier": "FT"}
        ],
        "upstream_specs": ["spec_26", "spec_27"]
    },
    {
        "spec_id": "spec_32",
        "spec_number": "32",
        "title": "自动化买方投委会决策简报与每日大盘早报联动流水线",
        "doc_path": "docs/32-自动化买方投委会决策简报与每日大盘早报联动流水线技术文档.md",
        "subsystem": "pipeline_orchestration",
        "core_features": ["Canyon单向线性流水线", "收盘快照->平账自检->深度建档->每日大盘->全景看板->投委会简报一键贯通", "端到端自动化调度"],
        "key_algorithms": ["单向流水线状态推进与异常阻断算法"],
        "code_bindings": [
            {"module": "scripts.run_canyon_linear_pipeline", "file": "scripts/run_canyon_linear_pipeline.py", "description": "Canyon单向线性流水线调度"}
        ],
        "test_bindings": [
            {"file": "scripts/test_canyon_linear_pipeline.py", "test_class": "TestCanyonLinearPipeline", "tier": "UAT"}
        ],
        "upstream_specs": ["spec_19", "spec_31"]
    },
    {
        "spec_id": "spec_33",
        "spec_number": "33",
        "title": "米奈尔维尼SEPA买入信号与价格时机引擎",
        "doc_path": "docs/33-米奈尔维尼SEPA买入信号与价格时机引擎产品设计与字段契约规范.md",
        "subsystem": "financial_core",
        "core_features": ["趋势模板Stage 2研判(200日/150日/50日均线)", "VCP波动收缩形态振幅收敛判断", "Pivot枢轴点突破信号", "价格新鲜度门禁解耦"],
        "key_algorithms": ["Minervini趋势模板算法", "VCP收缩波次计算", "无套利枢轴买点识别"],
        "code_bindings": [
            {"module": "financial_core.engines.sepa_buy_signal_engine", "file": "financial_core/engines/sepa_buy_signal_engine.py", "description": "SEPA买入信号引擎"}
        ],
        "test_bindings": [
            {"file": "scripts/test_sepa_buy_signal_engine.py", "test_class": "TestSepaBuySignalEngine", "tier": "UT"},
            {"file": "scripts/test_sepa_card_renderer.py", "test_class": "TestSepaCardRenderer", "tier": "IT"}
        ],
        "upstream_specs": ["spec_08", "spec_09", "spec_25"]
    },
    {
        "spec_id": "spec_34",
        "spec_number": "34",
        "title": "系统全量测试用例清单与四层测试方法全景说明书",
        "doc_path": "docs/34-系统全量测试用例清单与四层测试方法全景说明书.md",
        "subsystem": "testing_governance",
        "core_features": ["四层测试金字塔架构(UT/IT/FT/UAT)", "全量测试用例全息统计与索引", "测试覆盖度与治理回归保障"],
        "key_algorithms": ["四层金字塔测试分层法"],
        "code_bindings": [],
        "test_bindings": [
            {"file": "scripts/test_*.py", "test_class": "AllUnitTests", "tier": "UT/IT/FT/UAT"}
        ],
        "upstream_specs": ["spec_00"]
    },
    {
        "spec_id": "spec_35",
        "spec_number": "35",
        "title": "金融工具核心函数边界与测试数据业务场景全息说明书",
        "doc_path": "docs/35-金融工具核心函数边界与测试数据业务场景全息说明书.md",
        "subsystem": "testing_governance",
        "core_features": ["金融核心数学函数边界规范", "除零除负防御与极值下界收敛", "真实业务测试数据场景解构与仿真模拟"],
        "key_algorithms": ["数学除零保护", "有限责任下界捕获", "无套利上下界约束"],
        "code_bindings": [
            {"module": "financial_core.engines", "file": "financial_core/engines/__init__.py", "description": "底层算法引擎集合"}
        ],
        "test_bindings": [
            {"file": "scripts/test_finance_tools.py", "test_class": "FinanceTests", "tier": "UT"},
            {"file": "scripts/test_phase3b_engines.py", "test_class": "TestPhase3BEngines", "tier": "UT"}
        ],
        "upstream_specs": ["spec_09", "spec_34"]
    },
    {
        "spec_id": "spec_36",
        "spec_number": "36",
        "title": "系统工程设计文档编写规范与标准功能模板",
        "doc_path": "docs/36-系统工程设计文档编写规范与标准功能模板.md",
        "subsystem": "engineering_specification",
        "core_features": ["十大标准章节模板规范", "架构防劣变与非衰退准则", "设计书升级与变更流程标准"],
        "key_algorithms": ["文档工程规范度校验"],
        "code_bindings": [],
        "test_bindings": [],
        "upstream_specs": ["spec_00"]
    },
    {
        "spec_id": "spec_37",
        "spec_number": "37",
        "title": "云端无头每日行情与研报自动化调度流水线",
        "doc_path": "docs/37-云端无头每日行情与研报自动化调度流水线设计书.md",
        "subsystem": "cloud_pipeline",
        "core_features": ["跨平台无头渲染引擎自适应(Chromium/Edge)", "美日股每日大盘自动调度", "时效门禁verify_quote刚性拦截", "密码学时间链条存证", "GitHub Actions与Google Drive流式同步"],
        "key_algorithms": ["无头A4矢量无截断PDF编译", "交易时段时效性智能判定", "单向流式分批上云算法"],
        "code_bindings": [
            {"module": "scripts.cloud_daily_pipeline", "file": "scripts/cloud_daily_pipeline.py", "description": "云端无头每日行情流水线主控"},
            {"module": "financial_reporting.quote_freshness_gateway", "file": "financial_reporting/quote_freshness_gateway.py", "description": "行情新鲜度门禁网关"},
            {"module": "financial_core.engines.prediction_ledger", "file": "financial_core/engines/prediction_ledger.py", "description": "不可篡改密码学账本"}
        ],
        "test_bindings": [
            {"file": "scripts/test_cloud_daily_pipeline.py", "test_class": "CloudDailyPipelineTests", "tier": "UT/IT"}
        ],
        "upstream_specs": ["spec_19", "spec_32"]
    },
    # =========================================================================
    # 核心专责设计典籍权威矩阵 (SPEC-01 至 SPEC-12: 单一事实来源与一书专责一项核心系统职能)
    # =========================================================================
    {
        "spec_id": "spec_core_01",
        "spec_number": "SPEC-01",
        "title": "系统总体架构与分层工程总纲",
        "doc_path": "docs/SPEC_01_系统总体架构与分层工程总纲.md",
        "subsystem": "architecture_foundation",
        "core_features": ["六大核心功能域地图", "四层单向物理架构", "零逆向依赖铁律", "通俗自然语言汇报", "去工程符号化"],
        "key_algorithms": ["四层单向解耦检测", "单一事实来源SSOT治理"],
        "code_bindings": [
            {"module": "financial_core", "file": "financial_core/__init__.py", "description": "底层金融计算核心库"},
            {"module": "financial_reporting", "file": "financial_reporting/__init__.py", "description": "研报呈现与网关层"},
            {"module": "finance_tools", "file": "finance_tools/__init__.py", "description": "向下兼容工具中继层"},
            {"module": "scripts", "file": "scripts/verify_architecture_integrity.py", "description": "架构合规巡检调度器"}
        ],
        "test_bindings": [
            {"file": "scripts/verify_architecture_integrity.py", "test_class": "ArchitectureIntegrityCheck", "tier": "IT"}
        ],
        "upstream_specs": []
    },
    {
        "spec_id": "spec_core_02",
        "spec_number": "SPEC-02",
        "title": "多模态视觉呈现与研报Token设计规范",
        "doc_path": "docs/SPEC_02_多模态视觉呈现与研报Token设计规范.md",
        "subsystem": "financial_reporting",
        "core_features": ["出版级A4矢量无截断排版", "买方暗色仪表盘Token", "5-Sheet Excel深度工作簿样式规范"],
        "key_algorithms": ["A4分页避免截断渲染算法", "深色交互Token映射"],
        "code_bindings": [
            {"module": "financial_reporting.deep_pdf_renderer", "file": "financial_reporting/deep_pdf_renderer.py", "description": "A4深度档案渲染器"},
            {"module": "financial_reporting.daily_briefing_engine", "file": "financial_reporting/daily_briefing_engine.py", "description": "大盘研报渲染引擎"}
        ],
        "test_bindings": [
            {"file": "scripts/test_financial_reporting.py", "test_class": "ReportingTests", "tier": "FT"}
        ],
        "upstream_specs": ["spec_core_01"]
    },
    {
        "spec_id": "spec_core_03",
        "spec_number": "SPEC-03",
        "title": "行业知识中枢与微观商业机器解构规格书",
        "doc_path": "docs/SPEC_03_行业知识中枢与微观商业机器解构规格书.md",
        "subsystem": "knowledge_hub",
        "core_features": ["11大核心板块", "41个法定行业微观造血模型", "产业链供求拓扑", "双核知识图谱遍历与防御拦截"],
        "key_algorithms": ["图谱单向因果传导算法", "未知代码边界防御拦截"],
        "code_bindings": [
            {"module": "financial_core.engines.industry_knowledge_manager", "file": "financial_core/engines/industry_knowledge_manager.py", "description": "41行业商业机器知识管理器"},
            {"module": "financial_core.engines.knowledge_graph_engine", "file": "financial_core/engines/knowledge_graph_engine.py", "description": "知识图谱语义遍历引擎"}
        ],
        "test_bindings": [
            {"file": "scripts/test_knowledge_graph_engine.py", "test_class": "TestKnowledgeGraphEngine", "tier": "IT"},
            {"file": "scripts/test_industry_mapping.py", "test_class": "TestIndustryMapping", "tier": "UT"}
        ],
        "upstream_specs": ["spec_core_01"]
    },
    {
        "spec_id": "spec_core_04",
        "spec_number": "SPEC-04",
        "title": "六步研究法与官方财报三表契约规范",
        "doc_path": "docs/SPEC_04_六步研究法与官方财报三表契约规范.md",
        "subsystem": "data_contract",
        "core_features": ["买方六步投研闭环", "资产负债刚性平账契约(A=L+E)", "DIO库存周转天数", "Beneish M-Score舞弊排查"],
        "key_algorithms": ["资产负债绝对平账校验算法", "M-Score与Z-Score财务体检"],
        "code_bindings": [
            {"module": "financial_core.engines.integrated_three_statement_engine", "file": "financial_core/engines/integrated_three_statement_engine.py", "description": "集成三表分析引擎"},
            {"module": "financial_core.contracts", "file": "financial_core/contracts.py", "description": "财务契约定义"}
        ],
        "test_bindings": [
            {"file": "scripts/test_integrated_three_statement_engine.py", "test_class": "TestIntegratedThreeStatementEngine", "tier": "UT"},
            {"file": "scripts/test_research_contract.py", "test_class": "TestResearchContract", "tier": "IT"}
        ],
        "upstream_specs": ["spec_core_01"]
    },
    {
        "spec_id": "spec_core_05",
        "spec_number": "SPEC-05",
        "title": "数据采集AI浏览器补数与证据治理规范",
        "doc_path": "docs/SPEC_05_数据采集AI浏览器补数与证据治理规范.md",
        "subsystem": "data_ingestion",
        "core_features": ["SEC与JPX双市场全息底账", "公开合规渠道优先", "AI浏览器定向补数SOP", "多币种汇率统一折算"],
        "key_algorithms": ["非标申报字段标准化清洗算法", "跨币种动态汇率折算"],
        "code_bindings": [
            {"module": "financial_core.engines.sec_edgar_collector", "file": "financial_core/engines/sec_edgar_collector.py", "description": "SEC官方底账采集器"},
            {"module": "scripts.data_catalog", "file": "scripts/data_catalog.py", "description": "数据目录治理中枢"}
        ],
        "test_bindings": [
            {"file": "scripts/test_data_store.py", "test_class": "TestDataStore", "tier": "IT"}
        ],
        "upstream_specs": ["spec_core_04"]
    },
    {
        "spec_id": "spec_core_06",
        "spec_number": "SPEC-06",
        "title": "核心金融计算与多情景DCF估值引擎设计书",
        "doc_path": "docs/SPEC_06_核心金融计算与多情景DCF估值引擎设计书.md",
        "subsystem": "valuation_engine",
        "core_features": ["自由现金流FCFF折现", "WACC动态资本成本", "悲观/基准/乐观三态情景推演", "反向DCF预期差反推", "安全边际硬门禁"],
        "key_algorithms": ["三态情景DCF折现算法", "反向DCF复合增长率求解", "无风险利率敏感度分析"],
        "code_bindings": [
            {"module": "financial_core.engines.hall_discount_friction_engine", "file": "financial_core/engines/hall_discount_friction_engine.py", "description": "折现摩擦与资本成本引擎"},
            {"module": "financial_core.engines.business_quality_and_moat_engine", "file": "financial_core/engines/business_quality_and_moat_engine.py", "description": "商业质量与护城河评分引擎"}
        ],
        "test_bindings": [
            {"file": "scripts/test_hall_discount_friction_engine.py", "test_class": "TestHallDiscountFrictionEngine", "tier": "UT"},
            {"file": "scripts/test_business_quality_engine.py", "test_class": "TestBusinessQualityEngine", "tier": "UT"}
        ],
        "upstream_specs": ["spec_core_01", "spec_core_04"]
    },
    {
        "spec_id": "spec_core_07",
        "spec_number": "SPEC-07",
        "title": "买方时机决策与技术足迹分析引擎设计书",
        "doc_path": "docs/SPEC_07_买方时机决策与技术足迹分析引擎设计书.md",
        "subsystem": "timing_engine",
        "core_features": ["米奈尔维尼SEPA时机决策", "趋势模板Stage 2过滤", "波动收敛VCP足迹识别", "成交量枯竭VDU", "枢轴买点与保本动态上移"],
        "key_algorithms": ["VCP多波次收敛识别算法", "移动均线多头排列判定"],
        "code_bindings": [
            {"module": "financial_core.engines.sepa_buy_signal_engine", "file": "financial_core/engines/sepa_buy_signal_engine.py", "description": "SEPA买入时机决策引擎"}
        ],
        "test_bindings": [
            {"file": "scripts/test_sepa_buy_signal_engine.py", "test_class": "TestSepaBuySignalEngine", "tier": "UT"}
        ],
        "upstream_specs": ["spec_core_06"]
    },
    {
        "spec_id": "spec_core_08",
        "spec_number": "SPEC-08",
        "title": "期权全周期因果分析与仓位风控引擎设计书",
        "doc_path": "docs/SPEC_08_期权全周期因果分析与仓位风控引擎设计书.md",
        "subsystem": "options_engine",
        "core_features": ["五级因果推导链条", "标的时效性硬门禁", "实虚值Moneyness判定", "时间价值拆解与归零警示", "四分之一凯利仓位绝对封顶(<=2%)"],
        "key_algorithms": ["时间价值衰减与到期损益分布算法", "四分之一凯利仓位配比"],
        "code_bindings": [
            {"module": "financial_core.engines.options_causal_analyzer", "file": "financial_core/engines/options_causal_analyzer.py", "description": "期权因果分析与风控引擎"}
        ],
        "test_bindings": [
            {"file": "scripts/test_options_causal_analyzer.py", "test_class": "TestOptionsCausalAnalyzer", "tier": "UT"}
        ],
        "upstream_specs": ["spec_core_01", "spec_core_06"]
    },
    {
        "spec_id": "spec_core_09",
        "spec_number": "SPEC-09",
        "title": "全球宏观流动性与跨资产配置体系设计书",
        "doc_path": "docs/SPEC_09_全球宏观流动性与跨资产配置体系设计书.md",
        "subsystem": "macro_allocation",
        "core_features": ["美联储EFFR与10Y美债传导", "2Y/10Y利差倒挂与陡峭化", "实物黄金与金矿股投研框架", "宽基与主题ETF穿透分析"],
        "key_algorithms": ["实际利率TIPS负相关定价算法", "成分股重叠度与费率跟踪误差计算"],
        "code_bindings": [
            {"module": "financial_core.engines.macro_shock_transmission_engine", "file": "financial_core/engines/macro_shock_transmission_engine.py", "description": "宏观冲击传导引擎"},
            {"module": "financial_core.engines.cross_asset_engine", "file": "financial_core/engines/cross_asset_engine.py", "description": "跨资产协同估值引擎"}
        ],
        "test_bindings": [
            {"file": "scripts/test_cross_asset_engine.py", "test_class": "TestCrossAssetEngine", "tier": "UT"},
            {"file": "scripts/test_canyon_multi_asset_pipeline.py", "test_class": "TestCanyonMultiAssetPipeline", "tier": "FT"}
        ],
        "upstream_specs": ["spec_core_06"]
    },
    {
        "spec_id": "spec_core_10",
        "spec_number": "SPEC-10",
        "title": "千家资产池流式建档与公司深度档案生成流水线",
        "doc_path": "docs/SPEC_10_千家资产池流式建档与公司深度档案生成流水线.md",
        "subsystem": "streaming_pipeline",
        "core_features": ["美股与日股数千家企业全量资产池", "分级架构(Tier 0/1/2/3)", "分批并发切片(Batch Chunking)", "流式边渲染边上传(Chunk-and-Stream)", "断点续跑防伪收据"],
        "key_algorithms": ["批次状态机与原子文件锁", "流式并发交付算法"],
        "code_bindings": [
            {"module": "financial_core.engines.tiered_universe_manager", "file": "financial_core/engines/tiered_universe_manager.py", "description": "分级资产池管理器"},
            {"module": "financial_core.engines.normalized_reconciliation_engine", "file": "financial_core/engines/normalized_reconciliation_engine.py", "description": "常态化平账引擎与状态机"}
        ],
        "test_bindings": [
            {"file": "scripts/test_normalized_universe_reconciliation.py", "test_class": "TestNormalizedUniverseReconciliation", "tier": "FT"}
        ],
        "upstream_specs": ["spec_core_04", "spec_core_05"]
    },
    {
        "spec_id": "spec_core_11",
        "spec_number": "SPEC-11",
        "title": "云端无头每日行情与研报自动化调度流水线",
        "doc_path": "docs/SPEC_11_云端无头每日行情与研报自动化调度流水线.md",
        "subsystem": "cloud_pipeline",
        "core_features": ["跨平台无头渲染探测(Chromium/Edge)", "美日股每日定时触发(GitHub Actions)", "行情时效门禁刚性拦截", "重点个股三态推演卡片呈现", "密码学账本存证"],
        "key_algorithms": ["无头A4矢量无截断PDF编译", "交易时段时效性智能判定"],
        "code_bindings": [
            {"module": "scripts.cloud_daily_pipeline", "file": "scripts/cloud_daily_pipeline.py", "description": "云端无头每日行情流水线主控"},
            {"module": "financial_reporting.quote_freshness_gateway", "file": "financial_reporting/quote_freshness_gateway.py", "description": "行情时效门禁网关"}
        ],
        "test_bindings": [
            {"file": "scripts/test_cloud_daily_pipeline.py", "test_class": "CloudDailyPipelineTests", "tier": "UT/IT"}
        ],
        "upstream_specs": ["spec_core_02", "spec_core_08"]
    },
    {
        "spec_id": "spec_core_12",
        "spec_number": "SPEC-12",
        "title": "系统质量工程密码学账本与全息测试验收标准",
        "doc_path": "docs/SPEC_12_系统质量工程密码学账本与全息测试验收标准.md",
        "subsystem": "quality_governance",
        "core_features": ["SHA-256不可篡改时间链账本", "代码交付四道硬门禁", "金融数学边界防御", "单元测试用例规范与中文业务场景全息说明"],
        "key_algorithms": ["SHA-256区块链式连续验签算法", "架构完整性单向无污染巡检"],
        "code_bindings": [
            {"module": "financial_core.engines.prediction_ledger", "file": "financial_core/engines/prediction_ledger.py", "description": "密码学预测账本"},
            {"module": "scripts.verify_architecture_integrity", "file": "scripts/verify_architecture_integrity.py", "description": "架构防劣变巡检门禁"}
        ],
        "test_bindings": [
            {"file": "scripts/test_prediction_ledger.py", "test_class": "TestPredictionLedger", "tier": "UT"}
        ],
        "upstream_specs": ["spec_core_01"]
    }
]

def extract_markdown_profile(md_path: Path):
    """从行业 Markdown 正式档案中提取结构化事实与段落"""
    if not md_path.exists():
        return {}
    text = md_path.read_text(encoding="utf-8")

    # 提取法定买方反证逻辑
    falsify_match = re.search(r"\*\*法定买方核心反证逻辑\*\*：\s*“?([^”\n]+)”?", text)
    falsify_text = falsify_match.group(1).strip() if falsify_match else ""

    # 提取估值适配
    val_match = re.search(r"### 4\. 估值适配\s*\n+([^\n#]+)", text)
    valuation_summary = val_match.group(1).strip() if val_match else ""

    # 提取深跌适配
    drawdown_match = re.search(r"### 5\. 深跌适配\s*\n+([^\n#]+)", text)
    drawdown_summary = drawdown_match.group(1).strip() if drawdown_match else ""

    # 提取核心护城河结构解剖
    moat_section_match = re.search(r"### 1\. 核心护城河结构解剖\s*\n+(.*?)(?=### 2\.|\n## )", text, re.DOTALL)
    moat_text = moat_section_match.group(1).strip() if moat_section_match else ""

    return {
        "falsification_logic": falsify_text,
        "valuation_summary": valuation_summary,
        "drawdown_summary": drawdown_summary,
        "moat_structure_summary": moat_text[:400] + ("..." if len(moat_text) > 400 else "")
    }

def build_knowledge_graph():
    print("[开始构建] 全盘买方投研知识与设计书双核图谱底账 (knowledge_graph.json)...")

    # 读取原始基础配置
    ind_tax_path = ROOT_DIR / "knowledge" / "taxonomy" / "industries.json"
    rules_tax_path = ROOT_DIR / "knowledge" / "taxonomy" / "industry_rules.json"
    bm_tax_path = ROOT_DIR / "knowledge" / "taxonomy" / "business_models.json"
    metrics_path = ROOT_DIR / "knowledge" / "metrics" / "catalog.json"

    ind_tax = json.loads(ind_tax_path.read_text(encoding="utf-8"))
    rules_tax = json.loads(rules_tax_path.read_text(encoding="utf-8"))
    bm_tax = json.loads(bm_tax_path.read_text(encoding="utf-8"))
    metrics_catalog = json.loads(metrics_path.read_text(encoding="utf-8"))

    rules_map = {r["industry_id"]: r for r in rules_tax["rules"]}
    metrics_map = {m["id"]: m for m in metrics_catalog.get("metrics", [])}

    nodes = []
    edges = []

    # 1. 构建板块节点 (Sectors)
    sector_nodes = [n for n in ind_tax["nodes"] if n["level"] == "sector"]
    for s in sector_nodes:
        nodes.append({
            "id": f"sec_{s['id']}",
            "type": "Sector",
            "code": s["id"],
            "name_cn": s["name"],
            "status": "active"
        })
    print(f"  [完成] 已注入 {len(sector_nodes)} 个标准经济板块节点")

    # 2. 构建商业模式节点 (Business Models)
    bm_nodes = bm_tax.get("models", [])
    for bm in bm_nodes:
        nodes.append({
            "id": f"bm_{bm['id']}",
            "type": "BusinessModel",
            "code": bm["id"],
            "name_cn": bm.get("name", bm["id"]),
            "profile_path": bm.get("profile_path", f"knowledge/business_models/{bm['id']}.md"),
            "revenue_mechanism": bm.get("revenue_mechanism", ""),
            "status": "active"
        })
    print(f"  [完成] 已注入 {len(bm_nodes)} 个标准商业模式节点")

    # 3. 构建指标节点 (DriverMetrics)
    for m_id, m in metrics_map.items():
        nodes.append({
            "id": f"metric_{m_id}",
            "type": "DriverMetric",
            "code": m_id,
            "name_cn": m.get("name", m_id),
            "unit": m.get("unit", ""),
            "direction": m.get("direction", "higher_is_better"),
            "category": m.get("category", "industry_driver"),
            "status": "active"
        })
    print(f"  [完成] 已注入 {len(metrics_map)} 个量化指标节点")

    # 4. 构建行业节点 (Industries) 及其关系与附属子节点
    industry_raw_nodes = [n for n in ind_tax["nodes"] if n["level"] == "industry"]
    for ind in industry_raw_nodes:
        ind_id = ind["id"]
        sec_id = ind["parent_id"]
        rule = rules_map.get(ind_id, {})
        md_file = ROOT_DIR / ind.get("profile_path", "")
        extracted_info = extract_markdown_profile(md_file)
        spec_info = INDUSTRY_SPEC_MAPPINGS.get(ind_id, {})

        # 行业主节点
        ind_node_id = f"ind_{ind_id}"
        nodes.append({
            "id": ind_node_id,
            "type": "Industry",
            "code": ind_id,
            "name_cn": ind["name"],
            "sector_code": sec_id,
            "profile_path": ind.get("profile_path", ""),
            "required_segmentation": rule.get("required_segmentation", []),
            "status": "adapted_v2",
            "moat_summary": extracted_info.get("moat_structure_summary", "")
        })

        # 边: 行业 -> 板块
        edges.append({
            "source": ind_node_id,
            "target": f"sec_{sec_id}",
            "type": "BELONGS_TO_SECTOR"
        })

        # 边: 行业 -> 商业模式
        for bm_id in ind.get("business_model_ids", []):
            edges.append({
                "source": ind_node_id,
                "target": f"bm_{bm_id}",
                "type": "OPERATES_BUSINESS_MODEL"
            })

        # 边: 行业 -> 指标
        for m_id in rule.get("metric_ids", []):
            edges.append({
                "source": ind_node_id,
                "target": f"metric_{m_id}",
                "type": "TRACKS_DRIVER_METRIC",
                "priority": "P0"
            })

        # 附属节点: 估值路由节点 (ValuationRoute)
        val_node_id = f"val_route_{ind_id}"
        val_desc = rule.get("valuation_route", extracted_info.get("valuation_summary", ""))
        nodes.append({
            "id": val_node_id,
            "type": "ValuationRoute",
            "industry_code": ind_id,
            "valuation_route_desc": val_desc,
            "drawdown_policy": rule.get("drawdown_policy", extracted_info.get("drawdown_summary", "")),
            "judgment_rules": rule.get("judgment", {})
        })
        edges.append({
            "source": ind_node_id,
            "target": val_node_id,
            "type": "ROUTES_TO_VALUATION"
        })

        # 附属节点: 反证逻辑节点 (FalsificationRule)
        falsify_node_id = f"falsify_rule_{ind_id}"
        falsify_desc = extracted_info.get("falsification_logic", rule.get("counterevidence", ""))
        nodes.append({
            "id": falsify_node_id,
            "type": "FalsificationRule",
            "industry_code": ind_id,
            "verdict_logic": falsify_desc
        })
        edges.append({
            "source": ind_node_id,
            "target": falsify_node_id,
            "type": "FALSIFIED_BY"
        })

        # 附属节点: 设计书与功能代码映射节点 (DesignSpec)
        if spec_info:
            spec_node_id = f"spec_map_{ind_id}"
            nodes.append({
                "id": spec_node_id,
                "type": "DesignSpec",
                "industry_code": ind_id,
                "spec_doc": spec_info.get("spec_doc", ""),
                "engine_module": spec_info.get("engine", "")
            })
            edges.append({
                "source": ind_node_id,
                "target": spec_node_id,
                "type": "BACKED_BY_DESIGN_SPEC"
            })

    print(f"  [完成] 已注入 {len(industry_raw_nodes)} 个正式行业实体及其估值、反证与设计书契约")

    # 5. 注入产业链上下游有向边
    for sc in SUPPLY_CHAIN_EDGES:
        raw_src = sc['source']
        raw_tgt = sc['target']
        norm_src = ID_NORM_MAP.get(raw_src, raw_src)
        norm_tgt = ID_NORM_MAP.get(raw_tgt, raw_tgt)
        src_node = f"ind_{norm_src}"
        tgt_node = f"ind_{norm_tgt}"
        edges.append({
            "source": src_node,
            "target": tgt_node,
            "type": "SUPPLIES_TO",
            "mechanism": sc["mechanism"]
        })
    print(f"  [完成] 已注入 {len(SUPPLY_CHAIN_EDGES)} 条核心产业链上下游博弈有向拓扑边")

    # 6. 【重磅注入】：全系统核心主设计书 (SystemDesignSpec)、代码与测试绑定及 DAG 依赖网
    print("  [装配中] 开始装配全系统主设计书图谱、代码实现绑定与升级影响拓扑链路...")
    spec_node_ids = set()
    code_module_ids = set()
    test_file_ids = set()

    for spec in SYSTEM_DESIGN_SPECS:
        s_id = spec["spec_id"]
        spec_node_ids.add(s_id)
        nodes.append({
            "id": s_id,
            "type": "SystemDesignSpec",
            "spec_number": spec["spec_number"],
            "title": spec["title"],
            "doc_path": spec["doc_path"],
            "subsystem": spec["subsystem"],
            "core_features": spec["core_features"],
            "key_algorithms": spec["key_algorithms"],
            "code_bindings": spec.get("code_bindings", []),
            "test_bindings": spec.get("test_bindings", []),
            "upstream_specs": spec.get("upstream_specs", []),
            "status": "active"
        })

        # 边: 设计书 -> 依赖的上游设计书 (DEPENDS_ON_SPEC)
        for up_id in spec.get("upstream_specs", []):
            edges.append({
                "source": s_id,
                "target": up_id,
                "type": "DEPENDS_ON_SPEC"
            })

        # 辅助节点与边: 代码模块 (CodeModule)
        for cb in spec.get("code_bindings", []):
            m_name = cb.get("module")
            if m_name:
                code_id = f"code_{m_name.replace('.', '_')}"
                if code_id not in code_module_ids:
                    code_module_ids.add(code_id)
                    nodes.append({
                        "id": code_id,
                        "type": "CodeModule",
                        "module_name": m_name,
                        "file_path": cb.get("file", ""),
                        "description": cb.get("description", "")
                    })
                edges.append({
                    "source": s_id,
                    "target": code_id,
                    "type": "IMPLEMENTED_BY_CODE"
                })

        # 辅助节点与边: 测试套件 (TestFile)
        for tb in spec.get("test_bindings", []):
            t_file = tb.get("file", "")
            if t_file and "*" not in t_file:
                test_id = f"test_{Path(t_file).stem}"
                if test_id not in test_file_ids:
                    test_file_ids.add(test_id)
                    nodes.append({
                        "id": test_id,
                        "type": "TestFile",
                        "file_path": t_file,
                        "test_class": tb.get("test_class", ""),
                        "tier": tb.get("tier", "UT")
                    })
                edges.append({
                    "source": s_id,
                    "target": test_id,
                    "type": "VERIFIED_BY_TEST"
                })

    print(f"  [完成] 已注入 {len(SYSTEM_DESIGN_SPECS)} 篇全工程核心主设计书、{len(code_module_ids)} 个代码模块与 {len(test_file_ids)} 个测试验证套件")

    # 组合输出图谱
    graph_data = {
        "graph_metadata": {
            "name": "ShuiyuanBuySideKnowledgeAndDesignGraph",
            "version": "3.0.0",
            "effective_date": "2026-10-18",
            "authoritative_source": "SSOT_BuySide_Design_And_Knowledge_Base",
            "total_nodes": len(nodes),
            "total_edges": len(edges)
        },
        "nodes": nodes,
        "edges": edges
    }

    out_dir = ROOT_DIR / "knowledge" / "graph"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "knowledge_graph.json"
    out_file.write_text(json.dumps(graph_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[构建成功] 知识与设计图谱底账输出至: {out_file.relative_to(ROOT_DIR)}")
    print(f"   总节点数: {len(nodes)} 个 | 总关系边数: {len(edges)} 条")
    return graph_data

if __name__ == "__main__":
    build_knowledge_graph()
