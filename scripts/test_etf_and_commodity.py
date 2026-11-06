"""全球 ETF 穿透与黄金大宗商品宏观框架单元测试与 Schema 校验."""

import json
import sys
import unittest
from pathlib import Path
from jsonschema import validate

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from financial_reporting.etf_penetration import (
    ETFPenetrationEngine,
    STANDARD_ETF_REGISTRY,
)
from financial_reporting.commodity_gold_framework import (
    CommodityGoldFramework,
    GoldMacroContext,
    STANDARD_GOLD_MINERS,
)


class TestETFAndCommodity(unittest.TestCase):
    def test_etf_overlap_between_spy_and_qqq(self):
        """【UT-ETF-01: SPY与QQQ核心指数ETF头部持仓加权穿透重叠度与共同标的检验】

        1. 测试功能与测试点:
           - 验证 ETFPenetrationEngine.calculate_overlap_between_two_etfs 双 ETF 持仓穿透加权算法。
           - 提取头部共同持仓标的 (如 AAPL, MSFT, NVDA, AMZN 等)。
           - 加权穿透重叠度 (Weighted Overlap Pct): 真实跨指数重叠权重。

        2. 正常函数业务边界与参数契约:
           - 输入为 STANDARD_ETF_REGISTRY 中标准定义的 ETF 字典或对象。
           - weighted_overlap_pct 处于 [0.0, 100.0] 区间。

        3. 测试数据与模拟场景说明:
           - 标的: SPY (标普500) 与 QQQ (纳斯达克100)。
           - 模拟大型科技成长股在这两个全球最大流动性指数 ETF 中的穿透重合度。

        4. 预期断言与结果验证:
           - 断言 weighted_overlap_pct >= 20.0% (实际约为 25%~46%)。
           - 断言 overlap_details 字典中明确包含关键巨头 'NVDA' 与 'MSFT'。
        """
        spy = STANDARD_ETF_REGISTRY["SPY"]
        qqq = STANDARD_ETF_REGISTRY["QQQ"]
        res = ETFPenetrationEngine.calculate_overlap_between_two_etfs(spy, qqq)
        # SPY 与 QQQ 前十大重叠权重通常超过 25%
        self.assertGreaterEqual(res["weighted_overlap_pct"], 20.0)
        self.assertIn("NVDA", res["overlap_details"])
        self.assertIn("MSFT", res["overlap_details"])

    def test_etf_dossier_schema_validation(self):
        """【FT-ETF-02: 行业ETF深度档案对schemas/etf_dossier.schema.json契约严格合法性校验】

        1. 测试功能与测试点:
           - 验证 ETFPenetrationEngine.analyze_etf_dossier 生成的深度档案完全符合 JSON Schema 规范。
           - 契约约束: 包含 ticker, category, concentration (top_10_weight_pct), expense_ratio 等必填契约。

        2. 正常函数业务边界与参数契约:
           - ticker 在 STANDARD_ETF_REGISTRY 中有效。
           - 校验文件: schemas/etf_dossier.schema.json。

        3. 测试数据与模拟场景说明:
           - 标的: 梵克半导体 ETF (SMH)。

        4. 预期断言与结果验证:
           - validate(instance=dossier, schema=schema) 无任何 Schema 校验错误抛出。
           - 断言 dossier["ticker"] == "SMH" 且 category == "Semiconductor"。
           - 断言 top_10_weight_pct > 50.0% (半导体龙头高集中度特征)。
        """
        schema_path = ROOT / "schemas" / "etf_dossier.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        dossier = ETFPenetrationEngine.analyze_etf_dossier("SMH")
        validate(instance=dossier, schema=schema)
        self.assertEqual(dossier["ticker"], "SMH")
        self.assertEqual(dossier["category"], "Semiconductor")
        self.assertGreater(dossier["concentration"]["top_10_weight_pct"], 50.0)

    def test_gold_macro_valuation_and_schema(self):
        """【FT-GOLD-03: 现货黄金宏观公允估值与schemas/commodity_gold.schema.json契约结构校验】

        1. 测试功能与测试点:
           - 验证 CommodityGoldFramework.evaluate_gold_macro_valuation 买方宏观黄金估值报告。
           - 验证生成的宏观报告 100% 契合 schemas/commodity_gold.schema.json 契约。
           - 穿透涵盖 10Y TIPS 真实利率锚、通胀补偿与主权央行去美元化储备结构性溢价 (central_bank_structural_premium)。

        2. 正常函数业务边界与参数契约:
           - 输入为 GoldMacroContext 对象 (spot_gold_usd_oz > 0, us_10y_nominal_yield > 0)。

        3. 测试数据与模拟场景说明:
           - 现货金价 $2650/oz，10Y 名义利率 4.40%，通胀预期 2.35%。

        4. 预期断言与结果验证:
           - validate(instance=gold_report, schema=schema) 验签成功。
           - 断言报告包含 'spot_gold_usd'、'tips_10y_real_yield' 与 'central_bank_structural_premium'。
        """
        schema_path = ROOT / "schemas" / "commodity_gold.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        ctx = GoldMacroContext(
            spot_gold_usd_oz=2650.0,
            us_10y_nominal_yield=0.0440,
            breakeven_inflation_10y=0.0235,
        )
        gold_report = CommodityGoldFramework.evaluate_gold_macro_valuation(ctx)
        validate(instance=gold_report, schema=schema)
        self.assertIn("spot_gold_usd", gold_report)
        self.assertIn("tips_10y_real_yield", gold_report)
        self.assertIn("central_bank_structural_premium", gold_report["valuation_models"])

    def test_gold_miner_operating_leverage(self):
        """【UT-GOLD-04: 特级金矿股龙头(NEM/AEM/PAAS)AISC营运杠杆放大倍数与公允目标价推导】

        1. 测试功能与测试点:
           - 验证 CommodityGoldFramework.evaluate_gold_miner_leverage 对三大特级金矿龙头公司的估值建模。
           - 全维持成本 (AISC) 现金毛利穿透: Spot Gold - AISC。
           - 营运杠杆乘数效应 (Operating Leverage Multiplier): 金矿股利润释放对金价上行的倍数弹性。
           - 自由现金流公允目标价推算。

        2. 正常函数业务边界与参数契约:
           - spot_gold_price > AISC。
           - 覆盖 NEM (纽蒙特), AEM (阿格尼科鹰), PAAS (泛美白银)。

        3. 测试数据与模拟场景说明:
           - 现货金价 $2650/oz；NEM (AISC $1440), AEM, PAAS (AISC $1350)。

        4. 预期断言与结果验证:
           - NEM: cash_margin_per_oz 包含 '1210' (2650 - 1440)，operating_leverage_multiplier 包含 'x'。
           - AEM: fair_target_price 数值 > $50.0。
           - PAAS: cash_margin_per_oz 包含 '1300' (2650 - 1350)。
        """
        nem = CommodityGoldFramework.evaluate_gold_miner_leverage("NEM", spot_gold_price=2650.0)
        self.assertEqual(nem["ticker"], "NEM")
        # AISC $1440，现价 $2650，现金毛利 $1210
        self.assertIn("1210", nem["cash_margin_per_oz"])
        # 营运杠杆倍数一般大于 1.5x
        self.assertIn("x", nem["operating_leverage_multiplier"])

        aem = CommodityGoldFramework.evaluate_gold_miner_leverage("AEM", spot_gold_price=2650.0)
        self.assertEqual(aem["ticker"], "AEM")
        self.assertGreater(float(aem["fair_target_price"].replace("$", "")), 50.0)

        paas = CommodityGoldFramework.evaluate_gold_miner_leverage("PAAS", spot_gold_price=2650.0)
        self.assertEqual(paas["ticker"], "PAAS")
        self.assertIn("1300", paas["cash_margin_per_oz"])

    def test_expanded_etf_registry_coverage(self):
        """【IT-ETF-05: 全球核心宽基与行业主题ETF资产底账覆盖度及Schema契约合规性】

        1. 测试功能与测试点:
           - 验证横向拓展战略授权覆盖的核心资产底账完备性。
           - 覆盖罗素2000小盘股 (IWM)、传统能源 (XLE)、生物科技突破 (XBI)、高红利防御 (VIG) 与长久期美债 (IEF)。
           - 断言全量子资产档案均能生成并通过 schemas/etf_dossier.schema.json 契约验证。

        2. 正常函数业务边界与参数契约:
           - STANDARD_ETF_REGISTRY 包含拓展清单。
           - 档案持仓列表 top_holdings 长度 > 0。

        3. 测试数据与模拟场景说明:
           - 遍历 ["IWM", "XLE", "XBI", "VIG", "IEF"] 逐一生成深度档案并校验。

        4. 预期断言与结果验证:
           - 断言每个标的均在注册表中。
           - validate(instance=dossier, schema=schema) 全部通过。
           - 断言 dossier["ticker"] 匹配且 top_holdings 列表非空。
        """
        schema_path = ROOT / "schemas" / "etf_dossier.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        for ticker in ["IWM", "XLE", "XBI", "VIG", "IEF"]:
            self.assertIn(ticker, STANDARD_ETF_REGISTRY)
            dossier = ETFPenetrationEngine.analyze_etf_dossier(ticker)
            validate(instance=dossier, schema=schema)
            self.assertEqual(dossier["ticker"], ticker)
            self.assertGreater(len(dossier["top_holdings"]), 0)


if __name__ == "__main__":
    unittest.main()
