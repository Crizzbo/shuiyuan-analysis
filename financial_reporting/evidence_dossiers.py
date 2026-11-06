"""证据驱动的公司数据档案：缺失不补数，假设不冒充事实，不输出未验收评级。"""
import copy
from functools import lru_cache
import hashlib
import html
import importlib
import json
import re
from pathlib import Path
from financial_reporting.industry_specific import verify_snapshot
from financial_reporting.pipeline import local, ROOT


def primary_artifact(store, source_id, revision=None):
    """只接受目录中登记的primary原文，校验实际内容哈希；不信任调用方自填verified标志。"""
    if revision is None:
        row=store.db.execute('SELECT s.*,a.local_path FROM sources s JOIN artifacts a USING(sha256) WHERE source_id=? ORDER BY revision DESC LIMIT 1',(source_id,)).fetchone()
    else:
        row=store.db.execute('SELECT s.*,a.local_path FROM sources s JOIN artifacts a USING(sha256) WHERE source_id=? AND revision=?',(source_id,revision)).fetchone()
    if row is None: raise ValueError('原始来源未登记：'+source_id)
    manifest=json.loads(row['manifest_json'])
    if manifest['source_kind']!='primary': raise ValueError('非原始公司披露')
    raw=local(row['local_path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=row['sha256']: raise ValueError('原始证据内容变化')
    return raw.decode('utf8'),{'source_id':source_id,'revision':row['revision'],'sha256':row['sha256'],
        'source_path':row['local_path'],'available_at':row['available_at']}


@lru_cache(maxsize=1)
def evidence_context():
    """一批生成前核实不可变快照与全部来源；新批次须清缓存/重新运行进程。"""
    index=json.loads(local('data/financial/industry-specific-verification.json').read_text(encoding='utf8'))
    snapshot=verify_snapshot(index['snapshot_path'])
    ledger_index=json.loads(local('data/financial/industry-driver-input-verification.json').read_text(encoding='utf8'))
    from financial_reporting.industry_inputs import verify_ledger
    ledger=verify_ledger(json.loads(local(ledger_index['snapshot_path']).read_text(encoding='utf8')))
    facts={}
    LocalStore = importlib.import_module("scripts.data_store").LocalStore
    store=LocalStore()
    try:
        for observation in snapshot['observations']:
            ref=observation['source_ref']
            text,source=primary_artifact(store,ref['source_id'],ref['revision'])
            if source['revision']!=ref['revision'] or source['sha256']!=ref['sha256']:
                raise ValueError('观测来源版本错配')
            source_record=json.loads(text)
            symbol=observation['entity_id'].split(':')[1]
            market=observation['entity_id'].split(':')[0]
            fact={'name':observation['name_zh'] if '\ufffd' not in observation['name_zh'] else observation['component'],
                'component':observation['component'],'value':observation['value'],'unit':observation['unit'],
                'currency': 'USD' if observation['unit'].startswith('USD') else 'JPY' if observation['unit'].startswith('JPY') else None,
                'period_start':observation['period_start'],'period_end':observation['period_end'],'scope':observation['scope'],
                'fact_role':observation.get('binding_role','reported_metric'),
                'limitations':observation.get('limitation_zh','仅限公司披露的范围与期间；不能据此宣称驱动完整'),
                'source':dict(source,url=source_record['source_url'],locator=observation['locator'])}
            facts.setdefault((market,symbol),[]).append(fact)
        # 从已登记原始表格解析希捷真实年度事实；不消费旧公司池、旧报告或自填估值参数。
        text,source=primary_artifact(store,'seagate_20261011_results',1)
        url=re.search(r'来源：(https://\S+)',text).group(1)
        names={'Revenue':'营业收入','GAAP net income':'GAAP净利润','Operating cash flow':'经营现金流',
            'Capital expenditures':'资本开支','Free cash flow':'公司定义自由现金流',
            'Cash and cash equivalents':'现金及等价物','Current portion of long-term debt':'流动有息债务',
            'Long-term debt, less current portion':'非流动有息债务','Inventories, net':'期末公司存货',
            'Total shareholders\' equity (deficit)':'期末股东权益','GAAP diluted EPS':'GAAP摊薄每股收益'}
        for line in text.splitlines():
            columns=[x.strip() for x in line.split('|')]
            if len(columns)<4 or columns[1] not in names: continue
            key=columns[1];value=columns[2]
            if not re.fullmatch(r'-?\d+(?:\.\d+)?',value): raise ValueError('原表金额格式变化')
            facts.setdefault(('US','STX'),[]).append({'name':names[key],'component':key,'value':value,
                'unit':'USD_per_share' if key=='GAAP diluted EPS' else 'USD_million','currency':'USD',
                'period_start':None if key in ('Cash and cash equivalents','Current portion of long-term debt','Long-term debt, less current portion','Inventories, net',"Total shareholders' equity (deficit)") else '2025-06-28',
                'period_end':'2026-07-03','scope':'Seagate consolidated US GAAP','fact_role':'reported_metric',
                'limitations':'53周财年；FCF为CFO减资本开支，已含利息，不是FCFF；存货不是渠道库存',
                'source':dict(source,url=url,locator='官方FY2026业绩表：'+key)})
    finally: store.close()
    return {'facts':facts,'snapshot_path':index['snapshot_path'],'ledger_path':ledger_index['snapshot_path'],'drivers':ledger['drivers']}


def build_company_dossier(symbol, market, display_name):
    """身份显示名为候选标签；财务只从不可变来源读取，禁止调用方注入数字。"""
    if not re.fullmatch(r'[A-Za-z0-9.\-]+',symbol) or market not in ('US','JP'): raise ValueError('无效公司身份')
    context=evidence_context()
    facts=copy.deepcopy(context['facts'].get((market,symbol),[]))
    return {'schema_version':'2.0.0','symbol':symbol,'market':market,'display_name':display_name,
        'identity_status':'candidate_label_from_inventory','research_status':'evidence_partial' if facts else 'evidence_missing',
        'facts':facts,'observation_snapshot_path':context['snapshot_path'],'driver_snapshot_path':context['ledger_path'],
        'valuation':None,'investment_stance':None,'position_fraction':None,
        'unknowns':['最新完整三表与匹配股数','业务分部、行业归属与竞争证据','库存/账期原始分子分母与公司风险附注',
            '债务期限、利率、受限现金、再融资压力输入','全周期现金流、估值模型及显式情景假设'],
        'limitations':['存在数据档案不等于完成公司深度研究','未取得证据的字段不推算，不自动输出买入线或评级','原文期间可能早于报告制作日，不能称为实时财务']}


def validate_dossier(data):
    """使用重建对比验证身份、事实、来源和缺口，不能靠verified=true绕过。"""
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import ValidationError
    schema=json.loads(local('schemas/company-evidence-dossier.schema.json').read_text(encoding='utf8'))
    try:
        Draft202012Validator(schema,format_checker=FormatChecker()).validate(data)
    except ValidationError as exc:
        raise ValueError('公司数据封套不符合契约：'+exc.message) from exc
    expected=build_company_dossier(data['symbol'],data['market'],data['display_name'])
    if data!=expected: raise ValueError('报告数据与已登记原文不一致，拒绝生成/上传')
    return data


def dossier_sections(data):
    validate_dossier(data)
    facts=data['facts']
    sections=[('1. 公司标识与研究范围',[f"候选标识：{data['market']}:{data['symbol']}。显示名称来自原文件目录，独立证券身份和分类核验仍需完成。",
        '本版已移除旧报告的模板假事实、未经登记财报和自动买入建议。制作日期不是原始财务日期。']),
        ('2. 已核对的公司原始数据',[])]
    for i,fact in enumerate(facts,1):
        sections[1][1].append(f"{i}. {fact['name']}：{fact['value']} {fact['unit']}；期间 {fact['period_start'] or '期末时点'} 至 {fact['period_end']}；范围 {fact['scope']}。")
        sections[1][1].append('使用限制：'+fact['limitations'])
    if not facts: sections[1][1].append('没有匹配的已审核公司原子事实。营业收入、利润、现金、债务、股数和每股收益均保持缺失。')
    sections.extend([
        ('3. 商业模式与行业驱动',['行业观测见上表；尚未完成业务分部、护城河、供应商与客户结构的逐项取证。',
            '报告比例和公式分子分母分别记录；公司库存不替代渠道库存，ARPA不替代ARPU。']),
        ('4. 财务质量与风险',['ROE需要同范围净利润与平均权益；存货周转需要匹配的平均存货和销售成本。缺失时不计算。',
            '没有债务到期表、合同利率和受限现金证据，不宣称无偿付风险或固定低息债券占比。']),
        ('5. 估值、假设与行动条件',['未完成现金流正常化、股数/稀释及行业模型验证，本版估值和投资评级为空。',
            '不把FCF默认为FCFF；不把CAPM股权成本命名为WACC；不输出未经校准的安全边际买入线。']),
        ('6. 下一步取证与复核',data['unknowns']),
        ('7. 原文来源与可追溯位置',[])])
    seen=set()
    for fact in facts:
        src=fact['source'];key=(src['source_id'],src['locator'])
        if key in seen: continue
        seen.add(key)
        sections[-1][1].extend([src['url'],'定位：'+src['locator'],'本地证据：'+src['source_path']])
    if not facts: sections[-1][1].append('原始财报来源待补，原云盘报告不作为公司事实证据。')
    return sections


def render_dossier_html(data):
    sections=dossier_sections(data)
    return '<!doctype html><html lang="zh"><meta charset="utf-8"><title>'+html.escape(data['display_name'])+'</title><body><h1>'+html.escape(data['display_name'])+' 公司数据档案</h1>'+''.join('<h2>'+html.escape(title)+'</h2>'+''.join('<p>'+html.escape(p)+'</p>' for p in paragraphs) for title,paragraphs in sections)+'</body></html>'
