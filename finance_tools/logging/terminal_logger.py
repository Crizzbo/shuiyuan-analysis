# -*- coding: utf-8 -*-
"""工程级专属日志中枢与终端桥接器 (Terminal Logging Hub & Dedicated Log Router).

本模块实现全工程专属日志管理契约：
1. 物理分流落盘 (Dedicated Log Files):
   - data/logs/system.log           - 全局汇总滚动日志 (RotatingFileHandler)
   - data/logs/event_radar.log      - 突发事件雷达与舆情因果分析专属日志
   - data/logs/verification.log     - 官方监管公报核验与传闻隔离专属日志
   - data/logs/scheduler.log        - 定时任务调度与数据采集专属日志
   - data/logs/terminal_service.log - 终端 HTTP/SSE 服务与客户端请求专属日志
   - data/logs/alert.log            - 重大突发事件告警分发专属日志
2. 终端日志中枢桥接 (TerminalLogBridgeHandler):
   - 捕获全工程 Python 标准 logging 输出;
   - 归一化模块标签与日志级别 (INFO, WARN, ERROR);
   - 自动写入 WatersourceTerminalService 环形缓冲，并通过 SSE 实时广播到前端控制台。
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import threading
from typing import Any, Callable, Dict, List, Optional, Set

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_DIR = PROJECT_ROOT / "data" / "logs"

# 模块名归一化映射表
MODULE_ALIAS_MAP: Dict[str, str] = {
    "eventradarcollector": "event_radar",
    "eventradarservice": "event_radar",
    "eventradarengine": "event_radar",
    "finance_tools.events_and_verification.event_radar_collector": "event_radar",
    "evidenceverificationpipeline": "evidence_verification",
    "browserverificationassistant": "evidence_verification",
    "alertdispatcher": "alert_dispatcher",
    "supplychainrippleanalyzer": "ripple_analysis",
    "sotpeventanalyzer": "sotp_analysis",
    "terminalscheduler": "terminal_scheduler",
    "scripts.terminal_scheduler": "terminal_scheduler",
    "watersourceterminalservice": "terminal_service",
    "watersourcehttpserver": "terminal_service",
    "radardashboardserver": "radar_server",
}

# 专属日志文件名与其捕获的模块集合映射
DEDICATED_LOG_ROUTING: Dict[str, Set[str]] = {
    "event_radar.log": {"event_radar", "radar_server", "sotp_analysis"},
    "verification.log": {"evidence_verification"},
    "scheduler.log": {"terminal_scheduler", "pipeline_orchestrator", "task_config"},
    "terminal_service.log": {"terminal_service"},
    "alert.log": {"alert_dispatcher"},
}


def normalize_module_name(raw_name: str) -> str:
    """将 Python 内部 logger 名称归一化为业务语义模块名。"""
    cleaned = (raw_name or "system").strip().lower()
    if cleaned in MODULE_ALIAS_MAP:
        return MODULE_ALIAS_MAP[cleaned]
    # 前缀匹配
    for k, v in MODULE_ALIAS_MAP.items():
        if cleaned.startswith(k) or k in cleaned:
            return v
    # 默认截取末段
    return cleaned.split(".")[-1]


def normalize_log_level(level_no: int) -> str:
    """将标准 logging 级别转为前端统一契约级别 (INFO, WARN, ERROR)。"""
    if level_no >= logging.ERROR:
        return "ERROR"
    if level_no >= logging.WARNING:
        return "WARN"
    return "INFO"


class DedicatedModuleFilter(logging.Filter):
    """按模块将日志路由至对应的专属落盘文件。"""

    def __init__(self, allowed_modules: Optional[Set[str]] = None, allow_all: bool = False):
        super().__init__()
        self.allowed_modules = allowed_modules or set()
        self.allow_all = allow_all

    def filter(self, record: logging.LogRecord) -> bool:
        if self.allow_all:
            return True
        mod = normalize_module_name(record.name)
        return mod in self.allowed_modules


class TerminalLogBridgeHandler(logging.Handler):
    """将 Python 标准 logging 输出无缝桥接至 WatersourceTerminalService 环形缓冲与 SSE 广播。"""

    _tls = threading.local()

    def __init__(self, append_callback: Callable[..., Any]):
        super().__init__()
        self.append_callback = append_callback
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        # 防递归保护
        if getattr(self._tls, "in_emit", False):
            return

        try:
            self._tls.in_emit = True
            msg = self.format(record)
            if not msg.strip():
                return
            level = normalize_log_level(record.levelno)
            module = normalize_module_name(record.name)
            run_id = getattr(record, "run_id", None)

            self.append_callback(
                level=level,
                module=module,
                message=msg,
                run_id=run_id,
                broadcast=True,
            )
        except Exception:
            # 日志桥接不可影响主业务逻辑
            pass
        finally:
            self._tls.in_emit = False


class TerminalLoggingManager:
    """全工程统一专属日志管理器 (单例生命周期)。"""

    _instance: Optional[TerminalLoggingManager] = None
    _lock = threading.Lock()

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.file_handlers: Dict[str, RotatingFileHandler] = {}
        self.bridge_handler: Optional[TerminalLogBridgeHandler] = None
        self._is_initialized = False

    @classmethod
    def get_instance(cls, log_dir: Optional[Path] = None) -> TerminalLoggingManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(log_dir)
            return cls._instance

    def initialize(
        self,
        service_callback: Optional[Callable[..., Any]] = None,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
    ) -> None:
        """初始化物理专属日志文件与前端 SSE 桥接器。"""
        if self._is_initialized:
            # 若重复调用且传入了新回调，更新桥接器
            if service_callback and self.bridge_handler:
                self.bridge_handler.append_callback = service_callback
            return

        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        # 1. 挂载全局系统汇总日志 (system.log)
        sys_log_path = self.log_dir / "system.log"
        sys_handler = RotatingFileHandler(
            sys_log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        sys_handler.setFormatter(formatter)
        sys_handler.addFilter(DedicatedModuleFilter(allow_all=True))
        root_logger.addHandler(sys_handler)
        self.file_handlers["system.log"] = sys_handler

        # 2. 分流挂载各个业务线的专属日志文件
        for log_filename, modules in DEDICATED_LOG_ROUTING.items():
            log_path = self.log_dir / log_filename
            handler = RotatingFileHandler(
                log_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            handler.setFormatter(formatter)
            handler.addFilter(DedicatedModuleFilter(allowed_modules=modules))
            root_logger.addHandler(handler)
            self.file_handlers[log_filename] = handler

        # 3. 挂载前端 UI 环形缓冲与 SSE 实时广播桥接器
        if service_callback:
            self.bridge_handler = TerminalLogBridgeHandler(service_callback)
            root_logger.addHandler(self.bridge_handler)

        self._is_initialized = True

    def get_log_files_overview(self) -> List[Dict[str, Any]]:
        """列出所有专属日志文件的当前状态、文件大小与最后更新时间。"""
        items: List[Dict[str, Any]] = []
        all_logs = ["system.log", *DEDICATED_LOG_ROUTING.keys()]
        for name in all_logs:
            path = self.log_dir / name
            size_bytes = path.stat().st_size if path.exists() else 0
            mtime = path.stat().st_mtime if path.exists() else None
            try:
                rel_path = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
            except ValueError:
                rel_path = str(path).replace("\\", "/")
            items.append({
                "filename": name,
                "path": rel_path,
                "size_bytes": size_bytes,
                "size_formatted": f"{size_bytes / 1024:.1f} KB" if size_bytes < 1024 * 1024 else f"{size_bytes / (1024*1024):.2f} MB",
                "exists": path.exists(),
                "last_modified": mtime,
            })
        return items


def setup_terminal_logging(
    service_callback: Optional[Callable[..., Any]] = None,
    log_dir: Optional[Path] = None,
) -> TerminalLoggingManager:
    """快速初始化或获取全工程日志中枢单例。"""
    mgr = TerminalLoggingManager.get_instance(log_dir)
    mgr.initialize(service_callback=service_callback)
    return mgr
