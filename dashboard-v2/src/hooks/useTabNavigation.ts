// Hook for URL hash-based tab navigation

import { useState, useEffect, useCallback } from 'react'

export type TabId = 'overview' | 'agents' | 'artifacts' | 'economy' | 'activity' | 'network'

const VALID_TABS: TabId[] = ['overview', 'agents', 'artifacts', 'economy', 'activity', 'network']
const DEFAULT_TAB: TabId = 'overview'
const STORAGE_KEY = 'dashboard-last-tab'

function getTabFromHash(): TabId {
  const hash = window.location.hash.slice(1) // Remove '#'
  if (VALID_TABS.includes(hash as TabId)) {
    return hash as TabId
  }
  return DEFAULT_TAB
}

function getStoredTab(): TabId | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored && VALID_TABS.includes(stored as TabId)) {
      return stored as TabId
    }
  } catch {
    // localStorage not available
  }
  return null
}

function storeTab(tab: TabId) {
  try {
    localStorage.setItem(STORAGE_KEY, tab)
  } catch {
    // localStorage not available
  }
}

export function useTabNavigation() {
  // Initialize from URL hash, then localStorage, then default
  const [activeTab, setActiveTabState] = useState<TabId>(() => {
    const hashTab = getTabFromHash()
    if (hashTab !== DEFAULT_TAB) return hashTab
    return getStoredTab() ?? DEFAULT_TAB
  })

  // Update URL hash and localStorage when tab changes
  const setActiveTab = useCallback((tab: TabId) => {
    setActiveTabState(tab)
    window.location.hash = tab
    storeTab(tab)
  }, [])

  // Listen for browser back/forward
  useEffect(() => {
    const handleHashChange = () => {
      const newTab = getTabFromHash()
      setActiveTabState(newTab)
      storeTab(newTab)
    }

    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  // Keyboard shortcuts: 1-6 for tabs
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) {
        return
      }

      const keyNum = parseInt(e.key)
      if (keyNum >= 1 && keyNum <= 6) {
        const tab = VALID_TABS[keyNum - 1]
        if (tab) {
          setActiveTab(tab)
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [setActiveTab])

  // Set initial hash if not present
  useEffect(() => {
    if (!window.location.hash) {
      window.location.hash = activeTab
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return { activeTab, setActiveTab, tabs: VALID_TABS }
}
