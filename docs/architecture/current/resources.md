# Current Resource Model

How resources work TODAY.

**Last verified:** 2026-01-31 (Plan #238 - Tokenized rights deferred, see ADR-0025)

**See target:** [../target/resources.md](../target/resources.md)

---

## Resource Enforcement Model

Resources are enforced via the **ledger/quota system**:
- `ledger.spend_resource("llm_budget", cost)` - depletable resources
- `world.get_available_capacity(agent_id, "disk")` - allocatable resources
- `RateTracker` - renewable resources (rolling window)

Quota allocation is managed by `genesis/rights_registry.py` (the `GenesisRightsRegistry`).

**Note:** Plan #166 previously implemented tokenized rights-as-artifacts (`src/world/rights.py`), but these were deferred and removed per ADR-0025. The design was sound but lacked critical token soundness invariants (type immutability, atomic settlement). See ADR-0025 for resumption criteria and restore recipe.

---

## Terminology (Legacy)

| Term | Meaning | Internal Name | Category |
|------|---------|---------------|----------|
| **llm_tokens** | Rate-limited LLM API access | `llm_tokens` | Renewable (rate-limited) |
| **llm_budget** | Real $ for API calls | `max_api_cost` | Depletable |
| **disk** | Storage quota | `disk` | Allocatable |
| **cpu_seconds** | CPU time per rolling window | `cpu_seconds` | Renewable (rate-limited) |
| **memory_bytes** | Memory usage per rolling window | `memory_bytes` | Renewable (rate-limited) |
| **scrip** | Internal currency | `scrip` | Economic signal |

**Note:** Legacy config uses `resources.flow.compute` which maps to `llm_tokens`. The term "compute" is reserved for future local CPU tracking.

---

## Two-Layer Model

| Layer | Purpose | Persists? |
|-------|---------|-----------|
| Resources | Physical constraints | Renewable: No, Allocatable: Yes |
| Scrip | Economic currency | Yes |

Resources and scrip are independent. Spending resources doesn't cost scrip (except for priced artifacts).

---

## Renewable Resources (Rate-Limited)

### Discrete Per-Tick Refresh (Legacy Mode)

**`World.advance_tick()`** in `src/world/world.py`

Flow resources reset to quota at start of each tick:

```python
# In advance_tick()
for pid in self.principal_ids:
    quota = self.rights_registry.get_quota(pid, "compute")
    self.ledger.set_resource(pid, "llm_tokens", quota)
```

### LLM Tokens

| Property | Value |
|----------|-------|
| Config key (rate limiting) | `rate_limiting.resources.llm_tokens.max_per_window` |
| Config key (legacy tick) | `resources.flow.compute.per_tick` |
| Internal name | `llm_tokens` |
| Default | 1000 per window (or per tick in legacy mode) |

**Used for:**
- Thinking cost (LLM input/output tokens)
- Genesis method costs

**Thinking cost calculation** - `SimulationEngine.calculate_thinking_cost()` in `src/world/simulation_engine.py`:
```python
input_cost = ceil((input_tokens / 1000) * rate_input)   # rate_input = 1
output_cost = ceil((output_tokens / 1000) * rate_output) # rate_output = 3
total_cost = input_cost + output_cost
```

### No Debt Allowed

**`Ledger.can_spend_resource()`** in `src/world/ledger.py`

If agent doesn't have enough LLM tokens:
- Thinking proceeds (LLM already called)
- Cost deduction fails
- Agent marked as `insufficient_llm_tokens`
- Action not executed

```python
if not self.ledger.can_spend_resource(agent_id, "llm_tokens", cost):
    return SkipResult(reason="insufficient_llm_tokens")
```

---

## Allocatable Resources (Quota-Based)

### Disk

| Property | Value |
|----------|-------|
| Config key | `resources.stock.disk.total` |
| Default | 50000 bytes |
| Reset | Never |

**Behavior:**
- Quota checked before write_artifact
- Usage calculated from total artifact sizes (not a balance)
- Can reclaim space by overwriting with smaller content

**`World._execute_write()`** in `src/world/world.py`:
```python
if not self.rights_registry.can_write(agent_id, bytes_needed):
    return ActionResult(success=False, message="Insufficient disk quota")
```

### LLM Budget

| Property | Value |
|----------|-------|
| Config key (global) | `budget.max_api_cost` |
| Config key (per-agent default) | `budget.per_agent_budget` |
| Config key (per-principal) | `principals[].llm_budget` |
| Default (global) | $1.00 |
| Default (per-agent) | 0 (disabled) |
| Scope | System-wide + per-agent (Plan #12) |

**Behavior:**
- Tracks cumulative $ spent on LLM API calls (global)
- Per-agent `llm_budget` tracked as stock resource in Ledger (Plan #12)
- When global budget exhausted: simulation stops
- When per-agent budget exhausted: agent skipped for tick
- Per-agent budget is tradeable via `ledger.transfer_resource()`
- Set to 0 to disable per-agent enforcement

**`SimulationRunner.run()`** in `src/simulation/runner.py`:
```python
# Global budget check
if self.engine.is_budget_exhausted():
    save_checkpoint(...)  # Checkpoint saved before stopping
    return

# Per-agent budget check (Plan #12)
if has_llm_budget_config and llm_budget <= 0:
    return {"skipped": True, "skip_reason": "insufficient_llm_budget"}
```

---

## Scrip (Currency)

| Property | Value |
|----------|-------|
| Config key | `scrip.starting_amount` |
| Default | 100 per agent |
| Reset | Never |

**Cannot go negative** - `Ledger.can_afford_scrip()` in `src/world/ledger.py`:

```python
def can_afford_scrip(self, principal_id: str, amount: int) -> bool:
    return self.get_scrip(principal_id) >= amount
```

**Sources of scrip:**
- Starting allocation
- Mint awards (artifact scores)
- Transfers from other agents
- Artifact sales (read_price, invoke_price)

**Sinks of scrip:**
- Transfers to other agents
- Mint bids (redistributed as UBI to all agents)
- Artifact prices (read_price, invoke_price to owner)

---

## Charge Delegation (Plan #236)

Principals can authorize others to charge their accounts, enabling "target pays" and "pool pays" economic patterns.

### Core Concepts

| Concept | Description |
|---------|-------------|
| **Delegation grant** | Principal A authorizes principal B to charge A's account |
| **`charge_to` directive** | Artifact metadata field that controls who pays on invocation |
| **Rate caps** | Per-call and per-window limits on delegated charges |

### `charge_to` Resolution

Set in artifact metadata. Resolved during `_invoke_user_artifact()` settlement:

| Value | Payer | Use Case |
|-------|-------|----------|
| `"caller"` (default) | Invoker pays | Normal artifact invocation |
| `"target"` | `artifact.created_by` pays | Creator-sponsored services |
| `"contract"` | `artifact.created_by` pays | Contract-sponsored invocations |
| `"pool:{id}"` | Principal `{id}` pays | Third-party sponsorship |

**Security:** Payer resolution uses only the immutable `created_by` field, never mutable metadata. This prevents forgery attacks where an artifact's metadata is modified to redirect charges.

### Delegation Artifacts

Delegations are stored as kernel-protected artifacts:
- **ID format:** `charge_delegation:{payer_id}` (reserved namespace, Plan #235)
- **Type:** `"charge_delegation"`
- **Content:** JSON with delegations list
- **Protection:** `kernel_protected=True` — only kernel can modify

### Rate Limiting

Each delegation grant includes optional caps:

| Cap | Default | Purpose |
|-----|---------|---------|
| `max_per_call` | None (unlimited) | Maximum scrip per single invocation |
| `max_per_window` | None (unlimited) | Maximum cumulative scrip in window |
| `window_seconds` | 3600 | Rolling window duration |
| `expires_at` | None (never) | ISO timestamp for delegation expiry |

**Window tracking** is ephemeral (in-memory deque, same as RateTracker). Windows reset on restart. History is bounded to 1000 entries per payer-charger pair.

### Settlement Flow

In `_invoke_user_artifact()` (`src/world/action_executor.py`):

1. Read `charge_to` from artifact metadata (default: `"caller"`)
2. Resolve payer via `DelegationManager.resolve_payer()`
3. If payer != caller, check delegation via `authorize_charge()`
4. Check payer's balance (affordability)
5. Deduct from payer, credit to artifact owner
6. Record charge for rate window tracking

### Key Files

| File | Purpose |
|------|---------|
| `src/world/delegation.py` | `DelegationManager`, `DelegationEntry`, `resolve_payer()` |
| `src/world/kernel_interface.py` | `grant_charge_delegation()`, `revoke_charge_delegation()`, `authorize_charge()` |
| `src/world/action_executor.py` | Settlement integration (~line 1511) |

---

## Cost Types

### Thinking Cost (LLM Tokens)

Paid for every LLM call, regardless of action success.

```
Cost = ceil(input_tokens/1000 * 1) + ceil(output_tokens/1000 * 3)
```

### Genesis Method Cost (LLM Tokens)

Configurable per method in config.yaml:

```yaml
genesis:
  ledger:
    methods:
      balance:
        cost: 0        # Free
      transfer:
        cost: 1        # 1 llm_token unit
```

### Artifact Prices (Scrip)

Set by artifact owner:

| Price | When Paid | Paid To |
|-------|-----------|---------|
| read_price | On read_artifact | Owner |
| invoke_price | On invoke_artifact success | Owner |

---

## Key Files

| File | Key Functions | Description |
|------|---------------|-------------|
| `src/world/ledger.py` | `Ledger`, `can_spend_resource()`, `can_afford_scrip()` | Resource tracking |
| `src/world/ledger.py` | `calculate_thinking_cost()`, `deduct_thinking_cost()` | Thinking cost calculation |
| `src/world/world.py` | `World.advance_tick()` | Tick resource reset |
| `src/world/simulation_engine.py` | `calculate_thinking_cost()`, `is_budget_exhausted()` | Cost calculation, budget tracking |
| `src/world/simulation_engine.py` | `ResourceUsage`, `ResourceMeasurer`, `measure_resources()` | Action resource measurement |
| `src/world/genesis.py` | `GenesisRightsRegistry` | Quota management |

### Implementation Notes

- **Precision:** Ledger uses `Decimal` arithmetic for float operations to avoid floating-point precision issues
- **Naming:** Internal resource name is `llm_tokens`. Config uses `rate_limiting.resources.llm_tokens` (preferred) or legacy `resources.flow.compute`. The term "compute" in legacy config maps to `llm_tokens` internally.
- **Artifact wallets:** `Ledger.transfer_scrip()` auto-creates recipient principals with 0 balance, enabling transfers to contracts/artifacts
- **Future:** True local CPU tracking (actual "compute") will use separate resource type when implemented

---

## Implications

### Use-or-Lose (Legacy Tick Mode Only)
- When `rate_limiting.enabled=false`, unused tokens vanish at tick end
- When `rate_limiting.enabled=true`, tokens use rolling window (no tick reset)
- RateTracker mode allows more natural consumption patterns

### Strict Constraints = No Speculation
- Cannot spend what you don't have
- No borrowing, no credit
- Limits complex economic strategies

### LLM Budget Options (Plan #12)
- **Global budget** (`budget.max_api_cost`): All agents share total
- **Per-agent budget** (`budget.per_agent_budget` or `principals[].llm_budget`): Individual limits
- Per-agent budget is opt-in: set to 0 to disable (default)
- Both can be used together for tiered enforcement

---

## RateTracker Integration (Phase 2)

When `rate_limiting.enabled: true`, `Ledger` integrates with `RateTracker` for rolling-window rate limiting.

```python
# Ledger now accepts optional RateTracker
ledger = Ledger.from_config(config, agent_ids)  # Creates RateTracker if enabled

# Record resource usage (replaces tick-based reset)
ledger.rate_tracker.record("llm_calls", agent_id, 1)

# Check if within limits
can_proceed = ledger.rate_tracker.can_consume("llm_calls", agent_id, 1)
```

**Key differences from tick-based:**
- Rolling time window instead of discrete tick reset
- No use-or-lose: capacity replenishes continuously
- Async-safe: uses `asyncio.Lock` for concurrent access

See `docs/architecture/current/configuration.md` for rate limiting config options.

---

## Renewable Resources (Plan #53)

### CPU Seconds

| Property | Value |
|----------|-------|
| Config key | `rate_limiting.resources.cpu_seconds.max_per_window` |
| Internal name | `cpu_seconds` |
| Default | 5.0 CPU-seconds per 60-second window |
| Measurement | `time.process_time()` via ResourceMeasurer |

**Behavior:**
- Tracked via RateTracker rolling window
- Measured per-agent-turn using ResourceMeasurer
- Replenishes continuously over time
- ~90% accurate (±10% for Python runtime overhead)

**Enforcement (worker pool mode):**
```python
# In worker.py
if cpu_time_used > cpu_quota:
    return {"success": False, "error": "cpu_quota_exceeded"}
```

### Memory Bytes

| Property | Value |
|----------|-------|
| Config key | `rate_limiting.resources.memory_bytes.max_per_window` |
| Internal name | `memory_bytes` |
| Default | 104857600 bytes (100MB) per 60-second window |
| Measurement | `psutil.Process().memory_info().rss` |

**Behavior:**
- Tracked via RateTracker rolling window
- Measured per-agent-turn using psutil
- Replenishes continuously over time
- ~90% accurate (±10% for shared Python runtime)

**Enforcement (worker pool mode):**
```python
# In worker.py
if memory_used > memory_quota:
    return {"success": False, "error": "memory_quota_exceeded"}
```

### Resource Measurement Accuracy

| Resource | Method | Accuracy | Error Source |
|----------|--------|----------|--------------|
| LLM tokens | API response | Exact (0%) | None |
| LLM $ cost | litellm.completion_cost() | Exact (0%) | None |
| Disk bytes | File size | Exact (0%) | None |
| Memory | psutil.Process().memory_info() | ~90% | Shared Python runtime |
| CPU time | time.process_time() | ~90% | Shared runtime overhead |

**Note:** The ~10% error from shared Python runtime is realistic - agents pay for their infrastructure overhead.

---

## Agent Resource Visibility (Plan #93)

Agents see detailed resource metrics in their prompts to enable self-regulation and resource-aware decision making.

### Components

| Component | File | Purpose |
|-----------|------|---------|
| `ResourceMetricsProvider` | `src/world/resource_metrics.py` | Read-only aggregation of metrics |
| `ResourceVisibilityConfig` | `src/world/resource_metrics.py` | Per-agent visibility configuration |
| `VisibilityConfigDict` | `src/agents/loader.py` | Agent.yaml visibility config schema |

### Data Sources

The `ResourceMetricsProvider` aggregates from multiple sources:
- `Ledger.resources` - Current balances (llm_budget, disk, compute)
- `Agent.llm.get_usage_stats()` - Token counts, cost tracking
- Config - Initial allocations for percentage calculations

### Detail Levels

| Level | Shows |
|-------|-------|
| `minimal` | Remaining only |
| `standard` | Remaining, initial, spent, percentage |
| `verbose` | All metrics including burn rate, tokens in/out |

### Configuration

**System defaults** in `config/config.yaml`:
```yaml
resources:
  visibility:
    enabled: true
    defaults:
      resources: null         # null = all resources (llm_budget, disk, compute)
      detail_level: "standard"
      see_others: false
```

**Per-agent overrides** in `src/agents/<name>/agent.yaml`:
```yaml
visibility:
  resources: ["llm_budget"]  # Only show llm_budget (default: all)
  detail_level: "verbose"    # Show all metrics
  see_others: false          # Only own metrics
```

### Prompt Injection

Resource metrics appear in agent prompts under `## Resource Consumption`:

```
## Resource Consumption
- LLM Budget: $0.0850 / $0.1000 (85.0% remaining)
  - Spent: $0.0150
  - Burn rate: $0.000025/second
- Disk: 5000 / 10000 bytes (50.0% remaining)
- Compute: 450 / 500 units (90.0% remaining)
```

### StateSummary Integration

`World.get_state_summary()` includes `resource_metrics` dict:
```python
{
    "agent_1": {
        "timestamp": 1737345600.0,
        "resources": {
            "llm_budget": {
                "resource_name": "llm_budget",
                "unit": "dollars",
                "remaining": 0.085,
                "initial": 0.10,
                "spent": 0.015,
                "percentage": 85.0,
                "burn_rate": 0.000025
            }
        }
    }
}
```

### Key Files

| File | Functions | Description |
|------|-----------|-------------|
| `src/world/resource_metrics.py` | `ResourceMetricsProvider.get_agent_metrics()` | Metrics aggregation |
| `src/world/world.py` | `World.get_state_summary()` | Includes resource_metrics |
| `src/agents/agent.py` | `Agent.build_prompt()` | Formats metrics for prompt |
| `src/agents/loader.py` | `load_agents()` | Loads visibility config from agent.yaml |
