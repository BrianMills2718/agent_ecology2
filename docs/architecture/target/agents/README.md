# Agent Architecture

How agents are configured and how they execute. This documentation separates:

- **Configurability Space** - What CAN be configured (the framework)
- **Genesis Instantiation** - How genesis agents ARE configured (alpha_3, beta_3, delta_3)

---

## Terminology

| Term | Definition | YAML Field |
|------|------------|------------|
| **Agent** | Artifact with `has_standing=True` AND `can_execute=True` | - |
| **Workflow** | Sequence of steps an agent executes | `workflow:` |
| **State Machine** | States with conditional transitions | `workflow.state_machine:` |
| **Step** | Single unit of work (LLM call, code, or transition decision) | `workflow.steps:` |
| **Injected Prompt Component** | Reusable prompt fragment injected into steps | `components.traits:` |
| **Goal** | High-level directive always present in prompts | `components.goals:` |

---

## Document Structure

| Document | Content |
|----------|---------|
| [01_ontology.md](01_ontology.md) | What is an agent (artifacts with standing + execution) |
| [02_execution.md](02_execution.md) | How agents execute (state machines, steps, transitions) |
| [03_configuration.md](03_configuration.md) | Configurable components (injected prompt components, goals) |
| [04_memory.md](04_memory.md) | Memory systems (working, longterm, semantic) |
| [genesis.md](genesis.md) | Genesis agent configurations (alpha_3, beta_3, gamma_3, delta_3, epsilon_3) |

---

## Key Diagrams

### Agent Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         AGENT TURN                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Check current state (e.g., "observing")                     │
│                    ↓                                            │
│  2. Find step with matching in_state                            │
│                    ↓                                            │
│  3. Build prompt:                                               │
│     ┌─────────────────────────────────────────────────────┐    │
│     │ Step prompt (from workflow.steps)                   │    │
│     ├─────────────────────────────────────────────────────┤    │
│     │ + Injected prompt component 1 (if inject_into match)│    │
│     │ + Injected prompt component 2 (if inject_into match)│    │
│     │ + ...                                               │    │
│     └─────────────────────────────────────────────────────┘    │
│                    ↓                                            │
│  4. Make LLM call (for type: llm steps)                         │
│                    ↓                                            │
│  5. Execute returned action                                     │
│                    ↓                                            │
│  6. Transition to next state                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Prompt Composition

```
┌─────────────────────────────────────────────────────────────────┐
│                    FINAL PROMPT TO LLM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ STEP PROMPT (from agent.yaml → workflow.steps)          │   │
│  │                                                         │   │
│  │ === GOAL: Maximize scrip balance ===                    │   │
│  │ You are {agent_id}. Balance: {balance}...               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           +                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ INJECTED PROMPT COMPONENT (loop_breaker)                │   │
│  │ Injected because: inject_into includes "observe"        │   │
│  │                                                         │   │
│  │ === LOOP DETECTION ===                                  │   │
│  │ Check your "Recent Actions" section...                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           +                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ INJECTED PROMPT COMPONENT (semantic_memory)             │   │
│  │ Injected because: inject_into includes "observe"        │   │
│  │                                                         │   │
│  │ === LEARNING ===                                        │   │
│  │ ASK YOURSELF: What did I just learn...                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### State Machine (alpha_3 example)

```
                    ┌──────────────┐
                    │  observing   │◄─────────────────────┐
                    └──────┬───────┘                      │
                           │                              │
              ┌────────────┼────────────┐                 │
              ▼            ▼            │                 │
     ┌──────────────┐ ┌──────────┐      │                 │
     │ discovering  │ │ ideating │      │                 │
     └──────┬───────┘ └────┬─────┘      │                 │
            │              │            │                 │
            └──────┬───────┘            │                 │
                   ▼                    │                 │
            ┌──────────────┐            │                 │
            │  designing   │            │                 │
            └──────┬───────┘            │                 │
                   ▼                    │                 │
            ┌──────────────┐            │                 │
            │ implementing │◄───────────┤ (continue)      │
            └──────┬───────┘            │                 │
                   ▼                    │                 │
            ┌──────────────┐            │                 │
            │   testing    │            │                 │
            └──────┬───────┘            │                 │
                   ▼                    │                 │
            ┌──────────────┐            │                 │
            │  reflecting  │────────────┤                 │
            └──────┬───────┘            │                 │
                   │                    │ (pivot)         │
                   │ (ship)             └─────────────────┤
                   ▼                                      │
            ┌──────────────┐                              │
            │   shipping   │──────────────────────────────┘
            └──────────────┘
```

---

## Configurability vs Capability

The YAML structure is syntax; what matters is capability:

| Capability | Supported | Notes |
|------------|-----------|-------|
| Define states | ✓ | Any number of states |
| Define transitions | ✓ | Conditional or unconditional |
| Inject prompt text into steps | ✓ | Via injected prompt components |
| Choose which steps receive injection | ✓ | Via `inject_into` |
| Step types: LLM, code, transition | ✓ | Fixed set |
| **Conditional injection at runtime** | ✗ | Plan #222 addresses |
| **Artifact invocation in transitions** | ✗ | Plan #222 addresses |
| **Injection position control** | ✗ | Always appends |
| **Custom step types** | ✗ | Would need code change |

---

## Implementation Maturity

Current implementation status of agent subsystems (from [../../current/agent_cognition.md](../../current/agent_cognition.md)):

| Subsystem | Maturity | Key Gap |
|-----------|----------|---------|
| Prompts & Workflows | 90% | Prompt size management |
| State Machines | 85% | Agents don't use intentionally |
| Memory Systems | 80% | Incentive alignment |
| Decision-Making | 75% | Limited action space |
| Loop Detection | 75% | Passive only, no enforcement |
| Artifact Intelligence | 70% | Runner integration, hooks |
| Reflexes | 60% | No creation guidance |
| Self-Modification | 60% | Safety/atomicity |

See [../../current/agent_cognition.md](../../current/agent_cognition.md) for detailed gap analysis.

---

## Related

- [../03_agents.md](../03_agents.md) - Target agent model (higher-level vision)
- [Plan #155](../../../plans/155_v4_architecture_deferred.md) - Agents as artifact patterns (deferred)
- [Plan #222](../../../plans/222_artifact_aware_workflow.md) - Artifact-aware workflow engine
- [CONCERNS.md](../../../CONCERNS.md) - Design concerns to watch
