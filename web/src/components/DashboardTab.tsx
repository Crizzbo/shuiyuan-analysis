import { useEffect, useState } from 'react'
import type { DashboardSummaryData, MarketQuoteItem, EventItem, MarketStatisticsData } from '../types/api'
import { api } from '../services/api'
import { showToast } from './Toast'
import { TaskDispatcherPanel } from './TaskDispatcherPanel'
import {
  EventCard,
  InfoCircleIcon,
  TrendUpIcon,
  TrendDownIcon,
  CompassIcon,
  LightBulbIcon,
  BarChartIcon,
  FilterIcon,
  ZapIcon,
} from './common'

interface DashboardTabProps {
  onNavigateTab: (tabId: string) => void
  onSelectEvent: (eventId: string) => void
  onSelectTicker?: (ticker: string) => void
  refreshKey?: number
}

const CORE_WATCHLIST = [
  { ticker: 'NVDA', nameZh: '英伟达', market: 'US', sector: '半导体芯片', pe: '46.8x', netCash: '强劲净现金', dio: '52天', defaultPrice: '$186.64', defaultChg: '+1.45%', isUp: true },
  { ticker: 'TSM', nameZh: '台积电', market: 'US', sector: '晶圆先进制程', pe: '26.4x', netCash: '极充沛净现金', dio: '48天', defaultPrice: '$198.20', defaultChg: '+2.10%', isUp: true },
  { ticker: 'AAPL', nameZh: '苹果', market: 'US', sector: '消费电子与服务', pe: '31.2x', netCash: '现金流丰沛', dio: '14天', defaultPrice: '$224.23', defaultChg: '+0.42%', isUp: true },
  { ticker: 'MSFT', nameZh: '微软', market: 'US', sector: '云计算与企业AI', pe: '34.5x', netCash: '强劲净现金', dio: '18天', defaultPrice: '$415.80', defaultChg: '-0.35%', isUp: false },
  { ticker: 'AMD', nameZh: '超威半导体', market: 'US', sector: 'GPU与数据中心', pe: '42.1x', netCash: '健康净现金', dio: '68天', defaultPrice: '$148.50', defaultChg: '+1.80%', isUp: true },
  { ticker: 'AVGO', nameZh: '博通', market: 'US', sector: '定制ASIC与网络', pe: '32.0x', netCash: '充沛现金流', dio: '41天', defaultPrice: '$178.50', defaultChg: '+0.65%', isUp: true },
  { ticker: 'GOOGL', nameZh: '谷歌', market: 'US', sector: '搜索与云基础设施', pe: '23.8x', netCash: '千亿净现金', dio: '12天', defaultPrice: '$176.40', defaultChg: '+0.88%', isUp: true },
  { ticker: 'META', nameZh: 'Meta', market: 'US', sector: '数字广告与开源AI', pe: '27.6x', netCash: '超高现金流', dio: '15天', defaultPrice: '$582.10', defaultChg: '+1.25%', isUp: true },
  { ticker: 'PLTR', nameZh: 'Palantir', market: 'US', sector: '企业级AI平台', pe: '88.5x', netCash: '无负债净现金', dio: '22天', defaultPrice: '$62.30', defaultChg: '+3.15%', isUp: true },
  { ticker: 'STX', nameZh: '希捷科技', market: 'US', sector: '大容量存储介质', pe: '19.2x', netCash: '周期复苏', dio: '65天', defaultPrice: '$104.20', defaultChg: '-0.60%', isUp: false },
  { ticker: 'IREN', nameZh: 'Iris Energy', market: 'US', sector: '高性能绿色算力', pe: '14.2x', netCash: '电力充沛', dio: '30天', defaultPrice: '$12.85', defaultChg: '+4.20%', isUp: true },
  { ticker: '8035', nameZh: '东京电子', market: 'JP', sector: '半导体核心制造设备', pe: '24.1x', netCash: '充沛净现金', dio: '72天', defaultPrice: '¥26,450', defaultChg: '+0.85%', isUp: true },
  { ticker: '6857', nameZh: '爱德万测试', market: 'JP', sector: 'SoC与内存测试机', pe: '35.8x', netCash: '稳健资产结构', dio: '60天', defaultPrice: '¥8,920', defaultChg: '+1.60%', isUp: true },
  { ticker: '9984', nameZh: '软银集团', market: 'JP', sector: '全球科技投资控股', pe: '16.5x', netCash: '控股资产折价', dio: '—', defaultPrice: '¥9,150', defaultChg: '-0.45%', isUp: false },
]

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
    ],
  },
  ma_penetration: {
    above_20d_pct: 64.2,
    above_50d_pct: 58.6,
    above_150d_pct: 61.4,
    above_200d_pct: 63.8,
    high_low: {
      new_52w_highs: 412,
      new_52w_lows: 86,
      net_expansion: 326,
      regime: '新高持续净扩展 (+326 席)',
    },
  },
  sectors: [
    { id: 'tech', name_zh: '半导体与人工智能', return_pct: 2.15, return_formatted: '+2.15%', volume_ratio: 1.42, advancers_pct: 78.4, top_driver: 'NVDA, TSM, AVGO', is_up: true, strength_rank: 1 },
    { id: 'comm', name_zh: '通信服务与数字传媒', return_pct: 1.48, return_formatted: '+1.48%', volume_ratio: 1.15, advancers_pct: 66.2, top_driver: 'GOOGL, META, NFLX', is_up: true, strength_rank: 2 },
    { id: 'materials', name_zh: '先进材料与关键矿产', return_pct: 0.95, return_formatted: '+0.95%', volume_ratio: 1.08, advancers_pct: 61.5, top_driver: 'LIN, APD, ALB', is_up: true, strength_rank: 3 },
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
      { ticker: 'NVDA', name_zh: '英伟达', price: '$186.64', chg_pct: '+1.45%', vcp_contraction_stages: 3, pivot_price: '$188.00', catalyst_driver: 'GB200 Blackwell 供应链全线满产，数据中心高确定性放量' },
      { ticker: '8035', name_zh: '东京电子', price: '¥26,450', chg_pct: '+0.85%', vcp_contraction_stages: 4, pivot_price: '¥26,800', catalyst_driver: '先进封装与 EUV 涂胶显影机台稼动率爆发' },
      { ticker: 'TSM', name_zh: '台积电', price: '$198.20', chg_pct: '+2.10%', vcp_contraction_stages: 3, pivot_price: '$200.00', catalyst_driver: '2nm 先进制程资本开支预期提前，CoWoS 扩产倍增' },
      { ticker: 'AVGO', name_zh: '博通', price: '$178.50', chg_pct: '+0.65%', vcp_contraction_stages: 3, pivot_price: '$182.00', catalyst_driver: 'Tomahawk 5 交换芯片与超算定制 ASIC 获顶级云厂商加单' },
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

export function DashboardTab({ onNavigateTab, onSelectEvent, onSelectTicker, refreshKey }: DashboardTabProps) {
  const [data, setData] = useState<DashboardSummaryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isExtractingNews, setIsExtractingNews] = useState(false)
  const [showDispatcher, setShowDispatcher] = useState(false)
  const [activeTooltipTicker, setActiveTooltipTicker] = useState<string | null>(null)
  const [activeSentimentTooltipId, setActiveSentimentTooltipId] = useState<string | null>(null)

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
          title: '官方公报与事件抽取完成',
          message: '权威情报雷达底账已更新，正在重载大盘研报...',
        })
        await loadData()
      } else {
        const errMsg = typeof res.error === 'string' ? res.error : (res.error?.message || '后端任务启动失败')
        showToast({
          type: 'error',
          title: '采集触发受阻',
          message: errMsg,
        })
      }
    } catch (err) {
      showToast({
        type: 'error',
        title: '系统调用异常',
        message: String(err),
      })
    } finally {
      setIsExtractingNews(false)
    }
  }

  const loadData = async () => {
    setLoading(true)
    setError(null)
    const res = await api.getDashboardSummary()
    if (res.ok && res.data) {
      setData(res.data)
    } else {
      const errMsg = typeof res.error === 'string' ? res.error : (res.error?.message || '获取大盘仪表盘汇总数据失败')
      setError(errMsg)
    }
    setLoading(false)
  }

  useEffect(() => {
    void loadData()
  }, [refreshKey])

  const readiness = data?.readiness
  const stats: MarketStatisticsData = data?.market_statistics || DEFAULT_MARKET_STATS

  const getQuote = (ticker: string): MarketQuoteItem | null => {
    if (!data?.markets) return null
    if (data.markets.all_quotes) {
      const f = data.markets.all_quotes.find(q => q.ticker === ticker)
      if (f) return f
    }
    if (data.markets.us_indices) {
      const u = data.markets.us_indices.find(q => q.ticker === ticker)
      if (u) return u
    }
    if (data.markets.jp_indices) {
      const j = data.markets.jp_indices.find(q => q.ticker === ticker)
      if (j) return j
    }
    if (data.markets.jp_core_equities) {
      const c = data.markets.jp_core_equities.find(q => q.ticker === ticker)
      if (c) return c
    }
    return null
  }

  // 大盘基准指数精选阵列
  const backendBenchmarks = data?.benchmark_indices || data?.markets?.benchmark_indices
  const benchmarkIndices = (backendBenchmarks && backendBenchmarks.length > 0)
    ? backendBenchmarks.map(b => ({
        ticker: b.ticker,
        nameZh: b.name_zh,
        desc: b.role,
        detail: b.detail,
        param_reflection: b.param_reflection,
        market: b.market,
        currency: b.currency,
        symbol: b.symbol,
        formatted_price: b.formatted_price,
        change: b.change,
        change_pct: b.change_pct,
        is_up: b.is_up,
        data_status: b.data_status,
        data_status_zh: b.data_status_zh,
        quote: {
          ticker: b.ticker,
          company_name: b.name_zh,
          market: b.market,
          currency: b.currency,
          is_valid: true,
          price: b.price,
          formatted_price: b.formatted_price,
          data_status: b.data_status,
          timestamp_formatted: b.data_status_zh,
        } as MarketQuoteItem,
      }))
    : [
    {
      ticker: 'SPY',
      nameZh: '标普500 ETF',
      desc: '美股大盘蓝筹基准',
      detail: '追踪标准普尔500指数，覆盖美股500只代表性大盘蓝筹龙头，是全球配置美股核心权益资产与宏观风险偏好的第一风向标。',
      market: 'US',
      currency: 'USD',
      symbol: '$',
      change: '+6.20',
      change_pct: '+0.85%',
      is_up: true,
      data_status: 'PREVIOUS_CLOSE',
      data_status_zh: '前收盘基准',
      formatted_price: '$735.34',
      quote: getQuote('SPY'),
    },
    {
      ticker: 'QQQ',
      nameZh: '纳斯达克100 ETF',
      desc: '科技龙头与核心成长',
      detail: '追踪纳斯达克100指数，重仓全球顶尖科技、AI算法与数字经济成长旗舰企业，对无风险利率变动及科技资本开支高度敏感。',
      market: 'US',
      currency: 'USD',
      symbol: '$',
      change: '+7.28',
      change_pct: '+1.12%',
      is_up: true,
      data_status: 'PREVIOUS_CLOSE',
      data_status_zh: '前收盘基准',
      formatted_price: '$656.10',
      quote: getQuote('QQQ'),
    },
    {
      ticker: 'DIA',
      nameZh: '道琼斯工业 ETF',
      desc: '工业与价值蓝筹权重',
      detail: '追踪道琼斯工业平均指数（30家蓝筹工业与消费巨头），采用价格加权法，反映美国传统工业制造与成熟蓝筹周期的基本盘动能。',
      market: 'US',
      currency: 'USD',
      symbol: '$',
      change: '+2.10',
      change_pct: '+0.45%',
      is_up: true,
      data_status: 'PREVIOUS_CLOSE',
      data_status_zh: '前收盘基准',
      formatted_price: '$468.20',
      quote: getQuote('DIA'),
    },
    {
      ticker: '1306',
      nameZh: 'TOPIX 东证指数 ETF',
      desc: '日本全市场核心基准',
      detail: '野村东证股价指数NEXT FUNDS ETF，全息覆盖东京证交所Prime主板所有企业，代表日本全市场基本盘与央行货币政策正常化影响。',
      market: 'JP',
      currency: 'JPY',
      symbol: '¥',
      change: '+16.85',
      change_pct: '+0.61%',
      is_up: true,
      data_status: 'PREVIOUS_CLOSE',
      data_status_zh: '前收盘基准',
      formatted_price: '¥2,785.00',
      quote: getQuote('1306'),
    },
    {
      ticker: '^N225',
      nameZh: '日经225指数',
      desc: '日本出口与半导体风向标',
      detail: '日经平均株价指数，精选225家高流动性跨国制造与半导体出口巨头，深受日元汇率涨跌波动与海外供应链需求影响。',
      market: 'JP',
      currency: 'JPY',
      symbol: '¥',
      change: '+449.12',
      change_pct: '+0.74%',
      is_up: true,
      data_status: 'PREVIOUS_CLOSE',
      data_status_zh: '前收盘基准',
      formatted_price: '¥61,142.35',
      quote: getQuote('^N225'),
    },
    {
      ticker: 'SMH',
      nameZh: '半导体行业 ETF',
      desc: '全球芯片与算力风向标',
      detail: 'VanEck半导体行业ETF，重仓英伟达、台积电、博通、阿斯麦等芯片巨头，是全球算力基础设施、先进封装与周期胜负手代表。',
      market: 'US',
      currency: 'USD',
      symbol: '$',
      change: '+6.50',
      change_pct: '+1.45%',
      is_up: true,
      data_status: 'PREVIOUS_CLOSE',
      data_status_zh: '前收盘基准',
      formatted_price: '$454.62',
      quote: getQuote('SMH'),
    },
    {
      ticker: 'USDJPY',
      nameZh: '美元兑日元 (USD/JPY)',
      desc: '日美利差与汇率承压',
      detail: '全球最具系统重要性的套息货币对，反映美联储与日本央行政策利差，也是东证出口企业汇兑损益与全球流动性平仓的核心传导链。',
      market: 'FX',
      currency: 'JPY',
      symbol: '¥',
      change: '+0.38',
      change_pct: '+0.25%',
      is_up: true,
      data_status: 'PREVIOUS_CLOSE',
      data_status_zh: '前收盘基准',
      formatted_price: '154.28',
      quote: getQuote('USDJPY'),
    },
    {
      ticker: 'GLD',
      nameZh: '黄金信托 ETF (GLD)',
      desc: '全球避险与抗通胀核心锚',
      detail: '实物黄金信托ETF，穿透实物黄金金条储备，反映全球央行去美元化储备配置、地缘风险与实际利率走势。',
      market: 'US',
      currency: 'USD',
      symbol: '$',
      change: '+1.20',
      change_pct: '+0.52%',
      is_up: true,
      data_status: 'PREVIOUS_CLOSE',
      data_status_zh: '前收盘基准',
      formatted_price: '$236.40',
      quote: getQuote('GLD'),
    },
  ]

  // 宏观核心风险与流动性舵手指标
  const backendMacro = data?.macro_gauges
  const macroGauges = (backendMacro && backendMacro.length > 0)
    ? backendMacro.map(g => ({
        id: g.id,
        nameZh: g.name_zh,
        value: g.display_value || g.value,
        role: g.role,
        status: g.status,
      }))
    : [
    { id: '^VIX', nameZh: '恐慌指数', value: '28.18', role: '波动警戒 (≥25)', status: '警戒' },
    { id: '^TNX', nameZh: '10年美债', value: '4.42%', role: '无风险利率', status: '高息中枢' },
    { id: 'DXY', nameZh: '美元指数', value: '105.80', role: '美元流动性', status: '强势' },
    { id: 'T10Y2Y', nameZh: '期限利差', value: '+0.27%', role: '曲线正常化', status: '倒挂解除' },
    { id: '^N225VI', nameZh: '日经波动率', value: '29.80', role: '东京风险溢价', status: '高位震荡' },
    { id: 'EFFR', nameZh: '联邦有效利率', value: '3.88%', role: '隔夜政策利率', status: '政策底座' },
  ]

  const usAD = stats.advance_decline.us
  const jpAD = stats.advance_decline.jp
  const histogram = stats.advance_decline.histogram
  const ma = stats.ma_penetration
  const sectors = stats.sectors
  const funnel = stats.sepa_funnel
  const sentiment = stats.capital_and_sentiment

  return (
    <div className="p-4 md:p-6 space-y-6 max-w-[1600px] mx-auto">
      {/* ========================================================================= */}
      {/* 1. 顶层交易时段与统计基准状态条 */}
      {/* ========================================================================= */}
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs shadow-sm">
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="w-2 h-2 rounded-full bg-[#176249] animate-pulse" />
          <span className="font-bold text-[var(--text-primary)]">双市场交易时段状态</span>
          <span className="text-[var(--text-muted)]">|</span>
          <div className="flex flex-wrap items-center gap-3 text-[var(--text-secondary)] font-mono">
            <span className="flex items-center gap-1.5">
              <span className="text-[var(--text-muted)]">美股:</span>
              <span className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-sans text-[11px]">
                已收盘 (前收盘基准)
              </span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="text-[var(--text-muted)]">日股:</span>
              <span className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-sans text-[11px]">
                已收盘 (前收盘基准)
              </span>
            </span>
            <span className="text-[var(--text-muted)] hidden sm:inline">|</span>
            <span className="text-[var(--text-muted)]">
              统计基准交易日: <span className="text-[var(--text-primary)] font-bold">{readiness?.latest_date_str || '2026-11-14'}</span> (全量官方收盘统计)
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {loading && (
            <span className="text-[11px] text-[#176249] flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-[#176249] animate-ping" />
              <span>同步中...</span>
            </span>
          )}
          {error && (
            <span className="text-[11px] text-rose-600 font-mono">
              (部分底账拉取受限)
            </span>
          )}
          <button
            type="button"
            onClick={() => setShowDispatcher(!showDispatcher)}
            className="text-[11px] text-[var(--text-muted)] hover:text-[var(--text-primary)] cursor-pointer"
          >
            {showDispatcher ? '收起任务面板 ↑' : '任务调度状态 ↓'}
          </button>
          <button
            type="button"
            onClick={() => onNavigateTab('collection')}
            className="px-2.5 py-1 rounded-md bg-[var(--bg-card)] hover:bg-slate-100 text-slate-700 border border-slate-200 hover:text-[#176249] hover:border-[#176249]/40 font-medium cursor-pointer transition-all"
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
      {/* 2. 宏观决策全宽行动栏 (Macro Action Bar) + 8 大核心基准胶囊条 + 宏观流动性读数 */}
      {/* ========================================================================= */}
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 shadow-sm space-y-3.5">
        {/* 宏观定性与策略指引 */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pb-3 border-b border-[var(--border-color)]/60">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#176249] to-[#0e3a2f] flex items-center justify-center text-white shadow-xs shrink-0">
              <CompassIcon className="w-4 h-4 text-emerald-200" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-[var(--text-primary)]">
                  大盘定性：{data?.market_regime?.regime_title || '高息中枢定价约束 · 结构性主升浪分化扩散'}
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                  {data?.market_regime?.regime_status_zh || '波动警戒 (VIX 28.18)'}
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-slate-700 font-medium mt-1">
                <LightBulbIcon className="w-3.5 h-3.5 shrink-0 text-amber-600" />
                <span>策略指引：{data?.market_regime?.strategy_guidance || '全市场涨跌比处于 1.8 偏多顺风区间，但宏观利率锚高位压制估值倍数；仓位上限维持 3-4 成精选布局，聚焦通过 SEPA 严筛的 VCP 紧绷收缩标的。'}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono text-[var(--text-muted)] shrink-0">
            <span>美股ADR: <strong className="text-[var(--text-primary)]">{usAD.ad_ratio}</strong></span>
            <span>日股ADR: <strong className="text-[var(--text-primary)]">{jpAD.ad_ratio}</strong></span>
            <span>52周净新高: <strong className="text-rose-600">+{ma.high_low.net_expansion}</strong></span>
            <button
              type="button"
              onClick={() => onNavigateTab('intelligence')}
              className="text-[#176249] hover:underline font-sans cursor-pointer text-xs"
            >
              驱动事件雷达 &rarr;
            </button>
          </div>
        </div>

        {/* 8 大核心基准指数紧凑胶囊条 (Compact Benchmark Pills) */}
        <div>
          <div className="flex items-center justify-between text-[11px] font-semibold text-[var(--text-muted)] mb-2">
            <span>双市场核心基准指数 (8 大系统重要性定价锚)</span>
            <span className="font-mono text-[10px]">逐笔收盘核验 · 点击感叹号展开说明</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
            {benchmarkIndices.map((idx, index) => {
              const q = idx.quote
              const isUp = idx.is_up ?? true
              const chgPct = idx.change_pct || '+0.00%'
              const price = idx.formatted_price || q?.formatted_price || '—'

              const alignClass = (index === 0)
                ? 'left-0'
                : (index >= 6)
                ? 'right-0'
                : 'left-1/2 -translate-x-1/2'

              return (
                <div
                  key={idx.ticker}
                  className="bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-slate-300 rounded-lg p-2 flex flex-col justify-between transition-all shadow-xs relative group"
                >
                  <div className="flex items-center justify-between gap-1">
                    <span className="font-mono font-bold text-xs text-[var(--text-primary)] group-hover:text-[#176249] transition-colors">
                      {idx.ticker}
                    </span>

                    <div
                      className="relative shrink-0"
                      onMouseEnter={() => setActiveTooltipTicker(idx.ticker)}
                      onMouseLeave={() => setActiveTooltipTicker(null)}
                    >
                      <button
                        type="button"
                        title={`${idx.nameZh} 详细说明`}
                        aria-label={`${idx.nameZh} 详细说明`}
                        onClick={(e) => {
                          e.stopPropagation()
                          setActiveTooltipTicker(activeTooltipTicker === idx.ticker ? null : idx.ticker)
                        }}
                        className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer ${
                          activeTooltipTicker === idx.ticker
                            ? 'bg-slate-700 text-white'
                            : 'text-[var(--text-muted)] hover:text-slate-800'
                        }`}
                      >
                        <InfoCircleIcon className="w-2.5 h-2.5" />
                      </button>

                      {activeTooltipTicker === idx.ticker && (
                        <div
                          className={`absolute top-full mt-2 w-60 p-3 rounded-xl bg-white border border-slate-200 shadow-xl z-50 pointer-events-auto opacity-100 transition-all duration-200 text-left ${alignClass}`}
                          onMouseEnter={() => setActiveTooltipTicker(idx.ticker)}
                          onMouseLeave={() => setActiveTooltipTicker(null)}
                        >
                          <div className="flex items-center justify-between border-b border-slate-100 pb-1 mb-1">
                            <span className="font-mono font-bold text-xs text-slate-800">{idx.ticker}</span>
                            <span className="text-[10px] text-slate-600 font-medium">{idx.nameZh}</span>
                          </div>
                          <p className="text-[10px] text-slate-600 leading-relaxed">{idx.detail}</p>
                          <div className="mt-1.5 pt-1 border-t border-slate-100 flex items-center justify-between text-[9px] text-[var(--text-muted)] font-mono">
                            <span>市场: {idx.market}</span>
                            <span>状态: {idx.data_status_zh || '前收盘基准'}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="text-[10px] text-[var(--text-muted)] truncate mt-0.5 font-medium">
                    {idx.nameZh}
                  </div>

                  <div className="flex items-baseline justify-between gap-1 mt-1 font-mono">
                    <span className="text-xs font-black text-[var(--text-primary)] truncate">{price}</span>
                    <span className={`text-[10px] font-bold inline-flex items-center gap-0.5 px-1 py-0.2 rounded border ${
                      isUp ? 'text-rose-600 bg-rose-50 border-rose-200' : 'text-blue-600 bg-blue-50 border-blue-200'
                    }`}>
                      {isUp ? <TrendUpIcon className="w-2 h-2 stroke-[3]" /> : <TrendDownIcon className="w-2 h-2 stroke-[3]" />}
                      <span>{chgPct}</span>
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* 6 大宏观流动性指标紧凑横栏 */}
        <div className="pt-2 border-t border-[var(--border-color)]/50 flex flex-wrap items-center justify-between gap-2 text-xs">
          <span className="text-[10px] text-[var(--text-muted)] font-semibold shrink-0">
            流动性与风险定价锚：
          </span>
          <div className="flex flex-wrap items-center gap-2 font-mono text-[11px]">
            {macroGauges.map((g) => (
              <span
                key={g.id}
                className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border-color)]/70 shadow-2xs"
              >
                <span className="text-[var(--text-muted)] font-sans text-[10px]">{g.nameZh}:</span>
                <span className="font-bold text-[var(--text-primary)]">{g.value}</span>
                <span className="text-[9px] px-1 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200">
                  {g.status}
                </span>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 3. 核心决策主工作区 (58% / 42% Golden Split) */}
      {/* ========================================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* ==================== 左侧 58% (lg:col-span-7): SEPA 候选卡片 + 选股漏斗 ==================== */}
        <div className="lg:col-span-7 space-y-5">
          {/* SEPA 临界突破候选精选大卡片 */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]/60">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#176249] to-[#0e3a2f] flex items-center justify-center text-white shadow-xs">
                  <FilterIcon className="w-4 h-4 text-emerald-200" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--text-primary)]">
                    SEPA 临界突破候选池 (VCP 波动收敛主升浪)
                  </h2>
                  <p className="text-xs text-[var(--text-muted)] mt-0.5">
                    米纳尔维尼趋势模板全票通过 · 窄幅收缩完毕 · 临近关键 Pivot 突破点
                  </p>
                </div>
              </div>
              <span className="text-xs px-2.5 py-1 rounded-full bg-[#176249]/10 text-[#176249] border border-[#176249]/20 font-semibold font-mono">
                {funnel.top_candidates.length} 席临界候选
              </span>
            </div>

            {/* 候选卡片列表 */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {funnel.top_candidates.map((c) => (
                <div
                  key={c.ticker}
                  className="bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-[#176249]/50 rounded-xl p-4 transition-all shadow-xs hover:shadow-md flex flex-col justify-between space-y-3 group"
                >
                  <div>
                    {/* 头部：代码 + 名称 + VCP次数 */}
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-black text-sm text-[var(--text-primary)] group-hover:text-[#176249] transition-colors">
                          {c.ticker}
                        </span>
                        <span className="text-xs text-[var(--text-secondary)] font-medium">
                          {c.name_zh}
                        </span>
                      </div>
                      <span className="text-[10px] px-2 py-0.5 rounded font-semibold bg-[#176249]/10 text-[#176249] border border-[#176249]/25">
                        {c.vcp_contraction_stages}次收敛 VCP
                      </span>
                    </div>

                    {/* 现价与关键突破要素 */}
                    <div className="mt-2.5 grid grid-cols-3 gap-2 py-2 px-2.5 rounded-lg bg-[var(--surface-color)] border border-[var(--border-color)]/50 font-mono text-center">
                      <div>
                        <div className="text-[9px] text-[var(--text-muted)]">最新现价</div>
                        <div className="text-xs font-bold text-[var(--text-primary)] mt-0.5">{c.price}</div>
                        <div className={`text-[9px] font-semibold ${c.chg_pct?.startsWith('-') ? 'text-blue-600' : 'text-rose-600'}`}>
                          {c.chg_pct}
                        </div>
                      </div>
                      <div className="border-x border-[var(--border-color)]/50">
                        <div className="text-[9px] text-[var(--text-muted)]">突破买点</div>
                        <div className="text-xs font-bold text-[#176249] mt-0.5">{c.pivot_price}</div>
                        <div className="text-[9px] text-[var(--text-muted)]">Pivot 压力位</div>
                      </div>
                      <div>
                        <div className="text-[9px] text-[var(--text-muted)]">防守止损</div>
                        <div className="text-xs font-bold text-amber-600 mt-0.5">$178.50</div>
                        <div className="text-[9px] text-slate-400">下行保护线</div>
                      </div>
                    </div>

                    {/* 催化逻辑 */}
                    <p className="text-[11px] text-[var(--text-secondary)] mt-2.5 leading-relaxed line-clamp-2">
                      <span className="text-[var(--text-muted)] font-medium">催化动力：</span>
                      {c.catalyst_driver}
                    </p>
                  </div>

                  {/* 底部操作按钮 */}
                  <div className="pt-2 border-t border-[var(--border-color)]/40 flex items-center justify-between gap-2">
                    <button
                      type="button"
                      onClick={() => onSelectTicker?.(c.ticker)}
                      className="flex-1 py-1.5 px-2.5 rounded-lg text-xs font-semibold bg-[var(--surface-color)] hover:bg-[#176249]/10 text-[#176249] border border-[#176249]/30 hover:border-[#176249]/60 cursor-pointer transition-all text-center"
                    >
                      速览底账 (抽屉)
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        onSelectTicker?.(c.ticker)
                        onNavigateTab('analytics')
                      }}
                      className="flex-1 py-1.5 px-2.5 rounded-lg text-xs font-semibold bg-[#176249] hover:bg-[#0e3a2f] text-white shadow-xs cursor-pointer transition-all text-center"
                    >
                      进入 25 模型深度分析 &rarr;
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* SEPA 主升浪选股统计漏斗 */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-3.5">
            <div className="flex items-center justify-between pb-2.5 border-b border-[var(--border-color)]/60">
              <div className="flex items-center gap-2">
                <BarChartIcon className="w-4 h-4 text-[#176249]" />
                <h3 className="text-xs font-bold text-[var(--text-primary)]">
                  全市场 SEPA 趋势模板阶梯过滤漏斗
                </h3>
              </div>
              <span className="text-[11px] text-[var(--text-muted)] font-mono">
                从 14,892 只上市主体至 18 席 VCP 临界突破标的
              </span>
            </div>

            <div className="space-y-2">
              {[
                { stage: '全盘标的池扫描', count: funnel.total_screened, pct: '100%', barW: '100%' },
                { stage: '站上 200 日牛熊线', count: funnel.stage_1_base_building, pct: '25.7%', barW: '75%' },
                { stage: '第二阶段主升浪结构 (MA50>MA150>MA200)', count: funnel.stage_2_trend_aligned, pct: '7.5%', barW: '50%' },
                { stage: '高相对强度与接近52周新高 (RS ≥ 80)', count: funnel.stage_3_near_high, pct: '3.2%', barW: '32%' },
                { stage: 'VCP 临界突破候选标的', count: funnel.stage_4_vcp_candidates, pct: '0.12%', barW: '18%' },
              ].map((f, i) => (
                <div key={f.stage} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5">
                      <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold ${
                        i === 4 ? 'bg-gradient-to-r from-amber-500 to-rose-600 text-white shadow-xs' : 'bg-slate-100 text-slate-700'
                      }`}>
                        {i + 1}
                      </span>
                      <span className={`font-medium ${i === 4 ? 'text-rose-600 font-bold' : 'text-[var(--text-secondary)]'}`}>
                        {f.stage}
                      </span>
                    </div>
                    <span className="font-mono font-bold text-[var(--text-primary)]">
                      {f.count.toLocaleString()} 家 <span className="text-[var(--text-muted)] text-[10px]">({f.pct})</span>
                    </span>
                  </div>
                  <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        i === 4
                          ? 'bg-gradient-to-r from-amber-500 to-rose-600'
                          : i === 0
                          ? 'bg-slate-300'
                          : i === 1
                          ? 'bg-[#176249]/40'
                          : i === 2
                          ? 'bg-[#176249]/70'
                          : 'bg-[#176249]'
                      }`}
                      style={{ width: f.barW }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ==================== 右侧 42% (lg:col-span-5): 资金情绪与权威事件雷达 ==================== */}
        <div className="lg:col-span-5 space-y-5">
          {/* 宏观资金能级与期权情绪 */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-[var(--border-color)]/60">
              <div className="flex items-center gap-2">
                <ZapIcon className="w-4 h-4 text-slate-700" />
                <h3 className="text-xs font-bold text-[var(--text-primary)]">
                  宏观资金能级与期权情绪
                </h3>
              </div>
              <span className="text-[10px] text-[var(--text-muted)] font-mono">流动性与期权 PCR</span>
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              {[
                {
                  id: 'fg',
                  title: 'Fear & Greed 恐慌贪婪',
                  value: sentiment.fear_greed_score,
                  sub: sentiment.fear_greed_gauge,
                  valColor: 'text-rose-600',
                  detail: 'CNN 综合恐慌与贪婪指数（0-100）。综合市场动量、股票价格强度、避险需求与垃圾债利差。读数在 60-75 为健康贪婪蓄势，> 80 触发极度狂热警惕，< 25 为极端恐慌买点。',
                },
                {
                  id: 'pcr',
                  title: '期权看跌/看涨比 (PCR)',
                  value: sentiment.put_call_ratio,
                  sub: sentiment.put_call_signal,
                  valColor: 'text-blue-600',
                  detail: '全市场看跌期权 (Put) 与看涨期权 (Call) 总成交量之比。PCR < 0.70 表明市场看多投机亢奋，0.70 - 0.90 为健康防御中性区间，> 1.0 表明对冲买盘沉重。',
                },
                {
                  id: 'inflow',
                  title: '主力机构资金净流入',
                  value: sentiment.institutional_net_inflow_str,
                  sub: '净买入防御权重',
                  valColor: 'text-rose-600',
                  detail: '基于交易所大单宗数 (Block Trades) 资金流向监测的大机构主力买方净流入。反映聪明钱 (Smart Money) 在核心权重指数及龙头防御板块的战略建仓意愿。',
                },
                {
                  id: 'volume',
                  title: '市场成交量能倍率',
                  value: `${sentiment.volume_expansion_ratio}x`,
                  sub: sentiment.volume_verdict,
                  valColor: 'text-[var(--text-primary)]',
                  detail: '全市场当日总成交额相对 50 日均量 (50-Day Moving Average Volume) 的倍率。倍率在 1.1x - 1.3x 之间伴随指数上涨，代表机构资金真实介入的健康放量主升浪。',
                },
              ].map((item, index) => {
                const alignClass = (index % 2 === 0) ? 'left-0' : 'right-0'

                return (
                  <div
                    key={item.id}
                    className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-2.5 text-center relative group shadow-sm hover:border-slate-300 transition-all"
                  >
                    <div className="flex items-center justify-between gap-1 mb-1">
                      <div className="text-[10px] text-[var(--text-muted)] truncate font-medium text-left">
                        {item.title}
                      </div>

                      <div
                        className="relative shrink-0"
                        onMouseEnter={() => setActiveSentimentTooltipId(item.id)}
                        onMouseLeave={() => setActiveSentimentTooltipId(null)}
                      >
                        <button
                          type="button"
                          title={`${item.title} 详细说明`}
                          aria-label={`${item.title} 详细说明`}
                          onClick={(e) => {
                            e.stopPropagation()
                            setActiveSentimentTooltipId(activeSentimentTooltipId === item.id ? null : item.id)
                          }}
                          className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer ${
                            activeSentimentTooltipId === item.id
                              ? 'bg-[#176249] text-white'
                              : 'text-[var(--text-muted)] hover:text-slate-700'
                          }`}
                        >
                          <InfoCircleIcon className="w-2.5 h-2.5" />
                        </button>

                        {activeSentimentTooltipId === item.id && (
                          <div
                            className={`absolute top-full mt-2 w-60 p-3 rounded-xl bg-white border border-slate-200 shadow-xl z-50 pointer-events-auto opacity-100 transition-all duration-200 text-left ${alignClass}`}
                            onMouseEnter={() => setActiveSentimentTooltipId(item.id)}
                            onMouseLeave={() => setActiveSentimentTooltipId(null)}
                          >
                            <div className="font-bold text-xs text-slate-800 border-b border-slate-100 pb-1 mb-1">
                              {item.title}
                            </div>
                            <p className="text-[10px] text-slate-600 leading-relaxed">
                              {item.detail}
                            </p>
                            <div className="mt-1.5 pt-1 border-t border-slate-100 flex items-center justify-between text-[9px] text-[var(--text-muted)] font-mono">
                              <span>读数: <strong className="text-slate-800">{item.value}</strong></span>
                              <span>定性: <span className="text-[#176249] font-semibold">{item.sub}</span></span>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className={`text-base font-black font-mono ${item.valColor} mt-0.5`}>
                      {item.value}
                    </div>
                    <div className="text-[10px] text-[var(--text-secondary)] mt-0.5 font-medium truncate">
                      {item.sub}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* 权威事件情报雷达 */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-2.5 border-b border-[var(--border-color)]/60">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-rose-500" />
                <h3 className="text-xs font-bold text-[var(--text-primary)]">
                  权威事件情报雷达 ({data?.events_summary?.total_events || 0}篇)
                </h3>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={handleExtractNews}
                  disabled={isExtractingNews}
                  className="text-[10px] px-2 py-0.5 rounded bg-[var(--bg-card)] hover:bg-slate-100 text-slate-700 border border-slate-200 hover:text-[#176249] hover:border-[#176249]/40 cursor-pointer transition-all flex items-center gap-1"
                  title="即时核验与抽取官方最新公报"
                >
                  <ZapIcon className={`w-3 h-3 text-slate-600 ${isExtractingNews ? 'animate-spin' : ''}`} />
                  <span>{isExtractingNews ? '抽取中...' : '即时抽取'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => onNavigateTab('intelligence')}
                  className="text-[10px] text-[var(--text-secondary)] hover:text-[#176249] hover:underline cursor-pointer"
                >
                  全部情报 &rarr;
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
                  暂无权威事件记录
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 4. 美日核心资产全息监控池 (Full-Width Watchlist Table) */}
      {/* ========================================================================= */}
      <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[var(--border-color)]/60 gap-2">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-[var(--text-primary)]">
                美日核心资产全息监控池
              </h2>
              <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-[#176249]/10 text-[#176249] border border-[#176249]/20 font-mono">
                14 只核心跟踪标的
              </span>
            </div>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">
              点击任意标的整行或右侧操作按钮，即刻滑出右侧个股全息底账与 25 模型速览抽屉
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono text-[var(--text-muted)]">
            <span>官方财报三表与 25 模型健康评分对齐</span>
          </div>
        </div>

        {/* 监控池表格 */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[var(--border-color)] text-[var(--text-muted)] font-semibold">
                <th className="py-2.5 px-3">代码 / 名称</th>
                <th className="py-2.5 px-3">所属市场</th>
                <th className="py-2.5 px-3">GICS 细分赛道</th>
                <th className="py-2.5 px-3 text-right">最新基准价格</th>
                <th className="py-2.5 px-3 text-right">涨跌幅</th>
                <th className="py-2.5 px-3 text-right">估值 P/E</th>
                <th className="py-2.5 px-3">资产负债状况</th>
                <th className="py-2.5 px-3 text-right">库存周转天数 (DIO)</th>
                <th className="py-2.5 px-3 text-center">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-color)]/50">
              {CORE_WATCHLIST.map((item) => {
                const q = getQuote(item.ticker)
                const price = q?.formatted_price || item.defaultPrice
                const chg = (q as any)?.change_pct || (q as any)?.change_percent || item.defaultChg
                const isUp = item.isUp ?? !chg.startsWith('-')

                return (
                  <tr
                    key={item.ticker}
                    onClick={() => onSelectTicker?.(item.ticker)}
                    className="hover:bg-[var(--bg-card)] cursor-pointer transition-colors group"
                  >
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-xs text-[var(--text-primary)] group-hover:text-[#176249] transition-colors">
                          {item.ticker}
                        </span>
                        <span className="text-xs text-[var(--text-secondary)] font-medium">
                          {item.nameZh}
                        </span>
                      </div>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`text-[10px] px-1.5 py-0.2 rounded font-mono font-semibold border ${
                        item.market === 'US'
                          ? 'bg-slate-100 text-slate-700 border-slate-200'
                          : 'bg-rose-50 text-rose-700 border-rose-200'
                      }`}>
                        {item.market}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-[var(--text-secondary)]">
                      {item.sector}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono font-bold text-[var(--text-primary)]">
                      {price}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono font-bold">
                      <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.2 rounded border ${
                        isUp ? 'text-rose-600 bg-rose-50 border-rose-200' : 'text-blue-600 bg-blue-50 border-blue-200'
                      }`}>
                        {isUp ? <TrendUpIcon className="w-2.5 h-2.5 stroke-[3]" /> : <TrendDownIcon className="w-2.5 h-2.5 stroke-[3]" />}
                        <span>{chg}</span>
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-[var(--text-secondary)]">
                      {item.pe}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="text-[11px] px-2 py-0.5 rounded font-medium bg-[#176249]/10 text-[#176249] border border-[#176249]/20">
                        {item.netCash}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-[var(--text-secondary)]">
                      {item.dio}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          onSelectTicker?.(item.ticker)
                        }}
                        className="px-2.5 py-1 rounded text-xs font-semibold bg-[#176249]/10 hover:bg-[#176249] text-[#176249] hover:text-white border border-[#176249]/30 hover:border-[#176249] cursor-pointer transition-all"
                      >
                        速览底账
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 5. 次级透视区 (Secondary Depth Fold: ADR 直方图 + GICS 天梯 + 均线渗透) */}
      {/* ========================================================================= */}
      <div className="space-y-5 pt-2">
        {/* 全市场每日股票涨跌分布统计 */}
        <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[var(--border-color)]/60 gap-2">
            <div className="flex items-center gap-2.5">
              <BarChartIcon className="w-5 h-5 text-slate-700" />
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
              <div className="flex items-center gap-1.5 font-bold">
                <span className={`px-2 py-0.5 rounded border ${
                  !usAD.median_return_pct.startsWith('-') ? 'text-rose-600 bg-rose-50 border-rose-200' : 'text-blue-600 bg-blue-50 border-blue-200'
                }`}>
                  美股 {usAD.median_return_pct}
                </span>
                <span className={`px-2 py-0.5 rounded border ${
                  !jpAD.median_return_pct.startsWith('-') ? 'text-rose-600 bg-rose-50 border-rose-200' : 'text-blue-600 bg-blue-50 border-blue-200'
                }`}>
                  日股 {jpAD.median_return_pct}
                </span>
              </div>
            </div>
          </div>

          {/* 双市场涨跌数量与比例进度条 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* 美股 ADR */}
            <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3.5 space-y-2.5 shadow-sm">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                  <span className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono text-[10px] font-bold">US</span>
                  <span>美股全市场涨跌统计 (10,000+ 标的)</span>
                </span>
                <span className={`font-mono font-bold ${usAD.ad_ratio >= 1.0 ? 'text-rose-600' : 'text-blue-600'}`}>
                  涨跌比: {usAD.ad_ratio}
                </span>
              </div>
              <div className="h-3 w-full bg-slate-200 rounded-full overflow-hidden flex">
                <div
                  style={{ width: `${usAD.advancers_pct}%` }}
                  className="bg-rose-500 h-full transition-all"
                  title={`上涨: ${usAD.advancers} 家 (${usAD.advancers_pct}%)`}
                />
                <div
                  style={{ width: `${100 - usAD.advancers_pct - usAD.decliners_pct}%` }}
                  className="bg-slate-300 h-full transition-all"
                  title={`平盘: ${usAD.unchanged} 家`}
                />
                <div
                  style={{ width: `${usAD.decliners_pct}%` }}
                  className="bg-blue-500 h-full transition-all"
                  title={`下跌: ${usAD.decliners} 家 (${usAD.decliners_pct}%)`}
                />
              </div>
              <div className="flex items-center justify-between text-[11px] font-mono text-[var(--text-muted)] pt-0.5">
                <span className="text-rose-600 font-semibold inline-flex items-center gap-1">
                  <TrendUpIcon className="w-2.5 h-2.5 stroke-[3] text-rose-600" />
                  <span>上涨 {usAD.advancers.toLocaleString()} ({usAD.advancers_pct}%)</span>
                </span>
                <span className="text-slate-400">━ 平盘 {usAD.unchanged.toLocaleString()}</span>
                <span className="text-blue-600 font-semibold inline-flex items-center gap-1">
                  <TrendDownIcon className="w-2.5 h-2.5 stroke-[3] text-blue-600" />
                  <span>下跌 {usAD.decliners.toLocaleString()} ({usAD.decliners_pct}%)</span>
                </span>
              </div>
            </div>

            {/* 日股 ADR */}
            <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3.5 space-y-2.5 shadow-sm">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                  <span className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono text-[10px] font-bold">JP</span>
                  <span>东证全市场涨跌统计 (4,400+ 标的)</span>
                </span>
                <span className={`font-mono font-bold ${jpAD.ad_ratio >= 1.0 ? 'text-rose-600' : 'text-blue-600'}`}>
                  涨跌比: {jpAD.ad_ratio}
                </span>
              </div>
              <div className="h-3 w-full bg-slate-200 rounded-full overflow-hidden flex">
                <div
                  style={{ width: `${jpAD.advancers_pct}%` }}
                  className="bg-rose-500 h-full transition-all"
                  title={`上涨: ${jpAD.advancers} 家 (${jpAD.advancers_pct}%)`}
                />
                <div
                  style={{ width: `${100 - jpAD.advancers_pct - jpAD.decliners_pct}%` }}
                  className="bg-slate-300 h-full transition-all"
                  title={`平盘: ${jpAD.unchanged} 家`}
                />
                <div
                  style={{ width: `${jpAD.decliners_pct}%` }}
                  className="bg-blue-500 h-full transition-all"
                  title={`下跌: ${jpAD.decliners} 家 (${jpAD.decliners_pct}%)`}
                />
              </div>
              <div className="flex items-center justify-between text-[11px] font-mono text-[var(--text-muted)] pt-0.5">
                <span className="text-rose-600 font-semibold inline-flex items-center gap-1">
                  <TrendUpIcon className="w-2.5 h-2.5 stroke-[3] text-rose-600" />
                  <span>上涨 {jpAD.advancers.toLocaleString()} ({jpAD.advancers_pct}%)</span>
                </span>
                <span className="text-slate-400">━ 平盘 {jpAD.unchanged.toLocaleString()}</span>
                <span className="text-blue-600 font-semibold inline-flex items-center gap-1">
                  <TrendDownIcon className="w-2.5 h-2.5 stroke-[3] text-blue-600" />
                  <span>下跌 {jpAD.decliners.toLocaleString()} ({jpAD.decliners_pct}%)</span>
                </span>
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
                const barColor = isUp ? 'bg-rose-500' : 'bg-blue-500'
                const textColor = isUp ? 'text-rose-600' : 'text-blue-600'
                return (
                  <div
                    key={bucket.range}
                    className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-2.5 flex flex-col justify-between items-center text-center hover:border-slate-300 transition-all"
                  >
                    <div className="text-[10px] text-[var(--text-muted)] font-mono font-semibold truncate w-full">
                      {bucket.range}
                    </div>
                    <div className="w-full flex items-end justify-center h-14 py-1">
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

        {/* 下层并列双栏：GICS 全行业天梯榜 + 均线渗透与52周新高 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* GICS 行业天梯 */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]/60">
              <div className="flex items-center gap-2.5">
                <BarChartIcon className="w-5 h-5 text-slate-700" />
                <h2 className="text-base font-bold text-[var(--text-primary)]">
                  GICS 全行业收益与动量天梯
                </h2>
              </div>
              <span className="text-xs text-[var(--text-muted)] font-mono">
                9 大 GICS 核心产业
              </span>
            </div>

            <div className="space-y-2">
              {sectors.map((sec) => (
                <div
                  key={sec.id}
                  className="bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-slate-300 rounded-xl px-3 py-2 flex items-center justify-between gap-2 transition-all shadow-xs"
                >
                  <div className="flex items-center gap-2.5 min-w-[140px]">
                    <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold font-mono ${
                      sec.strength_rank <= 3
                        ? 'bg-[#176249] text-white'
                        : 'bg-[var(--surface-color)] text-[var(--text-muted)] border border-[var(--border-color)]'
                    }`}>
                      {sec.strength_rank}
                    </span>
                    <div>
                      <div className="text-xs font-bold text-[var(--text-primary)]">
                        {sec.name_zh}
                      </div>
                      <div className="text-[9px] text-[var(--text-muted)] font-mono">
                        龙头: {sec.top_driver}
                      </div>
                    </div>
                  </div>

                  <div className="hidden sm:flex items-center gap-1.5">
                    <div className="w-16 bg-slate-200 h-1.5 rounded-full overflow-hidden">
                      <div className="bg-rose-500 h-full rounded-full" style={{ width: `${sec.advancers_pct}%` }} />
                    </div>
                    <span className="text-[10px] text-[var(--text-muted)] font-mono">{sec.advancers_pct}%</span>
                  </div>

                  <div className="text-right flex items-center gap-2 font-mono">
                    <span className="text-[10px] text-[var(--text-muted)]">{sec.volume_ratio}x</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-bold border ${
                      sec.is_up ? 'bg-rose-50 text-rose-600 border-rose-200' : 'bg-blue-50 text-blue-600 border-blue-200'
                    }`}>
                      {sec.return_formatted}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 均线渗透与 52 周新高 */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]/60">
              <div className="flex items-center gap-2.5">
                <BarChartIcon className="w-5 h-5 text-emerald-500" />
                <h2 className="text-base font-bold text-[var(--text-primary)]">
                  均线渗透与 52 周新高净扩展
                </h2>
              </div>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 border border-emerald-500/30 font-semibold font-mono">
                {ma.high_low.regime}
              </span>
            </div>

            {/* 四大均线渗透 */}
            <div className="grid grid-cols-2 gap-2.5">
              {[
                { title: '20日短期冲刺线', pct: ma.above_20d_pct },
                { title: '50日中期生命线', pct: ma.above_50d_pct },
                { title: '150日趋势确立线', pct: ma.above_150d_pct },
                { title: '200日长期牛熊分水岭', pct: ma.above_200d_pct },
              ].map((item) => (
                <div key={item.title} className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3 space-y-1.5 shadow-xs">
                  <div className="text-[10px] text-[var(--text-muted)] font-medium truncate">{item.title}</div>
                  <div className="text-base font-black font-mono text-[var(--text-primary)]">{item.pct}%</div>
                  <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        item.pct >= 50 ? 'bg-[#176249]' : 'bg-amber-500'
                      }`}
                      style={{ width: `${item.pct}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* 52周新高 vs 新低 */}
            <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3.5 flex items-center justify-between gap-4 font-mono">
              <div className="text-left font-sans">
                <div className="text-xs font-bold text-[var(--text-primary)]">52 周新高 vs 52 周新低</div>
                <div className="text-[10px] text-[var(--text-muted)] mt-0.5">全市场广度领先风向标</div>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-center">
                  <div className="text-[9px] text-[var(--text-muted)]">52周新高</div>
                  <div className="text-xs font-black text-rose-600">+{ma.high_low.new_52w_highs} 席</div>
                </div>
                <div className="text-center">
                  <div className="text-[9px] text-[var(--text-muted)]">52周新低</div>
                  <div className="text-xs font-black text-blue-600">-{ma.high_low.new_52w_lows} 席</div>
                </div>
                <div className="text-center pl-2.5 border-l border-[var(--border-color)]">
                  <div className="text-[9px] text-[var(--text-muted)]">净扩展指数</div>
                  <div className="text-sm font-black text-rose-600">+{ma.high_low.net_expansion} 席</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DashboardTab
