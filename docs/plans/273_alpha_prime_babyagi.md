# Plan #273: Alpha Prime BabyAGI Upgrade

**Status:** Complete
**Priority:** High
**Theme:** Agent Cognition
**Created:** 2026-02-03

---

## Problem Statement

Alpha Prime (our V4 artifact-based agent) is too simple:
- One decision per iteration with no planning horizon
- No task queue or prioritization
- No decomposition of objectives into sub-tasks
- Just "think → act → repeat" without structured task management

Meanwhile, BabyAGI demonstrated that autonomous agents need:
1. **Task Queue** - Persistent list of things to do
2. **Task Creation** - Generate new tasks from results
3. **Task Prioritization** - Order tasks by importance
4. **Result Storage** - Remember what worked for context

---

## Solution: BabyAGI-Style Task Loop

Upgrade Alpha Prime to use a structured task management loop:

```
┌─────────────────────────────────────────────────────────┐
│                 Alpha Prime 2.0 Loop                     │
├─────────────────────────────────────────────────────────┤
│  1. POP: Get highest-priority task from queue           │
│  2. EXECUTE: Perform the task (may involve LLM)         │
│  3. STORE: Save result to completed_tasks               │
│  4. CREATE: Generate new tasks based on result          │
│  5. PRIORITIZE: Re-order task queue                     │
│  6. PERSIST: Write updated state                        │
│  7. REPEAT                                              │
└─────────────────────────────────────────────────────────┘
```

### New State Structure

```json
{
  "iteration": 42,
  "objective": "Earn 500 scrip by completing mint tasks",
  "task_queue": [
    {"id": 2, "description": "Build adder artifact", "priority": 8},
    {"id": 3, "description": "Submit adder to add_numbers", "priority": 7}
  ],
  "completed_tasks": [
    {"id": 1, "description": "Query mint tasks", "result": "Found: add_numbers, multiply_numbers, string_length"}
  ],
  "next_task_id": 4,
  "insights": {
    "closed_tasks": ["add_numbers"],
    "successful_submissions": ["multiply_numbers"],
    "learned": []
  }
}
```

### Prompts

**Task Execution Prompt:**
```
You are Alpha Prime. Your objective: {objective}

Current task: {current_task}

Recent results:
{completed_tasks[-3:]}

Insights:
- Closed tasks: {insights.closed_tasks}
- Successful: {insights.successful_submissions}

Execute this task. Return a JSON action:
{"action_type": "...", ...}
```

**Task Creation Prompt:**
```
Based on this result:
Task: {completed_task}
Result: {result}

And objective: {objective}

What 1-3 new tasks should be added? Return JSON:
{"new_tasks": [{"description": "...", "priority": 1-10}, ...]}

Priority guide: 10=urgent, 5=normal, 1=low
Don't create tasks for closed/completed items: {insights}
```

**Task Prioritization Prompt:**
```
Current task queue:
{task_queue}

Objective: {objective}
Insights: {insights}

Re-order by priority (highest first). Return JSON:
{"prioritized": [task_ids in order]}
```

---

## Implementation

### Files to Modify

| File | Change |
|------|--------|
| `src/world/world.py` | Update `_bootstrap_alpha_prime()` with new state structure and loop logic |
| `docs/plans/273_alpha_prime_babyagi.md` | This plan |

### Phase 1: State Structure

Update `alpha_prime_state` initial structure with task queue.

### Phase 2: Loop Logic

Rewrite `alpha_prime_loop` code to:
1. Pop task from queue
2. Execute task (call LLM for action)
3. Store result
4. Create new tasks (call LLM)
5. Prioritize (simple sort, optional LLM)
6. Persist state

### Phase 3: Prompts

Create focused prompts for each step that reference the state.

---

## Design Decisions

### Task Creation: LLM or Heuristic?

**Decision: LLM-based** - Let the model figure out what tasks follow from results. More flexible than hard-coded rules.

### Prioritization: LLM or Simple Sort?

**Decision: Simple priority number** - Tasks have priority 1-10. Sort by priority. LLM prioritization adds latency and cost for minimal benefit.

### How Many LLM Calls Per Iteration?

**Decision: 2 calls max**
1. Execute task (required)
2. Create new tasks (required)

Prioritization is just sorting by priority field - no LLM needed.

### Memory: Vector DB or JSON?

**Decision: JSON in state artifact** - Keep it simple. Vector search can be added later via `genesis_memory` artifact if needed.

---

## Success Criteria

1. Alpha Prime maintains a task queue across iterations
2. Completing a task generates relevant follow-up tasks
3. Agent progresses through: query tasks → build artifact → submit → earn scrip
4. Agent doesn't get stuck retrying closed tasks (uses insights)
5. 5-minute simulation shows measurable progress (scrip earned > 50)

---

## Test Plan

1. Unit test: State structure parses correctly
2. Unit test: Task queue operations (pop, add, sort)
3. Integration: Run 2-minute simulation, verify task progression
4. Manual: Watch logs to confirm BabyAGI-style behavior

---

## References

- Plan #155: V4 Architecture (deferred - this implements part of it)
- Plan #255: Kernel LLM Gateway (prerequisite, complete)
- Plan #256: Alpha Prime Bootstrap (current implementation)
- [BabyAGI Architecture](https://github.com/yoheinakajima/babyagi)
