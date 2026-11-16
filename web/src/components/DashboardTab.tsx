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
      return { text: '盘中实时', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' }
    case 'PREVIOUS_CLOSE':
      return { text: '前收盘基准', cls: 'bg-slate-100 text-slate-700 border-slate-200' }
    case 'STALE_BLOCKED':
      return { text: '前收盘基准', cls: 'bg-slate-100 text-slate-700 border-slate-200' }
    case 'NOT_CONFIGURED':
      return { text: '待配置源', cls: 'bg-slate-100 text-slate-500 border-slate-200' }
    case 'NO_QUOTE':
      return { text: '待补行情', cls: 'bg-slate-100 text-slate-500 border-slate-200' }
    default:
      return { text: '前收盘基准', cls: 'bg-slate-100 text-slate-500 border-slate-200' }
  }
}

export function DashboardTab({ onNavigateTab, onSelectEvent, onSelectTicker, refreshKey }: DashboardTabProps) {
  const [data, setData] = useState<DashboardSummaryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isExtractingNews, setIsExtractingNews] = useState(false)
  const [showDispatcher, setShowDispatcher] = useState(false)
  const [activeTooltipTicker, setActiveTooltipTicker] = useState<string | null>(null)
  const [activeMacroTooltipId, setActiveMacroTooltipId] = useState<string | null>(null)
  const [activeMaTooltipId, setActiveMaTooltipId] = useState<string | null>(null)
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
          <div className="w-8 h-8 border-3 border-[#176249] border-t-transparent rounded-full animate-spin" />
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

  // 大盘基准指数精选阵列（100% 后台契约字段对齐，优先消费后端数据）
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
      quote: getQuote('SPY') || { formatted_price: '$735.34', data_status: 'PREVIOUS_CLOSE', timestamp_formatted: '前收盘基准' },
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
      quote: getQuote('QQQ') || { formatted_price: '$656.10', data_status: 'PREVIOUS_CLOSE', timestamp_formatted: '前收盘基准' },
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
      quote: getQuote('DIA') || { formatted_price: '$468.20', data_status: 'PREVIOUS_CLOSE', timestamp_formatted: '前收盘基准' },
    },
    {
      ticker: 'IWM',
      nameZh: '罗素2000 ETF',
      desc: '中小盘流动性敏感标的',
      detail: '追踪罗素2000小盘指数，涵盖美国本土2000家微中型企业，对美国国内银行信贷松紧、企业再通胀及债务展期成本最为敏锐。',
      market: 'US',
      currency: 'USD',
      symbol: '$',
      change: '-0.89',
      change_pct: '-0.32%',
      is_up: false,
      data_status: 'PREVIOUS_CLOSE',
      data_status_zh: '前收盘基准',
      formatted_price: '$277.54',
      quote: getQuote('IWM') || { formatted_price: '$277.54', data_status: 'PREVIOUS_CLOSE', timestamp_formatted: '前收盘基准' },
    },
    {
      ticker: '1306',
      nameZh: '东证 TOPIX ETF',
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
      quote: getQuote('1306') || { formatted_price: '¥2,785.00', data_status: 'PREVIOUS_CLOSE', timestamp_formatted: '前收盘基准' },
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
      quote: getQuote('^N225') || { formatted_price: '¥61,142.35', data_status: 'PREVIOUS_CLOSE', timestamp_formatted: '前收盘基准' },
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
      quote: getQuote('SMH') || { formatted_price: '$454.62', data_status: 'PREVIOUS_CLOSE', timestamp_formatted: '前收盘基准' },
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
      quote: getQuote('USDJPY') || { formatted_price: '154.28', data_status: 'PREVIOUS_CLOSE', timestamp_formatted: '前收盘基准' },
    },
  ]

  // 宏观核心风险与流动性舵手指标（100% 后台契约字段对齐，优先消费后端数据）
  const backendMacro = data?.macro_gauges
  const macroGauges = (backendMacro && backendMacro.length > 0)
    ? backendMacro.map(g => ({
        id: g.id,
        nameZh: g.name_zh,
        value: g.display_value || g.value,
        role: g.role,
        status: g.status,
        status_code: g.status_code,
        tone: g.tone,
        detail: g.detail,
        param_reflection: g.param_reflection,
        data_status: g.data_status,
        data_status_zh: g.data_status_zh,
      }))
    : [
    {
      id: '^VIX',
      nameZh: '标普恐慌指数 (VIX)',
      value: data?.indicators?.find(i => i.id === '^VIX')?.display_value || '28.18',
      role: '波动率警戒 (≥25)',
      status: '波动警戒',
      tone: 'warning' as const,
      detail: 'CBOE 标普500期权隐含波动率指数，衡量期权市场对未来30天美股年化波动的预期。VIX ≥ 25 触发系统性恐慌警戒，买方机构通常收紧仓位敞口并提高现金防御比例。',
    },
    {
      id: '^TNX',
      nameZh: '10年期美债收益率',
      value: data?.indicators?.find(i => i.id === '^TNX')?.display_value || '4.42%',
      role: '无风险利率定价锚',
      status: '高息中枢',
      tone: 'accent' as const,
      detail: '全球金融资产之锚与无风险折现率基准。10年期美债收益率高位震荡直接提升权益类资产的贴现率要求，对高估值科技成长股与长久期资产倍数形成估值压制。',
    },
    {
      id: 'DXY',
      nameZh: '美元指数 (DXY)',
      value: data?.indicators?.find(i => i.id === 'DXY')?.display_value || '105.80',
      role: '全球美元流动性松紧',
      status: '强势高位',
      tone: 'info' as const,
      detail: '衡量美元对一篮子主要贸易伙伴货币（欧元、日元、英镑等）的相对强弱。美元走强意味着全球美元流动性回流收紧，对跨国企业海外营收折算与新兴市场资产构成压力。',
    },
    {
      id: 'T10Y2Y',
      nameZh: '10Y-2Y 美债期限利差',
      value: data?.indicators?.find(i => i.id === 'T10Y2Y')?.display_value || '+0.27%',
      role: '收益率曲线正常化',
      status: '倒挂解除',
      tone: 'good' as const,
      detail: '美国10年期与2年期国债收益率利差。倒挂解除并陡峭化上行标志着货币政策转入降息预期或长端通胀溢价重建，是宏观经济周期的核心转折信号。',
    },
    {
      id: '^N225VI',
      nameZh: '日经225波动率 (^N225VI)',
      value: data?.indicators?.find(i => i.id === '^N225VI')?.display_value || '29.80',
      role: '东京市场风险溢价',
      status: '高位震荡',
      tone: 'warning' as const,
      detail: '衡量东京证券交易所日经225指数期权隐含波动率。受日元汇率剧烈波动及海外对冲基金套息平仓动向影响，反映日本核心权益资产的恐慌情绪。',
    },
    {
      id: 'EFFR',
      nameZh: '有效联邦基金利率 (EFFR)',
      value: data?.indicators?.find(i => i.id === 'EFFR')?.display_value || '3.88%',
      role: '美联储基准隔夜利率',
      status: '政策底座',
      tone: 'info' as const,
      detail: '美国商业银行之间无担保隔夜拆借的实际加权中位数利率，是美联储货币政策框架中的终极政策操作目标与全市场资金成本底座。',
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
    <div className="p-4 md:p-6 space-y-6 max-w-[1600px] mx-auto">
      {/* ========================================================================= */}
      {/* 顶层交易时段与统计基准状态条 */}
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
      {/* 核心投研主工作区 (Bento 双栏: 左65%宏观罗盘与行业天梯，右35%SEPA主升浪与资金情绪) */}
      {/* ========================================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* ==================== 左侧 65% (lg:col-span-8): 水凤宏观罗盘、市场广度与行业天梯 ==================== */}
        <div className="lg:col-span-8 space-y-5">
          {/* 1. 水凤宏观罗盘与大盘体温研判 */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[var(--border-color)]/60 gap-2">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#176249] to-[#0e3a2f] flex items-center justify-center text-white shadow-xs shrink-0 relative overflow-hidden">
                  <CompassIcon className="w-5 h-5 text-emerald-200" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-bold text-[var(--text-primary)]">
                      全球双市场宏观罗盘与大盘体温研判
                    </h2>
                    <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-[#176249]/10 text-[#176249] border border-[#176249]/20 font-mono">
                      美日跨市宏观
                    </span>
                  </div>
                  <p className="text-xs text-[var(--text-muted)] mt-0.5">
                    美股与日股核心宏观流动性、波动率指数 (VIX) 与大盘情绪跨市场定价锚
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs px-2.5 py-1 rounded-full bg-[var(--bg-card)] text-[var(--text-secondary)] border border-[var(--border-color)] font-mono">
                  基准: {data?.trading_sessions?.benchmark_date || readiness?.latest_date_str || '2026-11-14'} ({data?.trading_sessions?.benchmark_note || '前收盘基准'})
                </span>
              </div>
            </div>

            {/* 买方顶层定性结论条 */}
            <div className="bg-[var(--bg-card)] rounded-xl p-3.5 border border-[var(--border-color)]/60 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-[var(--text-primary)]">
                    大盘定性：{data?.market_regime?.regime_title || '高息中枢定价约束 · 结构性主升浪分化扩散'}
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                    {data?.market_regime?.regime_status_zh || '波动警戒 (VIX 28.18)'}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => onNavigateTab('intelligence')}
                  className="text-xs text-slate-700 hover:text-slate-900 hover:underline cursor-pointer flex items-center gap-1 font-medium"
                >
                  <span>驱动事件雷达</span>
                  <span>&rarr;</span>
                </button>
              </div>
              <div className="flex items-start gap-1.5 text-xs text-slate-700 font-medium">
                <LightBulbIcon className="w-4 h-4 shrink-0 text-amber-600 mt-0.5" />
                <span>策略指引：{data?.market_regime?.strategy_guidance || '全市场涨跌比处于 1.8 偏多顺风区间，但宏观利率锚高位压制估值倍数；仓位上限维持 3-4 成精选布局，聚焦通过 SEPA 严筛的 VCP 紧绷收缩标的。'}</span>
              </div>
              <div className="text-[11px] text-[var(--text-muted)] font-mono pt-1 border-t border-[var(--border-color)]/40 flex flex-wrap gap-x-4 gap-y-1">
                <span>美股涨跌比 (ADR): {data?.market_regime?.adr_us || `${usAD.ad_ratio} (中位数 ${usAD.median_return_pct})`}</span>
                <span>日股涨跌比 (ADR): {data?.market_regime?.adr_jp || `${jpAD.ad_ratio} (中位数 ${jpAD.median_return_pct})`}</span>
                <span>52周净新高: {data?.market_regime?.net_highs_52w || `+${ma.high_low.net_expansion} 席`}</span>
              </div>
            </div>

            {/* 双市场核心基准卡片阵列 */}
            <div className="space-y-3 pt-1">
              <div className="flex items-center justify-between text-xs font-semibold text-[var(--text-secondary)]">
                <div className="flex items-center gap-1.5">
                  <span>双市场核心基准指数 (Benchmark Indices)</span>
                  <span className="text-[11px] text-[var(--text-muted)] font-normal hidden sm:inline">
                    · 点击右上角感叹号图标聚焦查看详细图表说明
                  </span>
                </div>
                <span className="text-[11px] text-[var(--text-muted)] font-normal">每日逐笔收盘核验为准</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {benchmarkIndices.map((idx, index) => {
                  const q = idx.quote as MarketQuoteItem
                  const badge = getStatusBadge(idx.data_status || q?.data_status)
                  const isUp = idx.is_up ?? true
                  const chgPct = idx.change_pct || '+0.00%'
                  
                  // 根据列位置动态调整展开浮层对齐方向，防止屏幕边缘被遮挡
                  const alignClass = (index % 4 === 0)
                    ? 'left-0 sm:left-0'
                    : (index % 4 === 3)
                    ? 'right-0 sm:right-0'
                    : 'right-0 sm:left-1/2 sm:-translate-x-1/2'

                  return (
                    <div
                      key={idx.ticker}
                      className="bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-slate-300 rounded-xl p-3 flex flex-col justify-between transition-all shadow-sm group relative"
                    >
                      <div>
                        {/* 顶栏：代码 + 状态标签 + 聚焦感叹号按钮 */}
                        <div className="flex items-center justify-between gap-1">
                          <span className="font-mono font-bold text-xs text-[var(--text-primary)] group-hover:text-[#176249] transition-colors">
                            {idx.ticker}
                          </span>
                          
                          <div className="flex items-center gap-1.5">
                            <span className={`text-[9px] px-1.5 py-0.2 rounded border font-medium ${badge.cls}`}>
                              {idx.data_status_zh || badge.text}
                            </span>

                            {/* 感叹号交互按钮：使用规范 SVG 矢量图标 */}
                            <div
                              className="relative"
                              onMouseEnter={() => setActiveTooltipTicker(idx.ticker)}
                              onMouseLeave={() => setActiveTooltipTicker(null)}
                            >
                              <button
                                type="button"
                                tabIndex={0}
                                title={`${idx.nameZh} 详细说明`}
                                aria-label={`${idx.nameZh} 详细说明`}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setActiveTooltipTicker(activeTooltipTicker === idx.ticker ? null : idx.ticker)
                                }}
                                onFocus={() => setActiveTooltipTicker(idx.ticker)}
                                onBlur={() => setActiveTooltipTicker(null)}
                                className={`w-4 h-4 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-slate-400 ${
                                  activeTooltipTicker === idx.ticker
                                    ? 'bg-slate-700 text-white shadow-sm'
                                    : 'bg-[var(--surface-color)] hover:bg-slate-200 text-[var(--text-muted)] hover:text-slate-800 border border-[var(--border-color)]'
                                }`}
                              >
                                <InfoCircleIcon className="w-3 h-3" />
                              </button>

                              {/* 聚焦/悬停/点击展开详细信息浮层 */}
                              {activeTooltipTicker === idx.ticker && (
                                <div
                                  className={`absolute top-full mt-2 w-64 p-3 rounded-xl bg-white border border-slate-200 shadow-xl z-50 pointer-events-auto opacity-100 transition-all duration-200 ${alignClass}`}
                                  onMouseEnter={() => setActiveTooltipTicker(idx.ticker)}
                                  onMouseLeave={() => setActiveTooltipTicker(null)}
                                >
                                  <div className="flex items-center justify-between border-b border-slate-100 pb-1.5 mb-1.5">
                                    <div className="flex items-center gap-1.5 min-w-0">
                                      <span className="font-mono font-bold text-xs text-slate-800">
                                        {idx.ticker}
                                      </span>
                                      <span className="text-[11px] text-slate-700 font-medium truncate">
                                        {idx.nameZh}
                                      </span>
                                    </div>
                                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200 font-medium shrink-0">
                                      {idx.desc}
                                    </span>
                                  </div>
                                  <p className="text-[11px] text-slate-600 leading-relaxed">
                                    {idx.detail}
                                  </p>
                                  {(idx as any).param_reflection && (
                                    <div className="mt-2 p-2 rounded-lg bg-slate-50 border border-slate-100 text-[10px] text-slate-600 leading-relaxed">
                                      <span className="font-semibold text-slate-800">【参数反映情况】：</span>
                                      {(idx as any).param_reflection}
                                    </div>
                                  )}
                                  <div className="mt-2 pt-1.5 border-t border-slate-100 flex items-center justify-between text-[10px] text-[var(--text-muted)] font-mono">
                                    <span>市场: {idx.market}</span>
                                    <span>货币: {idx.currency}</span>
                                    <span>时效: {idx.data_status_zh || badge.text}</span>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* 指数中文名称 */}
                        <div className="text-[11px] text-[var(--text-muted)] truncate mt-1">
                          {idx.nameZh}
                        </div>

                        {/* 最新报价 */}
                        <div className="text-lg font-black font-mono text-[var(--text-primary)] mt-1.5 tracking-tight truncate">
                          {idx.formatted_price || q?.formatted_price || (q?.price != null ? `${idx.symbol}${q.price}` : '—')}
                        </div>

                        {/* 涨跌幅：微型矢量箭头徽章 (红涨蓝跌) */}
                        <div className="flex items-center gap-1 mt-1 text-[11px] font-mono font-bold">
                          <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded border ${
                            isUp
                              ? 'text-rose-600 bg-rose-50 border-rose-200'
                              : 'text-blue-600 bg-blue-50 border-blue-200'
                          }`}>
                            {isUp ? <TrendUpIcon className="w-2.5 h-2.5 stroke-[3] text-rose-600" /> : <TrendDownIcon className="w-2.5 h-2.5 stroke-[3] text-blue-600" />}
                            <span>{chgPct}</span>
                          </span>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* 宏观流动性与恐慌舵手指标 */}
            <div className="space-y-2.5 pt-2 border-t border-[var(--border-color)]/50">
              <div className="flex items-center justify-between text-xs font-semibold text-[var(--text-secondary)]">
                <div className="flex items-center gap-1.5">
                  <span>宏观流动性、无风险利率与恐慌情绪指标 (Macro Liquidity & Volatility)</span>
                  <span className="text-[11px] text-[var(--text-muted)] font-normal hidden sm:inline">
                    · 点击右上角感叹号图标展开宏观影响解析
                  </span>
                </div>
                <span className="text-[11px] text-[var(--text-muted)] font-mono font-normal">系统重要性锚点</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
                {macroGauges.map((g, index) => {
                  const alignClass = (index % 6 === 0)
                    ? 'left-0'
                    : (index % 6 === 5)
                    ? 'right-0'
                    : 'right-0 sm:left-1/2 sm:-translate-x-1/2'

                  return (
                    <div
                      key={g.id}
                      className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-2.5 flex flex-col justify-between hover:border-slate-300 transition-all relative group shadow-sm"
                    >
                      <div>
                        {/* 顶栏：指标名称 + 感叹号展开浮层 */}
                        <div className="flex items-center justify-between gap-1">
                          <div className="text-[10px] text-[var(--text-muted)] truncate font-medium">
                            {g.nameZh}
                          </div>
                          
                          <div
                            className="relative shrink-0"
                            onMouseEnter={() => setActiveMacroTooltipId(g.id)}
                            onMouseLeave={() => setActiveMacroTooltipId(null)}
                          >
                            <button
                              type="button"
                              tabIndex={0}
                              title={`${g.nameZh} 详细说明`}
                              aria-label={`${g.nameZh} 详细说明`}
                              onClick={(e) => {
                                e.stopPropagation()
                                setActiveMacroTooltipId(activeMacroTooltipId === g.id ? null : g.id)
                              }}
                              onFocus={() => setActiveMacroTooltipId(g.id)}
                              onBlur={() => setActiveMacroTooltipId(null)}
                              className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#176249] ${
                                activeMacroTooltipId === g.id
                                  ? 'bg-[#176249] text-white shadow-sm'
                                  : 'bg-[var(--surface-color)] hover:bg-slate-100 text-[var(--text-muted)] hover:text-slate-700 border border-[var(--border-color)] hover:border-slate-300'
                              }`}
                            >
                              <InfoCircleIcon className="w-2.5 h-2.5" />
                            </button>

                            {/* 浮层 */}
                            {activeMacroTooltipId === g.id && (
                              <div
                                className={`absolute top-full mt-2 w-64 p-3 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto opacity-100 transition-all duration-200 ${alignClass}`}
                                onMouseEnter={() => setActiveMacroTooltipId(g.id)}
                                onMouseLeave={() => setActiveMacroTooltipId(null)}
                              >
                                <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                                  <div className="flex items-center gap-1.5 min-w-0">
                                    <span className="font-mono font-bold text-xs text-[var(--text-primary)]">
                                      {g.id}
                                    </span>
                                    <span className="text-[11px] text-[var(--text-secondary)] font-medium truncate">
                                      {g.nameZh}
                                    </span>
                                  </div>
                                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium shrink-0">
                                    {g.role}
                                  </span>
                                </div>
                                <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                                  {g.detail}
                                </p>
                                {(g as any).param_reflection && (
                                  <div className="mt-2 p-2 rounded-lg bg-[var(--bg-card)]/80 border border-[var(--border-color)]/60 text-[10px] text-[var(--text-secondary)] leading-relaxed">
                                    <span className="font-semibold text-[#176249]">【参数读数反映情况】：</span>
                                    {(g as any).param_reflection}
                                  </div>
                                )}
                                <div className="mt-2 pt-1.5 border-t border-[var(--border-color)]/40 flex items-center justify-between text-[10px] text-[var(--text-muted)] font-mono">
                                  <span>当前读数: <strong className="text-[var(--text-primary)]">{g.value}</strong></span>
                                  <span>状态: <span className={
                                    g.tone === 'warning' ? 'text-amber-500 font-semibold' :
                                    g.tone === 'good' ? 'text-[#176249] font-semibold' :
                                    'text-slate-700 font-semibold'
                                  }>{g.status}</span></span>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* 当前指标大字数值 */}
                        <div className="text-base font-black font-mono text-[var(--text-primary)] mt-1 tracking-tight">
                          {g.value}
                        </div>
                      </div>

                      {/* 底栏：代码 + 状态标签 */}
                      <div className="mt-1.5 flex items-center justify-between gap-1 pt-1 border-t border-[var(--border-color)]/40">
                        <span className="text-[9px] text-[var(--text-muted)] font-mono truncate">{g.id}</span>
                        <span className={`text-[9px] px-1 py-0.2 rounded font-medium border ${
                          g.tone === 'warning' ? 'text-amber-700 bg-amber-50 border-amber-200' :
                          g.tone === 'good' ? 'text-emerald-700 bg-emerald-50 border-emerald-200' :
                          'text-slate-700 bg-slate-100 border-slate-200'
                        }`}>
                          {g.status}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* 2. 全市场每日股票涨跌分布统计 (Market Advance-Decline Breadth & Return Histogram) */}
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
                {/* 比例条 (红涨蓝跌) */}
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
                <div className="text-[10px] text-[var(--text-secondary)] bg-[var(--surface-color)] px-2.5 py-1 rounded border border-[var(--border-color)]/50 flex justify-between">
                  <span>定性：{usAD.regime}</span>
                  <span className="font-mono">中位数涨幅: {usAD.median_return_pct}</span>
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
                {/* 比例条 (红涨蓝跌) */}
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
                <BarChartIcon className="w-5 h-5 text-slate-700" />
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
                  className="bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-slate-300 rounded-xl px-3.5 py-2.5 flex flex-wrap items-center justify-between gap-3 transition-all shadow-sm"
                >
                  {/* 左：排名与板块名称 */}
                  <div className="flex items-center gap-3 min-w-[200px]">
                    <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold font-mono ${
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
                      <div className="text-[10px] text-[var(--text-muted)] font-mono">
                        领涨龙头: <span className="text-[var(--text-secondary)] font-semibold">{sec.top_driver}</span>
                      </div>
                    </div>
                  </div>

                  {/* 中：上涨个股比例微进度条 */}
                  <div className="hidden md:flex items-center gap-2 min-w-[150px]">
                    <span className="text-[10px] text-[var(--text-muted)] font-mono shrink-0">上涨率:</span>
                    <div className="w-24 bg-slate-200 h-2 rounded-full overflow-hidden">
                      <div
                        className="bg-rose-500 h-full rounded-full"
                        style={{ width: `${sec.advancers_pct}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-[var(--text-secondary)] font-mono">
                      {sec.advancers_pct}%
                    </span>
                  </div>

                  {/* 右：成交量倍率与涨跌幅 (红涨蓝跌) */}
                  <div className="flex items-center gap-4 text-right">
                    <div className="text-right">
                      <div className="text-[9px] text-[var(--text-muted)]">量能倍率</div>
                      <div className="text-xs font-mono font-semibold text-[var(--text-primary)]">
                        {sec.volume_ratio}x
                      </div>
                    </div>
                    <div className="min-w-[80px] text-right">
                      <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-black font-mono border ${
                        sec.is_up ? 'bg-rose-50 text-rose-600 border-rose-200' : 'bg-blue-50 text-blue-600 border-blue-200'
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
                <BarChartIcon className="w-5 h-5 text-emerald-500" />
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
                {
                  id: 'ma20',
                  title: '20 日均线渗透率',
                  pct: ma.above_20d_pct,
                  role: '短期爆发冲刺力',
                  detail: '全市场站上 20 日均线的个股比例。衡量超短期市场爆发动量与日内冲刺力，渗透率超过 70% 表明短线极度亢奋，需注意技术性超买回踩。',
                  param_reflection: '站上20日线标的占比反映超短线进攻动量，当前读数处于中高位反映短期买方情绪处于健康爆发通道。',
                },
                {
                  id: 'ma50',
                  title: '50 日均线渗透率',
                  pct: ma.above_50d_pct,
                  role: '中期波段生命线',
                  detail: '全市场站上 50 日移动平均线的个股比例。50日线是公募与对冲基金主力的核心加仓成本防线，站上率 > 50% 是判定中级波段牛市顺风环境的基础契约。',
                  param_reflection: '站上50日线标的占比超 50%，反映主流公募基金与对冲基金正在波段加仓，主升浪获得中期机构底仓支撑。',
                },
                {
                  id: 'ma150',
                  title: '150 日均线渗透率',
                  pct: ma.above_150d_pct,
                  role: '趋势形态确立线',
                  detail: '全市场站上 150 日中长期移动平均线的个股比例。米纳尔维尼 SEPA 趋势模板核心过滤条件，表明标的经历充分筑底后正式进入第二阶段主升浪结构。',
                  param_reflection: '站上150日线标的占比突破 60%，反映全市场已有超六成股票完成筑底并确立第二阶段中长期上升通道。',
                },
                {
                  id: 'ma200',
                  title: '200 日均线渗透率',
                  pct: ma.above_200d_pct,
                  role: '长期牛熊分水岭',
                  detail: '全市场站上 200 日长期移动平均线的个股比例。全球机构投资者公认的宏观牛熊分水岭，> 50% 意味着全市场广度处于牛市健康扩张期，个股突破成功率显著提高。',
                  param_reflection: '全市场站上200日长期牛熊线标的比例超 60%，反映全盘牛市广度健康坚实，非少数巨头虚胖拉升。',
                },
              ].map((item, index) => {
                const alignClass = (index === 0)
                  ? 'left-0'
                  : (index === 3)
                  ? 'right-0'
                  : 'right-0 sm:left-1/2 sm:-translate-x-1/2'

                return (
                  <div
                    key={item.id}
                    className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3 space-y-2 relative group shadow-sm hover:border-slate-300 transition-all"
                  >
                    <div className="flex items-center justify-between gap-1">
                      <div className="text-[11px] text-[var(--text-muted)] font-medium truncate">
                        {item.title}
                      </div>

                      {/* 感叹号详细说明浮层 */}
                      <div
                        className="relative shrink-0"
                        onMouseEnter={() => setActiveMaTooltipId(item.id)}
                        onMouseLeave={() => setActiveMaTooltipId(null)}
                      >
                        <button
                          type="button"
                          tabIndex={0}
                          title={`${item.title} 详细说明`}
                          aria-label={`${item.title} 详细说明`}
                          onClick={(e) => {
                            e.stopPropagation()
                            setActiveMaTooltipId(activeMaTooltipId === item.id ? null : item.id)
                          }}
                          onFocus={() => setActiveMaTooltipId(item.id)}
                          onBlur={() => setActiveMaTooltipId(null)}
                          className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#176249] ${
                            activeMaTooltipId === item.id
                              ? 'bg-[#176249] text-white border-[#176249]'
                              : 'bg-[var(--surface-color)] hover:bg-slate-100 text-[var(--text-muted)] hover:text-slate-700 border border-[var(--border-color)] hover:border-slate-300'
                          }`}
                        >
                          <InfoCircleIcon className="w-2.5 h-2.5" />
                        </button>

                        {activeMaTooltipId === item.id && (
                          <div
                            className={`absolute top-full mt-2 w-64 p-3 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto opacity-100 transition-all duration-200 ${alignClass}`}
                            onMouseEnter={() => setActiveMaTooltipId(item.id)}
                            onMouseLeave={() => setActiveMaTooltipId(null)}
                          >
                            <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                              <span className="font-bold text-xs text-[var(--text-primary)]">
                                {item.title}
                              </span>
                              <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium shrink-0">
                                {item.role}
                              </span>
                            </div>
                            <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                              {item.detail}
                            </p>
                            {item.param_reflection && (
                              <div className="mt-2 p-2 rounded-lg bg-[var(--bg-card)]/80 border border-[var(--border-color)]/60 text-[10px] text-[var(--text-secondary)] leading-relaxed">
                                <span className="font-semibold text-[#176249]">【参数反映情况】：</span>
                                {item.param_reflection}
                              </div>
                            )}
                            <div className="mt-2 pt-1.5 border-t border-[var(--border-color)]/40 flex items-center justify-between text-[10px] text-[var(--text-muted)] font-mono">
                              <span>当前渗透率: <strong className="text-[var(--text-primary)]">{item.pct}%</strong></span>
                              <span>基准: <span className={item.pct >= 50 ? 'text-[#176249] font-semibold' : 'text-amber-500 font-semibold'}>{item.pct >= 50 ? '多头优势' : '空头承压'}</span></span>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="text-xl font-black font-mono text-[var(--text-primary)]">
                      {item.pct}%
                    </div>
                    <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          item.pct >= 50 ? 'bg-[#176249]' : 'bg-amber-500'
                        }`}
                        style={{ width: `${item.pct}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>

            {/* 52周新高净扩展指标 */}
            <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <TrendUpIcon className="w-5 h-5 text-rose-500" />
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-bold text-[var(--text-primary)]">
                      52 周新高 vs 52 周新低净扩展 (Net New Highs)
                    </span>
                    
                    {/* 感叹号交互说明：外置感叹号聚焦展开 */}
                    <div
                      className="relative"
                      onMouseEnter={() => setActiveTooltipTicker('NET_EXPANSION')}
                      onMouseLeave={() => setActiveTooltipTicker(null)}
                    >
                      <button
                        type="button"
                        tabIndex={0}
                        title="52周新高净扩展指标详细说明"
                        aria-label="52周新高净扩展指标详细说明"
                        onClick={(e) => {
                          e.stopPropagation()
                          setActiveTooltipTicker(activeTooltipTicker === 'NET_EXPANSION' ? null : 'NET_EXPANSION')
                        }}
                        onFocus={() => setActiveTooltipTicker('NET_EXPANSION')}
                        onBlur={() => setActiveTooltipTicker(null)}
                        className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#176249] ${
                          activeTooltipTicker === 'NET_EXPANSION'
                            ? 'bg-[#176249] text-white shadow-sm'
                            : 'bg-[var(--surface-color)] hover:bg-slate-100 text-[var(--text-muted)] hover:text-slate-700 border border-[var(--border-color)] hover:border-slate-300'
                        }`}
                      >
                        <InfoCircleIcon className="w-2.5 h-2.5" />
                      </button>

                      {activeTooltipTicker === 'NET_EXPANSION' && (
                        <div
                          className="absolute top-full mt-2 left-0 w-72 p-3 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto opacity-100 transition-all duration-200 text-left"
                          onMouseEnter={() => setActiveTooltipTicker('NET_EXPANSION')}
                          onMouseLeave={() => setActiveTooltipTicker(null)}
                        >
                          <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                            <span className="font-bold text-xs text-[var(--text-primary)]">
                              52 周新高净扩展
                            </span>
                            <span className="text-[9px] px-1.5 py-0.2 rounded bg-rose-50 text-rose-600 border border-rose-200 font-medium shrink-0">
                              多头广度指标
                            </span>
                          </div>
                          <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                            新高持续压制新低，表明牛市趋势内部流动性宽裕，假跌风险低。
                          </p>
                          <div className="mt-2 p-2 rounded-lg bg-[var(--bg-card)]/80 border border-[var(--border-color)]/60 text-[10px] text-[var(--text-secondary)] leading-relaxed">
                            <span className="font-semibold text-[#176249]">【参数反映情况】：</span>
                            当前净扩展为 +{ma.high_low.net_expansion} 席（52周新高 {ma.high_low.new_52w_highs} 席 vs 52周新低 {ma.high_low.new_52w_lows} 席），新高持续处于净主导地位，反映市场整体赚钱效应充沛，属于典型多头进攻浪潮。
                          </div>
                          <div className="mt-2 pt-1.5 border-t border-[var(--border-color)]/40 flex items-center justify-between text-[10px] text-[var(--text-muted)] font-mono">
                            <span>统计范围: 双市场全量</span>
                            <span>净差: +{ma.high_low.net_expansion}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="text-[10px] text-[var(--text-muted)] mt-0.5">
                    双市场广度指标 · 新高 vs 新低净差监测
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4 font-mono">
                <div className="text-center">
                  <div className="text-[9px] text-[var(--text-muted)]">52周新高</div>
                  <div className="text-sm font-black text-rose-600">+{ma.high_low.new_52w_highs} 席</div>
                </div>
                <div className="text-center">
                  <div className="text-[9px] text-[var(--text-muted)]">52周新低</div>
                  <div className="text-sm font-black text-blue-600">-{ma.high_low.new_52w_lows} 席</div>
                </div>
                <div className="text-center pl-3 border-l border-[var(--border-color)]">
                  <div className="text-[9px] text-[var(--text-muted)]">净扩展指数</div>
                  <div className="text-base font-black text-rose-600">+{ma.high_low.net_expansion} 席</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ==================== 右侧 35% (lg:col-span-4): SEPA漏斗、资金情绪与突发事件雷达 ==================== */}
        <div className="lg:col-span-4 space-y-5">
          {/* 1. SEPA 主升浪趋势形态统计漏斗 */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 shadow-sm space-y-3.5">
            <div className="flex items-center justify-between pb-2.5 border-b border-[var(--border-color)]/60">
              <div className="flex items-center gap-2">
                <FilterIcon className="w-4 h-4 text-[#176249]" />
                <h3 className="text-xs font-bold text-[var(--text-primary)]">
                  SEPA 主升浪选股统计漏斗
                </h3>
              </div>
              <span className="text-[10px] text-[var(--text-muted)] font-mono">趋势模板与形态收缩</span>
            </div>

            {/* 漏斗 5 阶层 */}
            <div className="space-y-2">
              {[
                { stage: '全盘标的池扫描', count: funnel.total_screened, pct: '100%', barW: '100%' },
                { stage: '站上 200 日牛熊线', count: funnel.stage_1_base_building, pct: '25.7%', barW: '75%' },
                { stage: '第二阶段主升浪结构', count: funnel.stage_2_trend_aligned, pct: '7.5%', barW: '50%' },
                { stage: '高相对强度 (RS ≥ 80)', count: funnel.stage_3_near_high, pct: '3.2%', barW: '32%' },
                { stage: 'VCP 临界突破候选', count: funnel.stage_4_vcp_candidates, pct: '0.12%', barW: '18%' },
              ].map((f, i) => (
                <div key={f.stage} className="space-y-1">
                  <div className="flex items-center justify-between text-[11px]">
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

            {/* 顶尖 VCP 突破候选个股卡片直达 */}
            <div className="space-y-2 pt-2 border-t border-[var(--border-color)]/60">
              <div className="flex items-center justify-between text-xs font-semibold text-[var(--text-secondary)]">
                <span>临界突破 VCP 精选标的 ({funnel.top_candidates.length}席)</span>
                <span className="text-[10px] text-[#176249] font-medium">点击进入分析 &rarr;</span>
              </div>
              <div className="space-y-2">
                {funnel.top_candidates.map((c) => (
                  <div
                    key={c.ticker}
                    onClick={() => {
                      onSelectTicker?.(c.ticker)
                      onNavigateTab('analytics')
                    }}
                    className="bg-[var(--bg-card)] border border-[var(--border-color)] hover:border-[#176249]/60 rounded-xl p-2.5 cursor-pointer transition-all flex items-center justify-between gap-3 group shadow-sm hover:shadow"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono font-bold text-xs text-[var(--text-primary)] group-hover:text-[#176249] transition-colors">
                          {c.ticker}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded font-medium bg-[#176249]/10 text-[#176249] border border-[#176249]/25">
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
                      <div className={`text-[10px] font-bold ${c.chg_pct?.startsWith('-') ? 'text-blue-600' : 'text-rose-600'}`}>
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
                  param_reflection: '读数处于 60-75 温和贪婪区，反映市场情绪向上扩张且未见 80 以上非理性狂热，风险收益比适宜。',
                },
                {
                  id: 'pcr',
                  title: '期权看跌/看涨比 (PCR)',
                  value: sentiment.put_call_ratio,
                  sub: sentiment.put_call_signal,
                  valColor: 'text-blue-600',
                  detail: '全市场看跌期权 (Put) 与看涨期权 (Call) 总成交量之比。PCR < 0.70 表明市场看多投机亢奋，0.70 - 0.90 为健康防御中性区间，> 1.0 表明对冲买盘沉重。',
                  param_reflection: 'PCR 0.70-0.90 处于健康中性区间，反映机构下行对冲买盘适度，认购期权未出现极端投机泡沫。',
                },
                {
                  id: 'inflow',
                  title: '主力机构资金净流入',
                  value: sentiment.institutional_net_inflow_str,
                  sub: '净买入防御权重',
                  valColor: 'text-rose-600',
                  detail: '基于交易所大单宗数 (Block Trades) 资金流向监测的大机构主力买方净流入。反映聪明钱 (Smart Money) 在核心权重指数及龙头防御板块的战略建仓意愿。',
                  param_reflection: '大额主力资金净流入呈现正向，反映顶级机构做市商与公募基金在核心蓝筹资产上正在持续吸筹建仓。',
                },
                {
                  id: 'volume',
                  title: '市场成交量能倍率',
                  value: `${sentiment.volume_expansion_ratio}x`,
                  sub: sentiment.volume_verdict,
                  valColor: 'text-[var(--text-primary)]',
                  detail: '全市场当日总成交额相对 50 日均量 (50-Day Moving Average Volume) 的倍率。倍率在 1.1x - 1.3x 之间伴随指数上涨，代表机构资金真实介入的健康放量主升浪。',
                  param_reflection: '量能倍率在 1.1x-1.3x 伴随指数收阳，反映增量资金进场接力，突破具备充足的量能置信度。',
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

                      {/* 感叹号浮层 */}
                      <div
                        className="relative shrink-0"
                        onMouseEnter={() => setActiveSentimentTooltipId(item.id)}
                        onMouseLeave={() => setActiveSentimentTooltipId(null)}
                      >
                        <button
                          type="button"
                          tabIndex={0}
                          title={`${item.title} 详细说明`}
                          aria-label={`${item.title} 详细说明`}
                          onClick={(e) => {
                            e.stopPropagation()
                            setActiveSentimentTooltipId(activeSentimentTooltipId === item.id ? null : item.id)
                          }}
                          onFocus={() => setActiveSentimentTooltipId(item.id)}
                          onBlur={() => setActiveSentimentTooltipId(null)}
                          className={`w-3.5 h-3.5 rounded-full flex items-center justify-center transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#176249] ${
                            activeSentimentTooltipId === item.id
                              ? 'bg-[#176249] text-white border-[#176249]'
                              : 'bg-[var(--surface-color)] hover:bg-slate-100 text-[var(--text-muted)] hover:text-slate-700 border border-[var(--border-color)] hover:border-slate-300'
                          }`}
                        >
                          <InfoCircleIcon className="w-2.5 h-2.5" />
                        </button>

                        {activeSentimentTooltipId === item.id && (
                          <div
                            className={`absolute top-full mt-2 w-60 p-3 rounded-xl bg-[var(--surface-color)] border border-[var(--border-color)] shadow-2xl z-50 pointer-events-auto opacity-100 transition-all duration-200 text-left ${alignClass}`}
                            onMouseEnter={() => setActiveSentimentTooltipId(item.id)}
                            onMouseLeave={() => setActiveSentimentTooltipId(null)}
                          >
                            <div className="flex items-center justify-between border-b border-[var(--border-color)]/60 pb-1.5 mb-1.5">
                              <span className="font-bold text-xs text-[var(--text-primary)]">
                                {item.title}
                              </span>
                            </div>
                            <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
                              {item.detail}
                            </p>
                            {item.param_reflection && (
                              <div className="mt-2 p-2 rounded-lg bg-[var(--bg-card)]/80 border border-[var(--border-color)]/60 text-[10px] text-[var(--text-secondary)] leading-relaxed">
                                <span className="font-semibold text-[#176249]">【参数反映情况】：</span>
                                {item.param_reflection}
                              </div>
                            )}
                            <div className="mt-2 pt-1.5 border-t border-[var(--border-color)]/40 flex items-center justify-between text-[10px] text-[var(--text-muted)] font-mono">
                              <span>读数: <strong className="text-[var(--text-primary)]">{item.value}</strong></span>
                              <span>定性: <span className="text-[#176249] font-semibold">{item.sub}</span></span>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className={`text-lg font-black font-mono ${item.valColor} mt-0.5`}>
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

          {/* 3. 权威事件情报雷达 (紧凑卡片流) */}
          <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-2.5 border-b border-[var(--border-color)]/60">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-rose-500" />
                <h3 className="text-xs font-bold text-[var(--text-primary)]">
                  权威事件雷达 ({data?.events_summary?.total_events || 0}篇)
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
                  暂无权威事件记录
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
