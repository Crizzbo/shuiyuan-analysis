"""多业务分部 (SOTP) 突发事件穿透分析工具 (SOTP Event Analyzer Tool).

本模块属于 finance_tools 中继工具层:
- 连接 SQLite 事件账本 (data/ledger/event_radar.sqlite3) 与底层 SotpEventPenetrationEngine;
- 从显式本地档案加载分部事实、证据引用与独立情景假设;
- 执行自动化分部暴露穿透、库存缓冲吸收、转嫁能力冲销与企业级损益加总。
"""

import json
import hashlib
import re
from jsonschema import Draft202012Validator
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from financial_core.engines.sotp_event_penetration_engine import (
    BusinessSegment,
    CompanySotpProfile,
    SegmentCausalImpact,
    EnterpriseEventImpactResult,
    SotpEventPenetrationEngine,
)
from financial_core.engines.event_radar_engine import StructuredEventSummary
from financial_core.engines.filing_mapper import OfficialFilingMapper
from financial_core.engines.quote_freshness_gateway import QuoteFreshnessGateway
from finance_tools.event_radar_collector import RadarDatabaseManager

ROOT = Path(__file__).resolve().parents[2]

logger = logging.getLogger(__name__)


class SotpEventAnalyzer:
    """多业务分部突发事件穿透与全息分析器."""

    def __init__(
        self,
        db_path: str = "data/ledger/event_radar.sqlite3",
        engine: Optional[SotpEventPenetrationEngine] = None,
        *,
        profiles_path: str = "config/sotp_profiles.json",
        root_dir: Optional[Path] = None,
        allow_synthetic: bool = False,
        current_time_iso: Optional[str] = None,
    ):
        self.root_dir = (root_dir or ROOT).resolve()
        if not self.root_dir.is_relative_to(ROOT):
            raise ValueError("SOTP 根目录必须在当前工程内")
        self.db_path = db_path
        self._db_mgr = None
        self.engine = engine or SotpEventPenetrationEngine()
        self.allow_synthetic = allow_synthetic
        self.current_time_iso = current_time_iso
        registry = json.loads(self._local_path(profiles_path).read_text(encoding="utf-8"))
        schema = json.loads((ROOT / "schemas/sotp_profiles.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(registry)
        self.profiles = registry["profiles"]

    @property
    def db_mgr(self) -> RadarDatabaseManager:
        """查询存量事件时才打开数据库，加载财务档案保持无写入副作用。"""
        if self._db_mgr is None:
            self._db_mgr = RadarDatabaseManager(db_path=str(self._local_path(self.db_path)))
        return self._db_mgr

    def _local_path(self, reference: str) -> Path:
        """核验项目内相对路径及符号链接最终位置。"""
        if not reference or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", reference) or reference.startswith(("/", "\\")):
            raise ValueError("SOTP 引用必须为项目内相对路径")
        target = (self.root_dir / reference).resolve()
        if not target.is_relative_to(self.root_dir):
            raise ValueError("SOTP 引用越过工程边界")
        return target

    def _verify_source(self, reference: Dict[str, str]) -> None:
        """核对已归档字节的摘要，事实释义仍需正式财报审核。"""
        source = self._local_path(reference["source_path"])
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != reference["sha256"]:
            raise ValueError("SOTP 原文缺失或摘要不匹配")

    def get_company_sotp_profile(self, ticker: str) -> Optional[CompanySotpProfile]:
        """从显式本地档案载入财务事实、独立情景假设及已核验行情。"""
        raw = self.profiles.get(ticker.upper())
        if raw is None:
            return None
        if raw["data_origin"] == "synthetic" and not self.allow_synthetic:
            raise ValueError("正式 SOTP 分析禁止加载合成演示档案")
        facts, assumptions = raw["facts"], raw["assumptions"]
        evidence = raw["fact_evidence"]

        def fact_number(field: str, value: Any) -> float:
            if field not in evidence:
                raise ValueError(f"SOTP 财务事实缺少逐项来源 {field}")
            self._verify_source(evidence[field])
            number = OfficialFilingMapper.parse_optional_financial_number(value, field)
            if number is None:
                raise ValueError(f"SOTP 财务事实缺失 {field}")
            return number

        segments = []
        total_revenue = fact_number("total_revenue", facts["total_revenue"])
        if total_revenue <= 0:
            raise ValueError("SOTP 总收入必须为正数")
        for segment in facts["segments"]:
            segment_id = segment["segment_id"]
            scenario = assumptions["segments"].get(segment_id)
            if scenario is None:
                raise ValueError(f"SOTP 分部缺少显式情景假设 {segment_id}")
            revenue = fact_number(f"segments.{segment_id}.revenue", segment["revenue"])
            income = fact_number(f"segments.{segment_id}.operating_income", segment["operating_income"])
            power = OfficialFilingMapper.parse_optional_financial_number(scenario["cost_pass_through_power"], "cost_pass_through_power")
            buffer = OfficialFilingMapper.parse_optional_financial_number(scenario["inventory_buffer_days"], "inventory_buffer_days")
            if power is None or buffer is None:
                raise ValueError("SOTP 情景假设缺失")
            segments.append(BusinessSegment(
                segment_id=segment_id, name_zh=segment["name_zh"], name_en=segment["name_en"],
                revenue=revenue, revenue_weight=revenue / total_revenue,
                operating_income=income, operating_margin=income / revenue if revenue else 0,
                cost_pass_through_power=power, inventory_buffer_days=buffer,
                relevant_keywords=scenario["relevant_keywords"],
            ))
        quote = raw["quote"]
        self._verify_source(quote["source"])
        price = OfficialFilingMapper.parse_optional_financial_number(quote["price"], "price")
        verified = QuoteFreshnessGateway.verify_quote(
            price, quote["currency"], quote["timestamp"], quote["market"], self.current_time_iso
        )
        if not verified.is_valid:
            raise ValueError(f"SOTP 行情被阻断 {verified.message}")
        profile = CompanySotpProfile(
            ticker=ticker.upper(), company_name=facts["company_name"], fiscal_year=facts["fiscal_year"],
            total_revenue=total_revenue,
            total_operating_income=fact_number("total_operating_income", facts["total_operating_income"]),
            effective_tax_rate=fact_number("effective_tax_rate", facts["effective_tax_rate"]),
            diluted_shares=fact_number("diluted_shares", facts["diluted_shares"]),
            current_share_price=price, segments=segments,
            unallocated_operating_income=fact_number("unallocated_operating_income", facts["unallocated_operating_income"]),
            source_refs={**evidence, "quote": quote["source"]}, assumption_id=assumptions["assumption_id"],
            assumption_rationale=assumptions["rationale"],
            assumption_status=assumptions["calibration_status"],
            quote_timestamp=quote["timestamp"], quote_session=verified.session_status,
            data_origin=raw["data_origin"],
            evidence_status="local_digest_verified_fact_review_required",
        )
        valid, message = profile.verify_balance_sheet_invariants()
        if not valid:
            raise ValueError(f"SOTP 平账校验失败 {ticker} {message}")
        return profile

    def analyze_event_on_company(
        self,
        ticker: str,
        event: StructuredEventSummary,
    ) -> EnterpriseEventImpactResult:
        """针对特定单家公司执行分部穿透与损益分析."""
        profile = self.get_company_sotp_profile(ticker)
        if not profile:
            raise ValueError(f"未找到标的 '{ticker}' 的已登记 SOTP 分部档案，请先补齐证据")

        return self.engine.analyze_company_impact(profile, event)

    def analyze_event_on_universe(
        self,
        event: StructuredEventSummary,
        target_tickers: Optional[List[str]] = None,
    ) -> List[EnterpriseEventImpactResult]:
        """对整个资产池或指定标的集合并发穿透此突发事件."""
        tickers = target_tickers or list(self.profiles.keys())
        results = []
        for t in tickers:
            profile = self.get_company_sotp_profile(t)
            if profile:
                res = self.engine.analyze_company_impact(profile, event)
                results.append(res)
        return results

    def analyze_stored_event_by_id(
        self,
        event_id: str,
        target_tickers: Optional[List[str]] = None,
    ) -> List[EnterpriseEventImpactResult]:
        """从 SQLite 数据库提取特定事件并执行全标的分部穿透."""
        events = self.db_mgr.query_events()
        matched = [e for e in events if e.get("event_id") == event_id]
        if not matched:
            raise KeyError(f"在 SQLite 数据库中未查询到 ID 为 '{event_id}' 的事件")

        raw_evt = matched[0]
        # 组装为 StructuredEventSummary (含完整信源分级、鉴真状态与密码学证据)
        summary = StructuredEventSummary(
            event_id=raw_evt["event_id"],
            timestamp=raw_evt["published_at"],
            category=raw_evt["category"],
            involved_entities=raw_evt["involved_entities"],
            micro_physical_impact=raw_evt["micro_physical_impact"],
            estimated_duration=raw_evt["estimated_duration"],
            affected_business_segments=raw_evt["affected_business_segments"],
            severity_level=raw_evt["severity_level"],
            requires_deep_analysis=bool(raw_evt["requires_deep_analysis"]),
            raw_title=raw_evt["title"],
            source_name=raw_evt["source_name"],
            credibility_tier=raw_evt.get("credibility_tier", "Tier3_Mainstream_Wire"),
            credibility_score=float(raw_evt.get("credibility_score", 0.8)),
            verification_status=raw_evt.get("verification_status", "Corroborated_Report"),
            verification_note=raw_evt.get("verification_note", ""),
            evidence_path=raw_evt.get("evidence_path"),
            evidence_sha256=raw_evt.get("evidence_sha256"),
            verified_at=raw_evt.get("verified_at"),
        )
        return self.analyze_event_on_universe(summary, target_tickers)

    def analyze_all_verified_major_events(
        self,
        target_tickers: Optional[List[str]] = None,
        only_confirmed_facts: bool = False,
    ) -> Dict[str, List[EnterpriseEventImpactResult]]:
        """全量扫描并穿透所有已就绪的重大事件 (P0/P1 或已核实事实)."""
        events = self.db_mgr.query_events()
        results_by_event: Dict[str, List[EnterpriseEventImpactResult]] = {}

        for evt in events:
            evt_id = evt["event_id"]
            is_major = evt.get("severity_level") in ("P0", "P1")
            is_confirmed = evt.get("verification_status") == "Confirmed_Fact"
            requires_deep = bool(evt.get("requires_deep_analysis", 1))

            if only_confirmed_facts and not is_confirmed:
                continue

            if is_major or is_confirmed or requires_deep:
                results_by_event[evt_id] = self.analyze_stored_event_by_id(evt_id, target_tickers)

        return results_by_event
