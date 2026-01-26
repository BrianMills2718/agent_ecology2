// Agents tab - Agent list, leaderboard, and details

import { AgentsPanel } from '../panels/AgentsPanel'
import { LeaderboardPanel } from '../panels/LeaderboardPanel'

export function AgentsTab() {
  return (
    <div className="p-4 space-y-4">
      {/* Leaderboard first for quick overview */}
      <LeaderboardPanel />
      {/* Full agent list below */}
      <AgentsPanel />
    </div>
  )
}
