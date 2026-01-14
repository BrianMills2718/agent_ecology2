# Gap 18: Dangling Reference Handling

**Status:** ✅ Complete

**Verified:** 2026-01-14T02:49:40Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-14T02:49:40Z
tests:
  unit: 1174 passed, 1 skipped in 13.82s
  e2e_smoke: PASSED (1.98s)
  doc_coupling: passed
commit: 5b149ce
```
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** No specification for what happens when referenced artifacts are deleted. Artifacts cannot be deleted at all currently.

**Target:** Soft delete with tombstones - clear semantics for artifact deletion with references.

---

## Problem Statement

Agents may hold references to artifacts that get deleted. Without clear semantics:
- `invoke()` on deleted artifact fails mysteriously
- References become dangling with no explanation
- Storage accumulates with no cleanup path

The chosen approach (75% confidence from GAPS.md): **Soft delete with tombstones**.

---

## Design

### Tombstone Schema

Add deletion fields to `Artifact` dataclass in `artifacts.py`:

```python
@dataclass
class Artifact:
    # Existing fields...
    deleted: bool = False
    deleted_at: datetime | None = None
    deleted_by: str | None = None  # Who requested deletion
```

### Deletion Semantics

| Action on Tombstone | Behavior |
|---------------------|----------|
| `invoke()` | Returns `{"success": False, "error_code": "DELETED", "error_message": "Artifact was deleted at {timestamp}"}` |
| `read_artifact()` | Returns tombstone metadata (deleted=True, deleted_at, etc.) |
| `write_artifact()` | Fails - cannot write to deleted artifact |
| `list_artifacts()` | Excludes by default, includes with `include_deleted=True` flag |

### Deletion Permission

Only the artifact owner can delete. Genesis artifacts cannot be deleted.

```python
def delete_artifact(artifact_id: str, requester_id: str) -> dict:
    artifact = get_artifact(artifact_id)
    if artifact.id.startswith("genesis_"):
        return {"success": False, "error": "Cannot delete genesis artifacts"}
    if artifact.owner_id != requester_id:
        return {"success": False, "error": "Only owner can delete"}
    artifact.deleted = True
    artifact.deleted_at = datetime.now()
    artifact.deleted_by = requester_id
    return {"success": True}
```

### Tombstone Cleanup (Optional Phase 2)

Configurable cleanup after retention period:

```yaml
artifacts:
  tombstone_retention_days: 7  # Delete tombstones older than 7 days
```

---

## Implementation Steps

### Phase 1: Core Deletion

1. [ ] Add `deleted`, `deleted_at`, `deleted_by` fields to `Artifact` in `artifacts.py`
2. [ ] Add `delete_artifact()` method to `World` class in `world.py`
3. [ ] Update `invoke()` in `executor.py` to check `deleted` flag
4. [ ] Add `delete_artifact` action type to `actions.py`

### Phase 2: Discovery Integration

5. [ ] Update `GenesisStore.list_all()` to accept `include_deleted` parameter
6. [ ] Update `GenesisStore.get_artifact()` to return tombstone with deleted info
7. [ ] Add `DELETED` error code to error conventions (if standardized)

### Phase 3: Configuration & Cleanup

8. [ ] Add `tombstone_retention_days` to config schema
9. [ ] (Optional) Add tombstone cleanup job to simulation runner
10. [ ] Update documentation

---

## Required Tests

| Test | Type | Purpose |
|------|------|---------|
| `test_delete_artifact_owner_only` | Unit | Only owner can delete |
| `test_delete_genesis_forbidden` | Unit | Cannot delete genesis artifacts |
| `test_invoke_deleted_artifact_fails` | Unit | invoke() returns DELETED error |
| `test_list_excludes_deleted_by_default` | Unit | list_all() excludes deleted |
| `test_list_includes_deleted_with_flag` | Unit | list_all(include_deleted=True) includes |
| `test_read_deleted_artifact_returns_tombstone` | Unit | read() returns tombstone metadata |
| `test_write_deleted_artifact_fails` | Unit | write() on deleted fails |

```python
# tests/unit/test_artifact_deletion.py

def test_delete_artifact_owner_only(world_with_artifacts):
    """Only owner can delete their artifact."""
    world = world_with_artifacts
    # Owner can delete
    result = world.delete_artifact("alice_artifact", "alice")
    assert result["success"]
    # Non-owner cannot delete
    result = world.delete_artifact("bob_artifact", "alice")
    assert not result["success"]
    assert "owner" in result["error"].lower()

def test_delete_genesis_forbidden(world_with_genesis):
    """Genesis artifacts cannot be deleted."""
    world = world_with_genesis
    result = world.delete_artifact("genesis_ledger", "alice")
    assert not result["success"]
    assert "genesis" in result["error"].lower()

def test_invoke_deleted_artifact_fails(world_with_artifacts):
    """Invoking deleted artifact returns DELETED error."""
    world = world_with_artifacts
    world.delete_artifact("executable_artifact", "owner")
    result = world.invoke_artifact("caller", "executable_artifact", {})
    assert not result["success"]
    assert result.get("error_code") == "DELETED" or "deleted" in result.get("error", "").lower()

def test_list_excludes_deleted_by_default(world_with_genesis):
    """list_all() excludes deleted artifacts by default."""
    # Create and delete artifact
    # Verify it doesn't appear in list_all()
    pass

def test_list_includes_deleted_with_flag(world_with_genesis):
    """list_all(include_deleted=True) includes deleted artifacts."""
    pass
```

---

## E2E Verification

After implementation:
1. Create an artifact
2. Have another agent reference it
3. Owner deletes the artifact
4. Verify other agent gets clear DELETED error on invoke
5. Verify artifact still visible with include_deleted flag

---

## Verification

- [ ] Artifact dataclass has deletion fields
- [ ] delete_artifact action works
- [ ] invoke() returns DELETED error for tombstones
- [ ] genesis_store filters tombstones appropriately
- [ ] Unit tests pass
- [ ] `docs/architecture/current/artifacts_executor.md` updated

---

## Notes

**Chosen approach:** Soft delete with tombstones (75% confidence)
- Pros: References detectable, clear error messages
- Cons: Storage overhead (mitigated by cleanup)

**Rejected alternatives:**
- Hard delete: Silent failures confuse agents
- Reference counting: Can't delete popular artifacts
- Cascade delete: Too destructive, surprising behavior

See GAPS.md archive (section 18) for original analysis.
