# Current Configuration System

How configuration works TODAY.

**Last verified:** 2026-02-01 (Plan #254 - genesis config section still valid for MCP bridges)

---

## Overview

Configuration is loaded from `config/config.yaml` and validated using Pydantic.
Typos and invalid values fail fast with clear error messages.

**Key files:**
- `config/config.yaml` - Runtime values
- `src/config.py` - Config loader with dot-path access
- `src/config_schema.py` - Pydantic validation models (schema + defaults)

---

## Loading Configuration

### At Startup

```python
from config import load_config, get, get_validated_config

# Load and validate (call once at startup)
load_config("config/config.yaml")

# Get values by dot-path (backward compatible)
max_ticks = get("world.max_ticks")

# Or use the typed config object (IDE autocompletion)
config = get_validated_config()
max_ticks = config.world.max_ticks
```

### Runtime Overrides

```python
from config import set_config_value

set_config_value("world.max_ticks", 50)  # Re-validates automatically
```

---

## Configuration Sections

### Resources

```yaml
resources:
  stock:                    # Finite pools (don't refresh)
    llm_budget:
      total: 1.00           # $ for API calls
      unit: dollars
      distribution: equal
    disk:
      total: 50000          # Bytes
      unit: bytes
      distribution: equal
  flow:                     # Rate-limited (refresh per tick)
    compute:
      per_tick: 1000        # Token units
      unit: token_units
      distribution: equal
    bandwidth:
      per_tick: 0
      unit: bytes
```

### Scrip

```yaml
scrip:
  starting_amount: 100      # Each agent starts with this
```

### Costs

```yaml
costs:
  per_1k_input_tokens: 1    # Compute cost per 1K input
  per_1k_output_tokens: 3   # Compute cost per 1K output
```

### Execution (Plan #53, #102)

```yaml
execution:
  # Note: Autonomous mode is always enabled (Plan #102 removed tick-based mode)
  use_worker_pool: false          # Enable worker pool for 100+ agents (Plan #53)
  worker_pool:
    num_workers: 4                # Number of parallel worker threads
    state_db_path: "agent_state.db"  # SQLite database for agent state
  agent_loop:
    min_loop_delay: 0.1           # Minimum seconds between actions
    max_loop_delay: 10.0          # Maximum backoff on errors
    resource_exhaustion_policy: skip  # "skip" or "block"
```

### Rate Limiting (Plan #53)

```yaml
rate_limiting:
  enabled: true                   # RateTracker-based rolling window rate limiting
  window_seconds: 60.0            # Rolling window duration
  resources:
    llm_tokens:
      max_per_window: 1000000000  # Effectively unlimited
    llm_calls:
      max_per_window: 1000000000  # Effectively unlimited
    disk_writes:
      max_per_window: 1000000     # 1M writes per window
    bandwidth_bytes:
      max_per_window: 1073741824  # 1GB per window
    cpu_seconds:
      max_per_window: 5.0         # CPU-seconds per window (Plan #53)
    memory_bytes:
      max_per_window: 104857600   # 100MB per window (Plan #53)
```

**Note:** Rate limiting replaces tick-based resource reset. When enabled, resources flow continuously via RateTracker rolling windows instead of resetting each tick.

### Executor (Phase 2)

```yaml
executor:
  use_contracts: false            # Enable contract-based permissions
  timeout_seconds: 5              # Code execution timeout
```

### Genesis Artifacts

```yaml
genesis:
  artifacts:                # Enable/disable each artifact
    ledger:
      enabled: true
    mint:
      enabled: true
    rights_registry:
      enabled: true
    event_log:
      enabled: true
    escrow:
      enabled: true
    store:
      enabled: true         # Artifact discovery (Gap #16)

  ledger:                   # Per-artifact config
    id: genesis_ledger
    description: "System ledger..."
    methods:
      balance:
        cost: 0
        description: "Get balance..."
      transfer:
        cost: 1
        description: "Transfer scrip..."

  mint:
    id: genesis_mint
    mint_ratio: 10          # score / ratio = scrip minted
    auction:                # Plan #83: Time-based auction config
      period_seconds: 60.0           # Seconds between auction starts
      bidding_window_seconds: 30.0   # Duration of bidding phase
      first_auction_delay_seconds: 30.0  # Delay before first auction
      minimum_bid: 1

  mcp:                      # MCP server artifacts (Plan #28)
    fetch:
      enabled: false        # HTTP fetch capability
      command: "npx"
      args: ["@anthropic/mcp-server-fetch"]
      env: {}
    filesystem:
      enabled: false        # Sandboxed file I/O
      command: "npx"
      args: ["@anthropic/mcp-server-filesystem", "/tmp/agent_sandbox"]
      env: {}
    web_search:
      enabled: false        # Brave Search
      command: "npx"
      args: ["@anthropic/mcp-server-brave-search"]
      env:
        BRAVE_API_KEY: "${BRAVE_API_KEY}"
```

### Executor

```yaml
executor:
  timeout_seconds: 5
  interface_validation: warn  # Plan #86: none, warn, or strict
  preloaded_imports:        # NOT a security whitelist
    - math
    - json
    - random
    - datetime
```

**Interface Validation (Plan #86):**

| Mode | Behavior |
|------|----------|
| `none` | Skip validation - trust interfaces |
| `warn` | Log warning if args don't match schema, proceed anyway |
| `strict` | Reject invoke if args don't match declared inputSchema |

### LLM

```yaml
llm:
  default_model: "gemini/gemini-3-flash-preview"
  timeout: 60
  rate_limit_delay: 15.0    # Seconds between ticks
  allowed_models:           # For future self-modification
    - "gemini/gemini-3-flash-preview"
  reasoning_effort: null    # Claude extended thinking (Plan #187)
                            # Values: null (disabled), "none", "low", "medium", "high"
                            # Only works with Anthropic Claude models
                            # WARNING: Higher values cost 5-10x more
```

### World

```yaml
world:
  max_ticks: 100
```

### Budget

```yaml
budget:
  max_api_cost: 1.0         # $ limit (0 = unlimited)
  checkpoint_file: "checkpoint.json"
  checkpoint_interval: 10   # Save every N ticks (0 = disable)
  checkpoint_on_end: true   # Save when simulation ends
```

### Dashboard

```yaml
dashboard:
  enabled: true
  host: "0.0.0.0"
  port: 8080
  static_dir: "src/dashboard/static"
  jsonl_file: "run.jsonl"
```

### Timeouts (Plan #97)

```yaml
timeouts:
  agent_loop_stop: 5.0            # AgentLoop stop timeout (seconds)
  loop_manager_stop: 10.0         # AgentLoopManager stop_all timeout
  simulation_shutdown: 5.0        # SimulationRunner shutdown timeout
  mcp_server: 5.0                 # MCP server operations timeout
  state_store_lock: 30.0          # SQLite lock timeout
  state_store_retry_max: 10       # Max retry attempts for SQLite lock errors
  state_store_retry_base: 0.05    # Base backoff delay (seconds)
  state_store_retry_max_delay: 2.0  # Max backoff delay cap (seconds)
  dashboard_server: 30.0          # Dashboard server operations timeout
```

**SQLite Isolation Levels (Plan #99):** The state store uses different isolation levels for reads and writes to maximize concurrency:
- **Reads** (`load()`, `list_agents()`): Use DEFERRED isolation (default), allowing concurrent readers via WAL mode
- **Writes** (`save()`, `delete()`, `clear()`): Use IMMEDIATE isolation to prevent deadlocks in read-then-write patterns

**SQLite Retry Logic:** When multiple worker threads access the state store database concurrently, SQLite can throw `database is locked` errors under contention. The retry parameters control exponential backoff behavior:
- Retries only on "database is locked" errors (other errors propagate immediately)
- Delay doubles each attempt: base_delay * 2^(attempt-1), capped at max_delay
- After max_retries, the error is raised
- Both read and write operations use retry logic for robustness during checkpoint operations

### Agent Prompt

```yaml
agent:
  prompt:
    recent_events_count: 5
    memory_limit: 5
    first_tick_enabled: true
    first_tick_hint: "TIP: New to this world?..."
  rag:
    enabled: true
    limit: 5
    query_template: "Tick {tick}. I am {agent_id}..."
  working_memory:                 # Plan #59
    enabled: false                # Master switch (off by default)
    auto_inject: true             # Inject into prompt when enabled
    max_size_bytes: 2000          # Truncate to prevent prompt bloat
    include_in_rag: false         # Also include in semantic search
    structured_format: true       # Enforce schema vs freeform
    warn_on_missing: false        # Log warning if no working memory
  cognitive_schema: "simple"      # Plan #88: "simple" | "ooda"
  failure_history_max: 5          # Plan #88: Max failures to track
  errors:
    access_denied_read: "Access denied:..."
    # ...
```

### Memory (Mem0/Qdrant)

```yaml
memory:
  llm_model: "gemini-3-flash-preview"
  embedding_model: "models/text-embedding-004"
  embedding_dims: 768
  temperature: 0.1
  collection_name: "agent_memories"
```

### Libraries (Plan #29)

```yaml
libraries:
  genesis:                    # Pre-installed, free (don't count against quota)
    - requests
    - aiohttp
    - urllib3
    - numpy
    - pandas
    - python-dateutil
    - scipy
    - matplotlib
    - cryptography
    - pyyaml
    - pydantic
    - jinja2
  blocked:                    # Security risks - installation rejected
    - docker
    - debugpy
    - pyautogui
    - keyboard
    - pynput
```

**Genesis libraries:** Pre-installed in the Docker image, available to all agents at no quota cost. These are cold-start conveniences like genesis artifacts.

**Runtime installation:** Agents can install additional libraries via `kernel_actions.install_library()`. Each installation deducts ~5MB from disk quota.

**Blocklist:** Packages that could escape Docker sandbox (e.g., `docker` for daemon access, `debugpy` for debugger attachment). Returns `BLOCKED_PACKAGE` error code.

---

## Validation

### Pydantic Models

All config is validated using Pydantic with `extra="forbid"` - unknown keys cause errors.

```python
class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")  # Catches typos
```

### Validation Examples

```yaml
# This will FAIL - typo in key name
wrold:          # Should be 'world'
  max_ticks: 100

# This will FAIL - invalid type
world:
  max_ticks: "hundred"  # Should be int

# This will FAIL - constraint violation
mint:
  auction:
    minimum_bid: -1  # Must be >= 0
    period: 50
```

---

## Key Files

| File | Purpose |
|------|---------|
| `src/config.py` | Loader with `get()` and `get_validated_config()` |
| `src/config_schema.py` | Pydantic models (schema + defaults) |
| `config/config.yaml` | Runtime values |

---

## Helper Functions

```python
from config import (
    get,                    # get("world.max_ticks")
    get_validated_config,   # Returns typed AppConfig
    get_stock_resource,     # get_stock_resource("disk", "total")
    get_flow_resource,      # get_flow_resource("compute", "per_tick")
    get_genesis_config,     # get_genesis_config("mint", "mint_ratio")
    compute_per_agent_quota # Computes quotas based on num_agents
)
```

---

## Implications

### Fail-Fast Validation
- Invalid config fails at startup (not at first use)
- Typos in keys are caught immediately
- Clear error messages with field locations

### No Magic Numbers
- All numeric values from config
- Missing config = immediate failure (no silent defaults in code)
- See `src/config_schema.py` for all options and defaults

### Typed Access
- `get_validated_config()` returns typed `AppConfig`
- IDE autocompletion works
- Type errors caught at development time
