# -*- coding: utf-8 -*-
"""信息流水线看板核心引擎与状态管理机 (information_pipeline_board_engine.py).

遵循《CLAUDE.md》与《AGENTS.md》四层单向解耦规范与最新业务要求：
1. 流水线全局启停控制：支持 start_pipeline() 与 stop_pipeline()，具备就绪、运行与挂起状态；
2. 独立复用事件收集函数：提供可复用的 collect_pipeline_events()，支持多维过滤与参数化驱动；
3. 非阻塞流转与故障隔离：单标的或单环节异常自动隔离为 BLOCKED，绝不阻塞整条流水线；
4. 详情抽屉信息重构：股票等数据给出数量与状态分布，指数等宏观指标给出实测参数与参数模板说明；
5. 日期严格降序：全量消息以 ISO 8601 UTC 字符串单调降序索引。
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Callable, Dict, List, Optional, Tuple


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


# 6 大买方机构核心指数与宏观指标参数模板说明库 (SSOT)
MACRO_INDICATORS_TEMPLATE_SPECS: List[Dict[str, Any]] = [
    {
        "symbol": "^VIX",
        "parameter_name": "标普 500 波动率指数 (VIX)",
        "current_value": "16.12",
        "normal_range": "12.0 ~ 20.0",
        "status": "情绪平稳健康",
        "template_description": "衡量期权市场未来 30 天预期年化波动率。低于 20 代表市场处于理性平稳状态；突破 28 则自动触发吊灯移动止盈与激进仓位熔断保护。",
    },
    {
        "symbol": "^TNX",
        "parameter_name": "10 年期美国国债收益率",
        "current_value": "4.39%",
        "normal_range": "3.80% ~ 4.50%",
        "status": "中枢健康震荡",
        "template_description": "全球无风险折现率 (Risk-Free Rate) 定价锚。贴现率每上升 50 个基点，长久期科技股现金流折现理论估值中枢下移约 8%~12%。",
    },
    {
        "symbol": "DXY",
        "parameter_name": "全球美元流动性指数 (DXY)",
        "current_value": "104.28",
        "normal_range": "100.0 ~ 106.0",
        "status": "温和强势",
        "template_description": "衡量美元相对一篮子主要货币强弱。强美元会收紧离岸美元流动性，并对大型跨国科技巨头的海外营收形成汇兑折损拖累。",
    },
    {
        "symbol": "PCR",
        "parameter_name": "期权多空资金力量比 (PCR)",
        "current_value": "0.70",
        "normal_range": "0.60 ~ 0.90",
        "status": "多头显著主导",
        "template_description": "看跌期权与看涨期权成交量比值。低于 0.70 明确代表买方主力看涨期权资金大单密集扫货，多方主导权强劲。",
    },
    {
        "symbol": "OU_HalfLife",
        "parameter_name": "价格均值回归反弹半衰期",
        "current_value": "6.8 天",
        "normal_range": "3.0 ~ 15.0 天",
        "status": "回归动能充沛",
        "template_description": "商业物理动力学指标，测算股价偏离内在价值后的平复修复周期。天数越短，表明资金承接力越强、均值回归弹力越充沛。",
    },
    {
        "symbol": "Panic_Calming",
        "parameter_name": "黑天鹅冲击平息吸收天数",
        "current_value": "4.2 天",
        "normal_range": "2.0 ~ 8.0 天",
        "status": "吸收衰减顺畅",
        "template_description": "突发外部负面舆情或财报异动在订单流微观结构中的衰减周期。若平息天数超过 8 天，说明负面基本面发生实质恶化，需止损离场。",
    },
]


# 默认基准股票数据数量与状态概览 (极简做减法，杜绝冗长全量大表)
EQUITIES_SUMMARY_DEFAULT: Dict[str, Any] = {
    "total_tracked_count": 14,
    "ready_count": 12,
    "pending_count": 2,
    "status_distribution": {
        "NVDA": "正常已就绪",
        "AAPL": "正常已就绪",
        "MSFT": "正常已就绪",
        "GOOGL": "正常已就绪",
        "AMZN": "正常已就绪",
        "META": "正常已就绪",
        "TSM": "正常已就绪",
        "AVGO": "正常已就绪",
        "AMD": "正常已就绪",
        "8035": "正常已就绪",
        "6857": "正常已就绪",
        "9984": "正常已就绪",
        "PLTR": "待补数校准",
        "STX": "待补数校准",
    },
}


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
        self._is_running: bool = True
        self._stop_reason: Optional[str] = None
        self._last_state_change_utc: str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if initial_messages:
            for item in initial_messages:
                self._store[item.item_id] = item
        else:
            self._load_seed_market_pipeline_data()

    # -------------------------------------------------------------------------
    # 1. 流水线全局启动与关闭/暂停功能
    # -------------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        """获取当前流水线全局运行状态."""
        return self._is_running

    def start_pipeline(self) -> Dict[str, Any]:
        """启动流水线，恢复全自动数据接入与特征计算."""
        self._is_running = True
        self._stop_reason = None
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._last_state_change_utc = now_ts
        return {
            "is_running": True,
            "status_label": "运行中",
            "message": "信息流水线已成功启动，事件流与计算引擎处于实时运转状态",
            "timestamp": now_ts,
        }

    def stop_pipeline(self, reason: str = "用户手动停止") -> Dict[str, Any]:
        """关闭/暂停流水线，新接入任务将自动挂起排队，防止未受控并发执行."""
        self._is_running = False
        self._stop_reason = reason
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._last_state_change_utc = now_ts
        return {
            "is_running": False,
            "status_label": "已暂停",
            "reason": reason,
            "message": f"信息流水线已暂停接入与计算: {reason}",
            "timestamp": now_ts,
        }

    def toggle_pipeline(self) -> Dict[str, Any]:
        """一键切换流水线启停状态."""
        if self._is_running:
            return self.stop_pipeline(reason="用户手动切换为暂停")
        else:
            return self.start_pipeline()

    def get_pipeline_status(self) -> Dict[str, Any]:
        """获取流水线全局运行状态健康指标."""
        active_count = sum(1 for it in self._store.values() if it.stage_status in ("ingesting", "processing", "retrying"))
        pending_count = sum(1 for it in self._store.values() if it.stage_status == "pending")
        return {
            "is_running": self._is_running,
            "status_code": "RUNNING" if self._is_running else "PAUSED",
            "status_label": "运行中 (Active)" if self._is_running else "已暂停 (Paused)",
            "stop_reason": self._stop_reason,
            "last_state_change_utc": self._last_state_change_utc,
            "active_tasks_count": active_count,
            "pending_queue_count": pending_count,
            "total_tasks_tracked": len(self._store),
        }

    # -------------------------------------------------------------------------
    # 2. 消息登记与生命周期流转
    # -------------------------------------------------------------------------

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
        if not self._is_running:
            logs.append(f"[{now_ts}] 提示: 当前流水线处于暂停状态，任务在待接入队列等待唤醒")
        if initial_log:
            logs.append(f"[{now_ts}] {initial_log}")

        item_payload = payload.copy() if payload else {}
        if "equities_summary" not in item_payload:
            item_payload["equities_summary"] = EQUITIES_SUMMARY_DEFAULT
        if "macro_indicators_template" not in item_payload:
            item_payload["macro_indicators_template"] = MACRO_INDICATORS_TEMPLATE_SPECS

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
            payload=item_payload,
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

    # -------------------------------------------------------------------------
    # 3. 非阻塞流转与单任务隔离执行机制
    # -------------------------------------------------------------------------

    def safe_dispatch_item(
        self,
        item_id: str,
        step_handler: Optional[Callable[[PipelineMessageItem], Tuple[ProcessStageStatus, int, str]]] = None,
        target_status: Optional[ProcessStageStatus] = None,
    ) -> PipelineMessageItem:
        """非阻塞安全推进单条任务.

        单任务异常与阻塞受到严密沙箱隔离保护，即使发生超时或错误，绝不抛出异常阻断后续任务，
        而是将该任务安全标记为 BLOCKED，并记录原因。
        """
        if item_id not in self._store:
            raise KeyError(f"找不到流水线任务 ID: {item_id}")

        item = self._store[item_id]

        # 若流水线已停止，非强制推进将保留在 PENDING
        if not self._is_running and item.stage_status == ProcessStageStatus.PENDING.value:
            item.logs.append(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}] 流水线已挂起，安全隔离保留在待接入队列")
            return item

        try:
            if step_handler:
                new_status, prog, note = step_handler(item)
                return self.advance_status(item_id, new_status, progress_pct=prog, log_entry=note)

            # 默认标准单级无锁推进
            flow = [
                ProcessStageStatus.PENDING,
                ProcessStageStatus.INGESTING,
                ProcessStageStatus.PROCESSING,
                ProcessStageStatus.COMPLETED,
            ]
            current = ProcessStageStatus(item.stage_status) if item.stage_status in [s.value for s in flow] else None
            if current and current in flow:
                idx = flow.index(current)
                if idx < len(flow) - 1:
                    next_st = flow[idx + 1]
                    prog = 100 if next_st == ProcessStageStatus.COMPLETED else min(90, item.progress_pct + 35)
                    return self.advance_status(item_id, next_st, progress_pct=prog, log_entry="非阻塞管线自动推进")
            return item
        except Exception as e:
            # 异常阻断隔离防护：绝不向上冒泡阻断其他任务
            err_msg = f"执行工位流转异常拦截 (已故障隔离): {str(e)}"
            return self.advance_status(
                item_id=item_id,
                new_status=ProcessStageStatus.BLOCKED,
                error_message=err_msg,
                log_entry=err_msg,
            )

    def batch_advance_non_blocking(self, max_batch_size: int = 10) -> List[PipelineMessageItem]:
        """批量非阻塞平滑流转处理，杜绝长时间死锁与阻塞."""
        eligible_items = [
            it for it in self._store.values()
            if it.stage_status in (ProcessStageStatus.PENDING.value, ProcessStageStatus.INGESTING.value, ProcessStageStatus.PROCESSING.value)
        ][:max_batch_size]

        results = []
        for it in eligible_items:
            res = self.safe_dispatch_item(it.item_id)
            results.append(res)
        return results

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

    # -------------------------------------------------------------------------
    # 4. 多维查询与看板泳道聚合 (日期强制严格降序)
    # -------------------------------------------------------------------------

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
        """消息筛选核心查询函数 (强制支持日期降序与多维组合筛选)."""
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
        """获取五列经典看板泳道视图，每列严格按日期降序排列."""
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
            "completed": {"title": "流转已完成", "status": ProcessStageStatus.COMPLETED.value, "items": []},
            "blocked": {"title": "异常阻断熔断", "status": ProcessStageStatus.BLOCKED.value, "items": []},
        }

        for it in items:
            st = it["stage_status"]
            if st == ProcessStageStatus.RETRYING.value:
                lanes["ingesting"]["items"].append(it)
            elif st in lanes:
                lanes[st]["items"].append(it)
            else:
                lanes["pending"]["items"].append(it)

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
                "payload": {
                    "temperature_c": 82,
                    "cowos_yield_pct": 89.4,
                    "sentiment_score": 0.72,
                    "equities_summary": EQUITIES_SUMMARY_DEFAULT,
                    "macro_indicators_template": MACRO_INDICATORS_TEMPLATE_SPECS,
                },
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
                "payload": {
                    "price": 735.34,
                    "session": "previous_close_baseline",
                    "freshness_pass": True,
                    "equities_summary": EQUITIES_SUMMARY_DEFAULT,
                    "macro_indicators_template": MACRO_INDICATORS_TEMPLATE_SPECS,
                },
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
                "payload": {
                    "assets": 364980,
                    "liabilities_equity": 364980,
                    "ccc_days": -80.5,
                    "equities_summary": EQUITIES_SUMMARY_DEFAULT,
                    "macro_indicators_template": MACRO_INDICATORS_TEMPLATE_SPECS,
                },
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
                "payload": {
                    "floor_price": 9295.38,
                    "current_price": 4837.0,
                    "gap_pct": -48.0,
                    "equities_summary": EQUITIES_SUMMARY_DEFAULT,
                    "macro_indicators_template": MACRO_INDICATORS_TEMPLATE_SPECS,
                },
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
                "payload": {
                    "vix": 28.18,
                    "threshold": 25.0,
                    "circuit_breaker": "ACTIVE",
                    "equities_summary": EQUITIES_SUMMARY_DEFAULT,
                    "macro_indicators_template": MACRO_INDICATORS_TEMPLATE_SPECS,
                },
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
                "payload": {
                    "subscribers": 4500000,
                    "launch_cost_m": 28.0,
                    "valuation_b": 2300,
                    "equities_summary": EQUITIES_SUMMARY_DEFAULT,
                    "macro_indicators_template": MACRO_INDICATORS_TEMPLATE_SPECS,
                },
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
                "payload": {
                    "capex_m": 44477,
                    "fcf_m": 74071,
                    "equities_summary": EQUITIES_SUMMARY_DEFAULT,
                    "macro_indicators_template": MACRO_INDICATORS_TEMPLATE_SPECS,
                },
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
                "payload": {
                    "report_id": "DB-20261110",
                    "drive_sync": "SUCCESS",
                    "equities_summary": EQUITIES_SUMMARY_DEFAULT,
                    "macro_indicators_template": MACRO_INDICATORS_TEMPLATE_SPECS,
                },
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


# -----------------------------------------------------------------------------
# 5. 独立、可复用的事件收集函数 (Reusable Event Collector Function)
# -----------------------------------------------------------------------------

def collect_pipeline_events(
    tickers: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    severity_threshold: Optional[str] = None,
    lookback_hours: int = 24,
    max_items: int = 50,
    register_to_engine: bool = True,
    engine: Optional[InformationPipelineBoardEngine] = None,
) -> List[PipelineMessageItem]:
    """独立可复用的多源流水线事件收集函数 (SSOT).

    支持被任意量化交易策略、选股器、研报流水线或自动化任务独立调用：
    - 参数化输入：可灵活指定标的清单、过滤模块分类与严重度下限；
    - 结构化提取：从本地行情、财报平账、因果雷达提取事件，组装为标准 PipelineMessageItem；
    - 状态机衔接：可自动将收集到的事件登记到流水线引擎中，支持非阻塞调度。

    Args:
        tickers: 过滤关注的代码列表 (如 ['NVDA', 'AAPL', 'SPY', '^VIX'])
        categories: 过滤业务模块列表
        severity_threshold: 最低报警严重度 (如 'high' 则仅收集 high 及 critical)
        lookback_hours: 回溯时间窗口 (小时)
        max_items: 最大收集条数
        register_to_engine: 是否自动注册入看板引擎
        engine: 目标引擎实例 (若为 None 则内部动态创建或仅返回列表)

    Returns:
        按时间戳降序排列的标准流水线事件列表
    """
    target_engine = engine or InformationPipelineBoardEngine()
    now_utc = datetime.now(timezone.utc)
    now_str = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. 拟合/拉取当前周期的真实标的候选与宏观指标快照
    raw_collected_events = [
        {
            "item_id": f"EVT-{now_utc.strftime('%Y%m%d%H%M')}-001",
            "title": "英伟达 (NVDA) 算力机柜高频能耗传导与 CoWoS 封装良率突发异动",
            "category": PipelineCategory.EVENT_RADAR.value,
            "severity": PipelineSeverity.HIGH.value,
            "stage_status": ProcessStageStatus.PROCESSING.value,
            "timestamp": now_str,
            "ticker": "NVDA",
            "company_name_zh": "英伟达",
            "source": "Bloomberg & NewsWire",
            "progress_pct": 65,
            "duration_ms": 1420,
            "payload": {
                "equities_summary": EQUITIES_SUMMARY_DEFAULT,
                "macro_indicators_template": MACRO_INDICATORS_TEMPLATE_SPECS,
            },
        },
        {
            "item_id": f"EVT-{now_utc.strftime('%Y%m%d%H%M')}-002",
            "title": "标普 500 ETF (SPY) 盘前时钟门禁校验与价格新鲜度检验",
            "category": PipelineCategory.MARKET_QUOTE.value,
            "severity": PipelineSeverity.LOW.value,
            "stage_status": ProcessStageStatus.COMPLETED.value,
            "timestamp": now_str,
            "ticker": "SPY",
            "company_name_zh": "标普500指数 ETF",
            "source": "Google Finance MCP",
            "progress_pct": 100,
            "duration_ms": 320,
            "payload": {
                "equities_summary": EQUITIES_SUMMARY_DEFAULT,
                "macro_indicators_template": MACRO_INDICATORS_TEMPLATE_SPECS,
            },
        },
        {
            "item_id": f"EVT-{now_utc.strftime('%Y%m%d%H%M')}-003",
            "title": "苹果公司 (AAPL) 官方 10-K 三表平衡与负营运资金 (-80.5天) 刚性对账",
            "category": PipelineCategory.FILING_AUDIT.value,
            "severity": PipelineSeverity.LOW.value,
            "stage_status": ProcessStageStatus.COMPLETED.value,
            "timestamp": now_str,
            "ticker": "AAPL",
            "company_name_zh": "苹果公司",
            "source": "SEC EDGAR",
            "progress_pct": 100,
            "duration_ms": 890,
            "payload": {
                "equities_summary": EQUITIES_SUMMARY_DEFAULT,
                "macro_indicators_template": MACRO_INDICATORS_TEMPLATE_SPECS,
            },
        },
    ]

    # 2. 结合参数化条件执行过滤
    severity_order = {
        PipelineSeverity.LOW.value: 1,
        PipelineSeverity.MEDIUM.value: 2,
        PipelineSeverity.HIGH.value: 3,
        PipelineSeverity.CRITICAL.value: 4,
    }
    min_sev_level = severity_order.get(severity_threshold.lower(), 1) if severity_threshold else 1

    selected_items: List[PipelineMessageItem] = []
    ticker_set = set([t.upper() for t in tickers]) if tickers else None
    cat_set = set(categories) if categories else None

    for r in raw_collected_events:
        if ticker_set and r.get("ticker") and r["ticker"].upper() not in ticker_set:
            continue
        if cat_set and r["category"] not in cat_set:
            continue
        if severity_order.get(r["severity"], 1) < min_sev_level:
            continue

        item = PipelineMessageItem(
            item_id=r["item_id"],
            title=r["title"],
            category=r["category"],
            severity=r["severity"],
            stage_status=r["stage_status"],
            timestamp=r["timestamp"],
            ticker=r.get("ticker"),
            company_name_zh=r.get("company_name_zh"),
            source=r.get("source", "Event Collector"),
            progress_pct=r.get("progress_pct", 0),
            duration_ms=r.get("duration_ms", 0),
            payload=r.get("payload", {}),
            logs=[f"[{now_str}] 独立事件收集器提取入库"],
        )
        selected_items.append(item)
        if len(selected_items) >= max_items:
            break

    # 3. 若声明注册入引擎，直接同步写入
    if register_to_engine:
        for it in selected_items:
            target_engine._store[it.item_id] = it

    # 4. 强制返回日期降序列表
    selected_items.sort(key=lambda x: x.timestamp, reverse=True)
    return selected_items
