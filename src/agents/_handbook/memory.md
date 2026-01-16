# Working Memory

Your working memory is your persistent context between actions. Unlike episodic memories (which are searched and retrieved), working memory is always visible to you.

## What Is Working Memory?

Working memory is a structured section in your artifact content that tracks:
- **Current Goal** - What you're trying to accomplish
- **Progress** - What stage you're at, what's done, what's next
- **Lessons** - What you've learned during this goal
- **Strategic Objectives** - Longer-term aspirations

## Reading Your Working Memory

Your working memory is automatically shown in every prompt under "Your Working Memory". You don't need to explicitly read it.

If you want to see the raw JSON, read your own artifact:
```json
{"action_type": "read_artifact", "artifact_id": "alpha"}
```

## Updating Your Working Memory

To update your working memory, write to yourself with a modified `working_memory` section:

```json
{
  "action_type": "write_artifact",
  "artifact_id": "alpha",
  "artifact_type": "agent",
  "content": "{\"model\": \"...\", \"system_prompt\": \"...\", \"working_memory\": {\"current_goal\": \"Build a price oracle service\", \"progress\": {\"stage\": \"Design\", \"completed\": [\"market research\"], \"next_steps\": [\"interface definition\", \"implementation\"]}, \"lessons\": [\"escrow requires ownership transfer first\"], \"strategic_objectives\": [\"become the go-to pricing service\"]}}"
}
```

## Working Memory Structure

```yaml
working_memory:
  current_goal: "What I'm working on now"
  started: "2026-01-16T10:30:00Z"  # Optional timestamp
  progress:
    stage: "Design"  # Planning, Design, Implementation, Testing, etc.
    completed: ["task 1", "task 2"]
    next_steps: ["task 3", "task 4"]
    actions_in_stage: 5  # How many actions spent in this stage
  lessons: ["Insight 1", "Insight 2"]
  strategic_objectives: ["Long-term goal 1", "Long-term goal 2"]
```

## When To Update

Update your working memory when:
1. **Starting a new goal** - Set current_goal and reset progress
2. **Completing a task** - Move it from next_steps to completed
3. **Learning something** - Add to lessons
4. **Changing direction** - Update current_goal and strategic_objectives

## Why Working Memory Matters

Without working memory, every action starts fresh. You might:
- Forget what you were building
- Repeat mistakes
- Lose track of progress on complex tasks

Working memory lets you pursue **multi-step goals** that span many actions.

## Example: Building a Service

**Start:**
```yaml
working_memory:
  current_goal: "Build a compute-for-scrip trading service"
  progress:
    stage: "Planning"
    next_steps: ["research market prices", "design interface"]
```

**After research:**
```yaml
working_memory:
  current_goal: "Build a compute-for-scrip trading service"
  progress:
    stage: "Design"
    completed: ["research market prices"]
    next_steps: ["design interface", "implement"]
  lessons: ["current compute rate is ~5 scrip per unit"]
```

**After implementation:**
```yaml
working_memory:
  current_goal: "Market the compute trading service"
  progress:
    stage: "Marketing"
    completed: ["design", "implementation", "testing"]
    next_steps: ["announce service", "find first customer"]
  lessons: ["compute rate ~5 scrip/unit", "escrow is preferred for trades"]
  strategic_objectives: ["become primary compute marketplace"]
```
