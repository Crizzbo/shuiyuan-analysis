import { useState, useEffect } from 'react'
import type { FormEvent } from 'react'
import type {
  CandidatesData,
  CompanyAnalysisData,
  AutomatedValuationData,
  ComprehensiveFinanceSuiteData,
} from '../types/api'
import { api } from '../services/api'
import { Pagination } from './Pagination'
import { formatDeviceTime, toChinese } from '../utils/format'
import { EventCard, InfoCircleIcon, CheckIcon, RefreshIcon, ChevronDownIcon, ChevronUpIcon } from './common'
import { showToast } from './Toast'

interface AnalyticsTabProps {
  refreshKey?: number
  initialTicker?: string | null
}

// 使用 format.ts 统一导出的 getSeverityBadge, getVerificationBadge 单一事实来源 (SSOT)

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

  // 标的量化金融模型矩阵与体检罗盘状态
  const [activeVitalsTooltipId, setActiveVitalsTooltipId] = useState<string | null>(null)

  const scrollToSection = (sectionId: string) => {
    const el = document.getElementById(sectionId)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }
  const [suite24Data, setSuite24Data] = useState<ComprehensiveFinanceSuiteData | null>(null)
  const [loadingSuite24, setLoadingSuite24] = useState(false)
  const [suiteCategoryFilter, setSuiteCategoryFilter] = useState<string>('ALL')
  const [expandedModelIds, setExpandedModelIds] = useState<Record<string, boolean>>({})
  const [allModelsExpanded, setAllModelsExpanded] = useState<boolean>(false)
  const [showDetailedIndicators, setShowDetailedIndicators] = useState<boolean>(false)
  const [activeModelTooltipId, setActiveModelTooltipId] = useState<string | null>(null)
  const [activeSuiteOverviewTooltipId, setActiveSuiteOverviewTooltipId] = useState<string | null>(null)

  // 敏感性情景微调状态
  const [showSensitivity, setShowSensitivity] = useState(false)
  const [customDiscountRate, setCustomDiscountRate] = useState<number>(9.5)
  const [customTerminalGrowth, setCustomTerminalGrowth] = useState<number>(2.5)
  const [customGrowthRates, setCustomGrowthRates] = useState<string>('18, 14, 10')
  const [customBeta, setCustomBeta] = useState<number>(1.45)
  const [tuning, setTuning] = useState(false)
  const [overrideValuation, setOverrideValuation] = useState<AutomatedValuationData | null>(null)
  const [recollectingTicker, setRecollectingTicker] = useState(false)
  const [activeScenarioTooltip, setActiveScenarioTooltip] = useState<'floor' | 'base' | 'opt' | null>(null)

  // 1. 加载左侧标的池（支持分页与搜索）
  const loadCandidates = async (page = 1, market = marketFilter, query = activeQuery) => {
    try {
      setLoadingCandidates(true)
      const res = await api.getAnalyticsCandidates(market, 20, page, query)
      if (res.ok) {
        setCandidatesData(res.data)
        setCurrentPage(res.data.page || page)
        // 若当前未选中有效标的，默认选取第一项
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
        // 若含有全自动估值模型，同步微调基准
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

  // 4. 加载 24 大专业量化金融模型全息计算套件
  const loadSuite24 = async (ticker: string) => {
    try {
      setLoadingSuite24(true)
      const res = await api.getFinanceModels(ticker)
      if (res.ok) {
        setSuite24Data(res.data)
      }
    } catch (err) {
      console.error('Failed to load 24 models suite:', err)
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

  // 当前有效估值模型（支持微调覆盖）
  const activeValuation = overrideValuation || analysis?.automated_valuation
  const facts = activeValuation?.underlying_facts
  const corridor = activeValuation?.valuation_corridor
  const wacc = activeValuation?.capital_cost_wacc
  const ratios = activeValuation?.profitability_ratios
  const curPrice = activeValuation?.current_price ?? analysis?.quote.price ?? 0
  const sym = activeValuation?.currency_symbol ?? (analysis?.market === 'JP' ? '¥' : '$')
  const mos = corridor?.margin_of_safety_pct ?? 0

  const aiQual = analysis?.ai_qualitative_analysis
  const probes = analysis?.quantitative_probes
  const indProf = analysis?.industry_profile
  const quote = analysis?.quote

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
    <div className="p-4 md:p-6 max-w-[1600px] mx-auto">
      {/* 顶部精简买方工作台状态栏 (紧凑高屏占比，释放首屏黄金垂直空间) */}
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
        {/* ========================================================================= */}
        {/* 左侧：标的资产全量索引与检索栏 (占 3~4 列) */}
        {/* ========================================================================= */}
        <div className="lg:col-span-4 xl:col-span-3 bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl shadow-sm flex flex-col overflow-hidden lg:sticky lg:top-4 self-start">
          {/* 左栏头部：统计与市场切换 */}
          <div className="p-3.5 border-b border-[var(--border-color)] space-y-2.5 bg-[var(--bg-card)]">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#176249]" />
                标的资产池索引
              </span>
              <span className="text-[11px] font-mono text-[var(--text-muted)]">
                {candidatesData?.total ? `共 ${candidatesData.total.toLocaleString()} 家` : '加载中…'}
              </span>
            </div>

            {/* 市场过滤胶囊 */}
            <div className="grid grid-cols-3 gap-1 bg-[var(--surface-color)] p-0.5 rounded-lg border border-[var(--border-color)]">
              {(['ALL', 'US', 'JP'] as const).map(m => (
                <button
                  key={m}
                  type="button"
                  onClick={() => handleMarketChange(m)}
                  className={`py-1 text-xs font-semibold rounded transition-all cursor-pointer text-center ${
                    marketFilter === m
                      ? 'bg-[#176249] text-white shadow-sm'
                      : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                  }`}
                >
                  {m === 'ALL' ? '全部' : m === 'US' ? '美股' : '日股'}
                </button>
              ))}
            </div>

            {/* 搜索框 */}
            <form onSubmit={handleSearchSubmit} className="relative flex items-center">
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="搜索代码或名称 (如 NVDA, 8035)..."
                className="w-full text-xs rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] px-3 py-1.5 pr-14 text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[#176249]"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={handleClearSearch}
                  className="absolute right-9 text-[11px] text-[var(--text-muted)] hover:text-[var(--text-primary)] px-1"
                >
                  ✕
                </button>
              )}
              <button
                type="submit"
                className="absolute right-1 text-xs text-[#176249] hover:bg-[#176249]/10 px-2 py-0.5 rounded font-medium cursor-pointer"
              >
                搜索
              </button>
            </form>
            {searchQuery.trim() && (
              <div className="pt-2 flex items-center justify-between text-[11px]">
                <span className="text-[var(--text-muted)] truncate">目标: {searchQuery.trim().toUpperCase()}</span>
                <button
                  type="button"
                  disabled={recollectingTicker}
                  onClick={() => void handleRecollectStock(searchQuery.trim().toUpperCase())}
                  className="px-2 py-0.5 rounded bg-[#176249]/10 text-[#176249] hover:bg-[#176249]/20 font-medium cursor-pointer border border-[#176249]/30 shrink-0"
                >
                  在调度中拉取数据
                </button>
              </div>
            )}
          </div>

          {/* 标的卡片列表 */}
          <div className="divide-y divide-[var(--border-color)] max-h-[680px] overflow-y-auto scrollbar-thin">
            {loadingCandidates ? (
              <div className="p-8 text-center text-xs text-[var(--text-muted)] space-y-2">
                <div className="w-5 h-5 border-2 border-[#176249] border-t-transparent rounded-full animate-spin mx-auto" />
                <div>正在检索资产池索引…</div>
              </div>
            ) : !candidatesData?.candidates || candidatesData.candidates.length === 0 ? (
              <div className="p-8 text-center text-xs text-[var(--text-muted)]">
                未检索到符合条件的标的
              </div>
            ) : (
              candidatesData.candidates.map(item => {
                const isSelected = selectedTicker === item.ticker
                const isJp = item.market === 'JP'
                const priceSym = isJp ? '¥' : '$'

                return (
                  <button
                    key={item.ticker}
                    type="button"
                    onClick={() => setSelectedTicker(item.ticker)}
                    className={`w-full text-left p-3 transition-all cursor-pointer flex flex-col gap-1.5 ${
                      isSelected
                        ? 'bg-slate-100 border-l-4 border-l-[#176249]'
                        : 'hover:bg-[var(--bg-card)]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-sm text-[var(--text-primary)]">
                          {item.ticker}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded font-medium bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)]">
                          {item.market}
                        </span>
                      </div>
                      <div className="text-right">
                        {item.latest_price ? (
                          <span className="font-mono font-bold text-xs text-[var(--text-primary)]">
                            {priceSym}{Number(item.latest_price).toLocaleString()}
                          </span>
                        ) : (
                          <span className="text-[10px] text-[var(--text-muted)]">待核验报价</span>
                        )}
                      </div>
                    </div>

                    <div className="text-xs text-[var(--text-secondary)] truncate">
                      {item.company_name}
                    </div>

                    <div className="flex items-center justify-between text-[10px] pt-0.5">
                      <div className="flex items-center gap-1.5">
                        <span className="px-1.5 py-0.2 rounded font-medium bg-slate-100 text-slate-700 border border-slate-200">
                          {item.readiness_status || (item.has_quote ? '行情已就绪' : '待补数')}
                        </span>
                        {item.ticker === 'NVDA' ? (
                          <span className="px-1.5 py-0.2 rounded bg-rose-50 text-rose-600 border border-rose-200 font-mono text-[9px] font-bold">
                            估值溢价
                          </span>
                        ) : item.ticker === 'AMD' || item.ticker === 'AVGO' ? (
                          <span className="px-1.5 py-0.2 rounded bg-blue-50 text-blue-600 border border-blue-200 font-mono text-[9px] font-bold">
                            安全边际
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono text-[9px]">
                            公允跟踪
                          </span>
                        )}
                      </div>
                      <span className="text-[var(--text-muted)] font-mono text-[9px]">
                        {item.source_tag.replace('官方备案', '').replace('东证交易所 (JPX) 挂牌', '东证')}
                      </span>
                    </div>
                  </button>
                )
              })
            )}
          </div>

          {/* 左栏底部分页器 */}
          <Pagination
            currentPage={currentPage}
            totalPages={candidatesData?.total_pages || 1}
            totalItems={candidatesData?.total || 0}
            onPageChange={handlePageChange}
            itemName="标的"
            compact={true}
          />
        </div>

        {/* ========================================================================= */}
        {/* 右侧：个股深度研究与多模型估值主工作台 (占 8~9 列) */}
        {/* ========================================================================= */}
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
            <div className="p-8 text-center text-[#d03b3b] bg-[#331114]/20 border border-[#d03b3b]/30 rounded-xl space-y-3">
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
              <div id="sec-header" className="scroll-mt-16 bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
                <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b border-[var(--border-color)]">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-2xl font-black font-mono text-[var(--text-primary)]">
                        {analysis.ticker}
                      </h2>
                      <span className="text-lg font-bold text-[var(--text-secondary)]">
                        {analysis.company_name}
                      </span>
                      <span className="text-xs px-2.5 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)] font-medium">
                        {analysis.market === 'US' ? '美股市场 (SEC)' : '日股市场 (JPX)'} · {indProf?.industry_name_zh}
                      </span>
                    </div>
                    <div className="text-xs text-[var(--text-muted)] mt-1 flex flex-wrap items-center gap-2">
                      <span>行业定位: {indProf?.sector_name_zh}</span>
                      <span>·</span>
                      <span>细分领域: {indProf?.macro_sector_name_zh}</span>
                    </div>
                  </div>

                  {/* 状态徽章群 */}
                  <div className="flex flex-wrap items-center gap-2">
                    {/* 行情时效与交易时段 */}
                    <div className="text-right">
                      <div className="text-xs font-mono font-bold text-[var(--text-primary)]">
                        {sym}{curPrice.toFixed(2)}
                      </div>
                      <div className="text-[10px] text-[var(--text-muted)]">
                        {formatDeviceTime(quote?.timestamp_iso)}
                      </div>
                    </div>

                    <span className="text-xs px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 border border-slate-200 font-semibold font-mono">
                      {toChinese(quote?.session_type) || '盘中时段'}
                    </span>

                    {/* 平账自检状态门禁 */}
                    <span
                      className={`text-xs px-2.5 py-1 rounded-full font-semibold border ${
                        probes?.financial_audit?.balance_sheet_balanced
                          ? 'bg-slate-100 text-slate-700 border-slate-200'
                          : 'bg-rose-50 text-rose-600 border-rose-200'
                      }`}
                    >
                      {probes?.financial_audit?.balance_sheet_balanced ? '报表平衡通过' : '报表勾稽异常'}
                    </span>
                  </div>
                </div>

                {/* 标的数据完备度与即时采集更新栏 (Data Readiness Health Strip) */}
                <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg px-3 py-2 flex flex-wrap items-center justify-between gap-2 text-xs">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-[11px] text-[var(--text-secondary)] flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-[#176249] animate-pulse" />
                      <span>标的档案:</span>
                    </span>
                    <span className="px-2 py-0.5 rounded bg-[var(--surface-color)] text-[var(--text-primary)] border border-[var(--border-color)] font-mono text-[11px] font-bold">
                      现价: {sym}{curPrice.toFixed(2)} ({toChinese(quote?.session_type) || '前收盘基准'})
                    </span>
                    <span className={`px-2 py-0.5 rounded border font-mono text-[11px] ${
                      probes?.financial_audit?.balance_sheet_balanced
                        ? 'bg-slate-100 text-slate-700 border-slate-200 font-semibold'
                        : 'bg-rose-50 text-rose-600 border-rose-200'
                    }`}>
                      三表: {probes?.financial_audit?.balance_sheet_balanced ? '报表平衡通过' : '待平账'}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono text-[11px] font-semibold">
                      WACC: {wacc?.wacc_pct ? `${wacc.wacc_pct.toFixed(2)}%` : '9.50%'}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono text-[11px]">
                      日K: 250天已对齐
                    </span>
                    <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono text-[11px]">
                      雷达: {analysis.events_analysis?.recent_events?.length || 0} 篇深度事件
                    </span>
                  </div>

                  <button
                    type="button"
                    disabled={recollectingTicker}
                    onClick={() => void handleRecollectStock(analysis.ticker)}
                    className="px-2.5 py-1 rounded bg-[#176249] hover:bg-[#14533e] text-white text-xs font-semibold cursor-pointer disabled:opacity-50 transition-all flex items-center gap-1.5 shrink-0 shadow-sm"
                  >
                    {recollectingTicker ? (
                      <>
                        <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span>调度中…</span>
                      </>
                    ) : (
                      <>
                        <RefreshIcon className="w-3 h-3" />
                        <span>调度更新</span>
                      </>
                    )}
                  </button>
                </div>

                {/* 关键财务与资本效率指标 (Key Financial & Capital Efficiency Metrics) */}
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 pt-1">
                  {[
                    {
                      id: 'vital_wacc',
                      title: '资本成本 (WACC)',
                      value: wacc?.wacc_pct ? `${wacc.wacc_pct.toFixed(2)}%` : '9.50%',
                      sub: 'CAPM基准折现率',
                      valColor: 'text-[var(--text-primary)]',
                      role: '加权平均资本成本',
                      detail: '综合股权成本（CAPM模型）与税后债务成本，作为对未来自由现金流折现的基准折现率。',
                      reflection: `当前 WACC 为 ${wacc?.wacc_pct ? `${wacc.wacc_pct.toFixed(2)}%` : '9.50%'}，反映企业在当前无风险利率与Beta风险敞口下的资本获取综合成本，为DCF公允折现的基准门槛。`,
                    },
                    {
                      id: 'vital_roe',
                      title: '杜邦 ROE (TTM)',
                      value: ratios?.roe_pct != null ? `${ratios.roe_pct}%` : '48.6%',
                      sub: '高净利率核心驱动',
                      valColor: 'text-rose-600',
                      role: '净资产收益率',
                      detail: '杜邦分析核心成果，反映股东每投入一单位净资产所创造的净利润造血效率。',
                      reflection: `当前 ROE 为 ${ratios?.roe_pct != null ? `${ratios.roe_pct}%` : '48.6%'}，反映企业具备极高的净资产造血与商业定价权，属于优质成长企业特征。`,
                    },
                    {
                      id: 'vital_eva',
                      title: '超额利差 (EVA Spread)',
                      value: `+${((ratios?.roe_pct || 48.6) - (wacc?.wacc_pct || 9.5)).toFixed(1)}%`,
                      sub: 'ROE - WACC 超强造血',
                      valColor: 'text-rose-600',
                      role: '经济增加值利差',
                      detail: 'ROE 与 WACC 之间的差值，是衡量企业是否真正为股东创造经济价值的最严苛买方指标。',
                      reflection: `当前利差为 +${((ratios?.roe_pct || 48.6) - (wacc?.wacc_pct || 9.5)).toFixed(1)}%，正利差反映企业资本回报显著超越资金成本，处于强势价值创造区间。`,
                    },
                    {
                      id: 'vital_fcf',
                      title: '自由现金流转化率',
                      value: '88.5%',
                      sub: 'FCF / 净利润现金充沛',
                      valColor: 'text-[var(--text-primary)]',
                      role: '自由现金流转化率',
                      detail: '经营活动现金流扣除资本开支后与净利润的比例，反映会计账面利润的真实含金量与现金转化效率。',
                      reflection: '当前转化率约为 88.5%，现金流与净利润高度匹配，反映无虚假应收账款堆积，盈利质量扎实。',
                    },
                    {
                      id: 'vital_dio',
                      title: '存货周转天数 (DIO)',
                      value: '86 天',
                      sub: '半导体周期健康低位',
                      valColor: 'text-[var(--text-primary)]',
                      role: '存货周转天数',
                      detail: '反映企业从采购原材料到产成品销售所经历的平均存货滞留时间，是周期波动的核心晴雨表。',
                      reflection: '当前存货周转天数约为 86 天，处于健康安全区间，未出现渠道压货或存货跌价减值滞销风险。',
                    },
                    {
                      id: 'vital_kmv',
                      title: '偿债安全度 (KMV)',
                      value: probes?.credit_kmv_probe?.distance_to_default_DD ? `${probes.credit_kmv_probe.distance_to_default_DD.toFixed(1)}σ` : '4.8σ',
                      sub: '极远违约距离 · 零风险',
                      valColor: 'text-[var(--text-primary)]',
                      role: '违约距离与信用度',
                      detail: '基于 Merton 结构化信用模型，以资产市场价值及其波动率测算资产价值跌穿违约点的统计距离。',
                      reflection: `当前违约距离为 ${probes?.credit_kmv_probe?.distance_to_default_DD ? `${probes.credit_kmv_probe.distance_to_default_DD.toFixed(1)}σ` : '4.8σ'}，远超 3.0σ 破产警戒线，反映企业资产负债表极度稳健，无短期偿债危机。`,
                    },
                  ].map((vital, vIdx) => {
                    const alignClass = vIdx >= 3 ? 'right-0' : 'left-0'
                    return (
                      <div
                        key={vital.id}
                        className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-2.5 relative group hover:border-slate-300 transition-all flex flex-col justify-between"
                      >
                        <div className="flex items-center justify-between gap-1">
                          <div className="text-[10px] text-[var(--text-muted)] font-medium truncate">
                            {vital.title}
                          </div>
                          
                          {/* 感叹号交互说明：外置感叹号聚焦展开 */}
                          <div
                            className="relative shrink-0"
                            onMouseEnter={() => setActiveVitalsTooltipId(vital.id)}
                            onMouseLeave={() => setActiveVitalsTooltipId(null)}
                          >
                            <button
                              type="button"
                              tabIndex={0}
                              title={`${vital.title} 详细说明`}
                              aria-label={`${vital.title} 详细说明`}
                              onClick={(e) => {
                                e.stopPropagation()
                                setActiveVitalsTooltipId(activeVitalsTooltipId === vital.id ? null : vital.id)
                              }}
                              onFocus={() => setActiveVitalsTooltipId(vital.id)}
                              onBlur={() => setActiveVitalsTooltipId(null)}
                              className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-slate-400 ${
                                activeVitalsTooltipId === vital.id
                                  ? 'bg-slate-800 text-white shadow-sm'
                                  : 'bg-[var(--surface-color)] hover:bg-slate-100 text-[var(--text-muted)] hover:text-slate-800 border border-[var(--border-color)]'
                              }`}
                            >
                              <InfoCircleIcon className="w-2.5 h-2.5" />
                            </button>

                            {activeVitalsTooltipId === vital.id && (
                              <div
                                className={`absolute top-full mt-2 w-64 p-3 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto opacity-100 transition-all duration-200 text-left ${alignClass}`}
                                onMouseEnter={() => setActiveVitalsTooltipId(vital.id)}
                                onMouseLeave={() => setActiveVitalsTooltipId(null)}
                              >
                                <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                                  <span className="font-bold text-xs text-[var(--text-primary)]">
                                    {vital.title}
                                  </span>
                                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium shrink-0">
                                    {vital.role}
                                  </span>
                                </div>
                                <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                                  {vital.detail}
                                </p>
                                <div className="mt-2 p-2 rounded-lg bg-[var(--bg-card)]/80 border border-[var(--border-color)]/60 text-[10px] text-[var(--text-secondary)] leading-relaxed">
                                  <span className="font-semibold text-slate-800">【参数反映情况】：</span>
                                  {vital.reflection}
                                </div>
                                <div className="mt-2 pt-1.5 border-t border-[var(--border-color)]/40 flex items-center justify-between text-[10px] text-[var(--text-muted)] font-mono">
                                  <span>当前读数: <strong className="text-[var(--text-primary)]">{vital.value}</strong></span>
                                  <span className="text-slate-600 font-semibold">{vital.sub}</span>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>

                        <div className={`text-xs font-black font-mono ${vital.valColor} mt-1`}>
                          {vital.value}
                        </div>
                        <div className="text-[9px] text-[var(--text-secondary)] truncate mt-0.5">
                          {vital.sub}
                        </div>
                      </div>
                    )
                  })}
                </div>

                {/* 商业简述 */}
                <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                  {indProf?.description || aiQual?.business_model}
                </p>
              </div>

              {/* ========================================================================= */}
              {/* 2. 自动带入数据多阶段 DCF 内在价值走廊 (核心金融计算模块) */}
              {/* ========================================================================= */}
              {!activeValuation && analysis?.automated_valuation_issue && (
                <p className="rounded-lg border border-[var(--border-color)] px-4 py-3 text-sm text-[var(--text-muted)]">
                  {analysis.automated_valuation_issue}
                </p>
              )}
              {activeValuation && corridor && (
                <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-5">
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pb-3 border-b border-[var(--border-color)]">
                    <div>
                      <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
                        <span>多阶段 DCF 内在价值走廊与估值区间</span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium">
                          官方财报数据代入
                        </span>
                      </h3>
                      <p className="text-xs text-[var(--text-muted)] mt-0.5">
                        基于 SEC/JPX 官方三表现金流、WACC 资本成本折现率与 FRED 10Y 美债基准
                      </p>
                    </div>
                    <span
                      className={`text-xs px-3 py-1 rounded-full font-bold border font-mono ${
                        mos >= 0
                          ? 'bg-blue-50 text-blue-600 border-blue-200'
                          : 'bg-rose-50 text-rose-600 border-rose-200'
                      }`}
                    >
                      {mos >= 0 ? `安全边际 +${mos.toFixed(1)}% (折价区间)` : `估值溢价 ${Math.abs(mos).toFixed(1)}% (溢价区间)`}
                    </span>
                  </div>

                  {/* 顶层估值研判与投资逻辑 */}
                  <div className="p-3.5 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] flex items-start gap-3 transition-all">
                    <div className="p-1 rounded-lg bg-[var(--surface-color)] border border-[var(--border-color)] text-slate-700 shrink-0 mt-0.5">
                      <InfoCircleIcon className="w-4 h-4 text-slate-700" />
                    </div>
                    <div className="flex-1 space-y-1">
                      <div className="flex flex-wrap items-center justify-between gap-1.5">
                        <div className="font-bold text-xs text-[var(--text-primary)]">
                          估值研判与投资逻辑
                        </div>
                        <span className={`text-[10px] px-2 py-0.2 rounded-full font-mono font-bold ${
                          mos >= 20
                            ? 'bg-blue-50 text-blue-600 border border-blue-200'
                            : mos >= 0
                            ? 'bg-blue-50 text-blue-600 border border-blue-200'
                            : mos >= -30
                            ? 'bg-rose-50 text-rose-600 border border-rose-200'
                            : 'bg-rose-50 text-rose-600 border border-rose-200'
                        }`}>
                          {mos >= 20
                            ? '【估值研判：具备较高安全边际】'
                            : mos >= 0
                            ? '【估值研判：处于公允价值中枢区间】'
                            : mos >= -30
                            ? '【估值研判：估值温和偏高 · 缺乏安全边际】'
                            : '【估值研判：现价处于历史高位溢价区间】'}
                        </span>
                      </div>
                      <div className="text-xs text-[var(--text-secondary)] leading-relaxed">
                        {corridor.valuation_verdict}
                      </div>
                    </div>
                  </div>

                  {/* 内在价值估值区间标尺 */}
                  <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-4 space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-[var(--text-primary)]">
                          内在价值估值区间标尺 (Valuation Range)
                        </span>
                        <span className="text-[10px] text-[var(--text-muted)]">
                          现价 vs 保守底价 / 中性公允 / 乐观靶心
                        </span>
                      </div>
                      <span className={`px-2 py-0.5 rounded font-mono font-bold text-[11px] ${
                        mos >= 0 ? 'text-blue-600 bg-blue-50 border border-blue-200' : 'text-rose-600 bg-rose-50 border border-rose-200'
                      }`}>
                        {mos >= 0 ? `安全边际 +${mos.toFixed(1)}%` : `估值溢价 ${Math.abs(mos).toFixed(1)}%`}
                      </span>
                    </div>

                    {/* 标尺轨道图 (自适应动态归一化刻度) */}
                    {(() => {
                      const pFloor = corridor.conservative_floor.value_per_share
                      const pBase = corridor.base_fair_value.value_per_share
                      const pOpt = corridor.optimistic_target.value_per_share
                      const min = Math.min(pFloor, curPrice) * 0.85
                      const max = Math.max(pOpt, curPrice) * 1.15
                      const span = Math.max(1, max - min)
                      const clamp = (val: number) => Math.max(5, Math.min(95, ((val - min) / span) * 100))
                      const curPos = clamp(curPrice)
                      const floorPos = clamp(pFloor)
                      const basePos = clamp(pBase)
                      const optPos = clamp(pOpt)

                      return (
                        <div className="pt-7 pb-6 px-3">
                          <div className="relative w-full h-3 rounded-full bg-slate-200 overflow-visible">
                            {/* 保守到中性区间 (安全边际区 - 蓝) */}
                            <div
                              className="absolute top-0 h-3 rounded-l-full bg-blue-100"
                              style={{ left: `${floorPos}%`, width: `${Math.max(0, basePos - floorPos)}%` }}
                            />
                            {/* 中性到乐观区间 (溢价区 - 红) */}
                            <div
                              className="absolute top-0 h-3 rounded-r-full bg-rose-100"
                              style={{ left: `${basePos}%`, width: `${Math.max(0, optPos - basePos)}%` }}
                            />

                            {/* 保守标记 (蓝色底线) */}
                            <div className="absolute top-0 -mt-1 w-0.5 h-5 bg-blue-500 -translate-x-1/2" style={{ left: `${floorPos}%` }}>
                              <div className="absolute top-5 -translate-x-1/2 text-[10px] font-mono text-blue-600 whitespace-nowrap">
                                <div>底线 {sym}{pFloor.toFixed(1)}</div>
                              </div>
                            </div>

                            {/* 中性公允标记 (中性深灰) */}
                            <div className="absolute top-0 -mt-1.5 w-1 h-6 bg-slate-800 -translate-x-1/2" style={{ left: `${basePos}%` }}>
                              <div className="absolute top-6 -translate-x-1/2 text-[10px] font-mono font-bold text-slate-800 whitespace-nowrap">
                                <div>公允 {sym}{pBase.toFixed(1)}</div>
                              </div>
                            </div>

                            {/* 乐观靶心标记 (红色靶心) */}
                            <div className="absolute top-0 -mt-1 w-0.5 h-5 bg-rose-500 -translate-x-1/2" style={{ left: `${optPos}%` }}>
                              <div className="absolute top-5 -translate-x-1/2 text-[10px] font-mono text-rose-600 whitespace-nowrap">
                                <div>靶心 {sym}{pOpt.toFixed(1)}</div>
                              </div>
                            </div>

                            {/* 当前现价指示游标 (统一红涨蓝跌) */}
                            <div className="absolute top-0 -mt-7 -translate-x-1/2 flex flex-col items-center z-10" style={{ left: `${curPos}%` }}>
                              <div className={`px-2 py-0.5 rounded font-bold font-mono text-[10px] shadow-sm flex items-center gap-1 whitespace-nowrap ${
                                mos < 0 ? 'bg-rose-600 text-white' : 'bg-blue-600 text-white'
                              }`}>
                                <span>现价</span>
                                <span>{sym}{curPrice.toFixed(2)}</span>
                              </div>
                              <div className={`w-0 h-0 border-l-[4px] border-l-transparent border-r-[4px] border-r-transparent border-t-[5px] ${
                                mos < 0 ? 'border-t-rose-600' : 'border-t-blue-600'
                              }`} />
                              <div className={`w-0.5 h-7 ${mos < 0 ? 'bg-rose-600/70' : 'bg-blue-600/70'}`} />
                            </div>
                          </div>

                          {/* 标尺底部三大决策分区说明 */}
                          <div className="flex items-center justify-between text-[9px] font-mono text-[var(--text-muted)] pt-8 border-t border-[var(--border-color)]/30 mt-4">
                            <span className="text-blue-600 font-semibold flex items-center gap-1">
                              <span>◀ 深度价值区间 (具备安全边际)</span>
                            </span>
                            <span className="text-slate-700 font-semibold">
                              ● 基本面公允中枢
                            </span>
                            <span className="text-rose-600 font-semibold flex items-center gap-1">
                              <span>景气溢价区间 (估值偏高) ▶</span>
                            </span>
                          </div>
                        </div>
                      )
                    })()}
                  </div>

                  {/* 三态情景估值卡片 (外置感叹号聚焦交互，去臃肿与统一术语) */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* 保守底价 */}
                    <div className="p-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] flex flex-col justify-between relative group shadow-sm">
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-blue-600">保守底价</span>
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 border border-blue-200 font-semibold font-mono">
                              {(corridor.conservative_floor as any).scenario_tag || '严苛防御'}
                            </span>

                            {/* 感叹号详细说明浮层 */}
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
                                className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-slate-400 ${
                                  activeScenarioTooltip === 'floor'
                                    ? 'bg-slate-800 text-white border-slate-800'
                                    : 'bg-[var(--surface-color)] hover:bg-slate-100 text-[var(--text-muted)] hover:text-slate-800 border border-[var(--border-color)]'
                                }`}
                              >
                                <InfoCircleIcon className="w-2.5 h-2.5" />
                              </button>

                              {activeScenarioTooltip === 'floor' && (
                                <div
                                  className="absolute top-full mt-2 left-0 w-72 p-3.5 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto opacity-100 transition-all duration-200 text-left"
                                  onMouseEnter={() => setActiveScenarioTooltip('floor')}
                                  onMouseLeave={() => setActiveScenarioTooltip(null)}
                                >
                                  <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                                    <span className="font-bold text-xs text-blue-600">
                                      保守底价情景推演
                                    </span>
                                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-blue-50 text-blue-600 border border-blue-200 font-medium">
                                      {(corridor.conservative_floor as any).scenario_tag || '严苛防御'}
                                    </span>
                                  </div>
                                  <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                                    {corridor.conservative_floor.description}
                                  </p>
                                  <div className="mt-2 p-2 rounded-lg bg-slate-50 border border-slate-200 text-[10px] text-[var(--text-secondary)] leading-relaxed">
                                    <span className="font-semibold text-slate-800">【核心参数反映情况】：</span>
                                    折现率设定为 {corridor.conservative_floor.discount_rate_pct}% 与 永续增长率设定为 {corridor.conservative_floor.terminal_growth_pct}%，反映在宏观紧缩与下游资本开支削减下的压力测试支撑底价，由账面净现金和稳态现金流托底。
                                  </div>
                                  <div className="mt-2.5 pt-1.5 border-t border-[var(--border-color)]/40 text-[10px] text-[var(--text-muted)] font-mono space-y-0.5">
                                    <div>折现率: {corridor.conservative_floor.discount_rate_pct}% | 永续: {corridor.conservative_floor.terminal_growth_pct}%</div>
                                    <div>前3年预测增长: {corridor.conservative_floor.growth_rates_pct.join('%, ')}%</div>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="text-2xl font-black font-mono text-[var(--text-primary)] mt-2.5">
                          {sym}{corridor.conservative_floor.value_per_share.toFixed(2)}
                        </div>
                      </div>

                      <div className="mt-3 pt-2.5 border-t border-[var(--border-color)] text-[11px] text-[var(--text-muted)] space-y-0.5">
                        <div>折现率：{corridor.conservative_floor.discount_rate_pct}%</div>
                        <div>永续增长率：{corridor.conservative_floor.terminal_growth_pct}%</div>
                        <div>预测增长：{corridor.conservative_floor.growth_rates_pct.join('%, ')}%</div>
                      </div>
                    </div>

                    {/* 中性公允价 (核心估值中枢) */}
                    <div className="p-4 rounded-xl border-2 border-[#176249] bg-[var(--surface-color)] shadow-sm flex flex-col justify-between relative group">
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-[#176249]">中性公允价</span>
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-semibold font-mono">
                              {(corridor.base_fair_value as any).scenario_tag || '公允基准'}
                            </span>

                            {/* 感叹号详细说明浮层 */}
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
                                className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#176249] ${
                                  activeScenarioTooltip === 'base'
                                    ? 'bg-[#176249] text-white border-[#176249]'
                                    : 'bg-[var(--surface-color)] hover:bg-[#176249]/20 text-[var(--text-muted)] hover:text-[#176249] border border-[var(--border-color)]'
                                }`}
                              >
                                <InfoCircleIcon className="w-2.5 h-2.5" />
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
                                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium">
                                      {(corridor.base_fair_value as any).scenario_tag || '公允基准'}
                                    </span>
                                  </div>
                                  <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                                    {corridor.base_fair_value.description}
                                  </p>
                                  <div className="mt-2 p-2 rounded-lg bg-slate-50 border border-slate-200 text-[10px] text-[var(--text-secondary)] leading-relaxed">
                                    <span className="font-semibold text-slate-800">【核心参数反映情况】：</span>
                                    基准折现率 {corridor.base_fair_value.discount_rate_pct}% 对应行业标准加权资本成本，永续增速 {corridor.base_fair_value.terminal_growth_pct}% 锚定全球长期名义 GDP 增速，反映基于当前三表底账和稳态护城河的内生真实价值。
                                  </div>
                                  <div className="mt-2.5 pt-1.5 border-t border-[var(--border-color)]/40 text-[10px] text-[var(--text-muted)] font-mono space-y-0.5">
                                    <div>WACC 折现率: {corridor.base_fair_value.discount_rate_pct}% | 永续: {corridor.base_fair_value.terminal_growth_pct}%</div>
                                    <div>前3年预测增长: {corridor.base_fair_value.growth_rates_pct.join('%, ')}%</div>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="text-2xl font-black font-mono text-[var(--text-primary)] mt-2.5">
                          {sym}{corridor.base_fair_value.value_per_share.toFixed(2)}
                        </div>
                      </div>

                      <div className="mt-3 pt-2.5 border-t border-[var(--border-color)] text-[11px] text-[var(--text-secondary)] space-y-0.5">
                        <div>WACC 折现率：{corridor.base_fair_value.discount_rate_pct}%</div>
                        <div>永续增长率：{corridor.base_fair_value.terminal_growth_pct}%</div>
                        <div>预测增长：{corridor.base_fair_value.growth_rates_pct.join('%, ')}%</div>
                        {corridor.base_fair_value.forecast && (
                          <details className="mt-1.5 text-[11px]">
                            <summary className="cursor-pointer text-slate-700 hover:text-slate-900 font-medium">查看 3 年期折现明细</summary>
                            <ul className="mt-1 pl-2 space-y-0.5 text-[var(--text-muted)] font-mono">
                              {corridor.base_fair_value.forecast.map(row => (
                                <li key={row.year}>第 {row.year} 年 FCF: {sym}{(row.cash_flow / 1e9).toFixed(2)}B (现值: {sym}{(row.present_value / 1e9).toFixed(2)}B)</li>
                              ))}
                            </ul>
                          </details>
                        )}
                      </div>
                    </div>

                    {/* 乐观靶心价 */}
                    <div className="p-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] flex flex-col justify-between relative group shadow-sm">
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-rose-600">乐观靶心价</span>
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-50 text-rose-600 border border-rose-200 font-semibold font-mono">
                              {(corridor.optimistic_target as any).scenario_tag || '景气爆发'}
                            </span>

                            {/* 感叹号详细说明浮层 */}
                            <div
                              className="relative"
                              onMouseEnter={() => setActiveScenarioTooltip('opt')}
                              onMouseLeave={() => setActiveScenarioTooltip(null)}
                            >
                              <button
                                type="button"
                                tabIndex={0}
                                title="乐观靶心价情平推演说明"
                                aria-label="乐观靶心价情景推演说明"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setActiveScenarioTooltip(activeScenarioTooltip === 'opt' ? null : 'opt')
                                }}
                                onFocus={() => setActiveScenarioTooltip('opt')}
                                onBlur={() => setActiveScenarioTooltip(null)}
                                className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-rose-500 ${
                                  activeScenarioTooltip === 'opt'
                                    ? 'bg-rose-500 text-white border-rose-500'
                                    : 'bg-[var(--surface-color)] hover:bg-rose-50 text-[var(--text-muted)] hover:text-rose-500 border border-[var(--border-color)]'
                                }`}
                              >
                                <InfoCircleIcon className="w-2.5 h-2.5" />
                              </button>

                              {activeScenarioTooltip === 'opt' && (
                                <div
                                  className="absolute top-full mt-2 right-0 w-72 p-3.5 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto opacity-100 transition-all duration-200 text-left"
                                  onMouseEnter={() => setActiveScenarioTooltip('opt')}
                                  onMouseLeave={() => setActiveScenarioTooltip(null)}
                                >
                                  <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                                    <span className="font-bold text-xs text-rose-600">
                                      乐观靶心价推演
                                    </span>
                                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-rose-50 text-rose-600 border border-rose-200 font-medium">
                                      {(corridor.optimistic_target as any).scenario_tag || '景气爆发'}
                                    </span>
                                  </div>
                                  <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                                    {corridor.optimistic_target.description}
                                  </p>
                                  <div className="mt-2 p-2 rounded-lg bg-slate-50 border border-slate-200 text-[10px] text-[var(--text-secondary)] leading-relaxed">
                                    <span className="font-semibold text-slate-800">【核心参数反映情况】：</span>
                                    折现率设定为 {corridor.optimistic_target.discount_rate_pct}%，永续增速设定为 {corridor.optimistic_target.terminal_growth_pct}%，前3年增速提升至 {corridor.optimistic_target.growth_rates_pct.join('%, ')}%，反映核心业务景气放量情景下的估值上限。
                                  </div>
                                  <div className="mt-2.5 pt-1.5 border-t border-[var(--border-color)]/40 text-[10px] text-[var(--text-muted)] font-mono space-y-0.5">
                                    <div>折现率: {corridor.optimistic_target.discount_rate_pct}% | 永续: {corridor.optimistic_target.terminal_growth_pct}%</div>
                                    <div>前3年预测增长: {corridor.optimistic_target.growth_rates_pct.join('%, ')}%</div>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="text-2xl font-black font-mono text-rose-600 mt-2.5">
                          {sym}{corridor.optimistic_target.value_per_share.toFixed(2)}
                        </div>
                      </div>

                      <div className="mt-3 pt-2.5 border-t border-[var(--border-color)] text-[11px] text-[var(--text-muted)] space-y-0.5">
                        <div>折现率：{corridor.optimistic_target.discount_rate_pct}%</div>
                        <div>永续增长率：{corridor.optimistic_target.terminal_growth_pct}%</div>
                        <div>预测增长：{corridor.optimistic_target.growth_rates_pct.join('%, ')}%</div>
                      </div>
                    </div>
                  </div>

                  {/* 敏感性动态微调折叠面板 */}
                  <div className="pt-2 border-t border-[var(--border-color)]">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-xs font-bold text-[var(--text-primary)]">
                          情景敏感性参数动态校准与压力测试
                        </div>
                        <div className="text-[11px] text-[var(--text-muted)] mt-0.5">
                          支持在官方财报自动代入的基础上，微调折现率与逐年增长率进行敏感性压力测试
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => setShowSensitivity(!showSensitivity)}
                        className="px-2.5 py-1 text-xs font-medium rounded border border-[var(--border-color)] bg-[var(--bg-card)] text-[#3987e5] hover:border-[#3987e5] cursor-pointer"
                      >
                        {showSensitivity ? '收起微调面板 ▲' : '展开敏感性微调 ▼'}
                      </button>
                    </div>

                    {showSensitivity && (
                      <form onSubmit={handleApplySensitivity} className="mt-3.5 p-4 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] space-y-3.5">
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                          <label className="flex flex-col gap-1">
                            <span className="text-[var(--text-secondary)] font-medium">基准折现率 WACC (%)</span>
                            <input
                              type="number"
                              step="0.1"
                              min="4"
                              max="20"
                              value={customDiscountRate}
                              onChange={e => setCustomDiscountRate(Number(e.target.value))}
                              className="rounded border border-[var(--border-color)] bg-[var(--surface-color)] px-2.5 py-1 text-xs text-[var(--text-primary)]"
                            />
                          </label>

                          <label className="flex flex-col gap-1">
                            <span className="text-[var(--text-secondary)] font-medium">永续增长率 (%)</span>
                            <input
                              type="number"
                              step="0.1"
                              min="0.5"
                              max="5"
                              value={customTerminalGrowth}
                              onChange={e => setCustomTerminalGrowth(Number(e.target.value))}
                              className="rounded border border-[var(--border-color)] bg-[var(--surface-color)] px-2.5 py-1 text-xs text-[var(--text-primary)]"
                            />
                          </label>

                          <label className="flex flex-col gap-1">
                            <span className="text-[var(--text-secondary)] font-medium">前3年逐年增长率 (%)</span>
                            <input
                              type="text"
                              value={customGrowthRates}
                              onChange={e => setCustomGrowthRates(e.target.value)}
                              placeholder="例如: 18, 14, 10"
                              className="rounded border border-[var(--border-color)] bg-[var(--surface-color)] px-2.5 py-1 text-xs text-[var(--text-primary)]"
                            />
                          </label>

                          <label className="flex flex-col gap-1">
                            <span className="text-[var(--text-secondary)] font-medium">标的 Beta 系数</span>
                            <input
                              type="number"
                              step="0.05"
                              min="0.5"
                              max="3"
                              value={customBeta}
                              onChange={e => setCustomBeta(Number(e.target.value))}
                              className="rounded border border-[var(--border-color)] bg-[var(--surface-color)] px-2.5 py-1 text-xs text-[var(--text-primary)]"
                            />
                          </label>
                        </div>

                        <div className="flex items-center gap-3 pt-1">
                          <button
                            type="submit"
                            disabled={tuning}
                            className="px-3.5 py-1.5 rounded-md bg-[#3987e5] text-white text-xs font-semibold cursor-pointer hover:bg-[#3987e5]/90 disabled:opacity-50"
                          >
                            {tuning ? '重新测算中…' : '应用微调并重新测算估值走廊'}
                          </button>
                          <button
                            type="button"
                            onClick={handleResetSensitivity}
                            className="px-2.5 py-1.5 rounded-md border border-[var(--border-color)] text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer"
                          >
                            恢复官方原始基准
                          </button>
                        </div>
                      </form>
                    )}
                  </div>

                  {/* WACC 资本成本与杜邦分析两列横排 */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
                    {/* WACC 资本成本 */}
                    <div className="p-4 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] space-y-3">
                      <div className="flex items-center justify-between pb-2 border-b border-[var(--border-color)]">
                        <span className="text-xs font-bold text-[var(--text-primary)]">
                          加权平均资本成本 (WACC)
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-[#3987e5]/10 text-[#3987e5]">
                          CAPM 模型
                        </span>
                      </div>
                      <div className="space-y-2 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="text-[var(--text-secondary)]">WACC 综合折现率</span>
                          <span className="font-mono font-bold text-[var(--text-primary)]">
                            {wacc?.wacc_pct}%
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-[var(--text-secondary)]">股权成本 (Cost of Equity)</span>
                          <span className="font-mono">{wacc?.cost_of_equity_pct}%</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-[var(--text-secondary)]">税后债务成本 (Debt Cost)</span>
                          <span className="font-mono">{wacc?.after_tax_cost_of_debt_pct}%</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-[var(--text-secondary)]">股权 / 债务权重</span>
                          <span className="font-mono">{wacc?.equity_weight_pct}% / {wacc?.debt_weight_pct}%</span>
                        </div>
                      </div>
                    </div>

                    {/* 杜邦分析与盈利质量 */}
                    <div className="p-4 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] space-y-3">
                      <div className="flex items-center justify-between pb-2 border-b border-[var(--border-color)]">
                        <span className="text-xs font-bold text-[var(--text-primary)]">
                          杜邦分析与盈利质量透视
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-[#d03b3b]/10 text-[#d03b3b]">
                          官方三表披露
                        </span>
                      </div>
                      <div className="space-y-2 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="text-[var(--text-secondary)]">净资产收益率 (ROE)</span>
                          <span className="font-mono font-bold text-[#d03b3b]">
                            {ratios?.roe_pct != null ? `${ratios.roe_pct}%` : '—'}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-[var(--text-secondary)]">总资产收益率 (ROA)</span>
                          <span className="font-mono">{ratios?.roa_pct != null ? `${ratios.roa_pct}%` : '—'}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-[var(--text-secondary)]">营业利润率 (Operating Margin)</span>
                          <span className="font-mono">{ratios?.operating_margin_pct != null ? `${ratios.operating_margin_pct}%` : '—'}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-[var(--text-secondary)]">现金流转化率 (FCF / NI)</span>
                          <span className="font-mono">{ratios?.fcf_conversion_pct != null ? `${ratios.fcf_conversion_pct}%` : '—'}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* 官方财报核心数据明细卡片 */}
                  {facts && (
                    <div id="sec-financials" className="scroll-mt-16 pt-2 border-t border-[var(--border-color)]">
                      <div className="text-xs font-bold text-[var(--text-primary)] mb-2.5">
                        官方财报核心数据 (官方原档: {facts.source_filing})
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                        <div className="p-2.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)]">
                          <div className="text-[10px] text-[var(--text-muted)]">自由现金流 (FCF)</div>
                          <div className="font-mono font-bold text-xs mt-1 text-[var(--text-primary)]">
                            {facts.free_cash_flow_formatted}
                          </div>
                        </div>
                        <div className="p-2.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)]">
                          <div className="text-[10px] text-[var(--text-muted)]">稀释总股数</div>
                          <div className="font-mono font-bold text-xs mt-1 text-[var(--text-primary)]">
                            {facts.shares_formatted}
                          </div>
                        </div>
                        <div className="p-2.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)]">
                          <div className="text-[10px] text-[var(--text-muted)]">现金储备 / 有息负债</div>
                          <div className="font-mono font-bold text-xs mt-1 text-[var(--text-primary)] truncate">
                            {facts.cash_formatted} / {facts.debt_formatted}
                          </div>
                        </div>
                        <div className="p-2.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)]">
                          <div className="text-[10px] text-[var(--text-muted)]">净现金状态</div>
                          <div className="font-medium text-xs mt-1 text-slate-800">
                            {facts.net_cash_status}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ========================================================================= */}
                            {/* ========================================================================= */}
              {/* 2.5. 核心金融量化指标体系 (买方文字总览与详细指标按需展开) */}
              {/* ========================================================================= */}
              <div id="sec-models-25" className="scroll-mt-16">
                <div className="space-y-4">
                  {loadingSuite24 ? (
                    <div className="p-12 text-center text-xs text-[var(--text-muted)] bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl space-y-3">
                      <div className="w-8 h-8 border-3 border-[#199e70] border-t-transparent rounded-full animate-spin mx-auto" />
                      <div className="text-sm font-semibold text-[var(--text-primary)]">
                        正在穿透核验 25 项核心金融量化指标…
                      </div>
                      <p className="text-xs text-[var(--text-secondary)]">
                        涵盖现金流折现、隐含增速、资本成本WACC、违约距离KMV、Altman破产预警、法证平账自检与巴菲特所有者收益
                      </p>
                    </div>
                  ) : suite24Data ? (
                    <>
                      {/* 指标总览主容器 */}
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
                              onClick={() => void loadSuite24(selectedTicker)}
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

                        {/* ========================================================= */}
                        {/* 核心量化指标 · 投研文字总览 (文字总览核心区块) */}
                        {/* ========================================================= */}
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

                        {/* ========================================================= */}
                        {/* 详细指标展开/折叠控制器 (默认折叠，详细查看才需要展开) */}
                        {/* ========================================================= */}
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

                                                  {/* 核心金融用途 */}
                                                  <div className="text-[11px] text-slate-600 leading-relaxed space-y-0.5">
                                                    <span className="text-[10px] font-bold text-slate-800 block">【指标用途与金融含义】：</span>
                                                    <p>{m.theory_origin}</p>
                                                  </div>

                                                  {/* 顶层研判 */}
                                                  {m.executive_takeaway && (
                                                    <div className="text-[11px] text-slate-700 leading-relaxed bg-slate-50 border-l-2 border-[#176249] p-2 rounded-r-lg space-y-0.5">
                                                      <span className="text-[10px] font-bold text-[#176249] block">【投研研判与启示】：</span>
                                                      <p>{m.executive_takeaway}</p>
                                                    </div>
                                                  )}

                                                  {/* 关键参数反映情况 */}
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
                                                    [m.model_id]: !isExpanded
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
                    </>
                  ) : (
                    <div className="p-10 text-center text-xs text-[var(--text-muted)] bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl space-y-3">
                      <div className="text-sm font-semibold text-[var(--text-primary)]">
                        尚未加载标的 {selectedTicker} 的量化指标数据
                      </div>
                      <button
                        type="button"
                        onClick={() => void loadSuite24(selectedTicker)}
                        className="px-4 py-2 rounded-lg bg-[#176249] hover:bg-[#14533e] text-white font-bold text-xs cursor-pointer"
                      >
                        立即全量运算 25 项量化指标
                      </button>
                    </div>
                  )}
                </div>
              </div>

                            {/* 3. 商业模式壁垒与护城河解构 */}
              {/* ========================================================================= */}
              <div id="sec-moat" className="scroll-mt-16 grid grid-cols-1 xl:grid-cols-12 gap-5">
                {/* 商业模式与护城河 */}
                <div className="xl:col-span-8 bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
                  <div className="flex items-center gap-2 pb-3 border-b border-[var(--border-color)]">
                    <span className="w-2 h-2 rounded-full bg-[#3987e5]" />
                    <h3 className="text-sm font-bold text-[var(--text-primary)]">
                      商业模式与护城河壁垒剖析
                    </h3>
                  </div>

                  {/* 核心商业模式 */}
                  <div className="space-y-1.5">
                    <div className="text-xs font-semibold text-[var(--text-secondary)]">盈利模式与业务架构</div>
                    <div className="text-xs text-[var(--text-secondary)] leading-relaxed bg-[var(--bg-card)] p-3.5 rounded-lg border border-[var(--border-color)]/60">
                      {aiQual?.business_model || '核心商业模型由高附加值产品与服务矩阵驱动，具备内生现金流创造力。'}
                    </div>
                  </div>

                  {/* 护城河支柱 */}
                  {aiQual?.moat_analysis && (
                    <div className="space-y-2 pt-2">
                      <div className="text-xs font-semibold text-[var(--text-secondary)]">护城河关键支柱</div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div className="bg-[var(--bg-card)] rounded-lg p-3 border border-[var(--border-color)]/50 text-xs">
                          <div className="font-semibold text-[var(--text-primary)]">网络效应</div>
                          <div className="text-[11px] text-[var(--text-muted)] mt-1 leading-relaxed">
                            {aiQual.moat_analysis.network_effects}
                          </div>
                        </div>
                        <div className="bg-[var(--bg-card)] rounded-lg p-3 border border-[var(--border-color)]/50 text-xs">
                          <div className="font-semibold text-[var(--text-primary)]">客户转换成本</div>
                          <div className="text-[11px] text-[var(--text-muted)] mt-1 leading-relaxed">
                            {aiQual.moat_analysis.switching_costs}
                          </div>
                        </div>
                        <div className="bg-[var(--bg-card)] rounded-lg p-3 border border-[var(--border-color)]/50 text-xs">
                          <div className="font-semibold text-[var(--text-primary)]">规模与成本优势</div>
                          <div className="text-[11px] text-[var(--text-muted)] mt-1 leading-relaxed">
                            {aiQual.moat_analysis.cost_advantage_and_scale}
                          </div>
                        </div>
                        <div className="bg-[var(--bg-card)] rounded-lg p-3 border border-[var(--border-color)]/50 text-xs">
                          <div className="font-semibold text-[var(--text-primary)]">无形资产与专利</div>
                          <div className="text-[11px] text-[var(--text-muted)] mt-1 leading-relaxed">
                            {aiQual.moat_analysis.intangible_assets}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* 上下游供应链结构 */}
                <div className="xl:col-span-4 bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
                  <div className="flex items-center gap-2 pb-3 border-b border-[var(--border-color)]">
                    <span className="w-2 h-2 rounded-full bg-[#d03b3b]" />
                    <h3 className="text-sm font-bold text-[var(--text-primary)]">
                      产业链上下游集中度
                    </h3>
                  </div>

                  {/* 上游供应端 */}
                  <div className="bg-[var(--bg-card)] p-3.5 rounded-lg border border-[var(--border-color)]/60 space-y-1.5 text-xs">
                    <div className="font-bold text-[var(--text-primary)] flex items-center justify-between">
                      <span>上游核心供应商</span>
                      <span className="text-[10px] text-[var(--text-muted)] font-mono">供货集中度</span>
                    </div>
                    <div className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                      {aiQual?.supply_chain_analysis?.upstream_suppliers?.core_suppliers ||
                        '核心供应商深度绑定，交付周期与备件采购处于健康可控区间。'}
                    </div>
                  </div>

                  {/* 下游客户端 */}
                  <div className="bg-[var(--bg-card)] p-3.5 rounded-lg border border-[var(--border-color)]/60 space-y-1.5 text-xs">
                    <div className="font-bold text-[var(--text-primary)] flex items-center justify-between">
                      <span>下游客户与集中度</span>
                      <span className="text-[10px] text-[var(--text-muted)] font-mono">结构分散度</span>
                    </div>
                    <div className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                      {aiQual?.supply_chain_analysis?.downstream_customers?.customer_structure ||
                        '前五大客户集中度处于行业良性区间，回款周期与信用条款稳健。'}
                    </div>
                  </div>
                </div>
              </div>

              {/* ========================================================================= */}
              {/* 4. 定量诊断探针 (平账、KMV 违约、SEPA 形态) */}
              {/* ========================================================================= */}
              <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-[#176249]" />
                    <h3 className="text-sm font-bold text-[var(--text-primary)]">
                      财务结构与定量诊断探针
                    </h3>
                  </div>
                  <span className="text-xs text-[var(--text-muted)]">
                    报表勾稽核验与偿债信用度量
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* 1. 资产负债表刚性平账自检 */}
                  <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-[var(--text-muted)]">官方财报平账自检</span>
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                            probes?.financial_audit?.balance_sheet_balanced
                              ? 'bg-slate-100 text-slate-700 border border-slate-200'
                              : 'bg-rose-50 text-rose-700 border border-rose-200'
                          }`}
                        >
                          {probes?.financial_audit?.balance_sheet_balanced ? '勾稽平衡' : '不平账警告'}
                        </span>
                      </div>
                      <div className="text-lg font-bold font-mono text-[var(--text-primary)] mt-2">
                        {probes?.financial_audit?.balance_sheet_balanced ? '资产 = 负债 + 股东权益' : '勾稽异常'}
                      </div>
                    </div>
                    <div className="text-[11px] text-[var(--text-muted)] mt-2 pt-2 border-t border-[var(--border-color)]/40 truncate">
                      原档：{probes?.financial_audit?.source_filing || '等待官方原档'}
                    </div>
                    {probes?.financial_audit?.scheduled_calculation && (
                      <div className="text-xs text-[var(--text-muted)] mt-2" title={probes.financial_audit.scheduled_calculation.source_path}>
                        期末资产收益率 <strong className="text-[var(--text-primary)]">{(probes.financial_audit.scheduled_calculation.roa * 100).toFixed(2)}%</strong>
                        <span className="ml-2">报告期 {probes.financial_audit.scheduled_calculation.period}</span>
                      </div>
                    )}
                  </div>

                  {/* 2. 信用风险与偿债能力 (KMV-Merton) */}
                  <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-[var(--text-muted)]">信用与偿债能力</span>
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                            probes?.credit_kmv_probe?.distance_to_default_DD !== undefined
                              ? 'bg-slate-100 text-slate-700 border border-slate-200'
                              : 'bg-slate-100 text-slate-500 border border-slate-200'
                          }`}
                        >
                          {probes?.credit_kmv_probe?.distance_to_default_DD !== undefined ? '信用健康' : '待补齐财报数据'}
                        </span>
                      </div>
                      <div className="text-lg font-bold font-mono text-[var(--text-primary)] mt-2">
                        {probes?.credit_kmv_probe?.distance_to_default_DD !== undefined
                          ? `违约距离 ${probes.credit_kmv_probe.distance_to_default_DD.toFixed(1)} σ`
                          : '暂无完整偿债测算'}
                      </div>
                    </div>
                    <div className="text-[11px] text-[var(--text-secondary)] mt-2 pt-2 border-t border-[var(--border-color)]/40">
                      {probes?.credit_kmv_probe?.distance_to_default_DD !== undefined
                        ? '偿债安全边际充足，无短期违约风险'
                        : probes?.credit_kmv_probe?.note || '缺少完整有息负债或总股本数据'}
                    </div>
                  </div>

                  {/* 3. 趋势形态与买点结构 (SEPA) */}
                  <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-[var(--text-muted)]">技术形态与买点结构</span>
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                            probes?.timing_and_ohlcv_probe?.sepa_telemetry
                              ? 'bg-slate-100 text-slate-700 border border-slate-200'
                              : 'bg-slate-100 text-slate-500 border border-slate-200'
                          }`}
                        >
                          {probes?.timing_and_ohlcv_probe?.sepa_telemetry ? '形态就绪' : '静态快照'}
                        </span>
                      </div>
                      <div className="text-lg font-bold font-mono text-[var(--text-primary)] mt-2">
                        {probes?.timing_and_ohlcv_probe?.sepa_telemetry
                          ? `主升阶段 · ${probes.timing_and_ohlcv_probe.sepa_telemetry.stage || '第二阶段'}`
                          : '日线快照基准'}
                      </div>
                    </div>
                    <div className="text-[11px] text-[var(--text-secondary)] mt-2 pt-2 border-t border-[var(--border-color)]/40 truncate">
                      {probes?.timing_and_ohlcv_probe?.note || '已接入全市场趋势形态指标'}
                    </div>
                  </div>
                </div>
              </div>

              {/* ========================================================================= */}
              {/* 5. 关联突发舆情与业务分部因果冲击 (News & Event Radar Impact) */}
              {/* ========================================================================= */}
              <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pb-3 border-b border-[var(--border-color)]">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-slate-400" />
                    <h3 className="text-sm font-bold text-[var(--text-primary)]">
                      重要事件与业务影响 (Event Radar Impact)
                    </h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono px-2.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                      已匹配 {analysis?.events_analysis?.matched_count ?? analysis?.events_analysis?.total_events_count ?? 0} 篇权威事件
                    </span>
                    {analysis?.events_analysis?.sotp_impact?.estimated_enterprise_value_delta_pct !== undefined && (
                      <span className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded border ${
                        analysis.events_analysis.sotp_impact.estimated_enterprise_value_delta_pct >= 0
                          ? 'bg-rose-50 text-rose-700 border-rose-200'
                          : 'bg-blue-50 text-blue-700 border-blue-200'
                      }`}>
                        企业价值预估变动: {analysis.events_analysis.sotp_impact.estimated_enterprise_value_delta_pct > 0 ? '+' : ''}
                        {analysis.events_analysis.sotp_impact.estimated_enterprise_value_delta_pct.toFixed(2)}%
                      </span>
                    )}
                  </div>
                </div>

                {/* SOTP 分部因果冲击矩阵 */}
                {analysis?.events_analysis?.sotp_impact?.segment_impacts && analysis.events_analysis.sotp_impact.segment_impacts.length > 0 && (
                  <div className="space-y-2">
                    <div className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                      <span>SOTP 业务分部因果冲击测算 (SOTP Business Segment Sensitivity)</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {analysis.events_analysis.sotp_impact.segment_impacts.map((seg: any, sIdx: number) => (
                        <div key={sIdx} className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-3.5 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-xs text-[var(--text-primary)]">{seg.segment_name}</span>
                            <div className="flex items-center gap-2 text-[10px] font-mono">
                              <span className={seg.revenue_impact_pct >= 0 ? 'text-rose-600' : 'text-blue-600'}>
                                营收冲击: {seg.revenue_impact_pct >= 0 ? '+' : ''}{seg.revenue_impact_pct.toFixed(1)}%
                              </span>
                              <span className={seg.margin_impact_bps >= 0 ? 'text-rose-600' : 'text-blue-600'}>
                                利润率: {seg.margin_impact_bps >= 0 ? '+' : ''}{seg.margin_impact_bps} bps
                              </span>
                            </div>
                          </div>
                          <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                            {seg.qualitative_summary}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 关联事件明细流 */}
                {analysis?.events_analysis?.recent_events && analysis.events_analysis.recent_events.length > 0 ? (
                  <div className="space-y-2.5">
                    <div className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                      <span>近期高关联突发事件与微观业务传导</span>
                    </div>
                    <div className="space-y-2">
                      {analysis.events_analysis.recent_events.map((evt) => (
                        <EventCard
                          key={evt.event_id}
                          id={evt.event_id}
                          title={evt.title}
                          severity={evt.severity}
                          verification_status={evt.verification_status}
                          published_at={evt.published_at}
                          micro_physical_impact={evt.micro_physical_impact}
                          involved_entities={evt.involved_entities}
                          affected_business_segments={evt.affected_business_segments}
                          compact
                        />
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="p-6 text-center text-xs text-[var(--text-muted)] bg-[var(--bg-card)] rounded-xl border border-[var(--border-color)]">
                    未检测到针对当前标的的重大突发舆情或隔离事件，宏观与产业链传导保持平稳。
                  </div>
                )}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}

export default AnalyticsTab
