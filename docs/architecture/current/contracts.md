# Current Contract System

How access control works today.

**Last verified:** 2026-02-05 (Plan #303: fail-loud audit)

**See also:** ADR-0019 (Unified Permission Architecture)

**Source:** `src/world/contracts.py`, `src/world/genesis_contracts.py`

---

## Overview

Contracts determine who can access artifacts. Every artifact has an `access_contract_id` pointing to a contract that governs permissions.

## Core Types

### PermissionAction

Actions that can be checked (see ADR-0019 for canonical list):

| Action | Description |
|--------|-------------|
| `READ` | Read artifact content |
| `WRITE` | Create/replace artifact content |
| `EDIT` | Surgical content modification |
| `INVOKE` | Call artifact's service interface (method + args) |
| `DELETE` | Delete artifact |

**Note:** Only `INVOKE` includes method/args in context. See ADR-0019 for full context specification.

### PermissionResult

Returned by permission checks:

```python
@dataclass
class PermissionResult:
    allowed: bool      # Whether action is permitted
    reason: str        # Human-readable explanation
    cost: int = 0      # Scrip cost (0 = free, must be non-negative)
    conditions: dict   # Optional metadata
```

### AccessContract Protocol

All contracts implement:

```python
class AccessContract(Protocol):
    contract_id: str
    contract_type: str

    def check_permission(
        self,
        caller: str,
        action: PermissionAction,
        target: str,
        context: dict | None = None,
    ) -> PermissionResult: ...
```

**Context keys** passed to `check_permission` (current implementation):
- `created_by`: Creator of the target artifact
- `artifact_type`: Type of the target artifact
- `caller_type`: Type of the calling principal

**Note:** ADR-0019 specifies minimal context: `caller`, `action`, `target`, `target_created_by`, `method`/`args` (invoke only). Current implementation may provide additional keys. Target is for contracts to fetch extra info via invoke.

---

## Kernel Defaults vs Cold-Start Conveniences

**Important distinction:** These are two separate concepts.

### Kernel Defaults (Infrastructure)

What the kernel does when an artifact has no contract or a null contract. This is kernel policy, configured in `config/config.yaml`:

| Scenario | Config Key | Default Behavior |
|----------|------------|------------------|
| `access_contract_id` is null | `contracts.default_when_null` | `creator_only` - only creator has access |
| Contract was deleted | `contracts.default_on_missing` | Falls back to freeware semantics |

These defaults are kernel infrastructure, not artifacts.

### Cold-Start Conveniences (Genesis Contracts)

Pre-made permission presets available at initialization. Like genesis artifacts (ledger, escrow), these are **conveniences, not privileged**. Agents could build equivalent contracts themselves.

**Important:** Kernel contracts are NOT artifacts. They're Python class instances stored in `KERNEL_CONTRACTS` dict, accessed by ID string (e.g., `"kernel_contract_freeware"`). Custom contracts created by agents ARE artifacts - see ExecutableContract below.

| Contract | ID | Behavior |
|----------|-----|----------|
| **Freeware** | `kernel_contract_freeware` | Anyone reads/invokes; only creator writes/deletes |
| **SelfOwned** | `kernel_contract_self_owned` | Only artifact itself (or creator) can access |
| **Private** | `kernel_contract_private` | Only creator can access |
| **Public** | `kernel_contract_public` | Anyone can do anything |
| **TransferableFreeware** | `kernel_contract_transferable_freeware` | Like freeware + authorized_writer can write |

**Note on `created_by`:** The genesis contracts reference `created_by` for access decisions. This is a contract policy choice, not kernel privilege. `created_by` is just metadata - contracts can use it however they want (or ignore it entirely for pure Ostrom-style rights). Custom contracts can implement any access pattern.

### Common Pattern: Freeware

Most artifacts use freeware-style access:
- Open read access (anyone can see)
- Open invoke access (anyone can use)
- Creator-only writes (only creator can modify)

This is a pragmatic default for cold-start, not a kernel requirement.

---

## How Permission Checks Work

```
Agent A tries to read Artifact X
  ↓
Executor looks up X.access_contract_id
  ↓
Executor calls contract.check_permission(
    caller="agent_a",
    action=PermissionAction.READ,
    target="artifact_x",
    context={"created_by": X.owner_id, "artifact_type": X.type}
)
  ↓
Contract returns PermissionResult(allowed=True/False, ...)
  ↓
Executor proceeds or rejects
```

---

## Custom Contracts (Plan #100)

Agents can create custom contracts as executable artifacts using `ExecutableContract`.

### ExecutableContract

A contract with executable Python code for dynamic permission logic:

```python
@dataclass
class ExecutableContract:
    contract_id: str
    code: str                           # Python code defining check_permission
    contract_type: str = "executable"
    timeout: int | None = None          # Execution timeout (default: 5s, or 30s for LLM)
    capabilities: list[str] = []        # e.g., ["call_llm"]
    cache_policy: dict | None = None    # e.g., {"ttl_seconds": 60}
```

### Contract Code Requirements

The code must define a `check_permission` function:

```python
def check_permission(caller, action, target, context, ledger):
    # caller: str - Principal requesting access
    # action: str - "read", "write", "invoke", etc.
    # target: str - Artifact ID being accessed
    # context: dict - Additional context (owner, tick, etc.)
    # ledger: ReadOnlyLedger - Read-only ledger for balance checks

    return {
        "allowed": True,    # bool - required
        "reason": "...",    # str - required
        "cost": 0           # int - optional, scrip cost
    }
```

### Available in Contract Code

**Modules:** `math`, `json`, `random`, `time`

**Ledger methods** (via `ReadOnlyLedger`):
- `ledger.get_scrip(principal_id)` - Get scrip balance
- `ledger.can_afford_scrip(principal_id, amount)` - Check affordability
- `ledger.get_resource(principal_id, resource)` - Get resource balance
- `ledger.can_spend_resource(principal_id, resource, amount)` - Check resource
- `ledger.get_all_resources(principal_id)` - All resource balances
- `ledger.principal_exists(principal_id)` - Check if principal exists

### Security Sandboxing

Contract code runs in a restricted environment:
- **Dangerous builtins removed:** `open`, `exec`, `eval`, `compile`, `__import__`, `input`, `breakpoint`, `exit`, `quit`
- **Timeout protection:** Default 5 seconds (30s if `call_llm` capability)
- **Read-only ledger access:** Cannot modify balances

### Error Handling

| Exception | When |
|-----------|------|
| `ContractExecutionError` | General execution failure |
| `ContractTimeoutError` | Contract code exceeds timeout |

---

## Permission Caching (Plan #100 Phase 2)

`PermissionCache` provides opt-in TTL-based caching for permission results.

```python
class PermissionCache:
    def get(key: CacheKey) -> PermissionResult | None
    def put(key: CacheKey, result: PermissionResult, ttl_seconds: float)
    def clear()
    def size() -> int
```

**Cache key:** `(artifact_id, action, requester_id, contract_version)`

**Opt-in:** Contracts specify caching via `cache_policy: {"ttl_seconds": N}`. No caching by default.

---

## Example: Pay-Per-Use Contract

```python
ExecutableContract(
    contract_id="pay_per_use",
    code='''
def check_permission(caller, action, target, context, ledger):
    price = 10
    if action == "read":
        price = 5  # Cheaper for reads

    if not ledger.can_afford_scrip(caller, price):
        return {"allowed": False, "reason": "Insufficient scrip", "cost": 0}

    return {"allowed": True, "reason": f"Paid {price} scrip", "cost": price}
''',
    cache_policy={"ttl_seconds": 60}  # Cache results for 1 minute
)
```

---

## Differences from Target

| Current | Target |
|---------|--------|
| Kernel contracts are Python classes | Contracts are artifacts (partially done) |
| Custom contracts fully supported | ✅ Done (Plan #100) |
| Permission caching available | ✅ Done (Plan #100) |
| No LLM in contracts | Contracts can call LLM (capability exists) |

See `docs/architecture/target/05_contracts.md` for target architecture.

---

## Architecture Decisions

Key ADRs governing the contract system:

| ADR | Decision |
|-----|----------|
| ADR-0003 | Contracts can do anything (invoke other artifacts, call LLM) |
| ADR-0015 | Contracts are artifacts, no genesis privilege |
| ADR-0016 | `created_by` replaces `owner_id` |
| ADR-0017 | Dangling contracts fail-open to configurable default |
| ADR-0018 | Bootstrap phase, Eris as creator |
| ADR-0019 | Unified permission architecture (consolidates above) |

### Key Principles (ADR-0019)

1. **Immediate Caller Model**: When A→B→C, C's contract checks if B (not A) has permission
2. **Minimal Context**: Kernel provides caller, action, target, target_created_by, method/args (for invoke)
3. **Null Contract Default**: When `access_contract_id` is null, creator has full rights, others blocked
4. **Dangling Contract Fallback**: When contract is deleted, falls back to configurable default (freeware)
5. **Contracts Fetch Context**: Contracts invoke other artifacts (ledger, event_log) for balances, history, etc.
