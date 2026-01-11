# Agent Ecology - Claude Code Context

This file is always loaded. Keep it lean. Reference other docs for details.

## What This Is

A simulation where LLM agents interact under real resource constraints (compute, disk, API budget).

## Project Structure

```
agent_ecology/
  run.py                    # Main entry point
  pyproject.toml            # Package config
  config/
    config.yaml             # Runtime values
    schema.yaml             # Structure + defaults
  src/
    config.py               # Config helpers: get(), get_genesis_config()
    config_schema.py        # Pydantic config validation
    world/                  # World state, ledger, executor, artifacts
    agents/                 # Agent loading, LLM interaction, memory
    simulation/             # SimulationRunner, checkpoint
    dashboard/              # HTML dashboard server
  tests/                    # pytest suite
  docs/                     # Extended documentation
```

## Key Commands

```bash
pip install -e .                              # Required for imports
python run.py --ticks 10 --agents 1           # Run simulation
pytest tests/                                 # Run tests (must pass)
python -m mypy src/ --ignore-missing-imports  # Type check (must pass)
```

---

## Design Principles

### 1. Fail Loud, No Silent Fallbacks

**Development must surface all errors immediately.**

- No `except: pass` - all exceptions handled explicitly with logging
- No silent fallbacks - if something fails, raise an error
- If fallback has production value: document in `docs/FALLBACKS.md` with feature flag (OFF in dev)
- Use `raise RuntimeError()` not `assert` for runtime checks

```python
# WRONG - hides bugs
except Exception:
    result = default

# RIGHT - fail loud in dev, optional fallback in prod
except APIError as e:
    if get("fallbacks.api_cache.enabled"):  # OFF in dev
        logger.warning("API failed, using cache: %s", e)
        return cached_value
    raise
```

### 2. Maximum Observability

**Every significant operation must be traceable.**

- Log all state changes with context (agent_id, tick, action)
- Use structured logging (key=value pairs)
- Errors must include full context for debugging
- Never swallow exceptions without logging

### 3. High Configurability

**Everything from config, not code.**

- No magic numbers in source files
- All values in `config/config.yaml`, schema in `config/schema.yaml`
- Use `src/config.py`: `get()`, `get_genesis_config()`

### 4. Strong Typing

- `mypy --strict` compliance required
- Pydantic models for structured data
- No `Any` without explicit justification

### 5. Physics-First

- Stock resources (llm_budget, disk): Finite, never refresh
- Flow resources (compute): Quota per tick, use-or-lose
- Scrip: Economic signal, separate from physical constraints

---

## Coding Standards

### Imports

```python
# Within src/ - relative imports
from ..config import get
from .ledger import Ledger

# From run.py or tests - absolute
from src.world import World
```

### Terminology

| Use | Not |
|-----|-----|
| `compute` | `flow` |
| `disk` | `stock` |
| `scrip` | `credits` |
| `principal` | `account` |
| `tick` | `turn` |

### Testing Philosophy

1. **Prefer real tests over mocks** - Test actual behavior, not mocked interfaces
2. **Mock only when necessary** - External APIs, network calls, time-sensitive operations
3. **If mocking, document why** - Comment explaining why mock is required
4. **Integration tests are valuable** - Test components working together

### Documentation Rules

1. **Code is primary** - Make code self-explanatory, minimal comments
2. **Update docs with code** - Changed behavior = updated docs
3. **Reference, don't duplicate** - Point to other docs
4. **CLAUDE.md stays lean** - It's always in context window

---

## Genesis Artifacts

| Artifact | Purpose |
|----------|---------|
| `genesis_ledger` | Balances, transfers, ownership |
| `genesis_oracle` | Auction-based scoring, minting |
| `genesis_rights_registry` | Quota management |
| `genesis_event_log` | Passive observability |
| `genesis_escrow` | Trustless artifact trading |
| `genesis_handbook` | Seeded documentation for agents |

---

## Multi-CC Instance Coordination

Multiple Claude Code instances may work simultaneously.

### Workflow

1. **Claim**: Move task from Backlog to In Progress, add CC-ID
2. **Plan**: Document approach in `temp_plan/CC-[ID]_[task].md`
3. **Implement**: Do work, update docs
4. **Mark Done**: Move to Awaiting Review
5. **Review**: Another CC verifies (tests + mypy pass, code correct)
6. **Archive**: Reviewer moves to `docs/TASK_LOG.md`

### Active Instances

| CC-ID | Task | Started |
|-------|------|---------|
| CC-1 | Align config defaults | 2025-01-11 |
| CC-2 | Available | - |
| CC-3 | Available | - |
| CC-4 | Move hardcoded values to config | 2025-01-11 |

### Task Backlog

| Task | Description | Priority |
|------|-------------|----------|
| Add artifact ID length validation | Prevent DoS | Low |
| Document Windows timeout limitation | signal.alarm Unix-only | Low |

### In Progress

| Task | CC-ID | Started | Notes |
|------|-------|---------|-------|
| Move hardcoded values to config | CC-4 | 2025-01-11 | Model names, timeouts |
| Align config defaults | CC-1 | 2025-01-11 | Dashboard port, compute unit mismatches |

### Awaiting Review

| Task | CC-ID | Completed | Reviewer |
|------|-------|-----------|----------|
| (none) | - | - | - |

### Coordination Rules

1. **One task at a time** - Finish or abandon before claiming another
2. **Update this file first** - Claim before starting work
3. **Tests + mypy must pass** - Before marking done
4. **Review required** - Another CC verifies before archiving to `docs/TASK_LOG.md`

### Review Checklist

- [ ] `pytest tests/` passes
- [ ] `python -m mypy src/ --ignore-missing-imports` passes
- [ ] Code matches task description
- [ ] No new silent fallbacks
- [ ] Relevant docs updated

---

## References

| Doc | Purpose |
|-----|---------|
| `docs/TASK_LOG.md` | Completed task history |
| `docs/FALLBACKS.md` | Fallback registry with feature flags |
| `docs/RESOURCE_MODEL.md` | Resource system design |
| `docs/DEFERRED_FEATURES.md` | Features considered but deferred |
| `docs/IMPLEMENTATION_PLAN.md` | Historical implementation notes |
| `config/schema.yaml` | All config options documented |
