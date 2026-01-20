# Gap 8: Agent Rights Trading

**Status:** ✅ Complete
**Priority:** Low
**Blocked By:** None (#100 completed 2026-01-20)
**Blocks:** None

---

## Gap

**Current:** Agent configuration is stored in artifacts and tradeable, but config changes only take effect on simulation restart (no dynamic reload).

**Target:** Agents can trade control rights over their configuration with dynamic config reload.

---

## Already Implemented

| Feature | Status | Location |
|---------|--------|----------|
| Agent config in artifact `content` | ✅ Done | `agent.py:_load_from_artifact()` |
| Config readable via `read_artifact` | ✅ Done | Standard artifact read |
| Config writable via `write_artifact` | ✅ Done | Standard artifact write |
| Contract-based permission checking | ✅ Done | `executor._check_permission()` (Plan #100) |
| Trading via escrow | ✅ Done | `genesis_escrow` |
| Basic documentation | ✅ Done | `handbook_self.md` |

---

## Remaining Gap

### Dynamic Config Reload
Currently `_load_from_artifact()` is only called at agent construction. If agent A buys agent B and modifies B's config, B continues with old config until simulation restart.

**Needed:** Agents reload config from their artifact each loop iteration.

**Use cases enabled:**
- "Only my employer can change my goals" (contract-gated, implemented by #100)
- "Config changes require payment" (contract-gated, implemented by #100)
- "Delegate config rights without transferring ownership" (contract-gated, implemented by #100)
- **New:** Changes take effect immediately, not on restart

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

Agent config stored as artifact content. Trading works via `genesis_escrow`. Access control via contracts (Plan #100).

---

## Plan

### Phase 1: Dynamic Config Reload

1. Add `reload_from_artifact()` method to Agent class
2. Call reload at start of each agent loop iteration
3. Handle gracefully if artifact deleted/inaccessible

### Phase 2: Documentation

1. Update handbook with trading patterns
2. Add examples of config delegation via contracts

---

## Required Tests

```
tests/unit/test_agent_rights.py::test_config_reload_picks_up_changes
tests/unit/test_agent_rights.py::test_config_reload_handles_missing_artifact
tests/unit/test_agent_rights.py::test_config_reload_handles_invalid_json
```

---

## Verification

- [x] Dynamic config reload implemented (`agent.py:reload_from_artifact()`)
- [x] Config changes take effect within one loop iteration (`runner.py:_agent_decide_action()` calls reload)
- [x] Tests pass (5 tests in `test_agent_rights.py`)
- [x] Docs updated (`handbook_self.md` - Trading Agent Control section)
