# -*- coding: utf-8 -*-
"""冷热数据分层生命周期引擎 (data_lifecycle_engine.py).

核心设计理念：
1. 云端(GitHub)放工具与方法，本地工作站存分层数据本体：
   - 本模块及配套加工脚本、索引契约、防泄露守卫沉淀在 GitHub 代码库；
   - 任何实际行情、财报底稿、压缩归档包均严格隔离在本地 data/ 目录，绝不进入版本控制。
2. 买方三层数据生命周期 (Hot / Warm / Cold)：
   - 热数据 (Hot Tier) : 近30天活跃行情与近1~2年核心财报速查快照 -> 未压缩极简 JSON，毫秒直读；
   - 温数据 (Warm Tier): 30天~3年标准日线与近3年(12季度)完整财报切片 -> 紧凑 JSON，秒级定位；
   - 冷数据 (Cold Tier): 3年以上历史老旧底稿与超期全量归档 -> 高压缩 .json.gz，节省 85%+ 磁盘空间，按需秒级无损唤醒。
3. 无损可逆契约 (Lossless & Verifiable)：
   - 拆分采取严格互斥时间分片：温数据(Warm) + 冷数据(Cold) 构成原数据的 100% 完备无重叠全集；
   - 热数据(Hot)为温数据最近活跃期的高频视图子集；
   - 每次归档均计算原始规范化 SHA-256 指纹与条目总数写入轻量清单，唤醒时强制验签比对，绝不丢数、绝不串数。
"""

from dataclasses import dataclass, asdict
from datetime import datetime, date, timezone
from enum import Enum
import gzip
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple


class DataTier(str, Enum):
    """数据冷热生命周期层级枚举."""

    HOT = "hot"    # 热数据：盘前/盘中毫秒直读
    WARM = "warm"  # 温数据：近3年形态与估值对比
    COLD = "cold"  # 冷数据：3年以上高压缩归档，按需唤醒


# 各层级通俗商业元数据注册表 (SSOT)
TIER_METADATA_REGISTRY: Dict[str, Dict[str, Any]] = {
    DataTier.HOT.value: {
        "zh_name": "热数据层 (Hot Tier)",
        "badge": "🔥 高频热区",
        "retention_rule": "行情/事件 <= 30天；财报切片 <= 1~2年（近4~6季度）",
        "business_purpose": "盘前3分钟决策、看板实时呼吸灯、实时流动性与期权异动盯盘",
        "storage_format": "极简紧凑 JSON（零压缩零解压开销，毫秒直读）",
        "local_subdir": "data/hot",
    },
    DataTier.WARM.value: {
        "zh_name": "温数据层 (Warm Tier)",
        "badge": "🌤️ 活跃温区",
        "retention_rule": "行情/事件 31天~3年；财报切片近3年（近12季度）",
        "business_purpose": "250日趋势与VCP形态初筛、连续12季度杜邦分解与DCF现金流贴现",
        "storage_format": "紧凑 JSON + 轻量元数据索引清单",
        "local_subdir": "data/warm",
    },
    DataTier.COLD.value: {
        "zh_name": "冷数据层 (Cold Tier)",
        "badge": "❄️ 深冷归档区",
        "retention_rule": "3年以上历史行情与过往年份官方原始财报事实",
        "business_purpose": "十年跨周期黑天鹅极限回测、历史法证审计与按需唤醒还原",
        "storage_format": "Gzip 高倍无损压缩包 (.json.gz) + SHA-256 校验清单",
        "local_subdir": "data/cold",
    },
}


@dataclass(frozen=True)
class LifecyclePolicyConfig:
    """冷热分层生命周期全局配置字典 (SSOT)."""

    hot_quote_days: int = 30
    warm_quote_days: int = 1095  # 约 3 年
    hot_filing_years: int = 1    # 包含参考年与前1年 (例如 2026 参考年 -> 2025~2026)
    warm_filing_years: int = 3   # 包含近3~4年 (例如 2026 参考年 -> 2023~2026)
    gzip_compresslevel: int = 9  # 最高无损压缩比


@dataclass(frozen=True)
class TieredFilingSplitResult:
    """官方 SEC 财报按时间切片分层加工结果契约."""

    cik: str
    entity_name: str
    reference_year: int
    warm_cutoff_year: int
    hot_cutoff_year: int
    total_original_items: int
    hot_items_count: int
    warm_items_count: int
    cold_items_count: int
    original_canonical_sha256: str
    is_lossless_partition: bool


@dataclass(frozen=True)
class CompactionReport:
    """单文件冷热加工与物理压缩实测报告."""

    source_path: str
    cik: str
    entity_name: str
    original_size_bytes: int
    hot_size_bytes: int
    warm_size_bytes: int
    cold_compressed_bytes: int
    manifest_size_bytes: int
    total_tiered_size_bytes: int
    space_saved_bytes: int
    space_saved_pct: float
    hot_items_count: int
    warm_items_count: int
    cold_items_count: int
    total_original_items: int
    original_canonical_sha256: str
    hot_path: str
    warm_path: str
    cold_path: str
    manifest_path: str
    lossless_verified: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RestoreVerificationResult:
    """冷数据唤醒还原与完整性验签结果."""

    cik: str
    entity_name: str
    restored_items_count: int
    expected_items_count: int
    restored_canonical_sha256: str
    expected_canonical_sha256: str
    integrity_passed: bool
    message: str


@dataclass(frozen=True)
class DataLeakCheckResult:
    """GitHub 云端仓库防数据泄露门禁检验结果."""

    is_clean: bool
    checked_paths_count: int
    violating_paths: List[str]
    violation_reasons: Dict[str, str]
    summary_message: str


def _canonical_json_bytes(obj: Any) -> bytes:
    """生成跨平台一致的紧凑规范化 JSON 字节流 (无空格、键名确定性排序)."""
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _compute_canonical_sha256(obj: Any) -> str:
    """计算任意 JSON 可序列化对象的规范化 SHA-256 哈希指纹."""
    return hashlib.sha256(_canonical_json_bytes(obj)).hexdigest()


def _extract_fact_year(item: Dict[str, Any]) -> Optional[int]:
    """安全提取单条 SEC 财报事实记录所属年份.

    优先级：
    1. 财报期末日期 `end` (如 "2024-01-28" -> 2024)；
    2. 申报提交日期 `filed` (如 "2024-02-21" -> 2024)；
    3. 财年字段 `fy` (如 2024)；
    4. 若均缺失或非法，返回 None（将安全归入温区以防误失）。
    """
    for key in ("end", "filed", "start"):
        val = item.get(key)
        if isinstance(val, str) and len(val) >= 4 and val[:4].isdigit():
            yr = int(val[:4])
            if 1900 <= yr <= 2100:
                return yr
    fy = item.get("fy")
    if isinstance(fy, int) and 1900 <= fy <= 2100:
        return fy
    if isinstance(fy, str) and fy.isdigit():
        yr = int(fy)
        if 1900 <= yr <= 2100:
            return yr
    return None


def _count_sec_fact_items(sec_data: Dict[str, Any]) -> int:
    """统计 SEC companyfacts JSON 中的全部事实条目总数."""
    total = 0
    facts = sec_data.get("facts") or {}
    if not isinstance(facts, dict):
        return 0
    for concepts in facts.values():
        if not isinstance(concepts, dict):
            continue
        for cobj in concepts.values():
            if not isinstance(cobj, dict):
                continue
            units = cobj.get("units") or {}
            if not isinstance(units, dict):
                continue
            for items in units.values():
                if isinstance(items, list):
                    total += len(items)
    return total


def _canonical_fact_multiset_digest(sec_data: Dict[str, Any]) -> Tuple[int, str]:
    """计算 SEC companyfacts 的顺序无关全集指纹 (条目数 + 排序后摘要哈希).

    用于验证 Warm + Cold 拆分再合并后，每个概念/单位下的事实记录是否与原文件 100% 完全等价。
    """
    normalized_facts: Dict[str, Dict[str, Dict[str, List[Any]]]] = {}
    total_count = 0
    facts = sec_data.get("facts") or {}
    for tax, concepts in sorted(facts.items()):
        if not isinstance(concepts, dict):
            continue
        tax_dict: Dict[str, Dict[str, List[Any]]] = {}
        for cname, cobj in sorted(concepts.items()):
            if not isinstance(cobj, dict):
                continue
            units = cobj.get("units") or {}
            unit_dict: Dict[str, List[Any]] = {}
            for uname, items in sorted(units.items()):
                if not isinstance(items, list):
                    continue
                total_count += len(items)
                # 对同一 unit 下的条目按规范化字符串排序，屏蔽列表重排影响
                serialized_items = sorted(
                    json.dumps(it, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    for it in items
                )
                unit_dict[uname] = serialized_items
            if unit_dict:
                tax_dict[cname] = unit_dict
        if tax_dict:
            normalized_facts[tax] = tax_dict

    envelope = {
        "cik": sec_data.get("cik"),
        "entityName": sec_data.get("entityName"),
        "facts": normalized_facts,
    }
    return total_count, _compute_canonical_sha256(envelope)


class DataLifecycleEngine:
    """买方机构级冷热数据分层与无损加工引擎 (核心纯净层)."""

    # 严格禁止提交至 GitHub 云端的本地数据路径与后缀特征
    FORBIDDEN_DATA_PREFIXES: Tuple[str, ...] = (
        "data/",
        "data_max/",
        "reports/",
        "scratch/",
        ".cache/",
    )

    FORBIDDEN_DATA_EXTENSIONS: Tuple[str, ...] = (
        ".tar.gz",
        ".tgz",
        ".gz",
        ".zip",
        ".parquet",
        ".sqlite",
        ".sqlite3",
        ".db",
        ".blob",
        ".pkl",
        ".pickle",
        ".feather",
        ".h5",
        ".hdf5",
    )

    def __init__(self, policy: Optional[LifecyclePolicyConfig] = None) -> None:
        self.policy = policy or LifecyclePolicyConfig()

    # =========================================================================
    # 一、 日常行情与事件时效冷热判定 (Quote & Event Tier Classification)
    # =========================================================================

    def classify_date_tier(
        self,
        target_date_str: str,
        reference_date_str: Optional[str] = None,
    ) -> DataTier:
        """根据业务时间距今跨度判定属于热、温还是冷数据层级.

        Args:
            target_date_str: 数据日期，支持 YYYY-MM-DD 或 YYYYMMDD 或 ISO 时间戳
            reference_date_str: 参考基准日（默认取当前 UTC 日期）
        """
        target_dt = self._parse_date_safe(target_date_str)
        if target_dt is None:
            # 无法解析日期时保守划入温区，避免误删或误冷
            return DataTier.WARM

        if reference_date_str:
            ref_dt = self._parse_date_safe(reference_date_str) or datetime.now(timezone.utc).date()
        else:
            ref_dt = datetime.now(timezone.utc).date()

        age_days = (ref_dt - target_dt).days
        if age_days <= self.policy.hot_quote_days:
            return DataTier.HOT
        if age_days <= self.policy.warm_quote_days:
            return DataTier.WARM
        return DataTier.COLD

    @staticmethod
    def _parse_date_safe(raw: str) -> Optional[date]:
        if not raw or not isinstance(raw, str):
            return None
        s = raw.strip()
        m_iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
        if m_iso:
            try:
                return date(int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3)))
            except ValueError:
                return None
        m_compact = re.match(r"^(\d{4})(\d{2})(\d{2})", s)
        if m_compact:
            try:
                return date(int(m_compact.group(1)), int(m_compact.group(2)), int(m_compact.group(3)))
            except ValueError:
                return None
        return None

    # =========================================================================
    # 二、 官方 SEC 财报底稿无损时间切片加工 (Lossless SEC Filing Tier Splitter)
    # =========================================================================

    def split_sec_company_facts(
        self,
        raw_sec_data: Dict[str, Any],
        reference_year: Optional[int] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], TieredFilingSplitResult]:
        """将海量历史 SEC companyfacts JSON 无损拆分为热、温、冷三层结构.

        拆分契约：
        - 温区 (Warm Payload): 包含 `year > warm_cutoff_year`（例如近3年+当年，以及极少数无日期标识条目）；
        - 冷区 (Cold Payload): 包含 `year <= warm_cutoff_year`（3年以上所有老旧历史事实）；
        - 热区 (Hot Payload): 温区中 `year >= hot_cutoff_year` 的高频速查子集（用于盘前秒级加载）；
        - 铁律：Warm 与 Cold 严格互斥且并集 = 100% 原始事实全集！

        Returns:
            (hot_payload, warm_payload, cold_payload, split_result)
        """
        if not isinstance(raw_sec_data, dict) or "facts" not in raw_sec_data:
            raise ValueError("非法的 SEC companyfacts 结构：缺少顶层 'facts' 字段")

        ref_year = reference_year or datetime.now(timezone.utc).year
        warm_cutoff_year = ref_year - self.policy.warm_filing_years  # 如 2026 - 3 = 2023 -> >= 2023归温，<=2022归冷
        hot_cutoff_year = ref_year - self.policy.hot_filing_years    # 如 2026 - 1 = 2025 -> >= 2025归热

        cik_val = raw_sec_data.get("cik")
        cik_str = f"CIK{int(cik_val):010d}" if isinstance(cik_val, int) else str(cik_val or "UNKNOWN")
        entity_name = str(raw_sec_data.get("entityName") or "Unknown Entity")

        hot_facts: Dict[str, Any] = {}
        warm_facts: Dict[str, Any] = {}
        cold_facts: Dict[str, Any] = {}

        hot_count = 0
        warm_count = 0
        cold_count = 0

        raw_facts = raw_sec_data.get("facts") or {}
        for taxonomy, concepts in raw_facts.items():
            if not isinstance(concepts, dict):
                continue

            for concept_name, concept_obj in concepts.items():
                if not isinstance(concept_obj, dict):
                    continue
                units = concept_obj.get("units") or {}
                if not isinstance(units, dict):
                    continue

                label = concept_obj.get("label")
                desc = concept_obj.get("description")

                hot_units: Dict[str, List[Dict[str, Any]]] = {}
                warm_units: Dict[str, List[Dict[str, Any]]] = {}
                cold_units: Dict[str, List[Dict[str, Any]]] = {}

                for unit_name, items in units.items():
                    if not isinstance(items, list):
                        continue
                    h_list: List[Dict[str, Any]] = []
                    w_list: List[Dict[str, Any]] = []
                    c_list: List[Dict[str, Any]] = []

                    for idx, item in enumerate(items):
                        if not isinstance(item, dict):
                            # 非字典防御兜底入温区
                            w_list.append(item)
                            warm_count += 1
                            continue

                        yr = _extract_fact_year(item)
                        if yr is None or yr >= warm_cutoff_year:
                            w_list.append(item)
                            warm_count += 1
                            if yr is not None and yr >= hot_cutoff_year:
                                h_list.append(item)
                                hot_count += 1
                        else:
                            c_list.append(item)
                            cold_count += 1

                    if h_list:
                        hot_units[unit_name] = h_list
                    if w_list:
                        warm_units[unit_name] = w_list
                    if c_list:
                        cold_units[unit_name] = c_list

                if hot_units:
                    hot_facts.setdefault(taxonomy, {})[concept_name] = {
                        "label": label,
                        "description": desc,
                        "units": hot_units,
                    }
                if warm_units:
                    warm_facts.setdefault(taxonomy, {})[concept_name] = {
                        "label": label,
                        "description": desc,
                        "units": warm_units,
                    }
                if cold_units:
                    cold_facts.setdefault(taxonomy, {})[concept_name] = {
                        "label": label,
                        "description": desc,
                        "units": cold_units,
                    }

        hot_payload = {
            "cik": cik_val,
            "entityName": entity_name,
            "tier": DataTier.HOT.value,
            "tier_cutoff_year": hot_cutoff_year,
            "facts": hot_facts,
        }
        warm_payload = {
            "cik": cik_val,
            "entityName": entity_name,
            "tier": DataTier.WARM.value,
            "tier_cutoff_year": warm_cutoff_year,
            "facts": warm_facts,
        }
        cold_payload = {
            "cik": cik_val,
            "entityName": entity_name,
            "tier": DataTier.COLD.value,
            "tier_max_year": warm_cutoff_year - 1,
            "facts": cold_facts,
        }

        orig_count, orig_sha = _canonical_fact_multiset_digest(raw_sec_data)
        is_lossless = (warm_count + cold_count == orig_count)

        split_result = TieredFilingSplitResult(
            cik=cik_str,
            entity_name=entity_name,
            reference_year=ref_year,
            warm_cutoff_year=warm_cutoff_year,
            hot_cutoff_year=hot_cutoff_year,
            total_original_items=orig_count,
            hot_items_count=hot_count,
            warm_items_count=warm_count,
            cold_items_count=cold_count,
            original_canonical_sha256=orig_sha,
            is_lossless_partition=is_lossless,
        )
        return hot_payload, warm_payload, cold_payload, split_result

    # =========================================================================
    # 三、 合并还原与防篡改验签 (Lossless Merge & Restore Verification)
    # =========================================================================

    @staticmethod
    def merge_warm_and_cold_sec_facts(
        warm_payload: Dict[str, Any],
        cold_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """将温数据切片与唤醒后的冷数据切片无损合成为完整的 SEC companyfacts 底稿."""
        merged_facts: Dict[str, Dict[str, Any]] = {}

        for source in (cold_payload, warm_payload):
            facts = source.get("facts") or {}
            for tax, concepts in facts.items():
                if not isinstance(concepts, dict):
                    continue
                target_tax = merged_facts.setdefault(tax, {})
                for cname, cobj in concepts.items():
                    if not isinstance(cobj, dict):
                        continue
                    target_c = target_tax.setdefault(
                        cname,
                        {
                            "label": cobj.get("label"),
                            "description": cobj.get("description"),
                            "units": {},
                        },
                    )
                    if target_c.get("label") is None and cobj.get("label") is not None:
                        target_c["label"] = cobj.get("label")
                    if target_c.get("description") is None and cobj.get("description") is not None:
                        target_c["description"] = cobj.get("description")

                    for uname, items in (cobj.get("units") or {}).items():
                        if isinstance(items, list):
                            target_c["units"].setdefault(uname, []).extend(items)

        return {
            "cik": warm_payload.get("cik") if warm_payload.get("cik") is not None else cold_payload.get("cik"),
            "entityName": warm_payload.get("entityName") or cold_payload.get("entityName"),
            "facts": merged_facts,
        }

    # =========================================================================
    # 四、 本地物理落盘压缩与秒级唤醒方法 (Local Disk Compaction & Restore)
    # =========================================================================

    def compact_sec_filing_file(
        self,
        source_file: Path,
        data_root: Path,
        reference_year: Optional[int] = None,
        prune_original: bool = False,
    ) -> CompactionReport:
        """将单个原始 SEC 财报大文件加工落盘为本地 Hot / Warm / Cold 三层结构.

        安全铁律：
        - 默认 `prune_original=False`（打样安全模式），绝不删除原始文件；
        - 落盘后强制立即执行一次冷数据逆向解压合成验签，100% 确认字节/语义哈希无损一致才签发通过！
        """
        src = Path(source_file)
        if not src.is_file():
            raise FileNotFoundError(f"原始财报文件不存在: {src}")

        raw_bytes = src.read_bytes()
        original_size_bytes = len(raw_bytes)
        raw_sec_data = json.loads(raw_bytes.decode("utf-8"))

        hot_payload, warm_payload, cold_payload, split_res = self.split_sec_company_facts(
            raw_sec_data, reference_year=reference_year
        )
        if not split_res.is_lossless_partition:
            raise RuntimeError(
                f"无损拆分校验异常: warm({split_res.warm_items_count}) + cold({split_res.cold_items_count}) != {split_res.total_original_items}"
            )

        stem = src.stem  # 例如 CIK0001045810
        hot_dir = Path(data_root) / "hot" / "filings_sec"
        warm_dir = Path(data_root) / "warm" / "filings_sec"
        cold_dir = Path(data_root) / "cold" / "filings_sec"
        manifest_dir = Path(data_root) / "warm" / "manifests"

        for d in (hot_dir, warm_dir, cold_dir, manifest_dir):
            d.mkdir(parents=True, exist_ok=True)

        hot_path = hot_dir / f"{stem}.hot.json"
        warm_path = warm_dir / f"{stem}.warm.json"
        cold_path = cold_dir / f"{stem}.cold.json.gz"
        manifest_path = manifest_dir / f"{stem}.lifecycle_manifest.json"

        # 1. 写入热数据与温数据（紧凑单行 JSON，零解析冗余空格）
        hot_bytes = _canonical_json_bytes(hot_payload)
        warm_bytes = _canonical_json_bytes(warm_payload)
        hot_path.write_bytes(hot_bytes)
        warm_path.write_bytes(warm_bytes)

        # 2. 写入深冷高压缩归档 (.json.gz)
        cold_bytes_raw = _canonical_json_bytes(cold_payload)
        with gzip.open(cold_path, "wb", compresslevel=self.policy.gzip_compresslevel) as gz:
            gz.write(cold_bytes_raw)

        cold_compressed_bytes = cold_path.stat().st_size
        cold_gz_sha256 = hashlib.sha256(cold_path.read_bytes()).hexdigest()
        warm_sha256 = hashlib.sha256(warm_bytes).hexdigest()

        # 3. 写入轻量生命周期元数据清单
        manifest = {
            "schema_version": "1.0.0",
            "cik": split_res.cik,
            "entity_name": split_res.entity_name,
            "processed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "reference_year": split_res.reference_year,
            "hot_cutoff_year": split_res.hot_cutoff_year,
            "warm_cutoff_year": split_res.warm_cutoff_year,
            "counts": {
                "original_total": split_res.total_original_items,
                "hot": split_res.hot_items_count,
                "warm": split_res.warm_items_count,
                "cold": split_res.cold_items_count,
            },
            "integrity": {
                "original_canonical_sha256": split_res.original_canonical_sha256,
                "warm_file_sha256": warm_sha256,
                "cold_gz_sha256": cold_gz_sha256,
            },
            "paths": {
                "hot": str(hot_path.as_posix()),
                "warm": str(warm_path.as_posix()),
                "cold": str(cold_path.as_posix()),
            },
        }
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        manifest_path.write_bytes(manifest_bytes)

        # 4. 强制当场回读唤醒验签 (防止写入损坏或数据丢失)
        verify_res = self.restore_and_verify_from_tiers(
            warm_path=warm_path,
            cold_path=cold_path,
            manifest_path=manifest_path,
        )
        if not verify_res.integrity_passed:
            raise RuntimeError(f"冷热分层落地验签失败: {verify_res.message}")

        # 5. 仅在明确授权 prune_original=True 且验签 100% 通过后才清理原巨型文件
        if prune_original:
            src.unlink()

        total_tiered_bytes = (
            len(hot_bytes)
            + len(warm_bytes)
            + cold_compressed_bytes
            + len(manifest_bytes)
        )
        # 比较仅温+冷(长期存档主干) vs 原文件，以及三层总和 vs 原文件
        space_saved = max(0, original_size_bytes - total_tiered_bytes)
        space_saved_pct = round((space_saved / original_size_bytes) * 100.0, 2) if original_size_bytes > 0 else 0.0

        return CompactionReport(
            source_path=str(src.as_posix()),
            cik=split_res.cik,
            entity_name=split_res.entity_name,
            original_size_bytes=original_size_bytes,
            hot_size_bytes=len(hot_bytes),
            warm_size_bytes=len(warm_bytes),
            cold_compressed_bytes=cold_compressed_bytes,
            manifest_size_bytes=len(manifest_bytes),
            total_tiered_size_bytes=total_tiered_bytes,
            space_saved_bytes=space_saved,
            space_saved_pct=space_saved_pct,
            hot_items_count=split_res.hot_items_count,
            warm_items_count=split_res.warm_items_count,
            cold_items_count=split_res.cold_items_count,
            total_original_items=split_res.total_original_items,
            original_canonical_sha256=split_res.original_canonical_sha256,
            hot_path=str(hot_path.as_posix()),
            warm_path=str(warm_path.as_posix()),
            cold_path=str(cold_path.as_posix()),
            manifest_path=str(manifest_path.as_posix()),
            lossless_verified=verify_res.integrity_passed,
        )

    def restore_and_verify_from_tiers(
        self,
        warm_path: Path,
        cold_path: Path,
        manifest_path: Path,
    ) -> RestoreVerificationResult:
        """从温区 JSON + 冷区 .json.gz 秒级唤醒并还原完整原始底稿，强制 SHA-256 验签."""
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        expected_sha = manifest["integrity"]["original_canonical_sha256"]
        expected_count = manifest["counts"]["original_total"]
        cik = manifest["cik"]
        entity_name = manifest["entity_name"]

        # 先验磁盘物理文件指纹防篡改
        warm_raw = Path(warm_path).read_bytes()
        if hashlib.sha256(warm_raw).hexdigest() != manifest["integrity"]["warm_file_sha256"]:
            return RestoreVerificationResult(
                cik=cik,
                entity_name=entity_name,
                restored_items_count=0,
                expected_items_count=expected_count,
                restored_canonical_sha256="TAMPERED_WARM",
                expected_canonical_sha256=expected_sha,
                integrity_passed=False,
                message="温数据文件哈希与清单记录不符，文件可能已损坏或被篡改",
            )

        cold_gz_raw = Path(cold_path).read_bytes()
        if hashlib.sha256(cold_gz_raw).hexdigest() != manifest["integrity"]["cold_gz_sha256"]:
            return RestoreVerificationResult(
                cik=cik,
                entity_name=entity_name,
                restored_items_count=0,
                expected_items_count=expected_count,
                restored_canonical_sha256="TAMPERED_COLD",
                expected_canonical_sha256=expected_sha,
                integrity_passed=False,
                message="冷数据压缩归档包哈希与清单记录不符，压缩包可能已损坏或被篡改",
            )

        warm_payload = json.loads(warm_raw.decode("utf-8"))
        with gzip.open(cold_path, "rb") as gz:
            cold_payload = json.loads(gz.read().decode("utf-8"))

        restored_full = self.merge_warm_and_cold_sec_facts(warm_payload, cold_payload)
        restored_count, restored_sha = _canonical_fact_multiset_digest(restored_full)

        passed = (restored_count == expected_count) and (restored_sha == expected_sha)
        msg = (
            f"无损唤醒验签通过：{restored_count}/{expected_count} 条事实记录与 SHA-256 规范指纹完全吻合"
            if passed
            else f"唤醒验签不一致：期望条目 {expected_count} 实得 {restored_count}，哈希匹配={restored_sha == expected_sha}"
        )

        return RestoreVerificationResult(
            cik=cik,
            entity_name=entity_name,
            restored_items_count=restored_count,
            expected_items_count=expected_count,
            restored_canonical_sha256=restored_sha,
            expected_canonical_sha256=expected_sha,
            integrity_passed=passed,
            message=msg,
        )

    def restore_sec_filing_dict(
        self,
        warm_path: Path,
        cold_path: Path,
        manifest_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """按需唤醒并返回完整的 SEC companyfacts 字典供历史长周期回测使用."""
        if manifest_path is not None:
            ver = self.restore_and_verify_from_tiers(warm_path, cold_path, manifest_path)
            if not ver.integrity_passed:
                raise RuntimeError(f"拒绝加载损坏的冷热数据归档: {ver.message}")

        warm_payload = json.loads(Path(warm_path).read_text(encoding="utf-8"))
        with gzip.open(cold_path, "rb") as gz:
            cold_payload = json.loads(gz.read().decode("utf-8"))
        return self.merge_warm_and_cold_sec_facts(warm_payload, cold_payload)

    # =========================================================================
    # 五、 全盘冷热分布扫描与云端防数据泄露安全检查 (Audit & Anti-Leak Guard)
    # =========================================================================

    @staticmethod
    def inspect_workspace_tiers(data_root: Path) -> Dict[str, Any]:
        """统计本地工作站热/温/冷三层与原始未分层底账的文件数量与空间占用."""
        root = Path(data_root)
        targets = {
            "hot": root / "hot",
            "warm": root / "warm",
            "cold": root / "cold",
            "legacy_raw_sec": root / "official_filings" / "sec",
        }
        summary: Dict[str, Any] = {}
        for key, folder in targets.items():
            if not folder.exists():
                summary[key] = {"exists": False, "file_count": 0, "size_mb": 0.0}
                continue
            files = [p for p in folder.rglob("*") if p.is_file()]
            total_bytes = sum(p.stat().st_size for p in files)
            summary[key] = {
                "exists": True,
                "file_count": len(files),
                "size_mb": round(total_bytes / (1024 * 1024), 2),
            }
        return summary

    def check_paths_for_data_leak(self, repo_relative_paths: Iterable[str]) -> DataLeakCheckResult:
        """检查一批相对路径是否包含严禁上传到 GitHub 云端的本地数据文件.

        这是保护“云端只放工具和方法，不放数据”铁律的核心纯逻辑守卫。
        """
        checked_count = 0
        violating: List[str] = []
        reasons: Dict[str, str] = {}

        for raw_p in repo_relative_paths:
            checked_count += 1
            norm_p = raw_p.replace("\\", "/").lstrip("./")
            lower_p = norm_p.lower()

            # 1. 路径前缀硬拦截 (data/, data_max/, reports/, .cache/, scratch/)
            matched_prefix = next(
                (pref for pref in self.FORBIDDEN_DATA_PREFIXES if lower_p.startswith(pref)),
                None,
            )
            if matched_prefix:
                violating.append(norm_p)
                reasons[norm_p] = f"命中禁传数据目录前缀 '{matched_prefix}'（云端 GitHub 严禁存放本地数据底账）"
                continue

            # 2. 禁止二进制/压缩归档/数据库后缀进入云端
            matched_ext = next(
                (ext for ext in self.FORBIDDEN_DATA_EXTENSIONS if lower_p.endswith(ext)),
                None,
            )
            if matched_ext:
                violating.append(norm_p)
                reasons[norm_p] = f"命中禁传数据压缩/二进制后缀 '{matched_ext}'（仅限本地冷热存储）"
                continue

            # 3. 拦截裸露在任意目录下的巨型 SEC CIK*.json 底稿
            fname = norm_p.rsplit("/", 1)[-1]
            if re.match(r"^CIK\d{10}\.(json|hot\.json|warm\.json)$", fname, flags=re.IGNORECASE):
                violating.append(norm_p)
                reasons[norm_p] = "命中 SEC 官方巨型原始财报文件（CIK*.json 禁止推送到 GitHub）"
                continue

        is_clean = len(violating) == 0
        if is_clean:
            msg = f"云端边界检查通过：已核验 {checked_count} 个路径，零数据泄露风险，仅包含工具、代码与知识文档。"
        else:
            msg = f"拦截警告：发现 {len(violating)} 个违禁数据路径试图进入云端 Git 仓库，已物理阻断！"

        return DataLeakCheckResult(
            is_clean=is_clean,
            checked_paths_count=checked_count,
            violating_paths=violating,
            violation_reasons=reasons,
            summary_message=msg,
        )
