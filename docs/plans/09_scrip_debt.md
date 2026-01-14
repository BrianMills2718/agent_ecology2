# Gap 9: Scrip Debt Contracts

**Status:** 📋 Planned (Post-V1)
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

## Design

### Debt as Artifact

Debt is NOT negative balance. It's a contract artifact:

```python
debt_contract = {
    "type": "debt",
    "debtor": "agent_A",
    "creditor": "agent_B",
    "principal": 100,
    "interest_rate": 0.1,  # Per tick
    "due_tick": 50,
}
```

### Enforcement via Contract

The debt artifact has an `access_contract` that:
1. Allows creditor to call `collect()` after due_tick
2. `collect()` transfers scrip from debtor (if available)
3. If debtor can't pay, debt remains (no magic enforcement)

### Tradeable Debt

Debt contracts are artifacts, so:
- Creditor can sell debt to another agent (factoring)
- Debtor can buy back their own debt at discount
- Market prices debt based on debtor reputation

---

## Plan

### Phase 1: Debt Contract Template

1. Create `DebtContract` artifact type
2. Methods: `collect()`, `repay()`, `transfer_creditor()`

### Phase 2: Issuance

1. Add `issue_debt(debtor, creditor, principal, terms)`
2. Both parties must sign (invoke to accept)

### Phase 3: Collection

1. Creditor calls `collect()` after due date
2. Returns success/failure (no magic enforcement)

---

## Required Tests

```
tests/unit/test_debt.py::test_create_debt_contract
tests/unit/test_debt.py::test_collect_succeeds_with_funds
tests/unit/test_debt.py::test_collect_fails_insufficient_funds
tests/unit/test_debt.py::test_debt_tradeable
```

---

## Verification

- [ ] Debt contracts created via mutual agreement
- [ ] Collection attempts transfer
- [ ] Debt artifacts tradeable
- [ ] Tests pass

---

## Notes

Key insight: No magic enforcement. Bad debtors get bad reputation via event log.
