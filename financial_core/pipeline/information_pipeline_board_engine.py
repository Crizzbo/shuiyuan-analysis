# -*- coding: utf-8 -*-
"""信息流水线看板核心引擎与状态管理机 (information_pipeline_board_engine.py).

遵循《CLAUDE.md》与《AGENTS.md》四层单向解耦规范：
1. 单一事实来源 (SSOT)：定义标准流水线消息契约、流转阶段状态机与多维过滤逻辑；
2. 进程状态全生命周期管理：待接入 (PENDING) -> 接入中 (INGESTING) -> 处理中 (PROCESSING) -> 完成 (COMPLETED) / 阻断 (BLOCKED) / 重试 (RETRYING)；
3. 日期时序降序排序：所有消息与看板泳道严格以毫秒/秒级准确时间戳倒序排列，最新动态第一时间呈现；
4. 纯净解耦：本模块位于底层核心层 (financial_core/pipeline)，严禁逆向依赖外层脚本或工具。
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple


class ProcessStageStatus(str, Enum):
    """流水线任务处理进程状态枚举 (去工程符号化，贴近业务实质)."""
    PENDING = "pending"          # 待接入排队
    INGESTING = "ingesting"      # 数据抓取/接入中
    PROCESSING = "processing"    # 特征计算/清洗中
    COMPLETED = "completed"      # 流转完成已落盘
    BLOCKED = "blocked"          # 异常阻断/时效不符
    RETRYING = "retrying"        # 自动重试调度中


class PipelineCategory(str, Enum):
    """信息流水线业务模块类别."""
    EVENT_RADAR = "event_radar"           # 突发舆情与新闻雷达
    MARKET_QUOTE = "market_quote"         # 行情时效与时钟门禁
    FILING_AUDIT = "filing_audit"         # 官方财报平账与法证
    QUANT_VALUATION = "quant_valuation"   # 商业物理与情景估值
    REPORT_DISPATCH = "report_dispatch"   # 研报卡片与云端同步


class PipelineSeverity(str, Enum):
    """消息优先级与警报严重程度."""
    CRITICAL = "critical"   # 致命级 (如平账失衡、破产预警、假账嫌疑)
    HIGH = "high"           # 严重级 (如行情严重延迟、突发黑天鹅跌破底价)
    MEDIUM = "medium"       # 中度级 (如波动率异动、动能减速滑行)
    LOW = "low"             # 常规级 (如日常例行快照、正常完成落盘)


@dataclass
class PipelineMessageItem:
    """标准流水线消息条目契约 (SSOT)."""
    item_id: str
    title: str
    category: str
    severity: str
    stage_status: str
    timestamp: str                       # ISO 8601 UTC 时间戳 (如 2026-11-10T08:30:00Z)
    ticker: Optional[str] = None         # 关联合约/标的代码 (如 NVDA, AAPL, SPY)
    company_name_zh: Optional[str] = None# 公司/指数中文名称
    source: str = "Internal System"      # 信源或触发模块 (如 SEC EDGAR, Google Finance, Event Radar)
    progress_pct: int = 0                # 0 ~ 100 处理进度百分比
    duration_ms: int = 0                 # 累计流转耗时 (毫秒)
    payload: Dict[str, Any] = field(default_factory=dict) # 业务结构化数据底账
    logs: List[str] = field(default_factory=list)         # 执行流流水日志
    error_message: Optional[str] = None  # 若异常阻断时的详细原因
    sha256_fingerprint: str = ""         # 密码学防伪签名

    def __post_init__(self):
        if not self.sha256_fingerprint:
            raw_text = f"{self.item_id}:{self.timestamp}:{self.title}:{self.category}:{self.severity}"
            self.sha256_fingerprint = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineMessageItem":
        clean_data = data.copy()
        return cls(**clean_data)


class InformationPipelineBoardEngine:
    """信息流水线看板核心逻辑与状态管理器."""

    def __init__(self, initial_messages: Optional[List[PipelineMessageItem]] = None):
        self._store: Dict[str, PipelineMessageItem] = {}
        if initial_messages:
            for item in initial_messages:
                self._store[item.item_id] = item
        else:
            self._load_seed_market_pipeline_data()

    def register_message(
        self,
        item_id: str,
        title: str,
        category: str,
        severity: str,
        stage_status: str = ProcessStageStatus.PENDING.value,
        timestamp: Optional[str] = None,
        ticker: Optional[str] = None,
        company_name_zh: Optional[str] = None,
        source: str = "System Flow",
        progress_pct: int = 0,
        duration_ms: int = 0,
        payload: Optional[Dict[str, Any]] = None,
        initial_log: Optional[str] = None,
    ) -> PipelineMessageItem:
        """登记一条全新流水线消息进入看板."""
        now_ts = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        logs = [f"[{now_ts}] 任务登记就绪，进入待接入队列: {title}"]
        if initial_log:
            logs.append(f"[{now_ts}] {initial_log}")

        item = PipelineMessageItem(
            item_id=item_id,
            title=title,
            category=category,
            severity=severity,
            stage_status=stage_status,
            timestamp=now_ts,
            ticker=ticker,
            company_name_zh=company_name_zh,
            source=source,
            progress_pct=progress_pct,
            duration_ms=duration_ms,
            payload=payload or {},
            logs=logs,
        )
        self._store[item_id] = item
        return item

    def advance_status(
        self,
        item_id: str,
        new_status: ProcessStageStatus,
        progress_pct: Optional[int] = None,
        log_entry: Optional[str] = None,
        error_message: Optional[str] = None,
        added_duration_ms: int = 0,
    ) -> PipelineMessageItem:
        """推进或流转任务进程状态."""
        if item_id not in self._store:
            raise KeyError(f"找不到流水线任务 ID: {item_id}")

        item = self._store[item_id]
        item.stage_status = new_status.value
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if progress_pct is not None:
            item.progress_pct = max(0, min(100, progress_pct))
        item.duration_ms += added_duration_ms

        if error_message:
            item.error_message = error_message

        status_zh = {
            ProcessStageStatus.PENDING.value: "进入待接入排队",
            ProcessStageStatus.INGESTING.value: "正在抓取外部事实",
            ProcessStageStatus.PROCESSING.value: "正在执行特征运算",
            ProcessStageStatus.COMPLETED.value: "已完成并落盘底账",
            ProcessStageStatus.BLOCKED.value: f"遭遇异常阻断: {error_message or '未知错误'}",
            ProcessStageStatus.RETRYING.value: "进入自动重试序列",
        }.get(new_status.value, new_status.value)

        log_text = f"[{now_ts}] 进程状态变更 -> {status_zh}"
        if log_entry:
            log_text += f" ({log_entry})"
        item.logs.append(log_text)

        return item

    def retry_message(self, item_id: str, log_note: str = "手动触发重试") -> PipelineMessageItem:
        """触发重试阻断或异常的任务."""
        if item_id not in self._store:
            raise KeyError(f"找不到流水线任务 ID: {item_id}")
        item = self._store[item_id]
        item.error_message = None
        item.stage_status = ProcessStageStatus.RETRYING.value
        item.progress_pct = 15
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        item.logs.append(f"[{now_ts}] 用户重试控制: {log_note}，重新载入接入调度管道")
        return item

    def kill_message(self, item_id: str, reason: str = "用户手动终止进程") -> PipelineMessageItem:
        """强制终止阻断流水线任务."""
        if item_id not in self._store:
            raise KeyError(f"找不到流水线任务 ID: {item_id}")
        item = self._store[item_id]
        item.stage_status = ProcessStageStatus.BLOCKED.value
        item.error_message = reason
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        item.logs.append(f"[{now_ts}] 任务被强制终止: {reason}")
        return item

    def query_messages(
        self,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        stage_status: Optional[str] = None,
        ticker: Optional[str] = None,
        search_keyword: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """消息筛选核心查询函数 (强制支持日期降序与多维组合筛选).

        Args:
            category: 业务分类过滤
            severity: 严重程度过滤
            stage_status: 进程状态过滤
            ticker: 股票代码过滤
            search_keyword: 标题/日志/来源模糊匹配
            start_date: 起始日期 (ISO 字符串或 YYYY-MM-DD)
            end_date: 截止日期 (ISO 字符串或 YYYY-MM-DD)
            sort_order: 'desc' (日期降序，默认最新在前) 或 'asc' (日期升序)
            page: 当前页码 (从 1 开始)
            page_size: 每页显示条数
        """
        all_items = list(self._store.values())

        # 1. 执行多维过滤
        filtered: List[PipelineMessageItem] = []
        kw = search_keyword.strip().lower() if search_keyword else None

        for it in all_items:
            if category and it.category != category:
                continue
            if severity and it.severity != severity:
                continue
            if stage_status and it.stage_status != stage_status:
                continue
            if ticker and it.ticker and it.ticker.upper() != ticker.upper():
                continue
            if start_date and it.timestamp < start_date:
                continue
            if end_date and it.timestamp > end_date:
                continue
            if kw:
                haystack = f"{it.title} {it.ticker or ''} {it.company_name_zh or ''} {it.source} {' '.join(it.logs)}".lower()
                if kw not in haystack:
                    continue
            filtered.append(it)

        # 2. 执行日期时序排序 (核心规范: 默认绝对降序)
        is_reverse = (sort_order.lower() != "asc")
        filtered.sort(key=lambda x: x.timestamp, reverse=is_reverse)

        # 3. 执行标准分页
        total_count = len(filtered)
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        current_page = max(1, min(page, total_pages))
        start_idx = (current_page - 1) * page_size
        end_idx = start_idx + page_size
        paged_items = filtered[start_idx:end_idx]

        return {
            "total_count": total_count,
            "total_pages": total_pages,
            "current_page": current_page,
            "page_size": page_size,
            "sort_order": "desc" if is_reverse else "asc",
            "items": [it.to_dict() for it in paged_items],
        }

    def get_kanban_board_view(
        self,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        search_keyword: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取四列经典看板泳道视图 (待接入、处理中、已完成、异常阻断)，每列严格按日期降序排列."""
        # 先利用 query_messages 获得全局日期降序的数据集
        query_res = self.query_messages(
            category=category,
            severity=severity,
            search_keyword=search_keyword,
            sort_order="desc",
            page=1,
            page_size=1000,
        )
        items = query_res["items"]

        lanes = {
            "pending": {"title": "待接入排队", "status": ProcessStageStatus.PENDING.value, "items": []},
            "ingesting": {"title": "数据抓取中", "status": ProcessStageStatus.INGESTING.value, "items": []},
            "processing": {"title": "运算清洗中", "status": ProcessStageStatus.PROCESSING.value, "items": []},
            "completed": {"title": "已完成落盘", "status": ProcessStageStatus.COMPLETED.value, "items": []},
            "blocked": {"title": "异常阻断熔断", "status": ProcessStageStatus.BLOCKED.value, "items": []},
        }

        for it in items:
            st = it["stage_status"]
            if st == ProcessStageStatus.RETRYING.value:
                # 重试状态归于抓取中处理
                lanes["ingesting"]["items"].append(it)
            elif st in lanes:
                lanes[st]["items"].append(it)
            else:
                lanes["pending"]["items"].append(it)

        # 汇总各泳道计数
        lane_counts = {k: len(v["items"]) for k, v in lanes.items()}

        return {
            "lanes": lanes,
            "counts": lane_counts,
            "total_active": lane_counts["ingesting"] + lane_counts["processing"],
            "total_blocked": lane_counts["blocked"],
            "total_completed": lane_counts["completed"],
            "total_items": len(items),
        }

    def get_pipeline_health_stats(self) -> Dict[str, Any]:
        """统计信息流水线宏观运行健康度与吞吐指标."""
        items = list(self._store.values())
        total = len(items)
        if total == 0:
            return {
                "total_messages": 0,
                "active_in_flight": 0,
                "completed_count": 0,
                "blocked_count": 0,
                "success_rate_pct": 100.0,
                "avg_duration_ms": 0,
                "category_breakdown": {},
                "severity_breakdown": {},
            }

        completed = sum(1 for it in items if it.stage_status == ProcessStageStatus.COMPLETED.value)
        blocked = sum(1 for it in items if it.stage_status == ProcessStageStatus.BLOCKED.value)
        active = sum(1 for it in items if it.stage_status in (
            ProcessStageStatus.INGESTING.value,
            ProcessStageStatus.PROCESSING.value,
            ProcessStageStatus.RETRYING.value,
        ))

        # 成功率计算 (已完成 / (已完成 + 阻断))
        terminal_total = completed + blocked
        success_rate = round((completed / terminal_total * 100.0), 1) if terminal_total > 0 else 100.0
        avg_dur = round(sum(it.duration_ms for it in items) / total, 1)

        cat_dist: Dict[str, int] = {}
        sev_dist: Dict[str, int] = {}

        for it in items:
            cat_dist[it.category] = cat_dist.get(it.category, 0) + 1
            sev_dist[it.severity] = sev_dist.get(it.severity, 0) + 1

        return {
            "total_messages": total,
            "active_in_flight": active,
            "completed_count": completed,
            "blocked_count": blocked,
            "success_rate_pct": success_rate,
            "avg_duration_ms": avg_dur,
            "category_breakdown": cat_dist,
            "severity_breakdown": sev_dist,
        }

    def _load_seed_market_pipeline_data(self) -> None:
        """加载初始的买方机构级真实情景模拟数据 (涵盖美股/日股真实标的与各阶段流转状态)."""
        seeds = [
            {
                "item_id": "PIPE-20261110-001",
                "title": "英伟达 (NVDA) 算力机柜高频能耗传导与 CoWoS 封装良率突发异动",
                "category": PipelineCategory.EVENT_RADAR.value,
                "severity": PipelineSeverity.HIGH.value,
                "stage_status": ProcessStageStatus.PROCESSING.value,
                "timestamp": "2026-11-10T03:25:12Z",
                "ticker": "NVDA",
                "company_name_zh": "英伟达",
                "source": "Bloomberg & NewsWire",
                "progress_pct": 65,
                "duration_ms": 1420,
                "payload": {"temperature_c": 82, "cowos_yield_pct": 89.4, "sentiment_score": 0.72},
                "logs": [
                    "[2026-11-10T03:25:12Z] 突发事件接入：监测到半导体封装线热力异常报告",
                    "[2026-11-10T03:25:13Z] 启动因果网络推演：正在评估台积电代工传导系数",
                ],
            },
            {
                "item_id": "PIPE-20261110-002",
                "title": "标普 500 ETF (SPY) 盘前时钟门禁校验与价格新鲜度检验",
                "category": PipelineCategory.MARKET_QUOTE.value,
                "severity": PipelineSeverity.LOW.value,
                "stage_status": ProcessStageStatus.COMPLETED.value,
                "timestamp": "2026-11-10T03:20:00Z",
                "ticker": "SPY",
                "company_name_zh": "标普500指数 ETF",
                "source": "Google Finance MCP",
                "progress_pct": 100,
                "duration_ms": 320,
                "payload": {"price": 735.34, "session": "previous_close_baseline", "freshness_pass": True},
                "logs": [
                    "[2026-11-10T03:20:00Z] 发起 Google Finance 行情表核验请求",
                    "[2026-11-10T03:20:01Z] 判定为前一交易日收盘价基准，新鲜度门禁通过落盘",
                ],
            },
            {
                "item_id": "PIPE-20261110-003",
                "title": "苹果公司 (AAPL) 官方 10-K 三表平衡与负营运资金 (-80.5天) 刚性对账",
                "category": PipelineCategory.FILING_AUDIT.value,
                "severity": PipelineSeverity.LOW.value,
                "stage_status": ProcessStageStatus.COMPLETED.value,
                "timestamp": "2026-11-10T03:15:45Z",
                "ticker": "AAPL",
                "company_name_zh": "苹果公司",
                "source": "SEC EDGAR",
                "progress_pct": 100,
                "duration_ms": 890,
                "payload": {"assets": 364980, "liabilities_equity": 364980, "ccc_days": -80.5},
                "logs": [
                    "[2026-11-10T03:15:45Z] SEC 10-K 财报底稿拉取成功",
                    "[2026-11-10T03:15:46Z] 刚性平账方程 Assets == Liabilities + Equity 断言 PASS",
                ],
            },
            {
                "item_id": "PIPE-20261110-004",
                "title": "东京电子 (8035.T) 极端停滞底价 (¥9295) 与当前股价深度低估黄金安全边际重测",
                "category": PipelineCategory.QUANT_VALUATION.value,
                "severity": PipelineSeverity.MEDIUM.value,
                "stage_status": ProcessStageStatus.COMPLETED.value,
                "timestamp": "2026-11-10T03:10:10Z",
                "ticker": "8035",
                "company_name_zh": "东京电子",
                "source": "Universal Dynamics Engine",
                "progress_pct": 100,
                "duration_ms": 650,
                "payload": {"floor_price": 9295.38, "current_price": 4837.0, "gap_pct": -48.0},
                "logs": [
                    "[2026-11-10T03:10:10Z] 启动通用商业物理动力学分析",
                    "[2026-11-10T03:10:11Z] 发现现价较零增长底价折价 -48%，标记为黄金安全垫状态",
                ],
            },
            {
                "item_id": "PIPE-20261110-005",
                "title": "美股大盘波动率指数 (^VIX) 突破 28 警戒线，触发组合吊灯移动止盈风控策略",
                "category": PipelineCategory.MARKET_QUOTE.value,
                "severity": PipelineSeverity.CRITICAL.value,
                "stage_status": ProcessStageStatus.BLOCKED.value,
                "timestamp": "2026-11-10T03:05:30Z",
                "ticker": "^VIX",
                "company_name_zh": "标普波动率指数",
                "source": "CBOE Option Flow",
                "progress_pct": 40,
                "duration_ms": 1100,
                "error_message": "恐慌指数突破 28 警戒上限，自动触发激进加仓熔断",
                "payload": {"vix": 28.18, "threshold": 25.0, "circuit_breaker": "ACTIVE"},
                "logs": [
                    "[2026-11-10T03:05:30Z] 接收到期权大单成交流脉冲",
                    "[2026-11-10T03:05:31Z] [阻断拦截] VIX=28.18 超过 25 阈值，系统自动冻结顺势做多通道",
                ],
            },
            {
                "item_id": "PIPE-20261110-006",
                "title": "SpaceX 星链 450 万用户订阅现金流与星舰复用成本模型分批对账",
                "category": PipelineCategory.QUANT_VALUATION.value,
                "severity": PipelineSeverity.MEDIUM.value,
                "stage_status": ProcessStageStatus.INGESTING.value,
                "timestamp": "2026-11-10T03:00:00Z",
                "ticker": "SPACEX",
                "company_name_zh": "太空探索技术公司",
                "source": "Secondary Tender Offer",
                "progress_pct": 30,
                "duration_ms": 780,
                "payload": {"subscribers": 4500000, "launch_cost_m": 28.0, "valuation_b": 2300},
                "logs": [
                    "[2026-11-10T03:00:00Z] 从非公开市场估值撮合池载入最新出价",
                    "[2026-11-10T03:00:01Z] 正在核算猎鹰 9 号单次发射 $2800 万真实复用边际成本",
                ],
            },
            {
                "item_id": "PIPE-20261110-007",
                "title": "微软 (MSFT) Azure AI 基础设施资本开支与云计算现金流季度折现评估",
                "category": PipelineCategory.FILING_AUDIT.value,
                "severity": PipelineSeverity.LOW.value,
                "stage_status": ProcessStageStatus.PENDING.value,
                "timestamp": "2026-11-10T02:50:00Z",
                "ticker": "MSFT",
                "company_name_zh": "微软",
                "source": "Scheduler Batch",
                "progress_pct": 0,
                "duration_ms": 0,
                "payload": {"capex_m": 44477, "fcf_m": 74071},
                "logs": [
                    "[2026-11-10T02:50:00Z] 定时调度入队，等待可用并发计算槽位",
                ],
            },
            {
                "item_id": "PIPE-20261110-008",
                "title": "今日美日大盘总研报 (Daily Briefing) 买方矢量 HTML 编译与云端流式推送",
                "category": PipelineCategory.REPORT_DISPATCH.value,
                "severity": PipelineSeverity.LOW.value,
                "stage_status": ProcessStageStatus.COMPLETED.value,
                "timestamp": "2026-11-10T02:40:00Z",
                "ticker": "MACRO",
                "company_name_zh": "全球跨资产宏观",
                "source": "Daily Briefing Engine",
                "progress_pct": 100,
                "duration_ms": 2350,
                "payload": {"report_id": "DB-20261110", "drive_sync": "SUCCESS"},
                "logs": [
                    "[2026-11-10T02:40:00Z] Schema 契约校验 100% PASS",
                    "[2026-11-10T02:40:02Z] Google Drive 云端研报库流式同步完成",
                ],
            },
        ]

        for s in seeds:
            item = PipelineMessageItem(
                item_id=s["item_id"],
                title=s["title"],
                category=s["category"],
                severity=s["severity"],
                stage_status=s["stage_status"],
                timestamp=s["timestamp"],
                ticker=s.get("ticker"),
                company_name_zh=s.get("company_name_zh"),
                source=s.get("source", "System Flow"),
                progress_pct=s.get("progress_pct", 0),
                duration_ms=s.get("duration_ms", 0),
                payload=s.get("payload", {}),
                logs=s.get("logs", []),
                error_message=s.get("error_message"),
            )
            self._store[item.item_id] = item
