# Gap 9: Scrip Debt Contracts

**Status:** ✅ Complete
**Priority:** Low
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Scrip transfers require sufficient balance. No debt allowed.

**Target:** Debt as tradeable contract artifacts enabling credit markets.

---

## Motivation

Real economies have credit. An agent with a good idea but no scrip can't execute without borrowing. Debt contracts enable:
1. Credit markets
2. Investment in promising agents
3. Time-shifted value transfer

---

## Implementation Approach

**Key insight from ADR-0003:** Contracts can do anything. Debt doesn't need kernel-level support - it's just a non-privileged genesis artifact demonstrating credit patterns.

The `genesis_debt_contract` is implemented as a non-privileged genesis artifact (like `genesis_escrow`):
- Cold-start convenience for agents
- Demonstrates credit/lending patterns
- Uses standard kernel interfaces (no special privileges)
- Agents can create competing debt contract artifacts

---

## Design

### Debt as Genesis Artifact

`genesis_debt_contract` tracks debts with:

```python
debt_record = {
    "debtor_id": "alice",
    "creditor_id": "bob",
    "principal": 100,
    "interest_rate": 0.1,  # Per tick (simple interest)
    "due_tick": 50,
    "status": "active",  # pending, active, paid, defaulted
    "amount_paid": 0,
}
```

### Methods

| Method | Purpose |
|--------|---------|
| `issue` | Debtor creates debt request |
| `accept` | Creditor accepts debt |
| `repay` | Debtor pays back (partial or full) |
| `collect` | Creditor collects after due_tick |
| `transfer_creditor` | Sell debt to another principal |
| `check` | Get debt status with current_owed |
| `list_debts` | List debts for a principal |
| `list_all` | List all debts in system |

### Enforcement

No magic enforcement:
1. `collect()` transfers what debtor has available
2. If debtor is broke, debt marked "defaulted"
3. Bad debtors observable via event log
4. Reputation emerges from observed behavior

### Tradeable Debt

Debt is tradeable:
- `transfer_creditor()` allows selling debt rights
- Payment goes to current creditor
- Market prices debt based on debtor reliability

---

## Required Tests

```
tests/unit/test_debt_contract.py::TestGenesisDebtContract::test_issue_debt_creates_pending_debt
tests/unit/test_debt_contract.py::TestGenesisDebtContract::test_issue_validates_inputs
tests/unit/test_debt_contract.py::TestGenesisDebtContract::test_accept_activates_debt
tests/unit/test_debt_contract.py::TestGenesisDebtContract::test_only_creditor_can_accept
tests/unit/test_debt_contract.py::TestGenesisDebtContract::test_repay_transfers_scrip
tests/unit/test_debt_contract.py::TestGenesisDebtContract::test_repay_fully_marks_paid
tests/unit/test_debt_contract.py::TestGenesisDebtContract::test_collect_after_due_tick
tests/unit/test_debt_contract.py::TestGenesisDebtContract::test_collect_partial_when_insufficient
tests/unit/test_debt_contract.py::TestGenesisDebtContract::test_collect_fails_when_broke
tests/unit/test_debt_contract.py::TestGenesisDebtContract::test_transfer_creditor_sells_debt
tests/unit/test_debt_contract.py::TestGenesisDebtContract::test_list_debts_for_principal
tests/unit/test_debt_contract.py::TestGenesisDebtContract::test_interest_accrues_over_time

tests/integration/test_debt_contract.py::TestDebtContractLifecycle
tests/integration/test_debt_contract.py::TestDebtCollection
tests/integration/test_debt_contract.py::TestDebtTrading
tests/integration/test_debt_contract.py::TestDebtContractWorldIntegration
tests/integration/test_debt_contract.py::TestMultipleDebts
```

---

## Verification

- [x] Debt contracts created via mutual agreement (issue → accept)
- [x] Collection attempts transfer (collect after due_tick)
- [x] Debt rights tradeable (transfer_creditor)
- [x] Interest accrues based on ticks elapsed
- [x] Tests pass (12 unit, 12 integration)

---

## Verification Evidence

```
Date: 2026-01-15
Unit tests: 12 passed (tests/unit/test_debt_contract.py)
Integration tests: 12 passed (tests/integration/test_debt_contract.py)
Full suite: 1418 passed, 22 skipped
mypy: Success (no issues in 38 source files)
```

---

## Notes

Key insight: No magic enforcement. Bad debtors get bad reputation via event log.

This is a **genesis artifact example** demonstrating how credit/lending can work, not a kernel feature. Agents can create their own debt tracking systems if they want different terms or behavior.
