"""正式财务事实契约及逐表字典：与六步行业指标 observation 区分。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=json.loads((ROOT/'schemas/financial-report.schema.json').read_text(encoding='utf-8'))
def prop(t,title,description,**kw):return {'type':t,'title':title,'description':description,**kw}
def obj(title,properties):return {'type':'object','title':title,'properties':properties,'required':list(properties),'additionalProperties':False}
sha=prop('string','内容摘要','内容字节 SHA-256',pattern='^[a-f0-9]{64}$')
ref=obj('执行材料引用',{'path':prop('string','项目内路径','不可变执行材料副本；拒绝越界'), 'sha256':sha})
version=obj('登记资料版本',{'source_id':prop('string','资料标识','正式 sources 表标识'),
 'revision':prop('integer','资料修订号','精确绑定原文版本',minimum=1),'sha256':sha})
schema=obj('正式财务事实登记',{
 'schema_version':prop('string','契约版本','正式登记封套版本',const='1.0.0'),
 'registration_id':sha|{'title':'登记标识','description':'除自身之外登记封套 canonical JSON 的 SHA-256'},
 'entity_id':prop('string','公司标识','与原文浏览器登记和财报一致'),
 'report_id':prop('string','报告版本标识','重述以新报告标识追加，比较列不自动归入历史发布'),
 'fact':{'$ref':'#/$defs/fact','title':'标准财务事实','description':'原始报表科目，金额十进制字符串，保留范围及期间'},
 'quality_status':prop('string','核验状态','原文及解析核验通过；不代表审计意见、行业判断或六步完成',const='source_verified'),
 'report_ref':ref|{'title':'财报快照引用'},'plan_ref':ref|{'title':'解析配置引用'},
 'implementation_ref':ref|{'title':'解析实现引用'},
 'original_source':version|{'title':'原始 ZIP/PDF 登记版本'},
 'evidence_source':version|{'title':'派生证据登记版本'},
 'taxonomy_validation':prop('object','分类标准校验','Inline XBRL 必须 passed；PDF 为 not_applicable',
    required=['status'],properties={'status':{'enum':['passed','not_applicable']}})})
schema.update({'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:shuiyuan:registered-financial-fact:1.0.0','$defs':s['$defs']})
(ROOT/'schemas/registered-financial-fact.schema.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
tables=[('registration',schema),('execution-ref',ref),('source-version',version)]
directory=ROOT/'docs/financial-dictionary'
for name,table in tables:
 lines=['# '+table['title'],'','| 字段代码 | 中文名称 | 类型 | 必填 | 业务含义 |','| --- | --- | --- | --- | --- |']
 for k,v in table['properties'].items():lines.append(f'| `{k}` | {v["title"]} | {v.get("type","对象引用")} | 是 | {v.get("description",v["title"]+"；结构见契约")} |')
 lines+=['','所有字段必填；完整嵌套结构及条件约束见 `schemas/registered-financial-fact.schema.json`。','']
 (directory/(name+'.md')).write_text('\n'.join(lines),encoding='utf-8')
