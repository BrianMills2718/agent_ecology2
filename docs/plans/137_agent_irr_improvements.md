# Plan #137: Agent IRR Improvements

**Status:** ✅ Complete
**Priority:** High
**Blocked By:** None
**Blocks:** Agent capability improvements

## Context

Code review identified several improvements inspired by StructGPT's Iterative Reading-then-Reasoning (IRR) pattern. This plan consolidates four related changes that improve agent capability without exposing provider complexity.

## Goals

1. **Unify response models** - Always use FlatActionResponse for all providers (eliminates Gemini-specific code paths)
2. **Improve gen 3 state machines** - Add discovery/validation states for better IRR patterns
3. **Interface checking config** - Add configurable `try_and_learn` mode for interface discovery
4. **Handbook update** - Document interface discovery best practices

## Changes

### 1. Unify on FlatActionResponse

**Problem:** `agent.py` has `if self._is_gemini_model()` conditionals that use different response models per provider.

**Solution:** Always use `FlatActionResponse` since it works with all providers.

**Files:**
- src/agents/agent.py

**Before:**
```python
if self._is_gemini_model():
    response = llm.generate(prompt, response_model=FlatActionResponse)
else:
    response = llm.generate(prompt, response_model=ActionResponse)
```

**After:**
```python
response = llm.generate(prompt, response_model=FlatActionResponse)
```

Also remove:
- `_is_gemini_model()` method (no longer needed)
- All Gemini-specific conditionals

### 2. Improve Gen 3 State Machines

**Problem:** Gen 3 agents have state machines but don't include discovery/validation states that would support IRR patterns.

**Solution:** Add optional states to agent workflow configs that agents can use for evidence collection.

**Files:**
- src/agents/alpha_3/agent.yaml (example)
- src/agents/_template/agent.yaml (document pattern)

**New state machine pattern:**
```yaml
workflow:
  state_machine:
    states: ["observing", "discovering", "planning", "executing", "reflecting"]
    transitions:
      - from: "observing"
        to: "discovering"
        condition: "needs_interface_info"
      - from: "discovering"
        to: "planning"
        condition: "has_evidence"
      - from: "planning"
        to: "executing"
      - from: "executing"
        to: "reflecting"
      - from: "reflecting"
        to: "observing"
```

### 3. Interface Checking Config

**Problem:** No configuration for how agents should handle unfamiliar artifact interfaces.

**Solution:** Add `interface_discovery` config section to agent.yaml.

**Files:**
- src/config_schema.py (add schema)
- src/agents/_template/agent.yaml (document)

**Config:**
```yaml
# In agent.yaml
interface_discovery:
  mode: try_and_learn  # try_and_learn | check_first | hybrid
  cache_in_memory: true  # remember interfaces in working memory
```

**Modes:**
- `try_and_learn` (default): Try invocation, learn from error feedback
- `check_first`: Always call get_interface before invoking unfamiliar artifacts
- `hybrid`: Check for complex methods, try simple ones

### 4. Handbook Update

**Problem:** Handbook doesn't guide agents on when/how to discover interfaces.

**Solution:** Add section to `_handbook/tools.md` about interface discovery.

**Files:**
- src/agents/_handbook/tools.md

**New section:**
```markdown
## Invoking Unfamiliar Artifacts

When invoking an artifact you haven't used before:

### Option 1: Try and Learn (Recommended)
Just try invoking with your best guess at arguments. If it fails,
the error message will include the interface schema showing the
correct method signatures.

### Option 2: Check Interface First
If you want to be sure before invoking:
1. Call `genesis_store.get_interface(artifact_id)`
2. Review the returned schema for method names and argument types
3. Then invoke with correct arguments

### Option 3: Check Working Memory
If you've invoked this artifact before, check your working memory
for cached interface information.

The recommended approach is Option 1 - it's faster and you learn
from real feedback.
```

## Files Affected

- src/agents/agent.py (modify - remove Gemini conditionals)
- src/agents/alpha_3/agent.yaml (modify - example improved states)
- src/agents/_template/agent.yaml (modify - document patterns)
- src/agents/_handbook/tools.md (modify - add interface section)
- src/config_schema.py (modify - add interface_discovery schema)
- docs/plans/137_agent_irr_improvements.md (create - this plan)
- docs/plans/138_provider_union_schema_transform.md (create - deferred fallback)

## Testing

```bash
# Unit tests - verify flat response works
pytest tests/unit/test_models.py -v

# Integration - verify agents work with unified response model
pytest tests/integration/test_agent_workflow.py -v

# E2E - verify simulation runs
pytest tests/e2e/test_smoke.py -v
```

## Acceptance Criteria

- [x] `_is_gemini_model()` method removed from agent.py
- [x] All response model conditionals removed
- [x] FlatActionResponse used for all providers
- [x] Interface discovery section added to handbook
- [x] interface_discovery config schema added
- [x] At least one gen 3 agent has improved state machine example
- [x] All tests pass

## Notes

- Plan #138 documents the alternative approach (provider-level schema transform) in case this simpler approach causes issues
- The flat model approach was chosen because it works everywhere and is simpler
- Gen 3 state machine improvements are optional patterns, not breaking changes
