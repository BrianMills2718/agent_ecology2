# ADR-0019: Unified Permission Architecture

**Status:** Accepted
**Date:** 2026-01-21
**Consolidates:** ADR-0003, ADR-0015, ADR-0016, ADR-0017, ADR-0018

## Context

Multiple ADRs address different aspects of the permission system:
- ADR-0003: Contracts can do anything
- ADR-0015: Contracts as artifacts
- ADR-0016: created_by replaces owner_id
- ADR-0017: Dangling contracts fail-open
- ADR-0018: Bootstrap and Eris

This ADR consolidates and clarifies the unified permission architecture, resolving ambiguities and documenting the complete model.

## Decision

### 1. Every Artifact Has access_contract_id

All artifacts have an `access_contract_id` field pointing to the contract that governs permissions:

```python
@dataclass
class Artifact:
    id: str
    content: Any
    created_by: str
    access_contract_id: str | None  # Contract that governs this artifact
    # ...
```

### 2. Five Kernel Actions, All Contract-Checked

The kernel provides five primitive actions. All check the target artifact's contract:

| Action | Purpose | Context Includes |
|--------|---------|------------------|
| `read` | Read artifact content | caller, action, target |
| `write` | Create/replace artifact | caller, action, target |
| `edit` | Surgical content modification | caller, action, target |
| `invoke` | Call method on artifact | caller, action, target, method, args |
| `delete` | Remove artifact | caller, action, target |

Only `invoke` includes method and args in context.

### 3. Immediate Caller Model

When A invokes B, and B invokes C:
- B's contract checks: "can A invoke B?"
- C's contract checks: "can B invoke C?"

The **immediate caller** is checked, not the original caller. Like Ethereum's `msg.sender`.

```
A ──invoke──► B ──invoke──► C
                    │
         C's contract sees B as caller,
         NOT A
```

**Rationale:** Simple, secure, no identity spoofing. Delegation is explicit (update contracts) not implicit.

### 4. Default When access_contract_id Is Null

When `access_contract_id` is null (not set), the kernel applies a configurable default:

**Default behavior (configurable):**
- Creator has full rights (read, write, edit, invoke, delete)
- All other callers are blocked

```yaml
# config.yaml
contracts:
  default_when_null: "creator_only"  # Options: "creator_only", "freeware", "private"
```

**Rationale:** New artifacts don't require explicit contract assignment. Sensible default preserves creator control.

### 5. Dangling Contracts Fail-Open (ADR-0017)

When `access_contract_id` points to a **deleted** contract (different from null):

- Fall back to configurable default contract
- Log warning for observability
- Selection pressure preserved (custom access control is lost)

```yaml
# config.yaml
contracts:
  default_on_missing: "genesis_freeware_contract"
```

**Distinction:**
- `access_contract_id = null`: Use default behavior (section 4)
- `access_contract_id` points to deleted contract: Use fallback contract (this section)

### 6. Minimal Context from Kernel

The kernel provides **minimal** context to contracts:

```python
context = {
    "caller": str,      # Who is making the request
    "action": str,      # read | write | edit | invoke | delete
    "target": str,      # Artifact ID being accessed
    "method": str,      # Only for invoke
    "args": list,       # Only for invoke
}
```

**Contracts invoke other artifacts to get more info:**

```python
def check_permission(caller, action, target, context):
    # Need caller's balance? Invoke ledger
    balance = invoke("genesis_ledger", "balance", [caller])

    # Need contribution history? Invoke event log
    history = invoke("genesis_event_log", "query", [{"caller": caller}])

    # Make decision based on gathered info
    if balance < 100:
        return {"allowed": False, "reason": "Insufficient balance"}
    return {"allowed": True}
```

**Rationale:**
- Minimal kernel (heuristic: kernel provides physics, not policy)
- Maximum flexibility (contracts get what they need)
- Pragmatic (genesis helpers can bundle common queries)

### 7. Kernel Optimization for Freeware

The kernel MAY optimize by skipping contract calls for known freeware:

```python
def check_permission(artifact, action, caller):
    # Pragmatic optimization
    if artifact.access_contract_id == "genesis_freeware_contract":
        # Skip contract call, apply freeware logic directly
        if action in ["read", "invoke"]:
            return PermissionResult(allowed=True)
        if caller == artifact.created_by:
            return PermissionResult(allowed=True)
        return PermissionResult(allowed=False)

    # Normal contract check
    return invoke_contract(artifact.access_contract_id, ...)
```

**Rationale:** Pragmatic performance win. Internal "firms" (clusters of artifacts with permissive access) have zero contract overhead.

**Not a privilege:** Freeware is still a contract. The optimization is equivalent to caching the contract's deterministic result. Any artifact can achieve similar by using freeware.

### 8. Genesis Contracts Are Convenience

Genesis contracts (freeware, private, self-owned) are pre-seeded convenience patterns:
- Not privileged at runtime
- Not required (agents can write their own)
- Solve cold-start problem (something must exist first)

Agents could create `better_freeware_contract` with identical behavior.

### 9. Bootstrap Creates Initial Contracts

During `World.__init__()`, bootstrap phase creates genesis contracts without permission checks:

```python
class World:
    def __init__(self):
        self._bootstrapping = True
        self._create_genesis_artifacts()  # No permission checks
        self._bootstrapping = False       # Physics now applies
```

**Why bootstrap is needed:** To CREATE the first contracts that other artifacts will reference. Once they exist, normal physics applies.

**Not needed for null contracts:** If `access_contract_id = null`, default behavior applies without referencing a contract artifact.

## Consequences

### Positive

- **Unified model** - All permissions flow through one system
- **No privilege asymmetry** - Genesis and user contracts are equals
- **Flexible** - Contracts can implement any access pattern (Ostrom-style, multi-sig, paid access)
- **Observable** - All permission checks can be logged
- **Pragmatic** - Freeware optimization reduces overhead without breaking model

### Negative

- **Complexity** - Multiple concepts to understand (null vs dangling, immediate vs original caller)
- **Performance** - Every action checks contracts (mitigated by caching/optimization)
- **Indirection** - Contracts invoking other artifacts for context adds latency

### Neutral

- Existing ADRs remain valid but this ADR is the authoritative consolidation
- Implementation may lag this specification

## Related

- ADR-0003: Contracts can do anything
- ADR-0015: Contracts as artifacts
- ADR-0016: created_by replaces owner_id
- ADR-0017: Dangling contracts fail-open
- ADR-0018: Bootstrap and Eris
- Plan #100: Contract System Overhaul
- `docs/architecture/target/05_contracts.md`
- `docs/architecture/target/08_kernel.md`
