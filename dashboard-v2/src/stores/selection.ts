// Global selection state for navigating to agents/artifacts from search

import { create } from 'zustand'

interface SelectionStore {
  selectedAgentId: string | null
  selectedArtifactId: string | null
  setSelectedAgent: (id: string | null) => void
  setSelectedArtifact: (id: string | null) => void
  clearSelection: () => void
}

export const useSelectionStore = create<SelectionStore>((set) => ({
  selectedAgentId: null,
  selectedArtifactId: null,
  setSelectedAgent: (id) => set({ selectedAgentId: id, selectedArtifactId: null }),
  setSelectedArtifact: (id) => set({ selectedArtifactId: id, selectedAgentId: null }),
  clearSelection: () => set({ selectedAgentId: null, selectedArtifactId: null }),
}))
