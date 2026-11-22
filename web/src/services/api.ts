import type {
  ApiResponse,
  HealthData,
  DashboardSummaryData,
  MarketQuotesData,
  IndicatorsData,
  EventsData,
  EventItem,
  CollectionOverviewData,
  TaskRerunResult,
  CandidatesData,
  CompanyAnalysisData,
  PipelineStatusData,
  PipelineRunItem,
  LogsData,
  SettingsData,
  AutomatedValuationData,
  ValuationCompanyItem,
  MarketArchiveItem,
  MarketReconciliationMap,
  TaskSchedulerInfo,
  MarketStatisticsData,
  BatchQuotesResponseData,
  ComprehensiveFinanceSuiteData,
  TerminalNewsItem,
  TerminalTasksConfigData,
} from '../types/api'

const BASE_URL = '' // 相对路径，由 Vite proxy 或 Python 网关同源处理

async function request<T>(endpoint: string, options?: RequestInit): Promise<ApiResponse<T>> {
  const url = `${BASE_URL}${endpoint}`
  const headers = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(options?.headers || {}),
  }

  try {
    const res = await fetch(url, { ...options, headers })
    const json = (await res.json()) as ApiResponse<T>
    if (!res.ok && !json.error) {
      return {
        ok: false,
        data: {} as T,
        meta: { as_of: '', updated_at: '', source: '', status: 'ERROR' },
        error: { code: `HTTP_${res.status}`, message: `请求失败: ${res.statusText}` },
      }
    }
    return json
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : '网络连接异常'
    return {
      ok: false,
      data: {} as T,
      meta: { as_of: '', updated_at: '', source: '', status: 'NETWORK_ERROR' },
      error: { code: 'NETWORK_ERROR', message: errorMsg },
    }
  }
}

export const api = {
  // 1. 系统健康与环境
  getHealth: () => request<HealthData>('/api/health'),

  // 2. 总览工作台
  getDashboardSummary: () => request<DashboardSummaryData>('/api/dashboard/summary'),
  getMarketStatistics: () => request<MarketStatisticsData>('/api/market/statistics'),

  // 3. 行情矩阵与批量采集
  getMarketQuotes: (market: 'ALL' | 'US' | 'JP' = 'ALL') =>
    request<MarketQuotesData>(`/api/markets/quotes?market=${market}`),

  batchCollectQuotes: (tickers: string[] | string, forceRefresh = false) =>
    request<BatchQuotesResponseData>('/api/terminal/quotes/batch-collect', {
      method: 'POST',
      body: JSON.stringify({ tickers, force_refresh: forceRefresh }),
    }),

  // 3.1 全盘流式分批并发采集 (Chunk-and-Stream Option 1)
  getStreamChunkStatus: () =>
    request<{
      status: string
      data: {
        schema_version: string
        total_chunks_available: number
        completed_chunks: number[]
        completed_chunks_count: number
        total_tickers_archived: number
        last_run_at: string | null
        last_processed_chunk: number
        next_chunk_to_process: number
        chunk_records: Record<string, any>
      }
    }>('/api/terminal/quotes/stream-chunk-status'),

  streamChunkCollect: (startChunk = 1, endChunk = 5, dryRun = false, maxWorkers = 4) =>
    request<{
      status: string
      message: string
      data: {
        pipeline: string
        start_chunk: number
        end_chunk: number
        processed_chunks: number[]
        total_chunks_processed: number
        total_tickers_collected: number
        total_tickers_failed: number
        elapsed_seconds: number
        chunk_results: Array<{
          chunk: number
          status: string
          tickers_collected?: number
          elapsed_seconds?: number
          receipt_file?: string
          error?: string
        }>
        errors: string[]
        checkpoint: any
      }
    }>('/api/terminal/quotes/stream-chunk-collect', {
      method: 'POST',
      body: JSON.stringify({
        start_chunk: startChunk,
        end_chunk: endChunk,
        dry_run: dryRun,
        max_workers: maxWorkers,
      }),
    }),

  // 4. 宏观与量化指标
  getLatestIndicators: () => request<IndicatorsData>('/api/indicators/latest'),

  // 5. 事件情报库
  getEvents: (params?: {
    severity?: string
    verification_status?: string
    date?: string
    q?: string
    limit?: number
  }) => {
    const sp = new URLSearchParams()
    if (params?.severity) sp.set('severity', params.severity)
    if (params?.verification_status) sp.set('verification_status', params.verification_status)
    if (params?.date) sp.set('date', params.date)
    if (params?.q) sp.set('q', params.q)
    if (params?.limit) sp.set('limit', String(params.limit))
    return request<EventsData>(`/api/events?${sp.toString()}`)
  },

  getEventDetail: (eventId: string) =>
    request<EventItem>(`/api/events/${encodeURIComponent(eventId)}`),

  distillEvents: () =>
    request<{
      message: string
      cycle_result?: Record<string, unknown>
      total_events: number
    }>('/api/events/distill', {
      method: 'POST',
      body: '{}',
    }),

  // 6. 采集中心
  getCollectionOverview: () => request<CollectionOverviewData>('/api/collection/overview'),

  // 采集中心子开关：阻塞重跑单个任务
  rerunCollectionTask: (pipelineId: string) =>
    request<TaskRerunResult>('/api/collection/tasks/rerun', {
      method: 'POST',
      body: JSON.stringify({ pipeline_id: pipelineId }),
    }),

  // 采集中心子开关：启用/停用单个任务
  toggleCollectionTask: (pipelineId: string, enabled?: boolean) =>
    request<{ pipeline_id: string; enabled: boolean; status: string }>(
      '/api/collection/tasks/toggle',
      {
        method: 'POST',
        body: JSON.stringify({ pipeline_id: pipelineId, enabled }),
      }
    ),

  // 7. 计算分析（无打分）
  getAnalyticsCandidates: (market: 'ALL' | 'US' | 'JP' = 'ALL', limit = 20, page = 1, q = '', assetCategory = 'ALL') => {
    const params = new URLSearchParams()
    if (market) params.set('market', market)
    if (limit) params.set('limit', String(limit))
    if (page) params.set('page', String(page))
    if (q) params.set('q', q)
    if (assetCategory && assetCategory !== 'ALL') params.set('asset_category', assetCategory)
    return request<CandidatesData>(`/api/analytics/candidates?${params.toString()}`)
  },

  getCompanyAnalysis: (ticker: string) =>
    request<CompanyAnalysisData>(`/api/analytics/company?ticker=${encodeURIComponent(ticker)}`),

  // 8. 全局总启动开关与流水线状态
  getPipelineStatus: () => request<PipelineStatusData>('/api/pipeline/status'),

  startPipeline: (mode = 'local_audit_sync', market = 'ALL') =>
    request<{ run_id: string; message: string }>('/api/pipeline/start', {
      method: 'POST',
      body: JSON.stringify({ mode, market }),
    }),

  stopPipeline: (runId?: string) =>
    request<{ message: string; run_id: string }>('/api/pipeline/stop', {
      method: 'POST',
      body: JSON.stringify({ run_id: runId }),
    }),

  getPipelineRuns: () => request<{ runs: PipelineRunItem[] }>('/api/pipeline/runs'),

  // 9. 系统日志
  getLogs: (params?: { level?: string; module?: string; q?: string; limit?: number }) => {
    const sp = new URLSearchParams()
    if (params?.level) sp.set('level', params.level)
    if (params?.module) sp.set('module', params.module)
    if (params?.q) sp.set('q', params.q)
    if (params?.limit) sp.set('limit', String(params.limit || 100))
    return request<LogsData>(`/api/logs?${sp.toString()}`)
  },

  // 10. 系统配置
  getSettings: () => request<SettingsData>('/api/settings'),

  // 11. 终端后台任务与定时调度
  getTerminalTasks: () => request<TaskSchedulerInfo>('/api/terminal/tasks'),

  startTerminalBatch: () => request<{ run_id: string }>('/api/terminal/tasks/start', {
    method: 'POST',
    body: '{}',
  }),

  setTerminalAutomatic: (enabled: boolean) => request<TaskSchedulerInfo>('/api/terminal/tasks/automatic', {
    method: 'POST',
    body: JSON.stringify({ enabled }),
  }),

  runTerminalTask: (taskId: string, ticker?: string) =>
    request<{ run_id: string; status: string; task: string; ticker?: string }>('/api/terminal/tasks/run', {
      method: 'POST',
      body: JSON.stringify({ task: taskId, ticker }),
    }),

  scheduleTerminalTask: (taskId: string, enabled: boolean) =>
    request<{ enabled: boolean }>('/api/terminal/tasks/schedule', {
      method: 'POST',
      body: JSON.stringify({ task: taskId, enabled }),
    }),

  getMarketArchives: () =>
    request<{ items: MarketArchiveItem[]; reconciliation?: MarketReconciliationMap }>('/api/terminal/market-archives'),

  getTerminalNews: () =>
    request<{ items: TerminalNewsItem[] }>('/api/terminal/news'),

  // 12. 自动带入数据金融估值与 24 大模型全息计算
  getFinanceCompanies: () =>
    request<{ companies: ValuationCompanyItem[]; total_count: number }>('/api/finance/companies'),

  getFinanceModels: (ticker = 'NVDA') =>
    request<ComprehensiveFinanceSuiteData>(`/api/finance/models?ticker=${encodeURIComponent(ticker)}`),

  getAutoValuation: (ticker: string) =>
    request<AutomatedValuationData>(`/api/finance/auto-calculate?ticker=${encodeURIComponent(ticker)}`),

  calculateAutoValuation: (ticker: string, adjustments?: Record<string, unknown>) =>
    request<AutomatedValuationData>('/api/finance/auto-calculate', {
      method: 'POST',
      body: JSON.stringify({ ticker, adjustments }),
    }),

  // 13. 全盘任务参数化 JSON 配置 (SSOT)
  getTaskConfig: () => request<TerminalTasksConfigData>('/api/tasks/config'),

  updateTaskConfig: (config: TerminalTasksConfigData | Record<string, any>) =>
    request<TerminalTasksConfigData>('/api/tasks/config', {
      method: 'POST',
      body: JSON.stringify(config),
    }),

  // 14. 合规审计与全盘密码学验签
  getAuditOverview: () => request<SettingsData>('/api/audit/overview'),
  verifyLedgerIntegrity: () =>
    request<SettingsData>('/api/terminal/ledger/verify', {
      method: 'POST',
      body: JSON.stringify({ action: 'verify' }),
    }),
}
