# Simulation Learnings

Observations and insights from running agent simulations. Focus on what we learn about emergent behavior, architectural weaknesses, and directions for improvement.

---

## 2026-01-25: Model Comparison (gemini-2.0-flash vs gemini-3-flash-preview)

### Experiment
Ran identical 120-second simulations with 3 agents (alpha_3, beta_3, delta_3) using different models.

### Results

| Metric | gemini-2.0-flash | gemini-3-flash-preview |
|--------|------------------|------------------------|
| Events | 917 | 972 |
| alpha_3 lessons stored | **0** | **35** |
| alpha_3 hit error limit | Yes (7x consecutive) | No |
| Economic activity | Only beta_3 active | All 3 agents active |
| Meta-learning observed | None | Yes ("stop storing generic actions") |

### Key Observation
The `semantic_memory` trait is injected into prompts for all agents. gemini-3-flash-preview follows it; gemini-2.0-flash ignores it.

### Wrong Lesson (Avoided)
Initial instinct: "Force learning behavior through hard-coded rules" - e.g., block retries until lessons stored, require reflection after failures.

**Why this is wrong:**
- Prescribing every failure case doesn't scale
- Doesn't improve innate intelligence/adaptability
- Creates brittle systems dependent on anticipating all scenarios
- Stronger models would just work around architectural issues

### Right Lesson
The architecture needs to create **conditions for emergence**, not script behaviors.

**Directions to explore:**

1. **Metacognitive capabilities** - Agents that think about their own thinking, evaluate their own strategies, notice their own patterns (gemini-3-flash-preview did this spontaneously: "Repeatedly storing generic action descriptions is not helpful")

2. **Self-modification** - Agents that can modify their own cognitive architectures, experiment with different approaches, evolve their workflows

3. **Long-term strategic behavior** - Not just reactive error handling, but genuine planning toward goals that span many actions

4. **Evolutionary pressure** - Selection mechanisms that favor agents with better learning/adaptation capabilities

### Design Principle
**Use weak models to stress-test architecture.** If gemini-2.0-flash can't bootstrap with our architecture, we're relying on model intelligence to paper over weaknesses. A stronger model might "work around" issues, masking problems that prevent genuine emergent collective capability.

The goal is an architecture robust enough that even weak models can bootstrap, because the structure itself facilitates learning - not because we've anticipated and hard-coded every scenario.

---

## 2026-01-25: Simplified Metacognitive Prompt (gemini-2.5-flash)

### Experiment
Simplified the `semantic_memory` trait from verbose instructions to a metacognitive question:

**Before (verbose):**
```
ACTION REQUIRED: If you learned something useful, STORE IT NOW...
WHEN TO STORE (do this!):
- After ANY failure: "LESSON: [action] failed because [reason]"
- After success: "STRATEGY: [approach] worked for [goal]"
...
```

**After (metacognitive):**
```
ASK YOURSELF: What did I just learn that my future self should know?

If the answer is something specific (not generic), store it...
Good: "LESSON: escrow deposit requires setting authorized_writer first"
Bad: "ACTION: I queried the kernel" (too generic, don't store)
```

### Results

| Metric | 2.0-flash (verbose) | 3-flash-preview (verbose) | 2.5-flash (metacognitive) |
|--------|---------------------|---------------------------|---------------------------|
| alpha_3 lessons | 0 | 35 | 2 |
| beta_3 lessons | 13 | 6 | 1 |
| delta_3 lessons | 15 | 9 | 4 |
| Lesson quality | N/A | Mixed (some generic spam) | **High (all specific)** |
| Hit error limit | Yes | No | No |
| Errors (recovered) | 7+ consecutive | 11 | 66/33/41 |

### Sample Lessons (2.5-flash with metacognitive prompt)
- "LESSON: escrow deposit requires setting authorized_writer first"
- "LESSON: Repeatedly writing and bidding on simple_fetch leads to MCP server errors"
- "LESSON: Failed to use query_kernel because I tried to invoke it directly"
- "LESSON: Check existing artifacts before building to avoid duplication"

### Key Finding
**Fewer but higher-quality lessons.** The metacognitive framing ("What did I learn that my future self should know?") filters out generic action logging. Quality over quantity.

### Insight
The metacognitive prompt works because it:
1. Shifts from "follow these instructions" to "reflect on your experience"
2. Provides a quality filter (specific vs generic)
3. Frames learning as self-beneficial ("your future self")

This aligns with the goal of **creating conditions for emergence** rather than prescribing behaviors.

---

## Future Experiments

- [x] ~~Evaluate metacognitive prompt strategies~~ (done: simplified prompt improves quality)
- [ ] Test cognitive architecture variations (different workflow structures)
- [ ] Measure cross-session learning persistence
- [ ] Compare prescriptive vs emergent learning approaches
- [ ] Test metacognitive prompt with weak model (gemini-2.0-flash)
- [ ] Longer simulations to observe learning accumulation
