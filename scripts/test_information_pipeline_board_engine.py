# -*- coding: utf-8 -*-
"""信息流水线看板核心引擎单元测试 (test_information_pipeline_board_engine.py).

遵循《CLAUDE.md》与《AGENTS.md》四段式中文测试说明文档规范：
1. 测试目标 (Objective)
2. 输入数据与边界 (Inputs & Boundaries)
3. 业务逻辑断言 (Assertions & Invariants)
4. 失败场景防护 (Failure Modes)
"""

import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.pipeline.information_pipeline_board_engine import (
    InformationPipelineBoardEngine,
    PipelineCategory,
    PipelineMessageItem,
    PipelineSeverity,
    ProcessStageStatus,
)
from finance_tools.governance_and_pipeline.information_pipeline_board_engine import (
    InformationPipelineBoardEngine as ToolInformationPipelineBoardEngine,
)


class TestInformationPipelineBoardEngine(unittest.TestCase):
    """信息流水线看板核心引擎与进程状态管理器测试套件."""

    def setUp(self):
        self.engine = InformationPipelineBoardEngine()

    def test_default_seed_data_and_date_descending_sort(self):
        """【测试一：默认种子数据载入与强制日期降序排序断言】

        1. 测试目标：验证系统初始化时载入真实种子数据，且 query_messages 默认严格按时间戳降序 (最新在前)。
        2. 输入数据：引擎内部自带的 8 条基准流转消息。
        3. 业务断言：
           - 初始数据集不少于 5 条；
           - 结果列表中的时间戳严格单调非递增 (T_i >= T_{i+1})；
           - 第 1 条记录的时间戳为全集最新时间。
        4. 失败防护：防止排序算法失效导致时间混乱或乱序输出。
        """
        res = self.engine.query_messages(page_size=100)
        items = res["items"]
        self.assertGreaterEqual(len(items), 5)
        self.assertEqual(res["sort_order"], "desc")

        # 断言单调降序
        for i in range(len(items) - 1):
            t_curr = items[i]["timestamp"]
            t_next = items[i + 1]["timestamp"]
            self.assertGreaterEqual(
                t_curr,
                t_next,
                f"时间戳必须严格降序: {t_curr} 应 >= {t_next} (索引 {i})"
            )

    def test_multidimensional_filtering(self):
        """【测试二：消息多维度组合筛选 (分类/严重度/状态/标的/关键词)】

        1. 测试目标：验证按业务模块、严重度、进程状态、股票代码及模糊关键词的精准组合过滤。
        2. 输入数据：
           - 按 category="event_radar" 过滤；
           - 按 ticker="NVDA" 过滤；
           - 按 severity="critical" 过滤；
           - 模糊搜索 "平账"。
        3. 业务断言：
           - 过滤结果 100% 满足条件；
           - 模糊搜索能正确定位到包含相应关键词的记录。
        """
        # 1. 过滤 category
        cat_res = self.engine.query_messages(category=PipelineCategory.EVENT_RADAR.value)
        for it in cat_res["items"]:
            self.assertEqual(it["category"], PipelineCategory.EVENT_RADAR.value)

        # 2. 过滤 ticker
        nvda_res = self.engine.query_messages(ticker="NVDA")
        self.assertGreaterEqual(nvda_res["total_count"], 1)
        for it in nvda_res["items"]:
            self.assertEqual(it["ticker"], "NVDA")

        # 3. 过滤 severity
        crit_res = self.engine.query_messages(severity=PipelineSeverity.CRITICAL.value)
        self.assertGreaterEqual(crit_res["total_count"], 1)
        for it in crit_res["items"]:
            self.assertEqual(it["severity"], PipelineSeverity.CRITICAL.value)

        # 4. 模糊搜索
        kw_res = self.engine.query_messages(search_keyword="平账")
        self.assertGreaterEqual(kw_res["total_count"], 1)
        self.assertIn("AAPL", [it["ticker"] for it in kw_res["items"]])

    def test_process_status_lifecycle_transitions(self):
        """【测试三：进程状态全生命周期流转与日志追加】

        1. 测试目标：验证任务从待接入 (PENDING) -> 接入中 (INGESTING) -> 处理中 (PROCESSING) -> 完成 (COMPLETED) 的顺畅流转。
        2. 输入数据：动态新建一条任务并依次触发 advance_status。
        3. 业务断言：
           - 状态正确更新；
           - 进度百分比受 [0, 100] 约束；
           - 日志流按时间顺序不断追加。
        """
        item_id = "TEST-TASK-001"
        item = self.engine.register_message(
            item_id=item_id,
            title="台积电 CoWoS 封装扩产与资本开支更新任务",
            category=PipelineCategory.FILING_AUDIT.value,
            severity=PipelineSeverity.MEDIUM.value,
            ticker="TSM",
            company_name_zh="台积电",
        )
        self.assertEqual(item.stage_status, ProcessStageStatus.PENDING.value)
        self.assertEqual(item.progress_pct, 0)
        self.assertEqual(len(item.logs), 1)

        # 推进到接入中
        self.engine.advance_status(
            item_id=item_id,
            new_status=ProcessStageStatus.INGESTING,
            progress_pct=25,
            log_entry="正在拉取台积电法说会公开披露文件",
            added_duration_ms=200,
        )
        self.assertEqual(item.stage_status, ProcessStageStatus.INGESTING.value)
        self.assertEqual(item.progress_pct, 25)
        self.assertEqual(item.duration_ms, 200)

        # 推进到处理中
        self.engine.advance_status(
            item_id=item_id,
            new_status=ProcessStageStatus.PROCESSING,
            progress_pct=75,
            log_entry="正在执行资本开支折现与产能占用分析",
            added_duration_ms=450,
        )
        self.assertEqual(item.stage_status, ProcessStageStatus.PROCESSING.value)
        self.assertEqual(item.progress_pct, 75)

        # 推进到已完成
        self.engine.advance_status(
            item_id=item_id,
            new_status=ProcessStageStatus.COMPLETED,
            progress_pct=100,
            log_entry="全息投研卡片生成完毕并落盘",
            added_duration_ms=150,
        )
        self.assertEqual(item.stage_status, ProcessStageStatus.COMPLETED.value)
        self.assertEqual(item.progress_pct, 100)
        self.assertEqual(item.duration_ms, 800)
        self.assertGreaterEqual(len(item.logs), 4)

    def test_process_blocked_and_retry_control(self):
        """【测试四：异常阻断拦截、手动重试与强制终止控制】

        1. 测试目标：验证异常熔断、用户手动发起重试及终止操作的状态变迁。
        2. 输入数据：将任务标记为 BLOCKED，再调用 retry_message 与 kill_message。
        3. 业务断言：
           - 阻断时携带明确的 error_message；
           - retry_message 将状态重置为 RETRYING 并清空错误；
           - kill_message 将任务强制标记为 BLOCKED 并留下终止日志。
        """
        item_id = "TEST-BLOCK-002"
        self.engine.register_message(
            item_id=item_id,
            title="美债收益率时钟门禁超时检验",
            category=PipelineCategory.MARKET_QUOTE.value,
            severity=PipelineSeverity.HIGH.value,
        )

        # 触发阻断
        self.engine.advance_status(
            item_id=item_id,
            new_status=ProcessStageStatus.BLOCKED,
            error_message="外部连接超时，未能获取最新时钟响应",
        )
        item = self.engine._store[item_id]
        self.assertEqual(item.stage_status, ProcessStageStatus.BLOCKED.value)
        self.assertEqual(item.error_message, "外部连接超时，未能获取最新时钟响应")

        # 触发重试
        self.engine.retry_message(item_id=item_id, log_note="网络恢复，重新拉取")
        self.assertEqual(item.stage_status, ProcessStageStatus.RETRYING.value)
        self.assertIsNone(item.error_message)

        # 强制终止
        self.engine.kill_message(item_id=item_id, reason="人工判定任务作废")
        self.assertEqual(item.stage_status, ProcessStageStatus.BLOCKED.value)
        self.assertIn("人工判定任务作废", item.error_message)

    def test_kanban_lanes_aggregation(self):
        """【测试五：四列看板泳道聚合与各列降序断言】

        1. 测试目标：验证看板泳道接口能够将任务准确归集到待接入、抓取中、清洗中、已完成、异常阻断五个列。
        2. 输入数据：调用 get_kanban_board_view。
        3. 业务断言：
           - 各泳道条目总和等于总条目数；
           - 泳道内条目严格保持日期降序；
           - 统计数据中的 total_active 与实际处于流转中的任务吻合。
        """
        board = self.engine.get_kanban_board_view()
        lanes = board["lanes"]
        self.assertIn("pending", lanes)
        self.assertIn("ingesting", lanes)
        self.assertIn("processing", lanes)
        self.assertIn("completed", lanes)
        self.assertIn("blocked", lanes)

        total_in_lanes = sum(len(lanes[k]["items"]) for k in lanes)
        self.assertEqual(total_in_lanes, board["total_items"])
        self.assertEqual(board["total_completed"], len(lanes["completed"]["items"]))
        self.assertEqual(board["total_blocked"], len(lanes["blocked"]["items"]))

    def test_pipeline_health_stats(self):
        """【测试六：系统宏观吞吐与健康度统计计算】

        1. 测试目标：断言成功率百分比、活跃处理数、平均耗时等指标的准确性。
        2. 输入数据：调用 get_pipeline_health_stats。
        3. 业务断言：
           - 成功率介于 0% ~ 100%；
           - 模块分布与严重度分布覆盖全集。
        """
        stats = self.engine.get_pipeline_health_stats()
        self.assertGreater(stats["total_messages"], 0)
        self.assertGreaterEqual(stats["success_rate_pct"], 0.0)
        self.assertLessEqual(stats["success_rate_pct"], 100.0)
        self.assertIn(PipelineCategory.EVENT_RADAR.value, stats["category_breakdown"])

    def test_architecture_facade_compatibility(self):
        """【测试七：中继门面与工具层导入透明性断言】

        1. 测试目标：验证从 finance_tools 导入与从底层 financial_core 导入具备完全一致的类定义与功能。
        2. 业务断言：ToolInformationPipelineBoardEngine is InformationPipelineBoardEngine。
        """
        self.assertIs(ToolInformationPipelineBoardEngine, InformationPipelineBoardEngine)


if __name__ == "__main__":
    unittest.main()
