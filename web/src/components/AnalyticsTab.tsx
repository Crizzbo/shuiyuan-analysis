import { useState, useEffect } from 'react'
import type { FormEvent } from 'react'
import type {
  CandidatesData,
  CompanyAnalysisData,
  AutomatedValuationData,
  ComprehensiveFinanceSuiteData,
} from '../types/api'
import { api } from '../services/api'
import { formatDeviceTime } from '../utils/format'
import { showToast } from './Toast'
import { CandidateListSidebar } from './analytics/CandidateListSidebar'
import { CompanyHeaderCard } from './analytics/CompanyHeaderCard'
import { DcfValuationCorridorCard } from './analytics/DcfValuationCorridorCard'
import { QuantMetricsSuiteCard } from './analytics/QuantMetricsSuiteCard'
import { MoatAndSupplyChainCard } from './analytics/MoatAndSupplyChainCard'
import { QuantitativeProbesCard } from './analytics/QuantitativeProbesCard'
import { EventImpactStreamCard } from './analytics/EventImpactStreamCard'

interface AnalyticsTabProps {
  refreshKey?: number
  initialTicker?: string | null
}

export function AnalyticsTab({ refreshKey, initialTicker }: AnalyticsTabProps) {
  // 左侧标的资产池状态
  const [candidatesData, setCandidatesData] = useState<CandidatesData | null>(null)
  const [marketFilter, setMarketFilter] = useState<'ALL' | 'US' | 'JP'>('ALL')
  const [selectedTicker, setSelectedTicker] = useState<string>('NVDA')
  const [searchQuery, setSearchQuery] = useState('')
  const [activeQuery, setActiveQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [loadingCandidates, setLoadingCandidates] = useState(true)

  // 右侧个股全息诊断与估值状态
  const [analysis, setAnalysis] = useState<CompanyAnalysisData | null>(null)
  const [loadingAnalysis, setLoadingAnalysis] = useState(false)
  const [analysisError, setAnalysisError] = useState<string | null>(null)

  // 标的量化金融模型矩阵
  const [suite24Data, setSuite24Data] = useState<ComprehensiveFinanceSuiteData | null>(null)
  const [loadingSuite24, setLoadingSuite24] = useState(false)

  // 敏感性情景微调状态
  const [showSensitivity, setShowSensitivity] = useState(false)
  const [customDiscountRate, setCustomDiscountRate] = useState<number>(9.5)
  const [customTerminalGrowth, setCustomTerminalGrowth] = useState<number>(2.5)
  const [customGrowthRates, setCustomGrowthRates] = useState<string>('18, 14, 10')
  const [customBeta, setCustomBeta] = useState<number>(1.45)
  const [tuning, setTuning] = useState(false)
  const [overrideValuation, setOverrideValuation] = useState<AutomatedValuationData | null>(null)
  const [recollectingTicker, setRecollectingTicker] = useState(false)

  const scrollToSection = (sectionId: string) => {
    const el = document.getElementById(sectionId)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  // 1. 加载左侧标的池（支持分页与搜索）
  const loadCandidates = async (page = 1, market = marketFilter, query = activeQuery) => {
    try {
      setLoadingCandidates(true)
      const res = await api.getAnalyticsCandidates(market, 20, page, query)
      if (res.ok) {
        setCandidatesData(res.data)
        setCurrentPage(res.data.page || page)
        if (res.data.candidates.length > 0 && !selectedTicker) {
          setSelectedTicker(res.data.candidates[0].ticker)
        }
      }
    } catch (err) {
      console.error('Failed to load candidates:', err)
    } finally {
      setLoadingCandidates(false)
    }
  }

  // 2. 加载右侧个股深度全息研报
  const loadAnalysis = async (ticker: string) => {
    try {
      setLoadingAnalysis(true)
      setAnalysisError(null)
      setOverrideValuation(null)
      setShowSensitivity(false)
      const res = await api.getCompanyAnalysis(ticker)
      if (res.ok) {
        setAnalysis(res.data)
        const autoVal = res.data.automated_valuation
        if (autoVal) {
          const baseFair = autoVal.valuation_corridor.base_fair_value
          setCustomDiscountRate(baseFair.discount_rate_pct)
          setCustomTerminalGrowth(baseFair.terminal_growth_pct)
          setCustomGrowthRates(baseFair.growth_rates_pct.join(', '))
          setCustomBeta(autoVal.capital_cost_wacc.beta)
        }
      } else {
        setAnalysisError(res.error?.message || '获取标的深度研报失败')
      }
    } catch (err: any) {
      setAnalysisError(err.message || '网络连接异常')
    } finally {
      setLoadingAnalysis(false)
    }
  }

  // 3. 在任务调度中为指定股票发起全维度数据补采与平账核验
  const handleRecollectStock = async (tickerToRun: string) => {
    const symbol = tickerToRun.trim().toUpperCase()
    if (!symbol || recollectingTicker) return
    setRecollectingTicker(true)
    showToast({
      type: 'info',
      title: `在任务调度中更新标的 [${symbol}] 数据`,
      message: '正在拉取最新报价、核验官方三表底稿、重算均线并刷新 DCF 估值走廊...',
    })
    try {
      const res = await api.runTerminalTask('STOCK_DOSSIER_COLLECT', symbol)
      if (res.ok) {
        showToast({
          type: 'success',
          title: `[${symbol}] 全量数据更新完成`,
          message: '官方三表已平账，内在价值走廊已根据最新财报数据重算完成。',
        })
        setSelectedTicker(symbol)
        await loadAnalysis(symbol)
        await loadCandidates(currentPage, marketFilter, activeQuery)
      } else {
        showToast({
          type: 'error',
          title: '更新数据失败',
          message: res.error?.message || '调度器未能完成该标的数据采集',
        })
      }
    } catch (err: any) {
      showToast({
        type: 'error',
        title: '请求异常',
        message: err.message || '网络连接或后端异常',
      })
    } finally {
      setRecollectingTicker(false)
    }
  }

  // 4. 加载 25 大专业量化金融模型全息计算套件
  const loadSuite24 = async (ticker: string) => {
    try {
      setLoadingSuite24(true)
      const res = await api.getFinanceModels(ticker)
      if (res.ok) {
        setSuite24Data(res.data)
      }
    } catch (err) {
      console.error('Failed to load models suite:', err)
    } finally {
      setLoadingSuite24(false)
    }
  }

  // 市场过滤器切换
  const handleMarketChange = (m: 'ALL' | 'US' | 'JP') => {
    setMarketFilter(m)
    setCurrentPage(1)
    void loadCandidates(1, m, activeQuery)
  }

  // 搜索提交
  const handleSearchSubmit = (e: FormEvent) => {
    e.preventDefault()
    const trimmed = searchQuery.trim()
    setActiveQuery(trimmed)
    setCurrentPage(1)
    void loadCandidates(1, marketFilter, trimmed)
  }

  // 清除搜索
  const handleClearSearch = () => {
    setSearchQuery('')
    setActiveQuery('')
    setCurrentPage(1)
    void loadCandidates(1, marketFilter, '')
  }

  // 分页切换
  const handlePageChange = (page: number) => {
    setCurrentPage(page)
    void loadCandidates(page, marketFilter, activeQuery)
  }

  // 应用敏感性微调
  const handleApplySensitivity = async (e: FormEvent) => {
    e.preventDefault()
    if (!selectedTicker) return
    setTuning(true)
    try {
      const parsedGrowths = customGrowthRates
        .split(/[,，\s]+/)
        .map(x => Number(x.trim()) / 100)
        .filter(x => Number.isFinite(x))

      const res = await api.calculateAutoValuation(selectedTicker, {
        discount_rate: customDiscountRate / 100,
        terminal_growth: customTerminalGrowth / 100,
        growth_rates: parsedGrowths.length ? parsedGrowths : undefined,
        beta: customBeta,
      })
      if (res.ok) {
        setOverrideValuation(res.data)
      }
    } catch (err) {
      console.error('Failed to tune sensitivity:', err)
    } finally {
      setTuning(false)
    }
  }

  // 恢复官方基准
  const handleResetSensitivity = () => {
    setOverrideValuation(null)
    const autoVal = analysis?.automated_valuation
    if (autoVal) {
      const baseFair = autoVal.valuation_corridor.base_fair_value
      setCustomDiscountRate(baseFair.discount_rate_pct)
      setCustomTerminalGrowth(baseFair.terminal_growth_pct)
      setCustomGrowthRates(baseFair.growth_rates_pct.join(', '))
      setCustomBeta(autoVal.capital_cost_wacc.beta)
    }
  }

  useEffect(() => {
    if (initialTicker && initialTicker !== selectedTicker) {
      setSelectedTicker(initialTicker)
    }
  }, [initialTicker])

  useEffect(() => {
    void loadCandidates(currentPage, marketFilter, activeQuery)
  }, [refreshKey])

  useEffect(() => {
    if (selectedTicker) {
      void loadAnalysis(selectedTicker)
      void loadSuite24(selectedTicker)
    }
  }, [selectedTicker, refreshKey])

  // 当前有效估值模型与指标派生
  const activeValuation = overrideValuation || analysis?.automated_valuation
  const curPrice = activeValuation?.current_price ?? analysis?.quote.price ?? 0
  const sym = activeValuation?.currency_symbol ?? (analysis?.market === 'JP' ? '¥' : '$')
  const wacc = activeValuation?.capital_cost_wacc
  const ratios = activeValuation?.profitability_ratios
  const probes = analysis?.quantitative_probes
  const indProf = analysis?.industry_profile
  const quote = analysis?.quote

  return (
    <div className="p-4 md:p-6 max-w-[1600px] mx-auto">
      {/* 顶部精简买方工作台状态栏 */}
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl px-4 py-2.5 mb-4 shadow-sm flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#176249] animate-pulse" />
          <h1 className="font-bold text-[var(--text-primary)] text-xs flex items-center gap-1.5">
            <span>标的深度投研与估值模型</span>
            <span className="text-[10px] px-2 py-0.2 rounded-full bg-slate-100 text-slate-700 border border-slate-200 font-mono font-bold">
              全量 14,892 标的
            </span>
          </h1>
          <span className="text-[11px] text-[var(--text-muted)] hidden lg:inline">
            | 官方财报核验 · 多阶段现金流折现 (DCF) · 核心财务与风险指标
          </span>
        </div>
        <div className="text-[10px] text-[var(--text-muted)] font-mono flex items-center gap-2.5">
          <span className="text-[#176249] font-semibold flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#176249]" />
            <span>财务报表平衡通过</span>
          </span>
          <span>·</span>
          <span>多情景估值区间</span>
          <span>·</span>
          <span>前收盘价基准</span>
        </div>
      </div>

      {/* 左右分栏核心工作区 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* 左侧：标的资产全量索引与检索栏 */}
        <CandidateListSidebar
          candidatesData={candidatesData}
          marketFilter={marketFilter}
          selectedTicker={selectedTicker}
          searchQuery={searchQuery}
          currentPage={currentPage}
          loadingCandidates={loadingCandidates}
          recollectingTicker={recollectingTicker}
          onMarketChange={handleMarketChange}
          onSearchChange={setSearchQuery}
          onSearchSubmit={handleSearchSubmit}
          onClearSearch={handleClearSearch}
          onSelectTicker={setSelectedTicker}
          onPageChange={handlePageChange}
          onRecollectStock={handleRecollectStock}
        />

        {/* 右侧：个股深度研究与多模型估值主工作台 */}
        <div className="lg:col-span-8 xl:col-span-9 space-y-5">
          {/* 顶层标的工作台导航与快捷锚点栏 */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-[var(--surface-color)] border border-[var(--border-color)] p-2.5 rounded-xl shadow-sm sticky top-0 z-30 backdrop-blur-md bg-opacity-95">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[11px] text-[var(--text-muted)] font-medium mr-1">标的工作台导航:</span>
              <button
                type="button"
                onClick={() => scrollToSection('sec-header')}
                className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[var(--bg-card)] hover:bg-slate-100 text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border-color)] cursor-pointer transition-all flex items-center"
              >
                <span>标的概览</span>
              </button>
              <button
                type="button"
                onClick={() => scrollToSection('sec-dcf')}
                className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[var(--bg-card)] hover:bg-slate-100 text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border-color)] cursor-pointer transition-all flex items-center"
              >
                <span>多阶段DCF估值</span>
              </button>
              <button
                type="button"
                onClick={() => scrollToSection('sec-models-25')}
                className="px-2.5 py-1 rounded-lg text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 cursor-pointer transition-all flex items-center gap-1.5 shadow-sm"
              >
                <span>25项量化指标</span>
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-[#176249] text-white">
                  {suite24Data?.total_models ? `${suite24Data.total_models}项` : '25项'}
                </span>
              </button>
              <button
                type="button"
                onClick={() => scrollToSection('sec-financials')}
                className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[var(--bg-card)] hover:bg-slate-100 text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border-color)] cursor-pointer transition-all flex items-center"
              >
                <span>官方三表底稿</span>
              </button>
              <button
                type="button"
                onClick={() => scrollToSection('sec-moat')}
                className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[var(--bg-card)] hover:bg-slate-100 text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border-color)] cursor-pointer transition-all flex items-center"
              >
                <span>护城河与供应链</span>
              </button>
              <button
                type="button"
                onClick={() => scrollToSection('sec-probes')}
                className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[var(--bg-card)] hover:bg-slate-100 text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border-color)] cursor-pointer transition-all flex items-center"
              >
                <span>财务结构与风险诊断</span>
              </button>
              <button
                type="button"
                onClick={() => scrollToSection('sec-radar')}
                className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[var(--bg-card)] hover:bg-slate-100 text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border-color)] cursor-pointer transition-all flex items-center"
              >
                <span>关联舆情雷达</span>
              </button>
            </div>

            <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] font-mono">
              <span>当前标的:</span>
              <span className="font-bold text-[var(--text-primary)] px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)]">
                {selectedTicker}
              </span>
              <span>·</span>
              <span>{formatDeviceTime(suite24Data?.as_of || analysis?.quote?.timestamp_iso || analysis?.quote?.timestamp_formatted || '')}</span>
            </div>
          </div>

          {loadingAnalysis ? (
            <div className="p-16 text-center text-xs text-[var(--text-muted)] bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl space-y-3">
              <div className="w-8 h-8 border-3 border-[#176249] border-t-transparent rounded-full animate-spin mx-auto" />
              <div className="text-sm font-semibold text-[var(--text-primary)]">
                正在调取官方财报并计算多阶段现金流折现 (DCF) 内在价值…
              </div>
              <p className="text-xs text-[var(--text-secondary)]">
                核验官方财务报表勾稽平衡、提取企业自由现金流并测算公允价值区间
              </p>
            </div>
          ) : analysisError ? (
            <div className="p-8 text-center text-rose-700 bg-rose-50 border border-rose-200 rounded-xl space-y-3">
              <div className="text-sm font-bold">获取标的深度研报失败</div>
              <p className="text-xs opacity-90">{analysisError}</p>
              <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => loadAnalysis(selectedTicker)}
                  className="px-3 py-1.5 rounded-md bg-[var(--bg-card)] text-[var(--text-primary)] border border-[var(--border-color)] text-xs font-medium cursor-pointer"
                >
                  重新加载
                </button>
                <button
                  type="button"
                  disabled={recollectingTicker}
                  onClick={() => void handleRecollectStock(selectedTicker)}
                  className="px-3.5 py-1.5 rounded-md bg-[#176249] hover:bg-[#14533e] text-white text-xs font-semibold cursor-pointer disabled:opacity-50 transition-all flex items-center gap-1.5"
                >
                  {recollectingTicker ? (
                    <>
                      <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>正在调度拉取中...</span>
                    </>
                  ) : (
                    <>
                      <span>在任务调度中拉取 [{selectedTicker}] 全量数据</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          ) : analysis ? (
            <>
              {/* 1. 标的概览标头卡片 */}
              <CompanyHeaderCard
                analysis={analysis}
                probes={probes}
                indProf={indProf}
                quote={quote}
                wacc={wacc}
                ratios={ratios}
                curPrice={curPrice}
                sym={sym}
                recollectingTicker={recollectingTicker}
                onRecollectStock={handleRecollectStock}
              />

              {/* 2. 自动带入数据多阶段 DCF 内在价值走廊 */}
              <DcfValuationCorridorCard
                activeValuation={activeValuation}
                analysis={analysis}
                curPrice={curPrice}
                sym={sym}
                customDiscountRate={customDiscountRate}
                customTerminalGrowth={customTerminalGrowth}
                customGrowthRates={customGrowthRates}
                customBeta={customBeta}
                tuning={tuning}
                showSensitivity={showSensitivity}
                setShowSensitivity={setShowSensitivity}
                setCustomDiscountRate={setCustomDiscountRate}
                setCustomTerminalGrowth={setCustomTerminalGrowth}
                setCustomGrowthRates={setCustomGrowthRates}
                setCustomBeta={setCustomBeta}
                onApplySensitivity={handleApplySensitivity}
                onResetSensitivity={handleResetSensitivity}
              />

              {/* 3. 核心金融量化指标体系 */}
              <QuantMetricsSuiteCard
                suite24Data={suite24Data}
                loadingSuite24={loadingSuite24}
                selectedTicker={selectedTicker}
                onReloadSuite24={loadSuite24}
              />

              {/* 4. 商业模式壁垒与护城河解构 */}
              <MoatAndSupplyChainCard aiQual={analysis.ai_qualitative_analysis} />

              {/* 5. 定量诊断探针 */}
              <QuantitativeProbesCard probes={probes} />

              {/* 6. 关联突发舆情与业务分部因果冲击 */}
              <EventImpactStreamCard eventsAnalysis={analysis.events_analysis} />
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}

export default AnalyticsTab
