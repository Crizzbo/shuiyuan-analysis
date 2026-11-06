"""单元测试：全市场常态化分批平账管道 (test_normalized_universe_reconciliation.py).

严格验证：
1. 排他进程锁生命周期、并发排斥与过期自愈 (ReconciliationProcessLock);
2. 断点续传状态机、原子持久化与看板指标 (NormalizedReconciliationStateManager);
3. 优先级队列调度与多维度筛选 (NormalizedReconciliationEngine);
4. 会计恒等式刚性平账自检与多准则解析;
5. 缺失数据拦截与补数清单同步闭环机制。
"""

from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.normalized_reconciliation_engine import (
    NormalizedReconciliationEngine,
    NormalizedReconciliationStateManager,
    ReconciliationProcessLock,
    ReconciliationRecord,
    ProcessLockError,
    is_pid_alive,
)
from financial_core.engines.tiered_universe_manager import (
    TieredUniverseManager,
    UniverseCompanyRecord,
)
from scripts.test_support.fixtures import project_temp


class TestNormalizedUniverseReconciliation(unittest.TestCase):
    """测试全市场常态化分批平账引擎与状态机."""

    def setUp(self):
        self.test_dir = project_temp(self, "test-reconciliation-")
        self.test_lock_path = self.test_dir / "test.lock"
        self.test_state_path = self.test_dir / "test_progress.json"
        self.test_manifest_path = self.test_dir / "test_gap_manifest.json"

    def test_01_pid_alive_check(self):
        """【UT-RECON-01: 跨平台操作系统进程存活检测与僵尸进程过滤】

        1. 测试功能与测试点:
           - 验证 is_pid_alive 函数跨平台检测 OS 进程存活状态的能力。
           - 准确识别活跃进程与已销毁无效进程，防止排他锁假死。

        2. 正常函数业务边界与参数契约:
           - pid 为有效正整数时进行系统级信号或句柄检测；负数或超界值返回 False。

        3. 测试数据与模拟场景说明:
           - 当前 Python 运行进程 os.getpid()，负数 PID (-1)，超大不存在 PID (99999999)。

        4. 预期断言与结果验证:
           - 断言 is_pid_alive(os.getpid()) 为 True。
           - 断言 is_pid_alive(-1) 为 False。
           - 断言 is_pid_alive(99999999) 为 False。
        """
        import os
        self.assertTrue(is_pid_alive(os.getpid()))
        self.assertFalse(is_pid_alive(-1))
        self.assertFalse(is_pid_alive(99999999))

    def test_02_process_lock_acquire_and_release(self):
        """【UT-RECON-02: 排他文件锁生命周期-上下文管理与退出自动释放】

        1. 测试功能与测试点:
           - 验证 ReconciliationProcessLock 排他锁获取、上下文生命周期管理与安全释放。
           - 确保并发定时任务调度时只有一个进程能够执行平账流水线。

        2. 正常函数业务边界与参数契约:
           - lock_path 位于项目内临时安全目录。

        3. 测试数据与模拟场景说明:
           - 使用 with lock 上下文语法模拟平账主进程运行。

        4. 预期断言与结果验证:
           - 进入前锁文件不存在，_acquired 为 False。
           - 进入后锁文件物理存在，_acquired 为 True。
           - 退出后锁文件自动清除，_acquired 为 False。
        """
        lock = ReconciliationProcessLock(self.test_lock_path)
        self.assertFalse(self.test_lock_path.exists())

        with lock:
            self.assertTrue(self.test_lock_path.exists())
            self.assertTrue(lock._acquired)

        self.assertFalse(self.test_lock_path.exists())
        self.assertFalse(lock._acquired)

    def test_03_process_lock_conflict_and_timeout(self):
        """【UT-RECON-03: 进程锁并发竞争冲突检测与超时刚性异常抛出(ProcessLockError)】

        1. 测试功能与测试点:
           - 验证多实例并发冲突时，第二个进程在获取锁超时后刚性抛出 ProcessLockError。
           - 防止早 07:00 / 16:00 定时任务重叠触发导致 SQLite 数据库或状态文件写锁冲突。

        2. 正常函数业务边界与参数契约:
           - timeout_sec 设置为短超时 (0.5s)，冲突触发强类型 ProcessLockError。

        3. 测试数据与模拟场景说明:
           - lock1 持有锁，lock2 尝试强行获取。

        4. 预期断言与结果验证:
           - 断言 lock2.acquire 抛出 ProcessLockError。
           - lock1 释放后锁文件彻底清理。
        """
        lock1 = ReconciliationProcessLock(self.test_lock_path)
        lock1.acquire()

        lock2 = ReconciliationProcessLock(self.test_lock_path)
        with self.assertRaises(ProcessLockError):
            lock2.acquire(timeout_sec=0.5)

        lock1.release()
        self.assertFalse(self.test_lock_path.exists())

    def test_04_process_lock_stale_recovery(self):
        """【UT-RECON-04: 死锁与非正常终止进程锁(Stale Lock)自愈机制】

        1. 测试功能与测试点:
           - 验证当由于宿主断电、强制杀死任务导致残留死锁时，系统自动探测持锁进程是否死亡。
           - 若持锁进程已不存在且时间戳超时，自动破锁并接管调度，实现全自动无人值守自愈。

        2. 正常函数业务边界与参数契约:
           - 锁文件中记录的 PID 处于非活跃态 (not is_pid_alive)。

        3. 测试数据与模拟场景说明:
           - 预先写入死亡进程 PID 99999999 与过期时间戳。

        4. 预期断言与结果验证:
           - 断言 lock.acquire(timeout_sec=1.0) 成功自愈接管并返回 True。
        """
        # 写入一个伪造的死亡进程锁 (PID 99999999)
        import json
        stale_data = {
            "pid": 99999999,
            "created_at": "2026-01-01T00:00:00Z",
            "timestamp": time.time() - 10000.0,
            "host_platform": sys.platform,
        }
        self.test_lock_path.write_text(json.dumps(stale_data), encoding="utf-8")

        lock = ReconciliationProcessLock(self.test_lock_path)
        acquired = lock.acquire(timeout_sec=1.0)
        self.assertTrue(acquired)
        lock.release()

    def test_05_state_manager_record_and_atomic_save(self):
        """【UT-RECON-05: 断点续传状态机记录-指标多维分类统计与原子落盘】

        1. 测试功能与测试点:
           - 验证 NormalizedReconciliationStateManager 记录成功平账企业事实。
           - 验证看板多维统计聚合 (Tier、市场、币种、会计准则)。
           - 原子文件持久化与重载自洽性断言。

        2. 正常函数业务边界与参数契约:
           - 写入合法 ReconciliationRecord。

        3. 测试数据与模拟场景说明:
           - 模拟记录 TEST_AAPL (Tier 0, US-GAAP, USD, 资产 3525.8 亿平账)。

        4. 预期断言与结果验证:
           - 重新加载后断言 is_completed("TEST_AAPL", "US") 为 True。
           - 断言 balanced_count == 1。
           - 断言 TIER_0, US, USD, US-GAAP 统计分类均精确为 1。
        """
        mgr = NormalizedReconciliationStateManager(self.test_state_path, sync_legacy=False)
        self.assertFalse(mgr.is_completed("TEST_AAPL", "US"))

        rec = ReconciliationRecord(
            ticker="TEST_AAPL",
            market="US",
            company_name="Test Apple Inc.",
            tier="TIER_0",
            cik="0000320193",
            status="COMPLETED",
            fiscal_year=2025,
            fiscal_year_end="2025-09-30",
            form="10-K",
            accounting_standard="US-GAAP",
            currency="USD",
            total_assets=352583000000.0,
            total_liabilities=290000000000.0,
            stockholders_equity=62583000000.0,
            revenue=391035000000.0,
            is_balanced=True,
            balance_sheet_diff=0.0,
            balance_sheet_rel_ratio=0.0,
            source_filing="SEC EDGAR 10-K",
        )
        mgr.record_success(rec)
        mgr.save()

        # 重新加载断言
        mgr2 = NormalizedReconciliationStateManager(self.test_state_path, sync_legacy=False)
        self.assertTrue(mgr2.is_completed("TEST_AAPL", "US"))
        self.assertEqual(mgr2.metadata["summary"]["balanced_count"], 1)

        dashboard = mgr2.get_dashboard_metrics()
        self.assertEqual(dashboard["tier_breakdown"]["TIER_0"], 1)
        self.assertEqual(dashboard["market_breakdown"]["US"], 1)
        self.assertEqual(dashboard["currency_breakdown"]["USD"], 1)
        self.assertEqual(dashboard["accounting_standard_breakdown"]["US-GAAP"], 1)

    def test_05b_state_manager_syncs_legacy(self):
        """【IT-RECON-06: 历史已核验底账无损热迁移与基准存量断言(>=600家)】

        1. 测试功能与测试点:
           - 验证状态机初次初始化时，能够自动无损扫描历史已核验的 600+ 家底账并建立索引。
           - 避免系统重启或重构时重复处理已有标的。

        2. 正常函数业务边界与参数契约:
           - sync_legacy=True 触发存量同步。

        3. 测试数据与模拟场景说明:
           - 扫描当前仓库中存量标准三表底账。

        4. 预期断言与结果验证:
           - 断言 balanced_count >= 600。
        """
        fresh_sync_path = self.test_dir / "test_fresh_sync.json"
        mgr = NormalizedReconciliationStateManager(fresh_sync_path, sync_legacy=True)
        self.assertGreaterEqual(mgr.metadata["summary"]["balanced_count"], 600)

    def test_06_build_candidate_queue(self):
        """【IT-RECON-07: 标普500与自定义指定标的候选优先级调度队列构建】

        1. 测试功能与测试点:
           - 验证 NormalizedReconciliationEngine.build_candidate_queue 队列编排能力。
           - 支持目标分组 (如 sp500) 与自定义代码指定 (tickers_override)。

        2. 正常函数业务边界与参数契约:
           - target_group 或 tickers_override 非空。

        3. 测试数据与模拟场景说明:
           - 场景 1: target_group="sp500"。
           - 场景 2: tickers_override=["NVDA", "AAPL", "MSFT"]。

        4. 预期断言与结果验证:
           - 标普队列长度 >= 500。
           - 自定义队列长度精确为 3，代码严格对齐。
        """
        mgr = NormalizedReconciliationStateManager(self.test_state_path)
        engine = NormalizedReconciliationEngine(state_mgr=mgr)

        # 1. 标普500核心队列
        sp500_queue = engine.build_candidate_queue(target_group="sp500")
        self.assertGreaterEqual(len(sp500_queue), 500)

        # 2. 按代码指定队列
        custom_queue = engine.build_candidate_queue(tickers_override=["NVDA", "AAPL", "MSFT"])
        self.assertEqual(len(custom_queue), 3)
        self.assertEqual([c.ticker for c in custom_queue], ["NVDA", "AAPL", "MSFT"])

    def test_07_dry_run_pipeline(self):
        """【IT-RECON-08: 批量平账流水线 Dry-Run 试运行模式与任务预览】

        1. 测试功能与测试点:
           - 验证流水线在 dry_run=True 模式下只产生推演计划，不真实写盘修改底账。
           - 为批处理运维与审计人员提供无副作用预览能力。

        2. 正常函数业务边界与参数契约:
           - dry_run=True, limit=5。

        3. 测试数据与模拟场景说明:
           - 调度 sp500 前 5 家进行空跑演练。

        4. 预期断言与结果验证:
           - 断言 status == 'DRY_RUN_COMPLETED'。
           - 断言 pending_targets_count >= 1。
           - 断言 preview 长度 <= 5。
        """
        mgr = NormalizedReconciliationStateManager(self.test_state_path)
        engine = NormalizedReconciliationEngine(
            state_mgr=mgr,
            lock=ReconciliationProcessLock(self.test_lock_path),
        )

        res = engine.run_reconciliation_batch(
            target_group="sp500",
            limit=5,
            dry_run=True,
        )
        self.assertEqual(res["status"], "DRY_RUN_COMPLETED")
        self.assertGreaterEqual(res["pending_targets_count"], 1)
        self.assertLessEqual(len(res["preview"]), 5)

    def test_08_reconcile_existing_verified_company(self):
        """【IT-RECON-09: 真实标的(VRT)官方财报刚性平账自检与相对误差限(<0.1%)】

        1. 测试功能与测试点:
           - 验证 reconcile_company 针对真实标的 (Vertiv, VRT) 执行三表平账运算。
           - 验证 balance_sheet_rel_ratio <= 0.1% 强约束。

        2. 正常函数业务边界与参数契约:
           - 输入合法 UniverseCompanyRecord。

        3. 测试数据与模拟场景说明:
           - VRT (Tier 1, CIK 0001674101)。

        4. 预期断言与结果验证:
           - 断言 ticker == 'VRT'。
           - 断言 is_balanced 为 True 且 balance_sheet_rel_ratio <= 0.001。
           - 断言 total_assets > 0 且 revenue > 0。
        """
        mgr = NormalizedReconciliationStateManager(self.test_state_path)
        engine = NormalizedReconciliationEngine(state_mgr=mgr)

        record = UniverseCompanyRecord(
            ticker="VRT",
            company_name="Vertiv Holdings Co",
            market="US",
            tier="TIER_1",
            cik="0001674101",
        )
        res = engine.reconcile_company(record, force_refresh=False)
        self.assertEqual(res.ticker, "VRT")
        self.assertTrue(res.is_balanced)
        self.assertLessEqual(res.balance_sheet_rel_ratio, 0.001)
        self.assertGreater(res.total_assets, 0)
        self.assertGreater(res.revenue, 0)

    def test_09_replenishment_manifest_sync(self):
        """【IT-RECON-10: 缺失破损财报自动识别并同步导出AI浏览器补数清单】

        1. 测试功能与测试点:
           - 验证当遇到残缺科目或无法平账时，引擎自动生成结构化补数清单 (replenishment manifest)。
           - 清单指明缺失原因与官方 SEC EDGAR 检索指引，绝不伪造虚假数据。

        2. 正常函数业务边界与参数契约:
           - 输出符合 schema 的 JSON 清单文件。

        3. 测试数据与模拟场景说明:
           - 注入破损标的 TEST_DEFICIENT (原因: Missing Assets line item)。

        4. 预期断言与结果验证:
           - 断言 manifest_path 物理存在。
           - 断言 total_pending_companies == 1。
           - 断言 target_filing 包含 'SEC EDGAR'。
        """
        mgr = NormalizedReconciliationStateManager(self.test_state_path)
        engine = NormalizedReconciliationEngine(state_mgr=mgr)

        deficient = [{
            "ticker": "TEST_DEFICIENT",
            "market": "US",
            "company_name": "Deficient Corp",
            "cik": "0009999999",
            "reason": "Missing Assets line item",
        }]
        engine._sync_replenishment_manifest(deficient, self.test_manifest_path)

        self.assertTrue(self.test_manifest_path.exists())
        import json
        manifest = json.loads(self.test_manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["total_pending_companies"], 1)
        self.assertEqual(manifest["tasks"][0]["ticker"], "TEST_DEFICIENT")
        self.assertIn("SEC EDGAR", manifest["tasks"][0]["target_filing"])


if __name__ == "__main__":
    unittest.main()
