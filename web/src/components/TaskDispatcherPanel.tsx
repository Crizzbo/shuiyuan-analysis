import { useState } from 'react'
import { api } from '../services/api'
import type { TaskSchedulerInfo } from '../types/api'
import { showToast } from './Toast'

interface Props {
  schedulerInfo?: TaskSchedulerInfo | null
  onTaskCompleted: () => Promise<void>
  onManage: () => void
  onSelectTicker?: (ticker: string) => void
}

const QUICK_TICKERS = [
  { ticker: 'NVDA', label: '英伟达 (算力龙头)', market: 'US' },
  { ticker: 'AAPL', label: '苹果 (消费电子)', market: 'US' },
  { ticker: 'MSFT', label: '微软 (企业智能云)', market: 'US' },
  { ticker: '8035', label: '东京电子 (半导体制造设备)', market: 'JP' },
  { ticker: '6857', label: '爱德万 (芯片测试设备)', market: 'JP' },
  { ticker: 'TSM', label: '台积电 (先进制程代工)', market: 'US' },
  { ticker: 'GOOGL', label: '谷歌 (基础大模型与云)', market: 'US' },
]

export function TaskDispatcherPanel({ schedulerInfo, onTaskCompleted, onManage, onSelectTicker }: Props) {
  const [busy, setBusy] = useState(false)
  const [runningTaskId, setRunningTaskId] = useState<string | null>(null)
  const [customTicker, setCustomTicker] = useState('NVDA')
  const [singleStockBusy, setSingleStockBusy] = useState(false)
  const [expanded, setExpanded] = useState(false)

  const active = schedulerInfo?.active_runs ?? []
  const automatic = schedulerInfo?.automatic_enabled ?? false

  // 全量批处理 / 自动调度总控
  async function submitMaster(action: 'start' | 'automatic') {
    setBusy(true)
    try {
      const result = action === 'start' ? await api.startTerminalBatch() : await api.setTerminalAutomatic(!automatic)
      if (!result.ok) {
        showToast({ type: 'error', title: '操作失败', message: result.error?.message || '调度服务不可用' })
        return
      }
      showToast({
        type: 'success',
        title: action === 'start' ? '已提交本地全量核对与数据采集' : '已更新自动调度',
        message: action === 'start' && 'run_id' in result.data ? `运行编号 ${result.data.run_id.slice(0, 8)}` : '',
      })
      await onTaskCompleted()
    } catch (error) {
      showToast({ type: 'error', title: '操作失败', message: error instanceof Error ? error.message : '无法连接调度服务' })
    } finally {
      setBusy(false)
    }
  }

  // 单个基石任务触发
  async function submitSingleTask(taskId: string, taskName: string) {
    if (runningTaskId) return
    setRunningTaskId(taskId)
    showToast({
      type: 'info',
      title: `正在启动任务: ${taskName}`,
      message: '任务已提交至终端后台线程池执行...',
    })
    try {
      const res = await api.runTerminalTask(taskId)
      if (res.ok) {
        showToast({
          type: 'success',
          title: `任务已就绪: ${taskName}`,
          message: `运行编号 ${res.data.run_id?.slice(0, 8) || 'RUNNING'}`,
        })
        await onTaskCompleted()
      } else {
        showToast({
          type: 'error',
          title: '任务执行未成功',
          message: res.error?.message || '调度器未能执行该任务',
        })
      }
    } catch (err: any) {
      showToast({
        type: 'error',
        title: '请求异常',
        message: err.message || '网络连接或后端异常',
      })
    } finally {
      setRunningTaskId(null)
    }
  }

  // 🎯 指定个股全维度一键数据拉取与平账核对
  async function handleCollectSingleStock(tickerToRun: string) {
    const symbol = tickerToRun.trim().toUpperCase()
    if (!symbol) {
      showToast({ type: 'warning', title: '请输入股票代码', message: '如 NVDA, AAPL, MSFT, 8035, 6857 等' })
      return
    }
    setSingleStockBusy(true)
    showToast({
      type: 'info',
      title: `启动标的 [${symbol}] 全维度数据拉取`,
      message: '正在拉取最新行情、核验官方三表底稿、计算250日均线并刷新DCF估值走廊...',
    })
    try {
      const res = await api.runTerminalTask('STOCK_DOSSIER_COLLECT', symbol)
      if (res.ok) {
        showToast({
          type: 'success',
          title: `标的 [${symbol}] 数据拉取与核算已完成`,
          message: `已同步最新报价、平账自检与 DCF 估值 (Run ID: ${res.data.run_id?.slice(0, 8)})`,
        })
        await onTaskCompleted()
        if (onSelectTicker) {
          onSelectTicker(symbol)
        }
      } else {
        showToast({
          type: 'error',
          title: '单票数据拉取失败',
          message: res.error?.message || '无法获取该标的数据',
        })
      }
    } catch (err: any) {
      showToast({
        type: 'error',
        title: '请求异常',
        message: err.message || '网络连接或调度服务异常',
      })
    } finally {
      setSingleStockBusy(false)
    }
  }

  const isTaskRunning = (taskId: string) => {
    return runningTaskId === taskId || active.some(r => r.task === taskId && (r.status === 'RUNNING' || r.status === 'QUEUED'))
  }

  return (
    <div className="rounded-xl border border-[var(--border-color)] bg-[var(--surface-color)] p-3 shadow-sm space-y-3">
      {/* 顶部总控条 (去运维化极简胶囊) */}
      <div className={`flex flex-wrap items-center justify-between gap-3 ${expanded ? 'pb-3 border-b border-[var(--border-color)]' : ''}`}>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#199e70] animate-pulse" />
            <span className="font-bold text-xs text-[var(--text-primary)]">
              投研数据调度中枢
            </span>
          </div>
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-[#3987e5]/10 text-[#3987e5] border border-[#3987e5]/25 font-medium">
            分时调度已开启 · 10大任务通道正常
          </span>
        </div>

        {/* 紧凑单票输入 */}
        <div className="flex items-center gap-1.5">
          <input
            type="text"
            value={customTicker}
            onChange={e => setCustomTicker(e.target.value.toUpperCase())}
            placeholder="代码 (如 NVDA, 8035)..."
            className="w-28 text-xs font-mono font-bold rounded-md border border-[var(--border-color)] bg-[var(--bg-card)] px-2 py-1 text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[#3987e5]"
          />
          <button
            type="button"
            disabled={singleStockBusy}
            onClick={() => void handleCollectSingleStock(customTicker)}
            className="px-2.5 py-1 rounded-md bg-[#3987e5] hover:bg-[#2c72c8] text-white text-xs font-semibold cursor-pointer disabled:opacity-50 transition-all flex items-center gap-1 shadow-sm"
          >
            {singleStockBusy ? (
              <>
                <div className="w-2.5 h-2.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>拉取中…</span>
              </>
            ) : (
              <span>单票拉取</span>
            )}
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={busy || !schedulerInfo}
            onClick={() => void submitMaster('start')}
            className="px-2.5 py-1 rounded-md bg-[#176249] hover:bg-[#14533e] text-white text-xs font-semibold cursor-pointer disabled:opacity-50 transition-all flex items-center gap-1 shadow-sm"
          >
            <span>全量核对</span>
          </button>

          <button
            type="button"
            role="switch"
            aria-checked={automatic}
            disabled={busy || !schedulerInfo?.automatic_available}
            onClick={() => void submitMaster('automatic')}
            className={`px-2.5 py-1 rounded-md border text-xs font-semibold cursor-pointer disabled:opacity-50 transition-all ${
              automatic
                ? 'bg-[#199e70]/15 text-[#199e70] border-[#199e70]/40 hover:bg-[#199e70]/20'
                : 'bg-[var(--bg-card)] text-[var(--text-muted)] border-[var(--border-color)] hover:text-[var(--text-primary)]'
            }`}
          >
            自动调度: {automatic ? '已开' : '已关'}
          </button>

          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-[#3987e5] hover:underline font-medium px-1.5 py-1 cursor-pointer"
          >
            {expanded ? '收起详情 ▲' : '展开基石调度 ▼'}
          </button>

          <button
            type="button"
            onClick={onManage}
            className="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] px-1.5 py-1 cursor-pointer"
          >
            采集中枢 →
          </button>
        </div>
      </div>

      {expanded && (
        <div className="space-y-4 pt-1">
          {/* ========================================================================= */}
          {/* 重点一：指定标的数据拉取与报表核验 (精准单票采集入口) */}
          {/* ========================================================================= */}
          <div className="rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] p-4 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-[var(--text-primary)]">
                  指定标的数据拉取与报表核验
                </span>
                <span className="text-xs text-[var(--text-muted)]">
                  一键同步：基准报价 · 官方财报平衡 · 250日均线 · 现金流折现 (DCF)
                </span>
              </div>
              <div className="text-[11px] text-[var(--text-muted)]">
                支持美股 (SEC) 与日股 (东证) 任意有效标的
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <input
                type="text"
                value={customTicker}
                onChange={e => setCustomTicker(e.target.value.toUpperCase())}
                placeholder="输入代码 (如 NVDA, AAPL, MSFT, 8035, 6857)..."
                className="w-48 text-xs font-mono font-bold rounded-lg border border-[var(--border-color)] bg-[var(--surface-color)] px-3 py-1.5 text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[#176249]"
              />

              <button
                type="button"
                disabled={singleStockBusy}
                onClick={() => void handleCollectSingleStock(customTicker)}
                className="px-3.5 py-1.5 rounded-lg bg-[#176249] hover:bg-[#14533e] text-white text-xs font-semibold cursor-pointer disabled:opacity-50 transition-all flex items-center gap-1.5 shadow-sm"
              >
                {singleStockBusy ? (
                  <>
                    <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>正在拉取与核验 {customTicker}...</span>
                  </>
                ) : (
                  <>
                    <span>立即拉取与核验</span>
                  </>
                )}
              </button>

              <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-[var(--text-muted)] pl-2">
                <span>快捷标的：</span>
                {QUICK_TICKERS.map(item => (
                  <button
                    key={item.ticker}
                    type="button"
                    onClick={() => {
                      setCustomTicker(item.ticker)
                      void handleCollectSingleStock(item.ticker)
                    }}
                    className="px-2 py-0.5 rounded bg-[var(--surface-color)] hover:bg-slate-100 border border-[var(--border-color)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer transition-all"
                  >
                    {item.ticker}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* ========================================================================= */}
          {/* 重点二：核心数据通道与维护任务 (可分别独立触发更新) */}
          {/* ========================================================================= */}
          <div>
            <div className="flex items-center justify-between pb-2">
              <span className="text-xs font-bold text-[var(--text-secondary)]">
                核心数据通道与维护任务（可分别独立触发更新）
              </span>
              <span className="text-[11px] text-[var(--text-muted)]">
                {active.length > 0 ? `当前 ${active.length} 项任务执行中` : '所有数据通道就绪'}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
              {/* 1. 现价与时效核验 */}
              <div className="p-3 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] flex flex-col justify-between gap-2">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                      <span>最新行情与时效核验</span>
                    </span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200">
                      现价维度
                    </span>
                  </div>
                  <p className="text-[11px] text-[var(--text-muted)] mt-1 line-clamp-2">
                    获取标的盘中现价与前收盘基准，执行 24h 新鲜度门禁，为 DCF 估值提供基准锚。
                  </p>
                </div>
                <div className="flex items-center justify-between pt-1 border-t border-[var(--border-color)]/60 text-[10px]">
                  <span className="text-[var(--text-muted)] font-mono">QUOTE_COLLECT</span>
                  <button
                    type="button"
                    disabled={isTaskRunning('QUOTE_COLLECT')}
                    onClick={() => void submitSingleTask('QUOTE_COLLECT', '最新行情与时效核验')}
                    className="px-2.5 py-1 rounded bg-[#176249] hover:bg-[#14533e] text-white font-medium cursor-pointer disabled:opacity-50"
                  >
                    {isTaskRunning('QUOTE_COLLECT') ? '拉取中…' : '立即拉取'}
                  </button>
                </div>
              </div>

              {/* 2. 官方三表底稿与报表勾稽 */}
              <div className="p-3 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] flex flex-col justify-between gap-2">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                      <span>官方三表底稿与报表勾稽</span>
                    </span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200">
                      财报维度
                    </span>
                  </div>
                  <p className="text-[11px] text-[var(--text-muted)] mt-1 line-clamp-2">
                    SEC 10-K / 东证决算短信底稿核验 (资产=负债+权益)，核算 FCF 与净负债。
                  </p>
                </div>
                <div className="flex items-center justify-between pt-1 border-t border-[var(--border-color)]/60 text-[10px]">
                  <span className="text-[var(--text-muted)] font-mono">FINANCE_CALC</span>
                  <button
                    type="button"
                    disabled={isTaskRunning('FINANCE_CALC')}
                    onClick={() => void submitSingleTask('FINANCE_CALC', '官方三表底稿与报表勾稽')}
                    className="px-2.5 py-1 rounded bg-[#176249] hover:bg-[#14533e] text-white font-medium cursor-pointer disabled:opacity-50"
                  >
                    {isTaskRunning('FINANCE_CALC') ? '核算中…' : '立即核算'}
                  </button>
                </div>
              </div>

              {/* 3. 250日历史日K量价 */}
              <div className="p-3 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] flex flex-col justify-between gap-2">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                      <span>250日历史日K量价</span>
                    </span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200">
                      量价维度
                    </span>
                  </div>
                  <p className="text-[11px] text-[var(--text-muted)] mt-1 line-clamp-2">
                    归档 250 天历史日线 OHLCV，计算 50/150/200 日均线与成交量变化。
                  </p>
                </div>
                <div className="flex items-center justify-between pt-1 border-t border-[var(--border-color)]/60 text-[10px]">
                  <span className="text-[var(--text-muted)] font-mono">US/JP_DAILY</span>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      disabled={isTaskRunning('US_DAILY')}
                      onClick={() => void submitSingleTask('US_DAILY', '美股日K量价')}
                      className="px-2 py-1 rounded bg-[#176249] hover:bg-[#14533e] text-white font-medium cursor-pointer disabled:opacity-50"
                    >
                      {isTaskRunning('US_DAILY') ? '美股…' : '美股日K'}
                    </button>
                    <button
                      type="button"
                      disabled={isTaskRunning('JP_DAILY')}
                      onClick={() => void submitSingleTask('JP_DAILY', '日股日K量价')}
                      className="px-2 py-1 rounded bg-[#176249] hover:bg-[#14533e] text-white font-medium cursor-pointer disabled:opacity-50"
                    >
                      {isTaskRunning('JP_DAILY') ? '日股…' : '日股日K'}
                    </button>
                  </div>
                </div>
              </div>

              {/* 4. SEPA 主升浪形态初筛 */}
              <div className="p-3 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] flex flex-col justify-between gap-2">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                      <span>SEPA 趋势与形态初筛</span>
                    </span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200">
                      形态维度
                    </span>
                  </div>
                  <p className="text-[11px] text-[var(--text-muted)] mt-1 line-clamp-2">
                    基于价量时序执行 Minervini 趋势模板与 VCP 波动收缩形态过滤，筛选上升趋势标的。
                  </p>
                </div>
                <div className="flex items-center justify-between pt-1 border-t border-[var(--border-color)]/60 text-[10px]">
                  <span className="text-[var(--text-muted)] font-mono">STOCK_SCREENING</span>
                  <button
                    type="button"
                    disabled={isTaskRunning('STOCK_SCREENING')}
                    onClick={() => void submitSingleTask('STOCK_SCREENING', 'SEPA主升浪初筛')}
                    className="px-2.5 py-1 rounded bg-[#176249] hover:bg-[#14533e] text-white font-medium cursor-pointer disabled:opacity-50"
                  >
                    {isTaskRunning('STOCK_SCREENING') ? '初筛中…' : '执行初筛'}
                  </button>
                </div>
              </div>

              {/* 5. 宏观无风险利率与 WACC */}
              <div className="p-3 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] flex flex-col justify-between gap-2">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                      <span>宏观折现率与标的 WACC</span>
                    </span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200">
                      资本成本
                    </span>
                  </div>
                  <p className="text-[11px] text-[var(--text-muted)] mt-1 line-clamp-2">
                    接入 10Y 美债基准与期限利差，动态测算标的专属 WACC 资本成本与多阶段折现率。
                  </p>
                </div>
                <div className="flex items-center justify-between pt-1 border-t border-[var(--border-color)]/60 text-[10px]">
                  <span className="text-[var(--text-muted)] font-mono">INDICATOR_UPDATE</span>
                  <button
                    type="button"
                    disabled={isTaskRunning('INDICATOR_UPDATE')}
                    onClick={() => void submitSingleTask('INDICATOR_UPDATE', '宏观折现率更新')}
                    className="px-2.5 py-1 rounded bg-[#176249] hover:bg-[#14533e] text-white font-medium cursor-pointer disabled:opacity-50"
                  >
                    {isTaskRunning('INDICATOR_UPDATE') ? '更新中…' : '刷新参数'}
                  </button>
                </div>
              </div>

              {/* 6. 官方资讯与事件雷达 */}
              <div className="p-3 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] flex flex-col justify-between gap-2">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                      <span>官方资讯与微观事件雷达</span>
                    </span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200">
                      催化剂维度
                    </span>
                  </div>
                  <p className="text-[11px] text-[var(--text-muted)] mt-1 line-clamp-2">
                    SEC / FED 官方资讯分时归档，提炼供应链传导与个股营运利润 ΔEBIT 冲击。
                  </p>
                </div>
                <div className="flex items-center justify-between pt-1 border-t border-[var(--border-color)]/60 text-[10px]">
                  <span className="text-[var(--text-muted)] font-mono">OFFICIAL_NEWS</span>
                  <button
                    type="button"
                    disabled={isTaskRunning('OFFICIAL_NEWS')}
                    onClick={() => void submitSingleTask('OFFICIAL_NEWS', '官方资讯与事件雷达')}
                    className="px-2.5 py-1 rounded bg-[#176249] hover:bg-[#14533e] text-white font-medium cursor-pointer disabled:opacity-50"
                  >
                    {isTaskRunning('OFFICIAL_NEWS') ? '抽取中…' : '提取公告'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
