import type { HealthData } from '../types/api'
import { formatDeviceTime } from '../utils/format'

interface HeaderProps {
  health: HealthData | null
  sseConnected: boolean
  onPipelineStarted: () => void
}

export function Header({ health, sseConnected, onPipelineStarted }: HeaderProps) {
  return (
    <header className="terminal-top">
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
        {/* 左侧：系统标题与环境状态 */}
        <div className="flex items-center gap-4">
          <div className="w-9 h-9 rounded-lg bg-[#176249] flex items-center justify-center font-bold text-white">
            水
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold tracking-tight text-[var(--text-primary)]">
                水源分析终端
              </h1>
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full flex items-center gap-1 font-medium ${
                  sseConnected
                    ? 'bg-[#199e70]/15 text-[#199e70] border border-[#199e70]/30'
                    : 'bg-[#d03b3b]/15 text-[#d03b3b] border border-[#d03b3b]/30'
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${sseConnected ? 'bg-[#199e70]' : 'bg-[#d03b3b]'}`} />
                {sseConnected ? '已连接' : '重连中'}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--text-muted)] mt-1.5">
              <span className="flex items-center gap-1 text-[var(--text-secondary)]">
                <span className="w-2 h-2 rounded-full bg-[#199e70]" />
                服务: {health?.service_connected ? '正常在线' : '离线'}
              </span>
              <span>·</span>
              <span>
                账本: {health?.ledger_valid ? `完整 (${health.ledger_total_predictions} 条)` : health ? '校验异常' : '待检测'}
              </span>
              <span>·</span>
              <span className="px-2.5 py-0.5 rounded bg-[#3987e5]/15 text-[#3987e5] border border-[#3987e5]/30 font-mono font-bold flex items-center gap-1">
                <span>🕒 更新时间:</span>
                <span>{health?.latest_data_ts ? formatDeviceTime(health.latest_data_ts) : '暂无'}</span>
              </span>
            </div>
          </div>
        </div>

        <button type="button" className="text-xs text-[var(--accent)]" onClick={onPipelineStarted}>
          采集中心
        </button>
      </div>
    </header>
  )
}
