# Plan 247: Remove Legacy Tick-Based Resource Mode

**Status:** ✅ Complete
**Priority:** High
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** The codebase has dual resource modes controlled by `rate_limiting.enabled`: legacy tick-based (`False`) and RateTracker rolling-window (`True`). This causes conditional branching in ~8 Ledger methods, World, and Runner. The legacy mode is already dead in practice — `config.yaml` enables rate limiting, `run.py` force-enables it, and `advance_tick()` no longer resets resources (Plan #102).

**Target:** RateTracker is the only resource mode. Remove `use_rate_tracker` flag and all conditional branching. Closes gaps GAP-RES-018, RES-019, RES-028, RES-029, RES-030, RES-033.

---

## References Reviewed

- `src/config_schema.py:978-996` - RateLimitingConfig with `enabled=False` default
- `src/world/ledger.py:100-178, 470-755` - Dual-mode Ledger methods
- `src/world/world.py:155-216` - `use_rate_tracker` field and initialization
- `src/simulation/runner.py:175-188, 1024-1029, 1242-1246` - Runner mode branching
- `run.py:374-381` - Force-enable rate_limiting for autonomous mode
- `tests/integration/test_runner.py:459-626` - TestResourceResetBehavior dual-mode tests
- `tests/unit/test_ledger.py:440-500` - Dual-mode ledger tests

---

## Files Affected

- `src/config_schema.py` (modify)
- `src/world/ledger.py` (modify)
- `src/world/world.py` (modify)
- `src/simulation/runner.py` (modify)
- `run.py` (modify)
- `tests/integration/test_runner.py` (modify)
- `tests/unit/test_ledger.py` (modify)
- `tests/unit/test_runner_output.py` (modify)
- `docs/architecture/current/resources.md` (modify)

---

## Plan

### Steps

1. Change `RateLimitingConfig.enabled` default to `True` in config_schema.py
2. Remove `use_rate_tracker` field and branching from ledger.py (always use RateTracker)
3. Remove `use_rate_tracker` field from world.py
4. Simplify runner.py (remove fallback creation, clean display logic)
5. Remove force-enable in run.py
6. Update tests to reflect rate-only mode
7. Update docs/architecture/current/resources.md

---

## Required Tests

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_rate_tracker.py` | RateTracker internals unchanged |
| `tests/integration/test_escrow.py` | Uses rate_limiting configs |
| `tests/e2e/test_smoke.py` | Full simulation smoke |
| `make check` | All checks pass |

---

## Verification

- [ ] `make test` passes
- [ ] `make mypy` passes
- [ ] `make lint` passes
- [ ] `make run DURATION=5 AGENTS=1` works
