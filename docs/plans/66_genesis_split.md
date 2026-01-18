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

## Verification

- pytest tests/ passes (1502 tests)
- python -c "from src.world.genesis import create_genesis_artifacts" works
