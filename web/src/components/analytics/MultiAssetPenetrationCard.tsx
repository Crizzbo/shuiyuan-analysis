import React from 'react'
import type { MultiAssetProfile } from '../../types/api'

interface MultiAssetPenetrationCardProps {
  profile?: MultiAssetProfile | null
  ticker: string
  companyName: string
}

export const MultiAssetPenetrationCard: React.FC<MultiAssetPenetrationCardProps> = ({
  profile,
  ticker,
  companyName,
}) => {
  if (!profile) return null

  const cat = profile.asset_category
  const isETF = cat === 'Broad_Or_Sector_ETF' || Boolean(profile.etf_profile)
  const isCommodity = cat === 'Gold_And_Commodity' || Boolean(profile.commodity_profile)
  const isDividend = cat === 'Dividend_And_Defensive' || Boolean(profile.dividend_profile)
  const isGrowth = !isETF && !isCommodity && !isDividend

  return (
    <section id="sec-multi-asset" className="card p-6 bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl space-y-6 shadow-sm">
      {/* 顶栏身份标识与资产分类勋章 */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-[var(--border-color)]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg flex items-center justify-center font-bold text-base shadow-sm border border-[var(--border-color)] bg-[var(--bg-card)]">
            {isETF ? '📊' : isCommodity ? '🪙' : isDividend ? '🛡️' : '🚀'}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-[var(--text-primary)]">
                {isETF ? '全球核心指数与主题 ETF 穿透深度分析' : isCommodity ? '黄金与特级贵金属宏观穿透分析' : isDividend ? '高质量自由现金流红利安全分析' : '高成长科技先锋资产评估'}
              </h3>
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                  isETF
                    ? 'bg-purple-100 text-purple-800 border border-purple-200'
                    : isCommodity
                    ? 'bg-amber-100 text-amber-800 border border-amber-200'
                    : isDividend
                    ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                    : 'bg-blue-100 text-blue-800 border border-blue-200'
                }`}
              >
                {profile.category_name_zh}
              </span>
            </div>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">
              {isETF
                ? '穿透前十大成分股重叠度、综合费率跟踪误差、风格因子与宏观降息敏感度'
                : isCommodity
                ? '穿透实物金银交割标准、10年期 TIPS 真实利率弹性、央行去美元化储备配置'
                : isDividend
                ? '穿透股息安全边际、自由现金流对分红覆盖倍数、下行半方差与防御造血屏障'
                : '纯本地 0-Token 执行第二阶段主升浪与 VCP 波动收缩形态评估'}
            </p>
          </div>
        </div>

        <div className="text-xs text-[var(--text-muted)] font-mono">
          资产代码: <span className="font-bold text-[var(--text-primary)]">{ticker}</span> ({companyName})
        </div>
      </div>

      {/* 1. 全球核心指数与主题 ETF 专用穿透面板 */}
      {isETF && profile.etf_profile && (
        <div className="space-y-6">
          {/* 四维核心量化指标卡片 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="p-3.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)]">
              <div className="text-[11px] text-[var(--text-secondary)]">跟踪基准指数</div>
              <div className="text-sm font-bold text-[var(--text-primary)] mt-1 truncate" title={profile.etf_profile.benchmark_index}>
                {profile.etf_profile.benchmark_index}
              </div>
              <div className="text-[10px] text-[var(--text-muted)] mt-1">再平衡: {profile.etf_profile.rebalance_frequency}</div>
            </div>

            <div className="p-3.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)]">
              <div className="text-[11px] text-[var(--text-secondary)]">综合费率与跟踪误差</div>
              <div className="text-sm font-bold text-purple-700 mt-1">
                {profile.etf_profile.expense_ratio_pct.toFixed(2)}%
                <span className="text-xs font-normal text-[var(--text-secondary)] ml-1">
                  / {profile.etf_profile.tracking_error_bps} bps
                </span>
              </div>
              <div className="text-[10px] text-[var(--text-muted)] mt-1">极低摩擦机构级底仓</div>
            </div>

            <div className="p-3.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)]">
              <div className="text-[11px] text-[var(--text-secondary)]">资产规模 (AUM) / 持仓数</div>
              <div className="text-sm font-bold text-[var(--text-primary)] mt-1">
                ${profile.etf_profile.aum_billions.toFixed(1)}B
                <span className="text-xs font-normal text-[var(--text-secondary)] ml-1">
                  ({profile.etf_profile.holdings_count}只)
                </span>
              </div>
              <div className="text-[10px] text-[var(--text-muted)] mt-1">全球顶级流动性基准</div>
            </div>

            <div className="p-3.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)]">
              <div className="text-[11px] text-[var(--text-secondary)]">Beta 系数 / 股息率</div>
              <div className="text-sm font-bold text-[var(--text-primary)] mt-1">
                {profile.etf_profile.style_factors.beta_to_sp500.toFixed(2)}
                <span className="text-xs font-normal text-emerald-700 ml-1">
                  / {profile.etf_profile.style_factors.dividend_yield_pct.toFixed(2)}%
                </span>
              </div>
              <div className="text-[10px] text-[var(--text-muted)] mt-1">
                久期: {profile.etf_profile.style_factors.interest_rate_duration_years > 0 ? `${profile.etf_profile.style_factors.interest_rate_duration_years}年` : '无久期损耗'}
              </div>
            </div>
          </div>

          {/* 前十大重仓成分股穿透表 */}
          <div className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                <span>🎯</span>
                <span>穿透前十大核心重仓成分股与权重分布 (Top 10 Holdings)</span>
              </div>
              <span className="text-[11px] text-[var(--text-secondary)]">
                前十集中度: {profile.etf_profile.top_holdings.reduce((acc, h) => acc + h.weight_pct, 0).toFixed(1)}%
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-[var(--border-color)] text-[var(--text-secondary)]">
                    <th className="py-2 px-2 font-medium w-10">序号</th>
                    <th className="py-2 px-3 font-medium w-24">标的代码</th>
                    <th className="py-2 px-3 font-medium">成分股名称</th>
                    <th className="py-2 px-3 font-medium text-right w-24">持仓权重</th>
                    <th className="py-2 px-3 font-medium w-48">权重占比分布可视化</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-color)]">
                  {profile.etf_profile.top_holdings.map((holding, idx) => (
                    <tr key={holding.ticker} className="hover:bg-slate-50 transition-colors">
                      <td className="py-2 px-2 text-[var(--text-muted)] font-mono">{idx + 1}</td>
                      <td className="py-2 px-3 font-mono font-bold text-[var(--text-primary)]">{holding.ticker}</td>
                      <td className="py-2 px-3 text-[var(--text-primary)] font-medium">{holding.name}</td>
                      <td className="py-2 px-3 text-right font-mono font-semibold text-purple-700">
                        {holding.weight_pct.toFixed(1)}%
                      </td>
                      <td className="py-2 px-3">
                        <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden border border-slate-200">
                          <div
                            className="bg-purple-600 h-full rounded-full"
                            style={{ width: `${Math.min(holding.weight_pct * 4, 100)}%` }}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 宏观降息敏感度与风格雷达 */}
          <div className="p-4 rounded-xl bg-purple-50/60 border border-purple-200 space-y-2">
            <div className="text-xs font-bold text-purple-900 flex items-center gap-1.5">
              <span>⚡</span>
              <span>宏观降息敏感度与风格因子传导研判</span>
            </div>
            <p className="text-xs text-purple-800 leading-relaxed">
              {profile.etf_profile.rate_cut_sensitivity}
            </p>
            <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px] text-purple-700">
              <span className="px-2 py-0.5 rounded bg-white/80 border border-purple-200">
                风格定位: {profile.etf_profile.style_factors.market_cap_style}
              </span>
              <span className="px-2 py-0.5 rounded bg-white/80 border border-purple-200">
                标普500相关性: {profile.etf_profile.style_factors.beta_to_sp500 >= 1.0 ? '高贝塔放大' : '低贝塔防御'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* 2. 黄金与特级贵金属大宗商品专用穿透面板 */}
      {isCommodity && profile.commodity_profile && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="p-3.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)]">
              <div className="text-[11px] text-[var(--text-secondary)]">真实利率负弹性 (10Y TIPS)</div>
              <div className="text-sm font-bold text-amber-700 mt-1">
                {profile.commodity_profile.real_yield_10y_tips_pct.toFixed(2)}%
                <span className="text-xs font-normal text-[var(--text-secondary)] ml-1">
                  (弹性: {profile.commodity_profile.real_yield_elasticity.toFixed(2)})
                </span>
              </div>
              <div className="text-[10px] text-[var(--text-muted)] mt-1">真实利率下行直接提振估值</div>
            </div>

            <div className="p-3.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)]">
              <div className="text-[11px] text-[var(--text-secondary)]">全球金银比 (Gold/Silver)</div>
              <div className="text-sm font-bold text-[var(--text-primary)] mt-1">
                {profile.commodity_profile.gold_silver_ratio ? profile.commodity_profile.gold_silver_ratio.toFixed(1) : '84.1'}
              </div>
              <div className="text-[10px] text-[var(--text-muted)] mt-1">历史中枢 65-75，目前处于高位</div>
            </div>

            <div className="p-3.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)]">
              <div className="text-[11px] text-[var(--text-secondary)]">实物现货交割溢价</div>
              <div className="text-sm font-bold text-emerald-700 mt-1">
                +{profile.commodity_profile.physical_premium_pct.toFixed(2)}%
              </div>
              <div className="text-[10px] text-[var(--text-muted)] mt-1">COMEX/伦敦现货交割强劲</div>
            </div>

            <div className="p-3.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)]">
              <div className="text-[11px] text-[var(--text-secondary)]">对冲评级 / AISC成本</div>
              <div className="text-sm font-bold text-[var(--text-primary)] mt-1 truncate" title={profile.commodity_profile.inflation_hedge_rating}>
                {profile.commodity_profile.aisc_cost_per_oz
                  ? `$${profile.commodity_profile.aisc_cost_per_oz}/oz`
                  : 'Tier-0 货币替代'}
              </div>
              <div className="text-[10px] text-[var(--text-muted)] mt-1">
                {profile.commodity_profile.aisc_cost_per_oz ? '特级金矿采矿全维持成本' : '实物黄金 100% 物理足额背书'}
              </div>
            </div>
          </div>

          {/* 实物储备与金库仓储交付标准 */}
          <div className="p-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border-color)] space-y-3">
            <div className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
              <span>🏛️</span>
              <span>实物交割标准与金库仓储穿透 (Allocated Vault Delivery)</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
                <div className="text-[var(--text-secondary)]">资产属性与实物背书</div>
                <div className="font-semibold text-[var(--text-primary)]">{profile.commodity_profile.asset_sub_type}</div>
                <div className="text-[11px] text-[var(--text-muted)] mt-0.5">{profile.commodity_profile.backing_type}</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1">
                <div className="text-[var(--text-secondary)]">金库物理托管地与安全性</div>
                <div className="font-semibold text-[var(--text-primary)]">{profile.commodity_profile.vault_location || '伦敦地下高安全金库'}</div>
                <div className="text-[11px] text-[var(--text-muted)] mt-0.5">{profile.commodity_profile.inflation_hedge_rating}</div>
              </div>
            </div>
          </div>

          {/* 主权央行去美元化储备配置趋势 */}
          <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200 space-y-2">
            <div className="text-xs font-bold text-amber-900 flex items-center gap-1.5">
              <span>🌐</span>
              <span>主权央行去美元化储备配置动向</span>
            </div>
            <p className="text-xs text-amber-800 leading-relaxed">
              {profile.commodity_profile.central_bank_buying_trend}
            </p>
          </div>
        </div>
      )}

      {/* 3. 高质量自由现金流红利防御资产专用面板 */}
      {isDividend && profile.dividend_profile && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="p-3.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)]">
              <div className="text-[11px] text-[var(--text-secondary)]">股息收益率 (Dividend Yield)</div>
              <div className="text-sm font-bold text-emerald-700 mt-1">
                {profile.dividend_profile.dividend_yield_pct.toFixed(2)}%
              </div>
              <div className="text-[10px] text-[var(--text-muted)] mt-1">显著超越基准债券利差</div>
            </div>

            <div className="p-3.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)]">
              <div className="text-[11px] text-[var(--text-secondary)]">股利支付率 (Payout Ratio)</div>
              <div className="text-sm font-bold text-[var(--text-primary)] mt-1">
                {profile.dividend_profile.payout_ratio_pct.toFixed(1)}%
              </div>
              <div className="text-[10px] text-[var(--text-muted)] mt-1">处于 &lt;60% 健康安全区间</div>
            </div>

            <div className="p-3.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)]">
              <div className="text-[11px] text-[var(--text-secondary)]">FCF 自由现金流覆盖倍数</div>
              <div className="text-sm font-bold text-emerald-700 mt-1">
                {profile.dividend_profile.free_cash_flow_coverage_ratio.toFixed(1)}x
              </div>
              <div className="text-[10px] text-[var(--text-muted)] mt-1">经营造血充足，无缩减分红风险</div>
            </div>

            <div className="p-3.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)]">
              <div className="text-[11px] text-[var(--text-secondary)]">连续分红增长年限</div>
              <div className="text-sm font-bold text-[var(--text-primary)] mt-1">
                {profile.dividend_profile.consecutive_dividend_growth_years} 年
              </div>
              <div className="text-[10px] text-[var(--text-muted)] mt-1">
                下行半方差: {profile.dividend_profile.downside_volatility_pct.toFixed(1)}% (极强抗回撤)
              </div>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 space-y-2">
            <div className="text-xs font-bold text-emerald-900 flex items-center gap-1.5">
              <span>🛡️</span>
              <span>防御造血护城河与安全边际</span>
            </div>
            <p className="text-xs text-emerald-800 leading-relaxed">
              {profile.dividend_profile.defensive_moat_type}
            </p>
          </div>
        </div>
      )}

      {/* 4. 高成长动量股常规状态提示 */}
      {isGrowth && (
        <div className="p-4 rounded-xl bg-blue-50/70 border border-blue-200 space-y-2">
          <div className="text-xs font-bold text-blue-900 flex items-center gap-1.5">
            <span>🚀</span>
            <span>高成长与科技先锋专有评估通道</span>
          </div>
          <p className="text-xs text-blue-800 leading-relaxed">
            该标的已接入 SEPA 经典主升浪与 VCP 4T 极窄收缩突破模型；下方已完整载入官方财报三表底稿、客户与供应商集中度，以及多阶段现金流折现 (DCF) 估值走廊。
          </p>
        </div>
      )}
    </section>
  )
}
export default MultiAssetPenetrationCard
