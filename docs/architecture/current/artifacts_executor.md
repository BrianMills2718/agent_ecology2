# Current Artifacts & Executor Model

How artifacts and code execution work TODAY.

**Last verified:** 2026-02-05 (Plan #300: added capability methods to kernel interface)

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
    created_by: str      # Principal who created this (immutable per ADR-0016)
    created_at: str      # ISO timestamp
    updated_at: str      # ISO timestamp
    executable: bool     # Can be invoked?
    code: str            # Python code (must define run() or handle_request())
    policy: dict         # Access control and pricing
    # Soft deletion fields (Plan #18)
    deleted: bool = False         # Is artifact deleted?
    deleted_at: str | None        # ISO timestamp of deletion
    deleted_by: str | None        # Who deleted it
    # Interface schema (Plan #14)
    interface: dict | None = None # JSON Schema for discoverability
    # Genesis method dispatch (Plan #15)
    genesis_methods: dict | None = None  # Legacy: Method dispatch (Plan #254: genesis removed)
    # Artifact dependencies (Plan #63)
    depends_on: list[str] = []  # List of artifact IDs this depends on
    # User-defined metadata (Plan #168)
    metadata: dict[str, Any] = {}  # Arbitrary key-value pairs for categorization
    # Privileged capabilities (Plan #254)
    capabilities: list[str] = []  # e.g., ['can_mint'] for mint authorization
```

### System Field Immutability (Plan #235)

Certain artifact fields are immutable after creation:

| Field | Mutability | Enforced In |
|-------|-----------|-------------|
| `id` | Immutable (structural) | N/A (dict key) |
| `created_by` | Immutable (ADR-0016) | Convention (no setter) |
| `type` | **Immutable after creation** (Phase 0, FM-6) | `ArtifactStore.write()` |
| `access_contract_id` | **Creator-only** (Phase 0, FM-7) | `ArtifactStore.write()`, `_execute_edit()` |
| `kernel_protected` | **System field** (Phase 1, FM-1) | Not user-writable; set by kernel only |

**Why `type` is immutable:** The kernel branches on artifact type (`trigger`, `right`, `config`, etc.). Allowing type mutation enables type-confusion attacks where an attacker flips a normal artifact to a privileged type.

**Why `access_contract_id` is creator-only:** This field determines who can access the artifact. Allowing any writer to change it enables policy-pointer swap attacks (changing to a permissive contract).

### Kernel-Protected Artifacts (Plan #235 Phase 1)

Artifacts with `kernel_protected=True` cannot be modified via user-facing paths (`write_artifact`, `edit_artifact`). Only kernel primitives (`modify_protected_content()`) can update them.

**Enforcement layers:**
1. `ArtifactStore.write()` - raises `PermissionError` if artifact is kernel_protected
2. `_execute_edit()` - returns error ActionResult before any modification
3. `_execute_write()` - returns error ActionResult before any modification

**Reserved ID namespaces** (FM-4):
| Prefix | Who Can Create | Purpose |
|--------|---------------|---------|
| `charge_delegation:<owner>` | Only `<owner>` | Delegation records |
| `right:*` | Only `system` | Rights artifacts (kernel-managed) |

**Kernel primitive:** `modify_protected_content(artifact_id, content=..., code=..., metadata=...)` bypasses protection for kernel-only updates.

### Artifact Metadata (Plan #168)

Artifacts have a `metadata` field for user-defined key-value pairs. This enables filtering and categorization without changing the core schema.

**Common uses:**
- `recipient`: Address artifacts to specific agents
- `tags`: Categorize artifacts (e.g., `["trading", "experimental"]`)
- `priority`: Ordering hints for processing
- `invokes`: Auto-populated list of invoke() targets (Plan #170)

**Querying metadata:**
```python
# Via query_kernel action (Plan #199 - replaces genesis_store)
result = query_kernel("list_artifacts", {"metadata.tags": "trading"})
# Supports dot notation for nested fields: metadata.tags.priority
```

### Static Outbound Dependencies (Plan #170)

When an executable artifact is written, the system automatically extracts `invoke()` targets from its code and stores them in `metadata["invokes"]`.

**Auto-population:**
```python
# When you write executable code like:
code = '''
def run(ctx):
    invoke("my_ledger", "transfer", [10])
    invoke("mcp_escrow", "deposit", [100])
    return True
'''
# The artifact's metadata is auto-populated:
# metadata["invokes"] = ["mcp_escrow", "my_ledger"]
```

**Key properties:**
- Deduplicated and sorted alphabetically
- Updated on every artifact write (code changes)
- Known limitation: regex extraction may have false positives from comments/strings
- Useful for: understanding artifact behavior without reading code

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
| Executable (handle_request) | True | `def handle_request()...` | Self-access-controlled services (ADR-0024) |

### handle_request Interface (Plan #234, ADR-0024)

Artifacts can define `handle_request(caller, operation, args)` instead of `run(*args)`. These artifacts handle their own access control — the kernel skips permission checking and provides verified `caller_id`.

**Key differences from run():**

| Aspect | `run(*args)` | `handle_request(caller, op, args)` |
|--------|-------------|-------------------------------------|
| Permission check | Kernel checks via `access_contract_id` | Skipped — artifact handles it |
| Caller identity | Not provided to code | `caller` parameter (verified by kernel) |
| Operation routing | Single entry point | `operation` parameter for method dispatch |
| Arguments | Positional `*args` | List passed as `args` parameter |

**Example artifact code:**

```python
def handle_request(caller, operation, args):
    # Self-handled access control
    if operation == "admin" and caller != "owner_id":
        return {"success": False, "error": "Admin access denied"}

    if operation == "read":
        return {"success": True, "result": "public data"}
    elif operation == "write":
        return {"success": True, "result": "written"}
    else:
        return {"success": False, "error": f"Unknown operation: {operation}"}
```

**Detection:** The kernel detects handle_request artifacts by checking `"def handle_request(" in artifact.code`. Genesis artifacts are excluded (they use method dispatch in Phase 1).

**Backwards compatibility:** Existing `run()` artifacts are unchanged. The kernel permission check still applies to them.


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

### Interface Validation (Plan #86)

When artifacts define an `interface` with `tools` containing `inputSchema`, the executor can validate invocation arguments against the schema.

**Configuration:**

```yaml
executor:
  interface_validation: warn  # Options: none, warn, strict
```

| Mode | Behavior |
|------|----------|
| `none` | Skip all validation - trust interfaces |
| `warn` | Log warning if args don't match schema, proceed anyway |
| `strict` | Reject invoke if args don't match schema |

**Validation Flow:**

1. Get artifact's `interface` at invoke time
2. Look up method in `interface.tools[]` by name
3. Validate args against method's `inputSchema` using JSON Schema
4. If invalid:
   - `warn` mode: Log warning, continue execution
   - `strict` mode: Return error, reject invocation

**What Gets Validated:**

| Check | Description |
|-------|-------------|
| Required fields | All fields in `inputSchema.required` must be present |
| Type matching | Argument types must match `inputSchema.properties[*].type` |
| Method existence | Method name must exist in `interface.tools[]` |

**Error on Strict Mode:**

```python
{
    "success": False,
    "message": "Interface validation failed: 'name' is a required property",
    "error_code": "invalid_argument",
    "error_category": "validation",
    "retriable": False
}
```

**Skip Conditions:**

Validation is skipped (proceeds with execution) when:
- `interface_validation: none` in config
- Artifact has no `interface` field
- Interface has no `tools` array
- Method not found in interface (warn only)
- Method has no `inputSchema`

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

Per ADR-0016 and Plan #210: "Ownership" is not a kernel concept. Contracts decide access.
Standard kernel contracts (freeware, self_owned, private) check `target_created_by`.

**Contract-Based Permission Checks (default)**

Permission checks go through the artifact's `access_contract_id` contract:
- Freeware (default): Creator can write, anyone can read/invoke
- Self-owned: Creator or self can access
- Private: Only creator can access
- Public: Anyone can do anything

**Legacy Static Policy Checks (deprecated)**

**`Artifact.can_read(agent_id)`** method in `src/world/artifacts.py`
- Creator always has access
- `"*"` grants everyone access
- Specific agent_id must be in list
- `@contract` raises NotImplementedError

**`Artifact.can_write(agent_id)`** method in `src/world/artifacts.py`
- Creator ALWAYS has write access (bypasses policy)
- Others need explicit listing
- `@contract` raises NotImplementedError

**`Artifact.can_invoke(agent_id)`** method in `src/world/artifacts.py`
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
| `get_creator(artifact_id)` | Get creator ID (immutable, per ADR-0016) |
| `list_all(include_deleted=False)` | List artifacts (excludes deleted by default) |
| `list_by_owner(owner_id)` | List artifacts by owner |
| `get_artifact_size(artifact_id)` | Size in bytes (content + code) |
| `get_owner_usage(owner_id)` | Total disk usage for owner |
| `transfer_ownership(artifact_id, from_id, to_id)` | Set metadata["controller"] (doesn't affect access under freeware) |

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

### JSON Argument Parsing (Plan #112)

LLMs often generate JSON strings when passing dict/list arguments (e.g., `'{"id": "foo"}'` instead of `{"id": "foo"}`). The executor auto-parses these before calling `run()`:

```python
# Agent sends: args=['register', '{"id": "x"}']
# Artifact receives: args=['register', {"id": "x"}]
```

**Parsing Rules:**

| Input | Output | Reason |
|-------|--------|--------|
| `'{"a": 1}'` | `{"a": 1}` | Valid JSON dict |
| `'[1, 2, 3]'` | `[1, 2, 3]` | Valid JSON list |
| `'hello'` | `'hello'` | Not JSON |
| `'123'` | `'123'` | JSON but not dict/list |
| `'true'` | `'true'` | JSON but not dict/list |
| `42` | `42` | Already non-string |

**Key behavior:**
- Only strings are parsed
- Only strings that parse to dict or list are converted
- Numbers, bools, and primitive JSON stay as strings
- Non-JSON strings pass through unchanged
- Applied in all three execute methods

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

#### `execute_with_invoke(code, args, caller_id, artifact_id, ledger, artifact_store, world, entry_point, method_name)` - Full composition

Adds `invoke()` for artifact-to-artifact calls. The `entry_point` parameter selects `run` (default) or `handle_request` dispatch. When `entry_point="handle_request"`, the function calls `handle_request(caller_id, method_name, args)` instead of `run(*args)`.

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

**Key principle:** All artifacts have equal access to kernel interfaces - no privilege difference (Plan #254).

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

All narrow waist actions return `ActionResult` with structured error information.

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
| transfer | Insufficient balance | `insufficient_funds` | resource | Yes |
| transfer | Recipient not found | `not_found` | resource | No |
| transfer | Recipient not a principal | `invalid_type` | validation | No |
| transfer | Invalid amount | `invalid_argument` | validation | No |
| mint | Not authorized (no can_mint) | `not_authorized` | permission | No |
| mint | Recipient not found | `not_found` | resource | No |
| mint | Recipient not a principal | `invalid_type` | validation | No |
| mint | Invalid amount | `invalid_argument` | validation | No |

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
| `EditArtifactIntent` | EDIT_ARTIFACT | `artifact_id`, `old_string`, `new_string` |
| `DeleteArtifactIntent` | DELETE_ARTIFACT | `artifact_id` |
| `InvokeArtifactIntent` | INVOKE_ARTIFACT | `artifact_id`, `method`, `args` |
| `QueryKernelIntent` | QUERY_KERNEL | `query_type`, `query_params` |
| `SubscribeArtifactIntent` | SUBSCRIBE_ARTIFACT | `artifact_id` |
| `UnsubscribeArtifactIntent` | UNSUBSCRIBE_ARTIFACT | `artifact_id` |
| `TransferIntent` | TRANSFER | `recipient_id`, `amount`, `memo` (Plan #254) |
| `MintIntent` | MINT | `recipient_id`, `amount`, `reason` (Plan #254, privileged) |
| `ConfigureContextIntent` | CONFIGURE_CONTEXT | `section_name`, `enabled`, `priority` (deprecated) |
| `ModifySystemPromptIntent` | MODIFY_SYSTEM_PROMPT | `operation`, `content`, `section_name` (deprecated) |

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
| `src/world/executor.py` | `validate_args_against_interface()`, `ValidationResult` | Interface validation (Plan #86) |
| `src/world/permission_checker.py` | `check_permission()`, `check_permission_via_contract()` | Permission checking logic (Plan #181) |
| `src/world/interface_validation.py` | `validate_args_against_interface()`, `ValidationResult` | Interface validation (Plan #181) |
| `src/world/invoke_handler.py` | `create_invoke_function()`, `execute_invoke()` | Invoke closure factory for artifact calls (Plan #181) |
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
    has_loop: bool = False    # Can execute code autonomously
    memory_artifact_id: str | None = None  # Link to memory artifact
```

### Convenience Properties

| Property | Condition | Description |
|----------|-----------|-------------|
| `is_principal` | `has_standing == True` | Can own artifacts, hold scrip |
| `is_agent` | `has_standing and has_loop` | Autonomous agent |

### Factory Functions

- `create_agent_artifact(agent_id, owner_id, config)` - Create agent artifact
- `create_memory_artifact(memory_id, owner_id)` - Create memory artifact

### Auto-Principal Creation (Plan #254)

When `write_artifact` creates a NEW artifact with `has_standing=True`, the kernel automatically:

1. Creates the artifact with `has_standing=True` (and `has_loop` if specified)
2. Registers the artifact as a principal in the ledger
3. Grants starting scrip (from config `agents.starting_scrip`)
4. Logs a `principal_created` event

**Example:**
```python
# Agent creates a new DAO artifact that can hold scrip
write_artifact(
    artifact_id="my_dao",
    artifact_type="dao",
    content={"rules": "..."},
    has_standing=True,  # ← triggers auto-principal creation
)
# Result: my_dao can now hold scrip, be party to contracts
```

This replaces the old `genesis_ledger.spawn_principal()` pattern. The artifact IS the principal.

---

## Contract-Based Permission Checks

Permission checks use the contract system by default (`use_contracts=True`).

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

## Transfer and Mint Actions (Plan #254)

The kernel provides two value-layer primitives for scrip management.

### Transfer Action

Moves scrip from the caller to a recipient. This is a kernel primitive, not a genesis artifact invocation.

```python
# TransferIntent
{
    "action_type": "transfer",
    "recipient_id": "bob",
    "amount": 50,
    "memo": "Payment for service"  # Optional
}
```

**Validation:**
- Caller must have sufficient balance
- Amount must be positive integer
- Recipient must exist and have `has_standing=True` (is a principal)

### Mint Action

Creates new scrip. This is a **privileged** action requiring the `can_mint` capability.

```python
# MintIntent
{
    "action_type": "mint",
    "recipient_id": "alice",
    "amount": 100,
    "reason": "bounty:task_123"  # Required for audit trail
}
```

**Authorization:**
- Caller must have `capabilities` including `"can_mint"`
- Only kernel_mint_agent (or similar bootstrap artifacts) have this capability
- The `reason` field creates an audit trail for all scrip creation

### Capabilities System (Plan #254)

Artifacts can have a `capabilities` list for privilege checking:

```python
artifact.capabilities = ["can_mint"]  # Authorized to mint scrip
```

Capabilities are:
- Set at artifact creation by the kernel
- Not modifiable via normal write/edit actions
- Checked by the kernel before executing privileged actions

Currently defined capabilities:
| Capability | Action | Description |
|------------|--------|-------------|
| `can_mint` | `mint` | Authorized to create new scrip |

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
- Pre-seeded MCP artifacts (`mcp_*`) cannot be deleted
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
