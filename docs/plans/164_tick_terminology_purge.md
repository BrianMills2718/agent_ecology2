# Plan #164: Tick Terminology Purge

**Status:** ✅ Complete

**Verified:** 2026-01-25T00:23:15Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-25T00:23:15Z
tests:
  unit: 2129 passed, 10 skipped, 3 warnings in 42.40s
  e2e_smoke: PASSED (8.82s)
  e2e_real: skipped (--skip-real-e2e)
  doc_coupling: passed
commit: 574cfc6
```
**Priority:** High
**Blocked By:** None
**Blocks:** Documentation clarity, reduced confusion

---

## Problem

The term "tick" persists throughout the codebase despite tick-synchronized execution being removed in Plan #102. This causes continual confusion because:

1. "Tick" implies tick-synchronized execution (one action per tick, two-phase commit)
2. The actual meaning now is just "event counter"
3. Documentation inconsistently describes tick mode as existing/legacy/removed
4. Agents see `{tick}` in prompts but it's meaningless in continuous execution

## Decision

Purge all "tick" terminology. Replace with semantically accurate terms:

| Current | Replacement | Reason |
|---------|-------------|--------|
| `world.tick` | `world.event_number` | Clear, self-documenting |
| `tick` in logs/events | `event_number` | Consistent |
| `{tick}` in agent prompts | Remove entirely | Not meaningful to agents |
| `tick % N == 0` conditions | `iteration % N == 0` | Agent's own iteration count |
| `tick_submitted` | `submitted_at` | Auction timing (event number) |
| `tick_resolved` | `resolved_at` | Auction timing (event number) |
| `last_action_tick` | `last_action_at` | Agent state |
| "tick-based" comments | Remove or update | Stale references |
| "two-phase commit" | Remove | Doesn't exist |

**Out of scope (separate plan needed):**
- Debt contract `due_tick` / `interest_rate` - needs redesign for time-based scheduling, not just rename

## Files Affected

### Core Code (src/)

| File | Changes |
|------|---------|
| `world/world.py` | `self.tick` → `self.event_number`, update all refs |
| `world/mint_auction.py` | `get_tick` → `get_event_number`, `tick` → `event_number` in dicts |
| `world/logger.py` | `tick` param → `event_number`, SummaryLogger |
| `world/ledger.py` | Remove "tick-based" comments |
| `world/invocation_registry.py` | `tick` field → `event_number` |
| `world/genesis/debt_contract.py` | OUT OF SCOPE - needs separate redesign plan |
| `world/genesis/mint.py` | Remove tick comments |
| `world/genesis/ledger.py` | Remove "resets each tick" comment |
| `world/genesis/rights_registry.py` | Remove "per tick" comments |
| `world/contracts.py` | Context `tick` → `event_number` |
| `world/id_registry.py` | Remove tick comment |

### Agent Configs (src/agents/)

Remove `{tick}` from prompts entirely. For periodic conditions, use agent's own iteration count.

| File | Changes |
|------|---------|
| `alpha/agent.yaml` | Remove `{tick}`, remove "this tick" |
| `alpha_2/agent.yaml` | Same |
| `alpha_3/agent.yaml` | Same |
| `beta/agent.yaml` | Same |
| `beta_2/agent.yaml` | Same, `tick % N` → `iteration % N` |
| `beta_3/agent.yaml` | Same |
| `gamma/agent.yaml` | Same |
| `gamma_3/agent.yaml` | Same |
| `delta/agent.yaml` | Same, time-based condition instead of `tick < 50` |
| `delta_3/agent.yaml` | Same |
| `epsilon/agent.yaml` | Same |
| `epsilon_3/agent.yaml` | Same |

### Config Files

| File | Changes |
|------|---------|
| `config/config.yaml` | Remove `{tick}` from prompts, remove tick comments |
| `config/schema.yaml` | Remove tick references |

### Tests (tests/)

All test files using `tick` in test data or assertions need updating.
~30 files affected - mechanical replacement.

### Documentation (docs/)

| File | Changes |
|------|---------|
| `architecture/current/README.md` | Remove "Legacy: Tick-Synchronized Mode" section |
| `architecture/current/CLAUDE.md` | Remove "two-phase commit" reference |
| `architecture/current/execution_model.md` | Already correct, verify |
| `GLOSSARY.md` | Update tick definition or remove |
| `THREAT_MODEL.md` | Update "within tick" → "atomically" |
| `AGENT_HANDBOOK.md` | Update tick references |
| `scripts/doc_coupling.yaml` | Remove "two-phase" reference |

### Meta/Acceptance Gates

| File | Changes |
|------|---------|
| `meta/acceptance_gates/simulation.yaml` | Major rewrite - describes tick-based execution |
| `meta/acceptance_gates/world.yaml` | Remove `world.tick` reference |
| `meta/acceptance_gates/agents.yaml` | Update world state description |
| `meta/acceptance_gates/dashboard.yaml` | `tick` → `sequence` in events |
| `meta/acceptance_gates/agent_loop.yaml` | Remove tick-synchronized references |
| `meta/acceptance_gates/configuration.yaml` | Remove "negative tick count" |

### Scripts

| File | Changes |
|------|---------|
| `scripts/view_log.py` | `tick` → `sequence` in output |

### Archive (NO CHANGES)

Files in `docs/archive/`, `docs/simulation_learnings/`, and ADRs are historical records - leave unchanged.

## Plan

### Phase 1: Core rename (world.tick → world.event_number)

1. Rename `World.tick` to `World.event_number` in `world.py`
2. Rename `increment_event_counter()` return and all internal refs
3. Update `mint_auction.py` (`get_tick` → `get_event_number`, dict keys)
4. Update `logger.py` (tick param → event_number)
5. Update `invocation_registry.py` (tick field → event_number)
6. Update `contracts.py` context
7. Skip `debt_contract.py` - needs separate redesign
8. Run tests, fix failures

### Phase 2: Agent prompts

1. Remove `{tick}` from all agent YAML files
2. Remove `{tick}` from `config/config.yaml` prompt templates
3. Replace `tick % N` conditions with `iteration % N` (using agent's own counter)
4. Remove "this tick" / "per tick" language from prompts

### Phase 3: Tests

1. Update test files to use `event_number`
2. Verify tests pass

### Phase 4: Documentation

1. Update `architecture/current/README.md` - remove tick mode section
2. Update `architecture/current/CLAUDE.md` - remove two-phase commit
3. Update `GLOSSARY.md` - remove or update tick definition
4. Update `THREAT_MODEL.md` - "within tick" → "atomically"
5. Update `AGENT_HANDBOOK.md`
6. Update `scripts/doc_coupling.yaml`
7. Remove stale "tick-based" comments from code

### Phase 5: Acceptance gates

1. Rewrite `simulation.yaml` for continuous execution
2. Update other acceptance gate files

### Phase 6: Cleanup

1. Grep for remaining "tick" references (excluding archive/ADRs)
2. Verify no regressions
3. Create follow-up plan for debt contract time-based redesign

## Verification

```bash
# No tick references in active code (excluding archive/ADRs/simulation_learnings)
grep -r "\btick\b" src/ config/ docs/architecture/current/ meta/acceptance_gates/ \
  --include="*.py" --include="*.yaml" --include="*.md" \
  | grep -v "archive/" | grep -v "/adr/" | grep -v "simulation_learnings/" \
  | grep -v "debt_contract"  # Excluded - separate plan

# Tests pass
make test

# Type check passes
make mypy
```

## E2E Verification

1. Run simulation with `make run DURATION=30`
2. Verify logs use `event_number` not `tick`
3. Verify agent prompts don't contain `tick`
4. Dashboard displays correctly

---

## Notes

- ADRs are immutable - they document historical decisions about tick vs continuous
- Archive files are historical - leave them as-is
- `simulation_learnings/` are research notes - leave as-is (they discuss the tick model problems)
- Debt contract needs separate plan - uses tick for scheduling, requires time-based redesign

## Follow-up Plans Needed

- **Plan #167: Debt Contract Time-Based Redesign** - Replace `due_tick` with timestamps, `interest_rate` with per-hour/per-day rate

(Note: Originally referenced as #165 but that number was taken by Genesis Contracts as Artifacts)
