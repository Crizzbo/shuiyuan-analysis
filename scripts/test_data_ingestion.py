"""接入层契约回归：错误响应、限流、归档、分页、断点恢复与来源边界。"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from data_ingestion.core import Archive, HTTP, IngestionError, encode, json_response, project_path, public_url, redacted_url
from data_ingestion.providers import Providers
from ingest_data import run_plan
from import_browser_source import import_document


class Response:
    def __init__(self, data, status=200, url="https://example.com/data", headers=None):
        self.content = data if isinstance(data, bytes) else encode(data)
        self.status_code, self.url = status, url
        self.headers = headers or {"Content-Type": "application/json"}


class Session:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), 0

    def request(self, *args, **kwargs):
        self.calls += 1
        return self.responses.pop(0)


class FakeHTTP:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []
        self.sources = {}

    def fetch(self, provider, url, **kwargs):
        self.calls.append((provider, url, kwargs))
        raw = next(self.replies)
        if not isinstance(raw, bytes):
            raw = encode(raw)
        return raw, {"source_path": "fixture", "sha256": hashlib.sha256(raw).hexdigest()}


class IngestionTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".cache").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".cache")
        self.archive = Archive(Path(self.temp.name).relative_to(ROOT).as_posix())
        self.sources = {"test": {"hosts": ["example.com"], "interval_seconds": 0,
            "daily_limit": 10, "ttl_seconds": 86400, "source_kind": "primary", "dataset_kind": "financial"}}

    def tearDown(self):
        self.archive.close()
        self.temp.cleanup()

    def test_cache_preserves_time_and_hash(self):
        """【UT-INGEST-01: 接入层本地缓存保真-时间戳与哈希一致性且零重复请求】

        1. 测试功能与测试点:
           - 验证 HTTP.fetch 本地归档缓存机制。
           - 首次请求写盘归档，二次请求直接命中本地缓存，网络请求次数为 1。

        2. 正常函数业务边界与参数契约:
           - 缓存命中时哈希值与元数据完全一致。

        3. 测试数据与模拟场景说明:
           - 模拟 GET https://example.com/data 返回 {"value": 1}。

        4. 预期断言与结果验证:
           - first == second。
           - session.calls == 1。
           - published_at 为 None。
        """
        session = Session([Response({"value": 1})])
        http = HTTP(self.archive, self.sources, session)
        first = http.fetch("test", "https://example.com/data")
        second = http.fetch("test", "https://example.com/data")
        self.assertEqual(first, second)
        self.assertEqual(session.calls, 1)
        self.assertIsNone(first[1]["published_at"])

    def test_key_not_in_archival_metadata(self):
        """【UT-INGEST-02: 敏感密钥物理脱敏-URL参数SECRET严禁落盘入元数据】

        1. 测试功能与测试点:
           - 验证归档元数据脱敏机制，严禁将包含 API 密钥的 URL 或参数写入元数据文件。

        2. 正常函数业务边界与参数契约:
           - 归档元数据中完全剥离敏感词 'SECRET'。

        3. 测试数据与模拟场景说明:
           - URL 包含 apikey=SECRET&symbol=A。

        4. 预期断言与结果验证:
           - 'SECRET' 不在 json.dumps(metadata) 中。
        """
        http = HTTP(self.archive, self.sources, Session([Response({"value": 1}, url="https://example.com/data?apikey=SECRET&symbol=A")]))
        _, metadata = http.fetch("test", "https://example.com/data", params={"apikey": "SECRET", "symbol": "A"})
        self.assertNotIn("SECRET", json.dumps(metadata))

    def test_modified_cache_fails(self):
        """【UT-INGEST-03: 篡改缓存文件完整性检验失败抛出(IngestionError)】

        1. 测试功能与测试点:
           - 验证缓存文件完整性校验机制。
           - 磁盘缓存内容被恶意修改后，哈希对不上，系统主动抛出 IngestionError。

        2. 正常函数业务边界与参数契约:
           - 缓存命中前必须通过 SHA-256 校验。

        3. 测试数据与模拟场景说明:
           - 篡改缓存内容为 b'corrupt'。

        4. 预期断言与结果验证:
           - 抛出 IngestionError 异常。
        """
        http = HTTP(self.archive, self.sources, Session([Response({"value": 1})]))
        _, metadata = http.fetch("test", "https://example.com/data")
        project_path(metadata["source_path"]).write_bytes(b"corrupt")
        with self.assertRaises(IngestionError):
            http.fetch("test", "https://example.com/data")

    def test_quota_persists(self):
        """【UT-INGEST-04: 配额预算持久化与超限拦截(quota_exhausted)】

        1. 测试功能与测试点:
           - 验证归档预算管理器的日配额持久化扣减与超额阻断机制。

        2. 正常函数业务边界与参数契约:
           - 配额耗尽抛出 status == 'quota_exhausted'。

        3. 测试数据与模拟场景说明:
           - 预留 0 秒内限制 1 次，连续调用 2 次。

        4. 预期断言与结果验证:
           - 抛出 IngestionError 且 status == 'quota_exhausted'。
        """
        self.archive.reserve("limited", 0, 1)
        with self.assertRaises(IngestionError) as caught:
            self.archive.reserve("limited", 0, 1)
        self.assertEqual(caught.exception.status, "quota_exhausted")

    def test_rate_limit_retry(self):
        """【UT-INGEST-05: 429限流重试机制与预算扣减对账】

        1. 测试功能与测试点:
           - 验证上游返回 429 且带 Retry-After: 0 时，客户端自动重试成功。

        2. 正常函数业务边界与参数契约:
           - 扣减两次预算，最终成功返回数据。

        3. 测试数据与模拟场景说明:
           - 第一次 429，第二次 200 {"ok": 1}。

        4. 预期断言与结果验证:
           - session.calls == 2。
           - budget used == 2。
        """
        session = Session([Response({}, 429, headers={"Retry-After": "0"}), Response({"ok": 1})])
        HTTP(self.archive, self.sources, session).fetch("test", "https://example.com/data")
        self.assertEqual(session.calls, 2)
        self.assertEqual(self.archive.db.execute("SELECT used FROM budget").fetchone()[0], 2)

    def test_long_retry_returns_control(self):
        """【UT-INGEST-06: 长周期重试交出控制权阻断(rate_limited)】

        1. 测试功能与测试点:
           - 验证当上游 429 要求长等待 (Retry-After: 120s) 时，客户端不假死等待，立即交出控制权。

        2. 正常函数业务边界与参数契约:
           - 抛出 IngestionError 并标注 status == 'rate_limited'。

        3. 测试数据与模拟场景说明:
           - 上游返回 Retry-After: 120。

        4. 预期断言与结果验证:
           - caught.exception.status == 'rate_limited'。
        """
        session = Session([Response({}, 429, headers={"Retry-After": "120"})])
        with self.assertRaises(IngestionError) as caught:
            HTTP(self.archive, self.sources, session).fetch("test", "https://example.com/data")
        self.assertEqual(caught.exception.status, "rate_limited")

    def test_redirect_whitelist(self):
        """【UT-INGEST-07: 重定向白名单安全防御-拦截恶意外链】

        1. 测试功能与测试点:
           - 验证 HTTP 302 重定向安全白名单。
           - 拦截跳转至未授权外部域名 (如 https://evil.invalid) 的攻击。

        2. 正常函数业务边界与参数契约:
           - 非法跳转抛出 IngestionError。

        3. 测试数据与模拟场景说明:
           - 302 Location: https://evil.invalid。

        4. 预期断言与结果验证:
           - 抛出 IngestionError。
        """
        session = Session([Response({}, 302, headers={"Location": "https://evil.invalid"})])
        with self.assertRaises(IngestionError):
            HTTP(self.archive, self.sources, session).fetch("test", "https://example.com/data")

    def test_secret_redirect_rejected(self):
        """【UT-INGEST-08: 携带敏感密钥重定向刚性拒绝】

        1. 测试功能与测试点:
           - 验证携带 API Key 的请求在遇到 302 重定向时，坚决拒绝继续跳传，防止密钥泄漏。

        2. 正常函数业务边界与参数契约:
           - params 包含敏感密钥时遇到重定向抛出异常。

        3. 测试数据与模拟场景说明:
           - 携带 apikey=SECRET 发生 302 跳转。

        4. 预期断言与结果验证:
           - 抛出 IngestionError。
        """
        session = Session([Response({}, 302, headers={"Location": "https://example.com/elsewhere"})])
        with self.assertRaises(IngestionError):
            HTTP(self.archive, self.sources, session).fetch("test", "https://example.com/data", params={"apikey": "SECRET"})

    def test_path_and_url_boundaries(self):
        """【UT-INGEST-09: 本地路径与公开URL安全边界强校验】

        1. 测试功能与测试点:
           - 验证 project_path 对上级目录跳出、跨盘绝对路径、网络共享路径的拦截。
           - 验证 public_url 对非 HTTPS、含认证信息凭据、回环地址及未授权域名的拦截。

        2. 正常函数业务边界与参数契约:
           - 路径违规抛出 ValueError，URL 违规抛出 IngestionError。

        3. 测试数据与模拟场景说明:
           - 非法路径: '../escape', 'C:/escape', '//server/file'。
           - 非法 URL: 'http://', 'https://user:pass@', 'https://127.0.0.1'。

        4. 预期断言与结果验证:
           - 所有非法用例全部抛出对应异常。
        """
        for value in ("../escape", "C:/escape", "//server/file", "data/../../escape"):
            with self.assertRaises(ValueError):
                project_path(value)
        for value in ("http://example.com", "https://user:pass@example.com", "https://127.0.0.1", "https://evil.invalid"):
            with self.assertRaises(IngestionError):
                public_url(value, ["example.com"])

    def test_api_error_not_data(self):
        """【UT-INGEST-10: 上游API错误载荷拦截-严禁作为正常数据录入】

        1. 测试功能与测试点:
           - 验证 json_response 对带有 'Information', 'Note', 'Error Message', 'error' 错误载荷的识别。
           - 严禁将配额超限提示误认作正常金融数据录入。

        2. 正常函数业务边界与参数契约:
           - 包含错误键的 JSON 字典抛出 IngestionError。

        3. 测试数据与模拟场景说明:
           - 遍历 4 类典型 API 错误载荷。

        4. 预期断言与结果验证:
           - 全部抛出 IngestionError。
        """
        for payload in ({"Information": "limit"}, {"Note": "limit"}, {"Error Message": "bad"}, {"error": "bad"}):
            with self.assertRaises(IngestionError):
                json_response(encode(payload))

    def test_sec_link_history_and_amendment(self):
        """【IT-INGEST-11: SEC EDGAR官方历史文件与更正案(10-K/A)解析】

        1. 测试功能与测试点:
           - 验证 Providers.source_sec 解析 SEC EDGAR 申报历史。
           - 正确提取 10-K/A 更正案的主文档 URL 链接。

        2. 正常函数业务边界与参数契约:
           - 需要配置 SEC_USER_AGENT 环境变量。

        3. 测试数据与模拟场景说明:
           - CIK 896878，申报更正案 10-K/A。

        4. 预期断言与结果验证:
           - calls 长度为 2。
           - primary_document_url 符合 EDGAR 归档规范。
           - 表单类型为 '10-K/A'。
        """
        recent = {"accessionNumber": ["0000896878-26-000001"], "form": ["10-K/A"], "primaryDocument": ["intu.htm"], "acceptanceDateTime": ["2026-01-01T15:00:00Z"]}
        fake = FakeHTTP([{"cik": "0000896878", "filings": {"recent": recent, "files": [{"name": "CIK0000896878-submissions-001.json"}]}}, recent])
        with patch.dict("os.environ", {"SEC_USER_AGENT": "test contact@example.com"}):
            rows, _ = Providers(fake).source_sec("submissions", {"cik": "896878", "history": True})
        self.assertEqual(len(fake.calls), 2)
        self.assertEqual(rows[0]["primary_document_url"], "https://www.sec.gov/Archives/edgar/data/896878/000089687826000001/intu.htm")
        self.assertEqual(rows[0]["form"], "10-K/A")

    def test_edinet_bad_zip_fails(self):
        """【UT-INGEST-12: EDINET破损ZIP文件异常阻断】

        1. 测试功能与测试点:
           - 验证 source_edinet 在下载到非标准 ZIP 字节流（如错误 JSON）时抛出 IngestionError。

        2. 正常函数业务边界与参数契约:
           - 解压失败抛出 IngestionError。

        3. 测试数据与模拟场景说明:
           - 返回错误 JSON 字节流。

        4. 预期断言与结果验证:
           - 抛出 IngestionError。
        """
        with patch.dict("os.environ", {"EDINET_API_KEY": "fixture"}):
            with self.assertRaises(IngestionError):
                Providers(FakeHTTP([b"{\"error\":true}"])).source_edinet("document", {"doc_id": "S1234567"})

    def test_jquants_pagination(self):
        """【UT-INGEST-13: J-Quants官方API游标分页抓取流转】

        1. 测试功能与测试点:
           - 验证 J-Quants 接口的分页逻辑，正确根据 pagination_key 推进多页抓取。

        2. 正常函数业务边界与参数契约:
           - 自动迭代直至无游标。

        3. 测试数据与模拟场景说明:
           - 第 1 页带 pagination_key='a'，第 2 页为尾页。

        4. 预期断言与结果验证:
           - 收集行数为 2。
           - 第 2 次请求携带 pagination_key='a'。
        """
        fake = FakeHTTP([{"data": [{"Code": "72030"}], "pagination_key": "a"}, {"data": [{"Code": "99840"}]}])
        with patch.dict("os.environ", {"JQUANTS_API_KEY": "fixture"}):
            rows, _ = Providers(fake).source_jquants("master", {})
        self.assertEqual(len(rows), 2)
        self.assertEqual(fake.calls[1][2]["params"]["pagination_key"], "a")

    def test_jquants_repeating_page_fails(self):
        """【UT-INGEST-14: J-Quants重复分页游标死循环防御】

        1. 测试功能与测试点:
           - 验证当上游接口返回重复不变的 pagination_key 时，主动中断死循环并抛出 IngestionError。

        2. 正常函数业务边界与参数契约:
           - 检测到重复游标立即拦截。

        3. 测试数据与模拟场景说明:
           - 连续两页返回相同的 pagination_key='a'。

        4. 预期断言与结果验证:
           - 抛出 IngestionError。
        """
        fake = FakeHTTP([{"data": [], "pagination_key": "a"}, {"data": [], "pagination_key": "a"}])
        with patch.dict("os.environ", {"JQUANTS_API_KEY": "fixture"}):
            with self.assertRaises(IngestionError):
                Providers(fake).source_jquants("master", {})

    def test_fred_requires_vintage(self):
        """【UT-INGEST-15: FRED宏观数据强制要求Vintage版本回溯】

        1. 测试功能与测试点:
           - 验证 FRED 宏观经济指标请求必须包含版本发布期 (vintage)，杜绝未来数据后视偏差。

        2. 正常函数业务边界与参数契约:
           - 缺少 vintage 参数抛出 IngestionError。

        3. 测试数据与模拟场景说明:
           - 仅传入 series_id="GDP"。

        4. 预期断言与结果验证:
           - 抛出 IngestionError。
        """
        with patch.dict("os.environ", {"FRED_API_KEY": "fixture"}):
            with self.assertRaises(IngestionError):
                Providers(FakeHTTP([])).source_fred("observations", {"series_id": "GDP"})

    def test_missing_key_explicit(self):
        """【UT-INGEST-16: 环境变量密钥缺失显式提示(needs_configuration)】

        1. 测试功能与测试点:
           - 验证当未配置对应环境变量密钥时，抛出明确的 needs_configuration 错误提示。

        2. 正常函数业务边界与参数契约:
           - caught.exception.status == 'needs_configuration'。

        3. 测试数据与模拟场景说明:
           - 清空环境变量调用 EDINET 接口。

        4. 预期断言与结果验证:
           - status == 'needs_configuration'。
        """
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(IngestionError) as caught:
                Providers(FakeHTTP([])).source_edinet("documents", {"date": "2026-01-01"})
        self.assertEqual(caught.exception.status, "needs_configuration")

    def test_partial_bls_not_success(self):
        """【UT-INGEST-17: BLS残缺数据序列严禁标记为成功】

        1. 测试功能与测试点:
           - 验证劳工统计局 (BLS) 返回空序列或残缺数据时，拒绝当做成功并抛出异常。

        2. 正常函数业务边界与参数契约:
           - data 列表为空判定为失败。

        3. 测试数据与模拟场景说明:
           - 返回空数据序列。

        4. 预期断言与结果验证:
           - 抛出 IngestionError。
        """
        fake = FakeHTTP([{"status": "REQUEST_SUCCEEDED", "Results": {"series": [{"seriesID": "X", "data": []}]}}])
        with self.assertRaises(IngestionError):
            Providers(fake).source_bls("series", {"series_ids": ["X"], "start_year": 2024, "end_year": 2025})

    def test_offline_does_not_fetch(self):
        """【UT-INGEST-18: 纯离线模式零网络请求与脱机未命中标记(offline_miss)】

        1. 测试功能与测试点:
           - 验证在 offline=True 时，流水线绝对不发生网络请求，未命中缓存直接标记为 offline_miss。

        2. 正常函数业务边界与参数契约:
           - offline=True 零外部 I/O。

        3. 测试数据与模拟场景说明:
           - 执行离线抓取计划。

        4. 预期断言与结果验证:
           - 任务状态为 'offline_miss'。
        """
        plan = {"schema_version": "1.0.0", "jobs": [{"id": "x", "provider": "test", "dataset": "unused"}]}
        result = run_plan(plan, self.archive, self.sources, offline=True)
        self.assertEqual(result[0]["status"], "offline_miss")

    def test_resume_and_integrity(self):
        """【IT-INGEST-19: 计划断点续传与防篡改物理自检闭环】

        1. 测试功能与测试点:
           - 验证 run_plan 的断点续传跳过已完成任务。
           - 验证当已完成结果被篡改时，离线校验主动发现异常并抛出 IngestionError。

        2. 正常函数业务边界与参数契约:
           - 篡改哈希不匹配刚性拦截。

        3. 测试数据与模拟场景说明:
           - 首次完成写入，二次执行断点续传；随后修改落盘文件为 b'tampered'。

        4. 预期断言与结果验证:
           - 二次执行 resumed 为 True。
           - 文件篡改后抛出 IngestionError。
        """
        plan = {"schema_version": "1.0.0", "jobs": [{"id": "x", "provider": "test", "dataset": "unused"}]}
        with patch.object(Providers, "execute", return_value={"status": "collected", "records": [{"v": 1}], "artifacts": []}):
            first = run_plan(plan, self.archive, self.sources)
        with patch.object(Providers, "execute", side_effect=AssertionError("must resume")):
            second = run_plan(plan, self.archive, self.sources)
        self.assertTrue(second[0]["resumed"])
        project_path(first[0]["result_path"]).write_bytes(b"tampered")
        with self.assertRaises(IngestionError):
            run_plan(plan, self.archive, self.sources, offline=True)

    def test_plan_duplicate_rejected_before_fetch(self):
        """【UT-INGEST-20: 计划任务重复项前置拦截(ValueError)】

        1. 测试功能与测试点:
           - 验证计划中存在重复任务 ID 时，在网络请求发生前直接在校验阶段抛出 ValueError。

        2. 正常函数业务边界与参数契约:
           - 任务 ID 唯一性公理。

        3. 测试数据与模拟场景说明:
           - 计划包含两个相同 id='x' 的任务。

        4. 预期断言与结果验证:
           - 抛出 ValueError。
        """
        job = {"id": "x", "provider": "test", "dataset": "unused"}
        with self.assertRaises(ValueError):
            run_plan({"schema_version": "1.0.0", "jobs": [job, job]}, self.archive, self.sources)

    def test_ir_wrong_document_type_fails(self):
        """【UT-INGEST-21: 发行人IR非研报类型文件(HTML冒充PDF)拦截】

        1. 测试功能与测试点:
           - 验证 issuer_ir 抓取要求下载真实 PDF，拦截返回 HTML 错误页的情况。

        2. 正常函数业务边界与参数契约:
           - 返回内容非 PDF 格式抛出 IngestionError。

        3. 测试数据与模拟场景说明:
           - 响应为 b'<html>not a report</html>'。

        4. 预期断言与结果验证:
           - 抛出 IngestionError。
        """
        with self.assertRaises(IngestionError):
            Providers(FakeHTTP([b"<html>not a report</html>"])).source_issuer_ir("document", {"url": "https://issuer.example/report.pdf"})

    def test_boj_daily_request_uses_month(self):
        """【UT-INGEST-22: 日本央行(BOJ)数据粒度合规性校验】

        1. 测试功能与测试点:
           - 验证日本央行月度时间序列参数格式校验。

        2. 正常函数业务边界与参数契约:
           - 参数不合规抛出 IngestionError。

        3. 测试数据与模拟场景说明:
           - 传入日级 startDate。

        4. 预期断言与结果验证:
           - 抛出 IngestionError。
        """
        with self.assertRaises(IngestionError):
            Providers(FakeHTTP([])).source_boj("series", {"db": "fm08", "code": "FXERD01", "startDate": "20261001"})

    def test_rss_official_classification(self):
        """【UT-INGEST-23: 官方权威RSS订阅源分类映射】

        1. 测试功能与测试点:
           - 验证从官方 RSS 源抓取的数据被正确分类为 primary 一级来源。

        2. 正常函数业务边界与参数契约:
           - authority='official' 映射 source_kind='primary'。

        3. 测试数据与模拟场景说明:
           - 官方 RSS Feed 抓取。

        4. 预期断言与结果验证:
           - result['status'] == 'collected'。
           - source_kind == 'primary'。
        """
        fake = FakeHTTP([b"<rss><channel><item><title>Policy</title><link>https://example.com/policy</link></item></channel></rss>"])
        fake.sources = {"rss": {"feeds": [{"url": "https://example.com/feed", "authority": "official"}]}}
        result = Providers(fake).execute({"provider": "rss", "dataset": "feed", "params": {"url": "https://example.com/feed"}})
        self.assertEqual(result["status"], "collected")
        self.assertEqual(fake.calls[0][2]["classification"]["source_kind"], "primary")

    def test_sec_ticker_dataset_classification(self):
        """【UT-INGEST-24: SEC代码数据集分类映射】

        1. 测试功能与测试点:
           - 验证 SEC 官方 company_tickers 数据集被正确分类为 classification 分类账。

        2. 正常函数业务边界与参数契约:
           - dataset_kind == 'classification'。

        3. 测试数据与模拟场景说明:
           - 获取 SEC tickers 列表。

        4. 预期断言与结果验证:
           - dataset_kind 精确为 'classification'。
        """
        fake = FakeHTTP([{"0": {"cik_str": 1, "ticker": "A"}}])
        with patch.dict("os.environ", {"SEC_USER_AGENT": "test contact@example.com"}):
            Providers(fake).execute({"provider": "sec", "dataset": "tickers", "params": {}})
        self.assertEqual(fake.calls[0][2]["classification"]["dataset_kind"], "classification")

    def test_disabled_source_no_request_even_when_key_exists(self):
        """【UT-INGEST-25: 停用数据源即使配置密钥也严禁请求(browser_required)】

        1. 测试功能与测试点:
           - 验证当来源在策略中被禁用时，即便环境中存在密钥，也绝对不发网络请求。
           - 自动转入 browser_required。

        2. 正常函数业务边界与参数契约:
           - session.calls 严格为 0。

        3. 测试数据与模拟场景说明:
           - 模拟已配置 EXISTING_SECRET 但来源禁用。

        4. 预期断言与结果验证:
           - caught.exception.status == 'browser_required'。
           - session.calls == 0。
        """
        self.sources["test"]["env"] = "EXISTING_SECRET"
        session = Session([])
        with patch.dict("os.environ", {"EXISTING_SECRET": "must-not-use"}):
            with self.assertRaises(IngestionError) as caught:
                HTTP(self.archive, self.sources, session).fetch("test", "https://example.com/data")
        self.assertEqual(caught.exception.status, "browser_required")
        self.assertEqual(session.calls, 0)

    def test_disabled_plan_generates_browser_request(self):
        """【IT-INGEST-26: 停用数据源计划自动转为AI浏览器取数清单】

        1. 测试功能与测试点:
           - 验证执行包含已停用数据源的任务计划时，自动生成 browser_required 补数需求。

        2. 正常函数业务边界与参数契约:
           - 拒绝直接抛出非捕获异常。

        3. 测试数据与模拟场景说明:
           - 来源 enabled=False。

        4. 预期断言与结果验证:
           - result[0]['status'] == 'browser_required'。
        """
        self.sources["test"]["enabled"] = False
        plan = {"schema_version": "1.0.0", "jobs": [{"id": "x", "provider": "test", "dataset": "unused", "params": {"cik": "896878"}}]}
        with patch.object(Providers, "execute", side_effect=AssertionError("disabled source")):
            result = run_plan(plan, self.archive, self.sources)
        self.assertEqual(result[0]["status"], "browser_required")

    def test_browser_pdf_archived_with_unknown_exact_time(self):
        """【IT-INGEST-27: 浏览器下载PDF凭据归档与时间精度记录】

        1. 测试功能与测试点:
           - 验证 import_document 导入浏览器下载的 PDF 凭据与元数据收据。
           - 记录发布时间精度 publication_precision='date'，精确时分秒未知。

        2. 正常函数业务边界与参数契约:
           - PDF 凭据必须物理存在。

        3. 测试数据与模拟场景说明:
           - 模拟下载 Intuit (INTU) 投资者关系 PDF。

        4. 预期断言与结果验证:
           - result['status'] == 'archived'。
           - published_at 为 None。
        """
        path = Path(self.temp.name) / "browser.pdf"
        path.write_bytes(b"%PDF-1.4 fixture")
        receipt = {"id": "fixture", "entity_id": "US:INTU", "search_url": "https://www.google.com/search?q=fixture",
                   "page_url": "https://investors.intuit.com/financial-information", "document_url": "https://investors.intuit.com/fixture.pdf",
                   "format": "pdf", "published_date": "2026-01-01", "publication_precision": "date", "verification_notes": "synthetic fixture, not real financial evidence"}
        result = import_document(path, receipt, self.archive)
        self.assertEqual(result["status"], "archived")
        data = json.loads(project_path(result["receipt_path"]).read_bytes())
        self.assertIsNone(data["artifact"]["published_at"])
        # 导入输出在固定本地 receipt 目录，删除本测试自己生成的唯一文件。
        project_path(result["receipt_path"]).unlink()

    def test_browser_unapproved_origin_rejected(self):
        """【UT-INGEST-28: 浏览器未经授权恶意域名凭据物理拦截】

        1. 测试功能与测试点:
           - 验证 import_document 针对未授权下载来源 (如 evil.invalid) 的安全阻断。

        2. 正常函数业务边界与参数契约:
           - 未在白名单的来源抛出 IngestionError。

        3. 测试数据与模拟场景说明:
           - page_url 和 document_url 均为 evil.invalid。

        4. 预期断言与结果验证:
           - 抛出 IngestionError。
        """
        receipt = {"id": "fixture", "entity_id": "US:INTU", "search_url": "https://www.google.com/search?q=fixture",
                   "page_url": "https://evil.invalid/", "document_url": "https://evil.invalid/file.pdf", "format": "pdf",
                   "published_date": None, "publication_precision": "unknown", "verification_notes": "fixture"}
        with self.assertRaises(IngestionError):
            import_document("no-such-file", receipt, self.archive)


if __name__ == "__main__":
    unittest.main()
