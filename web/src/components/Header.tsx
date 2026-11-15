import type { HealthData } from '../types/api'
import { formatDeviceTime } from '../utils/format'
import { BrandLogo } from './common/BrandLogo'

interface HeaderProps {
  health: HealthData | null
  sseConnected: boolean
  onPipelineStarted: () => void
}

export function Header({ health, sseConnected, onPipelineStarted }: HeaderProps) {
  return (
    <header className="terminal-top">
      <div className="container flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
        {/* 左侧：系统标题与环境状态 */}
        <div className="flex items-center gap-3.5">
          <BrandLogo size="md" className="rounded-lg shadow-xs" />
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold tracking-tight text-[var(--text-primary)]">
                水源分析终端
              </h1>
              <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-[#176249]/10 text-[#176249] border border-[#176249]/20">
                水凤·投研
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
              <span className="px-2.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono font-medium flex items-center gap-1">
                <span>更新时间:</span>
                <span>{health?.latest_data_ts ? formatDeviceTime(health.latest_data_ts) : '暂无'}</span>
              </span>
            </div>
          </div>
        </div>

        <button
          type="button"
          className="text-xs px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 hover:text-[#176249] hover:border-[#176249]/40 font-medium transition-all shadow-xs"
          onClick={onPipelineStarted}
        >
          数据采集
        </button>
      </div>
    </header>
  )
}
