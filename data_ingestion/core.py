"""公共接入设施。HTTP 使用既有 requests 库，不自行实现网络协议。"""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import sqlite3
import time
from urllib.parse import urlsplit, parse_qsl, urlencode, urlunsplit

import requests

ROOT = Path(__file__).resolve().parents[1]
SECRET_FIELDS = {"apikey", "api_key", "subscription-key", "appid", "userid", "registrationkey"}


class IngestionError(ValueError):
    """错误只含非敏感状态，不回显请求密钥或服务器正文。"""
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")


def project_path(relative):
    """拒绝绝对、盘符、反斜杠和父目录；真实路径必须留在项目内。"""
    path = Path(relative)
    if not relative or path.is_absolute() or ":" in relative or "\\" in relative or ".." in path.parts:
        raise ValueError("必须使用项目内相对路径")
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT) or resolved == ROOT:
        raise ValueError("路径越过项目边界")
    return resolved


def public_url(url, hosts):
    """所有请求及重定向均须命中显式域名，禁止账户 URI 和内网字面地址。"""
    p = urlsplit(url)
    if p.scheme != "https" or p.username or p.password or p.port not in (None, 443) or p.hostname not in hosts:
        raise IngestionError("invalid_request", "URL 不在配置的 HTTPS 域名范围")
    try:
        address = ipaddress.ip_address(p.hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise IngestionError("invalid_request", "禁止内网地址")
    if p.hostname == "localhost":
        raise IngestionError("invalid_request", "禁止本机地址")
    return url


def redacted_url(url):
    p = urlsplit(url)
    query = [(k, "REDACTED" if k.lower() in SECRET_FIELDS else v) for k, v in parse_qsl(p.query)]
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(query), ""))


def require_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise IngestionError("needs_configuration", f"请配置环境变量 {name}")
    return value


class Archive:
    """内容寻址原始归档及可重试任务账本；不将采集时间伪装为发布日期。"""
    def __init__(self, directory="data/ingestion"):
        self.base = project_path(directory)
        self.base.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.base / "state.sqlite3", timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS responses(
            id INTEGER PRIMARY KEY, request_id TEXT, provider TEXT, path TEXT,
            sha256 TEXT, acquired_at TEXT, metadata TEXT);
          CREATE TABLE IF NOT EXISTS budget(provider TEXT, day TEXT, used INTEGER,
            PRIMARY KEY(provider,day));
          CREATE TABLE IF NOT EXISTS pacing(provider TEXT PRIMARY KEY, last_at REAL);
          CREATE TABLE IF NOT EXISTS usage(provider TEXT, requested_at REAL);
          CREATE TABLE IF NOT EXISTS jobs(job_id TEXT PRIMARY KEY, result TEXT, updated_at TEXT);
        """)

    def close(self):
        self.db.close()

    def save(self, provider, request_id, content, metadata):
        sha = hashlib.sha256(content).hexdigest()
        path = self.base / "objects" / sha[:2] / f"{sha}.raw"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
                raise IngestionError("integrity_error", "既有归档摘要不匹配")
        else:
            # 独占创建，避免多个任务同时覆盖原文。
            try:
                with path.open("xb") as handle:
                    handle.write(content)
            except FileExistsError:
                if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
                    raise IngestionError("integrity_error", "并发归档摘要不匹配")
        acquired = utcnow()
        result = dict(metadata, provider=provider, source_path=path.relative_to(ROOT).as_posix(),
                      sha256=sha, acquired_at=acquired,
                      available_at=acquired, availability_basis="first_observed_by_project")
        # 首次观察时间是保守可得时点；历史发布时点留给供应商字段及独立审核。
        self.db.execute("INSERT INTO responses(request_id,provider,path,sha256,acquired_at,metadata) VALUES(?,?,?,?,?,?)",
                        (request_id, provider, result["source_path"], sha, acquired, encode(result).decode()))
        self.db.commit()
        return result

    def cached(self, request_id, ttl):
        row = self.db.execute("SELECT * FROM responses WHERE request_id=? ORDER BY id DESC LIMIT 1", (request_id,)).fetchone()
        if not row or time.time() - datetime.fromisoformat(row["acquired_at"]).timestamp() > ttl:
            return None
        path = project_path(row["path"])
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != row["sha256"]:
            raise IngestionError("integrity_error", "缓存归档被修改")
        return content, json.loads(row["metadata"])

    def reserve(self, provider, interval, daily_limit):
        """SQLite 事务跨进程共享额度；每次重试也占额度，免费上限不自动提高。"""
        day = datetime.now(timezone.utc).date().isoformat()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            used = self.db.execute("SELECT used FROM budget WHERE provider=? AND day=?", (provider, day)).fetchone()
            rolling = self.db.execute("SELECT COUNT(*) FROM usage WHERE provider=? AND requested_at>?", (provider, time.time() - 86400)).fetchone()[0]
            if daily_limit is not None and ((used and used[0] >= daily_limit) or rolling >= daily_limit):
                raise IngestionError("quota_exhausted", "项目保守日额度或滚动 24 小时额度已耗尽，请稍后重试")
            last = self.db.execute("SELECT last_at FROM pacing WHERE provider=?", (provider,)).fetchone()
            slot = max(time.time(), (last[0] + interval) if last else 0)
            self.db.execute("INSERT INTO budget VALUES(?,?,1) ON CONFLICT(provider,day) DO UPDATE SET used=used+1", (provider, day))
            self.db.execute("INSERT OR REPLACE INTO pacing VALUES(?,?)", (provider, slot))
            self.db.execute("INSERT INTO usage VALUES(?,?)", (provider, slot))
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise
        delay = slot - time.time()
        if delay > 0:
            time.sleep(delay)


class HTTP:
    def __init__(self, archive, sources, session=None):
        self.archive, self.sources = archive, sources
        self.session = session or requests.Session()

    def fetch(self, provider, url, params=None, headers=None, json_body=None, ttl=None, classification=None):
        config = self.sources[provider]
        if config.get("enabled") is False or config.get("env"):
            raise IngestionError("browser_required", "该来源已停用；请用 AI 浏览器检索官方公开原文")
        public_url(url, config["hosts"])
        clean_params = {k: v for k, v in (params or {}).items() if k.lower() not in SECRET_FIELDS}
        clean_body = {k: v for k, v in (json_body or {}).items() if k.lower() not in SECRET_FIELDS}
        # 密钥不参与持久化请求编号；只有公共查询语义参与缓存。
        request_id = hashlib.sha256(encode([provider, redacted_url(url), clean_params, clean_body])).hexdigest()
        cached = self.archive.cached(request_id, config.get("ttl_seconds", 3600) if ttl is None else ttl)
        if cached:
            return cached
        current, query = url, params
        for attempt in range(4):
            self.archive.reserve(provider, config.get("interval_seconds", 2), config.get("daily_limit"))
            try:
                response = self.session.request("POST" if json_body is not None else "GET", current,
                    params=query, headers=headers or {}, json=json_body, timeout=(10, 40),
                    allow_redirects=False)
            except requests.RequestException:
                if attempt == 3:
                    raise IngestionError("network_error", "网络连接失败；未记录任何响应为成功") from None
                time.sleep(2 ** attempt)
                continue
            if response.status_code in (301, 302, 303, 307, 308):
                from urllib.parse import urljoin
                current = public_url(urljoin(response.url, response.headers.get("Location", "")), config["hosts"])
                # 仅无密钥 GET 允许重定向，防止凭据跨域外泄。
                if json_body is not None or any(k.lower() in SECRET_FIELDS for k in (params or {})) or headers:
                    raise IngestionError("upstream_error", "带身份信息的请求拒绝重定向")
                query = None
                continue
            if response.status_code in (429, 500, 502, 503, 504):
                if attempt == 3:
                    raise IngestionError("rate_limited" if response.status_code == 429 else "upstream_error", f"HTTP {response.status_code}")
                retry = response.headers.get("Retry-After", "")
                try:
                    delay = float(retry)
                except ValueError:
                    try:
                        delay = parsedate_to_datetime(retry).timestamp() - time.time()
                    except (ValueError, TypeError, OverflowError):
                        delay = 2 ** attempt
                # 长等待交还任务账本，下次显式运行重试，避免无期限占用。
                if delay > 30:
                    raise IngestionError("rate_limited", "供应商要求较长等待，请稍后重新执行任务")
                time.sleep(max(0, delay))
                continue
            if response.status_code != 200:
                raise IngestionError("authentication_error" if response.status_code in (401,403) else "upstream_error", f"HTTP {response.status_code}")
            content = response.content
            if not content:
                raise IngestionError("empty_response", "上游返回空响应")
            if len(content) > 100 * 1024 * 1024:
                raise IngestionError("upstream_error", "响应超过单文件 100 MiB 限制")
            metadata = self.archive.save(provider, request_id, content,
                {"origin_url": redacted_url(response.url), "content_type": response.headers.get("Content-Type", ""),
                 "source_kind": (classification or {}).get("source_kind", config["source_kind"]),
                 "dataset_kind": (classification or {}).get("dataset_kind", config["dataset_kind"]),
                 "published_at": None, "quality_status": "unreviewed"})
            return content, metadata
        raise IngestionError("upstream_error", "重定向次数超过限制")


def json_response(content):
    """保留原始错误响应，但业务结果不得把错误对象当成有效数据。"""
    try:
        payload = json.loads(content)
    except (ValueError, UnicodeError):
        raise IngestionError("invalid_response", "预期 JSON，实际响应无法解析") from None
    if not isinstance(payload, (dict, list)):
        raise IngestionError("invalid_response", "JSON 根对象结构异常")
    if isinstance(payload, dict) and any(k in payload for k in ("Error Message", "Information", "Note", "error", "errors")):
        raise IngestionError("provider_error", "供应商返回错误、权限或限流信息")
    return payload
