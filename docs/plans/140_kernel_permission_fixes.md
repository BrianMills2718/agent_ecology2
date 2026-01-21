# Plan 140: Kernel Permission Fixes

**Status:** 📋 In Progress
**Priority:** High
**Blocked By:** None
**Blocks:** Custom contracts, proper access control

---

## Overview

The kernel violates ADR-0016 by checking `created_by` for permissions in several places. Per ADR-0016, `created_by` is just metadata (an immutable historical fact) - the kernel should pass it to contracts but NOT interpret it for access control.

Additionally, `PermissionResult` only specifies cost amount but not WHO pays. Per ADR-0003, contracts should be able to specify the payer.

---

## Problems Found

### 1. Kernel Checks `created_by` for Permissions

| Location | Violation |
|----------|-----------|
| `world.py:1573` | Delete checks `created_by != requester_id` |
| `kernel_interface.py:129` | Read checks `created_by != caller_id` |
| `kernel_interface.py:318` | Write checks `created_by != caller_id` |
| `kernel_interface.py:552` | Another kernel check |

These should all go through contracts via `_check_permission()`.

### 2. `created_by` is Mutable (Bug)

`artifacts.py:696` mutates `created_by`:
```python
artifact.created_by = to_id  # WRONG - should be immutable
```

Per ADR-0016, `created_by` is an immutable historical fact. "Ownership" transfer should be handled by contracts tracking owner in artifact metadata, not by mutating kernel fields.

### 3. Delete Bypasses Contracts

`_execute_delete()` calls `delete_artifact()` which has hardcoded owner check instead of going through `_check_permission("delete", ...)`.

### 4. Contracts Can't Specify Payer

`PermissionResult` has `cost: int` but no `payer: str`. The system hardcodes "caller pays" instead of letting contracts decide.

### 5. Terminology: "compute" = "llm_tokens"

The ledger has backward-compat methods that conflate "compute" with "llm_tokens". Per glossary:
- `cpu_rate` = CPU-seconds (renewable)
- `llm_rate` = LLM tokens/min (renewable)
- `llm_budget` = dollars (depletable)

"Compute" should mean CPU, not LLM tokens.

---

## Changes Required

### 1. Add `payer` to PermissionResult

```python
@dataclass
class PermissionResult:
    allowed: bool
    reason: str
    cost: int = 0
    payer: str | None = None  # If None, caller pays. Otherwise, charge this principal.
    conditions: Optional[dict[str, object]] = None
```

### 2. Update Executor to Use Payer

In `executor.py`, when charging for an action:
```python
# OLD
if total_cost > 0 and not ledger.can_afford_scrip(caller_id, total_cost):

# NEW
payer = perm_result.payer or caller_id
if total_cost > 0 and not ledger.can_afford_scrip(payer, total_cost):
```

### 3. Route Delete Through Contracts

In `world.py`, change `_execute_delete()`:
```python
# OLD - hardcoded check
result = self.delete_artifact(intent.artifact_id, intent.principal_id)

# NEW - through contracts
executor = get_executor()
allowed, reason = executor._check_permission(intent.principal_id, "delete", artifact)
if not allowed:
    return ActionResult(success=False, message=reason, ...)
# Then perform delete
```

### 4. Remove Kernel Permission Checks

Remove `created_by` checks from:
- `kernel_interface.py:129` (read check)
- `kernel_interface.py:318` (write check)
- `kernel_interface.py:552` (other check)
- `world.py:1573` (delete check - replaced by contract route)

These should all go through `_check_permission()` instead.

### 5. Make `created_by` Immutable (DEFERRED)

Per ADR-0016, `created_by` should be immutable and ownership should be tracked in artifact metadata (not by mutating kernel fields). However, the escrow system currently uses `transfer_ownership()` which mutates `created_by`.

**Proper fix requires:**
1. Add `controlled_by` or similar field for current controller (mutable)
2. Keep `created_by` as immutable historical fact
3. Update escrow and ledger contracts to use new field
4. Deprecate `transfer_ownership()` mutation

**Deferred to separate plan** - this is a larger refactor that touches escrow, ledger, and artifact model.

### 6. Fix Terminology

Rename backward-compat methods in `ledger.py`:
- `get_compute()` -> deprecation warning, calls `get_resource("llm_tokens")`
- `spend_compute()` -> deprecation warning
- etc.

Or remove them entirely if no longer used.

---

## Files Affected

- src/world/contracts.py (modify) - Add `payer` to PermissionResult
- src/world/executor.py (modify) - Use `payer` when charging
- src/world/world.py (modify) - Route delete through contracts
- src/world/kernel_interface.py (modify) - Remove `created_by` checks
- src/world/artifacts.py (modify) - Remove/fix `transfer_ownership()`
- src/world/ledger.py (modify) - Fix compute terminology
- src/world/genesis_contracts.py (modify) - Update to return `payer` if needed
- tests/ (modify) - Update tests

---

## Required Tests

| Test | Description |
|------|-------------|
| `test_delete_via_contract` | Delete permission goes through contract |
| `test_payer_from_contract` | Contract can specify alternate payer |
| `test_created_by_immutable` | Verify `created_by` cannot be changed |
| `test_no_kernel_owner_bypass` | Kernel doesn't check `created_by` for permissions |

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| No `created_by` permission checks in kernel | Grep returns 0 matches outside contracts |
| Delete routes through contracts | `_execute_delete` calls `_check_permission` |
| `payer` field exists | PermissionResult has optional payer field |
| Executor uses payer | Charges specified payer, not hardcoded caller |
| All tests pass | `make test` green |

---

## ADRs Applied

- ADR-0003: Contracts can do anything (contracts specify payer)
- ADR-0016: created_by replaces owner_id (created_by is immutable metadata)

---

## Deferred

- Full removal of backward-compat "compute" methods (can deprecate now, remove later)
- Complex cost splitting (single payer is sufficient for v1)
