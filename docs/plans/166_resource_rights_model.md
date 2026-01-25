# Plan 166: Resource Rights Model

**Status:** Planned
**Priority:** High
**Complexity:** High

## Problem

The current resource model has several issues:

1. **Terminology confusion**: `llm_tokens` conflates usage tracking with rights/quotas
2. **No unified rights model**: Resources tracked as numbers in dicts, not tradeable artifacts
3. **Mixed concerns**: Rate limits, dollar costs, and quotas are entangled
4. **Scrip vs resources unclear**: Different tracking mechanisms for similar concepts

## Current State

```python
# Scattered tracking
ledger.resources[agent]["llm_tokens"] = 500      # What is this? Quota? Usage? Rate?
ledger.scrip[agent] = 100                         # Separate mechanism
rate_tracker.consume(agent, "llm_tokens", cost)   # Rate limiting
simulation_engine.cumulative_api_cost             # Dollar tracking
```

## Solution

**Implementation note:** Phases 1-2 (terminology cleanup, usage tracking) can be done independently as a quick win. They don't require the full rights-as-artifacts model and provide immediate clarity.

### Core Concepts

**Separate three concerns:**

| Concern | Purpose | Tradeable? | Stored As |
|---------|---------|------------|-----------|
| Usage | Metrics (what was used) | No | Tracking data |
| Rights | What you're allowed to use | Yes | Artifacts |
| Capacity | External limits | No | Config |

### Phase 1: Terminology Cleanup

Remove `llm_tokens` as a concept. Replace with clear terms:

| Old Term | New Term | Meaning |
|----------|----------|---------|
| `llm_tokens` | Remove | Was conflating multiple concepts |
| N/A | `tokens_used` | Usage metric (per model) |
| N/A | `calls_made` | Usage metric (per model) |
| N/A | `dollars_spent` | Usage metric (total) |
| `llm_budget` | `dollar_budget` | Right to spend dollars |

**Files to update:**
- `src/world/resources.py` - remove LLM_TOKENS constant
- `src/world/ledger.py` - remove llm_tokens tracking
- `src/world/rate_tracker.py` - track by model, not generic tokens
- `config/config.yaml` - update resource configuration

### Phase 2: Usage Tracking

Track actual usage as metrics (not resources):

```python
class UsageTracker:
    """Tracks what agents have actually consumed."""

    def record_llm_call(self, agent_id: str, model: str,
                        input_tokens: int, output_tokens: int, cost: float):
        """Record an LLM call for metrics."""

    def get_usage(self, agent_id: str) -> UsageMetrics:
        """Get usage metrics for an agent."""
        return UsageMetrics(
            tokens_by_model={"gemini": 50000, "claude": 10000},
            calls_by_model={"gemini": 5, "claude": 2},
            dollars_spent=0.15
        )
```

### Phase 3: Rights as Artifacts

Create right artifacts that are tradeable:

```python
# Right artifact structure
{
    "type": "right",
    "right_type": "dollar_budget",  # or "rate_capacity", "disk_quota"
    "resource": "llm_dollars",       # what this right applies to
    "amount": 0.50,                  # current amount (decreases on use)
    "model": null,                   # for rate_capacity: specific model
    "window": null                   # for rate_capacity: "minute", "hour"
}
```

**Right types:**

| Right Type | Resource | Consumable? | Example |
|------------|----------|-------------|---------|
| `dollar_budget` | LLM API cost | Yes (shrinks) | "Can spend $0.50" |
| `rate_capacity` | API calls/window | Renewable | "100 calls/min to gemini" |
| `disk_quota` | Storage bytes | Allocatable | "Can use 100KB" |

**Genesis rights created at world init:**
- `genesis_right_dollar_budget_{agent}` - initial dollar allocation
- `genesis_right_rate_capacity_{agent}_{model}` - initial rate allocation
- `genesis_right_disk_quota_{agent}` - initial disk allocation

### Phase 4: Kernel Enforcement

Update kernel to check rights before actions:

```python
def check_can_call_llm(self, agent_id: str, model: str, estimated_cost: float) -> bool:
    # Check dollar budget right
    dollar_right = self.find_right(agent_id, "dollar_budget")
    if not dollar_right or dollar_right.amount < estimated_cost:
        return False

    # Check rate capacity right for this model
    rate_right = self.find_right(agent_id, "rate_capacity", model=model)
    if not rate_right or not self.has_rate_capacity(agent_id, rate_right):
        return False

    return True

def consume_llm_call(self, agent_id: str, model: str, actual_cost: float):
    # Reduce dollar budget right
    dollar_right = self.find_right(agent_id, "dollar_budget")
    dollar_right.amount -= actual_cost

    # Record rate usage (for window tracking)
    rate_right = self.find_right(agent_id, "rate_capacity", model=model)
    self.record_rate_usage(agent_id, rate_right)

    # Record usage metrics
    self.usage_tracker.record_llm_call(agent_id, model, ...)
```

### Phase 5: Trading Rights

Rights are artifacts, so trading uses existing mechanisms:

```python
# Transfer via escrow
invoke_artifact("genesis_escrow", "deposit", {
    "artifact_id": "my_dollar_budget_right",
    "price": 50  # scrip
})

# Or direct transfer via ledger
invoke_artifact("genesis_ledger", "transfer_ownership", {
    "artifact_id": "my_rate_capacity_right",
    "to_id": "other_agent"
})
```

**Splitting rights:**
```python
# Split a $0.50 right into two $0.25 rights
invoke_artifact("genesis_rights_registry", "split_right", {
    "right_id": "my_dollar_budget_right",
    "amounts": [0.25, 0.25]
})
# Creates two new right artifacts, destroys original
```

### Phase 6: Scrip Relationship

Scrip remains separate from resource rights:
- **Scrip** = money, medium of exchange (ledger entries)
- **Rights** = claims on physical capacity (artifacts)

Agents use scrip to BUY rights from each other. Rights are what enable actions.

```
Agent A has: 100 scrip, $0.10 dollar_budget_right
Agent B has: 50 scrip, $0.40 dollar_budget_right

A buys B's right for 80 scrip:
- A now has: 20 scrip, $0.50 dollar_budget_right (merged)
- B now has: 130 scrip, $0 dollar_budget_right
```

### Phase 7: Documentation Update

After implementation, comprehensive doc review:

1. **Glossary** (`docs/GLOSSARY.md`)
   - Remove: `llm_tokens`
   - Add: `right`, `dollar_budget`, `rate_capacity`, `disk_quota`
   - Clarify: `scrip` vs resources

2. **Architecture docs** (`docs/architecture/current/`)
   - `resources.md` - complete rewrite
   - `genesis_artifacts.md` - add genesis rights
   - `agent_cognition.md` - update resource visibility section

3. **Handbooks** (`src/agents/_handbook/`)
   - `handbook_resources.md` - update for rights model
   - `handbook_trading.md` - add rights trading

4. **Config** (`config/`)
   - `schema.yaml` - new rights configuration
   - `config.yaml` - example rights allocation

## Key Design Decisions

1. **Rights are artifacts** - consistent with "everything is an artifact"
2. **Usage is metrics** - tracked but not traded
3. **Scrip stays separate** - money ≠ resource rights
4. **Rights can be split/merged** - enables partial trades
5. **Kernel enforces rights** - not just tracking, actual enforcement

## Testing

- [ ] Remove llm_tokens, tests still pass
- [ ] Create right artifacts at world init
- [ ] Kernel blocks actions without sufficient rights
- [ ] Rights can be traded via escrow
- [ ] Rights can be split/merged
- [ ] Usage tracking works independently
- [ ] Multi-model rate limits work correctly
- [ ] Documentation is consistent

## Migration

1. Existing simulations: rights created from current quotas
2. Checkpoint format: include right artifacts
3. Backward compat: grace period with warnings

## Files Affected

- src/world/resources.py (modify) - Remove LLM_TOKENS, add right types
- src/world/ledger.py (modify) - Remove llm_tokens tracking
- src/world/rate_tracker.py (modify) - Per-model tracking
- src/world/usage_tracker.py (create) - NEW: usage metrics
- src/world/rights.py (create) - NEW: rights management
- src/world/genesis/rights_registry.py (modify) - Update for artifact-based rights
- src/world/kernel_interface.py (modify) - Rights checking
- src/world/world.py (modify) - Create genesis rights
- config/config.yaml (modify) - Rights configuration
- docs/GLOSSARY.md (modify) - Terminology update
- docs/architecture/current/resources.md (modify) - Full rewrite
- tests/unit/test_usage_tracker.py (create) - Tests for UsageTracker
- tests/unit/test_rights.py (create) - Tests for rights module
- tests/unit/test_kernel_interface.py (modify) - Tests for rights kernel integration

## Dependencies

- **Plan #165 (Genesis Contracts as Artifacts)** - MUST complete first. Establishes the pattern for contracts-as-artifacts. Rights may reference contracts for their own permissions.
- Plan #164 (Artifact Dependency Tracking) - rights would show as dependencies

## Design Decisions (Resolved)

1. **No expiration in kernel** - Keep kernel simple. Contracts can add time-bounded behavior (e.g., escrow that returns rights after elapsed time).

2. **Rate rights are per-model, window in config** - Rights specify model and capacity (e.g., "100 calls to gemini"). Window duration (minute, hour) is system-wide config, not per-right. Simpler rights, consistent enforcement.

3. **No minimum viable right** - Let dust exist. Selection pressure handles it - agents who fragment rights into unusable pieces waste their own resources. Don't over-engineer.
