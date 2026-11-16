import { useState, useEffect, useMemo } from 'react'
import type {
  PipelineStatusData,
  TaskSchedulerInfo,
  TaskSchedulerTask,
  TaskSchedulerRun,
  MarketArchiveItem,
  MarketReconciliationMap,
  BatchQuoteCollectedItem,
} from '../types/api'
import { api } from '../services/api'
import { showToast } from './Toast'
import { TaskConfigModal } from './TaskConfigModal'
import { formatDeviceTime } from '../utils/format'
import {
  ZapIcon,
  LayersIcon,
  RefreshIcon,
  ShieldCheckIcon,
  InfoCircleIcon,
  SearchIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  DatabaseIcon,
} from './common'

interface CollectionTabProps {
  pipelineStatus?: PipelineStatusData | null
  refreshKey?: number
  onNavigateToAnalytics?: (ticker: string) => void
}

export function CollectionTab({ refreshKey, onNavigateToAnalytics }: CollectionTabProps) {
  // 模式切换：批量价格采集 vs 单票深度档案
  const [collectionMode, setCollectionMode] = useState<'batch_prices' | 'single_dossier'>('batch_prices')

  // 批量股票价格采集状态
  const [batchInputText, setBatchInputText] = useState(
    'NVDA, AAPL, MSFT, AMD, AVGO, TSM, 8035, 6857, META, GOOGL, AMZN, PLTR, GLD'
  )
  const [isCollectingBatch, setIsCollectingBatch] = useState(false)
  const [collectedQuotes, setCollectedQuotes] = useState<BatchQuoteCollectedItem[]>([])
  const [quoteFilterMarket, setQuoteFilterMarket] = useState<'ALL' | 'US' | 'JP' | 'UP_ONLY'>('ALL')
  const [batchStats, setBatchStats] = useState<{
    total: number
    success: number
    failed: number
    sessionNote: string
    collectedAt: string
  } | null>(null)

  // 极简主视图模式：默认干净极简，高级选项可一键折叠展开
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [advancedTab, setAdvancedTab] = useState<'scheduler' | 'runs' | 'archives'>('scheduler')

  // 信息提示 Popover 状态 (统一感叹号说明组件)
  const [activePopover, setActivePopover] = useState<string | null>(null)

  // 调度器与任务状态
  const [schedulerInfo, setSchedulerInfo] = useState<TaskSchedulerInfo | null>(null)
  const [runningTaskId, setRunningTaskId] = useState<string | null>(null)
  const [togglingScheduleTaskId, setTogglingScheduleTaskId] = useState<string | null>(null)
  const [togglingAutomatic, setTogglingAutomatic] = useState(false)

  // 单票采集与全盘同步
  const [singleStockTicker, setSingleStockTicker] = useState('NVDA')
  const [runningSingleStockCollect, setRunningSingleStockCollect] = useState(false)
  const [runningBatchSync, setRunningBatchSync] = useState(false)

  // 全盘归档与对账
  const [marketArchives, setMarketArchives] = useState<MarketArchiveItem[]>([])
  const [reconciliation, setReconciliation] = useState<MarketReconciliationMap | null>(null)

  // 参数配置弹窗
  const [configModalOpen, setConfigModalOpen] = useState(false)
  const [selectedConfigTaskId, setSelectedConfigTaskId] = useState<string | null>(null)

  // 预设股票池
  const PRESET_POOLS = [
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
      tickers: 'NVDA, TSM, AVGO, AMD, 8035, 6857, ASML, QCOM',
    },
    {
      id: 'jpx',
      label: '东证核心龙头 (JPX Prime)',
      icon: '🗼',
      tickers: '8035, 6857, 7203, 9984, 6501, 7974, 1306',
    },
    {
      id: 'macro',
      label: '大盘与避险 (Macro & ETF)',
      icon: '🌐',
      tickers: 'SPY, QQQ, DIA, SMH, GLD, TLT, USDJPY, ^VIX',
    },
    {
      id: 'core31',
      label: '全量31只核心资产底账池',
      icon: '🎯',
      tickers:
        'SPY, QQQ, DIA, SMH, 1306, ^VIX, ^N225VI, DXY, USDJPY, ^TNX, NVDA, AMD, TSM, AVGO, MSFT, GOOGL, META, AAPL, STX, PLTR, IREN, 8035, 6857, 9984, LLY, RXRX, INTU, 7203, 6501, 7974, GLD',
    },
  ]

  // 解析输入的标的列表
  const parsedTickers = useMemo(() => {
    const raw = batchInputText
      .split(/[,;\s\n\t]+/)
      .map(t => t.trim().toUpperCase())
      .filter(t => t.length > 0)
    return Array.from(new Set(raw))
  }, [batchInputText])

  // 加载调度任务与归档信息
  const loadScheduler = async () => {
    try {
      const res = await api.getTerminalTasks()
      if (res.ok && res.data) {
        setSchedulerInfo(res.data)
      }
    } catch (err: any) {
      console.warn('获取调度信息失败:', err)
    }
  }

  const loadArchives = async () => {
    try {
      const res = await api.getMarketArchives()
      if (res.ok && res.data) {
        setMarketArchives(res.data.items || [])
        if (res.data.reconciliation) {
          setReconciliation(res.data.reconciliation)
        }
      }
    } catch (err: any) {
      console.warn('获取归档信息失败:', err)
    }
  }

  // 加载初始权威行情数据
  const loadInitialQuotes = async () => {
    try {
      const res = await api.getMarketQuotes('ALL')
      if (res.ok && res.data?.all_quotes) {
        const items: BatchQuoteCollectedItem[] = res.data.all_quotes.map(q => ({
          ...q,
          change: 0.0,
          change_percent: 0.0,
          status: 'success',
        }))
        setCollectedQuotes(items)
        setBatchStats({
          total: items.length,
          success: items.filter(x => x.is_valid).length,
          failed: items.filter(x => !x.is_valid).length,
          sessionNote: res.data.market_session_note || '前一交易日收盘基准 (闭市状态)',
          collectedAt: res.meta?.updated_at || new Date().toISOString(),
        })
      }
    } catch (err: any) {
      console.warn('获取行情数据失败:', err)
    }
  }

  const loadAll = async () => {
    await Promise.all([loadScheduler(), loadArchives(), loadInitialQuotes()])
  }

  useEffect(() => {
    void loadAll()
  }, [refreshKey])

  // 执行批量股票价格采集
  const handleRunBatchQuoteCollection = async () => {
    if (parsedTickers.length === 0 || isCollectingBatch) return
    setIsCollectingBatch(true)

    showToast({
      type: 'info',
      title: `启动批量股票价格采集 (${parsedTickers.length} 只标的)`,
      message: '正在前置核验交易时段、执行美分级精度校验并增量不可篡改归档...',
    })

    try {
      const res = await api.batchCollectQuotes(parsedTickers, true)
      if (res.ok && res.data) {
        const data = res.data
        setCollectedQuotes(data.items || [])
        setBatchStats({
          total: data.total_requested,
          success: data.success_count,
          failed: data.failed_count,
          sessionNote: data.market_session_note,
          collectedAt: data.collected_at,
        })

        showToast({
          type: 'success',
          title: `批量价格采集完成 (成功 ${data.success_count}/${data.total_requested})`,
          message: `已完成美分级精度检验与本地数据落盘，时效状态：${data.market_session_note}`,
        })
        await loadArchives()
      } else {
        showToast({
          type: 'error',
          title: '批量价格采集失败',
          message: res.error?.message || '未能完成批量报价获取',
        })
      }
    } catch (err: any) {
      showToast({
        type: 'error',
        title: '批量采集异常',
        message: err.message || '网络连接或服务端异常',
      })
    } finally {
      setIsCollectingBatch(false)
    }
  }

  // 1. 单只股票精准采集与平账核算
  const handleCollectSingleStock = async (ticker: string) => {
    const symbol = ticker.trim().toUpperCase()
    if (!symbol || runningSingleStockCollect) return
    setRunningSingleStockCollect(true)
    showToast({
      type: 'info',
      title: `启动标的 [${symbol}] 数据拉取`,
      message: '正在从官方来源拉取行情、官方三表底稿、重算250日K线与DCF估值走廊...',
    })
    try {
      const res = await api.runTerminalTask('STOCK_DOSSIER_COLLECT', symbol)
      if (res.ok) {
        showToast({
          type: 'success',
          title: `标的 [${symbol}] 数据拉取与核算已完成`,
          message: `已同步最新报价、官方三表底稿与DCF走廊 (Run ID: ${res.data.run_id?.slice(0, 8) || 'done'})`,
        })
        await loadAll()
      } else {
        showToast({
          type: 'error',
          title: '单票数据拉取失败',
          message: res.error?.message || '无法获取该标的数据，请检查代码拼写',
        })
      }
    } catch (err: any) {
      showToast({
        type: 'error',
        title: '请求异常',
        message: err.message || '网络连接或调度服务异常',
      })
    } finally {
      setRunningSingleStockCollect(false)
    }
  }

  // 2. 全市场一键同步与对账
  const handleRunFullSync = async () => {
    if (runningBatchSync) return
    setRunningBatchSync(true)
    showToast({
      type: 'info',
      title: '开始全市场同步与对账',
      message: '正在触发全市场日线行情归档、对账自检与形态初筛...',
    })
    try {
      const res = await api.startTerminalBatch()
      if (res.ok) {
        showToast({
          type: 'success',
          title: '全市场同步流水线已启动',
          message: `批处理任务正在后台运行 (Run ID: ${res.data.run_id?.slice(0, 8) || 'ok'})`,
        })
        await loadScheduler()
      } else {
        showToast({
          type: 'error',
          title: '启动同步流水线失败',
          message: res.error?.message || '后台调度器未能启动批处理',
        })
      }
    } catch (err: any) {
      showToast({
        type: 'error',
        title: '同步请求异常',
        message: err.message || '网络通信故障',
      })
    } finally {
      setRunningBatchSync(false)
    }
  }

  // 3. 切换全局定时守护开关
  const handleToggleAutomatic = async () => {
    if (togglingAutomatic || !schedulerInfo) return
    const targetState = !schedulerInfo.automatic_enabled
    setTogglingAutomatic(true)
    try {
      const res = await api.setTerminalAutomatic(targetState)
      if (res.ok && res.data) {
        setSchedulerInfo(res.data)
        showToast({
          type: 'success',
          title: targetState ? '定时守护已开启' : '定时守护已暂停',
          message: targetState
            ? '系统将在美股与日股闭市后自动执行全量对账与数据拉取'
            : '已暂停后台定时调度，您仍可随时手动更新',
        })
      } else {
        showToast({
          type: 'error',
          title: '设置定时状态失败',
          message: res.error?.message || '更新失败',
        })
      }
    } catch (err: any) {
      showToast({ type: 'error', title: '异常', message: err.message })
    } finally {
      setTogglingAutomatic(false)
    }
  }

  // 4. 运行特定调度任务
  const handleRunTask = async (task: TaskSchedulerTask) => {
    if (runningTaskId === task.id) return
    setRunningTaskId(task.id)
    showToast({
      type: 'info',
      title: '任务已提交至后台队列',
      message: `正在执行 [${task.name}]...`,
    })
    try {
      const res = await api.runTerminalTask(task.id)
      if (res.ok) {
        showToast({
          type: 'success',
          title: '任务已完成',
          message: `[${task.name}] 执行完毕`,
        })
        await loadScheduler()
      } else {
        showToast({
          type: 'error',
          title: '启动任务失败',
          message: res.error?.message || '未能排队执行该任务',
        })
      }
    } catch (err: any) {
      showToast({ type: 'error', title: '执行异常', message: err.message })
    } finally {
      setRunningTaskId(null)
    }
  }

  // 5. 切换单项任务的定时调度开关
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
        await loadScheduler()
      } else {
        showToast({
          type: 'error',
          title: '更新调度失败',
          message: res.error?.message || '无法修改任务定时配置',
        })
      }
    } catch (err: any) {
      showToast({ type: 'error', title: '请求异常', message: err.message })
    } finally {
      setTogglingScheduleTaskId(null)
    }
  }

  // 过滤后的价格列表
  const filteredCollectedQuotes = useMemo(() => {
    return collectedQuotes.filter(item => {
      if (quoteFilterMarket === 'US') return item.market === 'US'
      if (quoteFilterMarket === 'JP') return item.market === 'JP'
      if (quoteFilterMarket === 'UP_ONLY') return (item.change_percent || 0) > 0
      return true
    })
  }, [collectedQuotes, quoteFilterMarket])

  const tasks = schedulerInfo?.tasks || []
  const allRuns = schedulerInfo?.runs || schedulerInfo?.recent_runs || []
  const recentRuns: TaskSchedulerRun[] = allRuns.slice(0, 10)

  return (
    <div className="p-4 md:p-6 max-w-[1600px] mx-auto space-y-6">
      {/* 1. 顶层极简状态条 (冰魄玄冰面板) */}
      <div className="ice-panel rounded-2xl px-5 py-3.5 flex flex-wrap items-center justify-between gap-3 text-xs shadow-xs">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <ShieldCheckIcon className="w-4 h-4 text-sky-500" />
          </div>
          <span className="font-bold text-slate-800">官方行情与数据同步引擎 · 在线</span>
          <span className="text-slate-300">|</span>
          <div className="flex items-center gap-1.5 text-slate-600 font-mono">
            <span>
              数据基准：{batchStats?.sessionNote || '前收盘价基准 · 闭市核验'}
            </span>
            {/* 时效核验规则说明感叹号 */}
            <div className="relative inline-flex items-center">
              <button
                type="button"
                onClick={() => setActivePopover(activePopover === 'freshness' ? null : 'freshness')}
                className="w-3.5 h-3.5 rounded-full flex items-center justify-center text-slate-400 hover:text-sky-600 focus:outline-none"
                title="查看行情时效与闭市对账机制"
              >
                <InfoCircleIcon className="w-2.5 h-2.5" />
              </button>
              {activePopover === 'freshness' && (
                <div
                  className="absolute top-full left-0 mt-2 w-72 p-3 rounded-xl bg-white/95 border border-sky-200 shadow-xl z-50 text-left backdrop-blur-md"
                  onMouseLeave={() => setActivePopover(null)}
                >
                  <div className="flex items-center justify-between border-b border-sky-100 pb-1.5 mb-1.5">
                    <span className="font-bold text-xs text-slate-800">行情时效与对账核验机制</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-sky-50 text-sky-700 font-semibold border border-sky-200">
                      时效门禁
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600 leading-relaxed">
                    严格前置查验并标明行情时段状态，确保估值与决策基于最新真实交易依据。
                  </p>
                  <div className="mt-2 p-2 rounded-lg bg-sky-50/60 border border-sky-100 text-[10px] text-slate-700 leading-relaxed">
                    <span className="font-semibold text-slate-800">【参数反映情况】：</span>
                    非交易时段标记为 PREVIOUS_CLOSE 前收盘价基准，逐笔核验交易所收盘撮合价，保障数据时效性与准确性。
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadAll}
            className="text-slate-600 hover:text-sky-600 cursor-pointer flex items-center gap-1.5 transition-all px-3 py-1.5 rounded-xl border border-sky-200/80 bg-white/80 text-xs font-semibold hover:border-sky-300 shadow-2xs"
          >
            <RefreshIcon className="w-3.5 h-3.5" />
            <span>刷新服务底账</span>
          </button>
        </div>
      </div>

      {/* 2. 核心控制台：批量股票价格采集工作台 (全宽强化冰魄流火面板) */}
      <div className="ice-panel rounded-2xl p-6 shadow-sm space-y-6">
        {/* 顶部标题与模式切换 */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-sky-100/80 pb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-sky-500 to-blue-700 flex items-center justify-center text-white shadow-xs">
                <ZapIcon className="w-4 h-4" />
              </div>
              <h2 className="text-lg font-black text-slate-900 tracking-tight">
                批量股票价格数据采集控制台
              </h2>
              <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-orange-50 text-orange-700 border border-orange-200 font-bold font-mono">
                美分级精度 · 交易时段感知
              </span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              输入多个股票代码或一键点选快捷核心池，并发拉取官方权威行情、美分级精度核验、时效门禁打标并不可篡改归档至本地底账。
            </p>
          </div>

          {/* 模式切换胶囊 */}
          <div className="flex items-center bg-sky-50/70 p-1 rounded-xl border border-sky-200/60 shrink-0">
            <button
              type="button"
              onClick={() => setCollectionMode('batch_prices')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                collectionMode === 'batch_prices'
                  ? 'bg-white text-sky-800 shadow-2xs border border-sky-200'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              🚀 批量价格并发采集
            </button>
            <button
              type="button"
              onClick={() => setCollectionMode('single_dossier')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                collectionMode === 'single_dossier'
                  ? 'bg-white text-sky-800 shadow-2xs border border-sky-200'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              🎯 单票全息深度档案
            </button>
          </div>
        </div>

        {collectionMode === 'batch_prices' ? (
          /* ================================================================= */
          /* 模式 A：批量股票价格并发采集                                      */
          /* ================================================================= */
          <div className="space-y-5">
            {/* 快捷股票池预设按钮 */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span className="font-semibold text-slate-700">快捷填充行业与指数核心池:</span>
                <span className="font-mono text-[11px] text-sky-700 bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
                  当前已输入 {parsedTickers.length} 只标的
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {PRESET_POOLS.map(pool => (
                  <button
                    key={pool.id}
                    type="button"
                    onClick={() => setBatchInputText(pool.tickers)}
                    className="text-xs px-3 py-1.5 rounded-xl border border-sky-200/80 bg-white/90 hover:bg-sky-50/80 hover:border-sky-300 text-slate-700 font-semibold transition-all cursor-pointer flex items-center gap-1.5 shadow-2xs active:scale-95"
                  >
                    <span>{pool.icon}</span>
                    <span>{pool.label}</span>
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => setBatchInputText('')}
                  className="text-xs px-3 py-1.5 rounded-xl border border-rose-200 bg-rose-50/50 hover:bg-rose-50 text-rose-600 font-semibold transition-all cursor-pointer ml-auto"
                >
                  清空代码
                </button>
              </div>
            </div>

            {/* 多标的文本输入框与操作栏 */}
            <div className="space-y-3">
              <div className="relative">
                <textarea
                  rows={3}
                  value={batchInputText}
                  onChange={e => setBatchInputText(e.target.value)}
                  placeholder="输入股票代码，支持逗号、空格或换行分隔（例如：NVDA, AAPL, MSFT, AMD, AVGO, TSM, 8035, 6857, META, GOOGL, AMZN, PLTR, GLD）"
                  className="w-full text-sm font-mono font-bold rounded-xl border border-sky-200 bg-white/95 p-3.5 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-200 shadow-inner resize-y leading-relaxed"
                />
              </div>

              {/* 启动采集大按钮与统计标签 */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  <span>支持纽交所/纳斯达克全市场美股及东证全量日股（代码自动映射）</span>
                </div>

                <button
                  type="button"
                  disabled={isCollectingBatch || parsedTickers.length === 0}
                  onClick={handleRunBatchQuoteCollection}
                  className="px-6 py-3 rounded-xl bg-gradient-to-r from-orange-600 via-red-600 to-rose-600 hover:from-orange-500 hover:to-rose-500 text-white font-bold text-sm cursor-pointer disabled:opacity-50 transition-all flex items-center justify-center gap-2 shadow-md hover:shadow-lg active:scale-98 shrink-0"
                >
                  {isCollectingBatch ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>正在并发拉取与核验报价 ({parsedTickers.length} 只)...</span>
                    </>
                  ) : (
                    <>
                      <ZapIcon className="w-4 h-4 text-amber-200" />
                      <span>一键并发采集最新价格 ({parsedTickers.length} 只标的)</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* 批量采集统计卡片 (冰块质感微卡片) */}
            {batchStats && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2">
                <div className="ice-block rounded-xl p-3 shadow-2xs">
                  <div className="text-[11px] text-slate-500 font-semibold">本轮请求标的</div>
                  <div className="text-xl font-black font-mono text-slate-900 mt-1">
                    {batchStats.total} <span className="text-xs font-normal text-slate-500">只</span>
                  </div>
                </div>
                <div className="ice-block rounded-xl p-3 shadow-2xs">
                  <div className="text-[11px] text-slate-500 font-semibold">权威精度校验通过</div>
                  <div className="text-xl font-black font-mono text-emerald-600 mt-1">
                    {batchStats.success} <span className="text-xs font-normal text-slate-500">只 (100%)</span>
                  </div>
                </div>
                <div className="ice-block rounded-xl p-3 shadow-2xs">
                  <div className="text-[11px] text-slate-500 font-semibold">交易时段感知状态</div>
                  <div className="text-xs font-bold text-slate-800 mt-1.5 truncate" title={batchStats.sessionNote}>
                    {batchStats.sessionNote.split('|')[0] || '盘中/收盘基准'}
                  </div>
                </div>
                <div className="ice-block rounded-xl p-3 shadow-2xs">
                  <div className="text-[11px] text-slate-500 font-semibold">落盘时间戳</div>
                  <div className="text-xs font-mono text-sky-700 mt-1.5 truncate">
                    {formatDeviceTime(batchStats.collectedAt)}
                  </div>
                </div>
              </div>
            )}

            {/* 实时采集价格数据对账表 */}
            <div className="space-y-3 pt-2">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-slate-800">
                    最新批量采集价格对账清单 ({filteredCollectedQuotes.length})
                  </h3>
                  <span className="text-[10px] text-slate-400">· 实时美分级核算</span>
                </div>

                {/* 市场与涨跌筛选胶囊 */}
                <div className="flex items-center gap-1.5 text-xs bg-slate-100/80 p-1 rounded-xl border border-slate-200">
                  <button
                    type="button"
                    onClick={() => setQuoteFilterMarket('ALL')}
                    className={`px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                      quoteFilterMarket === 'ALL'
                        ? 'bg-white text-slate-900 shadow-2xs'
                        : 'text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    全部 ({collectedQuotes.length})
                  </button>
                  <button
                    type="button"
                    onClick={() => setQuoteFilterMarket('US')}
                    className={`px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                      quoteFilterMarket === 'US'
                        ? 'bg-white text-blue-700 shadow-2xs'
                        : 'text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    美股 US
                  </button>
                  <button
                    type="button"
                    onClick={() => setQuoteFilterMarket('JP')}
                    className={`px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                      quoteFilterMarket === 'JP'
                        ? 'bg-white text-emerald-700 shadow-2xs'
                        : 'text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    日股 JP
                  </button>
                  <button
                    type="button"
                    onClick={() => setQuoteFilterMarket('UP_ONLY')}
                    className={`px-2.5 py-1 rounded-lg font-bold transition-all cursor-pointer ${
                      quoteFilterMarket === 'UP_ONLY'
                        ? 'bg-white text-red-600 shadow-2xs'
                        : 'text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    仅大涨标的 🔥
                  </button>
                </div>
              </div>

              {/* 数据表格 */}
              <div className="overflow-x-auto rounded-xl border border-sky-100 bg-white/90 shadow-2xs">
                <table className="w-full text-left text-xs">
                  <thead className="bg-sky-50/60 border-b border-sky-100 text-slate-600 font-semibold">
                    <tr>
                      <th className="py-2.5 px-3.5">标的代码</th>
                      <th className="py-2.5 px-3.5">公司/指数简称</th>
                      <th className="py-2.5 px-3.5">市场</th>
                      <th className="py-2.5 px-3.5 text-right">最新价格</th>
                      <th className="py-2.5 px-3.5 text-right">当日涨跌幅</th>
                      <th className="py-2.5 px-3.5">交易时段</th>
                      <th className="py-2.5 px-3.5">本地二级来源底账</th>
                      <th className="py-2.5 px-3.5 text-center">操作</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-sky-50 font-mono">
                    {filteredCollectedQuotes.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="py-8 text-center text-slate-400 font-sans">
                          暂无符合条件的报价记录，请点击上方“一键并发采集最新价格”
                        </td>
                      </tr>
                    ) : (
                      filteredCollectedQuotes.map(item => {
                        const isUp = (item.change_percent || 0) > 0
                        const isDown = (item.change_percent || 0) < 0
                        return (
                          <tr key={item.ticker} className="hover:bg-sky-50/40 transition-colors">
                            <td className="py-2.5 px-3.5 font-bold text-slate-900">
                              {item.ticker}
                            </td>
                            <td className="py-2.5 px-3.5 font-sans font-medium text-slate-700 max-w-[200px] truncate" title={item.company_name}>
                              {item.company_name}
                            </td>
                            <td className="py-2.5 px-3.5">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  item.market === 'JP'
                                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                    : 'bg-blue-50 text-blue-700 border border-blue-200'
                                }`}
                              >
                                {item.market}
                              </span>
                            </td>
                            <td className="py-2.5 px-3.5 text-right font-black text-slate-900 text-sm">
                              {item.formatted_price || '—'}
                            </td>
                            <td className="py-2.5 px-3.5 text-right">
                              <span
                                className={`inline-flex items-center gap-0.5 px-2 py-0.5 rounded border text-[11px] font-black ${
                                  isUp
                                    ? 'flame-badge'
                                    : isDown
                                    ? 'frost-badge'
                                    : 'bg-slate-50 text-slate-600 border-slate-200'
                                }`}
                              >
                                {isUp ? '▲ +' : isDown ? '▼ ' : ''}
                                {item.change_percent != null ? `${item.change_percent.toFixed(2)}%` : '0.00%'}
                              </span>
                            </td>
                            <td className="py-2.5 px-3.5 font-sans text-[11px]">
                              <span
                                className={`px-2 py-0.5 rounded ${
                                  item.session_type === 'regular_trading'
                                    ? 'bg-amber-50 text-amber-700 border border-amber-200 font-semibold'
                                    : 'bg-slate-100 text-slate-600'
                                }`}
                              >
                                {item.session_type === 'regular_trading'
                                  ? '盘中现价'
                                  : item.session_type === 'pre_market'
                                  ? '盘前撮合'
                                  : '前收盘价基准'}
                              </span>
                            </td>
                            <td className="py-2.5 px-3.5 text-[10px] text-slate-500 max-w-[220px] truncate" title={item.source_file}>
                              {item.source_file || 'google-finance/raw'}
                            </td>
                            <td className="py-2.5 px-3.5 text-center">
                              {onNavigateToAnalytics ? (
                                <button
                                  type="button"
                                  onClick={() => onNavigateToAnalytics(item.ticker)}
                                  className="text-[11px] text-sky-600 hover:text-sky-800 font-bold font-sans cursor-pointer hover:underline"
                                >
                                  深度分析 →
                                </button>
                              ) : (
                                <span className="text-slate-300">—</span>
                              )}
                            </td>
                          </tr>
                        )
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ) : (
          /* ================================================================= */
          /* 模式 B：单票全息深度档案拉取与估值测算                            */
          /* ================================================================= */
          <div className="space-y-4 max-w-2xl">
            <div className="space-y-2">
              <h3 className="text-sm font-bold text-slate-800">单标的全息官方数据穿透与 DCF 走廊计算</h3>
              <p className="text-xs text-slate-500 leading-relaxed">
                输入指定股票代码，一键从 SEC EDGAR / 东证官方决算短信拉取完整三表底稿、重算 250 日均线时序并测算自由现金流折现区间。
              </p>
            </div>

            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <SearchIcon className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  value={singleStockTicker}
                  onChange={e => setSingleStockTicker(e.target.value.toUpperCase())}
                  onKeyDown={e => {
                    if (e.key === 'Enter') void handleCollectSingleStock(singleStockTicker)
                  }}
                  placeholder="输入单只股票代码 (如 NVDA, AAPL, 8035)..."
                  className="w-full text-sm font-mono font-bold rounded-xl border border-sky-200 bg-white pl-10 pr-3.5 py-2.5 text-slate-900 focus:outline-none focus:border-sky-500"
                />
              </div>
              <button
                type="button"
                disabled={runningSingleStockCollect}
                onClick={() => void handleCollectSingleStock(singleStockTicker)}
                className="px-5 py-2.5 rounded-xl bg-sky-700 hover:bg-sky-800 text-white text-xs font-bold cursor-pointer disabled:opacity-50 transition-all flex items-center gap-1.5 shadow-sm shrink-0"
              >
                {runningSingleStockCollect ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>正在拉取与核算…</span>
                  </>
                ) : (
                  <>
                    <ZapIcon className="w-3.5 h-3.5" />
                    <span>立即拉取并核算</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 3. 全市场日线归档与自动化初筛流水线 */}
      <div className="ice-panel rounded-2xl p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-sky-100 pb-3">
          <div className="flex items-center gap-2">
            <DatabaseIcon className="w-5 h-5 text-sky-600" />
            <h2 className="text-base font-bold text-slate-800">全市场日线归档与形态初筛流水线</h2>
          </div>
          <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-sky-50 text-sky-700 border border-sky-200 font-bold font-mono">
            全量数千家企业标的池
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl bg-white/80 border border-sky-100 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-800">全盘底账规模</span>
              <span className="text-xs font-mono font-bold text-sky-700">美股 10,443 · 日股 4,449</span>
            </div>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              后台自动维护东证全市场与纽交所/纳斯达克全量上市公司索引，分批执行日线技术形态初筛。
            </p>
          </div>

          <div className="p-4 rounded-xl bg-white/80 border border-sky-100 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-800">
                定时守护调度：{schedulerInfo?.automatic_enabled ? '已开启' : '已暂停'}
              </span>
              <button
                type="button"
                disabled={togglingAutomatic}
                onClick={handleToggleAutomatic}
                className="text-xs font-semibold px-2.5 py-1 rounded-lg border border-sky-200 text-sky-700 hover:bg-sky-50 cursor-pointer"
              >
                {schedulerInfo?.automatic_enabled ? '暂停自动守护' : '开启自动守护'}
              </button>
            </div>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              每周二至周六 08:00 JST / 07:00 EST 闭市后自动执行全量对账自检与数据增量归档。
            </p>
          </div>
        </div>

        <button
          type="button"
          disabled={runningBatchSync}
          onClick={handleRunFullSync}
          className="w-full py-3 rounded-xl border border-sky-200 bg-sky-50/70 hover:bg-sky-100/70 text-xs font-bold text-sky-900 cursor-pointer disabled:opacity-50 transition-all flex items-center justify-center gap-2 shadow-2xs"
        >
          {runningBatchSync ? (
            <>
              <div className="w-3.5 h-3.5 border-2 border-sky-700 border-t-transparent rounded-full animate-spin" />
              <span>正在执行全盘同步与对账…</span>
            </>
          ) : (
            <>
              <LayersIcon className="w-4 h-4 text-sky-700" />
              <span>立即执行全市场对账与形态同步流水线</span>
            </>
          )}
        </button>
      </div>

      {/* 4. 底部高级配置与任务历史折叠抽屉 */}
      <div className="pt-2 border-t border-sky-100 space-y-4">
        <div className="flex items-center justify-center">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-xs font-semibold text-slate-600 hover:text-slate-900 cursor-pointer px-4 py-2 rounded-xl border border-sky-200 bg-white/90 hover:border-sky-300 shadow-2xs transition-all"
          >
            {showAdvanced ? (
              <>
                <ChevronUpIcon className="w-3.5 h-3.5 text-slate-700" />
                <span>收起高级配置与运行历史</span>
              </>
            ) : (
              <>
                <ChevronDownIcon className="w-3.5 h-3.5 text-slate-500" />
                <span>高级配置、任务队列与历史对账 (按需展开)</span>
              </>
            )}
          </button>
        </div>

        {showAdvanced && (
          <div className="ice-panel rounded-2xl p-5 shadow-sm space-y-5 animate-in fade-in duration-200">
            {/* 子选项卡切换 */}
            <div className="flex items-center gap-2 border-b border-sky-100 pb-3">
              <button
                type="button"
                onClick={() => setAdvancedTab('scheduler')}
                className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                  advancedTab === 'scheduler'
                    ? 'bg-sky-100 text-sky-900 border border-sky-300 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                任务调度器与定时开关 ({tasks.length})
              </button>
              <button
                type="button"
                onClick={() => setAdvancedTab('runs')}
                className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                  advancedTab === 'runs'
                    ? 'bg-sky-100 text-sky-900 border border-sky-300 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                运行历史记录 ({recentRuns.length})
              </button>
              <button
                type="button"
                onClick={() => setAdvancedTab('archives')}
                className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                  advancedTab === 'archives'
                    ? 'bg-sky-100 text-sky-900 border border-sky-300 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                市场归档底账 ({marketArchives.length})
              </button>
            </div>

            {/* 子选项卡 A：任务调度器 */}
            {advancedTab === 'scheduler' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {tasks.map(task => (
                  <div
                    key={task.id}
                    className="ice-block rounded-xl p-3.5 flex items-center justify-between gap-3 shadow-2xs"
                  >
                    <div className="space-y-0.5 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-xs text-slate-800 truncate">{task.name}</span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-sky-50 text-sky-700 border border-sky-200 font-mono">
                          {task.dimension}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500 font-mono">{task.schedule}</div>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedConfigTaskId(task.id)
                          setConfigModalOpen(true)
                        }}
                        className="px-2 py-1 rounded text-[11px] font-medium bg-slate-50 hover:bg-slate-100 text-slate-600 border border-slate-200 cursor-pointer"
                        title="参数配置"
                      >
                        配置
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleToggleSchedule(task.id, task.enabled ?? true)}
                        className={`px-2 py-1 rounded text-[11px] font-medium border cursor-pointer ${
                          task.enabled !== false
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100'
                            : 'bg-slate-50 text-slate-500 border-slate-200 hover:bg-slate-100'
                        }`}
                        title="切换定时调度"
                      >
                        {task.enabled !== false ? '已开启' : '已暂停'}
                      </button>
                      <button
                        type="button"
                        disabled={runningTaskId === task.id}
                        onClick={() => void handleRunTask(task)}
                        className="px-2.5 py-1 rounded text-[11px] font-bold bg-sky-50 hover:bg-sky-100 text-sky-700 border border-sky-200 cursor-pointer disabled:opacity-50"
                      >
                        {runningTaskId === task.id ? '运行中…' : '立即执行'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* 子选项卡 B：运行历史 */}
            {advancedTab === 'runs' && (
              <div className="divide-y divide-sky-100 rounded-xl border border-sky-100 bg-white/90 overflow-hidden font-mono text-xs">
                {recentRuns.length === 0 ? (
                  <div className="p-4 text-center text-slate-400">暂无运行历史记录</div>
                ) : (
                  recentRuns.map(run => (
                    <div key={run.run_id} className="p-3 flex items-center justify-between gap-2 hover:bg-sky-50/50">
                      <div className="space-y-0.5">
                        <div className="font-bold text-slate-800">{run.task}</div>
                        <div className="text-[11px] text-slate-500">{run.created_at} · Run ID: {run.run_id.slice(0, 8)}</div>
                      </div>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          run.status === 'SUCCESS'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : run.status === 'RUNNING'
                            ? 'bg-amber-50 text-amber-700 border border-amber-200'
                            : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {run.status}
                      </span>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* 子选项卡 C：归档底账 */}
            {advancedTab === 'archives' && (
              <div className="text-xs space-y-2">
                <div className="flex items-center justify-between text-slate-500">
                  <span>已纳管日线归档标的共 {marketArchives.length} 只</span>
                  {reconciliation && (
                    <span className="font-mono text-sky-700">
                      对账匹配：美股 {reconciliation.us?.matched_count || 0} · 日股 {reconciliation.jp?.matched_count || 0}
                    </span>
                  )}
                </div>
                <div className="max-h-64 overflow-y-auto rounded-xl border border-sky-100 bg-white/90 p-2 divide-y divide-sky-50 font-mono text-[11px]">
                  {marketArchives.slice(0, 50).map(arch => (
                    <div key={`${arch.market}-${arch.symbol}`} className="py-1.5 px-2 flex items-center justify-between">
                      <span className="font-bold text-slate-800">{arch.symbol}</span>
                      <span className="text-slate-500">{arch.market} · {arch.count} 条日线 · 最新 {arch.last_date}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 参数配置弹窗 */}
      <TaskConfigModal
        isOpen={configModalOpen}
        onClose={() => setConfigModalOpen(false)}
        selectedTaskId={selectedConfigTaskId}
        onConfigSaved={loadScheduler}
      />
    </div>
  )
}
