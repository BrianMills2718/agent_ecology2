# Plan #194: Self-Modifying System Prompt

**Status:** ✅ Complete
**Created:** 2025-01-25
**Scope:** Agent Cognitive Autonomy

## Problem

While agents can technically modify their system prompt by writing to their own artifact, this requires:
1. Reading the full artifact content
2. Parsing the JSON
3. Modifying the system_prompt field
4. Writing the entire artifact back

This is error-prone (JSON parse errors break the agent) and wasteful (full artifact rewrite for small changes).

Agents should have a cleaner mechanism to:
- Append to their system prompt (add new instructions)
- Replace specific sections
- Reset to original prompt

## Solution

Provide dedicated actions for system prompt modification with safety guarantees.

### New Actions

```yaml
modify_system_prompt:
  operation: "append" | "prepend" | "replace_section" | "reset"
  content: string           # For append/prepend
  section_marker: string    # For replace_section (e.g., "## Goals")
  section_content: string   # New content for section

# Example: Add a new goal
modify_system_prompt:
  operation: append
  content: "\n\n## Learned Behavior\nAlways check balances before transfers."

# Example: Replace goals section
modify_system_prompt:
  operation: replace_section
  section_marker: "## Goals"
  section_content: "## Goals\n1. Maximize profit\n2. Minimize risk"
```

### Section Markers

Agents can use markdown headers as section markers:
```markdown
## Core Identity
I am a trading agent.

## Goals
1. Maximize scrip

## Learned Behaviors
[This section can be modified]
```

### Safety Guarantees

1. **Size limit**: System prompt cannot exceed `max_system_prompt_bytes` (default: 8000)
2. **Required prefix**: Original first N chars preserved (identity protection)
3. **Validation**: Syntax check before applying
4. **Rollback**: If prompt becomes invalid, revert to previous

## Implementation

### Files to Modify

1. **src/agents/agent.py**
   - Add `modify_system_prompt()` method
   - Add `_original_system_prompt` to track baseline
   - Add `_system_prompt_modifications: list[dict]` for history

2. **src/agents/schema.py**
   - Add `modify_system_prompt` action type

3. **src/world/executor.py**
   - Handle modify_system_prompt action
   - Apply size limits and validation
   - Update agent artifact

4. **config/schema.yaml**
   - `agent.system_prompt.max_size_bytes`: 8000
   - `agent.system_prompt.protected_prefix_chars`: 200

### Operation Details

#### Append
```python
def _append_to_prompt(self, content: str) -> str:
    new_prompt = self._system_prompt + "\n" + content
    if len(new_prompt) > self._max_prompt_size:
        raise ValueError("System prompt would exceed size limit")
    return new_prompt
```

#### Replace Section
```python
def _replace_section(self, marker: str, content: str) -> str:
    # Find section start
    start = self._system_prompt.find(marker)
    if start == -1:
        raise ValueError(f"Section '{marker}' not found")

    # Find section end (next ## or end of string)
    end = self._system_prompt.find("\n##", start + len(marker))
    if end == -1:
        end = len(self._system_prompt)

    # Replace
    return self._system_prompt[:start] + content + self._system_prompt[end:]
```

#### Reset
```python
def _reset_prompt(self) -> str:
    return self._original_system_prompt
```

## Testing

```bash
pytest tests/unit/test_system_prompt_modification.py -v
```

### Test Cases

1. Append content, verify in prompt
2. Prepend content, verify at start
3. Replace section by marker
4. Replace non-existent section (error)
5. Exceed size limit (rejected)
6. Reset to original
7. Protected prefix cannot be modified
8. Invalid content rejected
9. Persistence across checkpoint/restore

## Acceptance Criteria

- [x] Agent can append to system prompt
- [x] Agent can prepend to system prompt
- [x] Agent can replace sections by marker
- [x] Agent can reset to original prompt
- [x] Size limits enforced
- [x] Protected prefix preserved
- [x] Modifications persist via artifact state
- [x] History of modifications tracked (optional)
