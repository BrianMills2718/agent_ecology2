# Target Kernel Primitives

What we're building toward: the "physics" layer.

**Last verified:** 2026-01-13

**See also:** [01_README.md](01_README.md) - System vs Genesis distinction

---

## Design Principle

The kernel is "physics" - prerequisites for artifacts to exist. Everything else is built on top.

**Goal:** Maximum flexibility. Restrict as little as possible. Let agents figure out the rest.

**Rule:** The kernel defines what's POSSIBLE. Genesis artifacts define what's CONVENIENT.

---

## Storage Primitives

Raw byte storage. The foundation everything else builds on.

### Internal Primitives

These are kernel-internal. Artifact code accesses them through permission-checked wrappers.

```python
_store(id: str, data: bytes) -> void    # Store bytes at ID
_load(id: str) -> bytes | null          # Retrieve bytes by ID
_exists(id: str) -> bool                # Check if ID exists
_delete(id: str) -> void                # Remove bytes at ID
```

### Behavior

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| ID generation | Caller provides | Meaningful names are valuable |
| ID collision | Error (first-come-first-served) | Squatting is accepted as emergent behavior |
| Overwrite | Allowed (same ID overwrites) | Mutability useful; contracts can enforce immutability |
| Delete | Supported | Disk is actually scarce |

### Kernel-Tracked Metadata

The kernel automatically tracks:

| Field | Type | Description |
|-------|------|-------------|
| `creator` | string | Who made the create call (immutable fact) |
| `created_at` | timestamp | When first stored |
| `updated_at` | timestamp | When last modified |
| `size_bytes` | int | Current data size |

**NOT kernel-tracked:** `owner`. Ownership is tracked by genesis_store as a service, not kernel metadata. See [Creator vs Owner](#creator-vs-owner).

**Rationale:** Observability doesn't restrict flexibility. Creator is immutable fact; owner is mutable social concept.

### Resource Costs

| Operation | Cost | Rationale |
|-----------|------|-----------|
| Write | Disk quota | Actually scarce |
| Read | Free | Not scarce at 1000+ agents (SSDs handle 100k+ IOPS) |
| Delete | Free (reclaims quota) | Encourages cleanup |

**Rule:** Don't introduce artificial scarcity. Don't pretend scarce things aren't scarce.

---

## Permission Model

How artifacts access kernel storage.

### Access Flow

```
Artifact code calls kernel.store(artifact_id, data)
  -> Kernel identifies current caller
  -> Kernel checks caller's permission via artifact's access_contract_id
  -> If allowed: execute raw storage
  -> If denied: error
```

### Key Properties

| Property | Value | Rationale |
|----------|-------|-----------|
| Genesis artifacts privileged? | **No** | Anyone could build `better_store_api` |
| Permission check on kernel? | Kernel bypasses (it's physics) | Avoids infinite regress |
| Contract code permission checks? | Yes, subject to depth limit | Prevents loops |

### Contract = Any Artifact with check_permission

No special "contract" type. Interface-based detection:

```python
# Kernel checks if artifact can be used as a contract:
if "check_permission" in artifact.interface.methods:
    # Can be used as access_contract_id
```

**Rationale:** More flexible. Artifacts can be both tools AND contracts if they implement the method.

### Each Invocation Link Independent

```
A invokes B -> B's contract checks "can A invoke?"
B writes X -> X's contract checks "can B write?"
```

- Immediate caller matters, not original caller
- Each contract makes its own trust decision
- No call stack tracking needed

**Rationale:** Simpler model. Delegation is explicit (update contracts), not implicit.

---

## Circular Governance

Artifacts can have circular `access_contract_id` references.

### Why It's Safe

```
freeware_contract.access_contract_id = "self_owned_contract"
self_owned_contract.access_contract_id = "freeware_contract"
```

This is just data. The kernel can call `check_permission` directly without permission (it's physics).

### When Loops Actually Happen

Only when contract CODE invokes other artifacts that create a cycle:

```python
# Dangerous contract code:
def check_permission(requester, target, action):
    # This invocation could loop back
    result = invoke("other_contract", "validate", {...})
    return result
```

### Mitigation

Configurable depth limit OR cycle detection:

```python
MAX_PERMISSION_DEPTH = 10  # Configurable

def check_permission(artifact, action, requester, depth=0):
    if depth > MAX_PERMISSION_DEPTH:
        return {"allowed": False, "reason": "Depth exceeded"}
    # ... rest of check
```

**Preference:** Cycle detection is more precise (allows deep non-circular chains), but depth limit is simpler.

**Important:** Exceeding depth denies THIS request. Artifact is NOT permanently orphaned. Someone with a shallower path could still access, or contracts could be reorganized.

---

## Bootstrap / Genesis

How the system starts at T=0.

### Genesis Contract Self-Governance

Genesis contracts reference themselves:

```python
freeware_contract = {
    "id": "freeware_contract",
    "access_contract_id": "freeware_contract",  # Self-referential
    "creator": "genesis",  # Reserved value
    ...
}
```

**Why this works:** Kernel can call `check_permission` directly. Self-reference doesn't cause loops at kernel level.

### Creation Order

1. Create genesis contracts (self-governing)
2. Create other genesis artifacts pointing to those contracts

**No special bootstrap mode needed.**

### Reserved Creator Value

Genesis artifacts have `creator: "genesis"` - a reserved value no agent can impersonate.

---

## Creator vs Owner

Two distinct concepts with different homes:

| Field | Where | Mutable? | Purpose |
|-------|-------|----------|---------|
| `creator` | Kernel metadata | No | Who actually made the create call (fact of history) |
| `owner` | genesis_store data | Yes (via contracts) | Social/economic concept, contracts interpret |

**Key decision:** Owner is NOT kernel metadata. Genesis_store tracks ownership as a service.

**Rationale:**
- Creator is a fact the kernel observes at creation time (immutable history)
- Owner is a social concept with no privileged kernel meaning
- Keeping owner out of kernel maintains "maximum flexibility" principle
- Genesis_store can provide ownership tracking; contracts query when needed
- Alternative ownership models can emerge without kernel changes

---

## Dangling Contracts

What happens when `access_contract_id` points to a deleted contract?

### Decision: Fail-Open (ADR-0017, ADR-0019)

| Option | Behavior | Decision |
|--------|----------|----------|
| Fail-open | Fall back to configurable default | **Accepted** |
| Fail-closed | Deny all access | **Rejected** - too punitive |
| Prevent deletion | Can't delete referenced contracts | **Rejected** - too complex |

**Behavior:** When contract is deleted, artifact falls back to configurable default contract (freeware by default).

**Consequence:** Custom access control is lost (selection pressure preserved), but artifact remains accessible.

**Rationale:** Accept risk, observe outcomes. Fail-closed is punitive without learning benefit.

### Null vs Dangling

| Scenario | Behavior |
|----------|----------|
| `access_contract_id = null` | Default policy: creator has full rights, others blocked |
| `access_contract_id` → deleted | Fall back to configurable default contract |

See ADR-0019 for the unified permission architecture.

---

## Concurrency

Multiple agents acting simultaneously.

### Kernel Guarantees

| Operation | Behavior |
|-----------|----------|
| Create (same ID) | First writer wins, second gets error |
| Write (same artifact) | Serialized (implementation chooses last-writer-wins or conflict error) |
| Delete | Idempotent |

**Implementation:** SQLite/Postgres handles atomicity naturally.

---

## Self-Modification

Can an artifact modify itself?

### Decision: Allowed

If artifact A's contract permits A to write to A, then A can modify its own content.

**Rationale:** Intentional flexibility. Enables:
- Self-improvement
- Learning
- Adaptation

**Risk:** Instability. Agents are responsible for their own coherence.

---

## Naming Conventions

### Genesis Artifacts

Two categories with distinct suffixes:

**Services/APIs** (interfaces to kernel capabilities):
- `genesis_ledger_api`
- `genesis_store_api`
- `genesis_mint_api`

**Contracts** (permission policies):
- `freeware_contract`
- `private_contract`
- `self_owned_contract`

**Rationale:**
- `_api` clarifies these are interfaces, not the data itself
- `_contract` distinguishes from tools
- Avoids confusion (e.g., "genesis_store" sounds like a database, not an accessor)

**Open question (50% certainty):** Drop `genesis_` prefix entirely? They're just defaults, not special.

---

## Artifact Type Reference

From [03_agents.md](03_agents.md):

| Type | has_standing | has_loop | Examples |
|------|--------------|-------------|----------|
| Agent | true | true | Autonomous actors |
| Tool | false | true | Services, APIs, contracts |
| Account | true | false | Treasuries, escrows |
| Data | false | false | Documents, content |

**Contracts** are tools (`has_loop=true`, `has_standing=false`) that implement `check_permission`. No special type flag.

---

## What Kernel Does vs Doesn't Do

### Kernel DOES (Physics Layer)

| Concern | Why Kernel |
|---------|-----------|
| Storage primitives | Foundation for all artifacts |
| Quota tracking | Quotas are physics (what agents CAN do) |
| Rate limiting enforcement | Resource constraints are physics |
| Permission checking | Access control is physics |
| Creator metadata | Immutable fact of history |

### Kernel Does NOT Do

The kernel is minimal. These are NOT kernel concerns:

| Concern | Handled By |
|---------|------------|
| Artifact discovery/search | `genesis_store_api` |
| Scrip balance transfers | `genesis_ledger_api` (scrip is economic signal, not physics) |
| Escrow/trading | `genesis_escrow_contract` |
| Scoring/minting | `genesis_mint_api` |
| Ownership tracking | `genesis_store_api` (mutable social concept) |
| Naming conventions | Social/emergent |
| Reputation | Social/emergent |

**Note:** Quota tracking IS kernel (physics), but genesis_rights_registry_api provides friendly interface. Scrip transfers are NOT kernel because scrip is economic signal, not resource constraint.

---

## Open Questions

| Issue | Certainty | Notes |
|-------|-----------|-------|
| Drop `genesis_` prefix | 50% | Need to decide |
| Depth limit vs cycle detection | 70% | Cycle detection more precise but complex |
| Expensive contract pre-detection | 60% | No good solution for knowing cost before check |

**Resolved:** Creator vs Owner distinction - creator is kernel metadata (immutable fact), owner is genesis_store data (mutable social concept).

---

## Summary: Kernel Primitive List

### Storage (internal, permission-checked access)

```
_store(id: str, data: bytes) -> void
_load(id: str) -> bytes | null
_exists(id: str) -> bool
_delete(id: str) -> void
```

### Metadata (kernel-tracked automatically)

```
creator: string        # Who created (immutable)
created_at: timestamp
updated_at: timestamp
size_bytes: int
```

**NOT kernel-tracked:** `owner` (tracked by genesis_store)

### Quota Primitives (Kernel State)

Quotas are **kernel state**, not genesis artifact state. `genesis_rights_registry_api` is a convenience wrapper, not privileged.

**Kernel-tracked quota data:**
```python
# Per-principal quota metadata (kernel state)
quotas: dict[str, float] = {      # {resource_type: assigned_amount}
    "cpu_seconds_per_minute": 10.0,
    "llm_tokens_per_minute": 1000,
    "disk_bytes": 1_000_000,
}
usage_windows: RollingWindow      # Rolling window for rate limiting
```

**Quota primitives (internal, permission-checked access):**
```python
_get_quota(principal_id: str, resource: str) -> float
_set_quota(principal_id: str, resource: str, amount: float) -> void
_transfer_quota(from_id: str, to_id: str, resource: str, amount: float) -> void
_get_available_capacity(principal_id: str, resource: str) -> float
_consume_quota(principal_id: str, resource: str, amount: float) -> void
```

**Rationale:**
- Quotas are "physics" (what agents CAN do), not social convention
- Kernel enforces quotas before action execution
- genesis_rights_registry_api just wraps these primitives
- Agents could build alternative rights interfaces using same kernel primitives
- Tradeable quotas: `_transfer_quota` is kernel primitive, trading is emergent

**Enforcement:**
```python
# Kernel checks quota BEFORE executing any action
if not _has_capacity(principal_id, resource, estimated_cost):
    return ActionResult(error_code="QUOTA_EXCEEDED", retriable=True)
```

See [Plan #42: Kernel Quota Primitives](../../plans/42_kernel_quota_primitives.md) for implementation.

### Not Yet Specified

These need separate design discussions:

- **Scheduling:** sleep/wake primitives
- **Events:** subscription/publish primitives
- **Time:** current time access

---

## Migration Notes

### New Components
- Kernel storage primitives (internal)
- Permission-checked storage access
- Depth/cycle limit for contract invocation

### Naming Changes
- `genesis_store` -> `genesis_store_api`
- `genesis_ledger` -> `genesis_ledger_api`
- `genesis_freeware` -> `freeware_contract`

### Breaking Changes
- Artifacts with dangling `access_contract_id` fall back to configurable default (ADR-0017, ADR-0019)
- Artifacts with null `access_contract_id` use default policy (creator-only)
