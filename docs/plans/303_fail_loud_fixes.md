# Plan #303: Fix 13 Silent Fallback Violations (TD-010)

**Status:** ✅ Complete

## Problem

13 places in `src/world/` use silent defaults that hide bugs instead of failing loud (Design Principle #1). Found during codebase audit documented in TD-010.

## Changes

### Category A: Replace unnecessary getattr with direct access (5+ fixes)
Artifact dataclass fields (`access_contract_id`, `created_by`, `kernel_protected`, `capabilities`) and WriteArtifactIntent fields (`has_standing`, `has_loop`) are always present. Removed defensive `getattr(obj, "field", fallback)` patterns.

- `permission_checker.py`: 2 getattr removals + bonus hasattr/getattr cleanup
- `action_executor.py`: 5 getattr removals across write/edit/mint paths
- `executor.py`: 1 getattr removal in capability injection

### Category B: Add logging to cost fallbacks (3 fixes)
Cost tracking must be observable. Added `logger.warning()` when "cost" field is missing from LLM usage or contract results.

- `executor.py`: LLM syscall cost fallback
- `mint_auction.py`: Scorer cost fallback
- `contracts.py`: Executable contract cost fallback + config timeout fallback

### Category C: Fix broad exception catches (4 fixes)
Replaced broad `except KeyError`/`except Exception` with explicit checks or added logging.

- `model_access.py`: 2 fixes - explicit `in` checks replace broad `except KeyError`
- `capabilities.py`: Added `logger.exception()` before returning error dict
- `contracts.py`: Added `logger.warning()` with exc_info before timeout fallback

### Category D: Remove init-order guard (1 fix)
- `world.py`: Removed `if hasattr(self, 'resource_manager')` guard - field is always initialized before use

## Files Changed

| File | Changes |
|------|---------|
| `src/world/permission_checker.py` | Replace 2 getattr + remove hasattr guard |
| `src/world/action_executor.py` | Replace 5 getattr with direct access |
| `src/world/executor.py` | Replace 1 getattr + add cost warning logging |
| `src/world/mint_auction.py` | Add cost warning logging |
| `src/world/contracts.py` | Add cost + config fallback logging |
| `src/world/model_access.py` | Replace 2 broad KeyError catches |
| `src/world/capabilities.py` | Add exception logging |
| `src/world/world.py` | Remove hasattr init guard |
| `tests/unit/test_fail_loud.py` | 8 new tests |

## Tests

8 new tests in `tests/unit/test_fail_loud.py`:
- 5 tests for model_access explicit checks
- 2 tests for cost fallback logging
- 1 test for capability exception logging
