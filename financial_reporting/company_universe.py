"""公司候选身份注册表；禁止内嵌未登记财报、估值参数或投资评级。"""
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
