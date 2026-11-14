import { useState, useEffect, useRef } from 'react'
import type { CollectionOverviewData, CollectionPipelineItem, PipelineStatusData } from '../types/api'
import { api } from '../services/api'
import { showToast } from './Toast'
import { Pagination } from './Pagination'
import { TaskConfigModal } from './TaskConfigModal'

interface CollectionTabProps {
  pipelineStatus?: PipelineStatusData | null
}

export function CollectionTab({ pipelineStatus }: CollectionTabProps) {
  const [filterTrack, setFilterTrack] = useState<'ALL' | 'LOCAL_AUDIT_SYNC' | 'DATA_COLLECTION'>('ALL')
  const [data, setData] = useState<CollectionOverviewData | null>(null)

  // 任务参数化配置模态框状态 (SSOT JSON)
  const [configModalOpen, setConfigModalOpen] = useState(false)
  const [selectedConfigTaskId, setSelectedConfigTaskId] = useState<string | null>(null)

  const [rerunningTaskId, setRerunningTaskId] = useState<string | null>(null)
  const [togglingTaskId, setTogglingTaskId] = useState<string | null>(null)
  const [highlightTaskId, setHighlightTaskId] = useState<string | null>(null)
  const [runningAudit, setRunningAudit] = useState(false)
  const [runningIngest, setRunningIngest] = useState(false)

  // 补数队列分页
  const [queuePage, setQueuePage] = useState(1)
  const prevRunningRef = useRef(false)

  const loadAll = async () => {
    try {
      const colRes = await api.getCollectionOverview()
      if (colRes.ok) setData(colRes.data)
    } catch (err) {
      console.error('Failed to load collection overview:', err)
    }
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

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6">
      {/* 顶部标题与快速参数中枢入口 */}
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-base font-bold text-[var(--text-primary)] flex items-center gap-2">
            <span>数据运营调度与任务中枢</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#3987e5]/15 text-[#3987e5] border border-[#3987e5]/30 font-medium">
              全盘 8 项运营任务体系
            </span>
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            双轨解耦调度：「本地核对同步轨」与「增量数据采集轨」，支持单阶段独立阻塞重跑与 JSON 参数化配置 (SSOT)。
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
        </div>
      </div>

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

      {/* 8 大核心运营任务矩阵 (准确反映各项任务，包含独立子开关、重跑与 JSON 参数配置) */}
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
                {/* 标题 + 轨道标签 + 独立子开关 */}
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

                {/* 说明文本 */}
                <p className="text-[11px] text-[var(--text-secondary)] mt-2.5 line-clamp-2 leading-relaxed bg-[var(--bg-card)] p-2 rounded-lg border border-[var(--border-color)]/50">
                  {p.status_zh}
                </p>

                {/* 实时处理标的 */}
                {isThisTaskActive && currentStock && (
                  <div className="mt-2.5 p-2 rounded-lg bg-[#3987e5]/15 border border-[#3987e5]/35 flex items-center justify-between text-xs">
                    <span className="text-[10px] text-[var(--text-muted)]">处理中:</span>
                    <span className="font-mono font-bold text-xs text-white bg-[#3987e5]/40 px-1.5 py-0.2 rounded">
                      {currentStock}
                    </span>
                  </div>
                )}

                {/* 进度条与实际吞吐底账 */}
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

              {/* 底栏：参数配置按钮 + 独立重跑 */}
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
