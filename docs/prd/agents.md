# PRD: Agent Capabilities

---
id: prd/agents
type: prd
domain: agents
status: draft
thesis_refs:
  - THESIS.md#emergence-over-prescription
  - THESIS.md#accept-risk-observe-outcomes
  - THESIS.md#stage-1-individual-agency
  - THESIS.md#stage-2-ecosystem-awareness
  - THESIS.md#stage-3-collective-capability
---

## Overview

Agents are the autonomous entities in our ecosystem. This PRD defines what agents must be **capable** of doing - not how they're implemented, but what behaviors must be possible.

The thesis requires agents that can develop collective capability through emergence. This demands agents that are individually capable of sophisticated behavior.

## Capabilities

### long-term-planning

**Description:** Agents must pursue goals across multiple interactions, not just react to immediate stimuli.

**Why:** Without persistent goals, agents are reactive systems. Emergence requires agents that can work toward objectives over time, adapt strategies, and measure progress. (Thesis: Stage 1 - Individual Agency)

**Acceptance Criteria:**
- Agent maintains goal hierarchy (strategic → tactical → tasks)
- Agent can track progress toward goals across simulation cycles
- Agent can reprioritize goals based on outcomes
- Agent can create sub-goals to achieve parent goals

### adaptation

**Description:** Agents must learn from their environment and modify their behavior based on outcomes.

**Why:** Static behavior can't produce emergence. Agents need to learn what works, what doesn't, and adapt accordingly. (Thesis: Stage 1 - Individual Agency)

**Acceptance Criteria:**
- Agent records outcomes of actions (success/failure, effects)
- Agent modifies approach based on past outcomes
- Agent can identify patterns in what works/doesn't
- Agent can update its own prompts/strategy based on learnings

### ecosystem-awareness

**Description:** Agents must develop understanding of other agents and the broader ecosystem.

**Why:** Collective capability requires agents that understand they're part of a larger system. Agents need to know what resources exist, what other agents do, and how they might interact. (Thesis: Stage 2 - Ecosystem Awareness)

**Acceptance Criteria:**
- Agent maintains model of ecosystem (resources, artifacts, other agents)
- Agent can query and update its ecosystem understanding
- Agent can identify capabilities of other agents
- Agent can reason about ecosystem dynamics

### niche-finding

**Description:** Agents must discover and pursue unique value propositions within the ecosystem.

**Why:** Undifferentiated agents can't produce collective capability - they'll just compete for the same resources doing the same things. Differentiation is essential. (Thesis: Stage 2 - Ecosystem Awareness)

**Acceptance Criteria:**
- Agent develops hypothesis about its potential niche
- Agent tests and refines niche hypothesis based on outcomes
- Agent differentiates from other agents over time
- Niche is NOT necessarily specialization (could be generalist, connector, meta)

### self-modification

**Description:** Agents must be able to modify their own configuration, prompts, memory, and behavior.

**Why:** Adaptation requires self-modification. Agents that can only change their data but not their behavior are limited. True adaptation means agents can change how they think, not just what they know. (Thesis: Emergence Over Prescription)

**Acceptance Criteria:**
- Agent can modify its own system prompt
- Agent can modify its configuration (strategy, goals, thresholds)
- Agent can create/modify its own artifacts
- Agent can evolve its cognitive architecture over time

### collaboration

**Description:** Agents must be able to work with other agents to achieve goals neither could achieve alone.

**Why:** Collective capability is the thesis goal. This requires collaboration - agents combining capabilities, sharing resources, coordinating actions. (Thesis: Stage 3 - Collective Capability)

**Acceptance Criteria:**
- Agent can identify collaboration opportunities
- Agent can negotiate with other agents (contracts, exchanges)
- Agent can participate in multi-agent workflows
- Agent produces artifacts that enable other agents

## Non-Goals

- **Prescriptive roles** - We do NOT define "the analyst agent" or "the builder agent". Roles emerge from behavior.
- **Hardcoded collaboration patterns** - We do NOT prescribe how agents should collaborate. Patterns emerge.
- **Guaranteed outcomes** - We do NOT ensure agents will be "good" or "productive". We observe what emerges.
- **Safety constraints on emergence** - We do NOT prevent agents from doing unexpected things (within sandbox limits).

## Open Questions

1. **What's the minimal t=0 agent constellation?** What artifacts must exist at startup for an agent to have these capabilities?

2. **How do we measure niche differentiation?** What metrics indicate healthy vs unhealthy differentiation?

3. **How do we observe emergence without prescribing it?** How do we know if collective capability has emerged vs just parallel individual capability?

4. **What's the right balance of structure vs freedom?** Too much structure prevents emergence; too little prevents coherent behavior.

## References

- Thesis: `docs/THESIS.md`
- Domain Model: `docs/domain_model/agents.yaml`
- Draft notes: `docs/drafts/agent_vision_notes.md`
