"""通过PredictionLedger的兼容子类，追加历史验证产物的独立SHA-256审计链。"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from financial_core.engines.prediction_ledger import PredictionLedger, IntegrityResult, GENESIS_HASH


def local_path(root: Path, relative: str) -> Path:
    """拒绝绝对路径、URI、UNC及符号链接越界。"""
    if not isinstance(relative, str) or not relative or relative.startswith(("/", "\\")) or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", relative):
        raise ValueError("必须使用项目内相对路径")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("项目路径越界")
    return path


def digest_file(path: Path) -> str:
    """计算实际原文字节摘要。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


class HistoryValidationLedger(PredictionLedger):
    """保留父类预测/结果验签，并为通用验证产物增设独立链，不伪造股价预测字段。"""

    def __init__(self, root: Path, db_path: Path):
        self.validation_root = root.resolve()
        if not db_path.resolve().is_relative_to(self.validation_root):
            raise ValueError("验证账本必须位于项目内")
        super().__init__(db_path=db_path)
        with self._connection() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS validation_artifacts (id INTEGER PRIMARY KEY, prev_hash TEXT NOT NULL, payload TEXT NOT NULL, hash TEXT NOT NULL)")
            conn.commit()

    def append_validation(self, artifacts: list[Path], metadata: dict) -> str:
        """事务内检查链头，只追加；摘要关联原始输入、预测CSV及报告。"""
        if not self.verify_integrity().is_valid:
            raise ValueError("既有验证链或产物不完整，拒绝追加")
        entries = []
        for artifact in artifacts:
            relative = artifact.resolve().relative_to(self.validation_root).as_posix()
            entries.append({"path": relative, "sha256": digest_file(local_path(self.validation_root, relative))})
        payload = json.dumps({"created_at": datetime.now(timezone.utc).isoformat(), "artifacts": entries, "metadata": metadata}, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            previous = conn.execute("SELECT hash FROM validation_artifacts ORDER BY id DESC LIMIT 1").fetchone()
            prev = previous[0] if previous else GENESIS_HASH
            block_hash = hashlib.sha256((prev + payload).encode("utf-8")).hexdigest()
            conn.execute("INSERT INTO validation_artifacts(prev_hash,payload,hash) VALUES(?,?,?)", (prev, payload, block_hash))
            conn.commit()
        return block_hash

    def verify_integrity(self) -> IntegrityResult:
        """校验父链、验证链和每个本地产物，任何缺失/变更都失败。"""
        base = super().verify_integrity()
        if not base.is_valid:
            return base
        try:
            with self._connection() as conn:
                rows = conn.execute("SELECT prev_hash,payload,hash FROM validation_artifacts ORDER BY id").fetchall()
            prev = GENESIS_HASH
            for old, payload, current in rows:
                if old != prev or hashlib.sha256((prev + payload).encode("utf-8")).hexdigest() != current:
                    return IntegrityResult(False, "验证产物链断裂")
                for entry in json.loads(payload)["artifacts"]:
                    if digest_file(local_path(self.validation_root, entry["path"])) != entry["sha256"]:
                        return IntegrityResult(False, "验证输入或产物摘要不符")
                prev = current
            return IntegrityResult(True)
        except (OSError, ValueError, KeyError) as exc:
            return IntegrityResult(False, str(exc))
