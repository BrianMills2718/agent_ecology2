# Emergence Research Questions

**Source:** PRIORITIZED_ACTIONS_2026_01_16.md Tier 5
**Status:** Open questions requiring experimentation

---

## Core Questions

These questions require running real simulations and collecting data, not design decisions.

| # | Question | Why It Matters |
|---|----------|----------------|
| 1 | What emergent behaviors have actually been observed? | Core hypothesis validation |
| 2 | Have long simulations with real LLM been run? | No logs exist showing this |
| 3 | At what scale does interesting behavior appear? (2 vs 5 vs 20 agents) | Experiment design |
| 4 | How do you distinguish emergence from prompt-following? | Methodological clarity |
| 5 | Is the resource scarcity sufficient? | Current limits may be too generous |
| 6 | What's typical real-world token consumption? | Tests use mocks |
| 7 | Do agents actually use debt/escrow effectively? | Feature validation |

---

## Suggested Approach

1. **Run real simulation** - 30+ minutes with real LLM, multiple agents
2. **Preserve logs** - Don't overwrite run.jsonl
3. **Analyze patterns** - Look for coordination, trading, resource management
4. **Document observations** - Add to `docs/simulation_learnings/`

---

## Related

- `docs/simulation_learnings/` - Where observations should go
- `docs/research/agent_architecture_synthesis.md` - Recommendations for agent improvements
