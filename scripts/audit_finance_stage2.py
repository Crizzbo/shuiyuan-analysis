"""估值专项独立审计：Decimal参考、缩放不变性、求根残差及异常探针。"""
from pathlib import Path
from decimal import Decimal, localcontext
from datetime import datetime, timezone
import hashlib
import json
import os
import random
import socket
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['MPLCONFIGDIR']=str(ROOT/'.cache/matplotlib')
def deny(*a,**k): raise RuntimeError('审计禁止联网')
socket.socket.connect=deny
socket.socket.connect_ex=deny
socket.create_connection=deny
from finance_tools.valuation import multistage_dcf,reverse_dcf,residual_income,nav,reit_bridge,multiple_valuation
from financial_reporting.macro_valuation import MacroValuationEngine
from financial_reporting.strong_constrained_valuation import StronglyConstrainedValuationEngine as Strong


def main():
    rng=random.Random(20261016)
    checks=[]
    def check(name,a,b,tol=1e-8):
        checks.append(dict(name=name,actual=a,expected=b,passed=abs(a-b)<=tol*max(1,abs(b))))
    def d(x):return Decimal(str(x))
    with localcontext() as ctx:
        ctx.prec=60
        for i in range(100):
            cf=rng.uniform(10,1000); rates=[rng.uniform(-.2,.3) for _ in range(rng.randint(1,10))]
            r=rng.uniform(.06,.25); g=rng.uniform(-.02,.04); shares=rng.uniform(1,100); debt=rng.uniform(-100,200)
            flow=d(cf);pv=Decimal(0)
            for t,gr in enumerate(rates,1):
                flow*=1+d(gr);pv+=flow/(1+d(r))**t
            ev=pv+flow*(1+d(g))/(d(r)-d(g))/(1+d(r))**len(rates)
            got=multistage_dcf(cf,rates,r,g,shares,'FCFF',debt)
            check(f'dcf_decimal_{i}',got['value_per_share'],float((ev-d(debt))/d(shares)))
            scaled=multistage_dcf(cf*1000,rates,r,g,shares*1000,'FCFF',debt*1000)
            check(f'dcf_scale_{i}',scaled['value_per_share'],got['value_per_share'])
            check(f'fcfe_bridge_{i}',multistage_dcf(cf,rates,r,g,shares,'FCFE')['value_per_share'],float(ev/d(shares)))
            growth=rng.uniform(-.25,.35)
            price=multistage_dcf(cf,[growth]*5,r,g,shares,'FCFF')['value_per_share']
            inv=reverse_dcf(price,cf,5,r,g,shares,'FCFF')
            check(f'reverse_growth_{i}',inv['implied_growth'],growth)
            check(f'reverse_residual_{i}',inv['modeled_price'],price)
            book=d(100); total=book
            roes=[rng.uniform(-.1,.3) for _ in range(5)]
            ret=[rng.uniform(0,1) for _ in range(5)]
            for t,(roe,retain) in enumerate(zip(roes,ret),1):
                total+=book*(d(roe)-d(r))/(1+d(r))**t
                book*=1+d(roe)*d(retain)
            total+=book*(d(.12)-d(r))/(d(r)-d(g))/(1+d(r))**5
            check(f'residual_income_{i}',residual_income(100,roes,ret,r,.12,g)['value_per_share'],float(total))
            check(f'nav_{i}',nav([cf,100],20,10,-5,shares)['value_per_share'],(cf+65)/shares)
            check(f'multiple_{i}',multiple_valuation(cf,8,'enterprise',debt,shares)['value_per_share'],(cf*8-debt)/shares)
            check(f'reit_{i}',reit_bridge(cf,20,10,5,2,-3,15,[{'name':'调整','amount':-4}],shares)['affo_per_share'],(cf-5)/shares)
    probes={}
    actions={
        'macro_negative_debt':lambda:MacroValuationEngine.calculate_wacc(100,-10,1,.03),
        'macro_nan_market_cap':lambda:MacroValuationEngine.calculate_wacc(float('nan'),10,1,.03),
        'macro_tax_outside_range':lambda:MacroValuationEngine.calculate_wacc(100,20,1,.03,tax_rate=2),
        'strong_reverse_outside_bounds':lambda:Strong.solve_reverse_dcf(1e9,100,10,0,.1,.02),
        'strong_reverse_invalid_terminal':lambda:Strong.solve_reverse_dcf(100,100,10,0,.1,.2),
        'strong_future_quote':lambda:Strong.verify_quote_freshness('2030-01-01T00:00:00Z','2026-10-15T00:00:00Z'),
    }
    for name,action in actions.items():
        try: probes[name]={'returned':action()}
        except Exception as exc:probes[name]={'error':type(exc).__name__,'message':str(exc)}
    timings={}
    for name,action in {
        'dcf_5y':lambda:multistage_dcf(100,[.05]*5,.1,.02,10,'FCFF'),
        'reverse_5y':lambda:reverse_dcf(150,100,5,.1,.02,10,'FCFF'),
    }.items():
        batches=[]
        for _ in range(5):
            start=time.perf_counter()
            for _ in range(100):action()
            batches.append((time.perf_counter()-start)*1000/100)
        timings[name]={'median_ms':statistics.median(batches),'max_batch_ms':max(batches)}
    # NaN探针允许观察，但证据JSON必须严格标准；非有限值转为明确文本。
    import math
    def clean(x):
        if isinstance(x,float) and not math.isfinite(x):return str(x)
        if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
        if isinstance(x,(tuple,list)):return [clean(v) for v in x]
        return x
    files=['finance_tools/valuation.py','financial_reporting/macro_valuation.py','financial_reporting/strong_constrained_valuation.py','scripts/audit_finance_stage2.py']
    report=clean(dict(synthetic_only=True,seed=20261016,created_at=datetime.now(timezone.utc).isoformat(),
                     comparisons=len(checks),failures=[x for x in checks if not x['passed']],
                     probes=probes,timings=timings,checks=checks,
                     hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}))
    out=ROOT/'data/audits/financial-computation-20261015'/('stage2-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
    with out.open('x',encoding='utf8') as h:json.dump(report,h,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps({k:v for k,v in report.items() if k not in ('checks','hashes')},ensure_ascii=False,indent=2))
    print(out.relative_to(ROOT))


if __name__=='__main__':main()
