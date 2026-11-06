"""免费来源适配。官方 API 只转换请求，不擅自推断财务业务口径。"""
from datetime import date
import csv
import io
import re
from html.parser import HTMLParser
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

from .core import IngestionError, encode, json_response, require_env, utcnow


def token(value, pattern, label):
    value = str(value)
    if not re.fullmatch(pattern, value):
        raise IngestionError("invalid_request", f"{label} 格式错误")
    return value


def iso_date(value):
    try:
        return date.fromisoformat(value).isoformat()
    except (ValueError, TypeError):
        raise IngestionError("invalid_request", "日期须为 YYYY-MM-DD") from None


class Links(HTMLParser):
    """提取 TDnet 公共索引链接；原文保留，页面改变时显式失败。"""
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href:
                self.links.append(href)


class Providers:
    def __init__(self, http):
        self.http = http
        self.artifacts = []
        self.dataset = None

    def get(self, provider, url, **kwargs):
        classification = {}
        mapping = {("sec", "tickers"): "classification", ("sec", "submissions"): "company_action",
                   ("alpha_vantage", "daily"): "market", ("alpha_vantage", "news"): "news",
                   ("jquants", "master"): "classification", ("jquants", "summary"): "financial"}
        if (provider, self.dataset) in mapping:
            classification["dataset_kind"] = mapping[provider, self.dataset]
        if provider == "rss":
            config = self.http.sources.get("rss", {})
            feed = next((x for x in config.get("feeds", []) if x["url"] == url), {})
            classification["source_kind"] = "primary" if feed.get("authority") in ("official", "issuer") else "secondary"
        if classification:
            kwargs["classification"] = classification
        content, metadata = self.http.fetch(provider, url, **kwargs)
        self.artifacts.append(metadata)
        return content

    def get_json(self, provider, url, **kwargs):
        return json_response(self.get(provider, url, **kwargs))

    def execute(self, job):
        self.artifacts = []
        provider, dataset = job["provider"], job["dataset"]
        self.dataset = dataset
        config = self.http.sources.get(provider, {})
        if config.get("enabled") is False or config.get("env"):
            raise IngestionError("browser_required", "需要配置的接口不采用，转 AI 浏览器搜索官方资料")
        args = job.get("params", {})
        method = getattr(self, f"source_{provider}", None)
        if method is None:
            raise IngestionError("unsupported", "来源仅列入调查，尚未实现适配器")
        records, notes = method(dataset, args)
        return {"status": "collected" if records else "no_data", "records": records,
                "artifacts": self.artifacts, "quality_notes": notes}

    def source_sec(self, dataset, args):
        headers = {"User-Agent": require_env("SEC_USER_AGENT"), "Accept-Encoding": "gzip, deflate"}
        if dataset == "tickers":
            data = self.get_json("sec", "https://www.sec.gov/files/company_tickers.json", headers=headers)
            return list(data.values()), ["股票代码映射须结合交易所、CIK 和历史更名核对"]
        cik = token(args.get("cik", ""), r"\d{1,10}", "CIK").zfill(10)
        if dataset == "companyfacts":
            data = self.get_json("sec", f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", headers=headers)
            if data.get("cik") != int(cik) or not isinstance(data.get("facts"), dict):
                raise IngestionError("invalid_response", "SEC companyfacts 公司或结构不匹配")
            return [data], ["保留 taxonomy/tag/units/start/end/filed/accn/form/frame 原字段；标准合并事实不含所有自定义标签和分部指标", "filed 仅日期，不能当成精确可得时刻；需匹配提交 acceptanceDateTime", "聚合事实可能包含后续修订，历史研究需逐项筛选"]
        if dataset == "filing":
            accession = token(args.get("accession", ""), r"\d{10}-\d{2}-\d{6}", "申报号")
            document = token(args.get("document", ""), r"[A-Za-z0-9_.-]+", "申报文件名")
            if document in (".", ".."):
                raise IngestionError("invalid_request", "文件名错误")
            url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{document}"
            self.get("sec", url, headers=headers, ttl=365 * 86400)
            return [{"cik": cik, "accession": accession, "document": document}], ["正文归档完成；附件须从实际申报索引另行选择；未自动生成财务事实"]
        if dataset != "submissions":
            raise IngestionError("unsupported", "SEC 支持 tickers/submissions/companyfacts/filing")
        data = self.get_json("sec", f"https://data.sec.gov/submissions/CIK{cik}.json", headers=headers)
        if str(data.get("cik", "")).zfill(10) != cik:
            raise IngestionError("invalid_response", "SEC submissions 公司不匹配")
        blocks = [data.get("filings", {}).get("recent", {})]
        # 默认仅近年；请求 history 时逐页归档，可利用缓存从已下载页恢复。
        if args.get("history", False):
            for info in data.get("filings", {}).get("files", []):
                name = token(info["name"], r"CIK\d{10}-submissions-\d+\.json", "历史分页文件")
                blocks.append(self.get_json("sec", f"https://data.sec.gov/submissions/{name}", headers=headers, ttl=86400))
        forms = set(args.get("forms", ["10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A", "20-F", "20-F/A", "40-F", "6-K", "6-K/A"]))
        rows = []
        for block in blocks:
            if not isinstance(block, dict) or not isinstance(block.get("accessionNumber"), list):
                raise IngestionError("invalid_response", "SEC 提交数组缺失")
            length = len(block["accessionNumber"])
            if any(len(v) != length for v in block.values() if isinstance(v, list)):
                raise IngestionError("invalid_response", "SEC 列数组长度不一致")
            for index in range(length):
                row = {k: v[index] for k, v in block.items() if isinstance(v, list)}
                if row.get("form") not in forms:
                    continue
                document = row.get("primaryDocument", "")
                accession = row["accessionNumber"]
                token(document, r"[A-Za-z0-9_.-]+", "主文件名")
                token(accession, r"\d{10}-\d{2}-\d{6}", "申报号")
                row["primary_document_url"] = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{document}"
                rows.append(row)
        return rows, ["申报清单与正文分别取数；更正和原版均保留", "保留 acceptanceDateTime 原值，不以 filingDate 零点替代"]

    def source_edinet(self, dataset, args):
        params = {"Subscription-Key": require_env("EDINET_API_KEY")}
        if dataset == "documents":
            params.update(date=iso_date(args["date"]), type=2)
            data = self.get_json("edinet", "https://api.edinet-fsa.go.jp/api/v2/documents.json", params=params)
            if str(data.get("metadata", {}).get("status")) != "200" or not isinstance(data.get("results"), list):
                raise IngestionError("provider_error", "EDINET 状态或清单结构异常")
            rows = data["results"]
            if args.get("sec_code"):
                code = token(args["sec_code"], r"[0-9A-Z]{4,5}", "EDINET 证券代码")
                rows = [x for x in rows if x.get("secCode") == code]
            return rows, ["secCode 与交易所代码不同，须维护 EDINET code/证券代码/公司映射", "submitDateTime 为日本本地时间；撤回、修订状态必须保留"]
        if dataset == "document":
            doc_id = token(args.get("doc_id", ""), r"S[0-9A-Z]{7}", "EDINET 文件编号")
            kind = args.get("type", 1)
            if type(kind) is not int or kind not in (1, 2, 5):
                raise IngestionError("invalid_request", "type 仅支持 1 原文 ZIP、2 PDF、5 XBRL 转换 CSV ZIP")
            params["type"] = kind
            raw = self.get("edinet", f"https://api.edinet-fsa.go.jp/api/v2/documents/{doc_id}", params=params, ttl=365 * 86400)
            if not raw.startswith(b"%PDF" if kind == 2 else b"PK"):
                raise IngestionError("invalid_response", "返回内容不是预期 PDF/ZIP；未视为财报下载成功")
            return [{"doc_id": doc_id, "type": kind}], ["仅归档原始文件；未自动解压或完成 JGAAP/IFRS 口径映射"]
        raise IngestionError("unsupported", "EDINET 支持 documents/document")

    def source_jquants(self, dataset, args):
        routes = {"master": "/equities/master", "daily": "/equities/bars/daily", "summary": "/fins/summary"}
        if dataset not in routes:
            raise IngestionError("unsupported", "仅支持免费方案候选端点 master/daily/summary；不调用付费明细")
        headers = {"x-api-key": require_env("JQUANTS_API_KEY")}
        params = {k: v for k, v in args.items() if k in ("code", "date", "from", "to")}
        for key in ("date", "from", "to"):
            if key in params:
                iso_date(params[key])
        if "code" in params:
            token(params["code"], r"[0-9A-Z]{4,5}", "日股代码")
        rows, seen = [], set()
        for _ in range(100):
            data = self.get_json("jquants", "https://api.jquants.com/v2" + routes[dataset], params=params, headers=headers)
            if not isinstance(data.get("data"), list):
                raise IngestionError("invalid_response", "J-Quants data 数组缺失")
            rows.extend(data["data"])
            page = data.get("pagination_key")
            if not page:
                return rows, ["免费方案按官方约束延迟 12 周，不用于当天行情", "保留 V2 原字段；财报摘要不等于完整三张财务报表", "摘要不作为项目已审核的原始财务事实"]
            if page in seen:
                raise IngestionError("invalid_response", "J-Quants 分页游标重复")
            seen.add(page)
            params["pagination_key"] = page
        raise IngestionError("partial", "分页超过本次 100 页上限，已取页保留")

    def source_alpha_vantage(self, dataset, args):
        functions = {"daily": "TIME_SERIES_DAILY", "income": "INCOME_STATEMENT", "balance": "BALANCE_SHEET", "cashflow": "CASH_FLOW", "overview": "OVERVIEW", "earnings": "EARNINGS", "news": "NEWS_SENTIMENT"}
        if dataset not in functions:
            raise IngestionError("unsupported", "未启用该端点；不尝试付费行情端点")
        symbol = token(args.get("symbol", ""), r"[A-Za-z0-9.^_-]{1,30}", "股票代码")
        params = {"function": functions[dataset], "apikey": require_env("ALPHA_VANTAGE_API_KEY")}
        params["tickers" if dataset == "news" else "symbol"] = symbol
        if dataset == "daily":
            params["outputsize"] = "compact"
        data = self.get_json("alpha_vantage", "https://www.alphavantage.co/query", params=params)
        expected = {"daily": "Time Series (Daily)", "income": "annualReports", "balance": "annualReports", "cashflow": "annualReports", "overview": "Symbol", "earnings": "annualEarnings", "news": "feed"}[dataset]
        if not data or expected not in data:
            raise IngestionError("invalid_response", "返回数据为空或缺少对应业务字段")
        return [data], ["每日总额度 25 次，缓存命中不发请求", "三表为供应商整理数据，不代替 SEC/EDINET 原文", "不保证每个端点、市场和字段均在免费计划内；权限拒绝明确返回"]

    def source_fred_csv(self, dataset, args):
        if dataset != "series":
            raise IngestionError("unsupported", "FRED CSV 仅支持 series")
        series = token(args.get("series_id", ""), r"[A-Za-z0-9_]+", "FRED 序列")
        raw = self.get("fred_csv", "https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": series})
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
        if not rows or series not in rows[0] or not any(k in rows[0] for k in ("DATE", "observation_date")):
            raise IngestionError("invalid_response", "FRED CSV 表头或记录异常")
        return rows, ["无需 Key，当前修订版本，不用于历史无前视回测", "缺失值 . 保留，不填零；频率和单位需从序列元数据核对"]

    def source_fred(self, dataset, args):
        if dataset not in ("observations", "metadata"):
            raise IngestionError("unsupported", "FRED 支持 observations/metadata")
        params = {"series_id": token(args.get("series_id", ""), r"[A-Za-z0-9_]+", "FRED 序列"), "api_key": require_env("FRED_API_KEY"), "file_type": "json"}
        for key in ("realtime_start", "realtime_end", "observation_start", "observation_end"):
            if key in args:
                params[key] = iso_date(args[key])
        if dataset == "observations" and not all(k in params for k in ("realtime_start", "realtime_end")):
            raise IngestionError("invalid_request", "历史观察需明确 realtime_start/realtime_end，禁止默认今天版本冒充历史版本")
        route = "series/observations" if dataset == "observations" else "series"
        data = self.get_json("fred", "https://api.stlouisfed.org/fred/" + route, params=params)
        key = "observations" if dataset == "observations" else "seriess"
        if not isinstance(data.get(key), list):
            raise IngestionError("invalid_response", "FRED 预期数组缺失")
        if dataset == "observations" and data.get("count", len(data[key])) > len(data[key]):
            raise IngestionError("partial", "FRED 超过单页限制，已保留原文；需缩小观察区间")
        return data[key], ["保留实时版本区间与观察期日期，发布时刻仍需另行核对"]

    def source_bls(self, dataset, args):
        if dataset != "series":
            raise IngestionError("unsupported", "BLS 仅支持 series")
        ids = args.get("series_ids", [])
        if not isinstance(ids, list) or not 1 <= len(ids) <= 25:
            raise IngestionError("invalid_request", "未注册免费请求每批 1—25 个序列")
        for series in ids:
            token(series, r"[A-Za-z0-9]+", "BLS 序列")
        start, end = int(args["start_year"]), int(args["end_year"])
        if not 1900 <= start <= end <= date.today().year or end - start > 9:
            raise IngestionError("invalid_request", "BLS 免费未注册每批最多 10 年")
        data = self.get_json("bls", "https://api.bls.gov/publicAPI/v1/timeseries/data/", json_body={"seriesid": ids, "startyear": str(start), "endyear": str(end)})
        if data.get("status") != "REQUEST_SUCCEEDED":
            raise IngestionError("provider_error", "BLS 返回失败状态")
        rows = data.get("Results", {}).get("series", [])
        if not rows or any(not row.get("data") for row in rows):
            raise IngestionError("partial", "BLS 一个或多个序列无数据")
        return rows, ["未经注册免费额度每天 25 次，统计修订版本不能当作历史已知值"]

    def source_boj(self, dataset, args):
        routes = {"metadata": "getMetadata", "series": "getDataCode"}
        if dataset not in routes:
            raise IngestionError("unsupported", "BOJ 支持 metadata/series")
        params = {"format": "json", "lang": "en", "db": token(args.get("db", ""), r"[A-Za-z0-9]+", "BOJ 数据库")}
        if dataset == "series":
            params["code"] = token(args.get("code", ""), r"[A-Za-z0-9_,]+", "BOJ 序列代码")
            for key in ("startDate", "endDate"):
                if key in args:
                    params[key] = token(args[key], r"\d{4}|\d{6}", "BOJ 期间（年或年月，日度序列也按年月查询）")
        data = self.get_json("boj", "https://www.stat-search.boj.or.jp/api/v1/" + routes[dataset], params=params)
        if isinstance(data, dict) and str(data.get("STATUS", "200")) not in ("200", "0"):
            raise IngestionError("provider_error", "BOJ 状态异常")
        if isinstance(data, dict) and data.get("NEXTPOSITION"):
            raise IngestionError("partial", "BOJ 结果需要分页，请缩小区间；原文已归档")
        return [data], ["按官方 2026 年 API 取数；当前版本，不自动作为历史可得值"]

    def source_estat(self, dataset, args):
        routes = {"search": "getStatsList", "metadata": "getMetaInfo", "data": "getStatsData"}
        if dataset not in routes:
            raise IngestionError("unsupported", "e-Stat 支持 search/metadata/data")
        params = {"appId": require_env("ESTAT_APP_ID"), "lang": "E"}
        if dataset == "search":
            params["searchWord"] = str(args.get("query", "consumer price"))
        else:
            params["statsDataId"] = token(args.get("table_id", ""), r"[A-Za-z0-9]+", "统计表 ID")
        params["limit"] = 10000
        data = self.get_json("estat", "https://api.e-stat.go.jp/rest/3.0/app/json/" + routes[dataset], params=params)
        root = data.get({"search": "GET_STATS_LIST", "metadata": "GET_META_INFO", "data": "GET_STATS_DATA"}[dataset], {})
        if str(root.get("RESULT", {}).get("STATUS")) != "0":
            raise IngestionError("provider_error", "e-Stat 返回非成功状态")
        if root.get("STATISTICAL_DATA", {}).get("RESULT_INF", {}).get("NEXT_KEY"):
            raise IngestionError("partial", "e-Stat 需分页，原始首批已归档；请按分类缩小请求")
        return [data], ["分类、单位、统计表基准变更必须保留；本适配器不自动合并不同基准统计表"]

    def source_gdelt(self, dataset, args):
        if dataset != "news":
            raise IngestionError("unsupported", "GDELT 仅支持 news")
        query = args.get("query", "")
        if not isinstance(query, str) or not 1 <= len(query) <= 300:
            raise IngestionError("invalid_request", "新闻查询需 1—300 字符")
        data = self.get_json("gdelt", "https://api.gdeltproject.org/api/v2/doc/doc", params={"query": query, "mode": "artlist", "format": "json", "timespan": "24h", "maxrecords": 100, "sort": "datedesc"})
        if not isinstance(data.get("articles"), list):
            raise IngestionError("invalid_response", "GDELT 新闻数组缺失")
        return data["articles"], ["新闻发现与标题索引，不代表已下载正文或核实事实；24 小时结果最多 100 条"]

    def source_rss(self, dataset, args):
        if dataset != "feed":
            raise IngestionError("unsupported", "RSS 仅支持 feed")
        url = args.get("url", "")
        approved = self.http.sources["rss"].get("feeds", [])
        if url not in [x["url"] for x in approved]:
            raise IngestionError("invalid_request", "RSS URL 必须先登记到 sources.json")
        raw = self.get("rss", url)
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            raise IngestionError("invalid_response", "返回内容不是 RSS/Atom XML") from None
        rows = []
        for item in root.iter():
            if item.tag.split("}")[-1] not in ("item", "entry"):
                continue
            row = {}
            for child in item:
                name = child.tag.split("}")[-1]
                if name in ("title", "link", "pubDate", "published", "updated", "guid", "id", "description", "summary"):
                    row[name] = child.get("href") if name == "link" and child.get("href") else "".join(child.itertext())
            if row.get("title"):
                rows.append(row)
        return rows, ["RSS 仅标题、链接及供应商给出的时间；正文、真实性和重复报道需后续核对", "公司官方稿件需按单篇来源确认，媒体 RSS 保持二手来源"]

    def source_tdnet(self, dataset, args):
        if dataset == "index":
            day = iso_date(args["date"]).replace("-", "")
            page = token(args.get("page", "001"), r"\d{3}", "TDnet 页码")
            url = f"https://www.release.tdnet.info/inbs/I_list_{page}_{day}.html"
            raw = self.get("tdnet", url)
            parser = Links()
            parser.feed(raw.decode("utf-8", errors="replace"))
            links = sorted({urljoin(url, x) for x in parser.links if re.search(r"\.(pdf|zip)(?:\?|$)", x, re.I)})
            if not links:
                raise IngestionError("no_documents_or_layout_changed", "索引未找到 PDF/ZIP；可能无公告或页面结构改变，原文已保存")
            return [{"document_url": x, "date": args["date"]} for x in links], ["免费网页仅近期 31 天；当前只处理指定页，不能声称全市场当日清单完整", "正文需 document 任务另行下载；收费 API 未启用"]
        if dataset == "document":
            raw = self.get("tdnet", args["url"], ttl=365 * 86400)
            if not raw.startswith((b"%PDF", b"PK")):
                raise IngestionError("invalid_response", "TDnet 文档不是 PDF/ZIP")
            return [{"document_url": args["url"]}], ["仅原文归档；需核对发行人、公告时刻、更正版本"]
        raise IngestionError("unsupported", "TDnet 支持 index/document")

    def source_issuer_ir(self, dataset, args):
        """免费公司原文补充：仅接受已登记发行人域名，不自动猜测网址。"""
        if dataset not in ("index", "document"):
            raise IngestionError("unsupported", "IR 支持 index/document")
        raw = self.get("issuer_ir", args["url"], ttl=86400 if dataset == "index" else 365 * 86400)
        if dataset == "index":
            parser = Links()
            parser.feed(raw.decode("utf-8", errors="replace"))
            links = sorted({urljoin(args["url"], x) for x in parser.links if re.search(r"\.(pdf|zip|xlsx|csv|htm|html)(?:\?|$)", x, re.I)})
            return [{"document_url": x} for x in links], ["索引可能由 JavaScript 生成，提取链接不等于完整历史清单；须按公司维护入口"]
        expected = args.get("format", "pdf")
        if expected == "pdf" and not raw.startswith(b"%PDF"):
            raise IngestionError("invalid_response", "公司文件不是预期 PDF")
        if expected == "html" and b"<html" not in raw[:10000].lower() and b"<!doctype html" not in raw[:10000].lower():
            raise IngestionError("invalid_response", "公司文件不是预期 HTML")
        if expected not in ("pdf", "html"):
            raise IngestionError("invalid_request", "format 仅支持 pdf/html")
        return [{"entity_id": args.get("entity_id"), "document_url": args["url"], "format": expected}], ["发行人官方原文；未自动审核发行人、报告期、会计准则及发布时间", "公司集团与上市子公司必须区分，不能以品牌名合并财报"]

    def source_yfinance(self, dataset, args):
        if dataset != "daily":
            raise IngestionError("unsupported", "yfinance 仅启用日线及拆股分红，不将二手财务数据作为原始事实")
        symbol = token(args.get("symbol", ""), r"[A-Za-z0-9.^=_-]{1,30}", "Yahoo 代码")
        start, end = iso_date(args["start"]), iso_date(args["end"])
        if start >= end:
            raise IngestionError("invalid_request", "起始日期须早于结束日期（结束日不含）")
        identity = encode(["yfinance", symbol, start, end])
        import hashlib
        request_id = hashlib.sha256(identity).hexdigest()
        config = self.http.sources["yfinance"]
        cached = self.http.archive.cached(request_id, config["ttl_seconds"])
        if cached:
            raw, metadata = cached
            self.artifacts.append(metadata)
            return json_response(raw), ["缓存日线；观察时间保持原归档时间"]
        self.http.archive.reserve("yfinance", config["interval_seconds"], config["daily_limit"])
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            frame = ticker.history(start=start, end=end, interval="1d", auto_adjust=False,
                                   back_adjust=False, actions=True, raise_errors=True)
            metadata = ticker.history_metadata
        except Exception:
            raise IngestionError("upstream_error", "yfinance 查询失败，未切换到付费源或填入假数据") from None
        if frame.empty:
            raise IngestionError("no_data", "yfinance 返回空行情")
        rows = json_response(frame.reset_index().to_json(orient="records", date_format="iso").encode())
        info = self.http.archive.save("yfinance", request_id, encode(rows),
            {"origin_url": f"https://finance.yahoo.com/quote/{symbol}/history/", "source_kind": "secondary",
             "dataset_kind": "market", "published_at": None, "quality_status": "unreviewed",
             "currency": metadata.get("currency"), "exchange_timezone": metadata.get("exchangeTimezoneName"),
             "symbol": symbol, "price_adjustment": "auto_adjust_false_vendor_OHLC_and_Adj_Close",
             "raw_transport": "yfinance_library_dataframe_snapshot"})
        self.artifacts.append(info)
        return rows, ["第三方个人研究用途，无官方稳定性承诺；不是交易所实时行情", "保留 OHLC、Adj Close、分红拆股；OHLC 是否已按拆股调整须按供应商定义核对，不能宣称原始成交价", "此处归档库返回表格，未声称保存 Yahoo HTTP 原文；交易日、币种及行情新鲜度需核验"]
