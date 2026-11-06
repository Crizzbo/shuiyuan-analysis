"""单元测试：不可篡改预测与复盘账本 (Prediction Ledger Test Suite).

覆盖核心机制：
1. 哈希链条生成与密码学完整性校验；
2. 防篡改检测（模拟黑客或人为恶意修改历史市价与评级，断言检测报警）；
3. 盘面实际结果对账入库与成对案例提取；
4. 复盘反思记录持久化与生命周期状态流转 (ACTIVE -> RESOLVED)；
5. 幂等性与初始案例种子注入机制。
"""

import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from financial_core.engines.prediction_ledger import (
    PredictionLedger,
    GENESIS_HASH,
)
from financial_core.engines.retrospective_review_engine import (
    HistoricalPredictionSnapshot,
    ActualMarketOutcome,
)


class TestPredictionLedger(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_ledger.sqlite3"
        self.ledger = PredictionLedger(db_path=self.db_path)

        self.sample_snapshot1 = HistoricalPredictionSnapshot(
            prediction_id="PRED-20261014-NVDA",
            prediction_date="2026-10-14",
            market="US",
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            baseline_price=132.40,
            rating="旗舰核心重仓 (Top Pick)",
            safe_entry_trigger=118.00,
            pessimistic_floor=105.00,
            pessimistic_event="云厂商 AI 资本开支进入消化周期",
            neutral_fair_value=155.00,
            optimistic_target=185.00,
            optimistic_event="Blackwell 全面量产且主权 AI 采购激增",
            tactical_action="维持 15%~20% 核心底仓，回调坚决加仓",
            kelly_fraction=0.18,
            options_warning="平值 Call 大单主导，多头趋势稳健",
        )

        self.sample_snapshot2 = HistoricalPredictionSnapshot(
            prediction_id="PRED-20261014-8035",
            prediction_date="2026-10-14",
            market="JP",
            ticker="8035",
            company_name="Tokyo Electron Limited (东京电子)",
            baseline_price=28200.0,
            rating="强烈推荐买入 (Strong Buy)",
            safe_entry_trigger=25000.0,
            pessimistic_floor=22500.0,
            pessimistic_event="先进制程装机收入确认顺延",
            neutral_fair_value=32500.0,
            optimistic_target=39000.0,
            optimistic_event="2nm High-NA EUV 涂布设备密集放量",
            tactical_action="配置 10%~12% 作为日股进攻核心",
            kelly_fraction=0.12,
            options_warning="",
        )

        self.sample_outcome1 = ActualMarketOutcome(
            outcome_date="2026-10-15",
            current_price=132.80,
            quote_timestamp="2026-10-14 16:00 EDT",
            benchmark_return_pct=0.45,
            realized_catalysts=["Blackwell 供应链交货确认顺利推进"],
        )

    def tearDown(self):
        del self.ledger
        import gc
        gc.collect()
        self.temp_dir.cleanup()

    def _query(self, sql: str, params=()):
        conn = sqlite3.connect(str(self.db_path))
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            return cur.fetchall()
        finally:
            conn.close()

    def _execute(self, sql: str, params=()):
        conn = sqlite3.connect(str(self.db_path))
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()
        finally:
            conn.close()

    def test_record_and_hash_chaining(self):
        """【IT-LEDGER-01: 研判记录写入与密码学SHA-256哈希时间链条生成】

        1. 测试功能与测试点:
           - 验证不可篡改研判账本的记录落盘与区块链式时间链条生成。
           - 创世区块约束: 第 1 条预测记录的 prev_hash 严格等于 GENESIS_HASH (64位全0十六进制)。
           - 单向链条约束: 第 N 条预测记录的 prev_hash 严格等于第 N-1 条记录的 SHA-256 hash。
           - 验证全链条密码学完整性巡检方法 verify_integrity() 返回有效。

        2. 正常函数业务边界与参数契约:
           - record_prediction 接收强类型 HistoricalPredictionSnapshot。
           - 内部自动计算哈希并存入 SQLite 数据库，返回该记录的 64 位 SHA-256 字符串。

        3. 测试数据与模拟场景说明:
           - 记录 1: 英伟达 (NVDA) 2026-10-14 买入研判，基准价 132.40。
           - 记录 2: 东京电子 (8035.T) 2026-10-14 强烈推荐研判，基准价 28,200.0。

        4. 预期断言与结果验证:
           - 断言返回哈希长度为 64。
           - 断言 ID=1 的 prev_hash 为 GENESIS_HASH。
           - 断言 ID=2 的 prev_hash 等于 ID=1 的 hash。
           - 断言 ledger.verify_integrity() 返回 (True, None)。
        """
        hash1 = self.ledger.record_prediction(self.sample_snapshot1)
        self.assertIsNotNone(hash1)
        self.assertEqual(len(hash1), 64)

        # 校验第一条记录 prev_hash 为 GENESIS_HASH
        rows = self._query("SELECT prev_hash, hash FROM predictions WHERE id = 1")
        self.assertEqual(rows[0][0], GENESIS_HASH)
        self.assertEqual(rows[0][1], hash1)

        # 录入第二条
        hash2 = self.ledger.record_prediction(self.sample_snapshot2)
        self.assertNotEqual(hash1, hash2)

        # 第二条的 prev_hash 必须严格等于第一条的 hash
        rows = self._query("SELECT prev_hash, hash FROM predictions WHERE id = 2")
        self.assertEqual(rows[0][0], hash1)
        self.assertEqual(rows[0][1], hash2)

        # 链条完整性校验
        is_valid, err = self.ledger.verify_integrity()
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_tampering_detection(self):
        """【IT-LEDGER-02: 恶意数据篡改检测与哈希链条防伪验签阻断】

        1. 测试功能与测试点:
           - 验证当外部人员或黑客直接通过底层 SQL 篡改历史研判数据（如修改推荐买入成本价）时，账本密码学防伪引擎能否精准识别并报错。

        2. 正常函数业务边界与参数契约:
           - 任何字段变更均会导致当前行重新计算的 SHA-256 与存储的 hash 不符，或破坏后继区块的 prev_hash 链条。

        3. 测试数据与模拟场景说明:
           - 录入 NVDA 与东京电子两条合法记录。
           - 模拟底层恶意 SQL 注入: 执行 UPDATE 将 NVDA 的买入价从 132.40 篡改为 110.00。

        4. 预期断言与结果验证:
           - 断言 verify_integrity() 返回 False。
           - 断言错误信息中包含 'Data tampering detected' 并准确点名受损单号 'PRED-20261014-NVDA'。
        """
        self.ledger.record_prediction(self.sample_snapshot1)
        self.ledger.record_prediction(self.sample_snapshot2)

        # 初始应通过
        is_valid, _ = self.ledger.verify_integrity()
        self.assertTrue(is_valid)

        # 模拟恶意篡改数据库：将 NVDA 初始买入价从 132.40 篡改为 110.00
        self._execute("UPDATE predictions SET baseline_price = 110.00 WHERE id = 1")

        # 校验必须失败并明确指出篡改记录
        is_valid, err = self.ledger.verify_integrity()
        self.assertFalse(is_valid)
        self.assertIn("Data tampering detected", err)
        self.assertIn("PRED-20261014-NVDA", err)

    def test_outcome_and_paired_cases(self):
        """【IT-LEDGER-03: 盘面实际结果对账入库与成对案例对账提取】

        1. 测试功能与测试点:
           - 验证 record_outcome 盘面实际表现结果的对账关联。
           - 验证 get_all_paired_cases 能否将历史研判与真实结果精准拼接为分析对照对。

        2. 正常函数业务边界与参数契约:
           - 必须基于 prediction_id 建立外键唯一约束关联。

        3. 测试数据与模拟场景说明:
           - 研判: NVDA 预测记录。
           - 盘面实际: 2026-10-15 现价 132.80，催化剂事实 'Blackwell 供应链交货确认顺利推进'。

        4. 预期断言与结果验证:
           - 断言 paired 列表长度为 1。
           - 断言配对提取出的 p.ticker 为 'NVDA'，o.current_price 为 132.80。
        """
        self.ledger.record_prediction(self.sample_snapshot1)
        self.ledger.record_outcome(self.sample_snapshot1.prediction_id, self.sample_outcome1)

        paired = self.ledger.get_all_paired_cases()
        self.assertEqual(len(paired), 1)
        p, o = paired[0]
        self.assertEqual(p.ticker, "NVDA")
        self.assertEqual(o.current_price, 132.80)
        self.assertEqual(o.realized_catalysts, ["Blackwell 供应链交货确认顺利推进"])

    def test_review_lifecycle(self):
        """【IT-LEDGER-04: 复盘反思记录持久化与研判生命周期状态流转】

        1. 测试功能与测试点:
           - 验证研判从待对账 (ACTIVE) 到已复盘归档 (RESOLVED) 的单向生命周期状态流转。
           - 验证 get_stats 统计摘要聚合计算正确性。

        2. 正常函数业务边界与参数契约:
           - 初始记录状态必须为 'ACTIVE'。
           - 录入 record_review 后，状态自动流转为 'RESOLVED'。

        3. 测试数据与模拟场景说明:
           - 录入 NVDA 研判与盘面结果后，录入复盘审计数据：超额收益率 -0.15%，走廊命中 corridor_hit=True。

        4. 预期断言与结果验证:
           - 初始状态断言为 'ACTIVE'。
           - 录入复盘后状态断言为 'RESOLVED'。
           - 断言统计汇总中 total_predictions=1, total_outcomes=1, total_reviews=1。
        """
        self.ledger.record_prediction(self.sample_snapshot1)
        self.ledger.record_outcome(self.sample_snapshot1.prediction_id, self.sample_outcome1)

        # 初始状态在表结构里默认为 ACTIVE
        rows = self._query("SELECT status FROM predictions WHERE prediction_id = 'PRED-20261014-NVDA'")
        self.assertEqual(rows[0][0], "ACTIVE")

        # 录入复盘结果
        review_data = {
            "prediction_id": "PRED-20261014-NVDA",
            "review_date": "2026-10-15",
            "realized_return_pct": 0.30,
            "excess_alpha_pct": -0.15,
            "corridor_hit": True,
            "cognitive_bias_audit": "平值多头平稳过渡，未触发 Gamma 抛售",
            "bayesian_prior_shift": 0.05,
        }
        self.ledger.record_review(review_data)

        # 状态应流转为 RESOLVED
        rows = self._query("SELECT status FROM predictions WHERE prediction_id = 'PRED-20261014-NVDA'")
        self.assertEqual(rows[0][0], "RESOLVED")

        stats = self.ledger.get_stats()
        self.assertEqual(stats["total_predictions"], 1)
        self.assertEqual(stats["total_outcomes"], 1)
        self.assertEqual(stats["total_reviews"], 1)
        self.assertEqual(stats["status_distribution"].get("RESOLVED"), 1)

    def test_seed_initial_cases_if_empty(self):
        """【IT-LEDGER-05: 空账本初始种子案例安全导入与幂等执行】

        1. 测试功能与测试点:
           - 验证 seed_initial_cases_if_empty 在系统冷启动空库时的安全导入。
           - 验证多次重复执行的强幂等性 (Idempotency)。

        2. 正常函数业务边界与参数契约:
           - 首次调用时插入数量为 len(cases)；后续调用插入数量为 0。

        3. 测试数据与模拟场景说明:
           - 传入 1 组初始种子案例，连续执行两次注入。

        4. 预期断言与结果验证:
           - 第一次断言 inserted == 1。
           - 第二次断言 inserted_again == 0。
           - 断言全链条验签依然通过 (is_valid == True)。
        """
        cases = [(self.sample_snapshot1, self.sample_outcome1)]
        inserted = self.ledger.seed_initial_cases_if_empty(cases)
        self.assertEqual(inserted, 1)

        # 重复调用应幂等跳过
        inserted_again = self.ledger.seed_initial_cases_if_empty(cases)
        self.assertEqual(inserted_again, 0)

        is_valid, _ = self.ledger.verify_integrity()
        self.assertTrue(is_valid)


if __name__ == "__main__":
    unittest.main()
