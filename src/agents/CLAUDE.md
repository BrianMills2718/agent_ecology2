# Agents Module

LLM-powered agents that observe world state and propose actions.

## Module Responsibilities

| File | Responsibility |
|------|----------------|
| `agent.py` | LLM integration, action proposal, token tracking |
| `memory.py` | Mem0/Qdrant integration for persistent memory |
| `loader.py` | Agent discovery from `src/agents/*/` directories |
| `schema.py` | Action schema definitions for LLM |
| `models.py` | Pydantic models for agent config and results |

## Agent Directories

Each agent lives in `src/agents/{name}/`:
```
src/agents/alpha/
├── agent.yaml      # Config (model, starting_scrip, RAG settings)
└── system_prompt.md  # Agent personality and instructions
```

Seeded agents: `alpha`, `beta`, `gamma`, `delta`, `epsilon`

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
pytest tests/test_async_agent.py tests/test_memory.py tests/test_loader.py -v
```
