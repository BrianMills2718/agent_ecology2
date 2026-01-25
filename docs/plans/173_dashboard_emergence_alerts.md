# Plan #173: Dashboard Emergence Alerts

**Status:** ✅ Complete

**Priority:** High
**Blocked By:** None
**Blocks:** None

---

## Problem

The EmergencePanel shows metrics with gauges, but users must constantly watch to notice when interesting thresholds are crossed. Key emergence milestones (first coordination, high specialization, coalition formation) happen silently.

Observing emergent behavior is the core purpose of this project - we need alerts when significant emergence thresholds are crossed.

## Solution

Add an emergence alert system that:

1. **Tracks threshold crossings** - Detect when metrics cross significant thresholds
2. **Shows visual alerts** - Toast notifications that persist until dismissed
3. **Plays sound (optional)** - Audio notification for significant events
4. **Logs milestone history** - Track when emergence milestones were first reached

### Emergence Thresholds

| Metric | Threshold | Meaning |
|--------|-----------|---------|
| coordination_density | 0.3, 0.5, 0.7 | Agents beginning to network, collaborate, coordinate |
| specialization_index | 0.3, 0.5, 0.7 | Agents differentiating roles |
| reuse_ratio | 0.2, 0.4, 0.6 | Ecosystem developing shared artifacts |
| genesis_independence | 0.3, 0.5, 0.7 | Decreasing reliance on genesis artifacts |
| coalition_count | 2, 3, 5 | Distinct agent groups forming |
| capital_depth | 3, 5, 7 | Dependency chains growing |

### Alert Types

1. **First milestone** - "First coordination detected!" (coordination_density > 0.1)
2. **Threshold crossed** - "Coordination density reached 50%"
3. **Trend alert** - "Rapid specialization increase detected"

## Files Affected

- dashboard-v2/src/components/panels/EmergencePanel.tsx (modify)
- dashboard-v2/src/components/shared/AlertToast.tsx (create)
- dashboard-v2/src/hooks/useEmergenceAlerts.ts (create)
- dashboard-v2/src/stores/alerts.ts (create)
- dashboard-v2/src/App.tsx (modify)

## Implementation

### Phase 1: Alert Infrastructure

1. Create Zustand store for alerts:
   ```typescript
   interface Alert {
     id: string
     type: 'milestone' | 'threshold' | 'trend'
     message: string
     metric: string
     value: number
     timestamp: Date
     dismissed: boolean
   }
   ```

2. Create useEmergenceAlerts hook:
   - Track previous metric values
   - Detect threshold crossings
   - Add alerts to store
   - Play sound on significant events

3. Create AlertToast component:
   - Fixed position toast container
   - Auto-dismiss after 10s (or persist until clicked)
   - Different colors for milestone/threshold/trend

### Phase 2: Integration

1. Add hook to EmergencePanel
2. Show milestone badges on metrics that have crossed thresholds
3. Add "Milestones" section showing achieved emergence milestones

### Phase 3: Sound (Optional)

1. Add sound toggle to settings
2. Use Web Audio API for notification sounds
3. Different sounds for different alert types

## Verification

```bash
# Build succeeds
cd dashboard-v2 && npm run build

# Manual testing
make dash-run DURATION=120
# Wait for metrics to change
# Verify alerts appear when thresholds crossed
```

## Notes

- Consider browser notification permission for background tabs
- Store dismissed alerts in localStorage to avoid repeating
- Keep threshold values configurable
