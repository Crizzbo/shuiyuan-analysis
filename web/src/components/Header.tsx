import type { HealthData } from '../types/api'
import { formatDeviceTime } from '../utils/format'
import { BrandLogo } from './common/BrandLogo'
import { SearchIcon } from './common/Icons'

interface HeaderProps {
  health: HealthData | null
  sseConnected: boolean
  onPipelineStarted: () => void
  onOpenCommandPalette?: () => void
}

export function Header({ health, sseConnected, onPipelineStarted, onOpenCommandPalette }: HeaderProps) {
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
              <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-sky-50 text-sky-700 border border-sky-200 font-mono">
                量化投研
              </span>
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full flex items-center gap-1 font-medium ${
                  sseConnected
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-rose-50 text-rose-700 border border-rose-200'
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${sseConnected ? 'bg-emerald-600' : 'bg-rose-600'}`} />
                {sseConnected ? '已连接' : '重连中'}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--text-muted)] mt-1.5">
              <span className="flex items-center gap-1 text-[var(--text-secondary)]">
                <span className="w-2 h-2 rounded-full bg-emerald-600" />
                服务: {health?.service_connected ? '正常在线' : '离线'}
              </span>
              <span>·</span>
              <span>
                账本: {health?.ledger_valid ? `完整 (${health.ledger_total_predictions} 条)` : health ? '校验异常' : '待检测'}
              </span>
              <span>·</span>
              <span className="px-2.5 py-0.5 rounded bg-sky-50/70 text-sky-800 border border-sky-200/70 font-mono font-medium flex items-center gap-1">
                <span>更新时间:</span>
                <span>{health?.latest_data_ts ? formatDeviceTime(health.latest_data_ts) : '暂无'}</span>
              </span>
            </div>
          </div>
        </div>

        {/* 右侧：全局搜索与快捷触发器 */}
        <div className="flex items-center gap-3 w-full lg:w-auto justify-between lg:justify-end">
          <button
            type="button"
            onClick={onOpenCommandPalette}
            className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg border border-sky-200/90 bg-white/80 hover:bg-white text-xs text-[var(--text-secondary)] hover:text-sky-900 hover:border-sky-400 transition-all shadow-2xs group cursor-pointer"
            title="全局搜索标的、重大事件或切换功能 (Ctrl+K / ⌘K)"
          >
            <SearchIcon className="w-3.5 h-3.5 text-sky-600 group-hover:scale-110 transition-transform" />
            <span className="text-xs font-medium">全局搜索 / 命令...</span>
            <kbd className="hidden sm:inline-flex items-center text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-100/80 text-sky-700 border border-sky-200/90 shadow-2xs">
              ⌘K
            </kbd>
          </button>

          <button
            type="button"
            className="text-xs px-3.5 py-1.5 rounded-lg border border-sky-200 bg-white/90 text-sky-800 hover:text-white hover:bg-sky-600 hover:border-sky-600 font-medium transition-all shadow-xs cursor-pointer shrink-0"
            onClick={onPipelineStarted}
          >
            数据采集
          </button>
        </div>
      </div>
    </header>
  )
}
