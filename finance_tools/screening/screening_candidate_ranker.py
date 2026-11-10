"""万家股票初筛优选排序与候选池输出引擎 (Screening Candidate Ranker).

遵循《AGENTS.md》2026-11-08 初筛硬约束与分级资产池架构:
1. 聚合 data/screening/results/ 下全部 150 个分块初筛结果 (14,892 家上市主体);
2. 提取并通过两级金字塔过滤:
   - Tier 0 / Tier 1: 核心枢轴就绪买点 (Stage_2_Pivot_Ready)，全票通过 4 大维度与 12 项硬指标;
   - Tier 2: 主升浪观察池 (Watchlist_Forming)，均线主升成立、等待形态进一步收缩;
3. 纯本地数学排序 (0-Token):
   - 按筹码抽干比 (dryup_ratio) 升序 (越地量越优先);
   - 按末端收敛幅度 (last_contraction_pct) 升序 (波动越极窄越优先);
   - 按相对 52 周高点回撤幅度升序 (越靠近历史高点越优先);
4. 输出规整 JSON 契约至 data/screening/qualified_candidates.json 与可视化榜单.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class QualifiedCandidate:
    """准入候选标的结构."""

    ticker: str
    market: str
    company_name: str
    cik_or_code: str
    decision_action: str
    latest_price: float
    pivot_price: float
    dryup_ratio: float
    last_contraction_pct: float
    vcp_code: str
    gain_from_52w_low_pct: float
    pullback_from_52w_high_pct: float
    business_rationale_zh: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ScreeningCandidateRanker:
    """全盘初筛候选池排序与聚合器."""

    def __init__(self, data_root: Optional[Path] = None):
        self.data_root = data_root or (PROJECT_ROOT / "data")
        self.screening_dir = self.data_root / "screening"
        self.results_dir = self.screening_dir / "results"
        self.qualified_file = self.screening_dir / "qualified_candidates.json"

    def aggregate_and_rank_candidates(self) -> Dict[str, Any]:
        """扫描所有已筛分块，聚合并排序 Stage_2_Pivot_Ready 与 Watchlist_Forming 标的."""
        if not self.results_dir.exists():
            return {
                "title": "全盘初筛准入优质候选池总账 (Qualified Screening Candidates)",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "source_result_chunks_count": 0,
                "total_qualified_count": 0,
                "tier0_pivot_ready_count": 0,
                "tier1_watchlist_count": 0,
                "pivot_ready_candidates": [],
                "watchlist_candidates": [],
            }

        pivot_ready_list: List[QualifiedCandidate] = []
        watchlist_list: List[QualifiedCandidate] = []
        processed_files = 0
        us_chunks_count = 0
        jp_chunks_count = 0

        for result_file in sorted(self.results_dir.glob("screened_*.json")):
            processed_files += 1
            fname = result_file.name
            if "us_" in fname:
                us_chunks_count += 1
            elif "jp_" in fname:
                jp_chunks_count += 1

            try:
                content = json.loads(result_file.read_text(encoding="utf-8"))
            except Exception:
                continue

            records = content.get("records", [])
            for r in records:
                action = r.get("sepa_qualification", {}).get("decision_action")
                if action not in ("Stage_2_Pivot_Ready", "Watchlist_Forming"):
                    continue

                p_ma = r.get("price_and_moving_averages", {})
                cycle = r.get("cycle_and_high_low_positions", {})
                vol = r.get("volume_and_supply_dryup", {})
                vcp = r.get("vcp_pattern_footprints", {})
                qual = r.get("sepa_qualification", {})

                seq = vcp.get("contraction_sequence", [])
                last_c = seq[-1] if seq else 15.0

                candidate = QualifiedCandidate(
                    ticker=r.get("ticker", "UNKNOWN"),
                    market=r.get("market", "US"),
                    company_name=r.get("company_name", ""),
                    cik_or_code=r.get("cik_or_code", ""),
                    decision_action=action,
                    latest_price=p_ma.get("latest_price", 0.0),
                    pivot_price=vcp.get("pivot_price", 0.0),
                    dryup_ratio=vol.get("dryup_ratio", 1.0),
                    last_contraction_pct=last_c,
                    vcp_code=vcp.get("vcp_code", ""),
                    gain_from_52w_low_pct=cycle.get("gain_from_52w_low_pct", 0.0),
                    pullback_from_52w_high_pct=cycle.get("pullback_from_52w_high_pct", 0.0),
                    business_rationale_zh=qual.get("business_rationale_zh", ""),
                )

                if action == "Stage_2_Pivot_Ready":
                    pivot_ready_list.append(candidate)
                else:
                    watchlist_list.append(candidate)

        # 排序规则：地量抽干度最强（dryup_ratio 小）、形态收敛最紧（last_contraction 小）、距高点回撤最窄
        pivot_ready_list.sort(
            key=lambda c: (c.dryup_ratio, c.last_contraction_pct, c.pullback_from_52w_high_pct)
        )
        watchlist_list.sort(
            key=lambda c: (c.dryup_ratio, c.last_contraction_pct, c.pullback_from_52w_high_pct)
        )

        output_data = {
            "title": "全盘初筛准入优质候选池总账 (Qualified Screening Candidates)",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "source_result_chunks_count": processed_files,
            "market_chunks_breakdown": {
                "US": us_chunks_count,
                "JP": jp_chunks_count,
            },
            "total_qualified_count": len(pivot_ready_list) + len(watchlist_list),
            "tier0_pivot_ready_count": len(pivot_ready_list),
            "tier1_watchlist_count": len(watchlist_list),
            "pivot_ready_candidates": [c.to_dict() for c in pivot_ready_list],
            "watchlist_candidates": [c.to_dict() for c in watchlist_list],
        }

        self.qualified_file.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return output_data
