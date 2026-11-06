"""撤销项目内15家旧假数据档案，保留原文件审计副本，重建证据与缺口档案。"""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from financial_reporting.evidence_dossiers import build_company_dossier, dossier_sections

def main():
    directory=ROOT/'knowledge/companies'
    old=json.loads((directory/'companies.json').read_text(encoding='utf8'))
    if old['schema_version']!='1.0.0': raise ValueError('旧档案已经撤销，禁止重复运行')
    backup=ROOT/'data/audits/drive-deep-analysis-20261012/legacy-company-archives'
    backup.mkdir(parents=True,exist_ok=True)
    files=[directory/'companies.json',directory/'README.md']+[ROOT/c['profile_path'] for c in old['companies']]
    hashes=[]
    for path in files:
        raw=path.read_bytes();target=backup/(path.name+'.source' if path.suffix=='.md' else path.name)
        if target.exists(): raise ValueError('旧档案审计副本已存在')
        target.write_bytes(raw);hashes.append({'original_path':path.relative_to(ROOT).as_posix(),'backup_path':target.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(raw).hexdigest()})
    companies=[]
    for c in old['companies']:
        symbol=c['ticker'].split(':')[-1]
        data=build_company_dossier(symbol,c['market'],c['name_zh'])
        json_relative='knowledge/companies/'+c['company_id']+'.evidence.json'
        (ROOT/json_relative).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        rows=[f"# {c['name_zh']}（{c['ticker']}）公司数据与取证缺口",'',
            '旧版硬编码财务、估值区间和评级已撤销。本版不是完整深度研究。','']
        for title,paragraphs in dossier_sections(data):
            rows.extend(['## '+title,'',*paragraphs,''])
        (ROOT/c['profile_path']).write_text('\n'.join(rows)+'\n',encoding='utf8')
        companies.append({'company_id':c['company_id'],'ticker':c['ticker'],'market':c['market'],
            'profile_path':c['profile_path'],'evidence_path':json_relative,'research_status':data['research_status'],
            'investment_stance':None,'position_fraction':None})
    (directory/'companies.json').write_text(json.dumps({'schema_version':'2.0.0','title':'公司证据档案与缺口索引',
        'companies_count':len(companies),'companies':companies},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    rows=['# 公司档案统一目录','','旧版15家硬编码财务和评级已撤销，原文件在项目审计目录保留。以下为已核实字段与缺口，不宣称完成深度研究。','',
        '[41行业代表档案](representatives-20261012/README.md) · [数据完整性修复说明](../../docs/company-dossier-data-integrity-fix.md)','',
        '| 公司 | 研究状态 |','|---|---|']
    rows.extend(f"| [{c['ticker']}]({Path(c['profile_path']).name}) | {c['research_status']} |" for c in companies)
    (directory/'README.md').write_text('\n'.join(rows)+'\n',encoding='utf8')
    (backup/'manifest.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('撤销15家旧档案的无来源财务和评级，已保存原文并重建证据档案')

if __name__=='__main__': main()
