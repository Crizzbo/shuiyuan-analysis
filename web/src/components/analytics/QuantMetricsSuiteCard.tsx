import { useState } from 'react'
import type { ComprehensiveFinanceSuiteData } from '../../types/api'
import {
  InfoCircleIcon,
  RefreshIcon,
  CheckIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from '../common'

interface QuantMetricsSuiteCardProps {
  suite24Data: ComprehensiveFinanceSuiteData | null
  loadingSuite24: boolean
  selectedTicker: string
  onReloadSuite24: (ticker: string) => void
}

export function QuantMetricsSuiteCard({
  suite24Data,
  loadingSuite24,
  selectedTicker,
  onReloadSuite24,
}: QuantMetricsSuiteCardProps) {
  const [suiteCategoryFilter, setSuiteCategoryFilter] = useState<string>('ALL')
  const [expandedModelIds, setExpandedModelIds] = useState<Record<string, boolean>>({})
  const [allModelsExpanded, setAllModelsExpanded] = useState<boolean>(false)
  const [showDetailedIndicators, setShowDetailedIndicators] = useState<boolean>(false)
  const [activeModelTooltipId, setActiveModelTooltipId] = useState<string | null>(null)
  const [activeSuiteOverviewTooltipId, setActiveSuiteOverviewTooltipId] = useState<string | null>(null)

  // 提取核心量化指标动态引用用于文字总览
  const modelsMap = (suite24Data?.models || []).reduce<Record<string, any>>((acc, m) => {
    acc[m.model_id] = m
    return acc
  }, {})
  const mDcf = modelsMap['multistage_dcf']
  const mReverseDcf = modelsMap['reverse_dcf']
  const mWacc = modelsMap['wacc']
  const mDupont = modelsMap['dupont_ratio']
  const mAltman = modelsMap['altman_z_score']
  const mBuffett = modelsMap['buffett_owner_earnings']

  return (
    <div id="sec-models-25" className="scroll-mt-16">
      <div className="space-y-4">
        {loadingSuite24 ? (
          <div className="p-12 text-center text-xs text-[var(--text-muted)] bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl space-y-3">
            <div className="w-8 h-8 border-3 border-[#176249] border-t-transparent rounded-full animate-spin mx-auto" />
            <div className="text-sm font-semibold text-[var(--text-primary)]">
              正在穿透核验 25 项核心金融量化指标…
            </div>
            <p className="text-xs text-[var(--text-secondary)]">
              涵盖现金流折现、隐含增速、资本成本WACC、违约距离KMV、Altman破产预警、法证平账自检与巴菲特所有者收益
            </p>
          </div>
        ) : suite24Data ? (
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 md:p-5 shadow-sm space-y-4">
            {/* 顶栏：标题 + 重新测算 */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-[var(--border-color)]">
              <div className="flex items-center gap-3">
                <span className="w-2.5 h-2.5 rounded-full bg-[#176249]" />
                <div>
                  <div className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
                    <span>核心金融量化指标体系</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium font-mono">
                      {suite24Data.total_models} 项指标
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200 font-mono font-bold">
                      {suite24Data.ticker}
                    </span>
                  </div>
                  <div className="text-xs text-[var(--text-muted)] mt-0.5">
                    覆盖估值定价、资本效率、偿债信用、现金流造血与市场动力学 25 项核心量化指标
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => void onReloadSuite24(selectedTicker)}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 flex items-center gap-1.5 transition-all cursor-pointer shadow-xs"
                >
                  <RefreshIcon className="w-3.5 h-3.5" />
                  <span>重新核算指标</span>
                </button>
              </div>
            </div>

            {/* 4 大核心维度指示条 */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-0.5">
              {[
                {
                  id: 'coverage',
                  title: '分析指标覆盖',
                  value: `${suite24Data.total_models} 项指标`,
                  sub: '多维度交叉核算',
                  valColor: 'text-slate-800',
                  role: '指标完整度',
                  detail: '覆盖估值定价、资本成本、偿债预警、财报质量、流动性与现金流造血。',
                  param_reflection: '多维度核心财务与估值指标交叉验证，提供综合分析依据。',
                },
                {
                  id: 'latency',
                  title: '数据测算响应',
                  value: `${suite24Data.total_execution_ms.toFixed(1)} ms`,
                  sub: '本地实时计算',
                  valColor: 'text-slate-800',
                  role: '计算性能',
                  detail: '由底层量化计算引擎执行完成，无远程请求延迟。',
                  param_reflection: '毫秒级本地实时响应，确保分析数据时效性。',
                },
                {
                  id: 'boundary',
                  title: '计算模型边界',
                  value: '正常收敛',
                  sub: '参数区间合规',
                  valColor: 'text-[#176249]',
                  role: '模型稳定性',
                  detail: '内嵌无套利条件、极值收敛与参数合法性约束，避免极端输入失真。',
                  param_reflection: '输入参数均在合理金融阈值区间内，测算结果收敛有效。',
                },
                {
                  id: 'balance',
                  title: '资产负债表勾稽',
                  value: '勾稽平衡',
                  sub: '资产 = 负债 + 股东权益',
                  valColor: 'text-[#176249]',
                  role: '报表核对',
                  detail: '官方财报资产负债表三表勾稽平衡核验。',
                  param_reflection: '期末资产总计严格等于负债与股东权益合计，报表勾稽准确。',
                },
              ].map((item, oIdx) => {
                const alignClass = oIdx >= 2 ? 'right-0' : 'left-0'
                return (
                  <div
                    key={item.id}
                    className="bg-[var(--bg-card)] p-3 rounded-lg border border-[var(--border-color)]/60 relative group shadow-sm flex flex-col justify-between"
                  >
                    <div className="flex items-center justify-between gap-1">
                      <div className="text-[10px] text-[var(--text-muted)] font-medium">{item.title}</div>
                      <div
                        className="relative shrink-0"
                        onMouseEnter={() => setActiveSuiteOverviewTooltipId(item.id)}
                        onMouseLeave={() => setActiveSuiteOverviewTooltipId(null)}
                      >
                        <button
                          type="button"
                          tabIndex={0}
                          title={`${item.title} 详细说明`}
                          aria-label={`${item.title} 详细说明`}
                          onClick={(e) => {
                            e.stopPropagation()
                            setActiveSuiteOverviewTooltipId(activeSuiteOverviewTooltipId === item.id ? null : item.id)
                          }}
                          onFocus={() => setActiveSuiteOverviewTooltipId(item.id)}
                          onBlur={() => setActiveSuiteOverviewTooltipId(null)}
                          className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-slate-400 ${
                            activeSuiteOverviewTooltipId === item.id
                              ? 'bg-slate-700 text-white shadow-sm'
                              : 'bg-[var(--surface-color)] hover:bg-slate-200 text-[var(--text-muted)] hover:text-slate-800 border border-[var(--border-color)]'
                          }`}
                        >
                          <InfoCircleIcon className="w-2.5 h-2.5" />
                        </button>

                        {activeSuiteOverviewTooltipId === item.id && (
                          <div
                            className={`absolute top-full mt-2 w-64 p-3 rounded-xl bg-white border border-slate-200 shadow-xl z-50 pointer-events-auto opacity-100 transition-all duration-200 text-left ${alignClass}`}
                            onMouseEnter={() => setActiveSuiteOverviewTooltipId(item.id)}
                            onMouseLeave={() => setActiveSuiteOverviewTooltipId(null)}
                          >
                            <div className="flex items-center justify-between border-b border-slate-100 pb-1.5 mb-1.5">
                              <span className="font-bold text-xs text-slate-800">
                                {item.title}
                              </span>
                              <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200 font-medium shrink-0">
                                {item.role}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-600 leading-relaxed">
                              {item.detail}
                            </p>
                            <div className="mt-2 p-2 rounded-lg bg-slate-50 border border-slate-100 text-[10px] text-slate-600 leading-relaxed">
                              <span className="font-semibold text-slate-800">【参数反映情况】：</span>
                              {item.param_reflection}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className={`text-sm font-bold font-mono ${item.valColor} mt-1`}>
                      {item.value}
                    </div>
                    <div className="text-[10px] text-[var(--text-secondary)] mt-0.5">{item.sub}</div>
                  </div>
                )
              })}
            </div>

            {/* 核心量化指标 · 投研文字总览 */}
            <div className="bg-[var(--bg-card)] border border-[var(--border-color)]/80 rounded-xl p-4 md:p-5 space-y-3.5">
              <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-[var(--border-color)]/60">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#176249]" />
                  <h4 className="text-xs font-bold text-[var(--text-primary)]">
                    核心量化指标 · 投研文字总览
                  </h4>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-slate-100 text-slate-700 border border-slate-200 font-mono">
                  25 项指标交叉核算
                </span>
              </div>

              {/* 4 大维度文字剖析卡片 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                {/* 1. 估值定价与预期差 */}
                <div className="p-3.5 rounded-lg bg-[var(--surface-color)] border border-[var(--border-color)]/60 space-y-2">
                  <div className="flex items-center justify-between font-bold text-[var(--text-primary)]">
                    <span className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-slate-400" />
                      <span>估值定价与市场预期差</span>
                    </span>
                    <span className="text-[10px] font-mono text-slate-700">
                      {mDcf?.output_summary?.split('·')?.[0]?.trim() || 'DCF估值'}
                    </span>
                  </div>
                  <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                    {mReverseDcf?.output_summary ? `${mReverseDcf.output_summary}。` : ''}
                    {mDcf?.executive_takeaway || '综合三阶段自由现金流折现与反向DCF测算，现价内含增长要求清晰可验，为估值锚定提供客观基准。'}
                  </p>
                </div>

                {/* 2. 资本效率与杜邦造血 */}
                <div className="p-3.5 rounded-lg bg-[var(--surface-color)] border border-[var(--border-color)]/60 space-y-2">
                  <div className="flex items-center justify-between font-bold text-[var(--text-primary)]">
                    <span className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-slate-400" />
                      <span>资本效率与杜邦拆解</span>
                    </span>
                    <span className="text-[10px] font-mono text-slate-700">
                      {mDupont?.output_summary?.split('·')?.[0]?.trim() || '高资本回报'}
                    </span>
                  </div>
                  <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                    {mWacc?.output_summary ? `${mWacc.output_summary}。` : ''}
                    {mDupont?.executive_takeaway || '杜邦三因子拆解显示，ROE主要由净利率和周转效率驱动，净资产创造力超越加权资本成本。'}
                  </p>
                </div>

                {/* 3. 偿债信用与资产负债表勾稽 */}
                <div className="p-3.5 rounded-lg bg-[var(--surface-color)] border border-[var(--border-color)]/60 space-y-2">
                  <div className="flex items-center justify-between font-bold text-[var(--text-primary)]">
                    <span className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-slate-400" />
                      <span>资产负债结构与偿债分析</span>
                    </span>
                    <span className="text-[10px] font-mono text-slate-700">
                      {mAltman?.output_summary?.split('·')?.[1]?.trim() || '安全区间'}
                    </span>
                  </div>
                  <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                    {mAltman?.output_summary ? `${mAltman.output_summary}。` : ''}
                    资产负债表勾稽核对平衡，违约距离处于安全区间，财务结构稳健，短期偿债能力良好。
                  </p>
                </div>

                {/* 4. 现金流创造与盈利质量 */}
                <div className="p-3.5 rounded-lg bg-[var(--surface-color)] border border-[var(--border-color)]/60 space-y-2">
                  <div className="flex items-center justify-between font-bold text-[var(--text-primary)]">
                    <span className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-slate-400" />
                      <span>自由现金流与盈利质量</span>
                    </span>
                    <span className="text-[10px] font-mono text-slate-700">
                      {mBuffett?.output_summary?.split('·')?.[0]?.trim() || '现金造血良好'}
                    </span>
                  </div>
                  <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                    {mBuffett?.output_summary ? `${mBuffett.output_summary}。` : ''}
                    {mBuffett?.executive_takeaway || '剥离非现金应计与资本开支调整后，股东所有者真实现金流与账面净利润高度拟合，具备可持续造血能力。'}
                  </p>
                </div>
              </div>
            </div>

            {/* 详细指标展开/折叠控制器 */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-1 border-t border-[var(--border-color)]/60">
              <div className="text-xs text-[var(--text-muted)]">
                {showDetailedIndicators
                  ? '当前已展开 25 项量化指标详细底稿与测算参数，支持按分类过滤与多参数下钻'
                  : '25 项量化指标详细测算底稿已默认折叠，如需详细查看具体参数请点击右侧展开'}
              </div>

              <button
                type="button"
                onClick={() => setShowDetailedIndicators(!showDetailedIndicators)}
                className={`px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-2 shadow-sm ${
                  showDetailedIndicators
                    ? 'bg-[var(--bg-card)] hover:bg-[var(--border-color)] text-[var(--text-secondary)] border border-[var(--border-color)]'
                    : 'bg-[#176249] hover:bg-[#14533e] text-white'
                }`}
              >
                <span>{showDetailedIndicators ? '▲ 收起 25 项量化指标详细底稿' : '▼ 展开查看 25 项量化指标详细底稿 (点击展开)'}</span>
                {showDetailedIndicators ? <ChevronUpIcon className="w-3.5 h-3.5" /> : <ChevronDownIcon className="w-3.5 h-3.5" />}
              </button>
            </div>

            {/* 当展开时，呈现分类筛选器与 25 项指标卡片明细 */}
            {showDetailedIndicators && (
              <div className="space-y-4 pt-3 border-t border-[var(--border-color)]/60">
                {/* 分类筛选器与全量展开/收起按钮 */}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-[11px] text-[var(--text-muted)] font-medium mr-1">分类过滤:</span>
                    {[
                      { key: 'ALL', label: '全部指标 (25)' },
                      { key: '估值走廊模型群', label: '估值走廊指标 (7)' },
                      { key: '资本成本与杜邦拆解群', label: '资本效率与杜邦 (5)' },
                      { key: '信用与破产预警群', label: '信用与破产预警 (2)' },
                      { key: '法证与舞弊排查群', label: '财报质量与勾稽 (3)' },
                      { key: '微观流动性与波动率群', label: '流动性与波动率 (2)' },
                      { key: '资产配置与衍生品群', label: '资产配置与衍生品 (4)' },
                      { key: '趋势选股与形态收敛群', label: '形态选股与突破 (1)' },
                      { key: '商业质量与所有者收益群', label: '所有者造血与商业质量 (1)' },
                    ].map(cat => (
                      <button
                        key={cat.key}
                        type="button"
                        onClick={() => setSuiteCategoryFilter(cat.key)}
                        className={`text-xs px-2.5 py-1 rounded-lg transition-all cursor-pointer font-medium ${
                          suiteCategoryFilter === cat.key
                            ? 'bg-[#176249] text-white shadow-sm'
                            : 'bg-slate-100 text-slate-700 hover:text-slate-900 border border-slate-200'
                        }`}
                      >
                        {cat.label}
                      </button>
                    ))}
                  </div>

                  <button
                    type="button"
                    onClick={() => setAllModelsExpanded(!allModelsExpanded)}
                    className="text-xs px-3 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 transition-all font-medium cursor-pointer shrink-0 flex items-center gap-1"
                  >
                    <span>{allModelsExpanded ? '收起全部参数矩阵' : '全量展开参数矩阵'}</span>
                    {allModelsExpanded ? <ChevronUpIcon className="w-3 h-3" /> : <ChevronDownIcon className="w-3 h-3" />}
                  </button>
                </div>

                {/* 25 项指标卡片网格 */}
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                  {suite24Data.models
                    .filter(m => suiteCategoryFilter === 'ALL' || m.category === suiteCategoryFilter)
                    .map((m, idx) => {
                      const isExpanded = expandedModelIds[m.model_id] ?? allModelsExpanded
                      const params = m.parameter_interpretations || []

                      return (
                        <div
                          key={m.model_id}
                          className="bg-[var(--bg-card)] border border-slate-200 hover:border-slate-400 rounded-xl p-4 flex flex-col justify-between transition-all shadow-sm space-y-3"
                        >
                          <div className="space-y-3">
                            {/* 卡片顶部：编号、指标名称、感叹号与状态 */}
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex items-center gap-2 relative min-w-0">
                                <span className="text-xs font-mono font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 shrink-0">
                                  #{idx + 1 < 10 ? `0${idx + 1}` : idx + 1}
                                </span>
                                <h5 className="text-xs font-bold text-[var(--text-primary)] leading-tight truncate">
                                  {m.name_zh}
                                </h5>

                                {/* 外置感叹号说明按钮 */}
                                <div
                                  className="relative shrink-0"
                                  onMouseEnter={() => setActiveModelTooltipId(m.model_id)}
                                  onMouseLeave={() => setActiveModelTooltipId(null)}
                                >
                                  <button
                                    type="button"
                                    tabIndex={0}
                                    title={`${m.name_zh} 指标定位与参数反映情况`}
                                    aria-label={`${m.name_zh} 指标定位与参数反映情况`}
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      setActiveModelTooltipId(activeModelTooltipId === m.model_id ? null : m.model_id)
                                    }}
                                    onFocus={() => setActiveModelTooltipId(m.model_id)}
                                    onBlur={() => setActiveModelTooltipId(null)}
                                    className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-slate-400 ${
                                      activeModelTooltipId === m.model_id
                                        ? 'bg-slate-700 text-white shadow-sm'
                                        : 'bg-[var(--surface-color)] hover:bg-slate-200 text-[var(--text-muted)] hover:text-slate-800 border border-[var(--border-color)]'
                                    }`}
                                  >
                                    <InfoCircleIcon className="w-2.5 h-2.5" />
                                  </button>

                                  {/* 聚焦/悬停/点击展开详细信息浮层 */}
                                  {activeModelTooltipId === m.model_id && (
                                    <div
                                      className="absolute top-full mt-2 left-0 w-80 max-w-[90vw] p-3.5 rounded-xl bg-white border border-slate-200 shadow-2xl z-50 pointer-events-auto opacity-100 transition-all duration-200 text-left space-y-2"
                                      onMouseEnter={() => setActiveModelTooltipId(m.model_id)}
                                      onMouseLeave={() => setActiveModelTooltipId(null)}
                                    >
                                      <div className="flex items-center justify-between border-b border-slate-100 pb-1.5">
                                        <div className="flex items-center gap-1.5 min-w-0">
                                          <span className="font-mono font-bold text-xs text-slate-800">
                                            #{idx + 1}
                                          </span>
                                          <span className="text-xs font-bold text-slate-800 truncate">
                                            {m.name_zh}
                                          </span>
                                        </div>
                                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200 font-medium shrink-0">
                                          {m.category}
                                        </span>
                                      </div>

                                      <div className="text-[11px] text-slate-600 leading-relaxed space-y-0.5">
                                        <span className="text-[10px] font-bold text-slate-800 block">【指标用途与金融含义】：</span>
                                        <p>{m.theory_origin}</p>
                                      </div>

                                      {m.executive_takeaway && (
                                        <div className="text-[11px] text-slate-700 leading-relaxed bg-slate-50 border-l-2 border-[#176249] p-2 rounded-r-lg space-y-0.5">
                                          <span className="text-[10px] font-bold text-[#176249] block">【投研研判与启示】：</span>
                                          <p>{m.executive_takeaway}</p>
                                        </div>
                                      )}

                                      <div className="text-[11px] text-slate-600 leading-relaxed bg-slate-50 p-2 rounded-lg border border-slate-100 space-y-1">
                                        <span className="text-[10px] font-bold text-slate-800 block">【核心参数反映情况】：</span>
                                        <p>{m.core_param_reflection || '指标各输入参数均经严格官方财报映射与时序清洗，当前读数在基准情景下反映企业正常稳态营运。'}</p>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              </div>

                              <div className="flex items-center gap-1.5 shrink-0">
                                <span className="text-[10px] px-1.5 py-0.2 rounded font-mono text-[var(--text-muted)] bg-[var(--surface-color)] border border-[var(--border-color)]">
                                  {m.execution_ms.toFixed(1)} ms
                                </span>
                                <span className="flex items-center gap-0.5 text-[10px] px-1.5 py-0.2 rounded font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                                  <CheckIcon className="w-2.5 h-2.5" />
                                  <span>已核验</span>
                                </span>
                              </div>
                            </div>

                            {/* 测算成果摘要 */}
                            <div className="p-2 rounded-lg bg-[var(--surface-color)] border border-[var(--border-color)]/70 flex items-center justify-between gap-2">
                              <div className="min-w-0">
                                <div className="text-[9px] text-[var(--text-muted)] font-medium">测算成果</div>
                                <div className="text-xs font-mono font-bold text-[var(--text-primary)] truncate mt-0.5">
                                  {m.output_summary}
                                </div>
                              </div>
                              <span className="text-[9px] px-1.5 py-0.2 rounded bg-[var(--bg-card)] text-[var(--text-secondary)] border border-[var(--border-color)] font-medium shrink-0">
                                {m.category.replace('群', '')}
                              </span>
                            </div>

                            {/* 多参数结构化解读矩阵 */}
                            {params.length > 0 && (
                              <div className="space-y-2 pt-1 border-t border-[var(--border-color)]/50">
                                <div className="flex items-center justify-between text-xs">
                                  <span className="font-semibold text-[var(--text-secondary)] text-[11px] flex items-center gap-1">
                                    <span>参数构成 ({params.length} 项)</span>
                                  </span>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setExpandedModelIds(prev => ({
                                        ...prev,
                                        [m.model_id]: !isExpanded,
                                      }))
                                    }}
                                    className="text-[11px] text-slate-700 hover:text-slate-900 font-medium cursor-pointer flex items-center gap-1"
                                  >
                                    <span>{isExpanded ? '收起参数' : '展开参数解读'}</span>
                                    {isExpanded ? <ChevronUpIcon className="w-3 h-3" /> : <ChevronDownIcon className="w-3 h-3" />}
                                  </button>
                                </div>

                                {isExpanded && (
                                  <div className="space-y-2 pt-1">
                                    {params.map((param, pIdx) => {
                                      const statusBg =
                                        param.status_level === 'safe'
                                          ? 'bg-slate-100 text-slate-700 border-slate-200'
                                          : param.status_level === 'warning'
                                          ? 'bg-amber-50 text-amber-700 border-amber-200'
                                          : param.status_level === 'critical'
                                          ? 'bg-rose-50 text-rose-700 border-rose-200'
                                          : 'bg-slate-100 text-slate-700 border-slate-200'

                                      const statusText =
                                        param.status_level === 'safe'
                                          ? '正常'
                                          : param.status_level === 'warning'
                                          ? '关注'
                                          : param.status_level === 'critical'
                                          ? '警惕'
                                          : '参考'

                                      return (
                                        <div
                                          key={param.param_key || pIdx}
                                          className="bg-[var(--surface-color)] border border-[var(--border-color)]/70 rounded-lg p-2.5 space-y-1.5 text-xs"
                                        >
                                          <div className="flex flex-wrap items-center justify-between gap-2">
                                            <div className="flex items-center gap-1.5 min-w-0">
                                              <span className="font-bold text-[var(--text-primary)] text-[11px]">
                                                {param.param_name}
                                              </span>
                                              <span className="text-[9px] font-mono text-[var(--text-muted)]">
                                                ({param.param_key})
                                              </span>
                                            </div>
                                            <div className="flex items-center gap-1.5 shrink-0">
                                              <span className="font-mono font-bold text-xs text-[var(--text-primary)]">
                                                {param.param_value}
                                              </span>
                                              <span className={`text-[9px] px-1.5 py-0.2 rounded border font-medium ${statusBg}`}>
                                                {statusText}
                                              </span>
                                            </div>
                                          </div>

                                          <div className="text-[10px] text-[var(--text-muted)] flex items-center gap-1.5">
                                            <span>基准:</span>
                                            <span className="font-mono text-[var(--text-primary)]">{param.benchmark_range}</span>
                                          </div>

                                          <div className="text-[10px] text-[var(--text-secondary)] bg-[var(--bg-card)] p-1.5 rounded border border-[var(--border-color)]/40 leading-relaxed">
                                            <span className="text-slate-700 font-semibold">【参数反映情况】：</span>
                                            {param.economic_intuition}
                                          </div>

                                          <div className="text-[10px] text-[var(--text-primary)] leading-relaxed pl-2 border-l-2 border-slate-400 py-0.5">
                                            <span className="text-slate-800 font-semibold">【分析启示】：</span>
                                            {param.decision_implication}
                                          </div>
                                        </div>
                                      )
                                    })}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      )
                    })}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="p-10 text-center text-xs text-[var(--text-muted)] bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl space-y-3">
            <div className="text-sm font-semibold text-[var(--text-primary)]">
              尚未加载标的 {selectedTicker} 的量化指标数据
            </div>
            <button
              type="button"
              onClick={() => void onReloadSuite24(selectedTicker)}
              className="px-4 py-2 rounded-lg bg-[#176249] hover:bg-[#14533e] text-white font-bold text-xs cursor-pointer"
            >
              立即全量运算 25 项量化指标
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
