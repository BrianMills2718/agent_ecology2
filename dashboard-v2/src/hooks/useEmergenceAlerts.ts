// Hook to detect emergence threshold crossings and trigger alerts

import { useEffect, useRef } from 'react'
import { useAlertStore } from '../stores/alerts'
import type { EmergenceMetrics } from '../types/api'

interface ThresholdConfig {
  metric: keyof EmergenceMetrics
  thresholds: number[]
  labels: string[]
  getMessage: (value: number, threshold: number, label: string) => string
}

const THRESHOLD_CONFIGS: ThresholdConfig[] = [
  {
    metric: 'coordination_density',
    thresholds: [0.1, 0.3, 0.5, 0.7],
    labels: ['initial', 'emerging', 'growing', 'strong'],
    getMessage: (value, threshold, label) =>
      threshold === 0.1
        ? `First coordination detected! Agents beginning to interact (${(value * 100).toFixed(0)}%)`
        : `Coordination density reached ${(threshold * 100).toFixed(0)}% - ${label} collaboration`,
  },
  {
    metric: 'specialization_index',
    thresholds: [0.2, 0.4, 0.6],
    labels: ['beginning', 'developing', 'advanced'],
    getMessage: (_value, threshold, label) =>
      `Specialization at ${(threshold * 100).toFixed(0)}% - agents ${label} differentiated roles`,
  },
  {
    metric: 'reuse_ratio',
    thresholds: [0.1, 0.3, 0.5],
    labels: ['starting', 'growing', 'mature'],
    getMessage: (_value, threshold, label) =>
      threshold === 0.1
        ? `First artifact reuse! Ecosystem beginning to share code`
        : `Reuse ratio at ${(threshold * 100).toFixed(0)}% - ${label} shared artifact ecosystem`,
  },
  {
    metric: 'genesis_independence',
    thresholds: [0.2, 0.4, 0.6, 0.8],
    labels: ['early', 'growing', 'mature', 'self-sustaining'],
    getMessage: (_value, threshold, label) =>
      `Genesis independence at ${(threshold * 100).toFixed(0)}% - ${label} ecosystem`,
  },
  {
    metric: 'coalition_count',
    thresholds: [2, 3, 5, 7],
    labels: ['pair', 'trio', 'multiple', 'complex'],
    getMessage: (_value, threshold, label) =>
      threshold === 2
        ? `First coalition detected! Two agents forming a group`
        : `${threshold} coalitions formed - ${label} agent groupings`,
  },
  {
    metric: 'capital_depth',
    thresholds: [2, 4, 6],
    labels: ['shallow', 'medium', 'deep'],
    getMessage: (_value, threshold, label) =>
      threshold === 2
        ? `First dependency chain detected! Agents building on each other's work`
        : `Capital depth at ${threshold} - ${label} dependency chains`,
  },
]

// Simple notification sound using Web Audio API
function playNotificationSound(soundEnabled: boolean) {
  if (!soundEnabled) return

  try {
    const audioContext = new (window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)()
    const oscillator = audioContext.createOscillator()
    const gainNode = audioContext.createGain()

    oscillator.connect(gainNode)
    gainNode.connect(audioContext.destination)

    oscillator.frequency.value = 440 // A4 note
    oscillator.type = 'sine'
    gainNode.gain.value = 0.1

    oscillator.start()
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3)
    oscillator.stop(audioContext.currentTime + 0.3)
  } catch {
    // Audio not available
  }
}

export function useEmergenceAlerts(metrics: EmergenceMetrics | undefined) {
  const prevMetrics = useRef<EmergenceMetrics | null>(null)
  const addAlert = useAlertStore((s) => s.addAlert)
  const recordMilestone = useAlertStore((s) => s.recordMilestone)
  const hasMilestone = useAlertStore((s) => s.hasMilestone)
  const soundEnabled = useAlertStore((s) => s.soundEnabled)

  useEffect(() => {
    if (!metrics) return

    // Check each threshold config
    for (const config of THRESHOLD_CONFIGS) {
      const currentValue = metrics[config.metric]
      const prevValue = prevMetrics.current?.[config.metric] ?? 0

      // Check each threshold
      for (let i = 0; i < config.thresholds.length; i++) {
        const threshold = config.thresholds[i]
        const label = config.labels[i]

        // Skip if we've already recorded this milestone
        if (hasMilestone(config.metric, threshold)) continue

        // Check if we just crossed this threshold
        if (currentValue >= threshold && prevValue < threshold) {
          const message = config.getMessage(currentValue, threshold, label)

          // Determine alert type
          const type =
            config.thresholds.indexOf(threshold) === 0 ? 'milestone' : 'threshold'

          addAlert({
            type,
            message,
            metric: config.metric,
            value: currentValue,
            threshold,
          })

          recordMilestone(config.metric, threshold)
          playNotificationSound(soundEnabled)
        }
      }
    }

    prevMetrics.current = metrics
  }, [metrics, addAlert, recordMilestone, hasMilestone, soundEnabled])
}
