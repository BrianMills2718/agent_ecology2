# Plan #215: Unified Documentation Graph


**Status:** 📋 Planned
**Priority:** Medium
**Complexity:** Low-Medium
**Created:** 2026-01-25

## Problem

Documentation relationships are scattered across multiple config files:
- `governance.yaml` maps ADRs → code
- `doc_coupling.yaml` maps code → docs

This makes it impossible to trace the full chain: ADR → target architecture → current architecture → gaps → plans → code. Adding new relationship types requires new config files.

For LLM coders, this is particularly problematic: they must guess which docs are affected and rely on pre-commit hooks to catch misses. A queryable graph would let them know **before** implementing what's in scope.

## Solution

Unify all documentation relationships into a single `relationships.yaml` with a nodes/edges schema. Existing scripts read from this unified format (or via a thin adapter during migration).

### Schema

```yaml
# scripts/relationships.yaml
version: 1

# Node namespaces - glob patterns for doc categories
nodes:
  adr: docs/adr/*.md
  target: docs/architecture/target/*.md
  current: docs/architecture/current/*.md
  plans: docs/plans/*.md
  gaps: docs/architecture/gaps/*.yaml
  source: src/**/*.py

# Edge types
edge_types:
  governs:       # ADR governs code/docs (embeds headers)
  implements:    # Plan implements toward target
  documented_by: # Code documented by architecture doc (CI enforcement)
  vision_for:    # Target doc that current implements toward
  details:       # Plan linked to detailed gap analysis

# Relationships
edges:
  - from: adr/0001-everything-is-artifact
    to: [target/01_README, source/src/world/artifacts.py]
    type: governs

  - from: source/src/world/ledger.py
    to: current/resources
    type: documented_by
    coupling: strict  # CI fails if not updated together
```

### Benefits for LLM Coders

```bash
$ python scripts/validate_plan.py --plan 28
Checking Plan #28 against relationship graph...
- ADRs that govern affected files: [0001, 0003]
- Target docs to check consistency: [target/05_contracts.md]
- Current docs that need updating: [current/artifacts_executor.md]

⚠️  1 uncertainty found - discuss with user before implementing
```

## Plan

### Phase 1: Create unified schema and migration script
1. Define `relationships.yaml` schema
2. Write migration script to merge `governance.yaml` + `doc_coupling.yaml`
3. Validate merged output matches current behavior

### Phase 2: Update scripts to read new format
1. Add adapter layer to `sync_governance.py` to read from relationships.yaml
2. Add adapter layer to `check_doc_coupling.py` to read from relationships.yaml
3. Ensure backward compatibility during transition

### Phase 3: Add validation gate
1. Implement `--plan N` mode in validate_plan.py that queries the graph
2. Show governed ADRs, affected docs, and dependencies
3. Document usage in CLAUDE.md

### Phase 4: Cleanup
1. Deprecate old config files (keep as backup initially)
2. Update documentation
3. Add to meta-process templates

## Files Affected

- `scripts/relationships.yaml` (new)
- `scripts/migrate_to_relationships.py` (new)
- `scripts/sync_governance.py` (modify to read new format)
- `scripts/check_doc_coupling.py` (modify to read new format)
- `scripts/validate_plan.py` (add --plan N graph query)
- `CLAUDE.md` (document new workflow)
- `meta-process/patterns/09_documentation-graph.md` (update status)

## Acceptance Criteria

- [ ] `relationships.yaml` exists with all current relationships merged
- [ ] `sync_governance.py --check` works with new format
- [ ] `check_doc_coupling.py --strict` works with new format
- [ ] `validate_plan.py --plan N` shows governed ADRs and affected docs
- [ ] Pattern 09 status updated from PROPOSED to IMPLEMENTED
- [ ] Old config files deprecated (still present, marked as legacy)

## Test Requirements

```yaml
tests:
  unit:
    - test_relationships_schema_validation
    - test_migration_preserves_relationships
  integration:
    - test_governance_sync_with_unified_format
    - test_doc_coupling_with_unified_format
    - test_validate_plan_graph_query
```

## Risks

- **Migration errors**: Could miss relationships during merge → mitigate with validation
- **Learning curve**: Contributors need to understand edge types → mitigate with docs
- **Single large file**: Could become unwieldy → can split by namespace if needed

## References

- `meta-process/patterns/09_documentation-graph.md` (current proposed pattern)
- `scripts/governance.yaml` (current ADR governance)
- `scripts/doc_coupling.yaml` (current doc-code coupling)
