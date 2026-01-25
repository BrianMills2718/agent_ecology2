// Toast notifications for emergence alerts

import { useEffect } from 'react'
import { useAlertStore } from '../../stores/alerts'

const ALERT_COLORS = {
  milestone: {
    bg: 'bg-gradient-to-r from-green-500/20 to-emerald-500/20',
    border: 'border-green-500/50',
    icon: '🎯',
  },
  threshold: {
    bg: 'bg-gradient-to-r from-blue-500/20 to-cyan-500/20',
    border: 'border-blue-500/50',
    icon: '📈',
  },
  trend: {
    bg: 'bg-gradient-to-r from-amber-500/20 to-yellow-500/20',
    border: 'border-amber-500/50',
    icon: '⚡',
  },
}

function AlertItem({
  id,
  type,
  message,
  timestamp,
  onDismiss,
}: {
  id: string
  type: 'milestone' | 'threshold' | 'trend'
  message: string
  timestamp: Date
  onDismiss: (id: string) => void
}) {
  const colors = ALERT_COLORS[type]

  // Auto-dismiss after 15 seconds
  useEffect(() => {
    const timer = setTimeout(() => {
      onDismiss(id)
    }, 15000)
    return () => clearTimeout(timer)
  }, [id, onDismiss])

  return (
    <div
      className={`${colors.bg} ${colors.border} border rounded-lg p-3 shadow-lg backdrop-blur-sm animate-in slide-in-from-right duration-300`}
    >
      <div className="flex items-start gap-3">
        <span className="text-xl">{colors.icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-white">{message}</p>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            {timestamp.toLocaleTimeString()}
          </p>
        </div>
        <button
          onClick={() => onDismiss(id)}
          className="text-[var(--text-secondary)] hover:text-white transition-colors"
        >
          ✕
        </button>
      </div>
    </div>
  )
}

export function AlertToastContainer() {
  const alerts = useAlertStore((s) => s.alerts)
  const dismissAlert = useAlertStore((s) => s.dismissAlert)
  const dismissAll = useAlertStore((s) => s.dismissAll)
  const soundEnabled = useAlertStore((s) => s.soundEnabled)
  const toggleSound = useAlertStore((s) => s.toggleSound)

  const activeAlerts = alerts.filter((a) => !a.dismissed).slice(0, 5)

  if (activeAlerts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 w-80 space-y-2">
      {/* Controls */}
      <div className="flex items-center justify-between px-2 text-xs">
        <button
          onClick={toggleSound}
          className="flex items-center gap-1 text-[var(--text-secondary)] hover:text-white transition-colors"
          title={soundEnabled ? 'Mute notifications' : 'Enable notification sounds'}
        >
          {soundEnabled ? '🔔' : '🔕'}
          <span>{soundEnabled ? 'Sound on' : 'Sound off'}</span>
        </button>
        {activeAlerts.length > 1 && (
          <button
            onClick={dismissAll}
            className="text-[var(--text-secondary)] hover:text-white transition-colors"
          >
            Dismiss all
          </button>
        )}
      </div>

      {/* Alerts */}
      {activeAlerts.map((alert) => (
        <AlertItem
          key={alert.id}
          id={alert.id}
          type={alert.type}
          message={alert.message}
          timestamp={new Date(alert.timestamp)}
          onDismiss={dismissAlert}
        />
      ))}
    </div>
  )
}
