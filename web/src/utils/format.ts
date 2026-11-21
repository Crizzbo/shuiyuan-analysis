/**
 * 水源分析终端统一格式化与中文语义映射库 (Format & Chinese Terminology SSOT)
 * 遵循 DOC-42 规范：
 * 1. 日志和运行状态统一使用用户设备的系统当地时间：YYYY-MM-DD HH:mm:ss（UTC+XX:XX）
 * 2. 面向用户的分级、状态、筛选项、提示和失败原因统一使用自然中文语义
 */

/**
 * 将任意 ISO 8601 或时间戳转换为客户端设备的系统当地时间
 * 输出范式：2026-11-14 09:42:07（UTC+09:00）
 */
export function formatDeviceTime(value?: string | number | null): string {
  if (!value) return ''
  const strVal = String(value).trim()
  if (!strVal || strVal === '时间未提供' || strVal === '未知' || strVal === '待补数' || strVal === '待同步') return ''

  // 若仅包含纯日期 (如 2026-11-14)
  if (/^\d{4}-\d{2}-\d{2}$/.test(strVal)) {
    return strVal
  }

  const date = new Date(strVal)
  if (Number.isNaN(date.valueOf())) return strVal

  const pad = (n: number) => String(n).padStart(2, '0')
  const Y = date.getFullYear()
  const M = pad(date.getMonth() + 1)
  const D = pad(date.getDate())
  const h = pad(date.getHours())
  const m = pad(date.getMinutes())
  const s = pad(date.getSeconds())

  // 获取当地时区偏移 (UTC+XX:XX 或 UTC-XX:XX)
  const offsetMin = -date.getTimezoneOffset()
  const sign = offsetMin >= 0 ? '+' : '-'
  const absMin = Math.abs(offsetMin)
  const tzH = pad(Math.floor(absMin / 60))
  const tzM = pad(absMin % 60)
  const tzStr = `UTC${sign}${tzH}:${tzM}`

  return `${Y}-${M}-${D} ${h}:${m}:${s}（${tzStr}）`
}

/**
 * 中文语义字典：全量机器代号转业务直觉中文
 */
export const CHINESE_LABELS: Record<string, string> = {
  // 1. 任务与流水线执行状态
  IDLE: '待机就绪',
  QUEUED: '排队中',
  RUNNING: '运行中',
  STOPPING: '正在安全暂停',
  STOPPED: '已安全暂停',
  SUCCESS: '已完成',
  PARTIAL_SUCCESS: '部分完成',
  FAILED: '执行失败',
  BLOCKED: '待核查',
  CANCELLED: '已取消',
  WAITING_DEPENDENCY: '等待前置任务',
  CONFIGURED: '配置已更新',
  SUBMITTED: '已提交',
  scheduled: '定时触发',
  manual: '手动触发',

  // 2. 数据与行情新鲜度 (统一 SSOT)
  FRESH: '盘中实时',
  PREVIOUS_CLOSE: '前收盘基准',
  STALE_BLOCKED: '前收盘基准',
  NOT_CONFIGURED: '待配置源',
  NO_QUOTE: '待补行情',
  NO_FILING: '缺少财报',
  READY: '数据已就绪',
  ARCHIVED_BASELINE: '基线归档',
  EMPTY: '待初筛',
  collected: '已归档',
  no_data: '暂无数据',
  network_error: '网络失败',
  upstream_error: '上游失败',
  browser_required: '待官方原文核验',

  // 3. 事件与情报分级
  P0: 'P0 极高影响',
  P1: 'P1 重要关注',
  P2: 'P2 行业动态',
  P3: 'P3 常规资讯',
  Confirmed_Fact: '官方权威核实',
  Corroborated_Report: '多源佐证采信',
  Unverified_Rumor: '待核实传闻隔离',
  Pending_Verification: '待核验',
  ARCHIVED: '已归档',

  // 4. 财务与审计平账
  BALANCED: '报表勾稽平衡',
  UNBALANCED: '报表勾稽异常',
  AUDITED: '官方财报已审计',
  UNAUDITED: '未审计财报',
  VALID: '验签通过',
  INVALID: '验签失败',
  PENDING_SYNC: '待同步',
  UPLOADED: '已上传',
  UPLOAD_FAILED: '上传失败',

  // 5. 核心任务名称
  US_DAILY: '美股全市场盘前日线与宏观',
  JP_DAILY: '日股全市场盘前日线',
  OFFICIAL_NEWS: '官方财经资讯分时采集',
  STOCK_SCREENING: '股票收集与形态初筛',
  INDICATOR_UPDATE: '金融指标与市场宽度',
  FINANCE_CALC: '金融计算与估值区间',
  LOCAL_AUDIT: '本地数据与账本核验',
  QUOTE_COLLECT: '授权行情归档核对',
  INCREMENTAL_COLLECT: '权威财报核验清单',
  MASTER: '总启动',
  GF_MARKET_READINESS: '行情时效与交易时段',
  SEPA_UNIVERSE_SCREENER: '全市场趋势形态初筛',
  SEC_10K_BALANCED_AUDIT: '官方财报勾稽核对',
  UNIVERSE_567_BATCH: '全景深度研报管线',
  AI_BROWSER_REPLENISHMENT: '权威财报核查清单',
  EVENT_RADAR_POLLING: '事件雷达脉冲轮询',

  // 6. 市场
  ALL: '全部市场',
  US: '美股市场 (SEC)',
  JP: '日股市场 (JPX)',
}

/**
 * 翻译机器代号为自然中文
 */
export function toChinese(key?: string | null): string {
  if (!key) return ''
  return CHINESE_LABELS[key] || key
}

/**
 * 格式化数值展示
 */
export const numberFormatter = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 4 })

/**
 * 获取执行状态样式与中文
 */
export function getStatusBadge(status?: string): { text: string; cls: string } {
  switch (status) {
    case 'RUNNING':
      return { text: '运行中', cls: 'bg-[#176249]/15 text-[#176249] border border-[#176249]/30 animate-pulse' }
    case 'QUEUED':
      return { text: '排队中', cls: 'bg-slate-100 text-slate-700 border border-slate-200' }
    case 'SUCCESS':
      return { text: '已完成', cls: 'bg-[#176249]/10 text-[#176249] border border-[#176249]/25' }
    case 'PARTIAL_SUCCESS':
      return { text: '部分完成', cls: 'bg-amber-50 text-amber-700 border border-amber-200' }
    case 'FAILED':
      return { text: '执行失败', cls: 'bg-rose-50 text-rose-700 border border-rose-200' }
    case 'STOPPED':
      return { text: '已停止', cls: 'bg-slate-100 text-slate-600 border border-slate-200' }
    case 'STOPPING':
      return { text: '正在停止', cls: 'bg-amber-50 text-amber-700 border border-amber-200' }
    case 'BLOCKED':
      return { text: '待核查', cls: 'bg-amber-50 text-amber-800 border border-amber-200' }
    case 'CANCELLED':
      return { text: '已取消', cls: 'bg-slate-100 text-slate-500 border border-slate-200' }
    default:
      return { text: toChinese(status) || '待机就绪', cls: 'bg-slate-100 text-slate-700 border border-slate-200' }
  }
}

/**
 * 转换数组或按空白切分的字符串为字符串数组 (SSOT)
 */
export function toList(val?: string[] | string | null): string[] {
  if (!val) return []
  if (Array.isArray(val)) return val
  return String(val).split(/\s+/).filter(Boolean)
}

/**
 * 事件严重性徽章样式与自然中文文本映射 (SSOT)
 */
export function getSeverityBadge(sev?: string): { text: string; cls: string } {
  switch (String(sev || '').toUpperCase()) {
    case 'P0':
      return { text: '极高影响', cls: 'bg-rose-50 text-rose-700 border border-rose-200' }
    case 'P1':
      return { text: '重要关注', cls: 'bg-amber-50 text-amber-700 border border-amber-200' }
    case 'P2':
      return { text: '行业动态', cls: 'bg-slate-100 text-slate-700 border border-slate-200' }
    default:
      return { text: '常规资讯', cls: 'bg-slate-100 text-slate-500 border border-slate-200' }
  }
}

/**
 * 事实核验与传闻隔离徽章样式与自然中文文本映射 (SSOT)
 */
export function getVerificationBadge(status?: string): { text: string; cls: string } {
  switch (status) {
    case 'Confirmed_Fact':
      return { text: '官方权威核实', cls: 'bg-emerald-50 text-emerald-700 border border-emerald-200' }
    case 'Corroborated_Report':
      return { text: '主流媒体采信', cls: 'bg-slate-100 text-slate-700 border border-slate-200' }
    case 'Unverified_Rumor':
      return { text: '待核实传闻隔离', cls: 'bg-rose-50 text-rose-700 border border-rose-200' }
    default:
      return { text: '已归档', cls: 'bg-slate-100 text-slate-500 border border-slate-200' }
  }
}

/**
 * 事件分类英文枚举向优雅买方直觉中文映射 (SSOT)
 */
export function formatEventCategory(cat?: string): string {
  if (!cat) return ''
  const c = String(cat).trim()
  const map: Record<string, string> = {
    State_Policy_Regulatory: '政策法规',
    CentralBank_Liquidity_FX_Shock: '央行利率',
    Geopolitical_Conflict: '地缘局势',
    Physical_Plant_Disruption: '突发停工',
    Supply_Chain_Shortage: '供应链',
    Corporate_Earnings_Event: '公司财报',
    Technology_Breakthrough: '前沿技术',
    Executive_Leadership_Change: '高管变动',
    Other_Macro_Event: '宏观综合',
    Macro_Monetary: '宏观流动性',
    Regulatory_Compliance: '监管合规',
    Corporate_Action: '公司动态',
    general_market: '综合市场',
    earnings: '企业财报',
    macro: '宏观经济',
    technology: '前沿技术',
    General: '',
  }
  if (map[c] !== undefined) return map[c]
  return c.replace(/_/g, ' ')
}

/**
 * 信源权威可信度分级转换为专业中文标签 (SSOT)
 */
export function formatCredibilityTier(tier?: string): { text: string; cls: string } {
  const t = String(tier || '').trim()
  switch (t) {
    case 'Tier1_Official_Regulatory':
      return { text: '官方原发 (一级)', cls: 'bg-[#176249]/10 text-[#176249] border border-[#176249]/25' }
    case 'Tier2_Issuer_Direct':
      return { text: '企业直发 (二级)', cls: 'bg-slate-100 text-slate-700 border border-slate-200' }
    case 'Tier3_Mainstream_Wire':
      return { text: '主流财经 (三级)', cls: 'bg-amber-50 text-amber-700 border border-amber-200' }
    case 'Tier4_Public_Flash_Social':
      return { text: '公开快讯 (四级)', cls: 'bg-slate-100 text-slate-500 border border-slate-200' }
    default:
      return { text: t ? '已归档' : '', cls: 'bg-slate-100 text-slate-500 border border-slate-200' }
  }
}

/**
 * 将原始长 URL 或技术源名转换为友好机构信源名称 (SSOT)
 */
export function formatSourceName(source?: string): string {
  if (!source) return ''
  const s = String(source).trim()
  if (s.startsWith('http://') || s.startsWith('https://')) {
    try {
      const url = new URL(s)
      const host = url.hostname.toLowerCase()
      if (host.includes('federalreserve.gov')) return '美联储发布'
      if (host.includes('sec.gov')) return 'SEC 官方披露'
      if (host.includes('nvidia.com')) return '英伟达官方'
      if (host.includes('bloomberg.com')) return '彭博社'
      if (host.includes('reuters.com')) return '路透社'
      if (host.includes('cnbc.com')) return 'CNBC'
      if (host.includes('wsj.com')) return '华尔街日报'
      if (host.includes('ft.com')) return '金融时报'
      if (host.includes('jpx.co.jp')) return '东证官方'
      if (host.includes('yahoo.com')) return '雅虎财经'
      return host.replace(/^www\./, '')
    } catch {
      return s
    }
  }
  return s
}

/**
 * 过滤内部占位实体并去重限制数量 (SSOT)
 */
export function cleanEntityList(entities?: string | string[], max: number = 3): string[] {
  const list = toList(entities)
  const ignored = new Set([
    '未知实体', '未知主体', '未知', 'unknown', '通用产业', '通用主体', '通用', '无', 'none', 'null', 'n/a',
    '未指定', '未分类', '未匹配'
  ])
  const result: string[] = []
  const seen = new Set<string>()

  for (const ent of list) {
    let clean = String(ent).trim()
    clean = clean.replace(/^(\p{Extended_Pictographic}|\uFE0F|\s)+/u, '').trim()
    if (!clean || ignored.has(clean.toLowerCase())) continue
    if (!seen.has(clean)) {
      seen.add(clean)
      result.push(clean)
    }
    if (result.length >= max) break
  }
  return result
}

