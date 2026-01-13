# Gap 12: Per-Agent LLM Budget

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Global API budget shared by all agents

**Target:** Per-agent tradeable LLM budgets

---

## Problem Statement

Currently, all agents share a global `api_cost_limit` budget. This creates several issues:

1. **No individual accountability** - Can't tell which agent consumed how much
2. **Free rider problem** - Inefficient agents drain budget for everyone
3. **No market mechanism** - Budget can't be traded or reallocated
4. **Blunt stopping** - When budget exhausted, all agents stop

With per-agent budgets:
- Each agent has an LLM budget quota (in $)
- Quotas can be traded via `genesis_ledger.transfer_quota()`
- Agents who exhaust their budget freeze (not all agents)
- Efficient agents can sell surplus, inefficient can buy more

---

## Plan

### Phase 1: Per-Agent Budget Tracking

Add per-agent LLM budget quota to agent state:

```python
# In AgentState
@dataclass
class AgentState:
    id: str
    scrip: int = 0
    compute_quota: float = 0.0
    compute_used: float = 0.0
    llm_budget_quota: float = 0.0  # NEW: $ limit for this agent
    llm_budget_used: float = 0.0   # NEW: $ spent by this agent
    ...
```

### Phase 2: Budget Enforcement in Runner

Modify the runner to check per-agent budget before LLM calls:

```python
# In SimulationRunner or AgentLoop
def check_agent_budget(self, agent_id: str, estimated_cost: float) -> bool:
    """Check if agent has budget for an LLM call."""
    agent = self.agents[agent_id]
    remaining = agent.llm_budget_quota - agent.llm_budget_used
    return remaining >= estimated_cost

def charge_agent(self, agent_id: str, actual_cost: float) -> None:
    """Charge an agent for LLM usage."""
    agent = self.agents[agent_id]
    agent.llm_budget_used += actual_cost
    if agent.llm_budget_used >= agent.llm_budget_quota:
        agent.status = "frozen"
        self.emit_event("agent_frozen", {
            "agent_id": agent_id,
            "reason": "llm_budget_exhausted"
        })
```

### Phase 3: Budget Trading via Ledger

Extend `genesis_ledger.transfer_quota()` to support LLM budget:

```python
# In GenesisLedger
def transfer_quota(self, from_id: str, to_id: str, resource: str, amount: float) -> dict:
    """Transfer quota between principals.

    resource: "compute", "disk", "memory", or "llm_budget"
    """
    if resource == "llm_budget":
        return self._transfer_llm_budget(from_id, to_id, amount)
    ...
```

### Phase 4: Configuration

Add per-agent budget configuration:

```yaml
# config/schema.yaml
agents:
  initial_llm_budget: 0.10  # $ per agent at start
  llm_budget_tradeable: true

budget:
  total_api_cost_limit: 10.00  # Global ceiling (safety)
  per_agent_enforcement: true  # Enable per-agent limits
```

### Implementation Steps

1. **Add llm_budget fields to AgentState** - quota and used
2. **Update runner budget checks** - Per-agent instead of global
3. **Update charge_llm_usage()** - Credit to specific agent
4. **Extend transfer_quota()** - Support llm_budget resource
5. **Add configuration** - initial_llm_budget, tradeable flag
6. **Add tests** - Budget enforcement and trading
7. **Update docs** - Resources.md with LLM budget

---

## Required Tests

### Unit Tests
- `tests/unit/test_per_agent_budget.py::test_budget_check` - Check prevents over-budget calls
- `tests/unit/test_per_agent_budget.py::test_budget_charge` - Usage tracked correctly
- `tests/unit/test_per_agent_budget.py::test_budget_exhaustion_freezes` - Agent freezes at limit
- `tests/unit/test_per_agent_budget.py::test_budget_remaining` - Remaining calculated correctly

### Integration Tests
- `tests/integration/test_budget_trading.py::test_transfer_llm_budget` - Budget can be transferred
- `tests/integration/test_budget_trading.py::test_budget_isolation` - Agent A's usage doesn't affect B
- `tests/integration/test_budget_trading.py::test_frozen_agent_can_receive` - Frozen can receive to unfreeze

---

## E2E Verification

Run simulation with per-agent budgets:

```bash
python run.py --ticks 20 --agents 3 --config config/per_agent_budget.yaml
# With per_agent_enforcement: true
# Verify agents freeze individually when exhausted
# Verify budget trading works
```

---

## Out of Scope

- **Budget replenishment** - No automatic refill mechanism
- **Budget auctions** - No bidding for budget allocation
- **Budget derivatives** - No futures or options on budget
- **Cross-run persistence** - Budget resets each run

---

## Verification

- [ ] Tests pass
- [ ] Docs updated
- [ ] Implementation matches target

---

## Notes

This creates true economic scarcity for LLM usage. Agents must manage their API budget as a valuable resource.

Key design decisions:
- **Tradeable** - Budget can move between agents
- **Per-agent freeze** - Individual accountability
- **Global ceiling remains** - Safety limit for total spend
- **Initial allocation configurable** - Flexible starting conditions

See also:
- `src/world/ledger.py` - Transfer quota implementation
- `src/simulation/runner.py` - Budget enforcement
- `docs/architecture/current/resources.md` - Resource model
