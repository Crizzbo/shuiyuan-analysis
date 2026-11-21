import type { HealthData } from '../types/api'
import { formatDeviceTime } from '../utils/format'
import { BrandLogo } from './common/BrandLogo'
import { SearchIcon, SunIcon, MoonIcon } from './common/Icons'

interface HeaderProps {
  health: HealthData | null
  sseConnected: boolean
  theme?: 'light' | 'dark'
  onToggleTheme?: () => void
  onPipelineStarted: () => void
  onOpenCommandPalette?: () => void
}

export function Header({
  health,
  sseConnected,
  theme = 'light',
  onToggleTheme,
  onPipelineStarted,
  onOpenCommandPalette,
}: HeaderProps) {
  return (
    <header className="terminal-top">
      <div className="container flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
        {/* 左侧：系统标题与环境状态 */}
        <div className="flex items-center gap-3.5">
          <BrandLogo size="md" className="rounded-xl shadow-xs" />
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold tracking-tight text-[var(--text-primary)]">
                水源分析终端
              </h1>
              <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-sky-50 dark:bg-sky-950/60 text-sky-700 dark:text-sky-300 border border-sky-200 dark:border-sky-800 font-mono">
                量化投研
              </span>
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full flex items-center gap-1 font-medium ${
                  sseConnected
                    ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                    : 'bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${sseConnected ? 'bg-emerald-600 dark:bg-emerald-400' : 'bg-rose-600 dark:bg-rose-400'}`} />
                {sseConnected ? '已连接' : '重连中'}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--text-muted)] mt-1.5">
              <span className="flex items-center gap-1 text-[var(--text-secondary)]">
                <span className="w-2 h-2 rounded-full bg-emerald-600 dark:bg-emerald-400" />
                服务: {health?.service_connected ? '正常在线' : '离线'}
              </span>
              <span>·</span>
              <span>
                账本: {health?.ledger_valid ? `完整 (${health.ledger_total_predictions} 条)` : health ? '校验异常' : '待检测'}
              </span>
              <span>·</span>
              <span className="px-2.5 py-0.5 rounded bg-sky-50/70 dark:bg-sky-950/50 text-sky-800 dark:text-sky-300 border border-sky-200/70 dark:border-sky-800/70 font-mono font-medium flex items-center gap-1">
                <span>更新时间:</span>
                <span>{health?.latest_data_ts ? formatDeviceTime(health.latest_data_ts) : '暂无'}</span>
              </span>
            </div>
          </div>
        </div>

        {/* 右侧：全局搜索、主题切换与快捷触发器 */}
        <div className="flex items-center gap-2.5 w-full lg:w-auto justify-between lg:justify-end">
          <button
            type="button"
            onClick={onOpenCommandPalette}
            className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg border border-sky-200/90 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 hover:bg-white dark:hover:bg-slate-700 text-xs text-[var(--text-secondary)] dark:text-slate-300 hover:text-sky-900 dark:hover:text-sky-300 hover:border-sky-400 dark:hover:border-sky-500 transition-all shadow-2xs group cursor-pointer"
            title="全局搜索标的、重大事件或切换功能 (Ctrl+K / ⌘K)"
          >
            <SearchIcon className="w-3.5 h-3.5 text-sky-600 dark:text-sky-400 group-hover:scale-110 transition-transform" />
            <span className="text-xs font-medium">全局搜索 / 命令...</span>
            <kbd className="hidden sm:inline-flex items-center text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-100/80 dark:bg-slate-700 text-sky-700 dark:text-sky-300 border border-sky-200/90 dark:border-slate-600 shadow-2xs">
              ⌘K
            </kbd>
          </button>

          {onToggleTheme && (
            <button
              type="button"
              onClick={onToggleTheme}
              className="p-1.5 rounded-lg border border-sky-200/90 dark:border-slate-700 bg-white/80 dark:bg-slate-800/80 hover:bg-white dark:hover:bg-slate-700 text-[var(--text-secondary)] dark:text-slate-300 hover:text-sky-900 dark:hover:text-amber-300 transition-all shadow-2xs cursor-pointer flex items-center justify-center shrink-0"
              title={theme === 'dark' ? '切换为浅色日间模式' : '切换为「极夜玄冰」暗黑交易模式'}
              aria-label="切换界面主题"
            >
              {theme === 'dark' ? (
                <SunIcon className="w-4 h-4 text-amber-400 hover:rotate-45 transition-transform" />
              ) : (
                <MoonIcon className="w-4 h-4 text-sky-600 hover:-rotate-12 transition-transform" />
              )}
            </button>
          )}

          <button
            type="button"
            className="text-xs px-3.5 py-1.5 rounded-lg border border-sky-200 dark:border-slate-700 bg-white/90 dark:bg-slate-800/90 text-sky-800 dark:text-sky-300 hover:text-white hover:bg-sky-600 hover:border-sky-600 dark:hover:bg-sky-600 dark:hover:border-sky-600 font-medium transition-all shadow-xs cursor-pointer shrink-0"
            onClick={onPipelineStarted}
          >
            数据采集
          </button>
        </div>
      </div>
    </header>
  )
}
