# -*- coding: utf-8 -*-
"""行情数据接口适配器 (data_interface/market_adapter.py).

严格遵循《AGENTS.md》与《CLAUDE.md》：
1. 点时零前视偏差 (Strict Point-in-Time)：依据 as_of_date 严格截断未来日线；
2. 异构字段自适应对齐：兼容 close/Close/adj_close, volume/Volume, turnover/amount 等多源字段；
3. 金融数学边界防御：除零保护、极值平滑、缺失日线智能回退；
4. 输出类型安全不可变契约：StandardBar, MarketDataFeatureInput, LiquidityStressInput。
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from .contracts import MarketDataFeatureInput, LiquidityStressInput, StandardBar


class MarketDataAdapter:
    """行情数据接口适配器：将非标原始日线清洗转换为标准金融计算特征."""

    @staticmethod
    def normalize_bar(raw_bar: Dict[str, Any]) -> StandardBar:
        """将单个非标原始日线字典清洗为 StandardBar."""
        date_val = str(raw_bar.get("date") or raw_bar.get("Date") or raw_bar.get("time") or "")

        # 兼容不同收盘价字段
        close_val = float(raw_bar.get("close") if raw_bar.get("close") is not None else
                          raw_bar.get("Close") if raw_bar.get("Close") is not None else
                          raw_bar.get("adj_close") if raw_bar.get("adj_close") is not None else
                          raw_bar.get("Adj Close", 100.0))

        open_val = float(raw_bar.get("open") if raw_bar.get("open") is not None else
                         raw_bar.get("Open") if raw_bar.get("Open") is not None else close_val)

        high_val = float(raw_bar.get("high") if raw_bar.get("high") is not None else
                         raw_bar.get("High") if raw_bar.get("High") is not None else max(open_val, close_val))

        low_val = float(raw_bar.get("low") if raw_bar.get("low") is not None else
                        raw_bar.get("Low") if raw_bar.get("Low") is not None else min(open_val, close_val))

        volume_val = float(raw_bar.get("volume") if raw_bar.get("volume") is not None else
                           raw_bar.get("Volume") if raw_bar.get("Volume") is not None else
                           raw_bar.get("vol", 10_000.0))

        turnover_val = float(raw_bar.get("turnover") if raw_bar.get("turnover") is not None else
                            raw_bar.get("amount") if raw_bar.get("amount") is not None else
                            raw_bar.get("Turnover", volume_val * close_val))

        adj_close_val = float(raw_bar.get("adj_close") if raw_bar.get("adj_close") is not None else
                              raw_bar.get("Adj Close") if raw_bar.get("Adj Close") is not None else close_val)

        return StandardBar(
            date=date_val,
            open=round(open_val, 4),
            high=round(high_val, 4),
            low=round(low_val, 4),
            close=round(close_val, 4),
            volume=round(max(0.0, volume_val), 2),
            turnover=round(max(0.0, turnover_val), 2),
            adj_close=round(adj_close_val, 4),
        )

    @classmethod
    def filter_pit_bars(
        cls,
        raw_bars: List[Dict[str, Any]],
        as_of_date: Optional[str] = None
    ) -> List[StandardBar]:
        """清洗并严格按 as_of_date 执行点时截断."""
        standard_bars: List[StandardBar] = []
        for b in raw_bars:
            if not isinstance(b, dict):
                continue
            s_bar = cls.normalize_bar(b)
            if not s_bar.date:
                continue
            if as_of_date and s_bar.date > as_of_date:
                continue
            standard_bars.append(s_bar)

        standard_bars.sort(key=lambda x: x.date)
        return standard_bars

    @classmethod
    def extract_market_features(
        cls,
        symbol: str,
        raw_bars: List[Dict[str, Any]],
        as_of_date: Optional[str] = None,
        currency: str = "USD",
    ) -> MarketDataFeatureInput:
        """将原始行情序列提取加工为标准技术与波动率特征输入."""
        pit_bars = cls.filter_pit_bars(raw_bars, as_of_date)
        if not pit_bars:
            eff_date = as_of_date or "2026-01-01"
            return MarketDataFeatureInput(
                symbol=symbol,
                as_of_date=eff_date,
                currency=currency,
                bars_count=0,
                latest_close=100.0,
                historical_closes=[100.0],
                historical_volumes=[0.0],
                historical_turnovers=[0.0],
                log_returns_20d=[0.0],
                sma20=100.0,
                sma50=100.0,
                sma200=100.0,
                realized_vol20_annualized=0.20,
                highest_22d=100.0,
                lowest_22d=100.0,
                atr22=2.0,
            )

        eff_date = as_of_date or pit_bars[-1].date
        closes = [b.close for b in pit_bars]
        volumes = [b.volume for b in pit_bars]
        turnovers = [b.turnover for b in pit_bars]
        latest_c = closes[-1]

        # 均线计算
        sma20 = sum(closes[-20:]) / min(len(closes), 20)
        sma50 = sum(closes[-50:]) / min(len(closes), 50)
        sma200 = sum(closes[-200:]) / min(len(closes), 200)

        # 20日对数收益率与已实现年化波动率
        recent_21 = closes[-21:] if len(closes) >= 21 else closes
        log_rets = []
        for i in range(1, len(recent_21)):
            prev = recent_21[i-1]
            curr = recent_21[i]
            if prev > 0 and curr > 0:
                log_rets.append(math.log(curr / prev))
            else:
                log_rets.append(0.0)

        if len(log_rets) > 1:
            mean_r = sum(log_rets) / len(log_rets)
            var_r = sum((r - mean_r) ** 2 for r in log_rets) / (len(log_rets) - 1)
            vol20 = math.sqrt(var_r * 252.0)
        else:
            vol20 = 0.20

        # 22日极值与 ATR
        recent_22_bars = pit_bars[-22:]
        highest_22 = max([b.high for b in recent_22_bars]) if recent_22_bars else latest_c
        lowest_22 = min([b.low for b in recent_22_bars]) if recent_22_bars else latest_c

        tr_list = []
        for i in range(len(recent_22_bars)):
            curr_b = recent_22_bars[i]
            if i == 0:
                tr = curr_b.high - curr_b.low
            else:
                prev_c = recent_22_bars[i-1].close
                tr = max(curr_b.high - curr_b.low, abs(curr_b.high - prev_c), abs(curr_b.low - prev_c))
            tr_list.append(tr)
        atr22 = sum(tr_list) / len(tr_list) if tr_list else 2.0

        return MarketDataFeatureInput(
            symbol=symbol,
            as_of_date=eff_date,
            currency=currency,
            bars_count=len(pit_bars),
            latest_close=round(latest_c, 4),
            historical_closes=closes,
            historical_volumes=volumes,
            historical_turnovers=turnovers,
            log_returns_20d=[round(r, 6) for r in log_rets],
            sma20=round(sma20, 4),
            sma50=round(sma50, 4),
            sma200=round(sma200, 4),
            realized_vol20_annualized=round(vol20, 4),
            highest_22d=round(highest_22, 4),
            lowest_22d=round(lowest_22, 4),
            atr22=round(atr22, 4),
        )

    @classmethod
    def extract_liquidity_input(
        cls,
        symbol: str,
        raw_bars: List[Dict[str, Any]],
        as_of_date: Optional[str] = None,
        market: str = "US",
        intended_order_value: float = 50_000.0,
    ) -> LiquidityStressInput:
        """将原始行情序列提取加工为 Amihud 流动性冲击输入."""
        pit_bars = cls.filter_pit_bars(raw_bars, as_of_date)
        eff_date = as_of_date or (pit_bars[-1].date if pit_bars else "2026-01-01")

        # 转换为适配器原生字典列表供 AmihudLiquidityEngine 消费
        sample_dicts = [
            {
                "date": b.date,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
                "turnover": b.turnover,
            }
            for b in pit_bars[-60:]
        ]

        recent_20_turnovers = [b.turnover for b in pit_bars[-20:]]
        adv_20d = sum(recent_20_turnovers) / len(recent_20_turnovers) if recent_20_turnovers else 0.0

        return LiquidityStressInput(
            symbol=symbol,
            as_of_date=eff_date,
            market=market.upper(),
            sample_bars=sample_dicts,
            intended_order_value=float(intended_order_value),
            average_daily_turnover_20d=round(adv_20d, 2),
        )

    @staticmethod
    def round_to_lot_size(shares: float, lot_size: int = 1) -> float:
        """根据市场整手约束规整交易股数 (美股 1 股，日股通常 100 股)."""
        lot = max(1, int(lot_size))
        s = max(0.0, float(shares))
        if lot == 1:
            return float(math.floor(s))
        # 整手向下取整，严禁出现不可成交的碎股
        rounded_lots = math.floor(s / lot)
        return float(rounded_lots * lot)

    @staticmethod
    def convert_currency(
        amount: float,
        from_curr: str,
        to_curr: str,
        as_of_date: str = "",
        fx_rates_to_usd: Optional[Dict[str, float]] = None,
    ) -> float:
        """多币种资产价值折算基准汇率中枢 (以 USD 为组合统一记账基准币).

        fx_rates_to_usd: 币种对美元的汇率，例如 {"USD": 1.0, "JPY": 0.0065} (即 1 JPY = 0.0065 USD 或 1 USD = 153.8 JPY)
        """
        amt = float(amount)
        fc = from_curr.upper()
        tc = to_curr.upper()
        if fc == tc:
            return amt

        default_fx = {
            "USD": 1.0,
            "JPY": 0.00667, # 默认 1 USD = 150 JPY
            "EUR": 1.08,
            "HKD": 0.128,
        }
        lookup = dict(default_fx)
        if fx_rates_to_usd:
            lookup.update(fx_rates_to_usd)

        from_to_usd = lookup.get(fc, 1.0)
        to_to_usd = lookup.get(tc, 1.0)

        # 折算为 USD 再转为目标币种
        amt_usd = amt * from_to_usd
        amt_target = amt_usd / max(1e-6, to_to_usd)
        return round(amt_target, 4)
