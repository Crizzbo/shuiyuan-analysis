import { useState, useEffect } from 'react'
import type { FormEvent } from 'react'
import type { AutomatedValuationData, ValuationCompanyItem } from '../types/api'
import { api } from '../services/api'
import { TargetIcon } from './common'

interface AutomatedValuationPanelProps {
  onSelectTicker?: (ticker: string) => void
}

export function AutomatedValuationPanel({ onSelectTicker }: AutomatedValuationPanelProps) {
  const [companies, setCompanies] = useState<ValuationCompanyItem[]>([])
  const [selectedTicker, setSelectedTicker] = useState<string>('NVDA')
  const [searchTicker, setSearchTicker] = useState('')
  const [valuationData, setValuationData] = useState<AutomatedValuationData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 敏感性情景微调状态
  const [showSensitivity, setShowSensitivity] = useState(false)
  const [customDiscountRate, setCustomDiscountRate] = useState<number>(9.5)
  const [customTerminalGrowth, setCustomTerminalGrowth] = useState<number>(2.5)
  const [customGrowthRates, setCustomGrowthRates] = useState<string>('18, 14, 10')
  const [customBeta, setCustomBeta] = useState<number>(1.45)
  const [tuning, setTuning] = useState(false)
  const [activeScenarioTooltip, setActiveScenarioTooltip] = useState<'floor' | 'base' | 'opt' | null>(null)

  // 1. 加载可用企业池
  useEffect(() => {
    async function loadCompanies() {
      try {
        const res = await api.getFinanceCompanies()
        if (res.ok && res.data.companies) {
          setCompanies(res.data.companies)
        }
      } catch (err) {
        console.error('Failed to load valuation companies:', err)
      }
    }
    void loadCompanies()
  }, [])

  // 2. 加载选定标的自动估值
  const loadValuation = async (ticker: string, adjustments?: Record<string, any>) => {
    setLoading(true)
    setError(null)
    try {
      const res = adjustments
        ? await api.calculateAutoValuation(ticker, adjustments)
        : await api.getAutoValuation(ticker)
      if (res.ok) {
        setValuationData(res.data)
        // 同步敏感性微调默认值
        const baseCorridor = res.data.valuation_corridor.base_fair_value
        setCustomDiscountRate(baseCorridor.discount_rate_pct)
        setCustomTerminalGrowth(baseCorridor.terminal_growth_pct)
        setCustomGrowthRates(baseCorridor.growth_rates_pct.join(', '))
        setCustomBeta(res.data.capital_cost_wacc.beta)
      } else {
        setError(res.error?.message || '获取标的自动金融计算失败')
      }
    } catch (err: any) {
      setError(err.message || '网络连接异常')
    } finally {
      setLoading(false)
      setTuning(false)
    }
  }

  useEffect(() => {
    if (selectedTicker) {
      void loadValuation(selectedTicker)
    }
  }, [selectedTicker])

  const handleApplySensitivity = async (e: FormEvent) => {
    e.preventDefault()
    setTuning(true)
    const parsedGrowths = customGrowthRates
      .split(/[,，\s]+/)
      .map(x => Number(x.trim()) / 100)
      .filter(x => Number.isFinite(x))

    await loadValuation(selectedTicker, {
      discount_rate: customDiscountRate / 100,
      terminal_growth: customTerminalGrowth / 100,
      growth_rates: parsedGrowths.length ? parsedGrowths : undefined,
      beta: customBeta,
    })
  }

  const handleResetToBaseline = () => {
    void loadValuation(selectedTicker)
  }

  const facts = valuationData?.underlying_facts
  const corridor = valuationData?.valuation_corridor
  const wacc = valuationData?.capital_cost_wacc
  const ratios = valuationData?.profitability_ratios
  const curPrice = valuationData?.current_price ?? 0
  const sym = valuationData?.currency_symbol ?? '$'
  const mos = corridor?.margin_of_safety_pct ?? 0

  return (
    <div className="space-y-6">
      {/* 顶部标题与标的选择器 */}
      <section className="panel">
        <div className="section-head">
          <div>
            <h2>多阶段 DCF 估值模型与内在价值区间</h2>
            <p className="muted">
              基于官方财报数据、基准行情与美债收益率 · 多阶段 DCF 内在价值评估 · WACC 资本成本 · 杜邦比率
            </p>
          </div>
          <span className="badge">官方财报数据</span>
        </div>

        {/* 标的快速切换按钮池 */}
        <div className="flex flex-wrap items-center gap-2 mt-4">
          {companies.map(c => (
            <button
              key={c.ticker}
              type="button"
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 border ${
                selectedTicker === c.ticker
                  ? 'bg-[#176249] text-white border-[#176249] shadow-sm'
                  : 'bg-[var(--bg-card)] text-[var(--text-secondary)] border-[var(--border-color)] hover:border-slate-300'
              }`}
              onClick={() => {
                setSelectedTicker(c.ticker)
                if (onSelectTicker) onSelectTicker(c.ticker)
              }}
            >
              <span>{c.ticker}</span>
              <span className="opacity-80 font-normal">
                {c.company_name.split(' ')[0]}
              </span>
              {c.price && <span className="opacity-75">{sym}{c.price}</span>}
            </button>
          ))}
        </div>

        {/* 自由输入查询框 */}
        <form
          className="flex items-center gap-2 mt-3"
          onSubmit={e => {
            e.preventDefault()
            const t = searchTicker.trim().toUpperCase()
            if (t) {
              setSelectedTicker(t)
              if (onSelectTicker) onSelectTicker(t)
            }
          }}
        >
          <input
            placeholder="输入美股/日股代码 (如 NVDA, AAPL, 8035)"
            value={searchTicker}
            onChange={e => setSearchTicker(e.target.value)}
            className="w-64 rounded-md border border-[var(--border-color)] px-3 py-1.5 text-sm"
          />
          <button type="submit" className="primary">执行估值计算</button>
        </form>
      </section>

      {error && <div className="error" role="alert">{error}</div>}

      {loading && !valuationData && (
        <div className="panel p-8 text-center text-muted">
          正在从官方 SEC 10-K 原档与实时行情中提取财务事实并自动测算估值...
        </div>
      )}

      {valuationData && (
        <>
          {/* 1. 自动提取的官方财报事实卡片 */}
          <section className="panel">
            <div className="section-head">
              <div>
                <h2>官方财报数据与基准行情</h2>
                <p className="muted">
                  官方披露原档：{facts?.source_filing} · 报告期截止：{facts?.period_end} · 市场基准时点：{valuationData.quote_timestamp}
                </p>
              </div>
              <span className="badge">
                财务报表勾稽平衡
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
              <div className="p-3 bg-[var(--bg-subtle)] rounded-lg border border-[var(--border-color)]">
                <div className="text-xs text-muted">企业自由现金流 (FCF)</div>
                <div className="text-base font-bold mt-1 text-[var(--text-primary)]">
                  {facts?.free_cash_flow_formatted}
                </div>
                <div className="text-xs text-muted mt-0.5">三表内生经营净流入</div>
              </div>

              <div className="p-3 bg-[var(--bg-subtle)] rounded-lg border border-[var(--border-color)]">
                <div className="text-xs text-muted">稀释后总股数 (Shares)</div>
                <div className="text-base font-bold mt-1 text-[var(--text-primary)]">
                  {facts?.shares_formatted}
                </div>
                <div className="text-xs text-muted mt-0.5">官方申报摊薄口径</div>
              </div>

              <div className="p-3 bg-[var(--bg-subtle)] rounded-lg border border-[var(--border-color)]">
                <div className="text-xs text-muted">现金储备 vs 有息负债</div>
                <div className="text-base font-bold mt-1 text-[var(--text-primary)]">
                  {facts?.cash_formatted} / {facts?.debt_formatted}
                </div>
                <div className="text-xs text-[#176249] mt-0.5 font-medium">
                  {facts?.net_cash_status}
                </div>
              </div>

              <div className="p-3 bg-[var(--bg-subtle)] rounded-lg border border-[var(--border-color)]">
                <div className="text-xs text-muted">最新基准现价 (Market Price)</div>
                <div className="text-base font-bold mt-1 text-[var(--text-primary)]">
                  {sym}{curPrice.toFixed(2)}
                </div>
                <div className="text-xs text-muted mt-0.5">
                  无风险利率 {facts?.risk_free_rate_label}
                </div>
              </div>
            </div>
          </section>

          {/* 2. 多阶段 DCF 内在价值走廊三态卡片 */}
          <section className="panel">
            <div className="section-head">
              <div>
                <h2>多阶段 DCF 内在价值走廊与估值区间</h2>
                <p className="muted">
                  基于企业内生真实自由现金流、WACC 资本成本折现率及多情景增长推演
                </p>
              </div>
              <span className={`px-2.5 py-1 rounded-full font-bold text-xs font-mono border ${
                mos >= 0
                  ? 'text-blue-600 bg-blue-50 border-blue-200'
                  : 'text-rose-600 bg-rose-50 border-rose-200'
              }`}>
                {mos >= 0 ? `安全边际 +${mos.toFixed(1)}%` : `估值溢价 ${Math.abs(mos).toFixed(1)}%`}
              </span>
            </div>

            {/* 顶层通俗商业研判横幅 */}
            <div className="p-4 rounded-xl my-4 border bg-[var(--bg-subtle)] flex items-start gap-3">
              <TargetIcon className="w-5 h-5 text-slate-700 mt-0.5 shrink-0" />
              <div>
                <div className="font-bold text-sm text-[var(--text-primary)]">
                  估值研判与投资逻辑
                </div>
                <div className="text-xs mt-1 text-[var(--text-secondary)] leading-relaxed">
                  {corridor?.valuation_verdict}
                </div>
              </div>
            </div>

            {/* 三态情景卡片 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* 保守底价 */}
              <div className="p-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] flex flex-col justify-between relative group">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-800">保守底价</span>
                    <div className="flex items-center gap-1.5">
                      <span className="badge warning">严苛防御</span>
                      
                      {/* 感叹号浮层 */}
                      <div
                        className="relative"
                        onMouseEnter={() => setActiveScenarioTooltip('floor')}
                        onMouseLeave={() => setActiveScenarioTooltip(null)}
                      >
                        <button
                          type="button"
                          tabIndex={0}
                          title="保守底价情景推演说明"
                          aria-label="保守底价情景推演说明"
                          onClick={(e) => {
                            e.stopPropagation()
                            setActiveScenarioTooltip(activeScenarioTooltip === 'floor' ? null : 'floor')
                          }}
                          onFocus={() => setActiveScenarioTooltip('floor')}
                          onBlur={() => setActiveScenarioTooltip(null)}
                          className={`w-3.5 h-3.5 rounded-full flex items-center justify-center text-[9px] font-bold font-mono transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-slate-400 ${
                            activeScenarioTooltip === 'floor'
                              ? 'bg-slate-800 text-white border-slate-800'
                              : 'bg-[var(--surface-color)] hover:bg-slate-100 text-[var(--text-muted)] hover:text-slate-800 border border-[var(--border-color)]'
                          }`}
                        >
                          !
                        </button>

                        {activeScenarioTooltip === 'floor' && (
                          <div
                            className="absolute top-full mt-2 left-0 w-72 p-3.5 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto opacity-100 transition-all duration-200 text-left"
                            onMouseEnter={() => setActiveScenarioTooltip('floor')}
                            onMouseLeave={() => setActiveScenarioTooltip(null)}
                          >
                            <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                              <span className="font-bold text-xs text-slate-800">
                                保守底价情景推演
                              </span>
                              <span className="badge warning">严苛防御</span>
                            </div>
                            <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                              {corridor?.conservative_floor.description}
                            </p>
                            <div className="mt-2.5 pt-1.5 border-t border-[var(--border-color)]/40 text-[10px] text-[var(--text-muted)] font-mono space-y-0.5">
                              <div>折现率: {corridor?.conservative_floor.discount_rate_pct}% | 永续: {corridor?.conservative_floor.terminal_growth_pct}%</div>
                              <div>前3年预测增长: {corridor?.conservative_floor.growth_rates_pct.join('%, ')}%</div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="text-2xl font-black mt-2 text-[var(--text-primary)]">
                    {sym}{corridor?.conservative_floor.value_per_share.toFixed(2)}
                  </div>
                </div>
                <div className="mt-4 pt-3 border-t border-[var(--border-color)] text-xs text-muted space-y-1">
                  <div>折现率：{corridor?.conservative_floor.discount_rate_pct}%</div>
                  <div>永续增长率：{corridor?.conservative_floor.terminal_growth_pct}%</div>
                  <div>前3年预测增长：{corridor?.conservative_floor.growth_rates_pct.join('%, ')}%</div>
                </div>
              </div>

              {/* 中性公允价 (核心高亮) */}
              <div className="p-4 rounded-xl border-2 border-[#176249] bg-[var(--surface-color)] shadow-sm flex flex-col justify-between relative group">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[#176249]">中性公允价</span>
                    <div className="flex items-center gap-1.5">
                      <span className="badge success">基准公允</span>

                      {/* 感叹号浮层 */}
                      <div
                        className="relative"
                        onMouseEnter={() => setActiveScenarioTooltip('base')}
                        onMouseLeave={() => setActiveScenarioTooltip(null)}
                      >
                        <button
                          type="button"
                          tabIndex={0}
                          title="中性公允价情景推演说明"
                          aria-label="中性公允价情景推演说明"
                          onClick={(e) => {
                            e.stopPropagation()
                            setActiveScenarioTooltip(activeScenarioTooltip === 'base' ? null : 'base')
                          }}
                          onFocus={() => setActiveScenarioTooltip('base')}
                          onBlur={() => setActiveScenarioTooltip(null)}
                          className={`w-3.5 h-3.5 rounded-full flex items-center justify-center text-[9px] font-bold font-mono transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#176249] ${
                            activeScenarioTooltip === 'base'
                              ? 'bg-[#176249] text-white border-[#176249]'
                              : 'bg-[var(--surface-color)] hover:bg-[#176249]/20 text-[var(--text-muted)] hover:text-[#176249] border border-[var(--border-color)]'
                          }`}
                        >
                          !
                        </button>

                        {activeScenarioTooltip === 'base' && (
                          <div
                            className="absolute top-full mt-2 left-1/2 -translate-x-1/2 w-72 p-3.5 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto opacity-100 transition-all duration-200 text-left"
                            onMouseEnter={() => setActiveScenarioTooltip('base')}
                            onMouseLeave={() => setActiveScenarioTooltip(null)}
                          >
                            <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                              <span className="font-bold text-xs text-[#176249]">
                                中性公允价推演 (估值中枢)
                              </span>
                              <span className="badge success">基准公允</span>
                            </div>
                            <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                              {corridor?.base_fair_value.description}
                            </p>
                            <div className="mt-2.5 pt-1.5 border-t border-[var(--border-color)]/40 text-[10px] text-[var(--text-muted)] font-mono space-y-0.5">
                              <div>WACC 折现率: {corridor?.base_fair_value.discount_rate_pct}% | 永续: {corridor?.base_fair_value.terminal_growth_pct}%</div>
                              <div>前3年预测增长: {corridor?.base_fair_value.growth_rates_pct.join('%, ')}%</div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="text-3xl font-black mt-2 text-[var(--text-primary)]">
                    {sym}{corridor?.base_fair_value.value_per_share.toFixed(2)}
                  </div>
                </div>
                <div className="mt-4 pt-3 border-t border-[var(--border-color)] text-xs text-[var(--text-secondary)] space-y-1">
                  <div>WACC 折现率：{corridor?.base_fair_value.discount_rate_pct}%</div>
                  <div>永续增长率：{corridor?.base_fair_value.terminal_growth_pct}%</div>
                  <div>前3年预测增长：{corridor?.base_fair_value.growth_rates_pct.join('%, ')}%</div>
                  {corridor?.base_fair_value.forecast && (
                    <details className="mt-2 text-xs">
                      <summary className="cursor-pointer text-slate-700 hover:text-slate-900 font-medium">查看 3 年期折现预测明细</summary>
                      <ul className="mt-1 pl-2 space-y-0.5 text-muted">
                        {corridor.base_fair_value.forecast.map(row => (
                          <li key={row.year}>第 {row.year} 年 FCF: {sym}{(row.cash_flow / 1e9).toFixed(2)}B (现值: {sym}{(row.present_value / 1e9).toFixed(2)}B)</li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              </div>

              {/* 乐观靶心价 */}
              <div className="p-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] flex flex-col justify-between relative group">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-rose-500">乐观靶心价</span>
                    <div className="flex items-center gap-1.5">
                      <span className="badge info">景气爆发</span>

                      {/* 感叹号浮层 */}
                      <div
                        className="relative"
                        onMouseEnter={() => setActiveScenarioTooltip('opt')}
                        onMouseLeave={() => setActiveScenarioTooltip(null)}
                      >
                        <button
                          type="button"
                          tabIndex={0}
                          title="乐观靶心价情景推演说明"
                          aria-label="乐观靶心价情景推演说明"
                          onClick={(e) => {
                            e.stopPropagation()
                            setActiveScenarioTooltip(activeScenarioTooltip === 'opt' ? null : 'opt')
                          }}
                          onFocus={() => setActiveScenarioTooltip('opt')}
                          onBlur={() => setActiveScenarioTooltip(null)}
                          className={`w-3.5 h-3.5 rounded-full flex items-center justify-center text-[9px] font-bold font-mono transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-rose-500 ${
                            activeScenarioTooltip === 'opt'
                              ? 'bg-rose-500 text-white border-rose-500'
                              : 'bg-[var(--surface-color)] hover:bg-rose-50 text-[var(--text-muted)] hover:text-rose-500 border border-[var(--border-color)]'
                          }`}
                        >
                          !
                        </button>

                        {activeScenarioTooltip === 'opt' && (
                          <div
                            className="absolute top-full mt-2 right-0 w-72 p-3.5 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto opacity-100 transition-all duration-200 text-left"
                            onMouseEnter={() => setActiveScenarioTooltip('opt')}
                            onMouseLeave={() => setActiveScenarioTooltip(null)}
                          >
                            <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                              <span className="font-bold text-xs text-rose-500">
                                乐观靶心价推演
                              </span>
                              <span className="badge info">景气爆发</span>
                            </div>
                            <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                              {corridor?.optimistic_target.description}
                            </p>
                            <div className="mt-2.5 pt-1.5 border-t border-[var(--border-color)]/40 text-[10px] text-[var(--text-muted)] font-mono space-y-0.5">
                              <div>折现率: {corridor?.optimistic_target.discount_rate_pct}% | 永续: {corridor?.optimistic_target.terminal_growth_pct}%</div>
                              <div>前3年预测增长: {corridor?.optimistic_target.growth_rates_pct.join('%, ')}%</div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="text-2xl font-black mt-2 text-rose-500">
                    {sym}{corridor?.optimistic_target.value_per_share.toFixed(2)}
                  </div>
                </div>
                <div className="mt-4 pt-3 border-t border-[var(--border-color)] text-xs text-muted space-y-1">
                  <div>折现率：{corridor?.optimistic_target.discount_rate_pct}%</div>
                  <div>永续增长率：{corridor?.optimistic_target.terminal_growth_pct}%</div>
                  <div>前3年预测增长：{corridor?.optimistic_target.growth_rates_pct.join('%, ')}%</div>
                </div>
              </div>
            </div>
          </section>

          {/* 3. 资本成本 WACC 与杜邦盈利质量 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <section className="panel">
              <div className="section-head">
                <h2>加权平均资本成本 (WACC)</h2>
                <span className="badge info">CAPM / 市场权重</span>
              </div>
              <div className="rows mt-3">
                <div className="row">
                  <div><strong>加权平均资本成本 (WACC)</strong><p>企业投资回报率的最低门槛折现率</p></div>
                  <span className="text-base font-bold text-[var(--text-primary)]">{wacc?.wacc_pct}%</span>
                </div>
                <div className="row">
                  <div><strong>股权资本成本 (Cost of Equity)</strong><p>基于无风险利率 4.35% 与 Beta {wacc?.beta}</p></div>
                  <span className="font-semibold">{wacc?.cost_of_equity_pct}%</span>
                </div>
                <div className="row">
                  <div><strong>税后债务成本 (After-Tax Debt Cost)</strong><p>税前成本 5.0% · 所得税率 21%</p></div>
                  <span className="font-semibold">{wacc?.after_tax_cost_of_debt_pct}%</span>
                </div>
                <div className="row">
                  <div><strong>资本结构权重 (Equity / Debt)</strong><p>基于真实股权市值与有息负债比重</p></div>
                  <span className="font-semibold">{wacc?.equity_weight_pct}% / {wacc?.debt_weight_pct}%</span>
                </div>
              </div>
            </section>

            <section className="panel">
              <div className="section-head">
                <h2>杜邦分析与盈利质量透视</h2>
                <span className="badge">报表勾稽平衡</span>
              </div>
              <div className="rows mt-3">
                <div className="row">
                  <div><strong>净资产收益率 (ROE)</strong><p>普通股股东真实内生资本回报率</p></div>
                  <span className="text-base font-bold text-rose-500">{ratios?.roe_pct != null ? `${ratios.roe_pct}%` : '—'}</span>
                </div>
                <div className="row">
                  <div><strong>总资产收益率 (ROA)</strong><p>企业全量资产运营效率</p></div>
                  <span className="font-semibold">{ratios?.roa_pct != null ? `${ratios.roa_pct}%` : '—'}</span>
                </div>
                <div className="row">
                  <div><strong>营业利润率 (Operating Margin)</strong><p>扣除研发与销售后的核心主营溢价能力</p></div>
                  <span className="font-semibold">{ratios?.operating_margin_pct != null ? `${ratios.operating_margin_pct}%` : '—'}</span>
                </div>
                <div className="row">
                  <div><strong>自由现金流转化率 (FCF / NI)</strong><p>自由现金流占净利润比重（盈利含金量）</p></div>
                  <span className="font-semibold">{ratios?.fcf_conversion_pct != null ? `${ratios.fcf_conversion_pct}%` : '—'}</span>
                </div>
              </div>
            </section>
          </div>

          {/* 4. 情景敏感性微调面板 (可展开折叠) */}
          <section className="panel">
            <div className="flex items-center justify-between">
              <div>
                <h2>情景敏感性微调与压力测试</h2>
                <p className="muted">
                  支持在官方财报自动代入的基础上，微调折现率与逐年预期增长率进行敏感性推演
                </p>
              </div>
              <button
                type="button"
                className="text-button text-xs font-semibold"
                onClick={() => setShowSensitivity(!showSensitivity)}
              >
                {showSensitivity ? '收起微调面板 ▲' : '展开敏感性微调 ▼'}
              </button>
            </div>

            {showSensitivity && (
              <form onSubmit={handleApplySensitivity} className="mt-4 pt-4 border-t border-[var(--border-color)] space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <label className="field">
                    <span>基准折现率 WACC (%)</span>
                    <input
                      type="number"
                      step="0.1"
                      min="4"
                      max="20"
                      value={customDiscountRate}
                      onChange={e => setCustomDiscountRate(Number(e.target.value))}
                      className="rounded-md border border-[var(--border-color)] px-3 py-1.5 text-sm"
                    />
                  </label>

                  <label className="field">
                    <span>永续增长率 (%)</span>
                    <input
                      type="number"
                      step="0.1"
                      min="0.5"
                      max="5"
                      value={customTerminalGrowth}
                      onChange={e => setCustomTerminalGrowth(Number(e.target.value))}
                      className="rounded-md border border-[var(--border-color)] px-3 py-1.5 text-sm"
                    />
                  </label>

                  <label className="field">
                    <span>逐年增长率（第1, 2, 3年，%）</span>
                    <input
                      type="text"
                      value={customGrowthRates}
                      placeholder="例如: 18, 14, 10"
                      onChange={e => setCustomGrowthRates(e.target.value)}
                      className="rounded-md border border-[var(--border-color)] px-3 py-1.5 text-sm"
                    />
                  </label>

                  <label className="field">
                    <span>标的 Beta 系数</span>
                    <input
                      type="number"
                      step="0.05"
                      min="0.5"
                      max="3"
                      value={customBeta}
                      onChange={e => setCustomBeta(Number(e.target.value))}
                      className="rounded-md border border-[var(--border-color)] px-3 py-1.5 text-sm"
                    />
                  </label>
                </div>

                <div className="flex items-center gap-3">
                  <button type="submit" disabled={tuning} className="primary">
                    {tuning ? '重新测算中…' : '应用微调并重新测算内在价值走廊'}
                  </button>
                  <button type="button" onClick={handleResetToBaseline} className="text-button text-xs">
                    恢复官方原始基准数据
                  </button>
                </div>
              </form>
            )}
          </section>

          {/* 5. 校验摘要与算法溯源 */}
          <div className="text-xs text-muted px-2 py-1 flex items-center justify-between">
            <span>
              计算算法版本：{valuationData.calculation_provenance.method_version} · 纯净金融引擎：{valuationData.calculation_provenance.implementation_path}
            </span>
            <span>
              SHA-256 输入防篡改摘要：{valuationData.calculation_provenance.input_sha256?.slice(0, 16)}...
            </span>
          </div>
        </>
      )}
    </div>
  )
}
