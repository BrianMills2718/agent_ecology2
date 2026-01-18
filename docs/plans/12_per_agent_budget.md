# Plan #12: Per-Agent LLM Budget

**Status:** ✅ Complete

**Verified:** 2026-01-14T02:39:34Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-14T02:39:34Z
tests:
  unit: 1161 passed, 1 skipped in 13.75s
  e2e_smoke: PASSED (2.09s)
  doc_coupling: passed
commit: 998be9c
```
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Problem

**Current state:**
- Single global `max_api_cost` budget in SimulationEngine
- All agents share the same pool
- When budget exhausted, all agents stop
- `llm_budget_quota` exists in PerAgentQuota but not enforced

**Issues:**
1. One agent can consume all LLM budget, starving others
2. No economic pressure on LLM usage - agents have no incentive to be efficient
3. Can't simulate resource scarcity for LLM access
4. Budget not tradeable like other resources

---

## Solution

### Per-Agent Budget Tracking

Each agent gets an LLM budget allocation:

```python
class AgentBudget:
    """Per-agent LLM budget tracking."""
    agent_id: str
    allocated: Decimal      # Initial allocation
    consumed: Decimal       # Amount used
    remaining: Decimal      # allocated - consumed

    def can_afford(self, cost: Decimal) -> bool:
        return self.remaining >= cost

    def consume(self, cost: Decimal) -> bool:
        if not self.can_afford(cost):
            return False
        self.consumed += cost
        self.remaining -= cost
        return True
```

### Budget as Stock Resource

LLM budget should be a **stock resource** (depletable, non-resetting):
- Allocated at genesis from config
- Consumed with each LLM call
- Not reset per tick
- Tradeable via escrow/contracts

### Integration Points

1. **SimulationEngine**: Track per-agent costs
2. **Ledger**: Store budget as stock resource
3. **AgentLoop**: Check budget before LLM calls
4. **Genesis**: Initial budget allocation from config

### Configuration

```yaml
agents:
  initial_resources:
    llm_budget: 1.0  # $1.00 per agent

  # Or differential allocation
  agent_budgets:
    agent_1: 2.0
    agent_2: 0.5
```

---

## Implementation Steps

1. **Add budget tracking to Ledger:**
   - New `llm_budget` stock resource type
   - `allocate_llm_budget(agent_id, amount)`
   - `consume_llm_budget(agent_id, amount) -> bool`
   - `get_llm_budget(agent_id) -> Decimal`

2. **Update SimulationEngine:**
   - Remove global budget tracking
   - Add per-agent cost routing
   - `track_agent_api_cost(agent_id, cost)`

3. **Update AgentLoop:**
   - Check budget before LLM call
   - Handle budget exhaustion gracefully
   - Log budget consumption

4. **Update genesis:**
   - Allocate initial budgets from config
   - Add `llm_budget` to initial resources

5. **Enable trading:**
   - Allow `llm_budget` in transfer operations
   - Add to escrow-supported resources

---

## Required Tests

- `tests/unit/test_per_agent_budget.py::TestLedgerLLMBudget::test_llm_budget_allocation`
- `tests/unit/test_per_agent_budget.py::TestLedgerLLMBudget::test_llm_budget_consumption`
- `tests/unit/test_per_agent_budget.py::TestLedgerLLMBudget::test_llm_budget_exhausted`
- `tests/integration/test_per_agent_budget.py::TestPerAgentBudgetIntegration::test_budget_isolation`
- `tests/integration/test_per_agent_budget.py::TestBudgetTrading::test_budget_transfer`

---

## Acceptance Criteria

1. Each agent has independent LLM budget
2. Budget consumed per LLM call
3. Agent actions fail gracefully when budget exhausted
4. Budget is tradeable via transfer/escrow
5. Global budget still works as system-wide cap
6. Backward compatible with existing config

---

## Design Decisions

**Q: Keep global budget too?**
A: Yes - global budget is safety limit, per-agent is economic constraint. Both can coexist.

**Q: What happens when agent runs out?**
A: Agent loop returns special "budget_exhausted" action. Simulation continues without that agent making LLM calls.

**Q: How to handle existing simulations?**
A: If no per-agent config, all agents share global budget (backward compatible).

---

## Notes

This enables economic experiments where agents must optimize LLM usage. Future work could add:
- LLM budget auctions
- Agent-to-agent budget lending
- Budget earning through useful work

See GAPS.md archive for detailed context.
