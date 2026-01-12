# Current Contract System

How access control works today.

**Last verified:** 2026-01-12

**Source:** `src/world/contracts.py`, `src/world/genesis_contracts.py`

---

## Overview

Contracts determine who can access artifacts. Every artifact has an `access_contract_id` pointing to a contract that governs permissions.

## Core Types

### PermissionAction

Actions that can be checked:

| Action | Description |
|--------|-------------|
| `READ` | Read artifact content |
| `WRITE` | Modify artifact |
| `EXECUTE` | Execute artifact code |
| `INVOKE` | Call artifact's service interface |
| `DELETE` | Delete artifact |
| `TRANSFER` | Transfer ownership |

### PermissionResult

Returned by permission checks:

```python
@dataclass
class PermissionResult:
    allowed: bool      # Whether action is permitted
    reason: str        # Human-readable explanation
    cost: int = 0      # Scrip cost (0 = free)
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

---

## Genesis Contracts

Four built-in contracts available at initialization:

| Contract | ID | Behavior |
|----------|-----|----------|
| **Freeware** | `genesis_contract_freeware` | Anyone reads/executes/invokes; only owner writes/deletes |
| **SelfOwned** | `genesis_contract_self_owned` | Only artifact itself (or owner) can access |
| **Private** | `genesis_contract_private` | Only owner can access |
| **Public** | `genesis_contract_public` | Anyone can do anything |

### Default: Freeware

Most artifacts use freeware pattern:
- Open read access (anyone can see)
- Open invoke access (anyone can use)
- Owner-only writes (only creator can modify)

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
    context={"owner": X.owner_id}
)
  ↓
Contract returns PermissionResult(allowed=True/False, ...)
  ↓
Executor proceeds or rejects
```

---

## Custom Contracts

Agents can create custom contracts as executable artifacts. The artifact must:
1. Have `can_execute=True`
2. Implement `check_permission` in its code
3. Be referenced by other artifacts via `access_contract_id`

**Note:** Custom contract execution is not yet fully integrated. Genesis contracts cover most use cases.

---

## Differences from Target

| Current | Target |
|---------|--------|
| Genesis contracts are Python classes | Contracts are artifacts |
| Custom contracts partially supported | Full custom contract support |
| No contract caching | Contract results cacheable |
| No LLM in contracts | Contracts can call LLM |

See `docs/architecture/target/05_contracts.md` for target architecture.
