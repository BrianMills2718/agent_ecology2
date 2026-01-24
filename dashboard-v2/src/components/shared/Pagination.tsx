interface PaginationProps {
  page: number
  total: number
  perPage: number
  onPageChange: (page: number) => void
}

export function Pagination({ page, total, perPage, onPageChange }: PaginationProps) {
  const totalPages = Math.ceil(total / perPage)

  if (totalPages <= 1) return null

  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-[var(--text-secondary)]">
        Showing {page * perPage + 1}-{Math.min((page + 1) * perPage, total)} of {total}
      </span>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page === 0}
          className="px-3 py-1 rounded bg-[var(--bg-tertiary)] hover:bg-[var(--accent-primary)]/20 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          ←
        </button>
        <span className="text-[var(--text-secondary)]">
          Page {page + 1} of {totalPages}
        </span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages - 1}
          className="px-3 py-1 rounded bg-[var(--bg-tertiary)] hover:bg-[var(--accent-primary)]/20 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          →
        </button>
      </div>
    </div>
  )
}
