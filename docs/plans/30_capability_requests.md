# Gap 30: LLM Budget Trading

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** LLM budget tracked per-agent but not transferable.

**Target:** LLM budget contractable via kernel interface like all other resources.

---

## Motivation

LLM budget is the critical scarce resource. Currently:

| Resource | Contractable | Mechanism |
|----------|-------------|-----------|
| Scrip | ✓ | `kernel_actions.transfer_scrip()` |
| Disk quota | ✓ | `kernel_actions.transfer_resource()` |
| Compute | ✓ | `kernel_actions.transfer_resource()` |
| **LLM budget** | ✗ | **None** |

Agent with remaining budget but no ideas can't sell to agent with ideas but no budget.

---

## Plan

### Phase 1: Kernel Interface

Add to `KernelActions`:

```python
def transfer_llm_budget(self, caller_id: str, to_id: str, amount: float) -> bool:
    """Transfer LLM budget from caller to recipient."""
```

Add to `KernelState`:

```python
def get_llm_budget(self, agent_id: str) -> float:
    """Get remaining LLM budget for agent."""
```

### Phase 2: Ledger Integration

1. Track LLM budget as transferable in ledger
2. Verify caller_id matches invoking principal
3. Log transfers in event log

### Phase 3: Genesis Wrapper

Add `genesis_ledger.transfer_llm_budget()` for discoverability.

---

## Required Tests

```
tests/unit/test_llm_budget.py::test_transfer_success
tests/unit/test_llm_budget.py::test_insufficient_budget
tests/unit/test_llm_budget.py::test_caller_verification
tests/integration/test_budget_trading.py::test_contract_trades_budget
```

---

## Verification

- [ ] `kernel_actions.transfer_llm_budget()` works
- [ ] Insufficient budget returns error
- [ ] All resources now contractable
- [ ] Tests pass
- [ ] Docs updated

---

## Notes

Completes "everything is contractable" principle. Renamed from "Capability Request System".
