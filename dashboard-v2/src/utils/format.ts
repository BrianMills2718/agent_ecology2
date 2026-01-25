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
