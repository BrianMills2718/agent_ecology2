# Current Resource Model

How resources work TODAY.

**Last verified:** 2026-01-11

**See target:** [../target/resources.md](../target/resources.md)

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

### Compute (llm_tokens)

| Property | Value |
|----------|-------|
| Config key | `resources.flow.compute.per_tick` |
| Code name | `llm_tokens` |
| Default | 1000 per tick |
| Reset | Each tick (use-or-lose) |

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

If agent doesn't have enough compute:
- Thinking proceeds (LLM already called)
- Cost deduction fails
- Agent marked as `insufficient_compute`
- Action not executed

```python
if not self.ledger.can_spend_resource(agent_id, "llm_tokens", cost):
    return SkipResult(reason="insufficient_compute")
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
- Checked before write_artifact
- Decremented on successful write
- Can reclaim by deleting/overwriting smaller content

**`World._execute_write()`** in `src/world/world.py`:
```python
if not self.rights_registry.can_write(agent_id, bytes_needed):
    return ActionResult(success=False, message="Insufficient disk quota")
```

### LLM Budget

| Property | Value |
|----------|-------|
| Config key | `budget.max_api_cost` |
| Default | $1.00 |
| Scope | System-wide (shared) |

**Behavior:**
- Tracks cumulative $ spent on LLM API calls
- When exhausted: simulation stops
- Checkpoint saved before stopping

**`SimulationRunner.run()`** in `src/simulation/runner.py`:
```python
if self.engine.is_budget_exhausted():
    save_checkpoint(...)  # Checkpoint saved before stopping
    return
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
def can_afford_scrip(self, principal_id: str, amount: float) -> bool:
    return self.get_scrip(principal_id) >= amount
```

**Sources of scrip:**
- Starting allocation
- Oracle minting (artifact scores)
- Transfers from other agents
- Artifact sales (read_price, invoke_price)

**Sinks of scrip:**
- Transfers to other agents
- Oracle bids (paid to winner's UBI pool)
- Artifact purchases

---

## Cost Types

### Thinking Cost (Compute)

Paid for every LLM call, regardless of action success.

```
Cost = ceil(input_tokens/1000 * 1) + ceil(output_tokens/1000 * 3)
```

### Genesis Method Cost (Compute)

Configurable per method in config.yaml:

```yaml
genesis:
  ledger:
    methods:
      balance:
        cost: 0        # Free
      transfer:
        cost: 1        # 1 compute
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
| `src/world/genesis.py` | `GenesisRightsRegistry` | Quota management |

---

## Implications

### Use-or-Lose Creates Pressure
- Unused compute vanishes at tick end
- Agents should use full allocation
- No strategic saving for later

### Strict Constraints = No Speculation
- Cannot spend what you don't have
- No borrowing, no credit
- Limits complex economic strategies

### Shared LLM Budget = Collective Limit
- All agents share $1.00 total
- One expensive agent affects all
- No per-agent API budgets
