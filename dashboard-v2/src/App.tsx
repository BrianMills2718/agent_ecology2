import { useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Header } from './components/layout/Header'
import { TabNavigation } from './components/layout/TabNavigation'
import { AlertToastContainer } from './components/shared/AlertToast'
import { useTabNavigation } from './hooks/useTabNavigation'
import { useWebSocketStore } from './stores/websocket'
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

  // Connect WebSocket on mount
  useEffect(() => {
    connect()
  }, [connect])

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
