# Plan 93: Agent Resource Visibility

**Status:** 📋 Deferred
**Priority:** Medium
**Blocked By:** #92 (Unified Resource System)
**Blocks:** None

---

## Gap

**Current:** Agents receive limited context about their resource situation:
- `balance` (scrip) - YES, visible
- `llm_budget` remaining - NO
- `llm_budget` consumed - NO
- Token/dollar cost of previous action - NO
- Rate limit status - NO

Agents operate blind to their LLM budget consumption. They can conserve scrip while unknowingly depleting LLM tokens.

**Target:** Agents see their resource consumption in context, enabling:
- Self-regulation of expensive operations
- Strategic decisions about LLM budget allocation
- Learning which operations are cost-effective

**Why Medium:** Important for agent self-regulation but not blocking other work. Deferred until ResourceManager (#92) provides clean interface.

---

## References Reviewed

- `src/agents/agent.py:_build_workflow_context()` - Current context builder (only passes balance, not LLM budget)
- `src/world/ledger.py` - Current resource tracking (scattered)
- `docs/plans/92_unified_resource_system.md` - ResourceManager design with `get_available()` API
- `CLAUDE.md` - Project conventions

---

## Files Affected

- `src/agents/agent.py` (modify) - Add resource info to context
- `src/agents/prompts/` (modify) - Update prompts to include resource awareness
- `tests/test_agent.py` (modify) - Test resource visibility in context

---

## Plan

### Design Decision

**What to expose:**

| Resource | Expose to Agent | Rationale |
|----------|-----------------|-----------|
| `llm_budget_available` | YES | Allows budget-aware decisions |
| `llm_budget_consumed` | YES | Allows trend analysis |
| `last_action_cost` | YES | Enables learning what's expensive |
| `disk_available` | YES | Relevant for artifact creation |
| `cpu_rate_available` | MAYBE | Less actionable for agents |
| `llm_rate_available` | MAYBE | Less actionable for agents |

**Format in context:**
```python
"resources": {
    "llm_budget": {
        "available": 45.23,  # dollars
        "consumed": 4.77,    # dollars
        "unit": "dollars"
    },
    "disk": {
        "available": 1048576,  # bytes
        "consumed": 524288,
        "unit": "bytes"
    },
    "last_action_cost": 0.03  # dollars
}
```

### Changes Required

| File | Change |
|------|--------|
| `src/agents/agent.py` | Add `_build_resource_context()` method |
| `src/agents/agent.py` | Include resources in `_build_workflow_context()` |
| `src/agents/prompts/*.py` | Add resource awareness section to prompts |
| `tests/test_agent.py` | Test resource context building |

### Steps

1. **Wait for Plan #92** - ResourceManager must exist first
2. **Add resource context builder** - Method to fetch and format resource info
3. **Include in workflow context** - Add to `_build_workflow_context()`
4. **Update prompts** - Help agents understand resource info
5. **Test** - Verify context includes resource data

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_agent.py` | `test_context_includes_llm_budget` | llm_budget_available in context |
| `tests/test_agent.py` | `test_context_includes_last_action_cost` | Previous action cost visible |
| `tests/test_agent.py` | `test_resource_context_format` | Correct structure and units |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/test_agent.py` | Agent behavior unchanged |
| `tests/e2e/test_smoke.py` | End-to-end still works |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Agent sees budget | 1. Run simulation 2. Check agent reasoning in logs | Agent references budget constraints in decision-making |
| Budget-aware behavior | 1. Run with low budget 2. Observe agent choices | Agents make more conservative choices when budget low |

```bash
pytest tests/e2e/test_smoke.py -v --run-external
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 93`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [ ] E2E verification passes

### Documentation
- [ ] Agent context documented
- [ ] Doc-coupling check passes

### Completion Ceremony
- [ ] Plan file status -> `Complete`
- [ ] `plans/CLAUDE.md` index -> `Complete`
- [ ] Claim released
- [ ] Branch merged

---

## Notes

### Why Defer

Plan #92 (Unified Resource System) will:
1. Create `ResourceManager` with clean `get_available(agent, resource)` API
2. Consolidate scattered resource tracking
3. Make implementation trivial: one call to ResourceManager, format result

Implementing now would require wiring into 3 scattered systems, then rewriting after #92.

### Philosophical Consideration

Exposing resources is a design choice. Alternative: keep agents blind to LLM budget (like humans don't perceive neuron firing). Current decision: expose it, let agents learn to optimize. This aligns with "maximum observability" principle.

### Related Work

- Plan #92: Unified Resource System (dependency)
- Plan #12: Per-Agent LLM Budget (complete - tracking exists, just not exposed)
