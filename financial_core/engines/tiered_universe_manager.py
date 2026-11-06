"""全盘数千家分级资产池管理器 (tiered_universe_manager.py).

严格遵循 2026-10-12 全盘全量数千家企业资产池规范与分级资产池架构：
1. 覆盖全量资产池规模：美股 SEC EDGAR 官方登记 10,000+ 家企业与东证全市场 Prime/Standard/Growth 4,400+ 家企业；
2. 四级资产池分层架构 (Tiered Universe Architecture)：
   - Tier 0（核心旗舰 / 顶层重仓池，P0）：顶层蓝筹巨头，高频动态事件、官方财报三表全息底稿与精细化两阶段 DCF 估值；
   - Tier 1（主线成长 / 细分中坚池，P1）：高流动性中大型成长股与各赛道胜负手，定期情景更新与买点监控；
   - Tier 2 / Tier 3（全市场数千家全量标的池，P2/P3）：全市场全息索引 (SEC CIK、东证代码、行业大类、官方三表底账)；
3. 支持高效分批切片调度 (Batch Chunking，如每批 50~100 家)、增量断点续传与本地二级来源归档状态实时统计。
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEC_TICKERS_PATH = ROOT / "data" / "universe" / "sec_company_tickers.json"
DEFAULT_JPX_TICKERS_PATH = ROOT / "data" / "universe" / "jpx_company_tickers.json"
DEFAULT_SP500_PATH = ROOT / "data" / "universe" / "sp500_universe.json"
DEFAULT_SEC_CACHE_DIR = ROOT / "data" / "official_filings" / "sec"


@dataclass
class UniverseCompanyRecord:
    """全盘资产池企业标准化索引记录."""
    ticker: str
    company_name: str
    market: str                      # "US" 或 "JP"
    tier: str                        # "TIER_0", "TIER_1", "TIER_2", "TIER_3"
    cik: str = ""                    # 美股 SEC CIK (10位补零字符串)
    jpx_code: str = ""               # 日股东证代码 (如 7203)
    sector: str = ""                 # 对应行业/板块
    industry: str = ""               # 细分行业
    has_local_filing: bool = False   # 本地是否已归档官方原始底账


@dataclass
class TieredUniverseStats:
    """全盘资产池分级统计概要."""
    total_companies: int
    us_sec_count: int
    jp_jpx_count: int
    tier_0_count: int
    tier_1_count: int
    tier_2_count: int
    tier_3_count: int
    sec_archived_count: int
    sec_archived_ratio_pct: float


class TieredUniverseManager:
    """全盘全量数千家资产池分级管理与分批调度引擎."""

    _INSTANCE: Optional["TieredUniverseManager"] = None

    # 官方披露重组/控股载体更迭修正映射 (优先指向真实经审计三表 10-K 报送主体)
    CIK_OVERRIDES: Dict[str, str] = {
        "XOM": "0000034088",  # Exxon Mobil Corporation 经审计经营主账户
        "SQ": "0001512673",   # Block, Inc. (XYZ)
        "FI": "0000798354",   # Fiserv, Inc. (FISV)
        "BRKB": "0001067983", # Berkshire Hathaway Inc (BRK-B)
        "BRK.B": "0001067983",
        "EA": "0000712515",   # Electronic Arts Inc.
    }

    def __init__(
        self,
        sec_path: Optional[Path] = None,
        jpx_path: Optional[Path] = None,
        sp500_path: Optional[Path] = None,
        sec_cache_dir: Optional[Path] = None,
    ):
        self.sec_path = sec_path or DEFAULT_SEC_TICKERS_PATH
        self.jpx_path = jpx_path or DEFAULT_JPX_TICKERS_PATH
        self.sp500_path = sp500_path or DEFAULT_SP500_PATH
        self.sec_cache_dir = sec_cache_dir or DEFAULT_SEC_CACHE_DIR

        self._us_companies: Dict[str, UniverseCompanyRecord] = {}
        self._jp_companies: Dict[str, UniverseCompanyRecord] = {}
        self._sp500_ciks: Set[str] = set()
        self._sp500_tickers: Set[str] = set()
        self._is_loaded = False

    @classmethod
    def get_instance(cls) -> "TieredUniverseManager":
        """获取单例管理实例."""
        if cls._INSTANCE is None:
            cls._INSTANCE = cls()
            cls._INSTANCE.load_universe()
        return cls._INSTANCE

    def load_universe(self, force_reload: bool = False) -> None:
        """加载全盘美股与日股资产池索引并完成分级标记."""
        if self._is_loaded and not force_reload:
            return

        self._us_companies.clear()
        self._jp_companies.clear()
        self._sp500_ciks.clear()
        self._sp500_tickers.clear()

        # 1. 扫描本地 SEC 官方底账归档目录
        cached_ciks: Set[str] = set()
        if self.sec_cache_dir.exists():
            for p in self.sec_cache_dir.glob("CIK*.json"):
                cik_part = p.stem.replace("CIK", "").strip().zfill(10)
                cached_ciks.add(cik_part)

        # 2. 加载 S&P 500 核心池定义 (划入 Tier 0 / Tier 1 候选)
        if self.sp500_path.exists():
            try:
                sp_data = json.loads(self.sp500_path.read_text(encoding="utf-8"))
                constituents = sp_data.get("constituents", [])
                for item in constituents:
                    sym = item.get("symbol", "").upper().strip()
                    c = str(item.get("cik", "")).strip().zfill(10)
                    if sym in self.CIK_OVERRIDES:
                        c = self.CIK_OVERRIDES[sym]
                    if sym:
                        self._sp500_tickers.add(sym)
                    if c:
                        self._sp500_ciks.add(c)
            except Exception:
                pass

        # 3. 加载全量美股 SEC 官方登记公司 (10,000+ 家)
        if self.sec_path.exists():
            try:
                sec_raw = json.loads(self.sec_path.read_text(encoding="utf-8"))
                items = sec_raw.values() if isinstance(sec_raw, dict) else sec_raw
                for entry in items:
                    t = str(entry.get("ticker", "")).upper().strip()
                    if not t:
                        continue
                    c_num = entry.get("cik_str", "")
                    c_str = str(c_num).strip().zfill(10)
                    if t in self.CIK_OVERRIDES:
                        c_str = self.CIK_OVERRIDES[t]
                    name = entry.get("title", t)

                    # 确定层级分级
                    is_sp500 = (t in self._sp500_tickers) or (c_str in self._sp500_ciks)
                    is_archived = c_str in cached_ciks

                    if is_sp500 and is_archived:
                        tier = "TIER_0"
                    elif is_sp500:
                        tier = "TIER_1"
                    elif is_archived:
                        tier = "TIER_2"
                    else:
                        tier = "TIER_3"

                    rec = UniverseCompanyRecord(
                        ticker=t,
                        company_name=name,
                        market="US",
                        tier=tier,
                        cik=c_str,
                        has_local_filing=is_archived,
                    )
                    self._us_companies[t] = rec

                # 补全别名与重组标的映射
                for ov_t, ov_cik in self.CIK_OVERRIDES.items():
                    if ov_t not in self._us_companies:
                        ov_cik_str = str(ov_cik).strip().zfill(10)
                        is_sp = (ov_t in self._sp500_tickers) or (ov_cik_str in self._sp500_ciks)
                        is_arc = ov_cik_str in cached_ciks
                        tier = "TIER_0" if (is_sp and is_arc) else ("TIER_1" if is_sp else ("TIER_2" if is_arc else "TIER_3"))
                        self._us_companies[ov_t] = UniverseCompanyRecord(
                            ticker=ov_t,
                            company_name=ov_t,
                            market="US",
                            tier=tier,
                            cik=ov_cik_str,
                            has_local_filing=is_arc,
                        )
            except Exception:
                pass

        # 4. 加载全量日股东证上市公司 (4,400+ 家)
        if self.jpx_path.exists():
            try:
                jpx_raw = json.loads(self.jpx_path.read_text(encoding="utf-8"))
                for entry in jpx_raw:
                    t = entry.get("ticker", "").upper().strip()
                    code = str(entry.get("code", "")).strip()
                    name = entry.get("name", t)
                    mkt_seg = entry.get("market_segment", "")
                    ind33 = entry.get("industry_33", "")
                    scale = entry.get("scale_category", "")

                    if "TOPIX Core30" in scale or "TOPIX Large70" in scale:
                        tier = "TIER_0"
                    elif "プライム" in mkt_seg or "TOPIX Mid400" in scale:
                        tier = "TIER_1"
                    elif "スタンダード" in mkt_seg:
                        tier = "TIER_2"
                    else:
                        tier = "TIER_3"

                    rec = UniverseCompanyRecord(
                        ticker=t,
                        company_name=name,
                        market="JP",
                        tier=tier,
                        jpx_code=code,
                        sector=ind33,
                        industry=mkt_seg,
                        has_local_filing=False,
                    )
                    self._jp_companies[t] = rec
            except Exception:
                pass

        self._is_loaded = True

    def get_stats(self) -> TieredUniverseStats:
        """获取全盘资产池分级统计数据."""
        self.load_universe()
        tot = len(self._us_companies) + len(self._jp_companies)
        t0 = sum(1 for c in self._us_companies.values() if c.tier == "TIER_0") + sum(1 for c in self._jp_companies.values() if c.tier == "TIER_0")
        t1 = sum(1 for c in self._us_companies.values() if c.tier == "TIER_1") + sum(1 for c in self._jp_companies.values() if c.tier == "TIER_1")
        t2 = sum(1 for c in self._us_companies.values() if c.tier == "TIER_2") + sum(1 for c in self._jp_companies.values() if c.tier == "TIER_2")
        t3 = sum(1 for c in self._us_companies.values() if c.tier == "TIER_3") + sum(1 for c in self._jp_companies.values() if c.tier == "TIER_3")
        archived = sum(1 for c in self._us_companies.values() if c.has_local_filing)

        ratio = (archived / max(len(self._us_companies), 1)) * 100.0

        return TieredUniverseStats(
            total_companies=tot,
            us_sec_count=len(self._us_companies),
            jp_jpx_count=len(self._jp_companies),
            tier_0_count=t0,
            tier_1_count=t1,
            tier_2_count=t2,
            tier_3_count=t3,
            sec_archived_count=archived,
            sec_archived_ratio_pct=round(ratio, 2),
        )

    def lookup(self, ticker_or_code: str, market: Optional[str] = None) -> Optional[UniverseCompanyRecord]:
        """按代码检索全盘公司记录."""
        self.load_universe()
        query = ticker_or_code.upper().strip()

        # 美股优先
        if market in (None, "US", "us"):
            if query in self._us_companies:
                return self._us_companies[query]

        # 日股匹配
        if market in (None, "JP", "jp"):
            if query in self._jp_companies:
                return self._jp_companies[query]
            # 兼容纯数字或 TYO: 前缀
            jpx_clean = query.replace("TYO:", "")
            for rec in self._jp_companies.values():
                if rec.jpx_code == jpx_clean or rec.ticker.replace("TYO:", "") == jpx_clean:
                    return rec

        return None

    def get_batch_chunk(
        self,
        market: str = "US",
        tier: Optional[str] = None,
        batch_index: int = 0,
        batch_size: int = 50,
        unarchived_only: bool = False,
    ) -> List[UniverseCompanyRecord]:
        """获取资产池按批次切片清单 (Batch Chunking)."""
        self.load_universe()
        target_dict = self._us_companies if market.upper() == "US" else self._jp_companies
        candidates = list(target_dict.values())

        if tier:
            candidates = [c for c in candidates if c.tier == tier.upper()]

        if unarchived_only:
            candidates = [c for c in candidates if not c.has_local_filing]

        start = batch_index * batch_size
        end = start + batch_size
        return candidates[start:end]

    def get_sp500_priority_collection_list(self, unarchived_only: bool = True) -> List[UniverseCompanyRecord]:
        """获取 S&P 500 核心资产池优先收集清单."""
        self.load_universe()
        res = []
        for t in sorted(self._sp500_tickers):
            rec = self._us_companies.get(t)
            if rec:
                if unarchived_only and rec.has_local_filing:
                    continue
                res.append(rec)
        return res
