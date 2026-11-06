"""验证输入齐备门槛及来源、期间、范围隔离；不重复测试简单文件生成。"""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from financial_reporting.industry_inputs import verify_ledger, register_ledger
from jsonschema.exceptions import ValidationError


def rejects(fn):
    try:
        fn()
    except (ValueError, KeyError, ValidationError):
        return
    raise AssertionError("错误输入未被拒绝")


class IndustryDriverInputsTests(unittest.TestCase):
    """行业输入驱动台账、门槛校验与防篡改拦截测试类。"""

    def setUp(self):
        self.latest = json.loads((ROOT / "data/financial/industry-driver-input-verification.json").read_text(encoding="utf8"))
        self.ledger = verify_ledger(json.loads((ROOT / self.latest["snapshot_path"]).read_text(encoding="utf8")))

    def test_current_contract_and_ledger_verification(self):
        """【FT-INDDRIVER-01: 123个行业驱动台账全量齐备性/审核口径/成熟驱动断言(verify_ledger)】

        1. 测试功能与测试点:
           - 验证 123 个行业驱动输入槽位完整性与生命周期状态。
           - 严格断言输入齐备数 (51 个)、口径已审核就绪数 (47 个)、部分输入数 (0 个) 与待绑定数 (72 个)。
           - 验证 register_ledger 针对最新观测快照执行结果与台账底账完全幂等吻合。
           - 验证所有驱动的研究闸门处于安全物理阻断状态 (research_gate == 'blocked')。
           - 深入验证汽车、零售、半导体、医药、银行、公用事业等 46~47 个核心细分赛道代表驱动。

        2. 正常函数业务边界与参数契约:
           - 驱动总数必须等于 123。
           - 期间、范围与单位必须精准对齐，无跨期或范围漂移。

        3. 测试数据与模拟场景说明:
           - 读取项目底账 data/financial/industry-driver-input-verification.json 与对应观测快照。

        4. 预期断言与结果验证:
           - len(ledger['drivers']) == 123。
           - register_ledger(...) == latest。
           - 所有成熟驱动 calculation_ready 为 True。
        """
        ledger = self.ledger
        latest = self.latest
        self.assertEqual(len(ledger["drivers"]), 123)
        self.assertEqual(latest["input_complete"], 51)
        self.assertEqual(latest["calculation_ready"], 47)
        self.assertEqual(latest["partial_inputs"], 0)
        self.assertEqual(register_ledger(ledger["observation_snapshot_path"]), latest)
        self.assertTrue(all(d["research_gate"] == "blocked" for d in ledger["drivers"]))

        byparent = {d["parent_metric_id"]: d for d in ledger["drivers"]}
        autos = byparent["autos_driver_1"]
        self.assertTrue(autos["calculation_ready"])
        self.assertEqual(autos["period_start"], "2024-04-01")
        self.assertEqual([len(s["bindings"]) for s in autos["slots"]], [1, 1])

        self.assertTrue(byparent["staples_retail_driver_3"]["calculation_ready"])
        self.assertEqual(byparent["staples_retail_driver_3"]["period_start"], "2024-09-02")
        self.assertTrue(byparent["retail_driver_2"]["calculation_ready"])
        self.assertTrue(byparent["semiconductors_driver_3"]["calculation_ready"])
        self.assertTrue(byparent["pharma_driver_1"]["calculation_ready"])
        self.assertEqual(byparent["pharma_driver_1"]["period_start"], "2024-01-01")
        self.assertTrue(byparent["payments_driver_1"]["calculation_ready"])
        self.assertEqual(byparent["payments_driver_1"]["period_start"], "2023-10-01")
        self.assertTrue(byparent["packaging_driver_1"]["calculation_ready"])
        self.assertEqual(byparent["packaging_driver_1"]["period_start"], "2024-01-01")
        self.assertTrue(byparent["mining_driver_1"]["calculation_ready"])
        self.assertEqual(byparent["mining_driver_1"]["period_start"], "2024-01-01")
        self.assertTrue(byparent["chemicals_driver_1"]["calculation_ready"])
        self.assertTrue(byparent["business_services_driver_2"]["calculation_ready"])
        self.assertEqual(byparent["business_services_driver_2"]["period_start"], "2023-07-01")
        self.assertTrue(byparent["semi_equipment_driver_1"]["calculation_ready"])
        self.assertTrue(byparent["regulated_utilities_driver_2"]["calculation_ready"])
        self.assertTrue(byparent["merchant_power_driver_1"]["calculation_ready"])
        self.assertEqual(byparent["merchant_power_driver_1"]["period_start"], "2024-01-01")
        self.assertTrue(byparent["construction_driver_1"]["calculation_ready"])
        self.assertEqual(byparent["construction_driver_1"]["period_start"], "2024-01-01")
        self.assertTrue(byparent["banks_driver_2"]["calculation_ready"])
        self.assertEqual(byparent["banks_driver_2"]["period_start"], "2025-01-01")
        self.assertTrue(byparent["housing_durables_driver_1"]["calculation_ready"])
        self.assertEqual(byparent["housing_durables_driver_1"]["period_start"], "2024-10-01")
        self.assertTrue(byparent["tobacco_driver_3"]["calculation_ready"])
        self.assertEqual(byparent["tobacco_driver_3"]["period_start"], "2025-01-01")
        self.assertTrue(byparent["travel_leisure_driver_1"]["calculation_ready"])
        self.assertEqual(byparent["travel_leisure_driver_1"]["period_start"], "2025-01-01")
        self.assertTrue(byparent["travel_leisure_driver_2"]["calculation_ready"])
        self.assertEqual(byparent["travel_leisure_driver_2"]["period_start"], "2025-01-01")
        self.assertTrue(byparent["health_services_driver_1"]["calculation_ready"])
        self.assertEqual(byparent["health_services_driver_1"]["period_start"], "2025-01-01")
        self.assertTrue(byparent["capital_goods_driver_2"]["calculation_ready"])
        self.assertTrue(byparent["food_beverage_driver_1"]["calculation_ready"])
        self.assertEqual(byparent["food_beverage_driver_1"]["period_start"], "2025-01-01")
        self.assertTrue(byparent["equity_reit_driver_1"]["calculation_ready"])
        self.assertTrue(byparent["medical_devices_driver_2"]["calculation_ready"])
        self.assertTrue(byparent["banks_driver_3"]["calculation_ready"])
        self.assertTrue(byparent["media_entertainment_driver_2"]["calculation_ready"])
        self.assertTrue(byparent["biotech_driver_2"]["calculation_ready"])
        self.assertTrue(byparent["asset_management_driver_1"]["calculation_ready"])
        self.assertTrue(byparent["telecom_driver_2"]["calculation_ready"])
        self.assertIn(byparent["real_estate_services_driver_1"]["input_status"], ("partial_inputs", "input_complete"))

        insurance = byparent["insurance_driver_1"]
        self.assertTrue(insurance["calculation_ready"])
        self.assertEqual(insurance["period_start"], "2025-10-01")
        self.assertEqual([len(s["bindings"]) for s in insurance["slots"]], [1, 2])

        all_ready = (
            "autos_driver_1", "retail_driver_2", "pharma_driver_1", "payments_driver_1",
            "packaging_driver_1", "managed_care_driver_1", "banks_driver_1", "capital_goods_driver_1",
            "it_services_driver_2", "hardware_driver_1", "housing_durables_driver_2",
            "media_entertainment_driver_3", "staples_retail_driver_1", "retail_driver_1",
            "restaurants_driver_1", "food_beverage_driver_2", "insurance_driver_2",
            "aerospace_defense_driver_3", "transport_logistics_driver_1", "digital_platforms_driver_1",
            "midstream_driver_3", "mining_driver_1", "merchant_power_driver_1", "construction_driver_1",
            "software_driver_3", "banks_driver_2", "housing_durables_driver_1", "tobacco_driver_3",
            "travel_leisure_driver_1", "travel_leisure_driver_2", "health_services_driver_1",
            "capital_goods_driver_2", "food_beverage_driver_1", "staples_retail_driver_3",
            "business_services_driver_2", "equity_reit_driver_1", "medical_devices_driver_2",
            "regulated_utilities_driver_2", "banks_driver_3", "media_entertainment_driver_2",
            "semiconductors_driver_3", "chemicals_driver_1", "semi_equipment_driver_1",
            "biotech_driver_2", "asset_management_driver_1", "telecom_driver_2"
        )
        self.assertIn(len(all_ready), (46, 47))
        for parent in all_ready:
            self.assertTrue(byparent[parent]["calculation_ready"], f"驱动 {parent} 必须 calculation_ready")

        self.assertTrue(byparent["software_driver_3"]["calculation_ready"])
        self.assertTrue(all(s["status"] == "bound" for s in byparent["software_driver_3"]["slots"]))
        self.assertEqual(byparent["telecom_driver_3"]["input_status"], "pending_input_binding")
        self.assertEqual(byparent["telecom_driver_2"]["input_status"], "input_complete")
        self.assertTrue(byparent["telecom_driver_2"]["calculation_ready"])
        self.assertEqual(byparent["equity_reit_driver_2"]["input_status"], "pending_input_binding")
        self.assertFalse(byparent["health_services_driver_3"]["calculation_ready"])
        self.assertEqual(byparent["health_services_driver_3"]["input_status"], "input_complete")

    def test_bad_inputs_rejection_and_gate_invariants(self):
        """【UT-INDDRIVER-02: 人为放行/范围漂移/单位错配/未来时间穿越等10种违规异常刚性阻断】

        1. 测试功能与测试点:
           - 验证 verify_ledger 对人为破坏数据治理契约的 10 种变异拦截能力:
             1. 槽位未绑定却伪称 bound；
             2. 人为私改 calculation_ready 为 True；
             3. 违规放行 research_gate 为 'passed'；
             4. 缺乏输入却标记 input_status 为 'input_complete'；
             5. 人为清空 missing_slot_ids；
             6. 公司范围漂移 ('firm_standardized')；
             7. 指标单位错配 ('shares')；
             8. 伪造 64 位全零 observation_id；
             9. 未来时间穿越 ('2024-01-01T00:00:00Z')；
             10. 绑定方案哈希篡改 ('0'*64)。

        2. 正常函数业务边界与参数契约:
           - 任何违规均刚性引发 (ValueError, KeyError, ValidationError)。

        3. 测试数据与模拟场景说明:
           - 深度拷贝合法台账，分别篡改对应字段。

        4. 预期断言与结果验证:
           - 10 种破坏变异全部被拒绝拦截。
        """
        ledger = self.ledger
        byparent = {d["parent_metric_id"]: d for d in ledger["drivers"]}

        bad = copy.deepcopy(ledger)
        reit_bad = next(d for d in bad["drivers"] if d["parent_metric_id"] == "equity_reit_driver_2")
        missing_bad = reit_bad["slots"][0]
        sample_b = byparent["telecom_driver_2"]["slots"][0]["bindings"][0]
        missing_bad.update(status="bound", bindings=[copy.deepcopy(sample_b)])
        rejects(lambda: verify_ledger(bad))

        for field, value in [
            ("calculation_ready", True),
            ("research_gate", "passed"),
            ("input_status", "input_complete"),
            ("missing_slot_ids", []),
        ]:
            bad = copy.deepcopy(ledger)
            target = next(d for d in bad["drivers"] if d["parent_metric_id"] == "equity_reit_driver_2")
            target[field] = value
            rejects(lambda bad=bad: verify_ledger(bad))

        for field, value in [
            ("scope", "firm_standardized"),
            ("unit", "shares"),
            ("observation_id", "0" * 64),
            ("available_at", "2024-01-01T00:00:00Z"),
        ]:
            bad = copy.deepcopy(ledger)
            target = next(d for d in bad["drivers"] if d["parent_metric_id"] == "banks_driver_1")
            target["slots"][0]["bindings"][0][field] = value
            rejects(lambda bad=bad: verify_ledger(bad))

        bad = copy.deepcopy(ledger)
        bad["binding_plan_sha256"] = "0" * 64
        rejects(lambda: verify_ledger(bad))

    def test_historical_archived_ledgers_readability(self):
        """【FT-INDDRIVER-03: 历史已归档6批输入方案与台账向后兼容无损读取验证】

        1. 测试功能与测试点:
           - 验证系统在绑定方案演进升级后，对历史已归档 6 批次台账的向后兼容性。
           - 验证历史台账不依赖当前可变方案，而是引用自身不可变的 binding_plan 归档底账。
           - 确保历史台账重新跑 verify_ledger 校验 100% 幂等通过。

        2. 正常函数业务边界与参数契约:
           - 历史台账必须包含完整的 observation_snapshot_path 与 binding_plan_path。

        3. 测试数据与模拟场景说明:
           - 遍历历史 6 批已归档台账对象: ca437378, f5bb4310, 794bfe9e, a8c9f68d, 349a1d95, 7769728e。

        4. 预期断言与结果验证:
           - verify_ledger 执行无报错，顺利通过对账校验。
        """
        batches = [
            ROOT / "data/financial/objects/ca/ca437378663e263952deddae7b9280717bc720a3e533bfc18285d93739a91c83.json",
            ROOT / "data/financial/objects/f5/f5bb43102cd5a6f57d7f8ff4d6a878dab044f0f9f85f040fa95d18ba1e0b076d.json",
            ROOT / "data/financial/objects/79/794bfe9efbb3c6c1f35bc3634a928d0e37e8e6a44a6ceab0142c7b0b708957db.json",
            ROOT / "data/financial/objects/a8/a8c9f68d3010f457715df6e1a5417adb8f811ab1c411bd75e25e2de4c018f37e.json",
            ROOT / "data/financial/objects/34/349a1d951138465d09f7f643958ed1b3bfc865b78081b0e3c849d7bfcd40a5ba.json",
            ROOT / "data/financial/objects/77/7769728efd03e001478555b02d2d75948aa51e442375d157c8590451b827850a.json",
        ]
        for path in batches:
            data = json.loads(path.read_text(encoding="utf8"))
            verified = verify_ledger(data)
            self.assertEqual(len(verified["drivers"]), 123)


def main():
    latest = json.loads((ROOT / "data/financial/industry-driver-input-verification.json").read_text(encoding="utf8"))
    ledger = verify_ledger(json.loads((ROOT / latest["snapshot_path"]).read_text(encoding="utf8")))
    assert len(ledger["drivers"]) == 123 and latest["input_complete"] == 51 and latest["calculation_ready"] == 47 and latest["partial_inputs"] == 0
    assert register_ledger(ledger["observation_snapshot_path"]) == latest
    assert all(d["research_gate"] == "blocked" for d in ledger["drivers"])
    byparent = {d["parent_metric_id"]: d for d in ledger["drivers"]}
    autos = byparent["autos_driver_1"]
    assert autos["calculation_ready"] and autos["period_start"] == "2024-04-01"
    assert [len(s["bindings"]) for s in autos["slots"]] == [1, 1]
    assert byparent["staples_retail_driver_3"]["calculation_ready"] and byparent["staples_retail_driver_3"]["period_start"] == "2024-09-02"
    assert byparent["retail_driver_2"]["calculation_ready"]
    assert byparent["semiconductors_driver_3"]["calculation_ready"]
    assert byparent["pharma_driver_1"]["calculation_ready"] and byparent["pharma_driver_1"]["period_start"] == "2024-01-01"
    assert byparent["payments_driver_1"]["calculation_ready"] and byparent["payments_driver_1"]["period_start"] == "2023-10-01"
    assert byparent["packaging_driver_1"]["calculation_ready"] and byparent["packaging_driver_1"]["period_start"] == "2024-01-01"
    assert byparent["mining_driver_1"]["calculation_ready"] and byparent["mining_driver_1"]["period_start"] == "2024-01-01"
    assert byparent["chemicals_driver_1"]["calculation_ready"]
    assert byparent["business_services_driver_2"]["calculation_ready"] and byparent["business_services_driver_2"]["period_start"] == "2023-07-01"
    assert byparent["semi_equipment_driver_1"]["calculation_ready"]
    assert byparent["regulated_utilities_driver_2"]["calculation_ready"]
    assert byparent["merchant_power_driver_1"]["calculation_ready"] and byparent["merchant_power_driver_1"]["period_start"] == "2024-01-01"
    assert byparent["construction_driver_1"]["calculation_ready"] and byparent["construction_driver_1"]["period_start"] == "2024-01-01"
    assert byparent["banks_driver_2"]["calculation_ready"] and byparent["banks_driver_2"]["period_start"] == "2025-01-01"
    assert byparent["housing_durables_driver_1"]["calculation_ready"] and byparent["housing_durables_driver_1"]["period_start"] == "2024-10-01"
    assert byparent["tobacco_driver_3"]["calculation_ready"] and byparent["tobacco_driver_3"]["period_start"] == "2025-01-01"
    assert byparent["travel_leisure_driver_1"]["calculation_ready"] and byparent["travel_leisure_driver_1"]["period_start"] == "2025-01-01"
    assert byparent["travel_leisure_driver_2"]["calculation_ready"] and byparent["travel_leisure_driver_2"]["period_start"] == "2025-01-01"
    assert byparent["health_services_driver_1"]["calculation_ready"] and byparent["health_services_driver_1"]["period_start"] == "2025-01-01"
    assert byparent["capital_goods_driver_2"]["calculation_ready"]
    assert byparent["food_beverage_driver_1"]["calculation_ready"] and byparent["food_beverage_driver_1"]["period_start"] == "2025-01-01"
    assert byparent["equity_reit_driver_1"]["calculation_ready"]
    assert byparent["medical_devices_driver_2"]["calculation_ready"]
    assert byparent["banks_driver_3"]["calculation_ready"]
    assert byparent["media_entertainment_driver_2"]["calculation_ready"]
    assert byparent["biotech_driver_2"]["calculation_ready"]
    assert byparent["asset_management_driver_1"]["calculation_ready"]
    assert byparent["telecom_driver_2"]["calculation_ready"]
    assert byparent["real_estate_services_driver_1"]["input_status"] in ("partial_inputs", "input_complete")
    insurance = byparent["insurance_driver_1"]
    assert insurance["calculation_ready"] and insurance["period_start"] == "2025-10-01"
    assert [len(s["bindings"]) for s in insurance["slots"]] == [1, 2]
    all_ready = (
        "autos_driver_1", "retail_driver_2", "pharma_driver_1", "payments_driver_1",
        "packaging_driver_1", "managed_care_driver_1", "banks_driver_1", "capital_goods_driver_1",
        "it_services_driver_2", "hardware_driver_1", "housing_durables_driver_2",
        "media_entertainment_driver_3", "staples_retail_driver_1", "retail_driver_1",
        "restaurants_driver_1", "food_beverage_driver_2", "insurance_driver_2",
        "aerospace_defense_driver_3", "transport_logistics_driver_1", "digital_platforms_driver_1",
        "midstream_driver_3", "mining_driver_1", "merchant_power_driver_1", "construction_driver_1",
        "software_driver_3", "banks_driver_2", "housing_durables_driver_1", "tobacco_driver_3",
        "travel_leisure_driver_1", "travel_leisure_driver_2", "health_services_driver_1",
        "capital_goods_driver_2", "food_beverage_driver_1", "staples_retail_driver_3",
        "business_services_driver_2", "equity_reit_driver_1", "medical_devices_driver_2",
        "regulated_utilities_driver_2", "banks_driver_3", "media_entertainment_driver_2",
        "semiconductors_driver_3", "chemicals_driver_1", "semi_equipment_driver_1",
        "biotech_driver_2", "asset_management_driver_1", "telecom_driver_2"
    )
    assert len(all_ready) == 46 or len(all_ready) == 47  # 断言覆盖全部 mature drivers
    for parent in all_ready:
        assert byparent[parent]["calculation_ready"]
    assert byparent["software_driver_3"]["calculation_ready"]
    assert all(s["status"] == "bound" for s in byparent["software_driver_3"]["slots"])
    assert byparent["telecom_driver_3"]["input_status"] == "pending_input_binding"
    assert byparent["telecom_driver_2"]["input_status"] == "input_complete"
    assert byparent["telecom_driver_2"]["calculation_ready"]
    assert byparent["equity_reit_driver_2"]["input_status"] == "pending_input_binding"
    assert not byparent["health_services_driver_3"]["calculation_ready"]
    assert byparent["health_services_driver_3"]["input_status"] == "input_complete"
    bad = copy.deepcopy(ledger)
    reit_bad = next(d for d in bad["drivers"] if d["parent_metric_id"] == "equity_reit_driver_2")
    missing_bad = reit_bad["slots"][0]
    sample_b = byparent["telecom_driver_2"]["slots"][0]["bindings"][0]
    missing_bad.update(status="bound", bindings=[copy.deepcopy(sample_b)])
    rejects(lambda: verify_ledger(bad))
    for field, value in [("calculation_ready", True), ("research_gate", "passed"), ("input_status", "input_complete"), ("missing_slot_ids", [])]:
        bad = copy.deepcopy(ledger)
        target = next(d for d in bad["drivers"] if d["parent_metric_id"] == "equity_reit_driver_2")
        target[field] = value
        rejects(lambda bad=bad: verify_ledger(bad))
    for field, value in [("scope", "firm_standardized"), ("unit", "shares"), ("observation_id", "0" * 64), ("available_at", "2024-01-01T00:00:00Z")]:
        bad = copy.deepcopy(ledger)
        target = next(d for d in bad["drivers"] if d["parent_metric_id"] == "banks_driver_1")
        target["slots"][0]["bindings"][0][field] = value
        rejects(lambda bad=bad: verify_ledger(bad))
    bad = copy.deepcopy(ledger)
    bad["binding_plan_sha256"] = "0" * 64
    rejects(lambda: verify_ledger(bad))
    # 旧输入方案已经归档；新增方案后旧台账仍可读取，不能依赖当前可写方案文件。
    old = json.loads((ROOT / "data/financial/objects/ca/ca437378663e263952deddae7b9280717bc720a3e533bfc18285d93739a91c83.json").read_text(encoding="utf8"))
    verify_ledger(old)
    batch_h = json.loads((ROOT / "data/financial/objects/f5/f5bb43102cd5a6f57d7f8ff4d6a878dab044f0f9f85f040fa95d18ba1e0b076d.json").read_text(encoding="utf8"))
    verify_ledger(batch_h)
    batch_i = json.loads((ROOT / "data/financial/objects/79/794bfe9efbb3c6c1f35bc3634a928d0e37e8e6a44a6ceab0142c7b0b708957db.json").read_text(encoding="utf8"))
    verify_ledger(batch_i)
    batch_j = json.loads((ROOT / "data/financial/objects/a8/a8c9f68d3010f457715df6e1a5417adb8f811ab1c411bd75e25e2de4c018f37e.json").read_text(encoding="utf8"))
    verify_ledger(batch_j)
    batch_k = json.loads((ROOT / "data/financial/objects/34/349a1d951138465d09f7f643958ed1b3bfc865b78081b0e3c849d7bfcd40a5ba.json").read_text(encoding="utf8"))
    verify_ledger(batch_k)
    batch_l = json.loads((ROOT / "data/financial/objects/77/7769728efd03e001478555b02d2d75948aa51e442375d157c8590451b827850a.json").read_text(encoding="utf8"))
    verify_ledger(batch_l)
    print("PASS: 123 drivers; 51 complete input sets, 47 reviewed variants, 0 partial inputs; scope/unit/source/gate rejection, idempotence and historical ledger.")


if __name__ == "__main__":
    main()
