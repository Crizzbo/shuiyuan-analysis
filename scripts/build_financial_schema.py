"""财报事实契约及分表中文数据字典；字段说明与机器契约同源生成。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def field(t,title,desc,**rest):
    return {'type':t,'title':title,'description':desc,**rest}
def obj(title,props):
    return {'type':'object','title':title,'properties':props,'required':list(props),'additionalProperties':False}
source=json.loads((ROOT/'schemas/metric-batch.schema.json').read_text(encoding='utf-8'))['$defs']['source']
period=obj('财务期间',{
 'start':field(['string','null'],'期间起日','流量统计起日；时点存量必须为空',format='date'),
 'end':field('string','期间止日','统计止日或资产负债表时点',format='date'),
 'basis':field('string','期间类型','年度、季度、时点或累计/其他；不得自动把半年变成单季度',enum=['annual','quarter','instant','ytd_or_other'])})
fact=obj('标准财务事实',{
 'id':field('string','事实标识','由报告、字段、期间、范围和原文定位生成的 SHA-256',pattern='^[a-f0-9]{64}$'),
 'field':field('string','字段代码','经审核的报表科目映射，未映射科目不以相似名称替代'),
 'name_zh':field('string','中文名称','科目业务中文名称'),
 'value':field('string','基础货币金额','十进制字符串，保留精度和正负号；不是展示用百万金额',pattern='^-?[0-9]+(?:\\.[0-9]+)?$'),
 'period':{'$ref':'#/$defs/period','title':'财务期间','description':'原报表期间，流量与存量分开'},
 'scope_id':field('string','报表范围','consolidated 合并总额；consolidated_continuing 合并持续经营；不可混算'),
 'accounting_basis':field('string','会计准则','明确保留准则，不把 IFRS 与 GAAP 等同',enum=['GAAP','IFRS','J-GAAP']),
 'currency':field('string','币种','ISO 三字母币种，不自动换汇',pattern='^[A-Z]{3}$'),
 'unit':field('string','量纲','本阶段仅金额',const='currency'),
 'scale':field('integer','金额尺度','已转换为基础货币单位，因此恒为 1；原尺度见原文',const=1),
 'concept':field('string','原始科目','XBRL 展开 QName 或已核对的 PDF 精确行名'),
 'source':{'$ref':'#/$defs/source','title':'原文证据','description':'项目内原文、哈希、定位和实际可得时点'},
 'rounding_tolerance':field(['string','null'],'金额舍入容差','基础货币单位；四舍五入取半个最小展示单位，截断取一个单位；未知为空并阻断勾稽',pattern='^[0-9]+(?:\\.[0-9]+)?$'),
 'status':field('string','事实质量状态','extracted 表示完成提取，仍待研究审核；冲突和勾稽失败禁止计算',enum=['extracted','conflict','check_failed']),
 'duplicate_refs':field('array','同值重复原文引用','仅同字段、期间、范围、准则、币种且同金额时归并；保留所有证据',items={'$ref':'#/$defs/source'})})
check=obj('财务勾稽结果',{
 'check':field('string','校验代码','资产负债平衡、现金流合计或现金存量流量桥接',enum=['balance_sheet','cash_flow_bridge','cash_stock_bridge']),
 'group':field('array','同口径分组','依次为期间 JSON、范围、会计准则和币种',items={'type':'string'},minItems=4,maxItems=4),
 'status':field('string','校验状态','incomplete 不等于通过，failed 阻断涉及事实',enum=['passed','failed','incomplete']),
 'residual':field('string','勾稽残差','有完整输入时的基础币种十进制残差'),
 'tolerance':field('string','允许舍入误差','完整输入各舍入容差合计'),
 'fact_refs':field('array','输入事实引用','完整校验涉及的事实 ID',items={'type':'string'}),
 'missing_fields':field('array','缺失字段','不完整校验所缺字段或端点标识',items={'type':'string'})})
check['required']=['check','group','status']
check['allOf']=[{'if':{'properties':{'status':{'enum':['passed','failed']}}},'then':{'required':['residual','tolerance','fact_refs']}},
                {'if':{'properties':{'status':{'const':'incomplete'}}},'then':{'required':['missing_fields']}}]
calculation=obj('指标计算结果',{
 'metric_id':field('string','指标代码','计算绑定代码，不等于已完成行业全部指标'),
 'name_zh':field('string','指标中文名称','明确说明计算口径的显示名称'),
 'period':{'$ref':'#/$defs/period','title':'计算期间','description':'按同一报表期间执行'},
 'scope_id':field('string','计算范围','输入必须同范围'),
 'accounting_basis':field('string','计算会计准则','输入必须同准则'),
 'currency':field('string','输入币种','原始金额币种；比率本身无货币量纲'),
 'status':field('string','执行状态','computed 是口径审核后计算，blocked 是缺失或无效',enum=['computed','blocked']),
 'value':field(['number','null'],'计算值','成功为有限比率；阻断为空'),
 'unit':field('string','结果单位','当前计算均为比例，百分数展示需乘 100',const='ratio'),
 'input_fact_refs':field('array','输入事实引用','报告内事实 ID，公式复核入口',items={'type':'string'}),
 'calculation':field('object','公式及开源实现','标准金融服务返回完整调用记录；直接库调用记录 library/function/formula'),
 'reason':field('string','阻断原因','无法执行时的口径或输入原因'),
 'missing_fields':field('array','缺少输入字段','无法执行时的原始字段代码',items={'type':'string'})})
calculation['required']=['metric_id','period','scope_id','accounting_basis','currency','status','value']
calculation['allOf']=[{'if':{'properties':{'status':{'const':'computed'}}},'then':{'required':['unit','input_fact_refs','calculation'],'properties':{'value':{'type':'number'}}}},
                     {'if':{'properties':{'status':{'const':'blocked'}}},'then':{'properties':{'value':{'type':'null'}},'anyOf':[{'required':['reason']},{'required':['missing_fields']}]}}]
props={
 'schema_version':field('string','契约版本','财报 staging 契约版本',const='1.0.0'),
 'report_id':field('string','报告版本标识','解析配置对应的报告标识；新财报及重述建立新标识'),
 'entity_id':field('string','公司标识','与浏览器登记公司身份一致；CIK 核对由解析器完成'),
 'supersedes_report_id':field(['string','null'],'被替代报告标识','重述时显式链接旧报告；原历史不更新删除'),
 'artifact':field('object','原文归档记录','沿用接入原文对象，包含 ZIP/PDF 哈希及浏览器日期精度'),
 'parser':field('object','解析边界','成员哈希、准则证据或审核模板；完整 DTS 结果单独在 taxonomy_validation 保存'),
 'plan_sha256':field('string','解析配置摘要','可复现科目映射和列选择',pattern='^[a-f0-9]{64}$'),
 'implementation_sha256':field('string','解析实现摘要','运行时解析模块文件内容哈希',pattern='^[a-f0-9]{64}$'),
 'facts':field('array','标准事实列表','提取后归并的报表科目事实；不是正式研究 observation',items={'$ref':'#/$defs/fact'}),
 'issues':field('array','解析异常列表','无法安全转换的原文定位与原因；不填零',items={'type':'object'}),
 'checks':field('array','勾稽校验列表','passed/failed/incomplete，残差和容差使用基础货币单位',items={'$ref':'#/$defs/check'}),
 'calculations':field('array','计算结果列表','返回公式、开源库、事实引用；缺失或口径不符为 blocked',items={'$ref':'#/$defs/calculation'}),
 'release_status':field('string','发布状态','当前只能进入 staging，尚不自动发布研究结论',const='staging_pending_review'),
 'missing_capabilities':field('array','未执行能力','尚未执行的校验；不是六步分析完成状态',items={'type':'string'}),
 'taxonomy_validation':field('object','完整分类标准校验','passed/blocked/not_run/not_applicable；PDF 不适用 XBRL 校验，详细日志内容寻址归档')}
schema=obj('标准财报记录',props)
schema['required'].remove('taxonomy_validation')
schema.update({'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:shuiyuan:financial-report:1.0.0',
               '$defs':{'fact':fact,'period':period,'source':source,'check':check,'calculation':calculation}})
(ROOT/'schemas/financial-report.schema.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
directory=ROOT/'docs/financial-dictionary';directory.mkdir(parents=True,exist_ok=True)
for name,table in [('report',schema),('fact',fact),('period',period),('source',source),('check',check),('calculation',calculation)]:
    lines=[f'# {table["title"]}','', '| 字段代码 | 中文名称 | 类型 | 必填 | 业务含义 |','| --- | --- | --- | --- | --- |']
    for k,v in table['properties'].items():
        t=v.get('type','对象引用');t='/'.join(t) if isinstance(t,list) else t
        required='是' if k in table['required'] else '条件必填/可选'
        lines.append(f'| `{k}` | {v.get("title",k)} | {t} | {required} | {v.get("description","")} |')
    lines+=['','字段与 `schemas/financial-report.schema.json` 同源生成；对象数组的具体运行结果见 14 功能设计。','']
    (directory/f'{name}.md').write_text('\n'.join(lines),encoding='utf-8')
