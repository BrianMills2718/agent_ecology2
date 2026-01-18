# Current Artifacts & Executor Model

How artifacts and code execution work TODAY.

**Last verified:** 2026-01-18 (Plan #66 - exception-ok comments)

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
    # Soft deletion fields (Plan #18)
    deleted: bool = False         # Is artifact deleted?
    deleted_at: str | None        # ISO timestamp of deletion
    deleted_by: str | None        # Who deleted it
    # Interface schema (Plan #14)
    interface: dict | None = None # JSON Schema for discoverability
    # Genesis method dispatch (Plan #15)
    genesis_methods: dict | None = None  # Method dispatch for genesis artifacts
    # Artifact dependencies (Plan #63)
    depends_on: list[str] = []  # List of artifact IDs this depends on
```

### Artifact Dependencies (Plan #63)

Artifacts can declare dependencies on other artifacts. Dependencies are resolved at invocation time and injected into the execution context.

**Declaration Model:**
```python
artifact = Artifact(
    id="my_pipeline",
    depends_on=["helper_lib", "data_processor"],
    code="""
def run(*args):
    helper = context.dependencies["helper_lib"]
    result = helper.invoke()
    return result["result"]
""",
    ...
)
```

**Key Properties:**

| Property | Behavior |
|----------|----------|
| Declaration time | At artifact creation (static) |
| Cycle detection | Rejected at creation (DFS) |
| Missing deps | Rejected at creation |
| Depth limit | Default 10 (configurable) |
| Genesis as deps | Allowed |
| Transitive deps | Allowed within depth limit |

**Dependency Wrapper:**

At invocation, each dependency is wrapped in a `DependencyWrapper` that provides an `invoke()` method:

```python
# Inside artifact code
helper = context.dependencies["helper_lib"]
result = helper.invoke(arg1, arg2)  # Returns invoke result dict
```

**Deleted Dependencies:**

If a dependency is deleted after artifact creation:
- Invocation fails with clear error: "Dependency 'X' not found or deleted"
- Artifact itself remains valid but unusable
- Dashboard shows broken dependency link

### Artifact Types

| Type | executable | code | Use Case |
|------|------------|------|----------|
| Data | False | "" | Notes, configs, documents |
| Executable | True | `def run()...` | Services, contracts, tools |


### Interface Reserved Terms (Plan #54)

The `interface` field uses JSON format with conventional field names. These are **reserved terms** - not mandates. Agents may use them for peer-to-peer discoverability.

**Core Terms:**

| Term | Type | Description |
|------|------|-------------|
| `description` | `string` | Human-readable summary of artifact |
| `methods` | `array` | List of callable operations |
| `inputSchema` | `object` | JSON Schema for method inputs |
| `outputSchema` | `object` | JSON Schema for method outputs |

**StructGPT-inspired Terms:**

| Term | Type | Description |
|------|------|-------------|
| `dataType` | `string` | Category hint: `table`, `knowledge_graph`, `service`, `document` |
| `linearization` | `string` | Template for converting output to readable text |

**Learning & Economic Terms:**

| Term | Type | Description |
|------|------|-------------|
| `examples` | `array` | Example invocations with input/output pairs |
| `cost` | `number` | Per-method cost hint |
| `errors` | `array` | Possible error codes |

**Example interface:**

```json
{
  "description": "Calculator service",
  "dataType": "service",
  "methods": [
    {
      "name": "add",
      "description": "Add two numbers",
      "inputSchema": {"a": "number", "b": "number"},
      "outputSchema": {"type": "number"},
      "cost": 0,
      "examples": [{"input": {"a": 1, "b": 2}, "output": 3}]
    }
  ]
}
```

**Dashboard display:** When viewing artifacts, the dashboard renders recognized interface fields:
- `description` shown prominently
- `methods` rendered as expandable list
- `dataType` shown as badge
- `examples` shown as copyable snippets
- Unknown structure shown as raw JSON

See `docs/plans/53_interface_reserved_terms.md` for full specification.
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
| `list_all(include_deleted=False)` | List artifacts (excludes deleted by default) |
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

#### `execute_with_invoke(code, args, caller_id, artifact_id, ledger, artifact_store, world)` - Full composition

Adds `invoke()` for artifact-to-artifact calls:

```python
def run():
    result = invoke("other_artifact", arg1, arg2)
    # result: {"success": bool, "result": Any, "error": str, "price_paid": int}
```

**Dependency Injection (Plan #63):**

If the artifact has `depends_on`, dependencies are resolved and injected via global `context`:

```python
def run(*args):
    # Access declared dependencies
    helper = context.dependencies["helper_lib"]
    result = helper.invoke()
    return result["result"]
```

The `ExecutionContext` class provides:
- `dependencies: dict[str, DependencyWrapper]` - Resolved dependency wrappers

**Dependency Resolution Flow:**
1. Look up artifact's `depends_on` list
2. For each dep, verify it exists and is not deleted
3. Create `DependencyWrapper` with pre-bound `invoke()` function
4. Inject as `context` global
5. Execute artifact code

When `world` is provided, also injects kernel interfaces (Plan #39 - Genesis Unprivilege):

```python
def run():
    # Read-only state access
    balance = kernel_state.get_balance("alice")
    resource = kernel_state.get_resource("alice", "llm_tokens")
    artifacts = kernel_state.list_artifacts_by_owner("alice")
    metadata = kernel_state.get_artifact_metadata("art_id")
    content = kernel_state.read_artifact("art_id", caller_id)

    # Write access (caller verified)
    kernel_actions.transfer_scrip(caller_id, "bob", 50)
    kernel_actions.transfer_resource(caller_id, "bob", "llm_tokens", 10.0)
    kernel_actions.write_artifact(caller_id, "new_art", "content")
```

The `caller_id` is also injected so artifacts know who invoked them.

**Key principle:** Agent-built artifacts have equal access to kernel interfaces as genesis artifacts - no privilege difference.

### Recursion Protection

- Max invoke depth: 5 (DEFAULT_MAX_INVOKE_DEPTH)
- Prevents infinite loops in artifact composition
- Caller pays for all nested invocations

### Resource Tracking

Execution uses `ResourceMeasurer` from `src/world/simulation_engine.py` (Plan #31) to track actual CPU time:

```python
with measure_resources() as measurer:
    result = run_func(*args)
usage = measurer.get_usage()
resources_consumed = {"cpu_seconds": usage.cpu_seconds}
```

**CPU is rate-limited (renewable resource):**
- Uses rolling window rate limiter (`RateTracker`) not fixed balance
- Configured via `rate_limiting.resources.cpu_seconds.max_per_window`
- Default: 5.0 CPU-seconds per 60-second window
- Agents exceeding their rate limit are blocked from further invocations until window rolls
- This is "physics" - agents can trade rate allocation rights via contracts

---

## ActionResult (Plan #40)

All three narrow waist actions return `ActionResult` with structured error information.

### ActionResult Structure

```python
@dataclass
class ActionResult:
    success: bool
    message: str
    data: dict[str, Any] | None = None
    resources_consumed: dict[str, float] | None = None
    charged_to: str | None = None
    # Structured error fields (Plan #40)
    error_code: str | None = None       # e.g., "insufficient_funds", "not_found"
    error_category: str | None = None   # e.g., "resource", "permission"
    retriable: bool = False             # Should agent retry?
    error_details: dict[str, Any] | None = None  # Additional context
```

### Error Codes by Action

| Action | Error | Code | Category | Retriable |
|--------|-------|------|----------|-----------|
| read | Not found | `not_found` | resource | No |
| read | Access denied | `not_authorized` | permission | No |
| read | Cannot afford price | `insufficient_funds` | resource | Yes |
| write | Genesis protected | `not_authorized` | permission | No |
| write | Write denied | `not_authorized` | permission | No |
| write | Disk quota exceeded | `quota_exceeded` | resource | Yes |
| write | Invalid code | `invalid_argument` | validation | No |
| invoke | Not found | `not_found` | resource | No |
| invoke | Method not found | `not_found` | resource | No |
| invoke | Not executable | `invalid_type` | validation | No |
| invoke | Permission denied | `not_authorized` | permission | No |
| invoke | Insufficient scrip | `insufficient_funds` | resource | Yes |
| invoke | Timeout | `timeout` | execution | Yes |
| invoke | Runtime error | `runtime_error` | execution | No |

### Retriability

Agents can use `retriable` to decide whether to retry:
- **True:** Condition may change (get more scrip, free space, timing)
- **False:** Won't succeed without external change (permissions, code fixes)

---

## ActionIntent (Plan #49)

Agent actions flow through `ActionIntent` classes, which now include a required `reasoning` field for LLM-native monitoring.

### ActionIntent Structure

```python
@dataclass
class ActionIntent:
    action_type: ActionType
    principal_id: str
    reasoning: str = ""  # Plan #49: Why the agent chose this action
```

### Intent Types

| Intent Class | action_type | Additional Fields |
|--------------|-------------|-------------------|
| `NoopIntent` | NOOP | - |
| `ReadArtifactIntent` | READ_ARTIFACT | `artifact_id` |
| `WriteArtifactIntent` | WRITE_ARTIFACT | `artifact_id`, `artifact_type`, `content`, `price`, `code`, `policy` |
| `InvokeArtifactIntent` | INVOKE_ARTIFACT | `artifact_id`, `method`, `args` |

### Reasoning Field

The `reasoning` field enables:
- **LLM-native monitoring** - Semantic analysis of agent behavior
- **Debugging** - Understanding why agents make decisions
- **Observability** - Action log includes agent explanations
- **Strategy extraction** - Cluster agents by reasoning patterns

All intents include reasoning in their `to_dict()` output, so logged actions contain both the action and its justification.

---

## Key Files

| File | Key Classes/Functions | Description |
|------|----------------------|-------------|
| `src/world/artifacts.py` | `Artifact`, `ArtifactStore` | Storage and access control |
| `src/world/artifacts.py` | `default_policy()`, `is_contract_reference()` | Policy utilities |
| `src/world/artifacts.py` | `_validate_dependencies()`, `_would_create_cycle()` | Dependency validation |
| `src/world/executor.py` | `SafeExecutor` | Code execution |
| `src/world/executor.py` | `get_executor()` | Singleton accessor |
| `src/world/executor.py` | `DependencyWrapper`, `ExecutionContext` | Dependency injection (Plan #63) |
| `src/world/kernel_interface.py` | `KernelState`, `KernelActions` | Kernel interfaces for artifacts |
| `src/world/actions.py` | `ActionResult`, `ActionIntent` | Action definitions and results |
| `src/world/errors.py` | `ErrorCode`, `ErrorCategory` | Error response conventions |

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

## Artifact Deletion (Plan #18)

Soft delete with tombstones - deleted artifacts remain in storage with metadata.

### Delete Semantics

| Action on Deleted Artifact | Behavior |
|---------------------------|----------|
| `invoke()` | Returns `{"success": False, "error_code": "DELETED", "error": "..."}` |
| `read_artifact()` | Returns tombstone metadata (`deleted=True`, `deleted_at`, `deleted_by`) |
| `write_artifact()` | Fails - cannot write to deleted artifact |
| `list_all()` | Excludes deleted by default, includes with `include_deleted=True` |

### Deletion Rules

- Only artifact owner can delete
- Genesis artifacts (`genesis_*`) cannot be deleted
- Deletion is logged as `artifact_deleted` event
- Deleted artifacts count toward storage but cannot be modified

### World Methods

```python
# Delete an artifact (owner only)
world.delete_artifact(artifact_id, requester_id) -> {"success": bool, "error": str}

# Read (returns tombstone for deleted)
world.read_artifact(requester_id, artifact_id) -> {..., "deleted": True, ...}

# Write fails for deleted
world.write_artifact(...) -> {"success": False, "message": "Cannot write to deleted..."}

# Invoke fails for deleted
world.invoke_artifact(...) -> {"success": False, "error_code": "DELETED", ...}
```

---

## Differences from Target

| Current | Target |
|---------|--------|
| Contracts optional | Contracts always on |
| In-memory store | Git-backed store |
| Static policy lists | Contract-first |

See `docs/architecture/target/` for target architecture.
