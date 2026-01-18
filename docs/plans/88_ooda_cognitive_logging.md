# Plan #88: OODA Cognitive Logging

**Status:** 🚧 In Progress
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

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_agent_cognitive_schema.py` | `test_propose_action_async_returns_thought_process` | thought_process returned in proposal |
| `tests/unit/test_agent_cognitive_schema.py` | `test_proposal_structure_has_thought_process` | proposal dict has thought_process key |
| `tests/unit/test_agent_cognitive_schema.py` | `test_failure_history_initialized_empty` | Agent starts with empty failure history |
| `tests/unit/test_agent_cognitive_schema.py` | `test_failure_added_on_failed_action` | Failures tracked in history |
| `tests/unit/test_agent_cognitive_schema.py` | `test_success_does_not_add_to_failures` | Success doesn't pollute failure history |
| `tests/unit/test_agent_cognitive_schema.py` | `test_failure_history_respects_max_limit` | Failure history capped at config max |
| `tests/unit/test_agent_cognitive_schema.py` | `test_failures_appear_in_prompt` | Recent failures shown in agent prompts |
| `tests/unit/test_agent_cognitive_schema.py` | `test_no_failures_section_when_empty` | No failures section if no failures |
| `tests/unit/test_agent_cognitive_schema.py` | `test_ooda_response_model_fields` | OODA model has required fields |
| `tests/unit/test_agent_cognitive_schema.py` | `test_flat_ooda_response_converts_to_ooda_response` | FlatOODA converts to OODA |
| `tests/unit/test_agent_cognitive_schema.py` | `test_ooda_mode_returns_ooda_fields` | OODA mode returns OODA fields |
| `tests/unit/test_agent_cognitive_schema.py` | `test_simple_mode_returns_thought_process_only` | Simple mode backward compatible |
| `tests/unit/test_agent_cognitive_schema.py` | `test_config_toggle_switches_schema` | Config switches between schemas |
| `tests/integration/test_ooda_logging.py` | `test_thinking_result_has_thought_process` | Integration: thinking has thought_process |
| `tests/integration/test_ooda_logging.py` | `test_proposal_structure_for_execute` | Integration: proposal structure correct |
| `tests/integration/test_ooda_logging.py` | `test_end_to_end_reasoning_flow` | Integration: full reasoning flow |

## Acceptance Criteria

- [x] `reasoning` field populated in action events (both modes)
- [x] `{recent_failures}` populated in agent prompts after failures
- [x] OODA mode produces `situation_assessment` and `action_rationale`
- [x] `action_rationale` is concise (enforced via Pydantic Field description)
- [x] Config toggle works: `cognitive_schema: simple | ooda`
- [x] Dashboard displays OODA fields when present
- [x] Backward compatible - simple mode works exactly as before

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

## Files Affected

- src/simulation/runner.py (modify) - Fix reasoning field propagation bug
- src/agents/agent.py (modify) - Add recent_failures tracking, OODA schema support
- src/agents/models.py (modify) - Add OODAResponse Pydantic model
- src/agents/schema.py (modify) - Add OODA schema instructions for LLM
- src/config_schema.py (modify) - Add failure_history_max and cognitive_schema to config schema
- config/schema.yaml (modify) - Add cognitive_schema config option
- config/config.yaml (modify) - Add cognitive_schema default value
- src/dashboard/static/js/panels/thinking.js (modify) - Display OODA fields in thinking panel
- src/dashboard/static/css/dashboard.css (modify) - Add OODA-specific styles
- tests/unit/test_agent_cognitive_schema.py (create) - Unit tests for cognitive schema
- tests/integration/test_ooda_logging.py (create) - Integration tests for OODA logging
- docs/architecture/current/agents.md (modify) - Document failure tracking and OODA
- docs/architecture/current/execution_model.md (modify) - Document reasoning propagation
- docs/architecture/current/configuration.md (modify) - Document cognitive_schema config

## Related

- Plan #49: Reasoning in Narrow Waist (original reasoning field implementation)
- Plan #60: Tractable Logs
- Plan #89: Full Cognitive Schema Configurability (deferred)
