# Gap 30: LLM Budget Trading

**Status:** ✅ Complete
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
| **LLM budget** | ✓ | `kernel_actions.transfer_llm_budget()` |

Agent with remaining budget but no ideas can sell to agent with ideas but no budget.

---

## Implementation Summary

### Phase 1: Kernel Interface

Added to `KernelActions` (src/world/kernel_interface.py:277-294):

```python
def transfer_llm_budget(self, caller_id: str, to: str, amount: float) -> bool:
    """Transfer LLM budget from caller to recipient.
    Convenience method for transfer_resource(caller_id, to, "llm_budget", amount).
    """
    return self.transfer_resource(caller_id, to, "llm_budget", amount)
```

Added to `KernelState` (src/world/kernel_interface.py:61-74):

```python
def get_llm_budget(self, principal_id: str) -> float:
    """Get LLM budget for a principal.
    Convenience method for get_resource(principal_id, "llm_budget").
    """
    return self._world.ledger.get_resource(principal_id, "llm_budget")
```

### Phase 2: Ledger Integration

LLM budget already tracked as a resource in ledger. The new methods delegate to existing `transfer_resource()` and `get_resource()` which:
- Verify caller has sufficient balance
- Perform atomic transfer
- Log via existing event mechanisms

### Phase 3: Genesis Wrapper

Added to `GenesisLedger` (src/world/genesis.py):
- `transfer_budget` method - transfers LLM budget from invoker to recipient
- `get_budget` method - queries LLM budget for any agent

Method configs added to `LedgerMethodsConfig` (src/config_schema.py).

---

## Required Tests

```
tests/unit/test_llm_budget.py::TestKernelLLMBudget::test_transfer_success
tests/unit/test_llm_budget.py::TestKernelLLMBudget::test_insufficient_budget
tests/unit/test_llm_budget.py::TestKernelLLMBudget::test_negative_amount_rejected
tests/unit/test_llm_budget.py::TestKernelLLMBudget::test_zero_amount_rejected
tests/unit/test_llm_budget.py::TestKernelLLMBudget::test_get_budget
tests/unit/test_llm_budget.py::TestKernelLLMBudget::test_get_budget_nonexistent_principal
tests/integration/test_budget_trading.py::TestGenesisLedgerBudgetTrading::test_transfer_budget_via_genesis
tests/integration/test_budget_trading.py::TestGenesisLedgerBudgetTrading::test_cannot_transfer_others_budget
tests/integration/test_budget_trading.py::TestGenesisLedgerBudgetTrading::test_get_budget_via_genesis
```

---

## Verification

- [x] `kernel_actions.transfer_llm_budget()` works
- [x] Insufficient budget returns error
- [x] All resources now contractable
- [x] Tests pass (9/9 plan tests, 1388/1388 full suite)
- [x] Implementation complete (docs update with merge)

---

## Verification Evidence

**Verified:** 2026-01-15
**Test Results:** 1388 passed, 22 skipped
**Mypy:** Success, no issues found in 38 source files

---

## Notes

Completes "everything is contractable" principle. Renamed from "Capability Request System".
