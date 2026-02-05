# Plan #304: Fix Stale Doc References (TD-013)

**Status:** ✅ Complete

## Problem

TD-013 identified stale documentation references. Most were already fixed by Plans #301 and #302. One remaining issue: unused `PrincipalConfig` import in `runner.py`.

## Changes

- Remove unused `PrincipalConfig` import from `src/simulation/runner.py`
- Update TECH_DEBT.md: mark TD-010, TD-013, TD-014 as resolved; update TD-011/TD-012 for partial completion
- Update CONCERNS.md: resolve "missing creator denies silently" concern (fixed in Plan #303)

## Files Changed

| File | Change |
|------|--------|
| `src/simulation/runner.py` | Remove unused import |
| `docs/architecture/TECH_DEBT.md` | Resolve TD-010/013/014, update TD-011/012 |
| `docs/CONCERNS.md` | Resolve permission checker concern |
