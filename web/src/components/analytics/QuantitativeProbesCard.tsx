import { ContractionWaveform } from '../common'

interface QuantitativeProbesCardProps {
  probes: any
}

export function QuantitativeProbesCard({ probes }: QuantitativeProbesCardProps) {
  const sepa = probes?.timing_and_ohlcv_probe?.sepa_telemetry
  const pivot = sepa?.pivot_price ?? sepa?.pivot_buy_point ?? null
  const currentPrice = sepa?.current_price ?? null
  const vcpCode = sepa?.vcp_contraction_footprint || 'VCP-4T'

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
          6 大买方量化诊断：勾稽核验 · 偿债信用 · SEPA 形态 · 法证防舞弊 · 反向 DCF · 存货周转
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* 1. 资产负债表会计恒等式核验 */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-[var(--text-muted)]">官方财报会计恒等式核验</span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                  probes?.financial_audit?.balance_sheet_balanced
                    ? 'bg-slate-100 text-slate-700 border border-slate-200'
                    : 'bg-rose-50 text-rose-700 border border-rose-200'
                }`}
              >
                {probes?.financial_audit?.balance_sheet_balanced ? '勾稽平衡通过' : '勾稽待复核'}
              </span>
            </div>
            <div className="text-lg font-bold font-mono text-[var(--text-primary)] mt-2">
              {probes?.financial_audit?.balance_sheet_balanced ? '资产 = 负债 + 股东权益' : '勾稽异常'}
            </div>
          </div>
          <div className="text-[11px] text-[var(--text-muted)] mt-2 pt-2 border-t border-[var(--border-color)]/40 truncate">
            披露来源：{probes?.financial_audit?.source_filing || '等待官方原档'}
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

        {/* 3. 趋势形态与买点结构 (SEPA) 结合 VCP 动态微波形 */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-3 flex flex-col justify-between space-y-2">
          <ContractionWaveform
            pivotPrice={pivot}
            currentPrice={currentPrice}
            vcpCode={vcpCode}
            isStage2={Boolean(sepa?.is_stage_2 ?? true)}
            className="border-0 p-0 bg-transparent shadow-none"
          />
          <div className="text-[11px] text-[var(--text-secondary)] pt-1.5 border-t border-[var(--border-color)]/40 truncate">
            {probes?.timing_and_ohlcv_probe?.note || 'SEPA 均线多头排列 · 波动收缩买点监控中'}
          </div>
        </div>

        {/* 4. 法证会计与防舞弊诊断 (Beneish M-Score 8因子) */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-[var(--text-muted)]">法证会计防舞弊诊断</span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                  probes?.forensics_m_score_probe?.is_manipulation_suspect
                    ? 'bg-rose-50 text-rose-700 border border-rose-200'
                    : probes?.forensics_m_score_probe?.m_score !== undefined
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-slate-100 text-slate-500 border border-slate-200'
                }`}
              >
                {probes?.forensics_m_score_probe?.is_manipulation_suspect
                  ? '存在粉饰嫌疑'
                  : probes?.forensics_m_score_probe?.m_score !== undefined
                  ? '财务质量稳健'
                  : '待补充财报细节'}
              </span>
            </div>
            <div className="text-lg font-bold font-mono text-[var(--text-primary)] mt-2">
              {probes?.forensics_m_score_probe?.m_score !== undefined
                ? `M-Score ${probes.forensics_m_score_probe.m_score.toFixed(3)}`
                : 'Beneish 8因子排查中'}
            </div>
          </div>
          <div className="text-[11px] text-[var(--text-secondary)] mt-2 pt-2 border-t border-[var(--border-color)]/40 truncate" title={probes?.forensics_m_score_probe?.interpretation_zh}>
            {probes?.forensics_m_score_probe?.interpretation_zh || probes?.forensics_m_score_probe?.note || 'M < -1.78 无财务粉饰嫌疑'}
          </div>
        </div>

        {/* 5. 反向 DCF 市场预期增速 (Reverse DCF 5-Year Implied FCF CAGR) */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-[var(--text-muted)]">反向 DCF 市场预期</span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                  probes?.reverse_dcf_probe?.status === 'CONVERGED'
                    ? 'bg-sky-50 text-sky-700 border border-sky-200'
                    : 'bg-slate-100 text-slate-500 border border-slate-200'
                }`}
              >
                {probes?.reverse_dcf_probe?.status === 'CONVERGED' ? '折现增速收敛' : '待输入正向FCF'}
              </span>
            </div>
            <div className="text-lg font-bold font-mono text-[var(--text-primary)] mt-2">
              {probes?.reverse_dcf_probe?.implied_fcf_growth_5y_pct !== undefined
                ? `隐含 CAGR ${probes.reverse_dcf_probe.implied_fcf_growth_5y_pct > 0 ? '+' : ''}${probes.reverse_dcf_probe.implied_fcf_growth_5y_pct}%`
                : '暂无收敛结果'}
            </div>
          </div>
          <div className="text-[11px] text-[var(--text-secondary)] mt-2 pt-2 border-t border-[var(--border-color)]/40 truncate" title={probes?.reverse_dcf_probe?.summary_zh || probes?.reverse_dcf_probe?.note}>
            {probes?.reverse_dcf_probe?.summary_zh || probes?.reverse_dcf_probe?.note || '市价二分法反推未来 5 年复合现金流增长底线'}
          </div>
        </div>

        {/* 6. 存货运转与周转天数 (DIO Efficiency Probe) */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-[var(--text-muted)]">存货周转效率 (DIO)</span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                  probes?.inventory_dio_probe?.estimated_dio_days !== undefined
                    ? 'bg-slate-100 text-slate-700 border border-slate-200'
                    : 'bg-slate-100 text-slate-500 border border-slate-200'
                }`}
              >
                {probes?.inventory_dio_probe?.estimated_dio_days !== undefined ? '周转测算完成' : '轻资产/无实体存货'}
              </span>
            </div>
            <div className="text-lg font-bold font-mono text-[var(--text-primary)] mt-2">
              {probes?.inventory_dio_probe?.estimated_dio_days !== undefined
                ? `DIO ${probes.inventory_dio_probe.estimated_dio_days} 天`
                : '轻资产/未披露存货'}
            </div>
          </div>
          <div className="text-[11px] text-[var(--text-secondary)] mt-2 pt-2 border-t border-[var(--border-color)]/40 truncate">
            {probes?.inventory_dio_probe?.inventory_to_revenue_pct !== undefined
              ? `存货/营收比: ${probes.inventory_dio_probe.inventory_to_revenue_pct}% · ${probes.inventory_dio_probe.dio_health || ''}`
              : probes?.inventory_dio_probe?.note || '无实体库存或三表未单独拆分'}
          </div>
        </div>
      </div>
    </div>
  )
}
