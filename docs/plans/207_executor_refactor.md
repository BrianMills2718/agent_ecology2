# Plan #207: Executor Method Refactoring

**Status:** 📋 Deferred
**Priority:** Low
**Effort:** Medium
**Risk:** High (core simulation code)

## Problem

After Plan #181's extraction work, `executor.py` is still at 1331 lines (target was 800).
The remaining size is due to duplicated logic across three execute methods that cannot
be extracted without refactoring.

## Current State (Post Plan #181)

| File | Lines | Target |
|------|-------|--------|
| `executor.py` | 1331 | ~800 |
| `world.py` | 1127 | ~800 |

## Duplication Analysis

The three execute methods share ~150 lines of similar setup code:

| Method | Lines | Purpose |
|--------|-------|---------|
| `execute()` | ~160 | Basic execution |
| `execute_with_wallet()` | ~180 | Execution with pay/get_balance |
| `execute_with_invoke()` | ~450 | Full context with invoke, kernel interfaces |

**Shared patterns:**
1. Code validation and compilation (~20 lines each)
2. Building controlled_builtins with import function (~15 lines each)
3. Building controlled_globals with preloaded modules (~15 lines each)
4. Action class definition (~90 lines in two places)
5. Timeout context and resource measurement (~30 lines each)
6. Result handling and JSON serialization (~20 lines each)

## Proposed Refactoring

### New Helper Methods

```python
def _build_execution_globals(
    self,
    include_wallet: bool = False,
    include_invoke: bool = False,
    wallet_context: WalletContext | None = None,
    invoke_context: InvokeContext | None = None,
) -> dict[str, Any]:
    """Build controlled globals with appropriate context."""

def _run_with_measurement(
    self,
    run_func: Callable,
    args: list[Any],
) -> ExecutionResult:
    """Execute run() with timeout protection and resource measurement."""

def _create_action_class(
    self,
    controlled_globals: dict[str, Any],
    artifact_store: ArtifactStore | None = None,
) -> type:
    """Create Action class with appropriate capabilities."""
```

### Estimated Reduction

| Change | Lines Saved |
|--------|-------------|
| Unified globals building | ~60 |
| Shared Action class | ~90 |
| Common measurement logic | ~60 |
| Shared result handling | ~40 |
| **Total** | **~250** |

Post-refactor estimate: ~1080 lines (still above 800 but closer)

## Why Deferred

1. **High risk** - Core simulation code; all agents depend on this
2. **Low priority** - Current code works, tests pass
3. **Diminishing returns** - Plan #181 achieved 30% reduction safely
4. **Subtle bugs** - Shared logic refactoring risks edge cases
5. **No active pain** - File size isn't causing problems

## Acceptance Criteria (If Implemented)

- [ ] All 2500+ tests pass
- [ ] No behavioral changes (same results for same inputs)
- [ ] executor.py under 1100 lines
- [ ] Integration tests for invoke chains pass
- [ ] Performance benchmarks unchanged

## Implementation Notes

1. **Create backup branch** before starting
2. **Incremental changes** - refactor one helper at a time
3. **Test after each step** - don't batch changes
4. **Extra integration test scrutiny** - especially invoke chains
5. **Consider property-based testing** for execute methods

## Prerequisites

- Plan #181 complete (extraction done)
- Comprehensive integration test coverage for invoke
- Time for careful, incremental work

## Files Affected

- src/world/executor.py (modify)

## Related

- Plan #181: Split Large Core Files (extraction phase complete)
- `src/world/executor.py` - target file
