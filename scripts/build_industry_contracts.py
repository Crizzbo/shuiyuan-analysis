"""建立行业知识契约和指标口径契约；仅使用项目内资料，种子不宣称经验验证。"""
import json
from pathlib import Path
from build_research_schema import obj, arr, ref, S, IDS, POS, maybe, enum

ROOT = Path(__file__).resolve().parents[1]
LABELS = {
 'schema_version': ('契约版本', '本数据结构版本，与知识修订和统计验证状态分开。'),
 'revision': ('知识修订号', '该知识对象的修订标识；此模块尚无不可变历史登记接口。'),
 'industry_id': ('行业标识', '引用项目行业字典的 industry 节点。'),
 'metric_id': ('指标标识', '引用现有指标字典；细化口径不能冒充不同公司的可比观测。'),
 'name_zh': ('中文名称', '知识对象或指标的中文阅读名称。'),
 'scope': ('适用边界', '明确包含的业务和排除的业务，不表示证券自动分类完成。'),
 'required_segmentation': ('必需细分项', '研究前须解释的产品、收入模式、地区等细分口径。'),
 'business_model_ids': ('商业模式标识列表', '候选模式，实际公司分部归类需另有证据。'),
 'dimension_id': ('研究维度标识', '长期生命周期与供需、盈利、融资、情绪、定价分别登记。'),
 'question': ('研究问题', '本维度需要回答的问题，而非预设结论。'),
 'dimensions': ('维度要求列表', '恰好六个不同维度，语义检查集合完整性。'),
 'required_metric_ids': ('必查指标列表', '须检查适用性和可得性的指标；允许说明不适用，但不能跳过整个维度。'),
 'evidence_requirements': ('证据要求列表', '拟取证的内容、口径及时间要求，不表示已有该证据。'),
 'judgment_criteria': ('判断准则', '定性判断条件，不构成统计验证后的数值阈值。'),
 'improving': ('改善判断条件', '哪些证据组合支持改善，并须检查相反解释。'),
 'deteriorating': ('恶化判断条件', '哪些证据组合支持恶化，区分周期与结构因素。'),
 'unknown': ('无法判断条件', '缺失、冲突、不可比或边界未定义时应返回 unknown。'),
 'counterevidence': ('反证方向列表', '应主动查找的相反证据；不是已登记的实际反证。'),
 'valuation_routes': ('估值适配路径列表', '按商业模式选择的方法及适用限制，未执行估值计算。'),
 'method': ('方法说明', '估值路线或指标计算的具体文字口径。'),
 'applicability': ('适用条件', '方法、指标或资料可以使用的业务范围。'),
 'limitations': ('局限说明列表', '缺口、失效条件和不可自动检查的事项。'),
 'source_refs': ('项目内设计依据', '引用支持知识设计的文件及原文位置；不得冒充公司事实。'),
 'source_path': ('依据文件路径', '相对项目根目录的已存在文件，真实路径不得越界。'),
 'locator': ('依据定位信息', '章节、条目或 JSON 对象标识；由人工核实内容相关性。'),
 'source_kind': ('依据类型', 'project_design 为项目知识设计，primary/secondary 为实际资料，synthetic 为模拟。'),
 'statistical_validation_status': ('统计验证状态', '本版仅登记未验证种子或验证计划，不能切换成已验证。'),
 'empirical_validation_plan': ('经验验证计划', '未来数据、时点控制、时间分割及样本外评估的计划，不是结果。'),
 'thresholds': ('行业阈值状态', '深跌与估值数值尚未验证，当前必须保持 null。'),
 'drawdown': ('深跌阈值', '当前禁止启用；回撤仅为候选提示。'),
 'valuation': ('估值阈值', '当前禁止统一估值阈值，按商业模式研究。'),
 'research_gate': ('真实研究验收要求', '明确知识设计完成与真实分析通过是不同条件。'),
 'required_steps': ('要求覆盖步骤', '六步仍按 S1—S6 执行，本契约不替代 research.schema。'),
 'missing_data_action': ('缺资料处理', '缺本地数据时返回证据不足，不自动访问外部资料或补零。'),
 'real_case_status': ('真实样板状态', '当前没有公司观测和真实结论，样板为知识设计填写示例。'),
 'external_reference_status': ('猫哥参考资料状态', '记录所请求外部资料是否已在本项目内核对，本版尚未取得。'),
 'definitions': ('指标口径定义列表', '对现有指标定义作可计算性和取数要求登记，非观测数据。'),
 'definition_status': ('口径状态', 'specified 是已写明口径，needs_definition 是仍待细化；均不等于统计验证。'),
 'formula': ('公式或计算方法', '可计算时明确公式；复合指标未拆分时允许 null 并登记阻断原因。'),
 'inputs': ('公式输入项列表', '记录输入名称及来源方向，未来接入时还需绑定具体观测。'),
 'denominator': ('分母口径', '比例类明确分母；非比例应写不适用而非随意留空。'),
 'unit': ('计量单位', '必须与指标字典一致；context_defined 表示仍需选择具体单位，不能用于观测值。'),
 'period_basis': ('统计期间口径', '季度、年度、TTM、单时点或 source_dependent；取值时明确对应日期。'),
 'cadence': ('更新频率', '按原始资料实际发布频率取值，不表示调度已实现。'),
 'comparability_notes': ('可比性说明', '统一合并范围、货币、复权、分母和版本等口径后方可比较。'),
 'missing_data_policy': ('缺失数据策略', '不补零、不猜测；保留缺失原因并限制计算和结论。'),
 'source_requirements': ('实际取数证据要求', '需要哪些原始资料支持实际值；设计依据不能代替这些资料。'),
 'blocking_reasons': ('口径阻断原因列表', '阻止指标直接计算、跨公司比较或阈值启用的缺口。'),
 'validation_status': ('口径验证状态', 'not_validated 为仅设计；不代表公式和金融适用性已测试。'),
}

def schema_obj(fields):
    result = obj(fields)
    for name, node in result['properties'].items():
        node = dict(node)
        node['title'], node['description'] = LABELS[name]
        result['properties'][name] = node
    return result

def write(path, value):
    target = ROOT/path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

DIMENSIONS = {
 'lifecycle': ('长期生命周期', '产品需求、市场边界和渗透率处于何种长期阶段？'),
 'supply_demand': ('供需与资本周期', '供给扩张、资本开支、库存与需求如何相互影响？'),
 'earnings': ('盈利周期', '利润、经营杠杆与正常化现金流处于什么位置？'),
 'credit': ('信贷与融资', '融资成本、契约、债务到期和资本供给是否变化？'),
 'sentiment': ('情绪与风险偏好', '市场风险偏好和预期变化是否有可核对资料？'),
 'pricing': ('定价与预期', '价格包含哪些经营预期，价值情景如何反映风险？'),
}

def build():
    source = schema_obj({'source_path': S, 'locator': S, 'source_kind': enum('project_design','primary','secondary','synthetic')})
    criteria = schema_obj({k: S for k in ('improving','deteriorating','unknown')})
    dimension = schema_obj({'dimension_id': enum(*DIMENSIONS), 'name_zh': S, 'question': S,
        'required_metric_ids': IDS, 'evidence_requirements': arr(S,1),
        'judgment_criteria': ref('criteria'), 'counterevidence': arr(S,1)})
    route = schema_obj({'business_model_ids': IDS, 'method': S, 'applicability': S, 'limitations': arr(S,1)})
    schema = schema_obj({'schema_version': {'const':'1.0.0'}, 'revision': POS, 'industry_id': S, 'name_zh': S,
        'scope': S, 'required_segmentation': arr(S,1), 'business_model_ids': IDS,
        'required_metric_ids': IDS, 'dimensions': arr(ref('dimension'),6), 'valuation_routes': arr(ref('route'),1),
        'source_refs': arr(ref('source'),1), 'statistical_validation_status': enum('not_validated','validation_planned'),
        'empirical_validation_plan': S, 'thresholds': schema_obj({'drawdown': {'type':'null'}, 'valuation': {'type':'null'}}),
        'research_gate': schema_obj({'required_steps': arr(enum('S1','S2','S3','S4','S5','S6'),6),
            'missing_data_action': {'const':'insufficient_evidence'}, 'real_case_status': {'const':'pending_local_data'}}),
        'external_reference_status': enum('not_available_in_project','project_copy_reviewed')})
    schema['properties']['dimensions']['maxItems'] = 6
    schema['properties']['research_gate']['properties']['required_steps']['maxItems'] = 6
    schema.update({'$schema':'https://json-schema.org/draft/2020-12/schema', '$id':'urn:shuiyuan:industry-knowledge:1.0.0',
        '$defs': {'source':source,'criteria':criteria,'dimension':dimension,'route':route},
        'title':'行业知识库设计契约（非公司研究结果）'})
    write('schemas/industry-knowledge.schema.json',schema)
    definition = schema_obj({'metric_id':S,'name_zh':S,'definition_status':enum('specified','needs_definition'),
        'formula':maybe(S),'inputs':arr(S),'denominator':maybe(S),'unit':S,
        'period_basis':S,'cadence':S,'applicability':S,'comparability_notes':S,
        'missing_data_policy':{'const':'record_null_and_block_calculation'}, 'source_requirements':arr(S,1),
        'source_refs':arr(ref('source'),1),'blocking_reasons':arr(S),'validation_status':{'const':'not_validated'}})
    metric_schema = schema_obj({'schema_version':{'const':'1.0.0'},'revision':POS,'definitions':arr(ref('definition'),1)})
    metric_schema.update({'$schema':schema['$schema'],'$id':'urn:shuiyuan:metric-definition:1.0.0',
        '$defs':{'source':source,'definition':definition},'title':'指标口径设计目录'})
    write('schemas/metric-definition.schema.json',metric_schema)
    nodes = json.loads((ROOT/'knowledge/taxonomy/industries.json').read_text(encoding='utf-8'))['nodes']
    rules = json.loads((ROOT/'knowledge/taxonomy/industry_rules.json').read_text(encoding='utf-8'))['rules']
    metrics = json.loads((ROOT/'knowledge/metrics/catalog.json').read_text(encoding='utf-8'))['metrics']
    node_map = {n['id']:n for n in nodes}
    specs = []
    for m in metrics:
        # 现有公式文字只有通用简单口径可以作为待复核的 specified；行业复合驱动不得自动转成公式。
        specified = m['id'] in {'revenue_growth','operating_margin','market_price'}
        specs.append({'metric_id':m['id'],'name_zh':m['name'],
            'definition_status':'specified' if specified else 'needs_definition',
            'formula':m['definition'] if specified else None,
            'inputs':{'revenue_growth':['本期可比收入','同期可比收入'],
                'operating_margin':['同期间营业利润','同期间收入'],
                'market_price':['证券标识','交易日期及盘段','价格类型','复权口径','报价币种']}.get(m['id'],[]),
            'denominator': {'revenue_growth':'上年同期同币种、同业务范围收入', 'operating_margin':'同期间收入',
                'roe':'按项目定义确认平均或期末股东权益；比较前不得混用', 'market_price':'不适用；每股报价'} .get(m['id']),
            'unit':m['unit'],'period_basis':'point_in_time' if m['id']=='market_price' else 'source_dependent',
            'cadence':m['cadence'],'applicability':m['applicability'],'comparability_notes':m['comparability_notes'],
            'missing_data_policy':'record_null_and_block_calculation',
            'source_requirements':[m.get('source_candidates','项目内可定位的原始取数资料'), '实际值必须另行登记期间、口径、单位、可得时间及证据'],
            'source_refs':[{'source_path':'knowledge/metrics/catalog.json','locator':'metrics[id='+m['id']+']','source_kind':'project_design'}],
            'blocking_reasons':[] if specified else ['现有定义尚需明确输入、分母、统计期间及复合指标拆分，不能直接计算'],
            'validation_status':'not_validated'})
    write('knowledge/contracts/metric-definitions.json',{'schema_version':'1.0.0','revision':1,'definitions':specs})
    for rule in rules:
        n = node_map[rule['industry_id']]
        base_refs = [{'source_path':p,'locator':'行业研究及风险原则；具体应用属于项目设计', 'source_kind':'project_design'} for p in rule['evidence_refs']]
        profile = {'schema_version':'1.0.0','revision':1,'industry_id':n['id'],'name_zh':n['name'],
            'scope': '按项目行业定义研究 '+n['name']+'；跨行业业务按分部拆分，具体边界须结合分类证据确认。',
            'required_segmentation':rule['required_segmentation'],'business_model_ids':n['business_model_ids'],
            'required_metric_ids':rule['metric_ids'],
            'dimensions':[{'dimension_id':key,'name_zh':label,'question':question,
                'required_metric_ids':rule['metric_ids'] if key in ('lifecycle','supply_demand','earnings') else [],
                'evidence_requirements':['按 '+label+' 核对 '+n['name']+' 的时点可得资料，明确分部及可比口径',
                    '行业指标未覆盖本维度时须补充证据或说明未知，空指标列表不代表无需研究'],
                'judgment_criteria':rule['judgment'], 'counterevidence':[rule['counterevidence'], '验证该维度是否被其他周期或结构变化抵消']}
                for key,(label,question) in DIMENSIONS.items()],
            'valuation_routes':[{'business_model_ids':n['business_model_ids'],'method':rule['valuation_route'],
                'applicability':'仅为候选路线；公司研究须按实际业务模式说明采用及不采用理由',
                'limitations':['缺实际财务、价格和本地计算结果时不得完成 S4','该路线未证明适合所有列出的模式']}],
            'source_refs':base_refs+[{'source_path':'knowledge/framework/cycles.md','locator':'周期与生命周期研究框架','source_kind':'project_design'}],
            'statistical_validation_status':'not_validated',
            'empirical_validation_plan':'；'.join(rule['empirical_plan'].values()),
            'thresholds':{'drawdown':None,'valuation':None},
            'research_gate':{'required_steps':['S1','S2','S3','S4','S5','S6'],
                'missing_data_action':'insufficient_evidence','real_case_status':'pending_local_data'},
            'external_reference_status':'not_available_in_project'}
        for filename, locator in [('marks_notes.txt','第 8 章 关注周期；第 14 章 认识预测的局限性'),
                                  ('industry_cycle_notes.txt','第 2 节 纵向；第 3 节 横向')]:
            local = 'knowledge/sources/cat_reference/'+filename
            if (ROOT/local).is_file():
                profile['source_refs'].append({'source_path':local,'locator':locator,'source_kind':'secondary'})
                profile['external_reference_status']='project_copy_reviewed'
        write('knowledge/contracts/industries/'+n['id']+'.json',profile)
    # 软件样板增加业务针对性，但没有公司观测，不把设计样例伪装成真实研究。
    p = ROOT/'knowledge/contracts/industries/software.json'
    sample = json.loads(p.read_text(encoding='utf-8'))
    sample['scope']='企业及应用软件；订阅、用量计费和授权收入分别研究。硬件、纯咨询、云基础设施等不能因涉及软件就归入本范围。'
    if (ROOT/'knowledge/sources/cat_reference/intu_research.txt').is_file():
        sample['source_refs'].append({'source_path':'knowledge/sources/cat_reference/intu_research.txt',
            'locator':'二、第①步 生命周期定位；三、第②步 阶段聚焦', 'source_kind':'secondary'})
        sample['source_refs'].append({'source_path':'knowledge/sources/cat_reference/sp500_reference.csv',
            'locator':'表头：代码、公司名、行业、细分行业、公司业务；仅供候选身份映射', 'source_kind':'secondary'})
        sample['external_reference_status']='project_copy_reviewed'
    sample['required_segmentation'].append('正式报告分部与产品交叉口径区分；在线生态不能自动视为独立、不重叠分部')
    requirements = {
        'lifecycle':['定义企业客户与产品市场边界、渗透率分母、新增市场和替代需求；不能用 ARR 增速直接判定发展阶段'],
        'supply_demand':['核对客户预算、席位/用量、竞争供给和部署限制；不能机械套用制造业库存周期'],
        'earnings':['区分 ARR、收入确认、净留存、现金回收、股权薪酬和正常化自由现金流'],
        'credit':['核对现金、债务到期、融资条件及客户信用风险；经营现金流不等于无融资风险'],
        'sentiment':['核对可定位的市场预期及风险偏好资料；股价下跌本身不证明恐慌'],
        'pricing':['订阅/用量/授权分别建立现金流假设，扣除真实经济成本并桥接每股价值；本地计算未完成时不能裁决'],
    }
    for d in sample['dimensions']:
        d['evidence_requirements'] = requirements[d['dimension_id']]
        d['judgment_criteria'] = {'improving':'针对本维度的证据改善，且反证没有推翻该解释；不得由另一维度代替判断',
            'deteriorating':'本维度证据恶化，明确暂时周期与永久结构变化，不能只依据价格变化',
            'unknown':'相关资料缺失、口径不明、证据矛盾或输入不可比时返回 unknown'}
    write('knowledge/contracts/industries/software.json',sample)
    write('examples/industry-software.design.json',sample)
    print('Built 2 schemas, 41 design profiles, 146 metric specifications and software design sample.')

if __name__ == '__main__':
    build()
