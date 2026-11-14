import { useState, useEffect, useRef, useMemo } from 'react'
import type {
  CollectionOverviewData,
  CollectionPipelineItem,
  PipelineStatusData,
  TaskSchedulerInfo,
  TaskSchedulerRun,
  MarketArchiveItem,
} from '../types/api'
import { api } from '../services/api'
import { showToast } from './Toast'
import { Pagination } from './Pagination'
import { TaskConfigModal } from './TaskConfigModal'
import { formatDeviceTime, toChinese } from '../utils/format'

interface CollectionTabProps {
  pipelineStatus?: PipelineStatusData | null
}

interface TaskMeta {
  id: string
  name: string
  category: 'calc' | 'screening' | 'news' | 'indicator' | 'market' | 'audit'
  icon: string
  description: string
  scopeDetail: string
  defaultSchedule: string
  color: string
}

const TASK_METAS: TaskMeta[] = [
  {
    id: 'QUOTE_COLLECT',
    name: '权威行情与核心标的即时抽取',
    category: 'market',
    icon: '⚡',
    description: '24 项美股/日股核心指数、科技龙头与 AI 产业链权威报价即时抽取与美分级精度验签',
    scopeDetail: 'SPY, QQQ, DIA, SMH, TOPIX, NVDA, TSM, AVGO, MSFT, 软银, 东电等全盘核心资产，直接落盘不可篡改签名归档',
    defaultSchedule: '手动即时 / 盘中刷新',
    color: '#eab308',
  },
  {
    id: 'FINANCE_CALC',
    name: '24大专业金融模型与估值',
    category: 'calc',
    icon: '📊',
    description: '全量 24 大专业量化与金融估值模型矩阵及资产负债表刚性平账',
    scopeDetail: '严禁机械打分；多阶段DCF、反向DCF、EBO、WACC、Merton违约距离、Altman Z、Beneish M、GARCH、Kalman、Black-Litterman、CRR二叉树、SVI曲面、蒙特卡洛5000次模拟与SEPA全息测算',
    defaultSchedule: '手动即时 / 每日核算',
    color: '#3987e5',
  },
  {
    id: 'STOCK_SCREENING',
    name: '全盘标的收集与形态初筛',
    category: 'screening',
    icon: '🎯',
    description: '全盘 14,892 家上市企业（美股 10,445 + 日股 4,447）0-Token 纯本地形态初筛',
    scopeDetail: '纯本地数学计算 50/150/200 日均线多头排列、52周高点与 VCP 波动收缩形态，零 Token 消耗',
    defaultSchedule: '周二至周六 08:00 JST',
    color: '#199e70',
  },
  {
    id: 'OFFICIAL_NEWS',
    name: '官方资讯分时采集',
    category: 'news',
    icon: '⚡',
    description: '官方监管机构与交易所权威 RSS/资讯分时间采集与脉冲抽取',
    scopeDetail: 'SEC、东证、美联储与权威通讯社公开信源；自动事实核验与传闻隔离归档',
    defaultSchedule: '分时间采集：每小时脉冲',
    color: '#d03b3b',
  },
  {
    id: 'INDICATOR_UPDATE',
    name: '金融指标与宽度计算',
    category: 'indicator',
    icon: '📈',
    description: '宏观流动性基准利率与全市场 14,892 家多头趋势宽度走廊测算',
    scopeDetail: '10年期美债 (DGS10)、EFFR 基准利率、VIX 波动率及全市场 50日/200日均线上方股票占比',
    defaultSchedule: '分时间采集：每小时自动计算',
    color: '#c98500',
  },
  {
    id: 'US_DAILY',
    name: '美股全盘标的时序抽取',
    category: 'market',
    icon: '🇺🇸',
    description: '美股全盘 10,445 家上市主体（SEC 登记全量 105 批次流式分块）日线抽取与归档',
    scopeDetail: '覆盖 SEC 官方全量 10,445 家上市主体，流式分块抓取日线 OHLCV、宽基指数与美债基准，严格时效验签',
    defaultSchedule: '周二至周六 07:00 JST (收盘)',
    color: '#6366f1',
  },
  {
    id: 'JP_DAILY',
    name: '日股全盘标的时序抽取',
    category: 'market',
    icon: '🇯🇵',
    description: '日股全盘 4,447 家上市主体（东证登记全量 45 批次流式分块）日线抽取与归档',
    scopeDetail: '覆盖东京证券交易所 Prime/Standard/Growth 全量 4,447 家上市主体，流式分块抓取日线与日经波动率',
    defaultSchedule: '周一至周五 16:00 JST (收盘)',
    color: '#0ea5e9',
  },
  {
    id: 'LOCAL_AUDIT',
    name: '本地数据与账本核验',
    category: 'audit',
    icon: '🛡️',
    description: '三表刚性平账、离线数据源完整性与预测账本密码学 SHA-256 验签',
    scopeDetail: '资产=负债+所有者权益公式断言；PredictionLedger 链条验签，杜绝代码硬编码对账',
    defaultSchedule: '手动即时校验',
    color: '#10b981',
  },
  {
    id: 'INCREMENTAL_COLLECT',
    name: '官方监管补数与档案归档',
    category: 'audit',
    icon: '📑',
    description: '官方监管补数定向队列核验与深度档案增量归档',
    scopeDetail: '72 家待进入监管/交易所页面核验原文，流式分批热/温/冷生命周期安全归档',
    defaultSchedule: '每小时扫描补数队列',
    color: '#8b5cf6',
  },
]

export function CollectionTab({ pipelineStatus }: CollectionTabProps) {
  // 当前子模块视图：运营管线 | 调度计划与流水 | 全盘日线归档
  const [activeSection, setActiveSection] = useState<'pipelines' | 'scheduler' | 'archives'>('pipelines')

  // 1. 运营管线状态
  const [filterTrack, setFilterTrack] = useState<'ALL' | 'LOCAL_AUDIT_SYNC' | 'DATA_COLLECTION'>('ALL')
  const [data, setData] = useState<CollectionOverviewData | null>(null)
  const [configModalOpen, setConfigModalOpen] = useState(false)
  const [selectedConfigTaskId, setSelectedConfigTaskId] = useState<string | null>(null)
  const [rerunningTaskId, setRerunningTaskId] = useState<string | null>(null)
  const [togglingTaskId, setTogglingTaskId] = useState<string | null>(null)
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

  // 3. 全盘日线归档状态 (Market Archives)
  const [marketArchives, setMarketArchives] = useState<MarketArchiveItem[]>([])
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

  // 加载全盘日线行情归档底账
  const loadArchives = async () => {
    try {
      setLoadingArchives(true)
      const res = await api.getMarketArchives()
      if (res.ok && res.data?.items) {
        setMarketArchives(res.data.items)
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
    if (runningAudit || pipelineStatus?.is_running) return
    setRunningAudit(true)
    showToast({
      type: 'info',
      title: '启动本地核对同步',
      message: '正在对齐财报三表平账、最新日线行情时效与密码学账本验签…',
    })
    try {
      const res = await api.startPipeline('local_audit_sync', 'ALL')
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
  const handleRunDataIngest = async (market: 'ALL' | 'US' | 'JP' = 'ALL') => {
    if (runningIngest || pipelineStatus?.is_running) return
    setRunningIngest(true)
    showToast({
      type: 'info',
      title: '启动增量数据采集',
      message: `正在扫描并拉取 ${market === 'ALL' ? '全市场' : market} 增量行情与官方原档…`,
    })
    try {
      const res = await api.startPipeline('incremental_replenish', market)
      if (res.ok) {
        showToast({
          type: 'success',
          title: '数据采集任务已入队',
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

  // 4. 采集管线子开关切换
  const handleToggle = async (pipeline: CollectionPipelineItem) => {
    const nextState = !pipeline.enabled
    setTogglingTaskId(pipeline.pipeline_id)
    try {
      const res = await api.toggleCollectionTask(pipeline.pipeline_id, nextState)
      if (res.ok) {
        showToast({
          type: nextState ? 'success' : 'warning',
          title: `任务子开关: ${pipeline.name_zh}`,
          message: nextState ? '已启用（将参与全局流水线调度）' : '已停用（全局执行时将跳过此阶段）',
        })
        setData(prev => {
          if (!prev) return prev
          return {
            ...prev,
            pipelines: prev.pipelines.map(p =>
              p.pipeline_id === pipeline.pipeline_id ? { ...p, enabled: nextState } : p
            ),
          }
        })
      }
    } catch (err: any) {
      showToast({ type: 'error', title: '切换开关失败', message: err.message })
    } finally {
      setTogglingTaskId(null)
    }
  }

  // 5. 调度器任务触发运行
  const handleRunScheduledTask = async (taskMeta: TaskMeta) => {
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

  // 6. 切换调度器定时配置
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

  const isTaskEnabled = (taskId: string) => {
    const found = configuredTasks.find((t) => t.id === taskId)
    return found ? found.enabled : true
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
      {/* 顶部标题与快速参数中枢入口 */}
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-base font-bold text-[var(--text-primary)] flex items-center gap-2">
            <span>数据运营调度与任务中枢</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#3987e5]/15 text-[#3987e5] border border-[#3987e5]/30 font-medium">
              全盘数据运营原生工作台
            </span>
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            融合「运营管线与生命周期」、「分时调度与执行流水」以及「全盘日线归档底账」，支持独立阻塞重跑与 JSON 参数化配置 (SSOT)。
          </p>
        </div>

        {/* 顶部操作：打开全局任务参数中枢 */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={() => handleOpenConfig()}
            className="px-3.5 py-1.5 rounded-lg border border-[#3987e5]/40 bg-[#3987e5]/10 hover:bg-[#3987e5]/20 text-[#3987e5] text-xs font-semibold cursor-pointer transition-all flex items-center gap-1.5 shadow-sm"
          >
            <span>⚙️ 任务参数配置 (SSOT JSON)</span>
          </button>
          <button
            type="button"
            onClick={loadAll}
            className="px-3 py-1.5 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] hover:text-[#3987e5] text-xs font-medium cursor-pointer"
          >
            ↻ 刷新数据
          </button>
        </div>
      </div>

      {/* 原生三栏内嵌模块选择器 (拒绝新增外部页面，直接在采集中心内切换功能视图) */}
      <div className="flex items-center gap-2 bg-[var(--surface-color)] border border-[var(--border-color)] p-1.5 rounded-xl shadow-sm overflow-x-auto">
        <button
          type="button"
          onClick={() => setActiveSection('pipelines')}
          className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
            activeSection === 'pipelines'
              ? 'bg-[#3987e5] text-white shadow'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]'
          }`}
        >
          <span>🎛️ 运营管线与生命周期</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-white/20">
            {allPipelines.length}项
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
          <span>⚡ 任务计划与执行流水</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-white/20">
            {TASK_METAS.length}任务 · {recentRuns.length}记录
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
          <span>📈 全盘日线行情归档底账</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-white/20">
            {marketArchives.length}标的
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
                disabled={isPipelineRunning || runningAudit}
                onClick={handleRunAuditSync}
                className="px-3 py-1.5 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] hover:border-[#199e70] text-xs font-semibold text-[var(--text-primary)] cursor-pointer disabled:opacity-50"
              >
                {runningAudit || auditFlow?.status === 'RUNNING' ? '核对同步中…' : '▶ 执行核对同步轨'}
              </button>
              <button
                type="button"
                disabled={isPipelineRunning || runningIngest}
                onClick={() => handleRunDataIngest('ALL')}
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
              const isToggling = togglingTaskId === p.pipeline_id
              const isHighlighted = highlightTaskId === p.pipeline_id
              const isTaskBusy = isThisTaskActive || isRerunning
              const currentStock = (isThisTaskActive ? pipelineStatus?.current_processing_stock : null) || p.current_stock
              const pct = p.total > 0 ? Math.min(100, Math.round((p.completed / p.total) * 100)) : 100
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

                      {/* 参与调度子开关 */}
                      <div className="shrink-0 flex items-center">
                        <button
                          type="button"
                          onClick={() => handleToggle(p)}
                          disabled={isToggling || isTaskBusy}
                          title={p.enabled ? '已启用（点击停用）' : '已停用（点击启用）'}
                          className={`relative inline-flex h-4 w-7 shrink-0 cursor-pointer rounded-full border border-transparent transition-colors duration-200 ease-in-out ${
                            p.enabled ? (isCollection ? 'bg-[#3987e5]' : 'bg-[#199e70]') : 'bg-gray-600'
                          }`}
                        >
                          <span
                            className={`pointer-events-none inline-block h-3 w-3 transform rounded-full bg-white ring-0 transition duration-200 ease-in-out ${
                              p.enabled ? 'translate-x-3' : 'translate-x-0'
                            }`}
                          />
                        </button>
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
                      disabled={isTaskBusy || !p.enabled}
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
                <span>官方 SEC 原档底账: <strong className="text-[var(--text-primary)] font-mono">{data?.lifecycle_tiers.sec_official_files} 份已校验原档</strong></span>
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
      {/* 视图二：任务调度计划与历史执行流水 (Jobs & Scheduler Runs) */}
      {/* ========================================================================= */}
      {activeSection === 'scheduler' && (
        <div className="space-y-6">
          {/* 活动运行任务横幅 */}
          {activeRuns.length > 0 && (
            <div className="bg-[#3987e5]/10 border border-[#3987e5]/40 rounded-xl p-4 space-y-2 animate-pulse">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-[#3987e5] flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#3987e5] animate-ping" />
                  当前正在执行 {activeRuns.length} 个后台任务
                </span>
                <span className="text-[11px] text-[var(--text-muted)] font-mono">
                  线程池并发分配中 · 数据库事务锁安全
                </span>
              </div>
              <div className="flex flex-wrap gap-2 pt-1">
                {activeRuns.map((run) => (
                  <div
                    key={run.run_id}
                    className="bg-[var(--surface-color)] border border-[#3987e5]/40 px-3 py-1.5 rounded-md text-xs flex items-center gap-2 font-mono"
                  >
                    <div className="w-2.5 h-2.5 border-2 border-[#3987e5] border-t-transparent rounded-full animate-spin" />
                    <span className="font-bold text-[var(--text-primary)]">
                      {TASK_METAS.find((m) => m.id === run.task)?.name || run.task}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#3987e5]/20 text-[#3987e5]">
                      {toChinese(run.status)}
                    </span>
                    <span className="text-[10px] text-[var(--text-muted)]">
                      ID: {run.run_id.slice(0, 8)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 9 项调度任务卡片矩阵 */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {TASK_METAS.map((meta) => {
              const isRunning = isTaskRunning(meta.id)
              const isEnabled = isTaskEnabled(meta.id)
              const lastRun = getLastRun(meta.id)
              const isToggling = togglingScheduleTaskId === meta.id

              return (
                <div
                  key={meta.id}
                  className="bg-[var(--surface-color)] border border-[var(--border-color)] hover:border-[#3987e5]/40 rounded-xl p-4 flex flex-col justify-between transition-all shadow-sm space-y-3"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-xl shrink-0">{meta.icon}</span>
                        <h3 className="text-xs font-bold text-[var(--text-primary)] truncate">
                          {meta.name}
                        </h3>
                      </div>
                      <span
                        className="text-[10px] px-2 py-0.5 rounded-full font-mono shrink-0 font-medium"
                        style={{
                          backgroundColor: `${meta.color}15`,
                          color: meta.color,
                          border: `1px solid ${meta.color}35`,
                        }}
                      >
                        {meta.defaultSchedule}
                      </span>
                    </div>

                    <p className="text-[11px] text-[var(--text-secondary)] mt-2 leading-relaxed">
                      {meta.description}
                    </p>
                    <p className="text-[10px] text-[var(--text-muted)] mt-1 line-clamp-2 leading-normal">
                      {meta.scopeDetail}
                    </p>
                  </div>

                  {/* 最近运行摘要 */}
                  <div className="pt-2 border-t border-[var(--border-color)]/60 text-[10px] space-y-1">
                    <div className="flex items-center justify-between text-[var(--text-muted)]">
                      <span>最近运行:</span>
                      {lastRun ? (
                        <span
                          className={`font-semibold px-1.5 py-0.2 rounded ${
                            lastRun.status === 'SUCCESS'
                              ? 'bg-[#199e70]/20 text-[#199e70]'
                              : lastRun.status === 'PARTIAL_SUCCESS'
                              ? 'bg-[#c98500]/20 text-[#c98500]'
                              : lastRun.status === 'RUNNING'
                              ? 'bg-[#3987e5]/20 text-[#3987e5]'
                              : 'bg-[#d03b3b]/20 text-[#d03b3b]'
                          }`}
                        >
                          {toChinese(lastRun.status)} ({lastRun.finished_at ? formatDeviceTime(lastRun.finished_at) : '刚刚'})
                        </span>
                      ) : (
                        <span>未执行</span>
                      )}
                    </div>
                    {lastRun?.result?.message && (
                      <p className="text-[10px] text-[var(--text-secondary)] truncate font-mono">
                        {lastRun.result.message}
                      </p>
                    )}
                  </div>

                  {/* 操作栏 */}
                  <div className="flex items-center justify-between gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => handleToggleSchedule(meta.id, isEnabled)}
                      disabled={isToggling}
                      className={`text-[11px] px-2.5 py-1 rounded border font-medium flex items-center gap-1.5 transition-all cursor-pointer ${
                        isEnabled
                          ? 'bg-[var(--bg-card)] text-[var(--text-secondary)] border-[var(--border-color)] hover:border-[#3987e5]'
                          : 'bg-gray-800/40 text-gray-400 border-gray-700/50'
                      }`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${isEnabled ? 'bg-[#199e70]' : 'bg-gray-500'}`} />
                      <span>{isEnabled ? '定时开启' : '已暂停'}</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleRunScheduledTask(meta)}
                      disabled={isRunning}
                      className={`text-xs px-3 py-1.5 rounded-lg font-bold flex items-center gap-1.5 transition-all shadow-sm cursor-pointer ${
                        isRunning
                          ? 'bg-[#3987e5]/20 text-[#3987e5] border border-[#3987e5]/40 cursor-not-allowed'
                          : 'bg-[#3987e5] hover:bg-[#2b74cf] text-white active:scale-95'
                      }`}
                    >
                      {isRunning ? (
                        <>
                          <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                          <span>执行中...</span>
                        </>
                      ) : (
                        <>
                          <span>▶</span>
                          <span>立即执行</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>

          {/* 调度任务历史执行流水表格 */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-[var(--text-primary)]">
                调度任务历史执行流水 (SQLite 密码学断点持久化)
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
                          {TASK_METAS.find((m) => m.id === r.task)?.name || r.task}
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
      {/* 视图三：全盘日线行情归档底账 (Market Archives Explorer) */}
      {/* ========================================================================= */}
      {activeSection === 'archives' && (
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border-color)]">
            <div>
              <h3 className="text-sm font-bold text-[var(--text-primary)]">
                全盘日线行情时序归档底账 (14,892 上市标的池)
              </h3>
              <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                覆盖美股（SEC 10,445 家）与日股（东证 4,447 家）流式分块抽取之历史 OHLCV 日线底账。
              </p>
            </div>
            <span className="text-xs font-mono px-2.5 py-1 rounded bg-[#3987e5]/15 text-[#3987e5] border border-[#3987e5]/30">
              共收录 {marketArchives.length} 个标的行情底账
            </span>
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
              正在检索日线行情归档底账...
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
