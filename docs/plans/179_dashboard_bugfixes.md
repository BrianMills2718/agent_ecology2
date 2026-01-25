# Plan #179: Dashboard Bugfixes - Coordination Density & Tick Language

**Status:** ✅ Complete
**Priority:** High
**Blocked By:** None
**Blocks:** None

---

## Problem

Two issues in the dashboard:

### 1. Coordination Density shows 100% with no agent interactions

The `calculate_coordination_density` function in `kpis.py` counts ALL interaction pairs including `(agent, genesis_artifact)` pairs in the numerator, but only counts `agent_count * (agent_count - 1) / 2` in the denominator.

Example with 2 agents who only invoke genesis_ledger:
- Pairs counted: `(agent1, genesis_ledger)`, `(agent2, genesis_ledger)` = 2
- Max possible (agent-agent only): `2 * 1 / 2 = 1`
- Result: 200% → clamped to 100%

The network graph correctly shows no edges because there are no actual agent-to-agent interactions.

### 2. Tick-based language still in UI

Plan #83 removed tick-based execution but the UI still shows "T{tick}" labels throughout. Should show timestamps or relative time instead.

---

## Solution

### Fix 1: Coordination Density

Only count pairs where BOTH from_id and to_id are actual agents (not genesis artifacts):

```python
# Filter to only count agent-agent interactions
agent_ids = set(agent_id for agent_id in ... if not agent_id.startswith("genesis_"))
for interaction in interactions:
    from_id = getattr(interaction, "from_id", "")
    to_id = getattr(interaction, "to_id", "")
    # Only count if both are agents, not genesis
    if from_id in agent_ids and to_id in agent_ids and from_id != to_id:
        pair = tuple(sorted([from_id, to_id]))
        interacted_pairs.add(pair)
```

### Fix 2: Replace tick labels with timestamps

In all dashboard-v2 components, replace:
- `T{tick}` → relative timestamp or ISO time
- `Tick {tick}` → actual time

---

## Files Affected

- `src/dashboard/kpis.py` - Fix coordination_density calculation
- `dashboard-v2/src/components/panels/*.tsx` - Replace tick labels
- `dashboard-v2/src/types/api.ts` - Update types if needed

---

## Verification

```bash
cd dashboard-v2 && npm run build
make test
```
