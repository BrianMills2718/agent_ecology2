# Plan #195: Context Budget Management

**Status:** Planned
**Created:** 2025-01-25
**Scope:** Agent Cognitive Autonomy

## Problem

Context window is a scarce resource, but agents have no visibility into or control over how it's allocated. Currently:

- Each section takes whatever space it needs
- Large RAG results can crowd out other content
- Working memory can grow unbounded
- Agents can't prioritize what gets full context vs truncated

This violates the physics-first principle - context should be a managed resource like compute or disk.

## Solution

Treat context as a budgeted resource. Agents can allocate "context budget" to different sections.

### Context Budget Model

```python
# Agent specifies budget allocation (percentages or absolute tokens)
{
    "context_budget": {
        "total_tokens": 4000,  # Or derived from model context window
        "allocations": {
            "system_prompt": {"max_tokens": 500, "priority": "required"},
            "working_memory": {"max_tokens": 800, "priority": "high"},
            "rag_memories": {"max_tokens": 600, "priority": "medium"},
            "action_history": {"max_tokens": 400, "priority": "medium"},
            "recent_events": {"max_tokens": 300, "priority": "low"},
            "subscribed_artifacts": {"max_tokens": 400, "priority": "medium"},
            # ... etc
        },
        "overflow_policy": "truncate_low_priority"  # or "drop_low_priority"
    }
}
```

### Budget Enforcement

During `build_prompt()`:

1. Calculate total available tokens (model limit - output reserve)
2. Allocate to required sections first
3. Allocate to high priority sections
4. Fill remaining budget with medium/low priority
5. Truncate or drop sections that exceed allocation

## Files Affected

- src/agents/agent.py (modify)
- src/config_schema.py (modify)
- config/schema.yaml (modify)
- config/config.yaml (modify)
- tests/unit/test_context_budget.py (create)
- docs/architecture/current/agents.md (modify)

## Implementation

### Design Decision: No New Action Types

To preserve the narrow waist (6 verbs + query), context budget management is implemented
internally via configuration. Agents can customize budgets by:
1. System defaults from config.yaml
2. Writing custom budget config to their working_memory artifact

### Files to Modify

1. **src/agents/agent.py**
   - Add `_count_tokens(text: str) -> int` using litellm.token_counter
   - Add `_truncate_to_budget(section: str, content: str, max_tokens: int) -> str`
   - Add `_get_section_budget(section: str) -> int`
   - Modify `build_prompt()` to apply budgets
   - Add optional budget visibility section

2. **src/config_schema.py**
   - Add `ContextBudgetSectionModel` and `ContextBudgetModel`

3. **config/schema.yaml**
   - `agent.context_budget.enabled`: bool
   - `agent.context_budget.total_tokens`: int
   - `agent.context_budget.output_reserve`: int
   - `agent.context_budget.sections`: {...}

4. **config/config.yaml**
   - Add default context budget values

### Token Counting

Use LiteLLM's built-in token counter for accurate model-specific counting:

```python
from litellm import token_counter

def _count_tokens(self, text: str) -> int:
    """Count tokens using model-specific tokenizer via litellm."""
    messages = [{"role": "user", "content": text}]
    return token_counter(model=self._llm_model, messages=messages)
```

This uses model-specific tokenizers (tiktoken for OpenAI, etc.) and falls back to tiktoken for unknown models. Much more accurate than character-based estimation.

### Truncation Strategies

```python
def _truncate_section(self, content: str, max_tokens: int, section_type: str) -> str:
    actual = self._count_tokens(content)
    if actual <= max_tokens:
        return content

    # Strategy depends on section type
    if section_type in ["action_history", "failure_history"]:
        # Keep most recent entries
        lines = content.split("\n")
        while self._count_tokens("\n".join(lines)) > max_tokens and len(lines) > 1:
            lines.pop(0)  # Remove oldest
        return "\n".join(lines) + "\n[...older entries truncated]"

    elif section_type == "rag_memories":
        # Keep highest relevance (assume ordered by relevance)
        lines = content.split("\n")
        while self._count_tokens("\n".join(lines)) > max_tokens and len(lines) > 1:
            lines.pop()  # Remove least relevant (last)
        return "\n".join(lines) + "\n[...lower relevance truncated]"

    else:
        # Generic: binary search for truncation point
        # Start with half and adjust
        chars = len(content)
        while self._count_tokens(content[:chars]) > max_tokens and chars > 100:
            chars = chars // 2
        return content[:chars] + "\n[...truncated]"
```

## Design Considerations

### Dynamic vs Static Budget

Options:
1. **Static**: Agent sets budget once, applies every tick
2. **Dynamic**: Agent can adjust budget per-tick based on situation

Recommend starting with static, add dynamic later if needed.

### Budget Visibility

Agents should see their budget usage in prompts:
```
## Context Budget
Using 3200/4000 tokens (80%)
- system_prompt: 450/500
- working_memory: 780/800 (near limit!)
- rag_memories: 400/600
- ...
```

This enables agents to reason about their context allocation.

### Interaction with Other Plans

- **Plan #191 (Subscribed Artifacts)**: Budget applies to subscribed content
- **Plan #192 (Section Control)**: Disabled sections use 0 budget
- **Plan #193 (Priority)**: Budget priority separate from ordering priority

## Testing

```bash
pytest tests/unit/test_context_budget.py -v
```

### Test Cases

1. Section exceeds budget, verify truncation
2. Total prompt exceeds budget, verify overflow policy
3. Required sections always included
4. Low priority dropped when over budget
5. Budget visibility in prompt
6. Persistence across checkpoint/restore

## Acceptance Criteria

- [ ] Agent can set per-section token budgets
- [ ] Budget enforcement during prompt building
- [ ] Truncation strategies per section type
- [ ] Overflow policy (truncate vs drop)
- [ ] Budget usage visibility in prompt
- [ ] Required sections cannot be budget-starved
- [ ] Persistence via agent artifact state
