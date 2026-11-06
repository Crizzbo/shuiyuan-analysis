"""项目内内容归档、版本目录及研究快照。标准库 SQLite，无远程访问。"""
import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

from validate_knowledge_structure import ROOT, local_file
from validate_research import check_schema, instant, load, need, structural, validate

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

def digest(content):
    return hashlib.sha256(content).hexdigest()

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def destination(relative):
    raw = unquote(relative)
    need(not re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", raw) and not raw.startswith(("/", "\\")), "存储路径必须为项目内相对路径")
    resolved = (ROOT / raw).resolve()
    need(resolved.is_relative_to(ROOT) and resolved != ROOT, "存储位置越过项目边界")
    return resolved

DDL = """
CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS artifacts(
 sha256 TEXT PRIMARY KEY, local_path TEXT UNIQUE NOT NULL, size_bytes INTEGER NOT NULL,
 archived_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sources(
 source_id TEXT NOT NULL, revision INTEGER NOT NULL, manifest_json TEXT NOT NULL,
 sha256 TEXT NOT NULL REFERENCES artifacts(sha256), available_at TEXT NOT NULL,
 supersedes_revision INTEGER, registered_at TEXT NOT NULL,
 PRIMARY KEY(source_id,revision));
CREATE TABLE IF NOT EXISTS research(
 research_id TEXT NOT NULL, revision INTEGER NOT NULL, as_of TEXT NOT NULL,
 input_sha256 TEXT NOT NULL, snapshot_sha256 TEXT NOT NULL, snapshot_path TEXT UNIQUE NOT NULL,
 is_fictional INTEGER NOT NULL, archived_at TEXT NOT NULL,
 PRIMARY KEY(research_id,revision));
CREATE TABLE IF NOT EXISTS research_artifacts(
 research_id TEXT NOT NULL, revision INTEGER NOT NULL, role TEXT NOT NULL, item_id TEXT NOT NULL,
 original_path TEXT NOT NULL, sha256 TEXT NOT NULL REFERENCES artifacts(sha256),
 PRIMARY KEY(research_id,revision,role,item_id),
 FOREIGN KEY(research_id,revision) REFERENCES research(research_id,revision));
CREATE TABLE IF NOT EXISTS research_sources(
 research_id TEXT NOT NULL, revision INTEGER NOT NULL, evidence_id TEXT NOT NULL,
 source_id TEXT NOT NULL, source_revision INTEGER NOT NULL,
 PRIMARY KEY(research_id,revision,evidence_id),
 FOREIGN KEY(research_id,revision) REFERENCES research(research_id,revision),
 FOREIGN KEY(source_id,source_revision) REFERENCES sources(source_id,revision));
CREATE INDEX IF NOT EXISTS sources_asof ON sources(source_id,available_at);
CREATE INDEX IF NOT EXISTS research_asof ON research(research_id,as_of);
"""

CONTRACT_FILES = {
    "schema": "schemas/research.schema.json", "industries": "knowledge/taxonomy/industries.json",
    "business_models": "knowledge/taxonomy/business_models.json", "metrics": "knowledge/metrics/catalog.json",
    "industry_rules": "knowledge/taxonomy/industry_rules.json", "quality_policy": "data/quality-policy.json",
}

class LocalStore:
    def __init__(self, directory="data/catalog"):
        self.base = destination(directory)
        self.base.mkdir(parents=True, exist_ok=True)
        self.db_path = self.managed("catalog.sqlite3")
        self.db = sqlite3.connect(self.db_path, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(DDL)
        row = self.db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
        need(row is None or row[0] == "1", "存储版本不兼容，须迁移")
        self.db.execute("INSERT OR IGNORE INTO metadata VALUES('schema_version','1')")
        # 运行时禁止更新/删除历史目录；不是对文件所有者的权限隔离。
        for table in ("artifacts", "sources", "research", "research_artifacts", "research_sources"):
            for action in ("UPDATE", "DELETE"):
                self.db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT, 'append-only catalog'); END")
        self.db.commit()

    def managed(self, relative):
        path = (self.base / relative).resolve()
        need(path.is_relative_to(self.base) and path.is_relative_to(ROOT), "托管路径越界")
        return path

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    def _artifact(self, source_path):
        source = local_file(ROOT, source_path)
        content = source.read_bytes()
        sha = digest(content)
        path = self.managed(f"objects/{sha[:2]}/{sha}.blob")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            need(digest(path.read_bytes()) == sha, "既有原始归档被篡改")
        else:
            # 独占创建；失败事务留下未引用对象是允许的，可由审计识别。
            with path.open("xb") as handle:
                handle.write(content)
                handle.flush()
        relative = path.relative_to(ROOT).as_posix()
        existing = self.db.execute("SELECT * FROM artifacts WHERE sha256=?", (sha,)).fetchone()
        if existing:
            need(existing["local_path"] == relative and existing["size_bytes"] == len(content), "归档目录不一致")
        else:
            self.db.execute("INSERT INTO artifacts VALUES(?,?,?,?)", (sha, relative, len(content), now()))
        return sha, relative

    def register_source(self, manifest):
        schema = load(ROOT / "schemas/source-manifest.schema.json")
        check_schema(schema, schema)
        structural(manifest, schema, schema)
        need(instant(manifest["available_at"]) <= instant(manifest["acquired_at"]), "资料时间倒置")
        if manifest['published_at'] is not None:
            need(instant(manifest['published_at']) <= instant(manifest['available_at']), '资料发布时间倒置')
        period = manifest["effective_period"]
        need(period is None or period["start"] <= period["end"], "资料生效期间倒置")
        payload = canonical(manifest).decode("utf-8")
        with self.transaction():
            sha, path = self._artifact(manifest["source_path"])
            existing = self.db.execute("SELECT * FROM sources WHERE source_id=? AND revision=?", (manifest["source_id"], manifest["revision"])).fetchone()
            if existing:
                need(existing["manifest_json"] == payload and existing["sha256"] == sha, "同一资料版本不能覆盖")
                return {"source_id": manifest["source_id"], "revision": manifest["revision"], "sha256": sha, "archived_path": path, "idempotent": True}
            prev = self.db.execute("SELECT * FROM sources WHERE source_id=? ORDER BY revision DESC LIMIT 1", (manifest["source_id"],)).fetchone()
            if prev is None:
                need(manifest["revision"] == 1 and manifest["supersedes_revision"] is None, "首次资料版本必须为1")
            else:
                need(manifest["revision"] == prev["revision"]+1 and manifest["supersedes_revision"] == prev["revision"], "修订必须连续并引用前版")
                need(instant(manifest["available_at"]) >= instant(prev["available_at"]), "资料修订可得时间不能倒退")
            self.db.execute("INSERT INTO sources VALUES(?,?,?,?,?,?,?)", (manifest["source_id"], manifest["revision"], payload, sha, instant(manifest["available_at"]).isoformat(), manifest["supersedes_revision"], now()))
        return {"source_id": manifest["source_id"], "revision": manifest["revision"], "sha256": sha, "archived_path": path, "idempotent": False}

    def source_as_of(self, source_id, cutoff):
        bound = instant(cutoff)
        rows = self.db.execute("SELECT s.*, a.local_path FROM sources s JOIN artifacts a ON s.sha256=a.sha256 WHERE source_id=? ORDER BY revision DESC", (source_id,)).fetchall()
        for row in rows:
            if instant(row["available_at"]) <= bound:
                path = local_file(ROOT, row["local_path"])
                need(digest(path.read_bytes()) == row["sha256"], "资料归档完整性失败")
                return {"manifest": json.loads(row["manifest_json"]), "sha256": row["sha256"], "archived_path": row["local_path"]}
        return None

    def save_research(self, record, evidence_sources=None):
        validate(record)
        evidence_sources = evidence_sources or {}
        need(isinstance(evidence_sources, dict), "资料映射必须为对象")
        need(set(evidence_sources) <= {e["id"] for e in record["evidence"]}, "资料映射包含未知证据")
        if not record["is_fictional"]:
            need(set(evidence_sources) == {e["id"] for e in record["evidence"]}, "真实研究证据必须绑定登记资料版本")
        for e in record["evidence"]:
            link = evidence_sources.get(e["id"])
            if link is None:
                continue
            need(isinstance(link, dict) and set(link) == {"source_id", "revision"}, "资料版本映射字段错误")
            need(isinstance(link["source_id"], str) and type(link["revision"]) is int, "资料版本映射类型错误")
            row = self.db.execute("SELECT * FROM sources WHERE source_id=? AND revision=?", (link["source_id"], link["revision"])).fetchone()
            need(row is not None, "引用的登记资料版本不存在")
            source = json.loads(row["manifest_json"])
            need(source["source_kind"] == e["source_kind"], "证据与登记来源类型不一致")
            published_matches=(source['published_at'] is None and e['published_at'] is None) or (
                source['published_at'] is not None and e['published_at'] is not None and instant(source['published_at'])==instant(e['published_at']))
            need(published_matches and instant(source['available_at'])==instant(e['available_at']), '证据与登记资料时间不一致')
            if record['schema_version']=='1.1.0':
                precision=source.get('publication_precision','instant' if source['published_at'] is not None else 'unknown')
                published_date=source.get('published_date')
                if precision=='instant' and published_date is None:
                    published_date=instant(source['published_at']).date().isoformat()
                need(e['publication_precision']==precision and e['published_date']==published_date,'证据与登记资料的发布日期精度不一致')
            need(digest(local_file(ROOT, e["source_path"]).read_bytes()) == row["sha256"], "证据内容与登记版本不一致")
        contracts = {key: digest(local_file(ROOT, path).read_bytes()) for key, path in CONTRACT_FILES.items()}
        input_sha = digest(canonical({"record": record, "evidence_sources": evidence_sources, "contracts": contracts}))
        snapshot = json.loads(canonical(record))
        with self.transaction():
            existing = self.db.execute("SELECT * FROM research WHERE research_id=? AND revision=?", (record["research_id"], record["revision"])).fetchone()
            if existing:
                need(existing["input_sha256"] == input_sha, "同一研究修订不能覆盖")
                path = local_file(ROOT, existing["snapshot_path"])
                need(digest(path.read_bytes()) == existing["snapshot_sha256"], "研究快照被篡改")
                self._verify_research_attachments(record["research_id"], record["revision"])
                incoming = {(role, item["id"]): digest(local_file(ROOT, item[field]).read_bytes())
                    for role, field, items in (("evidence", "source_path", record["evidence"]), ("calculation_code", "implementation_path", record["calculations"])) for item in items}
                incoming.update({("contract", key): sha for key, sha in contracts.items()})
                saved = {(r["role"], r["item_id"]): r["sha256"] for r in self.db.execute("SELECT * FROM research_artifacts WHERE research_id=? AND revision=?", (record["research_id"], record["revision"]))}
                need(incoming == saved, "同修订所指文件内容已变化，必须创建新修订")
                return {"snapshot_path": existing["snapshot_path"], "sha256": existing["snapshot_sha256"], "idempotent": True}
            previous = self.db.execute("SELECT * FROM research WHERE research_id=? ORDER BY revision DESC LIMIT 1", (record["research_id"],)).fetchone()
            if previous is None:
                need(record["revision"] == 1, "首次研究修订必须为1")
            else:
                need(record["revision"] == previous["revision"]+1, "研究修订必须连续")
                prior = self.get_research(record["research_id"], previous["revision"])
                need(prior['schema_version']!='1.1.0' or record['schema_version']=='1.1.0','研究时间契约不能降级')
                # 恢复输入时原路径；档案保存路径不是业务资料变更。
                for item in self.db.execute("SELECT * FROM research_artifacts WHERE research_id=? AND revision=?", (record["research_id"], previous["revision"])):
                    if item["role"] == "contract":
                        continue
                    collection, field = ("evidence", "source_path") if item["role"] == "evidence" else ("calculations", "implementation_path")
                    for value in prior[collection]:
                        if value["id"] == item["item_id"]:
                            value[field] = item["original_path"]
                need(instant(record["as_of"]) >= instant(prior["as_of"]), "研究截止时间不能倒退")
                need(instant(record["recorded_at"]) >= instant(prior["recorded_at"]), "研究记录时间不能倒退")
                for old, new in zip(prior["steps"], record["steps"]):
                    need(new["version"] >= old["version"], "步骤版本不能倒退")
                    # 归档路径改写不构成业务变更；输入证据内容变化另由附件 hash 识别。
                    if any(old[key] != new[key] for key in ("output", "status", "inputs", "gates")):
                        need(new["version"] > old["version"], "步骤输入/输出/状态/门槛变化必须增加版本")
                    need(instant(new["updated_at"]) >= instant(old["updated_at"]), "步骤更新时间不能倒退")
            attachments = []
            for e in snapshot["evidence"]:
                original = e["source_path"]
                sha, archived = self._artifact(original)
                attachments.append(("evidence", e["id"], original, sha))
                e["source_path"] = archived
            for c in snapshot["calculations"]:
                original = c["implementation_path"]
                sha, archived = self._artifact(original)
                attachments.append(("calculation_code", c["id"], original, sha))
                c["implementation_path"] = archived
            for key, source_path in CONTRACT_FILES.items():
                sha, _ = self._artifact(source_path)
                attachments.append(("contract", key, source_path, sha))
            if previous is not None:
                prior_artifacts = {(r["role"], r["item_id"]): r["sha256"] for r in self.db.execute("SELECT * FROM research_artifacts WHERE research_id=? AND revision=?", (record["research_id"], previous["revision"]))}
                current_artifacts = {(role, item_id): sha for role, item_id, _, sha in attachments}
                previous_links = {r["evidence_id"]: {"source_id": r["source_id"], "revision": r["source_revision"]} for r in self.db.execute("SELECT * FROM research_sources WHERE research_id=? AND revision=?", (record["research_id"], previous["revision"]))}
                changed_inputs = prior_artifacts != current_artifacts or previous_links != evidence_sources or any(prior[key] != record[key] for key in ("schema_version", "subject", "evidence", "observations", "claims", "calculations", "as_of", "market_session_date", "investment_horizon_months", "is_fictional"))
                if changed_inputs:
                    # 保守策略：共享输入改变，所有已经开展的步骤须重审或重做。
                    for old, new in zip(prior["steps"], record["steps"]):
                        if old["status"] != "pending" or new["status"] != "pending":
                            need(new["version"] > old["version"], "共享输入变化后已开展步骤必须增加版本并重审")
            validate(snapshot)
            body = canonical(snapshot)
            snapshot_sha = digest(body)
            folder = digest(record["research_id"].encode("utf-8"))
            path = self.managed(f"research/{folder}/revision-{record['revision']:06d}.json")
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                need(path.read_bytes() == body, "遗留快照与新数据冲突")
            else:
                with path.open("xb") as handle:
                    handle.write(body)
                    handle.flush()
            relative = path.relative_to(ROOT).as_posix()
            self.db.execute("INSERT INTO research VALUES(?,?,?,?,?,?,?,?)", (record["research_id"], record["revision"], record["as_of"], input_sha, snapshot_sha, relative, int(record["is_fictional"]), now()))
            for role, item_id, original, sha in attachments:
                self.db.execute("INSERT INTO research_artifacts VALUES(?,?,?,?,?,?)", (record["research_id"], record["revision"], role, item_id, original, sha))
            for eid, link in evidence_sources.items():
                self.db.execute("INSERT INTO research_sources VALUES(?,?,?,?,?)", (record["research_id"], record["revision"], eid, link["source_id"], link["revision"]))
        return {"snapshot_path": relative, "sha256": snapshot_sha, "idempotent": False}

    def _verify_research_attachments(self, research_id, revision):
        rows = self.db.execute("SELECT a.* FROM research_artifacts r JOIN artifacts a ON r.sha256=a.sha256 WHERE research_id=? AND revision=?", (research_id, revision)).fetchall()
        for row in rows:
            need(digest(local_file(ROOT, row["local_path"]).read_bytes()) == row["sha256"], "研究附件完整性失败")

    def get_research(self, research_id, revision=None):
        if revision is None:
            row = self.db.execute("SELECT * FROM research WHERE research_id=? ORDER BY revision DESC LIMIT 1", (research_id,)).fetchone()
        else:
            row = self.db.execute("SELECT * FROM research WHERE research_id=? AND revision=?", (research_id, revision)).fetchone()
        need(row is not None, "研究记录不存在")
        path = local_file(ROOT, row["snapshot_path"])
        need(digest(path.read_bytes()) == row["snapshot_sha256"], "研究快照完整性失败")
        self._verify_research_attachments(research_id, row["revision"])
        record = load(path)
        context = self._research_context(research_id, row["revision"])
        validate(record, context)
        return record

    def _research_context(self, research_id, revision):
        rows = self.db.execute("SELECT r.item_id,a.local_path FROM research_artifacts r JOIN artifacts a ON r.sha256=a.sha256 WHERE research_id=? AND revision=? AND role='contract'", (research_id, revision)).fetchall()
        if not rows:
            return None  # 初始未固定契约的合成演示，仅可按当前定义读取，审计另行提醒。
        need({r["item_id"] for r in rows} == set(CONTRACT_FILES), "历史契约归档不完整")
        return {r["item_id"]: load(local_file(ROOT, r["local_path"])) for r in rows}

    def research_as_of(self, research_id, cutoff):
        """只返回当时已形成且信息截止不晚于查询时点的研究。"""
        bound = instant(cutoff)
        rows = self.db.execute("SELECT revision FROM research WHERE research_id=? ORDER BY revision DESC", (research_id,)).fetchall()
        for row in rows:
            record = self.get_research(research_id, row["revision"])
            if instant(record["as_of"]) <= bound and instant(record["recorded_at"]) <= bound:
                return record
        return None

    def backup(self, relative_directory):
        """创建自包含 SQLite＋对象副本；目标必须是项目内全新目录。"""
        import shutil
        target = destination(relative_directory)
        need(not target.exists() and not target.is_relative_to(self.base) and not self.base.is_relative_to(target), "备份须为独立且不存在的项目内目录")
        target.mkdir(parents=True)
        destination_db = sqlite3.connect(target / "catalog.sqlite3")
        try:
            self.db.backup(destination_db)
            rows = destination_db.execute("SELECT local_path,sha256 FROM artifacts").fetchall()
            snapshots = destination_db.execute("SELECT snapshot_path,snapshot_sha256 FROM research").fetchall()
            inventory = []
            for relative, sha in rows + snapshots:
                original = local_file(ROOT, relative)
                need(digest(original.read_bytes()) == sha, "备份遇到内容篡改")
                rel = original.relative_to(self.base)
                copy_path = (target / rel).resolve()
                need(copy_path.is_relative_to(target), "备份路径越界")
                copy_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, copy_path)
                need(digest(copy_path.read_bytes()) == sha, "备份内容校验失败")
                inventory.append({"relative_path": rel.as_posix(), "sha256": sha})
            manifest = {"schema_version": "1.0.0", "original_store": self.base.relative_to(ROOT).as_posix(),
                "created_at": now(), "database_sha256": digest((target / "catalog.sqlite3").read_bytes()), "files": inventory,
                "restore_note": "副本数据库保留原项目路径；恢复需放回原存储目录，不能直接将副本作为新目录打开"}
            (target / "backup-manifest.json").write_bytes(canonical(manifest))
        finally:
            destination_db.close()
        return {"backup_path": target.relative_to(ROOT).as_posix(), "files": len(inventory)}

    def audit(self):
        findings = []
        warnings = []
        registered_paths = set()
        for row in self.db.execute("SELECT * FROM artifacts"):
            registered_paths.add(row["local_path"])
            try:
                path = local_file(ROOT, row["local_path"])
                need(path.stat().st_size == row["size_bytes"] and digest(path.read_bytes()) == row["sha256"], "内容或大小改变")
            except ValueError as exc:
                findings.append({"kind": "artifact_integrity", "path": row["local_path"], "detail": str(exc)})
        for row in self.db.execute("SELECT * FROM research"):
            try:
                self.get_research(row["research_id"], row["revision"])
                if self._research_context(row["research_id"], row["revision"]) is None:
                    warnings.append({"kind": "legacy_unpinned_contract", "research_id": row["research_id"], "revision": row["revision"], "detail": "缺历史定义副本，只能按当前契约读，需复核"})
            except ValueError as exc:
                findings.append({"kind": "research_integrity", "research_id": row["research_id"], "revision": row["revision"], "detail": str(exc)})
        if self.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            findings.append({"kind": "database_integrity", "detail": "SQLite integrity_check failed"})
        for row in self.db.execute("PRAGMA foreign_key_check"):
            findings.append({"kind": "foreign_key", "detail": str(tuple(row))})
        orphan_objects = []
        objects = self.managed("objects")
        if objects.exists():
            for path in objects.rglob("*.blob"):
                if not path.resolve().is_relative_to(self.base):
                    findings.append({"kind": "path_boundary", "detail": "归档目录出现越界链接"})
                elif path.relative_to(ROOT).as_posix() not in registered_paths:
                    orphan_objects.append(path.relative_to(ROOT).as_posix())
        return {"ok": not findings, "findings": findings, "warnings": warnings, "sources": self.db.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
            "research_revisions": self.db.execute("SELECT COUNT(*) FROM research").fetchone()[0], "artifacts": self.db.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0],
            "orphan_objects": orphan_objects, "note": "未登记对象可能来自失败事务；仅报告，不自动删除"}

def verify_backup(relative_directory):
    base = destination(relative_directory)
    manifest = load(local_file(ROOT, (base / "backup-manifest.json").relative_to(ROOT).as_posix()))
    db_path = local_file(ROOT, (base / "catalog.sqlite3").relative_to(ROOT).as_posix())
    need(digest(db_path.read_bytes()) == manifest["database_sha256"], "备份数据库哈希不匹配")
    for item in manifest["files"]:
        path = destination((base.relative_to(ROOT) / item["relative_path"]).as_posix())
        need(path.is_relative_to(base) and path.is_file(), "备份对象越界或缺失")
        need(digest(path.read_bytes()) == item["sha256"], "备份对象哈希不匹配")
    conn = sqlite3.connect(db_path)
    try:
        need(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "备份数据库损坏")
        need(not conn.execute("PRAGMA foreign_key_check").fetchall(), "备份数据库关联损坏")
        source_base = destination(manifest["original_store"])
        expected = [(path, sha) for path, sha in conn.execute("SELECT local_path,sha256 FROM artifacts")] + [(path, sha) for path, sha in conn.execute("SELECT snapshot_path,snapshot_sha256 FROM research")]
        mapped = {}
        for original_path, sha in expected:
            original = destination(original_path)
            need(original.is_relative_to(source_base), "备份目录记录不属于原存储")
            mapped[original.relative_to(source_base).as_posix()] = sha
        supplied = {i["relative_path"]: i["sha256"] for i in manifest["files"]}
        need(len(supplied) == len(manifest["files"]) and mapped == supplied, "备份清单不完整或不匹配数据库")
    finally:
        conn.close()
    return {"ok": True, "files": len(manifest["files"]), "note": "已校验独立副本；实际恢复需放回原项目内存储目录"}
