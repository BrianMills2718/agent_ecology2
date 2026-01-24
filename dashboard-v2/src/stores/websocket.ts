import { create } from 'zustand'

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected'

interface WebSocketState {
  status: ConnectionStatus
  wsLatency: number | null
  ws: WebSocket | null
  reconnectAttempts: number
  connect: () => void
  disconnect: () => void
}

const MAX_RECONNECT_ATTEMPTS = 10
const RECONNECT_DELAY = 1000

export const useWebSocketStore = create<WebSocketState>((set, get) => ({
  status: 'disconnected',
  wsLatency: null,
  ws: null,
  reconnectAttempts: 0,

  connect: () => {
    const { ws, reconnectAttempts } = get()

    // Don't reconnect if already connected or max attempts reached
    if (ws?.readyState === WebSocket.OPEN) return
    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) return

    set({ status: 'connecting' })

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws`

    const newWs = new WebSocket(wsUrl)
    let pingInterval: ReturnType<typeof setInterval> | null = null
    let lastPingTime: number | null = null

    newWs.onopen = () => {
      console.log('WebSocket connected')
      set({ status: 'connected', reconnectAttempts: 0, ws: newWs })

      // Start ping interval for latency tracking
      pingInterval = setInterval(() => {
        if (newWs.readyState === WebSocket.OPEN) {
          lastPingTime = Date.now()
          newWs.send('ping')
        }
      }, 5000)
    }

    newWs.onmessage = (event) => {
      const data = event.data

      // Handle ping/pong
      if (data === 'pong' && lastPingTime) {
        set({ wsLatency: Date.now() - lastPingTime })
        return
      }
      if (data === 'ping') {
        newWs.send('pong')
        return
      }

      // Handle JSON messages
      try {
        const message = JSON.parse(data)
        // TODO: Dispatch to appropriate handlers based on message.type
        console.log('WS message:', message.type)
      } catch {
        console.error('Failed to parse WebSocket message')
      }
    }

    newWs.onclose = () => {
      console.log('WebSocket disconnected')
      if (pingInterval) clearInterval(pingInterval)
      set({ status: 'disconnected', ws: null })

      // Schedule reconnect
      const attempts = get().reconnectAttempts
      if (attempts < MAX_RECONNECT_ATTEMPTS) {
        const delay = RECONNECT_DELAY * Math.pow(1.5, attempts)
        console.log(`Reconnecting in ${delay}ms (attempt ${attempts + 1})`)
        setTimeout(() => {
          set({ reconnectAttempts: attempts + 1 })
          get().connect()
        }, delay)
      }
    }

    newWs.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  },

  disconnect: () => {
    const { ws } = get()
    if (ws) {
      ws.close()
      set({ ws: null, status: 'disconnected' })
    }
  },
}))
