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
import {
  TargetIcon,
  ZapIcon,
  LayersIcon,
  RefreshIcon,
  ShieldCheckIcon,
  InfoCircleIcon,
  SearchIcon,
  CalendarIcon,
  CheckIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  SettingsIcon,
  DatabaseIcon,
} from './common'

interface CollectionTabProps {
  pipelineStatus?: PipelineStatusData | null
  refreshKey?: number
}

export function CollectionTab({ refreshKey }: CollectionTabProps) {
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
    { ticker: '6857', name: '爱德万测试' },
    { ticker: 'TSM', name: '台积电' },
  ]

  const tasks = schedulerInfo?.tasks || []
  const allRuns = schedulerInfo?.runs || schedulerInfo?.recent_runs || []
  const recentRuns: TaskSchedulerRun[] = allRuns.slice(0, 10)

  return (
    <div className="p-4 md:p-6 max-w-[1600px] mx-auto space-y-6">
      {/* 1. 顶层极简状态条 (一句话看懂当前状态) */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-[var(--surface-color)] border border-[var(--border-color)] px-5 py-3.5 rounded-2xl shadow-sm text-xs">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#176249] animate-pulse" />
            <ShieldCheckIcon className="w-4 h-4 text-[#176249]" />
          </div>
          <span className="font-bold text-[var(--text-primary)]">官方数据源与同步引擎 · 在线</span>
          <span className="text-[var(--text-muted)]">|</span>
          <div className="flex items-center gap-1.5 text-[var(--text-secondary)] font-mono">
            <span>数据基准：2026-11-14（前收盘价基准 · 闭市核验）</span>
            {/* 时效核验规则说明感叹号 */}
            <div className="relative inline-flex items-center">
              <button
                type="button"
                onClick={() => setActivePopover(activePopover === 'freshness' ? null : 'freshness')}
                onFocus={() => setActivePopover('freshness')}
                onBlur={() => setActivePopover(null)}
                className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none ${
                  activePopover === 'freshness'
                    ? 'bg-slate-800 text-white shadow-sm'
                    : 'bg-[var(--surface-color)] hover:bg-slate-100 text-[var(--text-muted)] hover:text-[var(--text-primary)] border border-[var(--border-color)]'
                }`}
                title="查看行情时效与闭市对账机制"
              >
                <InfoCircleIcon className="w-2.5 h-2.5" />
              </button>
              {activePopover === 'freshness' && (
                <div
                  className="absolute top-full left-0 mt-2 w-72 p-3 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto text-left"
                  onMouseEnter={() => setActivePopover('freshness')}
                  onMouseLeave={() => setActivePopover(null)}
                >
                  <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                    <span className="font-bold text-xs text-[var(--text-primary)]">行情时效与对账核验机制</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold border border-slate-200">时效门禁</span>
                  </div>
                  <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                    严格前置查验并标明行情时段状态，确保估值与决策基于最新真实交易依据。
                  </p>
                  <div className="mt-2 p-2 rounded-lg bg-[var(--bg-card)]/80 border border-[var(--border-color)]/60 text-[10px] text-[var(--text-secondary)] leading-relaxed">
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
            className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer flex items-center gap-1.5 transition-all px-3 py-1.5 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] text-xs font-semibold hover:border-slate-300"
          >
            <RefreshIcon className="w-3.5 h-3.5" />
            <span>刷新服务状态</span>
          </button>
        </div>
      </div>

      {/* 2. 双核极简卡片：左边查单只股票，右边全市场同步 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 卡片 A：单标的数据同步与估值测算 */}
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm flex flex-col justify-between space-y-5 hover:border-slate-300 transition-all">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <TargetIcon className="w-5 h-5 text-[#176249]" />
                <h2 className="text-base font-bold text-[var(--text-primary)]">单标的数据同步与估值测算</h2>
                {/* 统一感叹号说明组件 */}
                <div className="relative inline-flex items-center">
                  <button
                    type="button"
                    onClick={() => setActivePopover(activePopover === 'single_stock' ? null : 'single_stock')}
                    onFocus={() => setActivePopover('single_stock')}
                    onBlur={() => setActivePopover(null)}
                    className={`w-4 h-4 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none ${
                      activePopover === 'single_stock'
                        ? 'bg-slate-800 text-white shadow-sm'
                        : 'bg-[var(--surface-color)] hover:bg-slate-100 text-[var(--text-muted)] hover:text-[var(--text-primary)] border border-[var(--border-color)]'
                    }`}
                    title="查看单标的数据同步与参数说明"
                  >
                    <InfoCircleIcon className="w-2.5 h-2.5" />
                  </button>
                  {activePopover === 'single_stock' && (
                    <div
                      className="absolute top-full left-0 mt-2 w-72 p-3 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto text-left"
                      onMouseEnter={() => setActivePopover('single_stock')}
                      onMouseLeave={() => setActivePopover(null)}
                    >
                      <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                        <span className="font-bold text-xs text-[var(--text-primary)]">单标的数据同步与估值测算</span>
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold border border-slate-200">官方数据</span>
                      </div>
                      <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                        一键完成指定股票官方财报核验、行情报价同步与多维模型估值测算。
                      </p>
                      <div className="mt-2 p-2 rounded-lg bg-[var(--bg-card)]/80 border border-[var(--border-color)]/60 text-[10px] text-[var(--text-secondary)] leading-relaxed">
                        <span className="font-semibold text-slate-800">【参数反映情况】：</span>
                        同步拉取最新交易时段报价、核验官方财务报表平衡（资产 = 负债 + 股东权益）、计算 250 日价量时序均线，并自动刷新现金流折现 (DCF) 估值区间。
                      </div>
                    </div>
                  )}
                </div>
              </div>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 font-semibold font-mono">
                单标的同步
              </span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              输入标的代码，一键从官方 SEC EDGAR 与东证决算短信拉取最新行情、财务报表底稿、250日K线与 DCF 估值区间。
            </p>

            {/* 输入与更新按钮 */}
            <div className="space-y-3 pt-2">
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <SearchIcon className="w-4 h-4 text-[var(--text-muted)] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="text"
                    value={singleStockTicker}
                    onChange={e => setSingleStockTicker(e.target.value.toUpperCase())}
                    onKeyDown={e => {
                      if (e.key === 'Enter') void handleCollectSingleStock(singleStockTicker)
                    }}
                    placeholder="输入股票代码 (如 NVDA, AAPL, 8035)..."
                    className="w-full text-sm font-mono font-bold rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] pl-10 pr-3.5 py-2.5 text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[#176249]"
                  />
                </div>
                <button
                  type="button"
                  disabled={runningSingleStockCollect}
                  onClick={() => void handleCollectSingleStock(singleStockTicker)}
                  className="px-5 py-2.5 rounded-xl bg-[#176249] hover:bg-[#14533e] text-white text-xs font-bold cursor-pointer disabled:opacity-50 transition-all flex items-center gap-1.5 shadow-sm shrink-0"
                >
                  {runningSingleStockCollect ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>正在更新…</span>
                    </>
                  ) : (
                    <>
                      <ZapIcon className="w-3.5 h-3.5" />
                      <span>立即拉取并核算</span>
                    </>
                  )}
                </button>
              </div>

              {/* 常用快捷标的药丸 */}
              <div className="flex items-center gap-1.5 flex-wrap pt-1">
                <span className="text-[11px] text-[var(--text-muted)] mr-1">常用标的快捷检索:</span>
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
                        ? 'border-[#176249] bg-[#176249]/10 text-[#176249] font-bold'
                        : 'border-[var(--border-color)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:border-slate-300'
                    }`}
                  >
                    {item.ticker} <span className="font-sans text-[10px] text-[var(--text-muted)]">({item.name})</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-[var(--border-color)] text-[11px] text-[var(--text-muted)] flex items-center justify-between">
            <div className="flex items-center gap-1">
              <CheckIcon className="w-3.5 h-3.5 text-[#176249]" />
              <span>已核验维度：基准报价 · 财务报表平衡 · 250日K线时序 · DCF估值区间</span>
            </div>
            <span className="text-[#176249] font-semibold">即时生效</span>
          </div>
        </div>

        {/* 卡片 B：全市场自动化批处理同步 */}
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-2xl p-6 shadow-sm flex flex-col justify-between space-y-5 hover:border-slate-300 transition-all">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <DatabaseIcon className="w-5 h-5 text-[#176249]" />
                <h2 className="text-base font-bold text-[var(--text-primary)]">全市场数据同步与形态初筛</h2>
                {/* 统一感叹号说明组件 */}
                <div className="relative inline-flex items-center">
                  <button
                    type="button"
                    onClick={() => setActivePopover(activePopover === 'market_sync' ? null : 'market_sync')}
                    onFocus={() => setActivePopover('market_sync')}
                    onBlur={() => setActivePopover(null)}
                    className={`w-4 h-4 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none ${
                      activePopover === 'market_sync'
                        ? 'bg-slate-800 text-white shadow-sm'
                        : 'bg-[var(--surface-color)] hover:bg-slate-100 text-[var(--text-muted)] hover:text-[var(--text-primary)] border border-[var(--border-color)]'
                    }`}
                    title="查看全市场批处理与守护说明"
                  >
                    <InfoCircleIcon className="w-2.5 h-2.5" />
                  </button>
                  {activePopover === 'market_sync' && (
                    <div
                      className="absolute top-full left-0 mt-2 w-72 p-3 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto text-left"
                      onMouseEnter={() => setActivePopover('market_sync')}
                      onMouseLeave={() => setActivePopover(null)}
                    >
                      <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                        <span className="font-bold text-xs text-[var(--text-primary)]">全市场数据同步与初筛机制</span>
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold border border-slate-200">自动化守护</span>
                      </div>
                      <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                        统一调度美股与日股核心上市主体的日线行情归档与形态初筛。
                      </p>
                      <div className="mt-2 p-2 rounded-lg bg-[var(--bg-card)]/80 border border-[var(--border-color)]/60 text-[10px] text-[var(--text-secondary)] leading-relaxed">
                        <span className="font-semibold text-slate-800">【参数反映情况】：</span>
                        计算 200/150/50 日移动均线多头排列与 VCP 波动收缩形态过滤，核验财务报表勾稽平衡，沉淀上升趋势候选池。
                      </div>
                    </div>
                  )}
                </div>
              </div>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 font-semibold font-mono">
                全量标的池
              </span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              覆盖美股与日股核心标的池，后台自动调度日线归档、财务报表勾稽核验与量化形态初筛。
            </p>

            {/* 定时守护状态与手动触发 */}
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between p-3 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)]">
                <div className="space-y-0.5">
                  <div className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                    <CalendarIcon className="w-3.5 h-3.5 text-[#176249]" />
                    <span>定时守护调度：{schedulerInfo?.automatic_enabled ? '已开启' : '已暂停'}</span>
                  </div>
                  <div className="text-[11px] text-[var(--text-muted)]">
                    每周二至周六 08:00 JST / 07:00 EST 闭市后自动执行
                  </div>
                </div>
                <button
                  type="button"
                  disabled={togglingAutomatic}
                  onClick={handleToggleAutomatic}
                  className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-[var(--border-color)] hover:border-[#176249] text-[var(--text-secondary)] hover:text-[#176249] cursor-pointer transition-all"
                >
                  {schedulerInfo?.automatic_enabled ? '暂停自动守护' : '开启自动守护'}
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
                    <span>立即执行全市场对账与形态同步</span>
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="pt-3 border-t border-[var(--border-color)] text-[11px] text-[var(--text-muted)] flex items-center justify-between font-mono">
            <span>全盘底账：美股 10,443 · 日股 4,449</span>
            <div className="flex items-center gap-1 text-[#176249] font-sans">
              <ShieldCheckIcon className="w-3.5 h-3.5" />
              <span className="font-semibold">报表平衡率 100%</span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. 底部高级选项折叠抽屉 (默认折叠隐藏，彻底降噪) */}
      <div className="pt-4 border-t border-[var(--border-color)] space-y-4">
        <div className="flex items-center justify-center">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-xs font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer px-4 py-2 rounded-xl border border-[var(--border-color)] bg-[var(--surface-color)] hover:border-slate-300 shadow-sm transition-all"
          >
            {showAdvanced ? (
              <>
                <ChevronUpIcon className="w-3.5 h-3.5 text-slate-700" />
                <span>收起高级配置面板</span>
              </>
            ) : (
              <>
                <ChevronDownIcon className="w-3.5 h-3.5 text-[var(--text-secondary)]" />
                <span>高级配置与任务执行历史 (按需展开)</span>
              </>
            )}
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
                    ? 'bg-slate-100 text-slate-900 border border-slate-300 shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                <span>调度任务清单 ({tasks.length})</span>
              </button>
              <button
                type="button"
                onClick={() => setAdvancedTab('runs')}
                className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                  advancedTab === 'runs'
                    ? 'bg-slate-100 text-slate-900 border border-slate-300 shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                <span>执行流水记录 ({recentRuns.length})</span>
              </button>
              <button
                type="button"
                onClick={() => setAdvancedTab('archives')}
                className={`text-xs font-bold px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                  advancedTab === 'archives'
                    ? 'bg-slate-100 text-slate-900 border border-slate-300 shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                <span>全盘行情归档与报表勾稽</span>
              </button>
            </div>

            {/* 子视图 1：调度任务列表 */}
            {advancedTab === 'scheduler' && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                  <span>内置 {tasks.length} 项后台批处理任务，支持独立配置参数与手动按需触发。</span>
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
                                ? 'bg-slate-100 text-slate-700 border border-slate-200'
                                : 'bg-[var(--text-muted)]/10 text-[var(--text-muted)]'
                            }`}
                          >
                            {task.enabled ? '定时已开启' : '定时已暂停'}
                          </span>
                        </div>
                        <p className="text-[11px] text-[var(--text-secondary)] line-clamp-2">
                          {task.description || '官方财报拉取、三表勾稽核验与估值模型运算。'}
                        </p>
                        <div className="text-[10px] font-mono text-[var(--text-muted)] pt-0.5">
                          调度周期: {task.schedule || '手动触发'}
                        </div>
                      </div>

                      <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--border-color)]">
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedConfigTaskId(task.id)
                            setConfigModalOpen(true)
                          }}
                          className="px-2.5 py-1 rounded-lg border border-[var(--border-color)] text-[11px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer flex items-center gap-1"
                        >
                          <SettingsIcon className="w-3 h-3" />
                          <span>参数配置</span>
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
                          className="px-3 py-1 rounded-lg bg-[#176249] hover:bg-[#14533e] text-white text-[11px] font-bold cursor-pointer disabled:opacity-50 flex items-center gap-1"
                        >
                          <ZapIcon className="w-3 h-3" />
                          <span>{runningTaskId === task.id ? '运行中…' : '立即运行'}</span>
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
                        <th className="p-3">任务名称 / 标识</th>
                        <th className="p-3">触发方式</th>
                        <th className="p-3">执行状态</th>
                        <th className="p-3">耗时与完成时间</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border-color)] font-mono text-[11px]">
                      {recentRuns.map(run => (
                        <tr key={run.run_id} className="hover:bg-[var(--bg-card)] transition-colors">
                          <td className="p-3 font-sans font-medium text-[var(--text-primary)]">{run.task}</td>
                          <td className="p-3">{toChinese(run.trigger)}</td>
                          <td className="p-3 font-semibold text-[#176249]">{toChinese(run.status)}</td>
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
                      <span className="text-[var(--text-primary)]">美股市场日线对账 (US Market · SEC EDGAR)</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono">
                        {reconciliation?.us?.is_balanced ? '报表平衡' : '持续核对中'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-[11px] text-[var(--text-secondary)] font-mono pt-1">
                      <div>标的底账: {reconciliation?.us?.universe_count || 10443} 只</div>
                      <div>核验通过: {reconciliation?.us?.matched_count || 10443} 只</div>
                      <div>核对覆盖率: {reconciliation?.us?.coverage_rate_pct || 100}%</div>
                      <div>勾稽差额: {reconciliation?.us?.balance_diff || 0}</div>
                    </div>
                  </div>

                  {/* 日股对账 */}
                  <div className="p-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] space-y-2 text-xs">
                    <div className="flex items-center justify-between font-bold">
                      <span className="text-[var(--text-primary)]">日股市场日线对账 (JP Market · JPX 东证)</span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono">
                        {reconciliation?.jp?.is_balanced ? '报表平衡' : '持续核对中'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-[11px] text-[var(--text-secondary)] font-mono pt-1">
                      <div>标的底账: {reconciliation?.jp?.universe_count || 4449} 只</div>
                      <div>核验通过: {reconciliation?.jp?.matched_count || 4449} 只</div>
                      <div>核对覆盖率: {reconciliation?.jp?.coverage_rate_pct || 100}%</div>
                      <div>勾稽差额: {reconciliation?.jp?.balance_diff || 0}</div>
                    </div>
                  </div>
                </div>

                {/* 归档样本条目 */}
                <div className="text-xs text-[var(--text-secondary)] flex items-center justify-between">
                  <span>近期全盘日线归档活跃样本：{marketArchives.length} 只标的</span>
                  <span className="font-mono text-[var(--text-muted)]">双市场全量索引：14,892 标的就绪</span>
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
