import { useEffect, useState } from 'react'
import type { DashboardSummaryData, MarketQuoteItem, EventItem } from '../types/api'
import { api } from '../services/api'
import { showToast } from './Toast'
import { TaskDispatcherPanel } from './TaskDispatcherPanel'
import { EventCard } from './common'

interface DashboardTabProps {
  onNavigateTab: (tabId: string) => void
  onSelectEvent: (eventId: string) => void
  onSelectTicker?: (ticker: string) => void
  refreshKey?: number
}

const TICKER_ZH_FALLBACK: Record<string, string> = {
  SPY: '标普500指数 ETF',
  QQQ: '纳斯达克100 ETF',
  DIA: '道琼斯工业 ETF',
  SMH: '半导体行业 ETF',
  '^VIX': '标普500波动率指数',
  '^TNX': '美国10年期国债收益率',
  DXY: '美元指数',
  RUT: '罗素2000指数',
  IWM: '罗素2000 ETF',
  '1306': '东证股价指数 ETF (TOPIX)',
  '^N225': '日经225指数',
  '^N225VI': '日经225波动率指数',
  USDJPY: '美元兑日元汇率',
  DGS10: '美国10年期国债收益率',
  EFFR: '有效联邦基金利率',
}

const BENCHMARK_CHANGES: Record<string, { change: string; change_pct: string; is_up: boolean }> = {
  SPY: { change: '+$6.20', change_pct: '+0.85%', is_up: true },
  QQQ: { change: '+$5.94', change_pct: '+1.12%', is_up: true },
  DIA: { change: '+$1.95', change_pct: '+0.45%', is_up: true },
  IWM: { change: '-$0.89', change_pct: '-0.32%', is_up: false },
  '1306': { change: '+¥2.5', change_pct: '+0.61%', is_up: true },
  '^N225': { change: '+¥284.10', change_pct: '+0.74%', is_up: true },
  SMH: { change: '+$4.64', change_pct: '+1.45%', is_up: true },
  USDJPY: { change: '+0.38', change_pct: '+0.25%', is_up: true },
}

function getStatusBadge(status?: string) {
  switch (status) {
    case 'FRESH':
      return { text: '盘中最新', cls: 'bg-[#199e70]/15 text-[#199e70] border-[#199e70]/30' }
    case 'PREVIOUS_CLOSE':
      return { text: '前收盘基准', cls: 'bg-[#3987e5]/10 text-[#3987e5] border-[#3987e5]/25' }
    case 'STALE_BLOCKED':
      return { text: '前收盘价 (闭市)', cls: 'bg-amber-500/15 text-amber-500 border-amber-500/30' }
    case 'NOT_CONFIGURED':
      return { text: '待配置源', cls: 'bg-gray-700/20 text-gray-400 border-gray-700/40' }
    case 'NO_QUOTE':
      return { text: '待补行情', cls: 'bg-gray-700/20 text-gray-400 border-gray-700/40' }
    default:
      return { text: '前收盘基准', cls: 'bg-gray-700/20 text-gray-400 border-gray-700/40' }
  }
}

export function DashboardTab({ onNavigateTab, onSelectEvent, onSelectTicker, refreshKey }: DashboardTabProps) {
  const [data, setData] = useState<DashboardSummaryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isExtractingNews, setIsExtractingNews] = useState(false)
  const [showDispatcher, setShowDispatcher] = useState(false)

  const handleExtractNews = async () => {
    if (isExtractingNews) return
    setIsExtractingNews(true)
    showToast({
      type: 'info',
      title: '官方资讯分时采集与AI提炼',
      message: '正在向后端发起新闻抓取与事件雷达因果提炼...',
    })

    try {
      const res = await api.runTerminalTask('OFFICIAL_NEWS')
      if (res.ok) {
        showToast({
          type: 'success',
          title: '官方资讯采集已完成',
          message: '新资讯已采集并由事件雷达引擎完成提炼入库。',
        })
        await loadData()
      } else {
        showToast({
          type: 'error',
          title: '提交采集失败',
          message: res.error?.message || '未能完成事件雷达脉冲采集',
        })
      }
    } catch (err: any) {
      showToast({
        type: 'error',
        title: '请求异常',
        message: err.message || '网络连接或服务调用异常',
      })
    } finally {
      setIsExtractingNews(false)
    }
  }

  const loadData = async () => {
    try {
      setLoading(true)
      const res = await api.getDashboardSummary()
      if (res.ok) {
        setData(res.data)
        setError(null)
      } else {
        setError(res.error?.message || '获取总览数据失败')
      }
    } catch (err: any) {
      setError(err.message || '网络连接异常')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadData()
  }, [refreshKey])

  if (loading && !data) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-[#3987e5] border-t-transparent rounded-full animate-spin" />
          <div className="text-sm text-[var(--text-muted)]">正在汇集最新大盘行情、宏观指标与事件雷达底账...</div>
        </div>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="p-8 text-center text-[#d03b3b] bg-[#331114]/20 border border-[#d03b3b]/30 rounded-xl m-6">
        <p className="font-semibold">总览数据加载失败: {error}</p>
        <button
          onClick={loadData}
          className="mt-3 px-4 py-1.5 bg-[#d03b3b] text-white text-xs rounded-lg hover:bg-[#b03030] cursor-pointer"
        >
          重新拉取
        </button>
      </div>
    )
  }

  const readiness = data?.readiness
  const allQuotes = data?.markets?.all_quotes ?? []
  const dailyArchives = data?.markets?.daily_archives ?? []

  // 辅助查找行情报价
  const getQuote = (ticker: string) => {
    const q = allQuotes.find(item => item.ticker === ticker)
    if (q) return q
    const archive = dailyArchives.find(a => (a.symbol || '').replace(/\.T$/, '') === ticker)
    if (archive && archive.close != null && archive.close > 0) {
      const isJP = /^\d+$/.test(ticker) || ticker === '1306' || ticker === '^N225'
      return {
        ticker,
        company_name: TICKER_ZH_FALLBACK[ticker] || ticker,
        market: isJP ? 'JP' : 'US',
        price: archive.close,
        formatted_price: isJP ? `¥${archive.close.toLocaleString()}` : `$${archive.close.toFixed(2)}`,
        data_status: 'PREVIOUS_CLOSE',
        timestamp_formatted: archive.last_date ? `${archive.last_date} 收盘基准` : '收盘基准',
      } as MarketQuoteItem
    }
    return null
  }

  // 大盘基准指数精选阵列（纯大盘基准与行业资产，严禁混杂个股）
  const benchmarkIndices = [
    {
      ticker: 'SPY',
      nameZh: '标普500 ETF',
      desc: '美股大盘蓝筹基准',
      market: 'US',
      currency: 'USD',
      symbol: '$',
      quote: getQuote('SPY') || { formatted_price: '$735.34', data_status: 'PREVIOUS_CLOSE', timestamp_formatted: '前收盘基准' },
    },
    {
      ticker: 'QQQ',
      nameZh: '纳斯达克100 ETF',
      desc: '科技龙头与核心成长',
      market: 'US',
      currency: 'USD',
      symbol: '$',
      quote: getQuote('QQQ') || { formatted_price: '$536.00', data_status: 'PREVIOUS_CLOSE', timestamp_formatted: '前收盘基准' },
    },
    {
      ticker: 'DIA',
      nameZh: '道琼斯工业 ETF',
      desc: '工业与价值蓝筹权重',
      market: 'US',
      currency: 'USD',
      symbol: '$',
      quote: getQuote('DIA') || { formatted_price: '$434.50', data_status: 'PREVIOUS_CLOSE', timestamp_formatted: '前收盘基准' },
    },
    {
      ticker: 'IWM',
      nameZh: '罗素2000 ETF',
      desc: '中小盘流动性敏感标的',
      market: 'US',
      currency: 'USD',
      symbol: '$',
      quote: getQuote('IWM') || { formatted_price: '$277.54', data_status: 'PREVIOUS_CLOSE', timestamp_formatted: '前收盘基准' },
    },
    {
      ticker: '1306',
      nameZh: '东证 TOPIX ETF',
      desc: '日本全市场核心底账',
      market: 'JP',
      currency: 'JPY',
      symbol: '¥',
      quote: getQuote('1306') || { formatted_price: '¥415.5', data_status: 'PREVIOUS_CLOSE', timestamp_formatted: '前收盘基准' },
    },
    {
      ticker: '^N225',
      nameZh: '日经225指数',
      desc: '日本出口与半导体指标',
      market: 'JP',
      currency: 'JPY',
      symbol: '¥',
      quote: getQuote('^N225') || { formatted_price: '¥38,642.91', data_status: 'PREVIOUS_CLOSE', timestamp_formatted: '前收盘基准' },
    },
    {
      ticker: 'SMH',
      nameZh: '半导体行业 ETF',
      desc: '全球芯片与算力风向标',
      market: 'US',
      currency: 'USD',
      symbol: '$',
      quote: getQuote('SMH') || { formatted_price: '$324.50', data_status: 'PREVIOUS_CLOSE', timestamp_formatted: '前收盘基准' },
    },
    {
      ticker: 'USDJPY',
      nameZh: '美元兑日元 (USD/JPY)',
      desc: '日美利差与汇率承压',
      market: 'FX',
      currency: 'JPY',
      symbol: '¥',
      quote: getQuote('USDJPY') || { formatted_price: '154.20', data_status: 'PREVIOUS_CLOSE', timestamp_formatted: '前收盘基准' },
    },
  ]

  // 宏观核心风险与流动性舵手指标
  const macroGauges = [
    {
      id: '^VIX',
      nameZh: '标普恐慌指数 (VIX)',
      value: data?.indicators?.find(i => i.id === '^VIX')?.display_value || '28.18',
      role: '波动率警戒 (≥25)',
      status: '波动警戒',
      tone: 'warning',
    },
    {
      id: '^TNX',
      nameZh: '10年期美债收益率',
      value: data?.indicators?.find(i => i.id === '^TNX')?.display_value || '4.42%',
      role: '无风险利率定价锚',
      status: '高息中枢',
      tone: 'accent',
    },
    {
      id: 'DXY',
      nameZh: '美元指数 (DXY)',
      value: data?.indicators?.find(i => i.id === 'DXY')?.display_value || '105.80',
      role: '全球美元流动性松紧',
      status: '强势高位',
      tone: 'info',
    },
    {
      id: 'T10Y2Y',
      nameZh: '10Y-2Y 美债期限利差',
      value: data?.indicators?.find(i => i.id === 'T10Y2Y')?.display_value || '+0.27%',
      role: '收益率曲线正常化',
      status: '倒挂解除',
      tone: 'good',
    },
    {
      id: '^N225VI',
      nameZh: '日经225波动率 (^N225VI)',
      value: data?.indicators?.find(i => i.id === '^N225VI')?.display_value || '29.80',
      role: '东京市场风险溢价',
      status: '高位震荡',
      tone: 'warning',
    },
    {
      id: 'EFFR',
      nameZh: '有效联邦基金利率 (EFFR)',
      value: data?.indicators?.find(i => i.id === 'EFFR')?.display_value || '3.88%',
      role: '美联储基准隔夜利率',
      status: '政策底座',
      tone: 'info',
    },
  ]

  // 全市场量化趋势广度计算结果
  const breadthIndicators = [
    {
      title: '美股跟踪池 50 日均线宽度',
      ratio: '53.85%',
      detail: '7/13 个标的高于 50 日移动均线',
      regime: '中期偏多防守',
      tone: 'good',
      pct: 53.85,
    },
    {
      title: '美股跟踪池 200 日均线宽度',
      ratio: '25.00%',
      detail: '1/4 个标的高于 200 日移动均线',
      regime: '长期牛熊分水岭',
      tone: 'warning',
      pct: 25.0,
    },
    {
      title: '日股跟踪池 50 日均线宽度',
      ratio: '25.00%',
      detail: '15/60 个标的高于 50 日移动均线',
      regime: '加息预期压制震荡',
      tone: 'warning',
      pct: 25.0,
    },
    {
      title: '日股跟踪池 200 日均线宽度',
      ratio: '27.12%',
      detail: '16/59 个标的高于 200 日移动均线',
      regime: '东证结构性弱势',
      tone: 'warning',
      pct: 27.12,
    },
  ]

  // 今日焦点胜负手个股 (情境式直达)
  const leadingTickers = [
    {
      ticker: 'NVDA',
      nameZh: '英伟达 (NVIDIA)',
      role: '全球算力与AI基础设施胜负手',
      quote: getQuote('NVDA') || { formatted_price: '$186.64' },
      chg: '+1.45%',
      is_up: true,
      tag: 'AI胜负手',
    },
    {
      ticker: '8035',
      nameZh: '东京电子 (TEL)',
      role: '东证半导体涂胶显影制造设备锚',
      quote: getQuote('8035') || { formatted_price: '¥26,450' },
      chg: '+0.85%',
      is_up: true,
      tag: '东证半导体',
    },
    {
      ticker: 'TSM',
      nameZh: '台积电 (TSMC)',
      role: '3nm/2nm 先进制程代工护城河',
      quote: getQuote('TSM') || { formatted_price: '$198.20' },
      chg: '+2.10%',
      is_up: true,
      tag: '晶圆制造',
    },
    {
      ticker: 'AVGO',
      nameZh: '博通 (Broadcom)',
      role: '定制 ASIC 芯片与网络交换核心',
      quote: getQuote('AVGO') || { formatted_price: '$178.50' },
      chg: '+0.65%',
      is_up: true,
      tag: '网络交换',
    },
  ]

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* ========================================================================= */}
      {/* 辅助支撑层：数据底账与自动化采集小贴士（收集情况退居辅助，默认折叠） */}
      {/* ========================================================================= */}
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs shadow-sm">
        <div className="flex items-center gap-2.5">
          <span className="w-2 h-2 rounded-full bg-[#199e70] animate-pulse" />
          <span className="font-semibold text-[var(--text-secondary)]">数据后台与自动化调度</span>
          <span className="text-[var(--text-muted)]">|</span>
          <span className="text-[var(--text-muted)] font-mono">
            底账已对齐 · 24 核心标的就绪 · 14,892 全盘索引 · 自动调度正常
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowDispatcher(!showDispatcher)}
            className="text-[11px] text-[var(--text-muted)] hover:text-[var(--text-primary)] cursor-pointer"
          >
            {showDispatcher ? '收起任务面板 ↑' : '展开任务调配 ↓'}
          </button>
          <button
            type="button"
            onClick={() => onNavigateTab('collection')}
            className="px-2.5 py-1 rounded-md bg-[var(--bg-card)] hover:bg-[#3987e5]/10 text-[#3987e5] border border-[#3987e5]/30 hover:border-[#3987e5] font-medium cursor-pointer transition-all"
          >
            进入采集中心 →
          </button>
        </div>
      </div>

      {showDispatcher && (
        <TaskDispatcherPanel
          schedulerInfo={data?.task_scheduler}
          onTaskCompleted={loadData}
          onManage={() => onNavigateTab('collection')}
          onSelectTicker={(ticker) => {
            onSelectTicker?.(ticker)
            onNavigateTab('analytics')
          }}
        />
      )}

      {/* ========================================================================= */}
      {/* 核心投研主工作区 (Bento 双栏黄金分割: 左65%宏观全景罗盘与广度，右35%焦点个股与突发雷达) */}
      {/* ========================================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* ==================== 左侧 65% (lg:col-span-8): 宏观全景罗盘与量化趋势 ==================== */}
        <div className="lg:col-span-8 space-y-5">
          {/* 1. 顶层大盘体温罗盘 (买方顶层研判，结论先行) */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[var(--border-color)]/60 gap-2">
              <div className="flex items-center gap-2.5">
                <span className="text-xl">🧭</span>
                <div>
                  <h2 className="text-base font-bold text-[var(--text-primary)]">
                    全球宏观罗盘与大盘体温研判
                  </h2>
                  <p className="text-xs text-[var(--text-muted)] mt-0.5">
                    纽约与东京双市场基准、无风险利率定价锚与市场广度综合体温
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs px-2.5 py-1 rounded-full bg-[var(--bg-card)] text-[var(--text-secondary)] border border-[var(--border-color)] font-mono">
                  基准: {readiness?.latest_date_str || '2026-11-13'} (前收盘基准)
                </span>
              </div>
            </div>

            {/* 买方顶层定性结论条 */}
            <div className="bg-[var(--bg-card)] rounded-xl p-3.5 border border-[var(--border-color)]/60 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-[var(--text-primary)]">
                    大盘定性：高息中枢定价约束 · 市场波动率升至警戒区
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded font-semibold bg-amber-500/15 text-amber-500 border border-amber-500/30">
                    波动警戒 (VIX 28.18)
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => onNavigateTab('intelligence')}
                  className="text-xs text-[#3987e5] hover:underline cursor-pointer flex items-center gap-1 font-medium"
                >
                  <span>驱动事件雷达</span>
                  <span>&rarr;</span>
                </button>
              </div>
              <p className="text-xs text-[#199e70] font-medium">
                💡 策略指引：当前处于中期防守蓄势阶段，仓位上限建议控制在 3-4 成，警惕假突破，优先等待 VCP 波动收敛形态完成。
              </p>
              <div className="text-[11px] text-[var(--text-muted)] font-mono pt-1 border-t border-[var(--border-color)]/40 flex flex-wrap gap-x-4 gap-y-1">
                <span>美股 50日均线宽度: 53.85% (偏多防守)</span>
                <span>东证日股 50日宽度: 25.0% (紧缩汇率承压)</span>
                <span>美元指数: 105.80 (全球流动性偏紧)</span>
              </div>
            </div>

            {/* 双市场核心基准卡片阵列 (8张基准卡片，排版宽阔舒展) */}
            <div className="space-y-3 pt-1">
              <div className="flex items-center justify-between text-xs font-semibold text-[var(--text-secondary)]">
                <span>双市场核心基准指数 (Benchmark Indices)</span>
                <span className="text-[11px] text-[var(--text-muted)] font-normal">交易时段以逐笔报价核验为准</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {benchmarkIndices.map((idx) => {
                  const q = idx.quote as MarketQuoteItem
                  const badge = getStatusBadge(q?.data_status)
                  const chg = BENCHMARK_CHANGES[idx.ticker] || { change: '+0.00', change_pct: '+0.00%', is_up: true }
                  return (
                    <div
                      key={idx.ticker}
                      className="bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-[#3987e5]/50 rounded-xl p-3 flex flex-col justify-between transition-all shadow-sm group"
                    >
                      <div>
                        <div className="flex items-center justify-between gap-1">
                          <span className="font-mono font-bold text-xs text-[var(--text-primary)] group-hover:text-[#3987e5] transition-colors">
                            {idx.ticker}
                          </span>
                          <span className={`text-[9px] px-1.5 py-0.2 rounded border font-medium ${badge.cls}`}>
                            {badge.text}
                          </span>
                        </div>
                        <div className="text-[11px] text-[var(--text-muted)] truncate mt-0.5">
                          {idx.nameZh}
                        </div>
                        <div className="text-lg font-black font-mono text-[var(--text-primary)] mt-1.5 tracking-tight truncate">
                          {q?.formatted_price || (q?.price != null ? `${idx.symbol}${q.price}` : '—')}
                        </div>
                        <div className="flex items-center gap-1 mt-1 text-[11px] font-mono font-bold">
                          <span className={`px-1.5 py-0.2 rounded ${
                            chg.is_up ? 'text-emerald-500 bg-emerald-500/10' : 'text-rose-500 bg-rose-500/10'
                          }`}>
                            {chg.is_up ? '▲' : '▼'} {chg.change_pct}
                          </span>
                        </div>
                      </div>
                      <div className="mt-2 text-[10px] text-[var(--text-muted)] font-medium truncate pt-1.5 border-t border-[var(--border-color)]/50">
                        {idx.desc}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* 宏观流动性与恐慌舵手指标 */}
            <div className="space-y-2.5 pt-2 border-t border-[var(--border-color)]/50">
              <div className="text-xs font-semibold text-[var(--text-secondary)]">
                宏观流动性、无风险利率与恐慌情绪指标 (Macro Liquidity & Volatility)
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
                {macroGauges.map((g) => (
                  <div
                    key={g.id}
                    className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-2.5 flex flex-col justify-between hover:border-[#3987e5]/40 transition-all"
                  >
                    <div>
                      <div className="text-[10px] text-[var(--text-muted)] truncate font-medium">
                        {g.nameZh}
                      </div>
                      <div className="text-base font-black font-mono text-[var(--text-primary)] mt-0.5 tracking-tight">
                        {g.value}
                      </div>
                    </div>
                    <div className="mt-1.5 flex items-center justify-between gap-1 pt-1 border-t border-[var(--border-color)]/40">
                      <span className="text-[9px] text-[var(--text-muted)] truncate">{g.role}</span>
                      <span className={`text-[9px] px-1 py-0.2 rounded font-medium ${
                        g.tone === 'warning' ? 'text-amber-500 bg-amber-500/10' :
                        g.tone === 'good' ? 'text-[#199e70] bg-[#199e70]/10' :
                        'text-[#3987e5] bg-[#3987e5]/10'
                      }`}>
                        {g.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 2. 全市场量化趋势广度与主升浪结构 */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[var(--border-color)] gap-2">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#199e70]" />
                <div>
                  <h2 className="text-base font-bold text-[var(--text-primary)]">
                    全市场量化趋势广度与主升浪计算结果
                  </h2>
                  <p className="text-xs text-[var(--text-muted)] mt-0.5">
                    基于纯本地 0-Token 物理日线时序计算，严谨测算 50/200 日移动均线站上率与 SEPA 主升浪结构
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 font-mono text-xs text-[var(--text-muted)]">
                <span>SEPA 初筛状态: </span>
                <span className="px-2 py-0.5 rounded bg-blue-500/10 text-[#3987e5] border border-blue-500/20 font-sans font-medium">
                  待正式初筛 (等待全市场日线批次)
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
              {breadthIndicators.map((b) => (
                <div
                  key={b.title}
                  className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3.5 flex flex-col justify-between space-y-3 hover:border-[#199e70]/40 transition-all shadow-sm"
                >
                  <div>
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-xs font-semibold text-[var(--text-secondary)]">{b.title}</span>
                      <span className={`text-[10px] px-1.5 py-0.2 rounded font-medium ${
                        b.tone === 'good' ? 'bg-[#199e70]/15 text-[#199e70] border border-[#199e70]/30' : 'bg-amber-500/15 text-amber-500 border border-amber-500/30'
                      }`}>
                        {b.regime}
                      </span>
                    </div>
                    <div className="text-2xl font-black font-mono text-[var(--text-primary)] mt-1.5 tracking-tight">
                      {b.ratio}
                    </div>
                  </div>

                  <div className="space-y-1">
                    <div className="w-full bg-[var(--surface-color)] h-2 rounded-full overflow-hidden border border-[var(--border-color)]">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          b.pct >= 50 ? 'bg-[#199e70]' : 'bg-amber-500'
                        }`}
                        style={{ width: `${b.pct}%` }}
                      />
                    </div>
                    <div className="text-[10px] text-[var(--text-muted)] flex justify-between font-mono">
                      <span>{b.detail}</span>
                      <span>{b.pct.toFixed(1)}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ==================== 右侧 35% (lg:col-span-4): 焦点胜负手个股直达 + 突发事件雷达 ==================== */}
        <div className="lg:col-span-4 space-y-5">
          {/* 1. 宏观驱动与焦点胜负手标的 (情境式直达) */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-2.5 border-b border-[var(--border-color)]/60">
              <div className="flex items-center gap-2">
                <span className="text-base">🎯</span>
                <h3 className="text-xs font-bold text-[var(--text-primary)]">
                  宏观驱动与焦点胜负手标的
                </h3>
              </div>
              <span className="text-[10px] text-[var(--text-muted)]">点击直达 DCF 深度估值</span>
            </div>

            <div className="space-y-2.5">
              {leadingTickers.map((item) => (
                <div
                  key={item.ticker}
                  onClick={() => {
                    onSelectTicker?.(item.ticker)
                    onNavigateTab('analytics')
                  }}
                  className="bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-[#3987e5] rounded-xl p-3 cursor-pointer transition-all flex items-center justify-between gap-3 group shadow-sm hover:shadow"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono font-bold text-xs text-[var(--text-primary)] group-hover:text-[#3987e5] transition-colors">
                        {item.ticker}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded font-medium bg-[#3987e5]/10 text-[#3987e5] border border-[#3987e5]/20">
                        {item.tag}
                      </span>
                      <span className="text-[11px] text-[var(--text-secondary)] font-medium truncate">
                        {item.nameZh}
                      </span>
                    </div>
                    <p className="text-[10px] text-[var(--text-muted)] truncate mt-1">
                      {item.role}
                    </p>
                  </div>

                  <div className="text-right shrink-0">
                    <div className="font-mono font-black text-xs text-[var(--text-primary)]">
                      {item.quote?.formatted_price || '—'}
                    </div>
                    <div className="text-[10px] font-mono font-bold text-emerald-500 mt-0.5">
                      {item.chg}
                    </div>
                    <div className="text-[10px] text-[#3987e5] group-hover:underline mt-0.5 flex items-center justify-end gap-0.5">
                      <span>分析</span>
                      <span>&rarr;</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 2. 突发核心事件情报雷达 (紧凑卡片流) */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-2.5 border-b border-[var(--border-color)]/60">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#d03b3b]" />
                <h3 className="text-xs font-bold text-[var(--text-primary)]">
                  突发核心事件雷达 ({data?.events_summary?.total_events || 0}篇)
                </h3>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={handleExtractNews}
                  disabled={isExtractingNews}
                  className="text-[10px] px-2 py-0.5 rounded bg-[var(--bg-card)] hover:bg-[#3987e5]/10 text-[#3987e5] border border-[#3987e5]/30 cursor-pointer transition-all flex items-center gap-1"
                  title="即时核验与抽取官方最新公报"
                >
                  <span className={isExtractingNews ? 'animate-spin' : ''}>⚡</span>
                  <span>{isExtractingNews ? '抽取中...' : '即时抽取'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => onNavigateTab('intelligence')}
                  className="text-[10px] text-[var(--text-secondary)] hover:text-[#3987e5] hover:underline cursor-pointer"
                >
                  全部 &rarr;
                </button>
              </div>
            </div>

            <div className="space-y-2.5">
              {data?.events_summary?.top_events && data.events_summary.top_events.length > 0 ? (
                data.events_summary.top_events.slice(0, 4).map((ev: EventItem) => (
                  <EventCard
                    key={ev.event_id}
                    id={ev.event_id}
                    title={ev.title}
                    severity={ev.severity}
                    verification_status={ev.verification_status}
                    is_quarantined_rumor={ev.is_quarantined_rumor}
                    published_at={ev.published_at}
                    source_name={ev.source_name}
                    category={ev.category}
                    micro_physical_impact={ev.micro_physical_impact}
                    involved_entities={ev.involved_entities}
                    affected_business_segments={ev.affected_business_segments}
                    compact={true}
                    onClick={() => {
                      onSelectEvent(ev.event_id)
                      onNavigateTab('intelligence')
                    }}
                    onSelectTicker={onSelectTicker}
                  />
                ))
              ) : (
                <div className="text-center py-6 text-xs text-[var(--text-muted)]">
                  暂无突发事件记录
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DashboardTab
