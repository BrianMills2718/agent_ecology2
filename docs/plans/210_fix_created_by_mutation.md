# Plan #210: Fix ADR-0016 Violation (created_by Mutation)

**Status:** Planned
**Priority:** High
**Blocks:** Correct ownership semantics, historical audit trail

## Problem

ADR-0016 states that `created_by` should be **immutable** - a historical fact recording who created an artifact. However, the current code violates this:

```python
# artifacts.py line 1059 - VIOLATES ADR-0016
def transfer_ownership(self, artifact_id, from_id, to_id):
    ...
    artifact.created_by = to_id  # WRONG: mutates immutable field
```

This causes:
1. **Lost history** - After transfer, we don't know who originally created the artifact
2. **Semantic confusion** - `created_by` doesn't mean "created by"
3. **Misleading APIs** - `get_owner()` returns `created_by`, conflating creator with owner

Per ADR-0016 and the glossary:
- `created_by` = immutable historical fact
- "Owner" = informal convention meaning "has complete rights" (determined by contracts)
- Rights are granted by contracts, not by kernel-level ownership

## Solution

### Phase 1: Stop Mutating created_by

Remove or modify `transfer_ownership()` to not mutate `created_by`:

```python
def transfer_ownership(self, artifact_id, from_id, to_id):
    """Transfer ownership via contract update, not created_by mutation.

    DEPRECATED: Use contract-based rights transfer instead.
    This method is kept for escrow compatibility but should not
    mutate created_by.
    """
    # Option A: Remove entirely, force contract-based transfer
    # Option B: Update artifact's access_contract_id to grant rights to new owner
    # Option C: Store "controlled_by" in metadata
```

### Phase 2: Fix get_owner()

Either:
- **Remove** `get_owner()` (ownership is contract-determined, not queryable)
- **Rename** to `get_creator()` (returns created_by, clearly named)
- **Change** to query contract for who has full rights (expensive, possibly undecidable)

Recommendation: Rename to `get_creator()`.

### Phase 3: Fix _index_by_owner

The index named `_index_by_owner` actually tracks `created_by`:

```python
self._index_by_owner[artifact.created_by].add(artifact_id)
```

Options:
- Rename to `_index_by_creator`
- Or accept that "owner" in index name means "original creator" (confusing)

Recommendation: Rename to `_index_by_creator`.

### Phase 4: Update Escrow

Genesis escrow uses `transfer_ownership()`. Update to:
- Grant rights via contract instead of mutating created_by
- Or store "controlled_by" in artifact metadata that escrow manages

### Phase 5: Update Queries

Methods like `list_by_owner()`, `get_artifacts_by_owner()` need review:
- Are they querying for creator or current rights holder?
- Rename or document clearly

## Design Decision: How to Track "Current Controller"

Three options:

| Option | Mechanism | Pros | Cons |
|--------|-----------|------|------|
| A | Contract-only | Pure, no kernel state | Can't easily query "who controls X" |
| B | `metadata["controller"]` | Explicit, queryable | Another field to maintain |
| C | `controlled_by` field | First-class support | Kernel complexity |

Recommendation: **Option A (contract-only)** with convention that contracts store controller in metadata if needed. Keeps kernel simple.

## Files Affected

| File | Change |
|------|--------|
| `src/world/artifacts.py` | Fix transfer_ownership, rename methods/indexes |
| `src/world/kernel_interface.py` | Update transfer_ownership wrapper |
| `src/world/genesis/ledger.py` | Update transfer_ownership method |
| `src/world/genesis/escrow.py` | Update to use contract-based transfer |
| `tests/` | Update tests for new semantics |

## Testing

- Verify `created_by` never changes after creation
- Verify escrow still works with contract-based transfer
- Verify ownership queries return expected results
- Verify historical audit trail preserved

## Migration

Existing artifacts have `created_by` that may have been mutated. Options:
1. **Accept as-is** - Can't recover original creator, document as known issue
2. **Add `original_creator`** - Copy current created_by before fix, add new field
3. **No migration** - Only affects new transfers going forward

Recommendation: Option 3 (no migration). Accept that historical data may have lost original creator info.

## References

- ADR-0016: created_by Replaces owner_id
- GLOSSARY.md: Creator vs Owner section
- Plan #100: Contract System Overhaul
