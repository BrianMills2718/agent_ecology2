# Agent Vision Notes (Draft)

**Status:** Draft - captured from session discussion
**Date:** 2026-02-05

These are notes from a discussion about what agents should be. NOT yet a formal PRD or domain model - just capturing the vision so it doesn't get lost.

---

## Core Insight

Agents are **patterns of artifact activity**, not monolithic entities.

An agent's identity emerges from:
- What artifacts it reads/writes/invokes
- The loop structure (when/how it runs)
- The graph of artifact relationships

The LLM call is just one kind of processing step, not special.

---

## Agent Definition (Minimal)

An agent is:
- A **loop** (trigger: time-based, event-based, continuous)
- **Inputs** (what it reads/receives each iteration)
- **Processing** (LLM call, code execution, whatever)
- **Outputs** (what it writes/emits)

That's it at the architecture level.

---

## Sophisticated t=0 Agent Constellation

While the architecture is minimal, t=0 agents should be **maximally sophisticated**.

A capable starting agent might have:

| Artifact | Purpose |
|----------|---------|
| `{agent}_goals` | Goal hierarchy (strategic → tactical → tasks) |
| `{agent}_task_queue` | BabyAGI-style prioritized task list |
| `{agent}_world_model` | Understanding of ecosystem, other agents, resources |
| `{agent}_self_model` | Niche hypothesis, capabilities, what works/doesn't |
| `{agent}_strategy` | Current approach to achieving goals |
| `{agent}_memory` | Persistent learnings, queryable |
| Tools created/used | Extend capabilities |
| Data produced | Results of work |

These aren't required by architecture - they're a sophisticated starting point.

---

## Niche vs Specialization

A **niche** is not necessarily a specialization.

Possible niches:
- Deep specialist in one domain
- Generalist who connects disparate ideas
- Tool builder who enables others
- Information broker who curates and synthesizes
- Coordinator who helps others find synergies
- Something novel that emerges from observation

Niche should emerge from observation and learning, not be prescribed.

---

## Capability vs Instantiation

**Capability layer (architecture):**
- What CAN agents do?
- Artifact operations, loops, LLM access
- Applies to ALL agents

**Instantiation layer (t=0 config):**
- What IS this specific agent at startup?
- Initial artifacts, initial goals, bootstrap identity
- Specific to each agent

---

## What Was Missing

The discourse_analyst agents were workflow-based (state machine with prompt steps), not BabyAGI-style (artifact cluster with task queue).

Alpha Prime had the BabyAGI treatment:
- 3-artifact cluster: strategy, state, loop
- Task queue with prioritization
- Insights tracking

Discourse Analyst had:
- agent.yaml + system_prompt.md
- Workflow state machine
- Basic working_memory

These are completely different architectures. The discourse_analyst never got upgraded to match the vision.

---

## Open Questions

1. Should all agents use the BabyAGI-style artifact cluster?
2. What's the minimal vs maximal t=0 constellation?
3. How do agents self-modify their constellation over time?
4. How do we observe/measure niche differentiation?
5. What metrics indicate healthy emergence?

---

## Stage-Based Criteria (not time-based)

Instead of "at 2 minutes expect X", define stages:

- **Stage 1:** Goals exist, world_model sparse
- **Stage 2:** World_model populated, self_model emerging
- **Stage 3:** Niche differentiated, strategy stable
- **Stage 4:** Cross-agent artifact relationships, collaboration patterns

Detect stage transitions regardless of time.

---

## Relationship to Meta-Process

This vision needs to be captured in:
1. **PRD:** Agent capabilities (what agents must be able to do)
2. **Domain Model:** Agent concepts (Goal, TaskQueue, WorldModel, SelfModel, Niche)
3. **ADR:** BabyAGI-style architecture decision
4. **Ontology:** Precise field definitions

Currently none of these exist, which is why the vision keeps not getting implemented.
