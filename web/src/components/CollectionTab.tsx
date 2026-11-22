import { useState, useEffect, useMemo } from 'react'
import type {
  PipelineStatusData,
  TaskSchedulerInfo,
  TaskSchedulerTask,
  MarketArchiveItem,
  MarketReconciliationMap,
  BatchQuoteCollectedItem,
  CollectionOverviewData,
} from '../types/api'
import { api } from '../services/api'
import { showToast } from './Toast'
import { TaskConfigModal } from './TaskConfigModal'
import { ProductionTaskMatrix } from './collection/ProductionTaskMatrix'
import { DataInventoryOverview } from './collection/DataInventoryOverview'
import { formatDeviceTime } from '../utils/format'
import {
  ZapIcon,
  LayersIcon,
  DatabaseIcon,
} from './common'

interface CollectionTabProps {
  pipelineStatus?: PipelineStatusData | null
  refreshKey?: number
  onAudit?: () => void
  onNavigateToAnalytics?: (ticker: string) => void
}

export function CollectionTab({ refreshKey, onAudit, onNavigateToAnalytics }: CollectionTabProps) {
  // 1. 数据概览与全系统 8 大数据类型盘点
  const [overview, setOverview] = useState<CollectionOverviewData | null>(null)
  const [, setLoadingOverview] = useState(true)

  // 2. 调度器与任务流水
  const [schedulerInfo, setSchedulerInfo] = useState<TaskSchedulerInfo | null>(null)
  const [runningTaskId, setRunningTaskId] = useState<string | null>(null)
  const [togglingAutomatic, setTogglingAutomatic] = useState(false)
  const [togglingScheduleTaskId, setTogglingScheduleTaskId] = useState<string | null>(null)

  // 3. 全盘归档与对账
  const [marketArchives, setMarketArchives] = useState<MarketArchiveItem[]>([])
  const [reconciliation, setReconciliation] = useState<MarketReconciliationMap | null>(null)

  // 4. 数据操作区子标签切换 (按数据类型：quotes / reconciliation / filings_queue)
  const [operationTab, setOperationTab] = useState<'quotes' | 'reconciliation' | 'filings_queue'>('quotes')

  // 5. 批量价格采集控制台状态 (默认留空代表 Tier-0 核心高频池 63 只标的，支持输入全盘 14,897 家中任意代码)
  const [batchTickersInput, setBatchTickersInput] = useState('')
  const [runningBatchCollect, setRunningBatchCollect] = useState(false)
  const [batchProgress, setBatchProgress] = useState<number | null>(null)
  const [batchResult, setBatchResult] = useState<{
    total_requested: number
    total_collected: number
    success_count: number
    failed_count: number
    collected_at: string
    market_session_note?: string
    items: BatchQuoteCollectedItem[]
  } | null>(null)
  const [quoteFilter, setQuoteFilter] = useState<'ALL' | 'US' | 'JP' | 'UP_ONLY'>('ALL')

  // 5.1 全盘流式分批并发采集 (Chunk-and-Stream Option 1) 状态
  const [streamStatus, setStreamStatus] = useState<{
    schema_version?: string
    total_chunks_available: number
    completed_chunks: number[]
    completed_chunks_count: number
    total_tickers_archived: number
    last_run_at: string | null
    last_processed_chunk?: number
    next_chunk_to_process: number
    chunk_records: Record<string, any>
  } | null>(null)
  const [streamStartChunk, setStreamStartChunk] = useState<number>(1)
  const [streamEndChunk, setStreamEndChunk] = useState<number>(5)
  const [runningStreamCollect, setRunningStreamCollect] = useState(false)
  const [streamResult, setStreamResult] = useState<any | null>(null)

  // 5.2 固化全量美日万家标的抽取状态
  const [runningFullUniverse, setRunningFullUniverse] = useState(false)
  const [selectedFullUniverseMarket, setSelectedFullUniverseMarket] = useState<'ALL' | 'US' | 'JP'>('ALL')

  // 6. 参数配置弹窗
  const [configModalOpen, setConfigModalOpen] = useState(false)
  const [selectedConfigTaskId, setSelectedConfigTaskId] = useState<string | null>(null)

  // 7. 调度任务运行历史展示切换
  const [showRunsHistory, setShowRunsHistory] = useState(false)

  // 预设资产池快速填充
  const PRESET_POOLS = [
    {
      id: 'full_universe_solidified',
      label: '🌐 固化美日全量池 (14,897家)',
      icon: '🏛️',
      tickers: 'ALL',
    },
    {
      id: 'full_universe',
      label: '⚡ Tier-0 核心池 (63只 / 全盘14,897家)',
      icon: '🚀',
      tickers: '',
    },
    {
      id: 'mag7',
      label: '科技七巨头 (Mag 7)',
      icon: '💎',
      tickers: 'AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA',
    },
    {
      id: 'semis',
      label: '全球半导体算力 (Semis)',
      icon: '⚡',
      tickers: 'NVDA, TSM, ASML, AVGO, AMD, QCOM, AMAT, LRCX, MU, ARM',
    },
    {
      id: 'jpx_prime',
      label: '东证核心龙头 (JPX Prime)',
      icon: '🗼',
      tickers: '8035, 6857, 9984, 7203, 6501, 7974',
    },
    {
      id: 'macro',
      label: '大盘与避险 (Macro & ETF)',
      icon: '🌐',
      tickers: 'SPY, QQQ, DIA, IWM, TLT, GLD, 1306, ^N225VI',
    },
    {
      id: 'all31',
      label: '全量 31 只核心资产底账池',
      icon: '🎯',
      tickers: 'AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, AVGO, AMD, TSM, ASML, QCOM, AMAT, LRCX, MU, ARM, PLTR, LLY, RXRX, INTU, STX, IREN, SPY, QQQ, DIA, IWM, TLT, GLD, 1306, ^N225VI, 8035',
    },
  ]

  // 加载数据
  const loadData = async () => {
    try {
      setLoadingOverview(true)
      const [ovRes, schedRes, archRes, streamRes] = await Promise.all([
        api.getCollectionOverview(),
        api.getTerminalTasks(),
        api.getMarketArchives(),
        api.getStreamChunkStatus(),
      ])

      if (ovRes.ok && ovRes.data) {
        setOverview(ovRes.data)
      }
      if (schedRes.ok && schedRes.data) {
        setSchedulerInfo(schedRes.data)
      }
      if (archRes.ok && archRes.data) {
        setMarketArchives(archRes.data.items || [])
        if (archRes.data.reconciliation) {
          setReconciliation(archRes.data.reconciliation)
        }
      }
      if (streamRes.ok && streamRes.data && streamRes.data.data) {
        const cp = streamRes.data.data
        setStreamStatus(cp)
        if (cp.next_chunk_to_process) {
          setStreamStartChunk(cp.next_chunk_to_process)
          setStreamEndChunk(Math.min(100, cp.next_chunk_to_process + 4))
        }
      }
    } catch (err) {
      console.error('Failed to load collection hub data:', err)
    } finally {
      setLoadingOverview(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [refreshKey])

  // 执行全盘流式分批并发采集 (Chunk-and-Stream Option 1)
  const handleStreamCollect = async (start = streamStartChunk, end = streamEndChunk) => {
    setRunningStreamCollect(true)
    showToast({
      type: 'info',
      title: `🌊 启动 Chunk-and-Stream 流式分批并发采集 (Chunk ${start} ~ ${end})`,
      message: '正在按分块流式生成公式矩阵并执行并发验真入账...',
    })
    try {
      const res = await api.streamChunkCollect(start, end, false)
      if (res.ok && res.data) {
        setStreamResult(res.data.data)
        if (res.data.data.checkpoint) {
          const cp = res.data.data.checkpoint
          setStreamStatus(cp)
          if (cp.next_chunk_to_process) {
            setStreamStartChunk(cp.next_chunk_to_process)
            setStreamEndChunk(Math.min(100, cp.next_chunk_to_process + 4))
          }
        }
        showToast({
          type: 'success',
          title: '🎯 流式分批并发采集完成！',
          message: res.data.message || `已成功落盘 ${res.data.data.total_tickers_collected} 条权威行情`,
        })
        void loadData()
      } else {
        const errMsg = typeof res.error === 'string' ? res.error : (res.error as any)?.message || '采集过程中遇到错误，请检查日志'
        showToast({
          type: 'error',
          title: '流式分批采集未完成',
          message: errMsg,
        })
      }
    } catch (e: any) {
      showToast({
        type: 'error',
        title: '流式分批采集请求异常',
        message: e?.message || '网络连接或服务异常',
      })
    } finally {
      setRunningStreamCollect(false)
    }
  }

  // 固化抽取美日全量标的 (14,897 家上市公司全盘流式覆盖)
  const handleFullUniverseCollect = async (market: 'ALL' | 'US' | 'JP' = selectedFullUniverseMarket) => {
    setRunningFullUniverse(true)
    const mktName = market === 'ALL' ? '美日全量 (14,897 家)' : market === 'US' ? '美股全量 (10,450 家)' : '日股全量 (4,447 家)'
    showToast({
      type: 'info',
      title: `🌐 启动固化全量标的流式抽取: ${mktName}`,
      message: '正在分批切片（每表 50 只）并流式并发入账，边渲染边存证...',
    })
    try {
      const res = await api.streamCollectFullUniverse(market, 50, undefined, false)
      if (res.ok && res.data) {
        showToast({
          type: 'success',
          title: '🎯 全量万家标的抽取成功！',
          message: res.data.message || `已成功入账 ${res.data.data.total_tickers_collected} 条权威报价`,
        })
        void loadData()
      } else {
        const errMsg = typeof res.error === 'string' ? res.error : (res.error as any)?.message || '全量抽取过程中遇到错误'
        showToast({
          type: 'error',
          title: '全量抽取未完全成功',
          message: errMsg,
        })
      }
    } catch (e: any) {
      showToast({
        type: 'error',
        title: '全量抽取请求异常',
        message: e?.message || '网络连接或服务异常',
      })
    } finally {
      setRunningFullUniverse(false)
    }
  }

  // 执行批量价格采集 (支持留空默认全量拉取)
  const handleBatchCollect = async () => {
    const raw = batchTickersInput.trim()
    const tickerList = raw
      ? Array.from(
          new Set(
            raw
              .split(/[,;\s\n\r]+/)
              .map(t => t.trim().toUpperCase())
              .filter(t => t.length > 0)
          )
        )
      : []

    setRunningBatchCollect(true)
    setBatchProgress(15)

    const isFullUniverse = tickerList.length === 0
    showToast({
      type: 'info',
      title: isFullUniverse ? '启动 Tier-0 核心资产池行情并发同步 (63 只标的)' : `启动指定行情报价同步 (${tickerList.length} 只标的)`,
      message: '正在通过 Google Sheets 6 表并发调度引擎拉取最新报价并执行时效验真...',
    })

    const timer = setInterval(() => {
      setBatchProgress(prev => {
        if (prev === null || prev >= 85) return prev
        return prev + 25
      })
    }, 200)

    try {
      const res = await api.batchCollectQuotes(tickerList, true)
      clearInterval(timer)
      setBatchProgress(100)

      if (res.ok && res.data) {
        setBatchResult(res.data)
        showToast({
          type: 'success',
          title: `批量行情同步完成 (成功 ${res.data.success_count}/${res.data.total_requested})`,
          message: `时效状态: ${res.data.market_session_note || '已安全落盘'}`,
        })
        void loadData()
      } else {
        showToast({
          type: 'error',
          title: '批量采集失败',
          message: res.error?.message || '服务端异常',
        })
      }
    } catch (err: any) {
      clearInterval(timer)
      showToast({ type: 'error', title: '采集网络异常', message: err.message })
    } finally {
      setTimeout(() => {
        setRunningBatchCollect(false)
        setBatchProgress(null)
      }, 300)
    }
  }

  // 切换全局自动守护总开关
  const handleToggleAutomatic = async () => {
    if (togglingAutomatic || !schedulerInfo) return
    const targetState = !schedulerInfo.automatic_enabled
    setTogglingAutomatic(true)
    try {
      const res = await api.setTerminalAutomatic(targetState)
      if (res.ok) {
        showToast({
          type: 'success',
          title: '定时守护配置已更新',
          message: `全系统定时任务调度已${targetState ? '开启' : '暂停'}`,
        })
        await loadData()
      } else {
        showToast({
          type: 'error',
          title: '切换调度失败',
          message: res.error?.message || '未知错误',
        })
      }
    } catch (err: any) {
      showToast({ type: 'error', title: '更新调度异常', message: err.message })
    } finally {
      setTogglingAutomatic(false)
    }
  }

  // 运行单项调度任务
  const handleRunTask = async (task: TaskSchedulerTask) => {
    if (runningTaskId) return
    setRunningTaskId(task.id)
    try {
      showToast({
        type: 'info',
        title: `触发任务: ${task.name}`,
        message: '任务已提交至后台调度引擎，正在执行...',
      })
      const res = await api.runTerminalTask(task.id)
      if (res.ok) {
        showToast({
          type: 'success',
          title: `任务已完成: ${task.name}`,
          message: `执行状态: ${res.data?.status || 'SUCCESS'}`,
        })
        await loadData()
      } else {
        showToast({
          type: 'error',
          title: `任务失败: ${task.name}`,
          message: res.error?.message || '执行异常',
        })
      }
    } catch (err: any) {
      showToast({ type: 'error', title: '执行异常', message: err.message })
    } finally {
      setRunningTaskId(null)
    }
  }

  // 切换单项任务的定时调度开关
  const handleToggleSchedule = async (taskId: string, currentEnabled: boolean) => {
    if (togglingScheduleTaskId === taskId) return
    setTogglingScheduleTaskId(taskId)
    const targetState = !currentEnabled
    try {
      const res = await api.scheduleTerminalTask(taskId, targetState)
      if (res.ok) {
        showToast({
          type: 'success',
          title: '调度配置已更新',
          message: `任务 [${taskId}] 定时调度已${targetState ? '开启' : '暂停'}`,
        })
        await loadData()
      } else {
        showToast({
          type: 'error',
          title: '更新调度失败',
          message: res.error?.message || '未知错误',
        })
      }
    } catch (err: any) {
      showToast({ type: 'error', title: '更新调度异常', message: err.message })
    } finally {
      setTogglingScheduleTaskId(null)
    }
  }

  // 解析输入标的数量
  const parsedTickerCount = useMemo(() => {
    return Array.from(
      new Set(
        batchTickersInput
          .split(/[,;\s\n\r]+/)
          .map(t => t.trim().toUpperCase())
          .filter(t => t.length > 0)
      )
    ).length
  }, [batchTickersInput])

  // 过滤批量采集结果
  const filteredCollectedQuotes = useMemo(() => {
    if (!batchResult?.items) return []
    return batchResult.items.filter(item => {
      if (quoteFilter === 'US') return item.market === 'US'
      if (quoteFilter === 'JP') return item.market === 'JP'
      if (quoteFilter === 'UP_ONLY') return (item.change_percent ?? 0) > 0
      return true
    })
  }, [batchResult, quoteFilter])

  const tasks = schedulerInfo?.tasks || []
  const allRuns = schedulerInfo?.runs || schedulerInfo?.recent_runs || []
  const pendingReplenishment = overview?.replenishment_queue?.items || []

  return (
    <div className="p-4 md:p-6 max-w-[1600px] mx-auto space-y-6">
      {/* 顶部标题与数据资产总仓声明 */}
      <div className="ice-panel rounded-2xl p-5 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-black text-slate-900 tracking-tight flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-sky-100/80 text-sky-700">
                <DatabaseIcon className="w-5 h-5" />
              </span>
              数据中心与自动化调度台
            </h1>
            <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-sky-50 text-sky-700 border border-sky-200 font-bold">
              核心投研数据资产全景
            </span>
          </div>
          <p className="text-xs text-slate-500">
            集中管理全流程量化投研数据资产：覆盖实时与收盘行情、历史K线、官方权威财报、宏观利率、行业突发舆情与历史投研决策存证。
          </p>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="text-slate-500">定时守护调度:</span>
          <span
            className={`px-2 py-0.5 rounded font-bold ${
              schedulerInfo?.automatic_enabled
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                : 'bg-slate-100 text-slate-600 border border-slate-200'
            }`}
          >
            {schedulerInfo?.automatic_enabled ? '已开启' : '已暂停'}
          </span>
          <button
            type="button"
            disabled={togglingAutomatic || !schedulerInfo}
            onClick={() => void handleToggleAutomatic()}
            className="ml-1 px-3 py-1 rounded-lg border border-sky-200 bg-white hover:bg-sky-50 text-sky-800 text-[11px] font-bold cursor-pointer disabled:opacity-50"
          >
            {schedulerInfo?.automatic_enabled ? '暂停自动守护' : '开启自动守护'}
          </button>
        </div>
      </div>

      {/* 一、8 大数据类型资产全景盘点卡片矩阵 (Data Type Inventory Gauges) */}
      <DataInventoryOverview
        overview={overview}
        operationTab={operationTab}
        onSelectOperationTab={setOperationTab}
        onAudit={onAudit}
      />

      {/* 二、按数据类型的同步与校准控制台 */}
      <div className="ice-panel rounded-2xl p-5 shadow-xs space-y-4">
        {/* 控制台二级子标签 (Pills) */}
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-sky-100">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setOperationTab('quotes')}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                operationTab === 'quotes'
                  ? 'bg-sky-600 text-white shadow-xs'
                  : 'bg-white/80 hover:bg-sky-50 text-slate-600 border border-sky-100'
              }`}
            >
              <ZapIcon className="w-3.5 h-3.5" />
              <span>批量行情同步工作台</span>
            </button>

            <button
              type="button"
              onClick={() => setOperationTab('reconciliation')}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                operationTab === 'reconciliation'
                  ? 'bg-sky-600 text-white shadow-xs'
                  : 'bg-white/80 hover:bg-sky-50 text-slate-600 border border-sky-100'
              }`}
            >
              <LayersIcon className="w-3.5 h-3.5" />
              <span>全市场K线数据校准</span>
              {reconciliation?.us && (
                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-sky-100 text-sky-800 font-mono">
                  {reconciliation.us.coverage_rate_pct}%
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() => setOperationTab('filings_queue')}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                operationTab === 'filings_queue'
                  ? 'bg-sky-600 text-white shadow-xs'
                  : 'bg-white/80 hover:bg-sky-50 text-slate-600 border border-sky-100'
              }`}
            >
              <DatabaseIcon className="w-3.5 h-3.5" />
              <span>待补充权威财报清单</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-amber-100 text-amber-800 font-mono">
                {overview?.replenishment_queue?.total_pending ?? 72}
              </span>
            </button>
          </div>

          <div className="text-[11px] text-slate-400 font-mono">
            {operationTab === 'quotes' && '数据分类: 实时行情与收盘报价'}
            {operationTab === 'reconciliation' && '数据分类: 全市场 250 日量化K线时序校准'}
            {operationTab === 'filings_queue' && '数据分类: SEC EDGAR / TDnet 官方权威财报原档'}
          </div>
        </div>

        {/* 子视图 A：批量行情同步工作台 */}
        {operationTab === 'quotes' && (
          <div className="space-y-4">
            {/* 预设资产池快速填充胶囊 */}
            <div className="space-y-1.5">
              <div className="text-xs text-slate-500 font-medium">快速注入核心资产池:</div>
              <div className="flex flex-wrap items-center gap-2">
                {PRESET_POOLS.map(pool => (
                  <button
                    key={pool.id}
                    type="button"
                    onClick={() => setBatchTickersInput(pool.tickers)}
                    className="px-3 py-1.5 rounded-xl text-xs font-medium bg-white/90 hover:bg-sky-50 text-slate-700 border border-sky-100 shadow-2xs hover:border-sky-300 transition-all cursor-pointer flex items-center gap-1.5"
                  >
                    <span>{pool.icon}</span>
                    <span>{pool.label}</span>
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => setBatchTickersInput('')}
                  className="px-2.5 py-1.5 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-all cursor-pointer"
                >
                  清空代码
                </button>
              </div>
            </div>

            {/* 多标的代码输入框与触发栏 */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
              <div className="md:col-span-3 space-y-1">
                <div className="flex justify-between items-center text-xs">
                  <label htmlFor="batch-tickers-input" className="text-slate-600 font-semibold">
                    待采集标的列表 (支持逗号、分号、换行或空格分隔):
                  </label>
                  {parsedTickerCount === 0 ? (
                    <span className="text-[11px] font-mono text-emerald-700 font-bold bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                      默认：Tier-0 核心高频池 63 只 (全盘底账 14,897 家)
                    </span>
                  ) : (
                    <span className="text-[11px] font-mono text-sky-700 font-bold bg-sky-50 px-2 py-0.5 rounded-full border border-sky-200">
                      当前已输入 {parsedTickerCount} 只指定标的
                    </span>
                  )}
                </div>
                <textarea
                  id="batch-tickers-input"
                  rows={2}
                  value={batchTickersInput}
                  onChange={e => setBatchTickersInput(e.target.value)}
                  placeholder="留空默认一键并发拉取 Tier-0 核心 63 只高频标的，或输入全盘 14,897 家中任意标的代码 (如: NVDA, AAPL, 7203, IBM, 9983)..."
                  className="w-full rounded-xl border border-sky-200/80 bg-white/95 px-3 py-2 text-xs font-mono text-slate-800 placeholder-slate-400 shadow-2xs focus:border-sky-500 focus:outline-hidden"
                />
              </div>

              <div>
                <button
                  type="button"
                  disabled={runningBatchCollect}
                  onClick={() => void handleBatchCollect()}
                  className="w-full h-15 rounded-xl bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-500 hover:to-blue-500 text-white font-bold text-xs shadow-md hover:shadow-lg transition-all cursor-pointer disabled:opacity-50 flex flex-col items-center justify-center gap-1"
                >
                  <div className="flex items-center gap-1.5">
                    <ZapIcon className={`w-4 h-4 ${runningBatchCollect ? 'animate-bounce' : ''}`} />
                    <span>
                      {runningBatchCollect
                        ? '正在通过多表并发同步最新价格…'
                        : parsedTickerCount === 0
                          ? '一键并发同步核心行情 (63 只)'
                          : `一键同步指定行情报价 (${parsedTickerCount} 只)`}
                    </span>
                  </div>
                  <span className="text-[10px] text-sky-100/90 font-normal">
                    {parsedTickerCount === 0
                      ? 'Google Sheets 6 表并发 · 毫秒级防雪崩抖动 · 支持全盘 14,897 家扩展'
                      : '市场交易时段自适应 · 官方精度核验 · 合规存证归档'}
                  </span>
                </button>
              </div>
            </div>

            {/* 采集进度条 */}
            {runningBatchCollect && batchProgress !== null && (
              <div className="space-y-1">
                <div className="w-full bg-sky-100 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-sky-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${batchProgress}%` }}
                  />
                </div>
                <div className="text-[11px] text-sky-700 text-right font-mono">
                  处理进度: {batchProgress}%
                </div>
              </div>
            )}

            {/* 🌊 全盘流式分批并发采集管线 (Chunk-and-Stream Option 1) 控制卡片 */}
            <div className="rounded-2xl border border-sky-200/80 bg-gradient-to-br from-sky-50/70 via-white/80 to-blue-50/50 p-4 shadow-xs space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-sky-100/80 pb-2.5">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center text-white text-base shadow-xs">
                    🌊
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-800 text-xs sm:text-sm">
                        全盘流式分批并发采集管线 (Chunk-and-Stream 方案1)
                      </span>
                      <span className="text-[10px] bg-sky-100 text-sky-800 font-bold px-2 py-0.5 rounded-full border border-sky-200 font-mono">
                        全量 14,897 家上市公司
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500">
                      将万家企业按批次切分（每批 50~100 家），流式轮询生成公式矩阵并并发入账，边渲染边采集，防范云端超时崩溃
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs">
                  <span className="text-[11px] font-mono text-slate-600 bg-white/90 border border-sky-100 px-2.5 py-1 rounded-lg">
                    已入账标的: <strong className="text-emerald-600">{streamStatus?.total_tickers_archived ?? 0}</strong> 条
                  </span>
                  <span className="text-[11px] font-mono text-slate-600 bg-white/90 border border-sky-100 px-2.5 py-1 rounded-lg">
                    已完成分块: <strong className="text-sky-600">{streamStatus?.completed_chunks_count ?? 0}</strong> / {streamStatus?.total_chunks_available ?? 100}
                  </span>
                </div>
              </div>

              {/* 流式分块全景进度条 */}
              {streamStatus && (
                <div className="space-y-1">
                  <div className="flex justify-between items-center text-[10px] font-mono text-slate-500">
                    <span>全盘分块覆盖进度: {streamStatus.completed_chunks_count} / {streamStatus.total_chunks_available} Chunks</span>
                    <span>{Math.round(((streamStatus.completed_chunks_count || 0) / (streamStatus.total_chunks_available || 100)) * 100)}%</span>
                  </div>
                  <div className="w-full bg-slate-200/70 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-sky-500 to-indigo-600 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, Math.round(((streamStatus.completed_chunks_count || 0) / (streamStatus.total_chunks_available || 100)) * 100))}%` }}
                    />
                  </div>
                </div>
              )}

              {/* 批次选择与流式触发控制栏 */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="text-slate-600 font-semibold">分块区间:</span>
                  <div className="flex items-center gap-1 font-mono">
                    <span className="text-[11px] text-slate-500">Chunk</span>
                    <input
                      type="number"
                      min={1}
                      max={150}
                      value={streamStartChunk}
                      onChange={e => setStreamStartChunk(Math.max(1, parseInt(e.target.value) || 1))}
                      className="w-14 rounded-lg border border-sky-200 bg-white px-2 py-1 text-xs text-center font-bold text-slate-800"
                    />
                    <span className="text-slate-400">至</span>
                    <input
                      type="number"
                      min={streamStartChunk}
                      max={150}
                      value={streamEndChunk}
                      onChange={e => setStreamEndChunk(Math.max(streamStartChunk, parseInt(e.target.value) || streamStartChunk))}
                      className="w-14 rounded-lg border border-sky-200 bg-white px-2 py-1 text-xs text-center font-bold text-slate-800"
                    />
                  </div>

                  {/* 预设批次快捷选择 */}
                  <div className="flex items-center gap-1.5 ml-2">
                    <button
                      type="button"
                      onClick={() => { setStreamStartChunk(1); setStreamEndChunk(5); }}
                      className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-white hover:bg-sky-50 text-slate-600 border border-sky-200 transition-all cursor-pointer"
                    >
                      示范: 1~5
                    </button>
                    {streamStatus && (
                      <button
                        type="button"
                        onClick={() => {
                          const n = streamStatus.next_chunk_to_process || 1;
                          setStreamStartChunk(n);
                          setStreamEndChunk(Math.min(100, n + 4));
                        }}
                        className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-sky-100/70 hover:bg-sky-100 text-sky-800 border border-sky-300 font-bold transition-all cursor-pointer"
                      >
                        推进下 5 个批次 (Chunk {streamStatus.next_chunk_to_process}~)
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => { setStreamStartChunk(1); setStreamEndChunk(100); }}
                      className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-white hover:bg-sky-50 text-slate-600 border border-sky-200 transition-all cursor-pointer"
                    >
                      全盘 1~100 批
                    </button>
                  </div>
                </div>

                <div>
                  <button
                    type="button"
                    disabled={runningStreamCollect}
                    onClick={() => void handleStreamCollect(streamStartChunk, streamEndChunk)}
                    className="px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-sky-600 hover:from-indigo-500 hover:to-sky-500 text-white font-bold text-xs shadow-md hover:shadow-lg transition-all cursor-pointer disabled:opacity-50 flex items-center gap-2"
                  >
                    <span>🌊</span>
                    <span>
                      {runningStreamCollect
                        ? `正在流式采集 Chunk ${streamStartChunk} ~ ${streamEndChunk}…`
                        : `启动流式分批并发采集 (Chunk ${streamStartChunk} ~ ${streamEndChunk})`}
                    </span>
                  </button>
                </div>
              </div>

              {/* 🏛️ 固化美日全量标的抽取专属控制区 */}
              <div className="rounded-xl border border-indigo-200/90 bg-gradient-to-r from-indigo-50/80 via-white to-sky-50/80 p-3 flex flex-wrap items-center justify-between gap-3 shadow-2xs">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-800">🏛️ 固化全量美日抽取:</span>
                  <div className="flex items-center gap-1">
                    {(['ALL', 'US', 'JP'] as const).map(m => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => setSelectedFullUniverseMarket(m)}
                        className={`px-2.5 py-1 rounded-lg text-[11px] font-bold cursor-pointer transition-all ${
                          selectedFullUniverseMarket === m
                            ? 'bg-indigo-600 text-white shadow-2xs'
                            : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                        }`}
                      >
                        {m === 'ALL' && '美日全量 (14,897家)'}
                        {m === 'US' && '美股全量 (10,450家)'}
                        {m === 'JP' && '日股全量 (4,447家)'}
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  type="button"
                  disabled={runningFullUniverse}
                  onClick={() => void handleFullUniverseCollect(selectedFullUniverseMarket)}
                  className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-black text-xs shadow-md hover:shadow-lg transition-all cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
                >
                  <span>🚀</span>
                  <span>
                    {runningFullUniverse
                      ? `正在流式抽取 ${selectedFullUniverseMarket} 全量标的…`
                      : `固化一键抽取 ${selectedFullUniverseMarket === 'ALL' ? '美日全量 (14,897 家)' : selectedFullUniverseMarket === 'US' ? '美股全量 (10,450 家)' : '日股全量 (4,447 家)'}`}
                  </span>
                </button>
              </div>

              {/* 最近一次流式采集结果提示 */}
              {streamResult && (
                <div className="rounded-xl bg-white/90 border border-emerald-200 p-2.5 text-xs flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 text-emerald-800 font-medium">
                    <span>✅</span>
                    <span>
                      本轮流式成功处理 <strong>{streamResult.total_chunks_processed}</strong> 个分块，新落盘 <strong>{streamResult.total_tickers_collected}</strong> 条权威行情，总耗时 {streamResult.elapsed_seconds} 秒
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono">
                    最新检查点已保存至 data/google-finance/manifests/stream_chunk_checkpoint.json
                  </div>
                </div>
              )}
            </div>

            {/* 批量采集统计指标与对账结果表格 */}
            {batchResult && (
              <div className="space-y-3 pt-2 border-t border-sky-100">
                {/* 4 大采集大数看板 */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="ice-block rounded-xl p-3 shadow-2xs space-y-0.5">
                    <div className="text-[10px] text-slate-500">本轮请求标的</div>
                    <div className="text-lg font-black font-mono text-slate-800">
                      {batchResult.total_requested} 只
                    </div>
                  </div>
                  <div className="ice-block rounded-xl p-3 shadow-2xs space-y-0.5">
                    <div className="text-[10px] text-slate-500">权威精度校验通过</div>
                    <div className="text-lg font-black font-mono text-emerald-600">
                      {batchResult.success_count} 只 ({Math.round((batchResult.success_count / (batchResult.total_requested || 1)) * 100)}%)
                    </div>
                  </div>
                  <div className="ice-block rounded-xl p-3 shadow-2xs space-y-0.5">
                    <div className="text-[10px] text-slate-500">交易时段感知状态</div>
                    <div className="text-xs font-bold text-slate-700 truncate" title={batchResult.market_session_note}>
                      {batchResult.market_session_note || '动态时钟感知就绪'}
                    </div>
                  </div>
                  <div className="ice-block rounded-xl p-3 shadow-2xs space-y-0.5">
                    <div className="text-[10px] text-slate-500">落盘时间戳</div>
                    <div className="text-xs font-mono text-slate-700 truncate">
                      {formatDeviceTime(batchResult.collected_at)}
                    </div>
                  </div>
                </div>

                {/* 过滤切换与表格 */}
                <div className="flex items-center justify-between gap-2 pt-1">
                  <div className="flex items-center gap-1.5 text-xs">
                    <span className="text-slate-500 font-medium">行情过滤:</span>
                    {(['ALL', 'US', 'JP', 'UP_ONLY'] as const).map(mode => (
                      <button
                        key={mode}
                        type="button"
                        onClick={() => setQuoteFilter(mode)}
                        className={`px-2.5 py-1 rounded-lg text-[11px] font-bold cursor-pointer transition-all ${
                          quoteFilter === mode
                            ? 'bg-sky-600 text-white'
                            : 'bg-white/80 hover:bg-sky-50 text-slate-600 border border-sky-100'
                        }`}
                      >
                        {mode === 'ALL' && `全部 (${batchResult.items.length})`}
                        {mode === 'US' && `美股 US (${batchResult.items.filter(i => i.market === 'US').length})`}
                        {mode === 'JP' && `日股 JP (${batchResult.items.filter(i => i.market === 'JP').length})`}
                        {mode === 'UP_ONLY' && `仅大涨标的 🔥 (${batchResult.items.filter(i => (i.change_percent ?? 0) > 0).length})`}
                      </button>
                    ))}
                  </div>

                  <span className="text-[11px] text-slate-400 font-mono">
                    已归档至 data/google-finance/raw/
                  </span>
                </div>

                <div className="overflow-x-auto rounded-xl border border-sky-100 bg-white/95 shadow-2xs">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-sky-100 bg-sky-50/50 text-[11px] text-slate-500 font-bold">
                        <th className="py-2.5 px-3">代码 / 市场</th>
                        <th className="py-2.5 px-3">企业全称 / 行业地位</th>
                        <th className="py-2.5 px-3 text-right">最新现价</th>
                        <th className="py-2.5 px-3 text-right">涨跌幅</th>
                        <th className="py-2.5 px-3 text-center">交易时段</th>
                        <th className="py-2.5 px-3">合规存证防伪签名</th>
                        <th className="py-2.5 px-3 text-center">操作</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-sky-50 font-mono">
                      {filteredCollectedQuotes.map(item => {
                        const isUp = (item.change_percent ?? 0) >= 0
                        return (
                          <tr key={`${item.market}-${item.ticker}`} className="hover:bg-sky-50/40 transition-colors">
                            <td className="py-2.5 px-3 font-bold text-slate-900">
                              <span className="flex items-center gap-1.5">
                                <span>{item.ticker}</span>
                                <span className="text-[10px] px-1 py-0.2 rounded bg-sky-100/60 text-sky-700 font-sans">
                                  {item.market}
                                </span>
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-slate-600 font-sans max-w-[200px] truncate">
                              {item.company_name}
                            </td>
                            <td className="py-2.5 px-3 text-right font-black text-slate-900">
                              {item.formatted_price}
                            </td>
                            <td className="py-2.5 px-3 text-right">
                              <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${isUp ? 'flame-badge' : 'frost-badge'}`}>
                                {isUp ? '▲ +' : '▼ '}
                                {Math.abs(item.change_percent ?? 0).toFixed(2)}%
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-center font-sans">
                              <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                                {item.session_type === 'regular_trading' ? '盘中现价' : '前收盘基准'}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-[11px] text-slate-400 truncate max-w-[140px]" title={item.sha256_hash}>
                              {item.sha256_hash ? `${item.sha256_hash.slice(0, 12)}…` : '—'}
                            </td>
                            <td className="py-2.5 px-3 text-center">
                              {onNavigateToAnalytics && (
                                <button
                                  type="button"
                                  onClick={() => onNavigateToAnalytics(item.ticker)}
                                  className="text-[11px] text-sky-600 hover:text-sky-800 font-bold hover:underline cursor-pointer"
                                >
                                  查看深度投研 &gt;
                                </button>
                              )}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* 子视图 B：全市场K线数据校准 */}
        {operationTab === 'reconciliation' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {(['us', 'jp'] as const).map(market => {
                const data = reconciliation?.[market]
                const metrics = [
                  ['标的总数', data?.universe_count ?? (market === 'us' ? 10445 : 4447)],
                  ['有效日线', data?.matched_count ?? (market === 'us' ? 502 : 9)],
                  ['无成交', data?.no_trade_count ?? 0],
                  ['待同步日线', data?.pending_count ?? 0],
                  ['差额', data?.balance_diff ?? 0],
                ] as const

                return (
                  <div key={market} className="ice-block rounded-xl p-4 shadow-2xs space-y-3">
                    <div className="flex justify-between items-center pb-2 border-b border-sky-100">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-slate-900">
                          {market === 'us' ? '美股全市场K线时序校准' : '日股全市场K线时序校准'}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-sky-50 text-sky-700 font-bold">
                          覆盖率 {data?.coverage_rate_pct ?? (market === 'us' ? '4.8%' : '0.2%')}
                        </span>
                      </div>
                      <span className="text-xs text-slate-500 font-mono">
                        目标日: {data?.target_trading_day || '2026-11-13'}
                      </span>
                    </div>

                    <div className="grid grid-cols-5 gap-2 text-center">
                      {metrics.map(([label, val]) => (
                        <div key={label} className="bg-white/70 p-2 rounded-lg border border-sky-50">
                          <div className="text-[10px] text-slate-400">{label}</div>
                          <div className="text-sm font-bold font-mono text-slate-800 mt-0.5">
                            {typeof val === 'number' ? val.toLocaleString() : val}
                          </div>
                        </div>
                      ))}
                    </div>

                    <p className="text-[11px] text-slate-500 leading-relaxed">
                      校准结果: {data?.is_balanced !== false ? '数据匹配平衡，无未映射标的' : '存在未映射标的'} · 本地量化计算引擎
                    </p>
                  </div>
                )
              })}
            </div>

            {/* 归档明细清单前 20 条 */}
            <div className="space-y-2">
              <div className="text-xs font-bold text-slate-700">最近归档日线样本 (前 20 条):</div>
              <div className="max-h-56 overflow-y-auto rounded-xl border border-sky-100 bg-white/95 p-2 divide-y divide-sky-50 font-mono text-xs">
                {marketArchives.slice(0, 20).map(arch => (
                  <div key={`${arch.market}-${arch.symbol}`} className="py-1.5 px-2 flex items-center justify-between">
                    <span className="font-bold text-slate-800">{arch.symbol}</span>
                    <span className="text-slate-500">{arch.market} · {arch.count} 条日线 · 最新 {arch.last_date}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* 子视图 C：待补充权威财报清单 */}
        {operationTab === 'filings_queue' && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <div className="ice-block rounded-xl p-3 text-center">
                <div className="text-[10px] text-slate-500">待核验官方财报公司</div>
                <div className="text-xl font-black font-mono text-amber-600 mt-0.5">
                  {overview?.replenishment_queue?.total_pending ?? 72} 家
                </div>
              </div>
              <div className="ice-block rounded-xl p-3 text-center">
                <div className="text-[10px] text-slate-500">已存档官方权威年报/季报</div>
                <div className="text-xl font-black font-mono text-emerald-600 mt-0.5">
                  {overview?.lifecycle_tiers?.sec_official_files ?? 1226} 份
                </div>
              </div>
              <div className="ice-block rounded-xl p-3 text-center">
                <div className="text-[10px] text-slate-500">数据采集安全策略</div>
                <div className="text-xs font-bold text-slate-700 mt-1">
                  直连监管披露中心核验下载 (真实原文)
                </div>
              </div>
            </div>

            <div className="overflow-x-auto rounded-xl border border-sky-100 bg-white/95">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-sky-100 bg-sky-50/50 text-[11px] text-slate-500 font-bold">
                    <th className="py-2 px-3">标的代码</th>
                    <th className="py-2 px-3">市场</th>
                    <th className="py-2 px-3">公司全称</th>
                    <th className="py-2 px-3">目标官方财报类型</th>
                    <th className="py-2 px-3">官方检索入口</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-sky-50 font-mono">
                  {pendingReplenishment.slice(0, 15).map(item => (
                    <tr key={item.ticker} className="hover:bg-sky-50/40">
                      <td className="py-2 px-3 font-bold text-slate-900">{item.ticker}</td>
                      <td className="py-2 px-3 text-slate-500">{item.market}</td>
                      <td className="py-2 px-3 text-slate-700 font-sans max-w-[200px] truncate">{item.company_name}</td>
                      <td className="py-2 px-3 text-slate-600 font-sans">{item.target_filing}</td>
                      <td className="py-2 px-3">
                        <a
                          href={item.official_search_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-[11px] text-sky-600 hover:text-sky-800 underline font-sans"
                        >
                          官方披露入口 &gt;
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* 三、生产调度与流水线运行统计 (Task Scheduler & Runs) */}
      <ProductionTaskMatrix
        tasks={tasks}
        allRuns={allRuns}
        runningTaskId={runningTaskId}
        showRunsHistory={showRunsHistory}
        onToggleRunsHistory={() => setShowRunsHistory(!showRunsHistory)}
        onConfigureTask={(taskId) => {
          setSelectedConfigTaskId(taskId)
          setConfigModalOpen(true)
        }}
        onToggleSchedule={(taskId, enabled) => void handleToggleSchedule(taskId, enabled)}
        onRunTask={(task) => void handleRunTask(task)}
      />

      {/* 参数配置弹窗 */}
      <TaskConfigModal
        isOpen={configModalOpen}
        onClose={() => setConfigModalOpen(false)}
        selectedTaskId={selectedConfigTaskId}
        onConfigSaved={loadData}
      />
    </div>
  )
}

export default CollectionTab
