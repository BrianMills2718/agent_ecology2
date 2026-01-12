# INT-002: Integrate Contracts into Executor

**Priority:** 2 (Wave 2 - can run parallel with INT-003)
**Complexity:** L
**Risk:** Medium
**Depends on:** INT-001

---

## Summary

Wire the standalone contracts module into the Executor so permission checks use contract-based access control instead of inline policy dicts.

---

## Current State

- `src/world/contracts.py` and `genesis_contracts.py` exist
- `src/world/executor.py` has inline permission checking:
  - `_check_permission()` reads artifact.policy dict
  - Owner bypass exists (owner always has access)
  - No contract invocation for permissions

---

## Target State

- Executor uses contracts for permission checks
- `check_permission(caller, action, target)` calls contract
- Genesis contracts (freeware, self_owned, private, public) work
- Feature flag `contracts.use_contracts` controls behavior
- Legacy policy dict mode still works when disabled

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/world/executor.py` | Add contract-based permission checking |
| `tests/test_executor.py` | Add tests for contract integration |

---

## Implementation Steps

### Step 1: Import Contracts Module

```python
# In src/world/executor.py

from src.world.contracts import PermissionAction, PermissionResult
from src.world.genesis_contracts import (
    get_genesis_contract,
    get_contract_by_id,
    GENESIS_CONTRACTS,
)
```

### Step 2: Add Contract Resolution Helper

```python
# In src/world/executor.py

class Executor:
    def __init__(self, world: "World", use_contracts: bool = True):
        self.world = world
        self.use_contracts = use_contracts
        self._contract_cache: dict[str, Any] = {}

    def _get_contract(self, contract_id: str):
        """
        Get contract by ID, with caching.

        Checks genesis contracts first, then artifact store.
        """
        if contract_id in self._contract_cache:
            return self._contract_cache[contract_id]

        # Check genesis contracts
        contract = get_contract_by_id(contract_id)
        if contract:
            self._contract_cache[contract_id] = contract
            return contract

        # Could look up custom contracts in artifact store here
        # For now, fall back to freeware if not found
        contract = get_genesis_contract("freeware")
        self._contract_cache[contract_id] = contract
        return contract
```

### Step 3: Modify Permission Checking

```python
# In src/world/executor.py

def _check_permission_via_contract(
    self,
    caller: str,
    action: str,
    artifact: Artifact,
) -> PermissionResult:
    """
    Check permission using artifact's access contract.
    """
    contract_id = getattr(artifact, 'access_contract_id', 'genesis_contract_freeware')
    contract = self._get_contract(contract_id)

    # Convert action string to PermissionAction
    try:
        perm_action = PermissionAction(action)
    except ValueError:
        return PermissionResult(
            allowed=False,
            reason=f"Unknown action: {action}"
        )

    # Build context for contract
    context = {
        "owner": artifact.owner_id,
        "artifact_type": artifact.artifact_type,
        "artifact_id": artifact.artifact_id,
    }

    return contract.check_permission(
        caller=caller,
        action=perm_action,
        target=artifact.artifact_id,
        context=context,
    )

def _check_permission(
    self,
    caller: str,
    action: str,
    artifact: Artifact,
) -> tuple[bool, str]:
    """
    Check if caller has permission for action on artifact.

    Uses contracts when use_contracts=True, otherwise legacy policy.
    Returns (allowed, reason).
    """
    if self.use_contracts:
        result = self._check_permission_via_contract(caller, action, artifact)
        return (result.allowed, result.reason)

    # Legacy policy-based check
    return self._check_permission_legacy(caller, action, artifact)

def _check_permission_legacy(
    self,
    caller: str,
    action: str,
    artifact: Artifact,
) -> tuple[bool, str]:
    """
    Legacy permission check using inline policy dict.

    DEPRECATED: Use contract-based checking when possible.
    """
    policy = getattr(artifact, 'policy', None) or {}

    # Owner always has access in legacy mode
    if caller == artifact.owner_id:
        return (True, "owner access")

    # Check allow lists
    allow_key = f"allow_{action}"
    allow_list = policy.get(allow_key, [])

    if "*" in allow_list or caller in allow_list:
        return (True, f"in {allow_key} list")

    return (False, f"not in {allow_key} list")
```

### Step 4: Update execute() to Use New Permission Check

```python
# In src/world/executor.py

def execute(
    self,
    caller: str,
    artifact: Artifact,
    action: str,
    params: dict,
) -> dict:
    """Execute action on artifact with permission check."""

    # Check permission via contract (or legacy)
    allowed, reason = self._check_permission(caller, action, artifact)

    if not allowed:
        return {
            "success": False,
            "error": f"Permission denied: {reason}",
            "result": None,
        }

    # If contract specifies a cost, handle it
    if self.use_contracts:
        result = self._check_permission_via_contract(caller, action, artifact)
        if result.cost > 0:
            # Deduct cost from caller
            if not self.world.ledger.transfer_scrip(caller, artifact.owner_id, result.cost):
                return {
                    "success": False,
                    "error": f"Insufficient scrip for access cost: {result.cost}",
                    "result": None,
                }

    # Proceed with execution
    return self._do_execute(caller, artifact, action, params)
```

### Step 5: Add Tests

```python
# In tests/test_executor.py

class TestContractIntegration:
    """Tests for Executor + Contracts integration."""

    def test_contracts_enabled_by_default(self, executor):
        """Contracts used by default."""
        assert executor.use_contracts is True

    def test_freeware_allows_read(self, executor, artifact):
        """Freeware contract allows anyone to read."""
        artifact.access_contract_id = "genesis_contract_freeware"
        allowed, _ = executor._check_permission("stranger", "read", artifact)
        assert allowed is True

    def test_freeware_denies_write_non_owner(self, executor, artifact):
        """Freeware contract denies write to non-owner."""
        artifact.access_contract_id = "genesis_contract_freeware"
        artifact.owner_id = "owner1"
        allowed, _ = executor._check_permission("stranger", "write", artifact)
        assert allowed is False

    def test_private_denies_all_non_owner(self, executor, artifact):
        """Private contract denies all access to non-owner."""
        artifact.access_contract_id = "genesis_contract_private"
        artifact.owner_id = "owner1"

        for action in ["read", "write", "invoke"]:
            allowed, _ = executor._check_permission("stranger", action, artifact)
            assert allowed is False

    def test_public_allows_everything(self, executor, artifact):
        """Public contract allows all actions."""
        artifact.access_contract_id = "genesis_contract_public"

        for action in ["read", "write", "invoke", "delete"]:
            allowed, _ = executor._check_permission("anyone", action, artifact)
            assert allowed is True

    def test_self_owned_allows_self(self, executor, artifact):
        """Self-owned contract allows artifact to access itself."""
        artifact.access_contract_id = "genesis_contract_self_owned"
        artifact.artifact_id = "artifact1"
        artifact.owner_id = "owner1"

        # Self access
        allowed, _ = executor._check_permission("artifact1", "read", artifact)
        assert allowed is True

        # Owner access
        allowed, _ = executor._check_permission("owner1", "read", artifact)
        assert allowed is True

        # Stranger denied
        allowed, _ = executor._check_permission("stranger", "read", artifact)
        assert allowed is False

    def test_legacy_mode_still_works(self):
        """Legacy policy mode works when contracts disabled."""
        executor = Executor(world=mock_world, use_contracts=False)
        artifact = Artifact(
            artifact_id="test",
            owner_id="owner1",
            policy={"allow_read": ["*"]},
        )

        allowed, _ = executor._check_permission("anyone", "read", artifact)
        assert allowed is True

    def test_missing_contract_falls_back_to_freeware(self, executor, artifact):
        """Unknown contract_id falls back to freeware."""
        artifact.access_contract_id = "nonexistent_contract"
        allowed, _ = executor._check_permission("anyone", "read", artifact)
        assert allowed is True  # Freeware allows read
```

---

## Interface Definition

```python
class Executor:
    use_contracts: bool

    def _get_contract(self, contract_id: str) -> AccessContract: ...
    def _check_permission_via_contract(self, caller: str, action: str, artifact: Artifact) -> PermissionResult: ...
    def _check_permission(self, caller: str, action: str, artifact: Artifact) -> tuple[bool, str]: ...
    def _check_permission_legacy(self, caller: str, action: str, artifact: Artifact) -> tuple[bool, str]: ...
```

---

## Acceptance Criteria

- [ ] Executor uses contracts for permission checks when enabled
- [ ] All 4 genesis contracts work correctly
- [ ] Legacy policy mode works when `use_contracts=False`
- [ ] Missing contracts fall back to freeware
- [ ] Permission denial includes contract's reason
- [ ] Contract cost deducted from caller when specified
- [ ] All existing executor tests pass
- [ ] New contract integration tests pass

---

## Verification

```bash
pytest tests/test_executor.py -v
pytest tests/ -v
python -m mypy src/world/executor.py --ignore-missing-imports
```

---

## Dependencies

- **Requires:** GAP-GEN-001 (Contract System) - COMPLETE ✓
- **Requires:** INT-001 (for ledger.transfer_scrip in cost handling)
- **Blocks:** CAP-003 (remove owner bypass)
