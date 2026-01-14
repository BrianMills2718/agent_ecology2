# Gap 22: Coordination Primitives

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Coordination primitives exist but lack documentation on usage patterns.

**Target:** Clear documentation showing how to use existing primitives for coordination.

---

## Clarification: No New Code Needed

**Contracts ARE the coordination primitive.**

| Primitive | Enables |
|-----------|---------|
| `genesis_escrow` | Trustless exchange, atomic swaps |
| `genesis_event_log` | Observable history, reputation |
| `genesis_ledger` | Value transfer, ownership |
| Contracts | Access control, pay-per-use |

Agents build coordination patterns using these. No kernel changes required.

---

## Plan: Documentation Only

### Phase 1: Coordination Patterns Guide

Create `docs/architecture/current/coordination_patterns.md`:

1. **Trustless Trading** - escrow workflow
2. **Pay-per-use Services** - contract-gated access
3. **Multi-party Agreements** - threshold signing
4. **Reputation Systems** - event log analysis

### Phase 2: Example Contracts

Add examples to `docs/examples/`:
- `voting_contract.py`
- `escrow_with_arbitration.py`

### Phase 3: Handbook Update

Add coordination guidance to `genesis_handbook`.

---

## Required Tests

None - documentation only.

---

## Verification

- [ ] Coordination patterns doc exists
- [ ] Examples work when executed
- [ ] Handbook updated
- [ ] No kernel code required
