"""按全部41行业代表生成证据档案；只有已审核事实，不产生评级或目标价。"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from financial_reporting.industry_specific import verify_snapshot
from financial_reporting.industry_inputs import verify_ledger
from scripts.data_store import LocalStore

def main():
    read=lambda path:json.loads((ROOT/path).read_text(encoding='utf8'))
    observation_index=read('data/financial/industry-specific-verification.json')
    snapshot=verify_snapshot(observation_index['snapshot_path'])
    ledger_index=read('data/financial/industry-driver-input-verification.json')
    ledger=verify_ledger(read(ledger_index['snapshot_path']))
    plan=read('config/google-finance-industry-plan.json')
    version = sys.argv[1] if len(sys.argv) > 1 else ('representatives-20261012b' if (ROOT / 'knowledge/companies/representatives-20261012/index.json').exists() else 'representatives-20261012')
    directory = ROOT / f'knowledge/companies/{version}'
    if (directory / 'index.json').exists():
        raise ValueError('档案版本已存在；不得覆写历史输出')
    directory.mkdir(parents=True, exist_ok=True)
    companies=[]
    store=LocalStore()
    try:
        for security in plan['securities']:
            industry=security['industry_id']
            entity=security['market']+':'+security['ticker'].split(':',1)[1]
            observations=[o for o in snapshot['observations'] if o['industry_id']==industry and o['entity_id']==entity]
            drivers=[d for d in ledger['drivers'] if d['industry_id']==industry]
            facts=[]
            for observation in observations:
                ref=observation['source_ref']
                source=store.source_as_of(ref['source_id'],observation['available_at'])
                if source is None or source['manifest']['revision']!=ref['revision'] or source['sha256']!=ref['sha256']:
                    raise ValueError('来源版本或哈希不一致')
                facts.append({'observation_id':observation['observation_id'], 'component':observation['component'],
                    'value':observation['value'],'unit':observation['unit'],'scope':observation['scope'],
                    'period_start':observation['period_start'],'period_end':observation['period_end'],
                    'source_path':source['manifest']['source_path'],'source_ref':ref,'locator':observation['locator']})
            # 行业归类来自项目人工配置；不将配置当作独立核实的证券身份。
            profile=industry+'.md'
            record={'industry_id':industry,'ticker':security['ticker'],'name':security['name'],'market':security['market'],
                'profile_path':(directory/profile).relative_to(ROOT).as_posix(),
                'security_identity_status':'candidate_requires_identity_review',
                'research_status':'evidence_partial' if facts else 'evidence_missing','facts':facts,
                'drivers':[{'parent_metric_id':d['parent_metric_id'],'input_status':d['input_status'],
                    'calculation_ready':d['calculation_ready'],'missing_slot_ids':d['missing_slot_ids']} for d in drivers],
                'valuation_status':'not_assessed','investment_stance':None,'position_fraction':None}
            companies.append(record)
            lines=[f"# {security['name']}（{security['ticker']}）证据档案",'',
                '## 1. 公司概况与证券标识','',f'行业配置：`{industry}`；市场：`{security["market"]}`。身份状态：候选映射，独立证券身份核验未完成。',
                '','## 2. 商业模式与核心护城河','',
                '仅依据已有行业指标选择研究方向；尚未完成公司护城河、业务分部与竞争优势专项论证，不生成未经验证的定性评级。',
                '','## 3. 通用财务健康体检（Generic Financial Metrics）','',
                '本档案未对无来源的硬编码财务数值做健康评级。收入、资产负债、现金流及摊薄口径需要独立正式财报输入。',
                '','## 4. 行业专属驱动指标与输入状态','',
                '| 原子事实 | 值与单位 | 期间 | 范围 | 项目内证据 |','|---|---|---|---|---|']
            for fact in facts:
                # Markdown管道必须转义，避免来源或范围破坏表格。
                escape=lambda text:str(text).replace('|','\\|').replace('\n',' ')
                link='../../../'+fact['source_path']
                lines.append(f"| `{escape(fact['component'])}` | {escape(fact['value'])} {escape(fact['unit'])} | {fact['period_start'] or '期末时点'} → {fact['period_end']} | {escape(fact['scope'])} | [原文摘录]({link})；{escape(fact['locator'])} |")
            if not facts: lines.append('| 无已审核公司原子事实 | 缺失 | 未知 | 未知 | 待浏览器核对官方原文 |')
            lines+=['','| 行业驱动 | 输入状态 | 可计算 | 缺少槽位 |','|---|---|---|---|']
            for driver in drivers:
                lines.append(f"| `{driver['parent_metric_id']}` | {driver['input_status']} | {driver['calculation_ready']} | {', '.join(driver['missing_slot_ids']) or '所选口径槽位齐备'} |")
            lines+=['','[行业输入分表](../../metrics/driver-inputs/'+industry+'.md)',
                '','## 5. 估值分层与交易策略','',
                '估值尚未评估，投资倾向和仓位为空。未启用未校准深跌阈值，单个行业观测不放行六步研究。',
                '','## 6. 核心催化剂与下行风险边界','',
                '待核对最新官方财报、行业驱动的缺失分子分母、同范围期间以及公司风险附注。事件发生日、概率和目标价没有完成取证，保持缺失。',
                '',f"观测快照：`{observation_index['snapshot_path']}`；台账快照：`{ledger_index['snapshot_path']}`。",
                '','本文件为证据组织档案，存在文档不等于完成深度分析。']
            (directory/profile).write_text('\n'.join(lines)+'\n',encoding='utf8')
    finally:
        store.close()
    index={'schema_version':'1.0.0','created_at':datetime.now(timezone.utc).isoformat(),
        'observation_snapshot_path':observation_index['snapshot_path'],'driver_snapshot_path':ledger_index['snapshot_path'],
        'companies_count':len(companies),'companies':companies}
    (directory/'index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    rows=['# 41行业代表公司证据档案统一目录','','完整深度研究仍待补数和逐公司验收；不以档案数量替代证据完整性。','',
        '| 行业 | 公司 | 事实数 | 研究状态 |','|---|---|---:|---|']
    rows.extend(f"| {c['industry_id']} | [{c['name']}（{c['ticker']}）]({c['industry_id']}.md) | {len(c['facts'])} | {c['research_status']} |" for c in companies)
    (directory/'README.md').write_text('\n'.join(rows)+'\n',encoding='utf8')
    print(f'生成{len(companies)}份证据档案；{sum(bool(c["facts"]) for c in companies)}份含已审核观测；深度研究完成数仍为0')

if __name__=='__main__': main()
