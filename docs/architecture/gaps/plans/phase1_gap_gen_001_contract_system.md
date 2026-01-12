# GAP-GEN-001: Contract-Based Access Control Implementation Plan

**Gap ID:** GAP-GEN-001
**Complexity:** XL (500+ lines, cross-component)
**Risk:** High
**Phase:** 1 - Foundations

---

## Summary

Replace inline policy dictionaries with contract-based access control. Contracts are artifacts that implement `check_permission(caller, action, target)` and return permission decisions. This is foundational because all artifact access flows through this system.

---

## Current State

- Artifacts have inline `policy` dict with `read/write/execute/invoke` lists
- Permission checks are hardcoded in `executor.py`
- Owner bypass exists (owner can always access)
- No contract invocation for permissions
- Policies cannot be traded or shared

---

## Target State

- Artifacts reference `access_contract_id` instead of inline policy
- Contracts implement `check_permission(caller, action, target) -> PermissionResult`
- Four genesis contracts: `freeware`, `self_owned`, `private`, `public`
- Owner bypass removed (contracts are sole authority)
- Contracts are artifacts and can be traded

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/world/contracts.py` | **NEW FILE** - Contract base class and interface |
| `src/world/genesis_contracts.py` | **NEW FILE** - Four genesis contract implementations |
| `src/world/artifacts.py` | Add `access_contract_id` field, deprecate `policy` |
| `src/world/executor.py` | Replace inline checks with contract invocation |
| `src/world/genesis.py` | Create genesis contracts on world init |
| `config/schema.yaml` | Add contract configuration |
| `tests/test_contracts.py` | **NEW FILE** - Contract system tests |
| `tests/test_genesis_contracts.py` | **NEW FILE** - Genesis contract tests |

---

## Implementation Steps

### Step 1: Define Contract Interface

Create `src/world/contracts.py`:

```python
from dataclasses import dataclass
from typing import Protocol, Literal, Optional
from enum import Enum

class PermissionAction(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    INVOKE = "invoke"
    DELETE = "delete"
    TRANSFER = "transfer"

@dataclass
class PermissionResult:
    """Result of a permission check."""
    allowed: bool
    reason: str
    cost: int = 0  # Scrip cost to perform action
    conditions: Optional[dict] = None  # Additional conditions

class AccessContract(Protocol):
    """Interface for access control contracts."""

    def check_permission(
        self,
        caller: str,  # principal_id requesting access
        action: PermissionAction,
        target: str,  # artifact_id being accessed
        context: Optional[dict] = None
    ) -> PermissionResult:
        """
        Check if caller has permission to perform action on target.

        Args:
            caller: The principal (agent/artifact) requesting access
            action: The action being attempted
            target: The artifact being accessed
            context: Optional additional context (e.g., parameters)

        Returns:
            PermissionResult with allowed status, reason, and optional cost
        """
        ...

    @property
    def contract_id(self) -> str:
        """Unique identifier for this contract."""
        ...

    @property
    def contract_type(self) -> str:
        """Contract type (freeware, self_owned, private, public, custom)."""
        ...
```

### Step 2: Implement Genesis Contracts

Create `src/world/genesis_contracts.py`:

```python
from dataclasses import dataclass
from typing import Optional, Set
from .contracts import AccessContract, PermissionAction, PermissionResult

@dataclass
class FreewareContract(AccessContract):
    """
    Anyone can read/execute/invoke. Only owner can write/delete/transfer.
    Default for most shared artifacts.
    """
    contract_id: str = "genesis_contract_freeware"
    contract_type: str = "freeware"

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: Optional[dict] = None
    ) -> PermissionResult:
        owner = context.get("owner") if context else None

        if action in (PermissionAction.READ, PermissionAction.EXECUTE, PermissionAction.INVOKE):
            return PermissionResult(allowed=True, reason="freeware: open access")

        if action in (PermissionAction.WRITE, PermissionAction.DELETE, PermissionAction.TRANSFER):
            if caller == owner:
                return PermissionResult(allowed=True, reason="freeware: owner access")
            return PermissionResult(allowed=False, reason="freeware: only owner can modify")

        return PermissionResult(allowed=False, reason="freeware: unknown action")


@dataclass
class SelfOwnedContract(AccessContract):
    """
    Only the artifact itself (or owner) can access.
    Used for agent memory, private state.
    """
    contract_id: str = "genesis_contract_self_owned"
    contract_type: str = "self_owned"

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: Optional[dict] = None
    ) -> PermissionResult:
        owner = context.get("owner") if context else None

        # Self-access or owner-access
        if caller == target or caller == owner:
            return PermissionResult(allowed=True, reason="self_owned: self/owner access")

        return PermissionResult(allowed=False, reason="self_owned: access denied")


@dataclass
class PrivateContract(AccessContract):
    """
    Only owner can access. No sharing at all.
    Used for sensitive artifacts.
    """
    contract_id: str = "genesis_contract_private"
    contract_type: str = "private"

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: Optional[dict] = None
    ) -> PermissionResult:
        owner = context.get("owner") if context else None

        if caller == owner:
            return PermissionResult(allowed=True, reason="private: owner access")

        return PermissionResult(allowed=False, reason="private: access denied")


@dataclass
class PublicContract(AccessContract):
    """
    Anyone can do anything. Used for true commons.
    """
    contract_id: str = "genesis_contract_public"
    contract_type: str = "public"

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: Optional[dict] = None
    ) -> PermissionResult:
        return PermissionResult(allowed=True, reason="public: open access")


# Registry of genesis contracts
GENESIS_CONTRACTS = {
    "freeware": FreewareContract(),
    "self_owned": SelfOwnedContract(),
    "private": PrivateContract(),
    "public": PublicContract(),
}

def get_genesis_contract(contract_type: str) -> AccessContract:
    """Get a genesis contract by type."""
    if contract_type not in GENESIS_CONTRACTS:
        raise ValueError(f"Unknown genesis contract type: {contract_type}")
    return GENESIS_CONTRACTS[contract_type]
```

### Step 3: Update Artifact Model

Update `src/world/artifacts.py`:

```python
@dataclass
class Artifact:
    artifact_id: str
    artifact_type: str
    owner_id: str
    content: Any

    # NEW: Contract-based access control
    access_contract_id: str = "genesis_contract_freeware"  # Default to freeware

    # DEPRECATED: Will be removed after migration
    policy: Optional[dict] = None  # Keep for migration period

    # ... rest of fields
```

### Step 4: Update Executor Permission Checks

Update `src/world/executor.py`:

```python
from .contracts import PermissionAction, PermissionResult
from .genesis_contracts import get_genesis_contract, GENESIS_CONTRACTS

class Executor:
    def __init__(self, world: "World", use_contracts: bool = True):
        self.world = world
        self.use_contracts = use_contracts  # Feature flag for migration
        self._contract_cache: Dict[str, AccessContract] = {}

    def _get_contract(self, contract_id: str) -> AccessContract:
        """Get contract by ID, using cache."""
        if contract_id in self._contract_cache:
            return self._contract_cache[contract_id]

        # Check genesis contracts first
        for gc in GENESIS_CONTRACTS.values():
            if gc.contract_id == contract_id:
                self._contract_cache[contract_id] = gc
                return gc

        # Load custom contract from artifact store
        contract_artifact = self.world.store.get(contract_id)
        if contract_artifact and contract_artifact.artifact_type == "contract":
            contract = self._load_custom_contract(contract_artifact)
            self._contract_cache[contract_id] = contract
            return contract

        raise ValueError(f"Contract not found: {contract_id}")

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target_artifact: Artifact
    ) -> PermissionResult:
        """Check permission using artifact's access contract."""

        if not self.use_contracts:
            # Legacy path: use inline policy
            return self._check_legacy_permission(caller, action, target_artifact)

        contract = self._get_contract(target_artifact.access_contract_id)

        context = {
            "owner": target_artifact.owner_id,
            "artifact_type": target_artifact.artifact_type,
            "caller_type": self._get_principal_type(caller),
        }

        return contract.check_permission(
            caller=caller,
            action=action,
            target=target_artifact.artifact_id,
            context=context
        )

    def execute(self, caller: str, artifact: Artifact, action: str, params: dict) -> dict:
        """Execute action on artifact with permission check."""

        # Map action string to PermissionAction
        perm_action = PermissionAction(action)

        # Check permission via contract
        result = self.check_permission(caller, perm_action, artifact)

        if not result.allowed:
            return {
                "success": False,
                "error": f"Permission denied: {result.reason}",
                "result": None
            }

        # Deduct cost if any
        if result.cost > 0:
            if not self.world.ledger.transfer(caller, artifact.owner_id, result.cost):
                return {
                    "success": False,
                    "error": f"Insufficient scrip for access cost: {result.cost}",
                    "result": None
                }

        # Proceed with execution
        return self._do_execute(caller, artifact, action, params)
```

### Step 5: Create Genesis Contracts on World Init

Update `src/world/genesis.py`:

```python
def create_genesis_artifacts(world: "World") -> None:
    """Create all genesis artifacts including contracts."""

    # ... existing genesis artifacts ...

    # Create genesis contract artifacts
    for contract_type, contract in GENESIS_CONTRACTS.items():
        world.store.create(
            artifact_id=contract.contract_id,
            artifact_type="contract",
            owner_id="genesis",
            content={
                "contract_type": contract_type,
                "description": contract.__doc__,
            },
            access_contract_id="genesis_contract_freeware",  # Contracts are freeware
        )
```

### Step 6: Add Configuration

Update `config/schema.yaml`:

```yaml
contracts:
  use_contracts: true  # Feature flag for migration
  default_contract: "genesis_contract_freeware"
  genesis_contracts:
    - freeware
    - self_owned
    - private
    - public
```

---

## Interface Definition

```python
class AccessContract(Protocol):
    contract_id: str
    contract_type: str

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: Optional[dict] = None
    ) -> PermissionResult: ...

@dataclass
class PermissionResult:
    allowed: bool
    reason: str
    cost: int = 0
    conditions: Optional[dict] = None
```

---

## Migration Strategy

1. **Phase 1A:** Add `access_contract_id` field with default `genesis_contract_freeware`
2. **Phase 1B:** Implement contract system with feature flag `use_contracts: false`
3. **Phase 1C:** Run both paths in parallel, log differences
4. **Phase 1D:** Enable `use_contracts: true` by default
5. **Phase 2:** Deprecate `policy` field, warn on usage
6. **Phase 3:** Remove `policy` field and legacy code path

---

## Test Cases

| Test | Description | Expected |
|------|-------------|----------|
| `test_freeware_read` | Anyone can read freeware | `allowed=True` |
| `test_freeware_write_owner` | Owner can write freeware | `allowed=True` |
| `test_freeware_write_other` | Non-owner cannot write | `allowed=False` |
| `test_self_owned_self` | Artifact can access itself | `allowed=True` |
| `test_self_owned_other` | Others cannot access | `allowed=False` |
| `test_private_owner` | Owner can access private | `allowed=True` |
| `test_private_other` | Non-owner denied | `allowed=False` |
| `test_public_anyone` | Anyone can do anything | `allowed=True` |
| `test_contract_cost` | Cost deducted from caller | Scrip transferred |
| `test_migration_parallel` | Legacy and contract paths match | Same results |

---

## Acceptance Criteria

- [ ] `check_permission(caller, action, target)` interface implemented
- [ ] Four genesis contracts work correctly
- [ ] Artifacts have `access_contract_id` field
- [ ] Executor uses contracts for permission checks
- [ ] Old policy dicts still work during migration period
- [ ] Feature flag controls contract usage
- [ ] Genesis contracts created on world initialization
- [ ] All tests pass

---

## Rollback Plan

If issues arise:
1. Set `use_contracts: false` in config
2. System falls back to legacy policy dicts
3. Debug contracts in isolation
4. Fix and re-enable

---

## Dependencies

- **Required for:** GAP-ART-008 (remove owner bypass)
- **Required for:** GAP-GEN-003 (genesis contracts)
- **Required for:** GAP-GEN-034 (custom contracts)
- **Blocks:** Phase 2 access control stream
