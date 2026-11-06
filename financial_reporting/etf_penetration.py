"""全球核心指数与主题 ETF 穿透分析引擎 (ETF Penetration & Overlap Analysis Engine)

功能模块：
1. 【前十大成分股穿透与重叠度矩阵 (Holdings Overlap Matrix)】：
   - 计算成对 ETF 之间的权重重合度 (Weighted Overlap %) 与 Jaccard 相似系数；
   - 警示投资者同时持有宽基与科技行业 ETF 时的底层股票过度集中风险 (如苹果/微软/英伟达三重重叠)。
2. 【集中度与多样化评分 (Concentration & Diversity Index)】：
   - 计算前十大集中度 CR10 与赫芬达尔-赫希曼指数 (HHI)；
3. 【多因子风格暴露雷达 (Multi-Factor Exposure Radar)】：
   - 估算成长 (Growth)、价值 (Value)、盈利质量 (Quality)、动量 (Momentum)、红利 (Dividend) 与低波动 (Low Vol) 六维因子得分；
4. 【费率与跟踪损耗摩擦测算 (Expense Ratio & Tracking Drag)】：
   - 测算 1 年 / 3 年 / 5 年在复利环境下的费率损耗对净值增长的侵蚀。
"""

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional, Tuple, Set

from financial_core.engines.cross_asset_engine import (
    CrossAssetValuationEngine,
    ETFOverlapResult,
    ETFPenetrationFact,
)


@dataclass(frozen=True)
class ETFProfile:
    """核心 ETF 资产静态事实底账。"""
    ticker: str
    name_zh: str
    asset_class: str             # "Equity", "Fixed Income", "Commodity"
    category: str                # "Broad Market", "Technology", "Semiconductor", "Dividend", "Treasury"
    expense_ratio: float         # 费率 (如 0.0009 代表 0.09%)
    aum_billion_usd: float       # 管理资产规模 (亿美元)
    top_holdings: Dict[str, float] # { "NVDA": 0.085, "AAPL": 0.072, ... }
    factor_scores: Dict[str, float] # { "growth": 85, "value": 30, "quality": 90, ... }


# 经典核心 ETF 资产底账注册表
STANDARD_ETF_REGISTRY: Dict[str, ETFProfile] = {
    "SPY": ETFProfile(
        ticker="SPY",
        name_zh="SPDR 标普 500 指数 ETF",
        asset_class="Equity",
        category="Broad Market",
        expense_ratio=0.0009,
        aum_billion_usd=560.0,
        top_holdings={
            "MSFT": 0.071,
            "AAPL": 0.069,
            "NVDA": 0.062,
            "AMZN": 0.038,
            "META": 0.025,
            "GOOGL": 0.021,
            "BRK.B": 0.018,
            "GOOG": 0.017,
            "LLY": 0.016,
            "AVGO": 0.015,
        },
        factor_scores={
            "growth": 65.0,
            "value": 50.0,
            "quality": 85.0,
            "momentum": 70.0,
            "dividend": 45.0,
            "low_vol": 60.0,
        },
    ),
    "QQQ": ETFProfile(
        ticker="QQQ",
        name_zh="Invesco 纳斯达克 100 指数 ETF",
        asset_class="Equity",
        category="Technology",
        expense_ratio=0.0020,
        aum_billion_usd=280.0,
        top_holdings={
            "AAPL": 0.088,
            "MSFT": 0.082,
            "NVDA": 0.079,
            "AMZN": 0.052,
            "META": 0.048,
            "AVGO": 0.045,
            "GOOGL": 0.028,
            "GOOG": 0.026,
            "TSLA": 0.025,
            "COST": 0.024,
        },
        factor_scores={
            "growth": 92.0,
            "value": 25.0,
            "quality": 95.0,
            "momentum": 88.0,
            "dividend": 20.0,
            "low_vol": 40.0,
        },
    ),
    "SMH": ETFProfile(
        ticker="SMH",
        name_zh="VanEck 全球半导体指数 ETF",
        asset_class="Equity",
        category="Semiconductor",
        expense_ratio=0.0035,
        aum_billion_usd=23.0,
        top_holdings={
            "NVDA": 0.205,
            "TSM": 0.128,
            "AVGO": 0.082,
            "QCOM": 0.051,
            "AMD": 0.048,
            "TXN": 0.045,
            "AMAT": 0.042,
            "ASML": 0.040,
            "MU": 0.038,
            "LRCX": 0.035,
        },
        factor_scores={
            "growth": 98.0,
            "value": 15.0,
            "quality": 92.0,
            "momentum": 95.0,
            "dividend": 15.0,
            "low_vol": 25.0,
        },
    ),
    "XLK": ETFProfile(
        ticker="XLK",
        name_zh="科技精选行业 SPDR 基金",
        asset_class="Equity",
        category="Technology",
        expense_ratio=0.0009,
        aum_billion_usd=72.0,
        top_holdings={
            "MSFT": 0.215,
            "NVDA": 0.198,
            "AAPL": 0.048,
            "AVGO": 0.045,
            "CRM": 0.032,
            "CSCO": 0.030,
            "ACN": 0.028,
            "ADBE": 0.025,
            "AMD": 0.024,
            "QCOM": 0.022,
        },
        factor_scores={
            "growth": 95.0,
            "value": 20.0,
            "quality": 96.0,
            "momentum": 90.0,
            "dividend": 22.0,
            "low_vol": 35.0,
        },
    ),
    "SCHD": ETFProfile(
        ticker="SCHD",
        name_zh="嘉信美国高股息股票 ETF",
        asset_class="Equity",
        category="Dividend",
        expense_ratio=0.0006,
        aum_billion_usd=62.0,
        top_holdings={
            "CSCO": 0.045,
            "TXN": 0.042,
            "PFE": 0.040,
            "CVX": 0.039,
            "HD": 0.038,
            "AMGN": 0.037,
            "ABBV": 0.036,
            "MRK": 0.035,
            "PEP": 0.034,
            "KO": 0.033,
        },
        factor_scores={
            "growth": 35.0,
            "value": 85.0,
            "quality": 80.0,
            "momentum": 45.0,
            "dividend": 95.0,
            "low_vol": 80.0,
        },
    ),
    "TLT": ETFProfile(
        ticker="TLT",
        name_zh="iShares 20年期以上美国国债 ETF",
        asset_class="Fixed Income",
        category="Treasury",
        expense_ratio=0.0015,
        aum_billion_usd=55.0,
        top_holdings={
            "US_TREASURY_30Y": 0.45,
            "US_TREASURY_25Y": 0.35,
            "US_TREASURY_20Y": 0.20,
        },
        factor_scores={
            "growth": 10.0,
            "value": 60.0,
            "quality": 99.0,
            "momentum": 30.0,
            "dividend": 88.0,
            "low_vol": 50.0,
        },
    ),
    "IWM": ETFProfile(
        ticker="IWM",
        name_zh="iShares 罗素 2000 小盘股 ETF",
        asset_class="Equity",
        category="Small Cap",
        expense_ratio=0.0019,
        aum_billion_usd=68.5,
        top_holdings={
            "FTNT": 0.0055,
            "SAIA": 0.0048,
            "DECK": 0.0045,
            "CROX": 0.0042,
            "LNTH": 0.0039,
            "MEDP": 0.0037,
            "POWI": 0.0035,
            "RAMP": 0.0034,
            "SFM": 0.0032,
            "EXPO": 0.0030,
        },
        factor_scores={
            "growth": 55.0,
            "value": 65.0,
            "quality": 48.0,
            "momentum": 52.0,
            "dividend": 32.0,
            "low_vol": 35.0,
        },
    ),
    "XLE": ETFProfile(
        ticker="XLE",
        name_zh="能源精选行业 SPDR 基金",
        asset_class="Equity",
        category="Energy",
        expense_ratio=0.0009,
        aum_billion_usd=38.0,
        top_holdings={
            "XOM": 0.228,
            "CVX": 0.162,
            "EOG": 0.048,
            "COP": 0.045,
            "SLB": 0.042,
            "MPC": 0.038,
            "PSX": 0.035,
            "VLO": 0.032,
            "WMB": 0.030,
            "OXY": 0.028,
        },
        factor_scores={
            "growth": 40.0,
            "value": 90.0,
            "quality": 75.0,
            "momentum": 62.0,
            "dividend": 85.0,
            "low_vol": 55.0,
        },
    ),
    "XBI": ETFProfile(
        ticker="XBI",
        name_zh="SPDR 标普生物科技 ETF",
        asset_class="Equity",
        category="Biotechnology",
        expense_ratio=0.0035,
        aum_billion_usd=7.8,
        top_holdings={
            "ALNY": 0.025,
            "INCY": 0.023,
            "VRTX": 0.021,
            "BIIB": 0.020,
            "MRNA": 0.019,
            "REGN": 0.018,
            "GILD": 0.017,
            "EXEL": 0.016,
            "BMRN": 0.015,
            "ARWR": 0.015,
        },
        factor_scores={
            "growth": 95.0,
            "value": 15.0,
            "quality": 42.0,
            "momentum": 72.0,
            "dividend": 5.0,
            "low_vol": 20.0,
        },
    ),
    "VIG": ETFProfile(
        ticker="VIG",
        name_zh="先锋股息增值 ETF",
        asset_class="Equity",
        category="Dividend",
        expense_ratio=0.0006,
        aum_billion_usd=85.0,
        top_holdings={
            "MSFT": 0.052,
            "AAPL": 0.045,
            "JNJ": 0.032,
            "JPM": 0.031,
            "PG": 0.029,
            "AVGO": 0.028,
            "XOM": 0.026,
            "HD": 0.025,
            "UNH": 0.024,
            "CVX": 0.022,
        },
        factor_scores={
            "growth": 50.0,
            "value": 75.0,
            "quality": 92.0,
            "momentum": 55.0,
            "dividend": 88.0,
            "low_vol": 82.0,
        },
    ),
    "IEF": ETFProfile(
        ticker="IEF",
        name_zh="iShares 7-10年期美国国债 ETF",
        asset_class="Fixed Income",
        category="Treasury",
        expense_ratio=0.0015,
        aum_billion_usd=31.0,
        top_holdings={
            "US_TREASURY_10Y": 0.55,
            "US_TREASURY_7Y": 0.45,
        },
        factor_scores={
            "growth": 15.0,
            "value": 55.0,
            "quality": 99.0,
            "momentum": 35.0,
            "dividend": 82.0,
            "low_vol": 65.0,
        },
    ),
}


class ETFPenetrationEngine:
    """ETF 穿透重叠度与多因子透视引擎。"""

    @classmethod
    def calculate_overlap_between_two_etfs(
        cls,
        etf_a: ETFProfile,
        etf_b: ETFProfile,
    ) -> Dict[str, Any]:
        """计算两只 ETF 之间的持仓重叠度 (Weighted Overlap)，底层委托至核心量化引擎。"""
        core_res = CrossAssetValuationEngine.compute_etf_overlap(
            holdings_a=etf_a.top_holdings,
            holdings_b=etf_b.top_holdings,
            ticker_a=etf_a.ticker,
            ticker_b=etf_b.ticker,
        )

        overlap_holdings = {
            sym: {
                "weight_in_a": item[0],
                "weight_in_b": item[1],
                "common_overlap_weight": item[2],
            }
            for sym, item in core_res.overlap_weights.items()
        }

        return {
            "etf_a": core_res.etf_a,
            "etf_b": core_res.etf_b,
            "weighted_overlap_pct": core_res.weighted_overlap_pct,
            "jaccard_symbol_similarity_pct": core_res.jaccard_similarity_pct,
            "common_holdings_count": core_res.common_holdings_count,
            "overlap_details": overlap_holdings,
            "portfolio_diversification_verdict": (
                "【重合度过高警报】二者持仓存在大幅重合，组合同时持有将造成个股敞口严重共振过度暴露！"
                if core_res.is_high_overlap
                else "【良好分散互补】持仓重叠适中，可提供稳健的风格与行业多元化配置。"
            ),
        }

    @classmethod
    def analyze_etf_dossier(cls, ticker: str) -> Dict[str, Any]:
        """生成单个 ETF 的全景穿透档案模型，底层指标委托至核心量化引擎。"""
        if ticker not in STANDARD_ETF_REGISTRY:
            raise ValueError(f"未登记的 ETF 代码: {ticker}，支持标的: {list(STANDARD_ETF_REGISTRY.keys())}")
        etf = STANDARD_ETF_REGISTRY[ticker]

        core_fact = CrossAssetValuationEngine.compute_etf_penetration(
            ticker=etf.ticker,
            expense_ratio=etf.expense_ratio,
            aum_billion_usd=etf.aum_billion_usd,
            top_holdings=etf.top_holdings,
            factor_scores=etf.factor_scores,
            capital_baseline=100000.0,
        )

        # 与其他核心 ETF 的横向重合度扫描
        overlaps = []
        for other_tk, other_etf in STANDARD_ETF_REGISTRY.items():
            if other_tk != ticker and etf.asset_class == other_etf.asset_class:
                ol = cls.calculate_overlap_between_two_etfs(etf, other_etf)
                overlaps.append({
                    "target_etf": other_tk,
                    "target_name_zh": other_etf.name_zh,
                    "overlap_pct": ol["weighted_overlap_pct"],
                    "verdict": ol["portfolio_diversification_verdict"],
                })

        return {
            "ticker": etf.ticker,
            "name_zh": etf.name_zh,
            "category": etf.category,
            "asset_class": etf.asset_class,
            "expense_ratio_display": f"{etf.expense_ratio * 100:.3f}%",
            "aum_display": f"${etf.aum_billion_usd:.1f} 亿美元",
            "concentration": {
                "top_10_weight_pct": round(core_fact.cr10_pct, 2),
                "hhi_index": round(core_fact.hhi_index, 1),
                "concentration_rating": "极度集中 (头部巨头主导)" if core_fact.is_concentrated else "适度分散 (稳健配置)",
            },
            "top_holdings": [
                {"symbol": k, "weight_pct": f"{v * 100:.2f}%"}
                for k, v in sorted(etf.top_holdings.items(), key=lambda x: x[1], reverse=True)
            ],
            "factor_scores": etf.factor_scores,
            "fee_drag_simulation": {
                "assumed_capital": "$100,000",
                "drag_1_year": f"${core_fact.fee_drag_1y:,.0f}",
                "drag_3_years": f"${core_fact.fee_drag_3y:,.0f}",
                "drag_5_years": f"${core_fact.fee_drag_5y:,.0f}",
            },
            "cross_etf_overlaps": overlaps,
        }
