"""把已核验的内容摊销另行登记到摊销驱动；保留现金流表原有调节项记录。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    bundle=json.loads((ROOT/'data/browser-search/industry-driver-inputs-20261011b.json').read_text(encoding='utf8'))
    original=next(s for s in bundle['sources'] if s['industry_id']=='media_entertainment')
    o=dict(next(o for o in original['observations'] if o['component']=='nflx_content_amortization'))
    o.update(parent_metric_id='media_entertainment_driver_3',component='nflx_content_amortization_driver3',name_zh='年度内容资产摊销费用',binding_role='reported_metric',limitation_zh='现金流表同期间内容摊销；不是新增内容资产或现金支付，不覆盖其他内容成本')
    source={**original,'observations':[o]}
    binding={k:o[k] for k in ('component','parent_metric_id','name_zh','binding_role','limitation_zh','raw_unit','unit')}
    outputs={'data/browser-search/content-amortization-reviewed-20261011.json':{**bundle,'sources':[source]},'knowledge/metrics/content-amortization-reviewed-binding.json':{'schema_version':'1.0.0','bindings':[binding]}}
    for name,data in outputs.items():
        text=json.dumps(data,ensure_ascii=False,indent=2)+'\n';path=ROOT/name
        if path.exists() and path.read_text(encoding='utf8')!=text: raise ValueError('禁止覆写已登记批次')
        path.write_text(text,encoding='utf8')

if __name__=='__main__': main()
