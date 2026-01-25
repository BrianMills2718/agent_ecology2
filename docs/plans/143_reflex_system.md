# Plan 143: Reflex System (System 1 Fast Path)

**Status:** ✅ Complete

**Verified:** 2026-01-25T03:49:39Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-25T03:49:39Z
tests:
  unit: 2198 passed, 10 skipped, 3 warnings in 55.96s
  e2e_smoke: skipped (--skip-e2e)
  e2e_real: skipped (--skip-real-e2e)
  doc_coupling: passed
commit: e6dcbc7
```
**Priority:** High
**Blocked By:** None
**Blocks:** Agent self-optimization, high-frequency trading

---

## Overview

Agents currently make ALL decisions via LLM calls (~1-3 seconds each). This prevents:
- High-frequency trading and monitoring
- Rapid response to known situations
- Cost-effective routine operations

We introduce a "Reflex System" - fast Python scripts that run BEFORE the LLM. If a reflex returns an action, it executes immediately (0 latency, 0 inference cost). If not, the agent falls back to LLM reasoning.

**Critical Design Principle:** Reflexes are NOT developer-hardcoded. They are agent-created artifacts that agents can create, modify, and trade. This enables evolutionary optimization of agent behavior.

---

## Design

### 1. ReflexArtifact Type

```python
# New artifact type: "reflex"
# Stored as executable Python code (uses existing sandbox)

artifact = {
    "id": "alice_trading_reflex",
    "type": "reflex",
    "created_by": "alice",
    "executable": True,
    "content": '''
def reflex(context):
    """Fast trading reflex.

    Args:
        context: dict with agent_id, balance, tick, recent_events, etc.

    Returns:
        Action dict if reflex fires, None to defer to LLM.
    """
    # Auto-accept escrow purchases under 10 scrip
    for event in context.get("pending_purchases", []):
        if event["price"] <= 10:
            return {
                "action_type": "invoke_artifact",
                "artifact_id": "genesis_escrow",
                "method": "accept",
                "args": [event["deal_id"]]
            }

    # No reflex fires - defer to LLM
    return None
'''
}
```

### 2. Agent Reflex Reference

Agents store a reference to their active reflex artifact:

```yaml
# In agent artifact content or agent.yaml
id: alice
reflex_artifact_id: alice_trading_reflex  # Optional, can be null
llm_model: gemini/gemini-2.0-flash
# ...
```

### 3. Execution Flow

```
Agent Loop Iteration:
├─ 1. Load reflex artifact (if reflex_artifact_id set)
├─ 2. Build reflex context (subset of world state)
├─ 3. Execute reflex in sandbox (timeout: 100ms)
├─ 4. If reflex returns Action:
│     └─ Execute action immediately (skip LLM)
├─ 5. Else (reflex returns None or errors):
│     └─ Fall back to LLM think() as normal
└─ 6. Continue loop
```

### 4. Reflex Context

Reflexes receive a limited context (fast to build):

```python
reflex_context = {
    "agent_id": str,
    "tick": int,
    "balance": int,  # Current scrip
    "llm_tokens_remaining": int,

    # Recent events (last 10)
    "recent_events": [
        {"type": "transfer", "from": "bob", "amount": 50},
        {"type": "invocation", "caller": "bob", "artifact": "my_service"},
    ],

    # Pending items requiring response
    "pending_purchases": [...],  # Escrow deals waiting
    "pending_contracts": [...],  # Contract proposals

    # Quick artifact lookup
    "owned_artifacts": ["artifact_1", "artifact_2"],
}
```

### 5. Agent Self-Modification

Agents can create/modify their own reflexes:

```python
# Agent creates a new reflex
action = {
    "action_type": "write_artifact",
    "artifact_id": "alice_new_reflex",
    "artifact_type": "reflex",
    "content": "def reflex(context): ..."
}

# Agent switches to new reflex
action = {
    "action_type": "invoke_artifact",
    "artifact_id": "genesis_store",
    "method": "update_agent_config",
    "args": [{"reflex_artifact_id": "alice_new_reflex"}]
}
```

### 6. Reflex Trading

Reflexes are artifacts, so they can be:
- Listed on escrow for sale
- Discovered via genesis_store
- Copied (read content, create new artifact)

This creates a market for optimized reflexes.

---

## Implementation

### Phase 1: Core Infrastructure

1. **Add reflex artifact type** (`artifacts.py`)
   - `artifact_type = "reflex"`
   - Validate has `def reflex(context):` entry point

2. **Update agent config** (`agent.py`)
   - Add `reflex_artifact_id: str | None` field
   - Add `reload_reflex()` method

3. **Create reflex executor** (`reflex.py`)
   - `execute_reflex(code: str, context: dict) -> Action | None`
   - Use existing sandbox with 100ms timeout
   - Return None on error (fail-safe to LLM)

### Phase 2: Loop Integration

4. **Update agent loop** (`agent_loop.py`)
   - Before `agent.decide_action()`, check for reflex
   - Execute reflex, use result if non-None
   - Log reflex fires vs LLM fallbacks

5. **Build reflex context** (`runner.py`)
   - Create `build_reflex_context(agent, world)` function
   - Fast subset of world state

### Phase 3: Agent API

6. **Add reflex management to genesis_store**
   - `update_agent_config` method (already exists?)
   - Allow setting `reflex_artifact_id`

7. **Seed genesis reflexes** (optional)
   - `genesis_trading_reflex` - basic trading automation
   - Agents can copy/modify these

---

## Files Affected

- src/world/artifacts.py (modify)
- src/agents/agent.py (modify)
- src/agents/reflex.py (create)
- src/simulation/agent_loop.py (modify)
- src/simulation/runner.py (modify)
- src/world/genesis/store.py (modify)
- config/schema.yaml (modify)
- tests/test_reflex.py (create)

---

## Required Tests

| Test | Description |
|------|-------------|
| `test_reflex_artifact_creation` | Can create artifact with type="reflex" |
| `test_reflex_execution_returns_action` | Reflex returning action skips LLM |
| `test_reflex_none_falls_through` | Reflex returning None triggers LLM |
| `test_reflex_timeout_falls_through` | Slow reflex times out, falls to LLM |
| `test_reflex_error_falls_through` | Reflex error triggers LLM fallback |
| `test_agent_switch_reflex` | Agent can change reflex_artifact_id |
| `test_reflex_context_contents` | Context has expected fields |

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| Reflex execution < 100ms | Timeout enforced |
| LLM bypass on reflex fire | No LLM call when reflex returns action |
| Agents can self-modify reflexes | Create/update reflex artifacts |
| Graceful degradation | Errors fall back to LLM |

---

## ADRs Applied

- ADR-0001: Everything is an Artifact (reflexes are artifacts)
- ADR-0014: Continuous Execution Primary (reflexes enable high-frequency loops)
- ADR-0015: Contracts as Artifacts (reflexes use same sandbox)

---

## Future Enhancements

- **Reflex chaining**: Multiple reflexes in priority order
- **Reflex metrics**: Dashboard showing reflex fire rate vs LLM calls
- **Reflex templates**: Pre-built reflexes for common patterns
