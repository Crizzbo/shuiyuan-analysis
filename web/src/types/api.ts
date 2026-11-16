// 终端统一 API 响应信封
export interface ApiResponse<T> {
  ok: boolean
  data: T
  meta: {
    as_of: string
    updated_at: string
    source: string
    status: string
    run_id?: string
  }
  error: {
    code: string
    message: string
    details?: any
  } | null
}

// 1. 健康与环境
export interface HealthData {
  service_connected: boolean
  environment: string
  architecture_layers_ok: boolean
  ledger_valid: boolean
  ledger_error: string | null
  ledger_total_predictions: number
  latest_data_ts: string
  ready_asset_count: number
  pipeline_state: string
}

// 2. 总览工作台 KPI 与摘要
export interface KpiItem {
  id: string
  label: string
  value: string | number
  unit?: string
  subtext?: string
  tone: 'good' | 'warning' | 'accent' | 'critical' | 'info' | string
}

export interface MarketQuoteItem {
  ticker: string
  market: 'US' | 'JP' | string
  company_name: string
  price: number | null
  currency: string
  formatted_price?: string
  timestamp_iso?: string
  timestamp_formatted?: string
  session_type?: string
  staleness_status?: string
  is_valid: boolean
  data_status: 'FRESH' | 'PREVIOUS_CLOSE' | 'STALE_BLOCKED' | 'NOT_CONFIGURED' | string
  source?: string
  source_file?: string
}

export interface BatchQuoteCollectedItem extends MarketQuoteItem {
  change?: number | null
  change_percent?: number | null
  previous_close?: number | null
  volume?: string | number | null
  is_fresh_today?: boolean
  sha256_hash?: string
  status?: string
  message?: string
}

export interface BatchQuotesResponseData {
  total_requested: number
  total_collected: number
  success_count: number
  failed_count: number
  collected_at: string
  market_session_note: string
  items: BatchQuoteCollectedItem[]
}

export interface IndicatorItem {
  id: string
  name_zh: string
  value: string | number
  display_value: string
  unit?: string
  signal?: string
  signal_zh?: string
  data_status?: string
  as_of?: string
  source: string
}

export interface SepaBreadthData {
  total_universe_scale: number
  stage_2_pivot_ready_count: number
  watchlist_forming_count: number
  trend_disqualified_count: number
  us_chunks: number
  jp_chunks: number
  elapsed_seconds: number
  updated_at: string
}

export interface DataReadinessInfo {
  latest_date_str: string
  latest_timestamp_utc: string
  macro_indices_completed: string[]
  equities_completed: string[]
  total_completed_count: number
  total_required_count?: number
  data_source_summary: string
  market_session_note: string
}

export interface TaskSchedulerTask {
  id: string
  name: string
  schedule: string
  enabled: boolean
  automatic: boolean
  track: 'local' | 'collection'
  dimension?: string
  dimension_name?: string
  description?: string
  serves_stock_analysis?: string
}

export interface TaskSchedulerRun {
  run_id: string
  task: string
  slot: string | null
  trigger: 'scheduled' | 'manual' | string
  status: 'QUEUED' | 'RUNNING' | 'SUCCESS' | 'PARTIAL_SUCCESS' | 'FAILED' | 'CANCELLED' | string
  created_at: string
  started_at: string | null
  finished_at: string | null
  result?: {
    message?: string
    items?: any[]
    [key: string]: any
  } | null
}

export interface TaskSchedulerInfo {
  scheduled: boolean
  automatic_enabled: boolean
  automatic_available: boolean
  tasks: TaskSchedulerTask[]
  active_runs?: TaskSchedulerRun[]
  recent_runs?: TaskSchedulerRun[]
  runs?: TaskSchedulerRun[]
}

export interface MarketArchiveItem {
  symbol: string
  market: string
  count: number
  last_date: string | null
  close?: number | null
  archived_at: string
}

export interface MarketReconciliationItem {
  market: 'US' | 'JP' | string
  target_trading_day: string
  as_of: string
  universe_count: number
  matched_count: number
  no_trade_count: number
  pending_count: number
  unmapped_count: number
  error_count: number
  coverage_rate_pct: number
  active_trade_rate_pct: number
  unmapped_symbols: string[]
  is_balanced: boolean
  balance_diff: number
  narrative_zh: string
}

export interface MarketReconciliationMap {
  us?: MarketReconciliationItem | null
  jp?: MarketReconciliationItem | null
}

export interface EquityValuationCard {
  ticker: string
  company_name: string
  market: 'US' | 'JP'
  currency: string
  current_price: number | null
  formatted_price: string
  data_status: string
  timestamp_formatted: string
  has_valuation: boolean
  corridor?: {
    conservative_floor?: number
    base_fair_value?: number
    optimistic_target?: number
    margin_of_safety_pct?: number
    verdict_grade?: string
    verdict_zh?: string
    valuation_verdict?: string
  } | null
  fundamentals?: {
    free_cash_flow_formatted?: string
    net_cash_status?: string
    wacc_pct?: string
    gross_margin?: string
  } | null
}

export interface TradingSessionItem {
  market: string
  name_zh: string
  session_status: string
  session_status_zh: string
  is_open: boolean
  trading_day: string
  timezone: string
  status_tone: string
}

export interface TradingSessionsData {
  benchmark_date: string
  benchmark_note: string
  us: TradingSessionItem
  jp: TradingSessionItem
}

export interface MarketRegimeData {
  regime_title: string
  regime_status: string
  regime_status_zh: string
  regime_tone: string
  strategy_guidance: string
  adr_us: string
  adr_jp: string
  net_highs_52w: string
}

export interface BenchmarkIndexItem {
  ticker: string
  name_zh: string
  price: number
  formatted_price: string
  change: string
  change_pct: string
  is_up: boolean
  data_status: string
  data_status_zh: string
  role: string
  detail: string
  param_reflection?: string
  currency: string
  symbol: string
  market: string
}

export interface MacroGaugeItem {
  id: string
  name_zh: string
  value: string
  display_value: string
  role: string
  status: string
  status_code: string
  tone: 'warning' | 'good' | 'accent' | 'critical'
  detail: string
  param_reflection?: string
  data_status: string
  data_status_zh: string
}

export interface DashboardSummaryData {
  as_of?: string
  freshness_banner: string
  readiness?: DataReadinessInfo
  task_scheduler?: TaskSchedulerInfo | null
  trading_sessions?: TradingSessionsData
  market_regime?: MarketRegimeData
  benchmark_indices?: BenchmarkIndexItem[]
  macro_gauges?: MacroGaugeItem[]
  kpis: KpiItem[]
  markets: {
    all_quotes?: MarketQuoteItem[]
    daily_archives?: MarketArchiveItem[]
    reconciliation?: MarketReconciliationMap | null
    benchmark_indices?: BenchmarkIndexItem[]
    us_indices: MarketQuoteItem[]
    jp_indices: MarketQuoteItem[]
    jp_core_equities: MarketQuoteItem[]
    market_session_note?: string
    market_status?: string
  }
  indicators: IndicatorItem[]
  core_equities_valuation?: EquityValuationCard[]
  sepa_breadth: SepaBreadthData
  events_summary: {
    total_events: number
    severity_counts: Record<string, number>
    verification_counts: Record<string, number>
    top_events: EventItem[]
  }
  pipeline: PipelineStatusData
  recent_logs: LogItem[]
  market_statistics?: MarketStatisticsData
}

export interface MarketStatisticsData {
  advance_decline: {
    us: {
      advancers: number
      decliners: number
      unchanged: number
      total: number
      ad_ratio: number
      advancers_pct: number
      decliners_pct: number
      regime: string
      median_return_pct: string
    }
    jp: {
      advancers: number
      decliners: number
      unchanged: number
      total: number
      ad_ratio: number
      advancers_pct: number
      decliners_pct: number
      regime: string
      median_return_pct: string
    }
    histogram: Array<{
      range: string
      count: number
      pct: number
      tone: 'up' | 'down' | 'neutral'
    }>
  }
  ma_penetration: {
    above_20d_pct: number
    above_50d_pct: number
    above_150d_pct: number
    above_200d_pct: number
    high_low: {
      new_52w_highs: number
      new_52w_lows: number
      net_expansion: number
      regime: string
    }
  }
  sectors: Array<{
    id: string
    name_zh: string
    return_pct: number
    return_formatted: string
    volume_ratio: number
    advancers_pct: number
    top_driver: string
    is_up: boolean
    strength_rank: number
  }>
  sepa_funnel: {
    total_screened: number
    stage_1_base_building: number
    stage_2_trend_aligned: number
    stage_3_near_high: number
    stage_4_vcp_candidates: number
    top_candidates: Array<{
      ticker: string
      name_zh: string
      price: string
      chg_pct: string
      vcp_contraction_stages: number
      pivot_price: string
      catalyst_driver: string
    }>
  }
  capital_and_sentiment: {
    fear_greed_score: number
    fear_greed_gauge: string
    put_call_ratio: number
    put_call_signal: string
    institutional_net_inflow_str: string
    volume_expansion_ratio: number
    volume_verdict: string
  }
}

// 3. 行情矩阵
export interface MarketQuotesData {
  freshness_banner?: string
  market_session_note?: string
  us_indices: MarketQuoteItem[]
  jp_indices: MarketQuoteItem[]
  jp_core_equities?: MarketQuoteItem[]
  all_ready_quotes?: MarketQuoteItem[]
  all_quotes?: MarketQuoteItem[]
  total_ready?: number
  stale_blocked_count?: number
}

// 4. 量化与宏观指标
export interface IndicatorsData {
  indicators: IndicatorItem[]
  sepa_breadth: SepaBreadthData
}

// 5. 事件情报
export interface EventItem {
  event_id: string
  title: string
  category: string
  severity: 'P0' | 'P1' | 'P2' | 'P3' | string
  severity_zh?: string
  severity_tone?: string
  published_at: string
  published_date?: string
  published_time?: string
  published_at_iso?: string
  collected_at: string
  source_name: string
  credibility_tier: string
  credibility_tier_zh?: string
  credibility_score: number
  verification_status: string
  verification_status_zh?: string
  verification_status_tone?: string
  verification_note?: string
  micro_physical_impact?: string
  involved_entities?: string[] | string
  affected_business_segments?: string[] | string
  estimated_duration?: string
  requires_deep_analysis?: boolean
  raw_content?: string
  is_quarantined_rumor: boolean
}

export interface EventsData {
  total_events: number
  filtered_count: number
  severity_counts: Record<string, number>
  verification_counts: Record<string, number>
  available_dates?: string[]
  date_counts?: Record<string, number>
  selected_date?: string | null
  events: EventItem[]
}

// 6. 采集中心
export interface CollectionPipelineItem {
  pipeline_id: string
  name_zh: string
  enabled: boolean
  completed: number
  total: number
  failed: number
  status_zh: string
  updated_at: string | null
  data_status: string
  is_running?: boolean
  current_stock?: string | null
  track?: 'LOCAL_AUDIT_SYNC' | 'DATA_COLLECTION' | string
  category?: string
  schedule_display?: string
  schedule_zh?: string
  throughput_label?: string
}

export interface CollectionOverviewData {
  pipelines: CollectionPipelineItem[]
  lifecycle_tiers: {
    hot_files: number
    warm_files: number
    cold_files: number
    sec_official_files: number
    hot_max_days: number
    warm_max_days: number
  }
  replenishment_queue: {
    total_pending: number
    created_at: string
    policy: string
    items: Array<{
      ticker: string
      market: string
      company_name: string
      target_filing: string
      official_search_url: string
    }>
  }
  radar_cycles?: any[]
  readiness?: any
}

export interface TaskRerunResult {
  pipeline_id: string
  run_id?: string
  status: string
  duration_ms: number
  execution_mode: 'blocking_sync'
  details: Record<string, any>
}

// 7. 计算分析（无打分）
export interface CandidateItem {
  ticker: string
  market: 'US' | 'JP' | string
  company_name: string
  source_tag: string
  latest_price: number | null
  currency: string
  data_status: string
  has_quote?: boolean
  has_sec_filing: boolean
  readiness_status?: string
  priority?: number
  vcp_code?: string | null
}

export interface CandidatesData {
  total?: number
  page?: number
  page_size?: number
  total_pages?: number
  total_qualified_count: number
  tier0_pivot_ready_count: number
  tier1_watchlist_count: number
  market: string
  candidates: CandidateItem[]
}

export interface CompanyAnalysisData {
  ticker: string
  market: 'US' | 'JP' | string
  company_name: string
  scoring_disabled: boolean
  quote: MarketQuoteItem
  industry_profile: {
    industry_id: string
    industry_name_zh: string
    sector_name_zh: string
    macro_sector_name_zh: string
    description: string
    key_drivers: string[]
    accounting_focus: string[]
    moat_types: string[]
    risk_factors: string[]
    causal_sensitivities?: {
      industry_catalysts: string[]
      industry_risks: string[]
      leading_optimistic_trigger: string
      leading_pessimistic_trigger: string
      valuation_route: string
    }
  }
  ai_qualitative_analysis: {
    business_model: string
    revenue_mix: string
    winner_factor: string
    market_share_and_crn: string
    tam_and_cagr: string
    moat_analysis: {
      network_effects: string
      switching_costs: string
      cost_advantage_and_scale: string
      intangible_assets: string
      reinvestment_efficiency: string
    }
    supply_chain_analysis: {
      upstream_suppliers: {
        core_suppliers: string
        supplier_concentration: string
        supply_chain_risks: string
      }
      downstream_customers: {
        customer_structure: string
        top5_customer_concentration: string
        default_and_churn_risks: string
      }
    }
    financial_statement_deep_dive: {
      profitability_quality: string
      net_cash_status: string
      inventory_cycle_position: string
    }
    catalysts: string[]
    kill_switch_risks: string[]
    rating: string
    stance: string
    tactical_action: string
    analysis_mode: string
  }
  three_state_scenario_corridor: {
    pessimistic_floor: {
      label: string
      price: number
      drawdown_pct: number
      trigger_events: string[]
      rationale: string
    }
    neutral_fair: {
      label: string
      price: number
      upside_pct: number
      rationale: string
    }
    optimistic_target: {
      label: string
      price: number
      upside_pct: number
      trigger_events: string[]
      rationale: string
    }
    tactical_discipline: {
      current_price: number
      tactical_action: string
      strike_zone_verdict: string
    }
    corridor_basis: string
    corridor_note: string
  }
  corridor_status: {
    available: boolean
    basis: string
    note?: string
    reason?: string
  }
  quantitative_probes: {
    financial_audit: {
      has_audited_statement: boolean
      source_filing?: string
      period?: string
      currency?: string
      balance_sheet_balanced: boolean
      metrics?: Record<string, number>
      balance_sheet_abs_diff?: number
      balance_sheet_rel_pct?: number
      scheduled_calculation?: { roa: number; period: string; source_filing: string; source_path: string; input_sha256: string } | null
    }
    credit_kmv_probe: {
      status: string
      symbol?: string
      default_point_debt?: number
      distance_to_default_DD?: number
      implied_default_probability?: number
      is_black_swan_alert?: boolean
      credit_health_status?: string
      note?: string
    }
    timing_and_ohlcv_probe: {
      status: string
      sepa_telemetry?: any
      note?: string
    }
  }
  automated_valuation?: AutomatedValuationData | null
  automated_valuation_issue?: string | null
  events_analysis?: {
    ticker: string
    matched_count?: number
    total_events_count: number
    recent_events: {
      event_id: string
      title: string
      category: string
      severity: string
      published_at: string
      published_date?: string
      published_time?: string
      source_name: string
      verification_status: string
      micro_physical_impact?: string
      involved_entities: string[]
      affected_business_segments: string[]
      estimated_duration?: string
    }[]
    sotp_impact?: SotpImpactData | null
  }
}

export interface SotpImpactData {
  status?: string
  total_events_evaluated?: number
  affected_segments_count?: number
  estimated_enterprise_value_delta_pct?: number
  penetration_level?: string
  impact_summary?: string
  affected_segments?: Array<string | any>
  segment_impacts?: Array<{
    segment_name: string
    revenue_impact_pct: number
    margin_impact_bps: number
    qualitative_summary: string
  }>
}

export interface PipelineSubFlow {
  run_id: string
  name: string
  status: string
  progress_pct: number
  message: string
  started_at?: string | null
  finished_at?: string | null
  details?: any
}

// 8. 流水线控制状态
export interface PipelineStatusData {
  pipeline_state: 'IDLE' | 'QUEUED' | 'RUNNING' | 'STOPPING' | 'STOPPED' | 'SUCCESS' | 'FAILED' | 'PARTIAL_SUCCESS' | string
  is_running: boolean
  active_run_id: string | null
  last_run_id?: string | null
  master_run_id?: string | null
  current_stage: string
  active_pipeline_task?: string | null
  current_processing_stock?: string | null
  progress_pct: number
  summary?: string
  local_audit_sync?: PipelineSubFlow
  data_ingestion?: PipelineSubFlow
  board_engine_status?: {
    is_running: boolean
    status_code: string
    status_label: string
    active_tasks_count: number
    pending_queue_count: number
    total_tasks_tracked: number
  }
  kanban_counts?: Record<string, number>
}

export interface PipelineRunItem {
  run_id: string
  started_at: string
  finished_at?: string
  mode: string
  market: string
  status: string
  stages_completed?: number
  total_stages?: number
  summary?: string
}

// 9. 系统日志
export interface LogItem {
  task?: string
  status?: string
  log_id: string
  timestamp: string
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG' | string
  module: string
  message: string
  run_id?: string
}

export interface LogFileInfo {
  filename: string
  path: string
  size_bytes: number
  size_formatted: string
  exists: boolean
  last_modified: number | null
}

export interface LogsData {
  total_buffered: number
  available_modules: string[]
  log_files?: LogFileInfo[]
  logs: LogItem[]
}

// 12. 自动带入数据金融估值模型
export interface ValuationScenarioItem {
  value_per_share: number
  equity_value?: number
  enterprise_value?: number
  discount_rate_pct: number
  terminal_growth_pct: number
  growth_rates_pct: number[]
  forecast?: Array<{ year: number; cash_flow: number; present_value: number }>
  label: string
  description: string
}

export interface AutomatedValuationData {
  ticker: string
  company_name: string
  market: string
  currency: string
  currency_symbol: string
  current_price: number
  quote_timestamp: string
  underlying_facts: {
    source_filing: string
    period_end: string
    free_cash_flow: number
    free_cash_flow_formatted: string
    diluted_shares: number
    shares_formatted: string
    cash: number
    cash_formatted: string
    total_debt: number
    debt_formatted: string
    net_debt: number
    net_cash_status: string
    total_assets: number
    total_liabilities: number
    stockholders_equity: number
    revenue: number
    operating_income: number
    net_income: number
    is_balanced: boolean
    balance_sheet_diff: number
    balance_sheet_status: string
    risk_free_rate: number
    risk_free_rate_label: string
    market_equity: number
    market_debt: number
  }
  valuation_corridor: {
    conservative_floor: ValuationScenarioItem
    base_fair_value: ValuationScenarioItem
    optimistic_target: ValuationScenarioItem
    current_price: number
    margin_of_safety_pct: number
    verdict_grade: string
    valuation_verdict: string
  }
  capital_cost_wacc: {
    wacc_pct: number
    cost_of_equity_pct: number
    after_tax_cost_of_debt_pct: number
    equity_weight_pct: number
    debt_weight_pct: number
    beta: number
    tax_rate_pct: number
  }
  profitability_ratios: {
    roe_pct?: number
    roa_pct?: number
    gross_margin_pct?: number
    operating_margin_pct?: number
    fcf_conversion_pct?: number
  }
  calculation_provenance: {
    method_version: string
    input_sha256: string
    implementation_path: string
  }
}

export interface ValuationCompanyItem {
  ticker: string
  company_name: string
  market: string
  currency: string
  sector_zh: string
  beta: number
  price: number | null
  formatted_price: string
  has_quote: boolean
  has_filing: boolean
  fiscal_year: number
  is_balanced: boolean
  data_status: string
}

// 13. 24 大专业量化与金融估值模型全息套件
export interface ModelParameterInterpretation {
  param_name: string
  param_key: string
  param_value: string
  benchmark_range: string
  status_level: 'safe' | 'warning' | 'critical' | 'info' | string
  economic_intuition: string
  decision_implication: string
}

export interface FinanceModelItem {
  model_id: string
  name_zh: string
  category: string
  status: string
  execution_ms: number
  theory_origin: string
  output_summary: string
  details: Record<string, any>
  executive_takeaway?: string
  core_param_reflection?: string
  parameter_interpretations?: ModelParameterInterpretation[]
}

export interface ComprehensiveFinanceSuiteData {
  as_of: string
  ticker: string
  total_models: number
  executed_count: number
  verified_count: number
  total_execution_ms: number
  categories_covered: string[]
  models: FinanceModelItem[]
}


// 10. 系统配置
export interface SettingsData {
  architecture_policy: {
    dependency_direction: string
    existing_tools_modified: boolean
    scoring_mode: string
    quote_max_staleness_hours: number
  }
  lifecycle_policy: {
    hot_quote_max_age_days: number
    warm_quote_max_age_days: number
    cold_compression: string
  }
  environment_discovery: {
    gdrive_detected: boolean
    edge_detected: boolean
    python_executable: string
  }
  prediction_ledger: {
    integrity_valid: boolean
    integrity_error: string | null
    total_predictions: number
    total_outcomes: number
    total_reviews: number
    unique_tickers: number
    status_distribution: Record<string, number>
  }
  api_contract_endpoints: Array<{
    method: string
    path: string
    purpose: string
  }>
}
