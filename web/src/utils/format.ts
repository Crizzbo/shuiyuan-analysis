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
  if (!value) return '时间未提供'
  const strVal = String(value).trim()
  if (!strVal) return '时间未提供'

  // 若仅包含纯日期 (如 2026-11-14)
  if (/^\d{4}-\d{2}-\d{2}$/.test(strVal)) {
    return `${strVal}（仅发布日期）`
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
  BLOCKED: '待补数',
  CANCELLED: '已取消',
  WAITING_DEPENDENCY: '等待前置任务',
  scheduled: '定时触发',
  manual: '手动触发',

  // 2. 数据与行情新鲜度
  FRESH: '盘中最新时段',
  PREVIOUS_CLOSE: '前一交易日收盘价基准',
  STALE_BLOCKED: '行情超期阻断',
  NOT_CONFIGURED: '待配置行情源',
  NO_QUOTE: '缺少行情',
  NO_FILING: '缺少财报',
  READY: '数据已就绪',
  ARCHIVED_BASELINE: '基线归档',
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
  ARCHIVED: '已归档',

  // 4. 财务与审计平账
  BALANCED: '平账通过',
  UNBALANCED: '不平账警告',
  AUDITED: '官方财报已审计',
  UNAUDITED: '未审计底账',
  VALID: '验签通过',
  INVALID: '验签失败',
  PENDING_SYNC: '待同步',
  UPLOADED: '已上传',
  UPLOAD_FAILED: '上传失败',

  // 5. 核心任务名称
  US_DAILY: '美股核心日线与宏观',
  JP_DAILY: '日股核心日线',
  OFFICIAL_NEWS: '官方财经资讯分时采集',
  STOCK_SCREENING: '股票收集与形态初筛',
  INDICATOR_UPDATE: '金融指标与市场宽度',
  FINANCE_CALC: '金融计算与估值走廊',
  LOCAL_AUDIT: '本地数据与账本核验',
  GF_MARKET_READINESS: '行情时效与交易时段',
  SEPA_UNIVERSE_SCREENER: '全市场趋势形态初筛',
  SEC_10K_BALANCED_AUDIT: '官方财报平账自检',
  UNIVERSE_567_BATCH: '全景深度研报管线',
  AI_BROWSER_REPLENISHMENT: '官方原文补数清单',
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
      return { text: '运行中', cls: 'bg-[#3987e5]/20 text-[#3987e5] border border-[#3987e5]/40 animate-pulse' }
    case 'QUEUED':
      return { text: '排队中', cls: 'bg-blue-100 text-blue-800 border border-blue-300' }
    case 'SUCCESS':
      return { text: '已完成', cls: 'bg-[#199e70]/15 text-[#199e70] border border-[#199e70]/40' }
    case 'PARTIAL_SUCCESS':
      return { text: '部分完成', cls: 'bg-[#c98500]/15 text-[#c98500] border border-[#c98500]/40' }
    case 'FAILED':
      return { text: '执行失败', cls: 'bg-[#d03b3b]/15 text-[#d03b3b] border border-[#d03b3b]/40' }
    case 'STOPPED':
      return { text: '已停止', cls: 'bg-gray-200 text-gray-700 border border-gray-400' }
    case 'STOPPING':
      return { text: '正在停止', cls: 'bg-[#c98500]/20 text-[#c98500] border border-[#c98500]/40' }
    case 'BLOCKED':
      return { text: '待补数', cls: 'bg-amber-100 text-amber-800 border border-amber-300' }
    case 'CANCELLED':
      return { text: '已取消', cls: 'bg-gray-100 text-gray-600 border border-gray-300' }
    default:
      return { text: toChinese(status) || '待机就绪', cls: 'bg-gray-100 text-gray-700 border border-gray-300' }
  }
}
