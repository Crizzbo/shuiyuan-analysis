"""资料登记 1.1：诚实保留日期精度；1.0 仍强制精确发布时间。"""
import json
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'schemas/source-manifest.schema.json'
s=json.loads(p.read_text(encoding='utf-8'))
s['$id']='urn:shuiyuan:source-manifest:1.1.0'
s['properties']['schema_version']={'enum':['1.0.0','1.1.0']}
s['properties']['published_at']={'type':['string','null'],'format':'date-time','title':'精确发布时间','description':'未知时为空，禁止从日期补造午夜时间'}
s['properties']['published_date']={'type':['string','null'],'format':'date','title':'发布日期','description':'仅来自官方页面的日期证据；不替代首次观察时刻'}
s['properties']['publication_precision']={'enum':['instant','date','unknown'],'title':'发布时间精度','description':'明确区分精确时刻、日期和未知'}
s['allOf']=[{'if':{'properties':{'schema_version':{'const':'1.0.0'}}},'then':{'properties':{'published_at':{'type':'string'}}}},
 {'if':{'properties':{'schema_version':{'const':'1.1.0'}}},'then':{'required':['published_date','publication_precision']}},
 {'if':{'required':['publication_precision'],'properties':{'publication_precision':{'const':'instant'}}},'then':{'properties':{'published_at':{'type':'string'}}}},
 {'if':{'required':['publication_precision'],'properties':{'publication_precision':{'const':'date'}}},'then':{'properties':{'published_at':{'type':'null'},'published_date':{'type':'string'}}}},
 {'if':{'required':['publication_precision'],'properties':{'publication_precision':{'const':'unknown'}}},'then':{'properties':{'published_at':{'type':'null'},'published_date':{'type':'null'}}}}]
p.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
