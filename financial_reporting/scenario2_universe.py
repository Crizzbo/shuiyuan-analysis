"""全量候选公司身份；缺失财报保持缺失，绝不生成替代资产负债表。"""
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
