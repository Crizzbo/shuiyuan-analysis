"""事件雷达高频收集与调度中枢 (Event Radar Collector & Scheduler).

本模块实现第一阶段的核心调度与采集功能:
1. 自发断网检测与平滑自治恢复 (NetworkHealthWatchdog);
2. 断点续传、SHA-256 指纹排重与进度管理 (RadarProgressManager);
3. 选项 2-B 统一微型模型摘要生成与 P0/P1 重大事件触发门禁;
4. 市场时段自适应调度 (盘前 5 分钟、盘中 15 分钟、休市 60 分钟).
"""

from datetime import datetime, timezone, timedelta
import json
import logging
import os
from pathlib import Path
import socket
import sqlite3
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

from financial_core.engines.event_radar_engine import (
    EventRadarEngine,
    EventSeverity,
    EventCategory,
    RawNewsItem,
    StructuredEventSummary,
)

logger = logging.getLogger(__name__)


class NetworkHealthWatchdog:
    """自发断网检测与自治恢复看门狗."""

    DEFAULT_PROBES = [
        {"host": "8.8.8.8", "port": 53, "provider": "Google_Public_DNS"},
        {"host": "1.1.1.1", "port": 53, "provider": "Cloudflare_DNS"},
    ]

    def __init__(
        self,
        probe_endpoints: Optional[List[Dict[str, Any]]] = None,
        timeout_sec: float = 1.5,
        max_offline_retries: int = 5,
        backoff_intervals: Optional[List[int]] = None,
    ):
        self.probe_endpoints = probe_endpoints or self.DEFAULT_PROBES
        self.timeout_sec = timeout_sec
        self.max_offline_retries = max_offline_retries
        self.backoff_intervals = backoff_intervals or [5, 15, 30, 60, 120]

    def check_connectivity(self) -> Tuple[bool, str, float]:
        """向权威无状态节点发送极轻量 Socket 探测.

        返回: (is_online, connected_node, latency_ms)
        """
        for probe in self.probe_endpoints:
            host = probe.get("host", "8.8.8.8")
            port = int(probe.get("port", 53))
            start_t = time.perf_counter()
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(self.timeout_sec)
                    sock.connect((host, port))
                latency_ms = (time.perf_counter() - start_t) * 1000.0
                return True, f"{probe.get('provider', host)} ({host}:{port})", round(latency_ms, 2)
            except Exception:
                continue
        return False, "ALL_PROBES_UNREACHABLE", -1.0

    def wait_for_recovery(
        self,
        max_retries: Optional[int] = None,
        sleep_func: Callable[[float], None] = time.sleep,
        on_status_change: Optional[Callable[[str, str], None]] = None,
    ) -> bool:
        """断网时执行指数退避静默挂起，不抛异常崩溃，等待网络自愈."""
        retries = max_retries if max_retries is not None else self.max_offline_retries
        for attempt in range(1, retries + 1):
            interval_idx = min(attempt - 1, len(self.backoff_intervals) - 1)
            wait_time = self.backoff_intervals[interval_idx]

            msg = (
                f"[断网自治看门狗] 检测到外部网络连接中断。进入静默等待第 {attempt}/{retries} 次，"
                f"将在 {wait_time} 秒后自动重试..."
            )
            if on_status_change:
                on_status_change("OFFLINE_HOLD", msg)
            else:
                logger.warning(msg)

            sleep_func(wait_time)

            is_online, node, lat = self.check_connectivity()
            if is_online:
                recover_msg = f"[断网自治看门狗] 网络已自愈恢复！成功连接至 {node}，延迟 {lat}ms。"
                if on_status_change:
                    on_status_change("RECOVERED", recover_msg)
                else:
                    logger.info(recover_msg)
                return True

        fail_msg = f"[断网自治看门狗] 已达到最大重试次数 ({retries}次)，网络未能恢复。"
        if on_status_change:
            on_status_change("RETRY_EXHAUSTED", fail_msg)
        return False


class RadarProgressManager:
    """断点续传、SHA-256 唯一指纹排重与进度账本管理器."""

    def __init__(
        self,
        checkpoint_path: str = "data/ledger/event_radar_checkpoint.json",
        max_hash_history_size: int = 10000,
    ):
        self.checkpoint_path = Path(checkpoint_path)
        self.max_hash_history_size = max_hash_history_size
        self._state: Dict[str, Any] = {
            "version": "1.0.0",
            "last_successful_timestamp": "1970-01-01T00:00:00Z",
            "processed_hashes": [],
            "cumulative_metrics": {
                "total_scanned": 0,
                "total_filtered_in": 0,
                "total_summarized": 0,
                "total_p0_p1_triggered": 0,
                "total_estimated_tokens": 0,
            },
            "recent_triggered_events": [],
        }
        self.load_checkpoint()

    def load_checkpoint(self) -> Dict[str, Any]:
        """读取本地不可篡改状态账本."""
        if self.checkpoint_path.is_file():
            try:
                with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._state.update(data)
            except Exception as e:
                logger.warning("读取断点账本异常，使用初始状态: %s", e)
        return self._state

    def is_hash_processed(self, raw_hash: str) -> bool:
        """检查文章哈希是否已在历史处理指纹库中 (秒级幂等排重)."""
        return raw_hash in self._state.get("processed_hashes", [])

    def record_processed_hash(self, raw_hash: str) -> None:
        """记录新处理的哈希指纹，超出容量上限时自动滑动丢弃最旧项."""
        hashes = self._state.setdefault("processed_hashes", [])
        if raw_hash not in hashes:
            hashes.append(raw_hash)
            if len(hashes) > self.max_hash_history_size:
                self._state["processed_hashes"] = hashes[-self.max_hash_history_size:]

    def save_checkpoint(
        self,
        current_timestamp: str,
        cycle_metrics: Dict[str, int],
        new_triggered_events: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """原子安全落盘当前状态水位线与累计指标."""
        self._state["last_successful_timestamp"] = current_timestamp

        cum = self._state.setdefault("cumulative_metrics", {})
        cum["total_scanned"] = cum.get("total_scanned", 0) + cycle_metrics.get("scanned", 0)
        cum["total_filtered_in"] = cum.get("total_filtered_in", 0) + cycle_metrics.get("filtered_in", 0)
        cum["total_summarized"] = cum.get("total_summarized", 0) + cycle_metrics.get("summarized", 0)
        cum["total_p0_p1_triggered"] = cum.get("total_p0_p1_triggered", 0) + cycle_metrics.get("p0_p1_triggered", 0)
        cum["total_estimated_tokens"] = cum.get("total_estimated_tokens", 0) + cycle_metrics.get("estimated_tokens", 0)

        if new_triggered_events:
            history = self._state.setdefault("recent_triggered_events", [])
            history.extend(new_triggered_events)
            # 保留最近 50 条触发记录
            self._state["recent_triggered_events"] = history[-50:]

        # 确保父级目录存在
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        temp_path = self.checkpoint_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)
        temp_path.replace(self.checkpoint_path)

    @property
    def state(self) -> Dict[str, Any]:
        return self._state


class RadarDatabaseManager:
    """事件雷达 SQLite 数据库持久化管理器.

    维护两大核心表:
    1. radar_events: 记录全量收集与提纯的事实条目 (时间戳、信源、分类、物理影响、涉及实体、分部、烈度评级与深研门禁状态).
    2. collection_cycles: 记录每次定时巡检轮次的历史审计 (时间戳、交易时段、探针延迟、扫描统计与 Token 消耗).
    """

    def __init__(self, db_path: str = "data/ledger/event_radar.sqlite3"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS radar_events (
                    event_id TEXT PRIMARY KEY,
                    raw_hash TEXT UNIQUE,
                    collected_at TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    micro_physical_impact TEXT NOT NULL,
                    involved_entities TEXT NOT NULL,
                    affected_business_segments TEXT NOT NULL,
                    estimated_duration TEXT NOT NULL,
                    severity_level TEXT NOT NULL,
                    requires_deep_analysis INTEGER NOT NULL,
                    url TEXT,
                    raw_content TEXT,
                    credibility_tier TEXT DEFAULT 'Tier3_Mainstream_Wire',
                    credibility_score REAL DEFAULT 0.8,
                    verification_status TEXT DEFAULT 'Corroborated_Report',
                    verification_note TEXT DEFAULT '主流财经通讯社通告'
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS collection_cycles (
                    cycle_id TEXT PRIMARY KEY,
                    cycle_timestamp TEXT NOT NULL,
                    market_session TEXT NOT NULL,
                    status TEXT NOT NULL,
                    active_probe_node TEXT NOT NULL,
                    probe_latency_ms REAL NOT NULL,
                    scanned_count INTEGER NOT NULL,
                    filtered_in_count INTEGER NOT NULL,
                    summarized_count INTEGER NOT NULL,
                    p0_p1_triggered_count INTEGER NOT NULL,
                    estimated_tokens_consumed INTEGER NOT NULL
                )
            """)
            # 平滑增量表结构迁移：检查并自动补齐新字段 (必须在创建新列索引前执行)
            cursor.execute("PRAGMA table_info(radar_events)")
            existing_cols = {row[1] for row in cursor.fetchall()}
            new_columns = [
                ("credibility_tier", "TEXT DEFAULT 'Tier3_Mainstream_Wire'"),
                ("credibility_score", "REAL DEFAULT 0.8"),
                ("verification_status", "TEXT DEFAULT 'Corroborated_Report'"),
                ("verification_note", "TEXT DEFAULT '主流财经通讯社通告'"),
                ("evidence_path", "TEXT DEFAULT NULL"),
                ("evidence_sha256", "TEXT DEFAULT NULL"),
                ("verified_at", "TEXT DEFAULT NULL"),
            ]
            for col_name, col_def in new_columns:
                if col_name not in existing_cols:
                    cursor.execute(f"ALTER TABLE radar_events ADD COLUMN {col_name} {col_def}")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_radar_events_severity ON radar_events (severity_level)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_radar_events_published ON radar_events (published_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_radar_events_requires_deep ON radar_events (requires_deep_analysis)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_radar_events_verif_status ON radar_events (verification_status)")

            conn.commit()

    def insert_event(self, summary: StructuredEventSummary, item: RawNewsItem, collected_at: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO radar_events (
                    event_id, raw_hash, collected_at, published_at, source_name,
                    category, title, micro_physical_impact, involved_entities,
                    affected_business_segments, estimated_duration, severity_level,
                    requires_deep_analysis, url, raw_content,
                    credibility_tier, credibility_score, verification_status, verification_note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                summary.event_id,
                item.raw_hash,
                collected_at,
                item.published_at,
                summary.source_name,
                summary.category,
                summary.raw_title,
                summary.micro_physical_impact,
                json.dumps(summary.involved_entities, ensure_ascii=False),
                json.dumps(summary.affected_business_segments, ensure_ascii=False),
                summary.estimated_duration,
                summary.severity_level,
                1 if summary.requires_deep_analysis else 0,
                item.url,
                item.content[:2000],
                getattr(summary, "credibility_tier", "Tier3_Mainstream_Wire"),
                float(getattr(summary, "credibility_score", 0.8)),
                getattr(summary, "verification_status", "Corroborated_Report"),
                getattr(summary, "verification_note", "主流财经通讯社通告"),
            ))
            conn.commit()

    def insert_cycle(self, cycle_report: Dict[str, Any]) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cycle_id = f"CYCLE_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')[:19]}"
            cursor.execute("""
                INSERT OR REPLACE INTO collection_cycles (
                    cycle_id, cycle_timestamp, market_session, status,
                    active_probe_node, probe_latency_ms, scanned_count,
                    filtered_in_count, summarized_count, p0_p1_triggered_count,
                    estimated_tokens_consumed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cycle_id,
                cycle_report.get("timestamp", datetime.now(timezone.utc).isoformat()),
                cycle_report.get("market_session", "unknown"),
                cycle_report.get("status", "SUCCESS"),
                cycle_report.get("active_probe_node", "UNKNOWN"),
                float(cycle_report.get("probe_latency_ms", 0.0)),
                int(cycle_report.get("scanned_count", 0)),
                int(cycle_report.get("filtered_in_count", 0)),
                int(cycle_report.get("summarized_count", 0)),
                int(cycle_report.get("p0_p1_triggered_count", 0)),
                int(cycle_report.get("estimated_tokens_consumed", 0)),
            ))
            conn.commit()

    def query_events(
        self,
        severity_filter: Optional[List[str]] = None,
        category: Optional[str] = None,
        only_requires_deep: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM radar_events WHERE 1=1"
        params: List[Any] = []
        if severity_filter:
            placeholders = ",".join(["?"] * len(severity_filter))
            query += f" AND severity_level IN ({placeholders})"
            params.extend(severity_filter)
        if category:
            query += " AND category = ?"
            params.append(category)
        if only_requires_deep:
            query += " AND requires_deep_analysis = 1"
        query += " ORDER BY published_at DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            results = []
            for row in rows:
                item = dict(row)
                try:
                    item["involved_entities"] = json.loads(item.get("involved_entities", "[]"))
                except Exception:
                    item["involved_entities"] = []
                try:
                    item["affected_business_segments"] = json.loads(item.get("affected_business_segments", "[]"))
                except Exception:
                    item["affected_business_segments"] = []
                item["requires_deep_analysis"] = bool(item.get("requires_deep_analysis", 0))
                results.append(item)
            return results

    def query_cycles(self, limit: int = 20) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM collection_cycles ORDER BY cycle_timestamp DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def query_summary_statistics(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), SUM(requires_deep_analysis) FROM radar_events")
            res_events = cursor.fetchone()
            total_events = res_events[0] if res_events else 0
            total_major = res_events[1] if res_events and res_events[1] else 0

            cursor.execute("SELECT COUNT(*), SUM(scanned_count), SUM(summarized_count), SUM(estimated_tokens_consumed) FROM collection_cycles")
            res_cycles = cursor.fetchone()
            total_cycles = res_cycles[0] if res_cycles else 0
            total_scanned = res_cycles[1] if res_cycles and res_cycles[1] else 0
            total_summarized = res_cycles[2] if res_cycles and res_cycles[2] else 0
            total_tokens = res_cycles[3] if res_cycles and res_cycles[3] else 0

            return {
                "total_events_stored": total_events or 0,
                "total_major_p0_p1": total_major or 0,
                "total_cycles_executed": total_cycles or 0,
                "total_scanned_news": total_scanned or 0,
                "total_summarized": total_summarized or 0,
                "total_tokens_burned": total_tokens or 0,
            }

    def confirm_event_verification(
        self,
        event_id: str,
        evidence_path: str,
        evidence_sha256: str,
        verified_at: str,
        note: Optional[str] = None,
    ) -> bool:
        """完成官方凭据核验并执行信源提级与传闻熔断解除 (买方闭环)."""
        actual_note = note or "经官方监管/交易所/当事方公报原文比对核实，解除传闻熔断"
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE radar_events
                SET verification_status = 'Confirmed_Fact',
                    credibility_tier = 'Tier1_Official_Regulatory',
                    credibility_score = 1.0,
                    requires_deep_analysis = 1,
                    evidence_path = ?,
                    evidence_sha256 = ?,
                    verified_at = ?,
                    verification_note = ?
                WHERE event_id = ?
            """, (evidence_path, evidence_sha256, verified_at, actual_note, event_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """依据事件 ID 精确提取单条事实底账."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM radar_events WHERE event_id = ?", (event_id,))
            row = cursor.fetchone()
            if not row:
                return None
            item = dict(row)
            try:
                item["involved_entities"] = json.loads(item.get("involved_entities", "[]"))
            except Exception:
                item["involved_entities"] = []
            try:
                item["affected_business_segments"] = json.loads(item.get("affected_business_segments", "[]"))
            except Exception:
                item["affected_business_segments"] = []
            item["requires_deep_analysis"] = bool(item.get("requires_deep_analysis", 0))
            return item

    def list_critical_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """查询已确认的 P0/P1 重大事件 (用于买方实战监控)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM radar_events
                WHERE severity_level IN ('P0', 'P1')
                ORDER BY
                    CASE severity_level WHEN 'P0' THEN 1 WHEN 'P1' THEN 2 ELSE 3 END,
                    published_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            results = []
            for row in rows:
                item = dict(row)
                try:
                    item["involved_entities"] = json.loads(item.get("involved_entities", "[]"))
                except Exception:
                    item["involved_entities"] = []
                try:
                    item["affected_business_segments"] = json.loads(item.get("affected_business_segments", "[]"))
                except Exception:
                    item["affected_business_segments"] = []
                item["requires_deep_analysis"] = bool(item.get("requires_deep_analysis", 0))
                results.append(item)
            return results


class MockModelSummarizer:
    """测试与沙箱环境下的确定性 2-B 结构化摘要生成器 (零成本 Mock)."""

    def generate_summary_json(self, prompt_payload: Dict[str, str], fallback_item: RawNewsItem) -> str:
        """基于快讯事实确定性构造标准的 2-B JSON 输出."""
        title_lower = fallback_item.title.lower()
        content_lower = fallback_item.content.lower()

        entities = ["未知实体"]
        impact = fallback_item.title
        category = "Other_Macro_Event"
        severity = "P2"
        duration = "短期"
        segments = ["通用产业"]

        if "罢工" in title_lower or "码头工人" in title_lower or "strike" in title_lower or "ila" in title_lower or "ilwu" in title_lower:
            category = "Labor_Strikes_Port_Railways"
            entities = ["国际码头工人协会(ILA)", "美东各大港口海事联盟", "集装箱航运枢纽"]
            impact = "美东与墨西哥湾主要港口码头工人宣布全线罢工，集装箱装卸业务停摆，运力周转受阻"
            severity = "P1"
            duration = "中期 2~4 周"
            segments = ["海运物流与货运代理", "港口装卸", "跨国供应链库存"]
        elif "反垄断" in title_lower or "antitrust" in title_lower or "337调查" in title_lower or "itc" in title_lower or "ftc" in title_lower or "doj" in title_lower:
            category = "Antitrust_Litigation"
            entities = ["美国司法部反垄断局", "联邦贸易委员会(FTC)", "国际贸易委员会(ITC)"]
            impact = "监管机构正式发起反垄断重组调查或针对核心专利侵权启动 337 调查及有限排除令"
            severity = "P1"
            duration = "长期司法诉讼 1~2 年"
            segments = ["数字广告与搜索引擎", "平台应用生态", "知识产权许可"]
        elif "战略石油储备" in title_lower or "spr" in title_lower or "现货升水" in title_lower or "倒挂" in title_lower or "backwardation" in title_lower or "逼仓" in title_lower:
            category = "Commodity_Physical_Squeeze"
            entities = ["美国能源部(DOE)", "LME实物交割仓", "大宗商品贸易商"]
            impact = "能源部宣布战略石油储备招标轮换或关键大宗实物仓单注销激增，现货期限结构深度倒挂"
            severity = "P1"
            duration = "中短期 1~3 个月"
            segments = ["上游油气开采与炼化", "基础金属冶炼", "大宗商品仓储"]
        elif "贴现窗口" in title_lower or "srf" in title_lower or "套息平仓" in title_lower or "carry trade" in title_lower or "日元" in title_lower or "流动性" in title_lower:
            category = "CentralBank_Liquidity_FX_Shock"
            entities = ["美联储公开市场操作台", "日本央行(BoJ)", "跨国对冲基金"]
            impact = "央行紧急贴现窗口调用突增或日元非线性暴力升值触发全球跨资产套息交易快速平仓拆解"
            severity = "P0"
            duration = "短期高烈度冲击 1~2 周"
            segments = ["投资银行与经纪业务", "跨国宏观量化基金", "高杠杆成长资产"]
        elif "红海" in title_lower or "苏伊士" in title_lower or "suez" in title_lower or "曼德海峡" in title_lower or "巴拿马运河" in title_lower or "panama" in title_lower:
            category = "Supply_Chain_Chokepoint"
            entities = ["全球航运巨头", "运河管理局", "苏伊士/巴拿马咽喉"]
            impact = "关键国际海运咽喉因地缘冲突或枯水期吃水限制被迫大面积绕航好望角，远洋航程与燃油附加费飙升"
            severity = "P1"
            duration = "中期 2~6 个月"
            segments = ["远洋集装箱海运", "干散货与油轮运输", "跨国制造业原料库存"]
        elif "加州" in title_lower or "california" in title_lower:
            category = "State_Policy_Regulatory"
            entities = ["加州能源委员会", "商业算力中心", "公用电网"]
            impact = "加州通过电网负荷新规，对50MW以上商业算力中心加征电网基础设施维护费"
            severity = "P1"
            duration = "长期法定政策"
            segments = ["云计算基础设施", "电力与公用事业"]
        elif "德州" in title_lower or "texas" in title_lower:
            category = "State_Policy_Regulatory"
            entities = ["德州立法会", "半导体制造企业"]
            impact = "德州通过半导体本土晶圆制造税收补贴激励修正案"
            severity = "P1"
            duration = "长期税收法案"
            segments = ["半导体晶圆制造", "先进封测"]
        elif "爆炸" in title_lower or "explosion" in title_lower or "fire" in title_lower or "火灾" in title_lower:
            category = "Physical_Plant_Disruption"
            entities = ["核心化工特种材料厂", "上游原料供应商"]
            impact = "特种树脂与光刻胶关键前驱体生产车间发生突发火灾，预计全面停产检修"
            severity = "P1"
            duration = "中期 1~3 个月"
            segments = ["特种电子化学品", "先进芯片制造代工"]
        elif "蓝营" in title_lower or "出口管制" in title_lower or "sanction" in title_lower or "制裁" in title_lower:
            category = "Geopolitical_CrossStrait"
            entities = ["商务部出口管制局", "关键芯片设计厂商"]
            impact = "突发地缘经贸摩擦升级，宣布对高端芯片先进制程供应链实施定向出口管制审查"
            severity = "P0"
            duration = "不可抗力中长期"
            segments = ["先进制程芯片设计", "全球代工供应链"]
        elif "限电" in title_lower or "电网" in title_lower or "寒潮" in title_lower or "气井" in title_lower:
            category = "Energy_Grid_Blackout_Rationing"
            entities = ["区域电网独立调度中心(NERC/ERCOT)", "工业高耗能产业", "商业算力中心"]
            impact = "极端气候导致气井冻结与电网跳闸，启动紧急负荷削减及工业限电"
            severity = "P1"
            duration = "短期 1~2 周"
            segments = ["电解铝与基础工业冶炼", "算力基础设施", "电力与燃气公用事业"]
        elif "工控" in title_lower or "勒索" in title_lower or "cisa" in title_lower or "蓝屏" in title_lower:
            category = "Cyber_Critical_Infrastructure"
            entities = ["关键基础设施运营方", "国家网络安全应急机构(CISA)"]
            impact = "要害工业控制系统或底层驱动发生严重故障瘫痪，交通与物流调度停滞"
            severity = "P1"
            duration = "突发短期数天"
            segments = ["自动化码头与港口", "工业控制与SCADA", "航空调度与金融清算"]
        elif "生物安全" in title_lower or "biosecure" in title_lower or "cxo" in title_lower or "原料药" in title_lower:
            category = "Biosecurity_Export_Embargo"
            entities = ["美国国会立法委员会", "FDA进出口合规司", "跨国CXO企业"]
            impact = "生物安全法案立法推进或FDA发布进口警报，限制跨国临床研发技术转移与原料药清关"
            severity = "P1"
            duration = "中长期 6~18 个月"
            segments = ["合同研发与生产组织(CXO)", "创新药临床管线", "特色原料药API"]
        elif "双用途" in title_lower or "锗镓" in title_lower or "锑矿" in title_lower or "矿产" in title_lower or "rkab" in title_lower:
            category = "Critical_Minerals_Export_Permit"
            entities = ["商务部海关总署", "印尼能矿部(ESDM)", "战略矿产开采加工企业"]
            impact = "主管机构收紧两用物项出口许可证审批或海外矿产开采配额延迟，现货升水急剧攀升"
            severity = "P1"
            duration = "中长期 3~12 个月"
            segments = ["半导体衬底材料", "军工与红外光学", "动力电池与储能材料"]
        elif "ndaa" in title_lower or "国防授权" in title_lower or "五角大楼" in title_lower or "军售" in title_lower or "dsca" in title_lower:
            category = "Defense_Procurement_Authorization"
            entities = ["美国国防部(DoD)", "国防安全合作局(DSCA)", "主承包防务商"]
            impact = "国防授权法案增订特别采购额度或重大对外军售批复放行，锁定特种军规产能"
            severity = "P1"
            duration = "跨财年长期 2~4 年"
            segments = ["特种军规芯片", "航空航天与防务", "特种先进复合材料"]
        elif "飓风" in title_lower or "hurricane" in title_lower or "炼化" in title_lower or "航天" in title_lower or "noaa" in title_lower:
            category = "Climate_Catastrophe_Insurance"
            entities = ["美国国家飓风中心(NHC/NOAA)", "沿海石化基地", "商业航天发射场"]
            impact = "极端气候飓风登陆导致沿海炼油重镇跳车关停，且巨灾再保险免赔额拉升"
            severity = "P1"
            duration = "短期物理冲击 2~4 周"
            segments = ["炼油与裂解化学品", "财产与巨灾再保险", "商业航天遥感与通信"]
        elif "保赔" in title_lower or "p&i" in title_lower or "战争险" in title_lower or "影子船队" in title_lower or "价格上限" in title_lower:
            category = "Maritime_Insurance_Sanctions"
            entities = ["国际保赔协会集团(IG P&I)", "联合战争委员会(JWC)", "远洋油轮合规船东"]
            impact = "战险附加保费暴涨或违反价格上限遭扣押，航行经济性恶化引发有效运力紧缩"
            severity = "P1"
            duration = "中期 1~6 个月"
            segments = ["合规远洋油运与干散货", "海事特种保险", "跨大洋原油流转"]
        elif "债务上限" in title_lower or "debt ceiling" in title_lower or "tga" in title_lower or "拍卖尾部" in title_lower or "auction tail" in title_lower:
            category = "Sovereign_Debt_Liquidity"
            entities = ["美国财政部(Treasury)", "一级交易商", "银行间回购市场"]
            impact = "债务上限博弈或国债拍卖尾部拉大，占用交易商负债表并收紧跨资产抵押流动性"
            severity = "P1"
            duration = "中期流动性脉冲 1~3 个月"
            segments = ["银行间质押回购(Repo)", "高贝塔成长股估值", "跨国固定收益流动性"]

        summary_dict = {
            "category": category,
            "involved_entities": entities,
            "micro_physical_impact": impact,
            "estimated_duration": duration,
            "affected_business_segments": segments,
            "severity_level": severity,
        }
        return json.dumps(summary_dict, ensure_ascii=False)


def parse_rss_atom_feed(xml_content: str, default_source: str = "Official_Regulatory_RSS") -> List[RawNewsItem]:
    """轻量解析公开标准 RSS 2.0 / Atom 1.0 XML 格式数据源 (零 Token 消耗、零外部依赖).

    严格遵循《2026-10-11 最新数据来源策略》:
    仅处理公开无需鉴权的公开公报 feed，提取标题、摘要内容、链接与时间戳，转化为 RawNewsItem。
    """
    items: List[RawNewsItem] = []
    if not xml_content or not xml_content.strip():
        return items

    try:
        root = ET.fromstring(xml_content)
    except Exception as e:
        logger.warning("解析 XML Feed 失败: %s", e)
        return items

    # 1. 尝试 RSS 2.0: <rss><channel><item>...
    channel = root.find("channel")
    if channel is not None:
        feed_title = channel.findtext("title") or default_source
        for idx, item in enumerate(channel.findall("item")):
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            description = item.findtext("description") or ""
            pub_date = item.findtext("pubDate") or datetime.now(timezone.utc).isoformat()
            guid = item.findtext("guid") or f"rss_{idx}_{int(time.time())}"

            if title:
                items.append(RawNewsItem(
                    id=str(guid),
                    title=title.strip(),
                    content=description.strip() or title.strip(),
                    source=feed_title.strip(),
                    published_at=pub_date.strip(),
                    url=link.strip(),
                ))
        return items

    # 2. 尝试 Atom 1.0: <feed xmlns="http://www.w3.org/2005/Atom"><entry>...
    # 处理 Atom 命名空间
    tag = root.tag
    ns = ""
    if "}" in tag:
        ns = tag.split("}")[0] + "}"

    feed_title_elem = root.find(f"{ns}title")
    feed_title = feed_title_elem.text if feed_title_elem is not None and feed_title_elem.text else default_source

    for idx, entry in enumerate(root.findall(f"{ns}entry")):
        title_elem = entry.find(f"{ns}title")
        title = title_elem.text if title_elem is not None and title_elem.text else ""

        id_elem = entry.find(f"{ns}id")
        entry_id = id_elem.text if id_elem is not None and id_elem.text else f"atom_{idx}_{int(time.time())}"

        updated_elem = entry.find(f"{ns}updated") or entry.find(f"{ns}published")
        pub_date = updated_elem.text if updated_elem is not None and updated_elem.text else datetime.now(timezone.utc).isoformat()

        link_elem = entry.find(f"{ns}link")
        link = link_elem.get("href", "") if link_elem is not None else ""

        content_elem = entry.find(f"{ns}content") or entry.find(f"{ns}summary")
        content = content_elem.text if content_elem is not None and content_elem.text else title

        if title:
            items.append(RawNewsItem(
                id=str(entry_id),
                title=title.strip(),
                content=(content or title).strip(),
                source=feed_title.strip(),
                published_at=pub_date.strip(),
                url=link.strip(),
            ))

    return items


class EventRadarCollector:
    """事件雷达高频收集与调度器."""

    def __init__(
        self,
        config_path: str = "config/event_radar_sources.json",
        watchdog: Optional[NetworkHealthWatchdog] = None,
        progress_manager: Optional[RadarProgressManager] = None,
        database_manager: Optional[RadarDatabaseManager] = None,
        model_client: Optional[Any] = None,
    ):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self._load_config()

        self.engine = EventRadarEngine(self.config)

        # 依赖注入或使用默认组件
        watchdog_cfg = self.config.get("network_watchdog", {})
        self.watchdog = watchdog or NetworkHealthWatchdog(
            probe_endpoints=watchdog_cfg.get("probe_endpoints"),
            timeout_sec=watchdog_cfg.get("timeout_seconds", 1.5),
            max_offline_retries=watchdog_cfg.get("max_offline_retries", 5),
            backoff_intervals=watchdog_cfg.get("backoff_intervals_seconds"),
        )

        prog_cfg = self.config.get("progress_management", {})
        ckpt_file = prog_cfg.get("checkpoint_file", "data/ledger/event_radar_checkpoint.json")
        self.progress_mgr = progress_manager or RadarProgressManager(
            checkpoint_path=ckpt_file,
            max_hash_history_size=prog_cfg.get("max_hash_history_size", 10000),
        )

        db_file = prog_cfg.get("database_file", "data/ledger/event_radar.sqlite3")
        self.db_mgr = database_manager or RadarDatabaseManager(db_path=db_file)

        self.model_client = model_client or MockModelSummarizer()

    def _load_config(self) -> None:
        if self.config_path.is_file():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            except Exception as e:
                logger.warning("读取配置文件异常: %s", e)

    def determine_trading_session(self, ref_time: Optional[datetime] = None) -> Tuple[str, int]:
        """依据美东时间与交易日历确定当前交易时段与自适应巡检频次 (分钟)."""
        now_utc = ref_time or datetime.now(timezone.utc)
        # 美东时间 (EDT 通常为 UTC-4，EST 为 UTC-5，此处按 UTC-4 近似)
        edt_hour = (now_utc.hour - 4) % 24
        edt_minute = now_utc.minute
        weekday = now_utc.weekday()  # 0=Monday, 6=Sunday

        intervals = self.config.get("scheduler", {}).get("polling_intervals_minutes", {})
        pre_m = intervals.get("pre_market", 5)
        reg_m = intervals.get("regular_market", 15)
        post_m = intervals.get("after_hours", 30)
        closed_m = intervals.get("market_closed", 60)

        # 周六、周日休市
        if weekday >= 5:
            return "market_closed", closed_m

        current_minutes = edt_hour * 60 + edt_minute
        # 盘前 Pre-Market: 04:00 - 09:30 (240 - 570 分钟)
        if 240 <= current_minutes < 570:
            return "pre_market", pre_m
        # 盘中 Regular Trading: 09:30 - 16:00 (570 - 960 分钟)
        elif 570 <= current_minutes < 960:
            return "regular_market", reg_m
        # 盘后 After-Hours: 16:00 - 20:00 (960 - 1200 分钟)
        elif 960 <= current_minutes < 1200:
            return "after_hours", post_m
        else:
            return "market_closed", closed_m

    def run_collection_cycle(
        self,
        raw_feed_items: Optional[List[Dict[str, Any]]] = None,
        force_offline_simulation: bool = False,
    ) -> Dict[str, Any]:
        """执行单轮次原子信息收集与事件门禁处理循环."""
        cycle_start_iso = datetime.now(timezone.utc).isoformat()
        session_name, recommended_interval = self.determine_trading_session()

        # 1. 前置自发断网自检 (Network Health Check)
        if force_offline_simulation:
            is_online = False
            active_node = "SIMULATED_OFFLINE"
            latency = -1.0
        else:
            is_online, active_node, latency = self.watchdog.check_connectivity()

        if not is_online:
            # 启动断网自治等待重试
            recovered = self.watchdog.wait_for_recovery()
            if not recovered:
                return {
                    "status": "OFFLINE_HOLD",
                    "timestamp": cycle_start_iso,
                    "market_session": session_name,
                    "message": "网络处于断开状态，看门狗已安全挂起并等待，无抛错闪退。",
                    "scanned_count": 0,
                    "filtered_in_count": 0,
                    "summarized_count": 0,
                    "p0_p1_triggered_count": 0,
                    "triggered_events": [],
                    "estimated_tokens_consumed": 0,
                }

        # 2. 准备原始资讯流 (若未外部传入则为空列表或测试用例)
        items_to_scan = raw_feed_items or []
        cycle_metrics = {
            "scanned": len(items_to_scan),
            "filtered_in": 0,
            "summarized": 0,
            "p0_p1_triggered": 0,
            "estimated_tokens": 0,
        }

        triggered_events: List[Dict[str, Any]] = []

        # 3. 逐条流式穿透四级漏斗
        for raw_dict in items_to_scan:
            item = RawNewsItem(
                id=str(raw_dict.get("id", "")),
                title=str(raw_dict.get("title", "")),
                content=str(raw_dict.get("content", "")),
                source=str(raw_dict.get("source", "Public_Feed")),
                published_at=str(raw_dict.get("published_at", cycle_start_iso)),
                url=str(raw_dict.get("url", "")),
            )

            # 漏斗第 1 级：SHA-256 唯一指纹幂等排重 (0 Token)
            if self.progress_mgr.is_hash_processed(item.raw_hash):
                continue

            # 漏斗第 2 级：物理去噪与实体词典命中初筛 (0 Token)
            matched, tags, likely_cat = self.engine.pre_filter(item)
            if not matched:
                # 记录为已处理指纹，防止重复扫描无关新闻
                self.progress_mgr.record_processed_hash(item.raw_hash)
                continue

            cycle_metrics["filtered_in"] += 1

            # 漏斗第 3 级：选项 2-B 统一微型模型摘要生成 (约 80~120 Token/条)
            prompt_payload = self.engine.build_summary_prompt(item, likely_cat)
            if hasattr(self.model_client, "generate_summary_json"):
                model_raw_json = self.model_client.generate_summary_json(prompt_payload, item)
            else:
                model_raw_json = json.dumps({
                    "category": likely_cat.value,
                    "involved_entities": [item.source],
                    "micro_physical_impact": item.title,
                    "estimated_duration": "短期",
                    "affected_business_segments": ["核心业务"],
                    "severity_level": "P2",
                })

            cycle_metrics["summarized"] += 1
            cycle_metrics["estimated_tokens"] += 110  # 选项 2-B 紧凑 JSON 单条预估消耗

            # 刚性校验与事件烈度分类
            summary = self.engine.parse_and_validate_summary(model_raw_json, item, likely_cat)

            # 持久化写入 SQLite 数据库
            self.db_mgr.insert_event(summary, item, cycle_start_iso)

            # 漏斗第 4 级：重大事件触发门禁
            if summary.requires_deep_analysis:
                cycle_metrics["p0_p1_triggered"] += 1
                triggered_events.append(summary.to_dict())

            # 记录处理完成的哈希
            self.progress_mgr.record_processed_hash(item.raw_hash)

        # 4. 原子安全保存断点账本
        self.progress_mgr.save_checkpoint(
            current_timestamp=cycle_start_iso,
            cycle_metrics=cycle_metrics,
            new_triggered_events=triggered_events,
        )

        cycle_report = {
            "status": "SUCCESS",
            "timestamp": cycle_start_iso,
            "market_session": session_name,
            "active_probe_node": active_node,
            "probe_latency_ms": latency,
            "recommended_interval_minutes": recommended_interval,
            "scanned_count": cycle_metrics["scanned"],
            "filtered_in_count": cycle_metrics["filtered_in"],
            "summarized_count": cycle_metrics["summarized"],
            "p0_p1_triggered_count": cycle_metrics["p0_p1_triggered"],
            "triggered_events": triggered_events,
            "estimated_tokens_consumed": cycle_metrics["estimated_tokens"],
            "checkpoint_saved": True,
            "db_persisted": True,
        }

        # 写入巡检轮次历史底账
        self.db_mgr.insert_cycle(cycle_report)

        return cycle_report

    def query_stored_events(
        self,
        severity_filter: Optional[List[str]] = None,
        category: Optional[str] = None,
        only_requires_deep: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """从 SQLite 数据库查询历史收集事件."""
        return self.db_mgr.query_events(
            severity_filter=severity_filter,
            category=category,
            only_requires_deep=only_requires_deep,
            limit=limit,
        )

    def query_stored_cycles(self, limit: int = 20) -> List[Dict[str, Any]]:
        """从 SQLite 数据库查询历史巡检轮次记录."""
        return self.db_mgr.query_cycles(limit=limit)

    def query_stored_statistics(self) -> Dict[str, Any]:
        """从 SQLite 数据库查询全量累计统计指标."""
        return self.db_mgr.query_summary_statistics()
