"""多标的产业链上下游涟漪效应分析中继工具 (Supply Chain Ripple Analyzer Tool).

本模块属于 finance_tools 中继工具层:
1. 单一事实来源 (SSOT): 从 config/supply_chain_topologies.json 加载拓扑，由 schemas 刚性验签;
2. 事件智能匹配: 自动将雷达数据库突发事件匹配至最相关的产业链拓扑图谱;
3. 全链协同穿透: 调用底层 SupplyChainRippleEngine 计算 "上游供应商 ➔ 核心中枢 ➔ 下游大客户" 连锁损益;
4. 交易室决策直觉输出: 生成多标的因果矩阵、存货周转天数 (DIO) 消耗期与买方调仓建议。
"""

import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

from jsonschema import Draft202012Validator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finance_tools.event_radar_collector import RadarDatabaseManager
from financial_core.engines.supply_chain_ripple_engine import (
    SupplyChainRippleEngine,
    SupplyChainRippleReport,
)

logger = logging.getLogger("SupplyChainRippleAnalyzer")


class SupplyChainRippleAnalyzer:
    """产业链多标的涟漪效应分析与因果穿透中继工具."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        topologies_path: Optional[str] = None,
        schema_path: Optional[str] = None,
        engine: Optional[SupplyChainRippleEngine] = None,
    ) -> None:
        """初始化产业链涟漪分析器.

        Args:
            db_path: 事件雷达数据库路径 (默认为 data/ledger/event_radar.sqlite3).
            topologies_path: 产业链拓扑定义配置文件路径.
            schema_path: 产业链拓扑 JSONSchema 模式文件路径.
            engine: 可选底层核心涟漪计算引擎.
        """
        self.db_path = str(Path(db_path) if db_path else (PROJECT_ROOT / "data/ledger/event_radar.sqlite3"))
        top_p = Path(topologies_path) if topologies_path else (PROJECT_ROOT / "config/supply_chain_topologies.json")
        sch_p = Path(schema_path) if schema_path else (PROJECT_ROOT / "schemas/supply_chain_topologies.schema.json")

        self.engine = engine or SupplyChainRippleEngine()
        self.db_mgr = RadarDatabaseManager(db_path=self.db_path)

        # 严格执行单一事实来源与模式校验
        if not top_p.exists():
            raise FileNotFoundError(f"未找到产业链拓扑配置文件: {top_p}")
        if not sch_p.exists():
            raise FileNotFoundError(f"未找到产业链模式定义文件: {sch_p}")

        schema = json.loads(sch_p.read_text(encoding="utf-8"))
        data = json.loads(top_p.read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(data)

        self.topologies: List[Dict[str, Any]] = data.get("topologies", [])
        self.topology_map: Dict[str, Dict[str, Any]] = {
            t["topology_id"]: t for t in self.topologies
        }
        logger.info(f"产业链拓扑加载成功: 已注册 {len(self.topologies)} 条全球核心产业链")

    def list_topologies(self) -> List[Dict[str, Any]]:
        """列出当前已注册的全量产业链拓扑概览."""
        return [
            {
                "topology_id": t["topology_id"],
                "name_zh": t["name_zh"],
                "industry_category": t.get("industry_category"),
                "core_hub": t["core_hub"]["name_zh"],
                "core_hub_ticker": t["core_hub"]["ticker"],
                "upstream_count": len(t.get("upstream_nodes", [])),
                "downstream_count": len(t.get("downstream_nodes", [])),
                "description": t.get("description", ""),
            }
            for t in self.topologies
        ]

    def get_topology(self, topology_id: str) -> Optional[Dict[str, Any]]:
        """按 ID 精确获取产业链拓扑详情."""
        return self.topology_map.get(topology_id)

    def match_topology_for_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """依据事件所属行业分类与涉案实体智能匹配最相关产业链.

        Args:
            event: 事件雷达记录字典.

        Returns:
            命中的产业链拓扑字典，若无匹配则返回 None.
        """
        category = event.get("category", "")
        entities = event.get("involved_entities", [])
        if isinstance(entities, str):
            try:
                entities = json.loads(entities)
            except Exception:
                entities = [entities]
        entities_upper = [str(e).upper() for e in entities]
        raw_title = (event.get("title") or "").upper()

        # 1. 优先按核心中枢及上下游 Ticker/实体子串精确匹配
        for t in self.topologies:
            hub_ticker = (t["core_hub"].get("ticker") or "").upper()
            hub_name = t["core_hub"].get("name_zh", "").upper()
            if hub_ticker in entities_upper or hub_name in raw_title:
                return t

            # 匹配上下游
            all_tickers = [
                (n.get("ticker") or "").upper()
                for n in t.get("upstream_nodes", []) + t.get("downstream_nodes", [])
            ]
            for tick in all_tickers:
                if tick and tick in entities_upper:
                    return t

        # 2. 次优按行业业务维度 (industry_category) 匹配
        for t in self.topologies:
            if t.get("industry_category") == category:
                return t

        # 3. 默认兜底第一条标杆产业链 (全球半导体光刻胶与晶圆制造链)
        return self.topologies[0] if self.topologies else None

    def analyze_event_ripple(
        self,
        event_id: str,
        topology_id: Optional[str] = None,
        disruption_days: Optional[float] = None,
    ) -> SupplyChainRippleReport:
        """为特定突发事件执行产业链全景涟漪穿透推演.

        Args:
            event_id: 突发事件 ID (如 EVT_E095B7243F76).
            topology_id: 可选显式强制指定的产业链拓扑 ID.
            disruption_days: 预估物理断供天数 (默认 60 天).

        Returns:
            SupplyChainRippleReport 综合研判报告.

        Raises:
            ValueError: 事件不存在或拓扑无法匹配.
        """
        event = self.db_mgr.get_event_by_id(event_id)
        if not event:
            raise ValueError(f"未在雷达账本中找到事件: {event_id}")

        if topology_id:
            topology = self.get_topology(topology_id)
            if not topology:
                raise ValueError(f"不存在的产业链拓扑: {topology_id}")
        else:
            topology = self.match_topology_for_event(event)
            if not topology:
                raise ValueError(f"未能为事件 {event_id} 匹配到合适的产业链拓扑")

        report = self.engine.evaluate_ripple_transmission(
            topology=topology,
            event=event,
            disruption_days=disruption_days,
        )
        return report

    def analyze_all_major_events(
        self, severity_levels: Tuple[str, ...] = ("P0", "P1")
    ) -> List[SupplyChainRippleReport]:
        """批量遍历全量重大突发事件，输出产业链全盘受损全景图.

        Args:
            severity_levels: 关注的严重烈度门槛 (默认 P0, P1).

        Returns:
            全量重大事件的产业链涟漪报告列表.
        """
        events = self.db_mgr.query_events(limit=100)
        reports: List[SupplyChainRippleReport] = []

        for e in events:
            sev = e.get("severity_level") or "P2"
            if sev in severity_levels:
                eid = e.get("event_id")
                if eid:
                    try:
                        rep = self.analyze_event_ripple(eid)
                        reports.append(rep)
                    except Exception as err:
                        logger.warning("分析事件 %s 涟漪传导时异常: %s", eid, err)

        return reports
