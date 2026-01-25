// Activity tab - Events, activity feed, and thinking

import { EventsPanel } from '../panels/EventsPanel'
import { ActivityPanel } from '../panels/ActivityPanel'
import { ThinkingPanel } from '../panels/ThinkingPanel'

export function ActivityTab() {
  return (
    <div className="p-4 space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <EventsPanel />
        <ActivityPanel />
        <ThinkingPanel />
      </div>
    </div>
  )
}
