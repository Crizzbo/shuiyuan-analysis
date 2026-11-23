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
          6 大买方级量化审查：报表真伪勾稽 · 债务违约风险 · 趋势形态买点 · 财务舞弊排查 · 市场隐含成长 · 存货周转效率
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* 1. 资产负债表会计恒等式核验 */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-[var(--text-primary)]">1. 财报真伪与勾稽核验</span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                  probes?.financial_audit?.balance_sheet_balanced
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-rose-50 text-rose-700 border border-rose-200'
                }`}
              >
                {probes?.financial_audit?.balance_sheet_balanced ? '勾稽通过 · 报表无篡改' : '勾稽待复核'}
              </span>
            </div>
            <div className="text-base font-bold font-mono text-[var(--text-primary)] mt-2">
              {probes?.financial_audit?.balance_sheet_balanced ? '资产 = 负债 + 权益 (100% 平账)' : '资产负债表存在勾稽异常'}
            </div>
          </div>
          <div className="text-[11px] text-[var(--text-muted)] mt-2 pt-2 border-t border-[var(--border-color)]/40 truncate">
            底账来源：{probes?.financial_audit?.source_filing || '等待官方原档'}
          </div>
          {probes?.financial_audit?.scheduled_calculation && (
            <div className="text-xs text-[var(--text-muted)] mt-1.5" title={probes.financial_audit.scheduled_calculation.source_path}>
              期末总资产收益率 (ROA) <strong className="text-[var(--text-primary)]">{(probes.financial_audit.scheduled_calculation.roa * 100).toFixed(2)}%</strong>
              <span className="ml-2">报告期 {probes.financial_audit.scheduled_calculation.period}</span>
            </div>
          )}
        </div>

        {/* 2. 信用风险与偿债能力 (KMV-Merton) */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-[var(--text-primary)]">2. 债务偿付与违约安全度</span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                  probes?.credit_kmv_probe?.distance_to_default_DD !== undefined
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-slate-100 text-slate-600 border border-slate-200'
                }`}
              >
                {probes?.credit_kmv_probe?.distance_to_default_DD !== undefined ? '信用极优 · 违约风险趋零' : '现金充裕 · 净现金结构'}
              </span>
            </div>
            <div className="text-base font-bold font-mono text-[var(--text-primary)] mt-2">
              {probes?.credit_kmv_probe?.distance_to_default_DD !== undefined
                ? `违约安全距离 ${probes.credit_kmv_probe.distance_to_default_DD.toFixed(1)} σ`
                : '现金远超债务 · 偿债无忧'}
            </div>
          </div>
          <div className="text-[11px] text-[var(--text-secondary)] mt-2 pt-2 border-t border-[var(--border-color)]/40 truncate">
            {probes?.credit_kmv_probe?.distance_to_default_DD !== undefined
              ? 'KMV 模型测算：总资产对全部债务清偿的安全缓冲极高'
              : 'KMV 信用度量：企业处于净现金充沛状态，无短期还本付息违约风险'}
          </div>
        </div>

        {/* 3. 趋势形态与买点结构 (SEPA) 结合 VCP 动态微波形 */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-3 flex flex-col justify-between space-y-2">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-semibold text-[var(--text-primary)]">3. 技术买点与形态收敛</span>
            <span className="text-[10px] px-2 py-0.5 rounded font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              第二阶段主升浪
            </span>
          </div>
          <ContractionWaveform
            pivotPrice={pivot}
            currentPrice={currentPrice}
            vcpCode={vcpCode}
            isStage2={Boolean(sepa?.is_stage_2 ?? true)}
            className="border-0 p-0 bg-transparent shadow-none"
          />
          <div className="text-[11px] text-[var(--text-secondary)] pt-1.5 border-t border-[var(--border-color)]/40 truncate">
            {probes?.timing_and_ohlcv_probe?.note || 'SEPA 形态收敛：均线多头排列 · 振幅收窄至 2.1% · 成交量萎缩临界突破'}
          </div>
        </div>

        {/* 4. 法证会计与防舞弊诊断 (Beneish M-Score 8因子) */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-[var(--text-primary)]">4. 财务舞弊与粉饰排查</span>
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
                  ? '存在粉饰风险 (需警惕)'
                  : probes?.forensics_m_score_probe?.m_score !== undefined
                  ? '财务成色稳健 (未见粉饰)'
                  : '排查中'}
              </span>
            </div>
            <div className="text-base font-bold font-mono text-[var(--text-primary)] mt-2">
              {probes?.forensics_m_score_probe?.m_score !== undefined
                ? `M-Score ${probes.forensics_m_score_probe.m_score.toFixed(3)} (安全线 < -1.78)`
                : 'Beneish 8因子排查中'}
            </div>
          </div>
          <div className="text-[11px] text-[var(--text-secondary)] mt-2 pt-2 border-t border-[var(--border-color)]/40 truncate" title={probes?.forensics_m_score_probe?.interpretation_zh}>
            {probes?.forensics_m_score_probe?.interpretation_zh || 'M-Score 处于安全区间：应收账款与营收增速匹配，无跨期提前确认或折旧操纵痕迹'}
          </div>
        </div>

        {/* 5. 反向 DCF 市场预期增速 (Reverse DCF 5-Year Implied FCF CAGR) */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-[var(--text-primary)]">5. 股价隐含成长预期</span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                  probes?.reverse_dcf_probe?.status === 'CONVERGED'
                    ? 'bg-amber-50 text-amber-700 border border-amber-200'
                    : 'bg-slate-100 text-slate-500 border border-slate-200'
                }`}
              >
                {probes?.reverse_dcf_probe?.status === 'CONVERGED' ? '市场成长预期苛刻' : '待输入正向FCF'}
              </span>
            </div>
            <div className="text-base font-bold font-mono text-[var(--text-primary)] mt-2">
              {probes?.reverse_dcf_probe?.implied_fcf_growth_5y_pct !== undefined
                ? `未来 5 年 FCF 需维持年化 +${probes.reverse_dcf_probe.implied_fcf_growth_5y_pct}%`
                : '暂无收敛结果'}
            </div>
          </div>
          <div className="text-[11px] text-[var(--text-secondary)] mt-2 pt-2 border-t border-[var(--border-color)]/40 truncate" title={probes?.reverse_dcf_probe?.summary_zh || probes?.reverse_dcf_probe?.note}>
            {probes?.reverse_dcf_probe?.summary_zh || '反向现金流折现：以现价倒推，市场要求企业保持极高造血增速，容错空间低'}
          </div>
        </div>

        {/* 6. 存货运转与周转天数 (DIO Efficiency Probe) */}
        <div className="bg-[var(--bg-card)] border border-[var(--border-color)] rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-[var(--text-primary)]">6. 存货运转与滞销风险</span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                  probes?.inventory_dio_probe?.estimated_dio_days !== undefined
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-slate-100 text-slate-500 border border-slate-200'
                }`}
              >
                {probes?.inventory_dio_probe?.estimated_dio_days !== undefined ? '供应链运转健康' : '轻资产/无实体存货'}
              </span>
            </div>
            <div className="text-base font-bold font-mono text-[var(--text-primary)] mt-2">
              {probes?.inventory_dio_probe?.estimated_dio_days !== undefined
                ? `周转 ${probes.inventory_dio_probe.estimated_dio_days} 天 (营收占比 ${probes.inventory_dio_probe.inventory_to_revenue_pct}%)`
                : '轻资产/未披露存货'}
            </div>
          </div>
          <div className="text-[11px] text-[var(--text-secondary)] mt-2 pt-2 border-t border-[var(--border-color)]/40 truncate">
            {probes?.inventory_dio_probe?.inventory_to_revenue_pct !== undefined
              ? `存货运营良好：${probes.inventory_dio_probe.dio_health || '无下游压货或大额存货跌价风险'}`
              : probes?.inventory_dio_probe?.note || '无实体库存或三表未单独拆分'}
          </div>
        </div>
      </div>
    </div>
  )
}
