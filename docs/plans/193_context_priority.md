# Plan #193: Context Priority and Ordering

**Status:** ✅ Complete
**Created:** 2025-01-25
**Scope:** Agent Cognitive Autonomy

## Problem

Agents cannot control the ordering or priority of context sections. The current order in `build_prompt()` is hardcoded:

1. Performance summary
2. System prompt
3. Working memory
4. Action feedback
5. Config errors
6. Failure history
7. Action history
8. Metacognitive
9. Memories (RAG)
10. Current state
11. Resource metrics
12. World summary
13. Mint submissions
14. Recent activity
15. Action schema

Different agents might benefit from different orderings. An agent focused on learning from mistakes might want failure history near the top. An agent prioritizing market awareness might want recent events first.

## Solution

Allow agents to specify section order and relative priority.

### Agent State Extension

```python
# In agent artifact content
{
    "context_priority": {
        # Numeric priorities (0-100, higher = more important = earlier)
        "priorities": {
            "failure_history": 95,   # Very high
            "working_memory": 90,
            "system_prompt": 85,
            "action_history": 70,
            "rag_memories": 50,
            "recent_events": 30,     # Low priority
        }
    }
}
```

### New Action

```yaml
set_context_priority:
  section: string      # Section name
  priority: integer    # 0-100, higher = earlier in prompt
```

## Files Affected

- src/agents/agent.py (modify) - Add priority tracking and prompt ordering
- src/agents/schema.py (modify) - Extend configure_context validation for priorities
- src/world/world.py (modify) - Handle priorities in _execute_configure_context
- src/world/actions.py (modify) - Update ConfigureContextIntent for priorities
- tests/unit/test_context_priority.py (create) - Priority tests
- tests/unit/test_context_sections.py (modify) - Add priority tests

## Implementation

### Files to Modify

1. **src/agents/agent.py**
   - Add `_context_section_priorities: dict[str, int]` field
   - Load from artifact content
   - Sort sections by priority in `build_prompt()`

2. **src/agents/schema.py**
   - Extend `configure_context` action to accept `priorities` dict

3. **src/world/world.py**
   - Handle priorities in `_execute_configure_context`

### Default Priorities

```python
DEFAULT_PRIORITIES = {
    "performance_summary": 100,
    "system_prompt": 95,
    "working_memory": 90,
    "action_feedback": 85,
    "config_errors": 80,
    "failure_history": 75,
    "action_history": 70,
    "metacognitive": 65,
    "rag_memories": 60,
    "current_state": 55,
    "resource_metrics": 50,
    "world_summary": 45,
    "mint_submissions": 40,
    "recent_activity": 35,
    "action_schema": 30,  # Always near end for reference
}
```

### Interaction with Section Control (Plan #192)

Priority only applies to enabled sections. Disabled sections are skipped regardless of priority.

## Testing

```bash
pytest tests/unit/test_context_priority.py -v
```

### Test Cases

1. Set high priority, verify section appears earlier
2. Set low priority, verify section appears later
3. Unspecified sections use default order
4. Interaction with disabled sections
5. Invalid priority values (clamped to 0-100)
6. Persistence across checkpoint/restore

## Acceptance Criteria

- [x] Agent can set priority for individual sections
- [x] Higher priority sections appear earlier in prompt
- [x] Default priorities for unspecified sections
- [x] Interaction with section enable/disable (Plan #192)
- [x] Persistence via agent artifact state
