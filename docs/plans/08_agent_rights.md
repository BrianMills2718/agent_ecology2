# Gap 8: Agent Rights Trading

**Status:** 📋 Planned
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
