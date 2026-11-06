"""行业观测封套契约；复用六步观测/证据类型，不改原始指标定义。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
research=json.loads((ROOT/'schemas/research.schema.json').read_text(encoding='utf-8'))
defs={k:research['$defs'][k] for k in ['evidence','observation','quantity','period','local_path']}
defs['evidence']['required']+=['published_date','publication_precision']
def field(t,title,description,**kw):return {'type':t,'title':title,'description':description,**kw}
props={
 'schema_version':field('string','映射契约版本','封套版本',const='1.0.0'),
 'entity_id':field('string','公司标识','与正式资料一致'),
 'industry_id':field('string','候选行业','用户指定的适配，不自动确认分部归类'),
 'classification_status':field('string','分类审核状态','指标计算不自动完成行业分类',const='unreviewed'),
 'scope_id':field('string','事实范围','合并或持续经营；不得跨范围混算'),
 'period_end':field('string','年度截止日','当前仅审核同报告年度或相邻年度',format='date'),
 'as_of':field('string','信息截止时点','正式事实可得时间不晚于此时点',format='date-time'),
 'mapping_results':field('array','逐指标执行结果','computed 或 blocked，保留正式登记输入及原因',items={'type':'object'}),
 'observations':field('array','有效指标观测','只写入可计算、单位和口径明确的观测',items={'$ref':'#/$defs/observation'}),
 'evidence':field('array','原始证据','保留发布时间精度和逐字摘录',items={'$ref':'#/$defs/evidence'}),
 'source_map':field('object','登记来源版本映射','证据标识对应 sources 修订'),
 'calculation_refs':field('array','计算执行材料','内容寻址 JSON 路径和摘要',items={'type':'object'}),
 'lineage':field('array','输入血缘','观测关联正式登记标识及完整报告快照',items={'type':'object'}),
 'missing_required_metric_ids':field('array','必需行业指标缺口','不能由财务共享指标替代',items={'type':'string'}),
 'industry_gate_status':field('string','行业指标门槛状态','缺必需项为 blocked；无缺口仍须分类审核',enum=['blocked','pending_classification_review'])}
schema={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:shuiyuan:industry-observations:1.0.0',
 'type':'object','additionalProperties':False,'properties':props,'required':list(props),'$defs':defs}
(ROOT/'schemas/industry-observations.schema.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# 行业指标观测映射封套','','| 字段 | 中文名称 | 类型 | 必填 | 业务含义 |','| --- | --- | --- | --- | --- |']
for k,v in props.items():lines.append(f'| `{k}` | {v["title"]} | {v["type"]} | 是 | {v["description"]} |')
lines+=['','观测与原文证据复用研究契约；接入研究前从正式事实重新执行并核对整个封套。','']
(ROOT/'docs/financial-dictionary/industry-observations.md').write_text('\n'.join(lines),encoding='utf-8')
