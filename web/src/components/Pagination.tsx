interface PaginationProps {
  currentPage: number
  totalPages: number
  totalItems?: number
  pageSize?: number
  onPageChange: (page: number) => void
  itemName?: string
  compact?: boolean
}

export function Pagination({
  currentPage,
  totalPages,
  totalItems,
  onPageChange,
  itemName = '条',
  compact = false,
}: PaginationProps) {
  if (totalPages <= 1 && (!totalItems || totalItems <= 0)) {
    return null
  }

  const safeTotalPages = Math.max(1, totalPages)
  const safeCurrentPage = Math.min(Math.max(1, currentPage), safeTotalPages)

  if (compact) {
    return (
      <div className="flex items-center justify-between gap-2 px-2 py-2 text-xs border-t border-[var(--border-color)] bg-[var(--surface-color)] select-none">
        <span className="text-[var(--text-muted)] font-mono">
          {totalItems !== undefined ? `共 ${totalItems.toLocaleString()} ${itemName} · ` : ''}
          {safeCurrentPage} / {safeTotalPages} 页
        </span>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            disabled={safeCurrentPage <= 1}
            onClick={() => onPageChange(safeCurrentPage - 1)}
            className="px-2 py-1 rounded border border-[var(--border-color)] bg-[var(--bg-card)] text-[var(--text-primary)] hover:border-[#176249] hover:text-[#176249] disabled:opacity-40 disabled:hover:border-[var(--border-color)] disabled:hover:text-[var(--text-primary)] cursor-pointer disabled:cursor-not-allowed transition-all"
          >
            上一页
          </button>
          <button
            type="button"
            disabled={safeCurrentPage >= safeTotalPages}
            onClick={() => onPageChange(safeCurrentPage + 1)}
            className="px-2 py-1 rounded border border-[var(--border-color)] bg-[var(--bg-card)] text-[var(--text-primary)] hover:border-[#176249] hover:text-[#176249] disabled:opacity-40 disabled:hover:border-[var(--border-color)] disabled:hover:text-[var(--text-primary)] cursor-pointer disabled:cursor-not-allowed transition-all"
          >
            下一页
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-4 py-3 border-t border-[var(--border-color)] bg-[var(--surface-color)] rounded-b-xl select-none">
      <div className="text-xs text-[var(--text-muted)] font-medium">
        {totalItems !== undefined && (
          <span className="mr-2">共 <strong className="text-[var(--text-primary)] font-mono">{totalItems.toLocaleString()}</strong> {itemName}</span>
        )}
        <span>第 <strong className="text-[var(--text-primary)] font-mono">{safeCurrentPage}</strong> / <strong className="font-mono">{safeTotalPages}</strong> 页</span>
      </div>

      <div className="flex items-center gap-1.5">
        <button
          type="button"
          disabled={safeCurrentPage <= 1}
          onClick={() => onPageChange(1)}
          className="px-2.5 py-1 text-xs rounded border border-[var(--border-color)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:border-[#176249] hover:text-[#176249] disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed transition-all"
        >
          首页
        </button>
        <button
          type="button"
          disabled={safeCurrentPage <= 1}
          onClick={() => onPageChange(safeCurrentPage - 1)}
          className="px-3 py-1 text-xs rounded border border-[var(--border-color)] bg-[var(--bg-card)] text-[var(--text-primary)] font-medium hover:border-[#176249] hover:text-[#176249] disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed transition-all"
        >
          上一页
        </button>
        <span className="px-2 text-xs font-mono text-[var(--text-primary)] font-semibold">
          {safeCurrentPage}
        </span>
        <button
          type="button"
          disabled={safeCurrentPage >= safeTotalPages}
          onClick={() => onPageChange(safeCurrentPage + 1)}
          className="px-3 py-1 text-xs rounded border border-[var(--border-color)] bg-[var(--bg-card)] text-[var(--text-primary)] font-medium hover:border-[#176249] hover:text-[#176249] disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed transition-all"
        >
          下一页
        </button>
        <button
          type="button"
          disabled={safeCurrentPage >= safeTotalPages}
          onClick={() => onPageChange(safeTotalPages)}
          className="px-2.5 py-1 text-xs rounded border border-[var(--border-color)] bg-[var(--bg-card)] text-[var(--text-secondary)] hover:border-[#176249] hover:text-[#176249] disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed transition-all"
        >
          末页
        </button>
      </div>
    </div>
  )
}
