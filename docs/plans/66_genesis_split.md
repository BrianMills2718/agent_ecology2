# Plan #66: Split genesis.py into Package

**Status:** 🚧 In Progress
**Claimed by:** plan-66-genesis-split

## Problem

`src/world/genesis.py` grew to 2,961 lines with 7 genesis artifact classes. This makes the file hard to navigate and maintain.

## Solution

Split into a package `src/world/genesis/` with one file per artifact:
- `__init__.py` - Re-exports for backward compatibility
- `base.py` - GenesisArtifact, GenesisMethod, helpers
- `types.py` - Shared TypedDicts
- `ledger.py` - GenesisLedger
- `mint.py` - GenesisMint
- `rights_registry.py` - GenesisRightsRegistry
- `event_log.py` - GenesisEventLog
- `escrow.py` - GenesisEscrow
- `debt_contract.py` - GenesisDebtContract
- `store.py` - GenesisStore
- `factory.py` - create_genesis_artifacts()

## Related Work

Also includes:
- Session marker system for worktree protection (scripts/safe_worktree_remove.py)
- Exception-ok comments in executor.py (user code boundaries)
- Test fix for should_block_removal() signature

## Acceptance Criteria

- [x] All genesis artifacts in separate files
- [x] `from src.world.genesis import ...` still works
- [x] All tests pass
- [x] executor.py exception catches documented

## Files Affected

- src/world/genesis/__init__.py (create)
- src/world/genesis/base.py (create)
- src/world/genesis/types.py (create)
- src/world/genesis/ledger.py (create)
- src/world/genesis/mint.py (create)
- src/world/genesis/rights_registry.py (create)
- src/world/genesis/event_log.py (create)
- src/world/genesis/escrow.py (create)
- src/world/genesis/debt_contract.py (create)
- src/world/genesis/store.py (create)
- src/world/genesis/factory.py (create)
- src/world/genesis.py (delete)
- scripts/governance.yaml (modify)
- scripts/check_new_code_tests.py (modify)
- docs/architecture/current/genesis_artifacts.md (modify)
- docs/architecture/current/artifacts_executor.md (modify)
- tests/unit/test_worktree_session.py (modify)

## Verification

- pytest tests/ passes (1502 tests)
- python -c "from src.world.genesis import create_genesis_artifacts" works
