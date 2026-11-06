"""希捷六步研究样例：仅从项目内证据生成，可复核但不代表交易授权。"""
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from finance_tools.service import calculate, research_record, sensitivity
from validate_research import validate

BASE = ROOT / 'data/seagate/2026-10-11'


def write(name, value):
    """输出在项目内，禁止覆盖已登记的历史版本。"""
    path = BASE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ValueError(f'已存在输出：{path.name}；新研究应建立新日期/版本目录')
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def main():
    inp = json.loads((BASE / 'inputs.json').read_text(encoding='utf-8'))
    f, a = inp['facts'], inp['assumptions']
    now = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    prefix = 'data/seagate/2026-10-11/'
    annual = {'start': '2025-06-28', 'end': '2026-07-03', 'basis': 'year'}
    price_period = {'start': '2026-10-09', 'end': '2026-10-09', 'basis': 'point_in_time'}
    evidence = []
    manifests = []
    # 不伪造官方发布的精确时刻；本次证据的保守可得时点取归档时刻。
    for eid, filename, kind, date, dataset, summary in [
        ('e_results', 'official-results-excerpt.md', 'primary', '2026-07-28', 'financial', '官方年度、季度财务及明确标注的指引'),
        ('e_10k', 'sec-10k-excerpt.md', 'primary', None, 'financial', 'SEC身份、单分部、EB出货、客户集中度与风险'),
        ('e_quote', 'google-finance-browser-excerpt.md', 'secondary', None, 'market', '浏览器常规交易报价；MCP本次失败'),
        ('e_inputs', 'inputs.json', 'project_design', None, 'research_material', '本地事实转录与显式模型假设'),
        ('e_checks', 'verification.json', 'project_design', None, 'research_material', '开源NPV交叉核对与反向DCF重算')]:
        precision = 'date' if date else 'unknown'
        evidence.append(dict(id=eid, source_path=prefix+filename, locator='全文（选择性摘录/计算记录）',
            source_kind=kind, published_at=None, published_date=date, publication_precision=precision,
            available_at=now, acquired_at=now, excerpt_or_summary=summary,
            limitations=['选择性摘录；数字转录不等于完整独立审计'] if kind=='primary' else ['仅支持声明范围；不是独立原始公司披露']))
        manifests.append(dict(schema_version='1.1.0', source_id='seagate_20261011_'+eid[2:], revision=1,
            source_path=prefix+filename, source_kind=kind, dataset_kind=dataset,
            published_at=None, published_date=date, publication_precision=precision,
            available_at=now, acquired_at=now, effective_period=None, license_notes='项目内研究使用；不代表再分发授权',
            quality_notes=[summary], supersedes_revision=None))

    observations = []
    def obs(oid, metric, value, unit, refs, period=annual, notes='US GAAP年度；FY2026为53周'):
        observations.append(dict(id=oid, metric_id=metric, segment_id=None, period=period,
            available_at=now, value={'value': value, 'unit': unit, 'currency': 'USD' if unit.startswith('currency') else None} if value is not None else None,
            missing_reason=notes if value is None else None, accounting_basis='US GAAP/明确的描述性桥接；见口径说明',
            comparability_notes=notes, evidence_refs=refs))
    obs('o_price', 'market_price', f['market_price'], 'currency_per_share', ['e_quote'], price_period, '2026-10-09常规收盘；非实时或盘后价')
    obs('o_fcf', 'fcf', f['fcf_2026']*1e6, 'currency', ['e_results'], notes='公司定义CFO-capex；利息之后，非FCFF或完整FCFE')
    obs('o_margin', 'operating_margin', f['operating_income_2026']/f['revenue_2026'], 'ratio', ['e_10k'])
    obs('o_growth', 'revenue_growth', f['revenue_2026']/f['revenue_2025']-1, 'ratio', ['e_results'], notes='53周对52周；未按同周调整')
    obs('o_debt', 'net_debt', (f['current_debt_2026']+f['long_debt_2026']-f['cash_2026'])*1e6, 'currency', ['e_results'], {'start':'2026-07-03','end':'2026-07-03','basis':'point_in_time'}, '账面有息债务减现金；未包含租赁/其他现金需求，非当前报价日债务')
    obs('o_units_missing', 'hardware_driver_1', None, 'units', ['e_10k'], notes='披露EB容量不是硬盘台数，不能以789EB填台数')
    obs('o_channel_missing', 'hardware_driver_2', None, 'days', ['e_10k'], notes='渠道库存未披露；公司库存1571百万美元不是渠道库存')
    claims = []
    def claim(cid, kind, text, refs=None, obsrefs=None, assumptions=None, counter=None, uncertainty='结论仅覆盖已归档资料；不是概率估计'):
        claims.append(dict(id=cid, kind=kind, statement=text, evidence_refs=refs or [], observation_refs=obsrefs or [],
            counterevidence_refs=counter or [], assumption_refs=assumptions or [], uncertainty=uncertainty))
    claim('c_identity','fact','爱尔兰普通股STX；硬件产品销售；一个会计分部，数据中心/Edge IoT为市场维度。',['e_10k'])
    claim('c_capacity','fact','Nearline容量695EB对497EB；总容量789EB对595EB；数据中心收入占80%；一客户约14%。',['e_10k'])
    claim('c_profit','fact','FY2026营收12195、净利3184、FCF3105百万美元；Q4毛利率52.3%；FY2026比上年多一周。',['e_results','e_10k'])
    claim('c_guidance','fact','管理层7月28日给出的FY2027Q1营收4100±100百万美元、非GAAP EPS7.30±0.20，是指引而非实际。',['e_results'])
    claim('c_risk','fact','官方披露客户订单变化、HAMR技术资格/良率、NAND替代、债券现金结算与稀释、BIS履约和诉讼风险。',['e_10k'])
    claim('c_cycle','inference','成熟存储产业出现高容量技术升级；已披露经营处扩张和提价阶段，但缺少完整供需、信用和情绪周期证据。',['e_10k','e_results'],['o_growth','o_margin'],counter=['e_10k'])
    claim('c_quality','inference','容量增长、定价和现金流共同支持经营改善；客户集中和现金流周期性限制长期确定性。',['e_10k','e_results'],['o_fcf'],counter=['e_10k'])
    claim('c_unknown','unknown','渠道库存、HAMR占比/良率、全行业产能、最新季度实际、债券前瞻偿付/稀释与代理声明专项治理审阅未完成。',['e_10k','e_results'])
    claim('a_bridge','assumption',a['cash_flow_bridge']+' '+a['share_basis'],['e_inputs'])
    for name in ['bear','base','bull']:
        claim('a_'+name,'assumption',json.dumps(a[name],ensure_ascii=False)+'；参数为研究假设，非统计校准。',['e_inputs'],assumptions=['a_bridge'])
    claim('a_sensitivity','assumption','股权成本8/10/12%，永续增长2/3/4%；没有CAPM输入，不声称市场校准。',['e_inputs'],assumptions=['a_base'])
    claim('c_bridge','inference','FCF减SBC为2892百万美元代理；FCFE不再减净债务；不额外加现金；尚未完成债务及跨周期正常化。',['e_inputs','e_results'],['o_fcf'],['a_bridge'])
    claim('c_value','inference','在本次显式参数下报价高于三情景价值；反向DCF衡量所需增速，不能据此断言市场错误。',['e_inputs','e_quote'],['o_price'],['a_bear','a_base','a_bull'],counter=['e_results'])
    claim('c_watch','inference','观察；未证实安全边际，深跌行业阈值未校准、关键未知未解决、未评估用户组合，不输出仓位。',['e_inputs','e_quote','e_10k'],['o_price'],['a_base'],counter=['e_results'])
    claim('a_review','assumption','2026-10-19检查新披露，2026-11-02研究复盘；为计划时点，非财报预约日、无自动任务。',['e_inputs'])

    runs, calcs, checks = {}, [], []
    cash = (f['fcf_2026']-f['sbc_2026'])*1e6
    shares = f['q4_diluted_shares_million']*1e6
    common = dict(cash_flow=cash, shares=shares, scope='FCFE', net_debt=0)
    def record(cid, run, field, unit, assumptions, obsrefs):
        runs[cid] = run
        rec = research_record(run,cid,[dict(field=field,unit=unit,currency='USD' if unit.startswith('currency') else None)],obsrefs,assumptions)
        rec.update(verification_status='checked', verification_evidence_refs=['e_checks'])
        calcs.append(rec)
    for name in ['bear','base','bull']:
        run = calculate('multistage_dcf',dict(common,**a[name]))
        # 独立开源NPV核对：t=0为0；第五年现金流加终值，不能把终值再折现一次。
        flows = [0]+[r['cash_flow'] for r in run['result']['forecast']]
        flows[-1] += run['result']['terminal_value']
        npv = calculate('cashflow',dict(operation='npv',cashflows=flows,interest_rate=a[name]['discount_rate']))
        difference = abs(npv['result']['value']-run['result']['equity_value'])
        assert math.isclose(npv['result']['value'],run['result']['equity_value'],rel_tol=1e-12)
        checks.append(dict(id='calc_'+name, check='numpy-financial NPV与股权价值核对',absolute_difference_usd=difference,passed=True))
        record('calc_'+name,run,'value_per_share','currency_per_share',['a_'+name],['o_fcf'])
        runs['npv_'+name] = npv
    reverse = calculate('reverse_dcf',dict(common,target_price=f['market_price'],years=5,discount_rate=.10,terminal_growth=.03))
    assert reverse['result']['status']=='converged'
    confirm = calculate('multistage_dcf',dict(common,growth_rates=[reverse['result']['implied_growth']]*5,discount_rate=.10,terminal_growth=.03))
    error = abs(confirm['result']['value_per_share']-f['market_price'])
    assert error < 1e-7
    checks.append(dict(id='calc_reverse',check='求根增速正向重算报价',price_error_usd=error,passed=True))
    record('calc_reverse',reverse,'implied_growth','ratio',['a_base'],['o_price','o_fcf'])
    runs['reverse_forward_check'] = confirm
    matrix = sensitivity(dict(common,**a['base']),a['sensitivity_discount_rates'],a['sensitivity_terminal_growth_rates'])
    sensitivity_refs=[]
    for i,row in enumerate(matrix):
        cid='calc_sensitivity_'+str(i+1)
        run=row['calculation']
        flows=[0]+[r['cash_flow'] for r in run['result']['forecast']]
        flows[-1]+=run['result']['terminal_value']
        check=calculate('cashflow',dict(operation='npv',cashflows=flows,interest_rate=row['discount_rate']))
        assert math.isclose(check['result']['value'],run['result']['equity_value'],rel_tol=1e-12)
        checks.append(dict(id=cid,check='独立NPV折现核对',passed=True))
        record(cid,run,'value_per_share','currency_per_share',['a_sensitivity'],['o_fcf'])
        sensitivity_refs.append(cid)
    for cid,op,num,den in [
        ('calc_pe','pe',f['market_price'],f['diluted_eps_2026']),
        ('calc_margin','operating_margin',f['operating_income_2026'],f['revenue_2026']),
        ('calc_liquidity','current_ratio',f['current_assets_2026'],f['current_liabilities_2026'])]:
        run=calculate('financial_ratio',dict(operation=op,numerator=num,denominator=den))
        assert math.isclose(run['result']['value'],num/den,rel_tol=1e-12)
        checks.append(dict(id=cid,check='FinanceToolkit与转录数值除法核对',passed=True))
        record(cid,run,'value','multiple' if op!='operating_margin' else 'ratio',[],['o_price'] if op=='pe' else ['o_margin'] if op=='operating_margin' else [])
    derived=dict(revenue_growth=f['revenue_2026']/f['revenue_2025']-1,
        nearline_capacity_growth=f['nearline_eb_2026']/f['nearline_eb_2025']-1,
        hdd_capacity_growth=f['hdd_eb_2026']/f['hdd_eb_2025']-1,
        decline_from_52w_high=1-f['market_price']/f['high52'],
        position_in_52w_range=(f['market_price']-f['low52'])/(f['high52']-f['low52']),
        fcf_yield=f['fcf_2026']/f['marketcap_usd_million'],
        owner_cash_proxy_yield=(f['fcf_2026']-f['sbc_2026'])/f['marketcap_usd_million'],
        net_debt_usd=(f['current_debt_2026']+f['long_debt_2026']-f['cash_2026'])*1e6)
    write('calculations.json',dict(acquired_evidence_cutoff=now,inputs_path=prefix+'inputs.json',cash_proxy_usd=cash,
        shares_proxy=shares,runs=runs,sensitivity=matrix,descriptive_arithmetic=derived,
        formulas='增长=本期/上期-1；距高点=1-price/high52；区间=(price-low)/(high-low)；收益率=现金/市值；净债务=账面有息债务-现金'))
    write('verification.json',dict(verified_at=now,scope='输入桥及数值实现；不是假设真实性或证券买入验证',checks=checks,
        fcf_bridge_check=f['cfo_2026']-f['capex_2026']==f['fcf_2026'],all_passed=all(c['passed'] for c in checks)))

    def assessment(text, refs, limits=None):
        return dict(verdict=text,claim_refs=refs,limitations=limits or ['仅定性判断；不代表统计校准'])
    trigger=dict(id='stx_thesis_change',description='技术、现金流或财务口径改变后回退研究',
        metric_ids=['fcf','operating_margin','hardware_driver_1','hardware_driver_2'],
        condition_description='实际披露表明HAMR认证/良率延误、订单削减、提价逆转或资本需求增加；先核对原文，不使用未校准固定阈值',
        claim_refs=['c_risk','c_unknown'],target_steps=['S1','S2','S3','S4','S5'])
    monitor=[dict(metric_id=metric,rationale=reason,cadence='quarterly',baseline_observation_refs=[oid] if oid else [],
        missing_baseline_reason=None if oid else '没有公开可用且同口径的数值，不用代理值顶替') for metric,oid,reason in [
        ('fcf','o_fcf','检验增量利润是否转成现金，结合SBC和资本开支'),
        ('operating_margin','o_margin','检验定价与产品组合的盈利传导'),
        ('net_debt','o_debt','跟踪债务偿还及可转债现金结算'),
        ('hardware_driver_1',None,'硬盘台数与容量需分别取得，不混用EB'),
        ('hardware_driver_2',None,'跟踪真实渠道库存，禁止用公司库存代替')]]
    outputs=[
        dict(segment_positions=[dict(segment_id='storage',industry_rule_id='hardware',positions={
            'lifecycle':assessment('成熟产业中的高容量技术升级',['c_identity','c_cycle']),
            'supply_demand':assessment('公司层面nearline扩张和有利定价；全行业供需未定',['c_capacity','c_cycle']),
            'earnings':assessment('已披露盈利处于明显扩张；周期峰值未判定',['c_profit','c_cycle']),
            'credit':assessment('账面降债；行业信用周期证据不足',['c_risk','c_unknown']),
            'sentiment':assessment('没有资金流和期权序列，情绪周期未知',['c_unknown']),
            'pricing':assessment('报价要求高增长；距52周高点不等于行业深跌',['c_value','c_watch'])})],
            research_priorities=['HAMR现金回报与稀释','需求/定价持续性','渠道库存与同行供需','全周期现金流正常化'],conclusion_claim_refs=['c_cycle']),
        dict(checks={k:assessment(v,r) for k,v,r in [
            ('business_model','硬件产品销售，现金回收随周期变化',['c_identity']),
            ('demand_growth','nearline容量和数据中心占比上升',['c_capacity']),
            ('competition','高容量路线优势待持续验证；有HDD同业及NAND替代',['c_risk']),
            ('financial_quality','GAAP利润改善；53/52周与非GAAP口径已分开',['c_profit']),
            ('cash_flow','FCF改善；SBC与偿债使股东现金不同于公司FCF',['c_bridge']),
            ('debt_liquidity','账面降债，但可转债现金结算与稀释尚需模拟',['c_risk']),
            ('governance','BIS及诉讼披露已列出；专项代理声明审阅未完成',['c_risk','c_unknown']),
            ('capital_allocation','还债优先、分红和回购；不能把资本回报直接当作盈利质量',['c_profit','c_risk'])]},
            thesis_claim_refs=['c_quality'],critical_unknown_claim_refs=['c_unknown']),
        dict(catalysts=[],no_catalyst_reason='HAMR和财报可能改变判断，但本次没有核实具体未来发生日；不登记已确定的事件催化剂',
            monitoring_indicators=monitor,invalidation_triggers=[trigger]),
        dict(valuation_method='multistage_dcf / FCFE proxy; reverse_dcf; FinanceToolkit PE crosscheck',
            applicability_claim_refs=['c_bridge','c_value'],price_observation_ref='o_price',
            scenarios=[dict(name=n,assumption_refs=['a_'+n],intrinsic_value_per_share=calcs[['calc_bear','calc_base','calc_bull'].index('calc_'+n)]['outputs'][0],
                calculation_refs=['calc_'+n],probability=None) for n in ['bear','base','bull']],
            probability_basis_claim_refs=[],crosscheck_calculation_refs=['calc_pe','calc_reverse'],sensitivity_calculation_refs=sensitivity_refs,
            market_expectation_claim_refs=['c_value'],value_bridge_claim_refs=['c_bridge'],
            valuation_horizon={'start':'2026-10-11','end':'2031-10-11','basis':'custom'},
            investment_horizon={'start':'2026-10-11','end':'2027-10-11','basis':'custom'},
            limitations=['现金流代理尚未正常化；可转债未完整模拟','折现率/增速为假设，非目标价','年度年末折现；假设一年后的现金流以FY2026为基期；未做月度过渡','PE使用已披露年度，不年化Q1指引']),
        dict(decision='watch',company_quality=assessment('经营改善、风险可识别；长期优势待验证',['c_quality']),
            price_attractiveness=assessment('本参数下未证实安全边际',['c_value']),
            action_suitability=assessment('观察；关键未知和校准不足',['c_watch']),
            permanent_loss_risks=[assessment('技术失败/客户订单流失/永久替代',['c_risk']),assessment('高价资本化不可持续利润、稀释和现金偿付',['c_value','c_risk'])],
            entry_conditions=['取得同口径最新实际与正常化现金流','完成债务/稀释模拟及独立行情核实','只在有证据的价格与风险边界下重新评估'],
            exit_conditions=['需求或技术优势被原文证据否定','现金回报长期低于维持技术与偿债所需'],
            portfolio_assessment='not_assessed',portfolio_evidence_refs=[],portfolio_calculation_refs=[],position_fraction=None,
            validated_rule_refs=[],decision_claim_refs=['c_watch']),
        dict(monitoring_plan=[dict(metric_id=m['metric_id'],cadence=m['cadence'],owner='研究执行agent（未配置自动任务）',
            last_observation_ref=m['baseline_observation_refs'][0] if m['baseline_observation_refs'] else None,next_due_at='2026-10-19T00:00:00Z') for m in monitor],
            triggers=[trigger],review_records=[],next_review_at='2026-11-02T00:00:00Z')]
    from validate_research import GATES
    reasons=[
        ['SEC证券身份及单一分部已核对；按硬件/产品销售归类','六维均给出有依据的定性结论或未知边界，未启用数值规则','原始摘录、单位、期间和本地引用完整'],
        ['八项检查均给出结论及未知；完成范围为观察型研究','客户、技术、债券及法律反证与正面论点并列','53/52周、GAAP/非GAAP、EB/台数和不同股数已拆开'],
        ['需求容量→产品组合/定价→利润/现金路径有原文，确定事件日期不足已说明','现金及利润有基线，渠道和台数缺口明确登记','技术、订单和偿付变化触发全部相关步骤重算'],
        ['股权现金代理适用范围及正常化不足明确，不将FCF冒充FCFF','三情景输入和中间结果齐全，概率留空，开源NPV逐项核对','年度PE和反向DCF交叉检查，已重算求根','九格折现率/终值敏感性保留并独立NPV核对','股权口径不二次扣债务，现金/SBC/股数桥及其不足明确'],
        ['永久损失路径与一般波动分开记录','已评估且判断行动条件尚未满足，输出watch','组合未评估；仓位null，无组合计算或交易指令','观察结论回连报价、假设和风险证据'],
        ['计划时间晚于截止时刻；不假称财报确定日','新证据须回退重算；不能沿用旧结论','复盘计划已给出，尚无已执行复盘记录']]
    steps=[]
    for i,out in enumerate(outputs):
        sid='S'+str(i+1)
        steps.append(dict(id=sid,version=1,status='completed',updated_at=now,
            inputs=dict(dependencies=[dict(step_id='S'+str(j),version=1) for j in range(1,i+1)],
                evidence_refs=[e['id'] for e in evidence],observation_refs=[o['id'] for o in observations],claim_refs=[c['id'] for c in claims]),
            gates=[dict(id=g,result='pass',reason=reason,evidence_refs=['e_10k','e_results','e_checks'] if i>=3 else ['e_10k','e_results']) for g,reason in zip(GATES[sid],reasons[i])],
            output=out,notes=['研究输出验收通过≠公司无风险、假设真实或可以买入；结论为watch。']))
    research=dict(schema_version='1.1.0',research_id='seagate_20261011',revision=1,is_fictional=False,
        as_of=now,recorded_at=now,market_session_date='2026-10-09',investment_horizon_months=12,
        subject=dict(company_id='seagate',security_ids=['NASDAQ:STX'],segments=[dict(id='storage',name='存储产品（单一会计分部）',
            industry_ids=['hardware'],business_model_ids=['product_sales'],classification_evidence_refs=['e_10k'],
            subindustry_description='大容量HDD/存储系统；Data Center和Edge IoT为市场维度',weight_basis='revenue',weight=1,
            weight_period=annual,weight_evidence_refs=['e_10k'])],is_adr=False,is_reit=False,classification_status='reviewed',
            unallocated_or_elimination_notes='不制造未披露的独立分部利润；80%/20%是市场收入构成，不是两个会计分部。'),
        evidence=evidence,observations=observations,claims=claims,calculations=calcs,steps=steps,invalidation_events=[])
    validate(research)
    write('research.json',research)
    for manifest in manifests:
        write('manifests/'+manifest['source_id']+'.json',manifest)
    write('source-map.json',{e['id']:dict(source_id=m['source_id'],revision=1) for e,m in zip(evidence,manifests)})
    print(json.dumps({'research':'data/seagate/2026-10-11/research.json','as_of':now,
        'values':{n:runs['calc_'+n]['result']['value_per_share'] for n in ['bear','base','bull']},
        'implied_growth':reverse['result']['implied_growth'],'descriptive':derived},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
