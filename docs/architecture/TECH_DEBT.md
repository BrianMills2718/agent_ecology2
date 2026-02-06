# Technical Debt & Architectural Improvements

Tracked architectural concerns and potential improvements. Items here are candidates for future plans.

**Last reviewed:** 2026-02-05

---

## Active Debt (Should Address)

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

## Resolved

| ID | Description | Resolved In | Date |
|----|-------------|-------------|------|
| TD-001 | World.py too large (extract MintAuction) | Extracted to `mint_auction.py` (Plan #44) | 2026-01-31 |
| TD-002 | Circular coupling World / RightsRegistry | RightsRegistry removed in Plan #299 | 2026-02-05 |
| TD-003 | Executor mixed responsibilities | PermissionChecker extracted (Plan #181), genesis dispatch removed (Plan #299) | 2026-02-05 |
| TD-004 | Inconsistent resource naming | Constants in `resources.py`, config/code fixed | 2026-01-31 |
| TD-009 | Contract permission depth limit not enforced | Implemented in `permission_checker.py` with configurable `max_contract_depth` | 2026-02-05 |
| TD-010 | Silent fallbacks violating Fail Loud (13 instances) | Plan #303: getattr removals, cost logging, exception narrowing | 2026-02-05 |
| TD-013 | Stale doc references (pool.py, worker.py, tick, unused import) | Plans #301, #304; doc refs fixed earlier, unused import removed | 2026-02-05 |
| TD-014 | Dashboard assess_health() type mismatch | Plan #302: fixed call pattern | 2026-02-05 |
| TD-008 | Genesis/kernel contract IDs hardcoded | Plan #305: `constants.py` with centralized IDs | 2026-02-05 |
| TD-011 | Missing observability in delegation/transfers | Plans #302, #305: EventLogger wired to ledger, delegation, artifact transfer | 2026-02-05 |
| TD-012 | Hardcoded economic parameters | Plans #302, #305: mint params + delegation max_history now in config | 2026-02-05 |

---

## How to Use This File

1. **Adding debt:** Add new item with TD-NNN ID, describe problem/impact/fix
2. **Addressing debt:** Create a plan in `docs/plans/`, reference TD-NNN
3. **Resolving debt:** Move to Resolved table with plan reference

This file is for architectural concerns. For bugs, use GitHub issues.
