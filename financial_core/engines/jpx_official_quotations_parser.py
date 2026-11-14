"""东证《株式相場表》批量日线解析与金融组装引擎 (JPX Daily Official Quotations Parser).

依据《SPEC-43 美日股全市场盘前采集调查》第 2 步规范：
1. 批量解析日本交易所集团 (JPX) 公开逐日《株式相場表》(Daily Official Quotations)；
2. 提取股票代码、股票名称、前场 (上午) 四价、后场 (下午) 四价与出来高 (成交量)；
3. 买方金融规则组装全日综合 OHLCV：
   - 始值 (Open)：首个有效成交价 (优先前场始值，前场无成交则取后场始值)；
   - 高值 (High)：全天各时段有效最高价之极大值；
   - 安值 (Low)：全天各时段有效最低价之极小值；
   - 终值 (Close)：最终有效收盘价 (优先后场终值，后场无成交则取前场终值)；
   - 出来高 (Volume)：按千株换算为实际股数；
4. 规范化处理停牌、无成交符号 (如 '-'、'▲'、'*')，区分有效交易与停牌无量。
"""

from dataclasses import dataclass
import math
import re
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class JpxDailyBar:
    """单只东证证券官方标准日线记录。"""
    code: str
    name: str
    session_date: str
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    volume: int
    is_suspended: bool
    raw_flags: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Date": self.session_date,
            "Open": self.open,
            "High": self.high,
            "Low": self.low,
            "Close": self.close,
            "Volume": self.volume,
            "is_suspended": self.is_suspended,
            "flags": self.raw_flags,
        }


def _clean_price(val: Any) -> Optional[float]:
    """清洗日文相场表价格字符串，去除逗号、特殊符号与前后空格。"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) if math.isfinite(val) and val > 0 else None
    s = str(val).strip().replace(",", "").replace("，", "")
    # 过滤未成交、停牌或空值占位符
    if not s or s in ("-", "−", "―", "▲", "*", "–", "—", "…", "・"):
        return None
    # 提取数字（支持如 1500.5 或 ▲1500）
    match = re.search(r"(\d+(?:\.\d+)?)", s)
    if match:
        try:
            p = float(match.group(1))
            return p if p > 0 else None
        except ValueError:
            return None
    return None


def _clean_volume(val: Any, unit_multiplier: int = 1000) -> int:
    """清洗成交量 (相场表出来高通常单位为千株，乘数默认为 1000)."""
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return max(0, int(val * unit_multiplier))
    s = str(val).strip().replace(",", "").replace("，", "")
    if not s or s in ("-", "−", "―", "*"):
        return 0
    match = re.search(r"(\d+(?:\.\d+)?)", s)
    if match:
        try:
            return max(0, int(float(match.group(1)) * unit_multiplier))
        except ValueError:
            return 0
    return 0


class JpxOfficialQuotationsParser:
    """东证日刊《株式相場表》批量解析器。"""

    @classmethod
    def assemble_bar(
        cls,
        code: str,
        name: str,
        session_date: str,
        morning_ohlc: Tuple[Any, Any, Any, Any],
        afternoon_ohlc: Tuple[Any, Any, Any, Any],
        volume_val: Any,
        volume_multiplier: int = 1000,
        flags: str = "",
    ) -> JpxDailyBar:
        """从前场、后场四价与成交量金融合成单日标准日线。"""
        m_open = _clean_price(morning_ohlc[0])
        m_high = _clean_price(morning_ohlc[1])
        m_low = _clean_price(morning_ohlc[2])
        m_close = _clean_price(morning_ohlc[3])

        a_open = _clean_price(afternoon_ohlc[0])
        a_high = _clean_price(afternoon_ohlc[1])
        a_low = _clean_price(afternoon_ohlc[2])
        a_close = _clean_price(afternoon_ohlc[3])

        # 1. 开盘价 (Open): 优先前场始值，前场无成交取后场始值
        eff_open = m_open if m_open is not None else a_open

        # 2. 收盘价 (Close): 优先后场终值，后场无成交取前场终值
        eff_close = a_close if a_close is not None else m_close

        # 3. 最高价 (High): 全天有效价格极大值
        valid_highs = [p for p in (m_high, a_high, eff_open, eff_close) if p is not None]
        eff_high = max(valid_highs) if valid_highs else None

        # 4. 最低价 (Low): 全天有效价格极小值
        valid_lows = [p for p in (m_low, a_low, eff_open, eff_close) if p is not None]
        eff_low = min(valid_lows) if valid_lows else None

        # 5. 成交量
        vol = _clean_volume(volume_val, volume_multiplier)

        # 6. 停牌判定：全天四价皆空且成交量为 0
        is_suspended = (eff_open is None and eff_close is None and vol == 0)

        # 规范化 4 位或 5 位东证代码
        clean_code = str(code).strip().upper().removeprefix("TYO:")

        return JpxDailyBar(
            code=clean_code,
            name=str(name).strip(),
            session_date=session_date[:10],
            open=eff_open,
            high=eff_high,
            low=eff_low,
            close=eff_close,
            volume=vol,
            is_suspended=is_suspended,
            raw_flags=flags,
        )

    @classmethod
    def parse_rows(
        cls,
        rows: List[Dict[str, Any]],
        session_date: str,
    ) -> List[JpxDailyBar]:
        """批量解析结构化数据行 (如从相场表 PDF 或 CSV 提取出的字典行)."""
        bars: List[JpxDailyBar] = []
        for r in rows:
            code = r.get("code") or r.get("ticker") or r.get("コード")
            if not code:
                continue
            name = r.get("name") or r.get("銘柄名") or ""

            # 兼容前场四价
            m_open = r.get("morning_open") or r.get("前場始値")
            m_high = r.get("morning_high") or r.get("前場高値")
            m_low = r.get("morning_low") or r.get("前場安値")
            m_close = r.get("morning_close") or r.get("前場終値")

            # 兼容后场四价
            a_open = r.get("afternoon_open") or r.get("後場始値")
            a_high = r.get("afternoon_high") or r.get("後場高値")
            a_low = r.get("afternoon_low") or r.get("後場安値")
            a_close = r.get("afternoon_close") or r.get("後場終値")

            vol = r.get("volume") or r.get("出来高") or 0
            mult = int(r.get("volume_multiplier", 1000))
            flags = str(r.get("flags") or "")

            bar = cls.assemble_bar(
                code=code,
                name=name,
                session_date=session_date,
                morning_ohlc=(m_open, m_high, m_low, m_close),
                afternoon_ohlc=(a_open, a_high, a_low, a_close),
                volume_val=vol,
                volume_multiplier=mult,
                flags=flags,
            )
            bars.append(bar)
        return bars
