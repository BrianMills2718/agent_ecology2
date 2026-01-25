import { useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Header } from './components/layout/Header'
import { TabNavigation } from './components/layout/TabNavigation'
import { AlertToastContainer } from './components/shared/AlertToast'
import { SearchDialog } from './components/shared/SearchDialog'
import { useTabNavigation } from './hooks/useTabNavigation'
import { useWebSocketStore } from './stores/websocket'
import { useSearchStore } from './stores/search'
import { useSelectionStore } from './stores/selection'
import { useQueryInvalidation } from './hooks/useQueryInvalidation'
import {
  OverviewTab,
  AgentsTab,
  ArtifactsTab,
  EconomyTab,
  ActivityTab,
  NetworkTab,
} from './components/tabs'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000, // Data considered fresh for 5s
      refetchInterval: 10000, // Refetch every 10s
    },
  },
})

function TabContent() {
  const { activeTab, setActiveTab } = useTabNavigation()
  const connect = useWebSocketStore((state) => state.connect)
  const toggleSearch = useSearchStore((state) => state.toggle)
  const setSelectedAgent = useSelectionStore((state) => state.setSelectedAgent)
  const setSelectedArtifact = useSelectionStore((state) => state.setSelectedArtifact)

  // Connect WebSocket on mount
  useEffect(() => {
    connect()
  }, [connect])

  // Keyboard shortcut: Cmd/Ctrl+K for search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        toggleSearch()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [toggleSearch])

  // Invalidate queries when WebSocket messages arrive
  useQueryInvalidation()

  return (
    <>
      <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />
      <main className="flex-1 overflow-auto">
        {activeTab === 'overview' && <OverviewTab />}
        {activeTab === 'agents' && <AgentsTab />}
        {activeTab === 'artifacts' && <ArtifactsTab />}
        {activeTab === 'economy' && <EconomyTab />}
        {activeTab === 'activity' && <ActivityTab />}
        {activeTab === 'network' && <NetworkTab />}
      </main>
      <SearchDialog
        onSelectAgent={setSelectedAgent}
        onSelectArtifact={setSelectedArtifact}
      />
    </>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen flex flex-col">
        <Header />
        <TabContent />
        <AlertToastContainer />
      </div>
    </QueryClientProvider>
  )
}

export default App
