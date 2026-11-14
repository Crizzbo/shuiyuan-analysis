import { useState } from 'react'
import type { TaskSchedulerInfo, TaskSchedulerRun } from '../types/api'
import { api } from '../services/api'
import { showToast } from './Toast'
import { toChinese } from '../utils/format'

interface TaskDispatcherPanelProps {
  schedulerInfo?: TaskSchedulerInfo | null
  onTaskCompleted?: () => void
}

interface TaskMeta {
  id: string
  name: string
  category: 'calc' | 'screening' | 'news' | 'indicator' | 'market' | 'audit'
  icon: string
  description: string
  scopeDetail: string
  defaultSchedule: string
  color: string
}

const TASK_METAS: TaskMeta[] = [
  {
    id: 'QUOTE_COLLECT',
    name: '权威行情与核心标的即时抽取',
    category: 'market',
    icon: '⚡',
    description: '24 项美股/日股核心指数、科技龙头与 AI 产业链权威报价即时抽取与美分级精度验签',
    scopeDetail: 'SPY, QQQ, DIA, SMH, TOPIX, NVDA, TSM, AVGO, MSFT, 软银, 东电等全盘核心资产，直接落盘不可篡改签名归档',
    defaultSchedule: '手动即时 / 盘中刷新',
    color: '#eab308',
  },
  {
    id: 'FINANCE_CALC',
    name: '24大专业金融模型与估值',
    category: 'calc',
    icon: '📊',
    description: '全量 24 大专业量化与金融估值模型矩阵及资产负债表刚性平账',
    scopeDetail: '严禁机械打分；多阶段DCF、反向DCF、EBO、WACC、Merton违约距离、Altman Z、Beneish M、GARCH、Kalman、Black-Litterman、CRR二叉树、SVI曲面、蒙特卡洛5000次模拟与SEPA全息测算',
    defaultSchedule: '手动即时 / 每日核算',
    color: '#3987e5',
  },
  {
    id: 'STOCK_SCREENING',
    name: '全盘标的收集与形态初筛',
    category: 'screening',
    icon: '🎯',
    description: '全盘 14,892 家上市企业（美股 10,445 + 日股 4,447）0-Token 纯本地形态初筛',
    scopeDetail: '纯本地数学计算 50/150/200 日均线多头排列、52周高点与 VCP 波动收缩形态，零 Token 消耗',
    defaultSchedule: '周二至周六 08:00 JST',
    color: '#199e70',
  },
  {
    id: 'OFFICIAL_NEWS',
    name: '官方资讯分时采集',
    category: 'news',
    icon: '⚡',
    description: '官方监管机构与交易所权威 RSS/资讯分时间采集与脉冲抽取',
    scopeDetail: 'SEC、东证、美联储与权威通讯社公开信源；自动事实核验与传闻隔离归档',
    defaultSchedule: '分时间采集：每小时脉冲',
    color: '#d03b3b',
  },
  {
    id: 'INDICATOR_UPDATE',
    name: '金融指标与宽度计算',
    category: 'indicator',
    icon: '📈',
    description: '宏观流动性基准利率与全市场 14,892 家多头趋势宽度走廊测算',
    scopeDetail: '10年期美债 (DGS10)、EFFR 基准利率、VIX 波动率及全市场 50日/200日均线上方股票占比',
    defaultSchedule: '分时间采集：每小时自动计算',
    color: '#c98500',
  },
  {
    id: 'US_DAILY',
    name: '美股全盘标的时序抽取',
    category: 'market',
    icon: '🇺🇸',
    description: '美股全盘 10,445 家上市主体（SEC 登记全量 105 批次流式分块）日线抽取与归档',
    scopeDetail: '覆盖 SEC 官方全量 10,445 家上市主体，流式分块抓取日线 OHLCV、宽基指数与美债基准，严格时效验签',
    defaultSchedule: '周二至周六 07:00 JST (收盘)',
    color: '#6366f1',
  },
  {
    id: 'JP_DAILY',
    name: '日股全盘标的时序抽取',
    category: 'market',
    icon: '🇯🇵',
    description: '日股全盘 4,447 家上市主体（东证登记全量 45 批次流式分块）日线抽取与归档',
    scopeDetail: '覆盖东京证券交易所 Prime/Standard/Growth 全量 4,447 家上市主体，流式分块抓取日线与日经波动率',
    defaultSchedule: '周一至周五 16:00 JST (收盘)',
    color: '#0ea5e9',
  },
  {
    id: 'LOCAL_AUDIT',
    name: '本地数据与账本核验',
    category: 'audit',
    icon: '🛡️',
    description: '三表刚性平账、离线数据源完整性与预测账本密码学 SHA-256 验签',
    scopeDetail: '资产=负债+所有者权益公式断言；PredictionLedger 链条验签，杜绝代码硬编码对账',
    defaultSchedule: '手动即时校验',
    color: '#10b981',
  },
  {
    id: 'INCREMENTAL_COLLECT',
    name: '官方监管补数与档案归档',
    category: 'audit',
    icon: '📑',
    description: '官方监管补数定向队列核验与深度档案增量归档',
    scopeDetail: '72 家待进入监管/交易所页面核验原文，流式分批热/温/冷生命周期安全归档',
    defaultSchedule: '每小时扫描补数队列',
    color: '#8b5cf6',
  },
]

export function TaskDispatcherPanel({ schedulerInfo, onTaskCompleted }: TaskDispatcherPanelProps) {
  const [runningTaskId, setRunningTaskId] = useState<string | null>(null)
  const [togglingTaskId, setTogglingTaskId] = useState<string | null>(null)
  const [showHistory, setShowHistory] = useState(false)

  const activeRuns = schedulerInfo?.active_runs || []
  const recentRuns = schedulerInfo?.recent_runs || []
  const configuredTasks = schedulerInfo?.tasks || []

  // 判断某个任务是否正在运行
  const isTaskRunning = (taskId: string) => {
    return (
      runningTaskId === taskId ||
      activeRuns.some((r) => r.task === taskId && (r.status === 'RUNNING' || r.status === 'QUEUED'))
    )
  }

  // 获取某个任务的开关状态
  const isTaskEnabled = (taskId: string) => {
    const found = configuredTasks.find((t) => t.id === taskId)
    return found ? found.enabled : true
  }

  // 获取某个任务最近一次的执行记录
  const getLastRun = (taskId: string): TaskSchedulerRun | undefined => {
    return recentRuns.find((r) => r.task === taskId)
  }

  // 触发任务运行
  const handleRunTask = async (taskMeta: TaskMeta) => {
    if (isTaskRunning(taskMeta.id)) return
    setRunningTaskId(taskMeta.id)
    showToast({
      type: 'info',
      title: '任务已提交至后台队列',
      message: `正在执行 [${taskMeta.name}]，由终端执行器独立线程池处理...`,
    })

    try {
      const res = await api.runTerminalTask(taskMeta.id)
      if (res.ok) {
        showToast({
          type: 'success',
          title: '任务执行已就绪',
          message: `[${taskMeta.name}] 已加入终端任务队列 (Run ID: ${res.data?.run_id?.slice(0, 8)})`,
        })
        onTaskCompleted?.()
      } else {
        showToast({
          type: 'error',
          title: '提交任务失败',
          message: res.error?.message || '未能排队执行该任务',
        })
      }
    } catch (err: any) {
      showToast({
        type: 'error',
        title: '请求异常',
        message: err.message || '网络连接或调度服务异常',
      })
    } finally {
      setRunningTaskId(null)
    }
  }

  // 切换任务定时启用/停用
  const handleToggleSchedule = async (taskId: string, currentEnabled: boolean) => {
    if (togglingTaskId === taskId) return
    setTogglingTaskId(taskId)
    const targetState = !currentEnabled

    try {
      const res = await api.scheduleTerminalTask(taskId, targetState)
      if (res.ok) {
        showToast({
          type: 'success',
          title: '调度配置已更新',
          message: `任务 [${taskId}] 定时分时调度已${targetState ? '开启' : '暂停'}`,
        })
        onTaskCompleted?.()
      } else {
        showToast({
          type: 'error',
          title: '更新调度失败',
          message: res.error?.message || '无法修改任务定时配置',
        })
      }
    } catch (err: any) {
      showToast({
        type: 'error',
        title: '请求异常',
        message: err.message || '更新调度配置失败',
      })
    } finally {
      setTogglingTaskId(null)
    }
  }

  return (
    <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
      {/* 顶部控制面板头部 */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[var(--border-color)]">
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#3987e5] shrink-0" />
          <h2 className="text-sm font-bold text-[var(--text-primary)]">
            任务调度与即时执行中心 (Mission Control)
          </h2>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#3987e5]/15 text-[#3987e5] border border-[#3987e5]/30 font-medium">
            分时定时采集 & 金融计算引擎
          </span>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-[var(--bg-card)] text-[var(--text-secondary)] border border-[var(--border-color)] font-mono">
            {schedulerInfo?.scheduled ? '● 自动分时调度已激活' : '○ 调度器单机就绪'}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="text-xs text-[var(--text-secondary)] hover:text-[#3987e5] flex items-center gap-1 cursor-pointer"
          >
            {showHistory ? '收起执行日志 ▲' : `查看最近流水 (${recentRuns.length}) ▼`}
          </button>
          <button
            onClick={() => onTaskCompleted?.()}
            className="text-xs text-[#3987e5] hover:underline flex items-center gap-1 cursor-pointer"
          >
            ↻ 刷新状态
          </button>
        </div>
      </div>

      {/* 活动运行任务横幅 */}
      {activeRuns.length > 0 && (
        <div className="bg-[#3987e5]/10 border border-[#3987e5]/40 rounded-lg p-3 space-y-2 animate-pulse">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-[#3987e5] flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#3987e5] animate-ping" />
              当前正在执行 {activeRuns.length} 个后台任务
            </span>
            <span className="text-[11px] text-[var(--text-muted)] font-mono">
              线程池并发分配中 · 数据库事务锁安全
            </span>
          </div>
          <div className="flex flex-wrap gap-2 pt-1">
            {activeRuns.map((run) => (
              <div
                key={run.run_id}
                className="bg-[var(--surface-color)] border border-[#3987e5]/40 px-3 py-1.5 rounded-md text-xs flex items-center gap-2 font-mono"
              >
                <div className="w-2.5 h-2.5 border-2 border-[#3987e5] border-t-transparent rounded-full animate-spin" />
                <span className="font-bold text-[var(--text-primary)]">
                  {TASK_METAS.find((m) => m.id === run.task)?.name || run.task}
                </span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#3987e5]/20 text-[#3987e5]">
                  {toChinese(run.status)}
                </span>
                <span className="text-[10px] text-[var(--text-muted)]">
                  ID: {run.run_id.slice(0, 8)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 核心任务网格卡片 (覆盖：金融计算、股票收集、信息分时间采集、指标更新、数据拉取) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3.5">
        {TASK_METAS.map((meta) => {
          const isRunning = isTaskRunning(meta.id)
          const isEnabled = isTaskEnabled(meta.id)
          const lastRun = getLastRun(meta.id)
          const isToggling = togglingTaskId === meta.id

          return (
            <div
              key={meta.id}
              className="bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-[#3987e5]/40 rounded-xl p-3.5 flex flex-col justify-between transition-all shadow-sm space-y-3"
            >
              {/* 卡片头部 */}
              <div>
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-lg shrink-0">{meta.icon}</span>
                    <h3 className="text-xs font-bold text-[var(--text-primary)] truncate">
                      {meta.name}
                    </h3>
                  </div>
                  <span
                    className="text-[10px] px-2 py-0.5 rounded-full font-mono shrink-0 font-medium"
                    style={{
                      backgroundColor: `${meta.color}15`,
                      color: meta.color,
                      border: `1px solid ${meta.color}35`,
                    }}
                  >
                    {meta.defaultSchedule}
                  </span>
                </div>

                {/* 任务描述与范围说明 */}
                <p className="text-[11px] text-[var(--text-secondary)] mt-2 leading-relaxed">
                  {meta.description}
                </p>
                <p className="text-[10px] text-[var(--text-muted)] mt-1 line-clamp-2 leading-normal">
                  {meta.scopeDetail}
                </p>
              </div>

              {/* 上次执行结果摘要 */}
              <div className="pt-2 border-t border-[var(--border-color)]/60 text-[10px] space-y-1">
                <div className="flex items-center justify-between text-[var(--text-muted)]">
                  <span>最近运行:</span>
                  {lastRun ? (
                    <span
                      className={`font-semibold px-1.5 py-0.2 rounded ${
                        lastRun.status === 'SUCCESS'
                          ? 'bg-[#199e70]/20 text-[#199e70]'
                          : lastRun.status === 'PARTIAL_SUCCESS'
                          ? 'bg-[#c98500]/20 text-[#c98500]'
                          : lastRun.status === 'RUNNING'
                          ? 'bg-[#3987e5]/20 text-[#3987e5]'
                          : 'bg-[#d03b3b]/20 text-[#d03b3b]'
                      }`}
                    >
                      {toChinese(lastRun.status)}
                    </span>
                  ) : (
                    <span>未执行</span>
                  )}
                </div>
                {lastRun?.result?.message && (
                  <p className="text-[10px] text-[var(--text-secondary)] truncate font-mono">
                    {lastRun.result.message}
                  </p>
                )}
              </div>

              {/* 操作按钮栏 */}
              <div className="flex items-center justify-between gap-2 pt-1">
                {/* 定时调度开关 */}
                <button
                  type="button"
                  onClick={() => handleToggleSchedule(meta.id, isEnabled)}
                  disabled={isToggling}
                  className={`text-[10px] px-2 py-1 rounded border font-medium flex items-center gap-1 transition-all cursor-pointer ${
                    isEnabled
                      ? 'bg-[var(--surface-color)] text-[var(--text-secondary)] border-[var(--border-color)] hover:border-[#3987e5]'
                      : 'bg-gray-800/40 text-gray-400 border-gray-700/50'
                  }`}
                  title="控制此任务是否按时钟自动调度执行"
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      isEnabled ? 'bg-[#199e70]' : 'bg-gray-500'
                    }`}
                  />
                  <span>{isEnabled ? '定时开启' : '已暂停'}</span>
                </button>

                {/* 立即执行按钮 */}
                <button
                  type="button"
                  onClick={() => handleRunTask(meta)}
                  disabled={isRunning}
                  className={`text-xs px-3 py-1.5 rounded-lg font-bold flex items-center gap-1.5 transition-all shadow-sm cursor-pointer ${
                    isRunning
                      ? 'bg-[#3987e5]/20 text-[#3987e5] border border-[#3987e5]/40 cursor-not-allowed'
                      : 'bg-[#3987e5] hover:bg-[#2b74cf] text-white active:scale-95'
                  }`}
                >
                  {isRunning ? (
                    <>
                      <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                      <span>执行中...</span>
                    </>
                  ) : (
                    <>
                      <span>▶</span>
                      <span>立即执行</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {/* 可展开的任务历史流水抽屉 */}
      {showHistory && (
        <div className="pt-3 border-t border-[var(--border-color)] space-y-2">
          <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
            <span className="font-semibold">终端调度任务历史执行流水 (SQLite 密码学断点持久化)</span>
            <span className="text-[11px] text-[var(--text-muted)] font-mono">
              共保留最近 {recentRuns.length} 条运行记录
            </span>
          </div>

          <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[var(--surface-color)] border-b border-[var(--border-color)] text-[var(--text-muted)]">
                <tr>
                  <th className="p-2.5">任务名称</th>
                  <th className="p-2.5">触发模式</th>
                  <th className="p-2.5">状态</th>
                  <th className="p-2.5">创建时间</th>
                  <th className="p-2.5">完成时间</th>
                  <th className="p-2.5">结果摘要与归档</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-color)]/50 font-mono text-[11px]">
                {recentRuns.length > 0 ? (
                  recentRuns.map((r) => (
                    <tr key={r.run_id} className="hover:bg-[var(--surface-color)]/50">
                      <td className="p-2.5 font-bold text-[var(--text-primary)]">
                        {TASK_METAS.find((m) => m.id === r.task)?.name || r.task}
                      </td>
                      <td className="p-2.5 text-[var(--text-secondary)]">
                        {r.trigger === 'scheduled' ? '⏰ 定时分时槽' : '⚡ 手动即时'}
                      </td>
                      <td className="p-2.5">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            r.status === 'SUCCESS'
                              ? 'bg-[#199e70]/20 text-[#199e70]'
                              : r.status === 'PARTIAL_SUCCESS'
                              ? 'bg-[#c98500]/20 text-[#c98500]'
                              : r.status === 'RUNNING'
                              ? 'bg-[#3987e5]/20 text-[#3987e5]'
                              : r.status === 'CANCELLED'
                              ? 'bg-gray-600/20 text-gray-400'
                              : 'bg-[#d03b3b]/20 text-[#d03b3b]'
                          }`}
                        >
                          {toChinese(r.status)}
                        </span>
                      </td>
                      <td className="p-2.5 text-[var(--text-muted)]">{r.created_at?.slice(11, 19)}</td>
                      <td className="p-2.5 text-[var(--text-muted)]">{r.finished_at?.slice(11, 19) || '—'}</td>
                      <td className="p-2.5 text-[var(--text-secondary)] max-w-xs truncate">
                        {r.result?.message || '—'}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="p-4 text-center text-[var(--text-muted)]">
                      暂无运行记录
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
export default TaskDispatcherPanel
