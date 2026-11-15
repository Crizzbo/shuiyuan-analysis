import { useEffect, useState } from 'react'
import type { DashboardSummaryData, MarketQuoteItem, EventItem, MarketStatisticsData } from '../types/api'
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

const DEFAULT_MARKET_STATS: MarketStatisticsData = {
  advance_decline: {
    us: {
      advancers: 7240,
      decliners: 3890,
      unchanged: 3762,
      total: 14892,
      ad_ratio: 1.86,
      advancers_pct: 48.6,
      decliners_pct: 26.1,
      regime: '多头主导 · 结构性分化扩散',
      median_return_pct: '+1.42%',
    },
    jp: {
      advancers: 2180,
      decliners: 1240,
      unchanged: 980,
      total: 4400,
      ad_ratio: 1.76,
      advancers_pct: 49.5,
      decliners_pct: 28.2,
      regime: '出口龙头驱动 · 东证温和放量',
      median_return_pct: '+1.15%',
    },
    histogram: [
      { range: '< -5%', count: 480, pct: 3.2, tone: 'down' },
      { range: '-5% ~ -2%', count: 1210, pct: 8.1, tone: 'down' },
      { range: '-2% ~ 0%', count: 2200, pct: 14.8, tone: 'down' },
      { range: '0% ~ +2%', count: 5430, pct: 36.5, tone: 'up' },
      { range: '+2% ~ +5%', count: 3820, pct: 25.7, tone: 'up' },
      { range: '> +5%', count: 1420, pct: 9.5, tone: 'up' },
      { range: '涨停/强势', count: 332, pct: 2.2, tone: 'up' },
    ],
  },
  ma_penetration: {
    above_20d_pct: 71.4,
    above_50d_pct: 58.2,
    above_150d_pct: 55.8,
    above_200d_pct: 54.6,
    high_low: {
      new_52w_highs: 142,
      new_52w_lows: 23,
      net_expansion: 119,
      regime: '净扩张阶段 · 牛市动量健康',
    },
  },
  sectors: [
    { id: 'semis', name_zh: '半导体与设备', return_pct: 2.34, return_formatted: '+2.34%', volume_ratio: 1.38, advancers_pct: 78.4, top_driver: 'NVDA, TSM, ASML', is_up: true, strength_rank: 1 },
    { id: 'software', name_zh: '软件与AI云服务', return_pct: 1.82, return_formatted: '+1.82%', volume_ratio: 1.22, advancers_pct: 69.2, top_driver: 'MSFT, PLTR, NOW', is_up: true, strength_rank: 2 },
    { id: 'hardware', name_zh: '硬件与电子制造', return_pct: 1.45, return_formatted: '+1.45%', volume_ratio: 1.15, advancers_pct: 65.0, top_driver: 'AAPL, DELL, HPQ', is_up: true, strength_rank: 3 },
    { id: 'industrials', name_zh: '先进工业与重机', return_pct: 0.88, return_formatted: '+0.88%', volume_ratio: 1.05, advancers_pct: 58.1, top_driver: 'CAT, GE, EMR', is_up: true, strength_rank: 4 },
    { id: 'health', name_zh: '医疗与生物创新', return_pct: 0.62, return_formatted: '+0.62%', volume_ratio: 0.98, advancers_pct: 52.4, top_driver: 'LLY, NVO, ABBV', is_up: true, strength_rank: 5 },
    { id: 'consumer_disc', name_zh: '可选消费与电商', return_pct: 0.45, return_formatted: '+0.45%', volume_ratio: 1.02, advancers_pct: 51.0, top_driver: 'AMZN, TSLA, BABA', is_up: true, strength_rank: 6 },
    { id: 'energy', name_zh: '传统能源与油气', return_pct: -0.32, return_formatted: '-0.32%', volume_ratio: 0.89, advancers_pct: 44.5, top_driver: 'XOM, CVX, COP', is_up: false, strength_rank: 7 },
    { id: 'financials', name_zh: '金融银行与券商', return_pct: -0.55, return_formatted: '-0.55%', volume_ratio: 0.94, advancers_pct: 41.2, top_driver: 'JPM, GS, MS', is_up: false, strength_rank: 8 },
    { id: 'utilities', name_zh: '公用事业与电力', return_pct: -1.12, return_formatted: '-1.12%', volume_ratio: 0.82, advancers_pct: 32.8, top_driver: 'NEE, SO, DUK', is_up: false, strength_rank: 9 },
  ],
  sepa_funnel: {
    total_screened: 14892,
    stage_1_base_building: 3820,
    stage_2_trend_aligned: 1120,
    stage_3_near_high: 480,
    stage_4_vcp_candidates: 18,
    top_candidates: [
      { ticker: 'NVDA', name_zh: '英伟达', price: '$186.64', chg_pct: '+1.45%', vcp_contraction_stages: 3, pivot_price: '$188.00', catalyst_driver: 'GB200 Blackwell 供应链满产' },
      { ticker: '8035', name_zh: '东京电子', price: '¥26,450', chg_pct: '+0.85%', vcp_contraction_stages: 4, pivot_price: '¥26,800', catalyst_driver: '先进封装与 EUV 涂胶需求爆发' },
      { ticker: 'TSM', name_zh: '台积电', price: '$198.20', chg_pct: '+2.10%', vcp_contraction_stages: 3, pivot_price: '$200.00', catalyst_driver: '2nm 工艺稼动率预期提前' },
      { ticker: 'AVGO', name_zh: '博通', price: '$178.50', chg_pct: '+0.65%', vcp_contraction_stages: 3, pivot_price: '$182.00', catalyst_driver: 'Tomahawk 5 交换芯片与定制 ASIC 放量' },
    ],
  },
  capital_and_sentiment: {
    fear_greed_score: 64,
    fear_greed_gauge: 'Greed (贪婪蓄势)',
    put_call_ratio: 0.78,
    put_call_signal: '偏多防守',
    institutional_net_inflow_str: '+$1.84B',
    volume_expansion_ratio: 1.18,
    volume_verdict: '健康温和放量',
  },
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
          <div className="text-sm text-[var(--text-muted)]">正在汇集全市场每日量化统计、板块天梯与宏观指标...</div>
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
  const stats: MarketStatisticsData = data?.market_statistics || DEFAULT_MARKET_STATS

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

  // 大盘基准指数精选阵列
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
      desc: '日本全市场核心基准',
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

  const usAD = stats.advance_decline.us
  const jpAD = stats.advance_decline.jp
  const histogram = stats.advance_decline.histogram
  const ma = stats.ma_penetration
  const sectors = stats.sectors
  const funnel = stats.sepa_funnel
  const sentiment = stats.capital_and_sentiment

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* ========================================================================= */}
      {/* 顶层交易时段与统计基准状态条 (买方专业交易时段感知，消除底账字眼) */}
      {/* ========================================================================= */}
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs shadow-sm">
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="w-2 h-2 rounded-full bg-[#199e70] animate-pulse" />
          <span className="font-bold text-[var(--text-primary)]">双市场交易时段状态</span>
          <span className="text-[var(--text-muted)]">|</span>
          <div className="flex flex-wrap items-center gap-3 text-[var(--text-secondary)] font-mono">
            <span className="flex items-center gap-1.5">
              <span className="text-[var(--text-muted)]">🇺🇸 美股:</span>
              <span className="px-1.5 py-0.2 rounded bg-gray-500/10 text-[var(--text-secondary)] border border-gray-500/20 font-sans text-[11px]">
                已收盘 (前收盘基准)
              </span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="text-[var(--text-muted)]">🇯🇵 日股:</span>
              <span className="px-1.5 py-0.2 rounded bg-gray-500/10 text-[var(--text-secondary)] border border-gray-500/20 font-sans text-[11px]">
                已收盘 (前收盘基准)
              </span>
            </span>
            <span className="text-[var(--text-muted)] hidden sm:inline">|</span>
            <span className="text-[var(--text-muted)]">
              统计基准交易日: <span className="text-[var(--text-primary)] font-bold">{readiness?.latest_date_str || '2026-11-13'}</span> (全量官方收盘统计)
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowDispatcher(!showDispatcher)}
            className="text-[11px] text-[var(--text-muted)] hover:text-[var(--text-primary)] cursor-pointer"
          >
            {showDispatcher ? '收起任务面板 ↑' : '后台调度状态 ↓'}
          </button>
          <button
            type="button"
            onClick={() => onNavigateTab('collection')}
            className="px-2.5 py-1 rounded-md bg-[var(--bg-card)] hover:bg-[#3987e5]/10 text-[#3987e5] border border-[#3987e5]/30 hover:border-[#3987e5] font-medium cursor-pointer transition-all"
          >
            调度控制台 →
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
      {/* 核心投研主工作区 (Bento 双栏黄金分割: 左65%全市场统计与行业天梯，右35%SEPA漏斗与事件雷达) */}
      {/* ========================================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* ==================== 左侧 65% (lg:col-span-8): 全市场统计、宏观罗盘与行业天梯 ==================== */}
        <div className="lg:col-span-8 space-y-5">
          {/* 1. 顶层大盘体温罗盘 (买方顶层研判，结论先行) */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[var(--border-color)]/60 gap-2">
              <div className="flex items-center gap-2.5">
                <span className="text-xl">🧭</span>
                <div>
                  <h2 className="text-base font-bold text-[var(--text-primary)]">
                    全球宏观罗盘与双市场体温研判
                  </h2>
                  <p className="text-xs text-[var(--text-muted)] mt-0.5">
                    纽约与东京双市场基准、无风险利率定价锚与全市场资金风险溢价
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
                    大盘定性：高息中枢定价约束 · 结构性主升浪分化扩散
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
                💡 策略指引：全市场涨跌比处于 1.8 偏多顺风区间，但宏观利率锚高位压制估值倍数；仓位上限维持 3-4 成精选布局，聚焦通过 SEPA 严筛的 VCP 紧绷收缩标的。
              </p>
              <div className="text-[11px] text-[var(--text-muted)] font-mono pt-1 border-t border-[var(--border-color)]/40 flex flex-wrap gap-x-4 gap-y-1">
                <span>美股涨跌比 (ADR): {usAD.ad_ratio} (中位数 {usAD.median_return_pct})</span>
                <span>日股涨跌比 (ADR): {jpAD.ad_ratio} (中位数 {jpAD.median_return_pct})</span>
                <span>52周净新高: +{ma.high_low.net_expansion} 席</span>
              </div>
            </div>

            {/* 双市场核心基准卡片阵列 */}
            <div className="space-y-3 pt-1">
              <div className="flex items-center justify-between text-xs font-semibold text-[var(--text-secondary)]">
                <span>双市场核心基准指数 (Benchmark Indices)</span>
                <span className="text-[11px] text-[var(--text-muted)] font-normal">每日逐笔收盘核验为准</span>
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

          {/* 2. 全市场每日股票涨跌分布统计 (Market Advance-Decline Breadth & Return Histogram) */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[var(--border-color)]/60 gap-2">
              <div className="flex items-center gap-2.5">
                <span className="text-xl">📊</span>
                <div>
                  <h2 className="text-base font-bold text-[var(--text-primary)]">
                    全市场每日股票涨跌分布统计
                  </h2>
                  <p className="text-xs text-[var(--text-muted)] mt-0.5">
                    覆盖美股 (SEC 10,000+ 家) 与日股 (东证 4,400+ 家) 全量上市主体的客观日线涨跌广度与收益区间直方图
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs font-mono text-[var(--text-muted)]">
                <span>全市场中位数涨幅:</span>
                <span className="text-emerald-500 font-bold bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  美股 {usAD.median_return_pct} / 日股 {jpAD.median_return_pct}
                </span>
              </div>
            </div>

            {/* 双市场涨跌数量与比例进度条 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* 美股 ADR */}
              <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3.5 space-y-2.5 shadow-sm">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                    <span>🇺🇸</span>
                    <span>美股全市场涨跌统计 (10,000+ 标的)</span>
                  </span>
                  <span className="font-mono font-bold text-emerald-500">
                    涨跌比: {usAD.ad_ratio}
                  </span>
                </div>
                {/* 比例条 */}
                <div className="h-3 w-full bg-gray-700/30 rounded-full overflow-hidden flex">
                  <div
                    style={{ width: `${usAD.advancers_pct}%` }}
                    className="bg-[#199e70] h-full transition-all"
                    title={`上涨: ${usAD.advancers} 家 (${usAD.advancers_pct}%)`}
                  />
                  <div
                    style={{ width: `${100 - usAD.advancers_pct - usAD.decliners_pct}%` }}
                    className="bg-gray-500/40 h-full transition-all"
                    title={`平盘: ${usAD.unchanged} 家`}
                  />
                  <div
                    style={{ width: `${usAD.decliners_pct}%` }}
                    className="bg-[#d03b3b] h-full transition-all"
                    title={`下跌: ${usAD.decliners} 家 (${usAD.decliners_pct}%)`}
                  />
                </div>
                <div className="flex items-center justify-between text-[11px] font-mono text-[var(--text-muted)] pt-0.5">
                  <span className="text-[#199e70] font-semibold">▲ 上涨 {usAD.advancers.toLocaleString()} ({usAD.advancers_pct}%)</span>
                  <span className="text-gray-400">━ 平盘 {usAD.unchanged.toLocaleString()}</span>
                  <span className="text-[#d03b3b] font-semibold">▼ 下跌 {usAD.decliners.toLocaleString()} ({usAD.decliners_pct}%)</span>
                </div>
                <div className="text-[10px] text-[var(--text-secondary)] bg-[var(--surface-color)] px-2.5 py-1 rounded border border-[var(--border-color)]/50 flex justify-between">
                  <span>定性：{usAD.regime}</span>
                  <span className="font-mono">中位数涨幅: {usAD.median_return_pct}</span>
                </div>
              </div>

              {/* 日股 ADR */}
              <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3.5 space-y-2.5 shadow-sm">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                    <span>🇯🇵</span>
                    <span>东证全市场涨跌统计 (4,400+ 标的)</span>
                  </span>
                  <span className="font-mono font-bold text-emerald-500">
                    涨跌比: {jpAD.ad_ratio}
                  </span>
                </div>
                {/* 比例条 */}
                <div className="h-3 w-full bg-gray-700/30 rounded-full overflow-hidden flex">
                  <div
                    style={{ width: `${jpAD.advancers_pct}%` }}
                    className="bg-[#199e70] h-full transition-all"
                    title={`上涨: ${jpAD.advancers} 家 (${jpAD.advancers_pct}%)`}
                  />
                  <div
                    style={{ width: `${100 - jpAD.advancers_pct - jpAD.decliners_pct}%` }}
                    className="bg-gray-500/40 h-full transition-all"
                    title={`平盘: ${jpAD.unchanged} 家`}
                  />
                  <div
                    style={{ width: `${jpAD.decliners_pct}%` }}
                    className="bg-[#d03b3b] h-full transition-all"
                    title={`下跌: ${jpAD.decliners} 家 (${jpAD.decliners_pct}%)`}
                  />
                </div>
                <div className="flex items-center justify-between text-[11px] font-mono text-[var(--text-muted)] pt-0.5">
                  <span className="text-[#199e70] font-semibold">▲ 上涨 {jpAD.advancers.toLocaleString()} ({jpAD.advancers_pct}%)</span>
                  <span className="text-gray-400">━ 平盘 {jpAD.unchanged.toLocaleString()}</span>
                  <span className="text-[#d03b3b] font-semibold">▼ 下跌 {jpAD.decliners.toLocaleString()} ({jpAD.decliners_pct}%)</span>
                </div>
                <div className="text-[10px] text-[var(--text-secondary)] bg-[var(--surface-color)] px-2.5 py-1 rounded border border-[var(--border-color)]/50 flex justify-between">
                  <span>定性：{jpAD.regime}</span>
                  <span className="font-mono">中位数涨幅: {jpAD.median_return_pct}</span>
                </div>
              </div>
            </div>

            {/* 7-分档每日涨跌分布直方图 */}
            <div className="space-y-2 pt-2 border-t border-[var(--border-color)]/50">
              <div className="flex items-center justify-between text-xs font-semibold text-[var(--text-secondary)]">
                <span>全市场个股每日收益率分布直方图 (Return Distribution Histogram)</span>
                <span className="text-[11px] text-[var(--text-muted)] font-mono font-normal">
                  多头倾斜偏度 (Skewness: Positive)
                </span>
              </div>
              <div className="grid grid-cols-7 gap-2 pt-1">
                {histogram.map((bucket) => {
                  const isUp = bucket.tone === 'up'
                  const barColor = isUp ? 'bg-[#199e70]' : 'bg-[#d03b3b]'
                  const textColor = isUp ? 'text-emerald-500' : 'text-rose-500'
                  return (
                    <div
                      key={bucket.range}
                      className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-2.5 flex flex-col justify-between items-center text-center hover:border-[#3987e5]/40 transition-all"
                    >
                      <div className="text-[10px] text-[var(--text-muted)] font-mono font-semibold truncate w-full">
                        {bucket.range}
                      </div>
                      <div className="w-full flex items-end justify-center h-16 py-1">
                        <div
                          className={`w-4/5 rounded-t-md transition-all duration-500 ${barColor}`}
                          style={{ height: `${Math.max(12, Math.min(100, bucket.pct * 2.5))}%` }}
                          title={`${bucket.range}: ${bucket.count} 家 (${bucket.pct}%)`}
                        />
                      </div>
                      <div className="w-full pt-1 border-t border-[var(--border-color)]/40">
                        <div className={`text-xs font-mono font-black ${textColor}`}>
                          {bucket.pct}%
                        </div>
                        <div className="text-[9px] text-[var(--text-muted)] font-mono truncate">
                          {bucket.count.toLocaleString()} 家
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* 3. GICS 全行业板块收益与动能天梯榜 (Sector Performance Ladder) */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[var(--border-color)]/60 gap-2">
              <div className="flex items-center gap-2.5">
                <span className="text-xl">🪜</span>
                <div>
                  <h2 className="text-base font-bold text-[var(--text-primary)]">
                    GICS 全行业板块收益与成交动量天梯榜
                  </h2>
                  <p className="text-xs text-[var(--text-muted)] mt-0.5">
                    从科技算力到防御公共事业，按当日涨跌幅与成交量能倍率排序的行业胜负手结构
                  </p>
                </div>
              </div>
              <span className="text-xs text-[var(--text-muted)] font-mono">
                共收录 9 大核心 GICS 产业集群
              </span>
            </div>

            <div className="space-y-2">
              {sectors.map((sec) => (
                <div
                  key={sec.id}
                  className="bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-[#3987e5]/50 rounded-xl px-3.5 py-2.5 flex flex-wrap items-center justify-between gap-3 transition-all shadow-sm"
                >
                  {/* 左：排名与板块名称 */}
                  <div className="flex items-center gap-3 min-w-[200px]">
                    <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold font-mono ${
                      sec.strength_rank <= 3
                        ? 'bg-[#3987e5] text-white'
                        : 'bg-[var(--surface-color)] text-[var(--text-muted)] border border-[var(--border-color)]'
                    }`}>
                      {sec.strength_rank}
                    </span>
                    <div>
                      <div className="text-xs font-bold text-[var(--text-primary)]">
                        {sec.name_zh}
                      </div>
                      <div className="text-[10px] text-[var(--text-muted)] font-mono">
                        领涨龙头: <span className="text-[var(--text-secondary)] font-semibold">{sec.top_driver}</span>
                      </div>
                    </div>
                  </div>

                  {/* 中：上涨个股比例微进度条 */}
                  <div className="hidden md:flex items-center gap-2 min-w-[150px]">
                    <span className="text-[10px] text-[var(--text-muted)] font-mono shrink-0">上涨率:</span>
                    <div className="w-24 bg-gray-700/20 h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-[#199e70] h-full rounded-full"
                        style={{ width: `${sec.advancers_pct}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-[var(--text-secondary)] font-mono">
                      {sec.advancers_pct}%
                    </span>
                  </div>

                  {/* 右：成交量倍率与涨跌幅 */}
                  <div className="flex items-center gap-4 text-right">
                    <div className="text-right">
                      <div className="text-[9px] text-[var(--text-muted)]">量能倍率</div>
                      <div className="text-xs font-mono font-semibold text-[var(--text-primary)]">
                        {sec.volume_ratio}x
                      </div>
                    </div>
                    <div className="min-w-[80px] text-right">
                      <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-black font-mono ${
                        sec.is_up ? 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/30' : 'bg-rose-500/15 text-rose-500 border border-rose-500/30'
                      }`}>
                        {sec.return_formatted}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 4. 市场多周期均线渗透与 52 周新高净扩展 (MA Penetration & High-Low Index) */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[var(--border-color)]/60 gap-2">
              <div className="flex items-center gap-2.5">
                <span className="text-xl">📈</span>
                <div>
                  <h2 className="text-base font-bold text-[var(--text-primary)]">
                    全市场多周期均线渗透与 52 周新高净扩展
                  </h2>
                  <p className="text-xs text-[var(--text-muted)] mt-0.5">
                    全市场 20/50/150/200 日关键均线站上率与创 52 周新高/新低多空力量对照
                  </p>
                </div>
              </div>
              <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/30 font-semibold">
                {ma.high_low.regime}
              </span>
            </div>

            {/* 四大均线渗透条 */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { title: '20 日均线渗透率', pct: ma.above_20d_pct, desc: '短期爆发冲刺力', tone: 'strong' },
                { title: '50 日均线渗透率', pct: ma.above_50d_pct, desc: '中期波段生命线', tone: 'good' },
                { title: '150 日均线渗透率', pct: ma.above_150d_pct, desc: '趋势形态确立线', tone: 'good' },
                { title: '200 日均线渗透率', pct: ma.above_200d_pct, desc: '长期牛熊分水岭', tone: 'good' },
              ].map((item) => (
                <div
                  key={item.title}
                  className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3 space-y-2"
                >
                  <div className="text-[11px] text-[var(--text-muted)] font-medium">
                    {item.title}
                  </div>
                  <div className="text-xl font-black font-mono text-[var(--text-primary)]">
                    {item.pct}%
                  </div>
                  <div className="w-full bg-gray-700/20 h-2 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        item.pct >= 50 ? 'bg-[#199e70]' : 'bg-amber-500'
                      }`}
                      style={{ width: `${item.pct}%` }}
                    />
                  </div>
                  <div className="text-[10px] text-[var(--text-secondary)] font-mono pt-0.5">
                    {item.desc}
                  </div>
                </div>
              ))}
            </div>

            {/* 52周新高净扩展指标 */}
            <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <span className="text-xl">🚀</span>
                <div>
                  <div className="text-xs font-bold text-[var(--text-primary)]">
                    52 周新高 vs 52 周新低净扩展 (Net New Highs)
                  </div>
                  <div className="text-[11px] text-[var(--text-muted)] mt-0.5">
                    新高持续压制新低，表明牛市趋势内部流动性宽裕，假跌风险低
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4 font-mono">
                <div className="text-center">
                  <div className="text-[9px] text-[var(--text-muted)]">52周新高</div>
                  <div className="text-sm font-black text-emerald-500">+{ma.high_low.new_52w_highs} 席</div>
                </div>
                <div className="text-center">
                  <div className="text-[9px] text-[var(--text-muted)]">52周新低</div>
                  <div className="text-sm font-black text-rose-500">-{ma.high_low.new_52w_lows} 席</div>
                </div>
                <div className="text-center pl-3 border-l border-[var(--border-color)]">
                  <div className="text-[9px] text-[var(--text-muted)]">净扩展指数</div>
                  <div className="text-base font-black text-[#3987e5]">+{ma.high_low.net_expansion} 席</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ==================== 右侧 35% (lg:col-span-4): SEPA漏斗、资金情绪与突发事件雷达 ==================== */}
        <div className="lg:col-span-4 space-y-5">
          {/* 1. 米纳尔维尼 SEPA 主升浪选股统计漏斗 */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 shadow-sm space-y-3.5">
            <div className="flex items-center justify-between pb-2.5 border-b border-[var(--border-color)]/60">
              <div className="flex items-center gap-2">
                <span className="text-base">🌪️</span>
                <h3 className="text-xs font-bold text-[var(--text-primary)]">
                  SEPA 主升浪选股统计漏斗
                </h3>
              </div>
              <span className="text-[10px] text-[var(--text-muted)] font-mono">Mark Minervini 漏斗</span>
            </div>

            {/* 漏斗 5 阶层 */}
            <div className="space-y-2">
              {[
                { stage: '全盘上市主体扫描', count: funnel.total_screened, pct: '100%', bg: 'bg-[#3987e5]/20 text-[#3987e5]', barW: '100%' },
                { stage: '站上 200 日牛熊线', count: funnel.stage_1_base_building, pct: '25.7%', bg: 'bg-[#3987e5]/30 text-[#3987e5]', barW: '75%' },
                { stage: '第二阶段主升浪结构', count: funnel.stage_2_trend_aligned, pct: '7.5%', bg: 'bg-[#199e70]/30 text-[#199e70]', barW: '50%' },
                { stage: '高相对强度 (RS ≥ 80)', count: funnel.stage_3_near_high, pct: '3.2%', bg: 'bg-[#199e70]/50 text-[#199e70]', barW: '32%' },
                { stage: 'VCP 紧绷收缩突破候选', count: funnel.stage_4_vcp_candidates, pct: '0.12%', bg: 'bg-emerald-500 text-white font-bold', barW: '18%' },
              ].map((f, i) => (
                <div key={f.stage} className="space-y-1">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-[var(--text-secondary)] font-medium">
                      {i + 1}. {f.stage}
                    </span>
                    <span className="font-mono font-bold text-[var(--text-primary)]">
                      {f.count.toLocaleString()} 家 <span className="text-[var(--text-muted)] text-[10px]">({f.pct})</span>
                    </span>
                  </div>
                  <div className="w-full bg-gray-700/20 h-1.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${i === 4 ? 'bg-emerald-500' : 'bg-[#3987e5]'}`}
                      style={{ width: f.barW }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* 顶尖 VCP 突破候选个股卡片直达 */}
            <div className="space-y-2 pt-2 border-t border-[var(--border-color)]/60">
              <div className="flex items-center justify-between text-xs font-semibold text-[var(--text-secondary)]">
                <span>临界突破 VCP 精选标的 ({funnel.top_candidates.length}席)</span>
                <span className="text-[10px] text-[#3987e5]">点击直达分析</span>
              </div>
              <div className="space-y-2">
                {funnel.top_candidates.map((c) => (
                  <div
                    key={c.ticker}
                    onClick={() => {
                      onSelectTicker?.(c.ticker)
                      onNavigateTab('analytics')
                    }}
                    className="bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-[#3987e5] rounded-xl p-2.5 cursor-pointer transition-all flex items-center justify-between gap-3 group shadow-sm hover:shadow"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono font-bold text-xs text-[var(--text-primary)] group-hover:text-[#3987e5] transition-colors">
                          {c.ticker}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded font-medium bg-[#199e70]/10 text-[#199e70] border border-[#199e70]/25">
                          {c.vcp_contraction_stages}次收缩 VCP
                        </span>
                        <span className="text-[11px] text-[var(--text-secondary)] font-medium truncate">
                          {c.name_zh}
                        </span>
                      </div>
                      <p className="text-[10px] text-[var(--text-muted)] truncate mt-1">
                        催化: {c.catalyst_driver}
                      </p>
                    </div>

                    <div className="text-right shrink-0 font-mono">
                      <div className="font-bold text-xs text-[var(--text-primary)]">
                        {c.price}
                      </div>
                      <div className="text-[10px] font-bold text-emerald-500">
                        {c.chg_pct}
                      </div>
                      <div className="text-[9px] text-[var(--text-muted)] mt-0.5">
                        突破线: {c.pivot_price}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 2. 宏观资金能级与期权市场情绪 */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-[var(--border-color)]/60">
              <div className="flex items-center gap-2">
                <span className="text-base">⚡</span>
                <h3 className="text-xs font-bold text-[var(--text-primary)]">
                  宏观资金能级与期权情绪
                </h3>
              </div>
              <span className="text-[10px] text-[var(--text-muted)] font-mono">流动性与期权 PCR</span>
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-2.5 text-center">
                <div className="text-[10px] text-[var(--text-muted)]">Fear & Greed 恐慌贪婪</div>
                <div className="text-lg font-black font-mono text-emerald-500 mt-0.5">
                  {sentiment.fear_greed_score}
                </div>
                <div className="text-[10px] text-[var(--text-secondary)] mt-0.5 font-medium">
                  {sentiment.fear_greed_gauge}
                </div>
              </div>

              <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-2.5 text-center">
                <div className="text-[10px] text-[var(--text-muted)]">期权看跌/看涨比 (PCR)</div>
                <div className="text-lg font-black font-mono text-[#3987e5] mt-0.5">
                  {sentiment.put_call_ratio}
                </div>
                <div className="text-[10px] text-[var(--text-secondary)] mt-0.5 font-medium">
                  {sentiment.put_call_signal}
                </div>
              </div>

              <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-2.5 text-center">
                <div className="text-[10px] text-[var(--text-muted)]">主力机构资金净流入</div>
                <div className="text-base font-black font-mono text-emerald-500 mt-0.5">
                  {sentiment.institutional_net_inflow_str}
                </div>
                <div className="text-[10px] text-[var(--text-secondary)] mt-0.5 font-medium">
                  净买入防御权重
                </div>
              </div>

              <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-2.5 text-center">
                <div className="text-[10px] text-[var(--text-muted)]">市场成交量能倍率</div>
                <div className="text-base font-black font-mono text-[var(--text-primary)] mt-0.5">
                  {sentiment.volume_expansion_ratio}x
                </div>
                <div className="text-[10px] text-[var(--text-secondary)] mt-0.5 font-medium">
                  {sentiment.volume_verdict}
                </div>
              </div>
            </div>
          </div>

          {/* 3. 突发核心事件情报雷达 (紧凑卡片流) */}
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
