# Plan #282: Ensure Resource Scarcity System is Fully Operational

## Status: Deferred

## Problem

Plan #281 fixed cost tracking (api_cost now populated), but `llm_budget_after: null` indicates agents may not have llm_budget resources allocated. The resource scarcity system has multiple components that need to work together:

1. **Initial allocation** - Agents need starting resources (llm_budget, disk, etc.)
2. **Deduction** - Costs must be deducted after each LLM call
3. **Enforcement** - Agents with exhausted budget should be skipped
4. **Visibility** - Resource state should be logged and visible

## Investigation Needed

### Questions to Answer

1. Are agents initialized with `llm_budget` in their resources?
   - Check `config/config.yaml` `resources.stock.llm_budget` distribution
   - Check `src/world/world.py` agent initialization
   - Verify `ledger.resources[agent_id]` contains `llm_budget`

2. Is deduction happening after our fix?
   - Runner calls `deduct_llm_cost()` at line 638 when `api_cost > 0`
   - Verify this path is hit with new cost data

3. Why is `llm_budget_after` null in events?
   - Check runner line 724: `self.world.ledger.get_llm_budget(agent.agent_id)`
   - If agent doesn't have llm_budget resource, this returns 0 or null

4. Is enforcement working?
   - Runner line 556: skips if `has_budget_config and llm_budget <= 0`
   - Need budget to be configured for this to trigger

## Likely Fix

The config has:
```yaml
resources:
  stock:
    llm_budget:
      total: 100.00
      distribution: equal
```

But agents may not be receiving this allocation. Need to trace:
- `World.__init__()` → resource distribution
- `Ledger.set_resource()` calls for each agent
- Why `get_llm_budget()` returns null

## Files to Investigate

- `config/config.yaml` - Resource configuration
- `src/world/world.py` - Agent initialization, resource distribution
- `src/world/ledger.py` - Resource storage and retrieval
- `src/simulation/runner.py` - Deduction and logging
- `src/config_schema.py` - Resource schema defaults

## Acceptance Criteria

- [ ] `llm_budget_after` shows non-null values in thinking events
- [ ] Budget decreases after each LLM call
- [ ] Agents with exhausted budget are skipped
- [ ] Resource metrics visible in dashboard

## Priority

Medium - Cost tracking works now (Plan #281), but scarcity enforcement is disabled without proper allocation.
