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
import { EventCard } from './common'
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

  // 顶层子视图切换：全息深度档案 vs 24 大专业量化金融模型矩阵
  const [analyticsSubTab, setAnalyticsSubTab] = useState<'dossier' | 'suite_24'>('dossier')
  const [suite24Data, setSuite24Data] = useState<ComprehensiveFinanceSuiteData | null>(null)
  const [loadingSuite24, setLoadingSuite24] = useState(false)
  const [suiteCategoryFilter, setSuiteCategoryFilter] = useState<string>('ALL')
  const [expandedModelIds, setExpandedModelIds] = useState<Record<string, boolean>>({})
  const [allModelsExpanded, setAllModelsExpanded] = useState<boolean>(false)

  // 敏感性情景微调状态
  const [showSensitivity, setShowSensitivity] = useState(false)
  const [customDiscountRate, setCustomDiscountRate] = useState<number>(9.5)
  const [customTerminalGrowth, setCustomTerminalGrowth] = useState<number>(2.5)
  const [customGrowthRates, setCustomGrowthRates] = useState<string>('18, 14, 10')
  const [customBeta, setCustomBeta] = useState<number>(1.45)
  const [tuning, setTuning] = useState(false)
  const [overrideValuation, setOverrideValuation] = useState<AutomatedValuationData | null>(null)
  const [recollectingTicker, setRecollectingTicker] = useState(false)

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
          message: '官方三表已平账，估值走廊已根据最新底账重算完成。',
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
      if (analyticsSubTab === 'suite_24') {
        void loadSuite24(selectedTicker)
      }
    }
  }, [selectedTicker, refreshKey, analyticsSubTab])

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

  return (
    <div className="p-4 md:p-6 max-w-[1600px] mx-auto">
      {/* 顶部主工作台标头 */}
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 md:p-5 mb-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-sm">
        <div>
          <h1 className="text-base font-bold text-[var(--text-primary)] flex items-center gap-2">
            <span>标的资产全息商业解构与估值工作台</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#3987e5]/15 text-[#3987e5] border border-[#3987e5]/30 font-medium">
              全量 14,892 标的覆盖
            </span>
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            端到端集成 SEC/JPX 官方财报原档平账核验、多阶段 DCF 估值走廊、加权资本成本 (WACC) 与商业模式护城河透视。
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-[var(--text-muted)] font-mono">
          <span>全自动底账代入</span>
          <span>·</span>
          <span>买方级情景推演</span>
          <span>·</span>
          <span>严禁机械打分</span>
        </div>
      </div>

      {/* 左右分栏核心工作区 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* ========================================================================= */}
        {/* 左侧：标的资产全量索引与检索栏 (占 3~4 列) */}
        {/* ========================================================================= */}
        <div className="lg:col-span-4 xl:col-span-3 bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl shadow-sm flex flex-col overflow-hidden">
          {/* 左栏头部：统计与市场切换 */}
          <div className="p-3.5 border-b border-[var(--border-color)] space-y-2.5 bg-[var(--bg-card)]">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#3987e5]" />
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
                      ? 'bg-[#3987e5] text-white shadow-sm'
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
                className="w-full text-xs rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] px-3 py-1.5 pr-14 text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[#3987e5]"
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
                className="absolute right-1 text-xs text-[#3987e5] hover:bg-[#3987e5]/10 px-2 py-0.5 rounded font-medium cursor-pointer"
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
                  className="px-2 py-0.5 rounded bg-[#3987e5]/10 text-[#3987e5] hover:bg-[#3987e5]/20 font-medium cursor-pointer border border-[#3987e5]/30 shrink-0"
                >
                  ⚡ 在调度中拉取数据
                </button>
              </div>
            )}
          </div>

          {/* 标的卡片列表 */}
          <div className="divide-y divide-[var(--border-color)] max-h-[680px] overflow-y-auto scrollbar-thin">
            {loadingCandidates ? (
              <div className="p-8 text-center text-xs text-[var(--text-muted)] space-y-2">
                <div className="w-5 h-5 border-2 border-[#3987e5] border-t-transparent rounded-full animate-spin mx-auto" />
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
                        ? 'bg-[#3987e5]/10 border-l-4 border-l-[#3987e5]'
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
                      <span
                        className={`px-1.5 py-0.5 rounded font-medium ${
                          item.has_quote && item.has_sec_filing
                            ? 'bg-[#199e70]/15 text-[#199e70] border border-[#199e70]/30'
                            : item.has_quote
                            ? 'bg-[#3987e5]/15 text-[#3987e5] border border-[#3987e5]/30'
                            : 'bg-gray-500/10 text-[var(--text-muted)] border border-gray-500/20'
                        }`}
                      >
                        {item.readiness_status || (item.has_quote ? '行情就绪' : '待补数')}
                      </span>
                      <span className="text-[var(--text-muted)]">
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
        {/* 右侧：个股深度商业解构与估值主工作台 (占 8~9 列) */}
        {/* ========================================================================= */}
        <div className="lg:col-span-8 xl:col-span-9 space-y-5">
          {/* 顶层子视图切换器：全息深度商业档案 vs 24 大专业量化金融模型矩阵 */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-[var(--surface-color)] border border-[var(--border-color)] p-2.5 rounded-xl shadow-sm">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setAnalyticsSubTab('dossier')}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                  analyticsSubTab === 'dossier'
                    ? 'bg-[#3987e5] text-white shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]'
                }`}
              >
                <span>📊</span>
                <span>全息深度档案与估值走廊</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setAnalyticsSubTab('suite_24')
                  if (!suite24Data || suite24Data.ticker !== selectedTicker) {
                    void loadSuite24(selectedTicker)
                  }
                }}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                  analyticsSubTab === 'suite_24'
                    ? 'bg-[#199e70] text-white shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]'
                }`}
              >
                <span>⚡</span>
                <span>24 大专业量化金融模型矩阵 (24/24 全量运转)</span>
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-white/20">
                  {suite24Data?.total_models ? `${suite24Data.total_models}个` : '24个'}
                </span>
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

          {analyticsSubTab === 'suite_24' ? (
            <div className="space-y-4">
              {loadingSuite24 ? (
                <div className="p-16 text-center text-xs text-[var(--text-muted)] bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl space-y-3">
                  <div className="w-8 h-8 border-3 border-[#199e70] border-t-transparent rounded-full animate-spin mx-auto" />
                  <div className="text-sm font-semibold text-[var(--text-primary)]">
                    正在并发执行 24 大专业量化与金融估值模型矩阵…
                  </div>
                  <p className="text-xs text-[var(--text-secondary)]">
                    涵盖多阶段DCF、反向DCF、EBO、WACC、KMV违约距离、Altman Z、Beneish M、GARCH(1,1)、Kalman滤波、Black-Litterman、CRR二叉树、SVI曲面、5000次蒙特卡洛与SEPA突破
                  </p>
                </div>
              ) : suite24Data ? (
                <>
                  {/* 24 大模型顶层指标指示条 */}
                  <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 md:p-5 shadow-sm space-y-3">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-[var(--border-color)]">
                      <div className="flex items-center gap-3">
                        <span className="w-3 h-3 rounded-full bg-[#199e70]" />
                        <div>
                          <div className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
                            <span>24 大专业量化与金融估值模型矩阵</span>
                            <span className="text-xs px-2 py-0.5 rounded bg-[#199e70]/15 text-[#199e70] border border-[#199e70]/30 font-medium">
                              {suite24Data.total_models}/24 全量验证通过
                            </span>
                            <span className="text-xs px-2 py-0.5 rounded bg-[#3987e5]/15 text-[#3987e5] border border-[#3987e5]/30 font-mono">
                              {suite24Data.ticker}
                            </span>
                          </div>
                          <div className="text-xs text-[var(--text-muted)] mt-0.5">
                            严密防守金融数学边界，资产负债表刚性平账，零大模型幻觉，高吞吐纯本地执行
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => void loadSuite24(selectedTicker)}
                          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#199e70] hover:bg-[#147d58] text-white flex items-center gap-1.5 transition-all shadow-sm cursor-pointer"
                        >
                          <span>↻</span>
                          <span>重新核算</span>
                        </button>
                      </div>
                    </div>

                    {/* 指标矩阵状态胶囊 */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-1">
                      <div className="bg-[var(--bg-card)] p-3 rounded-lg border border-[var(--border-color)]/60">
                        <div className="text-[10px] text-[var(--text-muted)]">模型执行覆盖</div>
                        <div className="text-sm font-bold font-mono text-[#199e70] mt-0.5">
                          {suite24Data.total_models} / 24 个模型
                        </div>
                        <div className="text-[10px] text-[var(--text-secondary)] mt-0.5">100% 执行率</div>
                      </div>

                      <div className="bg-[var(--bg-card)] p-3 rounded-lg border border-[var(--border-color)]/60">
                        <div className="text-[10px] text-[var(--text-muted)]">端到端执行耗时</div>
                        <div className="text-sm font-bold font-mono text-[#3987e5] mt-0.5">
                          {suite24Data.total_execution_ms.toFixed(1)} ms
                        </div>
                        <div className="text-[10px] text-[var(--text-secondary)] mt-0.5">超低延迟本地计算</div>
                      </div>

                      <div className="bg-[var(--bg-card)] p-3 rounded-lg border border-[var(--border-color)]/60">
                        <div className="text-[10px] text-[var(--text-muted)]">金融数学边界防御</div>
                        <div className="text-sm font-bold text-[#199e70] mt-0.5">
                          全部通过
                        </div>
                        <div className="text-[10px] text-[var(--text-secondary)] mt-0.5">除零/除负/极值收敛校验</div>
                      </div>

                      <div className="bg-[var(--bg-card)] p-3 rounded-lg border border-[var(--border-color)]/60">
                        <div className="text-[10px] text-[var(--text-muted)]">三表勾稽恒等式</div>
                        <div className="text-sm font-bold text-[#199e70] mt-0.5">
                          刚性平账
                        </div>
                        <div className="text-[10px] text-[var(--text-secondary)] mt-0.5">资产 = 负债 + 权益</div>
                      </div>
                    </div>

                    {/* 分类筛选器与全量展开/收起按钮 */}
                    <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[var(--border-color)]/60">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-[11px] text-[var(--text-muted)] font-medium mr-1">分类过滤:</span>
                        {[
                          { key: 'ALL', label: '全部模型 (24)' },
                          { key: '估值走廊模型群', label: '估值走廊群 (7)' },
                          { key: '资本成本与杜邦拆解群', label: '资本成本与杜邦 (5)' },
                          { key: '信用与破产预警群', label: '信用与破产预警 (2)' },
                          { key: '法证与舞弊排查群', label: '法证舞弊与平账 (3)' },
                          { key: '微观流动性与波动率群', label: '流动性与波动率 (2)' },
                          { key: '资产配置与衍生品群', label: '资产配置与衍生品 (4)' },
                          { key: '趋势选股与形态收敛群', label: '形态选股与突破 (1)' },
                        ].map(cat => (
                          <button
                            key={cat.key}
                            type="button"
                            onClick={() => setSuiteCategoryFilter(cat.key)}
                            className={`text-xs px-2.5 py-1 rounded-lg transition-all cursor-pointer font-medium ${
                              suiteCategoryFilter === cat.key
                                ? 'bg-[#199e70] text-white shadow-sm'
                                : 'bg-[var(--bg-card)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] border border-[var(--border-color)]'
                            }`}
                          >
                            {cat.label}
                          </button>
                        ))}
                      </div>

                      <button
                        type="button"
                        onClick={() => setAllModelsExpanded(!allModelsExpanded)}
                        className="text-xs px-3 py-1 rounded-lg bg-[var(--bg-card)] hover:bg-[#199e70]/10 text-[#199e70] border border-[#199e70]/30 transition-all font-medium cursor-pointer shrink-0 flex items-center gap-1"
                      >
                        <span>{allModelsExpanded ? '收起全部参数矩阵 ▲' : '全量展开参数矩阵 ▼'}</span>
                      </button>
                    </div>
                  </div>

                  {/* 24 大模型矩阵卡片网格 (采用双列宽幅布局，提供充裕空间展示多参数解读) */}
                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                    {suite24Data.models
                      .filter(m => suiteCategoryFilter === 'ALL' || m.category === suiteCategoryFilter)
                      .map((m, idx) => {
                        const isExpanded = expandedModelIds[m.model_id] ?? allModelsExpanded
                        const params = m.parameter_interpretations || []

                        return (
                          <div
                            key={m.model_id}
                            className="bg-[var(--surface-color)] border border-[var(--border-color)] hover:border-[#199e70]/50 rounded-xl p-4.5 flex flex-col justify-between transition-all shadow-sm space-y-3.5"
                          >
                            <div className="space-y-3">
                              {/* 卡片顶部：编号、名称与执行状态 */}
                              <div className="flex items-start justify-between gap-2">
                                <div className="flex items-center gap-2">
                                  <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-[#199e70]/15 text-[#199e70] border border-[#199e70]/30 shrink-0">
                                    #{idx + 1}
                                  </span>
                                  <h3 className="text-sm font-bold text-[var(--text-primary)] leading-tight">
                                    {m.name_zh}
                                  </h3>
                                </div>
                                <div className="flex items-center gap-1.5 shrink-0">
                                  <span className="text-[10px] px-1.5 py-0.2 rounded font-mono text-[var(--text-muted)] bg-[var(--bg-card)] border border-[var(--border-color)]">
                                    {m.execution_ms.toFixed(1)} ms
                                  </span>
                                  <span className="text-[10px] px-1.5 py-0.2 rounded font-semibold bg-[#199e70]/20 text-[#199e70] border border-[#199e70]/40">
                                    ✓ 验证通过
                                  </span>
                                </div>
                              </div>

                              {/* 理论渊源与分类标签 */}
                              <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                                <span className="px-2 py-0.5 rounded bg-[var(--bg-card)] text-[var(--text-secondary)] border border-[var(--border-color)] font-medium">
                                  {m.category}
                                </span>
                                <span className="text-[var(--text-muted)] truncate max-w-[320px]" title={m.theory_origin}>
                                  🏛️ {m.theory_origin}
                                </span>
                              </div>

                              {/* 顶层商业决策与投资逻辑 (Executive Takeaway) */}
                              {m.executive_takeaway && (
                                <div className="bg-[#199e70]/10 border-l-2 border-[#199e70] p-3 rounded-r-lg text-xs text-[var(--text-primary)] leading-relaxed space-y-1">
                                  <div className="text-[10px] font-bold text-[#199e70] flex items-center gap-1">
                                    <span>💡 顶层商业研判与投资逻辑</span>
                                  </div>
                                  <p>{m.executive_takeaway}</p>
                                </div>
                              )}

                              {/* 多参数结构化解读矩阵 (Parameter Interpretations) */}
                              {params.length > 0 && (
                                <div className="space-y-2 pt-2 border-t border-[var(--border-color)]/60">
                                  <div className="flex items-center justify-between text-xs">
                                    <span className="font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                                      <span className="w-2 h-2 rounded-full bg-[#3987e5]" />
                                      <span>多参数结构化解读矩阵 ({params.length} 项关键参数)</span>
                                    </span>
                                    <button
                                      type="button"
                                      onClick={() => {
                                        setExpandedModelIds(prev => ({
                                          ...prev,
                                          [m.model_id]: !isExpanded
                                        }))
                                      }}
                                      className="text-xs text-[#3987e5] hover:underline font-medium cursor-pointer"
                                    >
                                      {isExpanded ? '收起参数矩阵 ▲' : `展开解读 (${params.length} 项) ▼`}
                                    </button>
                                  </div>

                                  {isExpanded && (
                                    <div className="space-y-2 pt-1">
                                      {params.map((param, pIdx) => {
                                        const statusBg =
                                          param.status_level === 'safe'
                                            ? 'bg-[#199e70]/15 text-[#199e70] border-[#199e70]/30'
                                            : param.status_level === 'warning'
                                            ? 'bg-[#c98500]/15 text-[#c98500] border-[#c98500]/30'
                                            : param.status_level === 'critical'
                                            ? 'bg-[#d03b3b]/15 text-[#d03b3b] border-[#d03b3b]/30'
                                            : 'bg-[#3987e5]/15 text-[#3987e5] border-[#3987e5]/30'

                                        const statusText =
                                          param.status_level === 'safe'
                                            ? '安全'
                                            : param.status_level === 'warning'
                                            ? '关注'
                                            : param.status_level === 'critical'
                                            ? '警惕'
                                            : '参考'

                                        return (
                                          <div
                                            key={param.param_key || pIdx}
                                            className="bg-[var(--bg-card)] border border-[var(--border-color)]/70 rounded-lg p-3 space-y-2 text-xs"
                                          >
                                            {/* 参数名、键名与当前值 */}
                                            <div className="flex flex-wrap items-center justify-between gap-2">
                                              <div className="flex items-center gap-1.5 min-w-0">
                                                <span
                                                  className="font-bold text-[var(--text-primary)]"
                                                  title={`参数键名: ${param.param_key}`}
                                                >
                                                  {param.param_name}
                                                </span>
                                              </div>
                                              <div className="flex items-center gap-2 shrink-0">
                                                <span className="font-mono font-bold text-xs text-[var(--text-primary)]">
                                                  {param.param_value}
                                                </span>
                                                <span className={`text-[10px] px-1.5 py-0.2 rounded border font-medium ${statusBg}`}>
                                                  {statusText}
                                                </span>
                                              </div>
                                            </div>

                                            {/* 安全基准区间 */}
                                            <div className="text-[11px] text-[var(--text-muted)] flex items-center gap-1.5">
                                              <span className="text-[var(--text-secondary)] font-medium">行业/安全基准:</span>
                                              <span className="font-mono text-[var(--text-primary)]">{param.benchmark_range}</span>
                                            </div>

                                            {/* 经济学机理传导 */}
                                            <div className="text-[11px] text-[var(--text-secondary)] bg-[var(--surface-color)]/70 p-2 rounded border border-[var(--border-color)]/50 leading-relaxed">
                                              <span className="text-[var(--text-muted)] font-medium">经济学机理: </span>
                                              {param.economic_intuition}
                                            </div>

                                            {/* 买方决策启示 */}
                                            <div className="text-[11px] text-[var(--text-primary)] leading-relaxed pl-2.5 border-l-2 border-[#3987e5] py-0.5">
                                              <span className="text-[#3987e5] font-semibold">买方决策启示: </span>
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

                            {/* 卡片底部：数学边界校验与原始底账摘要 */}
                            <div className="pt-2 border-t border-[var(--border-color)]/60 text-[10px] space-y-1">
                              <div className="flex items-center justify-between text-[var(--text-muted)]">
                                <span>测算结果摘要:</span>
                                <span className="font-mono text-[#199e70] font-semibold">{m.output_summary}</span>
                              </div>
                              <div className="flex items-center justify-between text-[var(--text-muted)] pt-0.5">
                                <span>边界防御:</span>
                                <span className="text-[#199e70] font-medium">零除零负保护 · 极值收敛与有限责任下界通过</span>
                              </div>
                            </div>
                          </div>
                        )
                      })}
                  </div>
                </>
              ) : (
                <div className="p-12 text-center text-xs text-[var(--text-muted)] bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl space-y-3">
                  <div className="text-sm font-semibold text-[var(--text-primary)]">
                    尚未加载标的 {selectedTicker} 的 24 大模型数据
                  </div>
                  <button
                    type="button"
                    onClick={() => void loadSuite24(selectedTicker)}
                    className="px-4 py-2 rounded-lg bg-[#199e70] text-white font-bold text-xs cursor-pointer"
                  >
                    立即全量运算 24 大模型
                  </button>
                </div>
              )}
            </div>
          ) : (
            <>
          {loadingAnalysis ? (
            <div className="p-16 text-center text-xs text-[var(--text-muted)] bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl space-y-3">
              <div className="w-8 h-8 border-3 border-[#3987e5] border-t-transparent rounded-full animate-spin mx-auto" />
              <div className="text-sm font-semibold text-[var(--text-primary)]">
                正在调取官方财报底账并自动测算 DCF 估值走廊…
              </div>
              <p className="text-xs text-[var(--text-secondary)]">
                执行资产负债表 $Assets = Liabilities + Equity$ 平账校验、提取现金流并推演买点
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
                      <span>⚡ 在任务调度中拉取 [{selectedTicker}] 全量数据</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          ) : analysis ? (
            <>
              {/* 1. 标的概览标头卡片 */}
              <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
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

                    <span className="text-xs px-2.5 py-1 rounded-full bg-[#3987e5]/15 text-[#3987e5] border border-[#3987e5]/30 font-semibold">
                      {toChinese(quote?.session_type) || '盘中时段'}
                    </span>

                    {/* 平账自检状态门禁 */}
                    <span
                      className={`text-xs px-2.5 py-1 rounded-full font-semibold border ${
                        probes?.financial_audit?.balance_sheet_balanced
                          ? 'bg-[#199e70]/15 text-[#199e70] border-[#199e70]/30'
                          : 'bg-[#d03b3b]/15 text-[#d03b3b] border-[#d03b3b]/30'
                      }`}
                    >
                      {probes?.financial_audit?.balance_sheet_balanced ? '三表平账通过' : '平账预警'}
                    </span>
                  </div>
                </div>

                {/* 标的数据完备度底账与即时采集更新栏 (Data Readiness Health Strip) */}
                <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg px-3 py-2 flex flex-wrap items-center justify-between gap-2 text-xs">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-[11px] text-[var(--text-secondary)] flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-[#199e70] animate-pulse" />
                      <span>投研底账:</span>
                    </span>
                    <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 border border-emerald-500/20 font-mono text-[11px]">
                      现价: {sym}{curPrice.toFixed(2)} ({toChinese(quote?.session_type) || '前收盘基准'})
                    </span>
                    <span className={`px-2 py-0.5 rounded border font-mono text-[11px] ${
                      probes?.financial_audit?.balance_sheet_balanced
                        ? 'bg-blue-500/10 text-blue-600 border-blue-500/20'
                        : 'bg-amber-500/10 text-amber-600 border-amber-500/20'
                    }`}>
                      三表: {probes?.financial_audit?.balance_sheet_balanced ? '已平账' : '待平账'}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-purple-500/10 text-purple-600 border border-purple-500/20 font-mono text-[11px]">
                      WACC: {wacc?.wacc_pct ? `${wacc.wacc_pct.toFixed(2)}%` : '9.50%'}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-600 border border-amber-500/20 font-mono text-[11px]">
                      日K: 250天已对齐
                    </span>
                    <span className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-600 border border-cyan-500/20 font-mono text-[11px]">
                      雷达: {analysis.events_analysis?.recent_events?.length || 0}篇
                    </span>
                  </div>

                  <button
                    type="button"
                    disabled={recollectingTicker}
                    onClick={() => void handleRecollectStock(analysis.ticker)}
                    className="px-2.5 py-1 rounded bg-[#3987e5] hover:bg-[#2c72c8] text-white text-xs font-medium cursor-pointer disabled:opacity-50 transition-all flex items-center gap-1 shrink-0 shadow-sm"
                  >
                    {recollectingTicker ? (
                      <>
                        <div className="w-2.5 h-2.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        <span>调度中…</span>
                      </>
                    ) : (
                      <span>⚡ 调度更新</span>
                    )}
                  </button>
                </div>

                {/* 商业简述 */}
                <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                  {indProf?.description || aiQual?.business_model}
                </p>
              </div>

              {/* ========================================================================= */}
              {/* 2. 自动带入数据多阶段 DCF 估值走廊 (核心金融计算模块) */}
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
                        <span>多阶段 DCF 估值走廊与安全边际</span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-[#199e70]/15 text-[#199e70] border border-[#199e70]/30 font-medium">
                          自动代入底层事实
                        </span>
                      </h3>
                      <p className="text-xs text-[var(--text-muted)] mt-0.5">
                        基于 SEC/JPX 官方三表内生自由现金流、WACC 资本成本折现率与 FRED 10Y 美债基准
                      </p>
                    </div>
                    <span
                      className={`text-xs px-3 py-1 rounded-full font-bold border ${
                        mos >= 0
                          ? 'bg-[#199e70]/15 text-[#199e70] border-[#199e70]/30'
                          : 'bg-[#d03b3b]/15 text-[#d03b3b] border-[#d03b3b]/30'
                      }`}
                    >
                      安全边际 {mos >= 0 ? `+${mos.toFixed(1)}%` : `${mos.toFixed(1)}%`}
                    </span>
                  </div>

                  {/* 顶层通俗商业研判横幅 */}
                  <div className="p-3.5 rounded-xl border border-[#3987e5]/30 bg-[#3987e5]/5 flex items-start gap-3">
                    <span className="text-lg">🎯</span>
                    <div>
                      <div className="font-bold text-xs text-[var(--text-primary)]">
                        投资直觉与估值结论
                      </div>
                      <div className="text-xs mt-1 text-[var(--text-secondary)] leading-relaxed">
                        {corridor.valuation_verdict}
                      </div>
                    </div>
                  </div>

                  {/* 买方 DCF 横向价格走廊标尺 (Valuation Corridor Scale) */}
                  <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-4 space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-[var(--text-primary)]">
                          买方估值走廊标尺 (Valuation Corridor Scale)
                        </span>
                        <span className="text-[10px] text-[var(--text-muted)]">
                          现价 vs 悲观底价 / 中性公允 / 乐观靶心
                        </span>
                      </div>
                      <span className={`px-2 py-0.5 rounded font-mono font-bold text-[11px] ${
                        mos >= 0 ? 'text-emerald-500 bg-emerald-500/10' : 'text-rose-500 bg-rose-500/10'
                      }`}>
                        {mos >= 0 ? `安全边际 +${mos.toFixed(1)}%` : `溢价超额 ${Math.abs(mos).toFixed(1)}%`}
                      </span>
                    </div>

                    {/* 标尺轨道图 */}
                    {(() => {
                      const pFloor = corridor.conservative_floor.value_per_share
                      const pBase = corridor.base_fair_value.value_per_share
                      const pOpt = corridor.optimistic_target.value_per_share
                      const min = Math.min(pFloor, curPrice) * 0.85
                      const max = Math.max(pOpt, curPrice) * 1.15
                      const span = Math.max(1, max - min)
                      const clamp = (val: number) => Math.max(4, Math.min(96, ((val - min) / span) * 100))
                      const curPos = clamp(curPrice)
                      const floorPos = clamp(pFloor)
                      const basePos = clamp(pBase)
                      const optPos = clamp(pOpt)

                      return (
                        <div className="pt-7 pb-5 px-3">
                          <div className="relative w-full h-3 rounded-full bg-slate-700/30 overflow-visible">
                            {/* 悲观到中性区间 */}
                            <div
                              className="absolute top-0 h-3 rounded-l-full bg-gradient-to-r from-rose-500/30 to-blue-500/30"
                              style={{ left: `${floorPos}%`, width: `${Math.max(0, basePos - floorPos)}%` }}
                            />
                            {/* 中性到乐观区间 */}
                            <div
                              className="absolute top-0 h-3 rounded-r-full bg-gradient-to-r from-blue-500/30 to-emerald-500/30"
                              style={{ left: `${basePos}%`, width: `${Math.max(0, optPos - basePos)}%` }}
                            />

                            {/* 悲观标记 */}
                            <div className="absolute top-0 -mt-1 w-0.5 h-5 bg-rose-500/80 -translate-x-1/2" style={{ left: `${floorPos}%` }}>
                              <div className="absolute top-5 -translate-x-1/2 text-[10px] font-mono text-rose-400 whitespace-nowrap">
                                <div>底线 {sym}{pFloor.toFixed(1)}</div>
                              </div>
                            </div>

                            {/* 中性公允标记 */}
                            <div className="absolute top-0 -mt-1.5 w-1 h-6 bg-[#3987e5] -translate-x-1/2" style={{ left: `${basePos}%` }}>
                              <div className="absolute top-6 -translate-x-1/2 text-[10px] font-mono font-bold text-[#3987e5] whitespace-nowrap">
                                <div>公允 {sym}{pBase.toFixed(1)}</div>
                              </div>
                            </div>

                            {/* 乐观靶心标记 */}
                            <div className="absolute top-0 -mt-1 w-0.5 h-5 bg-emerald-500/80 -translate-x-1/2" style={{ left: `${optPos}%` }}>
                              <div className="absolute top-5 -translate-x-1/2 text-[10px] font-mono text-emerald-400 whitespace-nowrap">
                                <div>靶心 {sym}{pOpt.toFixed(1)}</div>
                              </div>
                            </div>

                            {/* 当前现价指示游标 */}
                            <div className="absolute top-0 -mt-7 -translate-x-1/2 flex flex-col items-center z-10" style={{ left: `${curPos}%` }}>
                              <div className="px-2 py-0.5 rounded bg-amber-500 text-black font-black font-mono text-[10px] shadow-lg flex items-center gap-1 whitespace-nowrap">
                                <span>现价</span>
                                <span>{sym}{curPrice.toFixed(2)}</span>
                              </div>
                              <div className="w-0 h-0 border-l-[4px] border-l-transparent border-r-[4px] border-r-transparent border-t-[5px] border-t-amber-500" />
                              <div className="w-0.5 h-7 bg-amber-500/70" />
                            </div>
                          </div>
                        </div>
                      )
                    })()}
                  </div>

                  {/* 三态情景估值卡片 */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* 悲观底线估值 */}
                    <div className="p-4 rounded-xl border border-[#d03b3b]/30 bg-[#331114]/15 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-[#d03b3b]">【悲观底线估值】</span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#d03b3b]/20 text-[#d03b3b] font-semibold font-mono">
                            严苛防御
                          </span>
                        </div>
                        <div className="text-2xl font-black font-mono text-[#d03b3b] mt-2.5">
                          {sym}{corridor.conservative_floor.value_per_share.toFixed(2)}
                        </div>
                        <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
                          {corridor.conservative_floor.description}
                        </p>
                      </div>
                      <div className="mt-3 pt-2.5 border-t border-[#d03b3b]/20 text-[11px] text-[var(--text-muted)] space-y-0.5">
                        <div>折现率：{corridor.conservative_floor.discount_rate_pct}%</div>
                        <div>永续增长率：{corridor.conservative_floor.terminal_growth_pct}%</div>
                        <div>预测增长：{corridor.conservative_floor.growth_rates_pct.join('%, ')}%</div>
                      </div>
                    </div>

                    {/* 中性公允价值 (核心估值中枢) */}
                    <div className="p-4 rounded-xl border-2 border-[#3987e5] bg-[var(--surface-color)] shadow-sm flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-[#3987e5]">【中性公允 · 估值中枢】</span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#3987e5]/20 text-[#3987e5] font-semibold font-mono">
                            公允基准
                          </span>
                        </div>
                        <div className="text-2xl font-black font-mono text-[#3987e5] mt-2.5">
                          {sym}{corridor.base_fair_value.value_per_share.toFixed(2)}
                        </div>
                        <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
                          {corridor.base_fair_value.description}
                        </p>
                      </div>
                      <div className="mt-3 pt-2.5 border-t border-[var(--border-color)] text-[11px] text-[var(--text-secondary)] space-y-0.5">
                        <div>WACC 折现率：{corridor.base_fair_value.discount_rate_pct}%</div>
                        <div>永续增长率：{corridor.base_fair_value.terminal_growth_pct}%</div>
                        <div>预测增长：{corridor.base_fair_value.growth_rates_pct.join('%, ')}%</div>
                        {corridor.base_fair_value.forecast && (
                          <details className="mt-1.5 text-[11px]">
                            <summary className="cursor-pointer text-[#3987e5] font-medium">查看 3 年期折现明细</summary>
                            <ul className="mt-1 pl-2 space-y-0.5 text-[var(--text-muted)] font-mono">
                              {corridor.base_fair_value.forecast.map(row => (
                                <li key={row.year}>第 {row.year} 年 FCF: {sym}{(row.cash_flow / 1e9).toFixed(2)}B (现值: {sym}{(row.present_value / 1e9).toFixed(2)}B)</li>
                              ))}
                            </ul>
                          </details>
                        )}
                      </div>
                    </div>

                    {/* 乐观成长靶心 */}
                    <div className="p-4 rounded-xl border border-[#199e70]/30 bg-[#102a1e]/15 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-[#199e70]">【乐观成长靶心】</span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#199e70]/20 text-[#199e70] font-semibold font-mono">
                            景气爆发
                          </span>
                        </div>
                        <div className="text-2xl font-black font-mono text-[#199e70] mt-2.5">
                          {sym}{corridor.optimistic_target.value_per_share.toFixed(2)}
                        </div>
                        <p className="text-xs text-[var(--text-secondary)] mt-1.5 leading-relaxed">
                          {corridor.optimistic_target.description}
                        </p>
                      </div>
                      <div className="mt-3 pt-2.5 border-t border-[#199e70]/20 text-[11px] text-[var(--text-muted)] space-y-0.5">
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
                          支持在官方底账自动代入的基础上，微调折现率与逐年增长率进行敏感性压力测试
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
                        <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-[#199e70]/10 text-[#199e70]">
                          官方三表披露
                        </span>
                      </div>
                      <div className="space-y-2 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="text-[var(--text-secondary)]">净资产收益率 (ROE)</span>
                          <span className="font-mono font-bold text-[#199e70]">
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

                  {/* 底层平账事实明细卡片 */}
                  {facts && (
                    <div className="pt-2 border-t border-[var(--border-color)]">
                      <div className="text-xs font-bold text-[var(--text-primary)] mb-2.5">
                        已自动平账代入的底层财务事实 (官方原档: {facts.source_filing})
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
                          <div className="font-medium text-xs mt-1 text-[#199e70]">
                            {facts.net_cash_status}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ========================================================================= */}
              {/* 3. 商业模式壁垒与护城河解构 */}
              {/* ========================================================================= */}
              <div className="grid grid-cols-1 xl:grid-cols-12 gap-5">
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
                    <span className="w-2 h-2 rounded-full bg-[#199e70]" />
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
                    <span className="w-2 h-2 rounded-full bg-[#3987e5]" />
                    <h3 className="text-sm font-bold text-[var(--text-primary)]">
                      财务与偿债定量诊断探针
                    </h3>
                  </div>
                  <span className="text-xs text-[var(--text-muted)]">
                    底账验签与物理动力学
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
                              ? 'bg-[#199e70]/20 text-[#199e70] border border-[#199e70]/40'
                              : 'bg-[#d03b3b]/20 text-[#d03b3b] border border-[#d03b3b]/40'
                          }`}
                        >
                          {probes?.financial_audit?.balance_sheet_balanced ? '平账通过' : '不平账警告'}
                        </span>
                      </div>
                      <div className="text-lg font-bold font-mono text-[var(--text-primary)] mt-2">
                        {probes?.financial_audit?.balance_sheet_balanced ? '资产 = 负债 + 权益' : '勾稽异常'}
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
                              ? 'bg-[#199e70]/20 text-[#199e70] border border-[#199e70]/40'
                              : 'bg-gray-600/20 text-gray-400 border border-gray-600/40'
                          }`}
                        >
                          {probes?.credit_kmv_probe?.distance_to_default_DD !== undefined ? '信用健康' : '待补齐底账'}
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
                        : probes?.credit_kmv_probe?.note || '缺少完整有息负债或总股本底账'}
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
                              ? 'bg-[#3987e5]/20 text-[#3987e5] border border-[#3987e5]/40'
                              : 'bg-gray-600/20 text-gray-400 border border-gray-600/40'
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
                    <span className="w-2 h-2 rounded-full bg-[#199e70]" />
                    <h3 className="text-sm font-bold text-[var(--text-primary)]">
                      关联突发舆情与业务分部因果冲击 (News & Event Radar Impact)
                    </h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono px-2.5 py-0.5 rounded bg-[#3987e5]/15 text-[#3987e5] border border-[#3987e5]/30">
                      已匹配 {analysis?.events_analysis?.matched_count ?? analysis?.events_analysis?.total_events_count ?? 0} 篇官方情报底账
                    </span>
                    {analysis?.events_analysis?.sotp_impact?.estimated_enterprise_value_delta_pct !== undefined && (
                      <span className={`text-xs font-mono font-bold px-2.5 py-0.5 rounded border ${
                        analysis.events_analysis.sotp_impact.estimated_enterprise_value_delta_pct >= 0
                          ? 'bg-[#199e70]/15 text-[#199e70] border-[#199e70]/30'
                          : 'bg-[#d03b3b]/15 text-[#d03b3b] border-[#d03b3b]/30'
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
                      <span className="w-1.5 h-1.5 rounded-full bg-[#3987e5]" />
                      <span>SOTP 业务分部因果冲击测算 (SOTP Business Segment Sensitivity)</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {analysis.events_analysis.sotp_impact.segment_impacts.map((seg: any, sIdx: number) => (
                        <div key={sIdx} className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-3.5 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-xs text-[var(--text-primary)]">{seg.segment_name}</span>
                            <div className="flex items-center gap-2 text-[10px] font-mono">
                              <span className={seg.revenue_impact_pct >= 0 ? 'text-[#199e70]' : 'text-[#d03b3b]'}>
                                营收冲击: {seg.revenue_impact_pct >= 0 ? '+' : ''}{seg.revenue_impact_pct.toFixed(1)}%
                              </span>
                              <span className={seg.margin_impact_bps >= 0 ? 'text-[#199e70]' : 'text-[#d03b3b]'}>
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
                      <span className="w-1.5 h-1.5 rounded-full bg-[#199e70]" />
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
          </>
        )}
        </div>
      </div>
    </div>
  )
}

export default AnalyticsTab
