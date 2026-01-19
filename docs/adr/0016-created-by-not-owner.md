# ADR-0016: created_by Replaces owner_id

**Status:** Accepted
**Date:** 2026-01-19

## Context

The current artifact model has an `owner_id` field that the kernel interprets for access control. The target architecture states: "The kernel doesn't know what an 'owner' is."

Problems with `owner_id`:

1. **Semantic ambiguity** - If Alice controls write access and Bob controls read access, who is the "owner"?
2. **Kernel privilege** - The kernel hardcodes owner checks in `artifact.can_write()` (line 219-220: `if agent_id == self.owner_id: return True`)
3. **Policy assumption** - "Owner can always write" is a policy choice that belongs in contracts, not kernel

The only unambiguous fact is: who created this artifact?

## Decision

**Replace `owner_id` with `created_by` as the kernel-level field.**

### 1. Artifact Field Change

```python
@dataclass
class Artifact:
    id: str
    type: str
    content: str
    created_by: str  # Immutable fact: who created this artifact
    # Remove: owner_id: str
```

### 2. Kernel Passes Facts, Not Interpretations

The kernel passes `created_by` to contracts as context:

```python
context = {
    "created_by": artifact.created_by,
    "artifact_type": artifact.type,
    "artifact_id": artifact.id,
}
result = contract.check_permission(caller, action, target, context)
```

The kernel does NOT interpret what `created_by` means for access control.

### 3. Contracts Implement "Owner" Semantics

The freeware contract (and others) decide what creator privileges mean:

```python
def check_permission(caller, action, target, context):
    if action in ["read", "invoke"]:
        return {"allowed": True, "reason": "open access"}
    if action in ["write", "delete"]:
        if caller == context["created_by"]:
            return {"allowed": True, "reason": "creator access"}
        return {"allowed": False, "reason": "only creator can modify"}
```

Different contracts can interpret `created_by` differently or ignore it entirely.

### 4. "Ownership" Is a Contract Pattern

If agents want transferable ownership:
- Create a contract that tracks "current owner" in artifact metadata
- Contract checks metadata, not `created_by`
- "Transfer" = update metadata (if contract allows)

This is more flexible than kernel-level ownership.

## Consequences

### Positive

- **Clear semantics** - `created_by` is an immutable historical fact
- **No kernel privilege** - kernel doesn't interpret creator as having special rights
- **Flexible ownership** - contracts can implement any ownership model
- **Eliminates ambiguity** - no more "who is the owner?" questions

### Negative

- **Migration required** - rename `owner_id` to `created_by` throughout codebase
- **Contract changes** - genesis contracts use `context["owner"]`, must change to `context["created_by"]`
- **Mental model shift** - developers used to "owner" must think in terms of "creator"

### Neutral

- Existing freeware semantics preserved (creator-only write) via contract logic
- No functional change to default access patterns

## Related

- ADR-0015: Contracts as Artifacts
- Plan #100: Contract System Overhaul
- `src/world/artifacts.py` - artifact model
- `src/world/genesis_contracts.py` - contract implementations
