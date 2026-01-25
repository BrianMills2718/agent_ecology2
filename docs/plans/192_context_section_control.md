# Plan #192: Context Section Control

**Status:** ✅ Complete
**Created:** 2025-01-25
**Scope:** Agent Cognitive Autonomy

## Problem

Agents have no control over which sections get injected into their prompt. All sections are hardcoded in `build_prompt()`:

- Working memory
- RAG memories
- Action history
- Failure history
- Recent events
- Resource metrics
- Mint submissions
- Quota info
- Metacognitive prompts

An agent focused on a specific task might not need the noise of recent events or mint submissions. An agent low on context budget might want to disable verbose sections.

## Solution

Allow agents to configure which prompt sections are enabled/disabled via their artifact state.

### Agent State Extension

```python
# In agent artifact content
{
    "llm_model": "...",
    "system_prompt": "...",
    "context_sections": {
        "working_memory": true,      # default: true
        "rag_memories": true,        # default: true
        "action_history": true,      # default: true
        "failure_history": true,     # default: true
        "recent_events": false,      # can disable
        "resource_metrics": true,    # default: true
        "mint_submissions": false,   # can disable
        "quota_info": true,          # default: true
        "metacognitive": false,      # can disable
        "subscribed_artifacts": true # default: true (Plan #191)
    }
}
```

### New Action

```yaml
configure_context:
  sections:
    working_memory: boolean
    rag_memories: boolean
    action_history: boolean
    # ... etc
```

### Prompt Builder Changes

```python
def build_prompt(self, world_state: dict[str, Any]) -> str:
    sections = self._context_sections or {}

    # Only include enabled sections
    if sections.get("working_memory", True):
        prompt += working_memory_section

    if sections.get("rag_memories", True):
        prompt += memories_section

    # ... etc
```

## Implementation

### Files to Modify

1. **src/agents/agent.py**
   - Add `_context_sections: dict[str, bool]` field
   - Load from artifact content
   - Conditionally include sections in `build_prompt()`

2. **src/agents/schema.py**
   - Add `configure_context` action type

3. **src/world/executor.py**
   - Handle configure_context action
   - Update agent artifact state

4. **config/schema.yaml**
   - Add `agent.context_sections.defaults` with all section defaults

## Design Considerations

### Required vs Optional Sections

Some sections might be required for agent functionality:
- **Required**: System prompt, action schema, world summary (basic state)
- **Optional**: Everything else

Agents cannot disable required sections.

### Section Dependencies

Some sections might depend on others:
- `metacognitive` depends on `action_history` (pattern analysis)

If a section is disabled, dependent sections should also be disabled or gracefully degrade.

## Testing

```bash
pytest tests/unit/test_context_sections.py -v
```

### Test Cases

1. Disable section, verify not in prompt
2. Re-enable section, verify appears
3. Cannot disable required sections
4. Dependency handling (disable parent disables child)
5. Default values when no config
6. Persistence across checkpoint/restore

## Acceptance Criteria

- [x] Agent can configure which sections are enabled
- [x] Disabled sections don't appear in prompt
- [x] Required sections cannot be disabled (validated in schema)
- [x] Default configuration when not specified
- [x] Persistence via agent artifact state
- [x] Action to update configuration (configure_context)
