# Plan #212: Memory and Context Quality for Agent Learning

**Status:** Planned
**Priority:** High
**Complexity:** Medium
**Blocks:** Effective agent learning and strategic behavior

## Problem

Analysis of a simulation run revealed that agents have all the infrastructure for learning but it's not working effectively:

### Evidence from Simulation

1. **Mem0 stores garbage** - "Your Memories" section shows 7 identical action echoes:
   ```
   - I performed invoke_artifact: genesis_escrow.list_active
   - I performed invoke_artifact: genesis_escrow.list_active
   (repeated 7 times)
   ```
   This is not useful memory - it's just echoing recent actions.

2. **Agent ignores loop warnings** - Pattern detection shows "15x same action" but agent continues anyway.

3. **Stuck on completed subgoal** - Agent achieved "List for sale" but keeps checking escrow 15 times instead of moving on.

4. **No strategic replanning** - Agent has no idea what to do after achieving a subgoal.

### Root Cause

**Memory stores WHAT happened, not WHAT IT MEANS.**

The research patterns (ExpeL, Reflexion, VOYAGER) emphasize storing **synthesized insights**, not raw action logs.

## Solution

### Phase 1: Memory Content Quality

**Problem:** Mem0 stores raw actions like "I performed invoke_artifact..."

**Fix:** Store synthesized insights instead.

**File:** `src/agents/memory.py`

Change what gets stored after actions:

```python
# Current (bad):
memory_content = f"I performed {action_type}: {json.dumps(intent)}"

# New (good):
def synthesize_memory(action_type: str, intent: dict, result: dict) -> str | None:
    """Synthesize meaningful memory from action outcome."""

    # Don't store routine checks
    if action_type == "invoke_artifact" and intent.get("method") == "list_active":
        return None  # Skip - this is routine, not memorable

    # Store failures with lessons
    if not result.get("success"):
        error = result.get("error", "unknown")
        return f"LESSON: {action_type} on {intent.get('artifact_id')} failed: {error}"

    # Store significant successes
    if action_type == "write_artifact":
        return f"CREATED: {intent.get('artifact_id')} - {intent.get('content', '')[:100]}"

    if action_type == "invoke_artifact" and intent.get("method") == "purchase":
        return f"PURCHASED: {intent.get('artifact_id')}"

    # Skip routine successes
    return None
```

### Phase 2: Stronger Loop Breaking

**Problem:** Agent sees "15x same action" warning but ignores it.

**Fix:** After N identical actions, inject STRONGER intervention into prompt.

**File:** `src/agents/agent.py` (in `build_prompt` or workflow step)

```python
def _get_loop_intervention(self, action_history: list[str]) -> str | None:
    """Detect loops and return intervention text."""
    if len(action_history) < 5:
        return None

    # Check last 5 actions
    last_5 = action_history[-5:]
    if len(set(last_5)) == 1:  # All identical
        return """
## STUCK IN LOOP - MANDATORY CHANGE

You have performed the SAME ACTION 5+ times in a row.
This is NOT productive. You MUST do something DIFFERENT.

Options:
1. If waiting for something - do something else while waiting
2. If checking status - stop checking and take action
3. If stuck - update your subgoal in working_memory

Your next action MUST be different from your last 5 actions.
"""
    return None
```

### Phase 3: Subgoal Completion Detection

**Problem:** Agent achieved subgoal but doesn't recognize it.

**Fix:** Add subgoal completion check to prompt construction.

**File:** `src/agents/agent.py`

```python
def _check_subgoal_completion(self, working_memory: dict, last_result: dict) -> str | None:
    """Check if current subgoal appears completed."""
    subgoal = working_memory.get("current_subgoal", "")

    # Heuristics for completion
    if "list" in subgoal.lower() and "for sale" in subgoal.lower():
        # Check if listing succeeded
        if last_result.get("success") and "listed" in str(last_result).lower():
            return """
## SUBGOAL COMPLETED

Your subgoal "{subgoal}" appears to be DONE.

You should:
1. Update working_memory with a NEW subgoal
2. Move on to something productive
3. Don't wait passively - build something else or submit to mint
"""
    return None
```

### Phase 4: Strategic Fallback Suggestions

**Problem:** Agent doesn't know what to do when "waiting".

**Fix:** Add strategic suggestions when agent appears idle.

**File:** `src/agents/agent.py` (add to prompt)

```python
def _get_strategic_suggestions(self, context: dict) -> str:
    """Suggest productive actions when agent seems stuck."""
    suggestions = []

    # Check if agent has artifacts not submitted to mint
    my_artifacts = context.get("my_artifacts", [])
    mint_submissions = context.get("mint_submissions", [])
    submitted_ids = {s["artifact_id"] for s in mint_submissions}
    unsubmitted = [a for a in my_artifacts if a not in submitted_ids]

    if unsubmitted:
        suggestions.append(f"Submit to mint: You have {len(unsubmitted)} artifacts not yet submitted: {unsubmitted[:3]}")

    # Check if agent has low revenue
    revenue = context.get("revenue_earned", 0)
    if revenue <= 0:
        suggestions.append("Revenue is negative - focus on creating value others will pay for")

    # Check if agent hasn't built anything recently
    artifacts_completed = context.get("artifacts_completed", 0)
    if artifacts_completed < 3:
        suggestions.append("Build more artifacts - you've only created {artifacts_completed}")

    if suggestions:
        return "## Strategic Suggestions\n" + "\n".join(f"- {s}" for s in suggestions)
    return ""
```

## Files Modified

| File | Change |
|------|--------|
| `src/agents/memory.py` | Add `synthesize_memory()`, filter what gets stored |
| `src/agents/agent.py` | Add loop intervention, subgoal completion, strategic suggestions |
| `config/schema.yaml` | Add config for loop_threshold, memory_synthesis |

## Testing

1. Run simulation, verify Mem0 stores insights not raw actions
2. Verify loop intervention triggers after 5 identical actions
3. Verify agent moves on after completing subgoal
4. Verify strategic suggestions appear when agent is stuck

## Acceptance Criteria

- [ ] "Your Memories" section shows lessons/insights, not action echoes
- [ ] Agent breaks out of loops after 5 identical actions
- [ ] Agent recognizes subgoal completion and sets new subgoal
- [ ] Strategic suggestions help stuck agents find productive actions
- [ ] Simulation shows improved behavior (agents don't repeat same action 15x)

## Success Metrics

| Metric | Before | Target |
|--------|--------|--------|
| Max consecutive identical actions | 15+ | ≤5 |
| Memory entries that are insights | ~0% | >80% |
| Subgoal updates per agent | ~1 | 3+ |
| Revenue per agent | -5 | >0 |

## Related Research

From `docs/research/agent_architecture_research_notes.md`:

- **ExpeL**: "Learning from experience WITHOUT parameter updates... extracts knowledge using natural language"
- **Reflexion**: "Self-improvement through linguistic feedback... stores self-critiques in episodic memory"
- **Memory Synthesis**: "Task diaries → periodic synthesis → prompt improvements"

These patterns all emphasize **storing insights, not raw data**.

## Risk

- Memory filtering might accidentally skip important events
- Loop intervention might be too aggressive
- Subgoal detection heuristics might misfire

## Mitigation

- Start with conservative filtering (only skip obvious noise)
- Make loop threshold configurable (default 5)
- Log when interventions trigger for debugging
