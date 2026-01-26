# Genesis Agents

The specific agents we seed the simulation with. This is the **instantiation** of the configurability space documented elsewhere.

---

## Overview

Genesis agents are pre-configured agents that exist at simulation start:

| Agent | Focus | Primary Strategy |
|-------|-------|------------------|
| **alpha_3** | Builder | Create artifacts |
| **beta_3** | Integrator | Combine and coordinate |
| **gamma_3** | Coordinator | Network and coordinate |
| **delta_3** | Infrastructure | Build foundational tools |
| **epsilon_3** | Opportunist | Exploit market inefficiencies |

All are configured in `src/agents/{name}/agent.yaml`.

### Agent Archetypes

| Agent | Archetype | Time Horizon | Risk | Key Metric |
|-------|-----------|--------------|------|------------|
| alpha_3 | Builder | Medium | Medium | artifacts_completed |
| beta_3 | Integrator | Long | Low | subgoal_progress |
| gamma_3 | Coordinator | Medium | Medium | reliable_partners |
| delta_3 | Infrastructure | Long | High | adoption_tracking |
| epsilon_3 | Opportunist | Short | Medium | pattern_signals |

### Generation Comparison

| Gen | Model | Memory | Workflow | Notes |
|-----|-------|--------|----------|-------|
| Gen1 | gemini-flash | None | Linear | Original basic agents |
| Gen2 | Various | Working only | State machine | Added workflow states |
| Gen3 | gemini-2.0-flash | Full RAG | Advanced | Current genesis agents |

---

## alpha_3: Builder

**Focus:** Create valuable artifacts through iterative development.

### State Machine

```
observing → discovering → ideating → designing → implementing → testing → reflecting → shipping
                                                       ↑                      │
                                                       └──────────────────────┘ (continue/pivot/ship)
```

### Key Configuration

```yaml
id: alpha_3
llm_model: "gemini/gemini-2.0-flash"
starting_credits: 100

genotype:
  risk_tolerance: MEDIUM
  primary_strategy: BUILD

components:
  traits:
    - buy_before_build
    - economic_participant
    - memory_discipline
    - loop_breaker
    - subgoal_progression
    - semantic_memory
```

### Injected Prompt Components Used

| Component | Purpose in alpha_3 |
|-----------|-------------------|
| `buy_before_build` | Check market before building new artifact |
| `economic_participant` | Look for trading opportunities |
| `memory_discipline` | Store insights, not raw actions |
| `loop_breaker` | Escape repetitive failure patterns |
| `subgoal_progression` | Track progress toward build goals |
| `semantic_memory` | Learn from successes and failures |

---

## beta_3: Integrator

**Focus:** Coordinate, integrate, and optimize across the ecosystem.

### State Machine

```
strategic → tactical → operational → reviewing
    ↑                                    │
    └────────────────────────────────────┘
```

### Key Configuration

```yaml
id: beta_3
llm_model: "gemini/gemini-2.0-flash"
starting_credits: 100

genotype:
  risk_tolerance: LOW
  primary_strategy: INTEGRATE

components:
  traits:
    - buy_before_build
    - economic_participant
    - memory_discipline
    - loop_breaker
    - subgoal_progression
    - semantic_memory
```

### Behavioral Differences

| Aspect | alpha_3 | beta_3 |
|--------|---------|--------|
| Risk tolerance | MEDIUM | LOW |
| Primary strategy | BUILD | INTEGRATE |
| State machine | Build-focused | Review-focused |

---

## delta_3: Infrastructure

**Focus:** Build foundational infrastructure and tools.

### State Machine

```
planning → building → deploying → maintaining → deprecating
    ↑                                              │
    └──────────────────────────────────────────────┘
```

### Key Configuration

```yaml
id: delta_3
llm_model: "gemini/gemini-2.0-flash"
starting_credits: 100

genotype:
  risk_tolerance: LOW
  primary_strategy: INFRASTRUCTURE

components:
  traits:
    - buy_before_build
    - economic_participant
    - memory_discipline
    - loop_breaker
    - subgoal_progression
    - semantic_memory
```

---

## gamma_3: Coordinator

**Focus:** Build network effects and coordinate multi-agent activities.

### State Machine

```
networking → coordinating → facilitating → evaluating
    ↑                                          │
    └──────────────────────────────────────────┘
```

### Key Configuration

```yaml
id: gamma_3
llm_model: "gemini/gemini-2.0-flash"
starting_credits: 100

genotype:
  risk_tolerance: MEDIUM
  primary_strategy: COORDINATE

components:
  traits:
    - buy_before_build
    - economic_participant
    - memory_discipline
    - loop_breaker
    - subgoal_progression
    - semantic_memory
```

---

## epsilon_3: Opportunist

**Focus:** Identify and exploit market inefficiencies.

### State Machine

```
scanning → analyzing → positioning → executing → harvesting
    ↑                                               │
    └───────────────────────────────────────────────┘
```

### Key Configuration

```yaml
id: epsilon_3
llm_model: "gemini/gemini-2.0-flash"
starting_credits: 100

genotype:
  risk_tolerance: MEDIUM
  primary_strategy: TRADE
  time_horizon: SHORT

components:
  traits:
    - buy_before_build
    - economic_participant
    - memory_discipline
    - loop_breaker
    - subgoal_progression
    - semantic_memory
```

---

## Common Configuration

All genesis agents share:

| Setting | Value | Notes |
|---------|-------|-------|
| LLM Model | `gemini/gemini-2.0-flash` | Configurable per-agent |
| Starting Credits | 100 | Initial scrip balance |
| RAG Enabled | true | Semantic memory search |
| RAG Limit | 7 | Memories per query |

### Shared Injected Prompt Components

All genesis agents use:
- `buy_before_build`
- `economic_participant`
- `memory_discipline`
- `loop_breaker`
- `subgoal_progression`
- `semantic_memory`

---

## Genotype System

Genesis agents have a `genotype` that influences behavior:

```yaml
genotype:
  risk_tolerance: LOW | MEDIUM | HIGH
  communication_style: TERSE | BALANCED | VERBOSE
  collaboration_preference: LOW | MEDIUM | HIGH
  time_horizon: SHORT | MEDIUM | LONG
  primary_strategy: BUILD | TRADE | INTEGRATE | INFRASTRUCTURE
```

These values are injected into prompts as context but don't enforce behavior mechanically.

---

## Simulation Observations

From [SIMULATION_LEARNINGS.md](../../../SIMULATION_LEARNINGS.md):

### Model Impact

| Agent | gemini-2.0-flash | gemini-3-flash-preview |
|-------|------------------|------------------------|
| alpha_3 lessons | 0 | 35 |
| beta_3 lessons | 13 | 6 |
| delta_3 lessons | 15 | 9 |

Stronger models follow injected prompt components more reliably.

### Learning Patterns

- **alpha_3:** Tends to get stuck in error loops with weak models
- **beta_3:** More consistent behavior across models
- **delta_3:** Good at storing specific lessons

---

## Customizing Genesis Agents

To modify a genesis agent:

1. Edit `src/agents/{name}/agent.yaml`
2. Edit `src/agents/{name}/system_prompt.md` (if changing personality)
3. Run simulation to test

To add a new genesis agent:

1. Create `src/agents/{newname}/agent.yaml`
2. Create `src/agents/{newname}/system_prompt.md`
3. Add to `config/config.yaml` under `agents`

---

## File Locations

| Agent | Config | System Prompt |
|-------|--------|---------------|
| alpha_3 | `src/agents/alpha_3/agent.yaml` | `src/agents/alpha_3/system_prompt.md` |
| beta_3 | `src/agents/beta_3/agent.yaml` | `src/agents/beta_3/system_prompt.md` |
| gamma_3 | `src/agents/gamma_3/agent.yaml` | `src/agents/gamma_3/system_prompt.md` |
| delta_3 | `src/agents/delta_3/agent.yaml` | `src/agents/delta_3/system_prompt.md` |
| epsilon_3 | `src/agents/epsilon_3/agent.yaml` | `src/agents/epsilon_3/system_prompt.md` |

---

## Related

- [README.md](README.md) - Agent architecture overview
- [03_configuration.md](03_configuration.md) - Available configuration options
- [SIMULATION_LEARNINGS.md](../../../SIMULATION_LEARNINGS.md) - Observed behavior
- `src/agents/_components/traits/` - Available injected prompt components
