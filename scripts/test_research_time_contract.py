"""新版时间精度、旧版兼容、真实来源绑定及迁移回归；全程离线。"""
import copy
import json
from pathlib import Path
import socket
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from validate_knowledge_structure import ROOT as VK_ROOT
from validate_research import load, validate, instant
from data_store import LocalStore
from migrate_research_time_contract import migrate


def deny(*a, **kw):
    raise AssertionError("时间契约测试禁止网络")


socket.socket.connect = deny
socket.create_connection = deny

class TimeContractTests(unittest.TestCase):
    """新版时间精度、旧版兼容、真实来源绑定及迁移回归测试类。"""

    def setUp(self):
        self.old = load(ROOT / "examples/completed.synthetic.json")
        self.new = copy.deepcopy(self.old)
        self.new["schema_version"] = "1.1.0"
        for e in self.new["evidence"]:
            e.update(
                publication_precision="instant",
                published_date=instant(e["published_at"]).date().isoformat(),
            )

    def test_legacy_and_new_precise(self):
        """【FT-TIME-01: 旧版v1.0.0瞬时时间与新版v1.1.0精准时间精度双向兼容校验】

        1. 测试功能与测试点:
           - 验证旧版 1.0.0 规范（仅依赖 published_at 瞬时时间）合法通过校验。
           - 验证新版 1.1.0 规范（具备 publication_precision='instant' 与 published_date）合法通过校验。

        2. 正常函数业务边界与参数契约:
           - validate(record) 正常放行。

        3. 测试数据与模拟场景说明:
           - 基准 completed.synthetic.json 样本与其 v1.1.0 扩展副本。

        4. 预期断言与结果验证:
           - validate 均成功放行无异常抛出。
        """
        validate(self.old)
        validate(self.new)

    def test_date_only(self):
        """【UT-TIME-02: 仅日期精度(date)合法性与published_at为空断言】

        1. 测试功能与测试点:
           - 验证真实世界中许多官方公报/报纸仅披露日期（无具体几点几分）时的合法表达。
           - publication_precision='date' 且 published_at 为 None。

        2. 正常函数业务边界与参数契约:
           - 仅日期精度时，必须省略瞬时秒级时间戳。

        3. 测试数据与模拟场景说明:
           - 将证据 0 修改为 date 精度。

        4. 预期断言与结果验证:
           - validate(self.new) 校验通过。
        """
        self.new["evidence"][0].update(publication_precision="date", published_at=None)
        validate(self.new)

    def test_unknown(self):
        """【UT-TIME-03: 未知时间精度(unknown)与时间字段全部留空合法性核验】

        1. 测试功能与测试点:
           - 验证历史资料或非标文献发布时间不可考时的合规表达。
           - publication_precision='unknown' 且 published_at 与 published_date 均为 None。

        2. 正常函数业务边界与参数契约:
           - 未知精度下，发布时间字段保持为空，但可用时间仍然存在。

        3. 测试数据与模拟场景说明:
           - 将证据 0 修改为 unknown 精度。

        4. 预期断言与结果验证:
           - validate(self.new) 校验通过。
        """
        self.new["evidence"][0].update(publication_precision="unknown", published_at=None, published_date=None)
        validate(self.new)

    def test_legacy_null_rejected(self):
        """【UT-TIME-04: 旧版时间契约空published_at刚性阻断拦截】

        1. 测试功能与测试点:
           - 验证旧版 1.0.0 契约下，严禁 published_at 为空（防止无精度说明的非法遗漏）。

        2. 正常函数业务边界与参数契约:
           - 破坏性变异抛出 ValueError。

        3. 测试数据与模拟场景说明:
           - 将 self.old 的 published_at 置为 None。

        4. 预期断言与结果验证:
           - 抛出 ValueError。
        """
        self.old["evidence"][0]["published_at"] = None
        with self.assertRaises(ValueError):
            validate(self.old)

    def test_new_metadata_required(self):
        """【UT-TIME-05: 新版契约缺失publication_precision元数据阻断拦截】

        1. 测试功能与测试点:
           - 验证新版 1.1.0 契约必须显式声明 publication_precision 精度元数据。

        2. 正常函数业务边界与参数契约:
           - 缺失精度元数据必须抛出 ValueError。

        3. 测试数据与模拟场景说明:
           - 从 self.new 证据中删除 publication_precision 字段。

        4. 预期断言与结果验证:
           - 抛出 ValueError。
        """
        self.new["evidence"][0].pop("publication_precision")
        with self.assertRaises(ValueError):
            validate(self.new)

    def test_date_cannot_forge_midnight(self):
        """【UT-TIME-06: 仅日期精度伪造午夜时间戳(forge midnight)防伪拦截】

        1. 测试功能与测试点:
           - 严禁将仅有日期的来源伪造为午夜零点瞬时时间戳（如 00:00:00Z）。
           - 声明为 'date' 精度时若 published_at 不为 None，必须拒绝。

        2. 正常函数业务边界与参数契约:
           - 防伪要求：date 精度必须将 published_at 置为 None。

        3. 测试数据与模拟场景说明:
           - 仅修改 precision 为 'date' 但保留原瞬时时间戳。

        4. 预期断言与结果验证:
           - 抛出 ValueError。
        """
        self.new["evidence"][0]["publication_precision"] = "date"
        with self.assertRaises(ValueError):
            validate(self.new)

    def test_instant_cannot_be_null(self):
        """【UT-TIME-07: 瞬时精度(instant)时间戳为空非法变异拦截】

        1. 测试功能与测试点:
           - 声明为 'instant' 瞬时精度时，published_at 严禁为空。

        2. 正常函数业务边界与参数契约:
           - 精度与字段必须自洽匹配。

        3. 测试数据与模拟场景说明:
           - 保持 instant 精度，将 published_at 置为 None。

        4. 预期断言与结果验证:
           - 抛出 ValueError。
        """
        self.new["evidence"][0]["published_at"] = None
        with self.assertRaises(ValueError):
            validate(self.new)

    def test_unknown_cannot_carry_date(self):
        """【UT-TIME-08: 未知精度(unknown)携带具体日期矛盾变异拦截】

        1. 测试功能与测试点:
           - 声明为 'unknown' 未知精度时，严禁携带具体 published_date 日期。

        2. 正常函数业务边界与参数契约:
           - 逻辑矛盾拦截。

        3. 测试数据与模拟场景说明:
           - 将 precision 改为 unknown，保留原 published_date。

        4. 预期断言与结果验证:
           - 抛出 ValueError。
        """
        self.new["evidence"][0].update(publication_precision="unknown", published_at=None)
        with self.assertRaises(ValueError):
            validate(self.new)

    def test_date_mismatch_rejected(self):
        """【UT-TIME-09: 瞬时时间与发布日期不一致(mismatch)篡改拦截】

        1. 测试功能与测试点:
           - 验证瞬时时间 published_at 提取出的日期必须与 published_date 严格一致。
           - 人为篡改 published_date（如改为 2020-01-01）触发矛盾拦截。

        2. 正常函数业务边界与参数契约:
           - 双重时间字段一致性校验。

        3. 测试数据与模拟场景说明:
           - 注入不匹配的发布日期。

        4. 预期断言与结果验证:
           - 抛出 ValueError。
        """
        self.new["evidence"][0]["published_date"] = "2020-01-01"
        with self.assertRaises(ValueError):
            validate(self.new)

    def test_future_availability_with_unknown_publication(self):
        """【UT-TIME-10: 未知发布精度但可用时间穿越到未来时序违规拦截】

        1. 测试功能与测试点:
           - 即使发布时间未知，可用时间 available_at 严禁处于未来时点（如 2030 年）。

        2. 正常函数业务边界与参数契约:
           - 时序前视偏误绝对防御。

        3. 测试数据与模拟场景说明:
           - available_at 设为 2030-01-01T00:00:00Z。

        4. 预期断言与结果验证:
           - 抛出 ValueError。
        """
        self.new["evidence"][0].update(
            publication_precision="unknown",
            published_at=None,
            published_date=None,
            available_at="2030-01-01T00:00:00Z",
        )
        with self.assertRaises(ValueError):
            validate(self.new)

    def test_obviously_future_date_rejected(self):
        """【UT-TIME-11: 明显未来日期(2030年)发布时间穿越违规拦截】

        1. 测试功能与测试点:
           - 仅日期精度下，published_date 处于未来年份（2030 年）必须被坚决拦截。

        2. 正常函数业务边界与参数契约:
           - 日期不得晚于当前业务时点。

        3. 测试数据与模拟场景说明:
           - published_date 设为 2030-01-01。

        4. 预期断言与结果验证:
           - 抛出 ValueError。
        """
        self.new["evidence"][0].update(
            publication_precision="date",
            published_at=None,
            published_date="2030-01-01",
        )
        with self.assertRaises(ValueError):
            validate(self.new)

    def test_migration_does_not_complete_steps(self):
        """【IT-TIME-12: 时间契约迁移自动作废下游步骤(invalidated)与版本自增对账】

        1. 测试功能与测试点:
           - 验证从旧版时间契约迁移到新版契约时：
             * 修订版本号 revision 自增 1；
             * 迁移后的全量步骤自动置为 'invalidated'（防止未经重算直接沿用旧结果）；
             * 证据的精度元数据被合规初始化为 'instant'。

        2. 正常函数业务边界与参数契约:
           - migrate(old_record, migration_time) 返回新版记录字典。

        3. 测试数据与模拟场景说明:
           - 对 completed 合成样本执行版本迁移。

        4. 预期断言与结果验证:
           - result['revision'] == old['revision'] + 1。
           - 所有步骤状态为 'invalidated'。
           - 证据精度为 'instant'。
        """
        result = migrate(self.old, "2026-10-11T10:00:00Z")
        self.assertEqual(result["revision"], self.old["revision"] + 1)
        self.assertTrue(all(s["status"] == "invalidated" for s in result["steps"]))
        self.assertTrue(all(s["status"] == "completed" for s in self.old["steps"]))
        self.assertTrue(all(e["publication_precision"] == "instant" for e in result["evidence"]))

    def test_real_draft_and_source_precision_binding(self):
        """【FT-TIME-13: 真实草稿(Intuit)来源时间精度强绑定与精度冲突刚性阻断】

        1. 测试功能与测试点:
           - 读取 Intuit 真实投研证据草稿 data/financial/research-drafts/intu-2026-evidence-v1.json。
           - 验证真实标的 is_fictional 为 False，步骤为 pending。
           - 验证证据精度均为 'date' 且 published_at 为空。
           - 验证保存到 LocalStore 时若出现时间精度不一致，刚性抛出 '精度不一致' 异常。

        2. 正常函数业务边界与参数契约:
           - 来源元数据与研究草稿精度必须双向对齐。

        3. 测试数据与模拟场景说明:
           - 真实 INTU 证据草稿与来源映射。

        4. 预期断言与结果验证:
           - 篡改日期后 save_research 抛出 ValueError('精度不一致')。
        """
        path = ROOT / "data/financial/research-drafts/intu-2026-evidence-v1.json"
        record = load(path)
        validate(record)
        self.assertFalse(record["is_fictional"])
        self.assertTrue(all(s["status"] == "pending" for s in record["steps"]))
        self.assertTrue(all(e["published_at"] is None and e["publication_precision"] == "date" for e in record["evidence"]))
        mapping = load(path.with_suffix(".sources.json"))
        c = LocalStore()
        try:
            record["evidence"][0]["published_date"] = "2026-09-08"
            with self.assertRaisesRegex(ValueError, "精度不一致"):
                c.save_research(record, mapping)
        finally:
            c.close()

    def test_real_saved_draft_roundtrip(self):
        """【FT-TIME-14: 本地存储已保存草稿往返(roundtrip)完整性与v1.1.0模式断言】

        1. 测试功能与测试点:
           - 验证从 LocalStore 读取已归档的 intu-2026-financial-evidence-draft (rev 1)。
           - 往返读取后通过契约校验 validate(result)。
           - 验证证据项数量为 2，契约模式版本为 1.1.0。

        2. 正常函数业务边界与参数契约:
           - c.get_research 返回完整结构。

        3. 测试数据与模拟场景说明:
           - 本地 SQLite 账本底账。

        4. 预期断言与结果验证:
           - 校验通过，证据数为 2，schema_version == '1.1.0'。
        """
        c = LocalStore()
        try:
            result = c.get_research("intu-2026-financial-evidence-draft", 1)
            validate(result)
            self.assertEqual(len(result["evidence"]), 2)
            self.assertEqual(result["schema_version"], "1.1.0")
        finally:
            c.close()

    def test_store_rejects_contract_downgrade(self):
        """【UT-TIME-15: 本地账本版本回退契约降级(v1.1.0降至v1.0.0)刚性拒绝拦截】

        1. 测试功能与测试点:
           - 验证向数据账本存储新版 1.1.0 记录后，后续修订严禁降级为 1.0.0 旧版契约。
           - 刚性拦截抛出 '不能降级' 异常。

        2. 正常函数业务边界与参数契约:
           - 账本修订版本不可逆降级防御。

        3. 测试数据与模拟场景说明:
           - 构造独立测试账本，写入 1.1.0 后尝试写入 1.0.0 rev 2。

        4. 预期断言与结果验证:
           - 抛出 ValueError('不能降级')。
        """
        pending = load(ROOT / "examples/pending.synthetic.json")
        pending.update(schema_version="1.1.0", research_id="time-test-" + uuid.uuid4().hex)
        for e in pending["evidence"]:
            e.update(publication_precision="instant", published_date=instant(e["published_at"]).date().isoformat())
        c = LocalStore(".cache/time-contract-" + uuid.uuid4().hex)
        try:
            c.save_research(pending)
            pending.update(schema_version="1.0.0", revision=2)
            with self.assertRaisesRegex(ValueError, "不能降级"):
                c.save_research(pending)
        finally:
            c.close()

    def test_pending_migration_preserves_pending(self):
        """【IT-TIME-16: 待处理状态(pending)草稿迁移时保持未处理状态与基准时间守恒】

        1. 测试功能与测试点:
           - 验证针对处于待处理状态 (pending) 的研究记录执行迁移时，各步骤维持 pending 状态不被错误置为 invalidated。
           - 验证基准时点 as_of 在迁移前后严格守恒相等。

        2. 正常函数业务边界与参数契约:
           - migrate 针对 pending 记录的状态保持逻辑。

        3. 测试数据与模拟场景说明:
           - pending.synthetic.json 迁移样本。

        4. 预期断言与结果验证:
           - 所有步骤状态均为 pending。
           - new['as_of'] == old['as_of']。
        """
        old = load(ROOT / "examples/pending.synthetic.json")
        new = migrate(old, "2026-10-11T10:00:00Z")
        self.assertTrue(all(s["status"] == "pending" for s in new["steps"]))
        self.assertEqual(new["as_of"], old["as_of"])


if __name__ == "__main__":
    unittest.main()
