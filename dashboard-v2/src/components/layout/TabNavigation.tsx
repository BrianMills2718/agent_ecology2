// Tab navigation bar component

import type { TabId } from '../../hooks/useTabNavigation'

interface TabConfig {
  id: TabId
  label: string
  icon: string
  shortcut: number
}

const TABS: TabConfig[] = [
  { id: 'overview', label: 'Overview', icon: '📊', shortcut: 1 },
  { id: 'agents', label: 'Agents', icon: '🤖', shortcut: 2 },
  { id: 'artifacts', label: 'Artifacts', icon: '📦', shortcut: 3 },
  { id: 'economy', label: 'Economy', icon: '💰', shortcut: 4 },
  { id: 'activity', label: 'Activity', icon: '📜', shortcut: 5 },
  { id: 'network', label: 'Network', icon: '🕸️', shortcut: 6 },
]

interface TabNavigationProps {
  activeTab: TabId
  onTabChange: (tab: TabId) => void
  badges?: Partial<Record<TabId, number | string>>
}

export function TabNavigation({ activeTab, onTabChange, badges = {} }: TabNavigationProps) {
  return (
    <nav className="bg-[var(--bg-secondary)] border-b border-[var(--border-color)]">
      <div className="flex items-center px-4">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id
          const badge = badges[tab.id]

          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`
                flex items-center gap-2 px-4 py-3 text-sm font-medium
                border-b-2 transition-colors
                ${isActive
                  ? 'border-[var(--accent-primary)] text-[var(--accent-primary)]'
                  : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-color)]'
                }
              `}
              title={`${tab.label} (${tab.shortcut})`}
            >
              <span>{tab.icon}</span>
              <span>{tab.label}</span>
              {badge !== undefined && (
                <span
                  className={`
                    px-1.5 py-0.5 text-xs rounded-full
                    ${isActive
                      ? 'bg-[var(--accent-primary)]/20'
                      : 'bg-[var(--bg-tertiary)]'
                    }
                  `}
                >
                  {badge}
                </span>
              )}
              <span className="text-xs text-[var(--text-secondary)] opacity-50">
                {tab.shortcut}
              </span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
