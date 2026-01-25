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
| `artifact_store.py` | Artifact storage, queries, ownership |~500 |
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

- src/world/permission_checker.py (create)
- src/world/interface_validation.py (create)
- src/world/invoke_handler.py (create)
- src/world/event_lifecycle.py (create)
- src/world/action_dispatch.py (create)
- src/world/executor.py (modify)
- src/world/world.py (modify)
- src/world/CLAUDE.md (modify)
- docs/architecture/current/artifacts_executor.md (modify)
- scripts/doc_coupling.yaml (modify)
- tests/unit/test_contracts.py (modify)

## Progress

### Part 1: permission_checker.py (Complete)
- ✅ Created `permission_checker.py` (348 lines) with permission checking functions
- ✅ Updated `executor.py` to delegate to permission_checker module
- ✅ All 2458 tests pass
- ✅ Documentation updated

### Part 2: interface_validation.py (Complete)
- ✅ Created `interface_validation.py` (375 lines) with argument validation functions
- ✅ Updated `executor.py` to import from interface_validation module
- ✅ All 2458 tests pass
- ✅ Documentation updated

**Current state:**
- `executor.py`: 1331 lines (down from 1890)
- `permission_checker.py`: 348 lines (new)
- `interface_validation.py`: 375 lines (new)
- `invoke_handler.py`: 267 lines (new)

### Part 3: invoke_handler.py (Complete)
- ✅ Created `invoke_handler.py` (267 lines) with invoke closure factory
- ✅ Updated `executor.py` to use `create_invoke_function()` from module
- ✅ All 2531 tests pass
- ✅ Documentation updated

### Part 4: world.py split (Not started)
- [ ] Split world.py into event_lifecycle.py, action_dispatch.py

**Summary:** executor.py reduced from 1890 to 1331 lines (30% reduction) via 3 module extractions.
Total extracted: 990 lines across 3 new modules.

## Related

- CODE_REVIEW_2026_01_16.md (source of finding)
- `src/world/CLAUDE.md` (module documentation)
