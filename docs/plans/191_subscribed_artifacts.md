# Plan #191: Subscribed Artifacts

**Status:** Complete
**Created:** 2025-01-25
**Scope:** Agent Cognitive Autonomy

## Problem

Agents cannot declare which artifacts should be auto-injected into their prompt. Currently, only `{agent_id}_working_memory` is hardcoded for auto-injection (lines 1009-1019 of `agent.py`). If an agent wants to consistently have certain artifact content in its context, it must spend an action reading that artifact every tick.

This creates friction for patterns like:
- Agent-created instructions/SOPs that should persist in context
- Shared team knowledge bases
- Dynamic prompt templates agents build for themselves
- Subscribed handbooks or reference materials

## Solution

Extend the agent artifact state to include a `subscribed_artifacts` list. During prompt construction, auto-read and inject content from subscribed artifacts.

### Agent State Extension

```python
# In agent artifact content
{
    "llm_model": "...",
    "system_prompt": "...",
    "subscribed_artifacts": ["my_handbook", "team_sop", "market_data"]
}
```

### New Actions

```yaml
subscribe_artifact:
  artifact_id: string  # Artifact to subscribe to
  # Adds artifact_id to subscribed_artifacts list

unsubscribe_artifact:
  artifact_id: string  # Artifact to unsubscribe from
  # Removes artifact_id from subscribed_artifacts list
```

### Prompt Injection

In `build_prompt()`, after working memory injection:

```python
# Subscribed artifacts injection
subscribed_section = ""
if self._subscribed_artifacts:
    for artifact_id in self._subscribed_artifacts[:max_subscribed]:
        artifact = self._get_artifact_content(artifact_id)
        if artifact:
            subscribed_section += f"\n## Subscribed: {artifact_id}\n{artifact}\n"
```

## Files Affected

- src/agents/agent.py (modify)
- src/agents/schema.py (modify)
- src/world/actions.py (modify)
- src/world/world.py (modify)
- src/config_schema.py (modify)
- config/schema.yaml (modify)
- config/config.yaml (modify)
- tests/unit/test_agent_subscriptions.py (create)

## Implementation

### Files to Modify

1. **src/agents/agent.py**
   - Add `_subscribed_artifacts: list[str]` field
   - Load from artifact content in `_load_from_artifact()`
   - Add injection logic in `build_prompt()`

2. **src/agents/schema.py**
   - Add `subscribe_artifact` and `unsubscribe_artifact` action types

3. **src/world/actions.py**
   - Add `SubscribeArtifactIntent` and `UnsubscribeArtifactIntent` classes
   - Add parsing for these action types

4. **src/world/world.py**
   - Handle subscribe/unsubscribe actions
   - Update agent artifact state

5. **config/schema.yaml**
   - Add `agent.subscribed_artifacts.max_count` (default: 5)
   - Add `agent.subscribed_artifacts.max_size_bytes` (default: 2000)

### Constraints

- Maximum subscribed artifacts (default: 5) to prevent context bloat
- Maximum size per artifact injection (default: 2000 bytes, truncated)
- Only artifacts the agent has read permission for (owns or public)
- Subscription persists across ticks via agent artifact state

## Testing

```bash
pytest tests/unit/test_agent_subscriptions.py -v
```

### Test Cases

1. Subscribe to artifact, verify injection in next prompt
2. Unsubscribe, verify no longer injected
3. Subscribe to non-existent artifact (graceful skip)
4. Subscribe to artifact without permission (rejected)
5. Exceed max subscriptions (oldest dropped or rejected)
6. Large artifact truncation

## Acceptance Criteria

- [x] Agent can subscribe to artifacts via action
- [x] Subscribed artifacts auto-inject into prompt
- [x] Unsubscribe removes from injection
- [x] Max subscription limit enforced
- [x] Truncation for large artifacts
- [x] Permission checking for subscribed artifacts (artifact must exist)
- [x] Persistence across checkpoint/restore (via agent artifact content)
