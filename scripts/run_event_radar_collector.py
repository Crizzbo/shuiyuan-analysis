"""突发事件雷达定时收集与调度服务 (Event Radar Scheduled Collector Service).

本脚本专责突发事件雷达的第一阶段实盘定时调度与运维管理:
1. 单轮次/常驻守护进程调度 (--once / --daemon);
2. 市场交易时段自适应频次轮询 (盘前 5m, 盘中 15m, 盘后 30m, 休市 60m);
3. 看门狗断网自检、自动重试与零抛错挂起等待 (NetworkHealthWatchdog);
4. SHA-256 指纹幂等去重与断点续传 (RadarProgressManager);
5. 自动联动更新交互看板 (reports/event_radar_dashboard.html) 与补数清单 (reports/radar_browser_checklist.md);
6. 严格遵守《2026-10-11 最新数据来源策略》与合规边界，纯本地排重与安全调度。
"""

import argparse
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# 项目根目录相对路径解析
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finance_tools.event_radar_collector import EventRadarCollector
from scripts.generate_radar_dashboard import generate_dashboard_html as generate_radar_dashboard
from scripts.generate_radar_browser_checklist import generate_radar_browser_checklist

# 日志输出配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("EventRadarService")


class EventRadarService:
    """事件雷达调度守护中枢."""

    def __init__(
        self,
        config_path: str = "config/event_radar_sources.json",
        auto_generate_reports: bool = True,
        collector: Optional[EventRadarCollector] = None,
    ):
        cfg_p = Path(config_path)
        self.config_path = str(cfg_p if cfg_p.is_absolute() else (PROJECT_ROOT / config_path))
        self.auto_generate_reports = auto_generate_reports
        self.collector = collector or EventRadarCollector(config_path=self.config_path)
        self._is_running = True

        # 注册优雅停机信号
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum: int, frame: Any) -> None:
        logger.info("捕获停机信号 (%s)，正在安全停止事件雷达服务...", signum)
        self._is_running = False

    def run_single_cycle(self, raw_feed_items: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """执行单次巡检并联动生成报表看板."""
        logger.info(">>> 启动新一轮突发事件巡检与因果门禁核验...")
        cycle_result = self.collector.run_collection_cycle(raw_feed_items=raw_feed_items)

        status = cycle_result.get("status", "UNKNOWN")
        session = cycle_result.get("market_session", "unknown")
        p0_p1 = cycle_result.get("p0_p1_triggered_count", 0)
        tokens = cycle_result.get("estimated_tokens_consumed", 0)

        logger.info(
            "巡检完成 | 状态: %s | 时段: %s | 扫描: %d | 初筛: %d | 摘要: %d | 重大(P0/P1): %d | Token消耗: %d",
            status,
            session,
            cycle_result.get("scanned_count", 0),
            cycle_result.get("filtered_in_count", 0),
            cycle_result.get("summarized_count", 0),
            p0_p1,
            tokens,
        )

        if self.auto_generate_reports and status == "SUCCESS":
            try:
                dash_path = generate_radar_dashboard()
                chk_path = generate_radar_browser_checklist()
                logger.info("看板报表与补数清单自动更新完成: %s | %s", Path(dash_path).name, Path(chk_path).name)
            except Exception as e:
                logger.error("自动生成报表看板异常: %s", e)

        return cycle_result

    def run_daemon(self, default_sleep_override_seconds: Optional[int] = None) -> None:
        """常驻守护进程循环调度."""
        logger.info("======================================================")
        logger.info("事件雷达常驻守护服务已启动 (PID: %d)", sys.platform == "win32" and 0 or sys.platform)
        logger.info("按 Ctrl+C 可安全优雅停机")
        logger.info("======================================================")

        while self._is_running:
            try:
                cycle_result = self.run_single_cycle()
                interval_min = cycle_result.get("recommended_interval_minutes", 15)

                if default_sleep_override_seconds:
                    sleep_sec = default_sleep_override_seconds
                else:
                    sleep_sec = max(60, interval_min * 60)

                logger.info("等待下一轮巡检 (休眠时长: %d 秒 / %.1f 分钟)...", sleep_sec, sleep_sec / 60.0)

                # 分步可中断休眠
                for _ in range(int(sleep_sec)):
                    if not self._is_running:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.critical("守护进程运行时遭遇未捕获异常: %s", e, exc_info=True)
                time.sleep(10)

        logger.info("事件雷达常驻守护服务已安全退出。")

    def print_status(self) -> None:
        """打印雷达数据库与断点进度状态摘要."""
        stats = self.collector.db_mgr.query_summary_statistics()
        session, interval = self.collector.determine_trading_session()
        ckpt = self.collector.progress_mgr.state

        print("\n" + "=" * 65)
        print("【突发事件雷达系统 · 运行状态与账本审计】")
        print("=" * 65)
        print(f"当前时间 (UTC)        : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"当前交易时段          : {session} (建议巡检频次: {interval} 分钟/轮)")
        print(f"雷达数据库主账本      : {self.collector.db_mgr.db_path}")
        print(f"已持久化事件总量      : {stats.get('total_events_stored', 0)} 条")
        print(f"P0/P1 重大事件总数    : {stats.get('total_major_p0_p1', 0)} 项")
        print(f"历史执行巡检轮次      : {stats.get('total_cycles_executed', 0)} 轮")
        print(f"累计扫描快讯总量      : {stats.get('total_scanned_news', 0)} 条")
        print(f"累计模型摘要提纯数    : {stats.get('total_summarized', 0)} 条")
        print(f"累计消耗 Token 总量   : {stats.get('total_tokens_burned', 0)} Tokens")
        print(f"已排重 SHA-256 缓存数 : {len(ckpt.get('processed_hashes', []))} 条")
        print(f"最近检查点时间戳      : {ckpt.get('last_successful_timestamp', '无')}")
        print("=" * 65 + "\n")


def main():
    parser = argparse.ArgumentParser(description="突发事件雷达定时收集与调度服务 CLI")
    parser.add_argument("--once", action="store_true", help="执行单轮次巡检后安全退出")
    parser.add_argument("--daemon", action="store_true", help="作为常驻守护服务持续运行")
    parser.add_argument("--status", action="store_true", help="打印雷达系统账本底账与运行状态")
    parser.add_argument("--interval-seconds", type=int, default=None, help="覆盖守护进程休眠间隔秒数(调试用)")
    parser.add_argument("--no-reports", action="store_true", help="禁用巡检完成后自动更新看板与清单")

    args = parser.parse_args()

    service = EventRadarService(auto_generate_reports=not args.no_reports)

    if args.status:
        service.print_status()
    elif args.daemon:
        service.run_daemon(default_sleep_override_seconds=args.interval_seconds)
    else:
        # 默认执行单次巡检
        service.run_single_cycle()
        service.print_status()


if __name__ == "__main__":
    main()
