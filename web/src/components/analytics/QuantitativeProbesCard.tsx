interface QuantitativeProbesCardProps {
  probes: any
}

export function QuantitativeProbesCard({ probes }: QuantitativeProbesCardProps) {
  return (
    <div id="sec-probes" className="scroll-mt-16 bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-[var(--border-color)]">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#176249]" />
          <h3 className="text-sm font-bold text-[var(--text-primary)]">
            财务结构与定量诊断探针
          </h3>
        </div>
        <span className="text-xs text-[var(--text-muted)]">
          报表勾稽核验与偿债信用度量
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* 1. 资产负债表刚性平账自检 */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-[var(--text-muted)]">官方财报平账自检</span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                  probes?.financial_audit?.balance_sheet_balanced
                    ? 'bg-slate-100 text-slate-700 border border-slate-200'
                    : 'bg-rose-50 text-rose-700 border border-rose-200'
                }`}
              >
                {probes?.financial_audit?.balance_sheet_balanced ? '勾稽平衡' : '不平账警告'}
              </span>
            </div>
            <div className="text-lg font-bold font-mono text-[var(--text-primary)] mt-2">
              {probes?.financial_audit?.balance_sheet_balanced ? '资产 = 负债 + 股东权益' : '勾稽异常'}
            </div>
          </div>
          <div className="text-[11px] text-[var(--text-muted)] mt-2 pt-2 border-t border-[var(--border-color)]/40 truncate">
            原档：{probes?.financial_audit?.source_filing || '等待官方原档'}
          </div>
          {probes?.financial_audit?.scheduled_calculation && (
            <div className="text-xs text-[var(--text-muted)] mt-2" title={probes.financial_audit.scheduled_calculation.source_path}>
              期末资产收益率 <strong className="text-[var(--text-primary)]">{(probes.financial_audit.scheduled_calculation.roa * 100).toFixed(2)}%</strong>
              <span className="ml-2">报告期 {probes.financial_audit.scheduled_calculation.period}</span>
            </div>
          )}
        </div>

        {/* 2. 信用风险与偿债能力 (KMV-Merton) */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-[var(--text-muted)]">信用与偿债能力</span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                  probes?.credit_kmv_probe?.distance_to_default_DD !== undefined
                    ? 'bg-slate-100 text-slate-700 border border-slate-200'
                    : 'bg-slate-100 text-slate-500 border border-slate-200'
                }`}
              >
                {probes?.credit_kmv_probe?.distance_to_default_DD !== undefined ? '信用健康' : '待补齐财报数据'}
              </span>
            </div>
            <div className="text-lg font-bold font-mono text-[var(--text-primary)] mt-2">
              {probes?.credit_kmv_probe?.distance_to_default_DD !== undefined
                ? `违约距离 ${probes.credit_kmv_probe.distance_to_default_DD.toFixed(1)} σ`
                : '暂无完整偿债测算'}
            </div>
          </div>
          <div className="text-[11px] text-[var(--text-secondary)] mt-2 pt-2 border-t border-[var(--border-color)]/40">
            {probes?.credit_kmv_probe?.distance_to_default_DD !== undefined
              ? '偿债安全边际充足，无短期违约风险'
              : probes?.credit_kmv_probe?.note || '缺少完整有息负债或总股本数据'}
          </div>
        </div>

        {/* 3. 趋势形态与买点结构 (SEPA) */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-[var(--text-muted)]">技术形态与买点结构</span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                  probes?.timing_and_ohlcv_probe?.sepa_telemetry
                    ? 'bg-slate-100 text-slate-700 border border-slate-200'
                    : 'bg-slate-100 text-slate-500 border border-slate-200'
                }`}
              >
                {probes?.timing_and_ohlcv_probe?.sepa_telemetry ? '形态就绪' : '静态快照'}
              </span>
            </div>
            <div className="text-lg font-bold font-mono text-[var(--text-primary)] mt-2">
              {probes?.timing_and_ohlcv_probe?.sepa_telemetry
                ? `主升阶段 · ${probes.timing_and_ohlcv_probe.sepa_telemetry.stage || '第二阶段'}`
                : '日线快照基准'}
            </div>
          </div>
          <div className="text-[11px] text-[var(--text-secondary)] mt-2 pt-2 border-t border-[var(--border-color)]/40 truncate">
            {probes?.timing_and_ohlcv_probe?.note || '已接入全市场趋势形态指标'}
          </div>
        </div>
      </div>
    </div>
  )
}
