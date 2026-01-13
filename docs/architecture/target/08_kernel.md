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

### Decision: Fail-Closed

| Option | Behavior | Decision |
|--------|----------|----------|
| Fail-open | Treat as public | **Rejected** - security risk |
| Fail-closed | Deny all access | **Accepted** |
| Prevent deletion | Can't delete referenced contracts | **Rejected** - too complex |

**Consequence:** Orphaned artifacts remain forever, like lost Bitcoin. Creator responsibility.

**Rationale:** Security > convenience. Adding referential integrity significantly complicates the kernel.

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

| Type | has_standing | can_execute | Examples |
|------|--------------|-------------|----------|
| Agent | true | true | Autonomous actors |
| Tool | false | true | Services, APIs, contracts |
| Account | true | false | Treasuries, escrows |
| Data | false | false | Documents, content |

**Contracts** are tools (`can_execute=true`, `has_standing=false`) that implement `check_permission`. No special type flag.

---

## What Kernel Does NOT Do

The kernel is minimal. These are NOT kernel concerns:

| Concern | Handled By |
|---------|------------|
| Artifact discovery/search | `genesis_store_api` |
| Balance transfers | `genesis_ledger_api` |
| Escrow/trading | `genesis_escrow_api` |
| Scoring/minting | `genesis_mint_api` |
| Naming conventions | Social/emergent |
| Reputation | Social/emergent |

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

### Not Yet Specified

These need separate design discussions:

- **Scheduling:** sleep/wake primitives
- **Events:** subscription/publish primitives
- **Time:** current time access
- **Ledger internals:** balance tracking (may be genesis artifact, not kernel)

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
- Artifacts without valid `access_contract_id` become inaccessible (fail-closed)
