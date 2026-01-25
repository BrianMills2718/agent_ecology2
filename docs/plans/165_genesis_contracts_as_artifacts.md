# Plan 165: Genesis Contracts as Artifacts

**Status:** Planned
**Priority:** Medium
**Complexity:** Medium

## Problem

Genesis contracts (freeware, private, owner_only, etc.) are currently Python classes stored in a dict (`world._contracts`), NOT artifacts. This creates:

1. **Inconsistency** - Everything else agents interact with is an artifact
2. **Opacity** - Agents can't `read_artifact("freeware")` to understand permission rules
3. **Mental model confusion** - "Everything is an artifact... except contracts"
4. **No discoverability** - Can't `genesis_store.list(type="contract")`

## Current State

```python
# In world.py
self._contracts = {
    "freeware": FreewareContract(),
    "private": PrivateContract(),
    # ...
}

# Lookup by name, not artifact_id
contract = self._contracts.get(contract_name)
```

## Solution

### Phase 1: Contract Artifact Interface

Define contract artifacts with a standard interface:

```python
# Contract artifact content structure
{
    "type": "contract",
    "interface": {
        "check_permission": {
            "args": ["caller", "action", "target"],
            "returns": {"allowed": "bool", "reason": "str"}
        }
    },
    "rules": {
        "read": "allow_all",
        "write": "owner_only",
        "invoke": "allow_all",
        "delete": "owner_only"
    }
}
```

### Phase 2: Migrate Genesis Contracts

Convert existing Python classes to artifacts:

| Current | New Artifact ID | Description |
|---------|-----------------|-------------|
| `FreewareContract` | `genesis_contract_freeware` | Anyone can read/invoke |
| `PrivateContract` | `genesis_contract_private` | Owner only |
| `OwnerOnlyContract` | `genesis_contract_owner_only` | Strict owner access |

### Phase 3: Kernel Default Behavior

Separate kernel's built-in default from genesis contracts:

```python
# Kernel has hardcoded fallback (not an artifact)
KERNEL_DEFAULT_PERMISSIONS = {
    "read": True,   # Default: readable
    "write": False, # Default: not writable
    "invoke": False, # Default: not invokable
    "delete": False  # Default: not deletable
}

# Used when:
# 1. Artifact has no contract specified
# 2. During bootstrap before genesis exists
```

### Phase 4: Update Artifact Assignment

```python
# Before: contract name string
artifact.contract = "freeware"

# After: artifact reference
artifact.contract_id = "genesis_contract_freeware"
```

## Key Design Decisions

1. **Kernel default is NOT an artifact** - It's physics, always present
2. **Genesis contracts ARE artifacts** - Optional conveniences, observable
3. **Backward compatibility** - Support both string names and artifact IDs during migration

## Mental Model After Implementation

```
Kernel (mandatory, not artifacts):
  - Default permissions when no contract specified
  - Core permission checking logic

Genesis Contracts (optional artifacts):
  - genesis_contract_freeware
  - genesis_contract_private
  - genesis_contract_owner_only
  - Agents can read, discover, understand rules
  - Agents could create equivalent contracts

Genesis Artifacts (optional, services):
  - genesis_ledger, genesis_escrow, etc.
  - Cold-start conveniences
```

## Testing

- [ ] Contract artifacts are discoverable via genesis_store
- [ ] `read_artifact("genesis_contract_freeware")` returns rules
- [ ] Permission checking works with artifact-based contracts
- [ ] Kernel default applies when no contract specified
- [ ] Backward compat: string contract names still work

## Files to Modify

| File | Change |
|------|--------|
| `src/world/contracts.py` | Extract rules to data, keep executor |
| `src/world/genesis/factory.py` | Create contract artifacts |
| `src/world/executor.py` | Look up contract by artifact_id |
| `src/artifacts/artifact.py` | `contract_id` field |

## Dependencies

- None

**Note:** This plan should be completed BEFORE Plan #166 (Resource Rights Model). Contracts-as-artifacts is simpler and establishes the pattern. Rights-as-artifacts builds on it and may reference contracts for permissions.

## Related

- Plan #164: Artifact Dependency Tracking (contracts would show as dependencies)
- docs/architecture/current/contracts.md (needs update after)
