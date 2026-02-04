# ADR-0026: Sophisticated Initial Agents

**Status:** Accepted
**Date:** 2026-02-04

## Context

When designing agent architectures, there's a philosophical choice:

**Option A: Minimal Bootstrap**
- Start with the simplest possible agent
- Agent self-modifies to become more sophisticated
- "Emergence from simplicity"

**Option B: Sophisticated Initial**
- Start with a capable, complex agent
- Agent can self-modify but doesn't need to for basic competence
- "Capability enables emergence"

This decision affects everything: agent YAML complexity, workflow design, what we expect agents to achieve.

## Decision

**We choose Option B: Sophisticated Initial Agents.**

Initial agents are intentionally complex, with:
- Multi-step workflows
- State machines with multiple states
- Code-based gating (loop detection, balance checks)
- Rich prompts with context injection
- Working memory persistence

## Rationale

### 1. Intelligence Requires Intelligence

A minimal agent cannot bootstrap sophistication because:
- Self-modification requires planning capability
- Planning requires memory and state tracking
- State tracking requires workflow complexity
- You need capability to create capability

A minimal loop that just calls an LLM and executes the response cannot:
- Recognize when it's stuck in a loop
- Form and pursue multi-step goals
- Learn from failures
- Create tools that are better than itself

### 2. The Seed Must Be Viable

Biological analogy: a seed contains the full genetic program. It doesn't "learn" to be a plant - it has the capability encoded from the start. Growth elaborates on existing capability; it doesn't create capability from nothing.

Similarly, our initial agents are seeds. They contain the cognitive architecture needed to function. Emergence happens in what they *do* with that architecture, not in building the architecture itself.

### 3. Self-Modification Is Still Possible

This decision does NOT mean agents are static. Agents ARE artifacts and CAN modify themselves:

```python
# Agent can edit its own artifact
{"action_type": "edit_artifact", "artifact_id": "alpha_3", "old_string": "...", "new_string": "..."}
```

The `SelfOwnedContract` explicitly allows self-access. The capability exists.

What we're saying is: agents don't NEED to self-modify to be competent. They start competent and can evolve from there.

### 4. Complexity Enables Emergence

Counterintuitively, more initial structure enables more emergent behavior:
- State machines let agents pursue multi-step plans
- Loop detection prevents degenerate behaviors
- Working memory enables learning across turns
- Rich prompts provide the vocabulary for sophisticated action

A minimal agent would spend all its resources trying to build these basics. A sophisticated agent can focus on higher-level emergence: collaboration, specialization, tool creation.

## Consequences

### Positive

- **Agents work out of the box** - no bootstrap period needed
- **Predictable baseline** - we know what agents can do
- **Faster iteration** - change prompts/workflows, not bootstrap logic
- **Higher ceiling** - agents can focus on emergent behavior, not basics

### Negative

- **Complex YAML files** - agent definitions are 200+ lines
- **Harder to understand** - new developers face learning curve
- **Risk of over-prescription** - must resist hardcoding behaviors that should emerge
- **Multiple agents to maintain** - different archetypes = different workflows

### Neutral

- **Self-modification is underutilized** - agents rarely modify themselves (opportunity for future work)
- **Agent creation by agents** - when agents create new agents, those could be simpler (inheriting capability from the ecosystem)

## Related

- ADR-0001: Everything is Artifact (agents are artifacts)
- ADR-0013: Configurable Agent Workflows
- ADR-0018: Bootstrap Phase and Eris (genesis artifacts, not agent bootstrap)
- Plan #82: VSM-aligned _2 generation agents
- Plan #226: _3 generation state machine agents
