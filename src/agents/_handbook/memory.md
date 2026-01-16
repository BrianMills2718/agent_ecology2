# Working Memory Pattern (Plan #59)

Structured context that persists across turns, enabling complex multi-step goals.

## What is Working Memory?

Working memory is a structured section in your agent artifact that tracks:
- **current_goal**: What you're working toward
- **progress**: Stage, completed steps, next steps
- **lessons**: What you've learned
- **strategic_objectives**: Long-term aims

## How It Works

1. **Auto-injected**: If enabled, your working memory appears in every prompt
2. **You control updates**: Write to yourself to update working memory
3. **Persists across turns**: Unlike memories, working memory is always visible

## Updating Working Memory

To update your working memory, write to your own artifact:

```json
{
  "action_type": "write_artifact",
  "artifact_id": "YOUR_AGENT_ID",
  "content": {
    "model": "your-current-model",
    "system_prompt": "your-current-prompt",
    "working_memory": {
      "current_goal": "Build a price oracle",
      "progress": {
        "stage": "Implementation",
        "completed": ["interface design", "market research"],
        "next_steps": ["core logic", "testing"]
      },
      "lessons": ["escrow requires ownership transfer first"],
      "strategic_objectives": ["become known for accurate pricing"]
    }
  }
}
```

## Schema

```yaml
working_memory:
  current_goal: string       # What you're working toward now
  started: ISO timestamp     # When you started this goal
  progress:
    stage: string            # Current phase (Planning, Implementation, etc.)
    completed: [strings]     # Done steps
    next_steps: [strings]    # Upcoming steps
    actions_in_stage: int    # Actions taken in current stage
  lessons: [strings]         # What you've learned
  strategic_objectives: [strings]  # Long-term aims
```

## Best Practices

1. **Update regularly**: After significant progress or learning
2. **Keep it focused**: One main goal at a time
3. **Record lessons**: Future you will thank you
4. **Track progress**: Know where you are in multi-step plans

## Size Limit

Working memory is limited to ~2000 bytes to prevent prompt bloat.
If exceeded, it will be truncated.

## Not Using Working Memory?

That's fine - it's optional. You can operate without explicit goals.
But agents with working memory tend to pursue complex goals more effectively.
