import { TaskDispatcherPanel } from '../TaskDispatcherPanel'

interface TradingSessionBarProps {
  benchmarkDate?: string
  benchmarkNote?: string
  schedulerInfo?: any
  showDispatcher: boolean
  onToggleDispatcher: () => void
  onNavigateTab: (tabId: string) => void
  onTaskCompleted: () => Promise<void> | void
  onSelectTicker?: (ticker: string) => void
}

export function TradingSessionBar({
  benchmarkDate,
  benchmarkNote,
  schedulerInfo,
  showDispatcher,
  onToggleDispatcher,
  onNavigateTab,
  onTaskCompleted,
  onSelectTicker,
}: TradingSessionBarProps) {
  return (
    <>
      <div className="ice-panel rounded-xl px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs shadow-sm">
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="w-2 h-2 rounded-full bg-[#176249] animate-pulse" />
          <span className="font-bold text-[var(--text-primary)]">双市场交易时段状态</span>
          <span className="text-[var(--text-muted)]">|</span>
          <div className="flex flex-wrap items-center gap-3 text-[var(--text-secondary)] font-mono">
            <span className="flex items-center gap-1.5">
              <span className="text-[var(--text-muted)]">美股:</span>
              <span className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-sans text-[11px]">
                已收盘 (前收盘基准)
              </span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="text-[var(--text-muted)]">日股:</span>
              <span className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-sans text-[11px]">
                已收盘 (前收盘基准)
              </span>
            </span>
            <span className="text-[var(--text-muted)] hidden sm:inline">|</span>
            <span className="text-[var(--text-muted)]">
              统计基准交易日: <span className="text-[var(--text-primary)] font-bold">{benchmarkDate || '2026-11-13'}</span> ({benchmarkNote || '全量官方收盘统计'})
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onToggleDispatcher}
            className="text-[11px] text-[var(--text-muted)] hover:text-[var(--text-primary)] cursor-pointer"
          >
            {showDispatcher ? '收起任务面板 ↑' : '任务调度状态 ↓'}
          </button>
          <button
            type="button"
            onClick={() => onNavigateTab('collection')}
            className="px-2.5 py-1 rounded-md bg-[var(--bg-card)] hover:bg-slate-100 text-slate-700 border border-slate-200 hover:text-[#176249] hover:border-[#176249]/40 font-medium cursor-pointer transition-all"
          >
            调度控制台 →
          </button>
        </div>
      </div>

      {showDispatcher && (
        <TaskDispatcherPanel
          schedulerInfo={schedulerInfo}
          onTaskCompleted={async () => {
            await onTaskCompleted()
          }}
          onManage={() => onNavigateTab('collection')}
          onSelectTicker={(ticker) => {
            onSelectTicker?.(ticker)
            onNavigateTab('analytics')
          }}
        />
      )}
    </>
  )
}
