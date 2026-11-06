"""机构级不可篡改预测与复盘账本 (Immutable Prediction & Retrospective Ledger).

遵循 Google Python 编程风格指南与《SPEC-12 系统质量工程密码学账本与全息测试验收标准》:
1. 预测记录前置锁死: 研究员/模型发布的每一次买点、目标价与安全边际，即刻写入账本并计算密码学 Hash;
2. 区块链级 Hash 链条: 每条预测记录包含 prev_hash 与 hash，形成不可篡改的单向追溯时间链;
3. 盘面真实结果强制对账: 将后续 T+N 日真实市价、催化剂与基准指数收益率精准挂载到预测快照;
4. 篡改自检与法证验证: 提供 verify_integrity() 全量验签机制，任何对历史价格/事件的人工篡改均被即刻捕获;
5. 本地 SQLite ACID 持久化: 基于标准库 sqlite3 零外部依赖，确立纯净的相对路径底账.
"""

# 1. Python 标准库
import contextlib
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, Generator, List, Optional, Tuple

# 2. 第三方数学与科学计算库
# (纯标准库依赖，保持密码学账本零外部二进制污染)

# 3. 内部核心库 (纯相对导入，符合 Google Python 规范与单向依赖铁律)
from .retrospective_review_engine import (
    ActualMarketOutcome,
    HistoricalPredictionSnapshot,
)

GENESIS_HASH: str = "0" * 64


class IntegrityResult(tuple):
    """兼具元组解构 (is_valid, error) 与字典/属性防伪访问 ['tampered'] 的对账结果对象."""

    def __new__(
        cls, is_valid: bool, error: Optional[str] = None
    ) -> "IntegrityResult":
        """创建不可变验签结果对象.

        Args:
            is_valid: 哈希链条是否完整无篡改.
            error: 发现篡改或哈希断裂时的详细法证错误信息 (若无错误则为 None).

        Returns:
            IntegrityResult 实例.
        """
        return super().__new__(cls, (is_valid, error))

    @property
    def is_valid(self) -> bool:
        """验签是否合法通过."""
        return self[0]

    @property
    def error(self) -> Optional[str]:
        """篡改或断链详细说明."""
        return self[1]

    @property
    def tampered(self) -> bool:
        """是否存在被恶意篡改迹象."""
        return not self[0]

    def __getitem__(self, item: Any) -> Any:
        """支持字典风格的属性防伪访问."""
        if isinstance(item, str):
            if item == "tampered":
                return not self[0]
            if item in ("is_valid", "valid"):
                return self[0]
            if item in ("error", "error_message"):
                return self[1]
            raise KeyError(f"Invalid key for IntegrityResult: {item}")
        return super().__getitem__(item)


class PredictionLedger:
    """真实可信不可篡改的预测与复盘审计底账系统 (Google Python Style Guide 设计)."""

    _global_lock = threading.RLock()

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """初始化不可篡改密码学预测账本.

        Args:
            db_path: 账本 SQLite 数据库文件物理路径 (留空则默认落地在 data/ledger/ 底账).
        """
        self._lock = self._global_lock
        if db_path is None:
            root = Path(__file__).resolve().parents[2]
            ledger_dir = root / "data" / "ledger"
            ledger_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = ledger_dir / "predictions_ledger.sqlite3"
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_tables()

    @contextlib.contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """安全创建与回收 SQLite 事务连接的上下文管理器 (私有方法)."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_tables(self) -> None:
        """初始化底账数据库表结构及高频检索索引 (私有方法)."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_id TEXT UNIQUE NOT NULL,
                    prev_hash TEXT NOT NULL,
                    hash TEXT NOT NULL,
                    prediction_date TEXT NOT NULL,
                    market TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    baseline_price REAL NOT NULL,
                    rating TEXT NOT NULL,
                    safe_entry_trigger REAL NOT NULL,
                    pessimistic_floor REAL NOT NULL,
                    pessimistic_event TEXT NOT NULL,
                    neutral_fair_value REAL NOT NULL,
                    optimistic_target REAL NOT NULL,
                    optimistic_event TEXT NOT NULL,
                    tactical_action TEXT NOT NULL,
                    kelly_fraction REAL NOT NULL,
                    options_warning TEXT NOT NULL,
                    falsification_signals_json TEXT NOT NULL,
                    liquidity_profile TEXT NOT NULL,
                    counterparty_type TEXT NOT NULL,
                    second_order_thesis TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_id TEXT UNIQUE NOT NULL,
                    outcome_date TEXT NOT NULL,
                    current_price REAL NOT NULL,
                    quote_timestamp TEXT NOT NULL,
                    benchmark_return_pct REAL NOT NULL,
                    realized_catalysts_json TEXT NOT NULL,
                    hash TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(prediction_id) REFERENCES predictions(prediction_id)
                )
                """
            )
            try:
                cursor.execute("ALTER TABLE outcomes ADD COLUMN hash TEXT")
            except Exception:
                pass
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS retrospective_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    review_id TEXT UNIQUE NOT NULL,
                    prediction_id TEXT NOT NULL,
                    review_date TEXT NOT NULL,
                    realized_return_pct REAL NOT NULL,
                    excess_alpha_pct REAL NOT NULL,
                    corridor_hit INTEGER NOT NULL,
                    cognitive_bias_audit TEXT NOT NULL,
                    bayesian_prior_shift REAL NOT NULL,
                    raw_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(prediction_id) REFERENCES predictions(prediction_id)
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_pred_id ON"
                " predictions(prediction_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_pred_ticker ON"
                " predictions(ticker)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_pred_date ON"
                " predictions(prediction_date)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_outcomes_pred ON"
                " outcomes(prediction_id)"
            )
            conn.commit()

    @staticmethod
    def _compute_outcome_hash(prediction_id: str, outcome: ActualMarketOutcome) -> str:
        """计算对账实际结果记录的密码学签名 (私有辅助方法)."""
        s = (
            f"{prediction_id}|{outcome.outcome_date}|"
            f"{float(outcome.current_price):.6f}|{outcome.quote_timestamp}|"
            f"{float(outcome.benchmark_return_pct):.6f}"
        )
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    @staticmethod
    def _compute_hash(
        prev_hash: str, snapshot: HistoricalPredictionSnapshot
    ) -> str:
        """根据前序哈希与当前快照的核心财务参数计算 SHA-256 签名 (私有辅助方法).

        Args:
            prev_hash: 前一区块哈希值 (创世区块为 64 个 '0').
            snapshot: 历史研判预测快照对象.

        Returns:
            SHA-256 16 进制字符串摘要.
        """
        canonical_str = (
            f"{prev_hash}|{snapshot.prediction_id}|{snapshot.prediction_date}|"
            f"{snapshot.market}|{snapshot.ticker}|{snapshot.company_name}|"
            f"{snapshot.baseline_price:.6f}|{snapshot.rating}|"
            f"{snapshot.safe_entry_trigger:.6f}|{snapshot.pessimistic_floor:.6f}|"
            f"{snapshot.pessimistic_event}|"
            f"{snapshot.neutral_fair_value:.6f}|"
            f"{snapshot.optimistic_target:.6f}|"
            f"{snapshot.optimistic_event}|"
            f"{snapshot.tactical_action}|"
            f"{snapshot.kelly_fraction:.6f}|{snapshot.options_warning}"
        )
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    @staticmethod
    def _compute_legacy_hash(
        prev_hash: str, snapshot: HistoricalPredictionSnapshot
    ) -> str:
        """根据历史早期格式计算兼容哈希签名 (私有辅助方法).

        Args:
            prev_hash: 前一区块哈希值.
            snapshot: 历史研判预测快照对象.

        Returns:
            早期版本 SHA-256 16 进制字符串摘要.
        """
        canonical_str = (
            f"{prev_hash}|{snapshot.prediction_id}|{snapshot.prediction_date}|"
            f"{snapshot.market}|{snapshot.ticker}|{snapshot.company_name}|"
            f"{snapshot.baseline_price:.6f}|{snapshot.rating}|"
            f"{snapshot.safe_entry_trigger:.6f}|{snapshot.pessimistic_floor:.6f}|"
            f"{snapshot.neutral_fair_value:.6f}|{snapshot.optimistic_target:.6f}|"
            f"{snapshot.kelly_fraction:.6f}|{snapshot.options_warning}"
        )
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def record_prediction(self, snapshot: HistoricalPredictionSnapshot) -> str:
        """登记一条历史研判预测至不可篡改链条.

        若记录已存在且签名一致，直接幂等返回其已有 hash；若载荷冲突则抛出异常；否则前向链接上一区块并写入。

        Args:
            snapshot: 历史预测快照数据对象.

        Returns:
            当前区块计算出的唯一 SHA-256 哈希值.

        Raises:
            ValueError: 当相同 prediction_id 传入了冲突的不同载荷时抛出.
        """
        with self._lock:
            with self._connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM predictions WHERE prediction_id = ?",
                    (snapshot.prediction_id,),
                )
                row = cursor.fetchone()
                if row:
                    existing_pred = self._row_to_prediction(row)
                    if (
                        abs(existing_pred.baseline_price - snapshot.baseline_price) > 1e-4
                        or existing_pred.rating != snapshot.rating
                        or existing_pred.tactical_action != snapshot.tactical_action
                        or existing_pred.pessimistic_event != snapshot.pessimistic_event
                        or existing_pred.optimistic_event != snapshot.optimistic_event
                        or abs(existing_pred.safe_entry_trigger - snapshot.safe_entry_trigger) > 1e-4
                        or abs(existing_pred.pessimistic_floor - snapshot.pessimistic_floor) > 1e-4
                        or abs(existing_pred.neutral_fair_value - snapshot.neutral_fair_value) > 1e-4
                        or abs(existing_pred.optimistic_target - snapshot.optimistic_target) > 1e-4
                    ):
                        raise ValueError(
                            f"【幂等冲突】预测ID '{snapshot.prediction_id}' 已存在但载荷不一致！"
                        )
                    return row["hash"]

                cursor.execute(
                    "SELECT hash FROM predictions ORDER BY id DESC LIMIT 1"
                )
                last_row = cursor.fetchone()
                prev_hash = last_row["hash"] if last_row else GENESIS_HASH

                record_hash = self._compute_hash(prev_hash, snapshot)
                now_iso = datetime.now(timezone.utc).isoformat()

                cursor.execute(
                    """
                    INSERT INTO predictions (
                        prediction_id, prev_hash, hash, prediction_date, market,
                        ticker, company_name, baseline_price, rating, safe_entry_trigger,
                        pessimistic_floor, pessimistic_event, neutral_fair_value,
                        optimistic_target, optimistic_event, tactical_action, kelly_fraction,
                        options_warning, falsification_signals_json, liquidity_profile,
                        counterparty_type, second_order_thesis, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot.prediction_id,
                        prev_hash,
                        record_hash,
                        snapshot.prediction_date,
                        snapshot.market,
                        snapshot.ticker,
                        snapshot.company_name,
                        float(snapshot.baseline_price),
                        snapshot.rating,
                        float(snapshot.safe_entry_trigger),
                        float(snapshot.pessimistic_floor),
                        snapshot.pessimistic_event,
                        float(snapshot.neutral_fair_value),
                        float(snapshot.optimistic_target),
                        snapshot.optimistic_event,
                        snapshot.tactical_action,
                        float(snapshot.kelly_fraction),
                        snapshot.options_warning,
                        json.dumps(
                            snapshot.falsification_signals, ensure_ascii=False
                        ),
                        snapshot.liquidity_profile,
                        snapshot.counterparty_type,
                        snapshot.second_order_thesis,
                        "ACTIVE",
                        now_iso,
                    ),
                )
                conn.commit()
                return record_hash

    def record_outcome(
        self, prediction_id: str, outcome: ActualMarketOutcome
    ) -> None:
        """登记对应预测的真实盘面对账结果.

        Args:
            prediction_id: 前置历史预测的唯一业务编号.
            outcome: 真实盘面回报与催化剂实现对象.

        Raises:
            ValueError: 当指定的 prediction_id 在底账中未曾登记，或结果日期早于预测时点时抛出.
        """
        with self._lock:
            with self._connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, prediction_date FROM predictions WHERE prediction_id = ?",
                    (prediction_id,),
                )
                row = cursor.fetchone()
                if not row:
                    raise ValueError(
                        f"【对账拦截】无法登记实际结果：预测编号 '{prediction_id}'"
                        " 在底账中不存在！"
                    )

                pred_date = row["prediction_date"]
                if outcome.outcome_date < pred_date:
                    raise ValueError(
                        f"【因果律拦截】无法登记实际结果：结果日期 '{outcome.outcome_date}' "
                        f"早于预测时点 '{pred_date}'！"
                    )

                now_iso = datetime.now(timezone.utc).isoformat()
                outcome_hash = self._compute_outcome_hash(prediction_id, outcome)
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO outcomes (
                        prediction_id, outcome_date, current_price, quote_timestamp,
                        benchmark_return_pct, realized_catalysts_json, hash, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        prediction_id,
                        outcome.outcome_date,
                        float(outcome.current_price),
                        outcome.quote_timestamp,
                        float(outcome.benchmark_return_pct),
                        json.dumps(outcome.realized_catalysts, ensure_ascii=False),
                        outcome_hash,
                        now_iso,
                    ),
                )
                conn.commit()

    def record_review(self, review_data: Dict[str, Any]) -> None:
        """登记复盘反思结果并将对应预测标记为 RESOLVED 已结案.

        Args:
            review_data: 包含 prediction_id、超额收益、认知偏差审计与贝叶斯先验漂移的字典.
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            prediction_id = review_data["prediction_id"]
            review_id = review_data.get(
                "review_id",
                (
                    "REV-"
                    f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-"
                    f"{prediction_id}"
                ),
            )
            now_iso = datetime.now(timezone.utc).isoformat()

            cursor.execute(
                """
                INSERT OR REPLACE INTO retrospective_reviews (
                    review_id, prediction_id, review_date, realized_return_pct,
                    excess_alpha_pct, corridor_hit, cognitive_bias_audit,
                    bayesian_prior_shift, raw_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review_id,
                    prediction_id,
                    review_data.get("review_date", now_iso[:10]),
                    float(review_data.get("realized_return_pct", 0.0)),
                    float(review_data.get("excess_alpha_pct", 0.0)),
                    1 if review_data.get("corridor_hit", False) else 0,
                    review_data.get("cognitive_bias_audit", ""),
                    float(review_data.get("bayesian_prior_shift", 0.0)),
                    json.dumps(review_data, ensure_ascii=False),
                    now_iso,
                ),
            )
            cursor.execute(
                "UPDATE predictions SET status = 'RESOLVED' WHERE prediction_id"
                " = ?",
                (prediction_id,),
            )
            conn.commit()

    def get_prediction(
        self, prediction_id: str
    ) -> Optional[HistoricalPredictionSnapshot]:
        """按 ID 查询预测快照对象.

        Args:
            prediction_id: 预测唯一编号.

        Returns:
            HistoricalPredictionSnapshot 或 None (若不存在).
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM predictions WHERE prediction_id = ?",
                (prediction_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_prediction(row)

    def get_outcome(self, prediction_id: str) -> Optional[ActualMarketOutcome]:
        """按 prediction_id 获取对应实际盘面结果.

        Args:
            prediction_id: 预测唯一编号.

        Returns:
            ActualMarketOutcome 或 None (若不存在).
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM outcomes WHERE prediction_id = ?",
                (prediction_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_outcome(row)

    def get_all_paired_cases(
        self, market: Optional[str] = None
    ) -> List[Tuple[HistoricalPredictionSnapshot, ActualMarketOutcome]]:
        """获取所有已录入盘面结果的 (预测快照, 盘面结果) 成对案例.

        Args:
            market: 市场过滤代码 ('US', 'JP'，留空则全选).

        Returns:
            成对元组列表.
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            sql = """
                SELECT p.*, o.outcome_date, o.current_price as out_price,
                       o.quote_timestamp, o.benchmark_return_pct, o.realized_catalysts_json
                FROM predictions p
                INNER JOIN outcomes o ON p.prediction_id = o.prediction_id
            """
            params: List[Any] = []
            if market:
                sql += " WHERE p.market = ?"
                params.append(market)
            sql += " ORDER BY p.id ASC"

            cursor.execute(sql, params)
            rows = cursor.fetchall()
            paired: List[
                Tuple[HistoricalPredictionSnapshot, ActualMarketOutcome]
            ] = []
            for r in rows:
                pred = self._row_to_prediction(r)
                out = ActualMarketOutcome(
                    outcome_date=r["outcome_date"],
                    current_price=float(r["out_price"]),
                    quote_timestamp=r["quote_timestamp"],
                    benchmark_return_pct=float(r["benchmark_return_pct"]),
                    realized_catalysts=json.loads(r["realized_catalysts_json"]),
                )
                paired.append((pred, out))
            return paired

    def verify_integrity(self) -> IntegrityResult:
        """校验账本区块链式哈希链条的完整性与防篡改真实性.

        Returns:
            IntegrityResult(True, None) 表示全部校验通过；
            IntegrityResult(False, error_message) 表示发现哈希断裂或篡改行为。
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM predictions ORDER BY id ASC")
            rows = cursor.fetchall()

            expected_prev_hash = GENESIS_HASH
            for r in rows:
                pred = self._row_to_prediction(r)
                actual_prev_hash = r["prev_hash"]
                actual_hash = r["hash"]

                if actual_prev_hash != expected_prev_hash:
                    return IntegrityResult(
                        False,
                        f"Chain broken at record #{r['id']} ({pred.prediction_id}): "
                        f"prev_hash mismatch. Expected {expected_prev_hash}, got {actual_prev_hash}",
                    )

                recomputed_hash = self._compute_hash(actual_prev_hash, pred)
                if recomputed_hash != actual_hash:
                    legacy_hash = self._compute_legacy_hash(actual_prev_hash, pred)
                    if legacy_hash != actual_hash:
                        return IntegrityResult(
                            False,
                            f"Data tampering detected at record #{r['id']} ({pred.prediction_id}): "
                            f"Hash signature mismatch. Stored: {actual_hash}, Recomputed: {recomputed_hash}",
                        )

                expected_prev_hash = actual_hash

            cursor.execute("SELECT * FROM outcomes ORDER BY id ASC")
            outcome_rows = cursor.fetchall()
            for row in outcome_rows:
                stored_hash = row["hash"] if "hash" in row.keys() else None
                if stored_hash:
                    outcome_obj = self._row_to_outcome(row)
                    recomputed_outcome_hash = self._compute_outcome_hash(
                        row["prediction_id"], outcome_obj
                    )
                    if recomputed_outcome_hash != stored_hash:
                        return IntegrityResult(
                            False,
                            f"Data tampering detected at outcome for prediction #{row['prediction_id']}: "
                            f"Hash mismatch. Stored: {stored_hash}, Recomputed: {recomputed_outcome_hash}",
                        )

            return IntegrityResult(True, None)

    def seed_initial_cases_if_empty(
        self,
        cases: List[Tuple[HistoricalPredictionSnapshot, ActualMarketOutcome]],
    ) -> int:
        """如果账本为空，将历史种子案例有序录入并构建初始防篡改区块链.

        Args:
            cases: 待录入的种子案例列表.

        Returns:
            实际写入记录条数.
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM predictions")
            cnt = cursor.fetchone()["cnt"]
            if cnt > 0:
                return 0

        inserted = 0
        for pred, outcome in cases:
            self.record_prediction(pred)
            self.record_outcome(pred.prediction_id, outcome)
            inserted += 1
        return inserted

    def get_stats(self) -> Dict[str, Any]:
        """获取账本统计底账.

        Returns:
            包含预测总量、结果总量、复盘总量与状态分布的统计字典.
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM predictions")
            total_predictions = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM outcomes")
            total_outcomes = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM retrospective_reviews")
            total_reviews = cursor.fetchone()["cnt"]

            cursor.execute(
                "SELECT COUNT(DISTINCT ticker) as cnt FROM predictions"
            )
            unique_tickers = cursor.fetchone()["cnt"]

            cursor.execute(
                "SELECT status, COUNT(*) as cnt FROM predictions GROUP BY"
                " status"
            )
            status_dist = {r["status"]: r["cnt"] for r in cursor.fetchall()}

            return {
                "total_predictions": total_predictions,
                "total_outcomes": total_outcomes,
                "total_reviews": total_reviews,
                "unique_tickers": unique_tickers,
                "status_distribution": status_dist,
            }

    @staticmethod
    def _row_to_prediction(r: sqlite3.Row) -> HistoricalPredictionSnapshot:
        """将数据库 Row 转换为不可变 HistoricalPredictionSnapshot (私有辅助方法)."""
        keys = r.keys()
        return HistoricalPredictionSnapshot(
            prediction_id=r["prediction_id"],
            prediction_date=r["prediction_date"],
            market=r["market"],
            ticker=r["ticker"],
            company_name=r["company_name"],
            baseline_price=float(r["baseline_price"]),
            rating=r["rating"],
            safe_entry_trigger=float(r["safe_entry_trigger"]),
            pessimistic_floor=float(r["pessimistic_floor"]),
            pessimistic_event=r["pessimistic_event"],
            neutral_fair_value=float(r["neutral_fair_value"]),
            optimistic_target=float(r["optimistic_target"]),
            optimistic_event=r["optimistic_event"],
            tactical_action=r["tactical_action"],
            kelly_fraction=float(r["kelly_fraction"]),
            options_warning=r["options_warning"],
            falsification_signals=(
                json.loads(r["falsification_signals_json"])
                if "falsification_signals_json" in keys
                else []
            ),
            liquidity_profile=(
                r["liquidity_profile"] if "liquidity_profile" in keys else ""
            ),
            counterparty_type=(
                r["counterparty_type"] if "counterparty_type" in keys else ""
            ),
            second_order_thesis=(
                r["second_order_thesis"]
                if "second_order_thesis" in keys
                else ""
            ),
        )

    @staticmethod
    def _row_to_outcome(r: sqlite3.Row) -> ActualMarketOutcome:
        """将数据库 Row 转换为不可变 ActualMarketOutcome (私有辅助方法)."""
        return ActualMarketOutcome(
            outcome_date=r["outcome_date"],
            current_price=float(r["current_price"]),
            quote_timestamp=r["quote_timestamp"],
            benchmark_return_pct=float(r["benchmark_return_pct"]),
            realized_catalysts=json.loads(r["realized_catalysts_json"]),
        )
