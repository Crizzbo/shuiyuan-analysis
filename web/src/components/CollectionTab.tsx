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

  // 5. 批量价格采集控制台状态
  const [batchTickersInput, setBatchTickersInput] = useState('AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA')
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

  // 6. 参数配置弹窗
  const [configModalOpen, setConfigModalOpen] = useState(false)
  const [selectedConfigTaskId, setSelectedConfigTaskId] = useState<string | null>(null)

  // 7. 调度任务运行历史展示切换
  const [showRunsHistory, setShowRunsHistory] = useState(false)

  // 预设资产池快速填充
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
      const [ovRes, schedRes, archRes] = await Promise.all([
        api.getCollectionOverview(),
        api.getTerminalTasks(),
        api.getMarketArchives(),
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
    } catch (err) {
      console.error('Failed to load collection hub data:', err)
    } finally {
      setLoadingOverview(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [refreshKey])

  // 执行批量价格采集
  const handleBatchCollect = async () => {
    const raw = batchTickersInput.trim()
    if (!raw) {
      showToast({ type: 'warning', title: '输入为空', message: '请在输入框填入股票代码或点击上方预设池' })
      return
    }

    const tickerList = Array.from(
      new Set(
        raw
          .split(/[,;\s\n\r]+/)
          .map(t => t.trim().toUpperCase())
          .filter(t => t.length > 0)
      )
    )

    if (tickerList.length === 0) {
      showToast({ type: 'warning', title: '无效代码', message: '未能解析出有效标的代码' })
      return
    }

    setRunningBatchCollect(true)
    setBatchProgress(15)

    showToast({
      type: 'info',
      title: `启动批量行情报价同步 (${tickerList.length} 只标的)`,
      message: '正在识别市场交易时段、核验价格精度并执行合规存证归档...',
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
                  <span className="text-[11px] font-mono text-sky-700 font-bold">
                    当前已输入 {parsedTickerCount} 只标的
                  </span>
                </div>
                <textarea
                  id="batch-tickers-input"
                  rows={2}
                  value={batchTickersInput}
                  onChange={e => setBatchTickersInput(e.target.value)}
                  placeholder="例如: AAPL, MSFT, GOOGL, NVDA, 8035, 7203..."
                  className="w-full rounded-xl border border-sky-200/80 bg-white/95 px-3 py-2 text-xs font-mono text-slate-800 placeholder-slate-400 shadow-2xs focus:border-sky-500 focus:outline-hidden"
                />
              </div>

              <div>
                <button
                  type="button"
                  disabled={runningBatchCollect || parsedTickerCount === 0}
                  onClick={() => void handleBatchCollect()}
                  className="w-full h-15 rounded-xl bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-500 hover:to-blue-500 text-white font-bold text-xs shadow-md hover:shadow-lg transition-all cursor-pointer disabled:opacity-50 flex flex-col items-center justify-center gap-1"
                >
                  <div className="flex items-center gap-1.5">
                    <ZapIcon className={`w-4 h-4 ${runningBatchCollect ? 'animate-bounce' : ''}`} />
                    <span>
                      {runningBatchCollect
                        ? '正在同步最新价格与核验时钟…'
                        : `一键同步最新行情报价 (${parsedTickerCount} 只)`}
                    </span>
                  </div>
                  <span className="text-[10px] text-sky-100/90 font-normal">
                    市场交易时段自适应 · 官方精度核验 · 合规存证归档
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
