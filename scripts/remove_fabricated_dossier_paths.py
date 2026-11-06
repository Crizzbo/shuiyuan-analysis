"""修复旧报告生成路径，原代码逐文件保存供追溯；不删除历史报告或访问网络。"""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    backup=ROOT/'data/audits/drive-deep-analysis-20261012/code-originals'
    backup.mkdir(parents=True,exist_ok=True)
    paths=['financial_reporting/deep_schema_generator.py','financial_reporting/scenario2_universe.py',
        'financial_reporting/company_universe.py','scripts/run_daily_analysis.py','scripts/build_company_archives.py',
        'scripts/build_full_universe.py','financial_reporting/pdf_templates.py']
    entries=[]
    for relative in paths:
        path=ROOT/relative;raw=path.read_bytes();out=backup/path.name
        if out.exists(): raise ValueError('修复备份已存在，不重复覆写')
        out.write_bytes(raw)
        entries.append({'path':relative,'sha256':hashlib.sha256(raw).hexdigest(),'backup_path':out.relative_to(ROOT).as_posix()})
    # 身份列表只用于组织研究；旧财务数值、评级和估值参数不再进入运行模块。
    import sys
    sys.path.insert(0,str(ROOT))
    from financial_reporting.company_universe import COMPANY_UNIVERSE
    identities=[{k:c[k] for k in ('company_id','ticker','name','name_zh','market','sector_id','industry_id','industry_name_zh','currency') if k in c} for c in COMPANY_UNIVERSE]
    (ROOT/'config/company-identities.json').write_text(json.dumps({'schema_version':'1.0.0','identity_status':'candidate_requires_identity_review','companies':identities},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    registry='''"""公司候选身份注册表；禁止内嵌未登记财报、估值参数或投资评级。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
COMPANY_UNIVERSE=json.loads((ROOT/'config/company-identities.json').read_text(encoding='utf8'))['companies']
def get_universe(market=None,tickers=None):
    rows=COMPANY_UNIVERSE
    if market: rows=[c for c in rows if c['market']==market.upper()]
    if tickers:
        names={x.upper() for x in tickers}
        rows=[c for c in rows if c['ticker'].upper() in names or c['ticker'].split(':')[-1].upper() in names or c['company_id'].upper() in names]
    return [dict(c) for c in rows]
def load_sec_full_universe():
    data=json.loads((ROOT/'data/universe/sec_company_tickers.json').read_text(encoding='utf8'))
    return [{'ticker':'US:'+r['ticker'],'symbol':r['ticker'],'cik':str(r['cik_str']).zfill(10),'name':r['title'],'market':'US'} for r in data.values()]
def load_jpx_full_universe():
    return json.loads((ROOT/'data/universe/jpx_company_tickers.json').read_text(encoding='utf8'))
def get_full_market_universe_stats():
    return {'us_count':len(load_sec_full_universe()),'jp_count':len(load_jpx_full_universe())}
'''
    (ROOT/'financial_reporting/company_universe.py').write_text(registry,encoding='utf8')
    (ROOT/'financial_reporting/scenario2_universe.py').write_text('''"""全量候选公司身份；缺失财报保持缺失，绝不生成替代资产负债表。"""
import json
from pathlib import Path
from financial_reporting.company_universe import get_universe,load_jpx_full_universe
ROOT=Path(__file__).resolve().parents[1]
def get_scenario2_universe():
    rows=get_universe();seen={(c['market'],c['ticker'].split(':')[-1]) for c in rows}
    data=json.loads((ROOT/'data/universe/sp500_universe.json').read_text(encoding='utf8'))
    for item in data['constituents']:
        symbol=item['symbol'].upper()
        if ('US',symbol) not in seen:
            rows.append({'company_id':'us_'+symbol.lower(),'ticker':'US:'+symbol,'name':item['name'],'name_zh':item['name'],'market':'US','currency':'USD','identity_status':'candidate_requires_identity_review'})
            seen.add(('US',symbol))
    for item in load_jpx_full_universe():
        code=str(item['code'])
        if item.get('scale_category') in ('TOPIX Core30','TOPIX Large70') and ('JP',code) not in seen:
            rows.append({'company_id':'jp_'+code,'ticker':'TYO:'+code,'name':item['name'],'name_zh':item['name'],'market':'JP','currency':'JPY','identity_status':'candidate_requires_identity_review'})
            seen.add(('JP',code))
    return rows
''',encoding='utf8')
    (ROOT/'financial_reporting/deep_schema_generator.py').write_text('''"""深度档案仅消费本地已审核证据；不读取调用方的未登记财务或宏观默认值。"""
from financial_reporting.evidence_dossiers import build_company_dossier
def build_deep_dossier_data(company,macro=None):
    return build_company_dossier(company['ticker'].split(':')[-1],company['market'],company.get('name_zh') or company.get('name') or company['ticker'])
def build_daily_briefing_data(company,macro=None):
    raise ValueError('旧自动评级日报路径已停用；使用已登记行情与新闻契约生成日报')
''',encoding='utf8')
    # 阻止旧入口绕过新的事实封套；明确报错，不能吞异常或静默使用估算值。
    changes={
        'scripts/run_daily_analysis.py':('    rf = company["raw_financials"]','    raise ValueError("旧未登记财务分析路径已停用；请执行 scripts/rebuild_verified_drive_dossiers.py")\n    rf = company["raw_financials"]'),
        'scripts/build_company_archives.py':('def main():','def main():\n    raise ValueError("旧硬编码公司归档入口已停用；请执行 scripts/rebuild_verified_drive_dossiers.py")'),
        'scripts/build_full_universe.py':('def update_company_universe():','def update_company_universe():\n    raise ValueError("禁止从硬编码财务重建公司注册表；只能维护候选身份与登记事实")'),
        'financial_reporting/pdf_templates.py':('    ov = data["overview"]','    from financial_reporting.evidence_dossiers import render_dossier_html\n    return render_dossier_html(data)\n    ov = data["overview"]')}
    for relative,(before,after) in changes.items():
        path=ROOT/relative;text=path.read_text(encoding='utf8')
        if before not in text: raise ValueError('生成路径发生变化：'+relative)
        path.write_text(text.replace(before,after,1),encoding='utf8')
    (backup/'manifest.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('已隔离旧财务、通用假事实、默认估值与评级路径；原代码保留审计副本')

if __name__=='__main__': main()
