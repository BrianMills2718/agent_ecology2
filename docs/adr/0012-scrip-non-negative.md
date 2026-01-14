# ADR-0012: Scrip Non-Negative

**Status:** Accepted
**Date:** 2026-01-14
**Certainty:** 90%

## Context

Should scrip balances be allowed to go negative? Two models:

1. **Negative balances allowed** - Overspending creates negative balance (debt)
2. **Non-negative only** - Ledger enforces `scrip >= 0`, debt modeled separately

Negative balances conflate two concepts: currency and debt. They also create complex resolution logic (when is debt repaid? what if never repaid?).

## Decision

**Scrip balance cannot go negative.** The ledger enforces `balance >= 0` invariant.

**Debt is modeled as contract artifacts, not negative balances:**

```python
# Borrowing 50 scrip from B
# WRONG: A.balance = -50
# RIGHT:
#   1. B transfers 50 scrip to A (A.balance increases)
#   2. Create debt artifact: "A owes B 50 scrip"
#   3. B owns the debt artifact
#   4. A must pay B to clear debt (invoke debt contract)
#   5. A's balance never goes negative
```

This is like M1 vs M2 money - base currency (scrip) is distinct from debt instruments (contract artifacts representing claims).

## Consequences

### Positive

- **Clear semantics** - Balance always represents actual holdings
- **Debt is explicit** - Debt artifacts are visible, tradeable, enforceable
- **No resolution logic** - Ledger doesn't need to handle negative balance states
- **Composable** - Debt contracts can have complex terms (interest, collateral)

### Negative

- **More artifacts** - Each debt relationship creates artifact(s)
- **Contract complexity** - Debt logic lives in contracts, not ledger
- **Credit harder** - No simple "borrow and pay later" without explicit debt creation

### Neutral

- Debt artifacts can be traded (B sells A's debt to C)
- Multiple debt types possible (simple IOU, secured, interest-bearing)

## Related

- ADR-0001: Everything is an artifact (debt as artifact)
- ADR-0003: Contracts can do anything (debt contracts)
- Gap #9: Scrip Debt Contracts
