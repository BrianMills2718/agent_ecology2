# ADR-0005: Unified Documentation Graph

**Status:** Proposed
**Date:** 2026-01-12
**Certainty:** 75%

## Context

Documentation relationships are scattered across multiple systems:

| Current File | Maps | Purpose |
|--------------|------|---------|
| `governance.yaml` | ADR → code | Embed GOVERNANCE headers in source |
| `doc_coupling.yaml` | code → docs, docs → docs | CI enforcement |
| Markdown headers | target → current | Manual cross-references |
| None | ADR → target, gaps → plans | Missing entirely |

Problems:
- No single source of truth for "how do documents relate?"
- Can't trace ADR → target architecture → current → gaps → plans → code
- Two gap systems (142 detailed, 34 plans) with no formal cross-reference
- Adding new relationship types requires new config files

## Decision

**Merge all documentation relationships into a single `relationships.yaml`.**

```yaml
# scripts/relationships.yaml
version: 1

# Node namespaces - define document categories with glob patterns
nodes:
  adr: docs/adr/*.md
  target: docs/architecture/target/*.md
  current: docs/architecture/current/*.md
  plans: docs/plans/*.md
  gaps: docs/architecture/gaps/*.yaml
  source: src/**/*.py

# Edge types and their semantics
edge_types:
  governs:
    description: "ADR that governs implementation"
    actions: [embed_header]

  implements:
    description: "Plan that implements toward target"
    actions: [validate_links]

  documented_by:
    description: "Code documented by architecture doc"
    actions: [ci_enforce]

  vision_for:
    description: "Target doc that current doc implements toward"
    actions: [validate_links]

  details:
    description: "Plan linked to detailed gap analysis"
    actions: [validate_links]

# Actual edges (relationships)
edges:
  # ADR → multiple targets (code, target docs, current docs)
  - from: adr/0001-everything-is-artifact
    to: [target/01_README, current/artifacts_executor, source/src/world/artifacts.py]
    type: governs
    context: "Artifacts are the universal interface"

  - from: adr/0002-no-compute-debt
    to: [target/04_resources, current/resources, source/src/world/ledger.py]
    type: governs

  # Plans → what they implement
  - from: plans/01_rate_allocation
    to: [current/resources, source/src/world/rate_tracker.py]
    type: implements

  - from: plans/02_continuous_execution
    to: [current/execution_model, source/src/simulation/runner.py]
    type: implements

  # Code → docs (CI enforcement)
  - from: source/src/world/ledger.py
    to: current/resources
    type: documented_by
    coupling: strict  # CI fails if not updated together

  - from: source/src/world/artifacts.py
    to: current/artifacts_executor
    type: documented_by
    coupling: strict

  # Target → Current
  - from: target/04_resources
    to: current/resources
    type: vision_for

  # Plans → Detailed gaps (cross-reference the two gap systems)
  - from: plans/01_rate_allocation
    to: gaps/ws3_resources
    type: details
    gap_ids: [GAP-RES-001, GAP-RES-002]
```

**Scripts read the same config:**
- `sync_governance.py` → processes edges with `type: governs` and source targets
- `check_doc_coupling.py` → processes edges with `coupling: strict|soft`
- `validate_plan.py` (new) → queries graph before implementation to surface:
  - Which ADRs govern affected files
  - Which target docs to check for consistency
  - Which current docs need updating
  - Any low-certainty items in DESIGN_CLARIFICATIONS.md

**Migration:**
1. Create `relationships.yaml` with all existing relationships from both configs
2. Update `sync_governance.py` to read new format
3. Update `check_doc_coupling.py` to read new format
4. Deprecate `governance.yaml` and `doc_coupling.yaml`
5. Add `validate_plan.py` for pre-implementation checks

## Consequences

### Positive

- **Single source of truth** - One file defines all doc relationships
- **Traceable decisions** - Can follow ADR → target → current → gaps → plans → code
- **Extensible** - Add new edge types without new config files
- **Enables validation gate** - `validate_plan.py` can query graph before implementing
- **Cleaner schema** - Node namespaces reduce path redundancy
- **Gap linkage** - Formally connects 142-gap analysis to 34-plan tracking

### Negative

- **Migration effort** - Must merge two configs, update two scripts
- **Larger config file** - Single file grows as relationships added
- **Learning curve** - Contributors must understand edge types

### Neutral

- Existing CI checks continue working (scripts read new format)
- GOVERNANCE headers in code unchanged (just generated from new config)
- Could add graph visualization tooling later (not required)

## Related

- ADR-0001: Everything is an artifact (first ADR to be linked)
- Gap #33: ADR Governance System (implemented governance.yaml)
- `docs/meta/doc-code-coupling.md` - Pattern documentation
- `docs/meta/adr-governance.md` - Pattern documentation
