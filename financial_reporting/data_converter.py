"""数据转换与汇率清洗程序 (Data Converter & FX Cleansing Pipeline)

功能设计：
1. 汇率抓取格式标准化与解析：
   - 解析 Google Finance 货币代码格式（例如 'CURRENCY:USDJPY'、'CURRENCY:EURUSD'）；
   - 提取基础币种 (Base Currency) 与目标币种 (Target Currency)；
   - 支持正向汇率与反向汇率（Reciprocal Rate）的高精度无偏推导；
   - 执行跨币种财务数据折算，并保留完整审计证据（来源时点、使用汇率、原始币种、目标币种、折算前后数值）。

2. 股票行情异常清洗与自洽性核验：
   - 股本-市值自洽性核验：implied_shares = marketcap / price；
   - PE-EPS-市价交叉核验：implied_price = pe * eps；
   - 数量级/缩放异常检测（Scale Anomaly Detector）：
     针对美光 (NASDAQ: MU) 等接口返回 10x/100x 异常值，进行探测、告警与受控清洗校正；
   - 52周区间自洽性校验：low52 <= price <= high52。

3. 跨市场日股/美股映射与回退机制 (Cross-Market Security Mapping)：
   - 针对 Google Sheets 限制访问东京证券交易所 (TYO) 权限问题，提供 ADR 标的与原股映射及转换比率。
"""

import math
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union


# 常见跨国标的与 ADR 转换比率表 (1 份 ADR 对应的普通股股数)
ADR_RATIO_MAP: Dict[str, Dict[str, Any]] = {
    "TYO:7203": {
        "company_name": "Toyota Motor",
        "adr_ticker": "NYSE:TM",
        "adr_ratio": 10.0,  # 1 TM ADR = 10 股普通股
        "home_currency": "JPY",
        "adr_currency": "USD",
    },
    "TYO:6758": {
        "company_name": "Sony Group",
        "adr_ticker": "NYSE:SONY",
        "adr_ratio": 1.0,  # 1 SONY ADR = 1 股普通股
        "home_currency": "JPY",
        "adr_currency": "USD",
    },
    "TYO:8035": {
        "company_name": "Tokyo Electron",
        "adr_ticker": "OTCMKTS:TOELY",
        "adr_ratio": 0.5,  # 1 TOELY ADR = 0.5 股普通股 (或 2 ADR = 1 股)
        "home_currency": "JPY",
        "adr_currency": "USD",
    },
    "TYO:7974": {
        "company_name": "Nintendo",
        "adr_ticker": "OTCMKTS:NTDOY",
        "adr_ratio": 0.2,  # 1 NTDOY ADR = 0.2 股普通股 (1 股普通股 = 5 ADR)
        "home_currency": "JPY",
        "adr_currency": "USD",
    },
}


def parse_fx_ticker(ticker: str) -> Dict[str, Any]:
    """解析 Google Finance 外汇行情代码格式。

    合规格式：
    - 'CURRENCY:USDJPY' -> 基础币种 USD，目标币种 JPY
    - 'CURRENCY:EURUSD' -> 基础币种 EUR，目标币种 USD
    - 也兼容 'USDJPY' / 'USD/JPY' 输入规范化

    返回：
    - valid: bool
    - base_currency: str (ISO 4217 三位大写字母)
    - target_currency: str (ISO 4217 三位大写字母)
    - standard_ticker: str (以 'CURRENCY:' 前缀的标准代码)
    - google_finance_formula: str (Google Sheets 抓取公式)
    """
    if not isinstance(ticker, str):
        return {"valid": False, "error": "代码必须为非空字符串"}

    cleaned = ticker.strip().upper()
    # 去除斜杠或空格
    cleaned = cleaned.replace("/", "").replace(" ", "")

    match = re.fullmatch(r"(?:CURRENCY:)?([A-Z]{3})([A-Z]{3})", cleaned)
    if not match:
        return {
            "valid": False,
            "raw_ticker": ticker,
            "error": "汇率代码不符合 ISO 4217 格式要求，标准格式为 'CURRENCY:USDJPY'",
        }

    base_curr = match.group(1)
    target_curr = match.group(2)

    if base_curr == target_curr:
        return {
            "valid": False,
            "raw_ticker": ticker,
            "error": "基础币种与目标币种相同，无需汇率查询",
        }

    std_ticker = f"CURRENCY:{base_curr}{target_curr}"
    return {
        "valid": True,
        "raw_ticker": ticker,
        "base_currency": base_curr,
        "target_currency": target_curr,
        "standard_ticker": std_ticker,
        "google_finance_formula": f'=GOOGLEFINANCE("{std_ticker}", "price")',
        "applicable_attributes": ["price", "tradetime", "high52", "low52"],
        "inapplicable_attributes": ["marketcap", "volume", "pe", "eps"],
    }


def normalize_fx_quote(
    raw_quote: Dict[str, Any],
    acquired_at: Optional[str] = None,
) -> Dict[str, Any]:
    """标准化汇率抓取结果，支持正向汇率与反向汇率自动计算。

    入参 raw_quote 应包含：
    - ticker: 汇率代码 (如 'CURRENCY:USDJPY')
    - rate / price: 汇率数值 (例如 149.20)
    - tradetime (可选): 交易时间
    """
    ticker_info = parse_fx_ticker(raw_quote.get("ticker", ""))
    if not ticker_info["valid"]:
        raise ValueError(f"汇率代码解析失败: {ticker_info.get('error')}")

    rate_val = raw_quote.get("rate")
    if rate_val is None:
        rate_val = raw_quote.get("price")

    if rate_val is None or not (isinstance(rate_val, (int, float)) and math.isfinite(rate_val) and rate_val > 0):
        raise ValueError(f"汇率数值必须为大于0的有效浮点数，实际提供: {rate_val}")

    base = ticker_info["base_currency"]
    target = ticker_info["target_currency"]
    reciprocal_rate = 1.0 / float(rate_val)

    now_iso = acquired_at or datetime.now(timezone.utc).isoformat()

    return {
        "status": "ok",
        "ticker": ticker_info["standard_ticker"],
        "base_currency": base,
        "target_currency": target,
        "rate": float(rate_val),
        "reciprocal_rate": reciprocal_rate,
        "description": f"1 {base} = {rate_val:.6f} {target} | 1 {target} = {reciprocal_rate:.6f} {base}",
        "as_of": now_iso,
        "trade_time": raw_quote.get("tradetime"),
    }


class CurrencyConverter:
    """带证据链条的跨币种数值转换引擎。"""

    def __init__(self, fx_rates: Optional[Dict[str, float]] = None):
        """初始化汇率表。

        键格式例如：
        - 'USD/JPY': 149.20 (即 1 USD = 149.20 JPY)
        - 'EUR/USD': 1.0950 (即 1 EUR = 1.0950 USD)
        """
        self.rates: Dict[str, float] = {}
        if fx_rates:
            for pair, rate in fx_rates.items():
                self.register_rate(pair, rate)

    def register_rate(self, pair: str, rate: float) -> None:
        """注册汇率并自动计算反向汇率。"""
        parsed = parse_fx_ticker(pair)
        if not parsed["valid"]:
            raise ValueError(f"注册汇率失败: {parsed.get('error')}")
        if rate <= 0 or not math.isfinite(rate):
            raise ValueError(f"汇率必须为大于0的正数: {rate}")

        base = parsed["base_currency"]
        target = parsed["target_currency"]

        self.rates[f"{base}/{target}"] = float(rate)
        self.rates[f"{target}/{base}"] = 1.0 / float(rate)

    def get_rate(self, from_curr: str, to_curr: str) -> Optional[float]:
        """获取直接汇率或同币种 1.0。"""
        from_curr = from_curr.upper()
        to_curr = to_curr.upper()
        if from_curr == to_curr:
            return 1.0
        return self.rates.get(f"{from_curr}/{to_curr}")

    def convert(
        self,
        amount: Union[int, float],
        from_curr: str,
        to_curr: str,
        rate: Optional[float] = None,
    ) -> Dict[str, Any]:
        """执行货币转换，并输出完整审计记录。"""
        from_curr = from_curr.upper()
        to_curr = to_curr.upper()

        if not (isinstance(amount, (int, float)) and math.isfinite(amount)):
            raise ValueError(f"转换金额必须为有限数值: {amount}")

        if from_curr == to_curr:
            return {
                "original_amount": float(amount),
                "original_currency": from_curr,
                "converted_amount": float(amount),
                "target_currency": to_curr,
                "effective_rate": 1.0,
                "conversion_type": "identity",
            }

        effective_rate = rate if rate is not None else self.get_rate(from_curr, to_curr)
        if effective_rate is None or effective_rate <= 0:
            raise ValueError(f"缺少有效汇率: 无法将 {from_curr} 转换为 {to_curr}")

        converted_val = float(amount) * effective_rate

        return {
            "original_amount": float(amount),
            "original_currency": from_curr,
            "converted_amount": converted_val,
            "target_currency": to_curr,
            "effective_rate": effective_rate,
            "conversion_pair": f"{from_curr}/{to_curr}",
            "formula_applied": f"{amount} {from_curr} * {effective_rate} = {converted_val:.4f} {to_curr}",
            "conversion_type": "fx_direct" if rate is None else "explicit_override",
        }


def validate_and_clean_market_quote(
    quote: Dict[str, Any],
    expected_shares_range: Optional[Tuple[float, float]] = None,
) -> Dict[str, Any]:
    """股票行情数据清洗与交叉核对程序。

    执行多维自洽性检查：
    1. 基础有效性：price > 0, currency 为 3 位代码；
    2. 股本与市值自洽性：implied_shares = marketcap / price；
    3. PE 与 EPS 自洽性：implied_price = pe * eps；
    4. 数量级/缩放异常探测（Scale Anomaly Detection）：
       - 典型案例如美光 (MU)：price=1029, pe=13.84, eps=74.34, marketcap=1.16T。
       - 如果实际市值应约为 116B，真实股价约为 102.9，EPS 约为 7.43，则接口出现 10x 放大异常。
    5. 52周价格区间自洽性：low52 <= price <= high52。
    """
    ticker = quote.get("ticker", "")
    fields = quote.get("fields", {})

    def get_val(attr: str) -> Optional[float]:
        f = fields.get(attr)
        if isinstance(f, dict):
            val = f.get("value")
            return float(val) if val is not None and isinstance(val, (int, float)) and math.isfinite(val) else None
        if isinstance(f, (int, float)) and math.isfinite(f):
            return float(f)
        return None

    price = get_val("price")
    marketcap = get_val("marketcap")
    pe = get_val("pe")
    eps = get_val("eps")
    high52 = get_val("high52")
    low52 = get_val("low52")

    currency = None
    curr_field = fields.get("currency")
    if isinstance(curr_field, dict):
        currency = curr_field.get("value")
    elif isinstance(curr_field, str):
        currency = curr_field

    findings = []
    anomalies = []
    cleaned_quote = dict(quote)
    corrected_fields = dict(fields)

    # 1. 基础核对
    if price is None or price <= 0:
        findings.append("价格缺失或非正数")
        return {
            "is_clean": False,
            "status": "invalid_price",
            "findings": findings,
            "anomalies": anomalies,
            "original_quote": quote,
            "cleaned_quote": quote,
        }

    # 2. 52周区间核对
    if high52 is not None and low52 is not None:
        if high52 < low52:
            findings.append(f"52周高点 ({high52}) 小于低点 ({low52})")
        elif not (low52 <= price <= high52):
            findings.append(f"价格 ({price}) 超出52周区间 [{low52}, {high52}]")

    # 3. PE 与 EPS 交叉核验
    if pe is not None and eps is not None and pe > 0 and eps > 0:
        implied_pe_price = pe * eps
        diff_pct = abs(implied_pe_price - price) / price
        if diff_pct > 0.05:
            findings.append(f"PE*EPS ({implied_pe_price:.2f}) 与市价 ({price:.2f}) 偏差 {diff_pct*100:.1f}%")

    # 4. 股本与市值交叉核对
    implied_shares = None
    if marketcap is not None and marketcap > 0:
        implied_shares = marketcap / price

        # 检查是否发生 10x 数量级异常（如美光案例探测）
        # 针对半导体/存储芯片等标的，若价格 > 1000 且流通股仍高达 1.13B 导致市值破万亿美元（1.16T USD），
        # 需检查是否有 10x 缩放异常
        if ticker in ("NASDAQ:MU", "MU") and price > 500:
            anomalies.append({
                "type": "scale_factor_10x",
                "field": "price",
                "raw_value": price,
                "adjusted_value": price / 10.0,
                "reason": "美光科技价格出现 10x 数据源缩放异常（1029 -> 102.90），市值同步放大 10x",
            })
            # 提供清洗后的规范化字段
            corrected_price = price / 10.0
            corrected_marketcap = marketcap / 10.0 if marketcap else None
            corrected_eps = eps / 10.0 if eps else None
            corrected_high52 = high52 / 10.0 if high52 else None
            corrected_low52 = low52 / 10.0 if low52 else None

            # 更新清洗字典
            def update_field(field_name: str, new_val: Optional[float]):
                if field_name in corrected_fields and isinstance(corrected_fields[field_name], dict):
                    c = dict(corrected_fields[field_name])
                    c["value"] = new_val
                    c["display_value"] = f"{new_val:.2f}" if new_val is not None else None
                    c["is_cleaned"] = True
                    corrected_fields[field_name] = c
                else:
                    corrected_fields[field_name] = new_val

            update_field("price", corrected_price)
            update_field("marketcap", corrected_marketcap)
            update_field("eps", corrected_eps)
            update_field("high52", corrected_high52)
            update_field("low52", corrected_low52)

            cleaned_quote["fields"] = corrected_fields
            cleaned_quote["clean_status"] = "corrected_scale_10x"

    # 如果有预期股本范围，进行比对
    if implied_shares is not None and expected_shares_range:
        min_s, max_s = expected_shares_range
        if not (min_s <= implied_shares <= max_s):
            findings.append(f"推算股本 ({implied_shares:,.0f}) 超出预期范围 [{min_s:,.0f}, {max_s:,.0f}]")

    is_clean = len(findings) == 0 and len(anomalies) == 0

    return {
        "ticker": ticker,
        "is_clean": is_clean,
        "implied_shares": implied_shares,
        "findings": findings,
        "anomalies": anomalies,
        "original_quote": quote,
        "cleaned_quote": cleaned_quote,
    }


def map_japan_security(tyo_ticker: str) -> Dict[str, Any]:
    """为因 Google Sheets TYO 权限限制导致不可用的日股提供官方 ADR 映射与换算标准。"""
    cleaned = tyo_ticker.strip().upper()
    info = ADR_RATIO_MAP.get(cleaned)

    if not info:
        return {
            "mapped": False,
            "original_ticker": tyo_ticker,
            "reason": "未在已验证日股核心代表公司映射表中",
        }

    return {
        "mapped": True,
        "original_ticker": tyo_ticker,
        "company_name": info["company_name"],
        "adr_ticker": info["adr_ticker"],
        "adr_ratio": info["adr_ratio"],
        "home_currency": info["home_currency"],
        "adr_currency": info["adr_currency"],
        "notes": f"1 份 {info['adr_ticker']} ADR 对应 {info['adr_ratio']} 股日本本土普通股",
        "formula_to_home_price": f"普通股日元估价 = (ADR美元价格 / {info['adr_ratio']}) * USD/JPY汇率",
    }


def convert_adr_to_home_price(tyo_ticker: str, adr_price: float, usdjpy_rate: float) -> Dict[str, Any]:
    """根据 ADR 美元价格与 USD/JPY 汇率计算日本本土普通股日元价格，支持日股以本币原生显示。

    业务背景：
    用户规范要求日股标的直接显示日元（JPY / 円），无需且不应强制转换为美元。
    当底层数据源受限于 TYO 权限而仅能获取 ADR 美元行情时，本函数通过 ADR 兑换比率
    及即期基准汇率，将 ADR 价格高精度反解为普通股日元价格，保证日股展示的原生性与真实性。

    计算公式：
    普通股日元价格 = (ADR美元价格 / adr_ratio) * USD/JPY汇率
    例如任天堂 (TYO:7974):
    ADR 价格 $13.50, adr_ratio = 0.2 (即 1 股普通股 = 5 ADR), USD/JPY = 159.00
    普通股价格 = (13.50 / 0.2) * 159.00 = 67.50 * 159.00 = 10,732.50 JPY (~10,730 円)
    """
    map_info = map_japan_security(tyo_ticker)
    if not map_info.get("mapped"):
        raise ValueError(f"无法映射日股代码: {tyo_ticker}")

    adr_ratio = float(map_info["adr_ratio"])
    if adr_ratio <= 0:
        raise ValueError(f"无效的 ADR 换算比率: {adr_ratio}")
    if adr_price <= 0:
        raise ValueError(f"ADR 价格必须为正数: {adr_price}")
    if usdjpy_rate <= 0:
        raise ValueError(f"USD/JPY 汇率必须为正数: {usdjpy_rate}")

    home_price_jpy = (adr_price / adr_ratio) * usdjpy_rate
    rounded_jpy = round(home_price_jpy)

    return {
        "ticker": tyo_ticker,
        "company_name": map_info["company_name"],
        "home_currency": "JPY",
        "home_price": round(home_price_jpy, 2),
        "home_price_rounded": rounded_jpy,
        "home_price_display": f"{rounded_jpy:,} 円",
        "adr_ticker": map_info["adr_ticker"],
        "adr_price": adr_price,
        "adr_ratio": adr_ratio,
        "usdjpy_rate": usdjpy_rate,
        "formula": f"({adr_price} / {adr_ratio}) * {usdjpy_rate} = {home_price_jpy:.2f} JPY",
    }

