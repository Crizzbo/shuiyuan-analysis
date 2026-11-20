import { useEffect, useState } from 'react'
import type { DashboardSummaryData, MarketQuoteItem, MarketStatisticsData } from '../types/api'
import { api } from '../services/api'
import { showToast } from './Toast'
import { TradingSessionBar } from './dashboard/TradingSessionBar'
import { MacroCompassCard } from './dashboard/MacroCompassCard'
import { MarketBreadthAndSectorsCard } from './dashboard/MarketBreadthAndSectorsCard'
import { SepaFunnelAndSentimentCard } from './dashboard/SepaFunnelAndSentimentCard'

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

  // 宏观核心风险与流动性舵手指标
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
      {/* 顶层交易时段与统计基准状态条 */}
      <TradingSessionBar
        benchmarkDate={data?.trading_sessions?.benchmark_date || readiness?.latest_date_str}
        benchmarkNote={data?.trading_sessions?.benchmark_note}
        schedulerInfo={data?.task_scheduler}
        showDispatcher={showDispatcher}
        onToggleDispatcher={() => setShowDispatcher(!showDispatcher)}
        onNavigateTab={onNavigateTab}
        onTaskCompleted={loadData}
        onSelectTicker={onSelectTicker}
      />

      {/* 核心投研主工作区 (Bento 双栏: 左65%宏观罗盘与行业天梯，右35%SEPA主升浪与资金情绪) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* 左侧 65% (lg:col-span-8): 水凤宏观罗盘、市场广度与行业天梯 */}
        <div className="lg:col-span-8 space-y-5">
          <MacroCompassCard
            benchmarkDate={data?.trading_sessions?.benchmark_date || readiness?.latest_date_str}
            benchmarkNote={data?.trading_sessions?.benchmark_note}
            marketRegime={data?.market_regime}
            benchmarkIndices={benchmarkIndices as any}
            macroGauges={macroGauges as any}
            usAD={usAD}
            jpAD={jpAD}
            ma={ma}
            onNavigateTab={onNavigateTab}
          />

          <MarketBreadthAndSectorsCard
            usAD={usAD}
            jpAD={jpAD}
            histogram={histogram}
            sectors={sectors}
            ma={ma}
          />
        </div>

        {/* 右侧 35% (lg:col-span-4): SEPA漏斗、资金情绪与突发事件雷达 */}
        <SepaFunnelAndSentimentCard
          funnel={funnel}
          sentiment={sentiment}
          eventsSummary={data?.events_summary}
          isExtractingNews={isExtractingNews}
          onExtractNews={handleExtractNews}
          onSelectEvent={onSelectEvent}
          onNavigateTab={onNavigateTab}
          onSelectTicker={onSelectTicker}
        />
      </div>
    </div>
  )
}

export default DashboardTab
