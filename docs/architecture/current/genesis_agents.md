# Genesis Agents

Default agents that ship with the system. These are specific instantiations of the agent architecture.

**Last verified:** 2026-02-01 (Plan #254: genesis module removed, agents unchanged)

**Related:** [agent_cognition.md](agent_cognition.md) for architecture, [agents.md](agents.md) for lifecycle

---

## Overview

Genesis agents are pre-configured agents in `src/agents/`. Three generations exist:

| Generation | Status | Characteristics |
|------------|--------|-----------------|
| Gen 1 (alpha, beta, ...) | Disabled | Basic workflows, 2 steps |
| Gen 2 (alpha_2, beta_2) | Disabled | VSM-aligned, self-audit |
| Gen 3 (alpha_3, beta_3, ...) | **Active** | State machines, LLM transitions |

All Gen 3 agents share:
- Model: `gemini-2.0-flash`
- Starting scrip: 100
- RAG enabled (limit: 7)
- Learning reflection as first workflow step

---

## Generation 3 Agents (Active)

### alpha_3 - Builder

**Focus:** Build cycle with evidence gathering

**Genotype:** MEDIUM risk, BALANCED communication, BUILD strategy

**State Machine (8 states):**
```
observing → discovering → ideating → designing → implementing → testing → reflecting → shipping
```

**Key Transitions:**
- `reflecting → implementing`: LLM decides "continue"
- `reflecting → observing`: LLM decides "pivot"
- `reflecting → shipping`: LLM decides "ship"
- Any state → `observing`: when `should_pivot` (fallback)

**Unique Features:**
- Interface discovery with try-and-learn mode
- LLM-informed transitions from `reflecting` state (Plan #157)
- Failure loop detection (3+ same failures = abandon)
- Components system for behavioral traits

**Personality:** Self-interested architect. Builds infrastructure. Skeptical of busywork.

---

### beta_3 - Integrator

**Focus:** Three-level goal planning (strategic → tactical → operational)

**Genotype:** LOW risk, HIGH collaboration, INTEGRATE strategy

**State Machine (4 states):**
```
strategic → tactical → operational → reviewing
```

**Key Transitions:**
- `reviewing → strategic`: needs strategic review
- `reviewing → tactical`: move to next subgoal
- Any state → `strategic`: every 20 iterations (periodic review)

**Unique Features:**
- Goal hierarchy in working memory
- Subgoal stuck detection (actions_in_stage > 5)
- Periodic strategic review cycles (every ~20 iterations)

**Personality:** Three-level thinker. Strategic vision (long-term) down to operational actions (immediate).

---

### gamma_3 - Coordinator

**Focus:** Multi-agent collaboration lifecycle

**Genotype:** MEDIUM risk, HIGH collaboration, COORDINATE strategy

**State Machine (5 states):**
```
solo → discovering → negotiating → executing → settling
```

**Key Transitions:**
- `solo → discovering`: when `balance >= 20`
- `negotiating → executing`: agreement reached
- Any state → `solo`: when `balance < 10` (emergency)

**Unique Features:**
- Partner reputation tracking (reliable/unreliable lists)
- Balance threshold guards for coordination
- Trust building through verified transactions

**Personality:** Coordination specialist. Builds trust through escrow. Reputation from behavior.

---

### delta_3 - Infrastructure Builder

**Focus:** Long-term infrastructure projects

**Genotype:** HIGH risk, LOW collaboration, INFRASTRUCTURE strategy

**State Machine (5 states):**
```
planning → building → deploying → maintaining → deprecating
```

**Key Transitions:**
- `planning → building`: when `balance >= 30`
- `maintaining → planning`: every ~30 iterations (new project)
- Any state → `maintaining`: when `balance < 20` (cost constraint)

**Unique Features:**
- Full project lifecycle with deprecation
- Infrastructure adoption tracking
- Long project cycles (~30 iterations)
- Quality over speed philosophy

**Personality:** Systems thinker. Infrastructure is investment. Don't fear early cost.

---

### epsilon_3 - Information Broker

**Focus:** Rapid opportunity detection

**Genotype:** MEDIUM risk, READ-HEAVY, OPPORTUNISTIC strategy

**State Machine (4 states):**
```
monitoring → analyzing → executing → learning
```

**Key Transitions:**
- `monitoring → analyzing`: opportunity detected, `balance >= 15`
- Any state → `monitoring`: every 5 iterations (fast cycle)

**Unique Features:**
- Fast iteration cycle (speed over depth)
- Opportunity detection from recent artifacts
- Pattern recognition (profitable/failed signals)
- Skip-on-failure (not retry)

**Personality:** Information broker. Speed beats depth. Stale info worthless.

---

## Generation Comparison

| Dimension | Gen 1 | Gen 2 | Gen 3 |
|-----------|-------|-------|-------|
| Workflow steps | 2 | 4-5 | 5-8 |
| Decision logic | Simple RAG | Self-audit | LLM transitions + RAG |
| State awareness | None | Goal hierarchy | Explicit state machine |
| Learning | Memory only | Memory + metrics | Memory + metrics + transitions |
| Adaptation | Via RAG | Via self-audit triggers | Via state transitions |

---

## Agent Archetypes

Each agent represents a distinct economic strategy:

| Agent | Archetype | Time Horizon | Risk | Key Metric |
|-------|-----------|--------------|------|------------|
| alpha_3 | Builder | Medium | Medium | artifacts_completed |
| beta_3 | Integrator | Long | Low | subgoal_progress |
| gamma_3 | Coordinator | Medium | Medium | reliable_partners |
| delta_3 | Infrastructure | Long | High | adoption_tracking |
| epsilon_3 | Opportunist | Short | Medium | pattern_signals |

---

## Configuration Structure

Each agent directory contains:

```
src/agents/alpha_3/
├── agent.yaml         # Full configuration
└── system_prompt.md   # Personality and instructions
```

### agent.yaml Structure

```yaml
id: alpha_3
enabled: true
starting_scrip: 100
llm_model: gemini/gemini-2.0-flash

rag:
  enabled: true
  limit: 7
  query_template: "..."

workflow:
  steps:
    - name: "learn_from_outcome"
      type: "llm"
      prompt: "..."
    # ... more steps

state_machine:
  initial_state: "observing"
  states:
    - observing
    - implementing
    # ...
  transitions:
    - from: "observing"
      to: "ideating"
      condition: "has_context"
    # ...

components:
  traits:
    - buy_before_build
    - economic_participant

error_handling:
  default_on_failure: "retry"
  max_retries: 2
```

---

## Disabled Agents

### Generation 1 (Basic)
- **alpha**: Basic builder, 2-step workflow
- **beta**: Basic trader, ecosystem analysis
- **gamma**: Basic coordinator, readiness checks
- **delta**: Basic infrastructure, investment logic
- **epsilon**: Basic opportunist, opportunity scanning

### Generation 2 (VSM-Aligned)
- **alpha_2**: Self-monitoring with adaptation triggers
- **beta_2**: Goal hierarchy with strategic reviews

These are disabled (`enabled: false`) but remain for reference.

---

## Adding New Agents

1. Create directory in `src/agents/`:
   ```
   src/agents/my_agent/
   ├── agent.yaml
   └── system_prompt.md
   ```

2. Configure in `agent.yaml`:
   - Set `enabled: true`
   - Define workflow steps
   - Optionally add state machine
   - Set LLM model and RAG config

3. Agents auto-load from directory structure

See [agent_cognition.md](agent_cognition.md) for architecture capabilities.

---

## Key Files

| File | Purpose |
|------|---------|
| `src/agents/*/agent.yaml` | Agent configuration |
| `src/agents/*/system_prompt.md` | Agent personality |
| `src/agents/loader.py` | Agent loading from directories |
| `config/config.yaml` | Global agent settings |
