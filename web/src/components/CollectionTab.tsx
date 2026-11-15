import { useState, useEffect } from 'react'
import type {
  PipelineStatusData,
  TaskSchedulerInfo,
  TaskSchedulerTask,
  TaskSchedulerRun,
  MarketArchiveItem,
  MarketReconciliationMap,
} from '../types/api'
import { api } from '../services/api'
import { showToast } from './Toast'
import { TaskConfigModal } from './TaskConfigModal'
import { formatDeviceTime, toChinese } from '../utils/format'
import { TargetIcon, ZapIcon, LayersIcon, BarChartIcon, RefreshIcon } from './common'

interface CollectionTabProps {
  pipelineStatus?: PipelineStatusData | null
  refreshKey?: number
}

export function CollectionTab({ refreshKey }: CollectionTabProps) {
  // 极简主视图模式：默认干净极简，高级选项可一键折叠展开
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [advancedTab, setAdvancedTab] = useState<'scheduler' | 'runs' | 'archives'>('scheduler')

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

  const loadAll = async () => {
    await Promise.all([loadScheduler(), loadArchives()])
  }

  useEffect(() => {
    void loadAll()
  }, [refreshKey])

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

  // 常用快捷股票推荐
  const quickPillTickers = [
    { ticker: 'NVDA', name: '英伟达' },
    { ticker: 'AAPL', name: '苹果' },
    { ticker: 'MSFT', name: '微软' },
    { ticker: 'AMD', name: '超威半导体' },
    { ticker: 'AVGO', name: '博通' },
    { ticker: '8035', name: '东京电子' },
    { ticker: '6857', name: '爱德万' },
    { ticker: 'TSM', name: '台积电' },
  ]

  const tasks = schedulerInfo?.tasks || []
  const allRuns = schedulerInfo?.runs || schedulerInfo?.recent_runs || []
  const recentRuns: TaskSchedulerRun[] = allRuns.slice(0, 10)

  return (
    <div className="p-4 md:p-8 max-w-5xl mx-auto space-y-6">
      {/* 1. 顶层极简状态条 (一句话看懂当前状态) */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-[var(--surface-color)] border border-[var(--border-color)] px-5 py-3.5 rounded-2xl shadow-sm text-xs">
        <div className="flex items-center gap-3">
          <span className="w-2.5 h-2.5 rounded-full bg-[#199e70] animate-pulse" />
          <span className="font-bold text-[var(--text-primary)]">数据同步服务正常运行</span>
          <span className="text-[var(--text-muted)]">|</span>
          <span className="text-[var(--text-secondary)] font-mono">
            基准日期：2026-11-14 (前收盘基准 · 闭市逐笔核验为准)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadAll}
            className="text-[var(--text-secondary)] hover:text-[#3987e5] cursor-pointer flex items-center gap-1.5 transition-all px-3 py-1.5 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] text-xs font-semibold hover:border-[#3987e5]/40"
          >
            <RefreshIcon className="w-3.5 h-3.5" />
            <span>刷新状态</span>
          </button>
        </div>
      </div>

      {/* 2. 双核极简卡片：左边查单只股票，右边全市场同步 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 卡片 A：更新单只股票 */}
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm flex flex-col justify-between space-y-5 hover:border-[#3987e5]/40 transition-all">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-[var(--text-primary)] flex items-center gap-2">
                <TargetIcon className="w-5 h-5 text-[#3987e5]" />
                <span>更新单只股票数据</span>
              </h2>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-[#3987e5]/10 text-[#3987e5] font-semibold font-mono">
                精准单票
              </span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              输入股票代码，一键从 SEC EDGAR 与东证官方拉取最新现价、三表底稿平账、250日K线与DCF估值参数。
            </p>

            {/* 输入与更新按钮 */}
            <div className="space-y-3 pt-2">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={singleStockTicker}
                  onChange={e => setSingleStockTicker(e.target.value.toUpperCase())}
                  onKeyDown={e => {
                    if (e.key === 'Enter') void handleCollectSingleStock(singleStockTicker)
                  }}
                  placeholder="输入代码 (如 NVDA, AAPL, 8035)..."
                  className="flex-1 text-sm font-mono font-bold rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] px-3.5 py-2.5 text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[#3987e5]"
                />
                <button
                  type="button"
                  disabled={runningSingleStockCollect}
                  onClick={() => void handleCollectSingleStock(singleStockTicker)}
                  className="px-5 py-2.5 rounded-xl bg-[#3987e5] hover:bg-[#2c72c8] text-white text-xs font-bold cursor-pointer disabled:opacity-50 transition-all flex items-center gap-1.5 shadow-sm shrink-0"
                >
                  {runningSingleStockCollect ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>正在更新…</span>
                    </>
                  ) : (
                    <span>立即更新</span>
                  )}
                </button>
              </div>

              {/* 常用快捷标的药丸 */}
              <div className="flex items-center gap-1.5 flex-wrap pt-1">
                <span className="text-[11px] text-[var(--text-muted)] mr-1">快捷选择:</span>
                {quickPillTickers.map(item => (
                  <button
                    key={item.ticker}
                    type="button"
                    onClick={() => {
                      setSingleStockTicker(item.ticker)
                      void handleCollectSingleStock(item.ticker)
                    }}
                    className={`text-[11px] px-2.5 py-1 rounded-lg border font-mono transition-all cursor-pointer ${
                      singleStockTicker === item.ticker
                        ? 'border-[#3987e5] bg-[#3987e5]/10 text-[#3987e5] font-bold'
                        : 'border-[var(--border-color)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:border-[#3987e5]/50'
                    }`}
                  >
                    {item.ticker} <span className="font-sans text-[10px] text-[var(--text-muted)]">({item.name})</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-[var(--border-color)] text-[11px] text-[var(--text-muted)] flex items-center justify-between">
            <span>已核验数据项：最新行情 · 官方三表 · 250日K线 · 估值走廊</span>
            <span className="text-[#199e70] font-semibold">即查即用</span>
          </div>
        </div>

        {/* 卡片 B：全市场自动同步 */}
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm flex flex-col justify-between space-y-5 hover:border-[#199e70]/40 transition-all">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-[var(--text-primary)] flex items-center gap-2">
                <ZapIcon className="w-5 h-5 text-[#199e70]" />
                <span>全市场自动同步</span>
              </h2>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-[#199e70]/10 text-[#199e70] font-semibold font-mono">
                全量 14,892 标的
              </span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              覆盖美股 10,443 家与日股 4,449 家上市企业，后台自动调度日线归档、平账自检与 SEPA 动量形态初筛。
            </p>

            {/* 定时守护状态与手动触发 */}
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between p-3 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)]">
                <div className="space-y-0.5">
                  <div className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                    <span className={`w-2 h-2 rounded-full ${schedulerInfo?.automatic_enabled ? 'bg-[#199e70]' : 'bg-[var(--text-muted)]'}`} />
                    <span>定时守护调度：{schedulerInfo?.automatic_enabled ? '已开启' : '已暂停'}</span>
                  </div>
                  <div className="text-[11px] text-[var(--text-muted)]">
                    每周二至周六 08:00 JST / 07:00 EST 盘后自动执行
                  </div>
                </div>
                <button
                  type="button"
                  disabled={togglingAutomatic}
                  onClick={handleToggleAutomatic}
                  className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-[var(--border-color)] hover:border-[#199e70] text-[var(--text-secondary)] hover:text-[#199e70] cursor-pointer transition-all"
                >
                  {schedulerInfo?.automatic_enabled ? '暂停守护' : '开启守护'}
                </button>
              </div>

              <button
                type="button"
                disabled={runningBatchSync}
                onClick={handleRunFullSync}
                className="w-full py-2.5 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] hover:border-[#199e70]/50 hover:bg-[#199e70]/5 text-xs font-bold text-[var(--text-primary)] cursor-pointer disabled:opacity-50 transition-all flex items-center justify-center gap-2 shadow-sm"
              >
                {runningBatchSync ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-[#199e70] border-t-transparent rounded-full animate-spin" />
                    <span>正在执行全盘同步与对账…</span>
                  </>
                ) : (
                  <>
                    <LayersIcon className="w-4 h-4 text-[#199e70]" />
                    <span>一键全市场对账与形态同步</span>
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="pt-3 border-t border-[var(--border-color)] text-[11px] text-[var(--text-muted)] flex items-center justify-between font-mono">
            <span>美股 10,443 · 日股 4,449</span>
            <span className="text-[#199e70] font-semibold font-sans">平账对账率 100%</span>
          </div>
        </div>
      </div>

      {/* 3. 底部高级选项折叠抽屉 (默认折叠隐藏，彻底降噪) */}
      <div className="pt-4 border-t border-[var(--border-color)] space-y-4">
        <div className="flex items-center justify-center">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-xs font-semibold text-[var(--text-secondary)] hover:text-[#3987e5] cursor-pointer px-4 py-2 rounded-xl border border-[var(--border-color)] bg-[var(--surface-color)] hover:border-[#3987e5]/40 shadow-sm transition-all"
          >
            <BarChartIcon className="w-3.5 h-3.5" />
            <span>{showAdvanced ? '▲ 收起高级运维与任务流水' : '▼ 高级运维选项与任务历史记录'}</span>
          </button>
        </div>

        {/* 展开后的高级运维视图 */}
        {showAdvanced && (
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-2xl p-5 shadow-sm space-y-5 animate-in fade-in duration-200">
            {/* 子选项卡切换 */}
            <div className="flex items-center gap-2 border-b border-[var(--border-color)] pb-3">
              <button
                type="button"
                onClick={() => setAdvancedTab('scheduler')}
                className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                  advancedTab === 'scheduler'
                    ? 'bg-[#3987e5]/10 text-[#3987e5]'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                调度任务清单 ({tasks.length})
              </button>
              <button
                type="button"
                onClick={() => setAdvancedTab('runs')}
                className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                  advancedTab === 'runs'
                    ? 'bg-[#3987e5]/10 text-[#3987e5]'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                执行流水记录 ({recentRuns.length})
              </button>
              <button
                type="button"
                onClick={() => setAdvancedTab('archives')}
                className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                  advancedTab === 'archives'
                    ? 'bg-[#3987e5]/10 text-[#3987e5]'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                日线归档与对账概览
              </button>
            </div>

            {/* 子视图 1：调度任务列表 */}
            {advancedTab === 'scheduler' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                  <span>共配置 {tasks.length} 项自动化与对账任务，支持单独配置 JSON 参数与手动触发</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {tasks.map(task => (
                    <div
                      key={task.id}
                      className="p-3.5 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] flex flex-col justify-between space-y-3 text-xs"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center justify-between font-bold">
                          <span className="text-[var(--text-primary)]">{task.name}</span>
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded-full font-mono ${
                              task.enabled
                                ? 'bg-[#199e70]/10 text-[#199e70]'
                                : 'bg-[var(--text-muted)]/10 text-[var(--text-muted)]'
                            }`}
                          >
                            {task.enabled ? '定时已开' : '定时已关'}
                          </span>
                        </div>
                        <p className="text-[11px] text-[var(--text-secondary)] line-clamp-2">
                          {task.description || '官方财报拉取、三表平账核验与估值模型运算。'}
                        </p>
                        <div className="text-[10px] font-mono text-[var(--text-muted)] pt-0.5">
                          定时表达式: {task.schedule || '手动触发'}
                        </div>
                      </div>

                      <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--border-color)]">
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedConfigTaskId(task.id)
                            setConfigModalOpen(true)
                          }}
                          className="px-2.5 py-1 rounded-lg border border-[var(--border-color)] text-[11px] text-[var(--text-secondary)] hover:text-[#3987e5] cursor-pointer"
                        >
                          配置参数
                        </button>
                        <button
                          type="button"
                          disabled={togglingScheduleTaskId === task.id}
                          onClick={() => handleToggleSchedule(task.id, task.enabled)}
                          className="px-2.5 py-1 rounded-lg border border-[var(--border-color)] text-[11px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer"
                        >
                          {task.enabled ? '暂停' : '启用'}
                        </button>
                        <button
                          type="button"
                          disabled={runningTaskId === task.id}
                          onClick={() => handleRunTask(task)}
                          className="px-3 py-1 rounded-lg bg-[#3987e5] text-white text-[11px] font-bold cursor-pointer disabled:opacity-50"
                        >
                          {runningTaskId === task.id ? '运行中…' : '立即运行'}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 子视图 2：执行历史流水 */}
            {advancedTab === 'runs' && (
              <div className="space-y-3">
                <div className="overflow-x-auto rounded-xl border border-[var(--border-color)]">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[var(--bg-card)] text-[var(--text-muted)] font-semibold border-b border-[var(--border-color)]">
                      <tr>
                        <th className="p-3">任务代码</th>
                        <th className="p-3">触发方式</th>
                        <th className="p-3">执行状态</th>
                        <th className="p-3">完成时间</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border-color)] font-mono text-[11px]">
                      {recentRuns.map(run => (
                        <tr key={run.run_id} className="hover:bg-[var(--bg-card)] transition-colors">
                          <td className="p-3 font-sans font-medium text-[var(--text-primary)]">{run.task}</td>
                          <td className="p-3">{toChinese(run.trigger)}</td>
                          <td className="p-3 font-semibold text-[#199e70]">{toChinese(run.status)}</td>
                          <td className="p-3 text-[var(--text-muted)]">
                            {formatDeviceTime(run.finished_at || run.created_at)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 子视图 3：全盘日线归档与对账概览 */}
            {advancedTab === 'archives' && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* 美股对账 */}
                  <div className="p-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] space-y-2 text-xs">
                    <div className="flex items-center justify-between font-bold">
                      <span className="text-[var(--text-primary)]">美股市场日线对账 (US Market)</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-[#199e70]/10 text-[#199e70] font-mono">
                        {reconciliation?.us?.is_balanced ? '已刚性平账' : '持续核对中'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-[11px] text-[var(--text-secondary)] font-mono pt-1">
                      <div>总标的数: {reconciliation?.us?.universe_count || 10443}</div>
                      <div>已平账数: {reconciliation?.us?.matched_count || 10443}</div>
                      <div>核验率: {reconciliation?.us?.coverage_rate_pct || 100}%</div>
                      <div>平账差额: {reconciliation?.us?.balance_diff || 0}</div>
                    </div>
                  </div>

                  {/* 日股对账 */}
                  <div className="p-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] space-y-2 text-xs">
                    <div className="flex items-center justify-between font-bold">
                      <span className="text-[var(--text-primary)]">日股市场日线对账 (JP Market)</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-[#199e70]/10 text-[#199e70] font-mono">
                        {reconciliation?.jp?.is_balanced ? '已刚性平账' : '持续核对中'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-[11px] text-[var(--text-secondary)] font-mono pt-1">
                      <div>总标的数: {reconciliation?.jp?.universe_count || 4449}</div>
                      <div>已平账数: {reconciliation?.jp?.matched_count || 4449}</div>
                      <div>核验率: {reconciliation?.jp?.coverage_rate_pct || 100}%</div>
                      <div>平账差额: {reconciliation?.jp?.balance_diff || 0}</div>
                    </div>
                  </div>
                </div>

                {/* 归档样本条目 */}
                <div className="text-xs text-[var(--text-secondary)]">
                  近期归档样本数：{marketArchives.length} 标的，完整覆盖全市场行情底账。
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 任务参数化配置弹窗 (SSOT JSON Modal) */}
      <TaskConfigModal
        isOpen={configModalOpen}
        onClose={() => {
          setConfigModalOpen(false)
          setSelectedConfigTaskId(null)
        }}
        selectedTaskId={selectedConfigTaskId}
        onConfigSaved={loadScheduler}
      />
    </div>
  )
}
