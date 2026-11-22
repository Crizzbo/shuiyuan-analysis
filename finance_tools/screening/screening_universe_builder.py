"""万家股票初筛资产池构建与价量形态指标计算引擎 (Screening Universe Builder).

遵循《CLAUDE.md》工程哲学与《AGENTS.md》2026-11-08 初筛规范:
1. 覆盖全量资产池：美股 10,445 家 (SEC EDGAR) + 日股 4,447 家 (东证全市场)，共计 14,892+ 家上市主体;
2. 严格遵循 0-Token 纯本地数学计算，严禁向大模型注入原始财报，实现全盘秒级初筛;
3. 严格契约化实现 4 大核心类别与 12 项硬指标:
   ① 价格与均线系统 (现价, MA50, MA150, MA200, 20天前MA200);
   ② 周期位置与高低点 (52周高点, 52周低点, 反弹>=30%, 回撤<=25%);
   ③ 成交量与筹码抽干 (今日成交量, 50天均量, 整理期最低量, 抽干比<=50%);
   ④ 形态收敛足迹 VCP (基底周数, 回调收缩序列, 枢轴突破买点, 足迹代码);
4. 先打样再批量 (Sampling POC First): 建立 Tier 0/1 核心金标样例库与全盘分块索引 (Chunking).
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from financial_core.engines.multi_asset_screening_engine import (
    AssetCategory,
    AssetClassClassifier,
    MultiAssetScreeningDecision,
    MultiAssetScreeningEngine,
    MultiAssetScreeningInput,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class PriceAndMovingAverages:
    """① 价格与均线系统."""

    latest_price: float
    ma50: float
    ma150: float
    ma200: float
    ma200_20d_ago: float
    is_price_above_all_mas: bool
    is_ma200_trending_up: bool


@dataclass
class CycleAndHighLowPositions:
    """② 周期位置与高低点."""

    high_52w: float
    low_52w: float
    gain_from_52w_low_pct: float
    pullback_from_52w_high_pct: float
    meets_cycle_thresholds: bool


@dataclass
class VolumeAndSupplyDryup:
    """③ 成交量与筹码抽干."""

    volume_today: float
    volume_50d_avg: float
    volume_min_consolidation: float
    dryup_ratio: float
    is_volume_dryup_confirmed: bool


@dataclass
class VcpPatternFootprints:
    """④ 形态收敛足迹 VCP."""

    base_duration_weeks: int
    contraction_sequence: List[float]
    pivot_price: float
    vcp_code: str
    vcp_stage: str


@dataclass
class SepaQualification:
    """初筛准入综合判定."""

    stage_2_markup_pass: bool
    vcp_ready_pass: bool
    overall_preliminary_pass: bool
    decision_action: str
    business_rationale_zh: str


@dataclass
class StockScreeningRecord:
    """单一标的全息初筛指标记录."""

    ticker: str
    market: str
    company_name: str
    cik_or_code: str
    as_of_date: str
    price_and_moving_averages: PriceAndMovingAverages
    cycle_and_high_low_positions: CycleAndHighLowPositions
    volume_and_supply_dryup: VolumeAndSupplyDryup
    vcp_pattern_footprints: VcpPatternFootprints
    sepa_qualification: SepaQualification
    asset_category: str = "Growth_Equity"
    multi_asset_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """序列化为符合 schemas/stock_screening_metrics.schema.json 的字典."""
        res = {
            "ticker": self.ticker,
            "market": self.market,
            "company_name": self.company_name,
            "cik_or_code": self.cik_or_code,
            "as_of_date": self.as_of_date,
            "price_and_moving_averages": asdict(self.price_and_moving_averages),
            "cycle_and_high_low_positions": asdict(self.cycle_and_high_low_positions),
            "volume_and_supply_dryup": asdict(self.volume_and_supply_dryup),
            "vcp_pattern_footprints": asdict(self.vcp_pattern_footprints),
            "sepa_qualification": asdict(self.sepa_qualification),
            "asset_category": self.asset_category,
        }
        if self.multi_asset_action:
            res["multi_asset_action"] = self.multi_asset_action
        return res


class ScreeningUniverseBuilder:
    """全盘万家企业初筛资产池与价量指标构建器."""

    def __init__(self, data_root: Optional[Path] = None):
        self.data_root = data_root or (PROJECT_ROOT / "data")
        self.universe_dir = self.data_root / "universe"
        self.screening_dir = self.data_root / "screening"
        self.us_chunk_dir = self.screening_dir / "us_10k"
        self.jp_chunk_dir = self.screening_dir / "jp_4k"
        self.samples_dir = self.screening_dir / "samples"
        self.multi_asset_engine = MultiAssetScreeningEngine()

    def ensure_directories(self) -> None:
        """创建初筛专属存储目录体系."""
        self.screening_dir.mkdir(parents=True, exist_ok=True)
        self.us_chunk_dir.mkdir(parents=True, exist_ok=True)
        self.jp_chunk_dir.mkdir(parents=True, exist_ok=True)
        self.samples_dir.mkdir(parents=True, exist_ok=True)

    def load_us_universe_raw(self) -> List[Dict[str, Any]]:
        """从 sec_company_tickers.json 加载美股 10,445 家官方备案企业索引."""
        sec_file = self.universe_dir / "sec_company_tickers.json"
        if not sec_file.exists():
            return []
        data = json.loads(sec_file.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            # SEC 格式为 {"0": {"cik_str": ..., "ticker": ..., "title": ...}, ...}
            return list(data.values())
        return data

    def load_jp_universe_raw(self) -> List[Dict[str, Any]]:
        """从 jpx_company_tickers.json 加载日股 4,447 家东证官方挂牌企业索引."""
        jpx_file = self.universe_dir / "jpx_company_tickers.json"
        if not jpx_file.exists():
            return []
        data = json.loads(jpx_file.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return list(data.values())
        return []

    def compute_screening_metrics(
        self,
        ticker: str,
        market: str,
        company_name: str,
        cik_or_code: str,
        as_of_date: str,
        latest_price: float,
        ma50: float,
        ma150: float,
        ma200: float,
        ma200_20d_ago: float,
        high_52w: float,
        low_52w: float,
        volume_today: float,
        volume_50d_avg: float,
        volume_min_consolidation: float,
        base_duration_weeks: int = 8,
        contraction_sequence: Optional[List[float]] = None,
        pivot_price: Optional[float] = None,
        asset_category: Optional[Union[AssetCategory, str]] = None,
        ma20: Optional[float] = None,
        real_rate_10y_tips: Optional[float] = None,
        dividend_yield_pct: Optional[float] = None,
        industry_id: str = "",
    ) -> StockScreeningRecord:
        """执行 0-Token 纯本地数学计算，生成多资产四维初筛指标契约."""
        if contraction_sequence is None:
            contraction_sequence = [24.0, 12.0, 5.0, 2.0]
        if pivot_price is None:
            pivot_price = round(latest_price * 1.02, 2)

        # 委托多资产自适应选股路由引擎进行定界与判定
        inp = MultiAssetScreeningInput(
            ticker=ticker,
            market=market,
            company_name=company_name,
            latest_price=latest_price,
            ma20=ma20,
            ma50=ma50,
            ma150=ma150,
            ma200=ma200,
            ma200_20d_ago=ma200_20d_ago,
            high_52w=high_52w,
            low_52w=low_52w,
            volume_today=volume_today,
            volume_50d_avg=volume_50d_avg,
            volume_min_consolidation=volume_min_consolidation,
            base_duration_weeks=base_duration_weeks,
            contraction_sequence=contraction_sequence,
            pivot_price=pivot_price,
            asset_category=asset_category,
            industry_id=industry_id,
            real_rate_10y_tips=real_rate_10y_tips,
            dividend_yield_pct=dividend_yield_pct,
        )
        decision = self.multi_asset_engine.screen(inp)

        # ① 价格与均线系统逻辑断言 (多资产自适应对齐)
        is_price_above = decision.trend_alignment_pass
        is_ma200_up = (ma200 > ma200_20d_ago) if decision.asset_category == AssetCategory.GROWTH_EQUITY.value else (ma200 >= ma200_20d_ago * 0.995)

        price_mas = PriceAndMovingAverages(
            latest_price=round(latest_price, 2),
            ma50=round(ma50, 2),
            ma150=round(ma150, 2),
            ma200=round(ma200, 2),
            ma200_20d_ago=round(ma200_20d_ago, 2),
            is_price_above_all_mas=is_price_above,
            is_ma200_trending_up=is_ma200_up,
        )

        # ② 周期位置与高低点
        gain_from_low = round(((latest_price - low_52w) / max(0.01, low_52w)) * 100.0, 2)
        pullback_from_high = round(((high_52w - latest_price) / max(0.01, high_52w)) * 100.0, 2)
        meets_cycle = decision.channel_or_cycle_pass

        cycle_pos = CycleAndHighLowPositions(
            high_52w=round(high_52w, 2),
            low_52w=round(low_52w, 2),
            gain_from_52w_low_pct=gain_from_low,
            pullback_from_52w_high_pct=pullback_from_high,
            meets_cycle_thresholds=meets_cycle,
        )

        # ③ 成交量与筹码抽干
        dryup_ratio = round(volume_min_consolidation / max(1.0, volume_50d_avg), 4)
        is_dryup = decision.risk_or_volatility_pass

        vol_dryup = VolumeAndSupplyDryup(
            volume_today=volume_today,
            volume_50d_avg=round(volume_50d_avg, 1),
            volume_min_consolidation=round(volume_min_consolidation, 1),
            dryup_ratio=dryup_ratio,
            is_volume_dryup_confirmed=is_dryup,
        )

        # ④ 形态收敛足迹 VCP (兼顾多资产足迹语义)
        t_count = len(contraction_sequence)
        last_contraction = contraction_sequence[-1] if contraction_sequence else 10.0
        vcp_code = f"{base_duration_weeks}W {int(contraction_sequence[0])}/{int(last_contraction)} {t_count}T"

        if decision.pivot_ready_pass:
            vcp_stage = "Tight_Pivot_Ready"
        elif decision.is_watchlist:
            vcp_stage = "Contracting"
        elif decision.channel_or_cycle_pass:
            vcp_stage = "Loose_Shaping"
        else:
            vcp_stage = "No_Contraction"

        vcp_footprints = VcpPatternFootprints(
            base_duration_weeks=base_duration_weeks,
            contraction_sequence=contraction_sequence,
            pivot_price=round(pivot_price, 2),
            vcp_code=vcp_code,
            vcp_stage=vcp_stage,
        )

        # 综合准入判定 (满足 JSON Schema: Stage_2_Pivot_Ready / Watchlist_Forming / Trend_Disqualified)
        action = "Stage_2_Pivot_Ready" if decision.is_qualified else ("Watchlist_Forming" if decision.is_watchlist else "Trend_Disqualified")

        qualification = SepaQualification(
            stage_2_markup_pass=decision.trend_alignment_pass and decision.channel_or_cycle_pass,
            vcp_ready_pass=decision.pivot_ready_pass,
            overall_preliminary_pass=decision.is_qualified,
            decision_action=action,
            business_rationale_zh=decision.business_rationale_zh,
        )

        return StockScreeningRecord(
            ticker=ticker,
            market=market,
            company_name=company_name,
            cik_or_code=cik_or_code,
            as_of_date=as_of_date,
            price_and_moving_averages=price_mas,
            cycle_and_high_low_positions=cycle_pos,
            volume_and_supply_dryup=vol_dryup,
            vcp_pattern_footprints=vcp_footprints,
            sepa_qualification=qualification,
            asset_category=decision.asset_category,
            multi_asset_action=decision.decision_action,
        )

    def generate_golden_samples(self) -> List[StockScreeningRecord]:
        """先打样：针对核心重点标的生成高精度打样黄金基准 (Golden POC Samples)."""
        as_of = "2026-11-07"
        samples = [
            # 1. NVDA (主升浪 + 极窄收敛就绪打样)
            self.compute_screening_metrics(
                ticker="NVDA",
                market="US",
                company_name="NVIDIA Corporation",
                cik_or_code="0001045810",
                as_of_date=as_of,
                latest_price=147.60,
                ma50=135.20,
                ma150=124.50,
                ma200=116.80,
                ma200_20d_ago=112.40,
                high_52w=152.89,
                low_52w=45.60,
                volume_today=48500000,
                volume_50d_avg=52000000,
                volume_min_consolidation=21000000,
                base_duration_weeks=8,
                contraction_sequence=[26.0, 13.0, 5.2, 2.1],
                pivot_price=149.50,
            ),
            # 2. TSM (台积电 · 稳健主升成长打样)
            self.compute_screening_metrics(
                ticker="TSM",
                market="US",
                company_name="Taiwan Semiconductor Manufacturing Co Ltd",
                cik_or_code="0001046179",
                as_of_date=as_of,
                latest_price=190.40,
                ma50=178.60,
                ma150=162.30,
                ma200=148.90,
                ma200_20d_ago=143.10,
                high_52w=205.84,
                low_52w=85.20,
                volume_today=12400000,
                volume_50d_avg=14800000,
                volume_min_consolidation=6500000,
                base_duration_weeks=7,
                contraction_sequence=[22.0, 11.0, 4.8, 1.9],
                pivot_price=194.00,
            ),
            # 3. 8035 (东电 · 日股半导体巨头打样)
            self.compute_screening_metrics(
                ticker="8035",
                market="JP",
                company_name="Tokyo Electron Limited (東京エレクトロン)",
                cik_or_code="8035",
                as_of_date=as_of,
                latest_price=24800.0,
                ma50=23200.0,
                ma150=21800.0,
                ma200=20400.0,
                ma200_20d_ago=19800.0,
                high_52w=26500.0,
                low_52w=13200.0,
                volume_today=2800000,
                volume_50d_avg=3200000,
                volume_min_consolidation=1350000,
                base_duration_weeks=9,
                contraction_sequence=[28.0, 14.0, 6.5, 2.4],
                pivot_price=25200.0,
            ),
            # 4. 6857 (爱德万测试 · 日股测试设备龙头)
            self.compute_screening_metrics(
                ticker="6857",
                market="JP",
                company_name="Advantest Corporation (アドバンテスト)",
                cik_or_code="6857",
                as_of_date=as_of,
                latest_price=8250.0,
                ma50=7600.0,
                ma150=6900.0,
                ma200=6200.0,
                ma200_20d_ago=5900.0,
                high_52w=8800.0,
                low_52w=3900.0,
                volume_today=4500000,
                volume_50d_avg=5100000,
                volume_min_consolidation=2100000,
                base_duration_weeks=6,
                contraction_sequence=[25.0, 12.0, 5.0, 1.8],
                pivot_price=8400.0,
            ),
            # 5. INTC / 负面反例打样 (趋势一票否决 · 年线下行破位股)
            self.compute_screening_metrics(
                ticker="INTC",
                market="US",
                company_name="Intel Corporation",
                cik_or_code="0000050863",
                as_of_date=as_of,
                latest_price=23.50,
                ma50=22.80,
                ma150=26.40,
                ma200=31.20,
                ma200_20d_ago=32.80,
                high_52w=51.28,
                low_52w=18.51,
                volume_today=45000000,
                volume_50d_avg=42000000,
                volume_min_consolidation=28000000,
                base_duration_weeks=12,
                contraction_sequence=[45.0, 32.0],
                pivot_price=28.00,
            ),
            # 6. GLD (SPDR Gold Shares · 黄金贵金属宏观中枢就绪打样)
            self.compute_screening_metrics(
                ticker="GLD",
                market="US",
                company_name="SPDR Gold Trust (Physical Gold ETF)",
                cik_or_code="0001222333",
                as_of_date=as_of,
                latest_price=242.0,
                ma50=238.0,
                ma150=226.0,
                ma200=218.0,
                ma200_20d_ago=215.0,
                high_52w=252.0,
                low_52w=195.0,
                volume_today=8500000,
                volume_50d_avg=8200000,
                volume_min_consolidation=4100000,
                base_duration_weeks=8,
                contraction_sequence=[10.0, 5.0, 2.5],
                pivot_price=245.0,
                real_rate_10y_tips=1.85,
            ),
            # 7. SPY (SPDR S&P 500 ETF Trust · 核心大盘指数顺势通道打样)
            self.compute_screening_metrics(
                ticker="SPY",
                market="US",
                company_name="SPDR S&P 500 ETF Trust",
                cik_or_code="0000884394",
                as_of_date=as_of,
                latest_price=592.0,
                ma50=578.0,
                ma150=555.0,
                ma200=532.0,
                ma200_20d_ago=528.0,
                high_52w=602.0,
                low_52w=468.0,
                volume_today=45000000,
                volume_50d_avg=48000000,
                volume_min_consolidation=22000000,
                base_duration_weeks=6,
                contraction_sequence=[8.0, 4.0, 1.8],
                pivot_price=596.0,
            ),
            # 8. SCHD (Schwab U.S. Dividend Equity ETF · 高股息护城河防御打样)
            self.compute_screening_metrics(
                ticker="SCHD",
                market="US",
                company_name="Schwab U.S. Dividend Equity ETF",
                cik_or_code="0001509378",
                as_of_date=as_of,
                latest_price=84.20,
                ma50=82.50,
                ma150=80.80,
                ma200=79.20,
                ma200_20d_ago=78.90,
                high_52w=85.50,
                low_52w=71.0,
                volume_today=3200000,
                volume_50d_avg=3500000,
                volume_min_consolidation=1800000,
                base_duration_weeks=8,
                contraction_sequence=[6.0, 3.0, 1.2],
                pivot_price=84.80,
                dividend_yield_pct=3.45,
            ),
            # 9. NEM (Newmont Corp · 金矿龙头股打样)
            self.compute_screening_metrics(
                ticker="NEM",
                market="US",
                company_name="Newmont Corporation (Gold Mining)",
                cik_or_code="0001164727",
                as_of_date=as_of,
                latest_price=48.50,
                ma50=46.20,
                ma150=42.80,
                ma200=39.50,
                ma200_20d_ago=38.60,
                high_52w=51.0,
                low_52w=29.40,
                volume_today=9500000,
                volume_50d_avg=10200000,
                volume_min_consolidation=4600000,
                base_duration_weeks=7,
                contraction_sequence=[12.0, 6.0, 2.8],
                pivot_price=49.50,
                industry_id="gold_mining",
            ),
        ]
        return samples

    def build_and_save_samples(self) -> Path:
        """保存黄金样本集至 data/screening/samples/."""
        self.ensure_directories()
        samples = self.generate_golden_samples()
        output_file = self.samples_dir / "golden_screening_samples.json"
        data = {
            "title": "米奈尔维尼 SEPA 初筛黄金打样集 (Golden POC Samples)",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "total_samples": len(samples),
            "samples": [s.to_dict() for s in samples],
        }
        output_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_file

    def build_universe_manifest_and_chunks(
        self, chunk_size: int = 100
    ) -> Dict[str, Any]:
        """全量建立美股 10,445 家与日股 4,447 家初筛索引与分块底账."""
        self.ensure_directories()

        us_raw = self.load_us_universe_raw()
        jp_raw = self.load_jp_universe_raw()

        # 美股分块落盘
        us_chunk_files = []
        for i in range(0, len(us_raw), chunk_size):
            chunk_items = us_raw[i : i + chunk_size]
            chunk_idx = (i // chunk_size) + 1
            chunk_file = self.us_chunk_dir / f"us_screening_chunk_{chunk_idx:03d}.json"
            chunk_data = {
                "market": "US",
                "chunk_index": chunk_idx,
                "total_items": len(chunk_items),
                "items": chunk_items,
            }
            chunk_file.write_text(json.dumps(chunk_data, ensure_ascii=False, indent=2), encoding="utf-8")
            us_chunk_files.append(chunk_file.name)

        # 日股分块落盘
        jp_chunk_files = []
        for i in range(0, len(jp_raw), chunk_size):
            chunk_items = jp_raw[i : i + chunk_size]
            chunk_idx = (i // chunk_size) + 1
            chunk_file = self.jp_chunk_dir / f"jp_screening_chunk_{chunk_idx:03d}.json"
            chunk_data = {
                "market": "JP",
                "chunk_index": chunk_idx,
                "total_items": len(chunk_items),
                "items": chunk_items,
            }
            chunk_file.write_text(json.dumps(chunk_data, ensure_ascii=False, indent=2), encoding="utf-8")
            jp_chunk_files.append(chunk_file.name)

        # 生成主清单 manifest.json
        manifest_data = {
            "title": "全市场数千家上市主体初筛资产池总账 (Full 10K+ Screening Universe Manifest)",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "total_companies": len(us_raw) + len(jp_raw),
            "market_summary": {
                "US_SEC_EDGAR": {
                    "total_count": len(us_raw),
                    "chunk_size": chunk_size,
                    "total_chunks": len(us_chunk_files),
                    "chunk_dir": "data/screening/us_10k",
                },
                "JP_TOKYO_JPX": {
                    "total_count": len(jp_raw),
                    "chunk_size": chunk_size,
                    "total_chunks": len(jp_chunk_files),
                    "chunk_dir": "data/screening/jp_4k",
                },
            },
            "four_screening_categories": [
                "① 价格与均线系统 (现价, MA50, MA150, MA200, 20天前MA200)",
                "② 周期位置与高低点 (52周最高价, 52周最低价, 底部反弹>=30%, 顶部回撤<=25%)",
                "③ 成交量与筹码抽干 (今日成交量, 50天日均成交量, 地量抽干比<=50%)",
                "④ 形态收敛足迹 VCP (基底周数, 历次回调收敛序列, 枢轴阻力买点)",
            ],
            "zero_token_contract": "纯本地物理 Python 数学运算，严禁向大模型注入原始财报，实现全盘 0-Token 秒级初筛",
            "samples_path": "data/screening/samples/golden_screening_samples.json",
        }

        manifest_file = self.screening_dir / "screening_manifest.json"
        manifest_file.write_text(
            json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return manifest_data
