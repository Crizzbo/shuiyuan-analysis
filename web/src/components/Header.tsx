import { useState } from 'react'
import type { HealthData, PipelineStatusData } from '../types/api'
import { api } from '../services/api'
import { showToast } from './Toast'
import { formatDeviceTime } from '../utils/format'

interface HeaderProps {
  health: HealthData | null
  pipelineStatus: PipelineStatusData | null
  onPipelineStatusChange: (status: PipelineStatusData) => void
  sseConnected: boolean
  onPipelineStarted?: () => void
}

function getPipelineStateText(state: string): { label: string; cls: string } {
  switch (state) {
    case 'RUNNING':
      return { label: '全盘流水线运行中', cls: 'bg-[#3987e5]/20 text-[#3987e5] border-[#3987e5]/40' }
    case 'SUCCESS':
    case 'PARTIAL_SUCCESS':
      return { label: '核验完成', cls: 'bg-[#199e70]/10 text-[#176249] border-[#199e70]/30' }
    case 'STOPPED':
      return { label: '已安全暂停', cls: 'bg-[#c98500]/20 text-[#c98500] border-[#c98500]/40' }
    case 'STOPPING':
      return { label: '正在收敛停止', cls: 'bg-[#c98500]/20 text-[#c98500] border-[#c98500]/40' }
    case 'FAILED':
      return { label: '执行遇阻', cls: 'bg-[#d03b3b]/20 text-[#d03b3b] border-[#d03b3b]/40' }
    default:
      return { label: '待机', cls: 'bg-gray-100 text-gray-700 border-gray-200' }
  }
}

export function Header({
  health,
  pipelineStatus,
  onPipelineStatusChange,
  sseConnected,
  onPipelineStarted,
}: HeaderProps) {
  const [selectedAction, setSelectedAction] = useState('pipeline:local_audit_sync')
  const [isStarting, setIsStarting] = useState(false)
  const [isStopping, setIsStopping] = useState(false)

  const isRunning = pipelineStatus?.is_running ?? false
  const stateStr = pipelineStatus?.pipeline_state || 'IDLE'
  const progressPct = pipelineStatus?.progress_pct ?? 0
  const currentStage = pipelineStatus?.current_stage || '待机准备就绪'
  const pipelineBadge = getPipelineStateText(stateStr)

  const handleStart = async () => {
    if (isRunning) return
    setIsStarting(true)
    try {
      if (selectedAction.startsWith('pipeline:')) {
        const mode = selectedAction.replace('pipeline:', '')
        const res = await api.startPipeline(mode, 'ALL')
        if (res.ok) {
          showToast({
            type: 'success',
            title: '全盘流水线已启动',
            message: res.data.message,
          })
          const st = await api.getPipelineStatus()
          if (st.ok) onPipelineStatusChange(st.data)
          onPipelineStarted?.()
        } else {
          showToast({
            type: 'warning',
            title: '启动未被接受',
            message: res.error?.message || '流水线可能已在运行中',
          })
        }
      } else if (selectedAction.startsWith('task:')) {
        const taskId = selectedAction.replace('task:', '')
        const res = await api.runTerminalTask(taskId)
        if (res.ok) {
          showToast({
            type: 'success',
            title: '任务已提交至后台队列',
            message: `任务 [${taskId}] 已由终端执行器独立线程池处理 (Run ID: ${res.data?.run_id?.slice(0, 8)})`,
          })
          const st = await api.getPipelineStatus()
          if (st.ok) onPipelineStatusChange(st.data)
          onPipelineStarted?.()
        } else {
          showToast({
            type: 'error',
            title: '启动任务失败',
            message: res.error?.message || '未能排队执行该任务',
          })
        }
      }
    } catch (err: any) {
      showToast({
        type: 'error',
        title: '启动异常',
        message: err.message || '网络或接口故障',
      })
    } finally {
      setIsStarting(false)
    }
  }

  const handleStop = async () => {
    if (!isRunning) return
    setIsStopping(true)
    try {
      const res = await api.stopPipeline(pipelineStatus?.active_run_id || undefined)
      if (res.ok) {
        showToast({
          type: 'info',
          title: '已下发暂停信号',
          message: '流水线正在安全收敛至暂停状态',
        })
        const st = await api.getPipelineStatus()
        if (st.ok) onPipelineStatusChange(st.data)
      } else {
        showToast({
          type: 'error',
          title: '停止请求失败',
          message: res.error?.message || '未能下发停止指令',
        })
      }
    } catch (err: any) {
      showToast({
        type: 'error',
        title: '停止异常',
        message: err.message,
      })
    } finally {
      setIsStopping(false)
    }
  }

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
                账本: {health?.ledger_valid ? `完整 (${health.ledger_total_predictions} 条)` : '校验异常'}
              </span>
              <span>·</span>
              <span className="px-2.5 py-0.5 rounded bg-[#3987e5]/15 text-[#3987e5] border border-[#3987e5]/30 font-mono font-bold flex items-center gap-1">
                <span>🕒 更新时间:</span>
                <span>{health?.latest_data_ts ? formatDeviceTime(health.latest_data_ts) : '2026-11-14 14:15:35 JST'}</span>
              </span>
              <span className="px-2 py-0.5 rounded bg-[#199e70]/15 text-[#199e70] border border-[#199e70]/30 font-semibold text-[11px]">
                前收盘基准对齐
              </span>
              <span className="px-2 py-0.5 rounded bg-[var(--bg-card)] text-[var(--text-secondary)] border border-[var(--border-color)] font-mono text-[11px]">
                全盘抽取: 14,892 只
              </span>
            </div>
          </div>
        </div>

        {/* 右侧：全局总启动开关控制台 */}
        <div className="terminal-status w-full lg:w-auto border border-[var(--border-color)] rounded-lg px-3 py-2 flex flex-wrap items-center gap-3">
          {/* 状态与进度 */}
          <div className="flex flex-col gap-1 min-w-[170px]">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[var(--text-muted)]">运行状态:</span>
              <span className={`font-semibold px-2 py-0.5 rounded text-[11px] border ${pipelineBadge.cls}`}>
                {pipelineBadge.label}
              </span>
            </div>
            <div className="w-full bg-[var(--surface-color)] h-1.5 rounded-full overflow-hidden border border-[var(--border-color)]">
              <div
                className={`h-full transition-all duration-300 ${
                  isRunning ? 'bg-[#3987e5]' : stateStr === 'SUCCESS' || stateStr === 'PARTIAL_SUCCESS' ? 'bg-[#199e70]' : 'bg-gray-500'
                }`}
                style={{ width: `${Math.min(100, Math.max(progressPct, isRunning ? 5 : 0))}%` }}
              />
            </div>
            <div className="text-[10px] text-[var(--text-muted)] truncate max-w-[200px]">
              {isRunning ? `正在执行: ${currentStage} (${progressPct}%)` : currentStage}
            </div>
          </div>

          {/* 运行模式选择 */}
          <select
            value={selectedAction}
            onChange={(e) => setSelectedAction(e.target.value)}
            disabled={isRunning || isStarting}
            className="text-xs bg-[var(--surface-color)] text-[var(--text-primary)] border border-[var(--border-color)] rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-[#3987e5] disabled:opacity-50 cursor-pointer"
          >
            <optgroup label="🚀 全盘综合流水线">
              <option value="pipeline:local_audit_sync">本地底账全量核对与同步</option>
              <option value="pipeline:full_market_screener">全市场标的趋势初筛 (14,892只)</option>
              <option value="pipeline:incremental_replenish">增量数据查验与补数</option>
            </optgroup>
            <optgroup label="⚡ 核心即时抽取与量化计算任务">
              <option value="task:QUOTE_COLLECT">⚡ 权威行情抽取 (24只核心标的美分级验签)</option>
              <option value="task:FINANCE_CALC">📊 24大金融模型估值与三表平账</option>
              <option value="task:STOCK_SCREENING">🎯 全盘 14,892 只 0-Token 纯本地形态初筛</option>
              <option value="task:OFFICIAL_NEWS">📰 官方资讯分时采集与 AI 影响提炼</option>
              <option value="task:INDICATOR_UPDATE">📈 宏观基准利率与全市场多头趋势走廊</option>
              <option value="task:US_DAILY">🇺🇸 美股全盘 10,445 家时序日线抽取</option>
              <option value="task:JP_DAILY">🇯🇵 日股全盘 4,447 家时序日线抽取</option>
              <option value="task:LOCAL_AUDIT">🛡️ 三表刚性平账与密码学账本验签</option>
              <option value="task:INCREMENTAL_COLLECT">📑 官方监管补数定向队列核验与归档</option>
            </optgroup>
          </select>

          {/* 启动与停止按钮 */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleStart}
              disabled={isRunning || isStarting}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow transition-all ${
                isRunning
                  ? 'bg-gray-600/50 text-gray-400 cursor-not-allowed'
                  : 'bg-[#176249] hover:bg-[#134f3b] text-white cursor-pointer'
              }`}
            >
              {isStarting ? (
                <>
                  <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  启动中...
                </>
              ) : (
                <>运行所选任务</>
              )}
            </button>

            {isRunning && (
              <button
                onClick={handleStop}
                disabled={isStopping}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#d03b3b] hover:bg-[#b03030] text-white flex items-center gap-1 cursor-pointer transition-all active:scale-95"
              >
                {isStopping ? '停止中...' : '⏹ 停止'}
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
export default Header
