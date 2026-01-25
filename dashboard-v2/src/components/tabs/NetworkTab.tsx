// Network tab - Full-width network visualization

import { NetworkPanel } from '../panels/NetworkPanel'

export function NetworkTab() {
  return (
    <div className="p-4">
      {/* Network panel gets full width in this tab */}
      <NetworkPanel />
    </div>
  )
}
