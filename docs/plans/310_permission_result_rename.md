# Plan #310: PermissionResult Field Rename and Expansion

**Status:** ✅ Complete

**Parent:** Plan #309 (Target Contracts Architecture Rewrite)

## Summary

Rename ambiguous PermissionResult fields to clarify scrip vs real resource concerns, and add fields needed for the target contract architecture.

## Changes

### Field Renames (clean break, no backward compatibility)

| Old Name | New Name | Purpose |
|----------|----------|---------|
| `cost` | `scrip_cost` | Clarifies this is scrip (artificial currency), not real $ |
| `payer` | `scrip_payer` | Who pays scrip (None = caller) |
| `recipient` | `scrip_recipient` | Who receives scrip payment |

### New Fields

| Field | Purpose |
|-------|---------|
| `resource_payer` | Who pays real resource costs (LLM $, disk, compute). None = caller. |
| `state_updates` | Contract state changes, applied atomically by kernel. Follow-up plan needed for storage/passing mechanism. |

## Files Modified

| File | Change |
|------|--------|
| `src/world/contracts.py` | PermissionResult definition, ExecutableContract dict mapping |
| `src/world/kernel_contracts.py` | 7 return statements |
| `src/world/invoke_handler.py` | 3 field reads |
| `src/world/action_executor.py` | 1 field read |
| `docs/architecture/current/contracts.md` | PermissionResult docs, examples |
| `tests/unit/test_contracts.py` | ~15 assertion updates |
| `tests/unit/test_permission_fixes.py` | Constructor args |
| `tests/unit/test_kernel_contracts.py` | Assertion updates |
| `tests/unit/test_fail_loud.py` | Warning message check |
| `tests/integration/test_contracts_acceptance.py` | Contract code strings, assertions |

## Follow-ups (not in scope)

- Contract state storage/passing mechanism (`state_updates` field added but unused)
- Resource payer authorization (`resource_payer` field added but kernel doesn't validate)
- Scrip/ledger migration from kernel to artifact level
