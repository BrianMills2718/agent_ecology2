# Current Resource Model

How resources work TODAY.

**Last verified:** 2026-01-16 (Plan #53 - Added cpu_seconds, memory_bytes resources)

**See target:** [../target/resources.md](../target/resources.md)

---

## Terminology

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
| Resources | Physical constraints | Flow: No, Stock: Yes |
| Scrip | Economic currency | Yes |

Resources and scrip are independent. Spending resources doesn't cost scrip (except for priced artifacts).

---

## Flow Resources

### Discrete Per-Tick Refresh

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

## Stock Resources

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
