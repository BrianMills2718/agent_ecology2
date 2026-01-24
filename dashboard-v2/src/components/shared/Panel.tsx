import { useState, useEffect, type ReactNode } from 'react'
import clsx from 'clsx'

interface PanelProps {
  title: string
  badge?: number
  collapsible?: boolean
  defaultCollapsed?: boolean
  fullscreenable?: boolean
  onExport?: () => void
  children: ReactNode
}

export function Panel({
  title,
  badge,
  collapsible = false,
  defaultCollapsed = false,
  fullscreenable = false,
  onExport,
  children,
}: PanelProps) {
  const storageKey = `panel_${title.toLowerCase().replace(/\s/g, '_')}_collapsed`

  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === 'undefined') return defaultCollapsed
    const stored = localStorage.getItem(storageKey)
    return stored !== null ? stored === 'true' : defaultCollapsed
  })

  const [fullscreen, setFullscreen] = useState(false)

  // Persist collapse state
  useEffect(() => {
    localStorage.setItem(storageKey, String(collapsed))
  }, [collapsed, storageKey])

  const handleHeaderClick = () => {
    if (collapsible) {
      setCollapsed(!collapsed)
    }
  }

  return (
    <section
      className={clsx(
        'bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg overflow-hidden',
        fullscreen && 'fixed inset-4 z-50'
      )}
    >
      <div
        className={clsx(
          'px-4 py-3 flex items-center justify-between border-b border-[var(--border-color)]',
          collapsible && 'cursor-pointer hover:bg-[var(--bg-tertiary)]'
        )}
        onClick={handleHeaderClick}
      >
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold">{title}</h2>
          {badge !== undefined && (
            <span className="bg-[var(--accent-primary)] text-[var(--bg-primary)] text-xs font-medium px-2 py-0.5 rounded-full">
              {badge}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {onExport && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onExport()
              }}
              className="text-[var(--text-secondary)] hover:text-[var(--accent-primary)] text-xs"
            >
              Export
            </button>
          )}
          {fullscreenable && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                setFullscreen(!fullscreen)
              }}
              className="text-[var(--text-secondary)] hover:text-[var(--accent-primary)] text-sm"
              title={fullscreen ? 'Exit fullscreen' : 'Fullscreen'}
            >
              {fullscreen ? '✕' : '⛶'}
            </button>
          )}
          {collapsible && (
            <span className="text-[var(--text-secondary)] text-sm">
              {collapsed ? '+' : '−'}
            </span>
          )}
        </div>
      </div>

      {!collapsed && (
        <div className="p-4">
          {children}
        </div>
      )}
    </section>
  )
}
