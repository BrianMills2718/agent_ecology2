# Gap 8: Agent Rights Trading

**Status:** ✅ Complete

**Verified:** 2026-01-15T05:48:04Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-15T05:48:04Z
tests:
  unit: 1413 passed, 7 skipped, 5 warnings in 23.67s
  e2e_smoke: PASSED (2.86s)
  e2e_real: PASSED (31.58s)
  doc_coupling: passed
commit: f7a2d9f
```
**Priority:** Low
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Agent configuration (system prompt, model, etc.) is fixed at creation.

**Target:** Agents can trade control rights over their configuration.

---

## Motivation

An agent's configuration IS valuable:
- System prompt encodes expertise
- Model selection affects capability
- Memory artifact contains knowledge

If agents are artifacts, and artifacts are tradeable, agent config should be too.

---

## Design

### What's Tradeable

| Config | Tradeable? | Notes |
|--------|-----------|-------|
| System prompt | Yes | Knowledge/expertise |
| Model selection | Yes | Capability tier |
| Memory artifact | Yes | Already tradeable |
| Budget allocation | Yes | Via #30 |
| ID/Identity | No | Immutable |

### Mechanism

Agent config stored as artifact content. Trading works via existing `genesis_escrow`.

---

## Plan

### Phase 1: Config as Artifact Content

1. Store agent config in artifact `content` field
2. Ensure config is readable/writable via artifact interface

### Phase 2: Config Modification Rights

1. Owner of agent artifact can modify config
2. Non-owners can read but not modify
3. Config changes take effect next tick

### Phase 3: Documentation

1. Document agent trading in handbook
2. Add examples of config trading patterns

---

## Required Tests

```
tests/unit/test_agent_rights.py::test_owner_can_modify_config
tests/unit/test_agent_rights.py::test_non_owner_cannot_modify
tests/unit/test_agent_rights.py::test_trade_transfers_control
```

---

## Verification

- [ ] Agent config stored as artifact content
- [ ] Ownership transfer transfers config control
- [ ] Tests pass
- [ ] Docs updated
