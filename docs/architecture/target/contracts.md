# Target Contract System

What we're building toward.

**Last verified:** 2026-01-11

**See current:** Access control is currently hardcoded policy fields on artifacts.

---

## Contracts Are Artifacts

Contracts are executable artifacts that answer permission questions.

```python
# Contract = artifact with can_execute=true and check_permission tool
{
    "id": "genesis_freeware",
    "can_execute": True,
    "has_standing": False,  # Contracts don't need standing
    "interface": {
        "tools": [{
            "name": "check_permission",
            "inputSchema": {...}
        }]
    }
}
```

Every artifact has an `access_contract_id` pointing to the contract that governs its permissions.

---

## Permission Check Flow

```
Agent A wants to read Artifact X
  1. System looks up X.access_contract_id → "genesis_freeware"
  2. System invokes genesis_freeware.check_permission({
       artifact_id: X.id,
       action: "read",
       requester_id: A.id
     })
  3. Contract returns {allowed: true/false, reason: "..."}
  4. If allowed: proceed with action
  5. If not: return error to A
```

### Cost Model

**Base permission checks are free.** (Certainty: 85%)

Simple permission checks (can_read, can_invoke, can_write) cost zero compute. Rationale: you need compute to check if you have compute - this creates infinite regress if checks have cost.

| Operation | Cost |
|-----------|------|
| Base check (simple logic) | 0 |
| Contract calls LLM | Invoker pays LLM cost |
| Contract invokes artifacts | Invoker pays invoke cost |

See DESIGN_CLARIFICATIONS.md for full cost model discussion.

---

## Required Interface

All contracts must implement `check_permission`:

```json
{
    "name": "check_permission",
    "description": "Check if requester can perform action on artifact",
    "inputSchema": {
        "type": "object",
        "properties": {
            "artifact_id": {
                "type": "string",
                "description": "ID of the artifact being accessed"
            },
            "action": {
                "type": "string",
                "enum": ["read", "write", "invoke", "delete", "transfer"],
                "description": "Action being attempted"
            },
            "requester_id": {
                "type": "string",
                "description": "ID of the agent/artifact requesting access"
            }
        },
        "required": ["artifact_id", "action", "requester_id"]
    }
}
```

### Response Format

```json
{
    "allowed": true,
    "reason": "Open access for read"
}
// or
{
    "allowed": false,
    "reason": "Only creator can write"
}
```

---

## Genesis Contracts

Default contracts provided at system initialization.

| Contract | Behavior |
|----------|----------|
| `genesis_freeware` | Anyone reads/invokes, only creator writes/deletes |
| `genesis_self_owned` | Only the artifact itself can access (for agent self-control) |
| `genesis_private` | Only creator has any access |
| `genesis_public` | Anyone can do anything |

### genesis_freeware (Default)

```python
def check_permission(artifact_id, action, requester_id):
    artifact = get_artifact(artifact_id)

    if action in ["read", "invoke"]:
        return {"allowed": True, "reason": "Open access"}
    else:  # write, delete, transfer
        if requester_id == artifact.created_by:
            return {"allowed": True, "reason": "Creator access"}
        else:
            return {"allowed": False, "reason": "Only creator can modify"}
```

### genesis_self_owned

```python
def check_permission(artifact_id, action, requester_id):
    if requester_id == artifact_id:  # Agent accessing itself
        return {"allowed": True, "reason": "Self access"}
    else:
        return {"allowed": False, "reason": "Self-owned: only self can access"}
```

---

## Custom Contracts

Agents can create contracts for any access pattern.

### Example: Paid Read Access

```python
{
    "id": "contract_paid_read",
    "can_execute": True,
    "content": """
def check_permission(artifact_id, action, requester_id):
    if action == "read":
        # Check if requester paid
        artifact = get_artifact(artifact_id)
        if has_paid(requester_id, artifact.owner, artifact.read_price):
            return {"allowed": True}
        else:
            return {"allowed": False, "reason": f"Pay {artifact.read_price} scrip first"}
    # ... other actions
"""
}
```

### Example: Multi-Sig Access

```python
{
    "id": "contract_multisig_2of3",
    "can_execute": True,
    "content": """
def check_permission(artifact_id, action, requester_id):
    if action in ["write", "delete", "transfer"]:
        # Require 2 of 3 signatures
        required = ["alice", "bob", "carol"]
        signatures = get_signatures(artifact_id, action)
        valid_sigs = [s for s in signatures if s.signer in required]
        if len(valid_sigs) >= 2:
            return {"allowed": True}
        else:
            return {"allowed": False, "reason": f"Need 2/3 signatures, have {len(valid_sigs)}"}
    else:
        return {"allowed": True}
"""
}
```

---

## Contract Capabilities

**Contracts can do anything.** (Decision updated: 2026-01-11)

Contracts are executable artifacts with full capabilities:
- Call LLM (invoker pays)
- Invoke other artifacts (invoker pays)
- Make external API calls (invoker pays)
- Cannot modify state directly (return decision, not mutate)

```python
# Contract execution context - full capabilities, invoker pays costs
def execute_contract(contract_code: str, inputs: dict, invoker_id: str) -> PermissionResult:
    namespace = {
        "artifact_id": inputs["artifact_id"],
        "action": inputs["action"],
        "requester_id": inputs["requester_id"],
        "artifact_content": inputs["artifact_content"],
        "context": inputs["context"],

        # Full capabilities - costs charged to invoker
        "invoke": lambda *args: invoke_as(invoker_id, *args),
        "call_llm": lambda *args: call_llm_as(invoker_id, *args),
    }
    exec(contract_code, namespace)
    return namespace["result"]
```

**Rationale:**
- LLMs are just API calls, not privileged - no reason to forbid
- Agents choose complexity/cost tradeoff for their contracts
- "Pure contracts with workarounds" adds complexity without preventing LLM usage
- Non-determinism accepted (system is already non-deterministic via agents)
- Invoker bears costs, preserving economic accountability

**Cost Model:**
| Operation | Who Pays |
|-----------|----------|
| Simple permission check | Free (pure logic) |
| Contract calls LLM | Invoker |
| Contract invokes other artifacts | Invoker |
| Contract execution time | Invoker (compute) |

**Note:** Contracts still cannot directly mutate world state - they return decisions. The kernel applies state changes.

---

## Contract Composition

Composition is handled by the **caller**, not by contracts invoking each other.

### Pattern: Pre-computed Composition

When artifact needs multiple checks, caller evaluates each:

```python
# Caller-side composition (in kernel)
def check_composed_permission(artifact, action, requester):
    contracts = artifact.access_contracts  # List of contract IDs

    for contract_id in contracts:
        contract = get_contract(contract_id)
        result = contract.check_permission(
            artifact_id=artifact.id,
            action=action,
            requester_id=requester,
            artifact_content=artifact.content,
            context={"created_by": artifact.created_by, ...}
        )
        if not result.allowed:
            return result  # AND composition: first failure stops

    return PermissionResult(allowed=True, reason="All checks passed")
```

### Pattern: Meta-Contract

A contract can encode composition logic internally:

```python
# Contract that checks multiple conditions
def check_permission(artifact_id, action, requester_id, artifact_content, context):
    # Check 1: Is requester the creator?
    is_creator = (requester_id == context["created_by"])

    # Check 2: Is artifact marked public?
    is_public = artifact_content.get("public", False)

    # Check 3: Is requester in allowlist?
    allowlist = artifact_content.get("allowlist", [])
    is_allowed = (requester_id in allowlist)

    # Compose: creator OR public OR allowlisted
    if is_creator or is_public or is_allowed:
        return {"allowed": True, "reason": "Access granted"}
    return {"allowed": False, "reason": "Not authorized"}
```

---

## No Owner Bypass

The `access_contract_id` is the ONLY authority. There is no kernel-level owner bypass.

```python
# WRONG - owner bypass breaks contract system
def can_access(artifact, action, requester):
    if requester == artifact.owner_id:
        return True  # BAD: kernel knows nothing about "owner"
    return check_contract(...)

# RIGHT - contract is only authority
def can_access(artifact, action, requester):
    return check_contract(artifact.access_contract_id, artifact, action, requester)
```

If you want owner-based access, your contract implements it. The kernel doesn't know what an "owner" is.

---

## Performance Considerations

### Caching for All Contracts (Certainty: 80%)

All contracts can opt into fast-path caching. No genesis privilege.

```python
# Contract declares caching behavior
{
    "id": "genesis_freeware",
    "can_execute": True,
    "cache_policy": {
        "cacheable": True,
        "ttl_seconds": 3600,
        "cache_key": ["artifact_id", "action", "requester_id"]
    }
}

# Permission check uses cache
def check_permission_cached(artifact, action, requester):
    contract = get_contract(artifact.access_contract_id)
    cache_key = (artifact.access_contract_id, artifact.id, action, requester)

    if cache_key in permission_cache:
        return permission_cache[cache_key]

    result = execute_contract(contract, artifact, action, requester)

    if contract.cache_policy.cacheable:
        permission_cache[cache_key] = result
        expire_at(cache_key, contract.cache_policy.ttl_seconds)

    return result
```

**Benefits:**
- Genesis and user contracts equally fast when cached
- Contracts control their own cache behavior
- Dynamic contracts can disable caching

**Cache invalidation:**
- TTL expiry (configurable per contract)
- Explicit invalidation when artifact content changes
- Explicit invalidation when contract itself changes

**Uncertainty:** Cache invalidation is hard. May see stale permission results.

---

## Migration Notes

### Breaking Changes
- Remove `policy` field from Artifact (allow_read, read_price, etc.)
- Add `access_contract_id` field (required)
- Permission checks become contract invocations

### Preserved
- Owner concept (implemented in contracts, not kernel)
- Access control logic (moved to contract code)

### New Components
- Genesis contracts (genesis_freeware, etc.)
- Contract invocation in permission checks
- check_permission interface standard
