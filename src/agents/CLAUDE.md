# Agents Module - DEPRECATED (Plan #299)

The legacy agent system has been removed. This directory is now a placeholder.

## Remaining Files

| File | Purpose |
|------|---------|
| `__init__.py` | Empty placeholder - exports nothing |

## New Architecture

Agents are now **3-artifact clusters** loaded by the genesis system:

1. **Strategy artifact** (text) - System prompt and instructions
2. **State artifact** (JSON) - Agent's working memory and state
3. **Loop artifact** (executable, has_loop=True) - Autonomous behavior code

See `config/genesis/agents/alpha_prime/` for the reference implementation.

## What Was Removed

| File | Lines | Was |
|------|-------|-----|
| `agent.py` | ~2700 | LLM wrapper with 77 methods |
| `workflow.py` | ~1100 | State machine engine |
| `loader.py` | ~300 | Agent discovery |
| `memory.py` | ~800 | Mem0/Qdrant integration |
| `schema.py` | ~600 | Action schema definitions |
| `models.py` | ~400 | Pydantic models |
| `hooks.py` | ~400 | Workflow hooks |
| `state_machine.py` | ~300 | State machine definitions |
| `state_store.py` | ~350 | SQLite state persistence |
| `component_loader.py` | ~400 | Prompt component loading |
| `motivation_loader.py` | ~150 | Motivation profiles |
| `agent_schema.py` | ~450 | Agent.yaml validation |
| `planning.py` | ~160 | Plan artifact patterns |
| `reflex.py` | ~350 | Pre-LLM decision scripts |
| `safe_eval.py` | ~90 | Secure expression evaluation |
| `template.py` | ~70 | Template rendering |

**Total removed:** ~8600 lines of legacy code

## Historical Reference

- `docs/catalog.yaml` - Agent lineage tracking (moved from here)
- Previous agent directories: alpha/, beta/, gamma/, delta/, epsilon/ (and _3 variants)
- discourse_analyst variants also removed

## Key Pattern: Artifact-Based Agents

```python
# Genesis loader creates 3 artifacts for each agent:
# 1. alpha_prime_strategy (text) - prompt
# 2. alpha_prime_state (JSON) - state
# 3. alpha_prime_loop (executable, has_loop=True) - behavior

# ArtifactLoopManager discovers and runs has_loop=True artifacts
manager.discover_loops()  # Finds alpha_prime_loop
manager.start_all()       # Runs loops autonomously
```

## Strict Couplings

This directory is now minimal. Main coupling is:
- `docs/architecture/current/agents.md` - Must be updated to reflect new architecture
