# Target Contract System

What we're building toward.

**Last verified:** 2026-01-21

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

### Kernel Actions (ADR-0019)

Five primitive actions, all contract-checked:

| Action | Purpose | Context Includes |
|--------|---------|------------------|
| `read` | Read artifact content | caller, action, target |
| `write` | Create/replace artifact | caller, action, target |
| `edit` | Surgical content modification | caller, action, target |
| `invoke` | Call method on artifact | caller, action, target, method, args |
| `delete` | Remove artifact | caller, action, target |

Only `invoke` includes method and args in context.

### Immediate Caller Model (ADR-0019)

When A invokes B, and B invokes C:
- B's contract checks: "can A invoke B?"
- C's contract checks: "can B invoke C?"

The **immediate caller** is checked, not the original caller. Delegation is explicit (update contracts) not implicit.

### Minimal Context (ADR-0019)

Kernel provides minimal context to contracts:

```python
context = {
    "caller": str,             # Who is making the request
    "action": str,             # read | write | edit | invoke | delete
    "target": str,             # Artifact ID being accessed
    "target_created_by": str,  # Creator of target (pragmatic inclusion)
    "method": str,             # Only for invoke
    "args": list,              # Only for invoke
}
```

**Included:** caller, action, target, target_created_by, method/args (invoke only)

**NOT included** (contracts fetch via invoke):
- Balances → `genesis_ledger`
- History → `genesis_event_log`
- Other metadata → `genesis_store`

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
                "enum": ["read", "write", "edit", "invoke", "delete"],
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

## Bootstrap Phase (ADR-0018)

Genesis contracts (and all genesis artifacts) are created during a bootstrap phase in `World.__init__()`:

```python
class World:
    def __init__(self):
        self._bootstrapping = True
        self._create_genesis_artifacts()  # No permission checks
        self._bootstrapping = False       # Physics now applies
```

**Key points:**
- Bootstrap is instantaneous (the constructor), not a time period
- No permission checks during bootstrap
- Once `World()` returns, bootstrap is over

**Analogy:** Initial conditions of the universe aren't explained by physics. Physics describes what happens after the initial state exists.

### Eris as Bootstrap Creator

Genesis artifacts are created by `Eris`:

```python
genesis_freeware_contract = Artifact(
    id="genesis_freeware_contract",
    created_by="Eris",
    access_contract_id="genesis_freeware_contract",  # Self-referential
    ...
)
```

**Why Eris?**
- Greek goddess of discord and strife
- Fits project philosophy: emergence over prescription, accept risk
- `Eris` is registered as a principal that exists but cannot act post-bootstrap

### Genesis Naming Convention

| Suffix | Meaning | Example |
|--------|---------|---------|
| `_api` | Accessor to kernel state | `genesis_ledger_api`, `genesis_event_log_api` |
| `_contract` | Access control contract | `genesis_freeware_contract`, `genesis_private_contract` |

The `genesis_` prefix is reserved for system artifacts. Agents cannot create artifacts with this prefix.

---

## Genesis Contracts

Default contracts provided at system initialization. **Genesis contracts are artifacts** - they have no special kernel privilege.

| Contract | Behavior |
|----------|----------|
| `genesis_freeware_contract` | Anyone reads/invokes, only creator writes/deletes |
| `genesis_self_owned_contract` | Only the artifact itself can access (for agent self-control) |
| `genesis_private_contract` | Only creator has any access |
| `genesis_public_contract` | Anyone can do anything |

### genesis_freeware_contract (Default)

```python
def check_permission(artifact_id, action, requester_id):
    artifact = get_artifact(artifact_id)

    if action in ["read", "invoke"]:
        return {"allowed": True, "reason": "Open access"}
    else:  # write, edit, delete
        if requester_id == artifact.created_by:
            return {"allowed": True, "reason": "Creator access"}
        else:
            return {"allowed": False, "reason": "Only creator can modify"}
```

### genesis_self_owned_contract

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
    if action in ["write", "edit", "delete"]:
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
- Call LLM
- Invoke other artifacts
- Make external API calls (weather, databases, oracles)
- Cannot modify state directly (return decision, not mutate)

```python
# Contract execution context - full capabilities
def execute_contract(contract_code: str, inputs: dict, context: dict) -> PermissionResult:
    namespace = {
        "artifact_id": inputs["artifact_id"],
        "action": inputs["action"],
        "requester_id": inputs["requester_id"],
        "artifact_content": inputs["artifact_content"],
        "context": context,

        # Full capabilities - cost model determined by contract
        "invoke": lambda *args: invoke_artifact(*args),
        "call_llm": lambda *args: call_llm(*args),
        "charge": lambda principal, amount: charge_principal(principal, amount),
    }
    exec(contract_code, namespace)
    return namespace["result"]
```

**Rationale:**
- LLMs are just API calls, like weather APIs - no special treatment
- Agents choose complexity/cost tradeoff for their contracts
- Non-determinism accepted (system is already non-deterministic via agents)

### Cost Model: Contract-Specified

Who pays for contract execution is determined by the contract itself, not hardcoded:

```python
# Contract specifies its cost model
{
    "id": "my_contract",
    "cost_model": "invoker_pays",  # or "owner_pays", "artifact_pays", "split"
}

# Or handle dynamically in logic
def check_permission(artifact_id, action, requester_id, context):
    cost = calculate_cost()
    charge(context["artifact_owner"], cost)  # Owner pays
    # or: charge(requester_id, cost)  # Invoker pays
    # ...
```

| Default | Behavior |
|---------|----------|
| `invoker_pays` | Requester bears all costs (sensible default) |
| `owner_pays` | Artifact owner bears costs |
| `split` | Costs divided by contract logic |
| Custom | Contract implements any payment model |

**Note:** Contracts still cannot directly mutate world state - they return decisions. The kernel applies state changes.

### Execution Depth Limit

Contract execution has a depth limit to prevent stack overflow:

```python
MAX_PERMISSION_DEPTH = 10

def check_permission(artifact, action, requester, depth=0):
    if depth > MAX_PERMISSION_DEPTH:
        return {"allowed": False, "reason": "Permission check depth exceeded"}

    contract = get_contract(artifact.access_contract_id)
    return contract.check(artifact, action, requester, depth=depth+1)
```

This prevents: Contract A invokes B → B's check invokes C → C's check invokes A → infinite loop.

### Sandbox Limits

Contract execution is sandboxed to prevent abuse:

**Time limit:**
```python
CONTRACT_TIMEOUT_SECONDS = 30  # Max execution time

async def execute_contract_sandboxed(contract_code: str, inputs: dict) -> PermissionResult:
    try:
        result = await asyncio.wait_for(
            execute_contract(contract_code, inputs),
            timeout=CONTRACT_TIMEOUT_SECONDS
        )
        return result
    except asyncio.TimeoutError:
        return {"allowed": False, "reason": "Contract execution timeout"}
```

**Resource limits:**
- CPU: Contracts run in worker pool, subject to rate limits
- Memory: Worker process memory limits apply
- No disk access: Contracts cannot write to filesystem
- No network access except through provided APIs

**Available APIs in contract namespace:**

| Function | Purpose | Cost |
|----------|---------|------|
| `invoke(artifact_id, args)` | Call another artifact | Artifact's cost model |
| `call_llm(prompt, model)` | Query LLM | LLM token cost |
| `charge(principal, amount)` | Charge scrip | 0 (accounting only) |
| `get_artifact_info(id)` | Read artifact metadata | 0 |
| `get_balance(principal, resource)` | Check balance | 0 |
| `now()` | Current timestamp | 0 |

**NOT available in contracts:**
- `open()`, `os.*`, `subprocess.*` - No filesystem/process access
- `socket.*`, `urllib.*` - No direct network (use `invoke` for APIs)
- `__import__` - No dynamic imports
- `eval()`, `compile()` - No nested code execution

**Error handling:**

```python
def execute_contract(contract_code: str, inputs: dict) -> PermissionResult:
    try:
        exec(contract_code, namespace)
        return namespace.get("result", {"allowed": False, "reason": "No result returned"})
    except Exception as e:
        # Log error but don't expose to requester
        log_contract_error(contract_id, e)
        return {"allowed": False, "reason": "Contract execution error"}
```

Contracts that error out deny permission by default (fail closed).

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

## No Owner Bypass (ADR-0016)

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

**Note:** The kernel stores `created_by` (who created the artifact) but interprets it as historical fact, not authority. Contracts may choose to grant special access to the creator, but that's a policy decision, not kernel semantics. See ADR-0016.

---

## Performance Considerations

### Caching for All Contracts (Certainty: 80%)

All contracts can opt into fast-path caching. No genesis privilege.

```python
# Contract declares caching behavior
{
    "id": "genesis_freeware_contract",
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

## Risks and Limitations

### Orphan Artifacts

Artifacts can become permanently inaccessible if their `access_contract_id` chain becomes broken or circular:

```
Artifact X.access_contract_id → Contract A
Contract A: "allow if Oracle reports temperature > 70°F"
Oracle is permanently offline → X is orphaned forever
```

Or circular:
```
Contract A: "allow if B allows"
Contract B: "allow if C allows"
Contract C: "allow if A allows"
All deny → permanently locked
```

**This is accepted.** No automatic rescue mechanism exists because:

1. **Many loops are valuable** - Mutual interdependence (A controls B, B controls A) is how partnerships and multi-sig work

2. **Detection is impossible** - Contracts can depend on external state, time, LLM interpretation. Cannot statically determine if an artifact is permanently inaccessible

3. **Trustlessness** - Adding backdoors breaks the security model

**Consequence:** Creators are responsible for designing access control carefully. Orphaned artifacts remain forever, like lost Bitcoin.

### Dangling Contracts → Fail-Open (ADR-0017)

When an artifact's `access_contract_id` points to a deleted contract, the system **fails open** to a configurable default contract (freeware by default).

| Scenario | Behavior |
|----------|----------|
| `access_contract_id` → deleted contract | Fall back to default contract |
| `access_contract_id` → non-existent | Fall back to default contract |

**Rationale:**
- **Accept risk, observe outcomes**: Fail-closed is punitive without learning benefit
- **Selection pressure still applies**: Your custom access control is gone - that's the consequence
- **Maximum configurability**: Default contract is configurable per-world

**Warning:** Loud logging occurs when this happens - artifacts falling back to default should be visible to operators.

**Note:** This is different from orphan artifacts (contract exists but denies everyone). Dangling means the contract itself is gone.

See ADR-0017 for full decision rationale.

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
- Genesis contracts (genesis_freeware_contract, etc.)
- Contract invocation in permission checks
- check_permission interface standard

---

## Related ADRs

| ADR | Decision |
|-----|----------|
| ADR-0003 | Contracts can do anything (invoke, call LLM) |
| ADR-0015 | Contracts are artifacts, no genesis privilege |
| ADR-0016 | `created_by` replaces `owner_id` - kernel doesn't interpret ownership |
| ADR-0017 | Dangling contracts fail-open to configurable default |
| ADR-0018 | Bootstrap phase, Eris as creator, genesis naming convention |
| ADR-0019 | Unified permission architecture (consolidates above) |
