/**
 * Safely format a number with toFixed, handling undefined/null values
 */
export function safeFixed(value: number | undefined | null, decimals: number = 2): string {
  if (value === undefined || value === null || isNaN(value)) {
    return '—'
  }
  return value.toFixed(decimals)
}

/**
 * Safely format a currency value
 */
export function safeCurrency(value: number | undefined | null, decimals: number = 2): string {
  if (value === undefined || value === null || isNaN(value)) {
    return '$—'
  }
  return `$${value.toFixed(decimals)}`
}

/**
 * Safely format a percentage (value is 0-1, displayed as 0-100%)
 */
export function safePercent(value: number | undefined | null, decimals: number = 1): string {
  if (value === undefined || value === null || isNaN(value)) {
    return '—%'
  }
  return `${(value * 100).toFixed(decimals)}%`
}

/**
 * Format bytes to human readable string
 */
export function formatBytes(bytes: number | undefined | null): string {
  if (bytes === undefined || bytes === null || isNaN(bytes)) {
    return '— B'
  }
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

/**
 * Format an ISO timestamp as a short time string (e.g., "12:34:56")
 */
export function formatTime(timestamp: string | undefined | null): string {
  if (!timestamp) return '—'
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return '—'
  }
}

/**
 * Format an ISO timestamp as relative time (e.g., "2s ago", "5m ago")
 */
export function formatRelativeTime(timestamp: string | undefined | null): string {
  if (!timestamp) return '—'
  try {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffSec = Math.floor(diffMs / 1000)

    if (diffSec < 60) return `${diffSec}s ago`
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
    return `${Math.floor(diffSec / 86400)}d ago`
  } catch {
    return '—'
  }
}
