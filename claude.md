# Agent Ecology - Core Philosophy

## What This Is

A simulation where LLM agents interact under real resource constraints. Constraints mirror actual physical/financial limits of the host system.

## Resources

All resources map to real scarcity. All have rights. All rights are tradeable.

### Stock Resources (finite pool, don't refresh)

| Resource | Physical Reality | Distribution |
|----------|-----------------|--------------|
| `llm_budget` | $ for API calls | Split among agents at start |
| `disk` | Storage bytes | Split among agents at start |

When an agent exhausts their `llm_budget` rights, they can't think until they acquire more from others.

### Flow Resources (rate-limited, refresh per tick)

| Resource | Physical Reality | Distribution |
|----------|-----------------|--------------|
| `compute` | CPU/GPU cycles | Quota per tick per agent |
| `bandwidth` | Network I/O | Quota per tick per agent |

Machine can only do X compute per tick. That capacity is available again next tick.

## Rights

Every resource has rights. Rights are distributed initially and tradeable.

```
Agent A has: llm_budget_rights=$2, disk_rights=2000bytes, compute_quota=50/tick
Agent A can trade any of these to Agent B
```

Trade types:
- Permanent transfer
- Time-limited (contract)
- Conditional (contract)

## Scrip

Scrip is NOT a resource. It's the medium of exchange.

- Trade for rights
- Pay for artifacts/services
- Signals value (prices, profits)
- Accumulates/depletes via economic activity

## Tick Model

Each tick:
1. Flow resources refresh (compute, bandwidth)
2. Each agent thinks (costs from their llm_budget)
3. Each agent acts (costs compute, may cost scrip)
4. Stock resources don't refresh (llm_budget, disk)

## Failure States

| State | Cause | Recovery |
|-------|-------|----------|
| **Frozen** | Out of llm_budget | Buy rights from others |
| **Out of compute** | Used tick's quota | Wait for next tick |
| **Out of disk** | Storage full | Delete or buy quota |
| **Broke** | Out of scrip | Sell tools/rights |

## Design Principles

1. **Model real scarcity** - Only constrain what's actually limited
2. **Distribute rights initially** - Stock resources split at start
3. **Everything tradeable** - Rights can always be contracted
4. **Scrip is information** - Not a resource, just a signal
5. **No hardcoded numbers** - All values come from config

## Configuration

All values in config, not code. See:
- `config/schema.yaml` - Structure and documentation
- `config/config.yaml` - Actual values

Code reads config. Code has no magic numbers.

## Coding Standards

### Configuration Rules

1. **No magic numbers in code** - Every numeric value must come from config
2. **Use `src/config.py` helpers** - `get()`, `get_genesis_config()`, `get_action_cost()`
3. **Fallbacks must also be configurable** - If you write `or 50`, that 50 should come from config
4. **New features need config entries** - Add to both `config.yaml` and `schema.yaml`

Example:
```python
# WRONG
timeout = 30
limit = min(n, 100)

# RIGHT
from config import get
timeout = get("oracle_scorer.timeout") or 30  # 30 is schema default
max_limit = get("genesis.event_log.max_per_read") or 100
limit = min(n, max_limit)
```

### Type Hints

1. **All functions must have type hints** - Parameters and return types
2. **Use modern Python typing** - `dict[str, Any]` not `Dict[str, Any]` for Python 3.9+
3. **Must pass `mypy --strict`** - No `Any` without justification
4. **Use TypedDict for structured dicts** - Especially config and state objects

Example:
```python
# WRONG
def get_balance(agent_id):
    return self.balances.get(agent_id, 0)

# RIGHT
def get_balance(self, agent_id: str) -> int:
    return self.balances.get(agent_id, 0)
```

### Terminology

Use consistent terms throughout:
- `compute` not `flow` (for CPU/GPU cycles per tick)
- `disk` not `stock` (for storage bytes)
- `scrip` not `credits` (for economic currency)
- `compute_quota` not `flow_quota`
- `disk_quota` not `stock_quota`
