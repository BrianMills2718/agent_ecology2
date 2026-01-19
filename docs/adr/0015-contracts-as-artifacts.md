# ADR-0015: Contracts as Artifacts

**Status:** Accepted
**Date:** 2026-01-19

## Context

The contract system has two parallel implementations:

1. **Genesis contracts** - Python classes in `genesis_contracts.py` with direct method calls
2. **User contracts** - `ExecutableContract` instances (artifacts) with sandboxed execution

This creates privilege asymmetry:
- Genesis contracts execute instantly (no sandbox overhead)
- Genesis contracts are checked first in lookup (implicit priority)
- Genesis contracts cannot be modified or deleted
- User contracts face sandbox restrictions genesis contracts don't

This violates the project principle: "Genesis artifacts as middle ground - useful patterns without kernel opinions."

Additionally, `World.py` bypasses contracts entirely via `artifact.can_read/write/invoke()` methods which contain hardcoded owner bypasses, while the target architecture states: "The `access_contract_id` is the ONLY authority."

## Decision

**Contracts are artifacts.** No distinction between genesis and user contracts at runtime.

### 1. Genesis Contracts Become Artifacts

Genesis contracts are created as artifacts during bootstrap:

```python
genesis_freeware_contract = Artifact(
    id="genesis_freeware_contract",
    type="contract",
    created_by="Eris",
    executable=True,
    code="def check_permission(caller, action, target, context): ...",
    access_contract_id="genesis_freeware_contract",  # self-referential
)
```

### 2. Contract Type is Advisory

Setting `type="contract"` enables validation at creation:
- Must be executable
- Must have `check_permission` in interface

But at runtime, `access_contract_id` can point to ANY executable artifact. Duck typing applies - if it implements `check_permission`, it's a contract.

### 3. World Uses Contracts for All Permission Checks

Remove `artifact.can_read/write/invoke()` bypasses. All permission checks flow through contracts:

```python
# World._execute_read (target behavior)
def _execute_read(self, intent):
    artifact = self.artifacts.get(intent.artifact_id)
    contract = self.get_artifact(artifact.access_contract_id)
    result = contract.check_permission(
        caller=intent.principal_id,
        action="read",
        target=artifact.id,
        context={"created_by": artifact.created_by, ...}
    )
    if not result.allowed:
        return ActionResult(success=False, message=result.reason)
    # proceed...
```

### 4. Contracts Can Invoke, Not Mutate

Contracts remain pure functions of their inputs:
- Can invoke other artifacts (via normal permission checks)
- Cannot directly mutate kernel state (ledger, storage)
- Return decisions; kernel executes mutations

## Consequences

### Positive

- **No privilege asymmetry** - genesis and user contracts are equals
- **Consistent execution path** - all contracts run through same code
- **Observable** - contracts are artifacts agents can discover and inspect
- **Modifiable** - genesis contracts can be updated (by whoever has rights)
- **Flexible** - any artifact can be used as a contract if it works

### Negative

- **Migration required** - existing genesis contract classes must become artifacts
- **Bootstrap complexity** - contracts must exist before artifacts need them
- **Performance** - genesis contracts lose "fast path" (mitigated by caching)

### Neutral

- Sandbox timeout/restrictions apply to all contracts equally
- Contract caching can optimize hot paths without privilege

## Related

- ADR-0001: Everything is an artifact
- ADR-0003: Contracts can do anything
- ADR-0018: Bootstrap and Eris
- Plan #100: Contract System Overhaul
- `docs/architecture/target/05_contracts.md`
