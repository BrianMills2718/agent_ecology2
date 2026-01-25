import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useWebSocketStore, type WSMessage } from '../stores/websocket'

/**
 * Hook that listens to WebSocket messages and invalidates
 * relevant TanStack Query caches when data changes.
 */
export function useQueryInvalidation() {
  const queryClient = useQueryClient()
  const subscribe = useWebSocketStore((state) => state.subscribe)

  useEffect(() => {
    const unsubscribe = subscribe((message: WSMessage) => {
      // Map message types to query keys to invalidate
      switch (message.type) {
        case 'tick':
        case 'progress':
          queryClient.invalidateQueries({ queryKey: ['progress'] })
          break

        case 'agent_action':
        case 'agent_update':
          queryClient.invalidateQueries({ queryKey: ['agents'] })
          queryClient.invalidateQueries({ queryKey: ['activity'] })
          break

        case 'artifact_created':
        case 'artifact_update':
          queryClient.invalidateQueries({ queryKey: ['artifacts'] })
          break

        case 'transfer':
        case 'escrow':
        case 'mint':
          queryClient.invalidateQueries({ queryKey: ['genesis'] })
          queryClient.invalidateQueries({ queryKey: ['activity'] })
          queryClient.invalidateQueries({ queryKey: ['charts'] })
          break

        case 'thinking':
          queryClient.invalidateQueries({ queryKey: ['thinking'] })
          break

        case 'network_update':
          queryClient.invalidateQueries({ queryKey: ['network'] })
          break

        case 'metrics':
        case 'kpis':
          queryClient.invalidateQueries({ queryKey: ['kpis'] })
          queryClient.invalidateQueries({ queryKey: ['emergence'] })
          break

        case 'event':
          queryClient.invalidateQueries({ queryKey: ['events'] })
          break

        default:
          // For unknown message types, don't invalidate anything
          break
      }
    })

    return unsubscribe
  }, [queryClient, subscribe])
}
