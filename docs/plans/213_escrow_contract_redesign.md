# Plan #213: Escrow Contract-Based Redesign

**Status:** Complete
**Priority:** Medium
**Depends on:** Plan #210 (merged)
**Blocks:** Correct artifact trading semantics

## Implementation Summary (PR #736)

Implemented `transferable_freeware` contract and redesigned escrow to use `metadata["authorized_writer"]`:
- Added `TransferableFreewareContract` to genesis_contracts.py
- Updated `permission_checker.py` to pass `target_metadata` in context
- Added `KernelActions.update_artifact_metadata()` (kept transfer_ownership for now as it's used elsewhere)
- Rewrote `escrow.py` to use authorized_writer pattern:
  - `_deposit()` checks for `authorized_writer = escrow.id`
  - `_purchase()` sets `authorized_writer` to buyer
  - `_cancel()` returns `authorized_writer` to seller
- Updated all escrow tests (27 tests total) to use new pattern

## Problem

After Plan #210, `created_by` is immutable (ADR-0016 compliant). However:

1. **`transfer_ownership()` is tech debt** - Sets `metadata["controller"]` but genesis contracts (freeware, self_owned, private) ignore it
2. **Escrow is subtly broken** - Buyers get `metadata["controller"]` set but can't write under freeware because freeware checks `created_by`
3. **No replacement pattern exists** for "selling" artifacts

Per user feedback: **"Ownership" is not a kernel concept**. Contracts decide access.

## Current Broken Flow

```
1. Alice creates artifact (created_by="alice", access_contract="freeware")
2. Alice transfers to escrow → metadata["controller"]="genesis_escrow"
3. Bob purchases → metadata["controller"]="bob"
4. Bob tries to write → DENIED (freeware checks created_by="alice", not controller)
```

## Solution: Contract-Based Rights Transfer

Instead of mutating ownership, store "authorized writer" in artifact metadata and use a contract that checks it.

### New Contract: `transferable_freeware`

```python
class TransferableFreewareContract:
    """Like freeware, but write permission checks metadata['authorized_writer']."""

    def check_permission(self, caller, action, target, context):
        if action in (READ, INVOKE):
            return allowed("open access")

        if action in (WRITE, EDIT, DELETE):
            # Check metadata["authorized_writer"] instead of created_by
            authorized = context.get("target_metadata", {}).get("authorized_writer")
            if authorized is None:
                # Fall back to creator if no authorized_writer set
                authorized = context.get("target_created_by")

            if caller == authorized:
                return allowed("authorized writer")
            return denied("not authorized writer")
```

### New Escrow Flow

```
1. Alice creates artifact:
   - created_by="alice" (immutable)
   - metadata["authorized_writer"]="alice"
   - access_contract_id="genesis_contract_transferable_freeware"

2. Alice lists on escrow:
   - Escrow records listing (no ownership transfer needed)
   - Artifact stays with Alice until purchase

3. Bob purchases:
   - Escrow atomically:
     a. Transfers scrip from Bob to Alice
     b. Updates metadata["authorized_writer"]="bob"
   - Bob can now write (contract checks metadata)
```

### Required Changes

1. **Add `transferable_freeware` contract** to genesis_contracts.py
2. **Update permission_checker** to pass `target_metadata` in context
3. **Remove `transfer_ownership()`** from:
   - `ArtifactStore`
   - `KernelActions`
   - `GenesisLedger`
4. **Redesign escrow** to update `metadata["authorized_writer"]` instead
5. **Update handbooks** to document new pattern
6. **Migration**: Existing freeware artifacts work unchanged (fall back to `created_by`)

## Files Affected

- src/world/genesis_contracts.py (add transferable_freeware)
- src/world/permission_checker.py (pass target_metadata in context)
- src/world/artifacts.py (remove transfer_ownership)
- src/world/kernel_interface.py (remove transfer_ownership)
- src/world/genesis/ledger.py (remove transfer_ownership method)
- src/world/genesis/escrow.py (use metadata update instead)
- src/agents/_handbook/trading.md (update documentation)
- tests/ (update tests)

## Testing

- Verify freeware artifacts still work (backward compatible)
- Verify transferable_freeware allows authorized_writer to write
- Verify escrow purchase flow works with new pattern
- Verify `transfer_ownership()` is removed
- Verify created_by never changes

## Design Decisions

1. **New contract vs modify freeware?** New contract - keeps freeware simple and backward compatible
2. **Where does escrow update metadata?** Via `kernel_actions.write_artifact_metadata()` (new method)
3. **What if no authorized_writer?** Fall back to `created_by` (backward compat)

## References

- Plan #210: Fix ADR-0016 Violation (merged)
- ADR-0016: created_by Replaces owner_id
- ADR-0003: Contracts can do anything
