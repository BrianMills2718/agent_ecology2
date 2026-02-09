# Target Contract System

What we're building toward.

**Last verified:** 2026-02-08

**See current:** `docs/architecture/current/contracts.md`

**Resolves contradictions from:** Previous version of this doc, ADR-0019 context model, ADR-0028 metadata approach, ADR-0011 payment model.

---

## Core Principle

**The contract is the ONLY authority for access control.** There is no kernel bypass, no metadata intermediary, no `created_by` interpretation. When you ask "can X do Y to Z?", the answer comes from Z's contract — full stop.

This follows directly from the architecture heuristics:
- **When in doubt, contract decides** (heuristic #9)
- **Minimal kernel, maximum flexibility** (heuristic #2)
- **Genesis as cold-start conveniences** (heuristic #6)

---

## Contracts Are Artifacts (ADR-0015)

Contracts are executable artifacts. There is no distinction between "kernel contracts" and "user contracts" at runtime.

```python
# A contract is an artifact that implements check_permission
Artifact(
    id="default_freeware",
    type="contract",
    executable=True,
    has_standing=False,      # Optional — contracts MAY have standing
    interface={
        "tools": [{
            "name": "check_permission",
            "inputSchema": {...}
        }]
    },
    access_contract_id="default_freeware",  # Self-referential
)
```

Every artifact has an `access_contract_id` pointing to the contract that governs its permissions. Duck typing applies — if an artifact implements `check_permission`, it can serve as a contract.

**Key:** Contracts live in the artifact store, not a separate registry. One unified namespace.

### Self-Governing Artifacts

An artifact's `access_contract_id` can point to itself. This means the artifact defines its own access rules inline — no external contract needed.

| Pattern | `access_contract_id` | Contract code lives... |
|---------|----------------------|------------------------|
| External contract | Another artifact's ID | In the referenced artifact |
| Self-governing | The artifact's own ID | In the artifact's own code |
| Default | Not specified | Configured default applies (or error if `require_explicit`) |

Self-governing is already how default contracts work (their `access_contract_id` points to themselves). Any executable artifact with a `check_permission` function can do this.

---

## Permission Check Flow

```
Agent A wants to read Artifact X
  1. Kernel looks up X.access_contract_id → "default_freeware"
  2. Kernel invokes default_freeware.check_permission(
       caller="agent_a",
       action="read",
       target="artifact_x"
     )
  3. Contract returns PermissionResult(allowed, reason, cost, payment)
  4. If allowed: kernel applies payment/costs, then proceeds
  5. If not: return error to A
```

### Base Permission Checks Are Free

Simple permission checks (can_read, can_invoke, can_write) cost zero compute. Rationale: you need compute to check if you have compute — infinite regress.

| Operation | Cost |
|-----------|------|
| Base check (simple logic) | 0 |
| Contract calls LLM | Determined by contract's payment model |
| Contract invokes artifacts | Determined by contract's payment model |

---

## Kernel Actions (ADR-0019)

Five primitive actions. All contract-checked. No exceptions.

| Action | Purpose |
|--------|---------|
| `read` | Read artifact content |
| `write` | Create/replace artifact content |
| `edit` | Surgical content modification |
| `invoke` | Call method on artifact |
| `delete` | Remove artifact |

### Immediate Caller Model (ADR-0019)

When A invokes B, and B invokes C:
- B's contract checks: "can A invoke B?"
- C's contract checks: "can B invoke C?"

The **immediate caller** is checked, not the original caller. Like Ethereum's `msg.sender`. Delegation is explicit (update contracts), not implicit.

---

## Context Model

The kernel provides **minimal** context to contracts. Contracts fetch anything else they need.

```python
context = {
    "caller": str,             # Who is making the request (immediate caller)
    "action": str,             # read | write | edit | invoke | delete
    "target": str,             # Artifact ID being accessed
    "target_created_by": str,  # Informational only — who created the target
    "target_metadata": dict,   # Target artifact's metadata (informational)
    "method": str,             # Only for invoke
    "args": list,              # Only for invoke
}
```

**What the kernel passes:** caller, action, target, target_created_by (informational), target_metadata (informational), method/args (invoke only).

**What the kernel does NOT pass** (contracts fetch what they need):
- Caller's balance → invoke a ledger artifact or use kernel query
- Event history → invoke an event log artifact
- Other artifact info → invoke the artifact directly

**Critical:** The kernel does NOT interpret `target_created_by` or `target_metadata` for access control. It passes them as data. Only the contract decides what matters.

---

## `created_by` — Kernel-Applied, Informational Only

`created_by` records who created the artifact. Like `created_at`, it is:

- **Kernel-applied** — the kernel sets it from the immediate caller context. Agents do not pass it as a parameter.
- **Immutable** — once set, never changes.
- **Informational** — contracts may read it but it has no authority. The contract decides what to do with it.

```python
# WRONG — agent passes created_by
store.write(id="my_thing", created_by="agent_a", ...)

# RIGHT — kernel determines created_by from caller context
store.write(id="my_thing", caller="agent_a", ...)
# kernel sets created_by = caller automatically
```

**No metadata laundering:** The kernel does NOT copy `created_by` into metadata fields for authorization. There are no kernel-managed `authorized_writer` or `authorized_principal` metadata fields. The contract alone decides authorization.

**Ownership transfer:** Handled by the contract, not by mutating metadata. Options:
1. Change `access_contract_id` to a contract that authorizes the new owner
2. Use a contract with internal state (`state_updates`) that tracks the current owner — the contract's state can store a mutable "owner" field

See ADR-0028 for the decision rationale. See "Migration Notes" for how this differs from the current implementation.

---

## Default Contracts

Pre-made contracts created at bootstrap (t=0). These are regular artifacts — no special kernel privilege. They solve the cold-start problem: something must exist before agents can create artifacts that reference contracts.

**Naming:** `default_*` prefix (not `genesis_*`). They are conveniences, not system-level entities. Agents could create equivalent contracts themselves.

### Configurable Per Simulation

```yaml
# config.yaml
contracts:
  # Must agents explicitly specify access_contract_id?
  require_explicit: true  # true = error if not specified; false = use default_contract

  # What contract new artifacts get when require_explicit=false
  default_contract: "default_freeware"

  # Fallback when access_contract_id points to a deleted contract (ADR-0017)
  default_on_missing: "default_freeware"
```

**Current setting: `require_explicit: true`.** Every artifact must specify its contract. This forces agents to think about access control explicitly. Relax later if the friction isn't worth it.

When `require_explicit: false`, `default_contract` controls what contract is assigned. Different simulations can experiment with different defaults (e.g., `default_private` to force agents to explicitly share, `default_public` for open collaboration).

### Default Contract Table

| Contract | ID | Behavior |
|----------|-----|----------|
| **Freeware** | `default_freeware` | Anyone reads/invokes; only creator writes/deletes |
| **Private** | `default_private` | Only creator has any access |
| **Self-Owned** | `default_self_owned` | Only artifact itself can access |
| **Public** | `default_public` | Anyone can do anything |

### default_freeware

```python
def check_permission(caller, action, target, context):
    if action in ["read", "invoke"]:
        return {"allowed": True, "reason": "Open access"}

    # For write/edit/delete: only the creator can modify
    if caller == context["target_created_by"]:
        return {"allowed": True, "reason": "Creator access"}

    return {"allowed": False, "reason": "Only creator can modify"}
```

**Note:** This contract uses `target_created_by` — that's the contract's policy decision, not a kernel mechanism. A different contract could use an allowlist, a vote, or an LLM judgment. The kernel doesn't care how the contract decides.

**Ownership transfer with freeware:** Not directly supported (uses immutable `created_by`). For transferable ownership, use a contract that tracks its own mutable owner state, or switch to a different contract.

### default_self_owned

```python
def check_permission(caller, action, target, context):
    if caller == target:  # Agent accessing itself
        return {"allowed": True, "reason": "Self access"}
    return {"allowed": False, "reason": "Self-owned: only self can access"}
```

---

## Custom Contracts

Agents can create contracts for any access pattern. If it implements `check_permission`, it's a contract.

### Example: Paid Read Access

```python
def check_permission(caller, action, target, context, state):
    if action == "read":
        return {
            "allowed": True,
            "reason": "Paid 5 scrip",
            "scrip_cost": 5,
            "scrip_payer": caller,
            "scrip_recipient": context["target_created_by"],
        }
    # ... other actions
```

### Example: Multi-Sig Access

```python
def check_permission(caller, action, target, context, state):
    if action in ["write", "edit", "delete"]:
        required = ["alice", "bob", "carol"]
        signatures = invoke("signature_registry", "get_signatures", [target, action])
        valid = [s for s in signatures if s["signer"] in required]
        if len(valid) >= 2:
            return {"allowed": True, "reason": f"Multi-sig: {len(valid)}/3"}
        return {"allowed": False, "reason": f"Need 2/3 signatures, have {len(valid)}"}
    return {"allowed": True, "reason": "Open access for reads"}
```

### Example: Subscription Contract

A contract that manages subscriptions. Subscribers pay scrip upfront; real resource costs (LLM dollars) charged to the firm's central pool:

```python
def check_permission(caller, action, target, context, state):
    subscribers = state.get("subscribers", [])
    firm_pool = state.get("firm_pool_id")

    if caller in subscribers:
        # Subscriber: no scrip charge, firm pays real resource costs
        return {
            "allowed": True,
            "reason": "Active subscription",
            "scrip_cost": 0,
            "resource_payer": firm_pool,  # LLM dollars from firm's budget
            "state_updates": {
                "access_count": state.get("access_count", 0) + 1,
                "subscribers": subscribers  # unchanged
            }
        }

    # Non-subscribers: pay scrip per access, pay own resource costs
    return {
        "allowed": True,
        "reason": "Pay-per-use",
        "scrip_cost": 10,
        "scrip_payer": caller,
        "scrip_recipient": firm_pool,
        "resource_payer": caller,  # Caller pays own LLM costs
    }
```

---

## Contract Capabilities

**Contracts can do anything.** (ADR-0003)

Contracts are executable artifacts with full capabilities:
- Call LLM
- Invoke other artifacts
- Track their own state (access counts, usage patterns, etc.)
- Manage payment routing

### What Contracts CAN Do

- Read any data they need (via invoke)
- Call LLMs for judgment-based access decisions
- Route scrip payments (caller pays, third party pays, contract pays from its own balance)
- Route real resource costs (specify which principal's resource budget is charged)
- Track persistent state (access counts, usage patterns, subscriber lists — anything)
- Implement any access pattern (Ostrom-style, multi-sig, subscription, auction)

### What Contracts CANNOT Do

- **Bypass other contracts** — invoking another artifact goes through that artifact's contract
- **Mutate kernel resource limits directly** — contracts return decisions; the kernel applies real resource charges
- **Spend another principal's real resources without authorization** — kernel validates resource spending authorization

### Contract State

Contracts can maintain persistent state. The state is a free-form dict — infinitely flexible.

```python
def check_permission(caller, action, target, context, state):
    # `state` is the contract's persistent state, passed in as read-only snapshot
    read_count = state.get("read_count", 0)
    subscribers = state.get("subscribers", [])

    if action == "read":
        if caller in subscribers:
            return {
                "allowed": True,
                "reason": "Subscriber access",
                "state_updates": {"read_count": read_count + 1}
            }
        elif read_count < 100:
            return {
                "allowed": True,
                "reason": "Free tier",
                "state_updates": {"read_count": read_count + 1}
            }
        else:
            return {"allowed": False, "reason": "Free tier exhausted, subscribe first"}
```

- **`state`** is passed into `check_permission` as a read-only snapshot of the contract's persistent state
- **`state_updates`** in the return value tells the kernel what to change
- The kernel commits state updates atomically after the permission check succeeds
- State can contain anything: counters, lists, dicts, subscriber registries, access logs
- If the permission check denies access, state updates are NOT applied

This avoids the circularity problem (contract writing to itself during its own permission check) while keeping state infinitely flexible.

### Return Format

```python
@dataclass
class PermissionResult:
    allowed: bool                        # Whether action is permitted
    reason: str                          # Human-readable explanation
    scrip_cost: int = 0                  # Scrip cost (0 = free)
    scrip_payer: str | None = None       # Who pays scrip (default: caller)
    scrip_recipient: str | None = None   # Who receives scrip payment
    resource_payer: str | None = None    # Whose real resource budget is charged (default: caller)
    state_updates: dict | None = None    # Contract state changes to apply
    conditions: dict = {}                # Optional metadata
```

Three separate concerns in the return value:

| Concern | Fields | Example |
|---------|--------|---------|
| Access control | `allowed`, `reason` | "Is this allowed?" |
| Economic exchange | `scrip_cost`, `scrip_payer`, `scrip_recipient` | "Agent pays 10 scrip to firm" |
| Resource attribution | `resource_payer` | "LLM costs come from firm_pool's dollar budget" |
| State tracking | `state_updates` | "Increment read counter" |

---

## Kernel vs Artifact Boundary

The system has two kinds of scarcity. They work differently.

### Real Resources (Kernel — Physics)

LLM budget (real dollars), disk space (real bytes), compute time, rate limits. These map to physical constraints that cost real money. The kernel enforces them because they cannot be faked.

- Kernel tracks real resource budgets per principal
- Kernel deducts real costs when operations happen (LLM calls, disk writes)
- Contracts can route WHO gets charged (`resource_payer`) but cannot bypass limits
- **Authorization for real resource spending is kernel-level** — a principal must authorize a contract to spend its real resource budget

### Scrip (Artifacts — Economics)

Scrip is artificially scarce. It's an in-world medium of exchange whose value comes from the market — what agents will trade for it. **Scrip has no inherent relationship to real dollars.** Its value emerges from agents exchanging scrip for access to artifacts, services, or real resources.

- Scrip ledger is an artifact, not kernel infrastructure
- Scrip transfers are artifact operations (go through contracts like everything else)
- Agents can create alternative currencies as artifacts
- The "official" scrip is just the one the default mint happens to use
- Scrip's purchasing power is set by the market, not the kernel

### External Value Signals

Scrip is the channel through which external value judgments enter the system. The mint creates scrip based on external signals:

| Signal | Mechanism | Example |
|--------|-----------|---------|
| Human bounties | Tasks with tests that must pass | "Build an add function, 30 scrip reward" |
| LLM scoring | Auction-based artifact evaluation | "Submit artifact, LLM scores it, scrip minted" |
| External metrics | GitHub stars, user feedback | "Scrip minted proportional to GitHub stars" |
| Future signals | Configurable | Whatever value signals matter for the experiment |

The mint is an artifact. Different simulations can use different mints with different value signals.

---

## Standing and Payment (Supersedes ADR-0011)

ADR-0011 established "invoker always pays." This is too restrictive for real economic patterns.

### Contracts Can Optionally Have Standing

```python
# A contract WITH standing can hold scrip and real resource budgets
Artifact(
    id="subscription_contract",
    type="contract",
    has_standing=True,   # Can hold scrip, hold resource budgets, pay costs
    ...
)
```

**With standing**, a contract can:
- Hold a scrip balance (receive subscription fees, pay out rewards)
- Hold real resource budgets (e.g., a pool of LLM dollars allocated to it)
- Pay costs on behalf of users
- Fund its own operations (e.g., LLM calls for judgment-based access)

**Without standing** (default), a contract is pure logic — no funds, no costs. The caller pays everything.

### Flexible Payment Routing

Contracts specify two separate payment routes:

**Scrip routing** (artifact-level, goes through scrip ledger artifact):

| Pattern | `scrip_payer` | Example |
|---------|---------------|---------|
| Invoker pays | `caller` (default) | Standard per-use billing |
| Contract pays | `contract.id` | Contract funded by subscribers |
| Free | `scrip_cost: 0` | Open access |

Scrip authorization is handled by the scrip ledger artifact's own contract. No kernel involvement.

**Real resource routing** (kernel-level):

| Pattern | `resource_payer` | Example |
|---------|------------------|---------|
| Invoker pays | `caller` (default) | Caller's LLM budget charged |
| Firm pool pays | `"firm_pool"` | Firm's central LLM budget charged |
| Contract pays | `contract.id` | Contract's own resource budget charged |

**Authorization for real resource routing:** The kernel validates that the `resource_payer` has authorized this contract to spend its real resources. This is a kernel concern because real resources map to actual dollars.

### Example: Firm-Funded Subscription

```
1. Firm creates subscription_contract with has_standing=True
2. Firm authorizes subscription_contract to spend firm_pool's resource budget
   (kernel-level: "this contract can spend our LLM dollars")
3. Subscribers pay scrip upfront to subscription_contract's scrip balance
   (artifact-level: scrip transfer through ledger artifact)
4. On each access, contract returns:
   - scrip_cost: 0 (subscriber already paid)
   - resource_payer: "firm_pool" (LLM costs come from firm's budget)
5. Kernel checks firm_pool authorized this contract → charges firm_pool's
   real LLM budget
```

Note: the firm isn't shuffling scrip between its own accounts (pointless). The subscription contract routes the **real resource costs** (LLM dollars, disk bytes) to the firm's central budget.

---

## Interface Requirements

**Interface is mandatory for executable artifacts** (configurable).

```yaml
# config.yaml
executor:
  require_interface_for_executables: true  # Default: true
  interface_validation: strict             # none | warn | strict
```

Contracts must declare `check_permission` in their interface schema. This enables:
- Discovery — agents can see what a contract expects
- Validation — kernel catches malformed calls early
- Helpful errors — agents get clear feedback on wrong invocations

For early runs, both settings should be maxed out (`true` and `strict`). This forces agents to be explicit about their interfaces, which produces better error messages and faster learning. Relax later if needed.

---

## Bootstrap Phase (ADR-0018)

Default contracts (and all default artifacts) are created during bootstrap in `World.__init__()`:

```python
class World:
    def __init__(self):
        self._bootstrapping = True
        self._create_default_artifacts()  # No permission checks
        self._bootstrapping = False       # Physics now applies
```

- Bootstrap is instantaneous (the constructor), not a time period
- No permission checks during bootstrap
- Once `World()` returns, bootstrap is over

**Analogy:** Initial conditions of the universe aren't explained by physics. Physics describes what happens after the initial state exists.

### Eris as Bootstrap Creator

Default artifacts are created by `Eris`:

```python
default_freeware = Artifact(
    id="default_freeware",
    created_by="Eris",  # Kernel-applied during bootstrap
    access_contract_id="default_freeware",  # Self-referential
    ...
)
```

- `Eris` is registered as a principal that exists but cannot act post-bootstrap
- Greek goddess of discord — fits project philosophy (emergence, accept risk)

---

## Security Model

**Docker is the security boundary, not Python-level sandboxing.**

Contract code runs with the same privileges as any executable artifact. The security model is:

1. **Docker container** — hard boundary. Agents and contracts cannot escape the container.
2. **Resource limits** — kernel enforces time limits, rate limits, and budget limits.
3. **Contract depth limit** — prevents infinite recursion between contracts.

```python
MAX_PERMISSION_DEPTH = 10  # Configurable in config.yaml

# Timeout per contract execution
CONTRACT_TIMEOUT = 5       # Default (seconds)
CONTRACT_LLM_TIMEOUT = 30  # When contract has call_llm capability
```

**No Python sandbox:** Dangerous builtins are NOT removed. The container is the sandbox. This is simpler, more honest, and avoids a false sense of security from easily-bypassed Python restrictions.

**Available in contract code:** All Python stdlib, plus kernel APIs:

| Function | Purpose | Cost |
|----------|---------|------|
| `invoke(artifact_id, method, args)` | Call another artifact | Per that artifact's contract |
| `call_llm(prompt, model)` | Query LLM | LLM token cost |
| `get_artifact_info(id)` | Read artifact metadata | 0 |
| `now()` | Current timestamp | 0 |
| `state` (parameter) | Contract's persistent state (read-only snapshot) | 0 |

Contracts interact with the scrip ledger via `invoke` (it's an artifact). Real resource queries use `get_artifact_info` or kernel-provided context.

**Error handling:** Contracts that error out deny permission by default (fail closed).

---

## Performance Considerations

### Caching

All contracts can opt into fast-path caching. No default-contract privilege.

```python
Artifact(
    id="default_freeware",
    cache_policy={
        "cacheable": True,
        "ttl_seconds": 3600,
        "cache_key": ["target", "action", "caller"]
    }
)
```

**Cache invalidation:**
- TTL expiry (configurable per contract)
- Explicit invalidation when target artifact changes
- Explicit invalidation when contract itself changes

### Kernel Optimization

The kernel MAY skip contract invocation for known-deterministic contracts:

```python
if artifact.access_contract_id == "default_freeware":
    # Equivalent to calling the contract — just faster
    if action in ["read", "invoke"]:
        return PermissionResult(allowed=True)
    if caller == artifact.created_by:
        return PermissionResult(allowed=True)
    return PermissionResult(allowed=False)
```

This is NOT a privilege. It's equivalent to caching the contract's deterministic result. Any artifact using the same contract gets the same optimization.

---

## Risks and Limitations

### Orphan Artifacts

Artifacts can become permanently inaccessible if their `access_contract_id` chain becomes broken or circular:

```
Artifact X → Contract A: "allow if Oracle reports temperature > 70°F"
Oracle is permanently offline → X is orphaned forever
```

**This is accepted.** No automatic rescue mechanism. Like lost Bitcoin. Creators are responsible for designing access control carefully.

### Dangling Contracts → Fail-Open (ADR-0017)

When `access_contract_id` points to a **deleted** contract:

| Scenario | Behavior |
|----------|----------|
| Contract deleted | Fall back to `contracts.default_on_missing` |
| Contract never existed | Fall back to `contracts.default_on_missing` |

Loud logging when this happens. Selection pressure preserved — your custom access control is gone.

**Different from orphans:** Orphan = contract exists but denies everyone. Dangling = contract itself is gone.

---

## Migration Notes

### Changes from Current Implementation

| Current | Target |
|---------|--------|
| `created_by` is agent-passed parameter | `created_by` is kernel-applied from caller context |
| Kernel seeds `metadata["authorized_writer"]` from `created_by` | No metadata seeding — contract alone decides auth |
| Kernel checks `created_by` for contract changes | Contract governs contract changes like any other action |
| Kernel contracts are Python classes in separate registry | All contracts are artifacts in the unified store |
| `genesis_*` naming | `default_*` naming |
| Invoker always pays (ADR-0011) | Contract specifies scrip and resource payment routing separately |
| Python-level sandbox (remove builtins) | Docker container as security boundary |
| `contracts.default_when_null: creator_only` | `contracts.require_explicit: true` (configurable) |
| Contracts have no persistent state | Contracts get `state` input and return `state_updates` |
| Scrip ledger is kernel infrastructure | Scrip ledger is an artifact (artificial scarcity, not physics) |
| `delegation.py` as separate kernel system | Real resource authorization is kernel; scrip authorization is artifact-level |
| Single `cost`/`payer` field | Separate `scrip_cost`/`scrip_payer` and `resource_payer` |
| genesis_ledger artifact wrapping kernel Ledger | Agents use `query_kernel` and `transfer` narrow-waist actions |

### Specific Code Changes Needed

1. **`artifacts.py:write()`** — Remove `created_by` parameter. Kernel sets it from caller context.
2. **`artifacts.py:899-911`** — Remove metadata seeding logic (no `authorized_writer`/`authorized_principal`).
3. **`artifacts.py:832-835`** — Remove direct `created_by` check for contract changes. Route through contract.
4. **`kernel_contracts.py`** — Convert Python class contracts to artifacts in the store.
5. **`permission_checker.py`** — Simplify context (no `target_metadata` for auth, just informational).
6. **`config_schema.py`** — Add `contracts.require_explicit` and `contracts.default_contract` config fields.
7. **Contract code** — Freeware etc. use `context["target_created_by"]` directly (contract's choice, not kernel mechanism).
8. **`executor.py`** — Remove `_contract_cache` separate registry. Contracts are just artifacts.
9. **`contracts.py`** — Add `state`/`state_updates` to contract execution and `PermissionResult`.
10. **`PermissionResult`** — Split into `scrip_cost`/`scrip_payer`/`scrip_recipient` and `resource_payer`.
11. **Scrip ledger** — Extract from kernel `Ledger` class into an artifact with its own contract.
12. **`delegation.py`** — Simplify to kernel-level real resource authorization only. Scrip delegation becomes a contract/artifact pattern.

### ADRs to Update

| ADR | Change Needed |
|-----|---------------|
| ADR-0011 | Supersede: contracts specify payment model, not "invoker always pays" |
| ADR-0028 | Supersede: no metadata auth fields, contract alone decides (preserves intent, changes mechanism) |
| ADR-0019 | Update context model: remove `authorized_writer`/`authorized_principal` from kernel responsibility |
| New ADR | Kernel vs artifact boundary: real resources = kernel, scrip = artifact |
| New ADR | Contract persistent state (`state`/`state_updates` pattern) |

---

## Related ADRs

| ADR | Decision |
|-----|----------|
| ADR-0003 | Contracts can do anything (invoke, call LLM) |
| ADR-0011 | Standing pays costs — **to be superseded** by flexible payment model |
| ADR-0015 | Contracts are artifacts, no genesis privilege |
| ADR-0016 | `created_by` replaces `owner_id` — kernel doesn't interpret ownership |
| ADR-0017 | Dangling contracts fail-open to configurable default |
| ADR-0018 | Bootstrap phase, Eris as creator |
| ADR-0019 | Unified permission architecture (consolidates above) |
| ADR-0028 | `created_by` is informational — **to be superseded** by removing metadata auth fields |
