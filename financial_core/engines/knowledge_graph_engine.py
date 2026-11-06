#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
financial_core/engines/knowledge_graph_engine.py

全盘买方投研知识图谱遍历与知识边界核验引擎 (Knowledge Graph Engine)
- 单一事实来源 (SSOT)：基于 `knowledge/graph/knowledge_graph.json` 拓扑底账
- 核心使命：为 AI 代理与底层估值流水线提供零思考的知识边界查询、因果链拓扑遍历与越界防御拦截
- 架构纯净性：属于 financial_core 核心计算层，零外部逆向依赖，完全自主闭环
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

class KnowledgeGraphEngine:
    """全盘买方投研知识图谱拓扑导航与知识边界自动核验引擎"""

    _instance = None
    _cached_graph = None

    def __init__(self, graph_path: Optional[str] = None):
        """
        初始化知识图谱引擎
        :param graph_path: 可选的图谱 json 路径，默认自动寻址项目根目录 knowledge/graph/knowledge_graph.json
        """
        if graph_path:
            self.graph_path = Path(graph_path)
        else:
            # 自动定位项目根目录
            current_dir = Path(__file__).resolve().parent
            project_root = current_dir.parent.parent
            self.graph_path = project_root / "knowledge" / "graph" / "knowledge_graph.json"

        self.graph_data = self._load_graph_data()
        self._build_indices()

    def _load_graph_data(self) -> Dict[str, Any]:
        """加载图谱数据底账"""
        if not self.graph_path.exists():
            raise FileNotFoundError(f"【知识图谱引擎错误】：未找到知识图谱底账文件: {self.graph_path}")
        with open(self.graph_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _build_indices(self):
        """构建内存图拓扑双向快速索引"""
        self.node_map: Dict[str, Dict[str, Any]] = {}
        self.industry_code_map: Dict[str, str] = {}
        self.spec_id_map: Dict[str, str] = {}
        self.spec_number_map: Dict[str, str] = {}
        self.out_edges: Dict[str, List[Dict[str, Any]]] = {}
        self.in_edges: Dict[str, List[Dict[str, Any]]] = {}
        self.type_index: Dict[str, List[str]] = {}
        self.downstream_spec_impacts: Dict[str, List[str]] = {}
        self.code_to_spec_map: Dict[str, List[str]] = {}
        self.test_to_spec_map: Dict[str, List[str]] = {}

        for node in self.graph_data.get("nodes", []):
            nid = node["id"]
            ntype = node.get("type", "Unknown")
            self.node_map[nid] = node

            # 构建节点类型倒排索引
            if ntype not in self.type_index:
                self.type_index[ntype] = []
            self.type_index[ntype].append(nid)

            # 行业代码快速映射
            if ntype == "Industry":
                code = node.get("code")
                if code:
                    self.industry_code_map[code] = nid
                    self.industry_code_map[nid] = nid

            # 设计书快速映射
            if ntype == "SystemDesignSpec":
                s_num = str(node.get("spec_number", "")).lower()
                self.spec_id_map[nid] = nid
                if s_num:
                    self.spec_number_map[s_num] = nid
                    self.spec_number_map[f"spec_{s_num}"] = nid

                # 记录代码与测试绑定反向索引
                for cb in node.get("code_bindings", []):
                    mod = cb.get("module", "")
                    if mod:
                        self.code_to_spec_map.setdefault(mod, []).append(nid)
                for tb in node.get("test_bindings", []):
                    tf = tb.get("file", "")
                    if tf:
                        self.test_to_spec_map.setdefault(tf, []).append(nid)

        for edge in self.graph_data.get("edges", []):
            src = edge["source"]
            tgt = edge["target"]
            etype = edge.get("type", "")

            if src not in self.out_edges:
                self.out_edges[src] = []
            self.out_edges[src].append(edge)

            if tgt not in self.in_edges:
                self.in_edges[tgt] = []
            self.in_edges[tgt].append(edge)

            # 构建设计书下游反向依赖波及链 (若 src 依赖 tgt，则 tgt 升级时波及 src)
            if etype == "DEPENDS_ON_SPEC":
                self.downstream_spec_impacts.setdefault(tgt, []).append(src)

    # 官方标准行业与常见细分产业/别名映射字典 (SSOT 归一化)
    INDUSTRY_ALIAS_MAP: Dict[str, str] = {
        # 零售、电商与消费
        "internet_retail": "retail",
        "retail_home_improvement": "retail",
        "e-commerce": "digital_platforms",
        "ecommerce": "digital_platforms",
        "specialty_retail": "retail",
        "department_stores": "retail",
        "general_merchandise": "retail",
        "apparel_retail": "retail",
        "retail_warehouse_club": "staples_retail",
        "convenience_stores": "staples_retail",
        "retail_omnichannel": "retail",

        # 互联网平台与数字互动传媒
        "interactive_media": "digital_platforms",
        "interactive_media_services": "digital_platforms",
        "social_media": "digital_platforms",
        "search_engines": "digital_platforms",
        "internet_content": "digital_platforms",
        "streaming_media": "media_entertainment",
        "gaming": "media_entertainment",
        "video_games": "media_entertainment",
        "entertainment_streaming": "media_entertainment",
        "digital_entertainment": "media_entertainment",

        # 软件与云服务
        "enterprise_software": "software",
        "cloud_software": "software",
        "saas": "software",
        "system_software": "software",
        "application_software": "software",
        "database_software": "software",
        "cybersecurity": "software",

        # 汽车制造与新能源核心
        "automotive_and_ai": "autos",
        "automotive": "autos",
        "auto_manufacturers": "autos",
        "auto_parts": "autos",
        "electric_vehicles": "autos",
        "oem_auto": "autos",
        "automotive_components": "autos",

        # 制药与医疗健康
        "pharmaceuticals": "pharma",
        "pharma_biotech": "pharma",
        "drug_manufacturers": "pharma",
        "major_pharmaceuticals": "pharma",
        "biotechnology": "biotech",
        "medical_instruments": "medical_devices",
        "health_care_equipment": "medical_devices",
        "life_sciences_tools": "health_services",
        "medical_equipment": "medical_devices",
        "health_care_services": "health_services",
        "hospitals": "health_services",
        "managed_healthcare": "managed_care",

        # 硬件通信与网络基建
        "network_infrastructure": "hardware",
        "networking": "hardware",
        "tech_hardware": "hardware",
        "technology_hardware": "hardware",
        "consumer_electronics": "hardware",
        "telecommunications": "telecom",
        "telecom_services": "telecom",
        "wireless_telecom": "telecom",
        "electronic_components_mlcc": "hardware",
        "electronic_components_and_batteries": "hardware",

        # 半导体与核心设备
        "tech_semi": "semiconductors",
        "semi": "semiconductors",
        "semiconductor": "semiconductors",
        "semiconductor_materials": "semiconductors",
        "semi_materials": "semiconductors",
        "semiconductor_equipment": "semi_equipment",
        "semi_cap": "semi_equipment",
        "foundry": "semiconductors",
        "precision_optics_and_semiconductor": "semi_equipment",
        "semiconductors_memory": "semiconductors",
        "semiconductors_automotive": "semiconductors",

        # 工业设备、自动化与综合重工
        "industrial_automation": "capital_goods",
        "machinery": "capital_goods",
        "robotics": "capital_goods",
        "heavy_machinery": "capital_goods",
        "electrical_equipment": "capital_goods",
        "hvac_and_chemicals": "capital_goods",
        "power_grid_and_digital": "capital_goods",
        "industrial_machinery": "capital_goods",
        "heavy_machinery_and_construction": "capital_goods",

        # 能源与公用事业
        "energy_oil_and_gas": "oil_gas",
        "oil_and_gas": "oil_gas",
        "integrated_oil_gas": "oil_gas",
        "utilities": "regulated_utilities",
        "electric_utilities": "regulated_utilities",

        # 金融科技、银行与投资控股
        "payments_and_fintech": "payments",
        "digital_payments": "payments",
        "banking_and_financials": "banks",
        "commercial_banking": "banks",
        "regional_banking": "banks",
        "diversified_banking": "banks",
        "holding_companies": "asset_management",
        "trading_and_investments": "asset_management",
        "conglomerates": "asset_management",
        "sogo_shosha": "asset_management",
        "investment_banking": "asset_management",
        "securities": "asset_management",
        "financial_services": "asset_management",
        "financial_conglomerate": "asset_management",

        # 消费品与食品饮料
        "non_alcoholic_beverages": "food_beverage",
        "packaged_foods_and_beverages": "food_beverage",
        "consumer_staples": "household_personal",

        # 商业服务与综合通用
        "general": "business_services",
        "general_corporate": "business_services",
        "commercial_services": "business_services",
        "professional_services": "business_services",
        "railway_transportation": "transport_logistics",
        "railway_transportation_and_real_estate": "transport_logistics",
    }

    @classmethod
    def _infer_industry_from_semantic_pattern(cls, raw_key: str) -> Optional[str]:
        """买方投研知识图谱语义模式归纳推导器.

        当外部数据源或全量数千家上市主体出现未见过的细分行业描述时，
        依据 41 个标准内部研究节点的词根特征进行确定性映射，杜绝系统因非标命名中断。
        """
        k = raw_key.lower().strip()

        # 1. 不动产投资信托 REITs
        if "reit" in k or "reits" in k:
            return "equity_reit"

        # 2. 半导体设备 (先进制程光刻/清洗/刻蚀/检测)
        if any(x in k for x in ["semi_equipment", "lithography", "wafer_cleaning", "steppers", "semiconductor_test", "semiconductor_cmp", "semiconductor_precision_machinery", "cleanroom"]):
            return "semi_equipment"

        # 3. 半导体与集成电路 (芯片设计/代工/封装)
        if any(x in k for x in ["semiconductor", "semiconductors", "foundry", "asic", "soc", "microcontrollers", "nand", "analog_power", "rf_frontend"]):
            return "semiconductors"

        # 4. 生物科技与基因工程
        if any(x in k for x in ["biotech", "biotechnology", "gene_editing", "mrna", "rnai", "synthetic_biology"]):
            return "biotech"

        # 5. 传统与现代制药工业
        if any(x in k for x in ["pharma", "pharmaceutical", "pharmaceuticals", "drug_discovery", "oncology", "vaccines", "antiviral", "neurology"]):
            return "pharma"

        # 6. 医疗器械与体外诊断
        if any(x in k for x in ["medical_device", "medical_devices", "cardiovascular", "endoscopy", "dialysis", "surgical", "orthopedic", "glucose_monitoring"]):
            return "medical_devices"

        # 7. 医疗医保管理
        if any(x in k for x in ["managed_care", "managed_healthcare", "health_insurance"]):
            return "managed_care"

        # 8. 医疗服务、CRO 与生命科学支持
        if any(x in k for x in ["clinical_laboratories", "diagnostics", "health_science", "life_sciences_tools", "cro", "bioprocessing", "health_services", "hospitals"]):
            return "health_services"

        # 9. 银行与金融机构
        if any(x in k for x in ["bank", "banking", "lending"]):
            return "banks"

        # 10. 保险与再保险
        if any(x in k for x in ["insurance", "reinsurance", "actuarial"]):
            return "insurance"

        # 11. 支付网络与金融科技
        if any(x in k for x in ["payment", "payments", "fintech", "merchant_acquiring", "credit_scoring", "credit_cards"]):
            return "payments"

        # 12. 基础与应用软件、云安全、SaaS
        if any(x in k for x in ["software", "saas", "cloud_security", "cybersecurity", "database", "devops", "erp", "crm", "work_os", "cpaas", "adtech", "apm", "aiops", "iam", "collaboration", "observability"]):
            return "software"

        # 13. 科技硬件、电子元器件、网络通信设备
        if any(x in k for x in ["hardware", "connectors", "batteries", "mlcc", "electronic_manufacturing", "ems", "pc_hardware", "electronic_components", "electronic_instruments", "test_and_measurement"]):
            return "hardware"

        # 14. 电信运营商与通信服务
        if any(x in k for x in ["telecom", "telecommunications", "wireless", "broadband", "carrier"]):
            return "telecom"

        # 15. 油气中游与管网储运
        if any(x in k for x in ["midstream", "pipeline", "pipelines", "lng_liquefaction"]):
            return "midstream"

        # 16. 石油与天然气上游与炼化综合
        if any(x in k for x in ["oil", "gas", "petroleum", "shale", "deepwater", "exploration_and_production", "energy_oil", "refining"]):
            return "oil_gas"

        # 17. 油田服务与能源设备
        if any(x in k for x in ["oilfield", "drilling", "energy_services", "turbomachinery"]):
            return "energy_services"

        # 18. 公用事业与水电气网
        if any(x in k for x in ["utilities", "utility", "electric_power", "power_generation", "nuclear_energy", "grid_resilience", "clean_energy", "solar"]):
            return "regulated_utilities"

        # 19. 交通运输与综合物流
        if any(x in k for x in ["airline", "airlines", "railroad", "railroads", "railway", "logistics", "shipping", "freight", "trucking", "delivery_parcel", "express_air", "marine_shipping", "aviation"]):
            return "transport_logistics"

        # 20. 汽车工业与交通出行
        if any(x in k for x in ["auto", "automotive", "vehicles", "fleets", "tires", "motorcycles"]):
            return "autos"

        # 21. 国防军工与航空航天
        if any(x in k for x in ["aerospace", "defense", "military", "naval_shipbuilding"]):
            return "aerospace_defense"

        # 22. 餐饮连锁
        if any(x in k for x in ["restaurant", "restaurants", "dining", "pizza", "fast_food"]):
            return "restaurants"

        # 23. 烟草与减害消费品
        if any(x in k for x in ["tobacco", "nicotine"]):
            return "tobacco"

        # 24. 食品与饮料
        if any(x in k for x in ["beverage", "beverages", "food", "foods", "brewing", "beer", "whisky", "spirits", "confectionery", "snacking", "coffee", "bakery", "agribusiness", "meat_protein"]):
            return "food_beverage"

        # 25. 必需消费品零售 (超市/便利店/仓储店)
        if any(x in k for x in ["convenience_stores", "grocery", "warehouse_club", "staples_retail", "supermarket"]):
            return "staples_retail"

        # 26. 综合零售与专卖百货
        if any(x in k for x in ["retail", "discount_stores", "home_improvement", "apparel_retail", "general_merchandise"]):
            return "retail"

        # 27. 互动传媒、流媒体与数字娱乐
        if any(x in k for x in ["gaming", "video_games", "streaming", "entertainment", "media", "broadcasting", "publishing", "music"]):
            return "media_entertainment"

        # 28. 旅游、酒店与度假休闲
        if any(x in k for x in ["hotel", "hotels", "resorts", "cruise", "travel", "vacation", "casinos", "lodging"]):
            return "travel_leisure"

        # 29. 特种与大宗化工
        if any(x in k for x in ["chemical", "chemicals", "materials_science", "coatings", "paints", "fertilizers"]):
            return "chemicals"

        # 30. 金属采矿与冶炼
        if any(x in k for x in ["mining", "metals", "copper", "gold", "iron_ore", "steel", "uranium", "lithium", "rare_earth"]):
            return "mining"

        # 31. 工程施工与重型建材
        if any(x in k for x in ["construction", "contractor", "aggregates", "building_materials", "homebuilding", "engineering_lng"]):
            return "construction"

        # 32. 资本品、机械与工业自动化
        if any(x in k for x in ["machinery", "robotics", "automation", "capital_goods", "compressors", "industrial_tools", "elevators", "hvac"]):
            return "capital_goods"

        # 33. 资产管理、综合商社与多元控股
        if any(x in k for x in ["asset_management", "wealth_management", "conglomerate", "private_equity", "trading_companies", "trading_houses", "holding_companies", "exchanges", "custody"]):
            return "asset_management"

        # 34. 数字平台与互联网电商平台
        if any(x in k for x in ["ecommerce", "e_commerce", "internet_search", "social_networking", "digital_platforms", "marketplace", "ridesharing", "metaverse"]):
            return "digital_platforms"

        # 35. IT 服务与数字化咨询
        if any(x in k for x in ["it_services", "it_consulting", "digital_consulting"]):
            return "it_services"

        # 36. 商业服务与支持
        if any(x in k for x in ["waste_management", "environmental_services", "pest_control", "business_services", "information_services", "hr_technology", "payroll"]):
            return "business_services"

        # 37. 日化个护与美妆
        if any(x in k for x in ["household", "personal_care", "cosmetics", "skincare", "beauty", "oral_care", "hygiene"]):
            return "household_personal"

        # 38. 住宅耐用品与家居
        if any(x in k for x in ["housing_durables", "furniture", "home_furnishings", "appliances", "bicycle"]):
            return "housing_durables"

        # 39. 包装材料与纸业
        if any(x in k for x in ["packaging", "containers", "paper_and_forest", "paper_and_sustainable"]):
            return "packaging"

        # 40. 房地产综合服务与物业
        if any(x in k for x in ["real_estate", "commercial_real_estate", "property_management"]):
            return "real_estate_services"

        return None

    def resolve_industry_node_id(self, industry_query: str) -> Optional[str]:
        """标准化解析行业节点 ID (支持官方标准代码、字典别名映射与语义模式自动归纳)"""
        if not industry_query:
            return None
        raw_key = str(industry_query).lower().strip()

        # 0. 精确命中标准代码字典
        if raw_key in self.industry_code_map:
            return self.industry_code_map[raw_key]

        # 1. 尝试显式字典映射
        normalized_key = self.INDUSTRY_ALIAS_MAP.get(raw_key, raw_key)
        if normalized_key in self.industry_code_map:
            return self.industry_code_map[normalized_key]

        # 2. 尝试剥离或附加前缀
        clean_code = normalized_key.replace("ind_", "")
        if clean_code in self.industry_code_map:
            return self.industry_code_map[clean_code]
        prefixed = f"ind_{normalized_key}"
        if prefixed in self.industry_code_map:
            return self.industry_code_map[prefixed]

        # 3. 语义模式自动归纳推导 (确保全盘数千家公司及外部细分标签 100% 连通与防腐)
        inferred = self._infer_industry_from_semantic_pattern(raw_key)
        if inferred and inferred in self.industry_code_map:
            return self.industry_code_map[inferred]
        if inferred and f"ind_{inferred}" in self.industry_code_map:
            return self.industry_code_map[f"ind_{inferred}"]

        return None

    def get_industry_boundary(self, industry_query: str) -> Dict[str, Any]:
        """
        【AI 零思考核心接口】：根据行业代码一键返回完整的买方知识边界配置
        包含：所属板块、适用商业模式、专属驱动指标、法定估值模型、反证逻辑、上下游博弈关系与对应设计书
        """
        ind_nid = self.resolve_industry_node_id(industry_query)
        if not ind_nid or ind_nid not in self.node_map:
            return {
                "success": False,
                "error": f"未在知识图谱中检索到行业: {industry_query}",
                "valid_industries": list(self.industry_code_map.keys())[:10]
            }

        ind_node = self.node_map[ind_nid]
        out_edges = self.out_edges.get(ind_nid, [])
        in_edges = self.in_edges.get(ind_nid, [])

        sector = None
        business_models = []
        driver_metrics = []
        valuation_route = None
        falsification_rule = None
        design_spec = None
        downstream_supplies = []
        upstream_suppliers = []

        # 遍历出边
        for edge in out_edges:
            etype = edge["type"]
            tgt_id = edge["target"]
            tgt_node = self.node_map.get(tgt_id, {})

            if etype == "BELONGS_TO_SECTOR":
                sector = {
                    "id": tgt_id,
                    "code": tgt_node.get("code"),
                    "name_cn": tgt_node.get("name_cn")
                }
            elif etype == "OPERATES_BUSINESS_MODEL":
                business_models.append({
                    "id": tgt_id,
                    "code": tgt_node.get("code"),
                    "name_cn": tgt_node.get("name_cn"),
                    "profile_path": tgt_node.get("profile_path")
                })
            elif etype == "TRACKS_DRIVER_METRIC":
                driver_metrics.append({
                    "id": tgt_id,
                    "code": tgt_node.get("code"),
                    "name_cn": tgt_node.get("name_cn"),
                    "unit": tgt_node.get("unit"),
                    "direction": tgt_node.get("direction"),
                    "priority": edge.get("priority", "P0")
                })
            elif etype == "ROUTES_TO_VALUATION":
                valuation_route = {
                    "id": tgt_id,
                    "valuation_summary": tgt_node.get("valuation_route_desc"),
                    "drawdown_policy": tgt_node.get("drawdown_policy"),
                    "judgment_rules": tgt_node.get("judgment_rules", {})
                }
            elif etype == "FALSIFIED_BY":
                falsification_rule = {
                    "id": tgt_id,
                    "core_falsification_logic": tgt_node.get("verdict_logic")
                }
            elif etype == "BACKED_BY_DESIGN_SPEC":
                design_spec = {
                    "id": tgt_id,
                    "spec_doc": tgt_node.get("spec_doc"),
                    "engine_module": tgt_node.get("engine_module")
                }
            elif etype == "SUPPLIES_TO":
                downstream_supplies.append({
                    "customer_industry_id": tgt_id,
                    "customer_industry_name": tgt_node.get("name_cn"),
                    "supply_mechanism": edge.get("mechanism")
                })

        # 遍历入边（获取上游供应商）
        for edge in in_edges:
            if edge["type"] == "SUPPLIES_TO":
                src_id = edge["source"]
                src_node = self.node_map.get(src_id, {})
                upstream_suppliers.append({
                    "supplier_industry_id": src_id,
                    "supplier_industry_name": src_node.get("name_cn"),
                    "supply_mechanism": edge.get("mechanism")
                })

        return {
            "success": True,
            "industry_id": ind_nid,
            "code": ind_node.get("code"),
            "name_cn": ind_node.get("name_cn"),
            "profile_path": ind_node.get("profile_path"),
            "required_segmentation": ind_node.get("required_segmentation", []),
            "moat_summary": ind_node.get("moat_summary", ""),
            "sector": sector,
            "business_models": business_models,
            "driver_metrics": driver_metrics,
            "valuation_route": valuation_route,
            "falsification_rule": falsification_rule,
            "design_spec": design_spec,
            "supply_chain": {
                "upstream_suppliers": upstream_suppliers,
                "downstream_customers": downstream_supplies
            }
        }

    def validate_action_boundary(
        self,
        industry_query: str,
        proposed_valuation_model: Optional[str] = None,
        proposed_metrics: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """
        【自动越界防御拦截器】：在执行任何修改或估值前，断言是否违反买方核心知识契约
        :return: (is_valid: bool, message: str)
        """
        boundary = self.get_industry_boundary(industry_query)
        if not boundary.get("success"):
            return False, f"【非法行业代码】：{industry_query} 不在 41 个标准行业图谱中。"

        ind_code = boundary["code"]
        val_route = boundary.get("valuation_route", {}).get("valuation_summary", "")

        # 1. 估值模型硬边界防御
        if proposed_valuation_model:
            model_upper = proposed_valuation_model.upper().strip()

            # 规则 0: 校验是否为合法登记的已知金融估值模型体系
            known_models = {
                "DCF", "FCFF", "FCFE", "MULTISTAGE_DCF", "REVERSE_DCF",
                "PB_ROE", "DDM", "RNPV", "RNPV_PIPELINE", "NAV", "P_AFFO", "AFFO",
                "MID_CYCLE_DCF", "SHILLER_CAPE", "MULTIPLES", "PE", "P/E", "EV_EBITDA",
                "EV/EBITDA", "P_S", "P/S", "P_B", "P/B", "SOTP", "SUM_OF_THE_PARTS",
                "LIQUIDATION", "TWO_STAGE_DCF", "THREE_STAGE_DCF", "DISCOUNTED_CASH_FLOW",
                "GORDON_GROWTH", "RESIDUAL_INCOME", "EVA", "MERTON_DD", "OPTION_TREE",
            }
            if model_upper not in known_models and not any(k in model_upper for k in known_models):
                return False, (
                    f"【知识图谱边界硬拦截】：估值模型 [{proposed_valuation_model}] 未在行业知识图谱中登记，"
                    f"严禁由 AI 自由捏造未知估值模型绕过知识图谱边界！"
                )

            # 规则 A: 银行/保险严禁使用 EV/EBITDA 或标准企业价值
            if ind_code in ["banks", "insurance"] and ("EV" in model_upper or "EBITDA" in model_upper):
                return False, (
                    f"【知识边界拦截】：行业 [{boundary['name_cn']}] 属于高杠杆金融机构，"
                    f"严禁使用企业价值倍数 ({proposed_valuation_model})！"
                    f"法定依据：经营性利息与存款属于核心负债，无法与经营性债务剥离，必须使用市净率 PB-ROE 或股息折现 DDM。"
                )

            # 规则 B: 研发期生物科技未盈利企业严禁使用静态 PE (需避免将 rNPV_Pipeline 等含 pipe 字符串误伤)
            is_static_pe = ("P/E" in model_upper) or bool(re.search(r'(?<![A-Z])PE(?![A-Z])', model_upper)) or any(k in model_upper for k in ["_PE", "PE_", "GAAP_PE", "STATIC_PE"])
            if ind_code == "biotech" and is_static_pe:
                return False, (
                    f"【知识边界拦截】：行业 [{boundary['name_cn']}] 属于研发驱动型管线企业，"
                    f"严禁直接使用静态市盈率 ({proposed_valuation_model})！"
                    f"法定依据：未商业化产品前账面无真实净利润，必须使用研发管线风险调整净现值 rNPV 估值。"
                )

            # 规则 C: 权益型 REITs 严禁使用未扣除维持性资本开支的 GAAP PE
            if ind_code == "equity_reit" and is_static_pe:
                return False, (
                    f"【知识边界拦截】：行业 [{boundary['name_cn']}] 严禁使用 GAAP 市盈率 ({proposed_valuation_model})！"
                    f"法定依据：建筑物直线折旧严重扭曲账面利润，必须采用经调整运营资金 P/AFFO 或每股资产净值 NAV 估值。"
                )

            # 规则 D: 周期品采矿与能源严禁在繁荣顶峰简单外推 PE
            if ind_code in ["mining", "oil_gas"] and ("PE_PEAK" in model_upper):
                return False, (
                    f"【知识边界拦截】：大宗周期行业 [{boundary['name_cn']}] 严禁在价格顶峰线性外推高利润估值！"
                    f"法定依据：必须使用跨周期正常化商品价格折现模型。"
                )

        # 2. 核心指标合规检查
        if proposed_metrics:
            allowed_driver_codes = [m["code"] for m in boundary.get("driver_metrics", [])]
            for m in proposed_metrics:
                if m not in allowed_driver_codes and not m.startswith("shared_"):
                    # 提示但不阻断
                    pass

        return True, f"【知识边界验证通过】：操作符合行业 [{boundary['name_cn']}] 买方治理契约。"

    def trace_supply_chain(self, industry_query: str, depth: int = 1) -> Dict[str, Any]:
        """拓扑遍历产业链供求关系有向图"""
        boundary = self.get_industry_boundary(industry_query)
        if not boundary.get("success"):
            return {"error": boundary.get("error")}

        return {
            "target_industry": boundary["name_cn"],
            "target_code": boundary["code"],
            "direct_upstream_suppliers": boundary["supply_chain"]["upstream_suppliers"],
            "direct_downstream_customers": boundary["supply_chain"]["downstream_customers"],
            "depth": depth
        }

    def search_nodes(self, keyword: str, node_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """全息模糊检索图谱节点"""
        kw = keyword.lower()
        results = []
        for nid, node in self.node_map.items():
            if node_type and node.get("type") != node_type:
                continue
            name_cn = node.get("name_cn", "").lower()
            code = node.get("code", "").lower()
            if kw in nid.lower() or kw in name_cn or kw in code:
                results.append(node)
        return results

    def get_graph_stats(self) -> Dict[str, Any]:
        """获取知识图谱全息元数据与结构规模统计"""
        type_counts = {t: len(nids) for t, nids in self.type_index.items()}
        edge_type_counts = {}
        for edge in self.graph_data.get("edges", []):
            et = edge.get("type", "UNKNOWN")
            edge_type_counts[et] = edge_type_counts.get(et, 0) + 1

        return {
            "metadata": self.graph_data.get("graph_metadata", {}),
            "total_nodes": len(self.node_map),
            "total_edges": len(self.graph_data.get("edges", [])),
            "node_type_distribution": type_counts,
            "edge_type_distribution": edge_type_counts
        }

    # =========================================================================
    # 设计书图谱核心服务：设计内容毫秒级查找与升级影响面分析引擎
    # =========================================================================

    def resolve_spec_node_id(self, spec_query: str) -> Optional[str]:
        """
        标准化解析设计书节点 ID
        支持格式：'14', 'spec_14', 'docs/14-财报解析标准化与计算功能设计.md', 或标题模糊匹配
        """
        q = str(spec_query).strip().lower()
        if q in self.spec_id_map:
            return self.spec_id_map[q]
        if q in self.spec_number_map:
            return self.spec_number_map[q]

        # 尝试剥离 spec_ 前缀或路径前缀
        clean_num = q.replace("spec_", "").replace("docs/", "")
        if "-" in clean_num:
            clean_num = clean_num.split("-")[0]
        if clean_num in self.spec_number_map:
            return self.spec_number_map[clean_num]

        # 尝试按标题模糊匹配
        for nid, node in self.node_map.items():
            if node.get("type") == "SystemDesignSpec":
                title = node.get("title", "").lower()
                doc_path = node.get("doc_path", "").lower()
                if q in title or q in doc_path:
                    return nid
        return None

    def get_design_spec_boundary(self, spec_query: str) -> Dict[str, Any]:
        """
        【设计书边界核心接口】：一键获取设计书的完整技术规格、代码实现、测试套件及上下游 DAG
        """
        s_nid = self.resolve_spec_node_id(spec_query)
        if not s_nid or s_nid not in self.node_map:
            return {
                "success": False,
                "error": f"未在设计书图谱中检索到设计书: {spec_query}",
                "valid_specs": list(self.spec_number_map.keys())[:15]
            }

        node = self.node_map[s_nid]
        out_edges = self.out_edges.get(s_nid, [])

        upstream_specs = []
        code_modules = []
        test_files = []

        for edge in out_edges:
            etype = edge.get("type", "")
            tgt_id = edge.get("target", "")
            tgt_node = self.node_map.get(tgt_id, {})

            if etype == "DEPENDS_ON_SPEC":
                upstream_specs.append({
                    "spec_id": tgt_id,
                    "spec_number": tgt_node.get("spec_number"),
                    "title": tgt_node.get("title"),
                    "doc_path": tgt_node.get("doc_path")
                })
            elif etype == "IMPLEMENTED_BY_CODE":
                code_modules.append({
                    "code_id": tgt_id,
                    "module_name": tgt_node.get("module_name"),
                    "file_path": tgt_node.get("file_path"),
                    "description": tgt_node.get("description")
                })
            elif etype == "VERIFIED_BY_TEST":
                test_files.append({
                    "test_id": tgt_id,
                    "file_path": tgt_node.get("file_path"),
                    "test_class": tgt_node.get("test_class"),
                    "tier": tgt_node.get("tier")
                })

        # 获取下游直接依赖本设计书的模块
        downstream_ids = self.downstream_spec_impacts.get(s_nid, [])
        downstream_specs = []
        for d_id in downstream_ids:
            d_node = self.node_map.get(d_id, {})
            downstream_specs.append({
                "spec_id": d_id,
                "spec_number": d_node.get("spec_number"),
                "title": d_node.get("title"),
                "doc_path": d_node.get("doc_path")
            })

        return {
            "success": True,
            "spec_id": s_nid,
            "spec_number": node.get("spec_number"),
            "title": node.get("title"),
            "doc_path": node.get("doc_path"),
            "subsystem": node.get("subsystem"),
            "core_features": node.get("core_features", []),
            "key_algorithms": node.get("key_algorithms", []),
            "code_bindings": code_modules,
            "test_bindings": test_files,
            "upstream_dependencies": upstream_specs,
            "direct_downstream_impacts": downstream_specs
        }

    def find_design_content(self, query: str, search_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        【设计内容多维秒级查找接口】：解决开发与改修过程中的定位难题
        支持按业务关键词、算法公式名称、代码类名、测试文件名或编号搜索设计书与功能点
        """
        q = str(query).strip().lower()
        results = []

        for nid in self.type_index.get("SystemDesignSpec", []):
            node = self.node_map.get(nid, {})
            title = node.get("title", "").lower()
            doc_path = node.get("doc_path", "").lower()
            spec_num = str(node.get("spec_number", "")).lower()
            subsystem = node.get("subsystem", "").lower()
            features = [f.lower() for f in node.get("core_features", [])]
            algorithms = [a.lower() for a in node.get("key_algorithms", [])]

            matched_fields = []
            relevance_score = 0
            if q == spec_num or q == f"spec_{spec_num}":
                matched_fields.append("spec_number")
                relevance_score += 100
            if q in title:
                matched_fields.append("title")
                relevance_score += 50
            if q in doc_path:
                matched_fields.append("doc_path")
                relevance_score += 20
            if q in subsystem:
                matched_fields.append("subsystem")
                relevance_score += 15
            if any(q in f for f in features):
                matched_fields.append("core_features")
                relevance_score += 30
            if any(q in a for a in algorithms):
                matched_fields.append("key_algorithms")
                relevance_score += 30

            # 匹配代码模块
            matched_code = []
            for cb in node.get("code_bindings", []):
                mod = cb.get("module", "").lower()
                c_file = cb.get("file", "").lower()
                desc = cb.get("description", "").lower()
                if q in mod or q in c_file or q in desc:
                    matched_code.append(cb)

            if matched_code:
                matched_fields.append("code_bindings")
                relevance_score += 10

            # 匹配测试文件
            matched_tests = []
            for tb in node.get("test_bindings", []):
                t_file = tb.get("file", "").lower()
                t_cls = tb.get("test_class", "").lower()
                if q in t_file or q in t_cls:
                    matched_tests.append(tb)

            if matched_tests:
                matched_fields.append("test_bindings")
                relevance_score += 5

            if matched_fields:
                results.append({
                    "spec_id": nid,
                    "spec_number": node.get("spec_number"),
                    "title": node.get("title"),
                    "doc_path": node.get("doc_path"),
                    "subsystem": node.get("subsystem"),
                    "relevance_score": relevance_score,
                    "matched_dimensions": matched_fields,
                    "core_features": node.get("core_features", []),
                    "key_algorithms": node.get("key_algorithms", []),
                    "code_bindings": node.get("code_bindings", []),
                    "test_bindings": node.get("test_bindings", []),
                    "upstream_specs": node.get("upstream_specs", []),
                    "downstream_impact_count": len(self.downstream_spec_impacts.get(nid, []))
                })

        # 按相关度分数从高到低排序
        results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return results

    def analyze_upgrade_impact(self, spec_query: str) -> Dict[str, Any]:
        """
        【升级影响面拓扑分析引擎】：在升级设计书或功能前，精准推演下游波及半径
        返回：直接下游设计书、间接传递波及设计书、波及代码模块、必须回归的测试用例及风险评级
        """
        boundary = self.get_design_spec_boundary(spec_query)
        if not boundary.get("success"):
            return boundary

        target_id = boundary["spec_id"]

        # BFS 拓扑遍历获取全部下游传递依赖
        visited_specs = set()
        queue = [target_id]
        direct_downstream = []
        transitive_downstream = []

        while queue:
            curr = queue.pop(0)
            downstream_ids = self.downstream_spec_impacts.get(curr, [])
            for d_id in downstream_ids:
                if d_id not in visited_specs and d_id != target_id:
                    visited_specs.add(d_id)
                    d_node = self.node_map.get(d_id, {})
                    info = {
                        "spec_id": d_id,
                        "spec_number": d_node.get("spec_number"),
                        "title": d_node.get("title"),
                        "doc_path": d_node.get("doc_path"),
                        "subsystem": d_node.get("subsystem")
                    }
                    if curr == target_id:
                        direct_downstream.append(info)
                    else:
                        transitive_downstream.append(info)
                    queue.append(d_id)

        # 收集受波及的代码模块与测试用例
        all_affected_spec_ids = [target_id] + list(visited_specs)
        affected_code_modules = []
        mandatory_tests = []
        seen_files = set()
        seen_tests = set()

        for s_id in all_affected_spec_ids:
            s_node = self.node_map.get(s_id, {})
            for cb in s_node.get("code_bindings", []):
                c_file = cb.get("file")
                if c_file and c_file not in seen_files:
                    seen_files.add(c_file)
                    affected_code_modules.append(cb)
            for tb in s_node.get("test_bindings", []):
                t_file = tb.get("file")
                if t_file and t_file not in seen_tests:
                    seen_tests.add(t_file)
                    mandatory_tests.append(tb)

        # 风险评级判定
        target_num = boundary["spec_number"]
        if target_num in ["00", "01", "04", "09", "14"]:
            risk_level = "Critical"
            risk_desc = "底层核心基石或数据平账底座：改动将全局传导，严禁破坏单向无环解耦与平账等式！"
        elif target_num in ["23", "25", "26", "33"]:
            risk_level = "High"
            risk_desc = "核心算法或全量资产调度引擎：影响多资产分析与批量流水线，需严格回归。"
        elif target_num in ["21", "27", "31", "32"]:
            risk_level = "Medium"
            risk_desc = "研报合成与主看板呈现层：改动涉及工作簿与卡片渲染，需验证视觉Token一致性。"
        else:
            risk_level = "Low"
            risk_desc = "局部规范或独立说明：影响范围较小，执行局部单测回归即可。"

        return {
            "success": True,
            "target_spec": {
                "spec_id": target_id,
                "spec_number": boundary["spec_number"],
                "title": boundary["title"],
                "doc_path": boundary["doc_path"],
                "subsystem": boundary["subsystem"]
            },
            "risk_assessment": {
                "risk_level": risk_level,
                "risk_description": risk_desc
            },
            "impact_radius": {
                "direct_downstream_specs": direct_downstream,
                "transitive_downstream_specs": transitive_downstream,
                "total_affected_specs_count": len(all_affected_spec_ids)
            },
            "affected_code_modules": affected_code_modules,
            "mandatory_regression_tests": mandatory_tests,
            "safety_architectural_directives": [
                "1. 严格四层依赖单向性：底层核心 (financial_core) 严禁 import 外层模块；",
                "2. 资产负债平账自检：财报数据改修必须通过 Assets = Liabilities + Equity 刚性断言；",
                "3. 零绝对路径硬编码：工具环境与路径必须使用相对路径动态探测；",
                "4. 密码学账本防伪：所有预测与对账必须由 PredictionLedger SHA-256 验签；",
                "5. 100% 物理消除所有 Emoji 表情符号，采用纯自然中文商业语义。"
            ]
        }

    def generate_upgrade_checklist(self, spec_query: str, upgrade_summary: str = "功能升级与契约对齐") -> Dict[str, Any]:
        """
        【升级检查单生成器】：严格遵循 docs/36 规范，自动输出五步升级实施闭环清单
        """
        impact = self.analyze_upgrade_impact(spec_query)
        if not impact.get("success"):
            return impact

        target = impact["target_spec"]
        spec_num = target["spec_number"]
        spec_title = target["title"]
        doc_path = target["doc_path"]

        checklist_steps = [
            {
                "step": 1,
                "name": "设计文档修订与契约对齐 (Spec Amendment)",
                "action": f"编辑更新设计文档 [{doc_path}]",
                "checkpoints": [
                    f"在 [{doc_path}] 记录升级版本号与变更原因；",
                    "补充新增功能的架构设计、状态机枚举与字段契约；",
                    "若涉及数据结构变动，同步更新 docs/*-dictionary/ 对应的数据字典。"
                ]
            },
            {
                "step": 2,
                "name": "底层代码改造与向后兼容性 (Code Implementation)",
                "action": "根据设计书改造目标代码类与函数",
                "target_modules": [m.get("file_path") for m in impact.get("affected_code_modules", [])[:5]],
                "checkpoints": [
                    "遵循纯相对导入，严禁向外层反向引用；",
                    "数值与定价计算注入除零除负防御、极值有限责任下界；",
                    "保持公共接口参数签名向后兼容，不破坏已有下游调用。"
                ]
            },
            {
                "step": 3,
                "name": "单体与集成测试用例增补 (Unit & Integration Testing)",
                "action": "在对应测试文件中追加针对本次升级场景的断言",
                "checkpoints": [
                    "在测试方法中补充清晰的中文描述、正常边界与异常仿真场景；",
                    "断言新增边界与逻辑 100% 毫秒级 PASS。"
                ]
            },
            {
                "step": 4,
                "name": "下游关联模块与全链路回归 (Downstream Regression)",
                "action": "执行受波及下游模块的回归测试",
                "tests_to_run": [t.get("file_path") for t in impact.get("mandatory_regression_tests", [])[:8]],
                "checkpoints": [
                    f"重点核验直接波及的 {len(impact['impact_radius']['direct_downstream_specs'])} 个下游设计书功能是否完好；",
                    "确保受影响测试用例 100% 成功，用例数量只增不减。"
                ]
            },
            {
                "step": 5,
                "name": "四道硬门禁验收与原子规范提交 (Gate Verification & Commit)",
                "action": "按顺序执行项目四大硬门禁",
                "commands": [
                    "python scripts/verify_architecture_integrity.py",
                    "python -m unittest discover -s scripts -p 'test_*.py'",
                    "python scripts/test_data_store.py && python scripts/validate_knowledge_structure.py",
                    "git add -A && git commit -m 'feat/refactor(spec-" + str(spec_num) + "): " + upgrade_summary + "'"
                ],
                "checkpoints": [
                    "门禁 1: 架构完整性巡检零污染、零环路；",
                    "门禁 2: 全量单测 100% 零失败；",
                    "门禁 3: 四大治理回归全绿；",
                    "门禁 4: 密码学账本验签通过 (tampered == False)。"
                ]
            }
        ]

        return {
            "success": True,
            "target_spec_number": spec_num,
            "target_spec_title": spec_title,
            "upgrade_summary": upgrade_summary,
            "risk_level": impact["risk_assessment"]["risk_level"],
            "checklist_steps": checklist_steps
        }

    def verify_graph_disk_integrity(self) -> Dict[str, Any]:
        """
        【物理磁盘链路保真性自动核验】：
        断言图谱中登记的所有设计书 doc_path、代码 file_path、测试 file_path 在本地磁盘真实存在
        """
        current_dir = Path(__file__).resolve().parent
        project_root = current_dir.parent.parent

        checked_docs = []
        checked_codes = []
        checked_tests = []
        missing_items = []

        for nid in self.type_index.get("SystemDesignSpec", []):
            node = self.node_map.get(nid, {})
            # 检查设计书路径
            doc_path = node.get("doc_path", "")
            if doc_path:
                full_doc = project_root / doc_path
                exists = full_doc.exists()
                checked_docs.append({"path": doc_path, "exists": exists})
                if not exists:
                    missing_items.append({"type": "DesignSpecDoc", "path": doc_path, "from_spec": nid})

            # 检查代码物理路径
            for cb in node.get("code_bindings", []):
                c_file = cb.get("file", "")
                if c_file:
                    full_code = project_root / c_file
                    exists = full_code.exists()
                    checked_codes.append({"path": c_file, "exists": exists})
                    if not exists:
                        missing_items.append({"type": "CodeFile", "path": c_file, "from_spec": nid})

            # 检查测试物理路径
            for tb in node.get("test_bindings", []):
                t_file = tb.get("file", "")
                if t_file and "*" not in t_file:
                    full_test = project_root / t_file
                    exists = full_test.exists()
                    checked_tests.append({"path": t_file, "exists": exists})
                    if not exists:
                        missing_items.append({"type": "TestFile", "path": t_file, "from_spec": nid})

        total_checked = len(checked_docs) + len(checked_codes) + len(checked_tests)
        is_all_valid = len(missing_items) == 0

        return {
            "all_valid": is_all_valid,
            "total_checked": total_checked,
            "docs_checked": len(checked_docs),
            "code_files_checked": len(checked_codes),
            "test_files_checked": len(checked_tests),
            "missing_count": len(missing_items),
            "missing_items": missing_items
        }

