# Plan #181: Split Large Core Files

**Status:** 🚧 In Progress
**Priority:** Low
**Effort:** High
**Risk:** High (core simulation code)

## Problem

Two core files exceed maintainability thresholds identified in CODE_REVIEW_2026_01_16:

| File | Lines | Issue |
|------|-------|-------|
| `src/world/world.py` | 2008 | Central state manager, too many responsibilities |
| `src/world/executor.py` | 1765 | Code execution + invoke handling mixed |

These files are hard to navigate, test in isolation, and modify safely.

## Proposed Split

### world.py (2008 lines → ~4 files)

| New File | Responsibility | Approximate Lines |
|----------|---------------|-------------------|
| `world.py` | World class, state coordination | ~600 |
| `event_lifecycle.py` | Event creation, lifecycle management | ~400 |
| `artifact_store.py` | Artifact storage, queries, ownership | ~500 |
| `action_dispatch.py` | Action routing, intent processing | ~500 |

### executor.py (1765 lines → ~3 files)

| New File | Responsibility | Approximate Lines |
|----------|---------------|-------------------|
| `executor.py` | Core execution, sandboxing | ~600 |
| `invoke_handler.py` | Invoke action logic, method dispatch | ~600 |
| `permission_checker.py` | Permission checking, contract calls | ~500 |

## Acceptance Criteria

- [ ] All 2137+ tests pass after refactoring
- [ ] No file exceeds 800 lines
- [ ] Each file has single responsibility
- [ ] Import cycles avoided (dependency graph is acyclic)
- [ ] `docs/architecture/current/` updated to reflect new structure

## Implementation Notes

1. **Extract, don't rewrite** - Move code with minimal changes
2. **Preserve interfaces** - External imports should not change
3. **Test after each extraction** - Don't batch multiple extractions
4. **Update doc-coupling** - Add new files to `scripts/doc_coupling.yaml`

## Why Low Priority

- Current structure works (tests pass)
- Refactoring is risky without immediate benefit
- Other plans have clearer value

## Files Affected

- src/world/world.py (modify) - reduce size by extracting action execution
- src/world/action_executor.py (create) - action execution logic extracted from world.py
- src/world/executor.py (modify) - may extract permission checking
- src/world/CLAUDE.md (modify) - update module documentation
- scripts/doc_coupling.yaml (modify) - add new file mappings
- docs/architecture/current/artifacts_executor.md (modify) - update architecture docs

## Related

- CODE_REVIEW_2026_01_16.md (source of finding)
- `src/world/CLAUDE.md` (module documentation)
