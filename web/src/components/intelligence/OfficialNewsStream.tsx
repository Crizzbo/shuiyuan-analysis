import React, { useMemo, useState } from 'react'
import { Pagination } from '../Pagination'
import { EventCard } from '../common/EventCard'
import { formatSourceName } from '../../utils/format'
import type { TerminalNewsItem } from '../../types/api'

export interface OfficialNewsStreamProps {
  newsItems: TerminalNewsItem[]
  newsLoading: boolean
  onSelectTicker?: (ticker: string) => void
  onViewRadarDetail: (title: string) => void
}

/**
 * 官方监管机构与交易所资讯流 (Official News Stream)
 * 覆盖 SEC、JPX、FED 及权威通讯社，支持分时检索、多维度主题分类与因果联动
 */
export const OfficialNewsStream: React.FC<OfficialNewsStreamProps> = ({
  newsItems,
  newsLoading,
  onSelectTicker,
  onViewRadarDetail,
}) => {
  const [newsSourceFilter, setNewsSourceFilter] = useState('ALL')
  const [newsCategoryFilter, setNewsCategoryFilter] = useState('ALL')
  const [newsSearch, setNewsSearch] = useState('')
  const [newsPage, setNewsPage] = useState(1)
  const newsPageSize = 12

  // 提取可用信源
  const availableSources = useMemo(() => {
    const set = new Set<string>()
    newsItems.forEach((n) => {
      if (n.source) set.add(n.source)
    })
    return Array.from(set)
  }, [newsItems])

  // 提取可用主题分类与统计
  const availableCategories = useMemo(() => {
    const counts: Record<string, number> = {}
    newsItems.forEach((n) => {
      if (n.category) counts[n.category] = (counts[n.category] || 0) + 1
    })
    return counts
  }, [newsItems])

  // 过滤后的资讯流
  const filteredNews = useMemo(() => {
    return newsItems.filter((n) => {
      if (newsSourceFilter !== 'ALL' && n.source !== newsSourceFilter) return false
      if (newsCategoryFilter !== 'ALL' && n.category !== newsCategoryFilter) return false
      if (newsSearch.trim()) {
        const q = newsSearch.trim().toLowerCase()
        const text = `${n.title} ${n.category || ''} ${n.micro_physical_impact || ''}`.toLowerCase()
        if (!text.includes(q)) return false
      }
      return true
    })
  }, [newsItems, newsSourceFilter, newsCategoryFilter, newsSearch])

  const totalNewsPages = Math.max(1, Math.ceil(filteredNews.length / newsPageSize))
  const pagedNews = useMemo(() => {
    const start = (newsPage - 1) * newsPageSize
    return filteredNews.slice(start, start + newsPageSize)
  }, [filteredNews, newsPage, newsPageSize])

  return (
    <div className="bg-[var(--surface-color)] border border-[var(--border-color)] rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border-color)]">
        <div>
          <h3 className="text-sm font-bold text-[var(--text-primary)]">
            官方监管机构与交易所资讯流
          </h3>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5">
            覆盖 SEC、东京证券交易所 (JPX)、美联储 (FED) 及官方通讯社权威公开信源。
          </p>
        </div>
        <span className="text-xs font-mono px-2.5 py-1 rounded bg-[#176249]/10 text-[#176249] border border-[#176249]/25">
          共收录 {newsItems.length} 条资讯
        </span>
      </div>

      {/* 筛选与搜索工具栏 */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-[var(--bg-card)] p-3 rounded-lg border border-[var(--border-color)]">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-[var(--text-muted)] mr-1">信源筛选:</span>
          <button
            type="button"
            onClick={() => {
              setNewsSourceFilter('ALL')
              setNewsPage(1)
            }}
            className={`px-2.5 py-1 rounded text-xs font-medium cursor-pointer transition-all ${
              newsSourceFilter === 'ALL'
                ? 'bg-[#176249] text-white shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-slate-100'
            }`}
          >
            全部信源 ({newsItems.length})
          </button>
          {availableSources.map((s) => (
            <button
              type="button"
              key={s}
              onClick={() => {
                setNewsSourceFilter(s)
                setNewsPage(1)
              }}
              className={`px-2.5 py-1 rounded text-xs font-medium cursor-pointer transition-all ${
                newsSourceFilter === s
                  ? 'bg-[#176249] text-white shadow-sm'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-slate-100'
              }`}
            >
              {formatSourceName(s)}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="搜索资讯标题关键字..."
            value={newsSearch}
            onChange={(e) => {
              setNewsSearch(e.target.value)
              setNewsPage(1)
            }}
            className="text-xs bg-[var(--surface-color)] text-[var(--text-primary)] border border-[var(--border-color)] rounded-lg px-3 py-1.5 w-60 focus:outline-none focus:border-[#176249] hover:border-slate-300"
          />
        </div>
      </div>

      {/* 主题分类筛选药丸 */}
      {Object.keys(availableCategories).length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 p-3 rounded-lg bg-[var(--bg-card)] border border-[var(--border-color)] text-xs">
          <span className="text-[11px] text-[var(--text-muted)] mr-1">主题分类:</span>
          <button
            type="button"
            onClick={() => {
              setNewsCategoryFilter('ALL')
              setNewsPage(1)
            }}
            className={`px-2.5 py-1 rounded text-xs font-medium cursor-pointer transition-all ${
              newsCategoryFilter === 'ALL'
                ? 'bg-[#176249] text-white shadow-sm'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-slate-100'
            }`}
          >
            全部类别 ({newsItems.length})
          </button>
          {Object.entries(availableCategories).map(([cat, count]) => (
            <button
              type="button"
              key={cat}
              onClick={() => {
                setNewsCategoryFilter(cat)
                setNewsPage(1)
              }}
              className={`px-2.5 py-1 rounded text-xs font-medium cursor-pointer transition-all flex items-center gap-1 ${
                newsCategoryFilter === cat
                  ? 'bg-[#176249] text-white shadow-sm'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] bg-[var(--surface-color)] border border-[var(--border-color)] hover:border-slate-300'
              }`}
            >
              <span>{cat}</span>
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                  newsCategoryFilter === cat ? 'bg-white/20' : 'bg-slate-100 text-slate-600'
                }`}
              >
                {count}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* 资讯流水表格列表 */}
      {newsLoading ? (
        <div className="p-8 text-center text-xs text-[var(--text-muted)] flex items-center justify-center gap-2">
          <span className="w-3.5 h-3.5 border-2 border-[#176249] border-t-transparent rounded-full animate-spin" />
          正在检索官方资讯流...
        </div>
      ) : pagedNews.length > 0 ? (
        <div className="space-y-2.5">
          {pagedNews.map((item, idx) => (
            <EventCard
              key={`${item.source}-${idx}`}
              title={item.title}
              severity={item.severity}
              published_at={item.published_at || undefined}
              source_name={item.source}
              category={item.category}
              micro_physical_impact={item.micro_physical_impact}
              involved_entities={item.involved_entities}
              is_distilled={item.is_distilled}
              onSelectTicker={onSelectTicker}
              onViewRadarDetail={() => onViewRadarDetail(item.title)}
            />
          ))}
        </div>
      ) : (
        <div className="p-8 text-center text-xs text-[var(--text-muted)] bg-[var(--bg-card)] rounded-xl border border-[var(--border-color)]">
          暂无匹配的官方来源资讯。点击右上角“即时抽取官方资讯”触发分时采集。
        </div>
      )}

      {/* 资讯分页器 */}
      {filteredNews.length > newsPageSize && (
        <div className="pt-2">
          <Pagination
            currentPage={newsPage}
            totalPages={totalNewsPages}
            totalItems={filteredNews.length}
            pageSize={newsPageSize}
            onPageChange={setNewsPage}
          />
        </div>
      )}
    </div>
  )
}
