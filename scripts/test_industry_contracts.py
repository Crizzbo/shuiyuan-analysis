"""验证知识契约拒绝危险的状态升级、错配引用及缺失口径。"""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from validate_industry_contracts import validate, validate_all, ROOT, load

def check_manual():
    guide = load(ROOT/'schemas/industry-field-guide.json')
    expected = {}
    def scan(node, filename, pointer='#'):
        if not isinstance(node,dict):
            return
        for name, child in node.get('properties',{}).items():
            p = pointer+'/properties/'+name
            expected[(filename,p)] = (child,name in node.get('required',[]))
            scan(child,filename,p)
        for name, child in node.get('$defs',{}).items():
            scan(child,filename,pointer+'/$defs/'+name)
    for filename in ['schemas/industry-knowledge.schema.json','schemas/metric-definition.schema.json']:
        scan(load(ROOT/filename),filename)
    entries = {(r['schema_file'],r['schema_pointer']):r for r in guide['fields']}
    assert len(entries)==len(guide['fields']) and set(entries)==set(expected), '新契约字段字典覆盖不完整'
    index = (ROOT/'docs/06a-行业与指标契约数据字典.md').read_text(encoding='utf-8')
    documents = set()
    for key,row in entries.items():
        node,required = expected[key]
        assert row['structural_schema']==node and row['required']==required
        assert row['name_zh']==node['title'] and row['description']==node['description']
        path = (ROOT/row['documentation_file']).resolve()
        assert path.is_relative_to((ROOT/'docs/industry-schema-dictionary').resolve())
        body = path.read_text(encoding='utf-8')
        assert row['name_zh'] in body and row['description'] in body and f"`{row['field']}`" in body
        assert 'industry-schema-dictionary/'+path.name in index
        documents.add(path)
    assert documents==set((ROOT/'docs/industry-schema-dictionary').glob('*.md'))
    return len(documents), len(entries)

def run_mutations_suite():
    industry = load(ROOT/'examples/industry-software.design.json')
    metrics = load(ROOT/'knowledge/contracts/metric-definitions.json')
    cases = []
    def industry_case(fn):
        data = deepcopy(industry)
        fn(data)
        cases.append((data,'industry'))
    industry_case(lambda x: x.update(industry_id='not_registered'))
    industry_case(lambda x: x['dimensions'][1].update(dimension_id='lifecycle'))
    industry_case(lambda x: x['thresholds'].update(drawdown=0.4))
    industry_case(lambda x: x.update(statistical_validation_status='validated'))
    industry_case(lambda x: x['source_refs'][0].update(source_path='../outside.md'))
    industry_case(lambda x: x['research_gate'].update(required_steps=['S1','S2','S3','S4','S5','S5']))
    industry_case(lambda x: x['valuation_routes'][0].update(business_model_ids=['not_registered']))
    industry_case(lambda x: x.update(required_metric_ids=['not_registered']))
    industry_case(lambda x: x['research_gate'].update(real_case_status='completed'))
    for update in ({'formula':None}, {'inputs':[]}, {'unit':'wrong_unit'}, {'definition_status':'needs_definition','blocking_reasons':[]}):
        data = deepcopy(metrics)
        data['definitions'][0].update(update)
        cases.append((data,'metrics'))
    rejected_count = 0
    for data, kind in cases:
        try:
            validate(data,kind)
        except ValueError:
            rejected_count += 1
        else:
            raise AssertionError('非法行业或指标契约未被拒绝')
    return rejected_count


class IndustryContractsTests(unittest.TestCase):
    """行业与指标契约全息质量巡检测试类。"""

    def test_validate_all_contracts(self):
        """【FT-INDCONTRACT-01: 行业契约与指标定义全量知识结构合规性巡检(validate_all)】

        1. 测试功能与测试点:
           - 验证全系统 41 个行业专属设计档案 (industry design profiles) 语法契约。
           - 验证 146 个业务指标规格说明 (metric specifications) 的严密定义。
           - 验证行业设计样板与知识档案的一致性。
           - 验证参考资料副本物理哈希 (SHA-256) 的防篡改强锁定。

        2. 正常函数业务边界与参数契约:
           - 扫描全部行业契约与指标规范，出现任一异常直接报错。

        3. 测试数据与模拟场景说明:
           - 遍历知识库底层正式登记的所有 JSON 契约。

        4. 预期断言与结果验证:
           - validate_all() 顺利执行无报错。
        """
        validate_all()

    def test_field_guide_manual_alignment(self):
        """【FT-INDCONTRACT-02: 行业字段数据字典双向互验与文档完备性自检(check_manual)】

        1. 测试功能与测试点:
           - 验证 schemas/industry-field-guide.json 字段手册与两大元模式完全对齐。
           - 验证 8 份行业模式字典文档 (docs/industry-schema-dictionary/*.md) 覆盖 60 个属性字段。
           - 保证元数据、中文名称、描述说明与业务字典目录索引 100% 互相对账。

        2. 正常函数业务边界与参数契约:
           - 所有字段必须在 Markdown 文档中有独立呈现，无孤立定义。

        3. 测试数据与模拟场景说明:
           - 遍历解析 schema 的 properties 与 $defs。

        4. 预期断言与结果验证:
           - 文档数等于 8，字段数等于 60。
        """
        docs_count, fields_count = check_manual()
        self.assertEqual(docs_count, 8)
        self.assertEqual(fields_count, 60)

    def test_contract_mutations_rejection(self):
        """【UT-INDCONTRACT-03: 行业知识与指标定义13种致命变异拦截(状态抢跑/非法路径/口径缺失)】

        1. 测试功能与测试点:
           - 验证系统对 13 组非法业务变异的阻断拦截能力:
             1. 未登记行业 ID；
             2. 维度命名重复；
             3. 风险回撤阈值超标；
             4. 缺乏实证却伪称 'validated'；
             5. 引用上级目录越界路径 ('../outside.md')；
             6. 研究关卡步骤重复；
             7. 绑定未登记商业模式；
             8. 绑定未登记核心指标；
             9. 缺乏案例却伪称 'completed'；
             10. 指标公式为空；
             11. 指标输入参数列表为空；
             12. 非法单位 ('wrong_unit')；
             13. 状态待定但未提供阻塞原因。

        2. 正常函数业务边界与参数契约:
           - 任何违规变异均刚性抛出 ValueError。

        3. 测试数据与模拟场景说明:
           - 动态变异 9 组行业契约与 4 组指标规范。

        4. 预期断言与结果验证:
           - 13 组变异全部被拒绝拦截。
        """
        count = run_mutations_suite()
        self.assertEqual(count, 13)


def main():
    validate_all()
    docs_count, fields_count = check_manual()
    print(f'PASS: {docs_count} new dictionary tables, {fields_count} fields independently checked.')
    rejected_count = run_mutations_suite()
    print(f'PASS: {rejected_count} invalid contract mutations rejected.')


if __name__ == '__main__':
    main()
