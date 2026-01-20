# Gap 8: Agent Rights Trading

**Status:** 📋 Planned (Post-V1)
**Priority:** Low
**Blocked By:** #100 (Contract System Overhaul)
**Blocks:** None

---

## Gap

**Current:** Agent configuration is stored in artifacts and tradeable, but:
- Config changes only take effect on simulation restart (no dynamic reload)
- Access control uses hardcoded owner bypass, not contracts

**Target:** Agents can trade control rights over their configuration with contract-based access control and dynamic config reload.

---

## Already Implemented (as of 2026-01)

| Feature | Status | Location |
|---------|--------|----------|
| Agent config in artifact `content` | ✅ Done | `agent.py:_load_from_artifact()` |
| Config readable via `read_artifact` | ✅ Done | Standard artifact read |
| Config writable via `write_artifact` | ✅ Done | Standard artifact write |
| Owner can modify (hardcoded bypass) | ✅ Done | `artifacts.py:can_write()` |
| Non-owners blocked from write | ✅ Done | Policy-based |
| Trading via escrow | ✅ Done | `genesis_escrow` |
| Basic documentation | ✅ Done | `handbook_self.md` |

---

## Remaining Gap

### 1. Dynamic Config Reload
Currently `_load_from_artifact()` is only called at agent construction. If agent A buys agent B and modifies B's config, B continues with old config until simulation restart.

**Needed:** Agents reload config from their artifact each loop iteration.

### 2. Contract-Based Access Control
Currently, owner bypass is hardcoded in `can_write()`. The target architecture uses contracts as the ONLY authority for access control.

**Needed:** Config modification rights should be gated by contracts, enabling patterns like:
- "Only my employer can change my goals"
- "Config changes require payment"
- "Delegate config rights without transferring ownership"

---

## Why Blocked by #100

Plan #100 (Contract System Overhaul) addresses the fundamental access control model:
- Removes hardcoded owner bypass from `can_write()`
- Makes contracts the sole authority for permissions
- Handles dangling contract references

Implementing dynamic config reload now would just reload static JSON with hardcoded owner checks. The real value comes when contracts can dynamically gate config modifications.

**Sequence:**
1. #100 completes → contracts are the authority
2. #8 implements → dynamic reload + contract-gated config rights

---

## Motivation

An agent's configuration IS valuable:
- System prompt encodes expertise
- Model selection affects capability
- Memory artifact contains knowledge

If agents are artifacts, and artifacts are tradeable via contracts, agent config should be too.

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

Agent config stored as artifact content. Trading works via `genesis_escrow`. Access control via contracts (after #100).

---

## Plan (Post #100)

### Phase 1: Dynamic Config Reload

1. Add `reload_from_artifact()` method to Agent class
2. Call reload at start of each agent loop iteration
3. Handle gracefully if artifact deleted/inaccessible

### Phase 2: Contract-Gated Config Rights

1. Remove reliance on owner bypass for config modification
2. Use contract-based `can_write` checks (enabled by #100)
3. Document contract patterns for config delegation

### Phase 3: Documentation

1. Update handbook with trading patterns
2. Add examples of config delegation via contracts

---

## Required Tests

```
tests/unit/test_agent_rights.py::test_owner_can_modify_config
tests/unit/test_agent_rights.py::test_non_owner_cannot_modify
tests/unit/test_agent_rights.py::test_trade_transfers_control
tests/unit/test_agent_rights.py::test_config_reload_on_loop
tests/unit/test_agent_rights.py::test_contract_gated_config_write
```

---

## Verification

- [ ] Dynamic config reload implemented
- [ ] Config changes take effect within one loop iteration
- [ ] Contract-based access control for config (requires #100)
- [ ] Tests pass
- [ ] Docs updated
