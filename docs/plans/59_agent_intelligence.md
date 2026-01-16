# Plan 59: Agent Intelligence Patterns

**Status:** 🚧 In Progress
**Priority:** High
**Blocked By:** #57 (merge first for prompt baseline)
**Blocks:** -

---

## Gap

**Current:** Agents have comprehensive tool documentation but no persistent working memory. Semantic search (Mem0) retrieves episodic memories but doesn't reliably surface goal state. Agents operate reactively, building trivial artifacts.

**Target:** Agents maintain structured working memory (current goal, progress, lessons) that is automatically injected into prompts. Enables complex, multi-step goal pursuit.

**Why High:** Core thesis requires emergent capability. Reactive agents can't produce emergence - they need context persistence to pursue complex goals.

---

## Plan

### Approach: Structured Self-Artifact Memory

**Key insight:** Agents are already artifacts. They can write to themselves via the narrow waist. We add a structured `working_memory` section to agent content that the system auto-injects.

### How It Works

1. **Agent artifact content includes `working_memory` section**
```yaml
{
  "model": "gemini-3-flash",
  "system_prompt": "...",
  "working_memory": {
    "current_goal": "Build price oracle",
    "started": "2026-01-16T10:30:00Z",
    "progress": {
      "stage": "Implementation",
      "completed": ["interface design"],
      "next_steps": ["core logic", "tests"],
      "actions_in_stage": 3
    },
    "lessons": ["escrow needs ownership transfer first"],
    "strategic_objectives": ["become known for pricing"]
  }
}
```

2. **System auto-injects into prompt** (in `propose_action`)
```python
# After existing memory retrieval
if self.inject_working_memory:  # configurable
    working_mem = self._get_working_memory()
    if working_mem:
        prompt += f"\n## Your Working Memory\n{format_working_memory(working_mem)}"
```

3. **Agent updates via write_artifact to self**
```json
{"action_type": "write_artifact", "artifact_id": "alpha", "content": "{...updated...}"}
```

4. **No new action type, no hoping for compliance**

---

## Configuration

All options in `config.yaml` under `agent.working_memory`:

```yaml
agent:
  working_memory:
    enabled: true                    # Master switch
    auto_inject: true                # Inject into prompt automatically
    max_size_bytes: 2000             # Limit to prevent bloat
    include_in_rag: false            # Also include in semantic search?
    structured_format: true          # Enforce YAML schema vs freeform
    warn_on_missing: false           # Log warning if agent has no working memory
```

---

## Changes Required

| File | Change |
|------|--------|
| `config/config.yaml` | Add `agent.working_memory` section |
| `src/config_schema.py` | Add `WorkingMemoryConfig` Pydantic model |
| `src/agents/agent.py` | Add `_get_working_memory()` and injection in `propose_action` |
| `src/agents/_handbook/memory.md` | NEW: Document working memory pattern |
| `src/agents/_handbook/intelligence.md` | NEW: Meta-patterns for goal pursuit |
| `src/agents/_handbook/_index.md` | Add new sections |
| `src/agents/_template/system_prompt.md` | Reference new handbooks |

---

## Downsides & Risks

### 1. Kernel Opinion
**Risk:** Adding structured working memory is a kernel opinion about how agents should think.

**Mitigation:**
- Fully configurable (can disable entirely)
- Agents can ignore it (just don't update)
- Schema is minimal, not prescriptive

**Accept for now, revisit in V2.**

### 2. Prompt Length Bloat
**Risk:** Working memory adds tokens to every prompt, increasing cost.

**Mitigation:**
- `max_size_bytes` config limits size
- Only inject if non-empty
- Monitor token usage in dashboard

### 3. Agents May Not Update Memory
**Risk:** Agents may read working memory but never write updates.

**Mitigation:**
- Not a problem - they just operate without goals
- Selection pressure: agents with working memory outperform
- Could add "stale memory" warning in future (V2)

### 4. Schema Coupling
**Risk:** If we change working memory schema, existing agents break.

**Mitigation:**
- Keep schema minimal and stable
- Version the schema if needed
- Graceful degradation (missing fields = empty)

### 5. Semantic Search Confusion
**Risk:** If `include_in_rag: true`, working memory may pollute semantic search results.

**Mitigation:**
- Default to `false`
- Keep working memory separate from episodic memory

---

## Alternatives for Future Versions

### V2: Agent-Managed Memory Artifacts
Instead of embedding in agent artifact, agents create separate `{id}_memory` artifacts.
- **Pro:** Observable, tradeable, can be larger
- **Con:** Requires agent action to read (unreliable)
- **When:** If prompt bloat becomes problematic

### V2: Memory Decay
Working memory entries older than N actions auto-expire.
- **Pro:** Prevents stale context
- **Con:** Adds complexity
- **When:** If agents accumulate irrelevant context

### V2: Hierarchical Memory
L1: Working memory (current goal) - always injected
L2: Episodic memory (recent events) - RAG
L3: Strategic memory (long-term objectives) - periodic injection
- **Pro:** Better organization
- **Con:** More complexity
- **When:** If single-level memory proves insufficient

### V2: Goal Validation
System checks if claimed progress matches event log.
- **Pro:** Prevents hallucinated progress
- **Con:** Adds kernel opinion about "truth"
- **When:** If agents consistently lie to themselves

### V3: Emergent Memory Protocols
Remove all system-provided memory. Agents must build their own.
- **Pro:** Pure emergence
- **Con:** Higher barrier to useful behavior
- **When:** Once ecosystem is mature enough

---

## Implementation Steps

1. Add config schema for `agent.working_memory`
2. Add `_get_working_memory()` method to Agent class
3. Modify `propose_action` to inject working memory if enabled
4. Create `handbook_memory.md` documenting the pattern
5. Create `handbook_intelligence.md` with goal pursuit patterns
6. Update handbook index
7. Update template prompt to reference new handbooks
8. Test with simulation run

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_agent.py` | `test_working_memory_injection_enabled` | Memory injected when config enabled |
| `tests/unit/test_agent.py` | `test_working_memory_injection_disabled` | Memory NOT injected when config disabled |
| `tests/unit/test_agent.py` | `test_working_memory_size_limit` | Large memory truncated to max_size_bytes |
| `tests/unit/test_agent.py` | `test_working_memory_missing_graceful` | No crash if working_memory absent |
| `tests/integration/test_agent_memory.py` | `test_agent_updates_own_memory` | Agent can write to self |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/e2e/test_smoke.py` | Basic simulation still works |
| `tests/unit/test_agent.py` | Agent behavior unchanged when disabled |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Memory injection | Run simulation, check prompts | Working memory appears in agent prompts |
| Memory update | Agent writes to self | Working memory reflects update |
| Config disabled | Set `enabled: false` | No working memory in prompts |

---

## Verification Checklist

### Tests & Quality
- [ ] All required tests pass
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `mypy src/`
- [ ] E2E verification passes

### Documentation
- [ ] Handbook files created
- [ ] Config documented in schema.yaml
- [ ] Downsides documented (this section)

### Completion
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released
- [ ] PR created/merged

---

## Notes

### Design Decisions

1. **Embed in agent artifact, not separate artifact** - Reliability over purity. System always has access.

2. **Auto-inject by default** - Opt-out rather than opt-in. Goal is to improve baseline intelligence.

3. **Configurable everything** - User can disable, limit size, change behavior.

4. **No enforcement** - Agents can ignore working memory. Selection pressure, not enforcement.

### Philosophy Alignment

| Principle | How We Align |
|-----------|--------------|
| Emergence over prescription | Memory is optional, agents choose to use it |
| Physics-first | Working memory costs disk (part of agent artifact) |
| Minimal kernel | Uses existing primitives (artifacts, write_artifact) |
| Configurable | All aspects configurable |
| Fail loud | Missing config = use defaults, not crash |

### Research Context

Based on analysis of BabyAGI, LangGraph, AutoGen, CrewAI, MetaGPT, and autonomous coding agents. Key insight: the problem is context management, not capability. Agents lose track of complex goals without explicit memory externalization.
