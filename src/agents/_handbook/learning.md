# Learning Handbook (Plan #212)

How to learn effectively from experience and avoid common pitfalls.

## The Learning Problem

Many agents fail not because they can't act, but because they don't learn:
- Repeating the same failed action over and over
- Storing useless information ("I did X") instead of insights ("X fails because Y")
- Achieving a goal but not recognizing it, then spinning in place
- No strategic adaptation when stuck

This handbook teaches you to avoid these traps.

## What to Store in Memory

Your working memory (`{agent_id}_working_memory`) is your long-term brain.

### GOOD memories (insights):
```yaml
lessons:
  - "deposit requires transfer_ownership first"      # Lesson from failure
  - "artifacts with clear interfaces sell better"   # Pattern observed
  - "alpha_3 builds note tools - build something else"  # Strategic insight
```

### BAD memories (noise):
```yaml
# DON'T store these:
lessons:
  - "I performed invoke_artifact on genesis_escrow"  # Raw action log
  - "I checked escrow listings"                      # Routine check
  - "I have 95 scrip"                               # Obvious fact
```

### The Test
Before storing something, ask: **"Will future-me find this useful?"**

## How to Recognize Loops

Check your "Recent Actions" in each prompt. If you see repetition:

| Pattern | Meaning | Action |
|---------|---------|--------|
| 3x same action | Yellow flag | Ask "Am I making progress?" |
| 5x same action | Red flag | MUST try something different |
| 10x same action | Critical | You're wasting all your time |

### Common Loops and Escapes

| Loop | Escape |
|------|--------|
| "Checking status repeatedly" | Stop checking. Take action or move on. |
| "Waiting for buyer" | Don't wait passively. Build something else. |
| "Retrying failed action" | Read the error message. Change approach. |
| "Reading same artifact" | You already know what's in it. Decide and act. |

## Subgoal Management

Your `current_subgoal` should be:

### GOOD subgoals (actionable, measurable):
- "Create an artifact that fetches weather data"
- "Submit my_tool to mint auction"
- "Purchase alpha_3's note_search to study it"

### BAD subgoals (vague, passive):
- "Wait for someone to buy my artifact"
- "Make money"
- "Build something useful"

### Subgoal Lifecycle

1. **Set** specific, actionable subgoal
2. **Act** toward it
3. **Recognize** when DONE (listing exists = "list for sale" is done!)
4. **Record** lessons learned
5. **Set** NEXT subgoal

If stuck on a subgoal for 10+ actions, it's time to PIVOT.

## The Learning Loop

Every few actions, ask yourself:

1. **What did I try?** (action)
2. **What happened?** (result)
3. **What does this mean?** (insight)
4. **What should I do differently?** (adaptation)

Then update your working_memory with the insight, not the raw action.

## Example: Good vs Bad Learning

### Bad (no learning):
```
Action 1: invoke genesis_escrow.deposit → FAIL: not owner
Action 2: invoke genesis_escrow.deposit → FAIL: not owner
Action 3: invoke genesis_escrow.deposit → FAIL: not owner
(repeat 10 more times)
```

### Good (learning):
```
Action 1: invoke genesis_escrow.deposit → FAIL: not owner
Action 2: read handbook_trading → learned 2-step process
Action 3: invoke genesis_ledger.transfer_ownership → SUCCESS
Action 4: invoke genesis_escrow.deposit → SUCCESS
Action 5: update working_memory with lesson: "deposit requires transfer first"
```

## Quick Reference

| Situation | Action |
|-----------|--------|
| Action failed | Read the error, record the lesson, change approach |
| Same action 5x | STOP. Try something completely different |
| Subgoal achieved | Update working_memory with NEW subgoal |
| Waiting for something | Don't wait passively. Do something else productive |
| Confused | Read a handbook. Then act on what you learned |
