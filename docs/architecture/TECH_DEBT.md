# Technical Debt & Architectural Improvements

Tracked architectural concerns and potential improvements. Items here are candidates for future plans.

**Last reviewed:** 2026-02-05

---

## Active Debt (Should Address)

### TD-010: Silent fallbacks violating Fail Loud (13 instances)

**Observed:** 2026-02-05 (codebase audit)

**Problem:** 13 places in `src/world/` use silent defaults that hide bugs instead of failing loud:

| File | Line | Pattern | Risk |
|------|------|---------|------|
| `model_access.py` | 123, 173 | `except KeyError: return False` | Conflates "missing agent" with "insufficient quota" |
| `capabilities.py` | 195 | `except Exception` (no logging) | Swallows programming bugs in handlers |
| `executor.py` | 194 | `.get("cost", estimated_cost)` | Hides provider failing to report actual cost |
| `mint_auction.py` | 381 | `.get("cost", 0.0)` | Scorer cost silently treated as free |
| `contracts.py` | 573 | `.get("cost", 0)` | Buggy contract becomes free |
| `contracts.py` | 348 | `except Exception: return 5` | Config failure returns magic timeout |
| `permission_checker.py` | 150 | `getattr(..., "freeware")` | Missing contract field defaults to open access |
| `permission_checker.py` | 347 | `getattr(..., None)` | Missing creator field silently denies |
| `action_executor.py` | 262 | `getattr(..., False)` | Corrupted artifact loses `kernel_protected` |
| `action_executor.py` | 366-373 | `getattr(..., False)` | Missing standing/loop silently skipped |
| `action_executor.py` | 1207 | `getattr(..., None) or []` | Double fallback hides corruption |
| `world.py` | 298 | `if hasattr(self, 'resource_manager')` | Silently skips principal creation |

**Impact:** Violates design principle #1 (Fail Loud). Bugs in contract cost, artifact corruption, and missing fields are all silently swallowed instead of surfaced.

**Recommended fix:** Replace each silent default with an explicit check that raises on unexpected state.

**Effort:** Medium (many small changes, each needs a test) | **Risk:** Low

---

### TD-011: Missing observability in ledger and delegation

**Observed:** 2026-02-05 (codebase audit)

**Problem:** The two most important state-mutating modules have no event logging:

1. **`ledger.py`** - Source of truth for all balances. Zero logging of credits, debits, or transfers.
2. **`delegation.py`** - Grant/revoke operations mutate artifacts without event logging.
3. **`artifacts.py:transfer_ownership()`** - Metadata mutations not logged.

**Impact:** Violates design principle #4 (Maximum Observability). Cannot trace economic activity.

**Recommended fix:** Add event logging to ledger mutation methods and delegation grant/revoke.

**Effort:** Low-Medium | **Risk:** Very Low (additive logging)

---

### TD-012: Hardcoded economic parameters

**Observed:** 2026-02-05 (codebase audit)

**Problem:** Core economic parameters are hardcoded instead of in `config.yaml`:

| File | Line | Value | Should Be Config |
|------|------|-------|------------------|
| `mint_auction.py` | 91-93 | `delay=30.0, window=60.0, period=120.0` | `scrip.mint.auction.*` |
| `mint_auction.py` | 361 | `mint_ratio = 10` | `scrip.mint.ratio` |
| `delegation.py` | 73 | `_MAX_ENTRIES_PER_PAIR = 1000` | `delegation.max_history` |

**Impact:** Cannot tune economic parameters without code changes. Mint auction timing and ratio determine how fast scrip enters the economy.

**Recommended fix:** Add config entries, read them in `__init__()`. Comment at line 90 even says "could be made configurable".

**Effort:** Low | **Risk:** Very Low

---

### TD-013: Stale documentation references (post Plan #299/#301)

**Observed:** 2026-02-05 (codebase audit)

**Problem:** Several docs reference deleted files or use removed terminology:

| File | Line | Issue |
|------|------|-------|
| `CORE_SYSTEMS.md` | 200 | References deleted `pool.py` |
| `CORE_SYSTEMS.md` | 199 | Says `agent_loop.py` is "legacy, unused" (it IS used) |
| `resources.md` | 355, 377 | Code examples from deleted `worker.py` |
| `config.yaml` | 215, 224, 571 | "tick" terminology (should be "events") |
| `config_schema.py` | 551, 569 | Debt contract descriptions use "due_tick" |
| `runner.py` | 25 | Unused `PrincipalConfig` import |

**Recommended fix:** Update docs and remove stale import. Small targeted edits.

**Effort:** Low | **Risk:** Very Low

---

### TD-014: Dashboard assess_health() type mismatch

**Observed:** 2026-02-05 (codebase audit)

**Problem:** `src/dashboard/server.py:184` calls `assess_health(self.parser.state, self.thresholds)` but `assess_health()` expects `EcosystemKPIs`, not `SimulationState`. The correct pattern is at line 938 in the same file.

**Impact:** Runtime crash. Already flagged by mypy.

**Recommended fix:** Match the correct call pattern at line 938.

**Effort:** Very Low | **Risk:** Very Low

---

### TD-005: Config flow is implicit

**Problem:** Components receive full config dict, extract what they need. No clear contract about what each component needs.

**Impact:** Hard to know what config a component uses, easy to break with config changes.

**Recommended fix:** Explicit config dataclasses per component.

**Effort:** High | **Risk:** Low (additive change)

---

## Potential Improvements (Nice to Have)

### TD-006: No explicit Kernel interface

**Problem:** "Kernel" is a design concept in docs but not in code. `World` implements kernel primitives but there's no explicit interface.

**Recommended fix:** Create `Kernel` protocol that World implements.

**Effort:** Low | **Risk:** Low

---

### TD-007: Missing `__all__` exports

**Problem:** Most world modules export everything implicitly. No clear public API.

**Recommended fix:** Add explicit `__all__` lists to all modules.

**Effort:** Low | **Risk:** Very Low

---

### TD-008: Genesis artifact IDs are hardcoded

**Problem:** IDs like `"genesis_ledger"`, `"genesis_mint"` are string literals scattered throughout.

**Recommended fix:** Constants in one place (e.g., `src/world/constants.py`).

**Effort:** Low | **Risk:** Very Low

---

## Resolved

| ID | Description | Resolved In | Date |
|----|-------------|-------------|------|
| TD-001 | World.py too large (extract MintAuction) | Extracted to `mint_auction.py` (Plan #44) | 2026-01-31 |
| TD-002 | Circular coupling World / RightsRegistry | RightsRegistry removed in Plan #299 | 2026-02-05 |
| TD-003 | Executor mixed responsibilities | PermissionChecker extracted (Plan #181), genesis dispatch removed (Plan #299) | 2026-02-05 |
| TD-004 | Inconsistent resource naming | Constants in `resources.py`, config/code fixed | 2026-01-31 |
| TD-009 | Contract permission depth limit not enforced | Implemented in `permission_checker.py` with configurable `max_contract_depth` | 2026-02-05 |

---

## How to Use This File

1. **Adding debt:** Add new item with TD-NNN ID, describe problem/impact/fix
2. **Addressing debt:** Create a plan in `docs/plans/`, reference TD-NNN
3. **Resolving debt:** Move to Resolved table with plan reference

This file is for architectural concerns. For bugs, use GitHub issues.
