# Agents Module

LLM-powered agents that observe world state and propose actions.

## Module Responsibilities

| File | Responsibility |
|------|----------------|
| `__init__.py` | Package exports (Agent, ActionResult, load_agents, etc.) |
| `agent.py` | LLM integration, action proposal, token tracking |
| `agent_schema.py` | Pydantic schema for agent.yaml validation |
| `catalog.yaml` | Agent lineage tracking and genotype characteristics |
| `component_loader.py` | Modular prompt component loading and injection |
| `hooks.py` | Workflow hooks for auto-invocation at timing points |
| `loader.py` | Agent discovery from `src/agents/*/` directories |
| `memory.py` | Mem0/Qdrant integration for persistent memory |
| `models.py` | Pydantic models for agent config and results |
| `planning.py` | Plan artifact pattern for deliberative agent behavior |
| `reflex.py` | Fast pre-LLM decision scripts (agent-created artifacts) |
| `safe_eval.py` | Secure expression evaluation for workflow conditions |
| `schema.py` | Action schema definitions for LLM |
| `state_machine.py` | State machine definitions and transitions |
| `state_store.py` | SQLite-backed agent state persistence between turns |
| `template.py` | Safe `{{variable}}` template rendering for workflow context |
| `workflow.py` | Configurable workflow execution with state machine support |

## Agent Directories

Each agent lives in `src/agents/{name}/`:
```
src/agents/alpha/
├── agent.yaml      # Config (model, starting_scrip, RAG settings)
└── system_prompt.md  # Agent personality and instructions
```

## Agent Generations

| Generation | Agents | Features |
|------------|--------|----------|
| Original | alpha, beta, gamma, delta, epsilon | Basic workflows, RAG memory |
| _2 (VSM-aligned) | alpha_2, beta_2 | Self-audit, goal hierarchies, adaptation triggers |
| _3 (State machines) | alpha_3, beta_3, gamma_3, delta_3, epsilon_3 | Explicit state machines |

### _3 Generation State Machines

| Agent | Focus | States |
|-------|-------|--------|
| alpha_3 | Builder | ideating → designing → implementing → testing |
| beta_3 | Integrator | strategic → tactical → operational → reviewing |
| gamma_3 | Coordinator | solo → discovering → negotiating → executing → settling |
| delta_3 | Infrastructure | planning → building → deploying → maintaining → deprecating |
| epsilon_3 | Info Broker | monitoring → analyzing → executing → learning |

## Key Patterns

### Async Thinking
```python
# Agents think in parallel via asyncio.gather()
results = await asyncio.gather(*[agent.propose_action_async() for agent in agents])
```

### Memory Integration
```python
# Memory uses Mem0 with Qdrant backend
memory.add(agent_id, "Learned that trading is profitable")
relevant = memory.search(agent_id, "trading strategies", limit=5)
```

### Token Tracking
```python
# Every LLM call tracks input/output tokens
result = agent.propose_action(world_state)
# result.input_tokens, result.output_tokens available
```

## Strict Couplings

Changes here MUST update `docs/architecture/current/agents.md`.

## Testing

```bash
pytest tests/unit/test_async_agent.py tests/unit/test_memory.py -v
```
