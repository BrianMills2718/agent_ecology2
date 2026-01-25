// Zustand store for emergence alerts

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface EmergenceAlert {
  id: string
  type: 'milestone' | 'threshold' | 'trend'
  message: string
  metric: string
  value: number
  threshold: number
  timestamp: Date
  dismissed: boolean
}

export interface MilestoneRecord {
  metric: string
  threshold: number
  achievedAt: Date
}

interface AlertStore {
  alerts: EmergenceAlert[]
  milestones: MilestoneRecord[]
  soundEnabled: boolean
  addAlert: (alert: Omit<EmergenceAlert, 'id' | 'timestamp' | 'dismissed'>) => void
  dismissAlert: (id: string) => void
  dismissAll: () => void
  recordMilestone: (metric: string, threshold: number) => void
  hasMilestone: (metric: string, threshold: number) => boolean
  toggleSound: () => void
}

export const useAlertStore = create<AlertStore>()(
  persist(
    (set, get) => ({
      alerts: [],
      milestones: [],
      soundEnabled: false,

      addAlert: (alert) => {
        const newAlert: EmergenceAlert = {
          ...alert,
          id: `${alert.metric}-${alert.threshold}-${Date.now()}`,
          timestamp: new Date(),
          dismissed: false,
        }
        set((state) => ({
          alerts: [newAlert, ...state.alerts].slice(0, 50), // Keep last 50
        }))
      },

      dismissAlert: (id) => {
        set((state) => ({
          alerts: state.alerts.map((a) =>
            a.id === id ? { ...a, dismissed: true } : a
          ),
        }))
      },

      dismissAll: () => {
        set((state) => ({
          alerts: state.alerts.map((a) => ({ ...a, dismissed: true })),
        }))
      },

      recordMilestone: (metric, threshold) => {
        const existing = get().milestones.find(
          (m) => m.metric === metric && m.threshold === threshold
        )
        if (!existing) {
          set((state) => ({
            milestones: [
              ...state.milestones,
              { metric, threshold, achievedAt: new Date() },
            ],
          }))
        }
      },

      hasMilestone: (metric, threshold) => {
        return get().milestones.some(
          (m) => m.metric === metric && m.threshold === threshold
        )
      },

      toggleSound: () => {
        set((state) => ({ soundEnabled: !state.soundEnabled }))
      },
    }),
    {
      name: 'emergence-alerts',
      partialize: (state) => ({
        milestones: state.milestones,
        soundEnabled: state.soundEnabled,
      }),
    }
  )
)
