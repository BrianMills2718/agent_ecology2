# Current Artifacts & Executor Model

How artifacts and code execution work TODAY.

**Last verified: 2026-01-12

---

## Overview

Artifacts are the fundamental unit of state in the ecology. The executor runs agent-created code with timeout protection.

**Key files:**
- `src/world/artifacts.py` - Artifact storage and access control
- `src/world/executor.py` - Code execution with wallet/invoke capabilities

---

## Artifact Model

### Artifact Structure

```python
@dataclass
class Artifact:
    id: str              # Unique identifier
    type: str            # Artifact type (e.g., "generic", "code")
    content: str         # Main content
    owner_id: str        # Principal who owns this
    created_at: str      # ISO timestamp
    updated_at: str      # ISO timestamp
    executable: bool     # Can be invoked?
    code: str            # Python code (must define run())
    policy: dict         # Access control and pricing
```

### Artifact Types

| Type | executable | code | Use Case |
|------|------------|------|----------|
| Data | False | "" | Notes, configs, documents |
| Executable | True | `def run()...` | Services, contracts, tools |

---

## Policy System

### Default Policy

```python
{
    "read_price": 0,      # Scrip cost to read
    "invoke_price": 0,    # Scrip cost to invoke
    "allow_read": ["*"],  # Everyone can read
    "allow_write": [],    # Only owner can write
    "allow_invoke": ["*"] # Everyone can invoke
}
```

### Access Control (allow_* fields)

| Value | Meaning |
|-------|---------|
| `["*"]` | Everyone allowed |
| `["alice", "bob"]` | Only listed agents |
| `[]` | Owner only (default for write) |
| `"@contract_id"` | V2: Defer to contract (NotImplementedError currently) |

### Hybrid Policy Schema

Two formats supported:

1. **Static lists** (V1 - implemented): Fast kernel-enforced access
2. **Contract references** (V2 - not implemented): Dynamic access via `@contract_id`

Contract references will enable DAOs, conditional access, and contracts governing contracts.

---

## Access Checks

**`Artifact.can_read(agent_id)`** - `artifacts.py:118-136`
- Owner always has access
- `"*"` grants everyone access
- Specific agent_id must be in list
- `@contract` raises NotImplementedError

**`Artifact.can_write(agent_id)`** - `artifacts.py:138-160`
- Owner ALWAYS has write access (bypasses policy)
- Others need explicit listing
- `@contract` raises NotImplementedError

**`Artifact.can_invoke(agent_id)`** - `artifacts.py:162-183`
- Must be executable
- Same logic as can_read
- `@contract` raises NotImplementedError

---

## ArtifactStore

In-memory storage for all artifacts.

### Key Methods

| Method | Description |
|--------|-------------|
| `exists(artifact_id)` | Check if artifact exists |
| `get(artifact_id)` | Get artifact or None |
| `write(...)` | Create or update artifact |
| `get_owner(artifact_id)` | Get owner ID |
| `list_all()` | List all artifacts (as dicts) |
| `list_by_owner(owner_id)` | List artifacts by owner |
| `get_artifact_size(artifact_id)` | Size in bytes (content + code) |
| `get_owner_usage(owner_id)` | Total disk usage for owner |
| `transfer_ownership(artifact_id, from_id, to_id)` | Transfer ownership |

---

## SafeExecutor

Executes agent-created code with timeout protection.

### Security Model

**IMPORTANT:** This is NOT a security sandbox.
- Agents CAN import any stdlib module
- Security boundary is Docker container (non-root user)
- `preloaded_imports` is convenience, not security

### Configuration

| Config Key | Default | Description |
|------------|---------|-------------|
| `executor.timeout_seconds` | 5 | Max execution time |
| `executor.preloaded_imports` | `[math, json, random, datetime]` | Pre-loaded modules |
| `executor.cost_per_ms` | 0.1 | Token cost per ms of execution |

### Execution Methods

#### `execute(code, args)` - Basic execution

```python
result = executor.execute(code, args=[1, 2, 3])
# Returns: {"success": bool, "result": Any, "error": str, "execution_time_ms": float, "resources_consumed": dict}
```

#### `execute_with_wallet(code, args, artifact_id, ledger)` - With pay()

Injects wallet functions into code namespace:

```python
def run():
    balance = get_balance()      # Get artifact's scrip balance
    pay("alice", 10)             # Transfer from artifact wallet
```

#### `execute_with_invoke(code, args, caller_id, artifact_id, ledger, artifact_store)` - Full composition

Adds `invoke()` for artifact-to-artifact calls:

```python
def run():
    result = invoke("other_artifact", arg1, arg2)
    # result: {"success": bool, "result": Any, "error": str, "price_paid": int}
```

### Recursion Protection

- Max invoke depth: 5 (DEFAULT_MAX_INVOKE_DEPTH)
- Prevents infinite loops in artifact composition
- Caller pays for all nested invocations

### Resource Tracking

Execution time converted to token cost:

```python
cost = max(1.0, execution_time_ms * cost_per_ms)
# Default: 1 token per 10ms, minimum 1 token
```

---

## Key Files

| File | Key Classes/Functions | Description |
|------|----------------------|-------------|
| `src/world/artifacts.py` | `Artifact`, `ArtifactStore` | Storage and access control |
| `src/world/artifacts.py` | `default_policy()`, `is_contract_reference()` | Policy utilities |
| `src/world/executor.py` | `SafeExecutor` | Code execution |
| `src/world/executor.py` | `get_executor()` | Singleton accessor |

---

## Implications

### All State is Artifacts
- No special "file system" or "database"
- Genesis artifacts are just artifacts with special code
- Disk usage = sum of artifact sizes

### Composability via invoke()
- Artifacts can call artifacts
- Caller pays for entire call chain
- Max depth prevents runaway recursion

### Policy is Data
- Access control stored in artifact
- Can be modified by owner
- V2 will enable dynamic policies via contracts

---

## Principal Capabilities (Phase 2)

Artifacts can now represent principals (agents, DAOs, contracts).

### New Fields on Artifact

```python
@dataclass
class Artifact:
    # ... existing fields ...
    has_standing: bool = False   # Can own things, enter contracts
    can_execute: bool = False    # Can execute code autonomously
    memory_artifact_id: str | None = None  # Link to memory artifact
```

### Convenience Properties

| Property | Condition | Description |
|----------|-----------|-------------|
| `is_principal` | `has_standing == True` | Can own artifacts, hold scrip |
| `is_agent` | `has_standing and can_execute` | Autonomous agent |

### Factory Functions

- `create_agent_artifact(agent_id, owner_id, config)` - Create agent artifact
- `create_memory_artifact(memory_id, owner_id)` - Create memory artifact

---

## Contract-Based Permission Checks (Phase 2)

When `executor.use_contracts: true`, permission checks use contract system.

### Configuration

```yaml
executor:
  use_contracts: false  # Enable contract-based permissions
```

### Check Flow

1. Executor calls `_check_permission_via_contract(caller, action, artifact)`
2. Looks up contract via `artifact.access_contract_id`
3. Contract returns `PermissionResult(allowed, reason, cost)`
4. Executor enforces decision

### ExecutableContract

Contracts can be executable artifacts with dynamic logic:

```python
# Contract code
def check_permission(caller, action, target, context):
    if action == "invoke" and context.get("tick", 0) > 100:
        return {"allowed": True, "reason": "Time-gated access"}
    return {"allowed": False, "reason": "Too early"}
```

### ReadOnlyLedger

Contracts execute with `ReadOnlyLedger` - can read balances but not modify.

---

## Differences from Target

| Current | Target |
|---------|--------|
| Contracts optional | Contracts always on |
| In-memory store | Git-backed store |
| Static policy lists | Contract-first |

See `docs/architecture/target/` for target architecture.
