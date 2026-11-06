"""从新知识契约中的中文 title/description 生成独立单表说明及目录。"""
import json
from pathlib import Path
from build_schema_manual import label, constraints

ROOT = Path(__file__).resolve().parents[1]

def rows(node, logical, pointer):
    result = []
    for name, child in node.get('properties',{}).items():
        if not child.get('title') or not child.get('description'):
            raise ValueError('知识契约字段缺中文名称或释义：'+logical+'.'+name)
        field = logical+'.'+name
        p = pointer+'/properties/'+name
        result.append({'field':field,'name_zh':child['title'],'description':child['description'],
            'schema_pointer':p,'type':label(child),'required':name in node.get('required',[]),
            'nullable':child.get('type')=='null' or any(c.get('type')=='null' for c in child.get('anyOf',[])),
            'structural_schema':child})
        result.extend(rows(child,field,p))
    return result

def main():
    directory = ROOT/'docs/industry-schema-dictionary'
    directory.mkdir(parents=True,exist_ok=True)
    index = []
    fields = []
    for root_name, source in [('industry_knowledge','schemas/industry-knowledge.schema.json'),('metric_catalog','schemas/metric-definition.schema.json')]:
        schema = json.loads((ROOT/source).read_text(encoding='utf-8'))
        for logical,node,pointer in [(root_name,schema,'#')]+[(k,v,'#/$defs/'+k) for k,v in schema['$defs'].items()]:
            entries = rows(node,logical,pointer)
            filename = root_name+'--'+logical+'.md'
            index.append(f'| [{logical}](industry-schema-dictionary/{filename}) | `{source}` | `{pointer}` | {len(entries)} |')
            body = f'# {logical} 知识契约单表说明\n\n契约版本：1.0.0。字段中文名称来自正式契约的 title，业务释义来自 description。\n\n[返回统一目录](../06a-行业与指标契约数据字典.md) · [填写说明](../06-行业知识契约与软件样板.md)\n\n所属契约：[{source}](../../{source})；定义位置：`{pointer}`。\n\n## 字段表\n\n| 定义字段标识 | 中文名称 | 类型或引用 | 必填 | 允许 null | 结构约束 | 业务含义 |\n|---|---|---|---|---|---|---|\n'
            for row in entries:
                row.update(schema_file=source,documentation_file='docs/industry-schema-dictionary/'+filename)
                fields.append(row)
                values = [f"`{row['field']}`",row['name_zh'],row['type'],'是' if row['required'] else '否',
                    '是' if row['nullable'] else '否',constraints(row['structural_schema']),row['description']]
                body += '| '+' | '.join(v.replace('|','\\|').replace('\n',' ') for v in values)+' |\n'
            body += '\n## 精确结构定义\n\n```json\n'+json.dumps(node,ensure_ascii=False,indent=2)+'\n```\n'
            (directory/filename).write_text(body,encoding='utf-8')
    intro = '# 行业与指标契约数据字典统一目录\n\n版本：1.0.0。仅对应本次新增的两份知识设计契约，原研究及资料登记字典仍见 [05a 目录](05a-Schema逐字段数据字典.md)。\n\n字段标识为定义路径，不是实例路径；必填按所属对象解释，允许 null 不等于允许省略。所有定义对象禁止额外字段。此目录不扩大现有研究校验器或归档接口的契约范围。\n\n| 单表说明 | 契约文件 | 定义指针 | 属性数 |\n|---|---|---|---|\n'
    (ROOT/'docs/06a-行业与指标契约数据字典.md').write_text(intro+'\n'.join(index)+'\n',encoding='utf-8')
    (ROOT/'schemas/industry-field-guide.json').write_text(json.dumps({'guide_version':'1.0.0','fields':fields},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Built {len(index)} knowledge dictionary tables with {len(fields)} named fields.')

if __name__=='__main__':
    main()
