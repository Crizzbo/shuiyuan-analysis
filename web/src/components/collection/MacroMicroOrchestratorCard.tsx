import { useState, useEffect } from 'react'
import type { PipelineStatusData } from '../../types/api'
import { api } from '../../services/api'
import { showToast } from '../Toast'

interface MacroMicroOrchestratorCardProps {
  pipelineStatus?: PipelineStatusData | null
  onSyncComplete?: () => void
}

const STAGES = [
  { id: 'macro', label: '1. 宏观流动性', sub: 'TNX / VIX / DXY' },
  { id: 'quotes', label: '2. 全盘现价快照', sub: '时效验真与价格锚' },
  { id: 'radar', label: '3. 突发事件雷达', sub: '因果提炼与P0/P1' },
  { id: 'kline', label: '4. 日线时序对账', sub: '250日时序平账' },
  { id: 'audit', label: '5. 官方三表平账', sub: 'SEC 平账与账本验签' },
  { id: 'valuation', label: '6. SEPA与DCF估值', sub: '动态利率估值走廊' },
]

export function MacroMicroOrchestratorCard({ pipelineStatus, onSyncComplete }: MacroMicroOrchestratorCardProps) {
  const [selectedMarket, setSelectedMarket] = useState<'ALL' | 'US' | 'JP'>('ALL')
  const [isStarting, setIsStarting] = useState(false)

  const isRunning = pipelineStatus?.is_running ?? false
  const progressPct = pipelineStatus?.progress_pct ?? 0
  const currentStage = pipelineStatus?.current_stage || '等待启动宏微观全流程同步'
  const isSuccess = pipelineStatus?.pipeline_state === 'SUCCESS'

  // 监听全流程完成，自动通知父级刷新
  useEffect(() => {
    if (isSuccess && onSyncComplete) {
      onSyncComplete()
    }
  }, [isSuccess])

  const handleStartOrchestrator = async () => {
    if (isRunning || isStarting) return
    setIsStarting(true)
    showToast({
      type: 'info',
      title: '🌐 启动宏微观全流程流水线调度',
      message: '正在按序串联：宏观基准 ➔ 全盘现价 ➔ 事件雷达 ➔ 日线对账 ➔ 财报三表 ➔ DCF估值...',
    })

    try {
      const res = await api.startPipeline('macro_micro_sync', selectedMarket)
      if (res.ok) {
        showToast({
          type: 'success',
          title: '流水线已成功入队',
          message: '6大核心投研环节正在后台全自动流式推进，各看板将实时同步更新。',
        })
      } else {
        showToast({
          type: 'error',
          title: '启动流水线失败',
          message: res.error?.message || '未知错误',
        })
      }
    } catch (err: any) {
      showToast({
        type: 'error',
        title: '请求异常',
        message: err?.message || '网络连接或服务异常',
      })
    } finally {
      setIsStarting(false)
    }
  }

  const handleStopOrchestrator = async () => {
    if (!isRunning) return
    try {
      const res = await api.stopPipeline()
      if (res.ok) {
        showToast({
          type: 'warning',
          title: '正在停止流水线',
          message: '已发送优雅停止信号，当前环节完成后退出。',
        })
      }
    } catch (err: any) {
      showToast({ type: 'error', title: '停止指令异常', message: err.message })
    }
  }

  // 计算当前处于第几阶段 (1 ~ 6)
  const currentStageIndex = progressPct <= 15 ? 0 :
    progressPct <= 35 ? 1 :
    progressPct <= 55 ? 2 :
    progressPct <= 70 ? 3 :
    progressPct <= 88 ? 4 : 5

  return (
    <div className="ice-block rounded-2xl p-5 shadow-xs border-2 border-emerald-400/30 bg-gradient-to-r from-emerald-500/5 via-sky-500/5 to-transparent space-y-4">
      {/* 顶栏标题与市场切换 */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-emerald-600 text-white flex items-center justify-center font-bold text-lg shadow-sm">
            🌐
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-extrabold text-sm sm:text-base text-slate-900 tracking-tight">
                全盘宏微观流水线全自动总调度
              </h3>
              <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                一键闭环中枢
              </span>
              {isRunning && (
                <span className="flex items-center gap-1 text-[11px] font-mono text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full animate-pulse border border-emerald-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  闭环运算中
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              消除孤立计算：按工序严格串联宏观流动性、全盘报价、突发舆情、日线平账、官方财报与多情景 DCF 估值走廊。
            </p>
          </div>
        </div>

        {/* 市场范围切换胶囊 */}
        <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl self-start sm:self-auto text-xs font-medium">
          {(['ALL', 'US', 'JP'] as const).map(mkt => (
            <button
              key={mkt}
              type="button"
              disabled={isRunning}
              onClick={() => setSelectedMarket(mkt)}
              className={`px-3 py-1 rounded-lg transition-all cursor-pointer font-bold disabled:opacity-50 ${
                selectedMarket === mkt
                  ? 'bg-white text-emerald-800 shadow-2xs'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              {mkt === 'ALL' ? '美日全盘 (14,897家)' : mkt === 'US' ? '美股全量' : '日股全量'}
            </button>
          ))}
        </div>
      </div>

      {/* 6 阶段可视化流转工序进度条 (Pipeline Stepper) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        {STAGES.map((stg, idx) => {
          const isDone = progressPct === 100 || (isRunning && currentStageIndex > idx)
          const isCurrent = isRunning && currentStageIndex === idx
          return (
            <div
              key={stg.id}
              className={`p-2.5 rounded-xl border transition-all ${
                isDone
                  ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
                  : isCurrent
                  ? 'bg-sky-50 border-sky-300 ring-2 ring-sky-300/50 shadow-2xs'
                  : 'bg-white/60 border-slate-100 text-slate-400'
              }`}
            >
              <div className="flex items-center justify-between text-[11px] font-bold">
                <span>{stg.label}</span>
                {isDone ? (
                  <span className="text-emerald-600 font-bold">✓</span>
                ) : isCurrent ? (
                  <span className="w-2 h-2 rounded-full bg-sky-500 animate-ping" />
                ) : (
                  <span className="text-[10px] text-slate-300">○</span>
                )}
              </div>
              <div className="text-[10px] text-slate-500 mt-1 truncate">
                {stg.sub}
              </div>
            </div>
          )
        })}
      </div>

      {/* 进度条与状态汇报 */}
      <div className="space-y-2 pt-1">
        <div className="flex items-center justify-between text-xs font-mono">
          <span className="text-slate-600 font-semibold flex items-center gap-1.5">
            <span className="text-slate-400">当前工序:</span>
            <span className="text-slate-800 font-bold">{currentStage}</span>
          </span>
          <span className="font-bold text-emerald-700">{progressPct}%</span>
        </div>
        <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-emerald-500 via-sky-500 to-emerald-600 transition-all duration-300 rounded-full"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* 操作按钮组 */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100">
        <div className="text-[11px] text-slate-400 flex items-center gap-1">
          <span>⚡ 特性：零手动跳转 · 自动注入宏观利率 · 官方三表平账 · 完成后秒级推送到所有看板</span>
        </div>
        <div className="flex items-center gap-2">
          {isRunning ? (
            <button
              type="button"
              onClick={handleStopOrchestrator}
              className="px-4 py-1.5 rounded-xl border border-rose-200 bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-bold transition-all cursor-pointer"
            >
              停止当前流水线
            </button>
          ) : (
            <button
              type="button"
              disabled={isStarting}
              onClick={handleStartOrchestrator}
              className="px-5 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-500 hover:to-teal-600 text-white text-xs font-black shadow-xs hover:shadow-md transition-all cursor-pointer flex items-center gap-2 disabled:opacity-50"
            >
              <span>🚀 一键启动宏微观全流程自动闭环同步</span>
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
