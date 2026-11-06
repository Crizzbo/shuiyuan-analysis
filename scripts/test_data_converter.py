"""数据转换与汇率清洗程序回归测试 (Data Converter & FX Cleansing Test Suite)

覆盖范围：
1. 汇率抓取格式解析与标准公式生成；
2. 汇率报价规范化与倒数反向汇率高精度计算；
3. 跨币种财务转换引擎（Nintendo J-GAAP 现金折算美元等实际商业案例）；
4. 股票行情自洽性检查与异常量纲探测（美光 MU 10x 异常清洗与修复）；
5. 跨市场日股 TYO 到 ADR 的映射与折算比率；
6. 网络访问隔离与严格异常阻断。
"""

import math
import os
from pathlib import Path
import socket
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# 严禁任何网络连接
def deny_network(*args, **kwargs):
    raise AssertionError("测试执行过程中禁止网络访问")

socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
socket.create_connection = deny_network

from financial_reporting.data_converter import (
    parse_fx_ticker,
    normalize_fx_quote,
    CurrencyConverter,
    validate_and_clean_market_quote,
    map_japan_security,
    convert_adr_to_home_price,
)


class DataConverterTests(unittest.TestCase):
    """数据转换与汇率处理模块单元测试。"""

    def test_parse_fx_ticker(self):
        """【UT-CONV-01: 汇率代码解析与标准化公式构建(CURRENCY前缀/正反向格式/异常拦截)】

        1. 测试功能与测试点:
           - 验证 parse_fx_ticker 解析多种形态外汇代码（如 'CURRENCY:USDJPY', 'EUR/USD', 'gbpusd'）。
           - 自动生成标准化代码与 GOOGLEFINANCE 报价公式，明确适用属性（price）与排除属性（pe）。
           - 拦截非法格式（单币种、同币种对冲、非字符串等）。

        2. 正常函数业务边界与参数契约:
           - 接收包含合法 3 字母 ISO 货币对的代码。
           - 返回标准字典包含 valid, base_currency, target_currency, standard_ticker 等。

        3. 测试数据与模拟场景说明:
           - 场景 1: 'CURRENCY:USDJPY'；场景 2: 'EUR/USD'；场景 3: 'gbpusd'；场景 4: 'USD', 'USDUSD', 12345。

        4. 预期断言与结果验证:
           - 合法代码 valid 为 True，base/target 货币解析正确。
           - 构造公式为 '=GOOGLEFINANCE("CURRENCY:USDJPY", "price")'。
           - 非法代码 valid 为 False。
        """
        # 1. 标准前缀格式
        res = parse_fx_ticker("CURRENCY:USDJPY")
        self.assertTrue(res["valid"])
        self.assertEqual(res["base_currency"], "USD")
        self.assertEqual(res["target_currency"], "JPY")
        self.assertEqual(res["standard_ticker"], "CURRENCY:USDJPY")
        self.assertEqual(res["google_finance_formula"], '=GOOGLEFINANCE("CURRENCY:USDJPY", "price")')
        self.assertIn("price", res["applicable_attributes"])
        self.assertIn("pe", res["inapplicable_attributes"])

        # 2. 简写与斜杠格式兼容
        res2 = parse_fx_ticker("EUR/USD")
        self.assertTrue(res2["valid"])
        self.assertEqual(res2["base_currency"], "EUR")
        self.assertEqual(res2["target_currency"], "USD")
        self.assertEqual(res2["standard_ticker"], "CURRENCY:EURUSD")

        res3 = parse_fx_ticker("gbpusd")
        self.assertTrue(res3["valid"])
        self.assertEqual(res3["base_currency"], "GBP")
        self.assertEqual(res3["target_currency"], "USD")

        # 3. 错误格式拒绝
        self.assertFalse(parse_fx_ticker("USD")["valid"])
        self.assertFalse(parse_fx_ticker("USDUSD")["valid"])
        self.assertFalse(parse_fx_ticker(12345)["valid"])
        self.assertFalse(parse_fx_ticker("INVALID_CODE")["valid"])

    def test_normalize_fx_quote(self):
        """【UT-CONV-02: 汇率报价规范化与倒数高精度反向汇率推算】

        1. 测试功能与测试点:
           - 验证 normalize_fx_quote 对原始外汇报价的规范化清洗。
           - 自动计算并保留高精度倒数反向汇率 (reciprocal_rate = 1.0 / rate)。
           - 严密拦截负数、零值及空值汇率报价。

        2. 正常函数业务边界与参数契约:
           - price 必须为正实数 (price > 0)。

        3. 测试数据与模拟场景说明:
           - USD/JPY 原始价格 159.00，时间戳 2026-10-11 15:30:00。

        4. 预期断言与结果验证:
           - status == 'ok'，rate == 159.00，reciprocal_rate ≈ 1.0 / 159.00。
           - 负数、零值、None 均抛出 ValueError。
        """
        raw = {
            "ticker": "CURRENCY:USDJPY",
            "price": 159.00,
            "tradetime": "2026-10-11 15:30:00",
        }
        res = normalize_fx_quote(raw, acquired_at="2026-10-11T09:50:00Z")
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["base_currency"], "USD")
        self.assertEqual(res["target_currency"], "JPY")
        self.assertAlmostEqual(res["rate"], 159.00)
        self.assertAlmostEqual(res["reciprocal_rate"], 1.0 / 159.00)
        self.assertEqual(res["as_of"], "2026-10-11T09:50:00Z")

        # 非法数值拒绝
        with self.assertRaises(ValueError):
            normalize_fx_quote({"ticker": "CURRENCY:USDJPY", "price": -10})
        with self.assertRaises(ValueError):
            normalize_fx_quote({"ticker": "CURRENCY:USDJPY", "price": 0})
        with self.assertRaises(ValueError):
            normalize_fx_quote({"ticker": "CURRENCY:USDJPY", "price": None})

    def test_currency_converter_cross_calculation(self):
        """【UT-CONV-03: 跨币种财务转换引擎(任天堂万亿日元现存款折算美元等商业案例)】

        1. 测试功能与测试点:
           - 验证 CurrencyConverter 多币种换算体系。
           - 覆盖同币种恒等映射、正向换算、基于倒数的反向换算及显式汇率覆盖。
           - 实测任天堂 (TYO:7974) J-GAAP 1.316万亿日元现金折算为 ~82.81 亿美元。

        2. 正常函数业务边界与参数契约:
           - 已注册相应货币对汇率，未注册抛出 ValueError。

        3. 测试数据与模拟场景说明:
           - USD/JPY 159.00，EUR/USD 1.0950。
           - 任天堂现金 1,316,680,000,000 JPY。

        4. 预期断言与结果验证:
           - 同币种有效汇率为 1.0。
           - 100 USD -> 15900 JPY。
           - 1.316万亿日元折算美元误差小于 0.01 美元。
           - 未注册的 GBP 抛出 ValueError。
        """
        converter = CurrencyConverter()
        converter.register_rate("USD/JPY", 159.00)
        converter.register_rate("EUR/USD", 1.0950)

        # 1. 同币种
        ident = converter.convert(1000, "USD", "USD")
        self.assertEqual(ident["converted_amount"], 1000.0)
        self.assertEqual(ident["effective_rate"], 1.0)

        # 2. USD -> JPY 正向换算
        res1 = converter.convert(100, "USD", "JPY")
        self.assertAlmostEqual(res1["converted_amount"], 15900.0)
        self.assertEqual(res1["conversion_pair"], "USD/JPY")

        # 3. JPY -> USD 反向自动换算（任天堂商业实测：1.316万亿日元现存款换算为美元）
        # 1,316,680,000,000 JPY / 159.00 = 8,281,006,289.31 USD (~82.81 亿美元)
        nintendo_jpy = 1316680000000
        res2 = converter.convert(nintendo_jpy, "JPY", "USD")
        expected_usd = nintendo_jpy / 159.00
        self.assertAlmostEqual(res2["converted_amount"], expected_usd, places=2)
        self.assertEqual(res2["target_currency"], "USD")
        self.assertIn("formula_applied", res2)

        # 4. 未注册币种拒绝
        with self.assertRaises(ValueError):
            converter.convert(100, "GBP", "USD")

        # 5. 显式覆盖汇率
        res3 = converter.convert(100, "USD", "JPY", rate=150.0)
        self.assertEqual(res3["converted_amount"], 15000.0)
        self.assertEqual(res3["conversion_type"], "explicit_override")

    def test_market_quote_validation_and_mu_cleansing(self):
        """【UT-CONV-04: 股票行情自洽性检查与量纲异常探测(美光MU 10x异常清洗与修复)】

        1. 测试功能与测试点:
           - 验证 validate_and_clean_market_quote 自动探测行情源的数据污染与量纲失真。
           - 核心修复案例: 美光科技 (MU) 历史行情数据源发生 10x 异常放大 (现价 $1029.0，市值 1.16万亿，EPS 74.34)。
           - 自动检测并识别 scale_factor_10x 异常，精准缩放清洗为正常量纲 ($102.9，市值 1162亿，EPS 7.434)。

        2. 正常函数业务边界与参数契约:
           - 输入包含 price, marketcap, pe, eps, high52, low52 字段。
           - 返回 clean_quote 及 anomalies 异常诊断列表。

        3. 测试数据与模拟场景说明:
           - 正常标的: EOG (现价 148.16，市值 777亿)。
           - 异常标的: MU (现价 1029.0，市值 1.16万亿)。

        4. 预期断言与结果验证:
           - EOG is_clean 为 True，无异常诊断。
           - MU is_clean 为 False，识别出 scale_factor_10x，清洗后现价精确等于 102.9。
        """
        # 正常股票测试 (EOG)
        normal_quote = {
            "ticker": "NYSE:EOG",
            "fields": {
                "price": {"value": 148.16},
                "currency": {"value": "USD"},
                "marketcap": {"value": 77714233376},
                "pe": {"value": 11.53},
                "eps": {"value": 12.85},
                "high52": {"value": 170.0},
                "low52": {"value": 110.0},
            },
        }
        clean_res = validate_and_clean_market_quote(normal_quote)
        self.assertTrue(clean_res["is_clean"])
        self.assertEqual(len(clean_res["anomalies"]), 0)
        self.assertAlmostEqual(clean_res["implied_shares"], 77714233376 / 148.16, places=1)

        # 异常股票测试 (美光 MU: 1029 异常放大)
        mu_raw_quote = {
            "ticker": "NASDAQ:MU",
            "fields": {
                "price": {"value": 1029.0},
                "currency": {"value": "USD"},
                "marketcap": {"value": 1162145397000.0},
                "pe": {"value": 13.84},
                "eps": {"value": 74.34},
                "high52": {"value": 1255.0},
                "low52": {"value": 179.61},
            },
        }
        mu_check = validate_and_clean_market_quote(mu_raw_quote)
        self.assertFalse(mu_check["is_clean"])
        self.assertEqual(len(mu_check["anomalies"]), 1)
        self.assertEqual(mu_check["anomalies"][0]["type"], "scale_factor_10x")
        self.assertEqual(mu_check["anomalies"][0]["adjusted_value"], 102.9)

        # 验证清洗后的规范化数据
        cleaned_mu = mu_check["cleaned_quote"]
        self.assertEqual(cleaned_mu["fields"]["price"]["value"], 102.9)
        self.assertEqual(cleaned_mu["fields"]["marketcap"]["value"], 116214539700.0)
        self.assertAlmostEqual(cleaned_mu["fields"]["eps"]["value"], 7.434)
        self.assertEqual(cleaned_mu["fields"]["high52"]["value"], 125.5)
        self.assertAlmostEqual(cleaned_mu["fields"]["low52"]["value"], 17.961)

    def test_map_japan_security_and_adr_bridge(self):
        """【UT-CONV-05: 跨市场日股(东证TYO)与美股ADR代码/换算比率映射】

        1. 测试功能与测试点:
           - 验证 map_japan_security 实现东证 (TYO) 本土标的与纽交所/纳斯达克/OTC 美股 ADR 的静态穿透映射。
           - 覆盖丰田 (TM, 10.0x)、索尼 (SONY, 1.0x)、东京电子 (TOELY, 0.5x)、任天堂 (NTDOY, 0.2x)。
           - 未录入代码安全返回 mapped=False。

        2. 正常函数业务边界与参数契约:
           - 输入合法 TYO 前缀代码。

        3. 测试数据与模拟场景说明:
           - 丰田 TYO:7203, 索尼 TYO:6758, 东电 TYO:8035, 任天堂 TYO:7974, 未知 TYO:9999。

        4. 预期断言与结果验证:
           - 映射结果中 adr_ticker 与 adr_ratio 与官方契约完全一致。
           - 未知代码 mapped 为 False。
        """
        # 1. 丰田
        toyota = map_japan_security("TYO:7203")
        self.assertTrue(toyota["mapped"])
        self.assertEqual(toyota["adr_ticker"], "NYSE:TM")
        self.assertEqual(toyota["adr_ratio"], 10.0)

        # 2. 索尼
        sony = map_japan_security("TYO:6758")
        self.assertTrue(sony["mapped"])
        self.assertEqual(sony["adr_ticker"], "NYSE:SONY")
        self.assertEqual(sony["adr_ratio"], 1.0)

        # 3. 东京电子
        tel = map_japan_security("TYO:8035")
        self.assertTrue(tel["mapped"])
        self.assertEqual(tel["adr_ticker"], "OTCMKTS:TOELY")
        self.assertEqual(tel["adr_ratio"], 0.5)

        # 4. 任天堂
        ntd = map_japan_security("TYO:7974")
        self.assertTrue(ntd["mapped"])
        self.assertEqual(ntd["adr_ticker"], "OTCMKTS:NTDOY")
        self.assertEqual(ntd["adr_ratio"], 0.2)

        # 5. 未知代码拒绝
        self.assertFalse(map_japan_security("TYO:9999")["mapped"])

    def test_convert_adr_to_home_price(self):
        """【UT-CONV-06: 美股ADR价格反解为本土日元原生价格(任天堂/丰田无损对齐)】

        1. 测试功能与测试点:
           - 验证 convert_adr_to_home_price 根据 ADR 美元报价与实时美日汇率，反解本土原生交易货币 (JPY) 现价。
           - 执行买方机构业务标准: 日股必须显式展示日元 (円)，严禁强制折算为美元。

        2. 正常函数业务边界与参数契约:
           - adr_price > 0, usdjpy_rate > 0。
           - 公式: home_price = (adr_price / adr_ratio) * usdjpy_rate。

        3. 测试数据与模拟场景说明:
           - 场景 1: 任天堂 ADR $13.50，比率 0.2，汇率 159.00 -> 10,732.50 JPY。
           - 场景 2: 丰田 ADR $180.00，比率 10.0，汇率 159.00 -> 2,862.00 JPY。

        4. 预期断言与结果验证:
           - 任天堂 home_price 精确等于 10732.50，显示为 '10,732 円'。
           - 丰田 home_price 精确等于 2862.00，显示为 '2,862 円'。
        """
        # 任天堂: ADR $13.50, 比率 0.2, USD/JPY 159.00
        # (13.50 / 0.2) * 159.00 = 67.50 * 159.00 = 10,732.50 JPY -> 10,730 円
        res = convert_adr_to_home_price("TYO:7974", adr_price=13.50, usdjpy_rate=159.00)
        self.assertEqual(res["ticker"], "TYO:7974")
        self.assertEqual(res["company_name"], "Nintendo")
        self.assertEqual(res["home_currency"], "JPY")
        self.assertAlmostEqual(res["home_price"], 10732.50, places=2)
        self.assertEqual(res["home_price_rounded"], 10732)
        self.assertEqual(res["home_price_display"], "10,732 円")
        self.assertEqual(res["adr_ticker"], "OTCMKTS:NTDOY")

        # 丰田: ADR $180.00, 比率 10.0, USD/JPY 159.00
        # (180.00 / 10.0) * 159.00 = 18.0 * 159.00 = 2,862 JPY
        toyota_res = convert_adr_to_home_price("TYO:7203", adr_price=180.00, usdjpy_rate=159.00)
        self.assertAlmostEqual(toyota_res["home_price"], 2862.00, places=2)
        self.assertEqual(toyota_res["home_price_display"], "2,862 円")


if __name__ == "__main__":
    unittest.main()
