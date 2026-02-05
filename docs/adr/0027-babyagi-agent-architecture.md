# ADR-0027: BabyAGI-Style Agent Cognitive Architecture

**Status:** Accepted
**Date:** 2026-02-05

## Context

Agents in the ecosystem need sophisticated cognitive capabilities to achieve the thesis goal of emergent collective capability. Current agent implementations vary:

- **Alpha Prime** has BabyAGI-style architecture: task queue, goal tracking, insights, strategy
- **Discourse Analyst** uses workflow-based architecture: state machine with prompt steps
- **v4_solo template** has basic working memory but no structured cognition

This inconsistency means:
1. Some agents can pursue long-term goals, others can't
2. Some agents learn and adapt, others are reactive
3. Vision for "sophisticated agents" keeps not getting implemented because there's no clear architectural spec

The PRD (docs/prd/agents.md) defines required capabilities:
- long-term-planning, adaptation, ecosystem-awareness
- niche-finding, self-modification, collaboration

The domain model (docs/domain_model/agents.yaml) defines the concepts that enable these:
- Goal, TaskQueue, WorldModel, SelfModel, Niche, Memory, Strategy

We need an architectural decision on how agents should implement these concepts.

## Decision

Adopt **BabyAGI-style architecture** as the standard cognitive architecture for agents.

### Core Pattern

Each agent maintains an **artifact constellation** - a set of related artifacts that together constitute its cognitive state:

```
{agent_id}_goals        # Goal hierarchy (strategic → tactical → tasks)
{agent_id}_task_queue   # Prioritized work items (BabyAGI-style)
{agent_id}_world_model  # Understanding of ecosystem
{agent_id}_self_model   # Understanding of self, niche hypothesis
{agent_id}_strategy     # Current approach to achieving goals
{agent_id}_memory       # Persistent learnings (queryable)
```

### Loop Structure

Each iteration:
1. **Read** task queue + relevant context
2. **Select** highest priority task aligned with goals
3. **Execute** task (may involve LLM call, artifact operations, etc.)
4. **Record** outcome in memory, update world/self models
5. **Generate** new tasks if needed, reprioritize queue
6. **Adapt** strategy if pattern of failures detected

### Key Properties

- **Artifacts, not prompt sections**: Cognitive state lives in artifacts, not embedded in prompts
- **Self-modifiable**: Agent can edit its own constellation
- **Observable**: External systems can read agent's goals, world model, etc.
- **Persistent**: State survives across simulation restarts
- **Evolvable**: Agent can add new artifacts to its constellation

### NOT Required

- Specific artifact schemas (agent decides internal structure)
- Particular LLM prompting patterns
- Fixed iteration timing
- Pre-defined goal hierarchies

The architecture specifies WHAT artifacts exist and HOW they relate, not their internal format.

## Consequences

### Positive

- **Consistent capability baseline**: All agents can pursue long-term goals
- **Observable cognition**: Can see what agent is thinking/planning
- **Self-modification path**: Clear mechanism for agents to evolve
- **Matches existing success**: Alpha Prime already works this way
- **Testable**: Can verify agents have required artifacts

### Negative

- **Bootstrap complexity**: Agents need initial artifact constellation at t=0
- **Storage overhead**: More artifacts per agent
- **Migration work**: Existing agents (discourse_analyst) need upgrade
- **Possible over-prescription**: Might constrain emergent architectures

### Neutral

- Workflow system still useful for specific multi-step operations within an iteration
- Memory artifact (ADR-0009) becomes one part of larger constellation
- Doesn't change kernel/artifact system - just patterns of usage

## Alternatives Considered

**1. Workflow-based (current discourse_analyst)**
- State machine with defined transitions
- Rejected: Too rigid, doesn't support long-term planning or adaptation

**2. Pure prompt-based**
- All cognition in system prompt, no external state
- Rejected: No persistence, no observability, hits context limits

**3. Minimal (has_standing + has_loop only)**
- Let each agent evolve its own architecture
- Rejected: Too slow for initial experiments, need baseline capability

**4. Prescriptive schemas**
- Define exact JSON structure for each artifact
- Rejected: Over-constrains emergence, agents should choose internal formats

## Related

- Plan #294: Document hierarchy and context injection meta-process
- PRD: docs/prd/agents.md
- Domain Model: docs/domain_model/agents.yaml
- ADR-0009: Memory as artifact
- ADR-0026: Sophisticated initial agents
- Pattern: BabyAGI (external reference)
