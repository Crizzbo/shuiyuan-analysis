"""独立绑定方案契约：拒绝字段漂移、错误日期与跨驱动槽位。"""
import copy
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from financial_reporting.industry_inputs import validate_binding_plans
from jsonschema.exceptions import ValidationError

class Tests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/'knowledge/metrics/industry-input-binding-plans.json').read_text(encoding='utf8'))
        self.specs=json.loads((ROOT/'knowledge/metrics/industry-specifications.json').read_text(encoding='utf8'))['specifications']

    def test_current_contract(self):
        """【FT-INDBIND-01: 行业指标输入绑定方案主契约全量合规校验】

        1. 测试功能与测试点:
           - 验证 knowledge/metrics/industry-input-binding-plans.json 方案底账。
           - 严格断言其与 industry-specifications.json 行业技术规范的槽位对齐度。
           - 验证 validate_binding_plans 返回当前数据对象本身。

        2. 正常函数业务边界与参数契约:
           - 方案版本、审核状态、期间与槽位定义必须完全吻合 Schema。

        3. 测试数据与模拟场景说明:
           - 读取当前项目底账 JSON。

        4. 预期断言与结果验证:
           - validate_binding_plans(self.data, self.specs) is self.data。
        """
        self.assertIs(validate_binding_plans(self.data,self.specs),self.data)

    def test_bad_structure_and_semantics(self):
        """【UT-INDBIND-02: 绑定方案结构/语义/时间穿越/非法槽位11种异常变异刚性阻断】

        1. 测试功能与测试点:
           - 验证针对绑定方案的 11 种致命变异场景的阻断拦截:
             1. Schema 版本不符 ('2.0.0')；
             2. 注入意外未知字段；
             3. 字符串布尔值违规 ('true' 而非 True)；
             4. 非法不存在日期 ('2025-02-30')；
             5. 截止日期为空；
             6. 未来日期穿越 ('2027-01-01')；
             7. 重复方案追加；
             8. 未知父级指标 ('unknown')；
             9. 未定义槽位名 ('错误槽位')；
             10. 非法推测类型 ('automatic_guess')；
             11. 单位为空字符串。

        2. 正常函数业务边界与参数契约:
           - 任意一种语义或结构缺陷坚决抛出 (ValueError, ValidationError)。

        3. 测试数据与模拟场景说明:
           - 变异闭包动态生成 11 组损坏的配置字典。

        4. 预期断言与结果验证:
           - 11 组用例全部触发 (ValueError, ValidationError)。
        """
        cases=[]
        def change(fn):
            d=copy.deepcopy(self.data); fn(d); cases.append(d)
        change(lambda d:d.update(schema_version='2.0.0'))
        change(lambda d:d.update(unexpected=True))
        change(lambda d:d['plans'][0].update(definition_reviewed='true'))
        change(lambda d:d['plans'][0].update(period_start='2025-02-30'))
        change(lambda d:d['plans'][0].update(period_end=None))
        change(lambda d:d['plans'][0].update(period_start='2027-01-01'))
        change(lambda d:d['plans'].append(copy.deepcopy(d['plans'][0])))
        change(lambda d:d['plans'][0].update(parent_metric_id='unknown'))
        change(lambda d:d['plans'][0]['slots'].update(错误槽位=[{'component':'x','kind':'numeric','scope':'x','unit':'x'}]))
        change(lambda d:next(iter(d['plans'][0]['slots'].values()))[0].update(kind='automatic_guess'))
        change(lambda d:next(iter(d['plans'][0]['slots'].values()))[0].update(unit=''))
        for i,data in enumerate(cases):
            with self.subTest(case=i),self.assertRaises((ValueError,ValidationError)):
                validate_binding_plans(data,self.specs)

if __name__=='__main__': unittest.main()
