/**
 * Run selection state management (Plan #224)
 *
 * Manages which simulation run is currently being viewed in the dashboard.
 */

import { create } from 'zustand'
import type { RunInfo, SelectRunResponse, ResumeRunResponse } from '../types/api'

interface RunsState {
  // Current run being viewed
  currentRunId: string | null
  currentRun: RunInfo | null
  isLive: boolean

  // Actions
  setCurrentRun: (run: RunInfo | null, isLive?: boolean) => void
  selectRun: (runId: string) => Promise<SelectRunResponse>
  resumeRun: (runId: string) => Promise<ResumeRunResponse>
  clearSelection: () => void
}

const API_BASE = '/api'

export const useRunsStore = create<RunsState>((set) => ({
  currentRunId: null,
  currentRun: null,
  isLive: false,

  setCurrentRun: (run, isLive = false) =>
    set({
      currentRunId: run?.run_id || null,
      currentRun: run,
      isLive,
    }),

  selectRun: async (runId: string): Promise<SelectRunResponse> => {
    try {
      const response = await fetch(`${API_BASE}/runs/select?run_id=${encodeURIComponent(runId)}`, {
        method: 'POST',
      })
      const data: SelectRunResponse = await response.json()

      if (data.success && data.run) {
        set({
          currentRunId: data.run_id,
          currentRun: data.run,
          isLive: false, // Switching to historical view
        })
      }

      return data
    } catch (error) {
      return {
        success: false,
        run_id: runId,
        run: null,
        message: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  },

  resumeRun: async (runId: string): Promise<ResumeRunResponse> => {
    try {
      const response = await fetch(`${API_BASE}/runs/${encodeURIComponent(runId)}/resume`, {
        method: 'POST',
      })
      const data: ResumeRunResponse = await response.json()

      if (data.success) {
        // After resume, the run becomes live
        set((state) => ({
          ...state,
          isLive: true,
        }))
      }

      return data
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  },

  clearSelection: () =>
    set({
      currentRunId: null,
      currentRun: null,
      isLive: false,
    }),
}))
