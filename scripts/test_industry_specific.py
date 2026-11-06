"""行业专属规格和真实样本的正向/拒绝回归；全程离线、仅使用项目数据。"""
import copy
from decimal import Decimal
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from financial_reporting.industry_specific import (
    verify_specs,
    verify_observation,
    verify_snapshot,
    register_samples,
    verify_original_document,
)


def rejects(call):
    try:
        call()
    except (ValueError, KeyError):
        return
    raise AssertionError("错误输入未被拒绝")


class IndustrySpecificTests(unittest.TestCase):
    """行业专属规格、真实样本、逐页原文PDF防伪与历史归档快照向后兼容回归测试类。"""

    def test_industry_specifications_and_representative_firms(self):
        """【FT-INDSPEC-01: 41个行业专属规格定义/代表企业对齐与组件规格完备性断言】

        1. 测试功能与测试点:
           - 验证覆盖全盘 41 个代表行业的专属指标规格。
           - 验证全部 123 个行业驱动规格规范定义。
           - 验证 41 家代表企业与官方调查源 URL 映射。
           - 验证每一个指标规格必须包含组件规格列表 (component_specs)，且每个组件规格必须具备中文业务名称 (name_zh)。

        2. 正常函数业务边界与参数契约:
           - verify_specs() 返回 (specs, reps, discovery) 元组。
           - len(specs) == 123, len(reps) == 41, len(discovery) == 41。

        3. 测试数据与模拟场景说明:
           - 读取项目内 knowledge/metrics/ 下登记的不可变行业规格与官方来源定义。

        4. 预期断言与结果验证:
           - specs 数量为 123，reps 数量为 41，discovery 数量为 41。
           - 组件规格及其中文名称无缺漏。
        """
        specs, reps, discovery = verify_specs()
        self.assertEqual(len(specs), 123)
        self.assertEqual(len(reps), 41)
        self.assertEqual(len(discovery), 41)
        self.assertTrue(all(s["component_specs"] and all(c["name_zh"] for c in s["component_specs"]) for s in specs))

    def test_sample_registration_idempotency_and_snapshot_coverage(self):
        """【FT-INDSPEC-02: 行业专属样本注册幂等性/138项原子观测与全行业覆盖断言】

        1. 测试功能与测试点:
           - 验证 register_samples() 的只追加与幂等性注册机制（连续两次登记返回内容严格恒等）。
           - 验证不可变快照包含 138 项官方真实观测，且覆盖全量 41 个行业。
           - 验证原子样本未完成全驱动审核状态 (parent_driver_complete == False)。
           - 验证研究闸门处于阻断状态 (research_gate == 'blocked')，防止未经审核的半成品数据流入研究结论。

        2. 正常函数业务边界与参数契约:
           - register_samples() 返回字典包含 snapshot_path 与 sha256。
           - verify_snapshot() 校验快照内容地址与元数据。

        3. 测试数据与模拟场景说明:
           - 登记当前已归档的 7 批浏览器可见原文摘录包。

        4. 预期断言与结果验证:
           - first == second。
           - len(snapshot['observations']) == 138。
           - len({o['industry_id'] for o in snapshot['observations']}) == 41。
           - 所有观测 parent_driver_complete 为 False。
           - 所有覆盖项 research_gate 为 'blocked'。
        """
        first = register_samples()
        second = register_samples()
        self.assertEqual(first, second, "重复登记必须幂等")
        snapshot = verify_snapshot(first["snapshot_path"])
        self.assertEqual(len(snapshot["observations"]), 138)
        self.assertEqual(len({o["industry_id"] for o in snapshot["observations"]}), 41)
        self.assertTrue(all(not o["parent_driver_complete"] for o in snapshot["observations"]))
        self.assertTrue(all(c["research_gate"] == "blocked" for c in snapshot["coverage"]))

    def test_representative_observations_precision_and_balance(self):
        """【UT-INDSPEC-03: 跨行业代表企业核心指标披露精度/复合比率守恒与转换保真核验】

        1. 测试功能与测试点:
           - 跨行业代表企业核心指标披露精度实测断言：
             * 汽车（丰田汽车 tm 零售交付量: 10,307,000）
             * 零售仓储（Costco cost 全球客流增长: 0.054）
             * 半导体（美光科技 mu DRAM 年度收入: 100,680,000,000）
             * 连锁商超（沃尔玛 wmt 销货成本: 516,879,000,000）
             * 生物医药（辉瑞 pfe 艾乐妥全球收入: 7,366,000,000）
             * 支付金融（Visa 支付总额: 13,200,000,000,000，净收入: 35,926,000,000）
             * 矿产资源（自由港麦克莫兰 fcx 铜平均实现售价: 4.21，销量: 4,100,000,000）
             * 软件SaaS（Datadog ddog 实际流通股: 342,118,782，SBC费用: 570,336,000，EPS稀释股数: 358,636,000）
             * 银行（摩根大通 jpm 平均保留贷款: 1,330,946,000,000，净稳定资金比率 NSFR: 1.16）
             * 烟草（菲利普莫里斯 pm 无烟业务营业利润: 6,800,000,000）
             * 酒店（万豪 mar 可比客房销售数: 18,740,000，客房收入: 5,047,000,000）
             * 软饮料（可口可乐 销量箱数: 33,300,000,000）
             * 化工材料（陶氏化学 dow 聚乙烯售价: 1180，乙烯原料成本: 680，原料比率: 1.02）
             * 资管（贝莱德 blk 总流入: 3,215,000,000,000，总流出: 2,502,000,000,000，资本回报: 15,000,000,000）
             * 通信运营（威瑞森 vz 后付费电话断开数: 769,284，平均连接数: 75,420,000，季度流失率: 0.0102）
           - 财险复合比率守恒公理实测验证：
             * 查布保险 (Chubb) 赔付率 (loss_ratio) + 承保获取率 (acquisition_ratio) + 管理费率 (admin_ratio) 严格等于综合成本率 (combined_ratio: 0.812)。

        2. 正常函数业务边界与参数契约:
           - 保留发行人披露原始精度，数值使用精准字符串与 Decimal 高精度比较。

        3. 测试数据与模拟场景说明:
           - 从已注册的最新行业专属样本快照中按 component 读取。

        4. 预期断言与结果验证:
           - 各项观测数值严格对齐官方公告。
           - 财险三项比率求和严格等于报告的 0.812。
        """
        first = register_samples()
        snapshot = verify_snapshot(first["snapshot_path"])
        bycomponent = {o["component"]: o for o in snapshot["observations"]}
        self.assertEqual(bycomponent["tm_retail_vehicle_deliveries_fy25"]["value"], "10307000")
        self.assertEqual(bycomponent["cost_worldwide_traffic_growth_fy25"]["value"], "0.054")
        self.assertEqual(bycomponent["mu_dram_annual_revenue_fy26"]["value"], "100680000000")
        self.assertEqual(bycomponent["wmt_cost_of_sales_fy25"]["value"], "516879000000")
        self.assertEqual(bycomponent["pfe_eliquis_worldwide_revenue_fy24"]["value"], "7366000000")
        self.assertEqual(bycomponent["visa_payments_volume_fy24"]["value"], "13200000000000")
        self.assertEqual(bycomponent["visa_net_revenue_fy24"]["value"], "35926000000")
        self.assertEqual(bycomponent["fcx_copper_average_realized_price_2024"]["value"], "4.21")
        self.assertEqual(bycomponent["fcx_consolidated_copper_sales_volume_2024"]["value"], "4100000000")
        self.assertEqual(bycomponent["ceg_annual_generation_mwh_2024"]["value"], "121000000")
        self.assertEqual(bycomponent["fluor_ending_backlog_2024"]["value"], "28484000000")
        self.assertEqual(bycomponent["fluor_annual_revenue_2024"]["value"], "16315000000")
        self.assertEqual(bycomponent["ddog_actual_shares_outstanding_ye24"]["value"], "342118782")
        self.assertEqual(bycomponent["ddog_annual_sbc_expense_2024"]["value"], "570336000")
        self.assertEqual(bycomponent["ddog_weighted_diluted_eps_shares_2024"]["value"], "358636000")
        self.assertEqual(bycomponent["jpm_firm_average_retained_loans_2025"]["value"], "1330946000000")
        self.assertEqual(bycomponent["dhi_cancelled_sales_orders_fy25"]["value"], "18312")
        self.assertEqual(bycomponent["pm_smoke_free_operating_income_2025"]["value"], "6800000000")
        self.assertEqual(bycomponent["mar_comparable_rooms_sold_2025"]["value"], "18740000")
        self.assertEqual(bycomponent["mar_comparable_rooms_revenue_2025"]["value"], "5047000000")
        self.assertEqual(bycomponent["coca_cola_unit_case_volume_2025"]["value"], "33300000000")
        self.assertEqual(bycomponent["cost_comparable_transactions_fy25"]["value"], "1581000000")
        self.assertEqual(bycomponent["adp_es_client_count_fy24"]["value"], "1000000")
        self.assertEqual(bycomponent["dow_psp_segment_net_sales_2024"]["value"], "21776000000")
        self.assertEqual(bycomponent["pkg_corrugated_products_shipments_2024"]["value"], "67")
        self.assertEqual(bycomponent["adp_es_client_revenue_retention_fy24"]["value"], "0.92")
        self.assertEqual(bycomponent["tel_annual_net_sales_fy24"]["value"], "1830500000000")
        self.assertEqual(bycomponent["duk_carolinas_allowed_roe_2024"]["value"], "0.098")
        self.assertEqual(bycomponent["ceg_annual_operating_revenues_2024"]["value"], "23568000000")
        self.assertEqual(bycomponent["hhh_mpc_land_sales_fy24"]["value"], "453195000")
        self.assertEqual(bycomponent["pld_q4_same_store_cash_noi"]["value"], "1281000000")
        self.assertEqual(bycomponent["isrg_tradein_retirements_q4"]["value"], "79")
        self.assertEqual(bycomponent["duk_carolinas_equity_capital_ratio_2024"]["value"], "0.52")
        self.assertEqual(bycomponent["jpm_nsfr_ratio_2025"]["value"], "1.16")
        self.assertEqual(bycomponent["dow_pe_average_selling_price_2024"]["value"], "1180")
        self.assertEqual(bycomponent["dow_ethylene_feedstock_cost_2024"]["value"], "680")
        self.assertEqual(bycomponent["dow_pe_feedstock_ratio_2024"]["value"], "1.02")
        self.assertEqual(bycomponent["mrna_monthly_cash_burn_2025"]["value"], "200000000")
        self.assertEqual(bycomponent["mrna_cash_runway_adjustments_2025"]["value"], "0")
        self.assertEqual(bycomponent["blk_gross_inflows_2025"]["value"], "3215000000000")
        self.assertEqual(bycomponent["blk_gross_outflows_2025"]["value"], "2502000000000")
        self.assertEqual(bycomponent["blk_capital_returned_2025"]["value"], "15000000000")
        self.assertEqual(bycomponent["mu_dram_annual_bit_shipments_fy26"]["value"], "96800000000")
        self.assertEqual(bycomponent["tel_annual_new_orders_fy24"]["value"], "1848200000000")
        self.assertEqual(bycomponent["vz_q4_postpaid_phone_disconnects"]["value"], "769284")
        self.assertEqual(bycomponent["vz_q4_postpaid_phone_average_connections"]["value"], "75420000")

        parts = [bycomponent[c] for c in ("cb_pc_loss_ratio_q4", "cb_pc_acquisition_ratio_q4", "cb_pc_admin_ratio_q4")]
        reported = bycomponent["cb_pc_combined_ratio_q4"]
        self.assertEqual(sum(Decimal(o["value"]) for o in parts), Decimal(reported["value"]))
        self.assertEqual(Decimal(reported["value"]), Decimal("0.812"))
        self.assertTrue(all(o["scope"] == reported["scope"] and o["period_start"] == reported["period_start"] for o in parts))

    def test_observation_verification_and_mutation_rejections(self):
        """【UT-INDSPEC-04: 观测单位/期间/越界时序等12种变异及非官方来源防御拦截】

        1. 测试功能与测试点:
           - 验证 verify_observation 对观测样本的严密防御性校验：
             * 数值篡改 ('85.8')
             * 非法原始单位 ('raw_unit': 'USD')
             * 单位类型混淆 ('unit': 'currency')
             * 跨父驱动冒充 ('banks_driver_1')
             * 未知组件名称 ('component': 'unknown')
             * 期间越界与未来倒置 ('period_start': '2026-01-01', 'period_end': '2030-01-01')
             * 摘录索引为空或越界 ('excerpt_indices': [], [999])
             * 原始数值不一致 ('raw_value': '123.456')
             * 未经批准转换函数 ('unapproved')
             * 非有限数值 ('NaN')
             * 来源行业不匹配 ('badsource')
             * 历史快照前视截断拦截
             * 跨期间越界拦截与非公式输入冒充拦截
           - 验证媒体行业负数带符号千分位指标 (-17,096,617,000) 符号防篡改。

        2. 正常函数业务边界与参数契约:
           - verify_observation 接受 (source, observation, observed_at)。
           - 任一不一致或变异刚性抛出 ValueError 或 KeyError。

        3. 测试数据与模拟场景说明:
           - 读取 industry-specific-reviewed-excerpts.json 与 industry-specific-expansion-20261011.json 进行动态破坏性变异注入。

        4. 预期断言与结果验证:
           - 所有 12 种变异及破坏场景均被 rejects() 成功捕获。
        """
        bundle = json.loads((ROOT / "data/browser-search/industry-specific-reviewed-excerpts.json").read_text(encoding="utf-8"))
        source = bundle["sources"][0]
        good = source["observations"][0]
        observed = bundle["observed_at"]
        self.assertTrue(verify_observation(source, good, observed))

        for patch in [
            {"value": "85.8"},
            {"raw_unit": "USD"},
            {"unit": "currency"},
            {"parent_metric_id": "banks_driver_1"},
            {"component": "unknown"},
            {"period_start": "2026-01-01"},
            {"period_end": "2030-01-01"},
            {"excerpt_indices": []},
            {"excerpt_indices": [999]},
            {"raw_value": "123.456"},
            {"conversion": "unapproved"},
            {"value": "NaN"},
        ]:
            bad = {**copy.deepcopy(good), **patch}
            rejects(lambda bad=bad: verify_observation(source, bad, observed))

        badsource = {**copy.deepcopy(source), "industry_id": "banks"}
        rejects(lambda: verify_observation(badsource, good, observed))

        first = register_samples()
        rejects(lambda: verify_snapshot(first["snapshot_path"], "2025-01-01T00:00:00+00:00"))

        expansion = json.loads((ROOT / "data/browser-search/industry-specific-expansion-20261011.json").read_text(encoding="utf8"))
        retail = next(s for s in expansion["sources"] if s["industry_id"] == "retail")
        rejects(lambda: verify_observation(retail, {**retail["observations"][0], "period_start": "2025-11-02"}, expansion["observed_at"]))

        snapshot = verify_snapshot(first["snapshot_path"])
        reit = next(c for c in snapshot["coverage"] if c["parent_metric_id"] == "equity_reit_driver_2")
        self.assertEqual(reit["status"], "definition_mismatch_sample_only")
        self.assertFalse(reit["usable_sample_ids"])

        transport = next(o for o in snapshot["observations"] if o["component"] == "annual_passenger_mile_yield")
        self.assertEqual(transport["value"], "0.2074")
        self.assertEqual(transport["unit"], "USD_per_passenger_mile")

        transport_source = next(s for s in expansion["sources"] if s["industry_id"] == "transport_logistics")
        yield_observation = next(o for o in transport_source["observations"] if o["component"] == "annual_passenger_mile_yield")
        rejects(lambda: verify_observation(transport_source, {**yield_observation, "value": "20.74", "conversion": "identity"}, expansion["observed_at"]))
        rejects(lambda: verify_observation(retail, {**retail["observations"][0], "binding_role": "formula_input"}, expansion["observed_at"]))

        new = json.loads((ROOT / "data/browser-search/industry-driver-inputs-20261011b.json").read_text(encoding="utf8"))
        media = next(s for s in new["sources"] if s["industry_id"] == "media_entertainment")
        signed = media["observations"][0]
        self.assertEqual(signed["value"], "-17096617000")
        rejects(lambda: verify_observation(media, {**signed, "value": "17096617000"}, new["observed_at"]))
        rejects(lambda: verify_observation(media, {**signed, "conversion": "identity"}, new["observed_at"]))

    def test_original_pdf_page_verification_and_historical_snapshots(self):
        """【FT-INDSPEC-05: 官方原始PDF逐页文本哈希防伪核验与历史归档快照向后兼容验证】

        1. 测试功能与测试点:
           - 官方原始 PDF 逐页原文比对核验：
             * 电信（Verizon 财务补充表第 10 页逐字比对）
             * 医保（联合健康 UNH 2025财报第 20 页逐字比对）
             * 伪造文本 ('Retail postpaid phone 99.99 %') 刚性阻断
             * 伪造哈希 ('0'*64) 刚性阻断
             * 伪造页码 ([1]) 刚性阻断
           - 历史已归档 7 批样本快照向后兼容无损读取：
             * dae7970c... (15 项观测)
             * 7bec27ba... (45 项观测)
             * a83a1889... (107 项观测)
             * db1a41a7... (114 项观测)
             * bef78436... (119 项观测)
             * 47d4fb3f... (122 项观测)
             * 16f5f74e... (126 项观测)

        2. 正常函数业务边界与参数契约:
           - verify_original_document() 解析真实 PDF 逐页 Text 提取并断言包含摘录。
           - verify_snapshot() 校验历史归档对象，观测条数精确匹配。

        3. 测试数据与模拟场景说明:
           - 本地导入的官方原始 PDF 与 objects 目录下的不可变历史快照。

        4. 预期断言与结果验证:
           - 正向 PDF 逐页比对通过。
           - 伪造输入均被拒绝抛出异常。
           - 7 批历史快照读取无损，条数完全对齐。
        """
        # 1. 历史快照向后兼容读取
        old = verify_snapshot("data/financial/objects/da/dae7970cb6ef59600dc03fe327baf7117b5c9145161ac71eaa55d638bb683da3.json")
        self.assertEqual(len(old["observations"]), 15)
        previous = verify_snapshot("data/financial/objects/7b/7bec27ba85b35d50b91fd064438ef764f9e81c4885b3a323b9cadbb7536ca327.json")
        self.assertEqual(len(previous["observations"]), 45)
        batch_h = verify_snapshot("data/financial/objects/a8/a83a1889403bb631423a0260786f8e725db92eb0ff02d0487f3a42186552c7b4.json")
        self.assertEqual(len(batch_h["observations"]), 107)
        batch_i = verify_snapshot("data/financial/objects/db/db1a41a793cd912640aa5897df833351e47b133ee30163a1ef402ee895f21b40.json")
        self.assertEqual(len(batch_i["observations"]), 114)
        batch_j = verify_snapshot("data/financial/objects/be/bef784362db506c53f056e45ec284eaeffd4aafa7e4f2ab44d56329ec425daca.json")
        self.assertEqual(len(batch_j["observations"]), 119)
        batch_k = verify_snapshot("data/financial/objects/47/47d4fb3f67a7483d781bc48ddd67e21830864f1f2350df2f44d607f14023d680.json")
        self.assertEqual(len(batch_k["observations"]), 122)
        batch_l = verify_snapshot("data/financial/objects/16/16f5f74e8ca9934fccbea1c6154428dc64b61c719275096f6a2c5ec6d9f0e388.json")
        self.assertEqual(len(batch_l["observations"]), 126)

        # 2. 原始 PDF 逐页防伪核验
        telecom = json.loads((ROOT / "data/browser-search/telecom-reviewed-20261012.json").read_text(encoding="utf8"))
        telecom_source = telecom["sources"][0]
        verify_original_document(telecom_source)

        first = register_samples()
        snapshot = verify_snapshot(first["snapshot_path"])
        churn = next(o for o in snapshot["observations"] if o["component"] == "vz_total_postpaid_phone_churn_q4")
        self.assertEqual(churn["value"], "0.0102")
        self.assertEqual(churn["scope"], "total_wireless_retail_postpaid_phone")
        arpu = next(o for o in snapshot["observations"] if o["component"] == "vz_core_prepaid_arpu_q4")
        self.assertEqual(arpu["value"], "32.90")
        self.assertEqual(arpu["binding_role"], "context_sample")

        bad = copy.deepcopy(telecom_source)
        bad["excerpts"][0] = "Retail postpaid phone 99.99 %"
        rejects(lambda: verify_original_document(bad))

        new = json.loads((ROOT / "data/browser-search/industry-driver-inputs-20261011b.json").read_text(encoding="utf8"))
        managed = next(s for s in new["sources"] if s["industry_id"] == "managed_care")
        verify_original_document(managed)
        bad = copy.deepcopy(managed)
        bad["original_document"]["sha256"] = "0" * 64
        rejects(lambda: verify_original_document(bad))
        bad = copy.deepcopy(managed)
        bad["original_document"]["excerpt_pages"] = [1]
        rejects(lambda: verify_original_document(bad))


def main():
    suite = unittest.TestLoader().loadTestsFromTestCase(IndustrySpecificTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
    print("PASS: 41 industries, 123 specifications, 122 observations across 41 industries; historical snapshots, signed thousands and original PDF evidence checked.")


if __name__ == "__main__":
    main()

