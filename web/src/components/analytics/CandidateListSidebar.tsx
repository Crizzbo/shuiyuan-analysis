import type { FormEvent } from 'react'
import type { CandidatesData } from '../../types/api'
import { Pagination } from '../Pagination'

interface CandidateListSidebarProps {
  candidatesData: CandidatesData | null
  marketFilter: 'ALL' | 'US' | 'JP'
  assetCategoryFilter: string
  selectedTicker: string
  searchQuery: string
  currentPage: number
  loadingCandidates: boolean
  recollectingTicker: boolean
  onMarketChange: (m: 'ALL' | 'US' | 'JP') => void
  onAssetCategoryChange: (cat: string) => void
  onSearchChange: (q: string) => void
  onSearchSubmit: (e: FormEvent) => void
  onClearSearch: () => void
  onSelectTicker: (ticker: string) => void
  onPageChange: (page: number) => void
  onRecollectStock: (ticker: string) => void
}

const ASSET_CATEGORIES = [
  { id: 'ALL', label: '全部分类' },
  { id: 'Growth_Equity', label: '成长动量' },
  { id: 'Broad_Or_Sector_ETF', label: '核心ETF' },
  { id: 'Gold_And_Commodity', label: '黄金大宗' },
  { id: 'Dividend_And_Defensive', label: '红利防御' },
] as const

export function CandidateListSidebar({
  candidatesData,
  marketFilter,
  assetCategoryFilter,
  selectedTicker,
  searchQuery,
  currentPage,
  loadingCandidates,
  recollectingTicker,
  onMarketChange,
  onAssetCategoryChange,
  onSearchChange,
  onSearchSubmit,
  onClearSearch,
  onSelectTicker,
  onPageChange,
  onRecollectStock,
}: CandidateListSidebarProps) {
  return (
    <div className="lg:col-span-4 xl:col-span-3 bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl shadow-sm flex flex-col overflow-hidden lg:sticky lg:top-4 self-start">
      {/* 左栏头部：统计与市场切换 */}
      <div className="p-3.5 border-b border-[var(--border-color)] space-y-2.5 bg-[var(--bg-card)]">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#176249]" />
            标的资产池索引
          </span>
          <span className="text-[11px] font-mono text-[var(--text-muted)]">
            {candidatesData?.total ? `共 ${candidatesData.total.toLocaleString()} 家` : '加载中…'}
          </span>
        </div>

        {/* 市场过滤胶囊 */}
        <div className="grid grid-cols-3 gap-1 bg-[var(--surface-color)] p-0.5 rounded-lg border border-[var(--border-color)]">
          {(['ALL', 'US', 'JP'] as const).map(m => (
            <button
              key={m}
              type="button"
              onClick={() => onMarketChange(m)}
              className={`py-1 text-xs font-semibold rounded transition-all cursor-pointer text-center ${
                marketFilter === m
                  ? 'bg-[#176249] text-white shadow-sm'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              {m === 'ALL' ? '全部' : m === 'US' ? '美股' : '日股'}
            </button>
          ))}
        </div>

        {/* 多资产自适应分类过滤胶囊 */}
        <div className="grid grid-cols-5 gap-0.5 sm:gap-1 bg-[var(--surface-color)] p-0.5 rounded-lg border border-[var(--border-color)]">
          {ASSET_CATEGORIES.map(cat => (
            <button
              key={cat.id}
              type="button"
              onClick={() => onAssetCategoryChange(cat.id)}
              className={`py-1 px-0.5 text-[10px] font-semibold rounded transition-all cursor-pointer text-center truncate ${
                assetCategoryFilter === cat.id
                  ? 'bg-[#176249] text-white shadow-xs'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
              title={cat.label}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* 搜索框 */}
        <form onSubmit={onSearchSubmit} className="relative flex items-center">
          <input
            type="text"
            value={searchQuery}
            onChange={e => onSearchChange(e.target.value)}
            placeholder="搜索代码或名称 (如 NVDA, 8035)..."
            className="w-full text-xs rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] px-3 py-1.5 pr-16 text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[#176249]"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={onClearSearch}
              className="absolute right-12 text-[12px] text-[var(--text-muted)] hover:text-[var(--text-primary)] px-1 cursor-pointer"
              title="清除搜索"
            >
              ✕
            </button>
          )}
          <button
            type="submit"
            className="absolute right-1 text-xs text-[#176249] hover:bg-[#176249]/10 px-2 py-0.5 rounded font-medium cursor-pointer"
          >
            搜索
          </button>
        </form>
        {searchQuery.trim() && (
          <div className="pt-2 flex items-center justify-between text-[11px]">
            <span className="text-[var(--text-muted)] truncate">目标: {searchQuery.trim().toUpperCase()}</span>
            <button
              type="button"
              disabled={recollectingTicker}
              onClick={() => void onRecollectStock(searchQuery.trim().toUpperCase())}
              className="px-2 py-0.5 rounded bg-[#176249]/10 text-[#176249] hover:bg-[#176249]/20 font-medium cursor-pointer border border-[#176249]/30 shrink-0"
            >
              在调度中拉取数据
            </button>
          </div>
        )}
      </div>

      {/* 标的卡片列表 */}
      <div className="divide-y divide-[var(--border-color)] max-h-[680px] overflow-y-auto scrollbar-thin">
        {loadingCandidates ? (
          <div className="p-8 text-center text-xs text-[var(--text-muted)] space-y-2">
            <div className="w-5 h-5 border-2 border-[#176249] border-t-transparent rounded-full animate-spin mx-auto" />
            <div>正在检索资产池索引…</div>
          </div>
        ) : !candidatesData?.candidates || candidatesData.candidates.length === 0 ? (
          <div className="p-8 text-center text-xs text-[var(--text-muted)]">
            未检索到符合条件的标的
          </div>
        ) : (
          candidatesData.candidates.map(item => {
            const isSelected = selectedTicker === item.ticker
            const isJp = item.market === 'JP'
            const priceSym = isJp ? '¥' : '$'

            return (
              <button
                key={item.ticker}
                type="button"
                onClick={() => onSelectTicker(item.ticker)}
                className={`w-full text-left p-3 transition-all cursor-pointer flex flex-col gap-1.5 ${
                  isSelected
                    ? 'bg-[#176249]/15 dark:bg-[#176249]/35 border-l-4 border-l-[#176249] shadow-2xs'
                    : 'hover:bg-slate-100/70 dark:hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-sm text-[var(--text-primary)]">
                      {item.ticker}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.2 rounded font-medium bg-[var(--bg-card)] border border-[var(--border-color)] text-[var(--text-secondary)]">
                      {item.market}
                    </span>
                  </div>
                  <div className="text-right">
                    {item.latest_price ? (
                      <span className="font-mono font-bold text-xs text-[var(--text-primary)]">
                        {priceSym}{Number(item.latest_price).toLocaleString()}
                      </span>
                    ) : (
                      <span className="text-[10px] text-[var(--text-muted)]">待核验报价</span>
                    )}
                  </div>
                </div>

                <div className="text-xs text-[var(--text-secondary)] truncate">
                  {item.company_name}
                </div>

                <div className="flex items-center justify-between text-[10px] pt-0.5">
                  <div className="flex items-center gap-1.5">
                    <span className="px-1.5 py-0.2 rounded font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                      {item.readiness_status || (item.has_quote ? '行情已就绪' : '待同步')}
                    </span>
                    {item.asset_category === 'Gold_And_Commodity' ? (
                      <span className="px-1.5 py-0.2 rounded bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 font-mono text-[9px] font-bold">
                        黄金大宗
                      </span>
                    ) : item.asset_category === 'Broad_Or_Sector_ETF' ? (
                      <span className="px-1.5 py-0.2 rounded bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 font-mono text-[9px] font-bold">
                        核心ETF
                      </span>
                    ) : item.asset_category === 'Dividend_And_Defensive' ? (
                      <span className="px-1.5 py-0.2 rounded bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 font-mono text-[9px] font-bold">
                        红利防御
                      </span>
                    ) : item.ticker === 'NVDA' ? (
                      <span className="px-1.5 py-0.2 rounded bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-800 font-mono text-[9px] font-bold">
                        估值溢价
                      </span>
                    ) : item.ticker === 'AMD' || item.ticker === 'AVGO' ? (
                      <span className="px-1.5 py-0.2 rounded bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800 font-mono text-[9px] font-bold">
                        安全边际
                      </span>
                    ) : (
                      <span className="px-1.5 py-0.2 rounded bg-cyan-50 text-cyan-700 border border-cyan-200 font-mono text-[9px]">
                        成长动量
                      </span>
                    )}
                  </div>
                  <span className="text-[var(--text-muted)] font-mono text-[9px]">
                    {item.source_tag.replace('官方备案', '').replace('东证交易所 (JPX) 挂牌', '东证')}
                  </span>
                </div>
              </button>
            )
          })
        )}
      </div>

      {/* 左栏底部分页器 */}
      <Pagination
        currentPage={currentPage}
        totalPages={candidatesData?.total_pages || 1}
        totalItems={candidatesData?.total || 0}
        onPageChange={onPageChange}
        itemName="标的"
        compact={true}
      />
    </div>
  )
}
