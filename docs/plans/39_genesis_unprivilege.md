# Plan 39: Remove Genesis Artifact Privilege

**Status:** ✅ Complete

**Verified:** 2026-01-14T06:02:42Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-14T06:02:42Z
tests:
  unit: 1211 passed, 1 skipped in 14.85s
  e2e_smoke: PASSED (1.99s)
  doc_coupling: passed
commit: a5d18fb
```
**Priority:** High
**Blocked By:** None
**Blocks:** None

---

## Problem Statement

Genesis artifacts currently have accidental runtime privilege through direct object references:

```python
# Current: genesis artifacts get direct kernel access
class GenesisLedger:
    def __init__(self, ledger: Ledger, ...):
        self.ledger = ledger  # Direct reference to kernel object
```

When an agent writes an artifact via `WriteArtifactIntent`, they write code as a string that runs in a sandbox. That sandbox cannot obtain references to `world.ledger`, `world.artifacts`, etc.

**This violates the design principle:** Genesis artifacts should be cold-start conveniences, not privileged. Any agent should be able to build an equivalent artifact.

---

## Architectural Clarification

| Concept | Examples | Agent Access |
|---------|----------|--------------|
| **Physics (Rules)** | Tick mechanics, resource costs, transfer rules | Readable via handbook |
| **State** | Balances, artifact contents, ownership | Queryable via interfaces (respecting access controls) |
| **Administration** | Advancing tick, minting scrip, creating principals | Dev/kernel only |

Genesis artifacts operate in the same layer as agent artifacts - they can read the handbook and query state, but cannot perform admin operations.

---

## Proposed Solution

### 1. Define Kernel State Interface

Create an interface available to ALL artifact code (genesis and agent-built):

```python
# Available in artifact execution sandbox
class KernelState:
    """Read-only interface to kernel state for artifacts."""

    def get_balance(self, principal_id: str) -> int:
        """Get scrip balance (public information)."""
        ...

    def get_resource(self, principal_id: str, resource: str) -> float:
        """Get resource amount (public information)."""
        ...

    def get_artifact_metadata(self, artifact_id: str) -> dict:
        """Get artifact metadata: owner, type, permissions (public)."""
        ...

    def read_artifact(self, artifact_id: str, caller_id: str) -> str | None:
        """Read artifact content (access controlled)."""
        ...

    def list_artifacts_by_owner(self, owner_id: str) -> list[str]:
        """List artifact IDs owned by principal (public)."""
        ...
```

### 2. Define Kernel Action Interface

For state-modifying operations, artifacts request actions (verified against caller):

```python
class KernelActions:
    """Action interface for artifacts - caller is verified."""

    def transfer_scrip(self, caller_id: str, to: str, amount: int) -> bool:
        """Transfer scrip FROM caller TO recipient."""
        # Kernel verifies caller_id matches actual invoker
        ...

    def transfer_resource(self, caller_id: str, to: str, resource: str, amount: float) -> bool:
        """Transfer resource FROM caller TO recipient."""
        ...

    def write_artifact(self, caller_id: str, artifact_id: str, content: str, ...) -> bool:
        """Write artifact owned by caller."""
        ...
```

### 3. Refactor Genesis Artifacts

Rewrite genesis artifacts to use the same interfaces:

```python
# After: genesis uses same interface as any artifact
class GenesisLedger:
    def __init__(self, kernel_state: KernelState, kernel_actions: KernelActions):
        self.state = kernel_state
        self.actions = kernel_actions

    def get_balance(self, caller_id: str, target_id: str) -> int:
        return self.state.get_balance(target_id)

    def transfer(self, caller_id: str, to: str, amount: int) -> bool:
        return self.actions.transfer_scrip(caller_id, to, amount)
```

### 4. Inject Interface into Sandbox

When executing artifact code (genesis or agent-built), inject the same interface:

```python
# In executor
sandbox_globals = {
    "kernel_state": KernelState(world),
    "kernel_actions": KernelActions(world, caller_id=invoking_agent),
    # ... other sandbox globals
}
exec(artifact_code, sandbox_globals)
```

---

## Access Control Rules

| Operation | Access |
|-----------|--------|
| Read any principal's balance | Public |
| Read any principal's resources | Public |
| List artifacts by owner | Public |
| Read artifact metadata (owner, type) | Public |
| Read artifact content | Access controlled (owner or granted read) |
| Transfer scrip/resources | Only from caller's own account |
| Write artifact | Only caller-owned artifacts |
| Invoke artifact | Subject to artifact's invoke permissions |

---

## Changes Required

| File | Change |
|------|--------|
| `src/world/kernel_interface.py` | New file: KernelState, KernelActions classes |
| `src/world/genesis.py` | Refactor all genesis artifacts to use interfaces |
| `src/world/executor.py` | Inject interface into artifact sandbox |
| `src/world/artifacts.py` | Add access control checks |
| `docs/architecture/current/genesis_artifacts.md` | Update to reflect non-privileged model |
| `docs/adr/` | New ADR documenting this decision |

---

## Required Tests

### Unit Tests
- `test_kernel_interface.py::test_state_read_public` - Any artifact can read balances
- `test_kernel_interface.py::test_state_read_access_controlled` - Artifact content respects permissions
- `test_kernel_interface.py::test_actions_verify_caller` - Can only transfer from own account
- `test_kernel_interface.py::test_genesis_uses_interface` - Genesis artifacts use same interface

### Integration Tests
- `test_genesis_unprivilege.py::test_agent_artifact_equivalent_to_genesis` - Agent can build functional equivalent of genesis_ledger
- `test_genesis_unprivilege.py::test_no_privilege_escalation` - Cannot bypass access controls via interface

---

## Migration Path

1. Create KernelState/KernelActions interfaces
2. Add interface injection to executor
3. Refactor genesis artifacts one at a time (can be incremental)
4. Verify agent-built artifacts can use same interface
5. Remove direct object references from genesis

---

## Out of Scope

- Changing what operations are admin-only (minting, tick advance)
- Changing the artifact execution sandbox itself
- Access control policy changes (just enforcing existing model)

---

## Notes

This emerged from discussion about vulture observability (Plan #26) where the question arose: are freeze detection methods privileged kernel stuff or accessible to any artifact?

The answer: kernel state should be queryable by any artifact through interfaces. Genesis artifacts are not privileged - they're just cold-start conveniences.

Reference: Conversation on 2026-01-14 about genesis privilege model.
