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

## Future Experiments

- [ ] Test cognitive architecture variations (different workflow structures)
- [ ] Measure cross-session learning persistence
- [ ] Compare prescriptive vs emergent learning approaches
- [ ] Evaluate metacognitive prompt strategies
