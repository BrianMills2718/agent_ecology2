# Plan #157: Agent Goal Clarity and Time Awareness

**Status:** ✅ Complete
**Priority:** High
**Created:** 2026-01-22
**Context:** Plan #156 showed that action history alone doesn't prevent loops. Agents recognize they're looping but continue anyway. Root cause: unclear goals and missing time/opportunity cost visibility.

---

## Problem Statement

Agents loop not because they can't detect loops, but because they lack:
1. **Clear operationalized goals** - "maximize scrip" is too vague
2. **Time scarcity awareness** - no visibility into simulation duration or progress
3. **Opportunity cost reasoning** - can't evaluate "is this worth more attempts?"
4. **LLM-informed state transitions** - state machine uses hardcoded thresholds, not reasoning

Evidence from Plan #156 testing:
- Agent recognized loop: "I have been repeatedly writing...indicating a loop"
- Agent continued anyway: "I will now focus on updating the interface definition"
- 20 writes to same artifact despite seeing the pattern

---

## Design Principles

1. **Goals over rules** - Don't add "don't loop" rules; make the goal clear enough that not-looping is inferrable
2. **Information over constraints** - Give agents data to reason with, not hardcoded limits
3. **LLM judgment for transitions** - State changes based on reasoning, not `balance >= 20`

---

## Solution

### 1. Time Context in Prompts

Add to agent context:
```yaml
Time:
  current_tick: 45
  total_ticks: 100  # or estimated from duration
  time_elapsed: "1m 30s"
  time_remaining: "2m 30s"
  progress: "45%"
```

Implementation: Update `_build_workflow_context()` to include tick/duration info from simulation.

### 2. Opportunity Cost Metrics

Add to agent context:
```yaml
Performance:
  actions_taken: 23
  successful_actions: 8
  revenue_earned: 0
  artifacts_completed: 0
  time_per_artifact: "N/A (none completed)"
```

Implementation: Track in Agent class, expose in context.

### 3. Clear Goal Statement

Replace vague "maximize scrip" with operationalized goal:
```
GOAL: Maximize your scrip balance by simulation end.

You have {time_remaining} left. Current stats:
- Revenue so far: {revenue_earned} scrip
- Working artifacts: {artifacts_completed}
- Current balance: {balance}

Every turn spent not earning revenue is opportunity cost.
```

### 4. LLM-Informed State Transitions

Replace hardcoded transitions:
```python
# Current (bad)
has_idea = balance >= 20  # Always true

# Proposed (good) - LLM evaluates
transition_prompt = """
You just completed: {last_action}
Result: {result}

Should you:
A) Continue with current artifact (you're making progress)
B) Abandon and try something different (you're stuck)
C) Ship what you have and move on (good enough)

Consider: {time_remaining} left, {revenue_earned} earned so far.
"""
```

This makes transitions a reasoning step, not a threshold check.

---

## Implementation Steps

### Phase 1: Time Context ✅
- [x] Add `tick`, `total_ticks`, `duration_seconds` to simulation runner
- [x] Pass time context to agents via `_build_workflow_context()`
- [x] Format as human-readable in prompts

### Phase 2: Opportunity Cost Metrics ✅
- [x] Add `revenue_earned`, `artifacts_completed` tracking to Agent
- [x] Add `actions_taken`, `successful_actions` counters
- [x] Include in prompt context

### Phase 3: Goal Reframing ✅
- [x] Update agent prompts with clear time-bound goal
- [x] Remove vague "build valuable artifacts" language
- [x] Add performance summary to each prompt

### Phase 4: LLM Transition Evaluation ✅
- [x] Design transition evaluation prompt
- [x] Add `evaluate_transition()` method to workflow engine
- [x] Replace hardcoded conditions with LLM judgments
- [x] Add "abandon" as explicit transition option

---

## Files to Modify

### Phase 1-3 (simpler)
- `src/agents/agent.py` - Add time context and metrics to prompts
- `src/simulation/runner.py` - Pass duration/tick info to agents
- `src/agents/*/agent.yaml` - Update goal framing in prompts

### Phase 4 (architectural)
- `src/agents/workflow.py` - LLM-informed transitions
- `src/agents/*/agent.yaml` - Transition prompts

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Max writes to single artifact | 20 | ≤3 |
| Agent recognizes AND acts on loop | No | Yes |
| Artifacts completed per 2min sim | ~1 | ≥3 |
| Agent references time pressure in reasoning | Never | Often |

---

## Risks

1. **LLM transition cost** - Extra LLM call per transition
   - Mitigation: Use smaller model for transitions, or batch with action

2. **Over-optimization for speed** - Agent ships broken artifacts
   - Mitigation: Include "working artifacts" metric, not just count

3. **Complexity** - Phase 4 is significant architectural change
   - Mitigation: Phases 1-3 may be sufficient; validate before Phase 4

---

## Dependencies

- Plan #156 (complete) - Action history infrastructure
- Plan #155 (deferred) - Broader V4 architecture considerations

---

## Open Questions

1. Should time be in ticks or wall-clock seconds?
2. How to handle variable-length simulations?
3. Is Phase 4 (LLM transitions) worth the added LLM cost?
