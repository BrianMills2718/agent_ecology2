# Plan #305: Final Tech Debt Cleanup (TD-008, TD-011, TD-012)

**Status:** ✅ Complete

## Summary

Resolves the remaining low-effort tech debt items from the codebase audit:

- **TD-011**: Add event logging to `delegation.py` grant/revoke and `artifacts.py` transfer_ownership
- **TD-012**: Make `delegation.py` `_MAX_ENTRIES_PER_PAIR` configurable via `delegation.max_history`
- **TD-008**: Centralize kernel contract ID string literals into `src/world/constants.py`

## Changes

| File | Change |
|------|--------|
| `src/world/constants.py` | New: centralized kernel contract IDs and SYSTEM_OWNER |
| `src/world/delegation.py` | Event logging on grant/revoke, configurable max_entries |
| `src/world/artifacts.py` | Logging on transfer_ownership, use contract constants |
| `src/world/kernel_contracts.py` | Use contract ID constants from constants.py |
| `src/world/permission_checker.py` | Use KERNEL_CONTRACT_FREEWARE constant |
| `src/world/world.py` | Wire EventLogger to DelegationManager |
| `src/world/__init__.py` | Re-export SYSTEM_OWNER from constants.py |
| `config/config.yaml` | Add `delegation.max_history` setting |
| `src/config_schema.py` | Add DelegationConfig model |
| `docs/architecture/TECH_DEBT.md` | Move TD-008/011/012 to Resolved |

## Decisions

- **TD-006 (Kernel protocol) skipped**: World has ~40 public methods. A protocol adds code without clear benefit given "Real Tests, Not Mocks" principle.
- **TD-007 (__all__ exports) skipped**: 6 of 32 files already have __all__, and `__init__.py` serves as the package's public API gateway. Adding to 26 more files is churn for marginal value.
- **Genesis artifact IDs not centralized**: They're config defaults in config_schema.py, not scattered literals. Only kernel contract IDs were truly scattered across src/world/.
