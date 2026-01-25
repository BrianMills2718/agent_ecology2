import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Header } from './components/layout/Header'
import { MainGrid } from './components/layout/MainGrid'
import { AlertToastContainer } from './components/shared/AlertToast'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000, // Data considered fresh for 5s
      refetchInterval: 10000, // Refetch every 10s
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen flex flex-col">
        <Header />
        <MainGrid />
        <AlertToastContainer />
      </div>
    </QueryClientProvider>
  )
}

export default App
