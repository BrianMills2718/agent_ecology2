import { useState } from 'react'
import { Modal } from '../shared/Modal'
import { startSimulation } from '../../api/queries'
import type { SimulationStartRequest } from '../../types/api'

const AVAILABLE_MODELS = [
  { value: 'gemini/gemini-2.0-flash', label: 'Gemini 2.0 Flash (fast, cheap)' },
  { value: 'gemini/gemini-1.5-pro', label: 'Gemini 1.5 Pro' },
  { value: 'anthropic/claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
  { value: 'anthropic/claude-3-haiku-20240307', label: 'Claude 3 Haiku (fast)' },
  { value: 'openai/gpt-4o', label: 'GPT-4o' },
  { value: 'openai/gpt-4o-mini', label: 'GPT-4o Mini (fast)' },
]

interface SimulationConfigFormProps {
  isOpen: boolean
  onClose: () => void
  onStarted: () => void
}

export function SimulationConfigForm({ isOpen, onClose, onStarted }: SimulationConfigFormProps) {
  const [duration, setDuration] = useState(60)
  const [agents, setAgents] = useState<number | ''>('')
  const [budget, setBudget] = useState(0.50)
  const [model, setModel] = useState('gemini/gemini-2.0-flash')
  const [rateLimitDelay, setRateLimitDelay] = useState(5)
  const [isStarting, setIsStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleStart = async () => {
    setIsStarting(true)
    setError(null)

    const config: SimulationStartRequest = {
      duration,
      budget,
      model,
      rate_limit_delay: rateLimitDelay,
    }

    if (agents !== '') {
      config.agents = agents
    }

    try {
      const result = await startSimulation(config)
      if (result.success) {
        onStarted()
        onClose()
      } else {
        setError(result.error || 'Failed to start simulation')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start simulation')
    } finally {
      setIsStarting(false)
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Start New Simulation">
      <div className="space-y-4">
        {/* Duration */}
        <div>
          <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
            Duration (seconds)
          </label>
          <input
            type="number"
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
            min={10}
            max={3600}
            className="w-full px-3 py-2 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded text-[var(--text-primary)] focus:border-[var(--accent-primary)] focus:outline-none"
          />
          <p className="text-xs text-[var(--text-tertiary)] mt-1">
            How long the simulation will run (10-3600 seconds)
          </p>
        </div>

        {/* Agents */}
        <div>
          <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
            Number of Agents
          </label>
          <input
            type="number"
            value={agents}
            onChange={(e) => setAgents(e.target.value === '' ? '' : Number(e.target.value))}
            min={1}
            max={20}
            placeholder="All available"
            className="w-full px-3 py-2 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded text-[var(--text-primary)] focus:border-[var(--accent-primary)] focus:outline-none"
          />
          <p className="text-xs text-[var(--text-tertiary)] mt-1">
            Leave empty for all available agents
          </p>
        </div>

        {/* Budget */}
        <div>
          <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
            API Budget ($)
          </label>
          <input
            type="number"
            value={budget}
            onChange={(e) => setBudget(Number(e.target.value))}
            min={0.01}
            max={10}
            step={0.01}
            className="w-full px-3 py-2 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded text-[var(--text-primary)] focus:border-[var(--accent-primary)] focus:outline-none"
          />
          <p className="text-xs text-[var(--text-tertiary)] mt-1">
            Maximum API cost before stopping ($0.01 - $10.00)
          </p>
        </div>

        {/* Model */}
        <div>
          <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
            LLM Model
          </label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full px-3 py-2 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded text-[var(--text-primary)] focus:border-[var(--accent-primary)] focus:outline-none"
          >
            {AVAILABLE_MODELS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </div>

        {/* Rate Limit Delay */}
        <div>
          <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
            Rate Limit Delay (seconds)
          </label>
          <input
            type="number"
            value={rateLimitDelay}
            onChange={(e) => setRateLimitDelay(Number(e.target.value))}
            min={0.5}
            max={60}
            step={0.5}
            className="w-full px-3 py-2 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded text-[var(--text-primary)] focus:border-[var(--accent-primary)] focus:outline-none"
          />
          <p className="text-xs text-[var(--text-tertiary)] mt-1">
            Delay between API calls (0.5-60 seconds)
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="p-3 bg-[var(--accent-danger)]/10 border border-[var(--accent-danger)] rounded text-[var(--accent-danger)] text-sm">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-4 border-t border-[var(--border-color)]">
          <button
            onClick={onClose}
            disabled={isStarting}
            className="px-4 py-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleStart}
            disabled={isStarting}
            className="px-4 py-2 text-sm bg-[var(--accent-secondary)] text-white rounded hover:bg-[var(--accent-secondary)]/80 transition-colors disabled:opacity-50"
          >
            {isStarting ? 'Starting...' : 'Start Simulation'}
          </button>
        </div>
      </div>
    </Modal>
  )
}
