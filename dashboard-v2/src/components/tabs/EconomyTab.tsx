// Economy tab - Capital flow, charts, and genesis activity

import { CapitalFlowPanel } from '../panels/CapitalFlowPanel'
import { ChartsPanel } from '../panels/ChartsPanel'
import { GenesisPanel } from '../panels/GenesisPanel'

export function EconomyTab() {
  return (
    <div className="p-4 space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <CapitalFlowPanel />
        <GenesisPanel />
      </div>
      <ChartsPanel />
    </div>
  )
}
