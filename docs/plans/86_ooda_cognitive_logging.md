# Plan #86: OODA Cognitive Logging

**Status:** 📋 Planned
**Priority:** High
**Blocks:** Agent observability, debugging, emergence analysis

## Problem Statement

Two related bugs in agent feedback/logging:

1. **`reasoning` field always empty** - The `reasoning` field in action events is always `""` despite `thought_process` being populated in thinking events. The code at `runner.py:693` attempts to copy `thought_process` → `reasoning` but fails silently.

2. **`{recent_failures}` never populated** - Agent prompts reference `{recent_failures}` but this template variable is never populated, preventing agents from learning from past mistakes.

Additionally, the current `thought_process` field conflates situation analysis with action rationale, making logs less tractable for debugging and pattern analysis.

## Solution: OODA-Aligned Cognitive Schema

Introduce a configurable cognitive schema based on the OODA loop (Observe-Orient-Decide-Act):

| Phase | Field | Purpose |
|-------|-------|---------|
| Orient | `situation_assessment` | Full analysis of current state (can be verbose) |
| Decide | `action_rationale` | Concise 1-2 sentence explanation of why THIS action |
| Act | `action` | The action to execute |

### Configuration

```yaml
# config.yaml
agent:
  cognitive_schema: "simple"  # "simple" | "ooda"
```

- **simple** (default): Current behavior - `thought_process` + `action`
- **ooda**: New structured output - `situation_assessment` + `action_rationale` + `action`

## Implementation

### Phase 1: Fix Existing Bugs

1. **Debug and fix `reasoning` field bug**
   - Add debug logging to `_execute_proposals` to identify why `proposal.get("thought_process", "")` returns empty
   - Fix the root cause

2. **Implement `recent_failures` tracking**
   - Add `failure_history: list[str]` to Agent class
   - Update `set_last_result()` to track failures
   - Populate `{recent_failures}` in prompt template context

### Phase 2: OODA Schema

1. **Add Pydantic models**
   ```python
   # src/agents/models.py
   class OODAResponse(BaseModel):
       situation_assessment: str = Field(description="Analysis of current state and options")
       action_rationale: str = Field(description="Concise explanation for this specific action (1-2 sentences)")
       action: ActionField
   ```

2. **Add config option**
   ```yaml
   # config/schema.yaml
   agent:
     cognitive_schema:
       type: str
       default: "simple"
       enum: ["simple", "ooda"]
       description: "Cognitive response schema for agents"
   ```

3. **Update Agent.propose_action_async()**
   - Check config for schema type
   - Use appropriate Pydantic model
   - Return appropriate fields

4. **Update logging**
   - Thinking events: Include `situation_assessment` and `action_rationale` (OODA mode)
   - Action events: `reasoning` = `action_rationale` (OODA) or `thought_process` (simple)

5. **Update prompts**
   - Add instructions for OODA output when in OODA mode
   - Emphasize conciseness for `action_rationale`

### Phase 3: Dashboard Integration

1. Update thinking panel to show OODA fields when available
2. Show tractable `action_rationale` in action summaries

## Required Tests

```
tests/unit/test_agent_cognitive_schema.py:
  - test_simple_schema_returns_thought_process
  - test_ooda_schema_returns_structured_output
  - test_action_rationale_included_in_reasoning
  - test_recent_failures_populated_after_failure
  - test_recent_failures_empty_on_success
  - test_config_toggle_switches_schema

tests/integration/test_ooda_logging.py:
  - test_ooda_thinking_event_has_both_fields
  - test_ooda_action_event_has_rationale_as_reasoning
  - test_simple_mode_backward_compatible
```

## Acceptance Criteria

- [ ] `reasoning` field populated in action events (both modes)
- [ ] `{recent_failures}` populated in agent prompts after failures
- [ ] OODA mode produces `situation_assessment` and `action_rationale`
- [ ] `action_rationale` is concise (enforced via prompt, validated in tests)
- [ ] Config toggle works: `cognitive_schema: simple | ooda`
- [ ] Dashboard displays OODA fields when present
- [ ] Backward compatible - simple mode works exactly as before

## Token Cost Analysis

OODA mode adds ~20-50 output tokens per turn:
- `action_rationale`: ~20-30 tokens (1-2 sentences)
- Slightly shorter `situation_assessment` vs `thought_process`: ~0-20 token savings

Net cost: ~$0.0001-0.0005 per agent turn. Acceptable for improved observability.

## Migration

- Default to `simple` mode (no breaking changes)
- OODA mode is opt-in via config
- Existing logs remain valid
- No schema migration needed

## Related

- Plan #49: Reasoning in Narrow Waist (original reasoning field implementation)
- Plan #60: Tractable Logs
- Plan #87: Full Cognitive Schema Configurability (deferred)
