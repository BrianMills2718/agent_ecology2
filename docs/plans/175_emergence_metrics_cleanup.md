# Plan #175: Emergence Metrics Cleanup

**Status:** 📋 Planned

**Priority:** High
**Blocked By:** None
**Blocks:** None

---

## Problem

The emergence metrics in the dashboard include poorly-defined metrics that don't measure what they claim to:

- **Specialization Index** - Measures coefficient of variation of action *types* (invoke/transfer/create), not actual role differentiation. Misleading.
- **Capital Depth** - Only works if dependency tracking is implemented properly (unclear if it is)

Users need to understand what metrics actually mean.

## Solution

### 1. Remove/Simplify Metrics

**KEEP** (with clear explanations):
- **Coordination Density** - % of possible agent pairs that have interacted. Simple network connectivity measure.
- **Reuse Ratio** - % of artifacts used by agents other than their creator. Shows infrastructure building.
- **Genesis Independence** - % of invocations that are non-genesis. Shows ecosystem maturity.
- **Coalition Count** - Number of disconnected agent clusters. Shows network fragmentation.

**REMOVE**:
- **Specialization Index** - Doesn't measure what it claims
- **Capital Depth** - Keep only if dependency tracking is verified working

### 2. Add Tooltips/Explanations

Each metric in the UI should have:
- Clear one-line description
- How it's calculated (formula)
- What high/low values mean

### 3. Update Alert Thresholds

Remove alerts for removed metrics. Adjust remaining thresholds to be meaningful.

## Files Affected

- dashboard-v2/src/components/tabs/OverviewTab.tsx (modify)
- dashboard-v2/src/components/panels/EmergencePanel.tsx (modify)
- dashboard-v2/src/hooks/useEmergenceAlerts.ts (modify)
- dashboard-v2/src/types/api.ts (modify - remove unused fields)

## Implementation

### Phase 1: Simplify UI

1. Remove Specialization Index gauge from OverviewTab and EmergencePanel
2. Remove Capital Depth gauge (or mark as "experimental")
3. Keep: Coordination, Reuse, Independence, Coalitions

### Phase 2: Add Tooltips

Add hover tooltips to each remaining metric explaining:
```
Coordination Density: 45%
━━━━━━━━━━━━━━━━━━━━
What: % of agent pairs that have interacted
Formula: unique_pairs / (n × (n-1) / 2)
Meaning: Higher = more connected network
```

### Phase 3: Update Alerts

Remove alerts for:
- specialization_index thresholds
- capital_depth thresholds (unless verified working)

Keep alerts for:
- coordination_density (first interaction, 30%, 50%)
- reuse_ratio (first reuse, 30%, 50%)
- genesis_independence (20%, 40%, 60%)
- coalition_count (2+)

## Verification

```bash
cd dashboard-v2 && npm run build
# Manual: verify removed metrics don't appear
# Manual: verify tooltips explain remaining metrics
```
