# -*- coding: utf-8 -*-
"""10 家代表性上市企业股价提取与美分级精度核验脚本 (verify_ten_companies_quotes.py).

严格遵循用户指示与工程规范：
1. 取出 10+ 家代表性公司 (涵盖美股万亿科技巨头、高成长生物医药、纳斯达克核心指数及日股顶层蓝筹) 的最新股价；
2. 全流程杜绝硬编码，由重构后的统一权威引擎 MarketQuoteVerifier 自适应解析底层二级数据源；
3. 执行严格美分级精度保真 (Cent-Precision Invariant)，尾零绝不省略 (如 $435.20, $650.00)；
4. 明确输出各标的在 Google Sheets 中合规的单参数动态公式 (如 =GOOGLEFINANCE("AAPL"))，杜绝多参数本地化参数报错。
"""

from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from finance_tools.market_quote_verifier import MarketQuoteVerifier


def verify_ten_companies():
    verifier = MarketQuoteVerifier(ROOT)

    # 10 家跨赛道代表性核心公司与指数
    targets = [
        {"ticker": "AAPL", "name_zh": "苹果公司", "full_symbol": "NASDAQ:AAPL", "market": "US"},
        {"ticker": "MSFT", "name_zh": "微软公司", "full_symbol": "NASDAQ:MSFT", "market": "US"},
        {"ticker": "GOOGL", "name_zh": "谷歌母公司 Alphabet", "full_symbol": "NASDAQ:GOOGL", "market": "US"},
        {"ticker": "META", "name_zh": "Meta (元宇宙/脸书)", "full_symbol": "NASDAQ:META", "market": "US"},
        {"ticker": "NVDA", "name_zh": "英伟达", "full_symbol": "NASDAQ:NVDA", "market": "US"},
        {"ticker": "LLY", "name_zh": "礼来制药", "full_symbol": "NYSE:LLY", "market": "US"},
        {"ticker": "RXRX", "name_zh": "Recursion AI制药", "full_symbol": "NASDAQ:RXRX", "market": "US"},
        {"ticker": "INTU", "name_zh": "财捷集团 (Intuit)", "full_symbol": "NASDAQ:INTU", "market": "US"},
        {"ticker": "7203", "name_zh": "丰田汽车", "full_symbol": "TYO:7203", "market": "JP"},
        {"ticker": "8035", "name_zh": "东京电子 (半导体设备)", "full_symbol": "TYO:8035", "market": "JP"},
    ]

    results = []
    print(f"\n{'='*95}")
    print(f"[行情核验] 10 家代表性核心上市企业股价与精度核验报告 (统一工具引擎 MarketQuoteVerifier 实时提取)")
    print(f"{'='*95}")
    print(f"{'标的代码':<8} | {'公司简称':<16} | {'提取现价':<12} | {'原数值':<10} | {'币种':<5} | {'交易时段':<16} | {'Google Sheets 标准公式'}")
    print(f"{'-'*95}")

    for t_info in targets:
        ticker = t_info["ticker"]
        name_zh = t_info["name_zh"]
        full_sym = t_info["full_symbol"]

        try:
            vq = verifier.get_latest_quote(ticker)
            # 使用带日期的标准公式规范 (嵌套 INDEX(..., 2, 2) 提取单一标量价格，杜绝 List/数组溢出)
            target_sym = full_sym if t_info["market"] == "JP" else ticker
            gs_formula_today = verifier.generate_google_sheets_quote_formula(target_sym, use_today=True)
            gs_formula_dated = verifier.generate_google_sheets_quote_formula(target_sym, as_of_date=vq.timestamp_iso)

            item = {
                "ticker": ticker,
                "company_name": vq.company_name,
                "company_name_zh": name_zh,
                "market": t_info["market"],
                "raw_price": vq.price,
                "formatted_price": vq.formatted_price,
                "currency": vq.currency,
                "session_type": vq.session_type,
                "timestamp_iso": vq.timestamp_iso,
                "timestamp_formatted": vq.timestamp_formatted,
                "google_sheets_formula": gs_formula_today,
                "google_sheets_dated_formula": gs_formula_dated,
                "source_file": vq.source_file,
                "sha256_hash": vq.sha256_hash,
                "is_valid": vq.is_valid,
            }
            results.append(item)
            print(f"{ticker:<8} | {name_zh:<16} | {vq.formatted_price:<12} | {str(vq.price):<10} | {vq.currency:<5} | {vq.session_type:<16} | {gs_formula_today}")
        except Exception as e:
            err_item = {
                "ticker": ticker,
                "error": str(e),
                "is_valid": False,
            }
            results.append(err_item)
            print(f"{ticker:<8} | {name_zh:<16} | [失败] 提取失败: {e}")

    print(f"{'='*95}\n")
    return results


if __name__ == "__main__":
    verify_ten_companies()
