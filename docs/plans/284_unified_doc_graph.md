# Plan #284: Implement Unified Documentation Graph

**Status:** ✅ Complete

**Verified:** 2026-02-04T11:01:01Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-02-04T11:01:01Z
tests:
  unit: skipped (--status-only, CI-validated)
  e2e_smoke: skipped (--status-only, CI-validated)
  e2e_real: skipped (--status-only, CI-validated)
  doc_coupling: skipped (--status-only, CI-validated)
commit: 3af9b6b
```
**Created:** 2026-02-04
**ADR:** 0005 (Unified Documentation Graph)

## Problem

ADR-0005 describes a unified documentation graph but it's only partially implemented:

**What exists (enforced):**
- `relationships.yaml` - defines couplings between code and docs
- `check_doc_coupling.py` - CI enforcement of code → doc updates
- `sync_governance.py` - ADR headers in source files

**What's missing:**
1. **CORE_SYSTEMS.md** - not coupled to any code, changes won't trigger updates
2. **No document hierarchy** - no enforced reading order (orientation → reference → detail)
3. **No Target ↔ Current links** - can't trace from aspirational to implemented
4. **No Gaps ↔ Plans links** - 142 gaps not formally linked to plans
5. **CONCEPTUAL_MODEL.yaml** - only soft-coupled, not verified

## Goals

1. Add CORE_SYSTEMS.md to coupling system so core file changes require update
2. Implement document hierarchy with enforced reading order
3. Add Target ↔ Current edges to relationships.yaml
4. Add Gaps → Plans cross-reference
5. Make CONCEPTUAL_MODEL.yaml coupling stricter

## Design

### 1. Document Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Orientation (New session? Read these first)    │
├─────────────────────────────────────────────────────────┤
│ CLAUDE.md (root)        → Process and workflow          │
│ CORE_SYSTEMS.md         → What subsystems exist         │
└───────────────────────────┬─────────────────────────────┘
                            │ references
                            ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 2: Reference (Look up when needed)                │
├─────────────────────────────────────────────────────────┤
│ CONCEPTUAL_MODEL.yaml   → Exact entities and fields     │
│ GLOSSARY.md             → Terminology definitions       │
│ Target architecture     → Where we're heading           │
└───────────────────────────┬─────────────────────────────┘
                            │ documented_by
                            ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Implementation (Detailed current state)        │
├─────────────────────────────────────────────────────────┤
│ docs/architecture/current/*.md                          │
│   ├── resources.md, agents.md, contracts.md ...         │
│   └── Each coupled to specific source files             │
└───────────────────────────┬─────────────────────────────┘
                            │ implements (bidirectional)
                            ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 4: Code (Source of truth)                         │
├─────────────────────────────────────────────────────────┤
│ src/**/*.py                                             │
└─────────────────────────────────────────────────────────┘
```

### 2. CORE_SYSTEMS.md Coupling

Add coupling for core infrastructure files:

```yaml
# relationships.yaml addition
- sources:
    - src/world/ledger.py
    - src/world/artifacts.py
    - src/world/contracts.py
    - src/world/kernel_interface.py
    - src/agents/agent.py
    - src/agents/workflow.py
    - src/simulation/runner.py
    - src/world/logger.py
  docs:
    - docs/architecture/current/CORE_SYSTEMS.md
  description: "Core systems overview - major changes need health status update"
  soft: true  # Warning only - not every change needs CORE_SYSTEMS update
```

### 3. Target ↔ Current Links

New edge type in relationships.yaml:

```yaml
# New section
target_current_links:
  - target: docs/architecture/target/04_resources.md
    current: docs/architecture/current/resources.md
    description: "Resource system vision vs implementation"

  - target: docs/architecture/target/03_agents.md
    current: docs/architecture/current/agents.md
    description: "Agent system vision vs implementation"

  # ... etc for each target doc
```

### 4. Gaps → Plans Cross-Reference

Add to `gaps/GAPS_SUMMARY.yaml`:

```yaml
# Extend existing gap entries with plan references
gaps:
  GAP-RES-001:
    title: "Rate limiting not enforced"
    plan: 01_rate_allocation.md
    status: closed

  GAP-AGT-042:
    title: "Agent memory not persistent"
    plan: null  # No plan yet
    status: open
```

### 5. Validation Script Enhancement

Extend `check_doc_coupling.py` to:
- Report orphan docs (docs not in any coupling)
- Report orphan targets (target docs with no current counterpart)
- Report gaps without plans
- Show document hierarchy when `--hierarchy` flag used

## Implementation

### Phase 1: CORE_SYSTEMS.md Coupling
1. Add coupling entry in relationships.yaml
2. Verify with `check_doc_coupling.py --suggest`

### Phase 2: Target ↔ Current Links
1. Add `target_current_links` section to relationships.yaml
2. Create mapping for all 8 target docs
3. (Optional) Add validation for target/current consistency

### Phase 3: Gaps → Plans Cross-Reference
1. Extend GAPS_SUMMARY.yaml with plan links
2. (Optional) Add script to validate gap-plan consistency

### Phase 4: Documentation
1. Update docs/CLAUDE.md with hierarchy explanation
2. Update root CLAUDE.md to explain reading order

## Files Changed

| File | Change |
|------|--------|
| `scripts/relationships.yaml` | Add CORE_SYSTEMS coupling, target-current links |
| `docs/architecture/gaps/GAPS_SUMMARY.yaml` | Add plan cross-references |
| `docs/CLAUDE.md` | Document hierarchy explanation |
| `CLAUDE.md` | Reading order guidance |

## Acceptance Criteria

- [ ] Changes to core files (`ledger.py`, `artifacts.py`, etc.) suggest CORE_SYSTEMS.md update
- [ ] Each target/*.md has explicit link to its current/*.md counterpart
- [ ] Gap summary includes plan references where plans exist
- [ ] `check_doc_coupling.py --hierarchy` shows document layers
- [ ] New session can trace: CORE_SYSTEMS → CONCEPTUAL_MODEL → current/*.md → src/

## Non-Goals

- Not adding new CI blocking checks (this adds structure, not hard gates)
- Not modifying existing doc content (only adding relationships)
- Not implementing graph visualization (future enhancement)

## Risks

- **Maintenance burden**: More relationships = more to keep updated
  - Mitigation: Make most links soft (warning-only)

- **Over-engineering**: Could make process feel heavy
  - Mitigation: Keep it advisory, not blocking

## Dependencies

- Plan #283 (completed) - CORE_SYSTEMS.md exists
