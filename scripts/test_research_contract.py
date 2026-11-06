"""回归检验拒绝路径，使用合成数据，无网络或项目外文件。"""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from validate_research import ValidationError, load, validate


class ResearchContractTests(unittest.TestCase):
    """投研契约、数据血缘、拒绝路径与状态机版本撤销回归测试类。"""

    def setUp(self):
        self.full = load(ROOT / "examples/completed.synthetic.json")

    def test_valid_synthetic_and_template_contracts(self):
        """【FT-RESCON-01: 合成数据基准(completed/pending/blocked)与研究模板契约校验通过断言】

        1. 测试功能与测试点:
           - 验证已完成、待处理与阻断状态的合成数据符合投研全流程契约。
           - 验证 knowledge/templates/research.pending.json 官方投研模板契约合法性。

        2. 正常函数业务边界与参数契约:
           - validate(record) 正常放行，无未处理异常。

        3. 测试数据与模拟场景说明:
           - completed.synthetic.json, pending.synthetic.json, blocked.synthetic.json, research.pending.json。

        4. 预期断言与结果验证:
           - validate 调用均成功返回 None。
        """
        for name in ("completed.synthetic.json", "pending.synthetic.json", "blocked.synthetic.json"):
            validate(load(ROOT / "examples" / name))
        validate(load(ROOT / "knowledge/templates/research.pending.json"))

    def test_structural_and_step_sequence_rejections(self):
        """【UT-RESCON-02: 必填字段缺失/未定义字段/步骤逆序与前序未过等结构拒绝拦截】

        1. 测试功能与测试点:
           - 缺必填字段 (pop subject)
           - 新增未定义字段 (unsupported=True)
           - 步骤顺序倒置 (reverse steps)
           - 前序未通过仍强行继续 (status="needs_review")
           - 过期上游版本伪装新步骤 (version=2)
           - 完成步骤无输出物 (output=None)

        2. 正常函数业务边界与参数契约:
           - 破坏性变异必须抛出 ValidationError 或 ValueError。

        3. 测试数据与模拟场景说明:
           - 动态变异 self.full 深拷贝结构。

        4. 预期断言与结果验证:
           - 变异操作均触发异常捕获。
        """
        for label, modify in [
            ("缺必填字段", lambda d: d.pop("subject")),
            ("新增未定义字段", lambda d: d.update(unsupported=True)),
            ("步骤顺序错误", lambda d: d["steps"].reverse()),
            ("前序未通过仍继续", lambda d: d["steps"][0].update(status="needs_review")),
            ("过期上游版本", lambda d: d["steps"][0].update(version=2)),
            ("完成步骤无输出", lambda d: d["steps"][3].update(output=None)),
        ]:
            with self.subTest(case=label):
                record = copy.deepcopy(self.full)
                modify(record)
                with self.assertRaises((ValidationError, ValueError)):
                    validate(record)

    def test_gate_and_evidence_integrity_rejections(self):
        """【UT-RESCON-03: 必需门槛未过/悬空证据/重复ID与跨目录越界路径等证据链拒绝拦截】

        1. 测试功能与测试点:
           - 必需门槛未通过 (result="fail")
           - 不能以不适用跳过门槛 (result="not_applicable")
           - 缺失关键门槛 (pop gates)
           - 悬空证据引用 (evidence_refs=["missing"])
           - 重复证据ID
           - 项目外相对路径 ("../outside.md")
           - 项目外绝对路径 ("C:/outside.md")
           - 远程非法证据 ("https://invalid.example")
           - URL 编码穿越路径 ("%2e%2e/outside.md")

        2. 正常函数业务边界与参数契约:
           - 任何证据篡改与路径越界均被拦截。

        3. 测试数据与模拟场景说明:
           - 变异证据元数据与路径字段。

        4. 预期断言与结果验证:
           - 变异操作均抛出 ValidationError 或 ValueError。
        """
        for label, modify in [
            ("必需门槛未通过", lambda d: d["steps"][0]["gates"][0].update(result="fail")),
            ("不能以不适用跳门槛", lambda d: d["steps"][0]["gates"][0].update(result="not_applicable")),
            ("缺门槛", lambda d: d["steps"][0]["gates"].pop()),
            ("悬空证据引用", lambda d: d["claims"][0].update(evidence_refs=["missing"])),
            ("重复证据ID", lambda d: d["evidence"].append(copy.deepcopy(d["evidence"][0]))),
            ("项目外路径", lambda d: d["evidence"][0].update(source_path="../outside.md")),
            ("项目外绝对路径", lambda d: d["evidence"][0].update(source_path="C:/outside.md")),
            ("远程证据", lambda d: d["evidence"][0].update(source_path="https://invalid.example")),
            ("编码穿越", lambda d: d["evidence"][0].update(source_path="%2e%2e/outside.md")),
        ]:
            with self.subTest(case=label):
                record = copy.deepcopy(self.full)
                modify(record)
                with self.assertRaises((ValidationError, ValueError)):
                    validate(record)

    def test_observation_and_calculation_rejections(self):
        """【UT-RESCON-04: 未知行业/未来证据/单位币种错配与未校验估值等计算拒绝拦截】

        1. 测试功能与测试点:
           - 未知行业 ID (industry_ids=["missing"])
           - 未知指标 ID (metric_id="missing")
           - 未来证据时序违规 (available_at="2026-10-12T12:00:00Z")
           - 未来观测违规
           - 无时区时间戳 (as_of="2026-10-10T12:00:00")
           - 无证据支撑的观测 (evidence_refs=[])
           - 缺失观测仍计算 (value=None, missing_reason="缺失")
           - 单位不匹配 (unit="ratio")
           - 价格币种缺失 (currency=None)
           - 假设引用类型错误 (assumption_refs=["c_fact"])
           - 未校验估值计算 (verification_status="unchecked")
           - 情景名称重复 (name="base")
           - 情景计算脱节 (value=999)
           - 概率不完整 (probability=.3)
           - 已知权重缺证据 (weight=.5)

        2. 正常函数业务边界与参数契约:
           - 严格断言抛出异常。

        3. 测试数据与模拟场景说明:
           - 变异财务事实、指标定义与情景参数。

        4. 预期断言与结果验证:
           - 均抛出 ValidationError 或 ValueError。
        """
        for label, modify in [
            ("未知行业", lambda d: d["subject"]["segments"][0].update(industry_ids=["missing"])),
            ("未知指标", lambda d: d["observations"][0].update(metric_id="missing")),
            ("未来证据", lambda d: d["evidence"][0].update(available_at="2026-10-12T12:00:00Z")),
            ("未来观测", lambda d: d["observations"][0].update(available_at="2026-10-12T12:00:00Z")),
            ("无时区时间", lambda d: d.update(as_of="2026-10-10T12:00:00")),
            ("无证据的观测", lambda d: d["observations"][0].update(evidence_refs=[])) ,
            ("缺失观测仍计算", lambda d: d["observations"][0].update(value=None, missing_reason="缺失")),
            ("单位不匹配", lambda d: d["observations"][0]["value"].update(unit="ratio")),
            ("价格币种缺失", lambda d: d["observations"][0]["value"].update(currency=None)),
            ("假设引用类型错误", lambda d: d["calculations"][0].update(assumption_refs=["c_fact"])),
            ("未校验估值计算", lambda d: d["calculations"][0].update(verification_status="unchecked")),
            ("情景重复", lambda d: d["steps"][3]["output"]["scenarios"][0].update(name="base")),
            ("情景计算脱节", lambda d: d["steps"][3]["output"]["scenarios"][0]["intrinsic_value_per_share"].update(value=999)),
            ("概率不完整", lambda d: d["steps"][3]["output"]["scenarios"][0].update(probability=.3)),
            ("已知权重缺证据", lambda d: d["subject"]["segments"][0].update(weight=.5)),
        ]:
            with self.subTest(case=label):
                record = copy.deepcopy(self.full)
                modify(record)
                with self.assertRaises((ValidationError, ValueError)):
                    validate(record)

    def test_portfolio_action_and_fictional_boundaries(self):
        """【FT-RESCON-05: 未评估组合强赋仓位/合成研究冒充真实行动与过期监控等行为边界拦截】

        1. 测试功能与测试点:
           - 未评估组合却分配仓位 (position_fraction=.2)
           - 合成研究触发投资行动 (decision="action_conditions_met")
           - 合成证据伪装真实 (is_fictional=False)
           - 监控时间过期 (next_review_at="2026-10-01T00:00:00Z")

        2. 正常函数业务边界与参数契约:
           - 严格遵守投资风控防御红线。

        3. 测试数据与模拟场景说明:
           - 变异组合决策字段与虚构标记。

        4. 预期断言与结果验证:
           - 均抛出 ValidationError 或 ValueError。
        """
        for label, modify in [
            ("未评估组合却给仓位", lambda d: d["steps"][4]["output"].update(position_fraction=.2)),
            ("合成研究行动", lambda d: d["steps"][4]["output"].update(decision="action_conditions_met")),
            ("合成证据伪装真实", lambda d: d.update(is_fictional=False)),
            ("监控时间过期", lambda d: d["steps"][5]["output"].update(next_review_at="2026-10-01T00:00:00Z")),
        ]:
            with self.subTest(case=label):
                record = copy.deepcopy(self.full)
                modify(record)
                with self.assertRaises((ValidationError, ValueError)):
                    validate(record)

    def test_invalidation_events_and_downstream_rollback(self):
        """【IT-RESCON-06: 假说推翻回退事件(invalidation_events)下游版本级联撤销与闭环解决】

        1. 测试功能与测试点:
           - 验证回退事件发生时不撤销下游状态被刚性拒绝 (回退不撤销下游)。
           - 验证回退范围不完整被刚性拒绝 (回退范围不完整)。
           - 验证合法回退状态：下游步骤置为 'invalidated' 时校验通过。
           - 验证回退解决闭环：状态置为 'resolved'，各步骤升级至 version=2，依赖版本同步递增。

        2. 正常函数业务边界与参数契约:
           - 状态机版本演化一致性保障。

        3. 测试数据与模拟场景说明:
           - 构造针对 S2 的 rerun 回退事件，级联影响 S2~S6。

        4. 预期断言与结果验证:
           - 异常回退均抛错；规范回退与解决均校验通过。
        """
        event = {
            "id": "rerun",
            "occurred_at": "2026-10-10T13:00:00Z",
            "reason": "新证据推翻S2",
            "evidence_refs": ["e_counter"],
            "earliest_step": "S2",
            "affected_steps": ["S2", "S3", "S4", "S5", "S6"],
            "status": "open",
            "baseline_versions": [{"step_id": f"S{i}", "version": 1} for i in range(2, 7)],
            "resolved_at": None,
        }

        # 1. 回退不撤销下游 -> 必须拒绝
        bad_record = copy.deepcopy(self.full)
        bad_record["invalidation_events"].append(copy.deepcopy(event))
        with self.assertRaises((ValidationError, ValueError)):
            validate(bad_record)

        # 2. 回退范围不完整 -> 必须拒绝
        bad_scope = copy.deepcopy(self.full)
        bad_scope["invalidation_events"].append({**event, "affected_steps": ["S2"]})
        with self.assertRaises((ValidationError, ValueError)):
            validate(bad_scope)

        # 3. 合法级联回退 (S2~S6 标记为 invalidated) -> 校验通过
        invalidated = copy.deepcopy(self.full)
        invalidated["invalidation_events"] = [event]
        for s in invalidated["steps"][1:]:
            s["status"] = "invalidated"
        validate(invalidated)

        # 4. 合法解决回退 (S2~S6 升至 version=2) -> 校验通过
        resolved = copy.deepcopy(self.full)
        resolved["invalidation_events"] = [copy.deepcopy(event)]
        resolved["invalidation_events"][0].update(status="resolved", resolved_at="2026-10-10T14:00:00Z")
        for s in resolved["steps"][1:]:
            s["version"] = 2
            s["updated_at"] = "2026-10-10T14:00:00Z"
            for dep in s["inputs"]["dependencies"]:
                if dep["step_id"] != "S1":
                    dep["version"] = 2
        validate(resolved)


def main():
    """兼容历史直接调用契约输出。"""
    suite = unittest.TestLoader().loadTestsFromTestCase(ResearchContractTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
    print("PASS: 6 valid records; 36 invalid cases rejected.")


if __name__ == "__main__":
    main()
