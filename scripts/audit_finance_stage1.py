"""第一阶段独立数值审计：合成输入、独立恒等式及本机热调用基准，不访问网络。

使用项目 .venv 运行；报告仅追加到独立审计目录，不修改历史研究或业务数据。
参考公式与适用边界见 docs/金融计算分阶段审核-20261015.md。
"""
import hashlib
import json
import math
import os
from pathlib import Path
import random
import socket
import statistics
import sys
import time
from datetime import date, timedelta, datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['MPLCONFIGDIR'] = str(ROOT / '.cache' / 'matplotlib')


def deny(*args, **kwargs):
    raise RuntimeError('审计禁止网络连接')


socket.socket.connect = deny
socket.socket.connect_ex = deny
socket.create_connection = deny

from finance_tools.basic import cashflow, dated_cashflow, financial_ratio, wacc, performance
from finance_tools.service import calculate


def run():
    rng = random.Random(20261015)
    results = []

    def check(name, actual, expected, tolerance=1e-9):
        error = abs(actual - expected)
        results.append(dict(name=name, actual=actual, expected=expected,
                            normalized_error=error / max(1, abs(expected)),
                            passed=math.isfinite(actual) and error <= tolerance * max(1, abs(expected))))

    # 直接对现金流逐期折现；年金用逐期相加，避免重复库闭式公式。
    for i in range(50):
        r = rng.uniform(-.15, .3)
        n = rng.randint(2, 30)
        flows = [rng.uniform(-10000, 10000) for _ in range(n)]
        check(f'npv_{i}', cashflow('npv', flows, r)['value'],
              math.fsum(c / (1+r)**t for t, c in enumerate(flows)))
        pmt = rng.uniform(-200, -1)
        for when in ('begin', 'end'):
            start = 0 if when == 'begin' else 1
            expected = -math.fsum(pmt / (1+r)**t for t in range(start, n+start))
            pv = cashflow('pv', interest_rate=r, periods=n, payment=pmt, when=when)['value']
            check(f'pv_{when}_{i}', pv, expected)
            recovered = cashflow('pmt', interest_rate=r, periods=n, present_value=pv, when=when)['value']
            check(f'pmt_inverse_{when}_{i}', recovered, pmt)
            fv = cashflow('fv', interest_rate=r, periods=n, payment=pmt, present_value=pv, when=when)['value']
            check(f'fv_identity_{when}_{i}', fv, 0, 1e-6)
        # 两期现金流根可直接确定，不依赖另一个 IRR 库。
        check(f'irr_{i}', cashflow('irr', [-100, 100*(1+r)])['value'], r)
        fr, rr = .03, .07
        fs = [-100, 20, -10, 150]
        pv_neg = 100 + 10/(1+fr)**2
        fv_pos = 20*(1+rr)**2 + 150
        check(f'mirr_{i}', cashflow('mirr', fs, finance_rate=fr, reinvest_rate=rr)['value'],
              (fv_pos/pv_neg)**(1/3)-1)
        d0 = date(2024, 1, 1)
        dates = [(d0+timedelta(days=t)).isoformat() for t in (0, 90, 366, 800)]
        amounts = [-100, 20, 30, 120]
        expected = sum(c/(1+r)**(t/365) for t,c in zip((0,90,366,800),amounts))
        check(f'xnpv_{i}', dated_cashflow('xnpv', dates, amounts, r)['value'], expected)
        irr = dated_cashflow('xirr', dates, amounts)['value']
        check(f'xirr_residual_{i}', sum(c/(1+irr)**(t/365) for t,c in zip((0,90,366,800),amounts)), 0, 1e-6)
        a, b = rng.uniform(1,1000), rng.uniform(1,1000)
        for op in ('roe','roa','operating_margin','gross_margin','net_margin','pe','pb','ev_ebitda','current_ratio'):
            check(f'{op}_{i}', financial_ratio(op,a,b)['value'], a/b)
        rf, beta, rm, kd, tax = .03, rng.uniform(0,2), .09, .05, .25
        expected = a/(a+b)*(rf+beta*(rm-rf)) + b/(a+b)*kd*(1-tax)
        check(f'wacc_{i}', wacc(a,b,rf,beta,rm,kd,tax)['value'], expected)

    # 绩效独立基准：样本标准差；初始财富为1；下行分母使用全体观察数。
    for i in range(20):
        xs = [rng.uniform(-.08,.08) for _ in range(60)]
        dates = [(date(2025,1,1)+timedelta(days=j)).isoformat() for j in range(len(xs))]
        annual, rf = 252, .04
        excess = [x-((1+rf)**(1/annual)-1) for x in xs]
        got = performance(xs,dates,annual,rf)
        wealth, peak, dd = 1., 1., 0.
        for x in xs:
            wealth *= 1+x
            peak = max(peak,wealth)
            dd = min(dd,wealth/peak-1)
        reference = dict(sharpe=statistics.mean(excess)/statistics.stdev(xs)*math.sqrt(annual),
                         volatility=statistics.stdev(xs)*math.sqrt(annual),
                         sortino=statistics.mean(excess)/math.sqrt(sum(min(0,x)**2 for x in excess)/len(xs))*math.sqrt(annual),
                         max_drawdown=dd,cagr=wealth**(annual/len(xs))-1)
        for key,value in reference.items():
            check(f'{key}_{i}',got[key],value)

    # 缺陷探针只记录现状，不能把现状错误写成必须通过的业务测试。
    probes = {}
    for name, action in {
        'zero_debt_wacc': lambda: wacc(100,0,.03,1,.08,.05,.25),
        'tiny_rate_pv': lambda: cashflow('pv',interest_rate=1e-16,periods=10,payment=-10),
    }.items():
        try:
            probes[name] = {'result':action()}
        except Exception as exc:
            probes[name] = {'exception':type(exc).__name__, 'message':str(exc)}

    # 预热后分批测量，报告每调用耗时；不把本机测量当作服务 SLA。
    timings = {}
    for name,action in {
        'npv_30':lambda:cashflow('npv',[-100]+[10]*29,.08),
        'ratio_direct':lambda:financial_ratio('roe',10,100),
        'ratio_registered':lambda:calculate('financial_ratio',dict(operation='roe',numerator=10,denominator=100)),
        'wacc':lambda:wacc(800,200,.03,1.2,.08,.05,.25),
    }.items():
        action()
        batches=[]
        for _ in range(7):
            start=time.perf_counter()
            for _ in range(100): action()
            batches.append((time.perf_counter()-start)*1000/100)
        timings[name]={'median_ms_per_call':statistics.median(batches),'max_batch_ms_per_call':max(batches),'calls':700}

    files=['finance_tools/basic.py','finance_tools/validation.py','finance_tools/service.py','scripts/audit_finance_stage1.py']
    report={'created_at':datetime.now(timezone.utc).isoformat(),'python':sys.version,
            'synthetic_only':True,'seed':20261015,'comparisons':len(results),
            'failures':[x for x in results if not x['passed']],
            'max_normalized_error':max(x['normalized_error'] for x in results),
            'boundary_probes':probes,'warm_benchmarks':timings,
            'implementation_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files},
            'checks':results}
    out=ROOT/'data/audits/financial-computation-20261015'
    out.mkdir(parents=True,exist_ok=True)
    target=out/('stage1-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
    with target.open('x',encoding='utf8') as f:
        json.dump(report,f,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps({k:v for k,v in report.items() if k not in ('checks','implementation_sha256')},ensure_ascii=False,indent=2))
    print(target.relative_to(ROOT).as_posix())


if __name__=='__main__':
    run()
