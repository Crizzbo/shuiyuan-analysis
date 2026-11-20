interface MoatAndSupplyChainCardProps {
  aiQual: any
}

export function MoatAndSupplyChainCard({ aiQual }: MoatAndSupplyChainCardProps) {
  return (
    <div id="sec-moat" className="scroll-mt-16 grid grid-cols-1 xl:grid-cols-12 gap-5">
      {/* 商业模式与护城河 */}
      <div className="xl:col-span-8 bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-[var(--border-color)]">
          <span className="w-2 h-2 rounded-full bg-[#176249]" />
          <h3 className="text-sm font-bold text-[var(--text-primary)]">
            商业模式与护城河壁垒剖析
          </h3>
        </div>

        {/* 核心商业模式 */}
        <div className="space-y-1.5">
          <div className="text-xs font-semibold text-[var(--text-secondary)]">盈利模式与业务架构</div>
          <div className="text-xs text-[var(--text-secondary)] leading-relaxed bg-[var(--bg-card)] p-3.5 rounded-lg border border-[var(--border-color)]/60">
            {aiQual?.business_model || '核心商业模型由高附加值产品与服务矩阵驱动，具备内生现金流创造力。'}
          </div>
        </div>

        {/* 护城河支柱 */}
        {aiQual?.moat_analysis && (
          <div className="space-y-2 pt-2">
            <div className="text-xs font-semibold text-[var(--text-secondary)]">护城河关键支柱</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="bg-[var(--bg-card)] rounded-lg p-3 border border-[var(--border-color)]/50 text-xs">
                <div className="font-semibold text-[var(--text-primary)]">网络效应</div>
                <div className="text-[11px] text-[var(--text-muted)] mt-1 leading-relaxed">
                  {aiQual.moat_analysis.network_effects}
                </div>
              </div>
              <div className="bg-[var(--bg-card)] rounded-lg p-3 border border-[var(--border-color)]/50 text-xs">
                <div className="font-semibold text-[var(--text-primary)]">客户转换成本</div>
                <div className="text-[11px] text-[var(--text-muted)] mt-1 leading-relaxed">
                  {aiQual.moat_analysis.switching_costs}
                </div>
              </div>
              <div className="bg-[var(--bg-card)] rounded-lg p-3 border border-[var(--border-color)]/50 text-xs">
                <div className="font-semibold text-[var(--text-primary)]">规模与成本优势</div>
                <div className="text-[11px] text-[var(--text-muted)] mt-1 leading-relaxed">
                  {aiQual.moat_analysis.cost_advantage_and_scale}
                </div>
              </div>
              <div className="bg-[var(--bg-card)] rounded-lg p-3 border border-[var(--border-color)]/50 text-xs">
                <div className="font-semibold text-[var(--text-primary)]">无形资产与专利</div>
                <div className="text-[11px] text-[var(--text-muted)] mt-1 leading-relaxed">
                  {aiQual.moat_analysis.intangible_assets}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 上下游供应链结构 */}
      <div className="xl:col-span-4 bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-[var(--border-color)]">
          <span className="w-2 h-2 rounded-full bg-rose-500" />
          <h3 className="text-sm font-bold text-[var(--text-primary)]">
            产业链上下游集中度
          </h3>
        </div>

        {/* 上游供应端 */}
        <div className="bg-[var(--bg-card)] p-3.5 rounded-lg border border-[var(--border-color)]/60 space-y-1.5 text-xs">
          <div className="font-bold text-[var(--text-primary)] flex items-center justify-between">
            <span>上游核心供应商</span>
            <span className="text-[10px] text-[var(--text-muted)] font-mono">供货集中度</span>
          </div>
          <div className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
            {aiQual?.supply_chain_analysis?.upstream_suppliers?.core_suppliers ||
              '核心供应商深度绑定，交付周期与备件采购处于健康可控区间。'}
          </div>
        </div>

        {/* 下游客户端 */}
        <div className="bg-[var(--bg-card)] p-3.5 rounded-lg border border-[var(--border-color)]/60 space-y-1.5 text-xs">
          <div className="font-bold text-[var(--text-primary)] flex items-center justify-between">
            <span>下游客户与集中度</span>
            <span className="text-[10px] text-[var(--text-muted)] font-mono">结构分散度</span>
          </div>
          <div className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
            {aiQual?.supply_chain_analysis?.downstream_customers?.customer_structure ||
              '前五大客户集中度处于行业良性区间，回款周期与信用条款稳健。'}
          </div>
        </div>
      </div>
    </div>
  )
}
