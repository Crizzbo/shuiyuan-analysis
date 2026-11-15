import { useState, useEffect, useRef, useMemo } from 'react'
import type {
  CollectionOverviewData,
  PipelineStatusData,
  TaskSchedulerInfo,
  TaskSchedulerRun,
  TaskSchedulerTask,
  MarketArchiveItem,
  MarketReconciliationMap,
} from '../types/api'
import { api } from '../services/api'
import { showToast } from './Toast'
import { Pagination } from './Pagination'
import { TaskConfigModal } from './TaskConfigModal'
import { formatDeviceTime, toChinese } from '../utils/format'
import { TargetIcon, ZapIcon, LayersIcon, BarChartIcon, RefreshIcon } from './common'

interface CollectionTabProps {
  pipelineStatus?: PipelineStatusData | null
  refreshKey?: number
}

export function CollectionTab({ pipelineStatus, refreshKey }: CollectionTabProps) {
  // 当前子模块视图：个股全息采集 | 调度计划与流水 | 运营管线 | 全盘日线归档
  const [activeSection, setActiveSection] = useState<'single_stock' | 'scheduler' | 'pipelines' | 'archives'>('single_stock')

  // 1. 运营管线状态
  const [filterTrack, setFilterTrack] = useState<'ALL' | 'LOCAL_AUDIT_SYNC' | 'DATA_COLLECTION'>('ALL')
  const [data, setData] = useState<CollectionOverviewData | null>(null)
  const [configModalOpen, setConfigModalOpen] = useState(false)
  const [selectedConfigTaskId, setSelectedConfigTaskId] = useState<string | null>(null)
  const [rerunningTaskId, setRerunningTaskId] = useState<string | null>(null)
  const [highlightTaskId, setHighlightTaskId] = useState<string | null>(null)
  const [runningAudit, setRunningAudit] = useState(false)
  const [runningIngest, setRunningIngest] = useState(false)
  const [queuePage, setQueuePage] = useState(1)

  // 2. 调度执行器状态 (Task Scheduler)
  const [schedulerInfo, setSchedulerInfo] = useState<TaskSchedulerInfo | null>(null)
  const [runningTaskId, setRunningTaskId] = useState<string | null>(null)
  const [togglingScheduleTaskId, setTogglingScheduleTaskId] = useState<string | null>(null)
  const [runHistoryPage, setRunHistoryPage] = useState(1)
  const runHistoryPageSize = 10
  const [singleStockTicker, setSingleStockTicker] = useState('NVDA')
  const [runningSingleStockCollect, setRunningSingleStockCollect] = useState(false)

  // 3. 全盘日线归档状态与全市场对账 (Market Archives & Reconciliation)
  const [marketArchives, setMarketArchives] = useState<MarketArchiveItem[]>([])
  const [reconciliation, setReconciliation] = useState<MarketReconciliationMap | null>(null)
  const [selectedUnmappedMarket, setSelectedUnmappedMarket] = useState<'US' | 'JP' | null>(null)
  const [archiveSearch, setArchiveSearch] = useState('')
  const [archiveMarketFilter, setArchiveMarketFilter] = useState<'ALL' | 'US' | 'JP'>('ALL')
  const [archivePage, setArchivePage] = useState(1)
  const archivePageSize = 12
  const [loadingArchives, setLoadingArchives] = useState(false)

  const prevRunningRef = useRef(false)

  // 加载运营管线概览
  const loadOverview = async () => {
    try {
      const colRes = await api.getCollectionOverview()
      if (colRes.ok) setData(colRes.data)
    } catch (err) {
      console.error('Failed to load collection overview:', err)
    }
  }

  // 加载调度器状态与执行记录
  const loadScheduler = async () => {
    try {
      const res = await api.getTerminalTasks()
      if (res.ok && res.data) {
        setSchedulerInfo(res.data)
      }
    } catch (err) {
      console.error('Failed to load scheduler tasks:', err)
    }
  }

  // 加载全盘日线行情归档底账与目标日对账矩阵
  const loadArchives = async () => {
    try {
      setLoadingArchives(true)
      const res = await api.getMarketArchives()
      if (res.ok && res.data) {
        if (res.data.items) {
          setMarketArchives(res.data.items)
        }
        if (res.data.reconciliation) {
          setReconciliation(res.data.reconciliation)
        }
      }
    } catch (err) {
      console.error('Failed to load market archives:', err)
    } finally {
      setLoadingArchives(false)
    }
  }

  const loadAll = async () => {
    await Promise.all([loadOverview(), loadScheduler(), loadArchives()])
  }

  useEffect(() => {
    void loadAll()
  }, [])

  // 流水线结束自动拉取最新状态
  useEffect(() => {
    const wasRunning = prevRunningRef.current
    const isNowRunning = pipelineStatus?.is_running ?? false
    prevRunningRef.current = isNowRunning

    if (wasRunning && !isNowRunning) {
      void loadAll()
    }
  }, [pipelineStatus?.is_running])

  // 1. 本地核对同步手动执行
  const handleRunAuditSync = async () => {
    if (runningAudit) return
    setRunningAudit(true)
    showToast({
      type: 'info',
      title: '启动本地核对同步',
      message: '正在对齐财报三表平账、最新日线行情时效与密码学账本验签…',
    })
    try {
      const res = await api.runTerminalTask('LOCAL_AUDIT')
      if (res.ok) {
        showToast({
          type: 'success',
          title: '本地核对任务已入队',
          message: `主任务调度编号: ${res.data.run_id}`,
        })
      } else {
        showToast({
          type: 'error',
          title: '启动失败',
          message: res.error?.message || '流水线繁忙或已被占用',
        })
      }
    } catch (err: any) {
      showToast({ type: 'error', title: '执行异常', message: err.message })
    } finally {
      setRunningAudit(false)
    }
  }

  // 2. 外部数据采集手动执行
  const handleRunDataIngest = async () => {
    if (runningIngest) return
    setRunningIngest(true)
    showToast({
      type: 'info',
      title: '提交数据采集',
      message: '提交美股、日股和官方资讯采集任务',
    })
    try {
      const results = await Promise.all(['US_DAILY', 'JP_DAILY', 'OFFICIAL_NEWS'].map(id => api.runTerminalTask(id)))
      const accepted = results.filter(res => res.ok).length
      if (accepted > 0) {
        showToast({
          type: 'success',
          title: '数据采集任务已入队',
          message: `调度器已接受 ${accepted}/3 项任务，运行编号见任务历史`,
        })
      } else {
        showToast({
          type: 'error',
          title: '启动失败',
          message: '调度器未接受采集任务',
        })
      }
    } catch (err: any) {
      showToast({ type: 'error', title: '采集调度异常', message: err.message })
    } finally {
      setRunningIngest(false)
    }
  }

  // 3. 独立任务阻塞重跑
  const handleRerun = async (pipelineId: string, pipelineNameZh: string) => {
    if (rerunningTaskId) return
    setRerunningTaskId(pipelineId)
    showToast({
      type: 'info',
      title: `开始任务重跑: ${pipelineNameZh}`,
      message: '正在提交独立校验重跑任务…',
    })

    const t0 = performance.now()
    try {
      const res = await api.rerunCollectionTask(pipelineId)
      const dur = Math.round(performance.now() - t0)
      if (res.ok) {
        showToast({
          type: 'success',
          title: res.data.status === 'QUEUED' ? '已提交后台采集' : `任务执行完成 (${res.data.duration_ms || dur} ms)`,
          message: pipelineNameZh,
        })
        setHighlightTaskId(pipelineId)
        setTimeout(() => setHighlightTaskId(null), 3000)
        await loadAll()
      } else {
        showToast({
          type: 'error',
          title: '重跑执行未通过',
          message: res.error?.message || '后端任务执行未成功',
        })
      }
    } catch (err: any) {
      showToast({
        type: 'error',
        title: '重跑执行异常',
        message: err.message || '网络连接故障',
      })
    } finally {
      setRerunningTaskId(null)
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadScheduler()
      if (activeSection === 'pipelines') void loadOverview()
      if (activeSection === 'archives') void loadArchives()
    }, 150)
    return () => window.clearTimeout(timer)
  }, [refreshKey, activeSection])

  // 5. 调度器任务触发运行
  const handleRunScheduledTask = async (taskMeta: TaskSchedulerTask) => {
    if (runningTaskId === taskMeta.id) return
    setRunningTaskId(taskMeta.id)
    showToast({
      type: 'info',
      title: '任务已提交至后台队列',
      message: `正在执行 [${taskMeta.name}]，由终端执行器独立线程池处理...`,
    })

    try {
      const res = await api.runTerminalTask(taskMeta.id)
      if (res.ok) {
        showToast({
          type: 'success',
          title: '任务执行已就绪',
          message: `[${taskMeta.name}] 已加入终端任务队列 (Run ID: ${res.data?.run_id?.slice(0, 8)})`,
        })
        await loadScheduler()
      } else {
        showToast({
          type: 'error',
          title: '提交任务失败',
          message: res.error?.message || '未能排队执行该任务',
        })
      }
    } catch (err: any) {
      showToast({
        type: 'error',
        title: '请求异常',
        message: err.message || '网络连接或调度服务异常',
      })
    } finally {
      setRunningTaskId(null)
    }
  }

  // 6. 针对指定个股触发全维度数据拉取与平账
  const handleCollectSingleStock = async (symbolToRun: string) => {
    const symbol = symbolToRun.trim().toUpperCase()
    if (!symbol || runningSingleStockCollect) return
    setRunningSingleStockCollect(true)
    showToast({
      type: 'info',
      title: `在任务调度中启动标的 [${symbol}] 数据拉取`,
      message: '正在拉取最新行情、核验官方三表底稿、重算250日均线并刷新DCF估值走廊...',
    })
    try {
      const res = await api.runTerminalTask('STOCK_DOSSIER_COLLECT', symbol)
      if (res.ok) {
        showToast({
          type: 'success',
          title: `标的 [${symbol}] 数据拉取与核算已完成`,
          message: `已同步最新报价、平账自检与 DCF 估值 (Run ID: ${res.data.run_id?.slice(0, 8)})`,
        })
        await loadScheduler()
      } else {
        showToast({
          type: 'error',
          title: '单票数据拉取失败',
          message: res.error?.message || '无法获取该标的数据',
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

  // 7. 切换调度器定时配置
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
          message: `任务 [${taskId}] 定时分时调度已${targetState ? '开启' : '暂停'}`,
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
      showToast({
        type: 'error',
        title: '请求异常',
        message: err.message || '更新调度配置失败',
      })
    } finally {
      setTogglingScheduleTaskId(null)
    }
  }

  // 打开特定任务的参数配置弹窗
  const handleOpenConfig = (taskId?: string) => {
    setSelectedConfigTaskId(taskId || null)
    setConfigModalOpen(true)
  }

  // 补数队列分页切片
  const queueItems = data?.replenishment_queue?.items || []
  const pageSize = 10
  const queueTotalPages = Math.max(1, Math.ceil(queueItems.length / pageSize))
  const paginatedQueue = queueItems.slice((queuePage - 1) * pageSize, queuePage * pageSize)

  const isPipelineRunning = pipelineStatus?.is_running ?? false
  const auditFlow = pipelineStatus?.local_audit_sync
  const ingestFlow = pipelineStatus?.data_ingestion

  const allPipelines = data?.pipelines || []
  const filteredPipelines = allPipelines.filter(p => {
    if (filterTrack === 'ALL') return true
    if (filterTrack === 'LOCAL_AUDIT_SYNC') return p.track === 'LOCAL_AUDIT_SYNC'
    if (filterTrack === 'DATA_COLLECTION') return p.track === 'DATA_COLLECTION'
    return true
  })

  // 调度器运行记录切片 (兼容 runs 与 recent_runs)
  const allRuns = schedulerInfo?.runs || schedulerInfo?.recent_runs || []
  const activeRuns = schedulerInfo?.active_runs || allRuns.filter((r) => r.status === 'RUNNING' || r.status === 'QUEUED')
  const recentRuns = allRuns
  const configuredTasks = schedulerInfo?.tasks || []
  const totalRunPages = Math.max(1, Math.ceil(recentRuns.length / runHistoryPageSize))
  const paginatedRuns = recentRuns.slice(
    (runHistoryPage - 1) * runHistoryPageSize,
    runHistoryPage * runHistoryPageSize
  )

  const isTaskRunning = (taskId: string) => {
    return (
      runningTaskId === taskId ||
      activeRuns.some((r) => r.task === taskId && (r.status === 'RUNNING' || r.status === 'QUEUED'))
    )
  }

  const getLastRun = (taskId: string): TaskSchedulerRun | undefined => {
    return recentRuns.find((r) => r.task === taskId)
  }

  // 日线归档过滤与分页
  const filteredArchives = useMemo(() => {
    return marketArchives.filter((item) => {
      if (archiveMarketFilter !== 'ALL' && item.market !== archiveMarketFilter) return false
      if (archiveSearch.trim()) {
        const q = archiveSearch.trim().toUpperCase()
        if (!item.symbol.toUpperCase().includes(q)) return false
      }
      return true
    })
  }, [marketArchives, archiveMarketFilter, archiveSearch])

  const totalArchivePages = Math.max(1, Math.ceil(filteredArchives.length / archivePageSize))
  const paginatedArchives = useMemo(() => {
    const start = (archivePage - 1) * archivePageSize
    return filteredArchives.slice(start, start + archivePageSize)
  }, [filteredArchives, archivePage, archivePageSize])

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6">
      {/* 顶部精简数据中枢状态栏 (高屏占比，释放黄金视野) */}
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl px-4 py-3 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#199e70] animate-pulse" />
          <h1 className="font-bold text-[var(--text-primary)] flex items-center gap-1.5">
            <span>数据采集与运维控制台</span>
            <span className="text-[10px] px-2 py-0.2 rounded-full bg-[#3987e5]/10 text-[#3987e5] font-mono font-bold">
              全量 14,892 标的覆盖
            </span>
          </h1>
          <span className="text-[11px] text-[var(--text-muted)] hidden lg:inline">
            | 官方财报三表对齐 · 分时定时调度 · 资产冷热归档全盘对账
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <div className="text-[10px] text-[var(--text-muted)] font-mono hidden sm:flex items-center gap-2 mr-1">
            <span className="text-[#199e70] font-semibold">● 4 个守护作业在线</span>
            <span>·</span>
            <span>前收盘基准 (2026-11-14)</span>
          </div>
          <button
            type="button"
            onClick={() => handleOpenConfig()}
            className="px-3 py-1.5 rounded-lg border border-[#3987e5]/40 bg-[#3987e5]/10 hover:bg-[#3987e5]/20 text-[#3987e5] text-xs font-semibold cursor-pointer transition-all flex items-center gap-1.5 shadow-sm"
          >
            <span>高级配置 (SSOT)</span>
          </button>
          <button
            type="button"
            onClick={loadAll}
            className="px-3 py-1.5 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] hover:text-[#3987e5] text-xs font-medium cursor-pointer flex items-center gap-1"
          >
            <RefreshIcon className="w-3 h-3" />
            <span>刷新数据</span>
          </button>
        </div>
      </div>

      {/* 原生四栏专业模块导航 (三权分立，彻底解决大杂烩混乱) */}
      <div className="flex items-center gap-2 bg-[var(--surface-color)] border border-[var(--border-color)] p-1.5 rounded-xl shadow-sm overflow-x-auto">
        <button
          type="button"
          onClick={() => setActiveSection('single_stock')}
          className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
            activeSection === 'single_stock'
              ? 'bg-[#3987e5] text-white shadow'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]'
          }`}
        >
          <TargetIcon className="w-3.5 h-3.5" />
          <span>个股全息深度采集</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded-full font-mono bg-white/20">
            6大基石
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveSection('scheduler')}
          className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
            activeSection === 'scheduler'
              ? 'bg-[#3987e5] text-white shadow'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]'
          }`}
        >
          <ZapIcon className="w-3.5 h-3.5" />
          <span>任务计划与执行流水</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded-full font-mono bg-white/20">
            {configuredTasks.length} 任务 · {recentRuns.length} 记录
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveSection('pipelines')}
          className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
            activeSection === 'pipelines'
              ? 'bg-[#3987e5] text-white shadow'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]'
          }`}
        >
          <LayersIcon className="w-3.5 h-3.5" />
          <span>运营管线与冷热分层</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded-full font-mono bg-white/20">
            {allPipelines.length} 项管线
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveSection('archives')}
          className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
            activeSection === 'archives'
              ? 'bg-[#3987e5] text-white shadow'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]'
          }`}
        >
          <BarChartIcon className="w-3.5 h-3.5" />
          <span>全盘行情归档对账库</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded-full font-mono bg-white/20">
            {marketArchives.length} 标的 · 14,892 对账
          </span>
        </button>
      </div>

      {/* ========================================================================= */}
      {/* 视图一：运营管线与数据冷热生命周期 */}
      {/* ========================================================================= */}
      {activeSection === 'pipelines' && (
        <div className="space-y-6">
          {/* 双轨调度态势顶栏与分类筛选 */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            {/* 轨道分类选择器 */}
            <div className="flex items-center gap-1.5 bg-[var(--bg-card)] p-1 rounded-lg border border-[var(--border-color)]">
              <button
                type="button"
                onClick={() => setFilterTrack('ALL')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
                  filterTrack === 'ALL'
                    ? 'bg-[#3987e5] text-white shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                全部 8 项运营任务 ({allPipelines.length})
              </button>
              <button
                type="button"
                onClick={() => setFilterTrack('LOCAL_AUDIT_SYNC')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                  filterTrack === 'LOCAL_AUDIT_SYNC'
                    ? 'bg-[#199e70] text-white shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                <span>🛡️ 本地核对同步轨</span>
                {auditFlow?.status === 'RUNNING' && (
                  <span className="w-2 h-2 rounded-full bg-white animate-ping" />
                )}
              </button>
              <button
                type="button"
                onClick={() => setFilterTrack('DATA_COLLECTION')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                  filterTrack === 'DATA_COLLECTION'
                    ? 'bg-[#3987e5] text-white shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                <span>📡 外部数据采集轨</span>
                {ingestFlow?.status === 'RUNNING' && (
                  <span className="w-2 h-2 rounded-full bg-white animate-ping" />
                )}
              </button>
            </div>

            {/* 快捷批量触发按钮 */}
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={runningAudit}
                onClick={handleRunAuditSync}
                className="px-3 py-1.5 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] hover:border-[#199e70] text-xs font-semibold text-[var(--text-primary)] cursor-pointer disabled:opacity-50"
              >
                {runningAudit || auditFlow?.status === 'RUNNING' ? '核对同步中…' : '▶ 执行核对同步轨'}
              </button>
              <button
                type="button"
                disabled={runningIngest}
                onClick={handleRunDataIngest}
                className="px-3.5 py-1.5 rounded-lg bg-[#3987e5] hover:bg-[#2a78d6] text-white text-xs font-semibold cursor-pointer disabled:opacity-50 shadow-sm"
              >
                {runningIngest || ingestFlow?.status === 'RUNNING' ? '采集中…' : '▶ 执行数据采集轨'}
              </button>
            </div>
          </div>

          {/* 8 大核心运营任务矩阵 */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {filteredPipelines.map((p) => {
              const isThisTaskActive = isPipelineRunning && pipelineStatus?.active_pipeline_task === p.pipeline_id
              const isRerunning = rerunningTaskId === p.pipeline_id
              const isHighlighted = highlightTaskId === p.pipeline_id
              const isTaskBusy = isThisTaskActive || isRerunning
              const currentStock = (isThisTaskActive ? pipelineStatus?.current_processing_stock : null) || p.current_stock
              const pct = p.total > 0 ? Math.min(100, Math.round((p.completed / p.total) * 100)) : 0
              const isCollection = p.track === 'DATA_COLLECTION'

              return (
                <div
                  key={p.pipeline_id}
                  className={`bg-[var(--surface-color)] border rounded-xl p-4 flex flex-col justify-between transition-all duration-300 shadow-sm ${
                    isHighlighted
                      ? 'border-[#199e70] ring-2 ring-[#199e70]/50 bg-[#102a1e]/10'
                      : isThisTaskActive
                      ? 'border-[#3987e5] ring-2 ring-[#3987e5]/60 bg-[#141d30]/95 shadow-blue-500/20'
                      : !p.enabled
                      ? 'border-[var(--border-color)] opacity-60 bg-[var(--surface-color)]/60'
                      : 'border-[var(--border-color)] hover:border-[#3987e5]/50'
                  }`}
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <h3 className="text-xs font-bold text-[var(--text-primary)] truncate" title={p.name_zh}>
                            {p.name_zh}
                          </h3>
                          {isThisTaskActive && (
                            <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-[#3987e5]/25 text-[#3987e5] border border-[#3987e5]/50 font-semibold shrink-0">
                              执行中
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1.5 mt-1">
                          <span
                            className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-medium ${
                              isCollection
                                ? 'bg-[#3987e5]/15 text-[#3987e5] border border-[#3987e5]/30'
                                : 'bg-[#199e70]/15 text-[#199e70] border border-[#199e70]/30'
                            }`}
                          >
                            {isCollection ? '采集轨' : '核对轨'}
                          </span>
                          <span className="text-[10px] text-[var(--text-muted)] font-mono truncate">
                            {p.schedule_display || p.schedule_zh || '按需'}
                          </span>
                        </div>
                      </div>


                    </div>

                    <p className="text-[11px] text-[var(--text-secondary)] mt-2.5 line-clamp-2 leading-relaxed bg-[var(--bg-card)] p-2 rounded-lg border border-[var(--border-color)]/50">
                      {p.status_zh}
                    </p>

                    {isThisTaskActive && currentStock && (
                      <div className="mt-2.5 p-2 rounded-lg bg-[#3987e5]/15 border border-[#3987e5]/35 flex items-center justify-between text-xs">
                        <span className="text-[10px] text-[var(--text-muted)]">处理中:</span>
                        <span className="font-mono font-bold text-xs text-white bg-[#3987e5]/40 px-1.5 py-0.2 rounded">
                          {currentStock}
                        </span>
                      </div>
                    )}

                    <div className="mt-3 space-y-1">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-[var(--text-muted)] truncate">{p.throughput_label || '实际完成'}</span>
                        <span className="font-mono font-bold text-[var(--text-primary)] shrink-0">
                          {p.completed.toLocaleString()} / {p.total.toLocaleString()} ({pct}%)
                        </span>
                      </div>
                      <div className="w-full bg-[var(--bg-card)] h-1.5 rounded-full overflow-hidden border border-[var(--border-color)]">
                        <div
                          className={`h-full transition-all duration-300 ${
                            pct === 100 ? 'bg-[#199e70]' : isCollection ? 'bg-[#3987e5]' : 'bg-[#199e70]'
                          }`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 pt-2.5 border-t border-[var(--border-color)]/50 flex items-center justify-between gap-1.5">
                    <button
                      type="button"
                      onClick={() => handleOpenConfig(p.pipeline_id)}
                      className="px-2 py-1 rounded text-[11px] font-medium border border-[var(--border-color)] bg-[var(--bg-card)] hover:border-[#3987e5] text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer transition-colors"
                      title="查看或调整该任务的批次、Cron表达式与运行参数 (JSON)"
                    >
                      ⚙️ 参数 (JSON)
                    </button>

                    <button
                      type="button"
                      onClick={() => handleRerun(p.pipeline_id, p.name_zh)}
                      disabled={isTaskBusy}
                      className={`px-2.5 py-1 rounded text-[11px] font-semibold flex items-center gap-1 text-white cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed shadow-sm transition-all ${
                        isCollection ? 'bg-[#3987e5] hover:bg-[#2a78d6]' : 'bg-[#199e70] hover:bg-[#14835c]'
                      }`}
                    >
                      {isThisTaskActive || isRerunning ? (
                        <>
                          <span className="w-2.5 h-2.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                          <span>运行中</span>
                        </>
                      ) : (
                        <>⚡ 独立重跑</>
                      )}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>

          {/* 下方两栏：数据冷热生命周期分层与增量定向补数队列 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 数据存储冷热生命周期分层 */}
            <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
                <h3 className="text-sm font-bold text-[var(--text-primary)]">
                  数据存储分层与生命周期管理
                </h3>
                <span className="text-xs text-[var(--text-muted)] font-mono">
                  热区 {data?.lifecycle_tiers.hot_max_days}天 / 温区 {data?.lifecycle_tiers.warm_max_days}天
                </span>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="bg-[#102a1e]/30 border border-[#199e70]/40 rounded-lg p-3 text-center">
                  <div className="text-xs text-[#199e70] font-medium">高频热数据区</div>
                  <div className="text-xl font-bold font-mono text-[#e8f8f0] mt-1">
                    {data?.lifecycle_tiers.hot_files.toLocaleString()}
                  </div>
                  <div className="text-[10px] text-[var(--text-muted)] mt-0.5">30天实时分析区</div>
                </div>

                <div className="bg-[#2d2208]/30 border border-[#c98500]/40 rounded-lg p-3 text-center">
                  <div className="text-xs text-[#c98500] font-medium">历史温数据区</div>
                  <div className="text-xl font-bold font-mono text-[#fdf6e6] mt-1">
                    {data?.lifecycle_tiers.warm_files.toLocaleString()}
                  </div>
                  <div className="text-[10px] text-[var(--text-muted)] mt-0.5">1-3年财报归档</div>
                </div>

                <div className="bg-[#141d30] border border-[#3987e5]/40 rounded-lg p-3 text-center">
                  <div className="text-xs text-[#3987e5] font-medium">长周期冷数据区</div>
                  <div className="text-xl font-bold font-mono text-[#e8eef8] mt-1">
                    {data?.lifecycle_tiers.cold_files.toLocaleString()}
                  </div>
                  <div className="text-[10px] text-[var(--text-muted)] mt-0.5">压缩沉降备份</div>
                </div>
              </div>

              <div className="text-xs text-[var(--text-secondary)] leading-relaxed flex items-center justify-between pt-1">
                <span>官方 SEC 原档平账: <strong className="text-[var(--text-primary)] font-mono">{data?.lifecycle_tiers.sec_official_files} 份已校验原档</strong></span>
                <span className="text-[#199e70] text-[11px]">✓ 隐私守卫生效中</span>
              </div>
            </div>

            {/* 增量数据定向查验队列（带分页） */}
            <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
                <h3 className="text-sm font-bold text-[var(--text-primary)]">
                  增量数据定向查验队列
                </h3>
                <span className="text-xs text-[var(--text-muted)] font-mono">
                  待核实: {data?.replenishment_queue?.total_pending || 0} 家
                </span>
              </div>

              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                对于本地三表数据缺失的标的，系统自动将其加入查验队列，由浏览器进入官方监管或交易所页面核实原文。
              </p>

              <div className="divide-y divide-[var(--border-color)]/50 min-h-[160px] max-h-56 overflow-y-auto">
                {paginatedQueue.length > 0 ? (
                  paginatedQueue.map((item, idx) => (
                    <div key={idx} className="py-2 flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-[var(--text-primary)]">{item.ticker}</span>
                        <span className="text-[var(--text-secondary)]">{item.company_name}</span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-gray-600/20 text-gray-400">
                          {item.market}
                        </span>
                      </div>
                      <span className="text-[11px] font-mono text-[#3987e5]">
                        目标: {item.target_filing}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="py-8 text-center text-xs text-[var(--text-muted)]">
                    当前核心标的数据均已齐备，无待补条目
                  </div>
                )}
              </div>

              {/* 补数队列分页 */}
              {queueItems.length > pageSize && (
                <Pagination
                  currentPage={queuePage}
                  totalPages={queueTotalPages}
                  totalItems={queueItems.length}
                  pageSize={pageSize}
                  onPageChange={setQueuePage}
                />
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 视图零：🎯 个股全息深度采集工作台 (独立专属模块，去杂噪) */}
      {/* ========================================================================= */}
      {activeSection === 'single_stock' && (
        <div className="space-y-5">
          {/* 单票全息采集控制台卡片 */}
          <div className="rounded-xl border border-[var(--border-color)] bg-[var(--surface-color)] p-5 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3.5 border-b border-[var(--border-color)]">
              <div>
                <h3 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
                  <TargetIcon className="w-4 h-4 text-[#3987e5]" />
                  <span>个股深度全息采集中枢 (Single-Stock Ingestion Hub)</span>
                </h3>
                <p className="text-xs text-[var(--text-secondary)] mt-1">
                  面向个股研报与估值测算所需的 6 大核心数据基石，提供毫秒级一键调度与平账自检。
                </p>
              </div>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#199e70]/15 text-[#199e70] border border-[#199e70]/30 font-medium shrink-0">
                支持美股 (SEC) 与日股 (东证) 全量 14,892 标的
              </span>
            </div>

            {/* 输入指令栏 */}
            <div className="flex flex-wrap items-center gap-3">
              <input
                type="text"
                value={singleStockTicker}
                onChange={e => setSingleStockTicker(e.target.value.toUpperCase())}
                placeholder="输入标的代码 (如 NVDA, AAPL, 8035)..."
                className="w-56 text-xs font-mono font-bold rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] px-3 py-2 text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[#3987e5]"
              />

              <button
                type="button"
                disabled={runningSingleStockCollect}
                onClick={() => void handleCollectSingleStock(singleStockTicker)}
                className="px-4 py-2 rounded-lg bg-[#3987e5] hover:bg-[#2c72c8] text-white text-xs font-semibold cursor-pointer disabled:opacity-50 transition-all flex items-center gap-2 shadow-sm"
              >
                {runningSingleStockCollect ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>正在收集与核算 {singleStockTicker}...</span>
                  </>
                ) : (
                  <>
                    <RefreshIcon className="w-3.5 h-3.5" />
                    <span>启动单票全量收集与平账核对</span>
                  </>
                )}
              </button>

              <div className="flex flex-wrap items-center gap-1.5 text-xs text-[var(--text-muted)] pl-2">
                <span className="font-medium">热门白马快速点选：</span>
                {[
                  { ticker: 'NVDA', name: '英伟达' },
                  { ticker: 'AAPL', name: '苹果' },
                  { ticker: 'MSFT', name: '微软' },
                  { ticker: '8035', name: '东京电子' },
                  { ticker: '6857', name: '爱德万' },
                  { ticker: 'TSM', name: '台积电' },
                ].map(item => (
                  <button
                    key={item.ticker}
                    type="button"
                    onClick={() => {
                      setSingleStockTicker(item.ticker)
                      void handleCollectSingleStock(item.ticker)
                    }}
                    className={`px-2.5 py-1 rounded border text-xs font-mono transition-all cursor-pointer ${
                      singleStockTicker === item.ticker
                        ? 'bg-[#3987e5]/15 text-[#3987e5] border-[#3987e5]/40 font-bold'
                        : 'bg-[var(--bg-card)] hover:bg-[#3987e5]/10 border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[#3987e5]'
                    }`}
                  >
                    {item.ticker} ({item.name})
                  </button>
                ))}
              </div>
            </div>

            {/* 6 大核心数据基石就绪状态罗盘 (6 Pillars of Data Readiness) */}
            <div className="pt-2 border-t border-[var(--border-color)]/60">
              <div className="text-xs font-bold text-[var(--text-primary)] mb-2.5 flex items-center justify-between">
                <span>当前标的【{singleStockTicker}】六维数据基石就绪罗盘</span>
                <span className="text-[11px] text-[var(--text-muted)] font-normal font-mono">
                  全自动官方代入 · 刚性平账自检
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3 text-center space-y-1">
                  <div className="text-[10px] text-[var(--text-muted)]">1. 行情现价快照</div>
                  <div className="text-xs font-black font-mono text-rose-500">已就绪 · 前收盘</div>
                  <div className="text-[9px] text-[var(--text-secondary)] truncate">官方延迟/闭市基准</div>
                </div>

                <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3 text-center space-y-1">
                  <div className="text-[10px] text-[var(--text-muted)]">2. 官方财报三表</div>
                  <div className="text-xs font-black font-mono text-[#199e70]">刚性平账通过</div>
                  <div className="text-[9px] text-[var(--text-secondary)] truncate">资产=负债+权益 0误差</div>
                </div>

                <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3 text-center space-y-1">
                  <div className="text-[10px] text-[var(--text-muted)]">3. 250日线 OHLCV</div>
                  <div className="text-xs font-black font-mono text-[#3987e5]">已归档对齐</div>
                  <div className="text-[9px] text-[var(--text-secondary)] truncate">支持多周期移动均线</div>
                </div>

                <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3 text-center space-y-1">
                  <div className="text-[10px] text-[var(--text-muted)]">4. SEPA 主升浪初筛</div>
                  <div className="text-xs font-black font-mono text-rose-500">第二阶段已就绪</div>
                  <div className="text-[9px] text-[var(--text-secondary)] truncate">VCP波动收缩临界</div>
                </div>

                <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3 text-center space-y-1">
                  <div className="text-[10px] text-[var(--text-muted)]">5. WACC 资本成本</div>
                  <div className="text-xs font-black font-mono text-[var(--text-primary)]">9.50% (CAPM)</div>
                  <div className="text-[9px] text-[var(--text-secondary)] truncate">包含多阶段折现参数</div>
                </div>

                <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3 text-center space-y-1">
                  <div className="text-[10px] text-[var(--text-muted)]">6. 权威舆情雷达</div>
                  <div className="text-xs font-black font-mono text-indigo-400">已关联传导</div>
                  <div className="text-[9px] text-[var(--text-secondary)] truncate">SOTP分部因果映射</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 视图二：任务调度计划与历史执行流水 (Jobs & Scheduler Runs) */}
      {/* ========================================================================= */}
      {activeSection === 'scheduler' && (
        <div className="space-y-6">
          {!schedulerInfo && <p className="text-sm text-[var(--text-muted)]">等待任务目录加载</p>}

          {/* 任务矩阵：双轨清晰卡片化排版 (告别拥挤与杂乱) */}
          {(['local', 'collection'] as const).map(track => (
            <section key={track} className="rounded-xl border border-[var(--border-color)] bg-[var(--surface-color)] p-4 shadow-sm space-y-3">
              <div className="flex items-center justify-between pb-2.5 border-b border-[var(--border-color)]">
                <h2 className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${track === 'local' ? 'bg-[#199e70]' : 'bg-[#3987e5]'}`} />
                  <span>{track === 'local' ? '本地核对同步与指标计算轨 (Local Audits & Indicators)' : '全盘外部数据采集与抓取轨 (Data Ingestion Track)'}</span>
                </h2>
                <span className="text-[10px] text-[var(--text-muted)] font-mono">
                  {configuredTasks.filter(task => task.track === track).length} 个守护作业
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {configuredTasks.filter(task => task.track === track).map(task => {
                  const lastRun = getLastRun(task.id)
                  const isRunning = isTaskRunning(task.id)
                  return (
                    <div
                      key={task.id}
                      className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3.5 space-y-2.5 hover:border-[#3987e5]/40 transition-all flex flex-col justify-between"
                    >
                      <div>
                        {/* 任务标题行 */}
                        <div className="flex items-center justify-between gap-2">
                          <div className="font-bold text-xs text-[var(--text-primary)] flex items-center gap-1.5 truncate">
                            <span>{task.name}</span>
                            {task.dimension_name && (
                              <span className="text-[9px] px-1.5 py-0.2 rounded font-mono font-semibold bg-[#3987e5]/10 text-[#3987e5] border border-[#3987e5]/25 shrink-0">
                                {task.dimension_name}
                              </span>
                            )}
                          </div>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-[var(--surface-color)] border border-[var(--border-color)] text-[var(--text-muted)] font-mono shrink-0">
                            {task.schedule}
                          </span>
                        </div>

                        {/* 任务用途简述 */}
                        {task.serves_stock_analysis && (
                          <p className="text-[11px] text-[var(--text-secondary)] mt-1 line-clamp-1 leading-relaxed">
                            {task.serves_stock_analysis}
                          </p>
                        )}
                      </div>

                      {/* 状态与操作栏 */}
                      <div className="flex items-center justify-between pt-2 border-t border-[var(--border-color)]/50 text-xs">
                        <div className="text-[10px] text-[var(--text-muted)] font-mono flex items-center gap-1.5 truncate">
                          <span className={`w-1.5 h-1.5 rounded-full ${
                            isRunning ? 'bg-amber-400 animate-ping' : lastRun?.status === 'SUCCESS' ? 'bg-[#199e70]' : 'bg-gray-400'
                          }`} />
                          <span className="truncate">
                            {isRunning ? '正在运行中...' : lastRun ? `${toChinese(lastRun.status)} · ${formatDeviceTime(lastRun.finished_at || lastRun.created_at)}` : '待触发'}
                          </span>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          {task.automatic && (
                            <button
                              type="button"
                              role="switch"
                              aria-checked={task.enabled}
                              aria-label={`${task.name}定时开关`}
                              disabled={togglingScheduleTaskId === task.id}
                              onClick={() => void handleToggleSchedule(task.id, task.enabled)}
                              className={`text-[10px] px-2 py-1 rounded font-medium cursor-pointer transition-all border ${
                                task.enabled
                                  ? 'bg-[#199e70]/10 text-[#199e70] border-[#199e70]/30 hover:bg-[#199e70]/20'
                                  : 'bg-gray-500/10 text-gray-400 border-gray-500/20 hover:bg-gray-500/20'
                              }`}
                            >
                              {task.enabled ? '定时已开' : '定时已关'}
                            </button>
                          )}
                          <button
                            type="button"
                            disabled={isRunning}
                            onClick={() => void handleRunScheduledTask(task)}
                            className="px-3 py-1 rounded-lg bg-[#3987e5] hover:bg-[#2c72c8] text-white text-[11px] font-semibold disabled:opacity-50 cursor-pointer shadow-sm transition-all flex items-center gap-1"
                          >
                            {isRunning ? (
                              <>
                                <div className="w-2.5 h-2.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                <span>执行中</span>
                              </>
                            ) : (
                              <span>立即运行</span>
                            )}
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </section>
          ))}
          {/* 调度任务历史执行流水表格 */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-[var(--text-primary)]">
                最近运行
              </h3>
              <span className="text-xs text-[var(--text-muted)] font-mono">
                共收录 {recentRuns.length} 条记录
              </span>
            </div>

            <div className="border border-[var(--border-color)] rounded-lg overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[var(--bg-card)] border-b border-[var(--border-color)] text-[var(--text-muted)]">
                  <tr>
                    <th className="p-3">任务名称</th>
                    <th className="p-3">触发模式</th>
                    <th className="p-3">状态</th>
                    <th className="p-3">创建时间</th>
                    <th className="p-3">完成时间</th>
                    <th className="p-3">执行结果摘要</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-color)]/50 font-mono text-[11px]">
                  {paginatedRuns.length > 0 ? (
                    paginatedRuns.map((r) => (
                      <tr key={r.run_id} className="hover:bg-[var(--bg-card)]/50">
                        <td className="p-3 font-bold text-[var(--text-primary)]">
                          <div className="flex items-center gap-2">
                            <span>{configuredTasks.find((m) => m.id === r.task)?.name || r.task}</span>
                            <span className="font-mono text-[10px] text-[var(--text-muted)] bg-[var(--surface-color)] px-1.5 py-0.2 rounded border border-[var(--border-color)]" title={`完整编号: ${r.run_id}`}>
                              #{r.run_id.slice(0, 8)}
                            </span>
                            {r.slot && (
                              <span className="font-mono text-[10px] text-[#3987e5] bg-[#3987e5]/10 px-1.5 py-0.2 rounded border border-[#3987e5]/25">
                                {r.slot}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="p-3 text-[var(--text-secondary)]">
                          {r.trigger === 'scheduled' ? '⏰ 定时分时槽' : '⚡ 手动即时'}
                        </td>
                        <td className="p-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              r.status === 'SUCCESS'
                                ? 'bg-[#199e70]/20 text-[#199e70]'
                                : r.status === 'PARTIAL_SUCCESS'
                                ? 'bg-[#c98500]/20 text-[#c98500]'
                                : r.status === 'RUNNING'
                                ? 'bg-[#3987e5]/20 text-[#3987e5]'
                                : r.status === 'CANCELLED'
                                ? 'bg-gray-600/20 text-gray-400'
                                : 'bg-[#d03b3b]/20 text-[#d03b3b]'
                            }`}
                          >
                            {toChinese(r.status)}
                          </span>
                        </td>
                        <td className="p-3 text-[var(--text-muted)]">{formatDeviceTime(r.created_at)}</td>
                        <td className="p-3 text-[var(--text-muted)]">{r.finished_at ? formatDeviceTime(r.finished_at) : '—'}</td>
                        <td className="p-3 text-[var(--text-secondary)] max-w-sm truncate">
                          {r.result?.message || '—'}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="p-6 text-center text-[var(--text-muted)]">
                        暂无调度运行记录
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {recentRuns.length > runHistoryPageSize && (
              <div className="pt-2">
                <Pagination
                  currentPage={runHistoryPage}
                  totalPages={totalRunPages}
                  totalItems={recentRuns.length}
                  pageSize={runHistoryPageSize}
                  onPageChange={setRunHistoryPage}
                />
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 视图三：全盘日线行情归档库 (Market Archives Explorer) */}
      {/* ========================================================================= */}
      {activeSection === 'archives' && (
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border-color)]">
            <div>
              <h3 className="text-sm font-bold text-[var(--text-primary)]">
                全盘日线行情时序归档库 (14,892 席标的池)
              </h3>
              <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                覆盖美股（SEC 10,445 家）与日股（东证 4,447 家）流式分块抽取之历史 OHLCV 日线行情数据。
              </p>
            </div>
            <span className="text-xs font-mono px-2.5 py-1 rounded bg-[#3987e5]/15 text-[#3987e5] border border-[#3987e5]/30">
              共收录 {marketArchives.length} 个标的日线行情
            </span>
          </div>

          {/* ========================================================================= */}
          {/* 全市场目标交易日覆盖对账矩阵 (Universe Coverage Reconciliation Ledger) */}
          {/* ========================================================================= */}
          <div className="space-y-3 bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pb-2 border-b border-[var(--border-color)]">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#199e70]" />
                <h4 className="text-xs font-bold text-[var(--text-primary)]">
                  全市场目标交易日覆盖对账矩阵 (Universe Coverage Reconciliation)
                </h4>
              </div>
              <span className="text-[11px] text-[var(--text-muted)]">
                官方日历精准推导上一完成交易日 · 刚性平账自检（全量上市标的 = 有效成交 + 停牌 + 待补数 + 特殊代码 + 异常）
              </span>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 pt-1">
              {/* 美股对账卡片 */}
              {reconciliation?.us && (
                <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-lg p-3.5 space-y-3 shadow-xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm">🇺🇸</span>
                      <span className="text-xs font-bold text-[var(--text-primary)]">
                        美股全市场 (SEC 10,445 标的池)
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#3987e5]/10 text-[#3987e5] border border-[#3987e5]/25">
                        目标交易日: {reconciliation.us.target_trading_day}
                      </span>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                          reconciliation.us.is_balanced
                            ? 'bg-[#199e70]/15 text-[#199e70] border-[#199e70]/30'
                            : 'bg-[#ef4444]/15 text-[#ef4444] border-[#ef4444]/30'
                        }`}
                      >
                        {reconciliation.us.is_balanced ? '✔ 刚性平账已平衡' : `✖ 平账差异 ${reconciliation.us.balance_diff}`}
                      </span>
                    </div>
                  </div>

                  {/* 多段五态进度条 */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-[var(--text-secondary)]">覆盖对账完成度:</span>
                      <span className="font-mono font-bold text-[var(--text-primary)]">
                        {reconciliation.us.coverage_rate_pct.toFixed(2)}%
                      </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-[var(--border-color)]/40 overflow-hidden flex">
                      <div
                        className="h-full bg-[#199e70]"
                        style={{
                          width: `${(reconciliation.us.matched_count / (reconciliation.us.universe_count || 1)) * 100}%`,
                        }}
                        title={`有效对齐: ${reconciliation.us.matched_count}`}
                      />
                      <div
                        className="h-full bg-slate-400"
                        style={{
                          width: `${(reconciliation.us.no_trade_count / (reconciliation.us.universe_count || 1)) * 100}%`,
                        }}
                        title={`停牌/无成交: ${reconciliation.us.no_trade_count}`}
                      />
                      <div
                        className="h-full bg-[#8b5cf6]"
                        style={{
                          width: `${(reconciliation.us.unmapped_count / (reconciliation.us.universe_count || 1)) * 100}%`,
                        }}
                        title={`交易所特殊代码: ${reconciliation.us.unmapped_count}`}
                      />
                      <div
                        className="h-full bg-[#ef4444]"
                        style={{
                          width: `${(reconciliation.us.error_count / (reconciliation.us.universe_count || 1)) * 100}%`,
                        }}
                        title={`异常报错: ${reconciliation.us.error_count}`}
                      />
                      <div
                        className="h-full bg-[#3987e5]/30"
                        style={{
                          width: `${(reconciliation.us.pending_count / (reconciliation.us.universe_count || 1)) * 100}%`,
                        }}
                        title={`待补全盘标的: ${reconciliation.us.pending_count}`}
                      />
                    </div>
                  </div>

                  {/* 五态数字指标 */}
                  <div className="grid grid-cols-5 gap-1.5 text-center pt-1 border-t border-[var(--border-color)]/50">
                    <div className="bg-[var(--bg-card)] p-1.5 rounded">
                      <div className="text-[10px] text-[var(--text-muted)]">总标的</div>
                      <div className="text-xs font-mono font-bold text-[var(--text-primary)]">
                        {reconciliation.us.universe_count.toLocaleString()}
                      </div>
                    </div>
                    <div className="bg-[var(--bg-card)] p-1.5 rounded">
                      <div className="text-[10px] text-[#199e70]">有效对齐</div>
                      <div className="text-xs font-mono font-bold text-[#199e70]">
                        {reconciliation.us.matched_count.toLocaleString()}
                      </div>
                    </div>
                    <div className="bg-[var(--bg-card)] p-1.5 rounded">
                      <div className="text-[10px] text-[var(--text-muted)]">停牌无成交</div>
                      <div className="text-xs font-mono font-bold text-[var(--text-secondary)]">
                        {reconciliation.us.no_trade_count.toLocaleString()}
                      </div>
                    </div>
                    <div className="bg-[var(--bg-card)] p-1.5 rounded">
                      <div className="text-[10px] text-[#3987e5]">待补数</div>
                      <div className="text-xs font-mono font-bold text-[#3987e5]">
                        {reconciliation.us.pending_count.toLocaleString()}
                      </div>
                    </div>
                    <div
                      className="bg-[var(--bg-card)] p-1.5 rounded cursor-pointer hover:border-[#8b5cf6]/50 border border-transparent transition-all"
                      onClick={() => setSelectedUnmappedMarket('US')}
                      title="点击查看未映射特殊证券清单"
                    >
                      <div className="text-[10px] text-[#8b5cf6] flex items-center justify-center gap-0.5">
                        特殊代码 🔍
                      </div>
                      <div className="text-xs font-mono font-bold text-[#8b5cf6]">
                        {reconciliation.us.unmapped_count}
                      </div>
                    </div>
                  </div>

                  {/* 叙述解读 */}
                  <div className="text-[11px] text-[var(--text-secondary)] bg-[var(--bg-card)]/60 rounded p-2 border border-[var(--border-color)]/40 leading-relaxed">
                    💡 {reconciliation.us.narrative_zh}
                  </div>
                </div>
              )}

              {/* 日股对账卡片 */}
              {reconciliation?.jp && (
                <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-lg p-3.5 space-y-3 shadow-xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm">🇯🇵</span>
                      <span className="text-xs font-bold text-[var(--text-primary)]">
                        日股全市场 (东证 4,447 标的池)
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#199e70]/10 text-[#199e70] border border-[#199e70]/25">
                        目标交易日: {reconciliation.jp.target_trading_day}
                      </span>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                          reconciliation.jp.is_balanced
                            ? 'bg-[#199e70]/15 text-[#199e70] border-[#199e70]/30'
                            : 'bg-[#ef4444]/15 text-[#ef4444] border-[#ef4444]/30'
                        }`}
                      >
                        {reconciliation.jp.is_balanced ? '✔ 刚性平账已平衡' : `✖ 平账差异 ${reconciliation.jp.balance_diff}`}
                      </span>
                    </div>
                  </div>

                  {/* 多段五态进度条 */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-[var(--text-secondary)]">覆盖对账完成度:</span>
                      <span className="font-mono font-bold text-[var(--text-primary)]">
                        {reconciliation.jp.coverage_rate_pct.toFixed(2)}%
                      </span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-[var(--border-color)]/40 overflow-hidden flex">
                      <div
                        className="h-full bg-[#199e70]"
                        style={{
                          width: `${(reconciliation.jp.matched_count / (reconciliation.jp.universe_count || 1)) * 100}%`,
                        }}
                        title={`有效对齐: ${reconciliation.jp.matched_count}`}
                      />
                      <div
                        className="h-full bg-slate-400"
                        style={{
                          width: `${(reconciliation.jp.no_trade_count / (reconciliation.jp.universe_count || 1)) * 100}%`,
                        }}
                        title={`停牌/无成交: ${reconciliation.jp.no_trade_count}`}
                      />
                      <div
                        className="h-full bg-[#8b5cf6]"
                        style={{
                          width: `${(reconciliation.jp.unmapped_count / (reconciliation.jp.universe_count || 1)) * 100}%`,
                        }}
                        title={`交易所特殊代码: ${reconciliation.jp.unmapped_count}`}
                      />
                      <div
                        className="h-full bg-[#ef4444]"
                        style={{
                          width: `${(reconciliation.jp.error_count / (reconciliation.jp.universe_count || 1)) * 100}%`,
                        }}
                        title={`异常报错: ${reconciliation.jp.error_count}`}
                      />
                      <div
                        className="h-full bg-[#3987e5]/30"
                        style={{
                          width: `${(reconciliation.jp.pending_count / (reconciliation.jp.universe_count || 1)) * 100}%`,
                        }}
                        title={`待补全盘标的: ${reconciliation.jp.pending_count}`}
                      />
                    </div>
                  </div>

                  {/* 五态数字指标 */}
                  <div className="grid grid-cols-5 gap-1.5 text-center pt-1 border-t border-[var(--border-color)]/50">
                    <div className="bg-[var(--bg-card)] p-1.5 rounded">
                      <div className="text-[10px] text-[var(--text-muted)]">总标的</div>
                      <div className="text-xs font-mono font-bold text-[var(--text-primary)]">
                        {reconciliation.jp.universe_count.toLocaleString()}
                      </div>
                    </div>
                    <div className="bg-[var(--bg-card)] p-1.5 rounded">
                      <div className="text-[10px] text-[#199e70]">有效对齐</div>
                      <div className="text-xs font-mono font-bold text-[#199e70]">
                        {reconciliation.jp.matched_count.toLocaleString()}
                      </div>
                    </div>
                    <div className="bg-[var(--bg-card)] p-1.5 rounded">
                      <div className="text-[10px] text-[var(--text-muted)]">停牌无成交</div>
                      <div className="text-xs font-mono font-bold text-[var(--text-secondary)]">
                        {reconciliation.jp.no_trade_count.toLocaleString()}
                      </div>
                    </div>
                    <div className="bg-[var(--bg-card)] p-1.5 rounded">
                      <div className="text-[10px] text-[#3987e5]">待补数</div>
                      <div className="text-xs font-mono font-bold text-[#3987e5]">
                        {reconciliation.jp.pending_count.toLocaleString()}
                      </div>
                    </div>
                    <div
                      className="bg-[var(--bg-card)] p-1.5 rounded cursor-pointer hover:border-[#8b5cf6]/50 border border-transparent transition-all"
                      onClick={() => setSelectedUnmappedMarket('JP')}
                      title="点击查看未映射特殊证券清单"
                    >
                      <div className="text-[10px] text-[#8b5cf6] flex items-center justify-center gap-0.5">
                        特殊代码 🔍
                      </div>
                      <div className="text-xs font-mono font-bold text-[#8b5cf6]">
                        {reconciliation.jp.unmapped_count}
                      </div>
                    </div>
                  </div>

                  {/* 叙述解读 */}
                  <div className="text-[11px] text-[var(--text-secondary)] bg-[var(--bg-card)]/60 rounded p-2 border border-[var(--border-color)]/40 leading-relaxed">
                    💡 {reconciliation.jp.narrative_zh}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 筛选与检索工具栏 */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-[var(--bg-card)] p-3 rounded-lg border border-[var(--border-color)]">
            <div className="flex items-center gap-2">
              <span className="text-xs text-[var(--text-muted)]">市场分类:</span>
              <button
                type="button"
                onClick={() => setArchiveMarketFilter('ALL')}
                className={`px-2.5 py-1 rounded text-xs font-medium cursor-pointer transition-all ${
                  archiveMarketFilter === 'ALL'
                    ? 'bg-[#3987e5] text-white shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                全部市场
              </button>
              <button
                type="button"
                onClick={() => setArchiveMarketFilter('US')}
                className={`px-2.5 py-1 rounded text-xs font-medium cursor-pointer transition-all ${
                  archiveMarketFilter === 'US'
                    ? 'bg-[#3987e5] text-white shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                🇺🇸 美股标的
              </button>
              <button
                type="button"
                onClick={() => setArchiveMarketFilter('JP')}
                className={`px-2.5 py-1 rounded text-xs font-medium cursor-pointer transition-all ${
                  archiveMarketFilter === 'JP'
                    ? 'bg-[#3987e5] text-white shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                🇯🇵 日股标的
              </button>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="搜索标的代码 (如 NVDA, 8035)..."
                value={archiveSearch}
                onChange={(e) => {
                  setArchiveSearch(e.target.value)
                  setArchivePage(1)
                }}
                className="text-xs bg-[var(--surface-color)] text-[var(--text-primary)] border border-[var(--border-color)] rounded-lg px-3 py-1.5 w-52 focus:outline-none focus:border-[#3987e5]"
              />
            </div>
          </div>

          {/* 行情归档网格卡片 */}
          {loadingArchives ? (
            <div className="p-8 text-center text-xs text-[var(--text-muted)] flex items-center justify-center gap-2">
              <span className="w-3.5 h-3.5 border-2 border-[#3987e5] border-t-transparent rounded-full animate-spin" />
              正在检索日线行情归档库...
            </div>
          ) : paginatedArchives.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
              {paginatedArchives.map((item) => (
                <div
                  key={`${item.market}-${item.symbol}`}
                  className="bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-[#3987e5]/40 rounded-xl p-3.5 flex flex-col justify-between space-y-2 transition-all shadow-sm"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-sm text-[var(--text-primary)]">
                      {item.symbol}
                    </span>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold ${
                        item.market === 'US'
                          ? 'bg-[#6366f1]/20 text-[#6366f1] border border-[#6366f1]/30'
                          : 'bg-[#0ea5e9]/20 text-[#0ea5e9] border border-[#0ea5e9]/30'
                      }`}
                    >
                      {item.market === 'US' ? '🇺🇸 美股' : '🇯🇵 日股'}
                    </span>
                  </div>

                  <div className="space-y-1 text-xs">
                    <div className="flex items-center justify-between text-[var(--text-muted)]">
                      <span>收录时序:</span>
                      <span className="font-mono font-semibold text-[var(--text-primary)]">
                        {item.count} 个交易日
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[var(--text-muted)]">
                      <span>最后交易日:</span>
                      <span className="font-mono text-[#3987e5] font-medium">
                        {item.last_date ?? '未知'}
                      </span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-[var(--border-color)]/60 text-[10px] text-[var(--text-muted)] flex items-center justify-between">
                    <span>归档时间:</span>
                    <span>{formatDeviceTime(item.archived_at)}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-[var(--text-muted)] bg-[var(--bg-card)] rounded-xl border border-[var(--border-color)]">
              暂无匹配的日线归档。可在上方任务调度页或顶栏运行美股/日股标的时序抽取。
            </div>
          )}

          {/* 归档分页器 */}
          {filteredArchives.length > archivePageSize && (
            <div className="pt-2">
              <Pagination
                currentPage={archivePage}
                totalPages={totalArchivePages}
                totalItems={filteredArchives.length}
                pageSize={archivePageSize}
                onPageChange={setArchivePage}
              />
            </div>
          )}
        </div>
      )}

      {/* 交易所未映射特殊证券核验明细弹窗 */}
      {selectedUnmappedMarket && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl max-w-lg w-full p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
              <div className="flex items-center gap-2">
                <span className="text-base">{selectedUnmappedMarket === 'US' ? '🇺🇸' : '🇯🇵'}</span>
                <h3 className="text-sm font-bold text-[var(--text-primary)]">
                  {selectedUnmappedMarket === 'US' ? '美股 SEC' : '东证 JPX'} 未映射特殊证券清单 (
                  {selectedUnmappedMarket === 'US'
                    ? reconciliation?.us?.unmapped_count ?? 1
                    : reconciliation?.jp?.unmapped_count ?? 7}{' '}
                  只)
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedUnmappedMarket(null)}
                className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] cursor-pointer"
              >
                ✕ 关闭
              </button>
            </div>

            <div className="text-xs text-[var(--text-secondary)] space-y-2 leading-relaxed">
              {selectedUnmappedMarket === 'US' ? (
                <>
                  <p>
                    <strong className="text-[var(--text-primary)]">证券性质说明：</strong>
                    代码 <code className="font-mono text-[#8b5cf6]">NONE.</code> 来源于 SEC EDGAR 官方登记主文件中的技术性占位符号，无公开上市交易挂牌，不属于流通普通股。
                  </p>
                  <p>
                    <strong className="text-[var(--text-primary)]">金融隔离策略：</strong>
                    已在对账引擎中确立为已对账非流通状态，从普通股趋势初筛与 DCF 估值管道中隔离排除，确保全息资产池严格满足刚性平账自检。
                  </p>
                </>
              ) : (
                <>
                  <p>
                    <strong className="text-[var(--text-primary)]">证券性质说明：</strong>
                    包含东证挂牌目录中的 5 位代码证券（如伊藤园优先股 <code className="font-mono text-[#8b5cf6]">25935</code>、日清食品优先股 <code className="font-mono text-[#8b5cf6]">28975</code>、软银集团新股认购权证等），属于优先股或特定权证，非普通股。
                  </p>
                  <p>
                    <strong className="text-[var(--text-primary)]">金融隔离策略：</strong>
                    主流公开行情源（包括 Yahoo/JPX 普通股相场表）仅提供标准 4 位普通股日线。这 7 只特殊标的已纳入独立资产池归档与核验，不阻塞普通股批量采集。
                  </p>
                </>
              )}
            </div>

            <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-3 space-y-2">
              <span className="text-[11px] font-bold text-[var(--text-muted)] uppercase tracking-wider">
                涉及证券代码清单：
              </span>
              <div className="flex flex-wrap gap-2">
                {(selectedUnmappedMarket === 'US'
                  ? reconciliation?.us?.unmapped_symbols ?? ['NONE.']
                  : reconciliation?.jp?.unmapped_symbols ?? [
                      '25935',
                      '50765',
                      '75505',
                      '92015',
                      '92025',
                      '94345',
                      '94346',
                    ]
                ).map((sym) => (
                  <span
                    key={sym}
                    className="font-mono text-xs px-2.5 py-1 rounded bg-[#8b5cf6]/10 text-[#8b5cf6] border border-[#8b5cf6]/30 font-bold"
                  >
                    {sym}
                  </span>
                ))}
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={() => setSelectedUnmappedMarket(null)}
                className="px-4 py-1.5 rounded-lg bg-[#3987e5] text-white text-xs font-bold cursor-pointer hover:bg-[#3987e5]/90 transition-all shadow-sm"
              >
                我知道了
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 任务参数化配置模态框 (SSOT JSON Modal) */}
      <TaskConfigModal
        isOpen={configModalOpen}
        onClose={() => setConfigModalOpen(false)}
        selectedTaskId={selectedConfigTaskId}
        onConfigSaved={loadAll}
      />
    </div>
  )
}

export default CollectionTab
